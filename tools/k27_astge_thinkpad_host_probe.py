#!/usr/bin/env python3
"""Non-promoting ThinkPad host qualification for Aura K27 ASTGE.

This probe measures one host. It does not authorize mmap, infer semantic K27
meaning, or prove production performance from CI/synthetic hardware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
import os
import platform
import random
import shutil
import statistics
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SCHEMA = "AURA_K27_ASTGE_THINKPAD_HOST_QUALIFICATION_V1"
BLOCK_SIZE = 4096


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_text(path: str) -> str:
    try:
        return Path(path).read_text(errors="replace")
    except OSError:
        return ""


def cpu_flags(cpuinfo: str | None = None) -> set[str]:
    text = cpuinfo if cpuinfo is not None else _read_text("/proc/cpuinfo")
    flags: set[str] = set()
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() in {"flags", "features"}:
            flags.update(value.strip().lower().split())
    return flags


def select_simd_path(flags: Iterable[str]) -> str:
    f = set(flags)
    if "avx512f" in f and ("avx512_vpopcntdq" in f or "avx512vpopcntdq" in f):
        return "AVX512_VPOPCNTDQ"
    if "avx2" in f and "popcnt" in f:
        return "AVX2_POPCNT64"
    if "popcnt" in f:
        return "SCALAR_POPCNT64"
    return "SCALAR_PORTABLE"


def detect_wsl(version_text: str | None = None) -> bool:
    text = version_text if version_text is not None else (_read_text("/proc/version") + " " + platform.release())
    low = text.lower()
    return "microsoft" in low or "wsl" in low


def memory_total_bytes(meminfo: str | None = None) -> int | None:
    text = meminfo if meminfo is not None else _read_text("/proc/meminfo")
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1]) * 1024
    return None


def nvidia_cuda_present() -> bool:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return False
    try:
        result = subprocess.run([exe, "-L"], capture_output=True, text=True, timeout=2, check=False)
        return result.returncode == 0 and bool(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def storage_summary(path: Path) -> dict[str, object]:
    out: dict[str, object] = {"path": str(path.resolve())}
    try:
        stat = os.statvfs(path)
        out["filesystem_block_size"] = int(stat.f_frsize or stat.f_bsize)
    except OSError:
        out["filesystem_block_size"] = None
    lsblk = shutil.which("lsblk")
    if lsblk:
        try:
            p = subprocess.run(
                [lsblk, "-J", "-o", "NAME,TYPE,SIZE,ROTA,TRAN,MOUNTPOINTS,MODEL"],
                capture_output=True, text=True, timeout=3, check=False,
            )
            if p.returncode == 0:
                out["lsblk"] = json.loads(p.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            out["lsblk"] = None
    return out


def deterministic_file(path: Path, size_bytes: int) -> str:
    """Create deterministic, non-sparse blocks and return SHA-256."""
    seed = bytes(range(256)) * 16
    h = hashlib.sha256()
    remaining = size_bytes
    with path.open("wb", buffering=0) as f:
        block_index = 0
        while remaining:
            take = min(BLOCK_SIZE, remaining)
            block = bytearray(seed[:take])
            if take >= 8:
                block[:8] = block_index.to_bytes(8, "little")
            raw = bytes(block)
            f.write(raw)
            h.update(raw)
            remaining -= take
            block_index += 1
        f.flush()
        os.fsync(f.fileno())
    return h.hexdigest()


def _offsets(file_size: int, samples: int, seed: int) -> list[int]:
    pages = file_size // BLOCK_SIZE
    if pages <= 0:
        raise ValueError("benchmark file must contain at least one 4KiB page")
    rng = random.Random(seed)
    return [rng.randrange(pages) * BLOCK_SIZE for _ in range(samples)]


def benchmark_same_pages(path: Path, samples: int = 2048, seed: int = 27) -> dict[str, object]:
    """Compare warm-cache pread and mmap over identical deterministic page offsets.

    This is deliberately a same-byte microbenchmark. It does not claim cold-NVMe
    superiority or production ASTGE throughput.
    """
    size = path.stat().st_size
    offsets = _offsets(size, samples, seed)

    def run_pread(fd: int) -> tuple[list[int], int]:
        times: list[int] = []
        checksum = 0
        for off in offsets:
            t0 = time.perf_counter_ns()
            raw = os.pread(fd, BLOCK_SIZE, off)
            times.append(time.perf_counter_ns() - t0)
            if len(raw) != BLOCK_SIZE:
                raise RuntimeError("short pread")
            checksum ^= int.from_bytes(hashlib.blake2s(raw, digest_size=8).digest(), "little")
        return times, checksum

    def run_mmap(fd: int) -> tuple[list[int], int]:
        times: list[int] = []
        checksum = 0
        with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as mm:
            for off in offsets:
                t0 = time.perf_counter_ns()
                raw = mm[off:off + BLOCK_SIZE]
                times.append(time.perf_counter_ns() - t0)
                if len(raw) != BLOCK_SIZE:
                    raise RuntimeError("short mmap slice")
                checksum ^= int.from_bytes(hashlib.blake2s(raw, digest_size=8).digest(), "little")
        return times, checksum

    with path.open("rb", buffering=0) as f:
        for off in offsets:
            if len(os.pread(f.fileno(), BLOCK_SIZE, off)) != BLOCK_SIZE:
                raise RuntimeError("warmup short read")
        pread_ns, pread_checksum = run_pread(f.fileno())
        mmap_ns, mmap_checksum = run_mmap(f.fileno())

    if pread_checksum != mmap_checksum:
        raise RuntimeError("backend byte-consequence mismatch")

    def stats(values: list[int]) -> dict[str, float]:
        ordered = sorted(values)
        p95_idx = min(len(ordered) - 1, max(0, int(len(ordered) * 0.95) - 1))
        return {
            "median_us": statistics.median(ordered) / 1000.0,
            "p95_us": ordered[p95_idx] / 1000.0,
            "mean_us": statistics.fmean(ordered) / 1000.0,
        }

    return {
        "mode": "WARM_SAME_4K_OFFSETS",
        "sample_count": samples,
        "seed": seed,
        "pread": stats(pread_ns),
        "mmap": stats(mmap_ns),
        "same_byte_consequence": True,
        "checksum64": f"{pread_checksum:016x}",
        "cold_nvme_performance_proven": False,
        "production_backend_promotion_authorized": False,
    }


def bandwidth_sanity(dataset_bytes: int, claimed_seconds: float, theoretical_bytes_per_second: float) -> dict[str, object]:
    required = dataset_bytes / claimed_seconds
    return {
        "dataset_bytes": dataset_bytes,
        "claimed_seconds": claimed_seconds,
        "required_bytes_per_second": required,
        "theoretical_bytes_per_second": theoretical_bytes_per_second,
        "claim_exceeds_theoretical_stream_bandwidth": required > theoretical_bytes_per_second,
    }


@dataclass(frozen=True)
class HostQualificationReceipt:
    schema: str
    os: str
    kernel: str
    machine: str
    wsl_detected: bool
    cpu_model: str
    logical_cpu_count: int | None
    simd_path: str
    avx2_present: bool
    avx512f_present: bool
    popcnt_present: bool
    memory_total_bytes: int | None
    nvidia_cuda_present: bool
    storage: dict[str, object]
    benchmark: dict[str, object]
    host_observation_only: bool
    production_mmap_promotion_authorized: bool
    io_uring_direct_path_proven: bool
    native_transformer_kv_accessed: bool
    semantic_k27_authority: bool


def cpu_model_name(cpuinfo: str | None = None) -> str:
    text = cpuinfo if cpuinfo is not None else _read_text("/proc/cpuinfo")
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip().lower() in {"model name", "hardware"}:
            return value.strip()
    return platform.processor() or "UNKNOWN"


def qualify(benchmark_dir: Path, size_mib: int, samples: int) -> dict[str, object]:
    flags = cpu_flags()
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="aura-k27-host-probe-", suffix=".bin", dir=benchmark_dir, delete=False) as tmp:
        path = Path(tmp.name)
    try:
        digest = deterministic_file(path, size_mib * 1024 * 1024)
        bench = benchmark_same_pages(path, samples=samples)
        bench["file_size_bytes"] = path.stat().st_size
        bench["file_sha256"] = digest
        receipt = HostQualificationReceipt(
            schema=SCHEMA,
            os=platform.system(),
            kernel=platform.release(),
            machine=platform.machine(),
            wsl_detected=detect_wsl(),
            cpu_model=cpu_model_name(),
            logical_cpu_count=os.cpu_count(),
            simd_path=select_simd_path(flags),
            avx2_present="avx2" in flags,
            avx512f_present="avx512f" in flags,
            popcnt_present="popcnt" in flags,
            memory_total_bytes=memory_total_bytes(),
            nvidia_cuda_present=nvidia_cuda_present(),
            storage=storage_summary(benchmark_dir),
            benchmark=bench,
            host_observation_only=True,
            production_mmap_promotion_authorized=False,
            io_uring_direct_path_proven=False,
            native_transformer_kv_accessed=False,
            semantic_k27_authority=False,
        )
        out = asdict(receipt)
        out["receipt_sha256"] = _sha256(json.dumps(out, sort_keys=True, separators=(",", ":")).encode())
        return out
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--benchmark-dir", type=Path, default=Path(tempfile.gettempdir()))
    p.add_argument("--size-mib", type=int, default=64)
    p.add_argument("--samples", type=int, default=2048)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.size_mib < 4 or args.size_mib > 1024:
        p.error("--size-mib must be in [4, 1024]")
    if args.samples < 64 or args.samples > 1_000_000:
        p.error("--samples must be in [64, 1000000]")
    result = qualify(args.benchmark_dir, args.size_mib, args.samples)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())