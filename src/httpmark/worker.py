import asyncio
import gc
import json
import signal
import sys
import time
from array import array
from collections import Counter

from httpmark import system
from httpmark.clients import get_async_client, get_sync_client
from httpmark.clients.base import AsyncClient, SyncClient
from httpmark.config import BenchmarkConfig


def _emit(obj: dict) -> None:
    print(json.dumps(obj), flush=True)


def _is_success(status: int) -> bool:
    return 200 <= status < 400


async def _async_iteration(client: AsyncClient, config: BenchmarkConfig) -> dict | None:
    url = config.url
    # single-threaded event loop makes next() on the shared iterator atomic
    pending = iter(range(config.total_requests))
    latencies = array("q")
    errors = 0

    async def pump() -> None:
        nonlocal errors
        for _ in pending:
            t0 = time.perf_counter_ns()
            try:
                status = await client.get(url)
            except Exception:
                errors += 1
                continue
            if _is_success(status):
                latencies.append(time.perf_counter_ns() - t0)
            else:
                errors += 1

    cpu_before = system.cpu_times()
    t_start = time.perf_counter_ns()
    workers = [asyncio.ensure_future(pump()) for _ in range(config.concurrency)]

    if config.iter_timeout > 0:
        done, unfinished = await asyncio.wait(workers, timeout=config.iter_timeout)
        if unfinished:
            for task in unfinished:
                task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            return None
        for task in done:
            exc = task.exception()
            if exc is not None:
                raise exc
    else:
        await asyncio.gather(*workers)

    duration_ns = time.perf_counter_ns() - t_start
    cpu_after = system.cpu_times()

    return {
        "ok": len(latencies),
        "errors": errors,
        "duration_ns": duration_ns,
        "lat_sum_ns": sum(latencies),
        "cpu_user": cpu_after[0] - cpu_before[0],
        "cpu_system": cpu_after[1] - cpu_before[1],
        "rss_bytes": system.current_rss_bytes(),
        "latencies": latencies,
    }


def _sync_iteration(client: SyncClient, config: BenchmarkConfig) -> dict:
    url = config.url
    latencies = array("q")
    errors = 0

    cpu_before = system.cpu_times()
    t_start = time.perf_counter_ns()

    for _ in range(config.sync_requests):
        t0 = time.perf_counter_ns()
        try:
            status = client.get(url)
        except Exception:
            errors += 1
            continue
        if _is_success(status):
            latencies.append(time.perf_counter_ns() - t0)
        else:
            errors += 1

    duration_ns = time.perf_counter_ns() - t_start
    cpu_after = system.cpu_times()

    return {
        "ok": len(latencies),
        "errors": errors,
        "duration_ns": duration_ns,
        "lat_sum_ns": sum(latencies),
        "cpu_user": cpu_after[0] - cpu_before[0],
        "cpu_system": cpu_after[1] - cpu_before[1],
        "rss_bytes": system.current_rss_bytes(),
        "latencies": latencies,
    }


def _sync_iteration_with_timeout(client: SyncClient, config: BenchmarkConfig) -> dict | None:
    if config.iter_timeout <= 0 or not hasattr(signal, "SIGALRM"):
        return _sync_iteration(client, config)

    def on_alarm(signum, frame):
        raise TimeoutError

    previous = signal.signal(signal.SIGALRM, on_alarm)
    signal.setitimer(signal.ITIMER_REAL, config.iter_timeout)
    try:
        return _sync_iteration(client, config)
    except TimeoutError:
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _collect(iterations: list[dict], hist: Counter) -> list[dict]:
    for it in iterations:
        for lat_ns in it.pop("latencies"):
            hist[lat_ns // 1000] += 1
    return iterations


async def _run_async(spec: dict, config: BenchmarkConfig) -> dict:
    client = get_async_client(spec["client"])()
    try:
        await client.setup(config, spec["http_version"])
    except Exception as e:
        _emit({"event": "fatal", "stage": "setup", "error": f"{type(e).__name__}: {e}"})
        sys.exit(1)

    for _ in range(spec["warmup"]):
        try:
            await _async_iteration(client, config)
        except Exception:
            pass
        _emit({"event": "progress"})

    gc.collect()
    gc.freeze()
    rss_baseline = system.current_rss_bytes()

    iterations: list[dict] = []
    timeouts = 0
    budget_start = time.monotonic()
    for _ in range(spec["iterations"]):
        gc.collect()
        try:
            it = await _async_iteration(client, config)
        except Exception as e:
            _emit({"event": "iteration_error", "error": f"{type(e).__name__}: {e}"})
            it = None
        if it is None:
            timeouts += 1
        else:
            iterations.append(it)
        _emit({"event": "progress"})
        if config.time_budget > 0 and time.monotonic() - budget_start > config.time_budget:
            break

    try:
        await client.teardown()
    except Exception:
        pass

    hist: Counter = Counter()
    return {
        "iterations": _collect(iterations, hist),
        "hist_us": dict(hist),
        "timeouts": timeouts,
        "rss_baseline": rss_baseline,
        "peak_rss": system.peak_rss_bytes(),
    }


def _run_sync(spec: dict, config: BenchmarkConfig) -> dict:
    client = get_sync_client(spec["client"])()
    try:
        client.setup(config)
    except Exception as e:
        _emit({"event": "fatal", "stage": "setup", "error": f"{type(e).__name__}: {e}"})
        sys.exit(1)

    for _ in range(spec["warmup"]):
        try:
            _sync_iteration_with_timeout(client, config)
        except Exception:
            pass
        _emit({"event": "progress"})

    gc.collect()
    gc.freeze()
    rss_baseline = system.current_rss_bytes()

    iterations: list[dict] = []
    timeouts = 0
    budget_start = time.monotonic()
    for _ in range(spec["iterations"]):
        gc.collect()
        try:
            it = _sync_iteration_with_timeout(client, config)
        except Exception as e:
            _emit({"event": "iteration_error", "error": f"{type(e).__name__}: {e}"})
            it = None
        if it is None:
            timeouts += 1
        else:
            iterations.append(it)
        _emit({"event": "progress"})
        if config.time_budget > 0 and time.monotonic() - budget_start > config.time_budget:
            break

    try:
        client.teardown()
    except Exception:
        pass

    hist: Counter = Counter()
    return {
        "iterations": _collect(iterations, hist),
        "hist_us": dict(hist),
        "timeouts": timeouts,
        "rss_baseline": rss_baseline,
        "peak_rss": system.peak_rss_bytes(),
    }


def main() -> None:
    spec = json.load(sys.stdin)
    config = BenchmarkConfig(**spec["config"])

    affinity = None
    affinity_error = None
    if config.cpu_affinity:
        affinity, affinity_error = system.apply_cpu_affinity(config.cpu_affinity)
    nice_level = system.raise_priority()

    if spec["mode"] == "async":
        result = asyncio.run(_run_async(spec, config))
    else:
        result = _run_sync(spec, config)

    result.update(
        {
            "event": "result",
            "affinity": affinity,
            "affinity_error": affinity_error,
            "nice": nice_level,
        }
    )
    _emit(result)


if __name__ == "__main__":
    main()
