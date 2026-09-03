from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from hashlib import sha256
import json
from typing import Iterable


class PrecisionTier(IntEnum):
    T1_CURRENTNESS = 1
    T2_STRUCTURAL = 2
    T3_PATH_SENSITIVE = 3
    T4_INTERPROCEDURAL_DATAFLOW = 4
    T5_STATEFUL_SYMBOLIC = 5
    T6_LOCAL_DYNAMIC = 6
    T7_L4_COUNTERFACTUAL = 7


TIER_COST = {
    PrecisionTier.T1_CURRENTNESS: 1,
    PrecisionTier.T2_STRUCTURAL: 2,
    PrecisionTier.T3_PATH_SENSITIVE: 4,
    PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW: 7,
    PrecisionTier.T5_STATEFUL_SYMBOLIC: 11,
    PrecisionTier.T6_LOCAL_DYNAMIC: 17,
    PrecisionTier.T7_L4_COUNTERFACTUAL: 25,
}

TIER_TOOL = {
    PrecisionTier.T1_CURRENTNESS: "SOURCE_INDEXER",
    PrecisionTier.T2_STRUCTURAL: "STATIC_CODE_GRAPH",
    PrecisionTier.T3_PATH_SENSITIVE: "STATIC_CODE_GRAPH",
    PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW: "STATIC_CODE_GRAPH",
    PrecisionTier.T5_STATEFUL_SYMBOLIC: "STATEFUL_LOCAL_ANALYZER",
    PrecisionTier.T6_LOCAL_DYNAMIC: "LOCAL_FUZZ_ORACLE",
    PrecisionTier.T7_L4_COUNTERFACTUAL: "LOCAL_BUILD_TEST",
}

TIER_CITY = {
    PrecisionTier.T1_CURRENTNESS: "ATHENS_RESEARCH_ARCHIVES",
    PrecisionTier.T2_STRUCTURAL: "SAN_FRANCISCO_ENGINEERING",
    PrecisionTier.T3_PATH_SENSITIVE: "SAN_FRANCISCO_ENGINEERING",
    PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW: "SAN_FRANCISCO_ENGINEERING",
    PrecisionTier.T5_STATEFUL_SYMBOLIC: "DETROIT_WORKSHOP",
    PrecisionTier.T6_LOCAL_DYNAMIC: "DETROIT_WORKSHOP",
    PrecisionTier.T7_L4_COUNTERFACTUAL: "DETROIT_WORKSHOP",
}


@dataclass(frozen=True)
class CaseState:
    case_id: str
    corpus_id: str
    expected_generation: str
    observed_generation: str
    hydrated_level: int
    dependency_complete: bool
    unresolved_structural: bool = False
    unresolved_path: bool = False
    unresolved_interprocedural: bool = False
    unresolved_stateful: bool = False
    dynamic_evidence_required: bool = False
    l4_counterfactual_required: bool = False
    local_oracle_available: bool = False
    source_tree_digest: str = ""
    oracle_generation: str = ""
    observed_oracle_generation: str = ""
    budget_units_remaining: int = 100
    network_required: bool = False
    credentials_required: bool = False


