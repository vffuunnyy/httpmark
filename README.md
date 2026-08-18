# httpmark

Benchmarks 14 Python HTTP clients against a local nginx + go-httpbin stand.
Sync and async, HTTP/1.1 and HTTP/2, over TLS. Each client runs in its own
process on pinned CPU cores, so memory and CPU numbers don't bleed between
clients. Raw per-iteration data lands in JSON.

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

To benchmark a fresh Linux box end to end (installs docker and uv, splits cores,
runs everything): copy the repo over and run `scripts/remote-bench.sh` as root.

## Results

Vultr VPS, 8 vCPU (AMD EPYC-Milan, 4 physical cores with SMT), Debian 13, Python 3.14.7.
Server pinned to both threads of two physical cores; benchmark workers pinned to one
thread of each remaining core, siblings left idle. 30 iterations in 3 shuffled rounds,
async: 10,000 requests per iteration at concurrency 100, sync: 200 sequential requests.

How to read the tables: RPS med is the median of per-iteration throughput. CV % says how
noisy the run was (under 5 is good), not how fast the client is. CPU µs/req is total CPU
time divided by successful requests — the efficiency number that survives hardware changes.

### Sync HTTP/1.1

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|
| pycurl | 3,317 | 4.9 | 0.29 | 0.38 | 0.44 | 70 | 98 |
| rnet | 3,077 | 5.8 | 0.32 | 0.41 | 0.47 | 109 | 110 |
| pyreqwest | 3,040 | 4.6 | 0.33 | 0.42 | 0.47 | 92 | 100 |
| primp | 3,034 | 3.6 | 0.32 | 0.42 | 0.48 | 85 | 97 |
| wreq | 2,972 | 5.8 | 0.33 | 0.42 | 0.48 | 104 | 112 |
| curl_cffi | 2,042 | 2.2 | 0.48 | 0.59 | 0.67 | 218 | 95 |
| requests | 1,200 | 4.0 | 0.81 | 1.03 | 1.19 | 542 | 98 |

### Async HTTP/1.1

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|
| aiohttp | 16,636 | 7.1 | 5.95 | 10.34 | 12.88 | 58 | 128 |
| pyreqwest | 15,465 | 4.4 | 6.14 | 10.42 | 13.06 | 75 | 113 |
| impit | 11,310 | 5.0 | 8.48 | 13.41 | 16.38 | 156 | 111 |
| aiosonic | 8,995 | 3.2 | 11.04 | 14.85 | 17.85 | 108 | 130 |
| primp | 8,369 | 4.3 | 9.48 | 32.87 | 55.71 | 171 | 108 |
| wreq | 7,508 | 1.4 | 13.31 | 17.11 | 20.09 | 209 | 111 |
| rnet | 7,436 | 12.8 | 12.93 | 17.83 | 21.42 | 202 | 110 |
| curl_cffi | 7,152 | 2.6 | 13.56 | 17.96 | 21.06 | 139 | 118 |
| urllib3-future | 3,762 | 2.2 | 25.63 | 31.99 | 35.95 | 266 | 152 |
| niquests | 2,173 | 2.3 | 44.38 | 52.51 | 72.71 | 463 | 160 |
| httpcore | 1,080 | 16.6 | 65.38 | 341.24 | 640.14 | 945 | 104 |
| httpx | 811 | 23.5 | 87.47 | 320.85 | 493.71 | 1286 | 105 |

