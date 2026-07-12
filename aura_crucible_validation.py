"""Holdout and historical shadow validation for Aura Crucible candidates."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from aura_crucible_miner import wilson_lower_bound
from aura_crucible_types import CrucibleCandidate, CruciblePolicy

CRUCIBLE_VALIDATION_VERSION = "AURA_CRUCIBLE_VALIDATION_V1"
_SUCCESS_OUTCOMES = frozenset({"ALLOWED", "COMPLETED", "PASS", "PASSED", "SUCCEEDED", "SUCCESS", "VERIFIED", "META_COMPLETED"})
_RANK_FIELDS = (
    "unresolved_risk",
    "declared_evidence_gap",
    "empirical_uncertainty",
    "semantic_ambiguity",
    "context_switch_cost",
    "latency_cost",
    "token_cost",
    "thermal_cost",
    "negative_semantic_fit",
    "negative_user_fit",
    "stable_transition_id",
)


def _validate_manifest_pin(manifest_path: str, manifest_digest: str) -> bool:
    """Validate that manifest path is repository-local and digest matches file contents.

    Returns True only if:
    1. Both path and digest are non-empty
    2. Path is relative (not absolute) and contains no path traversal
    3. The file exists and its BLAKE2b digest matches the declared digest
    """
    if not manifest_path or not manifest_digest:
        return False

    # Reject absolute paths
    if Path(manifest_path).is_absolute():
        return False

    # Reject path traversal attempts
    normalized = Path(manifest_path).as_posix()
    if ".." in normalized.split("/") or normalized.startswith("/"):
        return False

    # Verify digest matches file contents
    try:
        path = Path(manifest_path)
        if not path.exists() or not path.is_file():
            return False

        content = path.read_bytes()
        computed_digest = hashlib.blake2b(content, digest_size=20).hexdigest()
        return computed_digest == manifest_digest
    except (OSError, ValueError):
        return False


def validate_crucible_candidate(
    candidate: CrucibleCandidate,
    experiences: Iterable[dict[str, Any]],
    *,
    policy: CruciblePolicy | None = None,
) -> dict[str, Any]:
    """Validate one candidate without executing or mutating an active grammar."""

    policy = policy or CruciblePolicy()
    by_id = {str(row.get("experience_id") or ""): dict(row) for row in experiences if str(row.get("experience_id") or "")}
    train_ids = set(candidate.train_experience_ids)
    holdout_ids = set(candidate.holdout_experience_ids)
    leakage = sorted(train_ids & holdout_ids)
    holdout = [by_id[item] for item in candidate.holdout_experience_ids if item in by_id]
    successes = sum(str(row.get("final_outcome") or "").upper() in _SUCCESS_OUTCOMES for row in holdout)
    holdout_rate = successes / len(holdout) if holdout else 0.0
    holdout_lower = wilson_lower_bound(successes, len(holdout))
    shadow = historical_shadow_replay(candidate, holdout)

    checks = {
        "no_train_holdout_leakage": not leakage,
        "holdout_record_count": len(holdout) >= policy.min_holdout_records,
        "holdout_success_rate": holdout_rate >= policy.min_holdout_success_rate,
        "holdout_wilson_lower": holdout_lower >= policy.min_holdout_wilson_lower,
        "shadow_record_count": int(shadow["replay_record_count"]) >= policy.min_shadow_records,
        "shadow_no_unsafe_changes": int(shadow["unsafe_selection_changes"]) == 0,
        "shadow_change_rate": float(shadow["selection_change_rate"]) <= policy.max_shadow_selection_change_rate,
        "allowed_change_path": candidate.change_path == "soft_weight_profile.empirical_uncertainty",
        "manifest_pinned": _validate_manifest_pin(candidate.manifest_path, candidate.manifest_digest),
    }
    passed = all(checks.values())
    return {
        "ok": True,
        "version": CRUCIBLE_VALIDATION_VERSION,
        "passed": passed,
        "verifier_status": "PASSED" if passed else "FAILED",
        "candidate_id": candidate.candidate_id,
        "checks": checks,
        "leaked_experience_ids": leakage,
        "holdout_record_count": len(holdout),
        "holdout_success_count": successes,
        "holdout_success_rate": round(holdout_rate, 6),
        "holdout_wilson_lower": round(holdout_lower, 6),
        "shadow": shadow,
        "active_grammar_mutated": False,
        "learned_weight_patch_authority": False,
        "crystallization_patch_authority": False,
        "automatic_grammar_promotion": False,
    }


def historical_shadow_replay(candidate: CrucibleCandidate, holdout: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Replay recorded allowed-rank projections with the candidate value substituted.

    Only already-admitted transitions are replayed. Hard guards are neither bypassed
    nor reinterpreted. Records whose stored rank projection is incomplete are skipped.
    """

    replayed = 0
    selection_changes = 0
    unsafe_changes = 0
    baseline_mismatches = 0
    target_selected_before = 0
    target_selected_after = 0

    for experience in holdout:
        route = _route_packet(experience)
        rows = list(route.get("available") or []) if isinstance(route, dict) else []
        recorded_selected = str((route.get("selected") or {}).get("transition_id") or "") if isinstance(route, dict) else ""
        ranked: list[tuple[tuple[Any, ...], str, dict[str, Any]]] = []
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("rank"), dict):
                continue
            key = _rank_key(row["rank"])
            transition_id = str(row.get("transition_id") or "")
            if key is not None and transition_id:
                ranked.append((key, transition_id, row["rank"]))
        if not ranked:
            continue
        ranked.sort(key=lambda item: item[0])
        baseline = ranked[0][1]
        if recorded_selected and baseline != recorded_selected:
            baseline_mismatches += 1
            continue

        replayed += 1
        if baseline == candidate.transition_id:
            target_selected_before += 1
        modified: list[tuple[tuple[Any, ...], str, dict[str, Any]]] = []
        for _, transition_id, rank in ranked:
            next_rank = dict(rank)
            if transition_id == candidate.transition_id:
                next_rank["empirical_uncertainty"] = candidate.proposed_value
            key = _rank_key(next_rank)
            if key is not None:
                modified.append((key, transition_id, next_rank))
        modified.sort(key=lambda item: item[0])
        after = modified[0][1]
        if after == candidate.transition_id:
            target_selected_after += 1
        if after != baseline:
            selection_changes += 1
            old_rank = next(rank for _, transition_id, rank in ranked if transition_id == baseline)
            new_rank = next(rank for _, transition_id, rank in modified if transition_id == after)
            if (
                float(new_rank.get("unresolved_risk", 999)) > float(old_rank.get("unresolved_risk", 999))
                or float(new_rank.get("declared_evidence_gap", 999)) > float(old_rank.get("declared_evidence_gap", 999))
            ):
                unsafe_changes += 1

    return {
        "replay_record_count": replayed,
        "selection_changes": selection_changes,
        "selection_change_rate": round(selection_changes / replayed, 6) if replayed else 1.0,
        "unsafe_selection_changes": unsafe_changes,
        "baseline_projection_mismatches": baseline_mismatches,
        "target_selected_before": target_selected_before,
        "target_selected_after": target_selected_after,
        "hard_guards_replayed": False,
        "admitted_transitions_only": True,
    }


def _route_packet(experience: dict[str, Any]) -> dict[str, Any]:
    payload = experience.get("payload") or {}
    if not isinstance(payload, dict):
        return {}
    for key in ("route", "route_decision"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    action_result = payload.get("action_result")
    if isinstance(action_result, dict):
        for key in ("route", "route_decision"):
            value = action_result.get(key)
            if isinstance(value, dict):
                return value
    return {}


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
