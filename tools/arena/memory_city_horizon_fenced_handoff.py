from __future__ import annotations

"""D0 mode-sealed semantic-to-effect handoff capsule.

Memory City may cross-bind a current read result to the exact mutation boundary,
but effect-bound use never becomes READY here. A fully current cross-binding is
emitted only as HOLD_TECC_REQUIRED_D0 with an exact TECC input root.

Migration rule: the read/effect seam must bind the same proof-algorithm identity
as the current read owner. An unchanged outer certificate schema is not enough
when reproof semantics change.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

SCHEMA = "AURA-MEMORY-CITY-HORIZON-FENCED-HANDOFF-v2"
READ_BINDING_SCHEMA = "AURA-MEMORY-CITY-READ-WORLD-BINDING-v1"
EXPECTED_REPROOF_SEMANTICS = "HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1"
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


class HandoffDisposition(str, Enum):
    HOLD = "HOLD"
    REBIND_REQUIRED = "REBIND_REQUIRED"
    HOLD_TECC_REQUIRED_D0 = "HOLD_TECC_REQUIRED_D0"


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

    def __post_init__(self):
        _id(self.cell_id, "cell_id")
        _id(self.holder, "holder")
        _nn(self.revision, "revision")
        _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation")
        _nn(self.installed_fence_generation, "installed_fence_generation")
        if type(self.expires_at) is not int:
            raise ValueError("expires_at must be exact int")
        for name in ("configuration_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, name), name)

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
class HandoffVerificationContext:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    installed_fence_generation: int
    owner_evidence_root: str
    verifier_receipt_root: str
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str
    now: int

    def __post_init__(self):
        _id(self.cell_id, "cell_id")
        _nn(self.revision, "revision")
        _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation")
        _nn(self.installed_fence_generation, "installed_fence_generation")
        if type(self.now) is not int:
            raise ValueError("now must be exact int")
        for name in ("configuration_root", "owner_evidence_root", "verifier_receipt_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, name), name)


@dataclass(frozen=True)
class EffectHandoffEvidence:
    owner_evidence_root: str
    verifier_receipt_root: str

    def __post_init__(self):
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

    def __post_init__(self):
        if self.semantic_handoff_root is not None:
            _root(self.semantic_handoff_root, "semantic_handoff_root")
        if self.tecc_input_root is not None:
            _root(self.tecc_input_root, "tecc_input_root")
        if self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("D0 handoff cannot mint authority")


def canonical_read_binding_root(hydration, typed_closure) -> str:
    """Recompute the current PR878 ReadWorldBinding identity.

    The proof-algorithm identity is semantic identity. This intentionally differs
    from the pre-M3 same-schema binding that omitted reproof semantics.
    """
    return digest({
        "schema": READ_BINDING_SCHEMA,
        "hydration_receipt_root": getattr(hydration, "receipt_root", None),
        "hydration_support_root": getattr(hydration, "support_root", None),
        "typed_closure_receipt_root": getattr(typed_closure, "receipt_root", None),
        "typed_reproof_semantics": getattr(typed_closure, "reproof_semantics", None),
    })


def _admission_receipt_current(admission: Mapping[str, object], read_cert, hydration, typed_closure) -> tuple[bool, str]:
    if not isinstance(admission, Mapping):
        return False, "ADMISSION_RECEIPT_REQUIRED"
    if admission.get("admission_mode") != "EFFECT_BOUND":
        return False, "READ_ONLY_CANNOT_ENTER_EFFECT_HANDOFF"
    if admission.get("disposition") != "HOLD_TECC_REQUIRED_D0" or admission.get("required_verifier_schema") != TECC_SCHEMA:
        return False, "EFFECT_MODE_NOT_TECC_SEALED"
    if admission.get("typed_closure_receipt_root") != getattr(typed_closure, "receipt_root", None):
        return False, "ADMISSION_TYPED_CLOSURE_MOVED"
    if admission.get("coverage_receipt_root") != getattr(read_cert, "coverage_receipt_root", None):
        return False, "ADMISSION_COVERAGE_MOVED"
    if admission.get("support_root") != getattr(hydration, "support_root", None):
        return False, "ADMISSION_SUPPORT_MOVED"
    if admission.get("influence_root") != getattr(typed_closure, "influence_root", None):
        return False, "ADMISSION_INFLUENCE_MOVED"
    if admission.get("transition_model_root") != getattr(typed_closure, "transition_model_root", None):
        return False, "ADMISSION_TRANSITION_MOVED"
    if admission.get("horizon") != getattr(typed_closure, "horizon", None) or admission.get("future_congruence_root") != getattr(typed_closure, "future_congruence_root", None):
        return False, "ADMISSION_HORIZON_MOVED"
    if any(bool(admission.get(k, False)) for k in ("authority_minted", "mutation_authority", "effect_authority", "gate10")):
        return False, "ADMISSION_AUTHORITY_ESCALATION"
    receipt = admission.get("receipt_root")
    if not isinstance(receipt, str):
        return False, "ADMISSION_RECEIPT_ROOT_MISSING"
    payload = dict(admission)
    payload.pop("receipt_root", None)
    if digest(payload) != receipt:
        return False, "ADMISSION_RECEIPT_ROOT_FORGED"
    return True, "EFFECT_MODE_TECC_SEALED"


def _read_consequence_current(read_cert, read_use, hydration, typed_closure) -> tuple[bool, str, str | None]:
    if _status(read_cert) != "READY_D0" or _status(read_use) != "READY_D0":
        return False, "READ_CONSEQUENCE_NOT_READY", None
    if getattr(read_use, "certificate_root", None) != getattr(read_cert, "receipt_root", None):
        return False, "READ_USE_CERTIFICATE_MOVED", None
    if getattr(hydration, "status", None) != "READY_SUPPORT_CLOSED_HYDRATION_D0":
        return False, "ACTIVE_HYDRATION_NOT_READY", None
    if _status(typed_closure) != "READY_D0":
        return False, "ACTIVE_TYPED_CLOSURE_NOT_READY", None
    reproof_semantics = getattr(typed_closure, "reproof_semantics", None)
    if reproof_semantics != EXPECTED_REPROOF_SEMANTICS:
        return False, "ACTIVE_REPROOF_SEMANTICS_NOT_CURRENT", None
    binding = canonical_read_binding_root(hydration, typed_closure)
    if binding not in tuple(getattr(read_cert, "binding_roots", ())):
        return False, "ACTIVE_READ_WORLD_NOT_CERTIFIED", None
    if getattr(hydration, "receipt_root", None) not in tuple(getattr(read_cert, "member_hydration_receipt_roots", ())):
        return False, "ACTIVE_HYDRATION_RECEIPT_NOT_CERTIFIED", None
    if getattr(hydration, "support_root", None) not in tuple(getattr(read_cert, "member_support_roots", ())):
        return False, "ACTIVE_SUPPORT_ROOT_NOT_CERTIFIED", None
    if tuple(getattr(hydration, "support_cut", ())) != tuple(getattr(read_cert, "hydration_cut", ())):
        return False, "ACTIVE_HYDRATION_CONSEQUENCE_MOVED", None
    if tuple(getattr(typed_closure, "reproof_item_ids", ())) != tuple(getattr(read_cert, "reproof_item_ids", ())):
        return False, "ACTIVE_COMPONENT_REPROOF_MOVED", None
    if (getattr(typed_closure, "transition_model_root", None), getattr(typed_closure, "horizon", None), getattr(typed_closure, "future_congruence_root", None)) != (getattr(read_cert, "transition_model_root", None), getattr(read_cert, "horizon", None), getattr(read_cert, "future_congruence_root", None)):
        return False, "ACTIVE_TRANSITION_CONSEQUENCE_MOVED", None
    semantic = digest({
        "schema": SCHEMA,
        "kind": "current_read_semantic",
        "read_certificate_root": getattr(read_cert, "receipt_root", None),
        "active_binding_root": binding,
        "typed_closure_receipt_root": getattr(typed_closure, "receipt_root", None),
        "reproof_semantics": reproof_semantics,
        "coverage_receipt_root": getattr(read_cert, "coverage_receipt_root", None),
        "consequence_root": getattr(read_cert, "consequence_root", None),
        "reproof_item_ids": tuple(getattr(typed_closure, "reproof_item_ids", ())),
        "transition_model_root": getattr(typed_closure, "transition_model_root", None),
        "horizon": getattr(typed_closure, "horizon", None),
        "future_congruence_root": getattr(typed_closure, "future_congruence_root", None),
    })
    return True, "CURRENT_READ_CONSEQUENCE_BOUND", semantic


def compile_effect_handoff(read_cert, read_use, hydration, typed_closure,
                           admission: Mapping[str, object], evidence: EffectHandoffEvidence,
                           mutation: MutationBoundaryProjection,
                           verification: HandoffVerificationContext) -> HandoffDecision:
    """Cross-bind current read semantics to mutation state, then route to TECC."""
    read_ok, reason, semantic = _read_consequence_current(read_cert, read_use, hydration, typed_closure)
    if not read_ok:
        return HandoffDecision(HandoffDisposition.HOLD, reason)
    admission_ok, reason = _admission_receipt_current(admission, read_cert, hydration, typed_closure)
    if not admission_ok:
        return HandoffDecision(HandoffDisposition.HOLD, reason, semantic)
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
        "kind": "tecc_effect_handoff_input",
        "semantic_handoff_root": semantic,
        "reproof_semantics": EXPECTED_REPROOF_SEMANTICS,
        "admission_receipt_root": admission["receipt_root"],
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
        "EXACT_CURRENT_CROSS_BINDING_REQUIRES_INDEPENDENT_TECC",
        semantic,
        tecc_input,
        TECC_SCHEMA,
    )
