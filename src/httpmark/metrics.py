import math
import statistics

from collections import Counter
from dataclasses import dataclass, field


@dataclass(slots=True)
class IterationStats:
    ok: int
    errors: int
    duration_ns: int
    lat_sum_ns: int
    cpu_user: float
    cpu_system: float
    rss_bytes: int

    @property
    def rps(self) -> float:
        return self.ok / (self.duration_ns / 1e9) if self.duration_ns > 0 else 0.0

    @property
    def cpu_total(self) -> float:
        return self.cpu_user + self.cpu_system


@dataclass
class ClientResult:
    name: str
    category: str
    iterations: list[IterationStats] = field(default_factory=list)
    hist_us: Counter = field(default_factory=Counter)
    timeouts: int = 0
    peak_rss: int = 0
    rss_baseline: int = 0
    affinity: list[int] | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_worker(cls, name: str, category: str, payload: dict) -> "ClientResult":
        return cls(
            name=name,
            category=category,
            iterations=[IterationStats(**it) for it in payload["iterations"]],
            hist_us=Counter({int(k): v for k, v in payload["hist_us"].items()}),
            timeouts=payload["timeouts"],
            peak_rss=payload["peak_rss"],
            rss_baseline=payload["rss_baseline"],
            affinity=payload.get("affinity"),
        )

    def merge(self, other: "ClientResult") -> None:
        self.iterations.extend(other.iterations)
        self.hist_us.update(other.hist_us)
        self.timeouts += other.timeouts
        self.peak_rss = max(self.peak_rss, other.peak_rss)
        self.rss_baseline = max(self.rss_baseline, other.rss_baseline)
        if self.error is None:
            self.error = other.error

    @property
    def ok_total(self) -> int:
        return sum(it.ok for it in self.iterations)

    @property
    def error_total(self) -> int:
        return sum(it.errors for it in self.iterations)

    @property
    def error_rate(self) -> float:
        attempted = self.ok_total + self.error_total
        return self.error_total / attempted if attempted else 0.0

    @property
    def rps_median(self) -> float:
        rates = [it.rps for it in self.iterations]
        return statistics.median(rates) if rates else 0.0

    @property
    def rps_mean(self) -> float:
        rates = [it.rps for it in self.iterations]
        return statistics.fmean(rates) if rates else 0.0

    @property
    def rps_cv_pct(self) -> float:
        rates = [it.rps for it in self.iterations]
        if len(rates) < 2:
            return 0.0
        mean = statistics.fmean(rates)
        return statistics.stdev(rates) / mean * 100 if mean > 0 else 0.0

    def latency_percentile_ms(self, pct: float) -> float:
        total = sum(self.hist_us.values())
        if total == 0:
            return 0.0
        target = max(1, math.ceil(pct / 100 * total))
        cumulative = 0
        for bucket in sorted(self.hist_us):
            cumulative += self.hist_us[bucket]
            if cumulative >= target:
                return bucket / 1000
        return max(self.hist_us) / 1000

    @property
    def latency_mean_ms(self) -> float:
        ok = self.ok_total
        return sum(it.lat_sum_ns for it in self.iterations) / ok / 1e6 if ok else 0.0

    @property
    def cpu_us_per_request(self) -> float:
        ok = self.ok_total
        if not ok:
            return 0.0
        return sum(it.cpu_total for it in self.iterations) / ok * 1e6

    @property
    def rss_avg_mb(self) -> float:
        if not self.iterations:
            return 0.0
        return statistics.fmean(it.rss_bytes for it in self.iterations) / (1024 * 1024)

    @property
    def rss_peak_mb(self) -> float:
        return self.peak_rss / (1024 * 1024)
