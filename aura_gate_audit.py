"""Fail-closed Aura Gate audit adapter over canonical Aura contracts.

This module deliberately owns no independent audit truth.  Gate records are
canonical :class:`AuraEventEnvelope` entries with exact sanitized sidecars,
linked by canonical :class:`ChainedAuthorityReceipt` records.  The receipt
JSONL is an integrity index over the event store, not a competing ledger.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, fields
from enum import Enum
import json
import math
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, BinaryIO
from urllib.parse import urlsplit

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    canonical_json,
    sanitize_payload,
    stable_digest,
    stable_id,
)
from aura_relational_authority import (
    GENESIS_CHAIN_DIGEST,
    ChainedAuthorityReceipt,
    verify_receipt_chain,
)

if os.name == "nt":
    import msvcrt as _file_lock_backend
else:
    import fcntl as _file_lock_backend


GATE_AUDIT_VERSION = "AURA_GATE_AUDIT_V1"
SIEM_EVENT_VERSION = "AURA_GATE_SIEM_EVENT_V1"
_SIDECAR_KIND = "aura-gate-audit"
_RECEIPTS_FILENAME = "gate_receipts.jsonl"
_PHASES = frozenset({"PRE_ACTION", "POST_ACTION"})
_ACTOR_TYPES = frozenset(item.value for item in ActorType)
_EVENT_FIELDS = frozenset(item.name for item in fields(AuraEventEnvelope))
_RECEIPT_FIELDS = frozenset(item.name for item in fields(ChainedAuthorityReceipt))
_SIDECAR_FIELDS = frozenset(
    {
        "schema_version",
        "operation_id",
        "phase",
        "action",
        "actor_id",
        "actor_type",
        "purpose_digest",
        "policy_id",
        "policy_digest",
        "lease_id",
        "protocol",
        "destination",
        "decision",
        "verifier_id",
        "verifier_status",
        "cost_class",
        "revocation_reason",
        "dissolution_reason",
        "paired_live_id",
        "arena_id",
        "objective_id",
        "evidence_refs",
    }
)
_RECEIPT_ROW_FIELDS = frozenset(
    {
        "schema_version",
        "operation_id",
        "operation_digest",
        "event_id",
        "event_digest",
        "receipt",
    }
)
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_SAFE_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
_SAFE_TEXT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .,_:;/()\[\]+=-]{0,255}$")
_JWT = re.compile(r"(?:^|\s)[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}(?:$|\s)")
_FORBIDDEN_VALUE = re.compile(
    r"(?is)(?:"
    r"\bbearer\s+[A-Za-z0-9._~+/=%-]+|"
    r"\bbasic\s+[A-Za-z0-9+/=]+|"
    r"\bsk-[A-Za-z0-9._~+/=%-]{12,}|"
    r"\bAKIA[0-9A-Z]{16}\b|"
    r"-----BEGIN[^\r\n-]*PRIVATE KEY-----|"
    r"(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|auth[_ -]?token|"
    r"authorization|password|private[_ -]?key|secret)\s*[:=]|"
    r"chain[_ -]?of[_ -]?thought|hidden[_ -]?reasoning|private[_ -]?reasoning|"
    r"scratch[_ -]?pad|inner[_ -]?thought|"
    r"(?:system|developer|user)\s+prompt\s*[:=]|begin\s+prompt|"
    r"diff\s+--git|@@\s+-\d|```|<\|[^>]+\|>"
    r")"
)
_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


class GateAuditError(RuntimeError):
    """Bounded public failure raised when Gate audit cannot prove persistence."""

    def __init__(self, code: str, message: str) -> None:
        self.code = str(code)
        super().__init__(message)


@dataclass(frozen=True)
class _ReceiptRow:
    operation_id: str
    operation_digest: str
    event_id: str
    event_digest: str
    receipt: ChainedAuthorityReceipt


@dataclass(frozen=True)
class _LedgerState:
    events: tuple[AuraEventEnvelope, ...]
    sidecars: tuple[dict[str, Any], ...]
    rows: tuple[_ReceiptRow, ...]
    event_by_operation: Mapping[str, AuraEventEnvelope]
    sidecar_by_operation: Mapping[str, dict[str, Any]]
    row_by_operation: Mapping[str, _ReceiptRow]
    orphan_operation_id: str


def _thread_lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _acquire_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        if not handle.read(1):
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_LOCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_EX)


def _release_process_lock(handle: BinaryIO) -> None:
    handle.seek(0)
    if os.name == "nt":
        _file_lock_backend.locking(handle.fileno(), _file_lock_backend.LK_UNLCK, 1)
    else:
        _file_lock_backend.flock(handle.fileno(), _file_lock_backend.LOCK_UN)


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    thread_lock = _thread_lock_for(path)
    with thread_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a+b") as handle:
            _acquire_process_lock(handle)
            try:
                yield
            finally:
                _release_process_lock(handle)


def _fail(code: str, message: str) -> GateAuditError:
    return GateAuditError(code, message)


def _safe_text(
    value: Any,
    field_name: str,
    *,
    required: bool,
    limit: int = 256,
    token: bool = False,
) -> str:
    if isinstance(value, Enum):
        value = value.value
    if not isinstance(value, str):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", f"invalid gate audit field: {field_name}")
    text = value.strip()
    if required and not text:
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", f"missing gate audit field: {field_name}")
    if not text:
        return ""
    if len(text) > limit or "\n" in text or "\r" in text or "\0" in text:
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", f"invalid gate audit field: {field_name}")
    if _FORBIDDEN_VALUE.search(text) or _JWT.search(text):
        raise _fail("AURA_GATE_AUDIT_SENSITIVE_VALUE", f"sensitive gate audit field rejected: {field_name}")
    pattern = _SAFE_TOKEN if token else _SAFE_ID
    if not pattern.fullmatch(text):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", f"invalid gate audit field: {field_name}")
    return text


def _safe_reason(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", f"invalid gate audit field: {field_name}")
    text = value.strip()
    if not text:
        return ""
    if (
        len(text) > 256
        or "\n" in text
        or "\r" in text
        or "\0" in text
        or _FORBIDDEN_VALUE.search(text)
        or _JWT.search(text)
        or not _SAFE_TEXT.fullmatch(text)
    ):
        raise _fail("AURA_GATE_AUDIT_SENSITIVE_VALUE", f"unsafe gate audit field rejected: {field_name}")
    return text


def _safe_destination(value: Any) -> str:
    text = _safe_text(value, "destination", required=False, limit=256)
    if not text:
        return ""
    parsed = urlsplit(text)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"a2a", "http", "https", "mcp", "ws", "wss"}:
            raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: destination")
        if not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise _fail("AURA_GATE_AUDIT_SENSITIVE_VALUE", "unsafe gate audit field rejected: destination")
    return text


def _safe_refs(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: evidence_refs")
    try:
        refs = tuple(_safe_text(item, "evidence_refs", required=True, limit=256) for item in values)
    except TypeError as exc:
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: evidence_refs") from exc
    if len(refs) > 32 or len(set(refs)) != len(refs):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: evidence_refs")
    return refs


def _finite_timestamp(value: float | None, clock: Callable[[], float]) -> float:
    timestamp = clock() if value is None else value
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: created_at")
    normalized = float(timestamp)
    if not math.isfinite(normalized) or normalized < 0:
        raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: created_at")
    return normalized


def _exact_mapping(value: Any, expected: frozenset[str], artifact: str) -> dict[str, Any]:
    if not isinstance(value, dict) or frozenset(value) != expected:
        raise _fail("AURA_GATE_AUDIT_INTEGRITY", f"invalid {artifact} shape")
    if any(not isinstance(key, str) for key in value):
        raise _fail("AURA_GATE_AUDIT_INTEGRITY", f"invalid {artifact} shape")
    return value


class GateAuditLedger:
    """Narrow, fail-closed Gate adapter over Aura's canonical append-only store."""

    def __init__(
        self,
        root: str | Path,
        *,
        export_root: str | Path | None = None,
        ledger_id: str = "aura-gate",
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.root = Path(root).resolve()
        self.export_root = Path(
            export_root if export_root is not None else self.root.parent / f"{self.root.name}-siem"
        ).resolve()
        if (
            self.export_root == self.root
            or self.root in self.export_root.parents
            or self.export_root in self.root.parents
        ):
            raise _fail(
                "AURA_GATE_AUDIT_INVALID_INPUT",
                "SIEM export root must be separate from the audit ledger",
            )
        self.receipts_path = self.root / _RECEIPTS_FILENAME
        self.lock_path = self.root / ".gate-audit.lock"
        self.ledger_id = _safe_text(ledger_id, "ledger_id", required=True, limit=128)
        if not callable(clock):
            raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit clock")
        self._clock = clock
        try:
            self.export_root.mkdir(parents=True, exist_ok=True)
            self._store = AppendOnlyEventStore(self.root)
            with _exclusive_lock(self.lock_path):
                self._load_state(allow_trailing_orphan=True)
        except GateAuditError:
            raise
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit integrity verification failed") from exc

    def record(
        self,
        *,
        operation_id: str,
        phase: str,
        action: str,
        actor_id: str,
        actor_type: str | ActorType,
        purpose_digest: str,
        policy_id: str,
        policy_digest: str,
        lease_id: str,
        decision: str,
        protocol: str = "",
        destination: str = "",
        verifier_id: str = "",
        verifier_status: str = "",
        cost_class: str = "",
        revocation_reason: str = "",
        dissolution_reason: str = "",
        paired_live_id: str = "",
        arena_id: str = "",
        objective_id: str = "",
        evidence_refs: Iterable[str] = (),
        parent_event_id: str | None = None,
        created_at: float | None = None,
    ) -> dict[str, Any]:
        """Persist one Gate transition and return its canonical IDs.

        ``operation_id`` is the idempotency key.  Reuse with identical content
        returns the original IDs; reuse with different content fails closed.
        The API intentionally has no free-form payload or metadata parameter.
        """
        sidecar = self._build_sidecar(
            operation_id=operation_id,
            phase=phase,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            purpose_digest=purpose_digest,
            policy_id=policy_id,
            policy_digest=policy_digest,
            lease_id=lease_id,
            protocol=protocol,
            destination=destination,
            decision=decision,
            verifier_id=verifier_id,
            verifier_status=verifier_status,
            cost_class=cost_class,
            revocation_reason=revocation_reason,
            dissolution_reason=dissolution_reason,
            paired_live_id=paired_live_id,
            arena_id=arena_id,
            objective_id=objective_id,
            evidence_refs=evidence_refs,
        )
        operation_digest = stable_digest(sidecar)
        requested_parent = None
        if parent_event_id is not None:
            requested_parent = _safe_text(
                parent_event_id,
                "parent_event_id",
                required=bool(parent_event_id),
                limit=256,
            )
        timestamp = _finite_timestamp(created_at, self._clock)

        try:
            with _exclusive_lock(self.lock_path):
                state = self._load_state(allow_trailing_orphan=True)
                existing = state.event_by_operation.get(sidecar["operation_id"])
                if existing is not None:
                    persisted_parent = existing.parent_event_ids[0] if existing.parent_event_ids else ""
                    if requested_parent is not None and requested_parent != persisted_parent:
                        raise _fail(
                            "AURA_GATE_AUDIT_OPERATION_COLLISION",
                            "gate audit operation_id was reused with different content",
                        )
                    persisted_sidecar = state.sidecar_by_operation[sidecar["operation_id"]]
                    if stable_digest(persisted_sidecar) != operation_digest:
                        raise _fail(
                            "AURA_GATE_AUDIT_OPERATION_COLLISION",
                            "gate audit operation_id was reused with different content",
                        )
                    existing_row = state.row_by_operation.get(sidecar["operation_id"])
                    if existing_row is None:
                        if state.orphan_operation_id != sidecar["operation_id"]:
                            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit receipt continuity failed")
                        row = self._append_receipt_for_event(
                            event=existing,
                            operation_id=sidecar["operation_id"],
                            operation_digest=operation_digest,
                            rows=state.rows,
                            created_at=timestamp,
                        )
                        self._load_state(allow_trailing_orphan=False)
                        return self._result(existing, row, recovered=True)
                    return self._result(existing, existing_row, recovered=False)

                if state.orphan_operation_id:
                    raise _fail(
                        "AURA_GATE_AUDIT_INCOMPLETE",
                        "a prior gate audit operation requires receipt recovery",
                    )
                expected_parent = state.events[-1].event_id if state.events else ""
                if requested_parent is not None and requested_parent != expected_parent:
                    raise _fail("AURA_GATE_AUDIT_PARENT_MISMATCH", "gate audit parent continuity failed")

                payload_ref = self._store.store_payload(
                    sidecar,
                    kind=_SIDECAR_KIND,
                    created_at=timestamp,
                )
                event = AuraEventEnvelope.create(
                    trace_id=f"gate:{sidecar['operation_id']}",
                    parent_event_ids=(expected_parent,) if expected_parent else (),
                    event_type=f"AURA_GATE_{sidecar['phase']}_{sidecar['action']}",
                    actor_id=sidecar["actor_id"],
                    actor_type=sidecar["actor_type"],
                    arena_id=sidecar["arena_id"],
                    objective_id=sidecar["objective_id"],
                    purpose_digest=sidecar["purpose_digest"],
                    dikwp_stage=(DIKWPStage.PURPOSE if sidecar["phase"] == "PRE_ACTION" else DIKWPStage.WISDOM),
                    payload_ref=payload_ref.ref_id,
                    payload_digest=payload_ref.payload_digest,
                    evidence_refs=sidecar["evidence_refs"],
                    policy_scope=sidecar["policy_id"],
                    proposal_only=False,
                    created_at=timestamp,
                )
                if not self._store.append(event):
                    raise _fail("AURA_GATE_AUDIT_EVENT_COLLISION", "canonical gate audit event collision")
                row = self._append_receipt_for_event(
                    event=event,
                    operation_id=sidecar["operation_id"],
                    operation_digest=operation_digest,
                    rows=state.rows,
                    created_at=timestamp,
                )
                self._load_state(allow_trailing_orphan=False)
                return self._result(event, row, recovered=False)
        except GateAuditError:
            raise
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _fail("AURA_GATE_AUDIT_PERSISTENCE", "gate audit persistence failed") from exc

    def verify(self) -> dict[str, Any]:
        """Re-read and verify all canonical events, sidecars, and receipts."""
        try:
            with _exclusive_lock(self.lock_path):
                state = self._load_state(allow_trailing_orphan=False)
        except GateAuditError:
            raise
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit integrity verification failed") from exc
        return {
            "valid": True,
            "ledger_id": self.ledger_id,
            "event_count": len(state.events),
            "receipt_count": len(state.rows),
            "final_event_id": state.events[-1].event_id if state.events else "",
            "final_receipt_id": state.rows[-1].receipt.receipt_id if state.rows else "",
            "final_chain_digest": (state.rows[-1].receipt.chain_digest if state.rows else GENESIS_CHAIN_DIGEST),
        }

    def require_authority_issuance(
        self,
        *,
        operation_id: str,
        actor_id: str,
        purpose_digest: str,
        policy_id: str,
        policy_digest: str,
        lease_id: str,
        protocol: str,
        destination: str,
        verifier_id: str,
        arena_id: str,
        objective_id: str,
        evidence_refs: Iterable[str],
    ) -> dict[str, Any]:
        """Require an exact, already-persisted issuance before lease use.

        This is intentionally a read-only check. It must never synthesize a
        missing issuance from mutable operational lease state.
        """

        expected = self._build_sidecar(
            operation_id=operation_id,
            phase="PRE_ACTION",
            action="LEASE_ISSUE",
            actor_id=actor_id,
            actor_type=ActorType.HUMAN,
            purpose_digest=purpose_digest,
            policy_id=policy_id,
            policy_digest=policy_digest,
            lease_id=lease_id,
            protocol=protocol,
            destination=destination,
            decision="ALLOW",
            verifier_id=verifier_id,
            verifier_status="REQUIRED" if verifier_id else "",
            cost_class="BOUNDED",
            revocation_reason="",
            dissolution_reason="",
            paired_live_id="",
            arena_id=arena_id,
            objective_id=objective_id,
            evidence_refs=evidence_refs,
        )
        try:
            with _exclusive_lock(self.lock_path):
                state = self._load_state(allow_trailing_orphan=False)
                persisted = state.sidecar_by_operation.get(expected["operation_id"])
                row = state.row_by_operation.get(expected["operation_id"])
                event = state.event_by_operation.get(expected["operation_id"])
                if (
                    persisted is None
                    or row is None
                    or event is None
                    or stable_digest(persisted) != stable_digest(expected)
                ):
                    raise _fail(
                        "AURA_GATE_AUDIT_AUTHORITY_BINDING",
                        "gate authority issuance is missing or mismatched",
                    )
                return self._result(event, row, recovered=False)
        except GateAuditError:
            raise
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _fail(
                "AURA_GATE_AUDIT_INTEGRITY",
                "gate audit integrity verification failed",
            ) from exc

    def export_siem(self, output_path: str | Path) -> dict[str, Any]:
        """Write a deterministic, read-only SIEM projection of verified records."""
        destination = Path(output_path).resolve()
        if destination == self.export_root or self.export_root not in destination.parents:
            raise _fail(
                "AURA_GATE_AUDIT_INVALID_INPUT",
                "SIEM export must stay inside the configured export root",
            )
        try:
            with _exclusive_lock(self.lock_path):
                state = self._load_state(allow_trailing_orphan=False)
                rows = []
                for event, sidecar, receipt_row in zip(state.events, state.sidecars, state.rows, strict=True):
                    rows.append(self._siem_row(event, sidecar, receipt_row))
                encoded = "".join(f"{canonical_json(row)}\n" for row in rows)
            self._atomic_create(destination, encoded.encode("utf-8"))
        except GateAuditError:
            raise
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise _fail("AURA_GATE_AUDIT_EXPORT", "gate audit SIEM export failed") from exc
        return {
            "schema_version": SIEM_EVENT_VERSION,
            "event_count": len(rows),
            "digest": stable_digest(rows),
            "output_path": str(destination),
        }

    def _build_sidecar(
        self,
        *,
        operation_id: str,
        phase: str,
        action: str,
        actor_id: str,
        actor_type: str | ActorType,
        purpose_digest: str,
        policy_id: str,
        policy_digest: str,
        lease_id: str,
        protocol: str,
        destination: str,
        decision: str,
        verifier_id: str,
        verifier_status: str,
        cost_class: str,
        revocation_reason: str,
        dissolution_reason: str,
        paired_live_id: str,
        arena_id: str,
        objective_id: str,
        evidence_refs: Iterable[str],
    ) -> dict[str, Any]:
        actor_type_value = actor_type.value if isinstance(actor_type, ActorType) else actor_type
        actor_type_value = _safe_text(actor_type_value, "actor_type", required=True, limit=32, token=True).upper()
        if actor_type_value not in _ACTOR_TYPES:
            raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: actor_type")
        phase_value = _safe_text(phase, "phase", required=True, limit=32, token=True).upper()
        if phase_value not in _PHASES:
            raise _fail("AURA_GATE_AUDIT_INVALID_INPUT", "invalid gate audit field: phase")
        sidecar = {
            "schema_version": GATE_AUDIT_VERSION,
            "operation_id": _safe_text(operation_id, "operation_id", required=True, limit=128),
            "phase": phase_value,
            "action": _safe_text(action, "action", required=True, limit=64, token=True).upper(),
            "actor_id": _safe_text(actor_id, "actor_id", required=True, limit=256),
            "actor_type": actor_type_value,
            "purpose_digest": _safe_text(purpose_digest, "purpose_digest", required=True, limit=256),
            "policy_id": _safe_text(policy_id, "policy_id", required=True, limit=256),
            "policy_digest": _safe_text(policy_digest, "policy_digest", required=True, limit=256),
            "lease_id": _safe_text(lease_id, "lease_id", required=True, limit=256),
            "protocol": _safe_text(protocol, "protocol", required=False, limit=64, token=True).upper(),
            "destination": _safe_destination(destination),
            "decision": _safe_text(decision, "decision", required=True, limit=64, token=True).upper(),
            "verifier_id": _safe_text(verifier_id, "verifier_id", required=False, limit=256),
            "verifier_status": _safe_text(
                verifier_status, "verifier_status", required=False, limit=64, token=True
            ).upper(),
            "cost_class": _safe_text(cost_class, "cost_class", required=False, limit=64, token=True).upper(),
            "revocation_reason": _safe_reason(revocation_reason, "revocation_reason"),
            "dissolution_reason": _safe_reason(dissolution_reason, "dissolution_reason"),
            "paired_live_id": _safe_text(paired_live_id, "paired_live_id", required=False, limit=256),
            "arena_id": _safe_text(arena_id, "arena_id", required=False, limit=256),
            "objective_id": _safe_text(objective_id, "objective_id", required=False, limit=256),
            "evidence_refs": list(_safe_refs(evidence_refs)),
        }
        if frozenset(sidecar) != _SIDECAR_FIELDS:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "invalid gate audit sidecar shape")
        try:
            sanitized = sanitize_payload(sidecar)
        except ValueError as exc:
            raise _fail("AURA_GATE_AUDIT_SENSITIVE_VALUE", "sensitive gate audit value rejected") from exc
        if sanitized != sidecar:
            raise _fail("AURA_GATE_AUDIT_SENSITIVE_VALUE", "sensitive gate audit value rejected")
        return sidecar

    def _append_receipt_for_event(
        self,
        *,
        event: AuraEventEnvelope,
        operation_id: str,
        operation_digest: str,
        rows: tuple[_ReceiptRow, ...],
        created_at: float,
    ) -> _ReceiptRow:
        event_digest = stable_digest(event.to_dict())
        previous = rows[-1].receipt.chain_digest if rows else GENESIS_CHAIN_DIGEST
        receipt = ChainedAuthorityReceipt.create(
            ledger_id=self.ledger_id,
            sequence_number=len(rows) + 1,
            previous_chain_digest=previous,
            record_id=event.event_id,
            record_digest=event_digest,
            created_at=created_at,
        )
        row = _ReceiptRow(
            operation_id=operation_id,
            operation_digest=operation_digest,
            event_id=event.event_id,
            event_digest=event_digest,
            receipt=receipt,
        )
        self._append_receipt_row(self._receipt_row_to_dict(row))
        return row

    def _append_receipt_row(self, row: Mapping[str, Any]) -> None:
        """Append and fsync one row; kept narrow for fault-injection tests."""
        encoded = (canonical_json(dict(row)) + "\n").encode("utf-8")
        self.root.mkdir(parents=True, exist_ok=True)
        mode = "r+b" if self.receipts_path.exists() else "w+b"
        with self.receipts_path.open(mode) as handle:
            handle.seek(0, os.SEEK_END)
            original_size = handle.tell()
            try:
                written = handle.write(encoded)
                if written != len(encoded):
                    raise OSError("short gate audit receipt write")
                handle.flush()
                os.fsync(handle.fileno())
            except (OSError, ValueError):
                handle.seek(original_size)
                handle.truncate()
                handle.flush()
                os.fsync(handle.fileno())
                raise

    def _load_state(self, *, allow_trailing_orphan: bool) -> _LedgerState:
        events, sidecars = self._load_events_and_sidecars()
        rows = self._load_receipt_rows()

        event_ids = [event.event_id for event in events]
        if len(event_ids) != len(set(event_ids)):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "duplicate canonical gate audit event")
        operation_ids = [sidecar["operation_id"] for sidecar in sidecars]
        if len(operation_ids) != len(set(operation_ids)):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "duplicate gate audit operation_id")
        row_operations = [row.operation_id for row in rows]
        if len(row_operations) != len(set(row_operations)):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "duplicate gate audit receipt operation_id")

        for index, event in enumerate(events):
            expected_parents = () if index == 0 else (events[index - 1].event_id,)
            if event.parent_event_ids != expected_parents:
                raise _fail("AURA_GATE_AUDIT_INTEGRITY", "canonical event parent continuity failed")

        if len(rows) > len(events):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit receipt has no canonical event")
        paired_count = min(len(rows), len(events))
        for index in range(paired_count):
            event = events[index]
            sidecar = sidecars[index]
            row = rows[index]
            if (
                row.event_id != event.event_id
                or row.receipt.record_id != event.event_id
                or row.operation_id != sidecar["operation_id"]
                or row.operation_digest != stable_digest(sidecar)
                or row.event_digest != stable_digest(event.to_dict())
                or row.receipt.record_digest != row.event_digest
            ):
                raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit event-receipt identity failed")

        orphan_operation_id = ""
        if len(events) != len(rows):
            if len(events) == len(rows) + 1:
                orphan_operation_id = sidecars[-1]["operation_id"]
                if not allow_trailing_orphan:
                    raise _fail("AURA_GATE_AUDIT_INCOMPLETE", "trailing gate audit event lacks a receipt")
            else:
                raise _fail("AURA_GATE_AUDIT_INTEGRITY", "deleted or missing gate audit receipt")

        record_digests = {event.event_id: stable_digest(event.to_dict()) for event in events}
        verification = verify_receipt_chain(
            (row.receipt for row in rows),
            record_digests=record_digests,
        )
        if not verification.valid or (rows and verification.ledger_id != self.ledger_id):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit receipt chain verification failed")

        return _LedgerState(
            events=events,
            sidecars=sidecars,
            rows=rows,
            event_by_operation={
                sidecar["operation_id"]: event for event, sidecar in zip(events, sidecars, strict=True)
            },
            sidecar_by_operation={sidecar["operation_id"]: sidecar for sidecar in sidecars},
            row_by_operation={row.operation_id: row for row in rows},
            orphan_operation_id=orphan_operation_id,
        )

    def _load_events_and_sidecars(
        self,
    ) -> tuple[tuple[AuraEventEnvelope, ...], tuple[dict[str, Any], ...]]:
        if not self._store.events_path.exists():
            return (), ()
        events: list[AuraEventEnvelope] = []
        sidecars: list[dict[str, Any]] = []
        with self._store.events_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                encoded = line.rstrip("\n")
                if not encoded:
                    continue
                if line != encoded + "\n":
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "non-canonical gate audit event row")
                raw = json.loads(encoded)
                _exact_mapping(raw, _EVENT_FIELDS, "gate audit event")
                if canonical_json(raw) != encoded:
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "non-canonical gate audit event row")
                event = self._validated_event(raw)
                sidecar = self._load_sidecar(event)
                self._validate_event_sidecar_binding(event, sidecar)
                events.append(event)
                sidecars.append(sidecar)
        return tuple(events), tuple(sidecars)

    def _validated_event(self, raw: dict[str, Any]) -> AuraEventEnvelope:
        if (
            not isinstance(raw.get("parent_event_ids"), list)
            or not isinstance(raw.get("evidence_refs"), list)
            or not isinstance(raw.get("measurement_classes"), dict)
            or isinstance(raw.get("created_at"), bool)
            or not isinstance(raw.get("created_at"), (int, float))
            or not math.isfinite(float(raw["created_at"]))
        ):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "invalid canonical gate audit event")
        expected = AuraEventEnvelope.create(
            trace_id=raw["trace_id"],
            parent_event_ids=raw["parent_event_ids"],
            event_type=raw["event_type"],
            actor_id=raw["actor_id"],
            actor_type=raw["actor_type"],
            arena_id=raw["arena_id"],
            board_id=raw["board_id"],
            node_id=raw["node_id"],
            objective_id=raw["objective_id"],
            purpose_digest=raw["purpose_digest"],
            dikwp_stage=raw["dikwp_stage"],
            payload_ref=raw["payload_ref"],
            payload_digest=raw["payload_digest"],
            evidence_refs=raw["evidence_refs"],
            policy_scope=raw["policy_scope"],
            proposal_only=raw["proposal_only"],
            measurement_classes=raw["measurement_classes"],
            confidence=raw["confidence"],
            uncertainty=raw["uncertainty"],
            created_at=raw["created_at"],
        )
        if expected.to_dict() != raw:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "modified canonical gate audit event")
        return expected

    def _load_sidecar(self, event: AuraEventEnvelope) -> dict[str, Any]:
        if not _SAFE_ID.fullmatch(event.payload_ref):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "invalid gate audit sidecar reference")
        path = self._store.sidecars_dir / f"{event.payload_ref}.json"
        try:
            encoded = path.read_bytes()
            text = encoded.decode("utf-8")
            raw = json.loads(text)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "missing or invalid gate audit sidecar") from exc
        sidecar = _exact_mapping(raw, _SIDECAR_FIELDS, "gate audit sidecar")
        if canonical_json(sidecar).encode("utf-8") != encoded:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "non-canonical gate audit sidecar")
        if sanitize_payload(sidecar) != sidecar:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "unsafe gate audit sidecar")
        digest = stable_digest(sidecar)
        expected_ref = stable_id("payload", {"kind": _SIDECAR_KIND, "digest": digest})
        if digest != event.payload_digest or expected_ref != event.payload_ref:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "modified gate audit sidecar")
        rebuilt = self._build_sidecar(
            operation_id=sidecar["operation_id"],
            phase=sidecar["phase"],
            action=sidecar["action"],
            actor_id=sidecar["actor_id"],
            actor_type=sidecar["actor_type"],
            purpose_digest=sidecar["purpose_digest"],
            policy_id=sidecar["policy_id"],
            policy_digest=sidecar["policy_digest"],
            lease_id=sidecar["lease_id"],
            protocol=sidecar["protocol"],
            destination=sidecar["destination"],
            decision=sidecar["decision"],
            verifier_id=sidecar["verifier_id"],
            verifier_status=sidecar["verifier_status"],
            cost_class=sidecar["cost_class"],
            revocation_reason=sidecar["revocation_reason"],
            dissolution_reason=sidecar["dissolution_reason"],
            paired_live_id=sidecar["paired_live_id"],
            arena_id=sidecar["arena_id"],
            objective_id=sidecar["objective_id"],
            evidence_refs=sidecar["evidence_refs"],
        )
        if rebuilt != sidecar:
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "invalid gate audit sidecar values")
        return sidecar

    def _validate_event_sidecar_binding(self, event: AuraEventEnvelope, sidecar: Mapping[str, Any]) -> None:
        expected_stage = "PURPOSE" if sidecar["phase"] == "PRE_ACTION" else "WISDOM"
        if (
            event.trace_id != f"gate:{sidecar['operation_id']}"
            or event.event_type != f"AURA_GATE_{sidecar['phase']}_{sidecar['action']}"
            or event.actor_id != sidecar["actor_id"]
            or event.actor_type != sidecar["actor_type"]
            or event.arena_id != sidecar["arena_id"]
            or event.board_id
            or event.node_id
            or event.objective_id != sidecar["objective_id"]
            or event.purpose_digest != sidecar["purpose_digest"]
            or event.dikwp_stage != expected_stage
            or event.evidence_refs != tuple(sidecar["evidence_refs"])
            or event.policy_scope != sidecar["policy_id"]
            or event.proposal_only
            or event.measurement_classes
            or event.confidence is not None
            or event.uncertainty is not None
        ):
            raise _fail("AURA_GATE_AUDIT_INTEGRITY", "canonical event-sidecar binding failed")

    def _load_receipt_rows(self) -> tuple[_ReceiptRow, ...]:
        if not self.receipts_path.exists():
            return ()
        rows: list[_ReceiptRow] = []
        with self.receipts_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                encoded = line.rstrip("\n")
                if not encoded:
                    continue
                if line != encoded + "\n":
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "incomplete gate audit receipt row")
                raw = json.loads(encoded)
                _exact_mapping(raw, _RECEIPT_ROW_FIELDS, "gate audit receipt row")
                if canonical_json(raw) != encoded or raw["schema_version"] != GATE_AUDIT_VERSION:
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "non-canonical gate audit receipt row")
                receipt_raw = _exact_mapping(raw["receipt"], _RECEIPT_FIELDS, "authority receipt")
                receipt = ChainedAuthorityReceipt(**receipt_raw)
                try:
                    receipt.validate_integrity()
                except (TypeError, ValueError) as exc:
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "modified gate audit receipt") from exc
                operation_id = _safe_text(raw["operation_id"], "operation_id", required=True, limit=128)
                for field_name in ("operation_digest", "event_id", "event_digest"):
                    _safe_text(raw[field_name], field_name, required=True, limit=256)
                if raw["event_id"] != receipt.record_id or raw["event_digest"] != receipt.record_digest:
                    raise _fail("AURA_GATE_AUDIT_INTEGRITY", "gate audit receipt identity failed")
                rows.append(
                    _ReceiptRow(
                        operation_id=operation_id,
                        operation_digest=raw["operation_digest"],
                        event_id=raw["event_id"],
                        event_digest=raw["event_digest"],
                        receipt=receipt,
                    )
                )
        return tuple(rows)

    @staticmethod
    def _receipt_row_to_dict(row: _ReceiptRow) -> dict[str, Any]:
        return {
            "schema_version": GATE_AUDIT_VERSION,
            "operation_id": row.operation_id,
            "operation_digest": row.operation_digest,
            "event_id": row.event_id,
            "event_digest": row.event_digest,
            "receipt": row.receipt.to_dict(),
        }

    @staticmethod
    def _result(event: AuraEventEnvelope, row: _ReceiptRow, *, recovered: bool) -> dict[str, Any]:
        return {
            "event_id": event.event_id,
            "receipt_id": row.receipt.receipt_id,
            "sequence_number": row.receipt.sequence_number,
            "operation_id": row.operation_id,
            "recovered": recovered,
        }

    @staticmethod
    def _siem_row(
        event: AuraEventEnvelope,
        sidecar: Mapping[str, Any],
        receipt_row: _ReceiptRow,
    ) -> dict[str, Any]:
        return {
            "schema_version": SIEM_EVENT_VERSION,
            "timestamp": event.created_at,
            "event_id": event.event_id,
            "receipt_id": receipt_row.receipt.receipt_id,
            "sequence_number": receipt_row.receipt.sequence_number,
            "operation_id": sidecar["operation_id"],
            "phase": sidecar["phase"],
            "action": sidecar["action"],
            "actor": {"id": sidecar["actor_id"], "type": sidecar["actor_type"]},
            "purpose": {"digest": sidecar["purpose_digest"]},
            "policy": {"id": sidecar["policy_id"], "digest": sidecar["policy_digest"]},
            "lease": {"id": sidecar["lease_id"]},
            "protocol": sidecar["protocol"],
            "destination": sidecar["destination"],
            "decision": sidecar["decision"],
            "verifier": {
                "id": sidecar["verifier_id"],
                "status": sidecar["verifier_status"],
            },
            "cost": {"class": sidecar["cost_class"]},
            "revocation": {"reason": sidecar["revocation_reason"]},
            "dissolution": {"reason": sidecar["dissolution_reason"]},
            "paired_live_id": sidecar["paired_live_id"],
            "arena_id": sidecar["arena_id"],
            "objective_id": sidecar["objective_id"],
        }

    @staticmethod
    def _atomic_create(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError:
            try:
                existing = path.read_bytes()
            except OSError as exc:
                raise _fail("AURA_GATE_AUDIT_EXPORT", "existing SIEM export is unreadable") from exc
            if existing != content:
                raise _fail("AURA_GATE_AUDIT_EXPORT", "SIEM export path already contains other data")


__all__ = [
    "GATE_AUDIT_VERSION",
    "SIEM_EVENT_VERSION",
    "GateAuditError",
    "GateAuditLedger",
]
