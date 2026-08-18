# httpmark

Measures throughput, latency, CPU and memory of 16 Python HTTP clients — sync and
async, HTTP/1.1 and HTTP/2, over TLS. All clients hit the same local server (nginx
in front of go-httpbin), and each one runs in its own process on pinned CPU cores,
so nothing bleeds from one measurement into the next. Raw per-iteration data lands
in JSON.

## Quick start

```bash
echo "127.0.0.1   httpbin.local" | sudo tee -a /etc/hosts
bash certs/generate.sh
docker compose up -d
uv sync
uv run httpmark
```

Flags you'll actually use:

| Flag | Meaning |
|------|---------|
| `--clients rnet httpx ...` | run only these clients |
| `--categories async-http2` | run only these categories (`sync-http1`, `async-http1`, `async-http2`) |
| `-n 30` / `-r 10000` / `-c 100` | iterations, requests per iteration, concurrency |
| `--cpu-affinity 4-7` | pin benchmark workers to cores (Linux) |
| `--rounds 3 --shuffle` | split iterations into shuffled passes to spread thermal drift |
| `--time-budget 60` | cap wall-clock seconds per client per round; slow clients just report fewer iterations |
| `--json`, `--output results.json` | machine-readable output |

There is also `scripts/remote-bench.sh`: copy the repo to a fresh Linux box and run
it as root — it installs docker and uv, splits the cores between server and client,
and runs the whole thing.

## Results

Runs live under [results/](results/) — one folder per machine, library set and Python
version, each with raw per-iteration JSON and a generated report:

| Run | Machine | Python | Report |
|-----|---------|--------|--------|
| 2026-08-18 | Vultr CPU Optimized 8 vCPU (dedicated, EPYC-Milan) | 3.14.7 | [tables](results/2026-08-18-vultr-cpuopt8-py314/README.md) |
| 2026-08-18 | Vultr CPU Optimized 8 vCPU (dedicated, EPYC-Milan) | 3.13.5 | [tables](results/2026-08-18-vultr-cpuopt8-py313/README.md) |
| 2026-08-18 | Vultr CPU Optimized 8 vCPU (dedicated, EPYC-Milan) | 3.14.7t free-threaded | [tables](results/2026-08-18-vultr-cpuopt8-py314t/README.md) |

To add a run from your own machine, benchmark with `--output results.json`, drop the
file into `results/<date>-<machine>/` and run
`python scripts/report.py results/<date>-<machine>/results.json`.

Reading the reports: RPS med is the median of per-iteration throughput. CV % says how
noisy the run was (under 5 is good), not how fast the client is. CPU µs/req is total
CPU time divided by successful requests — the number that transfers best between
machines.

The short version:

- pycurl is the fastest sync client; aiohttp and pyreqwest top async HTTP/1.1;
  primp tops HTTP/2.
- 3.13 vs 3.14 makes almost no difference — every client lands within ±10%.
- Free-threaded 3.14t is easy on pure-Python clients (aiohttp loses 7%) and brutal
  to the Rust-backed ones: impit -84%, primp -80%, wreq -69%, pyreqwest -56%.
  Crossing the Python/Rust boundary gets much more expensive without the GIL.
  rnet has no free-threaded wheel at all. One caveat: the ft run pulled newer
  impit/primp versions (see the run report), so lean on wreq and pyreqwest for
  the clean apples-to-apples numbers.
- `TOKIO_WORKER_THREADS=1` speeds rnet and wreq up by ~55% on machines with few
  cores — their default multi-threaded tokio runtime just fights itself there.
  Each run report has the comparison.
- httpx and httpcore are slow on HTTP/1.1 and drop requests under HTTP/2 load.

## How it measures

- One subprocess per (client, category). RSS, CPU time and GC state can't leak from
  one client into the next, and Rust runtimes that never shut down can't haunt later runs.
- Async iterations use a fixed pool of workers pulling from a shared counter (like wrk),
  not one task per request.
- Latency is `perf_counter_ns` around each request, aggregated into a 1 µs histogram —
  percentiles stay exact no matter how many rounds you merge.
- Every adapter downloads the full response body; failed requests and status >= 400
  count as errors, never as latency samples.
- impit is the one exception on TLS: it can't load a custom CA, so it runs with
  verification off and slightly cheaper handshakes.
- After warmup: `gc.collect()` + `gc.freeze()`; GC stays on during measurement.
- RSS via `/proc` on Linux, `libproc` on macOS; peak from `ru_maxrss`.

## Pinning cores

The point is to keep the server and the client from fighting over the same cores —
otherwise the fastest clients get punished the most.

```bash
SERVER_CPUSET=0-3 docker compose -f docker-compose.yml -f docker-compose.pinning.yml up -d
uv run httpmark --cpu-affinity 4-7 --rounds 3 --shuffle
```

On SMT machines prefer one thread per physical core for the client side
(`scripts/remote-bench.sh` figures this out from `lscpu` automatically). The harness
warns when the governor isn't `performance`, when turbo is on, and when SMT might
map your pinned cores onto shared silicon.

## Clients

| Library | Type | HTTP/2 | Backend |
|---------|------|--------|---------|
| [aiohttp](https://pypi.org/project/aiohttp/) | async | no | Python + C (llhttp) |
| [aiosonic](https://pypi.org/project/aiosonic/) | async | experimental | Python |
| [curl_cffi](https://pypi.org/project/curl-cffi/) | both | yes | C (libcurl) |
| [httpcore](https://pypi.org/project/httpcore/) | async | yes | Python |
| [httpx](https://pypi.org/project/httpx/) | both | yes | Python |
| [httpx-aiohttp](https://pypi.org/project/httpx-aiohttp/) | async | no | httpx API over aiohttp transport |
| [impit](https://pypi.org/project/impit/) | async | no | Rust (reqwest) |
| [niquests](https://pypi.org/project/niquests/) | async | yes | Python |
| [primp](https://pypi.org/project/primp/) | both | yes | Rust |
| [pycurl](https://pypi.org/project/pycurl/) | sync | — | C (libcurl) |
| [pyreqwest](https://pypi.org/project/pyreqwest/) | both | yes | Rust (reqwest) |
| [requests](https://pypi.org/project/requests/) | sync | no | Python |
| [rnet](https://pypi.org/project/rnet/) | both | yes | Rust (wreq) |
| [urllib3-future](https://pypi.org/project/urllib3-future/) | async | yes | Python |
| [wreq](https://pypi.org/project/wreq/) | both | yes | Rust, successor of rnet |
| [zapros](https://pypi.org/project/zapros/) | both | via handler | Python sans-IO; also benchmarked as `zapros-rq` on its pyreqwest (Rust) handler |
