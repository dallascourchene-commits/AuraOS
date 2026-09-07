from __future__ import annotations

"""D0 bridge from current Memory City read consequence/typed closure proof to mutation authority.

The read/reproof/horizon compiler and mutation/fence compiler remain separate owners.
This module only proves that both decisions refer to one exact semantic handoff.
It supports the current multi-world ReadConsequenceCertificate shape without minting authority.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-MEMORY-CITY-HORIZON-FENCED-HANDOFF-v2"
D0 = "D0_NONPROMOTING"


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


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class HandoffDisposition(str, Enum):
    READY_D0 = "READY_D0"
    HOLD = "HOLD"
    REBIND_REQUIRED = "REBIND_REQUIRED"


@dataclass(frozen=True)
class SemanticHandoffEvidence:
    read_use_root: str
    semantic_handoff_root: str
    owner_evidence_root: str
    verifier_receipt_root: str

    def __post_init__(self):
        for name in ("read_use_root", "semantic_handoff_root", "owner_evidence_root", "verifier_receipt_root"):
            _root(getattr(self, name), name)


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
    semantic_handoff_root: str
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str

    def __post_init__(self):
        _id(self.cell_id, "cell_id"); _id(self.holder, "holder")
        _nn(self.revision, "revision"); _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation"); _nn(self.installed_fence_generation, "installed_fence_generation")
        if type(self.expires_at) is not int: raise ValueError("expires_at must be exact int")
        for name in ("configuration_root", "semantic_handoff_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, name), name)


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
        _nn(self.revision, "revision"); _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation"); _nn(self.installed_fence_generation, "installed_fence_generation")
        if type(self.now) is not int: raise ValueError("now must be exact int")
        for name in ("configuration_root", "owner_evidence_root", "verifier_receipt_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, name), name)


@dataclass(frozen=True)
class HandoffDecision:
    disposition: HandoffDisposition
    reason: str
    semantic_handoff_root: str | None = None
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self):
        if self.semantic_handoff_root is not None: _root(self.semantic_handoff_root, "semantic_handoff_root")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 handoff cannot mint authority")


def _state_value(obj):
    raw = getattr(obj, "disposition", None)
    if raw is None:
        raw = getattr(obj, "status", None)
    return getattr(raw, "value", raw)


def _horizon_fields(cert):
    transition_model_root = _root(getattr(cert, "transition_model_root", None), "transition_model_root")
    horizon = getattr(cert, "horizon", None)
    if type(horizon) is not int or horizon < 0:
        raise ValueError("horizon must be nonnegative exact int")
    future = getattr(cert, "future_congruence_root", None)
    if horizon > 0:
        _root(future, "future_congruence_root")
    elif future is not None:
        _root(future, "future_congruence_root")
    return transition_model_root, horizon, future


def semantic_handoff_root(cert) -> str:
    """Bind either the current multi-world read certificate or a singleton typed closure."""
    receipt_root = _root(getattr(cert, "receipt_root", None), "semantic_receipt_root")
    transition_model_root, horizon, future = _horizon_fields(cert)

    consequence_root = getattr(cert, "consequence_root", None)
    coverage_receipt_root = getattr(cert, "coverage_receipt_root", None)
    if consequence_root is not None or coverage_receipt_root is not None:
        _root(consequence_root, "consequence_root")
        _root(coverage_receipt_root, "coverage_receipt_root")
        program_root = _root(getattr(cert, "program_root", None), "program_root")
        sealed_domain_root = _root(getattr(cert, "sealed_domain_root", None), "sealed_domain_root")
        coverage_generation = getattr(cert, "coverage_generation", None)
        _nn(coverage_generation, "coverage_generation")
        binding_roots = tuple(sorted(_root(x, "binding_root") for x in tuple(getattr(cert, "binding_roots", ()))))
        member_support_roots = tuple(sorted(_root(x, "member_support_root") for x in tuple(getattr(cert, "member_support_roots", ()))))
        if not binding_roots or not member_support_roots:
            raise ValueError("read consequence certificate must bind members")
        return digest({
            "schema": SCHEMA,
            "kind": "read_consequence_handoff",
            "consequence_root": consequence_root,
            "coverage_receipt_root": coverage_receipt_root,
            "program_root": program_root,
            "sealed_domain_root": sealed_domain_root,
            "coverage_generation": coverage_generation,
            "binding_roots": binding_roots,
            "member_support_roots": member_support_roots,
            "transition_model_root": transition_model_root,
            "horizon": horizon,
            "future_congruence_root": future,
            "semantic_receipt_root": receipt_root,
        })

    support_root = _root(getattr(cert, "support_root", None), "support_root")
    influence_root = _root(getattr(cert, "influence_root", None), "influence_root")
    return digest({
        "schema": SCHEMA,
        "kind": "singleton_typed_closure_handoff",
        "support_root": support_root,
        "influence_root": influence_root,
        "transition_model_root": transition_model_root,
        "horizon": horizon,
        "future_congruence_root": future,
        "semantic_receipt_root": receipt_root,
    })


def read_use_root(cert, use_decision) -> str:
    return digest({
        "schema": SCHEMA,
        "kind": "read_use",
        "semantic_handoff_root": semantic_handoff_root(cert),
        "state": _state_value(use_decision),
        "certificate_root": getattr(use_decision, "certificate_root", None),
        "branch_id": getattr(use_decision, "branch_id", None),
        "hydrate_item_ids": tuple(getattr(use_decision, "hydrate_item_ids", ())),
        "reproof_item_ids": tuple(getattr(use_decision, "reproof_item_ids", ())),
    })


def compile_horizon_fenced_handoff(cert, use_decision, evidence: SemanticHandoffEvidence,
                                     mutation: MutationBoundaryProjection,
                                     verification: HandoffVerificationContext) -> HandoffDecision:
    """Join current read/reuse proof to mutation state without collapsing either owner."""
    if _state_value(cert) != "READY_D0" or _state_value(use_decision) != "READY_D0":
        return HandoffDecision(HandoffDisposition.HOLD, "READ_CLOSURE_NOT_READY")
    expected_semantic = semantic_handoff_root(cert)
    expected_use = read_use_root(cert, use_decision)
    if evidence.read_use_root != expected_use or evidence.semantic_handoff_root != expected_semantic:
        return HandoffDecision(HandoffDisposition.HOLD, "SEMANTIC_EVIDENCE_BINDING_MISMATCH")
    if evidence.owner_evidence_root != verification.owner_evidence_root:
        return HandoffDecision(HandoffDisposition.HOLD, "OWNER_EVIDENCE_ROOT_STALE")
    if evidence.verifier_receipt_root != verification.verifier_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "VERIFIER_RECEIPT_ROOT_STALE")
    if mutation.semantic_handoff_root != expected_semantic:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "SEMANTIC_HANDOFF_MOVED", expected_semantic)
    if mutation.cell_id != verification.cell_id:
        return HandoffDecision(HandoffDisposition.HOLD, "CELL_MISMATCH", expected_semantic)
    if mutation.revision != verification.revision:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "REVISION_MOVED", expected_semantic)
    if mutation.configuration_root != verification.configuration_root:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "CONFIGURATION_MOVED", expected_semantic)
    if mutation.support_epoch != verification.support_epoch:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "SUPPORT_EPOCH_MOVED", expected_semantic)
    if mutation.transition_authority_receipt_root != verification.transition_authority_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "TRANSITION_AUTHORITY_RECEIPT_STALE", expected_semantic)
    if mutation.resource_fence_receipt_root != verification.resource_fence_receipt_root:
        return HandoffDecision(HandoffDisposition.HOLD, "RESOURCE_FENCE_RECEIPT_STALE", expected_semantic)
    if mutation.fence_generation != verification.fence_generation:
        return HandoffDecision(HandoffDisposition.REBIND_REQUIRED, "FENCE_GENERATION_MOVED", expected_semantic)
    if mutation.installed_fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "INSTALLED_FENCE_RECEIPT_MISMATCH", expected_semantic)
    if mutation.fence_generation != mutation.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "FENCE_NOT_INSTALLED_CURRENT", expected_semantic)
    if verification.fence_generation != verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD, "RESOURCE_FENCE_NOT_CURRENT", expected_semantic)
    if verification.now >= mutation.expires_at:
        return HandoffDecision(HandoffDisposition.HOLD, "LEASE_EXPIRED", expected_semantic)
    return HandoffDecision(HandoffDisposition.READY_D0, "EXACT_SEMANTIC_TO_MUTATION_HANDOFF", expected_semantic)


def hard13d_handoff(axes):
    if len(axes) != 13 or any(type(x) is not int or x not in (0,1,2) for x in axes): return "HOLD_MALFORMED"
    hard = axes[:8]
    if 0 in hard: return "HOLD_HARD_INVALID"
    if 1 in hard: return "HOLD_UNRESOLVED"
    return "READY_D0"
