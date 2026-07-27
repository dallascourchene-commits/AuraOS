from __future__ import annotations

from copy import deepcopy
import time

import pytest

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_mcp import TOOL_DEFINITIONS
from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_architect_council_v3 import route_compass_failure_classes
from aura_architect_loop import (
    GroundingEvidence,
    build_fractal_plan_capsule,
    build_refactor_arena,
    shadow_plan_capsule,
    stage_arena_patch,
)
from aura_relationship_contracts import (
    BilateralPlanningContract,
    evaluate_bilateral_plan,
)


@pytest.fixture()
def bilateral_contract() -> BilateralPlanningContract:
    bridge = AuraAgentArenaBridge(repo_root=".")
    started = bridge.intent_refinement_start(
        source_request=(
            "Add deterministic bilateral plan enforcement. "
            "Do not allow a plan without negative requirement verification."
        ),
        affected_files=["aura_arena_architect_connector.py"],
        affected_symbols=["assess_plan"],
    )
    assert started["status"] == "TEACH_BACK_PENDING"
    confirmed = bridge.intent_refinement_confirm(
        session_id=started["session_id"],
        allowed_paths=["aura_arena_architect_connector.py"],
        human_reviewer="pytest-human",
    )
    assert confirmed["ok"] is True
    return BilateralPlanningContract.from_dict(confirmed["bilateral_contract"])


def _complete_plan(contract: BilateralPlanningContract) -> dict:
    coverage = lambda values: {  # noqa: E731
        value: {
            "enforcement": f"enforce:{index}",
            "verifier": contract.required_verifiers[index % len(contract.required_verifiers)],
        }
        for index, value in enumerate(values)
    }
    return {
        "architecture_decision": "Reuse the existing Architect connector and gates.",
        "act_tasks": [
            {
                "task_id": "BILATERAL-1",
                "objective": "Enforce the confirmed bilateral planning contract.",
                "target_file": "aura_arena_architect_connector.py",
                "target_symbol": "assess_plan",
                "acceptance": "The deterministic gate passes before scoring.",
                "expected_output": "UNIFIED_DIFF",
                "tests": ["tests/test_aura_bilateral_planning_enforcement.py"],
            }
        ],
        "acceptance_criteria": ["A complete plan remains eligible."],
        "rollback_conditions": ["Any bilateral proof failure."],
        "risk_map": ["A missing prohibition could otherwise win on score."],
        "constraints": ["proposal only"],
        "architecture_reuse": True,
        "coverage_tags": ["bilateral"],
        "intent_digest": contract.intent_digest,
        "semantic_ledger_digest": contract.semantic_ledger_digest,
        "confirmation_digest": contract.confirmation_digest,
        "semantic_definitions": [dict(item) for item in contract.semantic_definitions],
        "positive_requirement_coverage": coverage(contract.positive_requirements),
        "negative_requirement_coverage": coverage(contract.negative_requirements),
        "guardrail_coverage": coverage(
            [*contract.hard_guardrail_ids, *contract.human_guardrail_ids]
        ),
        "guardrail_verifiers": list(contract.required_verifiers),
        "assumption_register": [],
        "plan_revision_policy": "reconfirm meaning, scope, authority, or guardrail changes",
        "authority_conflicts": [],
        "expected_repository_head": contract.repository_head,
        "expected_source_tree_digest": contract.source_tree_digest,
        "allowed_path_set_digest": contract.allowed_path_set_digest,
        "intent_revision_id": contract.intent_revision_id,
        "plan_revision": {},
    }


def test_bilateral_plan_gate_passes_complete_exact_plan(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    gate = evaluate_bilateral_plan(
        _complete_plan(bilateral_contract),
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    assert gate.passed is True
    assert gate.failure_classes == ()


def test_bilateral_plan_gate_rejects_missing_negative_verifier(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan = _complete_plan(bilateral_contract)
    plan["negative_requirement_coverage"] = {}
    gate = evaluate_bilateral_plan(
        plan,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    assert gate.passed is False
    assert "NEGATIVE_REQUIREMENT" in gate.failure_classes


def test_connector_cannot_select_higher_scoring_ineligible_plan(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    complete = _complete_plan(bilateral_contract)
    incomplete = deepcopy(complete)
    incomplete["negative_requirement_coverage"] = {}
    incomplete["coverage_tags"] = ["bilateral", "extra"]
    connector = AuraArenaArchitectConnector(repo_root=".")
    result = connector.compare_plans(
        objective="Choose only a bilaterally eligible plan.",
        candidates=[
            {"candidate_id": "incomplete", "plan": incomplete},
            {"candidate_id": "complete", "plan": complete},
        ],
        required_capabilities=["bilateral"],
        bilateral_contract=bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
        record=False,
    )
    assert result["ok"] is True
    assert result["selected_candidate_id"] == "complete"
    by_id = {item["candidate_id"]: item for item in result["assessments"]}
    assert by_id["incomplete"]["eligible"] is False
    assert by_id["incomplete"]["score"] == 0.0


def test_shadow_and_patch_stage_retain_bilateral_scope(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan_data = _complete_plan(bilateral_contract)
    gate = evaluate_bilateral_plan(
        plan_data,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    plan = build_fractal_plan_capsule(
        "Enforce bilateral planning.",
        architecture_decision=plan_data["architecture_decision"],
        act_tasks=plan_data["act_tasks"],
        bilateral_contract=bilateral_contract.to_dict(),
        bilateral_plan_gate=gate.to_dict(),
        bilateral_proof_plan=plan_data,
    )
    grounding = [
        GroundingEvidence(
            task_id="BILATERAL-1",
            target_file="aura_arena_architect_connector.py",
            target_symbol="assess_plan",
            file_exists=True,
            codemap_file_hit=True,
            symbol_exists=True,
            codemap_symbol_hits=[],
            test_files=["tests/test_aura_bilateral_planning_enforcement.py"],
            neighbor_files=[],
        )
    ]
    shadow = shadow_plan_capsule(plan, grounding)
    assert shadow.ok is True
    arena = build_refactor_arena(plan, grounding, shadow)
    staged = stage_arena_patch(
        arena,
        task_id="BILATERAL-1",
        owner="temporary-surgeon",
        diff=(
            "--- a/unrelated.py\n"
            "+++ b/unrelated.py\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
        ),
        affected_files=["unrelated.py"],
    )
    assert staged.ok is False
    assert any(
        item.shadow_type == "bilateral_scope_violation"
        for item in staged.findings
    )


def test_council_routes_bilateral_meaning_back_to_human() -> None:
    routed = route_compass_failure_classes(
        ["SEMANTIC_AMBIGUITY", "AUTHORITY_DENIAL"]
    )
    assert routed["route"] == "HUMAN_RECONFIRMATION_REQUIRED"
    assert routed["deterministic_denial"] is True
    assert routed["council_override_allowed"] is False


def test_mcp_exposes_bounded_refinement_and_revision_tools() -> None:
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert {
        "intent_refinement_start",
        "intent_refinement_answer",
        "intent_refinement_teach_back",
        "intent_refinement_confirm",
        "intent_refinement_status",
        "intent_revision_propose",
        "intent_revision_confirm",
    }.issubset(names)
