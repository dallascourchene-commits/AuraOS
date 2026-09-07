from __future__ import annotations

"""D0 current-owner Memory City read-to-effect handoff.

The handoff deliberately re-runs the current PR878 read-use validator at the
mutation boundary instead of trusting a detached, previously READY read-use
object.  A valid cross-binding never becomes effect READY here; it emits an
exact AURA-TECC-v1 input capsule and remains HOLD_TECC_REQUIRED_D0.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

from memory_city_coverage_membrane import (
    AdmissionMode,
    TECC_SCHEMA,
    compile_proof_carrying_typed_admission,
)
from memory_city_read_consequence import ReadWorldBinding, validate_read_consequence_at_use
from memory_city_typed_closure import REPROOF_SEMANTICS

SCHEMA = "AURA-MEMORY-CITY-CURRENT-OWNER-EFFECT-HANDOFF-v1"
READ_CONSEQUENCE_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-v1"
READ_CERT_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-CERT-v1"
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


def canonical_read_consequence_root(cert) -> str:
    """Recompute the current PR878 read-consequence identity."""
    return digest({
        "schema": READ_CONSEQUENCE_SCHEMA,
        "hydration_cut": tuple(getattr(cert, "hydration_cut", ())),
        "reproof": tuple(getattr(cert, "reproof_item_ids", ())),
        "reproof_semantics": REPROOF_SEMANTICS,
        "transition_model_root": getattr(cert, "transition_model_root", None),
        "horizon": getattr(cert, "horizon", None),
        "future_congruence_root": getattr(cert, "future_congruence_root", None),
    })


def canonical_read_certificate_receipt_root(cert) -> str:
    """Recompute the READY certificate receipt produced by the current read owner."""
    return digest({
        "schema": READ_CERT_SCHEMA,
        "status": "READY_D0",
        "coverage_receipt_root": getattr(cert, "coverage_receipt_root", None),
        "program_root": getattr(cert, "program_root", None),
        "sealed_domain_root": getattr(cert, "sealed_domain_root", None),
        "coverage_generation": getattr(cert, "coverage_generation", None),
        "bindings": sorted(tuple(getattr(cert, "binding_roots", ()))),
        "member_support_roots": tuple(getattr(cert, "member_support_roots", ())),
        "member_hydration_receipts": tuple(getattr(cert, "member_hydration_receipt_roots", ())),
        "reproof_semantics": REPROOF_SEMANTICS,
        "consequence_root": getattr(cert, "consequence_root", None),
        "mutation_authority": False,
        "effect_authority": False,
        "gate10": False,
    })


def validate_read_certificate_integrity(cert) -> tuple[bool, str]:
    """Fail closed unless the supplied READY read certificate is internally canonical."""
    if _status(cert) != "READY_D0":
        return False, "READ_CERTIFICATE_NOT_READY"
    if getattr(cert, "authority", D0) != D0:
        return False, "READ_CERTIFICATE_AUTHORITY_ESCALATION"
    if any(bool(getattr(cert, name, False)) for name in ("mutation_authority", "effect_authority", "gate10")):
        return False, "READ_CERTIFICATE_AUTHORITY_ESCALATION"
    horizon = getattr(cert, "horizon", None)
    if type(horizon) is not int or horizon < 0:
        return False, "READ_CERTIFICATE_HORIZON_MALFORMED"
    root_fields = (
        "receipt_root", "coverage_receipt_root", "program_root", "sealed_domain_root",
        "consequence_root", "transition_model_root",
    )
    try:
        for field in root_fields:
            _root(getattr(cert, field, None), field)
        for field in ("binding_roots", "member_support_roots", "member_hydration_receipt_roots"):
            for value in tuple(getattr(cert, field, ())):
                _root(value, field)
        future = getattr(cert, "future_congruence_root", None)
        if horizon > 0:
            _root(future, "future_congruence_root")
        elif future is not None:
            _root(future, "future_congruence_root")
    except ValueError:
        return False, "READ_CERTIFICATE_ROOT_MALFORMED"
    if getattr(cert, "consequence_root", None) != canonical_read_consequence_root(cert):
        return False, "READ_CERTIFICATE_CONSEQUENCE_ROOT_FORGED"
    if getattr(cert, "receipt_root", None) != canonical_read_certificate_receipt_root(cert):
        return False, "READ_CERTIFICATE_RECEIPT_ROOT_FORGED"
    return True, "CURRENT_OWNER_READ_CERTIFICATE_CANONICAL"


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
        _nn(self.expires_at, "expires_at")
        for field in ("configuration_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, field), field)

    @property
    def lease_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "lease_identity",
            "cell_id": self.cell_id,
            "revision": self.revision,
            "configuration_root": self.configuration_root,
            "support_epoch": self.support_epoch,
            "fence_generation": self.fence_generation,
            "holder": self.holder,
            "expires_at": self.expires_at,
        })

    @property
    def boundary_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "mutation_boundary",
            "lease_root": self.lease_root,
            "installed_fence_generation": self.installed_fence_generation,
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
    holder: str
    expires_at: int
    owner_evidence_root: str
    verifier_receipt_root: str
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str
    now: int

    def __post_init__(self):
        _id(self.cell_id, "cell_id")
        _id(self.holder, "holder")
        _nn(self.revision, "revision")
        _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation")
        _nn(self.installed_fence_generation, "installed_fence_generation")
        _nn(self.expires_at, "expires_at")
        _nn(self.now, "now")
        for field in (
            "configuration_root", "owner_evidence_root", "verifier_receipt_root",
            "transition_authority_receipt_root", "resource_fence_receipt_root",
        ):
            _root(getattr(self, field), field)

    @property
    def lease_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "lease_identity",
            "cell_id": self.cell_id,
            "revision": self.revision,
            "configuration_root": self.configuration_root,
            "support_epoch": self.support_epoch,
            "fence_generation": self.fence_generation,
            "holder": self.holder,
            "expires_at": self.expires_at,
        })


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
        if self.authority != D0:
            raise ValueError("D0 handoff authority must remain D0_NONPROMOTING")
        if self.semantic_handoff_root is not None:
            _root(self.semantic_handoff_root, "semantic_handoff_root")
        if self.tecc_input_root is not None:
            _root(self.tecc_input_root, "tecc_input_root")
        if self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("D0 handoff cannot mint authority")


def _canonical_effect_admission(coverage, hydration, typed_closure) -> dict:
    return compile_proof_carrying_typed_admission(
        typed_closure_receipt_root=typed_closure.receipt_root,
        coverage=coverage,
        support_root=hydration.support_root,
        influence_root=typed_closure.influence_root,
        transition_model_root=typed_closure.transition_model_root,
        future_congruence_root=typed_closure.future_congruence_root,
        horizon=typed_closure.horizon,
        mode=AdmissionMode.EFFECT_BOUND,
    )


def compile_effect_handoff(
    read_cert,
    *,
    hydration,
    typed_closure,
    fixed_support_root: str,
    coverage,
    current_program_root: str,
    current_sealed_domain_root: str,
    current_coverage_generation: int,
    admission: Mapping[str, object],
    evidence: EffectHandoffEvidence,
    mutation: MutationBoundaryProjection,
    verification: HandoffVerificationContext,
) -> HandoffDecision:
    """Revalidate the rightful read owner at T1, cross-bind the lease, and route to TECC."""
    cert_ok, reason = validate_read_certificate_integrity(read_cert)
    if not cert_ok:
        return HandoffDecision(HandoffDisposition.HOLD, reason)

    current_use = validate_read_consequence_at_use(
        read_cert,
        hydration=hydration,
        typed_closure=typed_closure,
        fixed_support_root=fixed_support_root,
        coverage=coverage,
        current_program_root=current_program_root,
        current_sealed_domain_root=current_sealed_domain_root,
        current_coverage_generation=current_coverage_generation,
        mutation_requested=False,
    )
    if _status(current_use) != "READY_D0":
        return HandoffDecision(HandoffDisposition.HOLD, f"READ_OWNER_AT_T1_{_status(current_use)}")

    active_binding_root = ReadWorldBinding(hydration, typed_closure).binding_root
    semantic_root = digest({
        "schema": SCHEMA,
        "kind": "current_read_semantic",
        "read_certificate_root": read_cert.receipt_root,
        "active_binding_root": active_binding_root,
        "coverage_receipt_root": coverage.receipt_root,
        "current_program_root": current_program_root,
        "current_sealed_domain_root": current_sealed_domain_root,
        "current_coverage_generation": current_coverage_generation,
        "fixed_support_root": fixed_support_root,
        "typed_reproof_semantics": typed_closure.reproof_semantics,
        "consequence_root": read_cert.consequence_root,
    })

    expected_admission = _canonical_effect_admission(coverage, hydration, typed_closure)
    if not isinstance(admission, Mapping) or dict(admission) != expected_admission:
        return HandoffDecision(HandoffDisposition.HOLD, "ADMISSION_NOT_EXACT_CURRENT_OWNER_OUTPUT", semantic_root)

    if evidence.owner_evidence_root != verification.owner_evidence_root:
        return HandoffDecision(HandoffDisposition.HOLD, "OWNER_EVIDENCE_ROOT_STALE", semantic_root)
    if evidence.verifier_receipt_root != verification.verifier_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "VERIFIER_RECEIPT_ROOT_STALE", semantic_root)

    if mutation.cell_id != verification.cell_id:
        return HandoffDecision(HandoffDisposition.HOLD, "CELL_MISMATCH", semantic_root)
    if mutation.revision != verification.revision:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "REVISION_MOVED", semantic_root)
    if mutation.configuration_root != verification.configuration_root:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "CONFIGURATION_MOVED", semantic_root)
    if mutation.support_epoch != verification.support_epoch:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "SUPPORT_EPOCH_MOVED", semantic_root)
    if mutation.lease_root != verification.lease_root:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "LEASE_IDENTITY_MOVED", semantic_root)
    if mutation.transition_authority_receipt_root != verification.transition_authority_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "TRANSITION_AUTHORITY_RECEIPT_STALE", semantic_root)
    if mutation.resource_fence_receipt_root != verification.resource_fence_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "RESOURCE_FENCE_RECEIPT_STALE", semantic_root)
    if mutation.installed_fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "INSTALLED_FENCE_RECEIPT_MISMATCH", semantic_root)
    if mutation.fence_generation != mutation.installed_fence_generation or verification.fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "FENCE_NOT_INSTALLED_CURRENT", semantic_root)
    if verification.now >= mutation.expires_at:
        return HandoffDecision(HandoffDisposition.HOLD, "LEASE_EXPIRED", semantic_root)

    tecc_input_root = digest({
        "schema": SCHEMA,
        "kind": "tecc_effect_handoff_input",
        "semantic_handoff_root": semantic_root,
        "admission_receipt_root": expected_admission["receipt_root"],
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
        "EXACT_CURRENT_OWNER_CROSS_BINDING_REQUIRES_INDEPENDENT_TECC",
        semantic_root,
        tecc_input_root,
        TECC_SCHEMA,
    )
