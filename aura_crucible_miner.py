"""Deterministic OutcomeVector mining for Aura's proposal-only Arena Crucible."""
from __future__ import annotations

from collections import defaultdict
import math
import statistics
from typing import Any, Iterable

from aura_arena_experience import OutcomeVector
from aura_crucible_types import CrucibleCandidate, CruciblePolicy, bounded_probability, canonical_digest

CRUCIBLE_MINER_VERSION = "AURA_CRUCIBLE_MINER_V2"


def mine_crucible_candidates(
    experiences: Iterable[dict[str, Any]],
    grammar_index: dict[tuple[str, str], Any],
    *,
    policy: CruciblePolicy | None = None,
    arena_id: str = "",
) -> list[CrucibleCandidate]:
    """Mine existing-transition proposals from complete V2 observations.

    Terminal strings remain audit labels only. Candidate values come from continuous
    OutcomeVector projections. Thresholds are attached to proposals and never become
    guards, runtime policy, or promotion authority.
    """

    policy = policy or CruciblePolicy()
    groups: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in experiences:
        row = dict(raw or {})
        if not _eligible(row, arena_id=arena_id):
            continue
        key = (
            str(row.get("arena_id") or ""),
            str(row.get("grammar_version") or ""),
            str(row.get("grammar_manifest_digest") or ""),
            str(row.get("state_before") or ""),
            str(row.get("selected_transition") or ""),
        )
        grammar = grammar_index.get((key[0], key[1]))
        transition = grammar.transition_by_id(key[4]) if grammar is not None else None
        if grammar is None or str(getattr(grammar, "manifest_digest", "")) != key[2]:
            continue
        if transition is None or str(getattr(transition, "from_state", "")) not in {key[3], "*"}:
            continue
        groups[key].append(row)

    candidates: list[CrucibleCandidate] = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda item: (float(item.get("completed_at") or 0.0), str(item.get("experience_id") or "")))
        split = three_way_temporal_split(rows, policy)
        if split is None:
            continue
        train, validation, shadow = split
        train_summary = summarize_outcome_vectors(train)
        floor = train_summary.get("conservative_floor")
        if train_summary.get("score_mean") is None or floor is None:
            continue

        grammar = grammar_index[(key[0], key[1])]
        transition = grammar.transition_by_id(key[4])
        current = bounded_probability(getattr(getattr(transition, "soft_weight_profile", None), "empirical_uncertainty", 1.0))
        proposed = round(max(0.0, min(1.0, 1.0 - float(floor))), 6)
        if proposed == current:
            continue

        objective_count = len({str(row.get("objective_hash") or "") for row in train if str(row.get("objective_hash") or "")})
        assessment = assess_proposal_thresholds(
            policy=policy,
            train_count=len(train),
            validation_count=len(validation),
            shadow_count=len(shadow),
            distinct_objectives=objective_count,
            train_summary=train_summary,
            current_value=current,
            proposed_value=proposed,
        )
        train_ids = tuple(str(row["experience_id"]) for row in train)
        validation_ids = tuple(str(row["experience_id"]) for row in validation)
        shadow_ids = tuple(str(row["experience_id"]) for row in shadow)
        train_digest = canonical_digest(train_ids)
        validation_digest = canonical_digest(validation_ids)
        shadow_digest = canonical_digest(shadow_ids)
        source_digest = canonical_digest({
            "train": train_digest,
            "validation": validation_digest,
            "shadow": shadow_digest,
            "manifest_digest": key[2],
        })
        identity = {
            "arena_id": key[0], "grammar_version": key[1], "manifest_digest": key[2],
            "state_before": key[3], "transition_id": key[4],
            "change_path": "soft_weight_profile.empirical_uncertainty",
            "current": current, "proposed": proposed, "source_digest": source_digest,
        }
        candidates.append(CrucibleCandidate(
            candidate_id=f"CAND-{canonical_digest(identity)[:24]}",
            arena_id=key[0], grammar_version=key[1],
            manifest_path=str(getattr(grammar, "source_path", "")),
            manifest_digest=key[2], state_before=key[3], transition_id=key[4],
            change_path="soft_weight_profile.empirical_uncertainty",
            current_value=current, proposed_value=proposed,
            train_record_count=len(train), validation_record_count=len(validation), shadow_record_count=len(shadow),
            train_outcome_summary=train_summary,
            proposal_thresholds=policy.proposal_thresholds(),
            threshold_assessment=assessment,
            distinct_objectives=objective_count,
            train_experience_ids=train_ids,
            validation_experience_ids=validation_ids,
            shadow_experience_ids=shadow_ids,
            train_experience_digest=train_digest,
            validation_experience_digest=validation_digest,
            shadow_experience_digest=shadow_digest,
            source_experience_digest=source_digest,
        ))
    candidates.sort(key=lambda item: (
        not bool(item.threshold_assessment.get("all_proposal_thresholds_met")),
        -float(item.train_outcome_summary.get("conservative_floor") or 0.0),
        -item.train_record_count,
        item.candidate_id,
    ))
    return candidates[: policy.operational_max_proposals_per_run]


