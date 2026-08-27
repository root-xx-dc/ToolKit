"""
rootx.benchmark
===============
System benchmark tool. Pure stdlib.
Tests: CPU single-core, CPU multi-core, RAM speed, Disk write, Disk read.
Results saved as rootx-benchmark-YYYY-MM-DD.txt in current directory.
"""

from __future__ import annotations

import os
import platform
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Optional

from . import utils

@dataclass
class BenchmarkResult:
    name: str
    score: float
    unit: str
    duration_sec: float
    details: str = ""

_CPU_ITERATIONS = 5_000_000
_RAM_SIZE_MB = 256
_DISK_SIZE_MB = 256


def _cpu_worker(_) -> int:
    """Single-core CPU benchmark worker (integer loop)."""
    total = 0
    for i in range(_CPU_ITERATIONS):
        total += i * i
    return total


def bench_cpu_single() -> BenchmarkResult:
    """Benchmark CPU single-core performance."""
    start = time.perf_counter()
    _cpu_worker(None)
    elapsed = time.perf_counter() - start
    ops_per_sec = _CPU_ITERATIONS / elapsed if elapsed > 0 else 0
    return BenchmarkResult(
        name="CPU Single-core",
        score=round(ops_per_sec / 1_000_000, 2),
        unit="M ops/sec",
        duration_sec=round(elapsed, 2),
        details=f"{_CPU_ITERATIONS:,} integer operations",
    )


def bench_cpu_multi() -> BenchmarkResult:
    """Benchmark CPU multi-core performance using ProcessPoolExecutor."""
    workers = os.cpu_count() or 1
    start = time.perf_counter()
    try:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_cpu_worker, i) for i in range(workers)]
            for f in as_completed(futures):
                f.result()
    except Exception as e:
        return BenchmarkResult(
            name="CPU Multi-core",
            score=0.0,
            unit="M ops/sec",
            duration_sec=0.0,
            details=f"Error: {e}",
        )
    elapsed = time.perf_counter() - start
    total_ops = _CPU_ITERATIONS * workers
    ops_per_sec = total_ops / elapsed if elapsed > 0 else 0
    return BenchmarkResult(
        name="CPU Multi-core",
        score=round(ops_per_sec / 1_000_000, 2),
        unit="M ops/sec",
        duration_sec=round(elapsed, 2),
        details=f"{workers} cores × {_CPU_ITERATIONS:,} ops",
    )


def bench_ram() -> BenchmarkResult:
    """Benchmark RAM fill + read speed."""
    size = _RAM_SIZE_MB * 1024 * 1024
    data = bytes(range(256)) * (size // 256)
    start = time.perf_counter()
    arr = bytearray(data)
    write_time = time.perf_counter() - start
    start = time.perf_counter()
    checksum = sum(arr[::1024])
    read_time = time.perf_counter() - start
    total = write_time + read_time
    mb_per_sec = (_RAM_SIZE_MB * 2) / total if total > 0 else 0
    return BenchmarkResult(
        name="RAM Speed",
        score=round(mb_per_sec, 1),
        unit="MB/s",
        duration_sec=round(total, 2),
        details=f"{_RAM_SIZE_MB} MB fill+read (checksum={checksum})",
    )


def bench_disk() -> BenchmarkResult:
    """Benchmark disk write + read with temp file and fsync."""
    size = _DISK_SIZE_MB * 1024 * 1024
    chunk = b"X" * 65536
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".rootx_bench") as tmp:
            tmp_path = tmp.name
        start = time.perf_counter()
        with open(tmp_path, "wb") as f:
            written = 0
            while written < size:
                f.write(chunk)
                written += len(chunk)
            f.flush()
            os.fsync(f.fileno())
        write_time = time.perf_counter() - start
        start = time.perf_counter()
        with open(tmp_path, "rb") as f:
            while f.read(65536):
                pass
        read_time = time.perf_counter() - start
        write_mb = _DISK_SIZE_MB / write_time if write_time > 0 else 0
        read_mb = _DISK_SIZE_MB / read_time if read_time > 0 else 0
        return BenchmarkResult(
            name="Disk Write/Read",
            score=round(write_mb, 1),
            unit="MB/s write",
            duration_sec=round(write_time + read_time, 2),
            details=f"Write: {write_mb:.1f} MB/s | Read: {read_mb:.1f} MB/s | {_DISK_SIZE_MB} MB",
        )
    except Exception as e:
        return BenchmarkResult(
            name="Disk Write/Read",
            score=0.0,
            unit="MB/s",
            duration_sec=0.0,
            details=f"Error: {e}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def run_all_benchmarks() -> List[BenchmarkResult]:
    """Run all benchmarks in sequence."""
    return [
        bench_cpu_single(),
        bench_cpu_multi(),
        bench_ram(),
        bench_disk(),
    ]


def save_results(results: List[BenchmarkResult], path: Optional[str] = None) -> str:
    """Save benchmark results to a text file. Returns file path."""
    if path is None:
        date = time.strftime("%Y-%m-%d")
        path = f"rootx-benchmark-{date}.txt"
    lines = [
        "ROOT//X TOOLKIT — BENCHMARK RESULTS",
        f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"OS: {platform.system()} {platform.release()}",
        f"CPU: {platform.processor()}",
        f"Cores: {os.cpu_count()}",
        "-" * 60,
    ]
    for r in results:
        lines.append(f"  {r.name}: {r.score} {r.unit}  ({r.duration_sec}s)")
        if r.details:
            lines.append(f"    {r.details}")
    lines.append("-" * 60)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        return f"Could not save: {e}"
    return path


def list_previous_results(directory: str = ".") -> List[str]:
    """List previous benchmark result files."""
    try:
        return sorted(
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.startswith("rootx-benchmark-") and f.endswith(".txt")
        )
    except Exception:
        return []
