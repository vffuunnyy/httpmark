import ctypes
import os
import platform
import resource
import subprocess
import sys
from importlib import metadata

CLIENT_PACKAGES = [
    "aiohttp",
    "aiosonic",
    "curl-cffi",
    "httpx",
    "httpcore",
    "niquests",
    "urllib3-future",
    "impit",
    "primp",
    "pycurl",
    "pyreqwest",
    "rnet",
    "wreq",
    "requests",
]


def parse_cpu_spec(spec: str) -> list[int]:
    cores: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo, hi = part.split("-", 1)
            cores.update(range(int(lo), int(hi) + 1))
        else:
            cores.add(int(part))
    if not cores:
        raise ValueError(f"empty CPU spec: {spec!r}")
    return sorted(cores)


def apply_cpu_affinity(spec: str) -> tuple[list[int] | None, str | None]:
    cores = parse_cpu_spec(spec)
    if not hasattr(os, "sched_setaffinity"):
        return None, f"CPU affinity is not supported on {platform.system()}; running unpinned"
    try:
        os.sched_setaffinity(0, cores)
    except OSError as e:
        return None, f"failed to pin to CPUs {spec}: {e}"
    return cores, None


def raise_priority(delta: int = -5) -> int | None:
    try:
        return os.nice(delta)
    except OSError:
        return None


def _read_sys(path: str) -> str | None:
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None


def environment_warnings(cores: list[int] | None) -> list[str]:
    warnings: list[str] = []
    if sys.platform != "linux":
        warnings.append(
            f"{platform.system()} does not support CPU pinning or frequency control; "
            "results are more susceptible to scheduler and thermal noise"
        )
        return warnings

    cpus = cores if cores else list(range(os.cpu_count() or 1))
    non_performance: dict[str, list[int]] = {}
    for cpu in cpus:
        governor = _read_sys(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_governor")
        if governor and governor != "performance":
            non_performance.setdefault(governor, []).append(cpu)
    for governor, affected in non_performance.items():
        warnings.append(
            f"CPU governor is '{governor}' on cpus {affected}; "
            "set 'performance' (cpupower frequency-set -g performance) for stable clocks"
        )

    if _read_sys("/sys/devices/system/cpu/intel_pstate/no_turbo") == "0":
        warnings.append(
            "turbo boost is enabled (intel_pstate/no_turbo=0); "
            "disable it for run-to-run stability"
        )
    if _read_sys("/sys/devices/system/cpu/cpufreq/boost") == "1":
        warnings.append("boost is enabled (cpufreq/boost=1); disable it for run-to-run stability")

    if cores and _read_sys("/sys/devices/system/cpu/smt/control") == "on":
        warnings.append(
            "SMT is enabled; pinned cores may share physical cores with sibling threads "
            "(check /sys/devices/system/cpu/cpuN/topology/thread_siblings_list)"
        )
    return warnings


if sys.platform == "darwin":
    _PROC_PIDTASKINFO = 4

    class _ProcTaskInfo(ctypes.Structure):
        # struct proc_taskinfo from <libproc.h>
        _fields_ = [
            ("pti_virtual_size", ctypes.c_uint64),
            ("pti_resident_size", ctypes.c_uint64),
            ("pti_total_user", ctypes.c_uint64),
            ("pti_total_system", ctypes.c_uint64),
            ("pti_threads_user", ctypes.c_uint64),
            ("pti_threads_system", ctypes.c_uint64),
            ("pti_policy", ctypes.c_int32),
            ("pti_faults", ctypes.c_int32),
            ("pti_pageins", ctypes.c_int32),
            ("pti_cow_faults", ctypes.c_int32),
            ("pti_messages_sent", ctypes.c_int32),
            ("pti_messages_received", ctypes.c_int32),
            ("pti_syscalls_mach", ctypes.c_int32),
            ("pti_syscalls_unix", ctypes.c_int32),
            ("pti_csw", ctypes.c_int32),
            ("pti_threadnum", ctypes.c_int32),
            ("pti_numrunning", ctypes.c_int32),
            ("pti_priority", ctypes.c_int32),
        ]

    _libproc = ctypes.CDLL("/usr/lib/libproc.dylib", use_errno=True)

    def current_rss_bytes() -> int:
        info = _ProcTaskInfo()
        written = _libproc.proc_pidinfo(
            os.getpid(), _PROC_PIDTASKINFO, 0, ctypes.byref(info), ctypes.sizeof(info)
        )
        if written == ctypes.sizeof(info):
            return int(info.pti_resident_size)
        return 0

else:

    def current_rss_bytes() -> int:
        try:
            with open("/proc/self/statm") as f:
                return int(f.read().split()[1]) * os.sysconf("SC_PAGESIZE")
        except (OSError, ValueError, IndexError):
            return 0


def peak_rss_bytes() -> int:
    # ru_maxrss is bytes on macOS, kilobytes on Linux
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def cpu_times() -> tuple[float, float]:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime, r.ru_stime


def _cpu_model() -> str:
    if sys.platform == "darwin":
        try:
            return subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return platform.machine()
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def package_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for pkg in CLIENT_PACKAGES:
        try:
            versions[pkg] = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            continue
    return versions


def collect_environment() -> dict:
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "python": f"{platform.python_implementation()} {platform.python_version()}",
        "packages": package_versions(),
    }
