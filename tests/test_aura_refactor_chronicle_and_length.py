from __future__ import annotations

import json
from pathlib import Path

from aura_architect_council_v2 import (
    LengthAwareArchitectFusionCouncil,
    LengthAwareArchitectModelRouter,
    profile_refactor_length,
)
from aura_multistep_refactor_benchmark import run_benchmark
from aura_refactor_chronicle import RefactorChronicle


def test_length_profile_distinguishes_short_and_long_refactors() -> None:
    short = profile_refactor_length(
        {
            "act_tasks": [
                {
                    "task_id": "A1",
                    "target_file": "a.py",
                    "target_symbol": "f",
                    "size": "S",
                }
            ]
        }
    )
    long = profile_refactor_length(
        {
            "act_tasks": [
                {
                    "task_id": f"A{index}",
                    "target_file": f"a{index}.py",
                    "target_symbol": f"f{index}",
                    "size": "L" if index in {4, 7} else "S",
                    "depends_on": [f"A{index - 1}"] if index > 1 else [],
                }
                for index in range(1, 9)
            ]
        }
    )
    assert short.length_class == "SHORT"
    assert short.council_recommended is False
    assert long.length_class == "LONG"
    assert long.council_recommended is True
    assert long.task_count == 8
    assert long.dependency_edge_count == 7
    assert long.sequential_depth_estimate == 8
    assert long.estimated_max_model_turns == 24


def test_council_v2_preserves_full_plan_contract(tmp_path: Path) -> None:
    router = LengthAwareArchitectModelRouter(repo_root=tmp_path, model_caller=None, ledger_path=tmp_path / "ledger.jsonl")
    council = LengthAwareArchitectFusionCouncil(router)
    normalized = council._normalize_plan_spec(
        {
            "architecture_decision": "Use explicit adapters.",
            "target_file": "aura_live_architect.py",
            "target_symbol": "ArchitectFusionCouncil",
            "acceptance_criteria": ["All existing tests pass."],
            "rollback_conditions": ["Restore prior adapter on regression."],
            "risk_map": ["Public plan contract compatibility."],
            "constraints": ["No direct production mutation."],
            "escalation_rules": ["Two failed repairs require Judge review."],
            "act_tasks": [
                {
                    "task_id": "A1",
                    "objective": "Preserve the plan contract.",
                    "target_file": "aura_live_architect.py",
                    "target_symbol": "ArchitectFusionCouncil",
                    "allowed_scope": "one class method",
                    "acceptance": "Fields survive normalization.",
                    "expected_output": "UNIFIED_DIFF",
                }
            ],
        },
        intent="Preserve the Council plan contract",
        inferred_file="aura_live_architect.py",
        target_symbol="ArchitectFusionCouncil",
        topological_grounding={},
        source="test",
    )
    assert normalized is not None
    assert normalized["acceptance_criteria"] == ["All existing tests pass."]
    assert normalized["rollback_conditions"] == ["Restore prior adapter on regression."]
    assert normalized["risk_map"] == ["Public plan contract compatibility."]
    assert normalized["constraints"] == ["No direct production mutation."]
    assert normalized["escalation_rules"] == ["Two failed repairs require Judge review."]
    assert normalized["length_profile"]["length_class"] == "SHORT"


def test_refactor_chronicle_records_tokens_and_projects_experience(tmp_path: Path) -> None:
    chronicle = RefactorChronicle(
        tmp_path,
        path=tmp_path / "chronicle.jsonl",
        experience_db_path=tmp_path / "experience.db",
    )
    first = chronicle.record(
        "refactor_worker_completed",
        correlation_id="REF-1",
        session_id="S-1",
        objective="Refactor safely",
        plan_phase_hash="PLAN-1",
        task_id="A1",
        gate="ACT",
        status="WAITING_FOR_MODEL",
        provider="fixture",
        model="test-model",
        input_tokens_estimated=120,
        output_tokens_estimated=30,
        input_tokens_reported=118,
        output_tokens_reported=29,
        cost_usd_reported=0.001,
        prompt="bounded prompt",
        response="bounded response",
        payload={"api_key": "sk-abcdefghijklmnopqrstuvwxyz", "stage_ok": True},
    )
    assert first["ok"] is True
    summary = chronicle.summary(correlation_id="REF-1", session_id="S-1")
    assert summary["token_totals"]["input_tokens_estimated"] == 120
    assert summary["token_totals"]["output_tokens_estimated"] == 30
    assert summary["token_totals"]["input_tokens_reported"] == 118
    assert summary["token_totals"]["output_tokens_reported"] == 29
    assert summary["token_totals"]["cost_usd_reported"] == 0.001
    row = chronicle.history(correlation_id="REF-1")[0]
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in json.dumps(row)

    final = chronicle.finalize_experience(
        correlation_id="REF-1",
        session_id="S-1",
        objective="Refactor safely",
        plan_phase_hash="PLAN-1",
        final_outcome="READY_FOR_HUMAN_REVIEW",
        state_before="OPEN",
        state_after="READY_FOR_HUMAN_REVIEW",
        selected_transition="human_review",
        provider="fixture",
        model="test-model",
        raw_evidence_refs=[str(tmp_path / "chronicle.jsonl")],
        learning_notes=["One bounded step passed."],
    )
    assert final["ok"] is True
    assert final["experience_projection"] is True
    assert (tmp_path / "experience.db").is_file()


def test_multistep_benchmark_records_length_repair_and_io_tokens(tmp_path: Path) -> None:
    report = run_benchmark(tmp_path, tmp_path / "benchmark", [1, 4])
    cases = {case["task_count"]: case for case in report["cases"]}
    assert cases[1]["terminal_status"] == "READY_FOR_HUMAN_REVIEW"
    assert cases[4]["terminal_status"] == "READY_FOR_HUMAN_REVIEW"
    assert cases[4]["completed_tasks"] == 4
    assert cases[4]["turn_count"] == 5
    assert cases[4]["repair_event_count"] >= 1
    assert cases[4]["input_tokens_estimated"] > cases[1]["input_tokens_estimated"]
    assert cases[4]["output_tokens_estimated"] > cases[1]["output_tokens_estimated"]
    assert cases[4]["input_tokens_reported"] is not None
    assert cases[4]["output_tokens_reported"] is not None
    assert (tmp_path / "benchmark" / "multistep_refactor_benchmark.json").is_file()
    assert (tmp_path / "benchmark" / "benchmark_registry.jsonl").is_file()
    assert (tmp_path / "benchmark" / "tasks-4" / "refactor_chronicle.jsonl").is_file()
