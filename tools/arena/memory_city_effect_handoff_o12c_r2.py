from __future__ import annotations

"""Strict D0 owner-bound READ -> effect-refinement -> mutation -> TECC seam.

This module deliberately does not reconstruct the canonical PR878 ReadWorldBinding
identity or PR887 effect-refinement identity. Those are owner-produced identities.
It only admits them when they are cross-bound to current owner receipts and exact
runtime/mutation evidence. A valid effect-bound request remains HOLD_TECC_REQUIRED_D0.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

SCHEMA = "AURA-MEMORY-CITY-OWNER-BOUND-EFFECT-HANDOFF-v1"
READ_CERT_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-CERT-v1"
READ_CONSEQUENCE_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-v1"
ADMISSION_SCHEMA = "AURA-MEMORY-CITY-PROOF-CARRYING-TYPED-ADMISSION-v2"
TECC_SCHEMA = "AURA-TECC-v1"
D0 = "D0_NONPROMOTING"


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


def _nn(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be nonnegative exact int")
    return value


def _status(obj) -> str | None:
    raw = getattr(obj, "status", None)
    if raw is None:
        raw = getattr(obj, "disposition", None)
    return getattr(raw, "value", raw)


def _explicit_false_object(obj, fields: tuple[str, ...]) -> bool:
    return all(hasattr(obj, field) and getattr(obj, field) is False for field in fields)


def _explicit_false_mapping(obj: Mapping[str, object], fields: tuple[str, ...]) -> bool:
    return all(field in obj and obj[field] is False for field in fields)


class HandoffDisposition(str, Enum):
    HOLD = "HOLD"
    REBIND_REQUIRED = "REBIND_REQUIRED"
    HOLD_TECC_REQUIRED_D0 = "HOLD_TECC_REQUIRED_D0"


@dataclass(frozen=True)
class ReadOwnerBindingEvidence:
    active_read_binding_root: str
    current_read_use_root: str
    read_owner_receipt_root: str
    read_certificate_schema: str = READ_CERT_SCHEMA
    authority: str = D0
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for field in ("active_read_binding_root", "current_read_use_root", "read_owner_receipt_root"):
            _root(getattr(self, field), field)
        if self.read_certificate_schema != READ_CERT_SCHEMA:
            raise ValueError("read_certificate_schema must be canonical")
        if self.authority != D0 or self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("read-owner evidence cannot widen D0 authority")


@dataclass(frozen=True)
class EffectRefinementEvidence:
    selected_read_binding_root: str
    intent_binding_root: str
    effect_escalation_root: str
    refinement_plan_root: str
    effect_obligation_root: str
    refinement_owner_receipt_root: str
    authority: str = D0
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for field in (
            "selected_read_binding_root", "intent_binding_root", "effect_escalation_root",
            "refinement_plan_root", "effect_obligation_root", "refinement_owner_receipt_root",
        ):
            _root(getattr(self, field), field)
        if self.authority != D0 or self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("effect-refinement evidence cannot widen D0 authority")


@dataclass(frozen=True)
class MutationBoundaryProjection:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    installed_fence_generation: int
    holder: str
    expires_at: int
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str

    def __post_init__(self) -> None:
        _id(self.cell_id, "cell_id")
        _id(self.holder, "holder")
        _nn(self.revision, "revision")
        _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation")
        _nn(self.installed_fence_generation, "installed_fence_generation")
        _nn(self.expires_at, "expires_at")
        for field in ("configuration_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, field), field)

    @property
    def boundary_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "mutation_boundary",
            "cell_id": self.cell_id,
            "revision": self.revision,
            "configuration_root": self.configuration_root,
            "support_epoch": self.support_epoch,
            "fence_generation": self.fence_generation,
            "installed_fence_generation": self.installed_fence_generation,
            "holder": self.holder,
            "expires_at": self.expires_at,
            "transition_authority_receipt_root": self.transition_authority_receipt_root,
            "resource_fence_receipt_root": self.resource_fence_receipt_root,
        })


@dataclass(frozen=True)
class StrictVerificationContext:
    active_read_binding_root: str
    current_read_use_root: str
    read_owner_receipt_root: str
    intent_binding_root: str
    effect_escalation_root: str
    refinement_owner_receipt_root: str
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    installed_fence_generation: int
    holder: str
    owner_evidence_root: str
    verifier_receipt_root: str
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str
    nuisance_context_root: str
    now: int

    def __post_init__(self) -> None:
        for field in (
            "active_read_binding_root", "current_read_use_root", "read_owner_receipt_root",
            "intent_binding_root", "effect_escalation_root", "refinement_owner_receipt_root",
            "configuration_root", "owner_evidence_root", "verifier_receipt_root",
            "transition_authority_receipt_root", "resource_fence_receipt_root", "nuisance_context_root",
        ):
            _root(getattr(self, field), field)
        _id(self.cell_id, "cell_id")
        _id(self.holder, "holder")
        _nn(self.revision, "revision")
        _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation")
        _nn(self.installed_fence_generation, "installed_fence_generation")
        _nn(self.now, "now")


@dataclass(frozen=True)
class EffectHandoffEvidence:
    owner_evidence_root: str
    verifier_receipt_root: str

    def __post_init__(self) -> None:
        _root(self.owner_evidence_root, "owner_evidence_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")


@dataclass(frozen=True)
class HandoffDecision:
    disposition: HandoffDisposition
    reason: str
    semantic_handoff_root: str | None = None
    tecc_input_root: str | None = None
    required_verifier_schema: str | None = None
    authority: str = D0
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        if self.semantic_handoff_root is not None:
            _root(self.semantic_handoff_root, "semantic_handoff_root")
        if self.tecc_input_root is not None:
            _root(self.tecc_input_root, "tecc_input_root")
        if self.authority != D0 or self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("D0 handoff cannot mint authority")


def _canonical_consequence_root(hydration, typed_closure) -> str:
    semantics = getattr(typed_closure, "reproof_semantics", None)
    if not isinstance(semantics, str) or not semantics:
        raise ValueError("typed reproof semantics required")
    transition = _root(getattr(typed_closure, "transition_model_root", None), "transition_model_root")
    horizon = _nn(getattr(typed_closure, "horizon", None), "horizon")
    future = getattr(typed_closure, "future_congruence_root", None)
    if horizon > 0:
        _root(future, "future_congruence_root")
    elif future is not None:
        _root(future, "future_congruence_root")
    return digest({
        "schema": READ_CONSEQUENCE_SCHEMA,
        "hydration_cut": tuple(getattr(hydration, "support_cut", ())),
        "reproof": tuple(getattr(typed_closure, "reproof_item_ids", ())),
        "reproof_semantics": semantics,
        "transition_model_root": transition,
        "horizon": horizon,
        "future_congruence_root": future,
    })


def _strict_read_current(read_cert, read_use, hydration, typed_closure,
                         read_owner: ReadOwnerBindingEvidence,
                         verification: StrictVerificationContext) -> tuple[bool, str, str | None]:
    if not isinstance(read_owner, ReadOwnerBindingEvidence):
        return False, "READ_OWNER_EVIDENCE_REQUIRED", None
    if _status(read_cert) != "READY_D0" or _status(read_use) != "READY_D0":
        return False, "READ_CONSEQUENCE_NOT_READY", None
    if not _explicit_false_object(read_cert, ("mutation_authority", "effect_authority", "gate10")):
        return False, "READ_CERTIFICATE_AUTHORITY_ESCALATION", None
    if not _explicit_false_object(read_use, ("mutation_authority", "effect_authority", "gate10")):
        return False, "READ_USE_AUTHORITY_ESCALATION", None
    cert_receipt = _root(getattr(read_cert, "receipt_root", None), "read_certificate_root")
    _root(getattr(read_cert, "coverage_receipt_root", None), "coverage_receipt_root")
    cert_consequence = _root(getattr(read_cert, "consequence_root", None), "consequence_root")
    if getattr(read_use, "certificate_root", None) != cert_receipt:
        return False, "READ_USE_CERTIFICATE_MOVED", None
    if read_owner.active_read_binding_root != verification.active_read_binding_root:
        return False, "READ_OWNER_BINDING_MOVED", None
    if read_owner.current_read_use_root != verification.current_read_use_root:
        return False, "CURRENT_READ_USE_MOVED", None
    if read_owner.read_owner_receipt_root != verification.read_owner_receipt_root:
        return False, "READ_OWNER_RECEIPT_STALE", None
    if read_owner.active_read_binding_root not in tuple(getattr(read_cert, "binding_roots", ())):
        return False, "ACTIVE_READ_WORLD_NOT_CERTIFIED", None
    if getattr(hydration, "status", None) != "READY_SUPPORT_CLOSED_HYDRATION_D0":
        return False, "ACTIVE_HYDRATION_NOT_READY", None
    if _status(typed_closure) != "READY_D0":
        return False, "ACTIVE_TYPED_CLOSURE_NOT_READY", None
    if getattr(hydration, "receipt_root", None) not in tuple(getattr(read_cert, "member_hydration_receipt_roots", ())):
        return False, "ACTIVE_HYDRATION_RECEIPT_NOT_CERTIFIED", None
    if getattr(hydration, "support_root", None) not in tuple(getattr(read_cert, "member_support_roots", ())):
        return False, "ACTIVE_SUPPORT_ROOT_NOT_CERTIFIED", None
    if tuple(getattr(hydration, "support_cut", ())) != tuple(getattr(read_cert, "hydration_cut", ())):
        return False, "ACTIVE_HYDRATION_CONSEQUENCE_MOVED", None
    if tuple(getattr(typed_closure, "reproof_item_ids", ())) != tuple(getattr(read_cert, "reproof_item_ids", ())):
        return False, "ACTIVE_COMPONENT_REPROOF_MOVED", None
    if (getattr(typed_closure, "transition_model_root", None), getattr(typed_closure, "horizon", None), getattr(typed_closure, "future_congruence_root", None)) != (
        getattr(read_cert, "transition_model_root", None), getattr(read_cert, "horizon", None), getattr(read_cert, "future_congruence_root", None)
    ):
        return False, "ACTIVE_TRANSITION_CONSEQUENCE_MOVED", None
    if _canonical_consequence_root(hydration, typed_closure) != cert_consequence:
        return False, "READ_CONSEQUENCE_ROOT_SUBSTITUTED", None
    semantic = digest({
        "schema": SCHEMA,
        "kind": "owner_bound_current_read",
        "read_certificate_root": cert_receipt,
        "active_read_binding_root": read_owner.active_read_binding_root,
        "current_read_use_root": read_owner.current_read_use_root,
        "read_owner_receipt_root": read_owner.read_owner_receipt_root,
        "consequence_root": cert_consequence,
        "typed_reproof_semantics": getattr(typed_closure, "reproof_semantics", None),
    })
    return True, "OWNER_BOUND_CURRENT_READ", semantic


def _strict_admission(admission: Mapping[str, object], read_cert, hydration, typed_closure) -> tuple[bool, str]:
    if not isinstance(admission, Mapping):
        return False, "ADMISSION_RECEIPT_REQUIRED"
    if admission.get("schema") != ADMISSION_SCHEMA:
        return False, "ADMISSION_SCHEMA_NOT_CANONICAL"
    authority_fields = ("authority_minted", "mutation_authority", "effect_authority", "gate10")
    if not _explicit_false_mapping(admission, authority_fields):
        return False, "ADMISSION_AUTHORITY_FIELDS_MISSING_OR_ESCALATED"
    if admission.get("admission_mode") != "EFFECT_BOUND":
        return False, "READ_ONLY_CANNOT_ENTER_EFFECT_HANDOFF"
    if admission.get("disposition") != "HOLD_TECC_REQUIRED_D0" or admission.get("required_verifier_schema") != TECC_SCHEMA:
        return False, "EFFECT_MODE_NOT_TECC_SEALED"
    expected = {
        "typed_closure_receipt_root": getattr(typed_closure, "receipt_root", None),
        "coverage_receipt_root": getattr(read_cert, "coverage_receipt_root", None),
        "support_root": getattr(hydration, "support_root", None),
        "influence_root": getattr(typed_closure, "influence_root", None),
        "transition_model_root": getattr(typed_closure, "transition_model_root", None),
        "horizon": getattr(typed_closure, "horizon", None),
        "future_congruence_root": getattr(typed_closure, "future_congruence_root", None),
    }
    for field, value in expected.items():
        if admission.get(field) != value:
            return False, f"ADMISSION_{field.upper()}_MOVED"
    receipt = admission.get("receipt_root")
    if not isinstance(receipt, str):
        return False, "ADMISSION_RECEIPT_ROOT_MISSING"
    try:
        _root(receipt, "admission_receipt_root")
    except ValueError:
        return False, "ADMISSION_RECEIPT_ROOT_MALFORMED"
    payload = dict(admission)
    payload.pop("receipt_root", None)
    if digest(payload) != receipt:
        return False, "ADMISSION_RECEIPT_ROOT_FORGED"
    return True, "CANONICAL_EFFECT_ADMISSION_CURRENT"


def _strict_refinement(refinement: EffectRefinementEvidence, read_owner: ReadOwnerBindingEvidence,
                       verification: StrictVerificationContext) -> tuple[bool, str]:
    if not isinstance(refinement, EffectRefinementEvidence):
        return False, "EFFECT_REFINEMENT_EVIDENCE_REQUIRED"
    if refinement.selected_read_binding_root != read_owner.active_read_binding_root:
        return False, "EFFECT_REFINEMENT_BINDING_DETACHED"
    if refinement.selected_read_binding_root != verification.active_read_binding_root:
        return False, "EFFECT_REFINEMENT_BINDING_MOVED"
    if refinement.intent_binding_root != verification.intent_binding_root:
        return False, "EFFECT_INTENT_MOVED"
    if refinement.effect_escalation_root != verification.effect_escalation_root:
        return False, "EFFECT_ESCALATION_MOVED"
    if refinement.refinement_owner_receipt_root != verification.refinement_owner_receipt_root:
        return False, "EFFECT_REFINEMENT_OWNER_RECEIPT_STALE"
    return True, "OWNER_BOUND_EFFECT_REFINEMENT"


def compile_effect_handoff_r2(read_cert, read_use, hydration, typed_closure,
                              read_owner: ReadOwnerBindingEvidence,
                              admission: Mapping[str, object],
                              refinement: EffectRefinementEvidence,
                              evidence: EffectHandoffEvidence,
                              mutation: MutationBoundaryProjection,
                              verification: StrictVerificationContext) -> HandoffDecision:
    """Strict owner-bound effect handoff. The only successful terminal is TECC HOLD."""
    read_ok, reason, semantic = _strict_read_current(read_cert, read_use, hydration, typed_closure, read_owner, verification)
    if not read_ok:
        disposition = HandoffDisposition.REBIND_REQUIRED if reason in {
            "READ_OWNER_BINDING_MOVED", "CURRENT_READ_USE_MOVED", "READ_OWNER_RECEIPT_STALE"
        } else HandoffDisposition.HOLD
        return HandoffDecision(disposition, reason)
    admission_ok, reason = _strict_admission(admission, read_cert, hydration, typed_closure)
    if not admission_ok:
        return HandoffDecision(HandoffDisposition.HOLD, reason, semantic)
    refinement_ok, reason = _strict_refinement(refinement, read_owner, verification)
    if not refinement_ok:
        disposition = HandoffDisposition.REBIND_REQUIRED if reason in {
            "EFFECT_REFINEMENT_BINDING_MOVED", "EFFECT_INTENT_MOVED", "EFFECT_ESCALATION_MOVED",
            "EFFECT_REFINEMENT_OWNER_RECEIPT_STALE"
        } else HandoffDisposition.HOLD
        return HandoffDecision(disposition, reason, semantic)
    if evidence.owner_evidence_root != verification.owner_evidence_root:
        return HandoffDecision(HandoffDisposition.HOLD, "OWNER_EVIDENCE_ROOT_STALE", semantic)
    if evidence.verifier_receipt_root != verification.verifier_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "VERIFIER_RECEIPT_ROOT_STALE", semantic)
    if mutation.cell_id != verification.cell_id:
        return HandoffDecision(HandoffDisposition.HOLD, "CELL_MISMATCH", semantic)
    if mutation.revision != verification.revision:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "REVISION_MOVED", semantic)
    if mutation.configuration_root != verification.configuration_root:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "CONFIGURATION_MOVED", semantic)
    if mutation.support_epoch != verification.support_epoch:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "SUPPORT_EPOCH_MOVED", semantic)
    if mutation.holder != verification.holder:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "LEASE_HOLDER_MOVED", semantic)
    if mutation.transition_authority_receipt_root != verification.transition_authority_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "TRANSITION_AUTHORITY_RECEIPT_STALE", semantic)
    if mutation.resource_fence_receipt_root != verification.resource_fence_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "RESOURCE_FENCE_RECEIPT_STALE", semantic)
    if mutation.fence_generation != verification.fence_generation:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "FENCE_GENERATION_MOVED", semantic)
    if mutation.installed_fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "INSTALLED_FENCE_RECEIPT_MISMATCH", semantic)
    if mutation.fence_generation != mutation.installed_fence_generation or verification.fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "FENCE_NOT_INSTALLED_CURRENT", semantic)
    if verification.now >= mutation.expires_at:
        return HandoffDecision(HandoffDisposition.HOLD, "LEASE_EXPIRED", semantic)
    tecc_input = digest({
        "schema": SCHEMA,
        "kind": "owner_bound_effect_refined_tecc_input",
        "semantic_handoff_root": semantic,
        "active_read_binding_root": read_owner.active_read_binding_root,
        "current_read_use_root": read_owner.current_read_use_root,
        "read_owner_receipt_root": read_owner.read_owner_receipt_root,
        "admission_receipt_root": admission["receipt_root"],
        "intent_binding_root": refinement.intent_binding_root,
        "effect_escalation_root": refinement.effect_escalation_root,
        "refinement_plan_root": refinement.refinement_plan_root,
        "effect_obligation_root": refinement.effect_obligation_root,
        "refinement_owner_receipt_root": refinement.refinement_owner_receipt_root,
        "mutation_boundary_root": mutation.boundary_root,
        "owner_evidence_root": evidence.owner_evidence_root,
        "verifier_receipt_root": evidence.verifier_receipt_root,
        "required_verifier_schema": TECC_SCHEMA,
        "authority_minted": False,
        "mutation_authority": False,
        "effect_authority": False,
        "gate10": False,
    })
    return HandoffDecision(
        HandoffDisposition.HOLD_TECC_REQUIRED_D0,
        "OWNER_BOUND_EFFECT_REFINEMENT_REQUIRES_INDEPENDENT_TECC",
        semantic,
        tecc_input,
        TECC_SCHEMA,
    )
