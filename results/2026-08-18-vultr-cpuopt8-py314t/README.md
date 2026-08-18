# 2026-08-18 — Vultr CPU Optimized 8 vCPU, Python 3.14t free-threaded

- **Machine**: AMD EPYC-Milan Processor, 8 logical CPUs, Linux 6.12.101+deb13-amd64 x86_64
- **Python**: CPython 3.14.7 (free-threaded)
- **Load**: 30 iterations, async 10,000 req/iter @ concurrency 100, sync 200 req/iter
- **Pinning**: client CPUs `4,6`
- **Time budget**: 60s per client per round
- **Versions**: aiohttp 3.14.3 · aiosonic 1.0.5 · curl-cffi 0.16.0 · httpx 0.28.1 · httpcore 1.0.9 · niquests 3.21.0 · urllib3-future 2.24.901 · impit 0.13.2 · primp 1.3.1 · pycurl 7.47.0 · pyreqwest 0.12.4 · wreq 0.12.1 · requests 2.34.2 · zapros 0.16.0 · httpx-aiohttp 0.2.0
- **Warning**: SMT is enabled; pinned cores may share physical cores with sibling threads (check /sys/devices/system/cpu/cpuN/topology/thread_siblings_list)
- **Note**: This env resolved newer versions of some libraries than the 3.13/3.14 runs (aiohttp 3.14.3, impit 0.13.2, primp 1.3.1) because free-threaded wheels forced a fresh resolve outside the lockfile. wreq and pyreqwest versions match the other runs, so the Rust-bridge slowdown conclusion rests on them.

## Sync HTTP/1.1

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) | Iters | Errors |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|------:|-------:|
| pycurl | 3,571 | 6.4 | 0.27 | 0.34 | 0.40 | 64 | 114 | 30 | 0 |
| wreq | 3,328 | 6.4 | 0.29 | 0.37 | 0.43 | 100 | 121 | 30 | 0 |
| primp | 3,282 | 7.7 | 0.30 | 0.38 | 0.43 | 79 | 115 | 30 | 0 |
| pyreqwest | 3,233 | 5.5 | 0.30 | 0.38 | 0.43 | 83 | 113 | 30 | 0 |
| curl_cffi | 2,175 | 5.5 | 0.46 | 0.56 | 0.62 | 221 | 111 | 30 | 0 |
| zapros | 1,878 | 3.5 | 0.52 | 0.64 | 0.71 | 290 | 110 | 30 | 0 |
| httpx | 1,536 | 8.9 | 0.65 | 0.89 | 1.02 | 416 | 110 | 30 | 0 |
| requests | 1,101 | 3.0 | 0.89 | 1.06 | 1.17 | 650 | 115 | 30 | 0 |

## Async HTTP/1.1

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) | Iters | Errors |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|------:|-------:|
| aiohttp | 13,411 | 4.3 | 7.29 | 10.55 | 13.56 | 73 | 152 | 30 | 0 |
| aiosonic | 7,791 | 4.7 | 12.53 | 15.14 | 17.86 | 125 | 157 | 30 | 0 |
| pyreqwest | 6,625 | 1.8 | 15.18 | 19.51 | 21.82 | 173 | 122 | 30 | 0 |
| curl_cffi | 6,468 | 6.8 | 15.29 | 19.90 | 22.99 | 156 | 123 | 30 | 0 |
| zapros-rq | 5,924 | 3.5 | 16.69 | 22.94 | 26.41 | 274 | 124 | 30 | 0 |
| zapros | 4,153 | 2.4 | 22.90 | 26.16 | 37.00 | 242 | 159 | 30 | 0 |
| httpx-aiohttp | 3,435 | 3.0 | 27.34 | 32.45 | 82.50 | 292 | 181 | 30 | 0 |
| urllib3-future | 3,126 | 2.1 | 31.26 | 34.35 | 72.63 | 321 | 197 | 30 | 0 |
| wreq | 2,393 | 8.9 | 41.06 | 61.22 | 71.93 | 816 | 142 | 30 | 0 |
| impit | 1,886 | 14.3 | 53.98 | 96.29 | 124.03 | 1042 | 240 | 30 | 0 |
| niquests | 1,860 | 26.8 | 51.45 | 62.32 | 126.44 | 540 | 188 | 23 | 198 |
| primp | 1,704 | 23.6 | 55.45 | 114.45 | 151.87 | 1069 | 256 | 30 | 0 |
| httpcore | 617 | 7.6 | 116.02 | 463.68 | 714.78 | 1631 | 142 | 12 | 0 |
| httpx | 508 | 8.6 | 138.87 | 550.03 | 843.78 | 1941 | 168 | 10 | 0 |

## Async HTTP/2

| Client | RPS med | CV % | p50 (ms) | p95 (ms) | p99 (ms) | CPU µs/req | RSS avg (MB) | Iters | Errors |
|--------|--------:|-----:|---------:|---------:|---------:|-----------:|-------------:|------:|-------:|
| curl_cffi | 7,763 | 2.9 | 12.65 | 15.20 | 18.20 | 128 | 123 | 30 | 0 |
| pyreqwest | 5,322 | 2.2 | 15.85 | 42.63 | 58.27 | 207 | 120 | 30 | 0 |
| zapros-rq | 5,243 | 1.8 | 15.29 | 42.05 | 54.23 | 318 | 122 | 30 | 0 |
| urllib3-future | 2,949 | 2.2 | 33.00 | 37.33 | 69.06 | 340 | 197 | 30 | 2 |
| wreq | 2,537 | 4.8 | 39.00 | 58.59 | 71.95 | 775 | 137 | 30 | 0 |
| primp | 2,048 | 18.7 | 42.46 | 100.82 | 137.63 | 906 | 221 | 30 | 0 |
| httpcore | 1,873 | 2.1 | 52.57 | 62.03 | 68.46 | 535 | 117 | 30 | 638 |
| niquests | 1,646 | 3.2 | 57.81 | 69.34 | 119.16 | 608 | 205 | 30 | 2 |
| httpx | 1,316 | 2.4 | 74.44 | 88.12 | 114.03 | 766 | 133 | 24 | 543 |

