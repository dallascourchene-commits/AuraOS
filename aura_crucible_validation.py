"""Independent validation and shadow replay for Aura Crucible candidates."""
from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_crucible_miner import summarize_outcome_vectors
from aura_crucible_types import CrucibleCandidate, CruciblePolicy, canonical_digest

CRUCIBLE_VALIDATION_VERSION = "AURA_CRUCIBLE_VALIDATION_V2"
_RANK_FIELDS = (
    "unresolved_risk", "declared_evidence_gap", "empirical_uncertainty",
    "semantic_ambiguity", "context_switch_cost", "latency_cost", "token_cost",
    "thermal_cost", "negative_semantic_fit", "negative_user_fit", "stable_transition_id",
)


def validate_manifest_pin(*, repo_root: str | Path, manifest_path: str,
                          manifest_digest: str, arena_id: str,
                          grammar_version: str) -> dict[str, Any]:
    """Compile a repository-local manifest and compare its canonical digest."""

    root = Path(repo_root).resolve()
    raw = str(manifest_path or "").replace("\\", "/")
    try:
        relative = PurePosixPath(raw)
    except (TypeError, ValueError):
        relative = PurePosixPath(".")
    reasons: list[str] = []
    if not raw:
        reasons.append("manifest_path_missing")
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        reasons.append("manifest_path_not_repository_relative")
    resolved = (root / Path(*relative.parts)).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        reasons.append("manifest_path_escapes_repository")
    if not resolved.is_file():
        reasons.append("manifest_file_missing")
    compile_result = None
    if not reasons:
        compile_result = load_and_compile_arena_grammar(resolved)
        if not compile_result.ok or compile_result.grammar is None:
            reasons.append("manifest_compile_failed")
        else:
            grammar = compile_result.grammar
            if compile_result.manifest_digest != str(manifest_digest or ""):
                reasons.append("manifest_digest_mismatch")
            if grammar.arena_id != arena_id:
                reasons.append("manifest_arena_mismatch")
            if grammar.grammar_version != grammar_version:
                reasons.append("manifest_grammar_version_mismatch")
    return {
        "passed": not reasons,
        "repository_root": str(root),
        "manifest_path": raw,
        "resolved_path": str(resolved),
        "declared_digest": str(manifest_digest or ""),
        "compiled_digest": str(getattr(compile_result, "manifest_digest", "") or ""),
        "reasons": reasons,
        "repository_relative": not any(reason in reasons for reason in (
            "manifest_path_not_repository_relative", "manifest_path_escapes_repository",
        )),
        "canonical_compiler_digest": True,
    }


