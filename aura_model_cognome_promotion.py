"""Proposal-only promotion gate for Model Cognome route policies.

Promotion evidence must include independent REPLAY and SHADOW measurements.
Outputs require verifier and human review and cannot mutate active routing.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import time
from typing import Any, Mapping

from aura_model_cognome import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id

PROMOTION_VERSION = "AURA_MODEL_COGNOME_PROMOTION_V1"
PROMOTION_PROPOSED = "PROMOTION_PROPOSED"
PROMOTION_REJECTED = "PROMOTION_REJECTED"
_ALLOWED_MODES = frozenset({"ZERO_MODEL", "DIRECT", "CASCADE", "PANEL"})


def _probability(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{name} must be finite and between zero and one")
    return number


def _finite(value: Any, name: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class RoutePromotionPolicy:
    minimum_replay_cases: int = 20
    minimum_shadow_cases: int = 10
    minimum_replay_coverage: float = 0.80
    minimum_shadow_coverage: float = 0.80
    minimum_success_rate_delta: float = 0.02
    maximum_success_regression: float = 0.0
    maximum_cost_increase_usd: float = 0.0
    maximum_time_increase_ms: float = 0.0
    maximum_scope_violation_delta: float = 0.0
    maximum_drift_score: float = 0.20
    maximum_uncertainty: float = 0.20
    policy_version: str = PROMOTION_VERSION

    def __post_init__(self) -> None:
        for name in ("minimum_replay_cases", "minimum_shadow_cases"):
            if int(getattr(self, name)) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in (
            "minimum_replay_coverage",
            "minimum_shadow_coverage",
            "maximum_drift_score",
            "maximum_uncertainty",
        ):
            _probability(getattr(self, name), name)
        for name in (
            "minimum_success_rate_delta",
            "maximum_success_regression",
            "maximum_cost_increase_usd",
            "maximum_time_increase_ms",
            "maximum_scope_violation_delta",
        ):
            if _finite(getattr(self, name), name) < 0:
                raise ValueError(f"{name} must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "threshold_scope": "PROPOSAL_ONLY",
            "runtime_authority": False,
            "automatic_policy_promotion": False,
        }


@dataclass(frozen=True)
class PromotionEvidence:
    measurement_mode: str
    evaluated_count: int
    coverage: float
    success_rate_delta: float | None
    mean_cost_delta_usd: float | None
    mean_time_delta_ms: float | None
    mean_scope_violation_delta: float | None
    drift_score: float | None
    uncertainty: float | None
    evidence_digest: str
    comparison_id: str = ""

    def __post_init__(self) -> None:
        if self.measurement_mode not in {"REPLAY", "SHADOW"}:
            raise ValueError("promotion evidence must be REPLAY or SHADOW")
        if self.evaluated_count < 0:
            raise ValueError("evaluated_count must be non-negative")
        _probability(self.coverage, "coverage")
        for name in (
            "success_rate_delta",
            "mean_cost_delta_usd",
            "mean_time_delta_ms",
            "mean_scope_violation_delta",
        ):
            value = getattr(self, name)
            if value is not None:
                _finite(value, name)
        for name in ("drift_score", "uncertainty"):
            value = getattr(self, name)
            if value is not None:
                _probability(value, name)
        if not self.evidence_digest:
            raise ValueError("evidence_digest must not be empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, measurement_mode: str | None = None) -> "PromotionEvidence":
        mode = str(measurement_mode or value.get("measurement_mode") or "")
        return cls(
            measurement_mode=mode,
            evaluated_count=int(value.get("evaluated_count") or value.get("common_case_count") or value.get("case_count") or 0),
            coverage=float(value.get("coverage") if value.get("coverage") is not None else 0.0),
            success_rate_delta=value.get("success_rate_delta"),
            mean_cost_delta_usd=value.get("mean_cost_delta_usd"),
            mean_time_delta_ms=value.get("mean_time_delta_ms"),
            mean_scope_violation_delta=value.get("mean_scope_violation_delta"),
            drift_score=value.get("drift_score"),
            uncertainty=value.get("uncertainty"),
            evidence_digest=str(
                value.get("evidence_digest")
                or value.get("comparison_digest")
                or stable_digest(dict(value))
            ),
            comparison_id=str(value.get("comparison_id") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutePolicyProposal:
    proposal_id: str
    candidate_policy_id: str
    candidate_policy_mode: str
    baseline_policy_id: str
    replay_evidence: PromotionEvidence
    shadow_evidence: PromotionEvidence
    threshold_assessment: dict[str, Any]
    proposal_thresholds: dict[str, Any]
    source_evidence_digest: str
    created_at: float
    status: str = PROMOTION_PROPOSED
    required_next_gate: str = "VERIFIER_AND_HUMAN_REVIEW"
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    automatic_policy_promotion: bool = False
    automatic_commit: bool = False
    automatic_push: bool = False
    automatic_merge: bool = False
    version: str = PROMOTION_VERSION

    def __post_init__(self) -> None:
        if self.status != PROMOTION_PROPOSED:
            raise ValueError("route policy proposals must terminate at PROMOTION_PROPOSED")
        if not math.isfinite(float(self.created_at)) or self.created_at < 0:
            raise ValueError("created_at must be finite and non-negative")
        if self.candidate_policy_mode not in _ALLOWED_MODES:
            raise ValueError(f"unknown candidate policy mode: {self.candidate_policy_mode}")
        if self.replay_evidence.measurement_mode != "REPLAY":
            raise ValueError("replay_evidence must be REPLAY")
        if self.shadow_evidence.measurement_mode != "SHADOW":
            raise ValueError("shadow_evidence must be SHADOW")
        if self.replay_evidence.evidence_digest == self.shadow_evidence.evidence_digest:
            raise ValueError("REPLAY and SHADOW evidence must be independently digested")
        if self.threshold_assessment.get("passed") is not True:
            raise ValueError("route policy proposal requires passing thresholds")
        if self.required_next_gate != "VERIFIER_AND_HUMAN_REVIEW":
            raise ValueError("route policy proposals require verifier and human review")
        if (
            not self.proposal_only
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority
            or self.automatic_policy_promotion
            or self.automatic_commit
            or self.automatic_push
            or self.automatic_merge
        ):
            raise ValueError("route policy proposals cannot carry runtime or repository mutation authority")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["replay_evidence"] = self.replay_evidence.to_dict()
        data["shadow_evidence"] = self.shadow_evidence.to_dict()
        data["proposal_digest"] = stable_digest(data)
        return data


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    proposal: RoutePolicyProposal | None
    threshold_assessment: dict[str, Any]
    denial_reasons: tuple[str, ...]
    evidence_digest: str
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "proposal": self.proposal.to_dict() if self.proposal else None,
            "denial_reasons": list(self.denial_reasons),
        }


def _assess_one(evidence: PromotionEvidence, policy: RoutePromotionPolicy) -> dict[str, Any]:
    minimum_cases = policy.minimum_replay_cases if evidence.measurement_mode == "REPLAY" else policy.minimum_shadow_cases
    minimum_coverage = (
        policy.minimum_replay_coverage if evidence.measurement_mode == "REPLAY" else policy.minimum_shadow_coverage
    )
    checks = {
        "minimum_cases": evidence.evaluated_count >= minimum_cases,
        "minimum_coverage": evidence.coverage >= minimum_coverage,
        "known_success_delta": evidence.success_rate_delta is not None,
        "success_not_regressed": (
            evidence.success_rate_delta is not None
            and evidence.success_rate_delta >= -policy.maximum_success_regression
        ),
        "minimum_success_gain": (
            evidence.success_rate_delta is not None
            and evidence.success_rate_delta >= policy.minimum_success_rate_delta
        ),
        "cost_bound": (
            evidence.mean_cost_delta_usd is not None
            and evidence.mean_cost_delta_usd <= policy.maximum_cost_increase_usd
        ),
        "time_bound": (
            evidence.mean_time_delta_ms is not None
            and evidence.mean_time_delta_ms <= policy.maximum_time_increase_ms
        ),
        "scope_bound": (
            evidence.mean_scope_violation_delta is not None
            and evidence.mean_scope_violation_delta <= policy.maximum_scope_violation_delta
        ),
        "drift_known_and_bounded": (
            evidence.drift_score is not None and evidence.drift_score <= policy.maximum_drift_score
        ),
        "uncertainty_known_and_bounded": (
            evidence.uncertainty is not None and evidence.uncertainty <= policy.maximum_uncertainty
        ),
    }
    return {
        "measurement_mode": evidence.measurement_mode,
        "passed": all(checks.values()),
        "checks": checks,
        "evaluated_count": evidence.evaluated_count,
        "coverage": evidence.coverage,
        "evidence_digest": evidence.evidence_digest,
    }


def evaluate_route_policy_promotion(
    *,
    candidate_policy_id: str,
    candidate_policy_mode: str,
    baseline_policy_id: str,
    replay_evidence: PromotionEvidence | Mapping[str, Any],
    shadow_evidence: PromotionEvidence | Mapping[str, Any],
    policy: RoutePromotionPolicy | None = None,
    created_at: float | None = None,
) -> PromotionDecision:
    if not candidate_policy_id or not baseline_policy_id:
        raise ValueError("candidate and baseline policy IDs must not be empty")
    if candidate_policy_id == baseline_policy_id:
        raise ValueError("candidate and baseline policy IDs must differ")
    if candidate_policy_mode not in _ALLOWED_MODES:
        raise ValueError(f"unknown candidate policy mode: {candidate_policy_mode}")
    thresholds = policy or RoutePromotionPolicy()
    replay = (
        replay_evidence
        if isinstance(replay_evidence, PromotionEvidence)
        else PromotionEvidence.from_mapping(replay_evidence, measurement_mode="REPLAY")
    )
    shadow = (
        shadow_evidence
        if isinstance(shadow_evidence, PromotionEvidence)
        else PromotionEvidence.from_mapping(shadow_evidence, measurement_mode="SHADOW")
    )
    if replay.measurement_mode != "REPLAY" or shadow.measurement_mode != "SHADOW":
        raise ValueError("promotion requires one REPLAY and one SHADOW evidence set")
    if replay.evidence_digest == shadow.evidence_digest:
        raise ValueError("REPLAY and SHADOW evidence must be independent")
    replay_assessment = _assess_one(replay, thresholds)
    shadow_assessment = _assess_one(shadow, thresholds)
    assessment = {
        "passed": replay_assessment["passed"] and shadow_assessment["passed"],
        "replay": replay_assessment,
        "shadow": shadow_assessment,
        "policy_version": thresholds.policy_version,
    }
    source_digest = stable_digest(
        {
            "candidate_policy_id": candidate_policy_id,
            "candidate_policy_mode": candidate_policy_mode,
            "baseline_policy_id": baseline_policy_id,
            "replay_evidence_digest": replay.evidence_digest,
            "shadow_evidence_digest": shadow.evidence_digest,
            "thresholds": thresholds.to_dict(),
            "assessment": assessment,
        }
    )
    if not assessment["passed"]:
        failures = []
        for section in (replay_assessment, shadow_assessment):
            failures.extend(
                f"{section['measurement_mode']}:{name}"
                for name, passed in section["checks"].items()
                if not passed
            )
        return PromotionDecision(
            status=PROMOTION_REJECTED,
            proposal=None,
            threshold_assessment=assessment,
            denial_reasons=tuple(failures),
            evidence_digest=source_digest,
        )
    timestamp = time.time() if created_at is None else float(created_at)
    proposal_id = stable_id(
        "route-policy-proposal",
        {
            "candidate_policy_id": candidate_policy_id,
            "baseline_policy_id": baseline_policy_id,
            "source_evidence_digest": source_digest,
        },
    )
    proposal = RoutePolicyProposal(
        proposal_id=proposal_id,
        candidate_policy_id=candidate_policy_id,
        candidate_policy_mode=candidate_policy_mode,
        baseline_policy_id=baseline_policy_id,
        replay_evidence=replay,
        shadow_evidence=shadow,
        threshold_assessment=assessment,
        proposal_thresholds=thresholds.to_dict(),
        source_evidence_digest=source_digest,
        created_at=timestamp,
    )
    return PromotionDecision(
        status=PROMOTION_PROPOSED,
        proposal=proposal,
        threshold_assessment=assessment,
        denial_reasons=(),
        evidence_digest=source_digest,
    )


def crucible_route_policy_packet(decision: PromotionDecision) -> dict[str, Any]:
    """Return a generic Crucible-compatible packet without grammar mutation fields."""
    payload = decision.to_dict()
    return {
        "packet_type": "ROUTE_POLICY_PROMOTION_PROPOSAL",
        "version": PROMOTION_VERSION,
        "status": decision.status,
        "proposal": payload.get("proposal"),
        "threshold_assessment": decision.threshold_assessment,
        "source_evidence_digest": decision.evidence_digest,
        "required_next_gate": "VERIFIER_AND_HUMAN_REVIEW",
        "proposal_only": True,
        "runtime_authority": False,
        "automatic_policy_promotion": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "packet_digest": stable_digest(payload),
    }
