"""Deterministic offline replay evaluation for Model Cognome route policies.

Replay consumes already-recorded verifier outcomes. It never calls a provider,
executes a tool, mutates an active route policy, or fabricates PANEL outcomes from
independent model calls.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Iterable, Mapping

from aura_model_cognome import PATCH_AUTHORITY, VSA_PATCH_AUTHORITY, stable_digest, stable_id

REPLAY_VERSION = "AURA_MODEL_COGNOME_REPLAY_V1"
ZERO_MODEL = "ZERO_MODEL"
DIRECT = "DIRECT"
CASCADE = "CASCADE"
PANEL = "PANEL"
_EVALUABLE_SPLITS = frozenset({"VALIDATION", "SHADOW"})
_POLICY_MODES = frozenset({ZERO_MODEL, DIRECT, CASCADE, PANEL})


def _nonnegative(value: Any, name: str) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


@dataclass(frozen=True)
class ReplayOutcome:
    """One historically observed, verifier-linked outcome."""

    observation_id: str
    profile_id: str
    verifier_pass: bool | None
    cost_usd: float | None = None
    time_to_verified_ms: float | None = None
    repair_attempts: float = 0.0
    scope_violation_count: int = 0
    drift_score: float | None = None
    evidence_digest: str = ""
    policy_mode: str = ""

    def __post_init__(self) -> None:
        if not self.observation_id:
            raise ValueError("observation_id must not be empty")
        if not self.profile_id:
            raise ValueError("profile_id must not be empty")
        _nonnegative(self.cost_usd, "cost_usd")
        _nonnegative(self.time_to_verified_ms, "time_to_verified_ms")
        _nonnegative(self.repair_attempts, "repair_attempts")
        _nonnegative(self.scope_violation_count, "scope_violation_count")
        drift = _nonnegative(self.drift_score, "drift_score")
        if drift is not None and drift > 1.0:
            raise ValueError("drift_score must be between zero and one")
        if not self.evidence_digest:
            raise ValueError("evidence_digest must not be empty")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReplayOutcome":
        return cls(
            observation_id=str(value.get("observation_id") or ""),
            profile_id=str(value.get("profile_id") or ""),
            verifier_pass=value.get("verifier_pass"),
            cost_usd=value.get("cost_usd"),
            time_to_verified_ms=value.get("time_to_verified_outcome_ms", value.get("time_to_verified_ms")),
            repair_attempts=float(value.get("repair_attempt_count") or value.get("repair_attempts") or 0.0),
            scope_violation_count=int(value.get("scope_violation_count") or 0),
            drift_score=value.get("endpoint_drift_score", value.get("drift_score")),
            evidence_digest=str(value.get("evidence_digest") or stable_digest(dict(value))),
            policy_mode=str(value.get("policy_mode") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayCase:
    """One isolated historical task with mutually comparable outcomes."""

    case_id: str
    task_context_id: str
    evidence_split: str
    capability_graph_digest: str
    path_digest: str
    outcomes: tuple[ReplayOutcome, ...] = ()
    zero_model_outcome: ReplayOutcome | None = None
    panel_outcome: ReplayOutcome | None = None
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.case_id or not self.task_context_id:
            raise ValueError("case_id and task_context_id must not be empty")
        if self.evidence_split not in _EVALUABLE_SPLITS:
            raise ValueError("replay evidence must come from VALIDATION or SHADOW")
        if not self.capability_graph_digest or not self.path_digest:
            raise ValueError("replay cases must be graph and path bound")
        profile_ids = [item.profile_id for item in self.outcomes]
        if len(profile_ids) != len(set(profile_ids)):
            raise ValueError("a replay case cannot contain duplicate profile outcomes")

    @classmethod
    def create(
        cls,
        *,
        task_context_id: str,
        evidence_split: str,
        capability_graph_digest: str,
        path_digest: str,
        outcomes: Iterable[ReplayOutcome | Mapping[str, Any]] = (),
        zero_model_outcome: ReplayOutcome | Mapping[str, Any] | None = None,
        panel_outcome: ReplayOutcome | Mapping[str, Any] | None = None,
        created_at: float | None = None,
    ) -> "ReplayCase":
        normalized = tuple(
            item if isinstance(item, ReplayOutcome) else ReplayOutcome.from_mapping(item)
            for item in outcomes
        )
        zero = (
            zero_model_outcome
            if isinstance(zero_model_outcome, ReplayOutcome) or zero_model_outcome is None
            else ReplayOutcome.from_mapping(zero_model_outcome)
        )
        panel = (
            panel_outcome
            if isinstance(panel_outcome, ReplayOutcome) or panel_outcome is None
            else ReplayOutcome.from_mapping(panel_outcome)
        )
        basis = {
            "task_context_id": task_context_id,
            "evidence_split": evidence_split,
            "capability_graph_digest": capability_graph_digest,
            "path_digest": path_digest,
            "observation_ids": sorted(item.observation_id for item in normalized),
            "zero_observation_id": zero.observation_id if zero else "",
            "panel_observation_id": panel.observation_id if panel else "",
        }
        return cls(
            case_id=stable_id("replay-case", basis),
            task_context_id=task_context_id,
            evidence_split=evidence_split,
            capability_graph_digest=capability_graph_digest,
            path_digest=path_digest,
            outcomes=normalized,
            zero_model_outcome=zero,
            panel_outcome=panel,
            created_at=time.time() if created_at is None else float(created_at),
        )


@dataclass(frozen=True)
class ReplayPolicy:
    policy_id: str
    policy_mode: str
    profile_ids: tuple[str, ...] = ()
    policy_version: str = ""

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("policy_id must not be empty")
        if self.policy_mode not in _POLICY_MODES:
            raise ValueError(f"unknown replay policy mode: {self.policy_mode}")
        if self.policy_mode == ZERO_MODEL and self.profile_ids:
            raise ValueError("ZERO_MODEL replay policies cannot select profiles")
        if self.policy_mode in {DIRECT, CASCADE, PANEL} and not self.profile_ids:
            raise ValueError(f"{self.policy_mode} replay policies require profiles")
        if self.policy_mode == DIRECT and len(self.profile_ids) != 1:
            raise ValueError("DIRECT replay policies require exactly one profile")
        if self.policy_mode in {CASCADE, PANEL} and len(self.profile_ids) < 2:
            raise ValueError(f"{self.policy_mode} replay policies require at least two profiles")

    @classmethod
    def create(
        cls,
        *,
        policy_mode: str,
        profile_ids: Iterable[str] = (),
        policy_version: str = REPLAY_VERSION,
    ) -> "ReplayPolicy":
        profiles = tuple(str(item) for item in profile_ids)
        basis = {"policy_mode": policy_mode, "profile_ids": profiles, "policy_version": policy_version}
        return cls(
            policy_id=stable_id("replay-policy", basis),
            policy_mode=policy_mode,
            profile_ids=profiles,
            policy_version=policy_version,
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["profile_ids"] = list(self.profile_ids)
        return data


@dataclass(frozen=True)
class ReplayCaseResult:
    case_id: str
    status: str
    verified_success: bool | None
    used_profile_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    cost_usd: float | None
    time_to_verified_ms: float | None
    repair_attempts: float | None
    scope_violation_count: int | None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["used_profile_ids"] = list(self.used_profile_ids)
        data["observation_ids"] = list(self.observation_ids)
        return data


@dataclass(frozen=True)
class ReplayEvaluation:
    evaluation_id: str
    policy: ReplayPolicy
    case_results: tuple[ReplayCaseResult, ...]
    evaluated_count: int
    unevaluable_count: int
    coverage: float
    verified_success_rate: float | None
    mean_cost_usd: float | None
    mean_time_to_verified_ms: float | None
    mean_repair_attempts: float | None
    mean_scope_violation_count: float | None
    evidence_digest: str
    measurement_mode: str = "REPLAY"
    proposal_only: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "policy": self.policy.to_dict(),
            "case_results": [item.to_dict() for item in self.case_results],
        }


def _sum_known(values: Iterable[float | None]) -> float | None:
    items = list(values)
    if any(value is None for value in items):
        return None
    return sum(float(value) for value in items if value is not None)


def _evaluate_case(case: ReplayCase, policy: ReplayPolicy) -> ReplayCaseResult:
    by_profile = {item.profile_id: item for item in case.outcomes}
    if policy.policy_mode == ZERO_MODEL:
        outcome = case.zero_model_outcome
        if outcome is None:
            return ReplayCaseResult(case.case_id, "UNEVALUABLE", None, (), (), None, None, None, None, "no recorded ZERO_MODEL outcome")
        selected = [outcome]
    elif policy.policy_mode == DIRECT:
        outcome = by_profile.get(policy.profile_ids[0])
        if outcome is None:
            return ReplayCaseResult(case.case_id, "UNEVALUABLE", None, (), (), None, None, None, None, "selected profile has no comparable observation")
        selected = [outcome]
    elif policy.policy_mode == PANEL:
        outcome = case.panel_outcome
        if outcome is None or outcome.policy_mode != PANEL:
            return ReplayCaseResult(case.case_id, "UNEVALUABLE", None, (), (), None, None, None, None, "no recorded PANEL outcome; independent calls are not synthesized")
        selected = [outcome]
    else:
        selected = []
        for profile_id in policy.profile_ids:
            outcome = by_profile.get(profile_id)
            if outcome is None:
                return ReplayCaseResult(case.case_id, "UNEVALUABLE", None, tuple(item.profile_id for item in selected), tuple(item.observation_id for item in selected), None, None, None, None, f"fallback profile {profile_id} has no comparable observation")
            selected.append(outcome)
            if outcome.verifier_pass is True:
                break

    success = selected[-1].verifier_pass if selected else None
    return ReplayCaseResult(
        case_id=case.case_id,
        status="EVALUATED",
        verified_success=success,
        used_profile_ids=tuple(item.profile_id for item in selected),
        observation_ids=tuple(item.observation_id for item in selected),
        cost_usd=_sum_known(item.cost_usd for item in selected),
        time_to_verified_ms=_sum_known(item.time_to_verified_ms for item in selected),
        repair_attempts=_sum_known(item.repair_attempts for item in selected),
        scope_violation_count=sum(item.scope_violation_count for item in selected),
    )


def _mean_known(values: Iterable[float | int | None]) -> float | None:
    items = [float(value) for value in values if value is not None]
    return sum(items) / len(items) if items else None


def evaluate_replay(cases: Iterable[ReplayCase], policy: ReplayPolicy) -> ReplayEvaluation:
    normalized = tuple(cases)
    if not normalized:
        raise ValueError("replay evaluation requires at least one case")
    results = tuple(_evaluate_case(case, policy) for case in normalized)
    evaluated = tuple(item for item in results if item.status == "EVALUATED")
    successes = [item.verified_success for item in evaluated if item.verified_success is not None]
    evidence_basis = {
        "policy": policy.to_dict(),
        "cases": [
            {
                "case_id": case.case_id,
                "split": case.evidence_split,
                "graph": case.capability_graph_digest,
                "path": case.path_digest,
                "observation_ids": [item.observation_id for item in case.outcomes],
                "zero": case.zero_model_outcome.observation_id if case.zero_model_outcome else "",
                "panel": case.panel_outcome.observation_id if case.panel_outcome else "",
            }
            for case in normalized
        ],
        "results": [item.to_dict() for item in results],
    }
    evidence_digest = stable_digest(evidence_basis)
    evaluation_id = stable_id("replay-evaluation", {"policy_id": policy.policy_id, "evidence_digest": evidence_digest})
    return ReplayEvaluation(
        evaluation_id=evaluation_id,
        policy=policy,
        case_results=results,
        evaluated_count=len(evaluated),
        unevaluable_count=len(results) - len(evaluated),
        coverage=len(evaluated) / len(results),
        verified_success_rate=(sum(1 for value in successes if value) / len(successes)) if successes else None,
        mean_cost_usd=_mean_known(item.cost_usd for item in evaluated),
        mean_time_to_verified_ms=_mean_known(item.time_to_verified_ms for item in evaluated),
        mean_repair_attempts=_mean_known(item.repair_attempts for item in evaluated),
        mean_scope_violation_count=_mean_known(item.scope_violation_count for item in evaluated),
        evidence_digest=evidence_digest,
    )


def compare_replay_evaluations(candidate: ReplayEvaluation, baseline: ReplayEvaluation) -> dict[str, Any]:
    if candidate.measurement_mode != "REPLAY" or baseline.measurement_mode != "REPLAY":
        raise ValueError("only REPLAY evaluations can be compared")
    candidate_map = {
        item.case_id: item for item in candidate.case_results if item.status == "EVALUATED"
    }
    baseline_map = {
        item.case_id: item for item in baseline.case_results if item.status == "EVALUATED"
    }
    common = sorted(set(candidate_map) & set(baseline_map))
    if not common:
        raise ValueError("replay evaluations have no common evaluated cases")

    def summarize(values: dict[str, ReplayCaseResult]) -> dict[str, float | None]:
        selected = [values[case_id] for case_id in common]
        successes = [item.verified_success for item in selected if item.verified_success is not None]
        return {
            "verified_success_rate": (
                sum(1 for value in successes if value) / len(successes) if successes else None
            ),
            "mean_cost_usd": _mean_known(item.cost_usd for item in selected),
            "mean_time_to_verified_ms": _mean_known(item.time_to_verified_ms for item in selected),
            "mean_repair_attempts": _mean_known(item.repair_attempts for item in selected),
            "mean_scope_violation_count": _mean_known(
                item.scope_violation_count for item in selected
            ),
        }

    candidate_summary = summarize(candidate_map)
    baseline_summary = summarize(baseline_map)

    def delta(name: str) -> float | None:
        left = candidate_summary[name]
        right = baseline_summary[name]
        return None if left is None or right is None else float(left) - float(right)

    union_count = len(set(candidate_map) | set(baseline_map))
    result = {
        "comparison_id": stable_id(
            "replay-comparison",
            {
                "candidate": candidate.evaluation_id,
                "baseline": baseline.evaluation_id,
                "common_cases": common,
            },
        ),
        "measurement_mode": "REPLAY",
        "candidate_evaluation_id": candidate.evaluation_id,
        "baseline_evaluation_id": baseline.evaluation_id,
        "common_case_count": len(common),
        "evaluated_count": len(common),
        "coverage": len(common) / union_count if union_count else 0.0,
        "success_rate_delta": delta("verified_success_rate"),
        "mean_cost_delta_usd": delta("mean_cost_usd"),
        "mean_time_delta_ms": delta("mean_time_to_verified_ms"),
        "mean_repair_delta": delta("mean_repair_attempts"),
        "mean_scope_violation_delta": delta("mean_scope_violation_count"),
        "candidate_common_summary": candidate_summary,
        "baseline_common_summary": baseline_summary,
        "candidate_evidence_digest": candidate.evidence_digest,
        "baseline_evidence_digest": baseline.evidence_digest,
        "proposal_only": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
    result["comparison_digest"] = stable_digest(result)
    return result


def persist_replay_comparison(store: Any, comparison: Mapping[str, Any]) -> str:
    payload = dict(comparison)
    payload["measurement_mode"] = "REPLAY"
    payload["approved_live"] = False
    payload.setdefault("created_at", time.time())
    return str(store.record_experiment_comparison(payload))
