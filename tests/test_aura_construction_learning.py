from __future__ import annotations

from pathlib import Path

import pytest

from aura_construction_learning import (
    CONSTRUCTION_LEARNING_VERSION,
    NOT_MEASURED,
    run_construction_phase3_learning,
)


def test_learning_uses_distinct_seeded_synthetic_episodes(tmp_path: Path):
    result = run_construction_phase3_learning(
        repo_root=".",
        output_dir=tmp_path,
        experience_count=15,
        iterations_per_experience=2,
        seed_base=2000,
    )
    series = result["benchmark_series"]
    records = result["experience_ledger"]["records"]
    assert result["ok"] is True
    assert result["version"] == CONSTRUCTION_LEARNING_VERSION
    assert series["episode_count"] == 15
    assert series["unique_episode_digests"] == 15
    assert series["unique_evaluation_digests"] == 1
    assert series["unique_recommendations"] == 1
    assert len({item["seed"] for item in records}) == 15
    assert len({item["episode_digest"] for item in records}) == 15
    assert all(item["execution_class"] == "SYNTHETIC" for item in records)


def test_learning_preserves_crucible_and_authority_boundaries(tmp_path: Path):
    result = run_construction_phase3_learning(
        repo_root=".",
        output_dir=tmp_path,
        experience_count=15,
        iterations_per_experience=1,
    )
    boundaries = result["claim_boundaries"]
    crucible = result["crucible"]
    assert boundaries["source_episode_cloning"] is False
    assert boundaries["independent_seeded_executions"] is True
    assert boundaries["manual_shadow_labels_assigned"] is False
    assert boundaries["active_grammar_mutated"] is False
    assert boundaries["physical_work_authorized"] is False
    assert boundaries["payment_released"] is False
    assert crucible["threshold_scope"] == "PROPOSAL_ONLY"
    assert crucible["automatic_grammar_promotion"] is False
    assert crucible["required_next_gate"] == "VERIFIER_AND_HUMAN_REVIEW"


def test_learning_does_not_invent_provider_or_project_measurements(tmp_path: Path):
    result = run_construction_phase3_learning(
        repo_root=".",
        output_dir=tmp_path,
        experience_count=15,
        iterations_per_experience=1,
    )
    series = result["benchmark_series"]
    boundaries = result["claim_boundaries"]
    assert series["provider_tokens"] == NOT_MEASURED
    assert series["provider_cost"] == NOT_MEASURED
    assert series["real_project_savings"] == NOT_MEASURED
    assert boundaries["provider_tokens_and_cost"] == NOT_MEASURED
    assert boundaries["real_project_savings"] == NOT_MEASURED
    assert boundaries["production_readiness"] == "NOT_CLAIMED"
    assert result["coderabbit_triggered"] is False


def test_learning_rejects_invalid_execution_counts(tmp_path: Path):
    with pytest.raises(ValueError, match="at least 15"):
        run_construction_phase3_learning(
            repo_root=".",
            output_dir=tmp_path,
            experience_count=14,
        )
    with pytest.raises(ValueError, match="positive integer"):
        run_construction_phase3_learning(
            repo_root=".",
            output_dir=tmp_path,
            iterations_per_experience=0,
        )
    with pytest.raises(ValueError, match="seed_base must be an integer"):
        run_construction_phase3_learning(
            repo_root=".",
            output_dir=tmp_path,
            seed_base=1.5,
        )
