import argparse
import sys

from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn

from httpmark import system
from httpmark.clients import ASYNC_HTTP1_CLIENTS, ASYNC_HTTP2_CLIENTS, SYNC_CLIENTS, UNAVAILABLE
from httpmark.config import BenchmarkConfig
from httpmark.reporter import print_all, print_environment, to_json
from httpmark.runner import build_plan, execute


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="bench-req",
        description="HTTP client benchmarking suite",
    )
    p.add_argument("--url", default="https://httpbin.local:4443/get", help="Target URL")
    p.add_argument("--ca-cert", default="./certs/ca.crt", help="CA certificate file")
    p.add_argument(
        "--iterations", "-n", type=int, default=30, help="Measurement iterations per client"
    )
    p.add_argument("--warmup", type=int, default=3, help="Warmup iterations per round")
    p.add_argument(
        "--total-requests", "-r", type=int, default=10000, help="Requests per async iteration"
    )
    p.add_argument(
        "--concurrency", "-c", type=int, default=100, help="Concurrent workers per async iteration"
    )
    p.add_argument("--sync-requests", type=int, default=200, help="Requests per sync iteration")
    p.add_argument("--pool-size", type=int, default=100, help="Connection pool size")
    p.add_argument(
        "--cpu-affinity",
        default=None,
        help="Pin benchmark workers to these CPUs, e.g. '4-9' or '2,3,6' (Linux only)",
    )
    p.add_argument(
        "--rounds",
        type=int,
        default=1,
        help="Split iterations into N round-robin passes over all clients to average out drift",
    )
    p.add_argument(
        "--shuffle", action="store_true", help="Randomize client order within each round"
    )
    p.add_argument(
        "--categories",
        nargs="+",
        choices=["sync-http1", "async-http1", "async-http2"],
        default=None,
        help="Categories to run (default: all)",
    )
    p.add_argument(
        "--clients",
        nargs="+",
        default=None,
        help="Specific clients to run (e.g. aiohttp httpx rnet)",
    )
    p.add_argument(
        "--iter-timeout",
        type=float,
        default=120.0,
        help="Timeout per async iteration in seconds (0=none)",
    )
    p.add_argument(
        "--time-budget",
        type=float,
        default=0.0,
        help="Wall-clock seconds per client per round; slow clients stop early (0=off)",
    )
    p.add_argument("--json", action="store_true", help="Print results as JSON to stdout")
    p.add_argument("--output", type=Path, default=None, help="Also write JSON results to a file")
    return p.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    for name, value, minimum in (
        ("--iterations", args.iterations, 1),
        ("--warmup", args.warmup, 0),
        ("--total-requests", args.total_requests, 1),
        ("--concurrency", args.concurrency, 1),
        ("--sync-requests", args.sync_requests, 1),
        ("--pool-size", args.pool_size, 1),
        ("--rounds", args.rounds, 1),
    ):
        if value < minimum:
            sys.exit(f"{name} must be >= {minimum}")
    if args.rounds > args.iterations:
        sys.exit("--rounds cannot exceed --iterations")
    if args.cpu_affinity:
        try:
            system.parse_cpu_spec(args.cpu_affinity)
        except ValueError as e:
            sys.exit(f"invalid --cpu-affinity: {e}")
    if args.clients:
        known = {
            c.name
            for group in (SYNC_CLIENTS, ASYNC_HTTP1_CLIENTS, ASYNC_HTTP2_CLIENTS)
            for c in group
        }
        unknown = sorted(set(args.clients) - known)
        if unknown:
            sys.exit(f"unknown clients: {', '.join(unknown)} (known: {', '.join(sorted(known))})")


def main() -> None:
    args = parse_args()
    validate_args(args)

    config = BenchmarkConfig(
        url=args.url,
        ca_cert=args.ca_cert,
        iterations=args.iterations,
        warmup=args.warmup,
        total_requests=args.total_requests,
        concurrency=args.concurrency,
        sync_requests=args.sync_requests,
        pool_size=args.pool_size,
        iter_timeout=args.iter_timeout,
        time_budget=args.time_budget,
        cpu_affinity=args.cpu_affinity,
    )

    console = Console(stderr=args.json)
    env = system.collect_environment()
    cores = system.parse_cpu_spec(args.cpu_affinity) if args.cpu_affinity else None
    warnings = system.environment_warnings(cores)
    print_environment(console, env, config, warnings)

    if UNAVAILABLE:
        console.print(f"  [yellow]unavailable clients:[/yellow] {', '.join(sorted(UNAVAILABLE))}")

    plan = build_plan(args.categories, args.clients)
    if not plan:
        sys.exit("nothing to run: no clients match the given filters")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        results = execute(config, plan, args.rounds, args.shuffle, progress)

    json_report = to_json(results, env, config, warnings)
    if args.output:
        args.output.write_text(json_report)
        console.print(f"\nJSON report written to {args.output}")

    if args.json:
        print(json_report)
    else:
        print_all(console, results)


if __name__ == "__main__":
    main()
