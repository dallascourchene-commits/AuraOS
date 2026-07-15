"""Canonical proposal-only QDKT observations over the unchanged legacy DAG.

The legacy ``QuantumMerkleDAG`` result is preserved exactly and classified as
nondeterministic advisory evidence.  This module never executes plans, grants
policy or patch authority, or claims that a legacy root can be reproduced.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import Enum
import inspect
import math
import re
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
_DEFAULT_NONDETERMINISTIC_INPUTS = (
    "filesystem_snapshot",
    "random_thought_id",
    "thermal_reading",
    "optional_hdc_state",
)


class QDKTTruthClass(str, Enum):
    LEGACY_NONDETERMINISTIC_ADVISORY = "LEGACY_NONDETERMINISTIC_ADVISORY"


def _required(value: Any, field_name: str) -> str:
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _optional(value: Any, field_name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    return value.strip()


def _strict_strings(values: Sequence[Any], field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field_name} must be a sequence")
    normalized = tuple(_required(item, field_name) for item in values)
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return normalized


def _source_snapshot(snapshot: Any) -> tuple[str, int]:
    safe = sanitize_payload(snapshot)
    if isinstance(safe, Mapping):
        count = len(safe)
    elif isinstance(safe, Sequence) and not isinstance(safe, (str, bytes, bytearray)):
        count = len(safe)
    else:
        raise ValueError("source_snapshot must be a mapping or ordered sequence")
    if type(count) is not int or count < 0:
        raise ValueError("source_count must be a non-negative integer")
    return stable_digest(safe), count


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
        if type(self.legacy_root) is not str or _ROOT_RE.fullmatch(self.legacy_root) is None:
            raise ValueError("legacy_root must be 16 uppercase hexadecimal characters")
        if type(self.legacy_belief) is not int:
            raise ValueError("legacy_belief must be an integer")
        if type(self.source_snapshot_digest) is not str or _DIGEST_RE.fullmatch(
            self.source_snapshot_digest
        ) is None:
            raise ValueError("source_snapshot_digest must be a canonical BLAKE2 digest")
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
        inputs = _strict_strings(self.nondeterministic_inputs, "nondeterministic_inputs")
        if not inputs:
            raise ValueError("nondeterministic_inputs must not be empty")
        for field_name in ("planning_board_ref", "planning_history_ref", "continuity_ref"):
            object.__setattr__(self, field_name, _optional(getattr(self, field_name), field_name))
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
        payload = self.identity_payload()
        expected_id = stable_id("qdkt-observation", payload)
        if self.observation_id != expected_id:
            raise ValueError("observation_id does not match canonical observation identity")
        object.__setattr__(self, "truth_class", truth)
        object.__setattr__(self, "nondeterministic_inputs", inputs)

    @classmethod
    def from_legacy_result(
        cls,
        legacy_result: Mapping[str, Any],
        *,
        source_snapshot: Any,
        planning_board_ref: str = "",
        planning_history_ref: str = "",
        continuity_ref: str = "",
        nondeterministic_inputs: Sequence[str] = _DEFAULT_NONDETERMINISTIC_INPUTS,
    ) -> "QDKTObservation":
        if not isinstance(legacy_result, Mapping):
            raise ValueError("legacy_result must be a mapping")
        if set(legacy_result) != {"root", "belief"}:
            raise ValueError("legacy_result must contain exactly root and belief")
        root = legacy_result.get("root")
        belief = legacy_result.get("belief")
        if type(root) is not str or _ROOT_RE.fullmatch(root) is None:
            raise ValueError("legacy_result.root is malformed")
        if type(belief) is not int:
            raise ValueError("legacy_result.belief must be an integer")
        snapshot_digest, source_count = _source_snapshot(source_snapshot)
        inputs = _strict_strings(nondeterministic_inputs, "nondeterministic_inputs")
        payload = {
            "legacy_root": root,
            "legacy_belief": belief,
            "source_snapshot_digest": snapshot_digest,
            "source_count": source_count,
            "generator_version": QDKT_GENERATOR_VERSION,
            "truth_class": QDKTTruthClass.LEGACY_NONDETERMINISTIC_ADVISORY.value,
            "nondeterministic_inputs": inputs,
            "planning_board_ref": _optional(planning_board_ref, "planning_board_ref"),
            "planning_history_ref": _optional(planning_history_ref, "planning_history_ref"),
            "continuity_ref": _optional(continuity_ref, "continuity_ref"),
        }
        return cls(
            observation_id=stable_id("qdkt-observation", payload),
            proposal_only=True,
            reproducible=False,
            patch_authority=PATCH_AUTHORITY,
            vsa_patch_authority=False,
            qdkt_patch_authority=False,
            version=QDKT_EVENT_VERSION,
            **payload,
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QDKTObservation":
        if not isinstance(value, Mapping):
            raise ValueError("QDKT observation payload must be a mapping")
        expected = {field.name for field in cls.__dataclass_fields__.values()}
        if set(value) != expected:
            raise ValueError("QDKT observation payload fields are not canonical")
        return cls(
            observation_id=value["observation_id"],
            legacy_root=value["legacy_root"],
            legacy_belief=value["legacy_belief"],
            source_snapshot_digest=value["source_snapshot_digest"],
            source_count=value["source_count"],
            generator_version=value["generator_version"],
            truth_class=value["truth_class"],
            nondeterministic_inputs=tuple(value["nondeterministic_inputs"]),
            planning_board_ref=value["planning_board_ref"],
            planning_history_ref=value["planning_history_ref"],
            continuity_ref=value["continuity_ref"],
            proposal_only=value["proposal_only"],
            reproducible=value["reproducible"],
            patch_authority=value["patch_authority"],
            vsa_patch_authority=value["vsa_patch_authority"],
            qdkt_patch_authority=value["qdkt_patch_authority"],
            version=value["version"],
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "legacy_root": self.legacy_root,
            "legacy_belief": self.legacy_belief,
            "source_snapshot_digest": self.source_snapshot_digest,
            "source_count": self.source_count,
            "generator_version": self.generator_version,
            "truth_class": (
                self.truth_class.value
                if isinstance(self.truth_class, QDKTTruthClass)
                else str(self.truth_class)
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
        value["truth_class"] = (
            self.truth_class.value
            if isinstance(self.truth_class, QDKTTruthClass)
            else str(self.truth_class)
        )
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
        if self.event.event_type != QDKT_EVENT_TYPE:
            raise ValueError("event type does not match the QDKT contract")
        if self.event.payload_ref != self.payload_ref.ref_id:
            raise ValueError("event payload_ref does not match the sidecar")
        if self.event.payload_digest != self.payload_ref.payload_digest:
            raise ValueError("event payload_digest does not match the sidecar")
        if self.payload_ref.payload_digest != self.observation.digest:
            raise ValueError("sidecar digest does not match the observation")
        if self.event.node_id != self.observation.observation_id:
            raise ValueError("event node_id does not match the observation")
        if self.event.proposal_only is not True:
            raise ValueError("QDKT events must remain proposal_only")
        if self.version != QDKT_EVENT_VERSION:
            raise ValueError("unsupported QDKT event receipt version")


def _event_envelope(
    observation: QDKTObservation,
    *,
    trace_id: str,
    actor_id: str,
    actor_type: ActorType | str,
    purpose_digest: str,
    payload_ref: str,
    payload_digest: str,
    parent_event_ids: Sequence[str],
    evidence_refs: Sequence[str],
    arena_id: str,
    board_id: str,
    objective_id: str,
    policy_scope: str,
    created_at: float | None,
) -> AuraEventEnvelope:
    parents = _strict_strings(parent_event_ids, "parent_event_ids")
    evidence = _strict_strings(evidence_refs, "evidence_refs")
    if created_at is not None:
        timestamp = float(created_at)
        if not math.isfinite(timestamp):
            raise ValueError("created_at must be finite")
    return AuraEventEnvelope.create(
        trace_id=_required(trace_id, "trace_id"),
        parent_event_ids=parents,
        event_type=QDKT_EVENT_TYPE,
        actor_id=_required(actor_id, "actor_id"),
        actor_type=actor_type,
        arena_id=_optional(arena_id, "arena_id"),
        board_id=_optional(board_id, "board_id"),
        node_id=observation.observation_id,
        objective_id=_optional(objective_id, "objective_id"),
        purpose_digest=_required(purpose_digest, "purpose_digest"),
        dikwp_stage=DIKWPStage.KNOWLEDGE,
        payload_ref=_required(payload_ref, "payload_ref"),
        payload_digest=_required(payload_digest, "payload_digest"),
        evidence_refs=evidence,
        policy_scope=_required(policy_scope, "policy_scope"),
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

    # Prove all caller-controlled envelope fields before writing an immutable sidecar.
    _event_envelope(
        observation,
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        purpose_digest=purpose_digest,
        payload_ref="preflight:qdkt-observation",
        payload_digest="preflight-qdkt-observation-digest",
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        arena_id=arena_id,
        board_id=board_id,
        objective_id=objective_id,
        policy_scope=policy_scope,
        created_at=created_at,
    )
    payload_ref = store.store_payload(
        observation.to_dict(),
        kind=QDKT_SIDECAR_KIND,
        created_at=created_at,
    )
    event = _event_envelope(
        observation,
        trace_id=trace_id,
        actor_id=actor_id,
        actor_type=actor_type,
        purpose_digest=purpose_digest,
        payload_ref=payload_ref.ref_id,
        payload_digest=payload_ref.payload_digest,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        arena_id=arena_id,
        board_id=board_id,
        objective_id=objective_id,
        policy_scope=policy_scope,
        created_at=created_at,
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
    method = getattr(legacy_generator, "generate_epistemic_system_root", None)
    if method is None or not callable(method):
        raise ValueError("legacy_generator must expose generate_epistemic_system_root")
    result = method()
    if inspect.isawaitable(result):
        result = await result
    observation = QDKTObservation.from_legacy_result(
        result,
        source_snapshot=source_snapshot,
        planning_board_ref=planning_board_ref,
        planning_history_ref=planning_history_ref,
        continuity_ref=continuity_ref,
    )
    if observation.legacy_result != dict(result):
        raise ValueError("canonical observation changed the exact legacy QDKT result")
    return record_qdkt_observation(
        store,
        observation,
        trace_id=trace_id,
        actor_id=actor_id,
        purpose_digest=purpose_digest,
        actor_type=actor_type,
        parent_event_ids=parent_event_ids,
        evidence_refs=evidence_refs,
        arena_id=arena_id,
        board_id=board_id,
        objective_id=objective_id,
        created_at=created_at,
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
