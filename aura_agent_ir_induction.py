"""Induce reviewable Agent IR procedures from successful C3 capsule trial traces."""
from __future__ import annotations

import time
from typing import Any, Iterable

from aura_agent_ir import AgentIRNode, EffectType, IRFloor, MorphologyIRBridge
from aura_capsule_trial_types import (
    CapsuleTrialPolicy,
    CapsuleVariant,
    InducedProcedureProposal,
    canonical_digest,
)

AGENT_IR_INDUCTION_VERSION = "AURA_AGENT_IR_INDUCTION_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def induce_agent_ir_procedure(
    *,
    run_id: str,
    policy: CapsuleTrialPolicy,
    variant: CapsuleVariant,
    morphology_signature: dict[str, str],
    observations: Iterable[dict[str, Any]],
    assessment: dict[str, Any],
) -> InducedProcedureProposal:
    rows = [dict(item) for item in observations]
    trial_ids = tuple(sorted(str(item.get("trial_id") or "") for item in rows if item.get("trial_id")))
    floor_history = [IRFloor.TEXT]

    typed = bool(rows) and all(
        item.get("case_id") and item.get("variant_id") and isinstance(item.get("output"), dict)
        for item in rows
    )
    if typed:
        floor_history.append(IRFloor.TYPED)

    specified = typed and all(
        item.get("actual_context_digest")
        and isinstance(item.get("budget_requested"), dict)
        and isinstance(item.get("usage"), dict)
        for item in rows
    )
    if specified:
        floor_history.append(IRFloor.SPEC)

    output_keys = [set((item.get("output") or {}).keys()) for item in rows]
    stable_output_keys = sorted(set.intersection(*output_keys)) if output_keys else []
    stubbed = specified and bool(stable_output_keys)
    if stubbed:
        floor_history.append(IRFloor.STUB)

    executor_ids = {str(item.get("executor_id") or "") for item in rows}
    shimmed = stubbed and len(executor_ids) == 1 and all(item.get("executor_allowlisted") is True for item in rows)
    if shimmed:
        floor_history.append(IRFloor.SHIM)

    datasets = {str(item.get("dataset") or "") for item in rows}
    pure_checks = {
        "typed_observations": typed,
        "formal_bounds_present": specified,
        "stable_output_contract": stubbed,
        "single_allowlisted_executor": shimmed,
        "train_validation_shadow_present": {"TRAIN", "VALIDATION", "SHADOW"}.issubset(datasets),
        "all_trials_completed": bool(rows) and all(item.get("ok") is True for item in rows),
        "all_trials_reproducible": bool(assessment.get("all_reproducible")),
        "validation_passed": bool(assessment.get("validation_passed")),
        "shadow_passed": bool(assessment.get("shadow_passed")),
        "no_model_calls": all(int((item.get("usage") or {}).get("model_calls") or 0) == 0 for item in rows),
        "no_budget_failures": all(not item.get("budget_exceeded") for item in rows),
        "all_sandboxes_dissolved": all((item.get("sandbox") or {}).get("dissolution_verified") is True for item in rows),
        "no_arbitrary_code": all(item.get("arbitrary_code_executed") is False for item in rows),
        "no_native_fallback": all(item.get("native_fallback_used") is False for item in rows),
    }
    pure = all(pure_checks.values())
    if pure:
        floor_history.append(IRFloor.PURE)
    floor = floor_history[-1]

    payload = {
        "procedure_kind": "DETERMINISTIC_LOCALIZATION_PROCEDURE",
        "proposal_only": True,
        "inputs": {
            "objective": "string",
            "bounded_context_items": "exact_source_hash_records",
        },
        "preconditions": {
            "capsule_digest": variant.capsule_digest,
            "component_digests": dict(sorted(variant.component_digests.items())),
            "required_capabilities": list(variant.requested_capabilities),
            "source_hashes_required": bool(variant.data_aperture.get("require_source_hashes")),
        },
        "bounds": {
            "data_aperture": dict(variant.data_aperture),
            "execution_budget": dict(variant.execution_budget),
        },
        "steps": [
            {"step": "TOKENIZE_OBJECTIVE", "effect": "CPU"},
            {"step": "RANK_BOUNDED_CONTEXT_BY_EXPLICIT_METADATA", "effect": "CPU"},
            {"step": "CLAMP_FILES_SYMBOLS_AND_LINES", "effect": "CPU"},
            {"step": "EMIT_EXACT_SOURCE_HASHES_AND_AFFECTED_TESTS", "effect": "CPU"},
            {"step": "VERIFY_BUDGET_AND_DISSOLUTION_RECEIPT", "effect": "CPU"},
        ],
        "outputs": stable_output_keys,
        "executor_id": next(iter(executor_ids), ""),
        "trial_evidence_digest": canonical_digest(trial_ids),
        "pure_checks": pure_checks,
        "executable_code": False,
        "automatic_installation": False,
    }
    node_id = f"AIR-{canonical_digest({'run_id': run_id, 'variant': variant.variant_id, 'floor': floor.value, 'trials': trial_ids})[:24]}"
    node = AgentIRNode(
        node_id=node_id,
        floor=floor,
        payload=payload,
        effect=EffectType.CPU,
    )
    bridge = MorphologyIRBridge.bridge_packet(morphology_signature, floor)
    procedure_identity = {
        "run_id": run_id,
        "policy_id": policy.policy_id,
        "variant_id": variant.variant_id,
        "floor": floor.value,
        "source_trial_ids": trial_ids,
    }
    return InducedProcedureProposal(
        procedure_id=f"CPROC-{canonical_digest(procedure_identity)[:24]}",
        run_id=run_id,
        policy_id=policy.policy_id,
        capsule_id=variant.capsule_id,
        capsule_digest=variant.capsule_digest,
        variant_id=variant.variant_id,
        ir_floor=floor.value,
        floor_history=tuple(item.value for item in floor_history),
        agent_ir_node={
            "node_id": node.node_id,
            "floor": node.floor.value,
            "payload": node.payload,
            "effect": node.effect.value,
            "version": node.version,
        },
        morphology_ir_bridge=bridge,
        source_trial_ids=trial_ids,
        source_trial_digest=canonical_digest(trial_ids),
        assessment={
            **dict(assessment),
            "pure_checks": pure_checks,
            "agent_ir_induction_version": AGENT_IR_INDUCTION_VERSION,
            "procedure_is_executable_code": False,
        },
        created_at=time.time(),
    )
