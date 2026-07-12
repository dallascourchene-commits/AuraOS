"""Phase C3 isolated capsule trials and proposal-only Agent IR procedure induction."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import secrets
import time
from typing import Any, Iterable

from aura_agent_ir_induction import induce_agent_ir_procedure
from aura_capsule_trial_runner import (
    TRIAL_EXECUTION_LEASE,
    aggregate_trial_observations,
    run_capsule_trial,
)
from aura_capsule_trial_store import CapsuleTrialStore
from aura_capsule_trial_types import (
    C3_TRIAL_CASES_VERSION,
    CapsuleTrialCase,
    CapsuleTrialPolicy,
    CapsuleVariant,
    canonical_digest,
)
from aura_capsule_variant_generator import (
    generate_capsule_variants,
    load_capsule_trial_policy,
)

PHASE_C3_TRIAL_CRUCIBLE_VERSION = "AURA_PHASE_C3_TRIAL_CRUCIBLE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CapsuleTrialCrucibleService:
    """Bounded foreground C3 trial service with no activation or installation path."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        db_path: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.store = CapsuleTrialStore(self.repo_root, db_path=db_path)

    def close(self) -> None:
        self.store.close()

    def status(self) -> dict[str, Any]:
        return {
            **self.store.status(),
            "service_version": PHASE_C3_TRIAL_CRUCIBLE_VERSION,
            "feature_flag_required": True,
            "required_trial_lease": TRIAL_EXECUTION_LEASE,
            "dataset_split": ["TRAIN", "VALIDATION", "SHADOW"],
            "selection_dataset": "TRAIN_ONLY",
            "procedure_floors": ["TEXT", "TYPED", "SPEC", "STUB", "SHIM", "PURE"],
            "arbitrary_code_execution": False,
            "automatic_capsule_activation": False,
            "automatic_code_installation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }

    def run_once(
        self,
        *,
        policy_ref: str,
        cases_ref: str,
        trials_enabled: bool = False,
        lease_capabilities: Iterable[str] = (),
    ) -> dict[str, Any]:
        if not trials_enabled:
            return _denial("c3_trials_feature_disabled")
        lease = {str(item) for item in lease_capabilities if str(item)}
        if TRIAL_EXECUTION_LEASE not in lease:
            return _denial("c3_trial_lease_missing_capability", missing=[TRIAL_EXECUTION_LEASE])

        try:
            policy = load_capsule_trial_policy(policy_ref, repo_root=self.repo_root)
            cases, case_manifest = load_capsule_trial_cases(cases_ref, repo_root=self.repo_root)
        except Exception as exc:  # noqa: BLE001
            return _denial(f"c3_manifest_load_failed:{type(exc).__name__}")
        if case_manifest.get("route_capsule_ref") != policy.route_capsule_ref:
            return _denial("c3_policy_case_capsule_mismatch")
        split_report = validate_case_splits(cases)
        if not split_report.get("passed"):
            return _denial("c3_trial_case_split_invalid", diagnostics=split_report.get("diagnostics") or [])

        generated = generate_capsule_variants(policy, repo_root=self.repo_root)
        if not generated.get("ok"):
            return generated
        variants: list[CapsuleVariant] = list(generated.get("variant_objects") or [])
        if not variants:
            return _denial("c3_no_variants_generated")
        required = {TRIAL_EXECUTION_LEASE, *variants[0].requested_capabilities}
        missing = sorted(required - lease)
        if missing:
            return _denial("c3_trial_lease_missing_capability", missing=missing)

        run_id = f"C3RUN-{secrets.token_hex(10)}"
        started_at = time.time()
        train_cases = [item for item in cases if item.dataset == "TRAIN"]
        validation_cases = [item for item in cases if item.dataset == "VALIDATION"]
        shadow_cases = [item for item in cases if item.dataset == "SHADOW"]

        training: dict[str, list[dict[str, Any]]] = {}
        all_observations: list[dict[str, Any]] = []
        for variant in variants:
            rows = self._execute_cases(
                run_id=run_id,
                variant=variant,
                cases=train_cases,
                policy=policy,
                trials_enabled=trials_enabled,
                lease_capabilities=lease,
            )
            training[variant.variant_id] = rows
            all_observations.extend(rows)
        training_summaries = {
            variant_id: aggregate_trial_observations(rows)
            for variant_id, rows in sorted(training.items())
        }
        winner = _select_train_winner(variants, training_summaries, policy)
        if winner is None:
            report = _failed_report(
                run_id=run_id,
                policy=policy,
                case_manifest=case_manifest,
                generated=generated,
                split_report=split_report,
                training_summaries=training_summaries,
                started_at=started_at,
                reason="no_train_eligible_variant",
            )
            report["storage"] = self.store.record_run(report)
            return report

        baseline = next(item for item in variants if not item.overrides)
        evaluation_variants = [baseline] if winner.variant_id == baseline.variant_id else [baseline, winner]
        validation_rows: dict[str, list[dict[str, Any]]] = {}
        shadow_rows: dict[str, list[dict[str, Any]]] = {}
        for variant in evaluation_variants:
            validation_rows[variant.variant_id] = self._execute_cases(
                run_id=run_id,
                variant=variant,
                cases=validation_cases,
                policy=policy,
                trials_enabled=trials_enabled,
                lease_capabilities=lease,
            )
            shadow_rows[variant.variant_id] = self._execute_cases(
                run_id=run_id,
                variant=variant,
                cases=shadow_cases,
                policy=policy,
                trials_enabled=trials_enabled,
                lease_capabilities=lease,
            )
            all_observations.extend(validation_rows[variant.variant_id])
            all_observations.extend(shadow_rows[variant.variant_id])

        validation_summaries = {
            key: aggregate_trial_observations(value) for key, value in sorted(validation_rows.items())
        }
        shadow_summaries = {
            key: aggregate_trial_observations(value) for key, value in sorted(shadow_rows.items())
        }
        winner_train = training_summaries[winner.variant_id]
        winner_validation = validation_summaries[winner.variant_id]
        winner_shadow = shadow_summaries[winner.variant_id]
        baseline_validation = validation_summaries[baseline.variant_id]
        baseline_shadow = shadow_summaries[baseline.variant_id]
        assessment = _assess_winner(
            policy=policy,
            winner_train=winner_train,
            winner_validation=winner_validation,
            winner_shadow=winner_shadow,
            baseline_validation=baseline_validation,
            baseline_shadow=baseline_shadow,
        )
        winner_observations = [
            *training[winner.variant_id],
            *validation_rows[winner.variant_id],
            *shadow_rows[winner.variant_id],
        ]
        morphology = dict(
            ((generated.get("compiled_capsule") or {}).get("capsule") or {}).get("morphology_signature")
            or {}
        )
        procedure = induce_agent_ir_procedure(
            run_id=run_id,
            policy=policy,
            variant=winner,
            morphology_signature=morphology,
            observations=winner_observations,
            assessment=assessment,
        )

        observation_storage = [self.store.record_observation(item) for item in all_observations]
        procedure_storage = self.store.record_procedure(procedure)
        completed_at = time.time()
        report = {
            "ok": True,
            "version": PHASE_C3_TRIAL_CRUCIBLE_VERSION,
            "run_id": run_id,
            "status": "COMPLETED",
            "terminal_status": "PROCEDURE_INDUCTION_PROPOSED",
            "required_next_gate": "VERIFIER_AND_HUMAN_REVIEW",
            "started_at": started_at,
            "completed_at": completed_at,
            "policy": policy.to_dict(),
            "case_manifest": case_manifest,
            "case_split": split_report,
            "variant_count": len(variants),
            "variants": [item.to_dict() for item in variants],
            "winner_variant_id": winner.variant_id,
            "winner_selected_from": "TRAIN_ONLY",
            "validation_and_shadow_excluded_from_selection": True,
            "training_summaries": training_summaries,
            "validation_summaries": validation_summaries,
            "shadow_summaries": shadow_summaries,
            "winner_assessment": assessment,
            "procedure": procedure.to_dict(),
            "observation_count": len(all_observations),
            "observation_storage": observation_storage,
            "procedure_storage": procedure_storage,
            "isolated_sandbox_contract": "AURA_EPHEMERAL_BUILTIN_ONLY_OR_WASMTIME",
            "arbitrary_code_executed": False,
            "native_fallback_used": False,
            "active_capsule_mutated": False,
            "active_grammar_mutated": False,
            "executable_code_generated": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_capsule_activation": False,
            "automatic_grammar_promotion": False,
            "automatic_code_installation": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_merge": False,
        }
        report["storage"] = self.store.record_run(report)
        return report

    def _execute_cases(
        self,
        *,
        run_id: str,
        variant: CapsuleVariant,
        cases: list[CapsuleTrialCase],
        policy: CapsuleTrialPolicy,
        trials_enabled: bool,
        lease_capabilities: Iterable[str],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for case in cases:
            for repetition in range(policy.repetitions):
                rows.append(run_capsule_trial(
                    run_id=run_id,
                    variant=variant,
                    case=case,
                    executor_id=policy.executor_id,
                    repetition=repetition,
                    repo_root=self.repo_root,
                    trials_enabled=trials_enabled,
                    lease_capabilities=lease_capabilities,
                ))
        return rows


def load_capsule_trial_cases(
    reference: str,
    *,
    repo_root: str | Path = ".",
) -> tuple[list[CapsuleTrialCase], dict[str, Any]]:
    path = _resolve_under(repo_root, reference, ".aura/capsule_trial_cases")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("C3 trial case manifest must contain an object")
    if str(payload.get("schema_version") or "") != C3_TRIAL_CASES_VERSION:
        raise ValueError(f"expected case schema {C3_TRIAL_CASES_VERSION}")
    allowed = {"schema_version", "suite_id", "route_capsule_ref", "cases", "authority"}
    unknown = sorted(set(payload) - allowed)
    if unknown:
        raise ValueError(f"unknown case manifest fields: {unknown}")
    cases = [CapsuleTrialCase.from_dict(item) for item in payload.get("cases") or []]
    if not cases:
        raise ValueError("C3 case manifest contains no cases")
    return cases, {
        "suite_id": str(payload.get("suite_id") or ""),
        "route_capsule_ref": str(payload.get("route_capsule_ref") or ""),
        "case_count": len(cases),
        "manifest_digest": canonical_digest(payload),
        "source_path": path.resolve().relative_to(Path(repo_root).resolve()).as_posix(),
    }


def validate_case_splits(cases: Iterable[CapsuleTrialCase]) -> dict[str, Any]:
    rows = list(cases)
    ids = [item.case_id for item in rows]
    digests = [item.digest() for item in rows]
    diagnostics: list[dict[str, Any]] = []
    if len(ids) != len(set(ids)):
        diagnostics.append({"reason": "duplicate_case_id"})
    if len(digests) != len(set(digests)):
        diagnostics.append({"reason": "duplicate_case_digest_across_datasets"})
    datasets = {name: [item.case_id for item in rows if item.dataset == name] for name in ("TRAIN", "VALIDATION", "SHADOW")}
    for name, case_ids in datasets.items():
        if not case_ids:
            diagnostics.append({"reason": "dataset_empty", "dataset": name})
    return {
        "passed": not diagnostics,
        "datasets": datasets,
        "dataset_digests": {
            name: canonical_digest(tuple(case_ids)) for name, case_ids in datasets.items()
        },
        "pairwise_disjoint": len(ids) == len(set(ids)),
        "diagnostics": diagnostics,
    }


def _select_train_winner(
    variants: list[CapsuleVariant],
    summaries: dict[str, dict[str, Any]],
    policy: CapsuleTrialPolicy,
) -> CapsuleVariant | None:
    eligible: list[CapsuleVariant] = []
    for variant in variants:
        summary = summaries.get(variant.variant_id) or {}
        if not summary.get("all_completed"):
            continue
        if policy.require_reproducibility and not summary.get("reproducible"):
            continue
        if float(summary.get("score_mean") or 0.0) < policy.minimum_train_score:
            continue
        eligible.append(variant)
    if not eligible:
        return None
    eligible.sort(key=lambda item: (
        -float((summaries[item.variant_id]).get("score_mean") or 0.0),
        float((summaries[item.variant_id]).get("total_tokens") or 0.0),
        float((summaries[item.variant_id]).get("wall_seconds") or 0.0),
        item.variant_id,
    ))
    return eligible[0]


def _assess_winner(
    *,
    policy: CapsuleTrialPolicy,
    winner_train: dict[str, Any],
    winner_validation: dict[str, Any],
    winner_shadow: dict[str, Any],
    baseline_validation: dict[str, Any],
    baseline_shadow: dict[str, Any],
) -> dict[str, Any]:
    validation_score = float(winner_validation.get("score_mean") or 0.0)
    shadow_score = float(winner_shadow.get("score_mean") or 0.0)
    baseline_validation_score = float(baseline_validation.get("score_mean") or 0.0)
    baseline_shadow_score = float(baseline_shadow.get("score_mean") or 0.0)
    checks = {
        "train_score": float(winner_train.get("score_mean") or 0.0) >= policy.minimum_train_score,
        "validation_score": validation_score >= policy.minimum_validation_score,
        "shadow_score": shadow_score >= policy.minimum_shadow_score,
        "validation_no_excess_regression": validation_score >= baseline_validation_score - policy.maximum_validation_regression,
        "shadow_no_excess_regression": shadow_score >= baseline_shadow_score - policy.maximum_shadow_regression,
        "train_reproducible": bool(winner_train.get("reproducible")),
        "validation_reproducible": bool(winner_validation.get("reproducible")),
        "shadow_reproducible": bool(winner_shadow.get("reproducible")),
        "all_trials_completed": all(
            bool(summary.get("all_completed"))
            for summary in (winner_train, winner_validation, winner_shadow)
        ),
        "no_budget_failures": sum(int(summary.get("budget_failure_count") or 0) for summary in (winner_train, winner_validation, winner_shadow)) == 0,
        "no_dissolution_failures": sum(int(summary.get("dissolution_failure_count") or 0) for summary in (winner_train, winner_validation, winner_shadow)) == 0,
        "no_model_calls": sum(int(summary.get("model_calls") or 0) for summary in (winner_train, winner_validation, winner_shadow)) == 0,
    }
    return {
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "all_reproducible": all(bool(summary.get("reproducible")) for summary in (winner_train, winner_validation, winner_shadow)),
        "validation_passed": checks["validation_score"] and checks["validation_no_excess_regression"],
        "shadow_passed": checks["shadow_score"] and checks["shadow_no_excess_regression"],
        "baseline_validation_score": baseline_validation_score,
        "winner_validation_score": validation_score,
        "baseline_shadow_score": baseline_shadow_score,
        "winner_shadow_score": shadow_score,
        "threshold_scope": "PROPOSAL_ONLY",
        "runtime_authority": False,
    }


def _failed_report(
    *,
    run_id: str,
    policy: CapsuleTrialPolicy,
    case_manifest: dict[str, Any],
    generated: dict[str, Any],
    split_report: dict[str, Any],
    training_summaries: dict[str, Any],
    started_at: float,
    reason: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "version": PHASE_C3_TRIAL_CRUCIBLE_VERSION,
        "run_id": run_id,
        "status": "COMPLETED_WITHOUT_PROCEDURE",
        "reason": reason,
        "started_at": started_at,
        "completed_at": time.time(),
        "policy": policy.to_dict(),
        "case_manifest": case_manifest,
        "case_split": split_report,
        "variants": generated.get("variants") or [],
        "training_summaries": training_summaries,
        "winner_variant_id": "",
        "active_capsule_mutated": False,
        "executable_code_generated": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_code_installation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def _resolve_under(repo_root: str | Path, reference: str, expected_root: str) -> Path:
    root = Path(repo_root).resolve()
    raw = str(reference or "").strip().replace("\\", "/")
    relative = PurePosixPath(raw)
    expected = PurePosixPath(expected_root)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError("reference must be repository-relative without traversal")
    relative.relative_to(expected)
    path = root.joinpath(*relative.parts)
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(raw)
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def _denial(
    reason: str,
    *,
    missing: list[str] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "DENIED",
        "reason": reason,
        "missing": list(missing or []),
        "diagnostics": list(diagnostics or []),
        "fail_closed": True,
        "active_capsule_mutated": False,
        "active_grammar_mutated": False,
        "executable_code_generated": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_capsule_activation": False,
        "automatic_code_installation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }
