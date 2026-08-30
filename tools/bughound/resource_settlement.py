"""Observed-resource settlement for matched BugHound topology benchmarks.

A matched run plan is a preregistered budget, not evidence that the executed arm
actually respected that budget. This module keeps those planes separate: an
independent evaluator observation binds exact run-plan identity to the distinct
workers and tool calls actually observed, then admits a score for cross-topology
comparison only when both benchmark validity and measured budget compliance hold.

D0 / benchmark contract only. It does not execute workers, call providers, create
host effects, or authorize promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.bughound.seedlab_benchmark import BenchmarkScoreV1, MatchedRunPlanV1

OBSERVATION_SCHEMA = "BugHoundMatchedResourceObservationV1"
SETTLEMENT_SCHEMA = "BugHoundMatchedResourceSettlementV1"


class ResourceSettlementError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ResourceSettlementError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResourceSettlementError(code)
    return value.strip()


def _unique_text_tuple(value: Any, code: str, *, allow_empty: bool) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ResourceSettlementError(code)
    out = tuple(_text(item, code) for item in value)
    if not allow_empty and not out:
        raise ResourceSettlementError(code)
    if len(set(out)) != len(out):
        raise ResourceSettlementError("RESOURCE_OBSERVATION_DUPLICATE_ID", code)
    return out


@dataclass(frozen=True)
class MatchedResourceObservationV1:
    run_plan_digest: str
    topology_id: str
    source_generation: str
    observed_worker_ids: tuple[str, ...]
    observed_tool_call_ids: tuple[str, ...]
    observer_generation: str
    observer_current: bool = True
    independent_observer: bool = True
    run_completed: bool = True
    authority: bool = False
    external_effect: bool = False
    schema: str = OBSERVATION_SCHEMA

    def __post_init__(self) -> None:
        _text(self.run_plan_digest, "RUN_PLAN_DIGEST_REQUIRED")
        _text(self.topology_id, "TOPOLOGY_ID_REQUIRED")
        _text(self.source_generation, "SOURCE_GENERATION_REQUIRED")
        _unique_text_tuple(
            self.observed_worker_ids,
            "OBSERVED_WORKER_IDS_REQUIRED",
            allow_empty=False,
        )
        _unique_text_tuple(
            self.observed_tool_call_ids,
            "OBSERVED_TOOL_CALL_IDS_INVALID",
            allow_empty=True,
        )
        _text(self.observer_generation, "OBSERVER_GENERATION_REQUIRED")
        for value, code in (
            (self.observer_current, "OBSERVER_CURRENT_BOOL_REQUIRED"),
            (self.independent_observer, "INDEPENDENT_OBSERVER_BOOL_REQUIRED"),
            (self.run_completed, "RUN_COMPLETED_BOOL_REQUIRED"),
        ):
            if type(value) is not bool:
                raise ResourceSettlementError(code)
        if self.authority or self.external_effect:
            raise ResourceSettlementError("RESOURCE_OBSERVATION_AUTHORITY_WIDENING_FORBIDDEN")

    @property
    def observed_worker_count(self) -> int:
        return len(self.observed_worker_ids)

    @property
    def observed_tool_call_count(self) -> int:
        return len(self.observed_tool_call_ids)

    @property
    def observation_digest(self) -> str:
        return _digest("AURA_BUGHOUND_MATCHED_RESOURCE_OBSERVATION_V1", asdict(self))


@dataclass(frozen=True)
class MatchedResourceSettlementV1:
    topology_id: str
    run_plan_digest: str
    match_basis_digest: str
    resource_observation_digest: str
    planned_worker_budget: int
    planned_tool_budget: int
    observed_worker_count: int
    observed_tool_call_count: int
    benchmark_score_valid: bool
    resource_budget_satisfied: bool
    admitted_for_cross_topology_comparison: bool
    status: str
    blockers: tuple[str, ...]
    authority: bool = False
    external_effect: bool = False
    promotion_authorized: bool = False
    schema: str = SETTLEMENT_SCHEMA

    @property
    def settlement_digest(self) -> str:
        return _digest("AURA_BUGHOUND_MATCHED_RESOURCE_SETTLEMENT_V1", asdict(self))


def settle_matched_resource_use(
    *,
    plan: MatchedRunPlanV1,
    score: BenchmarkScoreV1,
    observation: MatchedResourceObservationV1,
) -> MatchedResourceSettlementV1:
    if not isinstance(plan, MatchedRunPlanV1):
        raise ResourceSettlementError("MATCHED_RUN_PLAN_REQUIRED")
    if not isinstance(score, BenchmarkScoreV1):
        raise ResourceSettlementError("BENCHMARK_SCORE_REQUIRED")
    if not isinstance(observation, MatchedResourceObservationV1):
        raise ResourceSettlementError("RESOURCE_OBSERVATION_REQUIRED")

    if observation.run_plan_digest != plan.run_plan_digest:
        raise ResourceSettlementError("RESOURCE_RUN_PLAN_BINDING_MISMATCH")
    if observation.topology_id != plan.topology_id or score.topology_id != plan.topology_id:
        raise ResourceSettlementError("RESOURCE_TOPOLOGY_BINDING_MISMATCH")
    if observation.source_generation != plan.source_generation:
        raise ResourceSettlementError("RESOURCE_SOURCE_GENERATION_MISMATCH")
    if score.match_basis_digest != plan.match_basis_digest:
        raise ResourceSettlementError("RESOURCE_MATCH_BASIS_MISMATCH")

    blockers: list[str] = []
    if not observation.observer_current:
        blockers.append("RESOURCE_OBSERVER_STALE")
    if not observation.independent_observer:
        blockers.append("INDEPENDENT_RESOURCE_OBSERVER_REQUIRED")
    if not observation.run_completed:
        blockers.append("RESOURCE_RUN_NOT_COMPLETED")
    if observation.observed_worker_count > plan.worker_budget:
        blockers.append("WORKER_BUDGET_EXCEEDED")
    if observation.observed_tool_call_count > plan.tool_budget:
        blockers.append("TOOL_BUDGET_EXCEEDED")
    if not score.valid_for_comparison:
        blockers.append("BENCHMARK_SCORE_NOT_VALID_FOR_COMPARISON")
    if not score.observed_metrics_only:
        blockers.append("BENCHMARK_SCORE_NOT_OBSERVED_METRICS_ONLY")
    if score.authority or score.external_effect or score.promotion_authorized:
        blockers.append("BENCHMARK_SCORE_AUTHORITY_WIDENING_FORBIDDEN")

    blockers = sorted(set(blockers))
    resource_ok = not any(
        blocker in blockers
        for blocker in (
            "RESOURCE_OBSERVER_STALE",
            "INDEPENDENT_RESOURCE_OBSERVER_REQUIRED",
            "RESOURCE_RUN_NOT_COMPLETED",
            "WORKER_BUDGET_EXCEEDED",
            "TOOL_BUDGET_EXCEEDED",
        )
    )
    score_ok = not any(
        blocker in blockers
        for blocker in (
            "BENCHMARK_SCORE_NOT_VALID_FOR_COMPARISON",
            "BENCHMARK_SCORE_NOT_OBSERVED_METRICS_ONLY",
            "BENCHMARK_SCORE_AUTHORITY_WIDENING_FORBIDDEN",
        )
    )
    admitted = resource_ok and score_ok and not blockers
    return MatchedResourceSettlementV1(
        topology_id=plan.topology_id,
        run_plan_digest=plan.run_plan_digest,
        match_basis_digest=plan.match_basis_digest,
        resource_observation_digest=observation.observation_digest,
        planned_worker_budget=plan.worker_budget,
        planned_tool_budget=plan.tool_budget,
        observed_worker_count=observation.observed_worker_count,
        observed_tool_call_count=observation.observed_tool_call_count,
        benchmark_score_valid=score_ok,
        resource_budget_satisfied=resource_ok,
        admitted_for_cross_topology_comparison=admitted,
        status="ADMITTED_MATCHED_OBSERVED_RESOURCES" if admitted else "BLOCKED",
        blockers=tuple(blockers),
    )
