"""Read-only integrity projection for canonical QDKT observation events."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import json
import math
from pathlib import Path
from typing import Any

from aura_event_contracts import (
    AppendOnlyEventStore,
    AuraEventEnvelope,
    canonical_json,
    stable_digest,
    stable_id,
)
from aura_qdkt_events import (
    QDKT_EVENT_TYPE,
    QDKT_EVENT_VERSION,
    QDKT_POLICY_SCOPE,
    QDKT_SIDECAR_KIND,
    QDKTObservation,
)

QDKT_PROJECTOR_VERSION = "AURA_QDKT_PROJECTOR_P6_1"


class QDKTProjectionFindingCode(str, Enum):
    EVENT_LOG_READ_FAILED = "EVENT_LOG_READ_FAILED"
    INVALID_EVENT_RECORD = "INVALID_EVENT_RECORD"
    NONCANONICAL_EVENT_RECORD = "NONCANONICAL_EVENT_RECORD"
    EVENT_ID_MISMATCH = "EVENT_ID_MISMATCH"
    ENVELOPE_MISMATCH = "ENVELOPE_MISMATCH"
    DUPLICATE_EVENT_ID = "DUPLICATE_EVENT_ID"
    CONFLICTING_DUPLICATE_EVENT = "CONFLICTING_DUPLICATE_EVENT"
    DUPLICATE_PARENT_REF = "DUPLICATE_PARENT_REF"
    DUPLICATE_EVIDENCE_REF = "DUPLICATE_EVIDENCE_REF"
    NON_PROPOSAL_EVENT = "NON_PROPOSAL_EVENT"
    WRONG_EVENT_CONTRACT = "WRONG_EVENT_CONTRACT"
    UNSAFE_PAYLOAD_REF = "UNSAFE_PAYLOAD_REF"
    MISSING_SIDECAR = "MISSING_SIDECAR"
    MALFORMED_SIDECAR = "MALFORMED_SIDECAR"
    NONCANONICAL_SIDECAR = "NONCANONICAL_SIDECAR"
    PAYLOAD_DIGEST_MISMATCH = "PAYLOAD_DIGEST_MISMATCH"
    PAYLOAD_REF_MISMATCH = "PAYLOAD_REF_MISMATCH"
    OBSERVATION_ID_MISMATCH = "OBSERVATION_ID_MISMATCH"
    OBSERVATION_EVENT_MISMATCH = "OBSERVATION_EVENT_MISMATCH"
    MISSING_PARENT = "MISSING_PARENT"
    OUT_OF_ORDER = "OUT_OF_ORDER"


@dataclass(frozen=True)
class QDKTProjectionFinding:
    code: QDKTProjectionFindingCode | str
    message: str
    event_ids: tuple[str, ...] = ()
    blocking: bool = True

    def __post_init__(self) -> None:
        try:
            code = (
                self.code
                if isinstance(self.code, QDKTProjectionFindingCode)
                else QDKTProjectionFindingCode(str(self.code))
            )
        except ValueError as exc:
            raise ValueError("unknown QDKT projection finding code") from exc
        if type(self.message) is not str or not self.message.strip():
            raise ValueError("finding message must not be empty")
        if isinstance(self.event_ids, (str, bytes, bytearray)):
            raise ValueError("finding event_ids must be a sequence")
        ids = tuple(str(item).strip() for item in self.event_ids)
        if any(not item for item in ids) or len(ids) != len(set(ids)):
            raise ValueError("finding event_ids must be unique non-empty strings")
        if type(self.blocking) is not bool:
            raise ValueError("finding blocking must be a boolean")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "message", self.message.strip())
        object.__setattr__(self, "event_ids", ids)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["code"] = self.code.value
        value["event_ids"] = list(self.event_ids)
        return value


@dataclass(frozen=True)
class ProjectedQDKTEvent:
    event_id: str
    observation_id: str
    payload_ref: str
    payload_digest: str
    trace_id: str
    parent_event_ids: tuple[str, ...]
    created_at: float

    def __post_init__(self) -> None:
        for field_name in (
            "event_id",
            "observation_id",
            "payload_ref",
            "payload_digest",
            "trace_id",
        ):
            value = getattr(self, field_name)
            if type(value) is not str or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")
        if isinstance(self.parent_event_ids, (str, bytes, bytearray)):
            raise ValueError("parent_event_ids must be a sequence")
        parents = tuple(str(item).strip() for item in self.parent_event_ids)
        if any(not item for item in parents) or len(parents) != len(set(parents)):
            raise ValueError("parent_event_ids must be unique non-empty strings")
        timestamp = float(self.created_at)
        if not math.isfinite(timestamp):
            raise ValueError("created_at must be finite")
        object.__setattr__(self, "parent_event_ids", parents)
        object.__setattr__(self, "created_at", timestamp)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["parent_event_ids"] = list(self.parent_event_ids)
        return value


@dataclass(frozen=True)
class QDKTProjectionReport:
    events: tuple[ProjectedQDKTEvent, ...]
    findings: tuple[QDKTProjectionFinding, ...]
    qdkt_event_count: int
    ignored_non_qdkt_events: int
    version: str = QDKT_PROJECTOR_VERSION

    def __post_init__(self) -> None:
        if not all(isinstance(item, ProjectedQDKTEvent) for item in self.events):
            raise ValueError("events contains an invalid projected event")
        if not all(isinstance(item, QDKTProjectionFinding) for item in self.findings):
            raise ValueError("findings contains an invalid finding")
        ids = [item.event_id for item in self.events]
        if len(ids) != len(set(ids)):
            raise ValueError("projected events must have unique event IDs")
        for field_name in ("qdkt_event_count", "ignored_non_qdkt_events"):
            value = getattr(self, field_name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.version != QDKT_PROJECTOR_VERSION:
            raise ValueError("unsupported QDKT projector version")

    @property
    def integrity_complete(self) -> bool:
        return not any(item.blocking for item in self.findings)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [item.to_dict() for item in self.events],
            "findings": [item.to_dict() for item in self.findings],
            "qdkt_event_count": self.qdkt_event_count,
            "ignored_non_qdkt_events": self.ignored_non_qdkt_events,
            "version": self.version,
            "integrity_complete": self.integrity_complete,
        }


class _Collector:
    def __init__(self) -> None:
        self.findings: list[QDKTProjectionFinding] = []
        self._seen: set[tuple[str, tuple[str, ...], str]] = set()

    def add(
        self,
        code: QDKTProjectionFindingCode,
        message: str,
        event_ids: Sequence[str] = (),
    ) -> None:
        ids = tuple(sorted({str(item).strip() for item in event_ids if str(item).strip()}))
        key = (code.value, ids, message)
        if key not in self._seen:
            self._seen.add(key)
            self.findings.append(QDKTProjectionFinding(code, message, ids))


def _raw_records(store: AppendOnlyEventStore, collector: _Collector) -> list[tuple[int, dict[str, Any]]]:
    if not store.events_path.exists():
        return []
    try:
        data = store.events_path.read_bytes()
        text = data.decode("utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        collector.add(QDKTProjectionFindingCode.EVENT_LOG_READ_FAILED, f"event log read failed: {type(exc).__name__}")
        return []
    records: list[tuple[int, dict[str, Any]]] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except (TypeError, ValueError):
            collector.add(QDKTProjectionFindingCode.INVALID_EVENT_RECORD, f"event row {index} is not valid JSON")
            continue
        if not isinstance(value, dict):
            collector.add(QDKTProjectionFindingCode.INVALID_EVENT_RECORD, f"event row {index} must be an object")
            continue
        if line != canonical_json(value):
            collector.add(
                QDKTProjectionFindingCode.NONCANONICAL_EVENT_RECORD,
                f"event row {index} is not canonical JSON",
                (str(value.get("event_id") or ""),),
            )
        records.append((index, value))
    return records


def _rebuild_envelope(raw: Mapping[str, Any], collector: _Collector) -> AuraEventEnvelope | None:
    event_id = str(raw.get("event_id") or "")
    parents = raw.get("parent_event_ids")
    evidence = raw.get("evidence_refs")
    if not isinstance(parents, list) or not isinstance(evidence, list):
        collector.add(QDKTProjectionFindingCode.INVALID_EVENT_RECORD, "parent and evidence refs must be JSON arrays", (event_id,))
        return None
    if len(parents) != len(set(map(str, parents))):
        collector.add(QDKTProjectionFindingCode.DUPLICATE_PARENT_REF, "duplicate parent reference", (event_id,))
        return None
    if len(evidence) != len(set(map(str, evidence))):
        collector.add(QDKTProjectionFindingCode.DUPLICATE_EVIDENCE_REF, "duplicate evidence reference", (event_id,))
        return None
    try:
        expected = AuraEventEnvelope.create(
            trace_id=raw.get("trace_id"),
            parent_event_ids=parents,
            event_type=raw.get("event_type"),
            actor_id=raw.get("actor_id"),
            actor_type=raw.get("actor_type"),
            arena_id=raw.get("arena_id"),
            board_id=raw.get("board_id"),
            node_id=raw.get("node_id"),
            objective_id=raw.get("objective_id"),
            purpose_digest=raw.get("purpose_digest"),
            dikwp_stage=raw.get("dikwp_stage"),
            payload_ref=raw.get("payload_ref"),
            payload_digest=raw.get("payload_digest"),
            evidence_refs=evidence,
            policy_scope=raw.get("policy_scope"),
            proposal_only=raw.get("proposal_only"),
            measurement_classes=raw.get("measurement_classes"),
            confidence=raw.get("confidence"),
            uncertainty=raw.get("uncertainty"),
            created_at=raw.get("created_at"),
        )
    except Exception:
        collector.add(QDKTProjectionFindingCode.INVALID_EVENT_RECORD, "QDKT event envelope is invalid", (event_id,))
        return None
    if event_id != expected.event_id:
        collector.add(QDKTProjectionFindingCode.EVENT_ID_MISMATCH, "event ID does not match canonical envelope identity", (event_id,))
        return None
    if raw != expected.to_dict():
        collector.add(QDKTProjectionFindingCode.ENVELOPE_MISMATCH, "serialized event differs from canonical envelope", (event_id,))
        return None
    if expected.proposal_only is not True:
        collector.add(QDKTProjectionFindingCode.NON_PROPOSAL_EVENT, "QDKT event is not proposal-only", (event_id,))
        return None
    if (
        expected.event_type != QDKT_EVENT_TYPE
        or expected.dikwp_stage != "KNOWLEDGE"
        or expected.policy_scope != QDKT_POLICY_SCOPE
        or expected.measurement_classes != {"legacy_belief": "DERIVED"}
    ):
        collector.add(QDKTProjectionFindingCode.WRONG_EVENT_CONTRACT, "QDKT event contract metadata changed", (event_id,))
        return None
    return expected


def _load_observation(
    store: AppendOnlyEventStore,
    envelope: AuraEventEnvelope,
    collector: _Collector,
) -> QDKTObservation | None:
    event_id = envelope.event_id
    ref = envelope.payload_ref
    if not ref.startswith("payload_") or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in ref):
        collector.add(QDKTProjectionFindingCode.UNSAFE_PAYLOAD_REF, "QDKT payload ref is unsafe", (event_id,))
        return None
    path = (store.sidecars_dir / f"{ref}.json").resolve()
    try:
        path.relative_to(store.sidecars_dir.resolve())
    except ValueError:
        collector.add(QDKTProjectionFindingCode.UNSAFE_PAYLOAD_REF, "QDKT sidecar escapes the store", (event_id,))
        return None
    if not path.is_file():
        collector.add(QDKTProjectionFindingCode.MISSING_SIDECAR, "QDKT sidecar is missing", (event_id,))
        return None
    try:
        raw_bytes = path.read_bytes()
        text = raw_bytes.decode("utf-8", errors="strict")
        payload = json.loads(text)
    except (OSError, UnicodeError, ValueError):
        collector.add(QDKTProjectionFindingCode.MALFORMED_SIDECAR, "QDKT sidecar is malformed", (event_id,))
        return None
    if not isinstance(payload, dict):
        collector.add(QDKTProjectionFindingCode.MALFORMED_SIDECAR, "QDKT sidecar must be an object", (event_id,))
        return None
    if text != canonical_json(payload):
        collector.add(QDKTProjectionFindingCode.NONCANONICAL_SIDECAR, "QDKT sidecar is not canonical JSON", (event_id,))
        return None
    payload_digest = stable_digest(payload)
    if payload_digest != envelope.payload_digest:
        collector.add(QDKTProjectionFindingCode.PAYLOAD_DIGEST_MISMATCH, "QDKT sidecar digest differs from the event", (event_id,))
        return None
    expected_ref = stable_id("payload", {"kind": QDKT_SIDECAR_KIND, "digest": payload_digest})
    if ref != expected_ref:
        collector.add(QDKTProjectionFindingCode.PAYLOAD_REF_MISMATCH, "QDKT payload ref differs from the canonical sidecar identity", (event_id,))
        return None
    try:
        observation = QDKTObservation.from_dict(payload)
    except Exception:
        collector.add(QDKTProjectionFindingCode.MALFORMED_SIDECAR, "QDKT observation contract is invalid", (event_id,))
        return None
    if observation.digest != payload_digest:
        collector.add(QDKTProjectionFindingCode.OBSERVATION_ID_MISMATCH, "QDKT observation digest is inconsistent", (event_id,))
        return None
    if envelope.node_id != observation.observation_id:
        collector.add(QDKTProjectionFindingCode.OBSERVATION_EVENT_MISMATCH, "event node does not identify the QDKT observation", (event_id,))
        return None
    if envelope.board_id and observation.planning_board_ref and envelope.board_id != observation.planning_board_ref:
        collector.add(QDKTProjectionFindingCode.OBSERVATION_EVENT_MISMATCH, "event board does not match the observation planning reference", (event_id,))
        return None
    return observation


def project_qdkt_events(store: AppendOnlyEventStore) -> QDKTProjectionReport:
    """Verify QDKT events and sidecars without mutating the event store."""
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    collector = _Collector()
    records = _raw_records(store, collector)
    all_events: dict[str, tuple[int, float]] = {}
    raw_qdkt_count = 0
    ignored = 0
    digests: dict[str, str] = {}
    projected: list[ProjectedQDKTEvent] = []

    for index, raw in records:
        event_id = str(raw.get("event_id") or "")
        created = raw.get("created_at")
        if event_id and isinstance(created, (int, float)) and not isinstance(created, bool) and math.isfinite(float(created)):
            all_events.setdefault(event_id, (index, float(created)))
        if raw.get("event_type") != QDKT_EVENT_TYPE:
            ignored += 1
            continue
        raw_qdkt_count += 1
        raw_digest = stable_digest(raw)
        previous = digests.get(event_id)
        if previous is not None:
            code = (
                QDKTProjectionFindingCode.DUPLICATE_EVENT_ID
                if previous == raw_digest
                else QDKTProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT
            )
            collector.add(code, "duplicate QDKT event ID in the event log", (event_id,))
            continue
        digests[event_id] = raw_digest
        envelope = _rebuild_envelope(raw, collector)
        if envelope is None:
            continue
        observation = _load_observation(store, envelope, collector)
        if observation is None:
            continue
        projected.append(
            ProjectedQDKTEvent(
                event_id=envelope.event_id,
                observation_id=observation.observation_id,
                payload_ref=envelope.payload_ref,
                payload_digest=envelope.payload_digest,
                trace_id=envelope.trace_id,
                parent_event_ids=envelope.parent_event_ids,
                created_at=envelope.created_at,
            )
        )

    for event in projected:
        child_position = all_events.get(event.event_id)
        for parent_id in event.parent_event_ids:
            parent = all_events.get(parent_id)
            if parent is None:
                collector.add(QDKTProjectionFindingCode.MISSING_PARENT, "QDKT parent event is missing", (event.event_id, parent_id))
            elif child_position is not None and (
                parent[0] >= child_position[0] or parent[1] > event.created_at
            ):
                collector.add(QDKTProjectionFindingCode.OUT_OF_ORDER, "QDKT parent occurs after its child", (event.event_id, parent_id))

    findings = tuple(sorted(collector.findings, key=lambda item: (item.code.value, item.event_ids, item.message)))
    events = tuple(sorted(projected, key=lambda item: (item.created_at, item.event_id)))
    return QDKTProjectionReport(events, findings, raw_qdkt_count, ignored)


__all__ = [
    "ProjectedQDKTEvent",
    "QDKTProjectionFinding",
    "QDKTProjectionFindingCode",
    "QDKTProjectionReport",
    "project_qdkt_events",
]
