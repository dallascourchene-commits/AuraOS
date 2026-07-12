"""Focused Phase C3 contracts for bounded variants, isolation, splits, and Agent IR."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path

from aura_agent_ir_induction import induce_agent_ir_procedure
from aura_capsule_trial_cli import build_parser
from aura_capsule_trial_runner import (
    TRIAL_EXECUTION_LEASE,
    aggregate_trial_observations,
    run_capsule_trial,
)
from aura_capsule_trial_store import CapsuleTrialStore
from aura_capsule_variant_generator import generate_capsule_variants, load_capsule_trial_policy
from aura_phase_c3_trial_crucible import (
    CapsuleTrialCrucibleService,
    load_capsule_trial_cases,
    validate_case_splits,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_REF = ".aura/capsule_trial_policies/coding_localize.v1.json"
CASES_REF = ".aura/capsule_trial_cases/coding_localize.v1.json"
LEASE = [TRIAL_EXECUTION_LEASE, "tool:topology_inspector"]


def test_variant_generator_emits_baseline_and_tightening_only():
    policy = load_capsule_trial_policy(POLICY_REF, repo_root=REPO_ROOT)
    result = generate_capsule_variants(policy, repo_root=REPO_ROOT)
    assert result["ok"], result
    variants = result["variant_objects"]
    assert variants[0].overrides == {}
    assert len(variants) <= policy.maximum_variants
    baseline = variants[0]
    for variant in variants:
        assert set(variant.overrides) <= set(policy.proposal_safe_dimensions)
        assert variant.requested_capabilities == baseline.requested_capabilities
        assert variant.component_digests == baseline.component_digests
        assert variant.data_aperture["maximum_files"] <= baseline.data_aperture["maximum_files"]
        assert variant.data_aperture["maximum_symbols"] <= baseline.data_aperture["maximum_symbols"]
        assert variant.data_aperture["maximum_lines"] <= baseline.data_aperture["maximum_lines"]
        assert variant.execution_budget["input_tokens"] <= baseline.execution_budget["input_tokens"]
        assert variant.execution_budget["output_tokens"] <= baseline.execution_budget["output_tokens"]
        assert variant.execution_budget["tool_calls"] <= baseline.execution_budget["tool_calls"]
        assert variant.execution_budget["wall_seconds"] <= baseline.execution_budget["wall_seconds"]


def test_variant_generator_rejects_baseline_expansion():
    policy = load_capsule_trial_policy(POLICY_REF, repo_root=REPO_ROOT)
    expanded = replace(
        policy,
        proposal_safe_dimensions={"data_aperture.maximum_files": (999,)},
    )
    result = generate_capsule_variants(expanded, repo_root=REPO_ROOT)
    assert result["ok"] is False
    assert result["reason"] == "proposal_dimension_expands_or_invalidates_baseline"


def test_case_splits_are_disjoint_and_complete():
    cases, _ = load_capsule_trial_cases(CASES_REF, repo_root=REPO_ROOT)
    report = validate_case_splits(cases)
    assert report["passed"], report
    assert all(report["datasets"][name] for name in ("TRAIN", "VALIDATION", "SHADOW"))
    assert report["pairwise_disjoint"] is True


def test_duplicate_case_id_fails_split_validation():
    cases, _ = load_capsule_trial_cases(CASES_REF, repo_root=REPO_ROOT)
    duplicate = replace(cases[0], dataset="SHADOW")
    report = validate_case_splits([*cases, duplicate])
    assert report["passed"] is False


def test_trial_requires_feature_flag_and_independent_lease():
    policy = load_capsule_trial_policy(POLICY_REF, repo_root=REPO_ROOT)
    generated = generate_capsule_variants(policy, repo_root=REPO_ROOT)
    cases, _ = load_capsule_trial_cases(CASES_REF, repo_root=REPO_ROOT)
    variant = generated["variant_objects"][0]
    disabled = run_capsule_trial(
        run_id="R1",
        variant=variant,
        case=cases[0],
        executor_id=policy.executor_id,
        repetition=0,
        repo_root=REPO_ROOT,
        trials_enabled=False,
        lease_capabilities=LEASE,
    )
    assert disabled["reason"] == "c3_trials_feature_disabled"
    unleased = run_capsule_trial(
        run_id="R2",
        variant=variant,
        case=cases[0],
        executor_id=policy.executor_id,
        repetition=0,
        repo_root=REPO_ROOT,
        trials_enabled=True,
        lease_capabilities=["tool:topology_inspector"],
    )
    assert TRIAL_EXECUTION_LEASE in unleased["missing"]


def test_builtin_trial_is_reproducible_and_dissolves_sandbox():
    policy = load_capsule_trial_policy(POLICY_REF, repo_root=REPO_ROOT)
    generated = generate_capsule_variants(policy, repo_root=REPO_ROOT)
    cases, _ = load_capsule_trial_cases(CASES_REF, repo_root=REPO_ROOT)
    variant = generated["variant_objects"][0]
    observations = [
        run_capsule_trial(
            run_id="REPRO",
            variant=variant,
            case=cases[0],
            executor_id=policy.executor_id,
            repetition=index,
            repo_root=REPO_ROOT,
            trials_enabled=True,
            lease_capabilities=LEASE,
        )
        for index in range(2)
    ]
    assert all(item["ok"] for item in observations)
    assert all(item["sandbox"]["dissolution_verified"] for item in observations)
    assert all(item["arbitrary_code_executed"] is False for item in observations)
    assert all(item["native_fallback_used"] is False for item in observations)
    summary = aggregate_trial_observations(observations)
    assert summary["reproducible"] is True
    assert summary["model_calls"] == 0


def test_agent_ir_pure_requires_independent_gates():
    policy = load_capsule_trial_policy(POLICY_REF, repo_root=REPO_ROOT)
    generated = generate_capsule_variants(policy, repo_root=REPO_ROOT)
    cases, _ = load_capsule_trial_cases(CASES_REF, repo_root=REPO_ROOT)
    variant = generated["variant_objects"][0]
    observations = []
    for case in cases:
        observations.append(run_capsule_trial(
            run_id="IR",
            variant=variant,
            case=case,
            executor_id=policy.executor_id,
            repetition=0,
            repo_root=REPO_ROOT,
            trials_enabled=True,
            lease_capabilities=LEASE,
        ))
    morphology = {
        "DIR": "OUT",
        "ASP": "GROUND",
        "CLASS": "LOCALIZE",
        "SUBJ": "REPOSITORY",
        "VOICE": "HUMAN_AGENT",
        "STEM": "INSPECT",
    }
    procedure = induce_agent_ir_procedure(
        run_id="IR",
        policy=policy,
        variant=variant,
        morphology_signature=morphology,
        observations=observations,
        assessment={
            "all_reproducible": True,
            "validation_passed": True,
            "shadow_passed": True,
        },
    )
    assert procedure.ir_floor == "PURE"
    assert procedure.executable_code_generated is False
    failed = induce_agent_ir_procedure(
        run_id="IR2",
        policy=policy,
        variant=variant,
        morphology_signature=morphology,
        observations=observations,
        assessment={
            "all_reproducible": False,
            "validation_passed": True,
            "shadow_passed": True,
        },
    )
    assert failed.ir_floor == "SHIM"


def test_store_and_cli_expose_no_apply_or_promotion(tmp_path):
    with CapsuleTrialStore(tmp_path, db_path=tmp_path / "c3.db") as store:
        status = store.status()
        assert status["apply_operation_available"] is False
        assert status["promotion_operation_available"] is False
        assert status["installation_operation_available"] is False
        assert not hasattr(store, "apply")
        assert not hasattr(store, "promote")
        assert not hasattr(store, "install")
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert set(commands) == {"status", "run-once", "procedures", "procedure"}


def test_end_to_end_c3_cycle_is_train_selected_and_review_only(tmp_path):
    service = CapsuleTrialCrucibleService(REPO_ROOT, db_path=tmp_path / "c3.db")
    try:
        report = service.run_once(
            policy_ref=POLICY_REF,
            cases_ref=CASES_REF,
            trials_enabled=True,
            lease_capabilities=LEASE,
        )
    finally:
        service.close()
    assert report["ok"], json.dumps(report, indent=2, default=str)
    assert report["winner_selected_from"] == "TRAIN_ONLY"
    assert report["validation_and_shadow_excluded_from_selection"] is True
    assert report["terminal_status"] == "PROCEDURE_INDUCTION_PROPOSED"
    assert report["procedure"]["executable_code_generated"] is False
    assert report["active_capsule_mutated"] is False
    assert report["automatic_code_installation"] is False
    assert report["automatic_commit"] is False
    assert report["automatic_push"] is False
    assert report["automatic_merge"] is False
