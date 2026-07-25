"""Proposal-only observations for the unchanged legacy QuantumMerkleDAG."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields
from enum import Enum
import inspect
import math
import re
import time
from typing import Any

from aura_event_contracts import (
    ActorType,
    AppendOnlyEventStore,
    AuraEventEnvelope,
    DIKWPStage,
    ExactPayloadRef,
    MeasurementClass,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_json,
    sanitize_payload,
    stable_digest,
    stable_id,
)

QDKT_EVENT_VERSION = "AURA_QDKT_EVENTS_P6_1"
QDKT_GENERATOR_VERSION = "QUANTUM_MERKLE_DAG_V1"
QDKT_EVENT_TYPE = "qdkt.observation.recorded"
QDKT_SIDECAR_KIND = "qdkt-observation-p6-1"
QDKT_POLICY_SCOPE = "qdkt.observation.advisory"
QDKT_PATCH_AUTHORITY = False
QDKT_REPRODUCIBLE = False

_ROOT_RE = re.compile(r"^[0-9A-F]{16}$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{32}$")
_NONDETERMINISTIC_INPUTS = (
    "filesystem_snapshot",
    "random_thought_id",
    "thermal_reading",
    "optional_hdc_state",
)


class QDKTTruthClass(str, Enum):
    LEGACY_NONDETERMINISTIC_ADVISORY = "LEGACY_NONDETERMINISTIC_ADVISORY"


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional(value: Any, name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    return value.strip()


def _strings(values: Sequence[Any], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence")
    result = tuple(_required(item, name) for item in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _safe_snapshot(snapshot: Any) -> tuple[Any, str, int]:
    try:
        original = canonical_json(snapshot)
        safe = sanitize_payload(snapshot)
        sanitized = canonical_json(safe)
    except (TypeError, ValueError) as exc:
        raise ValueError("source_snapshot must be canonical and safe") from exc
    if sanitized != original:
        raise ValueError("source_snapshot must not contain sensitive or lossy values")
    if isinstance(safe, Mapping):
        count = len(safe)
    elif isinstance(safe, Sequence) and not isinstance(safe, (str, bytes, bytearray)):
        count = len(safe)
    else:
        raise ValueError("source_snapshot must be a mapping or ordered sequence")
    return safe, stable_digest(safe), count


def _belief(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _timestamp(value: Any) -> float:
    if value is None:
        return time.time()
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("created_at must be a finite number")
    return float(value)


def _actor(value: ActorType | str) -> ActorType:
    if isinstance(value, ActorType):
        return value
    try:
        return ActorType(str(value))
    except ValueError as exc:
        raise ValueError("unsupported actor_type") from exc


def _preflight_fields(
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str,
    purpose_digest: str,
    parent_event_ids: Sequence[str],
    evidence_refs: Sequence[str],
    arena_id: str,
    board_id: str,
    objective_id: str,
    policy_scope: str,
    created_at: Any,
) -> dict[str, Any]:
    if policy_scope != QDKT_POLICY_SCOPE:
        raise ValueError("policy_scope must remain the canonical QDKT advisory scope")
    return {
        "trace_id": _required(trace_id, "trace_id"),
        "actor_id": _required(actor_id, "actor_id"),
        "actor_type": _actor(actor_type),
        "purpose_digest": _required(purpose_digest, "purpose_digest"),
        "parent_event_ids": _strings(parent_event_ids, "parent_event_ids"),
        "evidence_refs": _strings(evidence_refs, "evidence_refs"),
        "arena_id": _optional(arena_id, "arena_id"),
        "board_id": _optional(board_id, "board_id"),
        "objective_id": _optional(objective_id, "objective_id"),
        "policy_scope": policy_scope,
        "created_at": _timestamp(created_at),
    }


@dataclass(frozen=True)
class QDKTObservation:
    observation_id: str
    legacy_root: str
    legacy_belief: int
    source_snapshot_digest: str
    source_count: int
    generator_version: str
    truth_class: QDKTTruthClass | str
    nondeterministic_inputs: tuple[str, ...]
    planning_board_ref: str = ""
    planning_history_ref: str = ""
    continuity_ref: str = ""
    proposal_only: bool = True
    reproducible: bool = QDKT_REPRODUCIBLE
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    qdkt_patch_authority: bool = QDKT_PATCH_AUTHORITY
    version: str = QDKT_EVENT_VERSION

    def __post_init__(self) -> None:
        if type(self.legacy_root) is not str or not _ROOT_RE.fullmatch(self.legacy_root):
            raise ValueError("legacy_root must be 16 uppercase hexadecimal characters")
        _belief(self.legacy_belief, "legacy_belief")
        if type(self.source_snapshot_digest) is not str or not _DIGEST_RE.fullmatch(self.source_snapshot_digest):
            raise ValueError("source_snapshot_digest must be a canonical digest")
        if type(self.source_count) is not int or self.source_count < 0:
            raise ValueError("source_count must be a non-negative integer")
        if self.generator_version != QDKT_GENERATOR_VERSION:
            raise ValueError("unsupported QDKT generator version")
        try:
            truth = (
                self.truth_class
                if isinstance(self.truth_class, QDKTTruthClass)
                else QDKTTruthClass(str(self.truth_class))
            )
        except ValueError as exc:
            raise ValueError("unsupported QDKT truth class") from exc
        inputs = _strings(self.nondeterministic_inputs, "nondeterministic_inputs")
        if inputs != _NONDETERMINISTIC_INPUTS:
            raise ValueError("nondeterministic_inputs must declare the complete legacy set")
        object.__setattr__(self, "truth_class", truth)
        object.__setattr__(self, "nondeterministic_inputs", inputs)
        for name in ("planning_board_ref", "planning_history_ref", "continuity_ref"):
            object.__setattr__(self, name, _optional(getattr(self, name), name))
        if self.proposal_only is not True or self.reproducible is not False:
            raise ValueError("QDKT observations must remain proposal-only and non-reproducible")
        if (
            self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.qdkt_patch_authority is not False
        ):
            raise ValueError("QDKT authority boundary changed")
        if self.version != QDKT_EVENT_VERSION:
            raise ValueError("unsupported QDKT observation version")
        if self.observation_id != stable_id("qdkt-observation", self.identity_payload()):
            raise ValueError("observation_id does not match canonical observation identity")

    @classmethod
    def from_legacy_result(
        cls,
        legacy_result: Mapping[str, Any],
        *,
        source_snapshot: Any,
        planning_board_ref: str = "",
        planning_history_ref: str = "",
        continuity_ref: str = "",
    ) -> "QDKTObservation":
        if not isinstance(legacy_result, Mapping):
            raise ValueError("legacy_result must be a mapping")
        if set(legacy_result) != {"root", "belief"}:
            raise ValueError("legacy_result must contain exactly root and belief")
        root = legacy_result.get("root")
        belief = legacy_result.get("belief")
        if type(root) is not str or not _ROOT_RE.fullmatch(root):
            raise ValueError("legacy_result.root is malformed")
        belief = _belief(belief, "legacy_result.belief")
        _safe, source_digest, source_count = _safe_snapshot(source_snapshot)
        identity = {
            "legacy_root": root,
            "legacy_belief": belief,
            "source_snapshot_digest": source_digest,
            "source_count": source_count,
            "generator_version": QDKT_GENERATOR_VERSION,
            "truth_class": QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY.value,
            "nondeterministic_inputs": _NONDETERMINISTIC_INPUTS,
            "planning_board_ref": _optional(planning_board_ref, "planning_board_ref"),
            "planning_history_ref": _optional(planning_history_ref, "planning_history_ref"),
            "continuity_ref": _optional(continuity_ref, "continuity_ref"),
        }
        return cls(
            observation_id=stable_id("qdkt-observation", identity),
            proposal_only=True,
            reproducible=False,
            qdkt_patch_authority=False,
            **identity,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QDKTObservation":
        if not isinstance(value, Mapping):
            raise ValueError("QDKT observation payload must be a mapping")
        if set(value) != {field.name for field in fields(cls)}:
            raise ValueError("QDKT observation payload fields are not canonical")
        raw_inputs = value["nondeterministic_inputs"]
        if type(raw_inputs) is not list:
            raise ValueError("nondeterministic_inputs must be a canonical JSON array")
        kwargs = dict(value)
        kwargs["nondeterministic_inputs"] = tuple(raw_inputs)
        return cls(**kwargs)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "legacy_root": self.legacy_root,
            "legacy_belief": self.legacy_belief,
            "source_snapshot_digest": self.source_snapshot_digest,
            "source_count": self.source_count,
            "generator_version": self.generator_version,
            "truth_class": (
                self.truth_class.value if isinstance(self.truth_class, QDKTTruthClass) else str(self.truth_class)
            ),
            "nondeterministic_inputs": tuple(self.nondeterministic_inputs),
            "planning_board_ref": self.planning_board_ref,
            "planning_history_ref": self.planning_history_ref,
            "continuity_ref": self.continuity_ref,
        }

    @property
    def legacy_result(self) -> dict[str, Any]:
        return {"root": self.legacy_root, "belief": self.legacy_belief}

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["truth_class"] = self.truth_class.value
        value["nondeterministic_inputs"] = list(self.nondeterministic_inputs)
        return value


@dataclass(frozen=True)
class QDKTEventReceipt:
    observation: QDKTObservation
    payload_ref: ExactPayloadRef
    event: AuraEventEnvelope
    appended: bool
    version: str = QDKT_EVENT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.observation, QDKTObservation):
            raise ValueError("observation must be a QDKTObservation")
        if not isinstance(self.payload_ref, ExactPayloadRef):
            raise ValueError("payload_ref must be an ExactPayloadRef")
        if not isinstance(self.event, AuraEventEnvelope):
            raise ValueError("event must be an AuraEventEnvelope")
        if type(self.appended) is not bool:
            raise ValueError("appended must be a boolean")
        if self.payload_ref.kind != QDKT_SIDECAR_KIND:
            raise ValueError("sidecar kind does not match the QDKT contract")
        if self.payload_ref.redacted is not False:
            raise ValueError("canonical QDKT observation was unexpectedly redacted")
        expected_bytes = len(canonical_json(self.observation.to_dict()).encode("utf-8"))
        if self.payload_ref.byte_count != expected_bytes:
            raise ValueError("sidecar byte count does not match the observation")
        if self.payload_ref.created_at != self.event.created_at:
            raise ValueError("sidecar and event timestamps disagree")
        if (
            self.event.event_type != QDKT_EVENT_TYPE
            or self.event.node_id != self.observation.observation_id
            or self.event.payload_ref != self.payload_ref.ref_id
            or self.event.payload_digest != self.payload_ref.payload_digest
            or self.payload_ref.payload_digest != self.observation.digest
        ):
            raise ValueError("QDKT receipt identities disagree")
        if (
            self.event.dikwp_stage != DIKWPStage.KNOWLEDGE.value
            or self.event.policy_scope != QDKT_POLICY_SCOPE
            or self.event.measurement_classes != {"legacy_belief": MeasurementClass.DERIVED.value}
        ):
            raise ValueError("event metadata does not match the QDKT contract")
        if (
            self.event.proposal_only is not True
            or self.event.patch_authority != PATCH_AUTHORITY
            or self.event.vsa_patch_authority is not False
        ):
            raise ValueError("QDKT event authority boundary changed")
        if self.version != QDKT_EVENT_VERSION:
            raise ValueError("unsupported QDKT event receipt version")


def _envelope(
    observation: QDKTObservation,
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType,
    purpose_digest: str,
    payload_ref: str,
    payload_digest: str,
    parent_event_ids: tuple[str, ...],
    evidence_refs: tuple[str, ...],
    arena_id: str,
    board_id: str,
    objective_id: str,
    policy_scope: str,
    created_at: float,
) -> AuraEventEnvelope:
    return AuraEventEnvelope.create(
        trace_id=trace_id,
        parent_event_ids=parent_event_ids,
        event_type=QDKT_EVENT_TYPE,
        actor_id=actor_id,
        actor_type=actor_type,
        arena_id=arena_id,
        board_id=board_id,
        node_id=observation.observation_id,
        objective_id=objective_id,
        purpose_digest=purpose_digest,
        dikwp_stage=DIKWPStage.KNOWLEDGE,
        payload_ref=_required(payload_ref, "payload_ref"),
        payload_digest=_required(payload_digest, "payload_digest"),
        evidence_refs=evidence_refs,
        policy_scope=policy_scope,
        proposal_only=True,
        measurement_classes={"legacy_belief": MeasurementClass.DERIVED},
        created_at=created_at,
    )


def record_qdkt_observation(
    store: AppendOnlyEventStore,
    observation: QDKTObservation,
    *,
    trace_id: str,
    actor_id: str,
    purpose_digest: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    arena_id: str = "",
    board_id: str = "",
    objective_id: str = "",
    policy_scope: str = QDKT_POLICY_SCOPE,
    created_at: float | None = None,
) -> QDKTEventReceipt:
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    if not isinstance(observation, QDKTObservation):
        raise ValueError("observation must be a QDKTObservation")
    common = _preflight_fields(
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        purpose_digest=purpose_digest,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        arena_id=arena_id,
        board_id=board_id,
        objective_id=objective_id,
        policy_scope=policy_scope,
        created_at=created_at,
    )
    _envelope(
        observation,
        payload_ref="preflight:qdkt-observation",
        payload_digest="preflight-qdkt-observation-digest",
        **common,
    )
    payload_ref = store.store_payload(
        observation.to_dict(),
        kind=QDKT_SIDECAR_KIND,
        created_at=common["created_at"],
    )
    event = _envelope(
        observation,
        payload_ref=payload_ref.ref_id,
        payload_digest=payload_ref.payload_digest,
        **common,
    )
    return QDKTEventReceipt(observation, payload_ref, event, store.append(event))


async def capture_legacy_qdkt_observation(
    store: AppendOnlyEventStore,
    legacy_generator: Any,
    *,
    source_snapshot: Any,
    trace_id: str,
    actor_id: str,
    purpose_digest: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    arena_id: str = "",
    board_id: str = "",
    objective_id: str = "",
    planning_board_ref: str = "",
    planning_history_ref: str = "",
    continuity_ref: str = "",
    created_at: float | None = None,
) -> QDKTEventReceipt:
    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    preflight = _preflight_fields(
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        purpose_digest=purpose_digest,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        arena_id=arena_id,
        board_id=board_id,
        objective_id=objective_id,
        policy_scope=QDKT_POLICY_SCOPE,
        created_at=created_at,
    )
    safe_snapshot, _digest, _count = _safe_snapshot(source_snapshot)
    planning_board_ref = _optional(planning_board_ref, "planning_board_ref")
    planning_history_ref = _optional(planning_history_ref, "planning_history_ref")
    continuity_ref = _optional(continuity_ref, "continuity_ref")
    method = getattr(legacy_generator, "generate_epistemic_system_root", None)
    if method is None or not callable(method):
        raise ValueError("legacy_generator must expose generate_epistemic_system_root")
    result = method()
    if inspect.isawaitable(result):
        result = await result
    observation = QDKTObservation.from_legacy_result(
        result,
        source_snapshot=safe_snapshot,
        planning_board_ref=planning_board_ref,
        planning_history_ref=planning_history_ref,
        continuity_ref=continuity_ref,
    )
    if observation.legacy_result != dict(result):
        raise ValueError("canonical observation changed the exact legacy result")
    return record_qdkt_observation(
        store,
        observation,
        trace_id=preflight["trace_id"],
        actor_id=preflight["actor_id"],
        purpose_digest=preflight["purpose_digest"],
        actor_type=preflight["actor_type"],
        parent_event_ids=preflight["parent_event_ids"],
        evidence_refs=preflight["evidence_refs"],
        arena_id=preflight["arena_id"],
        board_id=preflight["board_id"],
        objective_id=preflight["objective_id"],
        policy_scope=preflight["policy_scope"],
        created_at=preflight["created_at"],
    )


__all__ = [
    "QDKT_EVENT_TYPE",
    "QDKT_EVENT_VERSION",
    "QDKT_GENERATOR_VERSION",
    "QDKT_POLICY_SCOPE",
    "QDKT_SIDECAR_KIND",
    "QDKTEventReceipt",
    "QDKTObservation",
    "QDKTTruthClass",
    "capture_legacy_qdkt_observation",
    "record_qdkt_observation",
]


# ---------------------------------------------------------------------------
# C8 — relationship experience advisory projection
# ---------------------------------------------------------------------------

RELATIONSHIP_EXPERIENCE_QDKT_VERSION = "AURA_RELATIONSHIP_EXPERIENCE_QDKT_V1"


def project_relationship_experience_advisory(observation: Any) -> dict[str, Any]:
    """Project one governed relationship experience into QDKT advisory memory.

    This is deliberately not a QDKT truth promotion. It carries receipt pointers and
    outcome labels only; canonical relationship validity remains owned by current
    Relational Index/Atlas evidence.
    """
    from aura_relationship_experience import RelationshipExperienceObservation

    item = (
        observation
        if isinstance(observation, RelationshipExperienceObservation)
        else RelationshipExperienceObservation.from_dict(observation)
    )
    payload = {
        "version": RELATIONSHIP_EXPERIENCE_QDKT_VERSION,
        "observation_id": item.observation_id,
        "relationship_id": item.relationship_id,
        "relationship_digest": item.relationship_digest,
        "repository_head": item.repository_head,
        "outcome": item.outcome.value,
        "human_disposition": item.human_disposition.value,
        "verifier_evidence_refs": list(item.verifier_evidence_refs),
        "receipt_refs": list(item.receipt_refs),
        "truth_class": "DERIVED_EXPERIENCE_ADVISORY",
        "canonical_relation_validity": False,
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }
    payload["projection_digest"] = stable_digest(payload)
    return payload


# ---------------------------------------------------------------------------
# U7 — governed consequential Relationship Experience advisory recording
# ---------------------------------------------------------------------------

GOVERNED_RELATIONSHIP_QDKT_EVENT_TYPE = "qdkt.relationship_experience.advisory_recorded"
GOVERNED_RELATIONSHIP_QDKT_POLICY_SCOPE = "qdkt.relationship_experience.governed_advisory"
GOVERNED_RELATIONSHIP_QDKT_SIDECAR_KIND = "qdkt-relationship-experience-u7"


@dataclass(frozen=True)
class GovernedRelationshipQDKTEventReceipt:
    projection: dict[str, Any]
    payload_ref: ExactPayloadRef
    event: AuraEventEnvelope
    appended: bool
    version: str = RELATIONSHIP_EXPERIENCE_QDKT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.projection, dict):
            raise ValueError("projection must be a dictionary")
        if not isinstance(self.payload_ref, ExactPayloadRef):
            raise ValueError("payload_ref must be an ExactPayloadRef")
        if not isinstance(self.event, AuraEventEnvelope):
            raise ValueError("event must be an AuraEventEnvelope")
        if type(self.appended) is not bool:
            raise ValueError("appended must be a boolean")
        if self.payload_ref.kind != GOVERNED_RELATIONSHIP_QDKT_SIDECAR_KIND:
            raise ValueError("governed QDKT sidecar kind mismatch")
        if self.payload_ref.redacted is not False:
            raise ValueError("governed QDKT projection was unexpectedly redacted")
        if self.event.event_type != GOVERNED_RELATIONSHIP_QDKT_EVENT_TYPE:
            raise ValueError("governed QDKT event type mismatch")
        if self.event.policy_scope != GOVERNED_RELATIONSHIP_QDKT_POLICY_SCOPE:
            raise ValueError("governed QDKT policy scope mismatch")
        if self.event.payload_ref != self.payload_ref.ref_id:
            raise ValueError("governed QDKT event payload reference mismatch")
        if self.event.payload_digest != self.payload_ref.payload_digest:
            raise ValueError("governed QDKT event payload digest mismatch")
        if self.event.node_id != str(self.projection.get("observation_id") or ""):
            raise ValueError("governed QDKT event node differs from Relationship Experience")
        if self.event.proposal_only is not True:
            raise ValueError("governed QDKT event must remain proposal-only")
        if self.projection.get("automatic_crystallization") is not False:
            raise ValueError("governed QDKT projection gained crystallization authority")
        if self.projection.get("qdkt_admitted") is not True:
            raise ValueError("governed QDKT projection requires admitted consequential evidence")
        if self.version != RELATIONSHIP_EXPERIENCE_QDKT_VERSION:
            raise ValueError("unsupported governed Relationship Experience QDKT version")


def record_relationship_experience_advisory(
    store: AppendOnlyEventStore,
    observation: Any,
    admission: Any,
    *,
    trace_id: str,
    actor_id: str,
    purpose_digest: str,
    actor_type: ActorType | str = ActorType.AURA,
    parent_event_ids: Sequence[str] = (),
    evidence_refs: Sequence[str] = (),
    arena_id: str = "",
    board_id: str = "",
    objective_id: str = "",
    created_at: float | None = None,
) -> GovernedRelationshipQDKTEventReceipt:
    """Append an admitted Relationship Experience advisory without crystallizing it."""
    from aura_relationship_experience import RelationshipExperienceObservation
    from aura_unified_memory_continuity import QDKTConsequentialAdmission

    if not isinstance(store, AppendOnlyEventStore):
        raise ValueError("store must be an AppendOnlyEventStore")
    item = (
        observation
        if isinstance(observation, RelationshipExperienceObservation)
        else RelationshipExperienceObservation.from_dict(observation)
    )
    if not isinstance(admission, QDKTConsequentialAdmission):
        raise ValueError("admission must use QDKTConsequentialAdmission")
    if admission.admitted is not True:
        raise ValueError("only admitted consequential evidence may enter governed QDKT")
    if admission.relationship_experience_ref != item.observation_id:
        raise ValueError("QDKT admission refers to a different Relationship Experience")
    required_refs = {
        *admission.raw_evidence_refs,
        admission.continuity_receipt_ref,
        admission.crucible_proposal_ref,
        admission.current_reproof_ref,
        admission.human_disposition_ref,
    }
    normalized_refs = _strings(evidence_refs, "evidence_refs")
    if not required_refs.issubset(normalized_refs):
        raise ValueError("governed QDKT event omits required consequential evidence refs")
    projection = {
        **project_relationship_experience_advisory(item),
        "qdkt_admission_ref": admission.decision_id,
        "qdkt_admission_digest": admission.decision_digest,
        "qdkt_admitted": True,
        "raw_evidence_refs": list(admission.raw_evidence_refs),
        "current_reproof_ref": admission.current_reproof_ref,
        "human_disposition_ref": admission.human_disposition_ref,
        "crucible_proposal_ref": admission.crucible_proposal_ref,
        "automatic_observe": False,
        "automatic_crystallization": False,
        "crystallization_authority": False,
    }
    projection["projection_digest"] = stable_digest(
        {key: value for key, value in projection.items() if key != "projection_digest"}
    )
    timestamp = _timestamp(created_at)
    payload_ref = store.store_payload(
        projection,
        kind=GOVERNED_RELATIONSHIP_QDKT_SIDECAR_KIND,
        created_at=timestamp,
    )
    event = AuraEventEnvelope.create(
        trace_id=_required(trace_id, "trace_id"),
        parent_event_ids=_strings(parent_event_ids, "parent_event_ids"),
        event_type=GOVERNED_RELATIONSHIP_QDKT_EVENT_TYPE,
        actor_id=_required(actor_id, "actor_id"),
        actor_type=actor_type,
        arena_id=_optional(arena_id, "arena_id"),
        board_id=_optional(board_id, "board_id"),
        node_id=item.observation_id,
        objective_id=_optional(objective_id, "objective_id"),
        purpose_digest=_required(purpose_digest, "purpose_digest"),
        dikwp_stage=DIKWPStage.KNOWLEDGE,
        payload_ref=payload_ref.ref_id,
        payload_digest=payload_ref.payload_digest,
        evidence_refs=normalized_refs,
        policy_scope=GOVERNED_RELATIONSHIP_QDKT_POLICY_SCOPE,
        proposal_only=True,
        measurement_classes={"admission": MeasurementClass.VERIFIER_BACKED},
        created_at=timestamp,
    )
    return GovernedRelationshipQDKTEventReceipt(
        projection=projection,
        payload_ref=payload_ref,
        event=event,
        appended=store.append(event),
    )


__all__ = [
    "GOVERNED_RELATIONSHIP_QDKT_EVENT_TYPE",
    "GOVERNED_RELATIONSHIP_QDKT_POLICY_SCOPE",
    "GOVERNED_RELATIONSHIP_QDKT_SIDECAR_KIND",
    "QDKT_EVENT_TYPE",
    "QDKT_EVENT_VERSION",
    "QDKT_GENERATOR_VERSION",
    "QDKT_POLICY_SCOPE",
    "QDKT_SIDECAR_KIND",
    "RELATIONSHIP_EXPERIENCE_QDKT_VERSION",
    "GovernedRelationshipQDKTEventReceipt",
    "QDKTEventReceipt",
    "QDKTObservation",
    "QDKTTruthClass",
    "capture_legacy_qdkt_observation",
    "project_relationship_experience_advisory",
    "record_qdkt_observation",
    "record_relationship_experience_advisory",
]
