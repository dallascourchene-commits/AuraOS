from __future__ import annotations

from copy import deepcopy
import subprocess
import time

import pytest

from aura_agent_arena_bridge import AuraAgentArenaBridge
from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request
from aura_architect_council_v3 import route_compass_failure_classes
from aura_architect_loop import (
    GroundingEvidence,
    build_fractal_plan_capsule,
    build_refactor_arena,
    shadow_plan_capsule,
    stage_arena_patch,
)
from aura_arena_architect_connector import AuraArenaArchitectConnector
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


@pytest.fixture()
def bilateral_session() -> tuple[AuraAgentArenaBridge, str, BilateralPlanningContract]:
    """Like ``bilateral_contract`` but also returns the bridge and session id
    backing the retained confirmation, for tests that must exercise the
    authenticated confirmation_session_id path rather than pass an
    already-instantiated contract object directly."""
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
    contract = BilateralPlanningContract.from_dict(confirmed["bilateral_contract"])
    return bridge, str(started["session_id"]), contract


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


def test_resolve_bilateral_contract_rejects_unretained_in_memory_object(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    """An already-instantiated BilateralPlanningContract that this connector's
    bridge never retained (e.g. confirmed against a different bridge/session,
    or held only in memory) must never be returned directly. It must be
    rejected even when passed straight to _resolve_bilateral_contract, and it
    must not be usable without a confirmation_session_id."""
    connector = AuraArenaArchitectConnector(repo_root=".")

    # No confirmation_session_id at all: rejected outright, even though the
    # object itself is a legitimately confirmed contract from some other
    # session/bridge.
    with pytest.raises(ValueError, match="confirmation_session_id is required"):
        connector._resolve_bilateral_contract(bilateral_contract, "")

    # A confirmation_session_id that this connector's bridge never retained
    # (nothing has been confirmed on this fresh bridge/connector) must also
    # be rejected -- the object cannot substitute for canonical retained
    # confirmation lookup.
    with pytest.raises(ValueError):
        connector._resolve_bilateral_contract(bilateral_contract, "unretained-session-id")


def test_resolve_bilateral_contract_accepts_object_only_via_matching_session_id(
    bilateral_session: tuple[AuraAgentArenaBridge, str, BilateralPlanningContract],
) -> None:
    """A BilateralPlanningContract object is only accepted when it resolves,
    by contract_digest, against the canonical bridge-retained confirmation
    identified by its own confirmation_session_id."""
    bridge, session_id, bilateral_contract = bilateral_session
    connector = AuraArenaArchitectConnector(repo_root=".", bridge=bridge)

    resolved = connector._resolve_bilateral_contract(bilateral_contract, session_id)
    assert resolved.contract_digest == bilateral_contract.contract_digest

    # A different (unrelated, never-retained) session id must still be
    # rejected even though the supplied object is otherwise well-formed.
    with pytest.raises(ValueError):
        connector._resolve_bilateral_contract(bilateral_contract, "some-other-session-id")


def test_connector_cannot_select_higher_scoring_ineligible_plan(
    bilateral_session: tuple[AuraAgentArenaBridge, str, BilateralPlanningContract],
) -> None:
    bridge, session_id, bilateral_contract = bilateral_session
    complete = _complete_plan(bilateral_contract)
    complete["architecture_reuse"] = False
    complete["acceptance_criteria"] = []
    incomplete = deepcopy(complete)
    incomplete["negative_requirement_coverage"] = {}
    incomplete["coverage_tags"] = ["bilateral", "extra"]
    incomplete["architecture_reuse"] = True
    incomplete["acceptance_criteria"] = [
        "This otherwise higher-scoring plan must still lose."
    ]
    connector = AuraArenaArchitectConnector(repo_root=".", bridge=bridge)
    result = connector.compare_plans(
        objective="Choose only a bilaterally eligible plan.",
        candidates=[
            {"candidate_id": "incomplete", "plan": incomplete},
            {"candidate_id": "complete", "plan": complete},
        ],
        required_capabilities=["bilateral"],
        bilateral_contract=bilateral_contract,
        confirmation_session_id=session_id,
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


@pytest.mark.parametrize(
    "failure_class",
    [
        "INTENT_FIDELITY",
        "POSITIVE_REQUIREMENT",
        "NEGATIVE_REQUIREMENT",
        "PLAN_ASSUMPTION_INVALIDATED",
    ],
)
def test_council_never_overrides_deterministic_bilateral_denials(
    failure_class: str,
) -> None:
    routed = route_compass_failure_classes([failure_class])
    assert routed["route"] == "HUMAN_RECONFIRMATION_REQUIRED"
    assert routed["council_override_allowed"] is False


def test_bilateral_plan_rejects_changed_semantic_definition(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan = _complete_plan(bilateral_contract)
    plan["semantic_definitions"][0]["definition"] = "caller-rewritten meaning"
    gate = evaluate_bilateral_plan(
        plan,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    assert "SEMANTIC_DEFINITION" in gate.failure_classes


def test_bilateral_plan_rejects_unadmitted_verifier(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan = _complete_plan(bilateral_contract)
    requirement = bilateral_contract.negative_requirements[0]
    plan["negative_requirement_coverage"][requirement]["verifier"] = "caller-test"
    gate = evaluate_bilateral_plan(
        plan,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    assert "NEGATIVE_REQUIREMENT" in gate.failure_classes


def test_meaning_change_cannot_echo_old_confirmation(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan = _complete_plan(bilateral_contract)
    plan["plan_revision"] = {
        "meaning_changed": True,
        "human_reconfirmed": True,
        "confirmation_digest": bilateral_contract.confirmation_digest,
    }
    gate = evaluate_bilateral_plan(
        plan,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    assert "PLAN_REVISION_RECONFIRMATION" in gate.failure_classes


def test_prepare_rejects_forged_unretained_contract(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    bridge = AuraAgentArenaBridge(repo_root=".")
    result = bridge.aura_prepare_arena(
        objective="Do not trust a caller-created bilateral contract.",
        target_file="aura_arena_architect_connector.py",
        bilateral_contract=bilateral_contract.to_dict(),
        bilateral_proof_plan=_complete_plan(bilateral_contract),
    )
    assert result["ok"] is False
    assert "confirmation_session_id is required" in result["message"]


def test_prepare_rejects_gate_only_input_without_retained_confirmation(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    plan = _complete_plan(bilateral_contract)
    gate = evaluate_bilateral_plan(
        plan,
        bilateral_contract,
        observed_repository_head=bilateral_contract.repository_head,
        observed_source_tree_digest=bilateral_contract.source_tree_digest,
        observed_at=time.time(),
    )
    bridge = AuraAgentArenaBridge(repo_root=".")
    result = bridge.aura_prepare_arena(
        objective="A gate-only request must not bypass retained confirmation.",
        target_file="aura_arena_architect_connector.py",
        bilateral_plan_gate=gate.to_dict(),
    )
    assert result["ok"] is False
    assert "confirmation_session_id is required" in result["message"]


def test_prepare_rejects_proof_plan_only_input_without_retained_confirmation(
    bilateral_contract: BilateralPlanningContract,
) -> None:
    bridge = AuraAgentArenaBridge(repo_root=".")
    result = bridge.aura_prepare_arena(
        objective="A proof-plan-only request must not bypass retained confirmation.",
        target_file="aura_arena_architect_connector.py",
        bilateral_proof_plan=_complete_plan(bilateral_contract),
    )
    assert result["ok"] is False
    assert "confirmation_session_id is required" in result["message"]


def test_prepare_forces_gate_to_exact_prepared_task(
    bilateral_contract: BilateralPlanningContract,
) -> None:
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
    contract = BilateralPlanningContract.from_dict(confirmed["bilateral_contract"])

    plan = _complete_plan(contract)
    # A benign-looking act_tasks list that (mis)declares an in-scope file while
    # the request actually targets an out-of-scope file must never authorize
    # that out-of-scope target_file for the task actually being prepared.
    plan["act_tasks"] = [
        {
            "task_id": "BILATERAL-1",
            "objective": "Claim scope over the allowed file only.",
            "target_file": "aura_arena_architect_connector.py",
            "target_symbol": "assess_plan",
            "acceptance": "The deterministic gate passes before scoring.",
            "expected_output": "UNIFIED_DIFF",
            "tests": ["tests/test_aura_bilateral_planning_enforcement.py"],
        }
    ]

    result = bridge.aura_prepare_arena(
        objective="Attempt to smuggle an out-of-scope target via act_tasks.",
        target_file="out_of_scope_file.py",
        confirmation_session_id=started["session_id"],
        bilateral_proof_plan=plan,
    )
    assert result["ok"] is False
    assert result["error_category"] == "scope_too_broad"


@pytest.mark.parametrize("raised", [OSError("git worktree unreadable"),
                                     subprocess.SubprocessError("git call failed")])
def test_intent_refinement_confirm_returns_protocol_error_on_repository_lookup_failure(
    monkeypatch: pytest.MonkeyPatch,
    raised: Exception,
) -> None:
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

    def _boom(*args: object, **kwargs: object) -> None:
        raise raised

    monkeypatch.setattr("aura_arena_gate_dialogue._repository_identity", _boom)

    result = bridge.intent_refinement_confirm(
        session_id=started["session_id"],
        allowed_paths=["aura_arena_architect_connector.py"],
        human_reviewer="pytest-human",
    )
    assert result["ok"] is False
    assert result["error_category"] == "mcp_protocol_error"

    state = bridge._intent_refinements[str(started["session_id"])]
    assert state["confirmation_in_progress"] is False
    assert state.get("confirmed") is None

    # The session must not be bricked: a retry without the induced failure
    # can still confirm successfully.
    monkeypatch.undo()
    confirmed = bridge.intent_refinement_confirm(
        session_id=started["session_id"],
        allowed_paths=["aura_arena_architect_connector.py"],
        human_reviewer="pytest-human",
    )
    assert confirmed["ok"] is True


def test_prepare_deterministic_denial_is_fail_closed(
    bilateral_contract: BilateralPlanningContract,
) -> None:
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
    contract = BilateralPlanningContract.from_dict(confirmed["bilateral_contract"])

    plan = _complete_plan(contract)
    plan["negative_requirement_coverage"] = {}

    result = bridge.aura_prepare_arena(
        objective="A plan missing negative coverage must be denied, not proposed.",
        target_file="aura_arena_architect_connector.py",
        target_symbol="assess_plan",
        confirmation_session_id=started["session_id"],
        bilateral_proof_plan=plan,
    )
    assert result["ok"] is False
    assert result["error_category"] == "scope_too_broad"
    assert "NEGATIVE_REQUIREMENT" in result["repair_hint"]


def test_mcp_rejects_non_object_bilateral_arguments() -> None:
    response = handle_request(
        AuraAgentArenaBridge(repo_root="."),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "aura_prepare_arena",
                "arguments": {
                    "objective": "Fail closed.",
                    "bilateral_contract": [],
                },
            },
        },
    )
    assert response is not None
    result = response["result"]
    assert result["isError"] is True


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
