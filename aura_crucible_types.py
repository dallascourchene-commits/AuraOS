"""Typed proposal-only contracts for Aura's Arena Crucible.

The Crucible may summarize complete observable experience records and emit
reviewable proposals. It cannot mutate an active grammar, grant capabilities,
or obtain patch authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

CRUCIBLE_TYPES_VERSION = "AURA_CRUCIBLE_TYPES_V1"
CRYSTALLIZATION_PROPOSED = "CRYSTALLIZATION_PROPOSED"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_ALLOWED_CHANGE_PATHS = frozenset({"soft_weight_profile.empirical_uncertainty"})


@dataclass(frozen=True)
class CruciblePolicy:
    """Deterministic thresholds for mining and validating one Crucible run."""

    min_train_records: int = 8
    min_holdout_records: int = 3
    holdout_fraction: float = 0.25
    min_distinct_objectives: int = 2
    min_train_success_rate: float = 0.70
    min_holdout_success_rate: float = 0.67
    min_holdout_wilson_lower: float = 0.30
    min_shadow_records: int = 1
    max_shadow_selection_change_rate: float = 0.35
    minimum_uncertainty_delta: float = 0.05
    max_proposals_per_run: int = 8
    max_source_ids: int = 200

    def __post_init__(self) -> None:
        for name in ("min_train_records", "min_holdout_records", "min_distinct_objectives", "min_shadow_records", "max_proposals_per_run", "max_source_ids"):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be nonnegative")
        for name in ("holdout_fraction", "min_train_success_rate", "min_holdout_success_rate", "min_holdout_wilson_lower", "max_shadow_selection_change_rate", "minimum_uncertainty_delta"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.holdout_fraction <= 0.0 or self.holdout_fraction >= 1.0:
            raise ValueError("holdout_fraction must be greater than 0 and less than 1")

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CruciblePolicy":
        data = dict(value or {})
        allowed = {field_name for field_name in cls.__dataclass_fields__}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown Crucible policy fields: {', '.join(unknown)}")
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CrucibleCandidate:
    """A mined, unpromoted candidate targeting one existing transition."""

    candidate_id: str
    arena_id: str
    grammar_version: str
    manifest_path: str
    manifest_digest: str
    state_before: str
    transition_id: str
    change_path: str
    current_value: float
    proposed_value: float
    train_record_count: int
    holdout_record_count: int
    train_success_count: int
    train_success_rate: float
    train_wilson_lower: float
    distinct_objectives: int
    train_experience_ids: tuple[str, ...] = ()
    holdout_experience_ids: tuple[str, ...] = ()
    source_experience_digest: str = ""
    version: str = CRUCIBLE_TYPES_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    learned_weight_patch_authority: bool = False
    crystallization_patch_authority: bool = False
    automatic_grammar_promotion: bool = False

    def __post_init__(self) -> None:
        if self.change_path not in _ALLOWED_CHANGE_PATHS:
            raise ValueError(f"unsupported Crucible change path: {self.change_path}")
        if set(self.train_experience_ids) & set(self.holdout_experience_ids):
            raise ValueError("train and holdout experience sets must not overlap")
        for value in (self.current_value, self.proposed_value, self.train_success_rate, self.train_wilson_lower):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("candidate probability/weight values must be between 0 and 1")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority,
            self.learned_weight_patch_authority,
            self.crystallization_patch_authority,
            self.automatic_grammar_promotion,
        )):
            raise ValueError("Crucible candidates cannot carry mutation or promotion authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["train_experience_ids"] = list(self.train_experience_ids)
        data["holdout_experience_ids"] = list(self.holdout_experience_ids)
        return data


@dataclass(frozen=True)
class CrystallizationProposal:
    """Verifier-approved proposal that terminates before active-grammar mutation."""

    proposal_id: str
    run_id: str
    candidate_id: str
    arena_id: str
    grammar_version: str
    manifest_path: str
    manifest_digest: str
    state_before: str
    transition_id: str
    change_path: str
    current_value: float
    proposed_value: float
    validation: dict[str, Any]
    source_experience_ids: tuple[str, ...]
    source_experience_digest: str
    created_at: float
    status: str = CRYSTALLIZATION_PROPOSED
    required_next_gate: str = "VERIFIER_AND_HUMAN_REVIEW"
    version: str = CRUCIBLE_TYPES_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    learned_weight_patch_authority: bool = False
    crystallization_patch_authority: bool = False
    automatic_grammar_promotion: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_merge: bool = False

    def __post_init__(self) -> None:
        if self.status != CRYSTALLIZATION_PROPOSED:
            raise ValueError("Crucible output must terminate at CRYSTALLIZATION_PROPOSED")
        if self.change_path not in _ALLOWED_CHANGE_PATHS:
            raise ValueError(f"unsupported proposal change path: {self.change_path}")
        if self.validation.get("passed") is not True:
            raise ValueError("a crystallization proposal requires passing validation")
        if self.required_next_gate != "VERIFIER_AND_HUMAN_REVIEW":
            raise ValueError("Crucible proposals must require verifier and human review")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority,
            self.learned_weight_patch_authority,
            self.crystallization_patch_authority,
            self.automatic_grammar_promotion,
            self.automatic_commit,
            self.automatic_push,
            self.automatic_merge,
        )):
            raise ValueError("Crucible proposals cannot carry mutation or promotion authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["source_experience_ids"] = list(self.source_experience_ids)
        data["proposal_digest"] = canonical_digest({key: value for key, value in data.items() if key != "proposal_digest"})
        return data


def canonical_digest(value: Any) -> str:
    """Return a deterministic BLAKE2 digest for proposal and source packets."""

    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def bounded_probability(value: Any) -> float:
    """Convert an arbitrary numeric value to a stable probability in ``[0, 1]``."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(1.0, number))
