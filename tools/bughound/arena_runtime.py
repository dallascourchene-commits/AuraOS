"""BugHound local ephemeral Arena runtime R0.

R0 is a deterministic local/tempdir capsule used to exercise BugHound against
source-bound snapshots without granting network, credential, submission, payout,
or other external-effect authority.  It separates immutable-input intent
(`source/`) from writable work (`overlay/`) and evidence (`evidence/`).

Important claim ceiling: ``network_policy == OFF`` is an admission contract in
R0, not proof of an OS/container network namespace.  R0 therefore always emits
``os_network_isolation_proven=False``.  A later R1 sandbox/container runtime must
supply that stronger proof independently.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Mapping

from tools.bughound.target_profile import (
    BugHoundTargetProfileReceiptV1,
    BugHoundTargetProfileV1,
    bind_target_profile,
)

SCHEMA = "BugHoundArenaRuntimeR0ReceiptV1"
TEARDOWN_SCHEMA = "BugHoundArenaTeardownReceiptV1"
EVIDENCE_SCHEMA = "BugHoundArenaEvidenceEventV1"
NETWORK_OFF = "OFF"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _safe_relative_path(path: str) -> str:
    _require_text("RELATIVE_PATH", path)
    if "\x00" in path or "\\" in path or path.startswith("/"):
        raise ValueError("BUGHOUND_CAPSULE_PATH_INVALID")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError("BUGHOUND_CAPSULE_PATH_INVALID")
    return "/".join(parts)


def _to_bytes(value: bytes | str) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError("BUGHOUND_SOURCE_CONTENT_MUST_BE_BYTES_OR_TEXT")


def source_tree_digest(files: Mapping[str, bytes | str]) -> str:
    """Return a deterministic digest over safe relative paths and exact bytes."""
    rows: list[dict[str, object]] = []
    for path in sorted(files):
        safe = _safe_relative_path(path)
        payload = _to_bytes(files[path])
        rows.append(
            {
                "path": safe,
                "size": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
        )
    return _digest("AURA_BUGHOUND_R0_SOURCE_TREE_V1", rows)


@dataclass(frozen=True)
class BugHoundArenaRuntimeR0SpecV1:
    profile: BugHoundTargetProfileV1
    source_digest: str
    network_policy: str = NETWORK_OFF
    credential_refs: tuple[str, ...] = ()
    max_source_files: int = 4096
    max_source_bytes: int = 16 * 1024 * 1024
    max_overlay_bytes: int = 16 * 1024 * 1024


@dataclass(frozen=True)
class BugHoundArenaEvidenceEventV1:
    sequence: int
    event_type: str
    artifact_ref: str
    artifact_digest: str
    schema: str = EVIDENCE_SCHEMA

    @property
    def event_digest(self) -> str:
        return _digest("AURA_BUGHOUND_R0_EVIDENCE_EVENT_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundArenaRuntimeR0ReceiptV1:
    capsule_id: str
    profile_receipt_digest: str
    profile_id: str
    target_ref: str
    target_generation: str
    source_digest: str
    source_file_count: int
    source_bytes: int
    network_policy: str
    logical_network_policy_off: bool
    os_network_isolation_proven: bool
    credential_count: int
    source_write_bits_present: bool
    external_effect: bool = False
    live_target_testing_authorized: bool = False
    submission_authorized: bool = False
    payout_authority: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_ARENA_RUNTIME_R0_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundArenaTeardownReceiptV1:
    capsule_id: str
    source_digest_expected: str
    source_digest_observed: str | None
    source_intact_before_teardown: bool
    evidence_event_count: int
    evidence_digest: str
    root_removed: bool
    network_policy: str
    credential_count: int
    os_network_isolation_proven: bool = False
    external_effect: bool = False
    schema: str = TEARDOWN_SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_ARENA_TEARDOWN_V1", asdict(self))


class BugHoundArenaRuntimeR0:
    """A bounded local capsule with source/overlay/evidence plane separation."""

    def __init__(
        self,
        spec: BugHoundArenaRuntimeR0SpecV1,
        source_files: Mapping[str, bytes | str],
    ) -> None:
        self.spec = spec
        self._source_files = dict(source_files)
        self._root: Path | None = None
        self._profile_receipt: BugHoundTargetProfileReceiptV1 | None = None
        self._events: list[BugHoundArenaEvidenceEventV1] = []
        self._materialization_receipt: BugHoundArenaRuntimeR0ReceiptV1 | None = None
        self._teardown_receipt: BugHoundArenaTeardownReceiptV1 | None = None

    @property
    def active(self) -> bool:
        return self._root is not None and self._root.exists()

    @property
    def root_path(self) -> Path:
        if not self.active or self._root is None:
            raise RuntimeError("BUGHOUND_CAPSULE_NOT_ACTIVE")
        return self._root

    @property
    def source_path(self) -> Path:
        return self.root_path / "source"

    @property
    def overlay_path(self) -> Path:
        return self.root_path / "overlay"

    @property
    def evidence_path(self) -> Path:
        return self.root_path / "evidence"

    @property
    def teardown_receipt(self) -> BugHoundArenaTeardownReceiptV1 | None:
        return self._teardown_receipt

    def _validate_admission(self) -> tuple[BugHoundTargetProfileReceiptV1, int]:
        if self.spec.network_policy != NETWORK_OFF:
            raise ValueError("BUGHOUND_R0_NETWORK_MUST_BE_OFF")
        if self.spec.credential_refs:
            raise ValueError("BUGHOUND_R0_CREDENTIALS_FORBIDDEN")
        if self.spec.max_source_files <= 0 or self.spec.max_source_bytes < 0:
            raise ValueError("BUGHOUND_R0_SOURCE_LIMIT_INVALID")
        if self.spec.max_overlay_bytes < 0:
            raise ValueError("BUGHOUND_R0_OVERLAY_LIMIT_INVALID")
        if len(self._source_files) > self.spec.max_source_files:
            raise ValueError("BUGHOUND_R0_SOURCE_FILE_LIMIT_EXCEEDED")
        total = sum(len(_to_bytes(value)) for value in self._source_files.values())
        if total > self.spec.max_source_bytes:
            raise ValueError("BUGHOUND_R0_SOURCE_BYTE_LIMIT_EXCEEDED")
        observed = source_tree_digest(self._source_files)
        if observed != self.spec.source_digest:
            raise ValueError("BUGHOUND_R0_SOURCE_DIGEST_MISMATCH")
        profile_receipt = bind_target_profile(self.spec.profile)
        return profile_receipt, total

    def materialize(self) -> BugHoundArenaRuntimeR0ReceiptV1:
        if self.active:
            raise RuntimeError("BUGHOUND_CAPSULE_ALREADY_ACTIVE")
        profile_receipt, total_bytes = self._validate_admission()
        root = Path(tempfile.mkdtemp(prefix="bughound-r0-"))
        source = root / "source"
        overlay = root / "overlay"
        evidence = root / "evidence"
        source.mkdir()
        overlay.mkdir()
        evidence.mkdir()

        try:
            for relative, value in sorted(self._source_files.items()):
                safe = _safe_relative_path(relative)
                target = source / safe
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(_to_bytes(value))
                target.chmod(0o444)
            # Remove write bits from every directory in the source plane after
            # materialization.  This is local filesystem evidence, not a
            # hostile-process security boundary.
            for directory in sorted(
                (p for p in source.rglob("*") if p.is_dir()),
                key=lambda p: len(p.parts),
                reverse=True,
            ):
                directory.chmod(0o555)
            source.chmod(0o555)
        except Exception:
            shutil.rmtree(root, ignore_errors=True)
            raise

        self._root = root
        self._profile_receipt = profile_receipt
        capsule_id = _digest(
            "AURA_BUGHOUND_R0_CAPSULE_ID_V1",
            {
                "profile_receipt_digest": profile_receipt.receipt_digest,
                "source_digest": self.spec.source_digest,
                "network_policy": self.spec.network_policy,
                "max_source_files": self.spec.max_source_files,
                "max_source_bytes": self.spec.max_source_bytes,
                "max_overlay_bytes": self.spec.max_overlay_bytes,
            },
        )
        write_bits = any((p.stat().st_mode & 0o222) != 0 for p in source.rglob("*"))
        receipt = BugHoundArenaRuntimeR0ReceiptV1(
            capsule_id=capsule_id,
            profile_receipt_digest=profile_receipt.receipt_digest,
            profile_id=profile_receipt.profile_id,
            target_ref=profile_receipt.target_ref,
            target_generation=profile_receipt.target_generation,
            source_digest=self.spec.source_digest,
            source_file_count=len(self._source_files),
            source_bytes=total_bytes,
            network_policy=self.spec.network_policy,
            logical_network_policy_off=True,
            os_network_isolation_proven=False,
            credential_count=0,
            source_write_bits_present=write_bits,
        )
        self._materialization_receipt = receipt
        return receipt

    def read_source(self, relative_path: str) -> bytes:
        safe = _safe_relative_path(relative_path)
        path = self.source_path / safe
        if not path.is_file():
            raise FileNotFoundError(safe)
        return path.read_bytes()

    def write_overlay(self, relative_path: str, content: bytes | str) -> str:
        safe = _safe_relative_path(relative_path)
        payload = _to_bytes(content)
        existing = sum(p.stat().st_size for p in self.overlay_path.rglob("*") if p.is_file())
        target = self.overlay_path / safe
        previous = target.stat().st_size if target.exists() and target.is_file() else 0
        if existing - previous + len(payload) > self.spec.max_overlay_bytes:
            raise ValueError("BUGHOUND_R0_OVERLAY_BYTE_LIMIT_EXCEEDED")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return hashlib.sha256(payload).hexdigest()

    def append_evidence(
        self,
        *,
        event_type: str,
        artifact_ref: str,
        artifact_digest: str,
    ) -> BugHoundArenaEvidenceEventV1:
        _require_text("EVENT_TYPE", event_type)
        _require_text("ARTIFACT_REF", artifact_ref)
        _require_text("ARTIFACT_DIGEST", artifact_digest)
        event = BugHoundArenaEvidenceEventV1(
            sequence=len(self._events) + 1,
            event_type=event_type,
            artifact_ref=artifact_ref,
            artifact_digest=artifact_digest,
        )
        self._events.append(event)
        with (self.evidence_path / "events.jsonl").open("ab") as handle:
            handle.write(_canonical({**asdict(event), "event_digest": event.event_digest}) + b"\n")
        return event

    def _observed_source_digest(self) -> str | None:
        if not self.active:
            return None
        observed: dict[str, bytes] = {}
        for path in self.source_path.rglob("*"):
            if path.is_file():
                observed[path.relative_to(self.source_path).as_posix()] = path.read_bytes()
        return source_tree_digest(observed)

    @staticmethod
    def _make_owner_writable(root: Path) -> None:
        if not root.exists():
            return
        for path in root.rglob("*"):
            try:
                if path.is_dir():
                    path.chmod(0o755)
                else:
                    path.chmod(0o644)
            except OSError:
                pass
        try:
            root.chmod(0o755)
        except OSError:
            pass

    def teardown(self) -> BugHoundArenaTeardownReceiptV1:
        if self._teardown_receipt is not None:
            return self._teardown_receipt
        if not self.active or self._root is None or self._materialization_receipt is None:
            raise RuntimeError("BUGHOUND_CAPSULE_NOT_ACTIVE")

        root = self._root
        observed = self._observed_source_digest()
        intact = observed == self.spec.source_digest
        evidence_digest = _digest(
            "AURA_BUGHOUND_R0_EVIDENCE_LOG_V1",
            [event.event_digest for event in self._events],
        )
        self._make_owner_writable(root)
        shutil.rmtree(root)
        removed = not root.exists()
        receipt = BugHoundArenaTeardownReceiptV1(
            capsule_id=self._materialization_receipt.capsule_id,
            source_digest_expected=self.spec.source_digest,
            source_digest_observed=observed,
            source_intact_before_teardown=intact,
            evidence_event_count=len(self._events),
            evidence_digest=evidence_digest,
            root_removed=removed,
            network_policy=self.spec.network_policy,
            credential_count=0,
        )
        self._root = None
        self._teardown_receipt = receipt
        return receipt

    def __enter__(self) -> "BugHoundArenaRuntimeR0":
        self.materialize()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.active:
            self.teardown()
