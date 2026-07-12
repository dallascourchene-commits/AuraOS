"""Typed proposal-only contracts for Aura's Arena Crucible.

The Crucible may summarize complete observable experience records and emit
reviewable proposals. It cannot mutate active grammars, grant capabilities,
or obtain patch authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

CRUCIBLE_TYPES_VERSION = "AURA_CRUCIBLE_TYPES_V2"
CRYSTALLIZATION_PROPOSED = "CRYSTALLIZATION_PROPOSED"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_ALLOWED_CHANGE_PATHS = frozenset({"soft_weight_profile.empirical_uncertainty"})


@dataclass(frozen=True)
class CruciblePolicy:
    """Proposal-only evidence thresholds and operational bounds."""

    validation_fraction: float = 0.20
    shadow_fraction: float = 0.20
    proposal_min_train_records: int = 8
    proposal_min_validation_records: int = 3
    proposal_min_shadow_records: int = 3
    proposal_min_distinct_objectives: int = 2
    proposal_min_outcome_coverage: float = 0.50
    proposal_min_train_score: float = 0.70
    proposal_min_validation_score: float = 0.67
    proposal_max_shadow_selection_change_rate: float = 0.35
    proposal_min_uncertainty_delta: float = 0.05
    operational_max_proposals_per_run: int = 8
    operational_max_source_ids: int = 500

    def __post_init__(self) -> None:
        for name in (
            "proposal_min_train_records", "proposal_min_validation_records",
            "proposal_min_shadow_records", "proposal_min_distinct_objectives",
            "operational_max_proposals_per_run", "operational_max_source_ids",
        ):
            if int(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be nonnegative")
        for name in (
            "validation_fraction", "shadow_fraction", "proposal_min_outcome_coverage",
            "proposal_min_train_score", "proposal_min_validation_score",
            "proposal_max_shadow_selection_change_rate", "proposal_min_uncertainty_delta",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.validation_fraction <= 0.0 or self.shadow_fraction <= 0.0:
            raise ValueError("validation_fraction and shadow_fraction must be positive")
        if self.validation_fraction + self.shadow_fraction >= 1.0:
            raise ValueError("validation_fraction + shadow_fraction must be less than 1")

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> "CruciblePolicy":
        data = dict(value or {})
        unknown = sorted(set(data) - set(cls.__dataclass_fields__))
        if unknown:
            raise ValueError(f"unknown Crucible policy fields: {', '.join(unknown)}")
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "threshold_scope": "PROPOSAL_ONLY",
            "runtime_authority": False,
            "automatic_grammar_promotion": False,
        }

    def proposal_thresholds(self) -> dict[str, Any]:
        return {key: value for key, value in self.to_dict().items() if key.startswith("proposal_")}


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
    validation_record_count: int
    shadow_record_count: int
    train_outcome_summary: dict[str, Any]
    proposal_thresholds: dict[str, Any]
    threshold_assessment: dict[str, Any]
    distinct_objectives: int
    train_experience_ids: tuple[str, ...] = ()
    validation_experience_ids: tuple[str, ...] = ()
    shadow_experience_ids: tuple[str, ...] = ()
    train_experience_digest: str = ""
    validation_experience_digest: str = ""
    shadow_experience_digest: str = ""
    source_experience_digest: str = ""
    version: str = CRUCIBLE_TYPES_VERSION
    threshold_scope: str = "PROPOSAL_ONLY"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    learned_weight_patch_authority: bool = False
    crystallization_patch_authority: bool = False
    automatic_grammar_promotion: bool = False

    def __post_init__(self) -> None:
        if self.change_path not in _ALLOWED_CHANGE_PATHS:
            raise ValueError(f"unsupported Crucible change path: {self.change_path}")
        sets = [set(self.train_experience_ids), set(self.validation_experience_ids), set(self.shadow_experience_ids)]
        if any(sets[i] & sets[j] for i in range(len(sets)) for j in range(i + 1, len(sets))):
            raise ValueError("train, validation, and shadow experience sets must be disjoint")
        for value in (self.current_value, self.proposed_value):
            if not 0.0 <= float(value) <= 1.0:
                raise ValueError("candidate weight values must be between 0 and 1")
        if self.threshold_scope != "PROPOSAL_ONLY":
            raise ValueError("Crucible thresholds must remain proposal-only")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority, self.learned_weight_patch_authority,
            self.crystallization_patch_authority, self.automatic_grammar_promotion,
        )):
            raise ValueError("Crucible candidates cannot carry mutation or promotion authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("train_experience_ids", "validation_experience_ids", "shadow_experience_ids"):
            data[key] = list(getattr(self, key))
        return data


@dataclass(frozen=True)
class CrystallizationProposal:
    """Structurally verified proposal that terminates before active mutation."""

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
    proposal_thresholds: dict[str, Any]
    threshold_assessment: dict[str, Any]
    train_experience_ids: tuple[str, ...]
    validation_experience_ids: tuple[str, ...]
    shadow_experience_ids: tuple[str, ...]
    source_experience_digest: str
    created_at: float
    status: str = CRYSTALLIZATION_PROPOSED
    required_next_gate: str = "VERIFIER_AND_HUMAN_REVIEW"
    version: str = CRUCIBLE_TYPES_VERSION
    threshold_scope: str = "PROPOSAL_ONLY"
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
            raise ValueError("a crystallization proposal requires structural validation")
        if self.required_next_gate != "VERIFIER_AND_HUMAN_REVIEW":
            raise ValueError("Crucible proposals must require verifier and human review")
        if self.threshold_scope != "PROPOSAL_ONLY":
            raise ValueError("proposal thresholds cannot become runtime authority")
        if self.patch_authority != PATCH_AUTHORITY or any((
            self.vsa_patch_authority, self.learned_weight_patch_authority,
            self.crystallization_patch_authority, self.automatic_grammar_promotion,
            self.automatic_commit, self.automatic_push, self.automatic_merge,
        )):
            raise ValueError("Crucible proposals cannot carry mutation or promotion authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        for key in ("train_experience_ids", "validation_experience_ids", "shadow_experience_ids"):
            data[key] = list(getattr(self, key))
        data["proposal_digest"] = canonical_digest(data)
        return data


def canonical_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


def bounded_probability(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(1.0, number))
