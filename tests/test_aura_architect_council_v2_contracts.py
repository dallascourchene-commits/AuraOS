from __future__ import annotations

from aura_architect_council_v2 import (
    LengthAwareArchitectFusionCouncil,
    _phase_hash,
    profile_refactor_length,
)


def _task(task_id: str, *, depends_on: list[str] | None = None) -> dict[str, object]:
    task: dict[str, object] = {
        "task_id": task_id,
        "objective": f"Implement {task_id}",
        "target_file": f"{task_id.lower()}.py",
        "target_symbol": task_id,
        "acceptance": f"test_{task_id.lower()} passes",
        "expected_output": "UNIFIED_DIFF",
    }
    if depends_on is not None:
        task["depends_on"] = depends_on
    return task


def test_music_fused_candidate_inherits_governance_contract_before_scoring() -> None:
    council = LengthAwareArchitectFusionCouncil(object())  # type: ignore[arg-type]
    governance = {
        "acceptance_criteria": ["all verifier gates pass"],
        "rollback_conditions": ["rollback on failed regression"],
        "risk_map": ["cross-module contract drift"],
        "constraints": ["HUMAN_REVIEW_REQUIRED"],
        "escalation_rules": ["escalate interface failures"],
    }
    source_plan = {
        "architecture_decision": "Use a bounded staged refactor.",
        "target_file": "a.py",
        "target_symbol": "A",
        "act_tasks": [_task("A")],
        **governance,
    }
    source = council._candidate(
        "planner_1",
        source_plan,
        cost_tier="premium",
        source="premium_planner",
    )
    assert source["plan_contract_completeness"] == 1.0

    fused = council._candidate(
        "music_mitosis_fusion",
        {
            "architecture_decision": "Fuse the grounded candidate with advisory research.",
            "target_file": "a.py",
            "target_symbol": "A",
            "act_tasks": [_task("A")],
            "music_mitosis": {"supporting_candidate_ids": ["planner_1"]},
        },
        cost_tier="free",
        source="music_mitosis_fusion",
    )

    for field, expected in governance.items():
        assert fused["plan"][field] == expected
    assert fused["plan_contract_completeness"] == 1.0
    assert fused["plan"]["length_profile"]["task_count"] == 1
    payload = {key: value for key, value in fused.items() if key != "phase_hash"}
    assert fused["phase_hash"] == _phase_hash(payload)


def test_length_profile_resolves_forward_dependencies_and_bounds_cycles() -> None:
    forward = profile_refactor_length(
        {"act_tasks": [_task("A", depends_on=["B"]), _task("B")]}
    )
    assert forward.dependency_edge_count == 1
    assert forward.sequential_depth_estimate == 2

    cyclic = profile_refactor_length(
        {
            "act_tasks": [
                _task("A", depends_on=["B"]),
                _task("B", depends_on=["A"]),
            ]
        }
    )
    assert cyclic.sequential_depth_estimate >= 2
    assert "dependency_cycle_detected" in cyclic.reasons
    assert cyclic.council_recommended is True

    unresolved = profile_refactor_length(
        {"act_tasks": [_task("A", depends_on=["MISSING"])]}
    )
    assert "unresolved_task_dependencies" in unresolved.reasons
    assert unresolved.council_recommended is True