def validate_crucible_candidate(candidate: CrucibleCandidate,
                                experiences: Iterable[dict[str, Any]], *,
                                repo_root: str | Path = ".",
                                policy: CruciblePolicy | None = None) -> dict[str, Any]:
    """Structurally validate a candidate and assess proposal-only thresholds."""

    policy = policy or CruciblePolicy()
    by_id = {str(row.get("experience_id") or ""): dict(row) for row in experiences if str(row.get("experience_id") or "")}
    train_ids = set(candidate.train_experience_ids)
    validation_ids = set(candidate.validation_experience_ids)
    shadow_ids = set(candidate.shadow_experience_ids)
    leakage = sorted((train_ids & validation_ids) | (train_ids & shadow_ids) | (validation_ids & shadow_ids))
    train = [by_id[item] for item in candidate.train_experience_ids if item in by_id]
    validation = [by_id[item] for item in candidate.validation_experience_ids if item in by_id]
    shadow_rows = [by_id[item] for item in candidate.shadow_experience_ids if item in by_id]

    manifest_pin = validate_manifest_pin(
        repo_root=repo_root, manifest_path=candidate.manifest_path,
        manifest_digest=candidate.manifest_digest, arena_id=candidate.arena_id,
        grammar_version=candidate.grammar_version,
    )
    validation_summary = summarize_outcome_vectors(validation)
    shadow = historical_shadow_replay(candidate, shadow_rows)
    source_matches = all(_record_matches_candidate(row, candidate) for row in (*train, *validation, *shadow_rows))
    observations_complete = all(_complete_observation(row) for row in shadow_rows)
    dataset_digests = {
        "train": canonical_digest(tuple(candidate.train_experience_ids)),
        "validation": canonical_digest(tuple(candidate.validation_experience_ids)),
        "shadow": canonical_digest(tuple(candidate.shadow_experience_ids)),
    }

    structural_checks = {
        "three_way_dataset_separation": not leakage,
        "all_train_records_present": len(train) == len(candidate.train_experience_ids),
        "all_validation_records_present": len(validation) == len(candidate.validation_experience_ids),
        "all_shadow_records_present": len(shadow_rows) == len(candidate.shadow_experience_ids),
        "dataset_digests_match": (
            dataset_digests["train"] == candidate.train_experience_digest
            and dataset_digests["validation"] == candidate.validation_experience_digest
            and dataset_digests["shadow"] == candidate.shadow_experience_digest
        ),
        "source_records_match_manifest_and_transition": source_matches,
        "shadow_observations_preserve_all_alternatives_and_predictions": observations_complete,
        "allowed_change_path": candidate.change_path == "soft_weight_profile.empirical_uncertainty",
        "manifest_pinned": bool(manifest_pin["passed"]),
    }
    proposal_threshold_checks = {
        "train_record_count": len(train) >= policy.proposal_min_train_records,
        "validation_record_count": len(validation) >= policy.proposal_min_validation_records,
        "shadow_record_count": len(shadow_rows) >= policy.proposal_min_shadow_records,
        "distinct_objectives": candidate.distinct_objectives >= policy.proposal_min_distinct_objectives,
        "train_outcome_coverage": float(candidate.train_outcome_summary.get("coverage_mean") or 0.0) >= policy.proposal_min_outcome_coverage,
        "train_outcome_score": float(candidate.train_outcome_summary.get("score_mean") or 0.0) >= policy.proposal_min_train_score,
        "validation_outcome_coverage": float(validation_summary.get("coverage_mean") or 0.0) >= policy.proposal_min_outcome_coverage,
        "validation_outcome_score": float(validation_summary.get("score_mean") or 0.0) >= policy.proposal_min_validation_score,
        "shadow_selection_change_rate": float(shadow.get("selection_change_rate") or 0.0) <= policy.proposal_max_shadow_selection_change_rate,
        "shadow_no_unsafe_changes": int(shadow.get("unsafe_selection_changes") or 0) == 0,
        "uncertainty_delta": abs(candidate.current_value - candidate.proposed_value) >= policy.proposal_min_uncertainty_delta,
    }
    passed = all(structural_checks.values())
    thresholds_met = all(proposal_threshold_checks.values())
    return {
        "ok": True,
        "version": CRUCIBLE_VALIDATION_VERSION,
        "passed": passed,
        "verifier_status": "STRUCTURALLY_VERIFIED" if passed else "FAILED",
        "proposal_recommendation": "READY_FOR_HUMAN_REVIEW" if passed and thresholds_met else "REVIEW_WITH_THRESHOLD_WARNINGS",
        "candidate_id": candidate.candidate_id,
        "structural_checks": structural_checks,
        "proposal_threshold_checks": proposal_threshold_checks,
        "all_proposal_thresholds_met": thresholds_met,
        "threshold_scope": "PROPOSAL_ONLY",
        "thresholds_have_runtime_authority": False,
        "leaked_experience_ids": leakage,
        "dataset_ids": {
            "train": list(candidate.train_experience_ids),
            "validation": list(candidate.validation_experience_ids),
            "shadow": list(candidate.shadow_experience_ids),
        },
        "dataset_digests": dataset_digests,
        "train_outcome_summary": candidate.train_outcome_summary,
        "validation_outcome_summary": validation_summary,
        "manifest_pin": manifest_pin,
        "shadow": shadow,
        "binary_outcome_used": False,
        "active_grammar_mutated": False,
        "learned_weight_patch_authority": False,
        "crystallization_patch_authority": False,
        "automatic_grammar_promotion": False,
    }


