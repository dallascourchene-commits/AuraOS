"""Governed U6→U7 runtime for unified memory and continuity.

This module orchestrates existing Aura owners. It does not introduce a memory,
truth, verification, Crucible, Relationship Experience, QDKT, or authority
plane. P0, P1, continuity, reproof, disposition, experience, and QDKT records
remain typed, exact-head-bound, proposal-only, and human/community-gated.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import subprocess
import time
from typing import Any

from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_crucible_store import CrucibleStore
from aura_crucible_types import CRYSTALLIZATION_PROPOSED, CrystallizationProposal
from aura_event_contracts import ActorType, AppendOnlyEventStore, PATCH_AUTHORITY, stable_digest
from aura_qdkt_observations import record_relationship_experience_advisory
from aura_relationship_experience import RelationshipExperienceObservation
from aura_unified_memory_continuity import (
    ActCapsuleEnvelope,
    AuthorityEnvelope,
    ContinuitySensitivityReceipt,
    IntentPacket,
    ModelExecutionPacket,
    P1Observation,
    PredictionPacket,
    QDKTConsequentialAdmission,
    commit_prediction,
    derive_continuity_sensitivity_receipt,
    evaluate_learning_to_reproof,
    evaluate_qdkt_consequential_admission,
    observe_prediction,
    relationship_experience_kwargs,
)
from aura_unified_memory_continuity_toolchain import UnifiedExecutionBinding

LEARNING_RUNTIME_VERSION = "AURA_UNIFIED_MEMORY_CONTINUITY_LEARNING_RUNTIME_V1"
CURRENT_REPROOF_VERSION = "AURA_CURRENT_REPROOF_RECEIPT_V1"
HUMAN_DISPOSITION_VERSION = "AURA_HUMAN_COMMUNITY_DISPOSITION_RECEIPT_V1"
CRUCIBLE_BINDING_VERSION = "AURA_CRUCIBLE_PROPOSAL_EXECUTION_BINDING_V1"
VSA_PATCH_AUTHORITY = False

_ALLOWED_DISPOSITIONS = frozenset({"APPROVED", "DENIED", "DEFERRED", "NOT_REVIEWED"})
_ALLOWED_OUTCOMES = frozenset(
    {
        "SUCCESS",
        "FAILURE",
        "DENIAL",
        "ABANDONMENT",
        "ROLLBACK",
        "SUPERSEDED",
        "EXPIRED",
        "CONTRADICTED",
    }
)
_MAX_ITEMS = 256
_MAX_TEXT_BYTES = 16 * 1024
_MAX_CLOCK_SKEW_SECONDS = 300.0


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_BYTES} UTF-8 bytes")
    return text


def _optional(value: Any, name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_BYTES} UTF-8 bytes")
    return text


def _strings(value: Any, name: str, *, required: bool = False) -> tuple[str, ...]:
    if value is None:
        value = ()
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(value) > _MAX_ITEMS:
        raise ValueError(f"{name} exceeds {_MAX_ITEMS} items")
    result = tuple(dict.fromkeys(_required(item, name) for item in value))
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    return result


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        decoded = json.loads(encoded)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be canonical JSON data") from exc
    if not isinstance(decoded, dict):
        raise ValueError(f"{name} must be an object")
    return decoded


def _timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite timestamp")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite timestamp")
    return result


def _current_timestamp(value: Any, name: str) -> float:
    current = time.time()
    result = current if value is None else _timestamp(value, name)
    if abs(result - current) > _MAX_CLOCK_SKEW_SECONDS:
        raise ValueError(f"{name} exceeds permitted clock skew")
    return result


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    return result.stdout.strip()


def _source_digest(root: Path, paths: Sequence[str]) -> str:
    hashes: dict[str, str] = {}
    for raw in sorted(_strings(paths, "allowed_files", required=True)):
        path = (root / raw).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError("allowed source path escaped repository root") from exc
        if not path.is_file():
            raise ValueError(f"current source file is missing: {raw}")
        hashes[raw] = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    return stable_digest(hashes)


def _validate_storage_path(
    repo_root: Path,
    path_value: Any,
    name: str,
) -> Path | None:
    """Validate storage path is relative, contains no traversal, and resolves within repo_root.

    Returns None if path_value is None, otherwise returns the validated absolute Path.
    Raises ValueError if path is absolute, contains .., or resolves outside repo_root.
    """
    if path_value is None:
        return None
    if not isinstance(path_value, (str, Path)):
        raise ValueError(f"{name} must be a string or Path")

    path_str = str(path_value).strip()
    if not path_str:
        return None

    # Reject absolute paths
    if Path(path_str).is_absolute():
        raise ValueError(f"{name} must not be an absolute path")

    # Reject paths containing .. traversal
    parts = Path(path_str).parts
    if ".." in parts:
        raise ValueError(f"{name} must not contain '..' path traversal")

    # Construct the full path and resolve it
    full_path = (repo_root / path_str).resolve()

    # Verify the resolved path is still within repo_root
    try:
        full_path.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"{name} resolves outside repository root") from exc

    return full_path


def _binding(session: Mapping[str, Any], task_id: str) -> UnifiedExecutionBinding:
    item = dict(session.get("unified_execution_bindings") or {}).get(task_id)
    if not isinstance(item, UnifiedExecutionBinding):
        raise ValueError("unified execution binding is not retained for this task")
    return item


def _intent(binding: UnifiedExecutionBinding) -> IntentPacket:
    raw = dict(binding.records["intent_packet"])
    authority = AuthorityEnvelope(**dict(raw.pop("authority")))
    for name in ("constraints", "prohibitions", "acceptance_criteria", "required_evidence"):
        raw[name] = tuple(raw[name])
    return IntentPacket(authority=authority, **raw)


def _envelope(binding: UnifiedExecutionBinding) -> ActCapsuleEnvelope:
    raw = dict(binding.records["act_capsule_envelope"])
    for name in (
        "allowed_files",
        "allowed_symbols",
        "prohibited_effects",
        "invariants",
        "allowed_tools",
        "acceptance_bundle",
        "legal_outcomes",
        "continuity_requirements",
    ):
        raw[name] = tuple(raw[name])
    return ActCapsuleEnvelope(**raw)


def _model_packet(binding: UnifiedExecutionBinding) -> ModelExecutionPacket:
    raw = dict(binding.records["model_execution_packet"])
    for name in (
        "prompt_structure",
        "evidence_refs",
        "context_order",
        "examples",
        "tools_available",
        "uncertainty_requirements",
        "stop_conditions",
        "disagreement_refs",
    ):
        raw[name] = tuple(raw[name])
    return ModelExecutionPacket(**raw)


def _prediction(value: Any) -> PredictionPacket:
    if isinstance(value, PredictionPacket):
        return value
    if value is None:
        raise ValueError("immutable P0 prediction is not retained for this task")
    raw = _mapping(value, "prediction")
    for name in ("expected_state_delta", "expected_evidence", "expected_risk"):
        raw[name] = tuple(raw[name])
    return PredictionPacket(**raw)


def _observation(value: Any) -> P1Observation:
    if isinstance(value, P1Observation):
        return value
    if value is None:
        raise ValueError("independent P1 observation is not retained for this task")
    raw = _mapping(value, "observation")
    for name in ("observed_state_delta", "observed_evidence_refs", "missing_measurements"):
        raw[name] = tuple(raw[name])
    return P1Observation(**raw)


@dataclass(frozen=True)
class CurrentReproofReceipt:
    """Immutable proof that continuity evidence still matches the current source."""

    reproof_id: str
    continuity_receipt_ref: str
    repository_head: str
    source_digest: str
    verifier_id: str
    verifier_evidence_refs: tuple[str, ...]
    verified_at: float
    reproof_digest: str
    version: str = CURRENT_REPROOF_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "reproof_id",
            "continuity_receipt_ref",
            "repository_head",
            "source_digest",
            "verifier_id",
            "reproof_digest",
        ):
            _required(getattr(self, name), name)
        object.__setattr__(
            self,
            "verifier_evidence_refs",
            _strings(self.verifier_evidence_refs, "verifier_evidence_refs", required=True),
        )
        object.__setattr__(self, "verified_at", _timestamp(self.verified_at, "verified_at"))
        if (
            self.version != CURRENT_REPROOF_VERSION
            or self.proposal_only is not True
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("current reproof authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.reproof_digest != expected or self.reproof_id != f"reproof_current_{expected}":
            raise ValueError("current reproof identity mismatch")

    def identity_payload(self) -> dict[str, Any]:
        """Return the canonical fields that determine this reproof receipt identity."""
        return {
            "continuity_receipt_ref": self.continuity_receipt_ref,
            "repository_head": self.repository_head,
            "source_digest": self.source_digest,
            "verifier_id": self.verifier_id,
            "verifier_evidence_refs": list(self.verifier_evidence_refs),
            "verified_at": self.verified_at,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the reproof receipt without changing its authority boundary."""
        return asdict(self)