### Async HTTP/2

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) | Errors |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|-------:|
| primp | 10,744 | 3.7 | 9.00 | 15.44 | 18.85 | 135 | 103 | 0 |
| pyreqwest | 9,237 | 3.4 | 8.61 | 29.25 | 46.83 | 103 | 111 | 0 |
| curl_cffi | 8,504 | 4.9 | 11.70 | 14.51 | 16.87 | 120 | 117 | 0 |
| rnet | 7,596 | 18.9 | 11.94 | 19.11 | 23.43 | 171 | 104 | 0 |
| wreq | 7,580 | 3.4 | 12.99 | 19.63 | 23.87 | 190 | 103 | 0 |
| urllib3-future | 3,642 | 2.1 | 26.35 | 32.53 | 36.24 | 272 | 153 | 0 |
| httpcore | 3,371 | 1.5 | 29.27 | 38.44 | 44.53 | 297 | 98 | 705 |
| httpx | 2,095 | 1.9 | 47.21 | 58.33 | 65.87 | 479 | 106 | 637 |
| niquests | 1,966 | 2.6 | 48.31 | 56.99 | 104.03 | 510 | 168 | 0 |

Worth knowing before quoting these numbers:

- httpx and httpcore drop hundreds of requests under HTTP/2 load (stream-level errors);
  their rows count successful requests only.
- Their HTTP/1.1 slowness is a known httpcore issue — the anyio removal
  (httpcore PRs #922, #930) has not shipped as of httpcore 1.0.9.
- impit runs with TLS verification off: it can't load a custom CA, so its handshakes
  are slightly cheaper than everyone else's.
- pycurl supports HTTP/2 but is kept as the classic sync HTTP/1.1 baseline.
  aiosonic's HTTP/2 is experimental and skipped.
- Every adapter downloads the full response body; a request only counts when its
  status is < 400.

### One env var doubles rnet and wreq

rnet, wreq and primp put every request through a multi-threaded tokio runtime — one
worker thread per visible core, only tunable through an env var. On a machine with few
cores those extra threads mostly fight each other. With `TOKIO_WORKER_THREADS=1`:

| Client | Category | RPS med | vs default | p99 (ms) | CPU µs/req |
|--------|----------|--------:|-----------:|---------:|-----------:|
| rnet | Async HTTP/1.1 | 11,661 | +57% | 14.79 | 95 |
| wreq | Async HTTP/1.1 | 11,480 | +53% | 14.89 | 96 |
| impit | Async HTTP/1.1 | 10,834 | -4% | 16.86 | 146 |
| primp | Async HTTP/1.1 | 8,410 | +0% | 57.09 | 157 |
| primp | Async HTTP/2 | 10,952 | +2% | 18.03 | 126 |
| rnet | Async HTTP/2 | 9,868 | +30% | 17.53 | 101 |
| wreq | Async HTTP/2 | 9,740 | +28% | 18.05 | 103 |

Latency tails shrink too (rnet p99: 21 ms → 15 ms). pyreqwest ships a single-threaded
runtime by default, which is a big part of why it needs no tuning to place well.

Raw per-iteration data for both passes lives in [results/](results/).

## How it measures

- One subprocess per (client, category). RSS, CPU time and GC state can't leak from
  one client into the next, and Rust runtimes that never shut down can't haunt later runs.
- Async iterations use a fixed pool of workers pulling from a shared counter (like wrk),
  not one task per request.
- Latency is `perf_counter_ns` around each request, aggregated into a 1 µs histogram —
  percentiles stay exact no matter how many rounds you merge.
- Failed requests and status >= 400 count as errors, never as latency samples.
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
| [httpx](https://pypi.org/project/httpx/) | async | yes | Python |
| [impit](https://pypi.org/project/impit/) | async | no | Rust (reqwest) |
| [niquests](https://pypi.org/project/niquests/) | async | yes | Python |
| [primp](https://pypi.org/project/primp/) | both | yes | Rust |
| [pycurl](https://pypi.org/project/pycurl/) | sync | — | C (libcurl) |
| [pyreqwest](https://pypi.org/project/pyreqwest/) | both | yes | Rust (reqwest) |
| [requests](https://pypi.org/project/requests/) | sync | no | Python |
| [rnet](https://pypi.org/project/rnet/) | both | yes | Rust (wreq) |
| [urllib3-future](https://pypi.org/project/urllib3-future/) | async | yes | Python |
| [wreq](https://pypi.org/project/wreq/) | both | yes | Rust, successor of rnet |
