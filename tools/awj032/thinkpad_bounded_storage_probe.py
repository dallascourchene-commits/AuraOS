"""Read-only, bounded owner-host storage probe for the AWJ032 ThinkPad lane.

This module performs *logical* file reads against one explicitly bounded path
inside the C2 request workspace.  It can measure logical bytes/read operations
and elapsed time.  It deliberately does not claim that buffered reads reached
physical NVMe media, does not bypass or flush the page cache, does not execute
a model, and does not authenticate the producer or admit G2.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import time
from typing import Any

from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest

PROBE_SCHEMA = "AWJ032ThinkPadBoundedStorageProbeReceiptV1"
PROBE_MODE = "BUFFERED_PREAD_READ_ONLY"
MAX_PROBE_BYTES = 256 * 1024 * 1024
MAX_PROBE_WALL_SECONDS = 30.0
MAX_CHUNK_BYTES = 8 * 1024 * 1024


class ThinkPadStorageProbeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ThinkPadStorageProbeError("NONCANONICAL_PROBE_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ThinkPadStorageProbeError(code)
    return value.strip()


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ThinkPadStorageProbeError(code)
    return value


def _positive_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ThinkPadStorageProbeError(code)
    return value


def _positive_float(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ThinkPadStorageProbeError(code)
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ThinkPadStorageProbeError(code)
    return result


def _file_identity(relative_path: str, st: os.stat_result) -> dict[str, Any]:
    return {
        "relative_path": relative_path,
        "device": int(st.st_dev),
        "inode": int(st.st_ino),
        "size_bytes": int(st.st_size),
        "mtime_ns": int(st.st_mtime_ns),
        "mode": int(st.st_mode),
    }


@dataclass(frozen=True)
class ThinkPadStorageProbeReceipt:
    request_digest: str
    relative_path: str
    file_identity_digest: str
    file_size_bytes: int
    byte_offset: int
    requested_probe_bytes: int
    logical_bytes_read: int
    read_operations: int
    chunk_bytes: int
    elapsed_seconds: float
    observed_logical_read_bytes_per_second: float
    window_sha256: str
    eof_reached: bool
    probe_mode: str = PROBE_MODE
    page_cache_bypass_proven: bool = False
    physical_nvme_io_attested: bool = False
    storage_medium_nvme_proven: bool = False
    producer_authenticated: bool = False
    model_execution_observed: bool = False
    lifecycle_measurement_admitted: bool = False
    effect_authority_proven: bool = False
    g2_admitted: bool = False
    schema: str = PROBE_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())

    @property
    def evidence_ref(self) -> str:
        return f"awj032-thinkpad-storage-probe-sha256:{self.receipt_digest}"


def _resolve_bounded_target(workspace_root: str, relative_path: str) -> tuple[Path, Path]:
    root_text = _text(workspace_root, "WORKSPACE_ROOT_REQUIRED")
    rel_text = _text(relative_path, "RELATIVE_PATH_REQUIRED")
    rel = Path(rel_text)
    if rel.is_absolute() or ".." in rel.parts:
        raise ThinkPadStorageProbeError("TARGET_PATH_NOT_BOUNDED_RELATIVE")

    root = Path(root_text).resolve(strict=True)
    if not root.is_dir():
        raise ThinkPadStorageProbeError("WORKSPACE_ROOT_NOT_DIRECTORY")

    lexical_target = root.joinpath(rel)
    try:
        lst = lexical_target.lstat()
    except FileNotFoundError as exc:
        raise ThinkPadStorageProbeError("TARGET_NOT_FOUND") from exc
    if stat.S_ISLNK(lst.st_mode):
        raise ThinkPadStorageProbeError("TARGET_SYMLINK_FORBIDDEN")

    target = lexical_target.resolve(strict=True)
    try:
        if os.path.commonpath((str(root), str(target))) != str(root):
            raise ThinkPadStorageProbeError("TARGET_ESCAPES_WORKSPACE")
    except ValueError as exc:
        raise ThinkPadStorageProbeError("TARGET_ESCAPES_WORKSPACE") from exc
    if not target.is_file():
        raise ThinkPadStorageProbeError("TARGET_NOT_REGULAR_FILE")
    return root, target


def run_bounded_storage_probe(
    *,
    request: OwnerHostC2CanaryRequest,
    relative_path: str,
    byte_offset: int,
    probe_bytes: int,
    chunk_bytes: int,
    max_wall_seconds: float,
) -> ThinkPadStorageProbeReceipt:
    """Read one bounded file window without writing or claiming physical media I/O."""
    if type(request) is not OwnerHostC2CanaryRequest:
        raise ThinkPadStorageProbeError("C2_REQUEST_TYPE_INVALID")
    if request.execution_authorized_by_this_contract is not False or request.g2_admitted is not False:
        raise ThinkPadStorageProbeError("C2_REQUEST_AUTHORITY_WIDENED")

    offset = _nonnegative_int(byte_offset, "BYTE_OFFSET_INVALID")
    bounded_bytes = _positive_int(probe_bytes, "PROBE_BYTES_INVALID")
    chunk = _positive_int(chunk_bytes, "CHUNK_BYTES_INVALID")
    wall = _positive_float(max_wall_seconds, "MAX_WALL_SECONDS_INVALID")

    if bounded_bytes > MAX_PROBE_BYTES or bounded_bytes > request.max_payload_bytes:
        raise ThinkPadStorageProbeError("PROBE_EXCEEDS_C2_PAYLOAD_BOUND")
    if chunk > MAX_CHUNK_BYTES or chunk > bounded_bytes:
        raise ThinkPadStorageProbeError("CHUNK_BYTES_OUT_OF_BOUND")
    if wall > MAX_PROBE_WALL_SECONDS or wall > float(request.max_wall_seconds):
        raise ThinkPadStorageProbeError("PROBE_EXCEEDS_C2_WALL_BOUND")

    _, target = _resolve_bounded_target(request.workspace_root, relative_path)
    open_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(target, open_flags)
    except OSError as exc:
        raise ThinkPadStorageProbeError("TARGET_READ_OPEN_FAILED") from exc

    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ThinkPadStorageProbeError("TARGET_NOT_REGULAR_FILE")
        if offset > before.st_size:
            raise ThinkPadStorageProbeError("BYTE_OFFSET_BEYOND_EOF")

        identity = _file_identity(relative_path, before)
        window_hasher = hashlib.sha256()
        logical_bytes = 0
        operations = 0
        eof = False
        start_ns = time.monotonic_ns()
        deadline_ns = start_ns + int(wall * 1_000_000_000)

        while logical_bytes < bounded_bytes:
            now = time.monotonic_ns()
            if now >= deadline_ns:
                break
            to_read = min(chunk, bounded_bytes - logical_bytes)
            payload = os.pread(fd, to_read, offset + logical_bytes)
            operations += 1
            if not payload:
                eof = True
                break
            logical_bytes += len(payload)
            window_hasher.update(payload)
            if len(payload) < to_read:
                eof = True
                break

        end_ns = time.monotonic_ns()
        after = os.fstat(fd)
    finally:
        os.close(fd)

    if (
        before.st_dev != after.st_dev
        or before.st_ino != after.st_ino
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
    ):
        raise ThinkPadStorageProbeError("TARGET_CHANGED_DURING_PROBE")
    if logical_bytes <= 0 or operations <= 0:
        raise ThinkPadStorageProbeError("PROBE_PRODUCED_NO_EVIDENCE")

    elapsed = (end_ns - start_ns) / 1_000_000_000
    if elapsed <= 0:
        raise ThinkPadStorageProbeError("PROBE_CLOCK_INVALID")
    observed_bps = logical_bytes / elapsed

    return ThinkPadStorageProbeReceipt(
        request_digest=request.request_digest,
        relative_path=relative_path,
        file_identity_digest=_digest(identity),
        file_size_bytes=int(before.st_size),
        byte_offset=offset,
        requested_probe_bytes=bounded_bytes,
        logical_bytes_read=logical_bytes,
        read_operations=operations,
        chunk_bytes=chunk,
        elapsed_seconds=elapsed,
        observed_logical_read_bytes_per_second=observed_bps,
        window_sha256=window_hasher.hexdigest(),
        eof_reached=eof,
    )