def three_way_temporal_split(
    rows: list[dict[str, Any]], policy: CruciblePolicy
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]] | None:
    """Return disjoint oldest-train, middle-validation, newest-shadow data."""

    total = len(rows)
    if total < 3:
        return None
    validation_count = max(1, int(math.floor(total * policy.validation_fraction)))
    shadow_count = max(1, int(math.floor(total * policy.shadow_fraction)))
    while validation_count + shadow_count >= total:
        if validation_count >= shadow_count and validation_count > 1:
            validation_count -= 1
        elif shadow_count > 1:
            shadow_count -= 1
        else:
            return None
    train_end = total - validation_count - shadow_count
    validation_end = total - shadow_count
    train = rows[:train_end]
    validation = rows[train_end:validation_end]
    shadow = rows[validation_end:]
    return (train, validation, shadow) if train and validation and shadow else None


def summarize_outcome_vectors(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize continuous OutcomeVector projections without binary coercion."""

    scores: list[float] = []
    coverages: list[float] = []
    dimensions: dict[str, list[float]] = defaultdict(list)
    terminal_classes: dict[str, int] = defaultdict(int)
    for row in rows:
        try:
            vector = OutcomeVector.from_dict(dict(row.get("outcome_vector") or {}))
        except (TypeError, ValueError):
            continue
        projection = vector.proposal_projection()
        if projection.get("score") is not None:
            scores.append(float(projection["score"]))
            coverages.append(float(projection.get("coverage") or 0.0))
        for name, value in projection.get("observed_dimensions", {}).items():
            dimensions[str(name)].append(float(value))
        terminal_classes[vector.terminal_class] += 1
    if not scores:
        return {"record_count": 0, "score_mean": None, "conservative_floor": None,
                "coverage_mean": 0.0, "dimension_means": {},
                "terminal_classes": dict(terminal_classes), "binary_outcome_used": False,
                "proposal_only": True}
    mean = statistics.fmean(scores)
    std = statistics.stdev(scores) if len(scores) > 1 else 0.0
    margin = 1.96 * std / math.sqrt(len(scores)) if len(scores) > 1 else 0.0
    return {
        "record_count": len(scores),
        "score_mean": round(mean, 6),
        "score_stddev": round(std, 6),
        "conservative_floor": round(max(0.0, min(1.0, mean - margin)), 6),
        "coverage_mean": round(statistics.fmean(coverages), 6),
        "dimension_means": {name: round(statistics.fmean(values), 6) for name, values in sorted(dimensions.items()) if values},
        "dimension_observation_counts": {name: len(values) for name, values in sorted(dimensions.items())},
        "terminal_classes": dict(sorted(terminal_classes.items())),
        "binary_outcome_used": False,
        "proposal_only": True,
    }


def assess_proposal_thresholds(*, policy: CruciblePolicy, train_count: int,
                               validation_count: int, shadow_count: int,
                               distinct_objectives: int, train_summary: dict[str, Any],
                               current_value: float, proposed_value: float) -> dict[str, Any]:
    checks = {
        "train_record_count": train_count >= policy.proposal_min_train_records,
        "validation_record_count": validation_count >= policy.proposal_min_validation_records,
        "shadow_record_count": shadow_count >= policy.proposal_min_shadow_records,
        "distinct_objectives": distinct_objectives >= policy.proposal_min_distinct_objectives,
        "train_outcome_coverage": float(train_summary.get("coverage_mean") or 0.0) >= policy.proposal_min_outcome_coverage,
        "train_outcome_score": float(train_summary.get("score_mean") or 0.0) >= policy.proposal_min_train_score,
        "uncertainty_delta": abs(float(current_value) - float(proposed_value)) >= policy.proposal_min_uncertainty_delta,
    }
    return {"checks": checks, "all_proposal_thresholds_met": all(checks.values()),
            "threshold_scope": "PROPOSAL_ONLY", "runtime_authority": False,
            "candidate_generation_blocked": False}


def _eligible(row: dict[str, Any], *, arena_id: str) -> bool:
    required = ("experience_id", "arena_id", "grammar_version", "grammar_manifest_digest",
                "state_before", "selected_transition", "outcome_vector")
    if any(not row.get(key) for key in required) or row.get("legacy_record") is True:
        return False
    if arena_id and str(row.get("arena_id")) != arena_id:
        return False
    if str(row.get("selected_transition") or "").startswith("META."):
        return False
    try:
        OutcomeVector.from_dict(dict(row.get("outcome_vector") or {}))
    except (TypeError, ValueError):
        return False
    return True
