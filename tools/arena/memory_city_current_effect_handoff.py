from __future__ import annotations

"""D0 cross-binding of current read-use, effect-obligation refinement, and mutation handoff.

This adapter composes existing owners. It does not authenticate effect evidence,
recompute read semantics, mint mutation/effect authority, or replace TECC/fence owners.
A READY result means only that the current read-use, selected effect subclass, and
current semantic/fence boundary were jointly cross-bound into one D0 receipt.
"""

from dataclasses import dataclass
from hashlib import sha256
import json

from memory_city_consequence_refinement import (
    EffectIntent,
    EffectRefinementPlan,
    effect_escalation_root,
    validate_effect_binding,
)
from memory_city_handoff_current_read_seal import (
    CurrentReadUseBinding,
    compile_current_horizon_fenced_handoff,
)
from memory_city_horizon_fenced_handoff import (
    HandoffDisposition,
    HandoffVerificationContext,
    MutationBoundaryProjection,
    SemanticHandoffEvidence,
    read_use_root,
    semantic_handoff_root,
)

SCHEMA = "AURA-MEMORY-CITY-CURRENT-EFFECT-SUBCLASS-HANDOFF-v1"
D0 = "D0_NONPROMOTING"


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class CurrentEffectSubclassDecision:
    status: str
    reason: str
    current_effect_handoff_root: str
    semantic_handoff_root: str
    current_read_use_root: str
    effect_escalation_root: str
    mutation_snapshot_root: str
    read_binding_root: str
    obligation_root: str
    intent_binding_root: str
    authority: str = D0
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for field in (
            "current_effect_handoff_root", "semantic_handoff_root",
            "current_read_use_root", "effect_escalation_root",
            "mutation_snapshot_root", "read_binding_root", "obligation_root",
            "intent_binding_root",
        ):
            _root(getattr(self, field), field)
        if self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("D0 current-effect handoff cannot mint authority")


def _mutation_snapshot_root(mutation: MutationBoundaryProjection, verification: HandoffVerificationContext) -> str:
    return digest({
        "schema": SCHEMA,
        "kind": "mutation_snapshot",
        "cell_id": mutation.cell_id,
        "revision": mutation.revision,
        "configuration_root": mutation.configuration_root,
        "support_epoch": mutation.support_epoch,
        "fence_generation": mutation.fence_generation,
        "installed_fence_generation": mutation.installed_fence_generation,
        "holder": mutation.holder,
        "expires_at": mutation.expires_at,
        "transition_authority_receipt_root": mutation.transition_authority_receipt_root,
        "resource_fence_receipt_root": mutation.resource_fence_receipt_root,
        "verification_now": verification.now,
    })


def _selected_child(plan: EffectRefinementPlan, read_binding_root: str, obligation_root: str):
    for child in plan.subclasses:
        if read_binding_root in child.member_binding_roots and child.obligation_root == obligation_root:
            return child
    return None


def _decision(status, reason, *, semantic_root, current_read_root, escalation_root,
              mutation_root, read_binding_root, obligation_root, intent_root):
    root = digest({
        "schema": SCHEMA,
        "status": status,
        "reason": reason,
        "semantic_handoff_root": semantic_root,
        "current_read_use_root": current_read_root,
        "effect_escalation_root": escalation_root,
        "mutation_snapshot_root": mutation_root,
        "read_binding_root": read_binding_root,
        "obligation_root": obligation_root,
        "intent_binding_root": intent_root,
        "authority_minted": False,
        "mutation_authority": False,
        "effect_authority": False,
        "gate10": False,
    })
    return CurrentEffectSubclassDecision(
        status, reason, root, semantic_root, current_read_root, escalation_root,
        mutation_root, read_binding_root, obligation_root, intent_root,
    )


def compile_current_effect_subclass_handoff(
    cert,
    use_decision,
    current_read: CurrentReadUseBinding,
    refinement: EffectRefinementPlan,
    intent: EffectIntent,
    *,
    read_binding_root: str,
    obligation_root: str,
    evidence: SemanticHandoffEvidence,
    mutation: MutationBoundaryProjection,
    verification: HandoffVerificationContext,
) -> CurrentEffectSubclassDecision:
    """Cross-bind three current owner decisions without converting them into authority."""
    _root(read_binding_root, "read_binding_root")
    _root(obligation_root, "obligation_root")
    if not isinstance(current_read, CurrentReadUseBinding):
        raise ValueError("current_read must be CurrentReadUseBinding")
    if not isinstance(refinement, EffectRefinementPlan):
        raise ValueError("refinement must be EffectRefinementPlan")
    if not isinstance(intent, EffectIntent):
        raise ValueError("intent must be EffectIntent")

    semantic_root = semantic_handoff_root(cert)
    current_read_root = read_use_root(cert, use_decision)
    mutation_root = _mutation_snapshot_root(mutation, verification)
    intent_root = intent.binding_root

    binding_state = validate_effect_binding(
        refinement, cert=cert, intent=intent,
        read_binding_root=read_binding_root, obligation_root=obligation_root,
    )
    child = _selected_child(refinement, read_binding_root, obligation_root)
    if binding_state != "READY_EFFECT_SUBCLASS_D0" or child is None:
        placeholder = digest({"schema": SCHEMA, "kind": "no_effect_escalation", "state": binding_state})
        return _decision(
            "HOLD_EFFECT_REFINEMENT_D0", binding_state,
            semantic_root=semantic_root, current_read_root=current_read_root,
            escalation_root=placeholder, mutation_root=mutation_root,
            read_binding_root=read_binding_root, obligation_root=obligation_root,
            intent_root=intent_root,
        )

    escalation_root = effect_escalation_root(refinement, child)
    handoff = compile_current_horizon_fenced_handoff(
        cert, use_decision, current_read, evidence, mutation, verification
    )
    if handoff.disposition is HandoffDisposition.REBIND_REQUIRED:
        return _decision(
            "REBIND_REQUIRED", handoff.reason,
            semantic_root=semantic_root, current_read_root=current_read_root,
            escalation_root=escalation_root, mutation_root=mutation_root,
            read_binding_root=read_binding_root, obligation_root=obligation_root,
            intent_root=intent_root,
        )
    if handoff.disposition is not HandoffDisposition.READY_D0:
        return _decision(
            "HOLD_HANDOFF_D0", handoff.reason,
            semantic_root=semantic_root, current_read_root=current_read_root,
            escalation_root=escalation_root, mutation_root=mutation_root,
            read_binding_root=read_binding_root, obligation_root=obligation_root,
            intent_root=intent_root,
        )

    return _decision(
        "READY_CURRENT_EFFECT_SUBCLASS_D0",
        "CURRENT_READ_EFFECT_SUBCLASS_AND_FENCE_CROSS_BOUND",
        semantic_root=semantic_root, current_read_root=current_read_root,
        escalation_root=escalation_root, mutation_root=mutation_root,
        read_binding_root=read_binding_root, obligation_root=obligation_root,
        intent_root=intent_root,
    )


def hard13d_current_effect(axes):
    if len(axes) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in axes):
        return "HOLD_MALFORMED"
    hard = axes[:8]
    if 0 in hard:
        return "HOLD_HARD_INVALID"
    if 1 in hard:
        return "HOLD_UNRESOLVED"
    return "READY_D0"
