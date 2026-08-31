#!/usr/bin/env python3
"""Observe io_uring capability without converting availability into performance authority."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import platform
from pathlib import Path

SCHEMA = "AURA_K27_ASTGE_IO_URING_CAPABILITY_OBSERVATION_V1"
BLOCK_SIZE = 4096


class IoSqringOffsets(ctypes.Structure):
    _fields_ = [
        ("head", ctypes.c_uint32), ("tail", ctypes.c_uint32),
        ("ring_mask", ctypes.c_uint32), ("ring_entries", ctypes.c_uint32),
        ("flags", ctypes.c_uint32), ("dropped", ctypes.c_uint32),
        ("array", ctypes.c_uint32), ("resv1", ctypes.c_uint32),
        ("user_addr", ctypes.c_uint64),
    ]


class IoCqringOffsets(ctypes.Structure):
    _fields_ = [
        ("head", ctypes.c_uint32), ("tail", ctypes.c_uint32),
        ("ring_mask", ctypes.c_uint32), ("ring_entries", ctypes.c_uint32),
        ("overflow", ctypes.c_uint32), ("cqes", ctypes.c_uint32),
        ("flags", ctypes.c_uint32), ("resv1", ctypes.c_uint32),
        ("user_addr", ctypes.c_uint64),
    ]


class IoUringParams(ctypes.Structure):
    _fields_ = [
        ("sq_entries", ctypes.c_uint32), ("cq_entries", ctypes.c_uint32),
        ("flags", ctypes.c_uint32), ("sq_thread_cpu", ctypes.c_uint32),
        ("sq_thread_idle", ctypes.c_uint32), ("features", ctypes.c_uint32),
        ("wq_fd", ctypes.c_uint32), ("resv", ctypes.c_uint32 * 3),
        ("sq_off", IoSqringOffsets), ("cq_off", IoCqringOffsets),
    ]


class IOVec(ctypes.Structure):
    _fields_ = [("iov_base", ctypes.c_void_p), ("iov_len", ctypes.c_size_t)]


def _wsl() -> bool:
    try:
        text = Path('/proc/version').read_text(errors='replace').lower()
    except OSError:
        text = ''
    return 'microsoft' in text or 'wsl' in text


def observe(machine: str | None = None) -> dict[str, object]:
    arch = (machine or platform.machine()).lower()
    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "machine": arch,
        "kernel": platform.release(),
        "wsl_detected": _wsl(),
        "io_uring_setup_observed": False,
        "registered_anonymous_buffer_observed": False,
        "registered_buffer_size": BLOCK_SIZE,
        "probe_errno": None,
        "probe_reason": "UNSUPPORTED_PROBE_ARCH",
        "direct_io_file_read_observed": False,
        "io_uring_direct_performance_proven": False,
        "cold_nvme_superiority_proven": False,
        "production_backend_promotion_authorized": False,
        "native_transformer_kv_accessed": False,
        "semantic_k27_authority": False,
    }
    if arch not in {'x86_64', 'amd64'}:
        return _seal(receipt)

    libc = ctypes.CDLL(None, use_errno=True)
    syscall = libc.syscall
    syscall.restype = ctypes.c_long
    params = IoUringParams()
    fd = syscall(425, 2, ctypes.byref(params))
    if fd < 0:
        err = ctypes.get_errno()
        receipt["probe_errno"] = err
        receipt["probe_reason"] = os.strerror(err)
        return _seal(receipt)

    receipt["io_uring_setup_observed"] = True
    try:
        raw = ctypes.create_string_buffer(BLOCK_SIZE)
        iov = IOVec(ctypes.cast(raw, ctypes.c_void_p), BLOCK_SIZE)
        rc = syscall(427, fd, 0, ctypes.byref(iov), 1)
        if rc == 0:
            receipt["registered_anonymous_buffer_observed"] = True
            receipt["probe_reason"] = "REGISTERED_ANONYMOUS_BUFFER"
            syscall(427, fd, 1, None, 0)
        else:
            err = ctypes.get_errno()
            receipt["probe_errno"] = err
            receipt["probe_reason"] = os.strerror(err)
    finally:
        os.close(fd)
    return _seal(receipt)


def _seal(receipt: dict[str, object]) -> dict[str, object]:
    out = dict(receipt)
    raw = json.dumps(out, sort_keys=True, separators=(',', ':')).encode()
    out['receipt_sha256'] = hashlib.sha256(raw).hexdigest()
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    receipt = observe()
    text = json.dumps(receipt, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + '\n')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
