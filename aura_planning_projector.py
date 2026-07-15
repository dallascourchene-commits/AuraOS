"""Read-only reconstruction and integrity validation for planning event chains.

P3.2 consumes the append-only contracts emitted by P3.1 and reconstructs
Planning Board -> regression -> frontier histories. It verifies serialized
events, immutable sidecars, digest bindings, semantic metadata, and parent
relationships without writing, repairing, executing, or authorizing anything.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import json
from typing import Any

from aura_event_contracts import (
    AppendOnlyEventStore,
    AuraEventEnvelope,
    canonical_json,
    stable_digest,
    stable_id,
)
from aura_planning_events import PlanningEventKind

PLANNING_PROJECTOR_VERSION = "AURA_PLANNING_PROJECTOR_V1"


class ProjectionFindingCode(str, Enum):
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
    PAYLOAD_METADATA_MISMATCH = "PAYLOAD_METADATA_MISMATCH"
    BOARD_NOT_ROOT = "BOARD_NOT_ROOT"
    WRONG_PARENT_COUNT = "WRONG_PARENT_COUNT"
    MISSING_PARENT = "MISSING_PARENT"
    WRONG_PARENT_TYPE = "WRONG_PARENT_TYPE"
    BRANCHING_CHAIN = "BRANCHING_CHAIN"
    MISSING_REGRESSION_CHILD = "MISSING_REGRESSION_CHILD"
    MISSING_FRONTIER_CHILD = "MISSING_FRONTIER_CHILD"
    CHAIN_CONTEXT_MISMATCH = "CHAIN_CONTEXT_MISMATCH"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    REGRESSION_BOARD_DIGEST_MISMATCH = "REGRESSION_BOARD_DIGEST_MISMATCH"
    FRONTIER_BOARD_DIGEST_MISMATCH = "FRONTIER_BOARD_DIGEST_MISMATCH"
    FRONTIER_REGRESSION_DIGEST_MISMATCH = "FRONTIER_REGRESSION_DIGEST_MISMATCH"
    STATE_DIGEST_MISMATCH = "STATE_DIGEST_MISMATCH"


_EXPECTED_SIDECAR_KIND = {
    PlanningEventKind.BOARD_CREATED: "planning-board-v1",
    PlanningEventKind.REGRESSION_COMPLETED: "planning-regression-v1",
    PlanningEventKind.FRONTIER_COMPLETED: "planning-frontier-v1",
}

_EXPECTED_STAGE = {
    PlanningEventKind.BOARD_CREATED: "PURPOSE",
    PlanningEventKind.REGRESSION_COMPLETED: "KNOWLEDGE",
    PlanningEventKind.FRONTIER_COMPLETED: "WISDOM",
}

_EXPECTED_MEASUREMENTS = {
    PlanningEventKind.BOARD_CREATED: {},
    PlanningEventKind.REGRESSION_COMPLETED: {"explored_nodes": "DERIVED"},
    PlanningEventKind.FRONTIER_COMPLETED: {"candidate_convergence": "DERIVED"},
}

_PLANNING_TYPES = {item.value for item in PlanningEventKind}


class CanonicalRecord:
    def to_dict(self) -> dict[str, Any]:
        return json.loads(canonical_json(self))


def _required(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _strings(values: Sequence[Any], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be a sequence")
    normalized = tuple(_required(item, field_name) for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class ProjectionFinding(CanonicalRecord):
    code: ProjectionFindingCode | str
    message: str
    event_ids: tuple[str, ...] = ()
    blocking: bool = True

    def __post_init__(self) -> None:
        try:
            code = (
                self.code
                if isinstance(self.code, ProjectionFindingCode)
                else ProjectionFindingCode(str(self.code))
            )
        except ValueError as exc:
            raise ValueError(f"unknown projection finding code: {self.code}") from exc
        object.__setattr__(self, "code", code)
        object.__setattr__(
            self,
            "message",
            _required(self.message, "finding.message"),
        )
        object.__setattr__(
            self,
            "event_ids",
            _strings(self.event_ids, "finding.event_ids"),
        )
        if type(self.blocking) is not bool:
            raise ValueError("finding.blocking must be a boolean")


@dataclass(frozen=True)
class ProjectedPlanningEvent(CanonicalRecord):
    event_id: str
    kind: PlanningEventKind | str
    payload_ref: str
    payload_digest: str
    created_at: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "event_id",
            _required(self.event_id, "projected_event.event_id"),
        )
        try:
            kind = (
                self.kind
                if isinstance(self.kind, PlanningEventKind)
                else PlanningEventKind(str(self.kind))
            )
        except ValueError as exc:
            raise ValueError(
                f"unknown projected planning event kind: {self.kind}"
            ) from exc
        object.__setattr__(self, "kind", kind)
        object.__setattr__(
            self,
            "payload_ref",
            _required(self.payload_ref, "projected_event.payload_ref"),
        )
        object.__setattr__(
            self,
            "payload_digest",
            _required(self.payload_digest, "projected_event.payload_digest"),
        )
        timestamp = float(self.created_at)
        if timestamp != timestamp or timestamp in (float("inf"), float("-inf")):
            raise ValueError("projected_event.created_at must be finite")
        object.__setattr__(self, "created_at", timestamp)


@dataclass(frozen=True)
class PlanningHistoryChain(CanonicalRecord):
    chain_id: str
    trace_id: str
    board_id: str
    arena_id: str
    objective_id: str
    purpose_digest: str
    policy_scope: str
    board_event: ProjectedPlanningEvent
    regression_event: ProjectedPlanningEvent
    frontier_event: ProjectedPlanningEvent

    def __post_init__(self) -> None:
        for field_name in (
            "chain_id",
            "trace_id",
            "board_id",
            "arena_id",
            "objective_id",
            "purpose_digest",
            "policy_scope",
        ):
            object.__setattr__(
                self,
                field_name,
                _required(getattr(self, field_name), f"chain.{field_name}"),
            )
        expected = (
            (self.board_event, PlanningEventKind.BOARD_CREATED),
            (self.regression_event, PlanningEventKind.REGRESSION_COMPLETED),
            (self.frontier_event, PlanningEventKind.FRONTIER_COMPLETED),
        )
        for event, kind in expected:
            if not isinstance(event, ProjectedPlanningEvent) or event.kind != kind:
                raise ValueError(f"chain event does not match {kind.value}")


@dataclass(frozen=True)
class PlanningHistoryProjectionReport(CanonicalRecord):
    chains: tuple[PlanningHistoryChain, ...]
    findings: tuple[ProjectionFinding, ...]
    planning_event_count: int
    ignored_nonplanning_events: int
    version: str = PLANNING_PROJECTOR_VERSION

    def __post_init__(self) -> None:
        if isinstance(self.chains, (str, bytes, bytearray)):
            raise ValueError("projection chains must be a sequence")
        chains = tuple(self.chains)
        if not all(isinstance(item, PlanningHistoryChain) for item in chains):
            raise ValueError("projection chains contains an invalid value")
        chain_ids = [item.chain_id for item in chains]
        if len(chain_ids) != len(set(chain_ids)):
            raise ValueError("projection chains must have unique chain IDs")

        if isinstance(self.findings, (str, bytes, bytearray)):
            raise ValueError("projection findings must be a sequence")
        findings = tuple(self.findings)
        if not all(isinstance(item, ProjectionFinding) for item in findings):
            raise ValueError("projection findings contains an invalid value")

        for name in ("planning_event_count", "ignored_nonplanning_events"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.version != PLANNING_PROJECTOR_VERSION:
            raise ValueError(
                f"unsupported planning projector version: {self.version}"
            )

        object.__setattr__(self, "chains", chains)
        object.__setattr__(self, "findings", findings)

    @property
    def integrity_complete(self) -> bool:
        return not any(item.blocking for item in self.findings)

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        value = super().to_dict()
        value["integrity_complete"] = self.integrity_complete
        return value


@dataclass(frozen=True)
class _ValidatedEvent:
    envelope: AuraEventEnvelope
    kind: PlanningEventKind
    payload: Mapping[str, Any]


class _Collector:
    def __init__(self) -> None:
        self.findings: list[ProjectionFinding] = []
        self._keys: set[tuple[str, tuple[str, ...], str]] = set()

    def add(
        self,
        code: ProjectionFindingCode,
        message: str,
        event_ids: Sequence[str] = (),
    ) -> None:
        normalized_ids = tuple(
            sorted(
                {
                    str(item).strip()
                    for item in event_ids
                    if str(item).strip()
                }
            )
        )
        key = (code.value, normalized_ids, message)
        if key in self._keys:
            return
        self._keys.add(key)
        self.findings.append(ProjectionFinding(code, message, normalized_ids))


def _merge_findings(target: _Collector, source: _Collector) -> None:
    for finding in source.findings:
        target.add(finding.code, finding.message, finding.event_ids)


def _ordered_findings(collector: _Collector) -> tuple[ProjectionFinding, ...]:
    return tuple(
        sorted(
            collector.findings,
            key=lambda item: (item.code.value, item.event_ids, item.message),
        )
    )


def _report(
    collector: _Collector,
    *,
    chains: Sequence[PlanningHistoryChain] = (),
    planning_event_count: int = 0,
    ignored_nonplanning_events: int = 0,
) -> PlanningHistoryProjectionReport:
    return PlanningHistoryProjectionReport(
        chains=tuple(sorted(chains, key=lambda item: item.chain_id)),
        findings=_ordered_findings(collector),
        planning_event_count=planning_event_count,
        ignored_nonplanning_events=ignored_nonplanning_events,
    )


def _planning_kind(raw: Mapping[str, Any]) -> PlanningEventKind | None:
    event_type = raw.get("event_type")
    if not isinstance(event_type, str) or event_type not in _PLANNING_TYPES:
        return None
    return PlanningEventKind(event_type)


def _validate_envelope(
    raw: Mapping[str, Any],
    kind: PlanningEventKind,
    collector: _Collector,
) -> AuraEventEnvelope | None:
    event_id = str(raw.get("event_id") or "")
    parents = raw.get("parent_event_ids")
    evidence = raw.get("evidence_refs")
    if not isinstance(parents, list):
        collector.add(
            ProjectionFindingCode.INVALID_EVENT_RECORD,
            "parent_event_ids must be a JSON array",
            (event_id,),
        )
        return None
    if not isinstance(evidence, list):
        collector.add(
            ProjectionFindingCode.INVALID_EVENT_RECORD,
            "evidence_refs must be a JSON array",
            (event_id,),
        )
        return None
    if len(parents) != len(set(map(str, parents))):
        collector.add(
            ProjectionFindingCode.DUPLICATE_PARENT_REF,
            "planning event contains duplicate parent references",
            (event_id,),
        )
        return None
    if len(evidence) != len(set(map(str, evidence))):
        collector.add(
            ProjectionFindingCode.DUPLICATE_EVIDENCE_REF,
            "planning event contains duplicate evidence references",
            (event_id,),
        )
        return None

    try:
        expected = AuraEventEnvelope.create(
            trace_id=raw.get("trace_id"),
            parent_event_ids=parents,
            event_type=raw.get("event_type"),
            actor_id=raw.get("actor_id"),
            actor_type=raw.get("actor_type"),
            arena_id=raw.get("arena_id", ""),
            board_id=raw.get("board_id", ""),
            node_id=raw.get("node_id", ""),
            objective_id=raw.get("objective_id", ""),
            purpose_digest=raw.get("purpose_digest"),
            dikwp_stage=raw.get("dikwp_stage"),
            payload_ref=raw.get("payload_ref"),
            payload_digest=raw.get("payload_digest"),
            evidence_refs=evidence,
            policy_scope=raw.get("policy_scope", ""),
            proposal_only=raw.get("proposal_only"),
            measurement_classes=raw.get("measurement_classes"),
            confidence=raw.get("confidence"),
            uncertainty=raw.get("uncertainty"),
            created_at=raw.get("created_at"),
        )
    except (TypeError, ValueError) as exc:
        collector.add(
            ProjectionFindingCode.INVALID_EVENT_RECORD,
            f"planning event contract validation failed: {exc}",
            (event_id,),
        )
        return None

    if event_id != expected.event_id:
        collector.add(
            ProjectionFindingCode.EVENT_ID_MISMATCH,
            "serialized event_id does not match the canonical envelope",
            (event_id, expected.event_id),
        )
        return None

    try:
        serialized = canonical_json(raw)
    except (TypeError, ValueError) as exc:
        collector.add(
            ProjectionFindingCode.INVALID_EVENT_RECORD,
            f"serialized planning event is not canonicalizable: {exc}",
            (event_id,),
        )
        return None
    if serialized != canonical_json(expected.to_dict()):
        collector.add(
            ProjectionFindingCode.ENVELOPE_MISMATCH,
            "serialized event contains non-canonical or unexpected envelope fields",
            (event_id,),
        )
        return None

    if expected.proposal_only is not True:
        collector.add(
            ProjectionFindingCode.NON_PROPOSAL_EVENT,
            "planning history events must remain proposal_only",
            (event_id,),
        )
        return None
    if (
        expected.node_id != kind.value
        or expected.dikwp_stage != _EXPECTED_STAGE[kind]
        or expected.measurement_classes != _EXPECTED_MEASUREMENTS[kind]
    ):
        collector.add(
            ProjectionFindingCode.WRONG_EVENT_CONTRACT,
            "planning event stage, node, or measurement contract is invalid",
            (event_id,),
        )
        return None
    return expected


def _load_sidecar(
    store: AppendOnlyEventStore,
    envelope: AuraEventEnvelope,
    kind: PlanningEventKind,
    collector: _Collector,
) -> Mapping[str, Any] | None:
    ref_id = envelope.payload_ref
    try:
        sidecars_root = store.sidecars_dir.resolve()
        candidate = (sidecars_root / f"{ref_id}.json").resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        collector.add(
            ProjectionFindingCode.UNSAFE_PAYLOAD_REF,
            f"payload_ref cannot be resolved safely: {exc}",
            (envelope.event_id,),
        )
        return None

    if candidate.parent != sidecars_root or candidate.name != f"{ref_id}.json":
        collector.add(
            ProjectionFindingCode.UNSAFE_PAYLOAD_REF,
            "payload_ref escapes or does not resolve directly under the sidecar directory",
            (envelope.event_id,),
        )
        return None
    if not candidate.is_file():
        collector.add(
            ProjectionFindingCode.MISSING_SIDECAR,
            "planning event sidecar is missing",
            (envelope.event_id,),
        )
        return None

    try:
        text = candidate.read_text(encoding="utf-8")
        payload = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        collector.add(
            ProjectionFindingCode.MALFORMED_SIDECAR,
            f"planning sidecar cannot be decoded: {exc}",
            (envelope.event_id,),
        )
        return None
    if not isinstance(payload, Mapping):
        collector.add(
            ProjectionFindingCode.MALFORMED_SIDECAR,
            "planning sidecar root must be a JSON object",
            (envelope.event_id,),
        )
        return None

    try:
        canonical = canonical_json(payload)
    except (TypeError, ValueError) as exc:
        collector.add(
            ProjectionFindingCode.MALFORMED_SIDECAR,
            f"planning sidecar is not canonicalizable: {exc}",
            (envelope.event_id,),
        )
        return None
    if text != canonical:
        collector.add(
            ProjectionFindingCode.NONCANONICAL_SIDECAR,
            "planning sidecar bytes do not match canonical JSON",
            (envelope.event_id,),
        )
        return None

    digest = stable_digest(payload)
    if digest != envelope.payload_digest:
        collector.add(
            ProjectionFindingCode.PAYLOAD_DIGEST_MISMATCH,
            "planning sidecar digest does not match the event",
            (envelope.event_id,),
        )
        return None
    expected_ref = stable_id(
        "payload",
        {"kind": _EXPECTED_SIDECAR_KIND[kind], "digest": digest},
    )
    if ref_id != expected_ref:
        collector.add(
            ProjectionFindingCode.PAYLOAD_REF_MISMATCH,
            "planning payload_ref is not the canonical sidecar ID for its event type",
            (envelope.event_id,),
        )
        return None
    return payload


def _validate_payload_metadata(
    envelope: AuraEventEnvelope,
    kind: PlanningEventKind,
    payload: Mapping[str, Any],
    collector: _Collector,
) -> bool:
    if kind == PlanningEventKind.BOARD_CREATED:
        goal = payload.get("goal")
        matches = (
            payload.get("board_id") == envelope.board_id
            and payload.get("arena_id") == envelope.arena_id
            and payload.get("purpose_digest") == envelope.purpose_digest
            and isinstance(goal, Mapping)
            and goal.get("goal_id") == envelope.objective_id
        )
    else:
        matches = payload.get("board_id") == envelope.board_id
    if matches:
        return True
    collector.add(
        ProjectionFindingCode.PAYLOAD_METADATA_MISMATCH,
        "planning sidecar metadata does not match its event envelope",
        (envelope.event_id,),
    )
    return False


def _projected(event: _ValidatedEvent) -> ProjectedPlanningEvent:
    envelope = event.envelope
    return ProjectedPlanningEvent(
        event_id=envelope.event_id,
        kind=event.kind,
        payload_ref=envelope.payload_ref,
        payload_digest=envelope.payload_digest,
        created_at=envelope.created_at,
    )


def _context_mismatches(events: Sequence[_ValidatedEvent]) -> tuple[str, ...]:
    fields = (
        "trace_id",
        "board_id",
        "arena_id",
        "objective_id",
        "purpose_digest",
        "policy_scope",
    )
    return tuple(
        field
        for field in fields
        if len({getattr(item.envelope, field) for item in events}) != 1
    )


def _snapshot_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=True,
    )


def _parse_serialized_event_log(
    raw_bytes: bytes,
    collector: _Collector,
) -> tuple[Mapping[str, Any], ...] | None:
    if not raw_bytes:
        return ()

    rows: list[Mapping[str, Any]] = []
    for row_number, raw_line in enumerate(raw_bytes.splitlines(keepends=True), 1):
        if not raw_line.strip():
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {row_number} is blank",
            )
            return None

        terminated = raw_line.endswith(b"\n")
        row_bytes = raw_line[:-1] if terminated else raw_line
        try:
            row_text = row_bytes.decode("utf-8")
        except UnicodeError as exc:
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {row_number} is not valid UTF-8: {exc}",
            )
            return None
        try:
            raw = json.loads(row_text)
        except json.JSONDecodeError as exc:
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {row_number} is malformed JSON: {exc}",
            )
            return None
        if not isinstance(raw, Mapping):
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {row_number} is not a JSON object",
            )
            return None

        kind = _planning_kind(raw)
        if kind is not None:
            event_id = str(raw.get("event_id") or "")
            try:
                canonical = canonical_json(raw)
            except (TypeError, ValueError) as exc:
                collector.add(
                    ProjectionFindingCode.INVALID_EVENT_RECORD,
                    f"planning event row {row_number} is not canonicalizable: {exc}",
                    (event_id,),
                )
                return None
            if not terminated or row_text != canonical:
                collector.add(
                    ProjectionFindingCode.NONCANONICAL_EVENT_RECORD,
                    f"planning event row {row_number} bytes are not canonical JSONL",
                    (event_id,),
                )
                return None
        rows.append(raw)
    return tuple(rows)


def _read_raw_events(
    store: AppendOnlyEventStore,
    collector: _Collector,
) -> tuple[Mapping[str, Any], ...] | None:
    for attempt in range(2):
        local = _Collector()
        try:
            locked_rows = tuple(store.iter_events())
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            if attempt == 0:
                continue
            try:
                raw_bytes = (
                    store.events_path.read_bytes()
                    if store.events_path.exists()
                    else b""
                )
            except OSError as read_exc:
                local.add(
                    ProjectionFindingCode.EVENT_LOG_READ_FAILED,
                    f"append-only event log cannot be read: {read_exc}",
                )
            else:
                _parse_serialized_event_log(raw_bytes, local)
                local.add(
                    ProjectionFindingCode.EVENT_LOG_READ_FAILED,
                    f"append-only event log cannot be decoded: {exc}",
                )
            _merge_findings(collector, local)
            return None

        try:
            raw_bytes = (
                store.events_path.read_bytes()
                if store.events_path.exists()
                else b""
            )
        except OSError as exc:
            if attempt == 0:
                continue
            collector.add(
                ProjectionFindingCode.EVENT_LOG_READ_FAILED,
                f"append-only event log cannot be read: {exc}",
            )
            return None

        serialized_rows = _parse_serialized_event_log(raw_bytes, local)
        if serialized_rows is None:
            if attempt == 0:
                continue
            _merge_findings(collector, local)
            return None
        if _snapshot_json(serialized_rows) == _snapshot_json(locked_rows):
            return serialized_rows
        if attempt == 0:
            continue
        collector.add(
            ProjectionFindingCode.EVENT_LOG_READ_FAILED,
            "append-only event log changed while its read-only snapshot was verified",
        )
        return None
    return None


def _exclude_duplicate_event_ids(
    planning_rows: Sequence[tuple[int, Mapping[str, Any], PlanningEventKind]],
    collector: _Collector,
) -> set[str]:
    occurrences: dict[
        str,
        list[tuple[int, Mapping[str, Any], PlanningEventKind]],
    ] = {}
    for row in planning_rows:
        event_id = str(row[1].get("event_id") or "")
        occurrences.setdefault(event_id, []).append(row)

    excluded: set[str] = set()
    for event_id, rows in occurrences.items():
        if len(rows) < 2:
            continue
        digests: set[str] = set()
        digest_failed = False
        for _index, raw, _kind in rows:
            try:
                digests.add(stable_digest(raw))
            except (TypeError, ValueError) as exc:
                collector.add(
                    ProjectionFindingCode.INVALID_EVENT_RECORD,
                    f"duplicate planning event is not canonicalizable: {exc}",
                    (event_id,),
                )
                digest_failed = True
        if digest_failed:
            excluded.add(event_id)
            continue
        code = (
            ProjectionFindingCode.CONFLICTING_DUPLICATE_EVENT
            if len(digests) > 1
            else ProjectionFindingCode.DUPLICATE_EVENT_ID
        )
        collector.add(
            code,
            "planning event ID occurs more than once in the append-only log",
            (event_id,),
        )
        excluded.add(event_id)
    return excluded


def project_planning_history(
    store: AppendOnlyEventStore,
) -> PlanningHistoryProjectionReport:
    """Read and verify planning histories without mutating the event store."""

    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")

    collector = _Collector()
    raw_events = _read_raw_events(store, collector)
    if raw_events is None:
        return _report(collector)

    planning_rows: list[tuple[int, Mapping[str, Any], PlanningEventKind]] = []
    ignored = 0
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, Mapping):
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {index} is not a JSON object",
            )
            continue
        event_type = raw.get("event_type")
        if event_type is not None and not isinstance(event_type, str):
            collector.add(
                ProjectionFindingCode.INVALID_EVENT_RECORD,
                f"event row {index} has a non-string event_type",
                (str(raw.get("event_id") or ""),),
            )
            continue
        kind = _planning_kind(raw)
        if kind is None:
            ignored += 1
            continue
        planning_rows.append((index, raw, kind))

    excluded_duplicate_ids = _exclude_duplicate_event_ids(
        planning_rows,
        collector,
    )

    valid: dict[str, _ValidatedEvent] = {}
    for _index, raw, kind in planning_rows:
        raw_event_id = str(raw.get("event_id") or "")
        if raw_event_id in excluded_duplicate_ids:
            continue
        envelope = _validate_envelope(raw, kind, collector)
        if envelope is None:
            continue
        payload = _load_sidecar(store, envelope, kind, collector)
        if payload is None:
            continue
        if not _validate_payload_metadata(envelope, kind, payload, collector):
            continue
        valid[envelope.event_id] = _ValidatedEvent(envelope, kind, payload)

    boards = tuple(
        sorted(
            (
                item
                for item in valid.values()
                if item.kind == PlanningEventKind.BOARD_CREATED
            ),
            key=lambda item: item.envelope.event_id,
        )
    )
    regressions = tuple(
        item
        for item in valid.values()
        if item.kind == PlanningEventKind.REGRESSION_COMPLETED
    )
    frontiers = tuple(
        item
        for item in valid.values()
        if item.kind == PlanningEventKind.FRONTIER_COMPLETED
    )

    regression_children: dict[str, list[_ValidatedEvent]] = {}
    frontier_children: dict[str, list[_ValidatedEvent]] = {}

    for board in boards:
        if board.envelope.parent_event_ids:
            collector.add(
                ProjectionFindingCode.BOARD_NOT_ROOT,
                "planning board event must be a root event",
                (board.envelope.event_id,),
            )

    parent_contracts = (
        *((item, PlanningEventKind.BOARD_CREATED, regression_children) for item in regressions),
        *((item, PlanningEventKind.REGRESSION_COMPLETED, frontier_children) for item in frontiers),
    )
    for event, expected_parent_kind, target in parent_contracts:
        parents = event.envelope.parent_event_ids
        if len(parents) != 1:
            collector.add(
                ProjectionFindingCode.WRONG_PARENT_COUNT,
                f"{event.kind.value} requires exactly one parent",
                (event.envelope.event_id, *parents),
            )
            continue
        parent_id = parents[0]
        parent = valid.get(parent_id)
        if parent is None:
            collector.add(
                ProjectionFindingCode.MISSING_PARENT,
                "planning event parent is missing or invalid",
                (event.envelope.event_id, parent_id),
            )
            continue
        if parent.kind != expected_parent_kind:
            collector.add(
                ProjectionFindingCode.WRONG_PARENT_TYPE,
                f"{event.kind.value} parent must be {expected_parent_kind.value}",
                (event.envelope.event_id, parent_id),
            )
            continue
        target.setdefault(parent_id, []).append(event)

    chains: list[PlanningHistoryChain] = []
    for board in boards:
        board_event_id = board.envelope.event_id
        if board.envelope.parent_event_ids:
            continue

        board_regressions = sorted(
            regression_children.get(board_event_id, []),
            key=lambda item: item.envelope.event_id,
        )
        if not board_regressions:
            collector.add(
                ProjectionFindingCode.MISSING_REGRESSION_CHILD,
                "planning board event has no regression child",
                (board_event_id,),
            )
            continue
        if len(board_regressions) > 1:
            collector.add(
                ProjectionFindingCode.BRANCHING_CHAIN,
                "planning board event has multiple regression children",
                (
                    board_event_id,
                    *(item.envelope.event_id for item in board_regressions),
                ),
            )
            continue

        regression = board_regressions[0]
        regression_event_id = regression.envelope.event_id
        regression_frontiers = sorted(
            frontier_children.get(regression_event_id, []),
            key=lambda item: item.envelope.event_id,
        )
        if not regression_frontiers:
            collector.add(
                ProjectionFindingCode.MISSING_FRONTIER_CHILD,
                "planning regression event has no frontier child",
                (regression_event_id,),
            )
            continue
        if len(regression_frontiers) > 1:
            collector.add(
                ProjectionFindingCode.BRANCHING_CHAIN,
                "planning regression event has multiple frontier children",
                (
                    regression_event_id,
                    *(item.envelope.event_id for item in regression_frontiers),
                ),
            )
            continue

        frontier = regression_frontiers[0]
        chain_events = (board, regression, frontier)
        chain_event_ids = tuple(
            item.envelope.event_id for item in chain_events
        )

        mismatches = _context_mismatches(chain_events)
        if mismatches:
            collector.add(
                ProjectionFindingCode.CHAIN_CONTEXT_MISMATCH,
                f"planning chain context differs across fields: {list(mismatches)}",
                chain_event_ids,
            )
            continue

        timestamps = tuple(
            item.envelope.created_at for item in chain_events
        )
        if timestamps != tuple(sorted(timestamps)):
            collector.add(
                ProjectionFindingCode.OUT_OF_ORDER,
                "planning chain timestamps are not board <= regression <= frontier",
                chain_event_ids,
            )
            continue

        board_digest = board.envelope.payload_digest
        if regression.payload.get("board_digest") != board_digest:
            collector.add(
                ProjectionFindingCode.REGRESSION_BOARD_DIGEST_MISMATCH,
                "regression sidecar is not bound to the board sidecar digest",
                (board_event_id, regression_event_id),
            )
            continue
        if frontier.payload.get("board_digest") != board_digest:
            collector.add(
                ProjectionFindingCode.FRONTIER_BOARD_DIGEST_MISMATCH,
                "frontier sidecar is not bound to the board sidecar digest",
                (board_event_id, frontier.envelope.event_id),
            )
            continue
        if (
            frontier.payload.get("regression_report_digest")
            != regression.envelope.payload_digest
        ):
            collector.add(
                ProjectionFindingCode.FRONTIER_REGRESSION_DIGEST_MISMATCH,
                "frontier sidecar is not bound to the regression sidecar digest",
                (regression_event_id, frontier.envelope.event_id),
            )
            continue
        if frontier.payload.get("state_digest") != regression.payload.get(
            "state_digest"
        ):
            collector.add(
                ProjectionFindingCode.STATE_DIGEST_MISMATCH,
                "regression and frontier sidecars disagree on initial state digest",
                (regression_event_id, frontier.envelope.event_id),
            )
            continue

        envelope = board.envelope
        chains.append(
            PlanningHistoryChain(
                chain_id=stable_id("planning-chain", chain_event_ids),
                trace_id=envelope.trace_id,
                board_id=envelope.board_id,
                arena_id=envelope.arena_id,
                objective_id=envelope.objective_id,
                purpose_digest=envelope.purpose_digest,
                policy_scope=envelope.policy_scope,
                board_event=_projected(board),
                regression_event=_projected(regression),
                frontier_event=_projected(frontier),
            )
        )

    return _report(
        collector,
        chains=chains,
        planning_event_count=len(planning_rows),
        ignored_nonplanning_events=ignored,
    )
