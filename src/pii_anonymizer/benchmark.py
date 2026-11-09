"""Size on disk and latency, following docs/benchmark-protocol.md."""

import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

WARMUP_CALLS = 5
RUNS_PER_INPUT = 10
THREADS = 4

# Environment variables read by the usual numeric libraries when they start.
THREAD_VARIABLES = ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")


def set_thread_variables(threads: int = THREADS) -> None:
    """Fix the thread count before a detector loads its runtime."""
    for name in THREAD_VARIABLES:
        os.environ[name] = str(threads)


def _read_cpu_name() -> str:
    """The CPU model name from the operating system, or an empty string."""
    if sys.platform.startswith("linux"):
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    elif sys.platform == "darwin":
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip()
    elif sys.platform == "win32":
        import winreg

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
    return ""


def cpu_name() -> str:
    """The CPU model name, for example "11th Gen Intel(R) Core(TM) i5-1130G7 @ 1.10GHz".

    Falls back to platform.processor(), then to "unknown". Never raises.
    """
    try:
        name = _read_cpu_name()
    except Exception:
        # Any failure of the OS query only means we use the fallback.
        name = ""
    return name or platform.processor().strip() or "unknown"


def size_on_disk(paths: Iterable[Path]) -> int:
    """Total size in bytes of the given files, folders walked recursively.

    A file reached twice (listed twice, or inside a listed folder) is counted once.
    """
    files = set()
    for path in paths:
        path = Path(path)
        if path.is_dir():
            files.update(p.resolve() for p in path.rglob("*") if p.is_file())
        elif path.is_file():
            files.add(path.resolve())
        else:
            raise FileNotFoundError(path)
    return sum(f.stat().st_size for f in files)


def count_words(text: str) -> int:
    """Number of words, split on whitespace."""
    return len(text.split())


def percentile(values: Sequence[float], q: int) -> float:
    """The q-th percentile, with linear interpolation between the closest values."""
    if not values:
        raise ValueError("no values")
    return statistics.quantiles(values, n=100, method="inclusive")[q - 1]


@dataclass(frozen=True)
class Latency:
    """Latency statistics over all recorded calls, in milliseconds."""

    calls: int
    p50_ms: float
    p95_ms: float
    # None when no input has a word (cannot happen with real snippets)
    p50_ms_per_100_words: float | None
    p95_ms_per_100_words: float | None


def measure_latency(
    detect: Callable[[str], object],
    texts: Sequence[str],
    warmup: int = WARMUP_CALLS,
    runs: int = RUNS_PER_INPUT,
    clock: Callable[[], float] = time.perf_counter,
) -> Latency:
    """Time `detect` on each text, one text per call (batch size 1).

    The detector must already be loaded. The first `warmup` calls go through the texts in
    order and are not recorded. Then each text runs `runs` times. `clock` returns seconds.
    """
    if not texts:
        raise ValueError("no texts to time")
    for i in range(warmup):
        detect(texts[i % len(texts)])

    times_ms = []
    times_per_100_words = []
    for text in texts:
        words = count_words(text)
        for _ in range(runs):
            start = clock()
            detect(text)
            elapsed_ms = (clock() - start) * 1000
            times_ms.append(elapsed_ms)
            if words:
                times_per_100_words.append(elapsed_ms * 100 / words)

    return Latency(
        calls=len(times_ms),
        p50_ms=percentile(times_ms, 50),
        p95_ms=percentile(times_ms, 95),
        p50_ms_per_100_words=percentile(times_per_100_words, 50) if times_per_100_words else None,
        p95_ms_per_100_words=percentile(times_per_100_words, 95) if times_per_100_words else None,
    )
