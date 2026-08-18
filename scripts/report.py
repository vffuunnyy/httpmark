#!/usr/bin/env python3
"""Generate a markdown report from httpmark results JSON.

Usage:
    python scripts/report.py results/<run-dir>/results.json [--tuned results-tokio1.json]

Writes README.md next to the results file.
"""

import argparse
import json

from pathlib import Path


TABLE_HEADER = (
    "| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) "
    "| CPU µs/req | RSS avg (MB) | Iters | Errors |\n"
    "|--------|--------:|-----:|---------:|---------:|---------:"
    "|-----------:|-------------:|------:|-------:|"
)


def row(r: dict) -> str:
    errors = r["errors"] + r["timeouts"]
    return (
        f"| {r['client']} | {r['rps_median']:,.0f} | {r['rps_cv_pct']:.1f} | "
        f"{r['latency_p50_ms']:.2f} | {r['latency_p95_ms']:.2f} | {r['latency_p99_ms']:.2f} | "
        f"{r['cpu_us_per_request']:.0f} | {r['rss_avg_mb']:.0f} | {r['iterations']} | {errors:,} |"
    )


def header_lines(data: dict, title: str, notes: list[str]) -> list[str]:
    env = data["environment"]
    cfg = data["config"]
    python_line = env["python"]
    if not env.get("gil_enabled", True):
        python_line += " (free-threaded)"
    versions = " · ".join(f"{name} {ver}" for name, ver in env["packages"].items())

    lines = [
        f"# {title}",
        "",
        f"- **Machine**: {env['cpu']}, {env['cpu_count']} logical CPUs, {env['os']} {env['arch']}",
        f"- **Python**: {python_line}",
        (
            f"- **Load**: {cfg['iterations']} iterations, async {cfg['total_requests']:,} req/iter"
            f" @ concurrency {cfg['concurrency']}, sync {cfg['sync_requests']} req/iter"
        ),
        f"- **Pinning**: client CPUs `{cfg['cpu_affinity'] or 'not pinned'}`",
    ]
    if cfg.get("time_budget"):
        lines.append(f"- **Time budget**: {cfg['time_budget']:.0f}s per client per round")
    lines.append(f"- **Versions**: {versions}")
    lines.extend(f"- **Warning**: {w}" for w in data.get("warnings", []))
    lines.extend(f"- **Note**: {note}" for note in notes)
    lines.append("")
    return lines


def category_lines(results: dict) -> list[str]:
    lines: list[str] = []
    for cat, rs in results.items():
        ok = [r for r in rs if "rps_median" in r]
        failed = [r for r in rs if "rps_median" not in r]
        lines.extend([f"## {cat}", "", TABLE_HEADER])
        lines.extend(row(r) for r in ok)
        lines.append("")
        lines.extend(f"- `{r['client']}` failed: {r['error']}" for r in failed)
        if failed:
            lines.append("")
    return lines


def tuned_lines(data: dict, tuned: dict) -> list[str]:
    header = TABLE_HEADER.replace("| Client |", "| Client | Category |", 1).replace(
        "|--------|", "|--------|----------|", 1
    )
    lines = ["## Tuned: TOKIO_WORKER_THREADS=1", "", header]
    base = {
        (cat, r["client"]): r
        for cat, rs in data["results"].items()
        for r in rs
        if "rps_median" in r
    }
    for cat, rs in tuned["results"].items():
        for r in rs:
            if "rps_median" not in r:
                continue
            b = base.get((cat, r["client"]))
            delta = f" ({(r['rps_median'] / b['rps_median'] - 1) * 100:+.0f}%)" if b else ""
            line = row(r).replace(f"| {r['client']} |", f"| {r['client']} | {cat} |", 1)
            line = line.replace(f"{r['rps_median']:,.0f} |", f"{r['rps_median']:,.0f}{delta} |", 1)
            lines.append(line)
    lines.append("")
    return lines


def render(data: dict, tuned: dict | None, title: str, notes: list[str]) -> str:
    lines = header_lines(data, title, notes)
    lines.extend(category_lines(data["results"]))
    if tuned:
        lines.extend(tuned_lines(data, tuned))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", type=Path)
    ap.add_argument("--tuned", type=Path, default=None)
    ap.add_argument("--output", type=Path, default=None)
    ap.add_argument("--title", default=None)
    ap.add_argument("--note", action="append", default=[])
    args = ap.parse_args()

    data = json.loads(args.results.read_text())
    tuned = json.loads(args.tuned.read_text()) if args.tuned else None
    title = args.title or args.results.parent.name
    output = args.output or args.results.parent / "README.md"
    output.write_text(render(data, tuned, title, args.note))
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