@dataclass(frozen=True)
class HumanDispositionReceipt:
    """Immutable human or community decision over one current reproof receipt."""

    disposition_id: str
    continuity_receipt_ref: str
    current_reproof_ref: str
    actor_id: str
    actor_type: str
    disposition: str
    reason_ref: str
    created_at: float
    disposition_digest: str
    version: str = HUMAN_DISPOSITION_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "disposition_id",
            "continuity_receipt_ref",
            "current_reproof_ref",
            "actor_id",
            "actor_type",
            "disposition",
            "disposition_digest",
        ):
            _required(getattr(self, name), name)
        actor_type = self.actor_type.upper()
        if actor_type not in {ActorType.HUMAN.value, ActorType.COMMUNITY.value}:
            raise ValueError("disposition actor_type must be HUMAN or COMMUNITY")
        object.__setattr__(self, "actor_type", actor_type)
        disposition = self.disposition.upper()
        if disposition not in _ALLOWED_DISPOSITIONS:
            raise ValueError("unsupported human or community disposition")
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "reason_ref", _optional(self.reason_ref, "reason_ref"))
        object.__setattr__(self, "created_at", _timestamp(self.created_at, "created_at"))
        if (
            self.version != HUMAN_DISPOSITION_VERSION
            or self.proposal_only is not True
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("human disposition authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.disposition_digest != expected or self.disposition_id != f"disposition_{expected}":
            raise ValueError("human disposition identity mismatch")

    def identity_payload(self) -> dict[str, Any]:
        """Return the canonical fields that determine this disposition identity."""
        return {
            "continuity_receipt_ref": self.continuity_receipt_ref,
            "current_reproof_ref": self.current_reproof_ref,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "disposition": self.disposition,
            "reason_ref": self.reason_ref,
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the disposition receipt without granting promotion authority."""
        return asdict(self)


def compile_current_reproof(
    *,
    repo_root: str | Path,
    binding: UnifiedExecutionBinding,
    continuity_receipt: ContinuitySensitivityReceipt,
    verifier_id: str,
    verifier_evidence_refs: Sequence[str],
    verified_at: float | None = None,
) -> CurrentReproofReceipt:
    """Compile exact-head reproof after independent P1 observation."""
    root = Path(repo_root).resolve()
    if not isinstance(binding, UnifiedExecutionBinding):
        raise ValueError("binding must use canonical UnifiedExecutionBinding")
    if not isinstance(continuity_receipt, ContinuitySensitivityReceipt):
        raise ValueError("continuity_receipt must use the canonical owner")
    head = _required(_git(root, "rev-parse", "HEAD"), "repository_head")
    envelope = _envelope(binding)
    source_digest = _source_digest(root, envelope.allowed_files)
    if head != continuity_receipt.repository_head:
        raise ValueError("current reproof repository head differs from continuity evidence")
    if source_digest != continuity_receipt.source_digest:
        raise ValueError("current reproof source digest differs from continuity evidence")
    verifier = _required(verifier_id, "verifier_id")
    if verifier == continuity_receipt.producer_id:
        raise ValueError("continuity producer cannot perform current reproof")
    evidence = _strings(verifier_evidence_refs, "verifier_evidence_refs", required=True)
    timestamp = _current_timestamp(verified_at, "verified_at")
    identity = {
        "continuity_receipt_ref": continuity_receipt.receipt_id,
        "repository_head": head,
        "source_digest": source_digest,
        "verifier_id": verifier,
        "verifier_evidence_refs": list(evidence),
        "verified_at": timestamp,
    }
    digest = stable_digest(identity)
    return CurrentReproofReceipt(
        reproof_id=f"reproof_current_{digest}",
        reproof_digest=digest,
        **identity,
    )


def compile_human_disposition(
    *,
    continuity_receipt: ContinuitySensitivityReceipt,
    current_reproof: CurrentReproofReceipt,
    actor_id: str,
    actor_type: ActorType | str,
    disposition: str,
    reason_ref: str = "",
    created_at: float | None = None,
) -> HumanDispositionReceipt:
    """Compile a mandatory human or community disposition after current reproof."""
    if current_reproof.continuity_receipt_ref != continuity_receipt.receipt_id:
        raise ValueError("human disposition reproof differs from continuity evidence")
    actor_value = actor_type.value if isinstance(actor_type, ActorType) else str(actor_type).upper()
    timestamp = _current_timestamp(created_at, "created_at")
    if timestamp <= current_reproof.verified_at:
        raise ValueError("human or community disposition must occur after current reproof")
    identity = {
        "continuity_receipt_ref": continuity_receipt.receipt_id,
        "current_reproof_ref": current_reproof.reproof_id,
        "actor_id": _required(actor_id, "actor_id"),
        "actor_type": actor_value,
        "disposition": _required(disposition, "disposition").upper(),
        "reason_ref": _optional(reason_ref, "reason_ref"),
        "created_at": timestamp,
    }
    digest = stable_digest(identity)
    return HumanDispositionReceipt(
        disposition_id=f"disposition_{digest}",
        disposition_digest=digest,
        **identity,
    )


def _proposal(value: Any) -> CrystallizationProposal:
    if isinstance(value, CrystallizationProposal):
        return value
    raw = _mapping(value, "crucible_proposal")
    raw.pop("proposal_digest", None)
    for name in ("train_experience_ids", "validation_experience_ids", "shadow_experience_ids"):
        raw[name] = tuple(raw[name])
    return CrystallizationProposal(**raw)


@dataclass(frozen=True)
class CrucibleProposalBindingReceipt:
    """Immutable reference-only binding between a Crucible proposal and execution."""

    binding_receipt_id: str
    proposal_id: str
    proposal_digest: str
    execution_binding_id: str
    plan_phase_hash: str
    task_id: str
    repository_head: str
    source_digest: str
    bound_at: float
    binding_receipt_digest: str
    version: str = CRUCIBLE_BINDING_VERSION
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "binding_receipt_id",
            "proposal_id",
            "proposal_digest",
            "execution_binding_id",
            "plan_phase_hash",
            "task_id",
            "repository_head",
            "source_digest",
            "binding_receipt_digest",
        ):
            _required(getattr(self, name), name)
        object.__setattr__(self, "bound_at", _timestamp(self.bound_at, "bound_at"))
        if (
            self.version != CRUCIBLE_BINDING_VERSION
            or self.proposal_only is not True
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("Crucible binding authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.binding_receipt_digest != expected or self.binding_receipt_id != f"crucible_binding_{expected}":
            raise ValueError("Crucible binding receipt identity mismatch")

    def identity_payload(self) -> dict[str, Any]:
        """Return the canonical fields that determine this binding identity."""
        return {
            "proposal_id": self.proposal_id,
            "proposal_digest": self.proposal_digest,
            "execution_binding_id": self.execution_binding_id,
            "plan_phase_hash": self.plan_phase_hash,
            "task_id": self.task_id,
            "repository_head": self.repository_head,
            "source_digest": self.source_digest,
            "bound_at": self.bound_at,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the proposal binding without mutating the canonical proposal."""
        return asdict(self)


def bind_crucible_proposal(
    proposal: CrystallizationProposal | Mapping[str, Any],
    binding: UnifiedExecutionBinding,
    *,
    bound_at: float | None = None,
) -> CrucibleProposalBindingReceipt:
    """Bind an unchanged canonical Crucible proposal to one exact execution binding."""
    item = _proposal(proposal)
    if not isinstance(binding, UnifiedExecutionBinding):
        raise ValueError("binding must use canonical UnifiedExecutionBinding")
    if item.status != CRYSTALLIZATION_PROPOSED:
        raise ValueError("Crucible proposal must remain proposal-only")
    timestamp = _current_timestamp(bound_at, "crucible_bound_at")
    if item.created_at > timestamp:
        raise ValueError("Crucible proposal cannot be bound before it was created")
    packet = dict(binding.records["model_execution_packet"])
    proposal_digest = _required(item.to_dict().get("proposal_digest"), "proposal_digest")
    identity = {
        "proposal_id": item.proposal_id,
        "proposal_digest": proposal_digest,
        "execution_binding_id": binding.binding_id,
        "plan_phase_hash": binding.plan_phase_hash,
        "task_id": binding.task_id,
        "repository_head": _required(packet.get("repository_head"), "repository_head"),
        "source_digest": _required(packet.get("source_digest"), "source_digest"),
        "bound_at": timestamp,
    }
    digest = stable_digest(identity)
    return CrucibleProposalBindingReceipt(
        binding_receipt_id=f"crucible_binding_{digest}",
        binding_receipt_digest=digest,
        **identity,
    )


def record_bound_crucible_proposal(
    store: CrucibleStore,
    proposal: CrystallizationProposal | Mapping[str, Any],
    binding: UnifiedExecutionBinding,
    *,
    bound_at: float | None = None,
) -> tuple[CrystallizationProposal, CrucibleProposalBindingReceipt, dict[str, Any]]:
    """Store the unchanged canonical proposal, then compile a reference-only binding."""
    if not isinstance(store, CrucibleStore):
        raise ValueError("store must be a CrucibleStore")
    item = _proposal(proposal)
    result = store.record_proposal(item)
    if result.get("ok") is not True:
        raise ValueError(f"Crucible proposal storage failed: {result.get('reason') or 'unknown'}")
    retained = store.get_proposal(item.proposal_id)
    if retained is None:
        raise ValueError("Crucible proposal storage did not retain the proposal")
    retained_item = _proposal(retained)
    if retained_item.to_dict().get("proposal_digest") != item.to_dict().get("proposal_digest"):
        raise ValueError("retained Crucible proposal differs from the canonical proposal")
    receipt = bind_crucible_proposal(retained_item, binding, bound_at=bound_at)
    return retained_item, receipt, result


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value


def commit_bridge_prediction(
    bridge: Any,
    *,
    plan_phase_hash: str,
    task_id: str,
    contract: Mapping[str, Any],
) -> PredictionPacket:
    """Commit one immutable P0 after canonical proposal storage and binding."""
    if not isinstance(contract, Mapping):
        raise ValueError("prediction contract must be an object")
    phase = _required(plan_phase_hash, "plan_phase_hash")
    task = _required(task_id, "task_id")
    session = bridge._require_session(phase)
    binding = _binding(session, task)
    predictions = session.setdefault("unified_prediction_packets", {})
    if task in predictions:
        raise ValueError("immutable P0 is already retained for this task")
    repo_root = Path(bridge.repo_root).resolve()
    storage = _mapping(contract.get("storage") or {}, "storage")
    crucible_path = _validate_storage_path(repo_root, storage.get("crucible_db_path"), "crucible_db_path")
    with CrucibleStore(repo_root, db_path=crucible_path) as crucible_store:
        proposal, proposal_binding, proposal_storage = record_bound_crucible_proposal(
            crucible_store,
            contract.get("crucible_proposal"),
            binding,
            bound_at=contract.get("crucible_bound_at"),
        )
    committed_at = _current_timestamp(contract.get("committed_at"), "committed_at")
    if committed_at <= proposal_binding.bound_at:
        raise ValueError("P0 commitment must occur strictly after Crucible proposal binding")
    prediction = commit_prediction(
        intent=_intent(binding),
        act_envelope=_envelope(binding),
        model_execution_packet=_model_packet(binding),
        current_state_digest=_required(contract.get("current_state_digest"), "current_state_digest"),
        prompt_runtime_digest=_required(contract.get("prompt_runtime_digest"), "prompt_runtime_digest"),
        proposed_transition=_required(contract.get("proposed_transition"), "proposed_transition"),
        expected_state_delta=_strings(contract.get("expected_state_delta"), "expected_state_delta", required=True),
        expected_evidence=_strings(contract.get("expected_evidence"), "expected_evidence", required=True),
        expected_cost=_mapping(contract.get("expected_cost"), "expected_cost"),
        expected_risk=_strings(contract.get("expected_risk"), "expected_risk", required=True),
        producer_id=_required(contract.get("producer_id"), "producer_id"),
        committed_at=committed_at,
    )
    session.setdefault("unified_crucible_proposals", {})[task] = proposal
    session.setdefault("unified_crucible_bindings", {})[task] = proposal_binding
    session.setdefault("unified_crucible_proposal_storage", {})[task] = proposal_storage
    predictions[task] = prediction
    return prediction


def observe_bridge_prediction(
    bridge: Any,
    *,
    plan_phase_hash: str,
    task_id: str,
    observation: Mapping[str, Any],
) -> P1Observation:
    """Record one immutable independent P1 observation for a retained P0."""
    if not isinstance(observation, Mapping):
        raise ValueError("observation must be an object")
    phase = _required(plan_phase_hash, "plan_phase_hash")
    task = _required(task_id, "task_id")
    session = bridge._require_session(phase)
    binding = _binding(session, task)
    observations = session.setdefault("unified_p1_observations", {})
    if task in observations:
        raise ValueError("independent P1 observation is already retained for this task")
    prediction = _prediction(dict(session.get("unified_prediction_packets") or {}).get(task))
    root = Path(bridge.repo_root).resolve()
    head = _required(_git(root, "rev-parse", "HEAD"), "repository_head")
    source_digest = _source_digest(root, _envelope(binding).allowed_files)
    result = observe_prediction(
        prediction=prediction,
        p0_digest=prediction.p0_digest,
        objective_digest=prediction.objective_digest,
        purpose_digest=prediction.purpose_digest,
        repository_head=head,
        source_digest=source_digest,
        observed_state_delta=_strings(observation.get("observed_state_delta"), "observed_state_delta"),
        observed_evidence_refs=_strings(
            observation.get("observed_evidence_refs"), "observed_evidence_refs", required=True
        ),
        observed_cost=_mapping(observation.get("observed_cost"), "observed_cost"),
        missing_measurements=_strings(observation.get("missing_measurements"), "missing_measurements"),
        observer_id=_required(observation.get("observer_id"), "observer_id"),
        observed_at=observation.get("observed_at"),
    )
    observations[task] = result
    return result


def finalize_bridge_learning(
    bridge: Any,
    *,
    plan_phase_hash: str,
    task_id: str,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Finalize governed learning only after P0, P1, reproof, and disposition."""
    if not isinstance(contract, Mapping):
        raise ValueError("learning contract must be an object")
    phase = _required(plan_phase_hash, "plan_phase_hash")
    task = _required(task_id, "task_id")
    session = bridge._require_session(phase)
    binding = _binding(session, task)
    prediction = _prediction(dict(session.get("unified_prediction_packets") or {}).get(task))
    observation = _observation(dict(session.get("unified_p1_observations") or {}).get(task))
    learning_results = session.setdefault("unified_learning_results", {})
    if task in learning_results:
        raise ValueError("governed learning result is already retained for this task")
    root = Path(bridge.repo_root).resolve()
    head = _required(_git(root, "rev-parse", "HEAD"), "repository_head")
    source_digest = _source_digest(root, _envelope(binding).allowed_files)
    packet = _model_packet(binding)
    disposition_requirement_ref = _required(
        contract.get("human_disposition_requirement_ref"),
        "human_disposition_requirement_ref",
    )
    receipt = derive_continuity_sensitivity_receipt(
        prediction=prediction,
        observation=observation,
        current_repository_head=head,
        current_source_digest=source_digest,
        model_profile_digest=packet.model_profile_digest,
        model_execution_packet_digest=packet.packet_digest,
        prompt_runtime_digest=prediction.prompt_runtime_digest,
        error_class=str(contract.get("error_class") or "UNRESOLVED"),
        prediction_error=_strings(contract.get("prediction_error"), "prediction_error"),
        consequence_dimensions=_strings(
            contract.get("consequence_dimensions"), "consequence_dimensions", required=True
        ),
        protected_pathways=_strings(contract.get("protected_pathways"), "protected_pathways", required=True),
        mutation_budget=_strings(contract.get("mutation_budget"), "mutation_budget", required=True),
        replay_burden=_strings(contract.get("replay_burden"), "replay_burden", required=True),
        raw_evidence_refs=_strings(contract.get("raw_evidence_refs"), "raw_evidence_refs", required=True),
        replacement_candidate_refs=_strings(contract.get("replacement_candidate_refs"), "replacement_candidate_refs"),
        uncertainty=contract.get("uncertainty", 1.0),
        producer_id=_required(contract.get("receipt_producer_id"), "receipt_producer_id"),
        independent_verifier_id=observation.observer_id,
        verifier_evidence_refs=_strings(
            contract.get("verifier_evidence_refs"), "verifier_evidence_refs", required=True
        ),
        human_disposition_ref=disposition_requirement_ref,
    )

    storage = _mapping(contract.get("storage") or {}, "storage")
    experience_path = _validate_storage_path(root, storage.get("experience_db_path"), "experience_db_path")
    qdkt_event_root_raw = storage.get("qdkt_event_root")
    qdkt_event_root = (
        _validate_storage_path(root, qdkt_event_root_raw, "qdkt_event_root")
        if qdkt_event_root_raw is not None
        else root / "Aura_Memory" / "qdkt_governed_events"
    )
    attempt_archive_path = _validate_storage_path(root, storage.get("attempt_archive_db_path"), "attempt_archive_db_path")
    proposal = dict(session.get("unified_crucible_proposals") or {}).get(task)
    if not isinstance(proposal, CrystallizationProposal):
        raise ValueError("bounded Crucible proposal was not staged before P0")
    proposal_binding = dict(session.get("unified_crucible_bindings") or {}).get(task)
    if not isinstance(proposal_binding, CrucibleProposalBindingReceipt):
        raise ValueError("Crucible proposal lacks an exact execution binding receipt")
    proposal_storage = dict(session.get("unified_crucible_proposal_storage") or {}).get(task)
    if not isinstance(proposal_storage, Mapping) or proposal_storage.get("ok") is not True:
        raise ValueError("bounded Crucible proposal lacks successful canonical storage")
    packet_binding = dict(binding.records["model_execution_packet"])
    expected_proposal_bindings = {
        "proposal_id": proposal.proposal_id,
        "proposal_digest": proposal.to_dict().get("proposal_digest"),
        "execution_binding_id": binding.binding_id,
        "plan_phase_hash": phase,
        "task_id": task,
        "repository_head": head,
        "source_digest": packet_binding.get("source_digest"),
    }
    for name, expected in expected_proposal_bindings.items():
        if getattr(proposal_binding, name) != expected:
            raise ValueError(f"Crucible proposal binding {name} is stale or mismatched")
    if proposal_binding.bound_at >= prediction.committed_at:
        raise ValueError("Crucible proposal binding must precede committed P0")

    reproof = compile_current_reproof(
        repo_root=root,
        binding=binding,
        continuity_receipt=receipt,
        verifier_id=_required(contract.get("reproof_verifier_id"), "reproof_verifier_id"),
        verifier_evidence_refs=_strings(contract.get("reproof_evidence_refs"), "reproof_evidence_refs", required=True),
        verified_at=contract.get("reproof_verified_at"),
    )
    if reproof.verified_at <= observation.observed_at:
        raise ValueError("current reproof must occur strictly after P1 observation")
    disposition = compile_human_disposition(
        continuity_receipt=receipt,
        current_reproof=reproof,
        actor_id=_required(contract.get("disposition_actor_id"), "disposition_actor_id"),
        actor_type=_required(contract.get("disposition_actor_type"), "disposition_actor_type"),
        disposition=_required(contract.get("human_disposition"), "human_disposition"),
        reason_ref=str(contract.get("disposition_reason_ref") or ""),
        created_at=contract.get("disposition_created_at"),
    )
    learning = evaluate_learning_to_reproof(
        relationship_id=_required(contract.get("relationship_id"), "relationship_id"),
        relationship_digest=_required(contract.get("relationship_digest"), "relationship_digest"),
        repository_head=head,
        current_source_digest=source_digest,
        continuity_receipt=receipt,
        crucible_proposal_ref=proposal.proposal_id,
        current_reproof_ref=reproof.reproof_id,
        independent_verifier_ref=receipt.independent_verifier_id,
        human_disposition=disposition.disposition,
        human_disposition_ref=disposition.disposition_id,
        extra_blockers=_strings(contract.get("extra_blockers"), "extra_blockers"),
    )

    outcome = _required(contract.get("outcome"), "outcome").upper()
    if outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("unsupported unified learning outcome")
    relationship: RelationshipExperienceObservation | None = None
    relationship_storage: dict[str, Any] = {
        "ok": False,
        "reason": "learning_reproof_not_eligible",
    }
    if learning.eligible_for_relationship_experience:
        verifier_refs = tuple(
            dict.fromkeys(
                [
                    receipt.independent_verifier_id,
                    *receipt.verifier_evidence_refs,
                    *reproof.verifier_evidence_refs,
                ]
            )
        )
        relationship_recorded_at = _current_timestamp(
            contract.get("relationship_recorded_at"), "relationship_recorded_at"
        )
        if relationship_recorded_at <= disposition.created_at:
            raise ValueError("Relationship Experience must be recorded after disposition")
        relationship = RelationshipExperienceObservation.create(
            **relationship_experience_kwargs(
                decision=learning,
                outcome=outcome,
                verifier_evidence_refs=verifier_refs,
                receipt_refs=(
                    receipt.receipt_id,
                    proposal.proposal_id,
                    reproof.reproof_id,
                    disposition.disposition_id,
                ),
                source_refs=_strings(contract.get("source_refs"), "source_refs", required=True),
                working_tree_digest=_required(
                    dict(binding.records["model_execution_packet"]).get("working_tree_digest"),
                    "working_tree_digest",
                ),
                privacy_class=str(contract.get("privacy_class") or "PROJECT"),
                objective_digest=receipt.objective_digest,
                reason=str(contract.get("reason") or ""),
            ),
            transaction_time=relationship_recorded_at,
        )
        with ArenaExperienceLedger(root, db_path=experience_path) as ledger:
            relationship_storage = ledger.record_relationship_observation(relationship)
        if relationship_storage.get("ok") is not True:
            raise ValueError(
                f"Relationship Experience storage failed: {relationship_storage.get('reason') or 'unknown'}"
            )

    admission = evaluate_qdkt_consequential_admission(
        continuity_receipt=receipt,
        learning_decision=learning,
        relationship_experience=relationship,
        raw_evidence_refs=_strings(contract.get("raw_evidence_refs"), "raw_evidence_refs", required=True),
        current_repository_head=head,
        current_source_digest=source_digest,
        purpose_compatible=_strict_bool(contract.get("purpose_compatible"), "purpose_compatible"),
        privacy_compatible=_strict_bool(contract.get("privacy_compatible"), "privacy_compatible"),
        consent_compatible=_strict_bool(contract.get("consent_compatible"), "consent_compatible"),
        sovereignty_compatible=_strict_bool(contract.get("sovereignty_compatible"), "sovereignty_compatible"),
        extra_blockers=_strings(contract.get("qdkt_extra_blockers"), "qdkt_extra_blockers"),
    )

    qdkt_receipt: dict[str, Any] | None = None
    if admission.admitted:
        if relationship is None:
            raise ValueError("QDKT admission cannot exist without Relationship Experience")
        qdkt_created_at = _current_timestamp(contract.get("qdkt_created_at"), "qdkt_created_at")
        if qdkt_created_at <= relationship.transaction_time:
            raise ValueError("governed QDKT observation must occur after Relationship Experience")
        event_store = AppendOnlyEventStore(qdkt_event_root)
        event_receipt = record_relationship_experience_advisory(
            event_store,
            relationship,
            admission,
            trace_id=_required(contract.get("trace_id"), "trace_id"),
            actor_id=_required(contract.get("qdkt_actor_id"), "qdkt_actor_id"),
            purpose_digest=receipt.purpose_digest,
            parent_event_ids=_strings(contract.get("parent_event_ids"), "parent_event_ids"),
            evidence_refs=tuple(
                dict.fromkeys(
                    [
                        *receipt.raw_evidence_refs,
                        receipt.receipt_id,
                        proposal.proposal_id,
                        reproof.reproof_id,
                        disposition.disposition_id,
                    ]
                )
            ),
            arena_id=str(contract.get("arena_id") or "coding"),
            objective_id=receipt.objective_digest,
            created_at=qdkt_created_at,
        )
        if event_receipt.appended is not True:
            raise ValueError("governed QDKT event was not appended to the event store")
        qdkt_receipt = {
            "appended": event_receipt.appended,
            "event": event_receipt.event.to_dict(),
            "payload_ref": event_receipt.payload_ref.to_dict(),
            "projection": event_receipt.projection,
            "automatic_crystallization": False,
        }

    result = {
        "version": LEARNING_RUNTIME_VERSION,
        "ok": True,
        "plan_phase_hash": phase,
        "task_id": task,
        "prediction": prediction.to_dict(),
        "observation": observation.to_dict(),
        "continuity_receipt": receipt.to_dict(),
        "crucible_proposal_ref": proposal.proposal_id,
        "crucible_binding": proposal_binding.to_dict(),
        "crucible_storage": proposal_storage,
        "current_reproof": reproof.to_dict(),
        "human_disposition": disposition.to_dict(),
        "learning_decision": learning.to_dict(),
        "relationship_experience": relationship.to_dict() if relationship is not None else None,
        "relationship_storage": relationship_storage,
        "qdkt_admission": admission.to_dict(),
        "qdkt_event_receipt": qdkt_receipt,
        "automatic_crystallization": False,
        "automatic_promotion": False,
        "production_mutation": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }

    archive = ArenaAttemptArchive(root, db_path=attempt_archive_path)
    try:
        archive_result = archive.record(
            arena_id=str(contract.get("arena_id") or "coding"),
            route="unified-memory-continuity/learning-to-reproof",
            request={
                "action_id": "complete_unified_learning_cycle",
                "plan_phase_hash": phase,
                "task_id": task,
                "outcome": outcome,
                "continuity_receipt_ref": receipt.receipt_id,
            },
            result={
                "ok": outcome == "SUCCESS",
                "status": outcome,
                "learning_eligible": learning.eligible_for_relationship_experience,
                "qdkt_admitted": admission.admitted,
                "blockers": list(admission.blockers),
            },
            workflow_state={
                "workflow_id": phase,
                "current_phase": "LEARNING_TO_REPROOF",
                "objective": dict(binding.records["intent_packet"]).get("objective", ""),
            },
            archive_context={
                "stage_hint": "U7",
                "binding_id": binding.binding_id,
                "crucible_binding_ref": proposal_binding.binding_receipt_id,
                "continuity_receipt_ref": receipt.receipt_id,
                "current_reproof_ref": reproof.reproof_id,
                "human_disposition_ref": disposition.disposition_id,
            },
        )
    finally:
        archive.close()
    result["attempt_archive"] = archive_result

    session.setdefault("unified_continuity_receipts", {})[task] = receipt
    session.setdefault("unified_current_reproofs", {})[task] = reproof
    session.setdefault("unified_human_dispositions", {})[task] = disposition
    session.setdefault("unified_learning_decisions", {})[task] = learning
    session.setdefault("unified_relationship_experiences", {})[task] = relationship
    session.setdefault("unified_qdkt_admissions", {})[task] = admission
    learning_results[task] = result
    return result


__all__ = [
    "CRUCIBLE_BINDING_VERSION",
    "CURRENT_REPROOF_VERSION",
    "HUMAN_DISPOSITION_VERSION",
    "LEARNING_RUNTIME_VERSION",
    "CrucibleProposalBindingReceipt",
    "CurrentReproofReceipt",
    "HumanDispositionReceipt",
    "bind_crucible_proposal",
    "commit_bridge_prediction",
    "compile_current_reproof",
    "compile_human_disposition",
    "finalize_bridge_learning",
    "observe_bridge_prediction",
    "record_bound_crucible_proposal",
]
