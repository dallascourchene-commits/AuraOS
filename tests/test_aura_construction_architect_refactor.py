from __future__ import annotations

from pathlib import Path

import pytest

from aura_architect_control import normalize_control_profile
from aura_arena_architect_connector import AuraArenaArchitectConnector
from aura_construction_architect_refactor import (
    EXISTING_MODULES,
    NOT_MEASURED,
    REQUIRED_CAPABILITIES,
    SELECTED_PLAN_ID,
    SOURCE_SHARDS,
    build_refactor_plan_candidates,
    run_construction_architect_refactor,
)
from aura_work_splitter import split_by_file, work_split_to_act_capsules


def test_selective_council_v3_selects_governed_surgeon_plan(tmp_path: Path):
    control = normalize_control_profile(
        {
            "surface": "native",
            "council_mode": "SELECTIVE_V3",
            "council_call_budget": 6,
            "critic_lanes": ["scope", "tests", "sequence", "rollback", "cost"],
            "surgeon_mode": "STAGE_AND_VERIFY",
            "record_outputs": False,
        }
    )
    result = AuraArenaArchitectConnector(tmp_path, bridge=object()).compare_plans(
        objective="Verify the SCO Construction Phase 3 refactor.",
        candidates=build_refactor_plan_candidates(),
        required_capabilities=REQUIRED_CAPABILITIES,
        control=control,
        surface="native",
        record=False,
        benchmark=False,
    )
    assert result["selected_candidate_id"] == SELECTED_PLAN_ID
    assert result["selected_assessment"]["coverage_fraction"] == 1.0
    assert result["selected_assessment"]["exact_task_fraction"] == 1.0
    assert result["selected_assessment"]["architecture_reuse"] is True
    assert result["actual_model_calls"] == 0


def test_selected_plan_uses_exact_bounded_source_shards():
    candidate = next(
        item
        for item in build_refactor_plan_candidates()
        if item["candidate_id"] == SELECTED_PLAN_ID
    )
    tasks = candidate["plan"]["act_tasks"]
    assert len(tasks) == len(SOURCE_SHARDS) == 3
    assert {item["target_file"] for item in tasks} == {
        "aura_construction_adapter.py",
        "aura_construction_fixtures.py",
        "aura_construction_benchmark.py",
    }
    assert all(item["target_symbol"] for item in tasks)
    assert all(item["expected_output"] == "UNIFIED_DIFF" for item in tasks)
    assert all(item["allowed_scope"].startswith("single ") for item in tasks)


def test_native_control_cannot_gain_production_or_vsa_authority():
    profile = normalize_control_profile(
        {
            "surface": "native",
            "council_mode": "SELECTIVE_V3",
            "surgeon_mode": "STAGE_AND_VERIFY",
        },
        benchmark=True,
    )
    payload = profile.to_dict()
    assert payload["human_review_required"] is True
    assert payload["production_mutation"] is False
    assert payload["vsa_patch_authority"] is False
    assert payload["patch_authority"] == "exact_source_spans_and_hashes_only"


def test_work_splitter_emits_patch_authority_bounded_capsules():
    split = split_by_file([item["target_file"] for item in SOURCE_SHARDS])
    capsules = work_split_to_act_capsules(split)
    assert len(split["child_tasks"]) == 3
    assert len(capsules["act_capsules"]) == 3
    assert all(item["patch_authority"] == "exact_source_spans_and_hashes_only" for item in capsules["act_capsules"])
    assert all(item["vsa_patch_authority"] is False for item in capsules["act_capsules"])


def test_plan_candidates_reuse_existing_owners_and_do_not_invent_usage():
    candidates = build_refactor_plan_candidates()
    selected = next(item for item in candidates if item["candidate_id"] == SELECTED_PLAN_ID)
    assert set(EXISTING_MODULES).issubset(selected["plan"]["existing_modules"])
    assert selected["plan"]["architecture_reuse"] is True
    assert all(
        item["token_usage"]["measurement_class"] == NOT_MEASURED
        and item["token_usage"]["provider_reported"] is None
        for item in candidates
    )


def test_architect_refactor_rejects_missing_base_sha(tmp_path: Path):
    with pytest.raises(ValueError, match="base_sha is required"):
        run_construction_architect_refactor(repo_root=tmp_path, base_sha="")


def test_architect_refactor_rejects_absolute_output_path(tmp_path: Path):
    with pytest.raises(ValueError, match="repository-relative"):
        run_construction_architect_refactor(
            repo_root=tmp_path,
            base_sha="abc123",
            output_dir=tmp_path / "absolute-output",
        )
