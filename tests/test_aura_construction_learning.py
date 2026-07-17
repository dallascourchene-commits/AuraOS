from __future__ import annotations

from pathlib import Path

import pytest

from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_construction_learning import (
    CONSTRUCTION_LEARNING_VERSION,
    NOT_MEASURED,
    run_construction_phase3_learning,
)


@pytest.fixture(scope="module")
def learning_result(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict]:
    output = tmp_path_factory.mktemp("construction-learning")
    result = run_construction_phase3_learning(
        repo_root=".",
        output_dir=output,
        experience_count=15,
        iterations_per_experience=1,
        seed_base=2000,
    )
    return output, result


def test_learning_uses_distinct_single_scenario_permutation_episodes(
    learning_result: tuple[Path, dict],
):
    _, result = learning_result
    series = result["benchmark_series"]
    records = result["experience_ledger"]["records"]
    assert result["ok"] is True
    assert result["version"] == CONSTRUCTION_LEARNING_VERSION
    assert series["episode_count"] == 15
    assert series["scenario_count"] == 1
    assert series["objective_count"] == 1
    assert series["unique_episode_digests"] == 15
    assert series["unique_evaluation_digests"] == 1
    assert series["unique_recommendations"] == 1
    assert len({item["seed"] for item in records}) == 15
    assert len({item["episode_digest"] for item in records}) == 15
    assert all(
        item["execution_class"] == "SYNTHETIC_PERMUTATION" for item in records
    )
    assert all(item["eligible_for_generalization_claim"] is False for item in records)
    assert all(item["idempotent_replay"] is False for item in records)


def test_learning_preserves_crucible_and_authority_boundaries(
    learning_result: tuple[Path, dict],
):
    _, result = learning_result
    boundaries = result["claim_boundaries"]
    crucible = result["crucible"]
    assert boundaries["source_episode_cloning"] is False
    assert boundaries["single_synthetic_scenario"] is True
    assert boundaries["independent_permutation_executions"] is True
    assert boundaries["generalization_claimed"] is False
    assert boundaries["all_proposal_thresholds_expected"] is False
    assert boundaries["content_addressed_payload_excludes_wall_clock_timing"] is True
    assert boundaries["active_grammar_mutated"] is False
    assert boundaries["physical_work_authorized"] is False
    assert boundaries["payment_released"] is False
    assert crucible["threshold_scope"] == "PROPOSAL_ONLY"
    assert crucible["thresholds_have_runtime_authority"] is False
    assert crucible["automatic_grammar_promotion"] is False
    assert crucible["automatic_commit"] is False
    assert crucible["automatic_push"] is False
    assert crucible["automatic_merge"] is False
    assert crucible["required_next_gate"] == "VERIFIER_AND_HUMAN_REVIEW"
    assert all(
        proposal["validation"]["all_proposal_thresholds_met"] is False
        for proposal in crucible["proposals"]
    )


def test_learning_does_not_invent_human_provider_or_project_measurements(
    learning_result: tuple[Path, dict],
):
    output, result = learning_result
    series = result["benchmark_series"]
    boundaries = result["claim_boundaries"]
    assert series["provider_tokens"] == NOT_MEASURED
    assert series["provider_cost"] == NOT_MEASURED
    assert series["real_project_savings"] == NOT_MEASURED
    assert boundaries["provider_tokens_and_cost"] == NOT_MEASURED
    assert boundaries["real_project_savings"] == NOT_MEASURED
    assert boundaries["production_readiness"] == "NOT_CLAIMED"

    with ArenaExperienceLedger(".", db_path=output / "arena_experience.db") as ledger:
        rows = ledger.history(arena_id="sco_construction", limit=100)
    assert len(rows) == 15
    assert all(row["outcome_vector"]["human_alignment"] is None for row in rows)
    assert all(
        row["outcome_vector"]["measurement_classes"]["human_alignment"]
        == "UNAVAILABLE"
        for row in rows
    )


def test_learning_replays_idempotently_without_latency_digest_conflicts(
    learning_result: tuple[Path, dict],
):
    output, first = learning_result
    second = run_construction_phase3_learning(
        repo_root=".",
        output_dir=output,
        experience_count=15,
        iterations_per_experience=1,
        seed_base=2000,
    )
    first_records = first["experience_ledger"]["records"]
    second_records = second["experience_ledger"]["records"]
    assert [item["experience_digest"] for item in second_records] == [
        item["experience_digest"] for item in first_records
    ]
    assert all(item["idempotent_replay"] is True for item in second_records)
    assert second["experience_ledger"]["status"]["record_count"] == 15


def test_learning_rejects_invalid_execution_bounds(tmp_path: Path):
    for experience_count in (14, 501):
        with pytest.raises(ValueError, match="experience_count must be between"):
            run_construction_phase3_learning(
                repo_root=".",
                output_dir=tmp_path / f"count-{experience_count}",
                experience_count=experience_count,
            )
    for iterations in (0, 10_001):
        with pytest.raises(ValueError, match="positive bounded integer"):
            run_construction_phase3_learning(
                repo_root=".",
                output_dir=tmp_path / f"iterations-{iterations}",
                iterations_per_experience=iterations,
            )
    for seed in (-1, 1.5):
        with pytest.raises(ValueError, match="non-negative integer"):
            run_construction_phase3_learning(
                repo_root=".",
                output_dir=tmp_path / f"seed-{seed}",
                seed_base=seed,
            )


def test_learning_rejects_repository_root_as_output(tmp_path: Path):
    with pytest.raises(ValueError, match="may not be the repository root"):
        run_construction_phase3_learning(
            repo_root=tmp_path,
            output_dir=tmp_path,
        )
