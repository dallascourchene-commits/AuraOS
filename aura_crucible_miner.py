"""Deterministic experience mining for Aura's proposal-only Arena Crucible."""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any, Iterable

from aura_crucible_types import CrucibleCandidate, CruciblePolicy, bounded_probability, canonical_digest

CRUCIBLE_MINER_VERSION = "AURA_CRUCIBLE_MINER_V1"
_SUCCESS_OUTCOMES = frozenset({"ALLOWED", "COMPLETED", "PASS", "PASSED", "SUCCEEDED", "SUCCESS", "VERIFIED", "META_COMPLETED"})
_FAILURE_OUTCOMES = frozenset({"BLOCKED", "DENIED", "FAILED", "FAIL", "ERROR", "ABSTAINED", "INVALIDATED"})


def mine_crucible_candidates(
    experiences: Iterable[dict[str, Any]],
    grammar_index: dict[tuple[str, str], Any],
    *,
    policy: CruciblePolicy | None = None,
    arena_id: str = "",
) -> list[CrucibleCandidate]:
    """Mine supported transition-weight candidates using temporal train/holdout splits.

    ``grammar_index`` maps ``(arena_id, grammar_version)`` to a compiled grammar. A
    record targeting a missing or stale transition is ignored rather than guessed.
    """

    policy = policy or CruciblePolicy()
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for raw in experiences:
        row = dict(raw or {})
        if not _eligible(row, arena_id=arena_id):
            continue
        key = (
            str(row.get("arena_id") or ""),
            str(row.get("grammar_version") or ""),
            str(row.get("state_before") or ""),
            str(row.get("selected_transition") or ""),
        )
        grammar = grammar_index.get((key[0], key[1]))
        transition = grammar.transition_by_id(key[3]) if grammar is not None else None
        if transition is None or str(getattr(transition, "from_state", "")) not in {key[2], "*"}:
            continue
        groups[key].append(row)

    candidates: list[CrucibleCandidate] = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda item: (float(item.get("completed_at") or 0.0), str(item.get("experience_id") or "")))
        split = _temporal_split(rows, policy)
        if split is None:
            continue
        train, holdout = split
        train_successes = sum(_is_success(row) for row in train)
        train_rate = train_successes / len(train)
        if train_rate < policy.min_train_success_rate:
            continue
        objective_count = len({str(row.get("objective_hash") or "") for row in train if str(row.get("objective_hash") or "")})
        if objective_count < policy.min_distinct_objectives:
            continue

        grammar = grammar_index[(key[0], key[1])]
        transition = grammar.transition_by_id(key[3])
        profile = getattr(transition, "soft_weight_profile", None)
        current = bounded_probability(getattr(profile, "empirical_uncertainty", 1.0))
        lower = wilson_lower_bound(train_successes, len(train))
        proposed = round(max(0.05, min(1.0, 1.0 - lower)), 6)
        if abs(current - proposed) < policy.minimum_uncertainty_delta:
            continue

        train_ids = tuple(str(row["experience_id"]) for row in train[: policy.max_source_ids])
        holdout_ids = tuple(str(row["experience_id"]) for row in holdout[: policy.max_source_ids])
        source_digest = canonical_digest(sorted((*train_ids, *holdout_ids)))
        identity = {
            "arena_id": key[0],
            "grammar_version": key[1],
            "manifest_digest": str(getattr(grammar, "manifest_digest", "")),
            "state_before": key[2],
            "transition_id": key[3],
            "change_path": "soft_weight_profile.empirical_uncertainty",
            "current": current,
            "proposed": proposed,
            "source_digest": source_digest,
        }
        candidate_id = f"CAND-{canonical_digest(identity)[:24]}"
        candidates.append(CrucibleCandidate(
            candidate_id=candidate_id,
            arena_id=key[0],
            grammar_version=key[1],
            manifest_path=str(getattr(grammar, "source_path", "")),
            manifest_digest=str(getattr(grammar, "manifest_digest", "")),
            state_before=key[2],
            transition_id=key[3],
            change_path="soft_weight_profile.empirical_uncertainty",
            current_value=current,
            proposed_value=proposed,
            train_record_count=len(train),
            holdout_record_count=len(holdout),
            train_success_count=train_successes,
            train_success_rate=round(train_rate, 6),
            train_wilson_lower=round(lower, 6),
            distinct_objectives=objective_count,
            train_experience_ids=train_ids,
            holdout_experience_ids=holdout_ids,
            source_experience_digest=source_digest,
        ))
    candidates.sort(key=lambda item: (-item.train_wilson_lower, -item.train_record_count, item.candidate_id))
    return candidates[: policy.max_proposals_per_run]


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    """Return the lower Wilson confidence bound for a binomial success rate."""

    if total <= 0:
        return 0.0
    successes = max(0, min(int(successes), int(total)))
    n = float(total)
    p = successes / n
    denominator = 1.0 + (z * z / n)
    centre = p + (z * z / (2.0 * n))
    margin = z * math.sqrt((p * (1.0 - p) / n) + (z * z / (4.0 * n * n)))
    return max(0.0, min(1.0, (centre - margin) / denominator))


def _eligible(row: dict[str, Any], *, arena_id: str) -> bool:
    required = ("experience_id", "arena_id", "grammar_version", "state_before", "selected_transition", "final_outcome")
    if any(not str(row.get(key) or "").strip() for key in required):
        return False
    if arena_id and str(row.get("arena_id")) != arena_id:
        return False
    transition_id = str(row.get("selected_transition") or "")
    if transition_id.startswith("META."):
        return False
    return str(row.get("final_outcome") or "").upper() in (_SUCCESS_OUTCOMES | _FAILURE_OUTCOMES)


def _is_success(row: dict[str, Any]) -> int:
    return int(str(row.get("final_outcome") or "").upper() in _SUCCESS_OUTCOMES)


def _temporal_split(rows: list[dict[str, Any]], policy: CruciblePolicy) -> tuple[list[dict[str, Any]], list[dict[str, Any]]] | None:
    total = len(rows)
    minimum = policy.min_train_records + policy.min_holdout_records
    if total < minimum:
        return None
    holdout_count = max(policy.min_holdout_records, int(math.ceil(total * policy.holdout_fraction)))
    holdout_count = min(holdout_count, total - policy.min_train_records)
    train = rows[: total - holdout_count]
    holdout = rows[total - holdout_count :]
    if len(train) < policy.min_train_records or len(holdout) < policy.min_holdout_records:
        return None
    return train, holdout
