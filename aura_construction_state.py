"""Deterministic append-only state, supersession, conflict, and query projection.

Readiness in this module means evidence-ready for governed authority review. It
never means physical-work authorization or professional certification.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable

from aura_event_contracts import stable_digest
from aura_construction_contracts import (
    ConstructionClaim,
    ConstructionEvent,
    ConstructionEvidence,
    ConstructionEvidenceClass,
    ConstructionPrivacyClass,
    ConstructionRecordKind,
    GENESIS_CHAIN_DIGEST,
    PATCH_AUTHORITY,
    PROPOSAL_ONLY,
    VSA_PATCH_AUTHORITY,
)

CONSTRUCTION_STATE_VERSION = "AURA_CONSTRUCTION_STATE_V1"
_NON_DISPOSITIVE = frozenset(
    {ConstructionEvidenceClass.SENSOR.value, ConstructionEvidenceClass.LOCATION.value}
)
_PRIVACY_RANK = {
    ConstructionPrivacyClass.PUBLIC.value: 0,
    ConstructionPrivacyClass.PROJECT.value: 1,
    ConstructionPrivacyClass.RESTRICTED.value: 2,
    ConstructionPrivacyClass.SENSITIVE.value: 3,
}


def _digest(value: Any, name: str) -> str:
    if type(value) is not str or len(value) not in {32, 64}:
        raise ValueError(f"{name} must be a 32- or 64-character digest")
    normalized = value.lower()
    if any(ch not in "0123456789abcdef" for ch in normalized):
        raise ValueError(f"{name} must be hexadecimal")
    if value != normalized:
        raise ValueError(f"{name} must use canonical lowercase hexadecimal")
    return normalized


def _timestamp(value: Any, name: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _require_canonical_float(value: Any, name: str) -> None:
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{name} must be a canonical finite float")


def _sequence_input(value: Any, name: str) -> tuple[Any, ...]:
    if type(value) not in {list, tuple}:
        raise ValueError(f"{name} must be a list or tuple")
    return tuple(value)


def _tuple_strings(value: Any, name: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    normalized = tuple(" ".join(item.split()) if type(item) is str else item for item in value)
    if any(type(item) is not str or not item for item in normalized):
        raise ValueError(f"{name} contains an invalid value")
    if normalized != value:
        raise ValueError(f"{name} must contain canonical normalized strings")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    if normalized != tuple(sorted(normalized)):
        raise ValueError(f"{name} must use canonical sorted order")
    return normalized


@dataclass(frozen=True)
class ConstructionConflict:
    record_kind: str
    state_key: str
    active_event_ids: tuple[str, ...]
    record_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.record_kind not in {item.value for item in ConstructionRecordKind}:
            raise ValueError("conflict record_kind is invalid")
        if type(self.state_key) is not str or not self.state_key:
            raise ValueError("conflict state_key is required")
        _tuple_strings(self.active_event_ids, "conflict.active_event_ids")
        _tuple_strings(self.record_digests, "conflict.record_digests")
        if len(self.active_event_ids) < 2 or len(self.record_digests) < 2:
            raise ValueError("conflict requires at least two active events and digests")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionConflict":
        data = dict(value)
        return cls(
            record_kind=data.get("record_kind"),
            state_key=data.get("state_key"),
            active_event_ids=_sequence_input(
                data.get("active_event_ids", ()), "conflict.active_event_ids"
            ),
            record_digests=_sequence_input(
                data.get("record_digests", ()), "conflict.record_digests"
            ),
        )


def _reduce_events(
    events: tuple[ConstructionEvent, ...],
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[ConstructionConflict, ...]]:
    if not events:
        raise ValueError("at least one construction event is required")
    if not all(type(item) is ConstructionEvent for item in events):
        raise ValueError("all construction events must be exact ConstructionEvent values")

    project_id = events[0].project_id
    ledger_id = events[0].ledger_id
    seen: dict[str, ConstructionEvent] = {}
    active: set[str] = set()
    active_record_ids: dict[str, str] = {}
    superseded: set[str] = set()
    previous_chain = GENESIS_CHAIN_DIGEST
    previous_created_at = float("-inf")

    for expected_sequence, event in enumerate(events, start=1):
        event.__post_init__()
        if event.project_id != project_id:
            raise ValueError("construction ledger contains multiple projects")
        if event.ledger_id != ledger_id:
            raise ValueError("construction ledger contains multiple ledger IDs")
        if event.sequence_number != expected_sequence:
            raise ValueError(
                f"construction event sequence gap or reorder at {expected_sequence}"
            )
        if event.previous_chain_digest != previous_chain:
            raise ValueError(
                f"construction event previous digest mismatch at {expected_sequence}"
            )
        if event.created_at < previous_created_at:
            raise ValueError(
                f"construction event timestamp moved backward at {expected_sequence}"
            )
        if event.event_id in seen:
            raise ValueError(f"duplicate construction event ID: {event.event_id}")

        missing_parents = set(event.parent_event_ids).difference(seen)
        if missing_parents:
            raise ValueError(
                f"event references missing parent events: {sorted(missing_parents)}"
            )

        for target_id in event.supersedes_event_ids:
            target = seen.get(target_id)
            if target is None:
                raise ValueError(f"event supersedes missing event: {target_id}")
            if target_id not in active:
                raise ValueError(f"event supersedes an already inactive event: {target_id}")
            if target.record_kind != event.record_kind or target.state_key != event.state_key:
                raise ValueError("supersession must preserve record kind and state key")
            active.remove(target_id)
            superseded.add(target_id)
            active_record_ids.pop(target.record_id, None)

        prior_event_id = active_record_ids.get(event.record_id)
        if prior_event_id is not None:
            raise ValueError(
                f"duplicate active construction record without supersession: {event.record_id}"
            )

        seen[event.event_id] = event
        active.add(event.event_id)
        active_record_ids[event.record_id] = event.event_id
        previous_chain = event.chain_digest
        previous_created_at = event.created_at

    active_records = [event for event in events if event.event_id in active]
    groups: dict[tuple[str, str], list[ConstructionEvent]] = {}
    for event in active_records:
        groups.setdefault((event.record_kind, event.state_key), []).append(event)

    conflicts: list[ConstructionConflict] = []
    for (record_kind, state_key), group in sorted(groups.items()):
        digests = tuple(
            sorted(
                {
                    event.record.value_digest
                    if type(event.record) is ConstructionClaim
                    else event.record.payload_digest
                    for event in group
                }
            )
        )
        if len(digests) > 1:
            conflicts.append(
                ConstructionConflict(
                    record_kind=record_kind,
                    state_key=state_key,
                    active_event_ids=tuple(sorted(event.event_id for event in group)),
                    record_digests=digests,
                )
            )

    return (
        project_id,
        ledger_id,
        tuple(sorted(active)),
        tuple(sorted(superseded)),
        tuple(conflicts),
    )


def _state_payload(
    *,
    project_id: str,
    ledger_id: str,
    events: tuple[ConstructionEvent, ...],
    active_event_ids: tuple[str, ...],
    superseded_event_ids: tuple[str, ...],
    conflicts: tuple[ConstructionConflict, ...],
    final_chain_digest: str,
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "ledger_id": ledger_id,
        "events": [event.to_dict() for event in events],
        "active_event_ids": list(active_event_ids),
        "superseded_event_ids": list(superseded_event_ids),
        "conflicts": [item.to_dict() for item in conflicts],
        "final_chain_digest": final_chain_digest,
        "version": CONSTRUCTION_STATE_VERSION,
        "proposal_only": PROPOSAL_ONLY,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


@dataclass(frozen=True)
class ConstructionProjectState:
    project_id: str
    ledger_id: str
    events: tuple[ConstructionEvent, ...]
    active_event_ids: tuple[str, ...]
    superseded_event_ids: tuple[str, ...]
    conflicts: tuple[ConstructionConflict, ...]
    final_chain_digest: str
    state_digest: str
    version: str = CONSTRUCTION_STATE_VERSION
    proposal_only: bool = PROPOSAL_ONLY
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        if self.version != CONSTRUCTION_STATE_VERSION:
            raise ValueError("unsupported construction state version")
        if self.proposal_only is not True:
            raise ValueError("construction state must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or self.vsa_patch_authority is not False:
            raise ValueError("construction state authority boundary was modified")
        if type(self.events) is not tuple:
            raise ValueError("state events must be a tuple")
        projected = _reduce_events(self.events)
        expected_project, expected_ledger, expected_active, expected_superseded, expected_conflicts = projected
        if self.project_id != expected_project or self.ledger_id != expected_ledger:
            raise ValueError("state project or ledger does not match its event chain")
        if self.active_event_ids != expected_active:
            raise ValueError("state active-event projection does not match its event chain")
        if self.superseded_event_ids != expected_superseded:
            raise ValueError("state supersession projection does not match its event chain")
        if self.conflicts != expected_conflicts:
            raise ValueError("state conflict projection does not match its event chain")
        if self.final_chain_digest != self.events[-1].chain_digest:
            raise ValueError("state final chain digest does not match the final event")
        if self.state_digest != stable_digest(self._identity_payload()):
            raise ValueError("state digest does not match its content")

    def _identity_payload(self) -> dict[str, Any]:
        return _state_payload(
            project_id=self.project_id,
            ledger_id=self.ledger_id,
            events=self.events,
            active_event_ids=self.active_event_ids,
            superseded_event_ids=self.superseded_event_ids,
            conflicts=self.conflicts,
            final_chain_digest=self.final_chain_digest,
        )

    @property
    def events_by_id(self) -> dict[str, ConstructionEvent]:
        return {item.event_id: item for item in self.events}

    @property
    def active_events(self) -> tuple[ConstructionEvent, ...]:
        active = set(self.active_event_ids)
        return tuple(item for item in self.events if item.event_id in active)

    @property
    def active_claim_events(self) -> tuple[ConstructionEvent, ...]:
        return tuple(
            item
            for item in self.active_events
            if item.record_kind == ConstructionRecordKind.CLAIM.value
        )

    @property
    def active_evidence_events(self) -> tuple[ConstructionEvent, ...]:
        return tuple(
            item
            for item in self.active_events
            if item.record_kind == ConstructionRecordKind.EVIDENCE.value
        )

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionProjectState":
        data = dict(value)
        return cls(
            project_id=data.get("project_id"),
            ledger_id=data.get("ledger_id"),
            events=tuple(
                ConstructionEvent.from_dict(dict(item))
                for item in data.get("events", ())
            ),
            active_event_ids=_sequence_input(
                data.get("active_event_ids", ()), "state.active_event_ids"
            ),
            superseded_event_ids=_sequence_input(
                data.get("superseded_event_ids", ()), "state.superseded_event_ids"
            ),
            conflicts=tuple(
                ConstructionConflict.from_dict(dict(item))
                for item in data.get("conflicts", ())
            ),
            final_chain_digest=data.get("final_chain_digest"),
            state_digest=data.get("state_digest"),
            version=data.get("version"),
            proposal_only=data.get("proposal_only"),
            patch_authority=data.get("patch_authority"),
            vsa_patch_authority=data.get("vsa_patch_authority"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._identity_payload(), "state_digest": self.state_digest}


def replay_construction_events(
    events: Iterable[ConstructionEvent],
) -> ConstructionProjectState:
    items = tuple(events)
    project_id, ledger_id, active, superseded, conflicts = _reduce_events(items)
    payload = _state_payload(
        project_id=project_id,
        ledger_id=ledger_id,
        events=items,
        active_event_ids=active,
        superseded_event_ids=superseded,
        conflicts=conflicts,
        final_chain_digest=items[-1].chain_digest,
    )
    return ConstructionProjectState(
        project_id=project_id,
        ledger_id=ledger_id,
        events=items,
        active_event_ids=active,
        superseded_event_ids=superseded,
        conflicts=conflicts,
        final_chain_digest=items[-1].chain_digest,
        state_digest=stable_digest(payload),
    )


@dataclass(frozen=True)
class ConstructionReadinessReport:
    claim_id: str
    ready: bool
    blockers: tuple[str, ...]
    active_evidence_ids: tuple[str, ...]
    conflict_event_ids: tuple[str, ...]
    state_digest: str
    evaluated_at: float
    readiness_class: str = "EVIDENCE_READY_FOR_AUTHORITY_REVIEW"
    proposal_only: bool = PROPOSAL_ONLY
    human_release_required: bool = True
    physical_work_authorized: bool = False

    def __post_init__(self) -> None:
        if type(self.claim_id) is not str or not self.claim_id:
            raise ValueError("readiness claim_id is required")
        if type(self.ready) is not bool:
            raise ValueError("readiness ready flag must be boolean")
        _tuple_strings(self.blockers, "readiness.blockers")
        _tuple_strings(self.active_evidence_ids, "readiness.active_evidence_ids")
        _tuple_strings(self.conflict_event_ids, "readiness.conflict_event_ids")
        _digest(self.state_digest, "readiness.state_digest")
        _require_canonical_float(self.evaluated_at, "readiness.evaluated_at")
        _timestamp(self.evaluated_at, "readiness.evaluated_at")
        if self.readiness_class != "EVIDENCE_READY_FOR_AUTHORITY_REVIEW":
            raise ValueError("unsupported construction readiness class")
        if self.ready == bool(self.blockers):
            raise ValueError("readiness flag and blocker set disagree")
        if (
            self.proposal_only is not True
            or self.human_release_required is not True
            or self.physical_work_authorized is not False
        ):
            raise ValueError("readiness report crossed its authority boundary")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ConstructionReadinessReport":
        data = dict(value)
        return cls(
            claim_id=data.get("claim_id"),
            ready=data.get("ready"),
            blockers=_sequence_input(data.get("blockers", ()), "readiness.blockers"),
            active_evidence_ids=_sequence_input(data.get("active_evidence_ids", ()), "readiness.active_evidence_ids"),
            conflict_event_ids=_sequence_input(data.get("conflict_event_ids", ()), "readiness.conflict_event_ids"),
            state_digest=data.get("state_digest"),
            evaluated_at=data.get("evaluated_at"),
            readiness_class=data.get("readiness_class"),
            proposal_only=data.get("proposal_only"),
            human_release_required=data.get("human_release_required"),
            physical_work_authorized=data.get("physical_work_authorized"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _readiness_indexes(
    state: ConstructionProjectState,
) -> tuple[
    dict[str, tuple[ConstructionEvent, ...]],
    dict[str, ConstructionEvidence],
    dict[tuple[str, str], tuple[ConstructionConflict, ...]],
]:
    claims: dict[str, list[ConstructionEvent]] = {}
    for event in state.active_claim_events:
        if type(event.record) is ConstructionClaim:
            claims.setdefault(event.record.claim_id, []).append(event)
    evidence = {
        event.record.evidence_id: event.record
        for event in state.active_evidence_events
        if type(event.record) is ConstructionEvidence
    }
    conflicts: dict[tuple[str, str], list[ConstructionConflict]] = {}
    for item in state.conflicts:
        conflicts.setdefault((item.record_kind, item.state_key), []).append(item)
    return (
        {key: tuple(value) for key, value in claims.items()},
        evidence,
        {key: tuple(value) for key, value in conflicts.items()},
    )


def _query_claim_readiness_validated(
    state: ConstructionProjectState,
    *,
    claim_id: str,
    evaluated: float,
    claim_events_by_id: dict[str, tuple[ConstructionEvent, ...]],
    evidence_by_id: dict[str, ConstructionEvidence],
    conflicts_by_key: dict[tuple[str, str], tuple[ConstructionConflict, ...]],
) -> ConstructionReadinessReport:
    active_claim_events = claim_events_by_id.get(claim_id, ())
    if len(active_claim_events) != 1:
        return ConstructionReadinessReport(
            claim_id=claim_id,
            ready=False,
            blockers=("claim_not_uniquely_active",),
            active_evidence_ids=(),
            conflict_event_ids=(),
            state_digest=state.state_digest,
            evaluated_at=evaluated,
        )

    claim_event = active_claim_events[0]
    claim = claim_event.record
    assert type(claim) is ConstructionClaim
    blockers: list[str] = []
    conflict_ids: list[str] = []

    for conflict in conflicts_by_key.get(
        (ConstructionRecordKind.CLAIM.value, claim.state_key), ()
    ):
        blockers.append("conflicting_active_claims")
        conflict_ids.extend(conflict.active_event_ids)

    if claim.expires_at is not None and evaluated >= claim.expires_at:
        blockers.append("claim_expired")
    if not claim.evidence_refs:
        blockers.append("claim_has_no_evidence")

    active_evidence: list[ConstructionEvidence] = []
    for evidence_id in claim.evidence_refs:
        evidence = evidence_by_id.get(evidence_id)
        if evidence is None:
            blockers.append(f"missing_evidence:{evidence_id}")
            continue
        active_evidence.append(evidence)
        if evidence.scope != claim.scope:
            blockers.append(f"evidence_scope_mismatch:{evidence_id}")
        if evidence.subject_id != claim.subject_id:
            blockers.append(f"evidence_subject_mismatch:{evidence_id}")
        if _PRIVACY_RANK[evidence.privacy_class] > _PRIVACY_RANK[claim.privacy_class]:
            blockers.append(f"privacy_class_downgrade:{evidence_id}")
        if not set(evidence.consent_refs).issubset(claim.consent_refs):
            blockers.append(f"missing_consent_propagation:{evidence_id}")
        if evidence.observed_at > claim.created_at:
            blockers.append(f"evidence_postdates_claim:{evidence_id}")
        if evidence.expires_at is not None and evaluated >= evidence.expires_at:
            blockers.append(f"evidence_expired:{evidence_id}")
        for conflict in conflicts_by_key.get(
            (ConstructionRecordKind.EVIDENCE.value, evidence.state_key), ()
        ):
            blockers.append(f"conflicting_evidence:{evidence_id}")
            conflict_ids.extend(conflict.active_event_ids)

    if active_evidence and all(
        item.evidence_class in _NON_DISPOSITIVE for item in active_evidence
    ):
        blockers.append("non_dispositive_evidence_only")

    blocker_tuple = tuple(sorted(set(blockers)))
    return ConstructionReadinessReport(
        claim_id=claim_id,
        ready=not blocker_tuple,
        blockers=blocker_tuple,
        active_evidence_ids=tuple(sorted(item.evidence_id for item in active_evidence)),
        conflict_event_ids=tuple(sorted(set(conflict_ids))),
        state_digest=state.state_digest,
        evaluated_at=evaluated,
    )


def query_claim_readiness(
    state: ConstructionProjectState,
    *,
    claim_id: str,
    now: float,
) -> ConstructionReadinessReport:
    state.__post_init__()
    evaluated = _timestamp(now, "now")
    claims, evidence, conflicts = _readiness_indexes(state)
    return _query_claim_readiness_validated(
        state,
        claim_id=claim_id,
        evaluated=evaluated,
        claim_events_by_id=claims,
        evidence_by_id=evidence,
        conflicts_by_key=conflicts,
    )


def query_project_conflicts(
    state: ConstructionProjectState,
) -> tuple[ConstructionConflict, ...]:
    state.__post_init__()
    return state.conflicts


def query_project_readiness(
    state: ConstructionProjectState,
    *,
    now: float,
) -> tuple[ConstructionReadinessReport, ...]:
    state.__post_init__()
    evaluated = _timestamp(now, "now")
    claims, evidence, conflicts = _readiness_indexes(state)
    return tuple(
        _query_claim_readiness_validated(
            state,
            claim_id=claim_id,
            evaluated=evaluated,
            claim_events_by_id=claims,
            evidence_by_id=evidence,
            conflicts_by_key=conflicts,
        )
        for claim_id in sorted(claims)
    )


__all__ = [
    "CONSTRUCTION_STATE_VERSION",
    "ConstructionConflict",
    "ConstructionProjectState",
    "ConstructionReadinessReport",
    "replay_construction_events",
    "query_claim_readiness",
    "query_project_conflicts",
    "query_project_readiness",
]
