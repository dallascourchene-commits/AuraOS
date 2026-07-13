"""Shadow-only adaptive model routing for Aura's Model Cognome.

This module evaluates ZERO_MODEL, DIRECT, CASCADE, and PANEL policies from
already-grounded Capability Connectome paths and verifier-backed Cognome
candidate evidence. It never calls a provider, executes tools, changes the
active router, or promotes a learned policy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import time
from typing import Any, Iterable, Mapping, Sequence

from aura_model_cognome import RouteDecision, TaskContext, stable_digest

SHADOW_ROUTER_VERSION = "AURA_SHADOW_MODEL_ROUTER_V2"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

ZERO_MODEL = "ZERO_MODEL"
DIRECT = "DIRECT"
CASCADE = "CASCADE"
PANEL = "PANEL"
DENIED = "DENIED"

_ACTIVE_ENDPOINT = "ACTIVE"
_HIGH_RISK = frozenset({"HIGH", "CRITICAL", "CONSEQUENTIAL"})


def _finite_nonnegative(value: Any, *, name: str, allow_none: bool = True) -> float | None:
    if value is None and allow_none:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric or None") from exc
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return numeric


def _probability(value: Any, *, default: float | None = None) -> float | None:
    if value is None:
        return default
    numeric = _finite_nonnegative(value, name="probability", allow_none=False)
    assert numeric is not None
    if numeric > 1:
        raise ValueError("probability must be between 0 and 1")
    return numeric


def _tuple_strings(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(str(item) for item in value if str(item))


def _first(mapping: Mapping[str, Any], names: Iterable[str], default: Any = None) -> Any:
    for name in names:
        if name in mapping and mapping[name] is not None:
            return mapping[name]
    return default


@dataclass(frozen=True)
class ShadowRoutingPolicy:
    policy_version: str = "AURA_SHADOW_POLICY_V1"
    quality_weight: float = 1.0
    cost_weight: float = 0.10
    latency_weight: float = 0.05
    repair_weight: float = 0.15
    scope_weight: float = 0.50
    drift_weight: float = 0.50
    energy_weight: float = 0.01
    unknown_cost_penalty: float = 0.05
    unknown_latency_penalty: float = 0.05
    cascade_min_primary_success: float = 0.65
    cascade_min_gain: float = 0.01
    high_risk_direct_min_success: float = 0.90
    panel_uncertainty_threshold: float = 0.20
    panel_size: int = 3
    verifier_overhead_ms: float = 0.0
    panel_synthesis_overhead_ms: float = 0.0
    allow_cascade: bool = True
    allow_panel: bool = True

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise ValueError("policy_version must not be empty")
        for name in (
            "quality_weight", "cost_weight", "latency_weight", "repair_weight",
            "scope_weight", "drift_weight", "energy_weight", "unknown_cost_penalty",
            "unknown_latency_penalty", "cascade_min_gain", "verifier_overhead_ms",
            "panel_synthesis_overhead_ms",
        ):
            _finite_nonnegative(getattr(self, name), name=name, allow_none=False)
        for name in (
            "cascade_min_primary_success", "high_risk_direct_min_success",
            "panel_uncertainty_threshold",
        ):
            _probability(getattr(self, name))
        if self.panel_size < 2:
            raise ValueError("panel_size must be at least 2")


@dataclass(frozen=True)
class CandidateEvidence:
    profile_id: str
    provider: str
    model: str
    endpoint_status: str
    access_class: str
    capability_ids: tuple[str, ...]
    capability_graph_digest: str
    evidence_split: str
    verified_success_probability: float | None
    mean_cost_usd: float | None
    mean_time_to_verified_ms: float | None
    mean_repair_attempts: float | None
    scope_violation_rate: float | None
    drift_score: float | None
    energy_joules: float | None
    uncertainty: float | None
    context_window: int | None
    supported_tools: tuple[str, ...]
    evidence_count: int
    evidence_digest: str
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @classmethod
    def from_mapping(cls, candidate: Mapping[str, Any]) -> "CandidateEvidence":
        profile_id = str(candidate.get("profile_id", "")).strip()
        if not profile_id:
            raise ValueError("candidate profile_id must not be empty")
        provider = str(candidate.get("provider", "unknown"))
        model = str(_first(candidate, ("returned_model", "requested_model", "model"), "unknown"))
        success = _probability(
            _first(candidate, ("verified_success_probability", "verified_success_mean", "posterior_mean"))
        )
        scope = _probability(_first(candidate, ("scope_violation_rate",)), default=0.0)
        drift = _probability(_first(candidate, ("endpoint_drift_score", "drift_score")))
        uncertainty = _probability(_first(candidate, ("uncertainty", "uncertainty_score", "calibration_error")))
        context_window_raw = _first(candidate, ("context_window", "max_context_tokens"))
        context_window = int(context_window_raw) if context_window_raw is not None else None
        if context_window is not None and context_window < 0:
            raise ValueError("candidate context_window must be non-negative")
        evidence_count = int(candidate.get("evidence_count") or candidate.get("sample_count") or 0)
        if evidence_count < 0:
            raise ValueError("candidate evidence_count must be non-negative")
        return cls(
            profile_id=profile_id,
            provider=provider,
            model=model,
            endpoint_status=str(candidate.get("status") or candidate.get("endpoint_status") or _ACTIVE_ENDPOINT),
            access_class=str(candidate.get("access_class") or "BLACK_BOX"),
            capability_ids=_tuple_strings(
                _first(candidate, ("capability_ids", "required_capability_ids", "supported_capability_ids"), ())
            ),
            capability_graph_digest=str(candidate.get("capability_graph_digest") or ""),
            evidence_split=str(candidate.get("evidence_split") or ""),
            verified_success_probability=success,
            mean_cost_usd=_finite_nonnegative(
                _first(candidate, ("mean_cost_usd", "expected_cost_usd", "cost_usd")),
                name="mean_cost_usd",
            ),
            mean_time_to_verified_ms=_finite_nonnegative(
                _first(candidate, ("mean_time_to_verified_ms", "expected_time_to_verified_ms", "p50_time_to_verified_ms")),
                name="mean_time_to_verified_ms",
            ),
            mean_repair_attempts=_finite_nonnegative(
                _first(candidate, ("mean_repair_attempts", "repair_burden"), 0.0),
                name="mean_repair_attempts",
            ),
            scope_violation_rate=scope,
            drift_score=drift,
            energy_joules=_finite_nonnegative(
                _first(candidate, ("energy_joules", "mean_energy_joules")),
                name="energy_joules",
            ),
            uncertainty=uncertainty,
            context_window=context_window,
            supported_tools=_tuple_strings(_first(candidate, ("supported_tools", "tools"), ())),
            evidence_count=evidence_count,
            evidence_digest=str(candidate.get("evidence_digest") or ""),
            raw=dict(candidate),
        )

    @property
    def is_local(self) -> bool:
        return self.provider.lower() == "local" or bool(self.raw.get("local"))


@dataclass(frozen=True)
class CandidateAssessment:
    candidate: CandidateEvidence
    admitted: bool
    rejection_reasons: tuple[str, ...]
    utility: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.candidate.profile_id,
            "provider": self.candidate.provider,
            "model": self.candidate.model,
            "admitted": self.admitted,
            "rejection_reasons": list(self.rejection_reasons),
            "utility": self.utility,
            "verified_success_probability": self.candidate.verified_success_probability,
            "mean_cost_usd": self.candidate.mean_cost_usd,
            "mean_time_to_verified_ms": self.candidate.mean_time_to_verified_ms,
            "mean_repair_attempts": self.candidate.mean_repair_attempts,
            "scope_violation_rate": self.candidate.scope_violation_rate,
            "drift_score": self.candidate.drift_score,
            "uncertainty": self.candidate.uncertainty,
            "evidence_count": self.candidate.evidence_count,
            "evidence_digest": self.candidate.evidence_digest,
        }


@dataclass(frozen=True)
class PolicyOption:
    policy_mode: str
    profile_ids: tuple[str, ...]
    expected_success: float
    expected_cost_usd: float | None
    expected_time_to_verified_ms: float | None
    expected_repair_burden: float
    expected_scope_violation_rate: float
    expected_drift: float
    expected_energy_joules: float | None
    utility: float
    explanation: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"profile_ids": list(self.profile_ids), "explanation": list(self.explanation)}


@dataclass(frozen=True)
class ShadowRouteResult:
    status: str
    route_decision: dict[str, Any] | None
    selected_option: PolicyOption | None
    options: tuple[PolicyOption, ...]
    candidate_assessments: tuple[CandidateAssessment, ...]
    baseline_comparisons: dict[str, dict[str, Any]]
    denial_reasons: tuple[str, ...]
    graph_digest: str
    path_digest: str
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": SHADOW_ROUTER_VERSION,
            "status": self.status,
            "route_decision": self.route_decision,
            "selected_option": self.selected_option.to_dict() if self.selected_option else None,
            "options": [option.to_dict() for option in self.options],
            "candidate_assessments": [item.to_dict() for item in self.candidate_assessments],
            "baseline_comparisons": self.baseline_comparisons,
            "denial_reasons": list(self.denial_reasons),
            "graph_digest": self.graph_digest,
            "path_digest": self.path_digest,
            "created_at": self.created_at,
            "shadow_only": True,
            "proposal_only": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def _utility(
    *,
    success: float,
    cost: float | None,
    latency_ms: float | None,
    repair: float,
    scope: float,
    drift: float,
    energy_joules: float | None,
    policy: ShadowRoutingPolicy,
) -> float:
    value = policy.quality_weight * success
    value -= policy.cost_weight * cost if cost is not None else policy.unknown_cost_penalty
    value -= policy.latency_weight * (latency_ms / 1000.0) if latency_ms is not None else policy.unknown_latency_penalty
    value -= policy.repair_weight * repair
    value -= policy.scope_weight * scope
    value -= policy.drift_weight * drift
    if energy_joules is not None:
        value -= policy.energy_weight * (energy_joules / 1000.0)
    return round(value, 8)


def _context_value(context: TaskContext, name: str, default: Any = None) -> Any:
    return getattr(context, name, default)


def _risk_class(context: TaskContext) -> str:
    return str(_context_value(context, "risk", "LOW") or "LOW").upper()


def _assess_candidate(
    candidate: CandidateEvidence,
    *,
    context: TaskContext,
    graph_digest: str,
    model_capability_ids: tuple[str, ...],
    consequential: bool,
    policy: ShadowRoutingPolicy,
) -> CandidateAssessment:
    reasons: list[str] = []
    if candidate.endpoint_status != _ACTIVE_ENDPOINT:
        reasons.append(f"endpoint status is {candidate.endpoint_status}")
    if not bool(_context_value(context, "data_egress_allowed", True)) and not candidate.is_local:
        reasons.append("data egress is not allowed")
    missing_capabilities = sorted(set(model_capability_ids) - set(candidate.capability_ids))
    if missing_capabilities:
        reasons.append("missing validated capability support: " + ", ".join(missing_capabilities))
    if candidate.capability_graph_digest != graph_digest:
        reasons.append("candidate capability evidence is stale or graph-unbound")
    if candidate.evidence_split not in {"SHADOW", "VALIDATION", "VALIDATED_EDGE"}:
        reasons.append("candidate evidence is not validation/shadow isolated")
    if candidate.evidence_count <= 0 or not candidate.evidence_digest:
        reasons.append("no verifier-backed capability evidence")
    if candidate.verified_success_probability is None:
        reasons.append("verified-success probability is unknown")
    context_tokens = int(_context_value(context, "context_tokens", 0) or 0)
    if context_tokens > 0 and candidate.context_window is None:
        reasons.append("context window is unknown")
    elif candidate.context_window is not None and candidate.context_window < context_tokens:
        reasons.append("context window is insufficient")
    required_tools = set(_tuple_strings(_context_value(context, "required_tools", ())))
    if required_tools and not required_tools.issubset(set(candidate.supported_tools)):
        reasons.append("required tools are unsupported")
    cost_budget = _context_value(context, "cost_budget_usd")
    if cost_budget is not None:
        if candidate.mean_cost_usd is None:
            reasons.append("cost is unknown under a hard budget")
        elif candidate.mean_cost_usd > float(cost_budget):
            reasons.append("expected cost exceeds budget")
    latency_budget = _context_value(context, "latency_budget_ms")
    if latency_budget is not None:
        if candidate.mean_time_to_verified_ms is None:
            reasons.append("time to verified outcome is unknown under a hard latency budget")
        elif candidate.mean_time_to_verified_ms > float(latency_budget):
            reasons.append("expected time to verified outcome exceeds budget")
    if consequential and candidate.uncertainty is None:
        reasons.append("uncertainty is unknown for a consequential route")
    admitted = not reasons
    utility = None
    if admitted:
        utility = _utility(
            success=float(candidate.verified_success_probability),
            cost=candidate.mean_cost_usd,
            latency_ms=candidate.mean_time_to_verified_ms,
            repair=float(candidate.mean_repair_attempts or 0.0),
            scope=float(candidate.scope_violation_rate or 0.0),
            drift=float(candidate.drift_score or 0.0),
            energy_joules=candidate.energy_joules,
            policy=policy,
        )
    return CandidateAssessment(candidate, admitted, tuple(reasons), utility)


def _direct_option(assessment: CandidateAssessment, policy: ShadowRoutingPolicy) -> PolicyOption:
    candidate = assessment.candidate
    assert assessment.utility is not None and candidate.verified_success_probability is not None
    return PolicyOption(
        policy_mode=DIRECT,
        profile_ids=(candidate.profile_id,),
        expected_success=candidate.verified_success_probability,
        expected_cost_usd=candidate.mean_cost_usd,
        expected_time_to_verified_ms=candidate.mean_time_to_verified_ms,
        expected_repair_burden=float(candidate.mean_repair_attempts or 0.0),
        expected_scope_violation_rate=float(candidate.scope_violation_rate or 0.0),
        expected_drift=float(candidate.drift_score or 0.0),
        expected_energy_joules=candidate.energy_joules,
        utility=assessment.utility,
        explanation=("highest admitted single-model utility",),
    )


def _cascade_option(
    primary: CandidateAssessment,
    fallback: CandidateAssessment,
    policy: ShadowRoutingPolicy,
) -> PolicyOption | None:
    first, second = primary.candidate, fallback.candidate
    p1, p2 = first.verified_success_probability, second.verified_success_probability
    if p1 is None or p2 is None or p1 < policy.cascade_min_primary_success:
        return None
    cost = None
    if first.mean_cost_usd is not None and second.mean_cost_usd is not None:
        cost = first.mean_cost_usd + (1.0 - p1) * second.mean_cost_usd
    latency = None
    if first.mean_time_to_verified_ms is not None and second.mean_time_to_verified_ms is not None:
        latency = (
            first.mean_time_to_verified_ms
            + policy.verifier_overhead_ms
            + (1.0 - p1) * second.mean_time_to_verified_ms
        )
    success = p1 + (1.0 - p1) * p2
    repair = float(first.mean_repair_attempts or 0.0) + (1.0 - p1) * float(second.mean_repair_attempts or 0.0)
    scope = max(float(first.scope_violation_rate or 0.0), float(second.scope_violation_rate or 0.0))
    drift = max(float(first.drift_score or 0.0), float(second.drift_score or 0.0))
    energy = None
    if first.energy_joules is not None and second.energy_joules is not None:
        energy = first.energy_joules + (1.0 - p1) * second.energy_joules
    utility = _utility(
        success=success,
        cost=cost,
        latency_ms=latency,
        repair=repair,
        scope=scope,
        drift=drift,
        energy_joules=energy,
        policy=policy,
    )
    return PolicyOption(
        policy_mode=CASCADE,
        profile_ids=(first.profile_id, second.profile_id),
        expected_success=round(success, 8),
        expected_cost_usd=round(cost, 8) if cost is not None else None,
        expected_time_to_verified_ms=round(latency, 8) if latency is not None else None,
        expected_repair_burden=round(repair, 8),
        expected_scope_violation_rate=scope,
        expected_drift=drift,
        expected_energy_joules=round(energy, 8) if energy is not None else None,
        utility=utility,
        explanation=(
            "cheap/specialist primary is verifier-gated",
            "fallback cost and latency are probability-weighted",
        ),
    )


def _panel_option(
    assessments: Sequence[CandidateAssessment],
    policy: ShadowRoutingPolicy,
) -> PolicyOption | None:
    selected = tuple(assessments[: policy.panel_size])
    if len(selected) < 2:
        return None
    failures = 1.0
    costs: list[float] = []
    latencies: list[float] = []
    energies: list[float] = []
    repair = scope = drift = 0.0
    for assessment in selected:
        candidate = assessment.candidate
        if candidate.verified_success_probability is None:
            return None
        failures *= 1.0 - candidate.verified_success_probability
        if candidate.mean_cost_usd is not None:
            costs.append(candidate.mean_cost_usd)
        if candidate.mean_time_to_verified_ms is not None:
            latencies.append(candidate.mean_time_to_verified_ms)
        if candidate.energy_joules is not None:
            energies.append(candidate.energy_joules)
        repair += float(candidate.mean_repair_attempts or 0.0)
        scope = max(scope, float(candidate.scope_violation_rate or 0.0))
        drift = max(drift, float(candidate.drift_score or 0.0))
    success = 1.0 - failures
    cost = sum(costs) if len(costs) == len(selected) else None
    latency = max(latencies) + policy.panel_synthesis_overhead_ms if len(latencies) == len(selected) else None
    energy = sum(energies) if len(energies) == len(selected) else None
    utility = _utility(
        success=success,
        cost=cost,
        latency_ms=latency,
        repair=repair,
        scope=scope,
        drift=drift,
        energy_joules=energy,
        policy=policy,
    )
    return PolicyOption(
        policy_mode=PANEL,
        profile_ids=tuple(item.candidate.profile_id for item in selected),
        expected_success=round(success, 8),
        expected_cost_usd=round(cost, 8) if cost is not None else None,
        expected_time_to_verified_ms=round(latency, 8) if latency is not None else None,
        expected_repair_burden=round(repair, 8),
        expected_scope_violation_rate=scope,
        expected_drift=drift,
        expected_energy_joules=round(energy, 8) if energy is not None else None,
        utility=utility,
        explanation=("optimistic independence surrogate; shadow proposal only",),
    )


def _fits_budgets(option: PolicyOption, context: TaskContext) -> bool:
    cost_budget = _context_value(context, "cost_budget_usd")
    if cost_budget is not None and (option.expected_cost_usd is None or option.expected_cost_usd > float(cost_budget)):
        return False
    latency_budget = _context_value(context, "latency_budget_ms")
    if latency_budget is not None and (
        option.expected_time_to_verified_ms is None
        or option.expected_time_to_verified_ms > float(latency_budget)
    ):
        return False
    return True


def _baselines(admitted: Sequence[CandidateAssessment]) -> dict[str, dict[str, Any]]:
    if not admitted:
        return {}
    strongest = max(admitted, key=lambda item: float(item.candidate.verified_success_probability or 0.0))
    cheapest = min(
        admitted,
        key=lambda item: (
            item.candidate.mean_cost_usd is None,
            item.candidate.mean_cost_usd if item.candidate.mean_cost_usd is not None else float("inf"),
        ),
    )
    static = admitted[0]
    baseline_policy = ShadowRoutingPolicy()
    return {
        "static_priority": _direct_option(static, baseline_policy).to_dict(),
        "strongest_only": _direct_option(strongest, baseline_policy).to_dict(),
        "cheapest_only": _direct_option(cheapest, baseline_policy).to_dict(),
    }


def evaluate_shadow_route(
    *,
    context: TaskContext,
    path_resolution: Mapping[str, Any],
    policy: ShadowRoutingPolicy | None = None,
    created_at: float | None = None,
) -> ShadowRouteResult:
    """Evaluate a route in shadow mode without executing it."""
    policy = policy or ShadowRoutingPolicy()
    created = time.time() if created_at is None else float(created_at)
    graph_digest = str(path_resolution.get("graph_digest") or _context_value(context, "capability_graph_digest", ""))
    path_digest = str(path_resolution.get("path_digest") or "")
    denial: list[str] = []
    if path_resolution.get("status") == DENIED or path_resolution.get("ok") is False:
        denial.extend(str(item) for item in path_resolution.get("errors", []) or [])
    if not graph_digest or graph_digest != str(_context_value(context, "capability_graph_digest", "")):
        denial.append("capability graph digest is missing or stale")
    if not path_digest:
        denial.append("capability path digest is missing")
    unresolved = _tuple_strings(path_resolution.get("unresolved_execution_capability_ids"))
    if unresolved:
        denial.append("execution class unresolved: " + ", ".join(unresolved))
    required_path = _tuple_strings(path_resolution.get("required_capability_ids"))
    context_required = _tuple_strings(_context_value(context, "required_capability_ids", ()))
    if not required_path or required_path != context_required:
        denial.append("resolved capability path does not match TaskContext")
    if _tuple_strings(_context_value(context, "capability_path", ())) != required_path:
        denial.append("TaskContext capability path is missing or mismatched")
    model_capability_ids = _tuple_strings(path_resolution.get("model_dependent_capability_ids"))
    if not set(model_capability_ids).issubset(set(required_path)):
        denial.append("model-dependent capability IDs are outside the admitted path")
    zero_model = path_resolution.get("zero_model", {}) or {}
    zero_eligible = bool(zero_model.get("eligible"))
    if zero_eligible and model_capability_ids:
        denial.append("ZERO_MODEL cannot include model-dependent capabilities")
    if not zero_eligible and not model_capability_ids:
        denial.append("non-zero route has no model-dependent capability IDs")
    if denial:
        return ShadowRouteResult(
            status=DENIED,
            route_decision=None,
            selected_option=None,
            options=(),
            candidate_assessments=(),
            baseline_comparisons={},
            denial_reasons=tuple(dict.fromkeys(denial)),
            graph_digest=graph_digest,
            path_digest=path_digest,
            created_at=created,
        )

    if zero_eligible:
        option = PolicyOption(
            policy_mode=ZERO_MODEL,
            profile_ids=(),
            expected_success=1.0,
            expected_cost_usd=0.0,
            expected_time_to_verified_ms=0.0,
            expected_repair_burden=0.0,
            expected_scope_violation_rate=0.0,
            expected_drift=0.0,
            expected_energy_joules=0.0,
            utility=policy.quality_weight,
            explanation=("all admitted capabilities are deterministic and locally grounded",),
        )
        evidence_digest = stable_digest(
            {"context_id": context.task_context_id, "graph_digest": graph_digest, "path_digest": path_digest, "selected": option.to_dict()}
        )
        decision = RouteDecision.create(
            task_context_id=context.task_context_id,
            purpose_digest=context.purpose_digest,
            policy_mode=ZERO_MODEL,
            policy_version=policy.policy_version,
            selected_profile_ids=(),
            admitted_profile_ids=(),
            predicted_verified_success=1.0,
            expected_cost_usd=0.0,
            expected_time_to_verified_ms=0.0,
            capability_graph_digest=graph_digest,
            knowledge_snapshot_digest=evidence_digest,
            created_at=created,
        ).to_dict()
        decision.update({"shadow_only": True, "proposal_only": True, "path_digest": path_digest, "policy_evidence_digest": evidence_digest})
        return ShadowRouteResult(
            status="PROPOSED",
            route_decision=decision,
            selected_option=option,
            options=(option,),
            candidate_assessments=(),
            baseline_comparisons={},
            denial_reasons=(),
            graph_digest=graph_digest,
            path_digest=path_digest,
            created_at=created,
        )

    consequential = _risk_class(context) in _HIGH_RISK or bool(_context_value(context, "exactness_required", ""))
    assessments: list[CandidateAssessment] = []
    for raw in path_resolution.get("model_candidates", []) or []:
        try:
            evidence = CandidateEvidence.from_mapping(raw)
            assessments.append(
                _assess_candidate(
                    evidence,
                    context=context,
                    graph_digest=graph_digest,
                    model_capability_ids=model_capability_ids,
                    consequential=consequential,
                    policy=policy,
                )
            )
        except (TypeError, ValueError) as exc:
            profile_id = str(raw.get("profile_id", "invalid")) if isinstance(raw, Mapping) else "invalid"
            invalid = CandidateEvidence(
                profile_id=profile_id,
                provider="unknown",
                model="unknown",
                endpoint_status="INVALID",
                access_class="BLACK_BOX",
                capability_ids=(),
                capability_graph_digest="",
                evidence_split="",
                verified_success_probability=None,
                mean_cost_usd=None,
                mean_time_to_verified_ms=None,
                mean_repair_attempts=None,
                scope_violation_rate=None,
                drift_score=None,
                energy_joules=None,
                uncertainty=None,
                context_window=None,
                supported_tools=(),
                evidence_count=0,
                evidence_digest="",
                raw=dict(raw) if isinstance(raw, Mapping) else {},
            )
            assessments.append(CandidateAssessment(invalid, False, (f"invalid candidate evidence: {exc}",), None))

    admitted_in_input_order = [item for item in assessments if item.admitted]
    admitted = sorted(
        admitted_in_input_order,
        key=lambda item: (-float(item.utility or -float("inf")), item.candidate.profile_id),
    )
    if not admitted:
        return ShadowRouteResult(
            status=DENIED,
            route_decision=None,
            selected_option=None,
            options=(),
            candidate_assessments=tuple(assessments),
            baseline_comparisons={},
            denial_reasons=("no candidate passed all hard admission gates",),
            graph_digest=graph_digest,
            path_digest=path_digest,
            created_at=created,
        )

    options: list[PolicyOption] = [_direct_option(item, policy) for item in admitted]
    direct = options[0]
    if policy.allow_cascade and len(admitted) >= 2:
        fallback = max(admitted[1:], key=lambda item: float(item.candidate.verified_success_probability or 0.0))
        cheap_candidates = sorted(
            admitted,
            key=lambda item: (
                item.candidate.mean_cost_usd is None,
                item.candidate.mean_cost_usd if item.candidate.mean_cost_usd is not None else float("inf"),
                -float(item.candidate.verified_success_probability or 0.0),
            ),
        )
        primary = next((item for item in cheap_candidates if item.candidate.profile_id != fallback.candidate.profile_id), None)
        if primary is not None:
            cascade = _cascade_option(primary, fallback, policy)
            if cascade is not None and _fits_budgets(cascade, context):
                options.append(cascade)

    high_risk = _risk_class(context) in _HIGH_RISK
    panel_pool = admitted
    if high_risk:
        panel_pool = []
        seen_providers: set[str] = set()
        for item in admitted:
            provider = item.candidate.provider.lower()
            if provider in seen_providers:
                continue
            seen_providers.add(provider)
            panel_pool.append(item)
    panel = None
    if policy.allow_panel and len(panel_pool) >= 2:
        panel = _panel_option(panel_pool, policy)
        if panel is not None and _fits_budgets(panel, context):
            options.append(panel)

    selected = direct
    best_uncertainty = admitted[0].candidate.uncertainty
    needs_panel = high_risk and (
        direct.expected_success < policy.high_risk_direct_min_success
        or best_uncertainty is None
        or best_uncertainty >= policy.panel_uncertainty_threshold
    )
    if needs_panel:
        if panel is None or panel not in options:
            return ShadowRouteResult(
                status=DENIED,
                route_decision=None,
                selected_option=None,
                options=tuple(options),
                candidate_assessments=tuple(assessments),
                baseline_comparisons=_baselines(admitted_in_input_order),
                denial_reasons=("high-risk route requires a diverse admitted panel",),
                graph_digest=graph_digest,
                path_digest=path_digest,
                created_at=created,
            )
        selected = panel
    else:
        cascade_options = [option for option in options if option.policy_mode == CASCADE]
        if cascade_options:
            best_cascade = max(cascade_options, key=lambda option: option.utility)
            if best_cascade.utility >= direct.utility + policy.cascade_min_gain:
                selected = best_cascade

    selected_uncertainties = [
        item.candidate.uncertainty
        for item in admitted
        if item.candidate.profile_id in selected.profile_ids and item.candidate.uncertainty is not None
    ]
    evidence_digest = stable_digest(
        {
            "context_id": context.task_context_id,
            "graph_digest": graph_digest,
            "path_digest": path_digest,
            "selected": selected.to_dict(),
            "candidates": [item.to_dict() for item in assessments],
            "policy": asdict(policy),
        }
    )
    decision = RouteDecision.create(
        task_context_id=context.task_context_id,
        purpose_digest=context.purpose_digest,
        policy_mode=selected.policy_mode,
        policy_version=policy.policy_version,
        selected_profile_ids=selected.profile_ids,
        admitted_profile_ids=tuple(item.candidate.profile_id for item in admitted),
        predicted_verified_success=selected.expected_success,
        expected_cost_usd=selected.expected_cost_usd,
        expected_time_to_verified_ms=selected.expected_time_to_verified_ms,
        uncertainty_score=max(selected_uncertainties) if selected_uncertainties else None,
        capability_graph_digest=graph_digest,
        knowledge_snapshot_digest=evidence_digest,
        created_at=created,
    ).to_dict()
    decision.update(
        {
            "shadow_only": True,
            "proposal_only": True,
            "path_digest": path_digest,
            "policy_evidence_digest": evidence_digest,
        }
    )
    return ShadowRouteResult(
        status="PROPOSED",
        route_decision=decision,
        selected_option=selected,
        options=tuple(options),
        candidate_assessments=tuple(assessments),
        baseline_comparisons=_baselines(admitted_in_input_order),
        denial_reasons=(),
        graph_digest=graph_digest,
        path_digest=path_digest,
        created_at=created,
    )


def compare_shadow_to_baselines(result: ShadowRouteResult) -> dict[str, Any]:
    """Compare the selected shadow policy with simple non-adaptive baselines."""
    selected = result.selected_option
    if selected is None:
        return {
            "ok": False,
            "reason": "no shadow route was proposed",
            "version": SHADOW_ROUTER_VERSION,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    comparisons: dict[str, Any] = {}
    for name, baseline in result.baseline_comparisons.items():
        comparisons[name] = {
            "utility_delta": round(selected.utility - float(baseline["utility"]), 8),
            "success_delta": round(selected.expected_success - float(baseline["expected_success"]), 8),
            "cost_delta_usd": (
                round(selected.expected_cost_usd - float(baseline["expected_cost_usd"]), 8)
                if selected.expected_cost_usd is not None and baseline.get("expected_cost_usd") is not None
                else None
            ),
            "time_to_verified_delta_ms": (
                round(selected.expected_time_to_verified_ms - float(baseline["expected_time_to_verified_ms"]), 8)
                if selected.expected_time_to_verified_ms is not None
                and baseline.get("expected_time_to_verified_ms") is not None
                else None
            ),
        }
    return {
        "ok": True,
        "selected_policy_mode": selected.policy_mode,
        "comparisons": comparisons,
        "shadow_only": True,
        "proposal_only": True,
        "version": SHADOW_ROUTER_VERSION,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
