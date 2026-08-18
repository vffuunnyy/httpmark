import json
import random
import subprocess
import sys
import tempfile

from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from rich.progress import Progress, TaskID

from httpmark.clients import ASYNC_HTTP1_CLIENTS, ASYNC_HTTP2_CLIENTS, SYNC_CLIENTS
from httpmark.config import BenchmarkConfig
from httpmark.metrics import ClientResult


CATEGORIES = [
    ("sync-http1", "Sync HTTP/1.1", "sync", "1.1"),
    ("async-http1", "Async HTTP/1.1", "async", "1.1"),
    ("async-http2", "Async HTTP/2", "async", "2"),
]


@dataclass
class PlanEntry:
    category_key: str
    category_label: str
    mode: str
    http_version: str
    client: str
    task_id: TaskID | None = None
    result: ClientResult | None = None
    notes: list[str] = field(default_factory=list)


def build_plan(categories: list[str] | None, client_filter: list[str] | None) -> list[PlanEntry]:
    registry = {
        "sync-http1": SYNC_CLIENTS,
        "async-http1": ASYNC_HTTP1_CLIENTS,
        "async-http2": ASYNC_HTTP2_CLIENTS,
    }
    plan: list[PlanEntry] = []
    for key, label, mode, http_version in CATEGORIES:
        if categories is not None and key not in categories:
            continue
        for cls in registry[key]:
            if client_filter is not None and cls.name not in client_filter:
                continue
            plan.append(PlanEntry(key, label, mode, http_version, cls.name))
    return plan


def _split_iterations(total: int, rounds: int) -> list[int]:
    base, remainder = divmod(total, rounds)
    return [base + (1 if r < remainder else 0) for r in range(rounds)]


def _run_worker(
    spec: dict,
    on_progress: Callable[[], None],
    on_note: Callable[[str], None],
) -> tuple[dict | None, str | None]:
    with tempfile.TemporaryFile(mode="w+") as stderr_file:
        proc = subprocess.Popen(
            [sys.executable, "-m", "httpmark.worker"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
        )
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError("worker pipes were not created")
        proc.stdin.write(json.dumps(spec))
        proc.stdin.close()

        result: dict | None = None
        fatal: str | None = None
        for line in proc.stdout:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("event")
            if kind == "progress":
                on_progress()
            elif kind == "iteration_error":
                on_note(event["error"])
            elif kind == "result":
                result = event
            elif kind == "fatal":
                fatal = event["error"]

        proc.wait()
        if result is None and fatal is None:
            stderr_file.seek(0)
            tail = stderr_file.read()[-2000:].strip()
            fatal = f"worker exited with code {proc.returncode}" + (f": {tail}" if tail else "")
        return result, fatal


def _run_round(
    config: BenchmarkConfig,
    entry: PlanEntry,
    iterations: int,
    total_ticks: int,
    progress: Progress,
) -> None:
    spec = {
        "client": entry.client,
        "mode": entry.mode,
        "http_version": entry.http_version,
        "warmup": config.warmup,
        "iterations": iterations,
        "config": asdict(config),
    }
    task_id = entry.task_id
    payload, fatal = _run_worker(
        spec,
        on_progress=lambda task_id=task_id: progress.advance(task_id),
        on_note=entry.notes.append,
    )
    if fatal is not None:
        if entry.result is None:
            entry.result = ClientResult(entry.client, entry.category_label, error=fatal)
        else:
            entry.result.error = fatal
        progress.update(
            task_id,
            description=f"  {entry.client} [red]FAILED: {fatal[:60]}[/red]",
            completed=total_ticks,
        )
        return
    round_result = ClientResult.from_worker(entry.client, entry.category_label, payload)
    if entry.result is None:
        entry.result = round_result
    else:
        entry.result.merge(round_result)


def _add_progress_tasks(plan: list[PlanEntry], total_ticks: int, progress: Progress) -> None:
    seen_categories: list[str] = []
    for entry in plan:
        if entry.category_label not in seen_categories:
            seen_categories.append(entry.category_label)
            progress.add_task(f"[bold]{entry.category_label}[/bold]", total=0)
        entry.task_id = progress.add_task(f"  {entry.client}", total=total_ticks)


def execute(
    config: BenchmarkConfig,
    plan: list[PlanEntry],
    rounds: int,
    shuffle: bool,
    progress: Progress,
) -> dict[str, list[ClientResult]]:
    chunks = _split_iterations(config.iterations, rounds)
    total_ticks = rounds * config.warmup + config.iterations
    _add_progress_tasks(plan, total_ticks, progress)

    for round_index in range(rounds):
        order = list(plan)
        if shuffle:
            random.shuffle(order)
        for entry in order:
            if entry.result is not None and entry.result.error is not None:
                continue
            _run_round(config, entry, chunks[round_index], total_ticks, progress)
            if (
                round_index == rounds - 1
                and entry.result is not None
                and entry.result.error is None
            ):
                progress.update(entry.task_id, completed=total_ticks)

    results: dict[str, list[ClientResult]] = {}
    for entry in plan:
        if entry.result is None:
            continue
        entry.result.notes = list(dict.fromkeys(entry.notes))[:5]
        if entry.result.error is None:
            progress.update(entry.task_id, description=f"  {entry.client} [green]done[/green]")
        results.setdefault(entry.category_label, []).append(entry.result)
    return results
