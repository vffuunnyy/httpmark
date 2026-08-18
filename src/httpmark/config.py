from dataclasses import dataclass


@dataclass
class BenchmarkConfig:
    url: str = "https://httpbin.local:4443/get"
    ca_cert: str = "./certs/ca.crt"

    iterations: int = 30
    warmup: int = 3

    total_requests: int = 10000
    concurrency: int = 100
    pool_size: int = 100

    sync_requests: int = 200

    iter_timeout: float = 120.0
    time_budget: float = 0.0

    cpu_affinity: str | None = None