def historical_shadow_replay(candidate: CrucibleCandidate,
                             shadow_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Replay only the independent shadow dataset with all alternatives retained."""

    replay_records: list[dict[str, Any]] = []
    selection_changes = unsafe_changes = incomplete_records = 0
    for experience in shadow_rows:
        alternatives = [dict(item) for item in experience.get("admissible_alternatives", []) if isinstance(item, dict)]
        predictions = [dict(item) for item in experience.get("predictions", []) if isinstance(item, dict)]
        ranked: list[tuple[tuple[Any, ...], str, dict[str, Any]]] = []
        for row in alternatives:
            transition_id = str(row.get("transition_id") or "")
            rank = dict(row.get("rank") or {}) if isinstance(row.get("rank"), dict) else {}
            key = _rank_key(rank)
            if transition_id and key is not None:
                ranked.append((key, transition_id, rank))
        if not ranked or not predictions:
            incomplete_records += 1
            continue
        ranked.sort(key=lambda item: item[0])
        baseline_order = [transition_id for _, transition_id, _ in ranked]
        predicted_selected = next((str(item.get("transition_id") or "") for item in predictions if item.get("predicted_selected")), "")
        baseline_selected = predicted_selected or str(experience.get("selected_transition") or baseline_order[0])
        modified: list[tuple[tuple[Any, ...], str, dict[str, Any]]] = []
        for _, transition_id, rank in ranked:
            next_rank = dict(rank)
            if transition_id == candidate.transition_id:
                next_rank["empirical_uncertainty"] = candidate.proposed_value
            key = _rank_key(next_rank)
            if key is not None:
                modified.append((key, transition_id, next_rank))
        modified.sort(key=lambda item: item[0])
        proposed_order = [transition_id for _, transition_id, _ in modified]
        proposed_selected = proposed_order[0]
        changed = proposed_selected != baseline_selected
        unsafe = False
        if changed:
            selection_changes += 1
            old_rank = next((rank for _, transition_id, rank in ranked if transition_id == baseline_selected), {})
            new_rank = next((rank for _, transition_id, rank in modified if transition_id == proposed_selected), {})
            unsafe = (
                float(new_rank.get("unresolved_risk", 999.0)) > float(old_rank.get("unresolved_risk", 999.0))
                or float(new_rank.get("declared_evidence_gap", 999.0)) > float(old_rank.get("declared_evidence_gap", 999.0))
            )
            if unsafe:
                unsafe_changes += 1
        replay_records.append({
            "experience_id": str(experience.get("experience_id") or ""),
            "baseline_selected": baseline_selected,
            "proposed_selected": proposed_selected,
            "selection_changed": changed,
            "unsafe_change": unsafe,
            "baseline_order": baseline_order,
            "proposed_order": proposed_order,
            "admissible_alternatives": alternatives,
            "recorded_predictions": predictions,
            "grammar_manifest_digest": str(experience.get("grammar_manifest_digest") or ""),
            "outcome_vector": dict(experience.get("outcome_vector") or {}),
        })
    replayed = len(replay_records)
    return {
        "dataset": "SHADOW",
        "replay_record_count": replayed,
        "incomplete_record_count": incomplete_records,
        "selection_changes": selection_changes,
        "selection_change_rate": round(selection_changes / replayed, 6) if replayed else 0.0,
        "unsafe_selection_changes": unsafe_changes,
        "replay_records": replay_records,
        "all_admissible_alternatives_preserved": incomplete_records == 0,
        "all_predictions_preserved": incomplete_records == 0,
        "hard_guards_replayed": False,
        "admitted_transitions_only": True,
        "binary_outcome_used": False,
    }


def _record_matches_candidate(row: dict[str, Any], candidate: CrucibleCandidate) -> bool:
    return (
        str(row.get("arena_id") or "") == candidate.arena_id
        and str(row.get("grammar_version") or "") == candidate.grammar_version
        and str(row.get("grammar_manifest_digest") or "") == candidate.manifest_digest
        and str(row.get("state_before") or "") == candidate.state_before
        and str(row.get("selected_transition") or "") == candidate.transition_id
        and isinstance(row.get("outcome_vector"), dict)
    )


def _complete_observation(row: dict[str, Any]) -> bool:
    alternatives = [item for item in row.get("admissible_alternatives", []) if isinstance(item, dict)]
    predictions = [item for item in row.get("predictions", []) if isinstance(item, dict)]
    return bool(alternatives and predictions and
                [str(item.get("transition_id") or "") for item in alternatives] ==
                [str(item.get("transition_id") or "") for item in predictions])


def _rank_key(rank: dict[str, Any]) -> tuple[Any, ...] | None:
    values: list[Any] = []
    for field in _RANK_FIELDS:
        value = rank.get(field)
        if field == "stable_transition_id":
            values.append(str(value or ""))
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return None
    return tuple(values)
