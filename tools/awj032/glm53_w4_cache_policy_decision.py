"""D0 cache-policy decision membrane for AWJ032 GLM-5.3 W4.

Consumes already-attested W4 expert-I/O counter receipts and separately attested
lifecycle measurements. A candidate may replace an explicit baseline only by
Pareto dominance on the exact same source/workload/measurement campaign.

This module does not benchmark a host, implement cache/prefetch policy, grant
K27/geometric placement priority, read checkpoint payloads, execute a model, or
admit G2. Hit ratio is diagnostic only and never a winning criterion.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

try:
    from .glm53_w4_host_preflight import W4PreflightReceipt
except ImportError:
    from glm53_w4_host_preflight import W4PreflightReceipt

SCHEMA = "GLM53W4CachePolicyDecisionV1"
ROLE = "CACHE_PLACEMENT_ONLY_NO_PREFETCH_CREDIT"


class W4CachePolicyDecisionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W4CachePolicyDecisionError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _exact_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise W4CachePolicyDecisionError(f"{name.upper()}_INVALID")
    return value


def _nonnegative(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise W4CachePolicyDecisionError(f"{name.upper()}_INVALID")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise W4CachePolicyDecisionError(f"{name.upper()}_INVALID")
    return out


def _bytes(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise W4CachePolicyDecisionError(f"{name.upper()}_INVALID")
    return value


def _ratio(name: str, value: Any) -> float:
    out = _nonnegative(name, value)
    if out > 1:
        raise W4CachePolicyDecisionError(f"{name.upper()}_INVALID")
    return out


@dataclass(frozen=True)
class W4CachePolicyObservation:
    policy_id: str
    policy_class: str
    preflight: W4PreflightReceipt
    measurement_campaign_ref: str
    lifecycle_measurement_attestation_ref: str
    lifecycle_metrics_attested: bool
    correctness_reference_equivalent: bool
    source_current: bool
    measurement_current: bool
    cache_hit_ratio: float
    energy_joules: float
    peak_resident_bytes: int
    warmup_seconds: float
    restart_seconds: float
    revalidation_seconds: float
    control_overhead_seconds: float
    role: str = ROLE


@dataclass(frozen=True)
class W4CachePolicyDecisionReceipt:
    schema: str
    baseline_policy_id: str
    candidate_policy_id: str
    relation: str
    retained_policy_id: str | None
    source_generation: str
    workload_ref: str
    scope_ref: str
    measurement_campaign_ref: str
    baseline_lifecycle_attestation_ref: str
    candidate_lifecycle_attestation_ref: str
    compared_metrics: tuple[str, ...]
    better_metrics: tuple[str, ...]
    worse_metrics: tuple[str, ...]
    equal_metrics: tuple[str, ...]
    baseline_hit_ratio: float
    candidate_hit_ratio: float
    higher_hit_ratio_not_used_as_authority: bool
    k27_or_geometry_privileged: bool = False
    runtime_execution_proven: bool = False
    end_to_end_usability_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    authority: bool = False
    claim_ceiling: str = (
        "D0_SAME_SCOPE_ATTESTED_CACHE_POLICY_PARETO_DECISION_ONLY_"
        "HIT_RATIO_NE_NET_BENEFIT_NO_HOST_RUNTIME_QUALITY_OR_G2_PROOF"
    )


_METRICS = (
    "physical_total_expert_bytes",
    "exposed_seconds",
    "energy_joules",
    "peak_resident_bytes",
    "warmup_seconds",
    "restart_seconds",
    "revalidation_seconds",
    "control_overhead_seconds",
)


def _validate_observation(obs: W4CachePolicyObservation, *, label: str) -> dict[str, float]:
    if not isinstance(obs, W4CachePolicyObservation):
        raise W4CachePolicyDecisionError(f"{label}_OBSERVATION_REQUIRED")
    _text(f"{label}_policy_id", obs.policy_id)
    _text(f"{label}_policy_class", obs.policy_class)
    _text(f"{label}_measurement_campaign_ref", obs.measurement_campaign_ref)
    _text(f"{label}_lifecycle_measurement_attestation_ref", obs.lifecycle_measurement_attestation_ref)
    if obs.role != ROLE:
        raise W4CachePolicyDecisionError(f"{label}_ROLE_MISMATCH")
    if not isinstance(obs.preflight, W4PreflightReceipt):
        raise W4CachePolicyDecisionError(f"{label}_W4_PREFLIGHT_REQUIRED")
    if obs.preflight.physical_io_attested is not True:
        raise W4CachePolicyDecisionError(f"{label}_PHYSICAL_IO_ATTESTATION_REQUIRED")
    if obs.preflight.runtime_execution_proven or obs.preflight.end_to_end_usability_proven or obs.preflight.g2_admitted:
        raise W4CachePolicyDecisionError(f"{label}_W4_EFFECT_CEILING_WIDENED")

    if obs.preflight.prefetch_useful_bytes != 0 or obs.preflight.prefetch_waste_bytes != 0:
        raise W4CachePolicyDecisionError(f"{label}_PREFETCH_CROSS_CREDIT_FORBIDDEN")
    if obs.preflight.overlap_seconds != 0:
        raise W4CachePolicyDecisionError(f"{label}_OVERLAP_CROSS_CREDIT_FORBIDDEN")

    if not _exact_bool(f"{label}_lifecycle_metrics_attested", obs.lifecycle_metrics_attested):
        raise W4CachePolicyDecisionError(f"{label}_LIFECYCLE_METRICS_ATTESTATION_REQUIRED")
    if not _exact_bool(f"{label}_correctness_reference_equivalent", obs.correctness_reference_equivalent):
        raise W4CachePolicyDecisionError(f"{label}_CORRECTNESS_REQUIRED")
    if not _exact_bool(f"{label}_source_current", obs.source_current):
        raise W4CachePolicyDecisionError(f"{label}_SOURCE_CURRENT_REQUIRED")
    if not _exact_bool(f"{label}_measurement_current", obs.measurement_current):
        raise W4CachePolicyDecisionError(f"{label}_MEASUREMENT_CURRENT_REQUIRED")

    return {
        "physical_total_expert_bytes": float(_bytes(f"{label}_physical_total_expert_bytes", obs.preflight.physical_total_expert_bytes)),
        "exposed_seconds": _nonnegative(f"{label}_exposed_seconds", obs.preflight.exposed_seconds),
        "energy_joules": _nonnegative(f"{label}_energy_joules", obs.energy_joules),
        "peak_resident_bytes": float(_bytes(f"{label}_peak_resident_bytes", obs.peak_resident_bytes)),
        "warmup_seconds": _nonnegative(f"{label}_warmup_seconds", obs.warmup_seconds),
        "restart_seconds": _nonnegative(f"{label}_restart_seconds", obs.restart_seconds),
        "revalidation_seconds": _nonnegative(f"{label}_revalidation_seconds", obs.revalidation_seconds),
        "control_overhead_seconds": _nonnegative(f"{label}_control_overhead_seconds", obs.control_overhead_seconds),
    }


def compare_cache_policy_to_baseline(*, baseline: W4CachePolicyObservation, candidate: W4CachePolicyObservation) -> W4CachePolicyDecisionReceipt:
    """Compare exact same-campaign cache policies without invented scalar weights."""
    b = _validate_observation(baseline, label="BASELINE")
    c = _validate_observation(candidate, label="CANDIDATE")
    if baseline.policy_id == candidate.policy_id:
        raise W4CachePolicyDecisionError("DISTINCT_POLICY_IDS_REQUIRED")

    bp, cp = baseline.preflight, candidate.preflight
    if not (
        bp.scope_ref == cp.scope_ref
        and bp.source_generation == cp.source_generation
        and bp.workload_ref == cp.workload_ref
        and bp.logical_expert_bytes_required == cp.logical_expert_bytes_required
        and bp.exposed_io_budget_seconds == cp.exposed_io_budget_seconds
    ):
        raise W4CachePolicyDecisionError("SAME_SCOPE_SOURCE_WORKLOAD_REQUIRED")
    if baseline.measurement_campaign_ref != candidate.measurement_campaign_ref:
        raise W4CachePolicyDecisionError("SAME_MEASUREMENT_CAMPAIGN_REQUIRED")

    b_hit = _ratio("baseline_cache_hit_ratio", baseline.cache_hit_ratio)
    c_hit = _ratio("candidate_cache_hit_ratio", candidate.cache_hit_ratio)
    better = tuple(name for name in _METRICS if c[name] < b[name])
    worse = tuple(name for name in _METRICS if c[name] > b[name])
    equal = tuple(name for name in _METRICS if c[name] == b[name])

    if better and not worse:
        relation, retained = "CANDIDATE_PARETO_DOMINATES_BASELINE", candidate.policy_id
    elif worse and not better:
        relation, retained = "CANDIDATE_PARETO_REGRESSES_BASELINE", baseline.policy_id
    elif not better and not worse:
        relation, retained = "CANDIDATE_EQUAL_TO_BASELINE", baseline.policy_id
    else:
        relation, retained = "NONDOMINATED_TRADEOFF_REQUIRES_EXPLICIT_POLICY_PREFERENCE", None

    return W4CachePolicyDecisionReceipt(
        schema=SCHEMA,
        baseline_policy_id=baseline.policy_id,
        candidate_policy_id=candidate.policy_id,
        relation=relation,
        retained_policy_id=retained,
        source_generation=bp.source_generation,
        workload_ref=bp.workload_ref,
        scope_ref=bp.scope_ref,
        measurement_campaign_ref=baseline.measurement_campaign_ref,
        baseline_lifecycle_attestation_ref=baseline.lifecycle_measurement_attestation_ref,
        candidate_lifecycle_attestation_ref=candidate.lifecycle_measurement_attestation_ref,
        compared_metrics=_METRICS,
        better_metrics=better,
        worse_metrics=worse,
        equal_metrics=equal,
        baseline_hit_ratio=b_hit,
        candidate_hit_ratio=c_hit,
        higher_hit_ratio_not_used_as_authority=c_hit > b_hit,
    )