@dataclass(frozen=True)
class RouteDecision:
    case_id: str
    disposition: str
    tier: PrecisionTier | None
    tool_id: str | None
    city_lane: str | None
    cost_units: int
    widened_for_incomplete_dependencies: bool
    stale_evidence_invalidated: bool
    testing_authorized: bool = False
    network_authorized: bool = False
    credentials_authorized: bool = False
    submission_authorized: bool = False
    payment_authorized: bool = False
    external_effect: bool = False

    @property
    def decision_digest(self) -> str:
        payload = {
            "case_id": self.case_id,
            "disposition": self.disposition,
            "tier": None if self.tier is None else int(self.tier),
            "tool_id": self.tool_id,
            "city_lane": self.city_lane,
            "cost_units": self.cost_units,
            "widened": self.widened_for_incomplete_dependencies,
            "stale": self.stale_evidence_invalidated,
            "authority": [
                self.testing_authorized,
                self.network_authorized,
                self.credentials_authorized,
                self.submission_authorized,
                self.payment_authorized,
                self.external_effect,
            ],
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _required_tier(s: CaseState) -> PrecisionTier:
    if not s.dependency_complete:
        if s.local_oracle_available:
            return PrecisionTier.T7_L4_COUNTERFACTUAL
        return PrecisionTier.T6_LOCAL_DYNAMIC
    if s.l4_counterfactual_required:
        return PrecisionTier.T7_L4_COUNTERFACTUAL
    if s.dynamic_evidence_required:
        return PrecisionTier.T6_LOCAL_DYNAMIC
    if s.unresolved_stateful:
        return PrecisionTier.T5_STATEFUL_SYMBOLIC
    if s.unresolved_interprocedural:
        return PrecisionTier.T4_INTERPROCEDURAL_DATAFLOW
    if s.unresolved_path:
        return PrecisionTier.T3_PATH_SENSITIVE
    if s.unresolved_structural:
        return PrecisionTier.T2_STRUCTURAL
    return PrecisionTier.T1_CURRENTNESS


def route_case(s: CaseState) -> RouteDecision:
    if not s.case_id or not s.corpus_id:
        raise ValueError("CASE_ID_AND_CORPUS_REQUIRED")
    if s.network_required or s.credentials_required:
        return RouteDecision(s.case_id, "HOLD_EXTERNAL_EFFECT_REQUIREMENT", None, None, None, 0, False, False)
    if not s.expected_generation or not s.observed_generation or s.expected_generation != s.observed_generation:
        return RouteDecision(
            s.case_id,
            "REHYDRATE_FROM_L0_SOURCE_GENERATION",
            PrecisionTier.T1_CURRENTNESS,
            TIER_TOOL[PrecisionTier.T1_CURRENTNESS],
            TIER_CITY[PrecisionTier.T1_CURRENTNESS],
            TIER_COST[PrecisionTier.T1_CURRENTNESS],
            False,
            True,
        )
    if s.oracle_generation and s.observed_oracle_generation and s.oracle_generation != s.observed_oracle_generation:
        return RouteDecision(
            s.case_id,
            "INVALIDATE_L4_ORACLE_REPROOF_REQUIRED",
            PrecisionTier.T7_L4_COUNTERFACTUAL,
            TIER_TOOL[PrecisionTier.T7_L4_COUNTERFACTUAL],
            TIER_CITY[PrecisionTier.T7_L4_COUNTERFACTUAL],
            TIER_COST[PrecisionTier.T7_L4_COUNTERFACTUAL],
            True,
            True,
        )

    tier = _required_tier(s)
    if tier == PrecisionTier.T7_L4_COUNTERFACTUAL and not s.local_oracle_available:
        return RouteDecision(
            s.case_id,
            "HOLD_L4_LOCAL_ORACLE_UNAVAILABLE",
            tier,
            None,
            "FEDERAL_CAPITAL",
            0,
            not s.dependency_complete,
            False,
        )
    cost = TIER_COST[tier]
    if s.budget_units_remaining < cost:
        return RouteDecision(
            s.case_id,
            "STOP_BUDGET_EXHAUSTED",
            tier,
            TIER_TOOL[tier],
            TIER_CITY[tier],
            0,
            not s.dependency_complete,
            False,
        )
    if tier == PrecisionTier.T1_CURRENTNESS:
        return RouteDecision(
            s.case_id,
            "NO_DEEPER_ANALYSIS_REQUIRED",
            tier,
            TIER_TOOL[tier],
            TIER_CITY[tier],
            cost,
            False,
            False,
        )
    return RouteDecision(
        s.case_id,
        "RUN_MINIMUM_SUFFICIENT_LOCAL_TIER",
        tier,
        TIER_TOOL[tier],
        TIER_CITY[tier],
        cost,
        not s.dependency_complete,
        False,
    )


def naive_full_cost(states: Iterable[CaseState]) -> int:
    return sum(TIER_COST[PrecisionTier.T7_L4_COUNTERFACTUAL] for _ in states)


def routed_cost(states: Iterable[CaseState]) -> int:
    return sum(route_case(s).cost_units for s in states)


def difficulty_vector(s: CaseState) -> tuple[int, int, int, int, int, int, int]:
    return (
        int(s.unresolved_structural),
        int(s.unresolved_path),
        int(s.unresolved_interprocedural),
        int(s.unresolved_stateful),
        int(s.dynamic_evidence_required),
        int(s.l4_counterfactual_required),
        int(not s.dependency_complete),
    )


def hyper1000_cells() -> list[tuple[str, str, str]]:
    bug_classes = [
        "MEMORY", "INJECTION", "AUTHZ", "RACE", "LOGIC", "PARSER", "STATE", "CRYPTO", "RESOURCE", "SUPPLY_CHAIN"
    ]
    complexities = [
        "LOCAL", "BRANCH", "PATH", "INTERPROC", "DATAFLOW", "STATEFUL", "ASYNC", "CROSS_MODULE", "DYNAMIC", "COUNTERFACTUAL"
    ]
    invalidators = [
        "SOURCE_GEN", "ORACLE_GEN", "DEPENDENCY_UNKNOWN", "PATCH_DRIFT", "TOOL_GEN", "BUDGET", "CLEAN_CONTROL", "TRACE_DRIFT", "BUILD_ENV", "REPLAY"
    ]
    return [(b, c, i) for b in bug_classes for c in complexities for i in invalidators]


KEEPER_LAWS = (
    "StaleGreenEvidence != CurrentProof",
    "GeneratedProviderMovement != SemanticMovement",
    "Ambiguity != MandatoryExpensiveAnalysis",
    "UnknownDependencyCompleteness => WiderLocalValidationDebt",
    "LocalWiderValidation != OwnerAuthority",
    "StaticSuspicion != DynamicReproduction",
    "DynamicReproduction != CounterfactualSpecificity",
    "DifficultyVector != ExploitabilityProbability",
    "ToolRoute != TestingAuthority",
    "BenchmarkOptimization != LiveTargetAuthorization",
)
