import json

from dataclasses import asdict

from rich.console import Console
from rich.table import Table

from httpmark.config import BenchmarkConfig
from httpmark.metrics import ClientResult


def print_environment(
    console: Console, env: dict, config: BenchmarkConfig, warnings: list[str]
) -> None:
    machine = f"{env['os']} {env['arch']}, {env['cpu']} ({env['cpu_count']} cores)"
    console.print(f"[bold]httpmark[/bold] — {machine}")
    console.print(f"  Python: {env['python']}")
    versions = " · ".join(f"{name} {ver}" for name, ver in env["packages"].items())
    console.print(f"  Packages: {versions}")
    console.print(f"  URL: {config.url}")
    console.print(
        f"  Iterations: {config.iterations} (+{config.warmup} warmup/round), "
        f"async {config.total_requests} req/iter @ concurrency {config.concurrency}, "
        f"sync {config.sync_requests} req/iter"
    )
    affinity = config.cpu_affinity or "not set"
    console.print(f"  CPU affinity: {affinity}")
    for warning in warnings:
        console.print(f"  [yellow]warning:[/yellow] {warning}")
    console.print()


def print_category(console: Console, category: str, results: list[ClientResult]) -> None:
    failed = [r for r in results if not r.iterations]
    results = [r for r in results if r.iterations]
    if not results and not failed:
        console.print(f"\n[yellow]{category}: no results[/yellow]")
        return

    results.sort(key=lambda r: r.rps_median, reverse=True)

    table = Table(
        title=f"\n{category}",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
    )
    table.add_column("Client", style="bold", min_width=14)
    table.add_column("RPS med", justify="right", min_width=9)
    table.add_column("CV %", justify="right", min_width=6)
    table.add_column("p50 (ms)", justify="right", min_width=9)
    table.add_column("p95 (ms)", justify="right", min_width=9)
    table.add_column("p99 (ms)", justify="right", min_width=9)
    table.add_column("CPU µs/req", justify="right", min_width=10)
    table.add_column("RSS avg (MB)", justify="right", min_width=12)
    table.add_column("RSS peak (MB)", justify="right", min_width=13)
    table.add_column("Err", justify="right", min_width=5)
    table.add_column("TO iters", justify="right", min_width=8)

    best_rps = results[0].rps_median if results else 0

    for r in results:
        rps_pct = (r.rps_median / best_rps * 100) if best_rps > 0 else 0
        rps_color = "green" if rps_pct > 90 else "yellow" if rps_pct > 60 else "red"
        cv = r.rps_cv_pct
        cv_color = "dim" if cv < 5 else "yellow" if cv < 15 else "red"

        table.add_row(
            r.name,
            f"[{rps_color}]{r.rps_median:,.0f}[/{rps_color}]",
            f"[{cv_color}]{cv:.1f}[/{cv_color}]",
            f"{r.latency_percentile_ms(50):.2f}",
            f"{r.latency_percentile_ms(95):.2f}",
            f"{r.latency_percentile_ms(99):.2f}",
            f"{r.cpu_us_per_request:.1f}",
            f"{r.rss_avg_mb:.1f}",
            f"{r.rss_peak_mb:.1f}",
            f"[red]{r.error_total:,}[/red]" if r.error_total else "0",
            f"[red]{r.timeouts}[/red]" if r.timeouts else "0",
        )

    console.print(table)

    for r in results:
        if r.error is not None:
            console.print(f"  [red]{r.name}: partial data — {r.error}[/red]")
        for note in r.notes:
            console.print(f"  [dim]{r.name}: {note}[/dim]")
    for r in failed:
        console.print(f"  [red]{r.name}: {r.error or 'no successful iterations'}[/red]")


def print_all(console: Console, all_results: dict[str, list[ClientResult]]) -> None:
    for category, results in all_results.items():
        print_category(console, category, results)


def _result_dict(r: ClientResult) -> dict:
    return {
        "client": r.name,
        "rps_median": round(r.rps_median, 1),
        "rps_mean": round(r.rps_mean, 1),
        "rps_cv_pct": round(r.rps_cv_pct, 2),
        "latency_mean_ms": round(r.latency_mean_ms, 3),
        "latency_p50_ms": round(r.latency_percentile_ms(50), 3),
        "latency_p90_ms": round(r.latency_percentile_ms(90), 3),
        "latency_p95_ms": round(r.latency_percentile_ms(95), 3),
        "latency_p99_ms": round(r.latency_percentile_ms(99), 3),
        "latency_p999_ms": round(r.latency_percentile_ms(99.9), 3),
        "cpu_us_per_request": round(r.cpu_us_per_request, 2),
        "rss_avg_mb": round(r.rss_avg_mb, 1),
        "rss_peak_mb": round(r.rss_peak_mb, 1),
        "rss_baseline_mb": round(r.rss_baseline / (1024 * 1024), 1),
        "requests_ok": r.ok_total,
        "errors": r.error_total,
        "timeouts": r.timeouts,
        "error_rate": round(r.error_rate, 5),
        "iterations": len(r.iterations),
        "affinity": r.affinity,
        "error": r.error,
        "notes": r.notes,
        "per_iteration": [
            {
                "rps": round(it.rps, 1),
                "ok": it.ok,
                "errors": it.errors,
                "duration_s": round(it.duration_ns / 1e9, 4),
                "cpu_user_s": round(it.cpu_user, 4),
                "cpu_system_s": round(it.cpu_system, 4),
                "rss_mb": round(it.rss_bytes / (1024 * 1024), 1),
            }
            for it in r.iterations
        ],
    }


def to_json(
    all_results: dict[str, list[ClientResult]],
    env: dict,
    config: BenchmarkConfig,
    warnings: list[str],
) -> str:
    data: dict = {
        "environment": env,
        "config": asdict(config),
        "warnings": warnings,
        "results": {},
    }
    for category, results in all_results.items():
        entries = []
        for r in sorted(results, key=lambda r: r.rps_median, reverse=True):
            if r.iterations:
                entries.append(_result_dict(r))
            else:
                entries.append({"client": r.name, "error": r.error or "no successful iterations"})
        data["results"][category] = entries
    return json.dumps(data, indent=2)
