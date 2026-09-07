from __future__ import annotations

"""O14: bind effect-refinement identity into the already-proven O13 TECC handoff.

This module is intentionally thin. O13 remains the current read/admission/lease/fence
owner. O8/PR887 remains the effect-refinement owner. O14 only prevents security-context
discontinuity between those two proof planes by checking the current selected refinement
and including it in the final TECC input identity. No effect authority is minted here.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

from memory_city_consequence_refinement import (
    D0,
    EffectIntent,
    EffectRefinementPlan,
    EffectSubclass,
    effect_escalation_root,
    validate_effect_binding,
)
from memory_city_effect_handoff_o13 import (
    HandoffDecision,
    HandoffDisposition,
    compile_effect_handoff,
)
from memory_city_read_consequence import ReadWorldBinding

SCHEMA = "AURA-MEMORY-CITY-EFFECT-REFINEMENT-HANDOFF-v1"
TECC_SCHEMA = "AURA-TECC-v1"


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


@dataclass(frozen=True)
class EffectRefinementEvidence:
    plan: EffectRefinementPlan
    intent: EffectIntent
    child: EffectSubclass
    owner_receipt_root: str
    verifier_receipt_root: str
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self):
        if not isinstance(self.plan, EffectRefinementPlan):
            raise ValueError("plan must be EffectRefinementPlan")
        if not isinstance(self.intent, EffectIntent):
            raise ValueError("intent must be EffectIntent")
        if not isinstance(self.child, EffectSubclass):
            raise ValueError("child must be EffectSubclass")
        _root(self.owner_receipt_root, "owner_receipt_root")
        _root(self.verifier_receipt_root, "verifier_receipt_root")
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("effect refinement evidence cannot mint authority")

    @property
    def escalation_root(self) -> str:
        return effect_escalation_root(self.plan, self.child)


@dataclass(frozen=True)
class EffectRefinementVerificationContext:
    read_binding_root: str
    plan_root: str
    intent_binding_root: str
    obligation_root: str
    escalation_root: str
    owner_receipt_root: str
    verifier_receipt_root: str

    def __post_init__(self):
        for field in (
            "read_binding_root",
            "plan_root",
            "intent_binding_root",
            "obligation_root",
            "escalation_root",
            "owner_receipt_root",
            "verifier_receipt_root",
        ):
            _root(getattr(self, field), field)



def bind_effect_refinement(
    base: HandoffDecision,
    *,
    read_cert,
    hydration,
    typed_closure,
    refinement: EffectRefinementEvidence,
    refinement_verification: EffectRefinementVerificationContext,
) -> HandoffDecision:
    """Bind the current PR887 refinement only after O13 has reached its TECC terminal."""
    if not isinstance(base, HandoffDecision):
        raise ValueError("base must be HandoffDecision")
    if base.disposition is not HandoffDisposition.HOLD_TECC_REQUIRED_D0:
        return base
    if base.required_verifier_schema != TECC_SCHEMA or base.tecc_input_root is None or base.semantic_handoff_root is None:
        return HandoffDecision(HandoffDisposition.HOLD, "O13_TECC_TERMINAL_MALFORMED", base.semantic_handoff_root)
    if base.authority != D0 or base.authority_minted or base.mutation_authority or base.effect_authority or base.gate10:
        return HandoffDecision(HandoffDisposition.HOLD, "O13_AUTHORITY_ESCALATION", base.semantic_handoff_root)

    active_binding_root = ReadWorldBinding(hydration, typed_closure).binding_root
    if active_binding_root != refinement_verification.read_binding_root:
        return HandoffDecision(HandoffDisposition.HOLD, "REFINEMENT_READ_BINDING_STALE", base.semantic_handoff_root)

    selected = validate_effect_binding(
        refinement.plan,
        cert=read_cert,
        intent=refinement.intent,
        read_binding_root=active_binding_root,
        obligation_root=refinement.child.obligation_root,
    )
    if selected != "READY_EFFECT_SUBCLASS_D0":
        return HandoffDecision(HandoffDisposition.HOLD, selected, base.semantic_handoff_root)

    escalation = refinement.escalation_root
    checks = (
        (refinement.plan.plan_root, refinement_verification.plan_root, "REFINEMENT_PLAN_MOVED"),
        (refinement.intent.binding_root, refinement_verification.intent_binding_root, "REFINEMENT_INTENT_MOVED"),
        (refinement.child.obligation_root, refinement_verification.obligation_root, "REFINEMENT_OBLIGATION_MOVED"),
        (escalation, refinement_verification.escalation_root, "REFINEMENT_ESCALATION_MOVED"),
        (refinement.owner_receipt_root, refinement_verification.owner_receipt_root, "REFINEMENT_OWNER_RECEIPT_STALE"),
        (refinement.verifier_receipt_root, refinement_verification.verifier_receipt_root, "REFINEMENT_VERIFIER_RECEIPT_STALE"),
    )
    for observed, current, reason in checks:
        if observed != current:
            return HandoffDecision(HandoffDisposition.HOLD, reason, base.semantic_handoff_root)

    refined_tecc = digest({
        "schema": SCHEMA,
        "kind": "effect_refined_tecc_input",
        "o13_tecc_input_root": base.tecc_input_root,
        "semantic_handoff_root": base.semantic_handoff_root,
        "read_binding_root": active_binding_root,
        "refinement_plan_root": refinement.plan.plan_root,
        "intent_binding_root": refinement.intent.binding_root,
        "obligation_root": refinement.child.obligation_root,
        "effect_escalation_root": escalation,
        "refinement_owner_receipt_root": refinement.owner_receipt_root,
        "refinement_verifier_receipt_root": refinement.verifier_receipt_root,
        "required_verifier_schema": TECC_SCHEMA,
        "authority_minted": False,
        "mutation_authority": False,
        "effect_authority": False,
        "gate10": False,
    })
    return HandoffDecision(
        HandoffDisposition.HOLD_TECC_REQUIRED_D0,
        "CURRENT_EFFECT_REFINEMENT_BOUND_REQUIRES_INDEPENDENT_TECC",
        base.semantic_handoff_root,
        refined_tecc,
        TECC_SCHEMA,
    )


def compile_effect_refined_handoff(
    read_cert,
    *,
    hydration,
    typed_closure,
    fixed_support_root: str,
    coverage,
    current_program_root: str,
    current_sealed_domain_root: str,
    current_coverage_generation: int,
    admission,
    evidence,
    mutation,
    verification,
    refinement: EffectRefinementEvidence,
    refinement_verification: EffectRefinementVerificationContext,
) -> HandoffDecision:
    """Delegate the entire currentness/effect-boundary check to O13, then bind O8 refinement."""
    base = compile_effect_handoff(
        read_cert,
        hydration=hydration,
        typed_closure=typed_closure,
        fixed_support_root=fixed_support_root,
        coverage=coverage,
        current_program_root=current_program_root,
        current_sealed_domain_root=current_sealed_domain_root,
        current_coverage_generation=current_coverage_generation,
        admission=admission,
        evidence=evidence,
        mutation=mutation,
        verification=verification,
    )
    return bind_effect_refinement(
        base,
        read_cert=read_cert,
        hydration=hydration,
        typed_closure=typed_closure,
        refinement=refinement,
        refinement_verification=refinement_verification,
    )
