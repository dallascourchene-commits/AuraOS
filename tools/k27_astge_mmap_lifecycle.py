"""Fail-closed lifecycle guard for the K27 ASTGE mmap reference reader.

This module does not claim that a userspace precheck can make file-backed mmap
intrinsically safe.  Instead it defines the strongest deterministic reference
contract Aura can own before each mapped read:

- bind the opened file descriptor to the path identity observed at open;
- bind exact size plus full-content digest for nodes and edge pages;
- reject truncation, replacement, mutation and closed handles before mapped use;
- bound raw slices before access;
- validate the generation again after successful mapped operations;
- require an explicit reopen/remap after a generation change.

There is an unavoidable process-race ceiling between validation and a later OS
memory access.  Accordingly every receipt keeps both SIGBUS-impossibility and
concurrent-mutation-race safety false.  Native/Rust code needs its own ownership,
locking/versioning and platform-specific proof before those claims can change.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import BinaryIO, Literal

import k27_astge_reference as ref

SCHEMA = "AuraK27ASTGEMmapLifecycleGuardV1"
READ_CHUNK = 1024 * 1024


class MmapLifecycleError(ref.ASTGEFormatError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _digest_fd(fd: int, expected_size: int) -> str:
    h = hashlib.sha256(b"AURA_K27_ASTGE_MMAP_FILE_CONTENT_V1\0")
    offset = 0
    if hasattr(os, "pread"):
        while offset < expected_size:
            chunk = os.pread(fd, min(READ_CHUNK, expected_size - offset), offset)
            if not chunk:
                raise MmapLifecycleError("MMAP_FILE_SHORT_READ_DURING_DIGEST")
            h.update(chunk)
            offset += len(chunk)
    else:  # pragma: no cover - Linux hosted contract uses pread.
        dup = os.dup(fd)
        try:
            with os.fdopen(dup, "rb", closefd=True) as handle:
                handle.seek(0)
                while offset < expected_size:
                    chunk = handle.read(min(READ_CHUNK, expected_size - offset))
                    if not chunk:
                        raise MmapLifecycleError("MMAP_FILE_SHORT_READ_DURING_DIGEST")
                    h.update(chunk)
                    offset += len(chunk)
        except Exception:
            try:
                os.close(dup)
            except OSError:
                pass
            raise
    return h.hexdigest()


@dataclass(frozen=True)
class MappedFileGenerationV1:
    role: str
    path: str
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    content_digest: str

    @property
    def generation_digest(self) -> str:
        return hashlib.sha256(
            b"AURA_K27_ASTGE_MMAP_FILE_GENERATION_V1\0" + _canonical(asdict(self))
        ).hexdigest()


@dataclass(frozen=True)
class MmapLifecycleValidationReceiptV1:
    nodes_generation_digest: str
    edges_generation_digest: str
    combined_generation_digest: str
    path_identity_verified: bool = True
    exact_size_verified: bool = True
    full_content_digest_verified: bool = True
    observed_generation_current: bool = True
    concurrent_mutation_race_proven_safe: bool = False
    sigbus_impossible_proven: bool = False
    native_engine_safety_proven: bool = False
    external_effect: bool = False
    schema: str = SCHEMA


def _capture_generation(role: str, path: str, handle: BinaryIO) -> MappedFileGenerationV1:
    if handle.closed:
        raise MmapLifecycleError("MMAP_LIFECYCLE_CLOSED")
    fd_stat = os.fstat(handle.fileno())
    try:
        path_stat = os.stat(path)
    except FileNotFoundError as exc:
        raise MmapLifecycleError(f"{role}_PATH_MISSING") from exc
    if (path_stat.st_dev, path_stat.st_ino) != (fd_stat.st_dev, fd_stat.st_ino):
        raise MmapLifecycleError(f"{role}_PATH_FD_IDENTITY_MISMATCH")
    return MappedFileGenerationV1(
        role=role,
        path=str(Path(path).resolve()),
        device=fd_stat.st_dev,
        inode=fd_stat.st_ino,
        size=fd_stat.st_size,
        mtime_ns=fd_stat.st_mtime_ns,
        ctime_ns=fd_stat.st_ctime_ns,
        content_digest=_digest_fd(handle.fileno(), fd_stat.st_size),
    )


def _validate_generation(snapshot: MappedFileGenerationV1, handle: BinaryIO) -> None:
    role = snapshot.role
    if handle.closed:
        raise MmapLifecycleError("MMAP_LIFECYCLE_CLOSED")
    fd_stat = os.fstat(handle.fileno())
    if (fd_stat.st_dev, fd_stat.st_ino) != (snapshot.device, snapshot.inode):
        raise MmapLifecycleError(f"{role}_FD_IDENTITY_DRIFT")
    try:
        path_stat = os.stat(snapshot.path)
    except FileNotFoundError as exc:
        raise MmapLifecycleError(f"{role}_PATH_MISSING") from exc
    if (path_stat.st_dev, path_stat.st_ino) != (snapshot.device, snapshot.inode):
        raise MmapLifecycleError(f"{role}_PATH_REPLACED")
    if fd_stat.st_size < snapshot.size:
        raise MmapLifecycleError(f"{role}_FILE_TRUNCATED")
    if fd_stat.st_size != snapshot.size:
        raise MmapLifecycleError(f"{role}_FILE_SIZE_DRIFT")
    current_digest = _digest_fd(handle.fileno(), snapshot.size)
    if current_digest != snapshot.content_digest:
        raise MmapLifecycleError(f"{role}_FILE_CONTENT_DRIFT")
    if fd_stat.st_mtime_ns != snapshot.mtime_ns or fd_stat.st_ctime_ns != snapshot.ctime_ns:
        raise MmapLifecycleError(f"{role}_FILE_METADATA_DRIFT")


def _combined_digest(nodes: MappedFileGenerationV1, edges: MappedFileGenerationV1) -> str:
    payload = {
        "nodes": nodes.generation_digest,
        "edges": edges.generation_digest,
    }
    return hashlib.sha256(
        b"AURA_K27_ASTGE_MMAP_COMBINED_GENERATION_V1\0" + _canonical(payload)
    ).hexdigest()


class LifecycleGuardedMmapGraphReader:
    """Composition guard around PR459's exact mmap reference reader."""

    def __init__(self, nodes_path: os.PathLike[str] | str, edges_path: os.PathLike[str] | str):
        self._nodes_path = str(Path(nodes_path).resolve())
        self._edges_path = str(Path(edges_path).resolve())
        self._reader = ref.MmapGraphReader(self._nodes_path, self._edges_path)
        try:
            self._nodes_generation = _capture_generation(
                "NODES", self._nodes_path, self._reader._nodes_file
            )
            self._edges_generation = _capture_generation(
                "EDGES", self._edges_path, self._reader._edges_file
            )
        except Exception:
            self._reader.close()
            raise
        self._closed = False

    @property
    def node_count(self) -> int:
        self._require_open()
        return self._reader.node_count

    @property
    def block_count(self) -> int:
        self._require_open()
        return self._reader.block_count

    def _require_open(self) -> None:
        if self._closed or self._reader._nodes_file is None or self._reader._edges_file is None:
            raise MmapLifecycleError("MMAP_LIFECYCLE_CLOSED")

    def validate_generation(self) -> MmapLifecycleValidationReceiptV1:
        self._require_open()
        _validate_generation(self._nodes_generation, self._reader._nodes_file)
        _validate_generation(self._edges_generation, self._reader._edges_file)
        return MmapLifecycleValidationReceiptV1(
            nodes_generation_digest=self._nodes_generation.generation_digest,
            edges_generation_digest=self._edges_generation.generation_digest,
            combined_generation_digest=_combined_digest(
                self._nodes_generation, self._edges_generation
            ),
        )

    def _validated_operation(self, fn, *args, **kwargs):
        before = self.validate_generation()
        result = fn(*args, **kwargs)
        after = self.validate_generation()
        if after.combined_generation_digest != before.combined_generation_digest:
            raise MmapLifecycleError("MMAP_GENERATION_CHANGED_DURING_OPERATION")
        return result

    def get_node(self, node_id: int) -> ref.NodeRecord:
        return self._validated_operation(self._reader.get_node, node_id)

    def query_affected_cone(self, root_node_id: int, max_depth: int) -> ref.HydratedCone:
        return self._validated_operation(
            self._reader.query_affected_cone, root_node_id, max_depth
        )

    def read_bounded_slice(
        self, role: Literal["nodes", "edges"], start: int, length: int
    ) -> bytes:
        self._require_open()
        if not isinstance(start, int) or not isinstance(length, int) or start < 0 or length < 0:
            raise MmapLifecycleError("MMAP_SLICE_RANGE_INVALID")
        if role == "nodes":
            mapping = self._reader._nodes_mmap
            size = self._nodes_generation.size
        elif role == "edges":
            mapping = self._reader._edges_mmap
            size = self._edges_generation.size
        else:
            raise MmapLifecycleError("MMAP_SLICE_ROLE_INVALID")
        end = start + length
        if end < start or end > size:
            raise MmapLifecycleError("MMAP_SLICE_OUT_OF_RANGE")
        return self._validated_operation(lambda: bytes(mapping[start:end]))

    def reopen(self) -> "LifecycleGuardedMmapGraphReader":
        """Close this generation and create a fresh mapping from current paths."""
        nodes_path, edges_path = self._nodes_path, self._edges_path
        self.close()
        return type(self)(nodes_path, edges_path)

    def close(self) -> None:
        if not self._closed:
            self._reader.close()
            self._closed = True

    def __enter__(self) -> "LifecycleGuardedMmapGraphReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
