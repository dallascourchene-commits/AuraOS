from __future__ import annotations

from pathlib import Path
import math
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def replace_between(text: str, start: str, end: str, replacement: str) -> str:
    left = text.find(start)
    if left < 0:
        raise RuntimeError(f"missing start marker: {start!r}")
    right = text.find(end, left)
    if right < 0:
        raise RuntimeError(f"missing end marker: {end!r}")
    return text[:left] + replacement + text[right:]


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


records_path = ROOT / "aura_model_cognome_store_records.py"
records = records_path.read_text(encoding="utf-8")
query_start = records.index("    def query_candidates(self, context: TaskContext) -> list[dict[str, Any]]:")
records = records[:query_start] + '''    def query_candidates(self, context: TaskContext) -> list[dict[str, Any]]:
        """Return verifier-backed, graph-pinned routing evidence for complete paths.

        Endpoint identity alone is never a routing candidate. Every returned row
        supports every required capability on the current graph and carries the
        weakest-link edge evidence plus an optional VALIDATION/SHADOW posterior.
        """
        required = tuple(dict.fromkeys(str(item) for item in context.required_capability_ids))
        if not required or not context.capability_graph_digest:
            return []
        task = str(context.task_family or context.domain or "ANY")
        bucket = context_bucket(int(context.context_tokens))
        marks = ",".join("?" for _ in required)
        profile_rows = self._conn.execute(
            f"""SELECT e.profile_id,e.record_json,COUNT(DISTINCT m.aura_capability_id) supported
            FROM model_endpoints e JOIN model_capability_edges m ON m.profile_id=e.profile_id
            WHERE e.status='ACTIVE' AND m.status='VALIDATED' AND m.evidence_count>0
              AND m.evidence_digest<>'' AND m.last_validated_at>0
              AND m.aura_capability_id IN ({marks})
              AND m.task_bucket IN (?, '*', 'ANY')
              AND m.capability_graph_digest=?
            GROUP BY e.profile_id,e.record_json HAVING supported=?
            ORDER BY e.provider,e.returned_model""",
            (*required, task, context.capability_graph_digest, len(required)),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for profile_row in profile_rows:
            profile_id = str(profile_row[0])
            endpoint = json.loads(profile_row[1])
            edge_rows = self._conn.execute(
                f"""SELECT record_json FROM model_capability_edges
                WHERE profile_id=? AND status='VALIDATED' AND evidence_count>0
                  AND evidence_digest<>'' AND last_validated_at>0
                  AND aura_capability_id IN ({marks})
                  AND task_bucket IN (?, '*', 'ANY')
                  AND capability_graph_digest=?
                ORDER BY aura_capability_id,task_bucket""",
                (profile_id, *required, task, context.capability_graph_digest),
            ).fetchall()
            edges = [json.loads(row[0]) for row in edge_rows]
            supported = {str(edge.get("aura_capability_id", "")) for edge in edges}
            if not set(required).issubset(supported):
                continue

            posterior: dict[str, Any] | None = None
            if context.verifier_id:
                posterior_row = self._conn.execute(
                    """SELECT record_json FROM capability_posteriors
                    WHERE profile_id=? AND task_bucket IN (?, '*', 'ANY')
                      AND context_bucket=? AND verifier_id=?
                      AND validation_split IN ('SHADOW','VALIDATION')
                      AND status='VALIDATED' AND sample_count>0 AND evidence_digest<>''
                    ORDER BY CASE validation_split WHEN 'SHADOW' THEN 0 ELSE 1 END,
                             CASE task_bucket WHEN ? THEN 0 ELSE 1 END,
                             last_validated_at DESC LIMIT 1""",
                    (profile_id, task, bucket, context.verifier_id, task),
                ).fetchone()
                if posterior_row is not None:
                    posterior = json.loads(posterior_row[0])

            def complete_values(name: str) -> list[float]:
                values = [edge.get(name) for edge in edges]
                if not values or any(value is None for value in values):
                    return []
                return [float(value) for value in values]

            edge_success = complete_values("verified_success_probability")
            edge_costs = complete_values("mean_cost_usd")
            edge_times = complete_values("p50_time_to_verified_ms")
            success = min(edge_success) if edge_success else None
            cost = max(edge_costs) if edge_costs else None
            verified_time = max(edge_times) if edge_times else None
            repair = None
            scope_rate = None
            uncertainty = None
            evidence_split = "VALIDATED_EDGE"
            if posterior is not None:
                success = posterior.get("verified_success_mean", success)
                cost = posterior.get("mean_cost_usd") if posterior.get("mean_cost_usd") is not None else cost
                verified_time = (
                    posterior.get("mean_time_to_verified_ms")
                    if posterior.get("mean_time_to_verified_ms") is not None
                    else verified_time
                )
                repair = posterior.get("mean_repair_attempts")
                scope_rate = posterior.get("scope_violation_rate")
                evidence_split = str(posterior.get("validation_split") or "")
                uncertainty_values: list[float] = []
                if posterior.get("calibration_error") is not None:
                    uncertainty_values.append(float(posterior["calibration_error"]))
                alpha = float(posterior.get("verified_success_alpha") or 0.0)
                beta = float(posterior.get("verified_success_beta") or 0.0)
                denominator = alpha + beta
                if alpha > 0 and beta > 0 and denominator > 0:
                    variance = alpha * beta / (denominator * denominator * (denominator + 1.0))
                    uncertainty_values.append(math.sqrt(variance))
                uncertainty = max(uncertainty_values) if uncertainty_values else None

            edge_counts = [int(edge.get("evidence_count") or 0) for edge in edges]
            evidence_count = min(edge_counts) if edge_counts else 0
            if posterior is not None:
                evidence_count = min(evidence_count, int(posterior.get("sample_count") or 0))
            evidence_digest = stable_digest(
                {
                    "profile_id": profile_id,
                    "graph_digest": context.capability_graph_digest,
                    "required": required,
                    "edges": [
                        {
                            "edge_id": edge.get("edge_id"),
                            "capability_id": edge.get("aura_capability_id"),
                            "evidence_digest": edge.get("evidence_digest"),
                            "last_validated_at": edge.get("last_validated_at"),
                        }
                        for edge in edges
                    ],
                    "posterior": (
                        {
                            "split": posterior.get("validation_split"),
                            "evidence_digest": posterior.get("evidence_digest"),
                            "last_validated_at": posterior.get("last_validated_at"),
                        }
                        if posterior
                        else None
                    ),
                }
            )
            drift_row = self._conn.execute(
                "SELECT drift_score FROM endpoint_fingerprints WHERE profile_id=? "
                "ORDER BY observed_at DESC LIMIT 1",
                (profile_id,),
            ).fetchone()
            endpoint.update(
                {
                    "capability_ids": list(required),
                    "verified_success_probability": success,
                    "mean_cost_usd": cost,
                    "mean_time_to_verified_ms": verified_time,
                    "mean_repair_attempts": repair,
                    "scope_violation_rate": scope_rate,
                    "endpoint_drift_score": drift_row[0] if drift_row is not None else None,
                    "uncertainty": uncertainty,
                    "evidence_count": evidence_count,
                    "evidence_digest": evidence_digest,
                    "evidence_split": evidence_split,
                    "capability_graph_digest": context.capability_graph_digest,
                    "context_bucket": bucket,
                    "task_bucket": task,
                    "supported_tools": list(endpoint.get("supported_tools", [])),
                    "context_window": endpoint.get("context_window"),
                }
            )
            candidates.append(endpoint)
        return sorted(candidates, key=lambda item: (str(item.get("provider")), str(item.get("returned_model"))))
'''
records_path.write_text(records, encoding="utf-8")

router_path = ROOT / "aura_shadow_model_router.py"
router = router_path.read_text(encoding="utf-8")
router = router.replace(
    'SHADOW_ROUTER_VERSION = "AURA_SHADOW_MODEL_ROUTER_V1"',
    'SHADOW_ROUTER_VERSION = "AURA_SHADOW_MODEL_ROUTER_V2"',
)
new_candidate = '''@dataclass(frozen=True)
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


'''
router = replace_between(
    router,
    "@dataclass(frozen=True)\nclass CandidateEvidence:",
    "@dataclass(frozen=True)\nclass CandidateAssessment:",
    new_candidate,
)
new_assess = '''def _assess_candidate(
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


'''
router = replace_between(router, "def _assess_candidate(", "def _direct_option(", new_assess)
router = router.replace(
    'explanation=("independent model evidence is combined only as a shadow proposal",),',
    'explanation=("optimistic independence surrogate; shadow proposal only",),',
)
new_evaluate = '''def evaluate_shadow_route(
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


'''
router = replace_between(router, "def evaluate_shadow_route(", "def compare_shadow_to_baselines(", new_evaluate)
router_path.write_text(router, encoding="utf-8")

tests = r'''from __future__ import annotations

import ast
import inspect
from pathlib import Path

from aura_model_cognome import (
    CapabilityPosterior,
    ModelCapabilityEdge,
    ModelEndpointIdentity,
    TaskContext,
)
from aura_model_cognome_store import ModelCognomeStore
import aura_shadow_model_router as shadow
from aura_shadow_model_router import (
    DENIED,
    DIRECT,
    PANEL,
    ZERO_MODEL,
    ShadowRoutingPolicy,
    compare_shadow_to_baselines,
    evaluate_shadow_route,
)


def context(*, risk: str = "LOW", egress: bool = True, tools: tuple[str, ...] = (), tokens: int = 0) -> TaskContext:
    return TaskContext.create(
        objective="repair governed routing",
        purpose_digest="purpose-1",
        task_family="coding",
        risk=risk,
        verifier_id="pytest",
        required_tools=tools,
        context_tokens=tokens,
        required_capability_ids=("cap-a",),
        capability_path=("cap-a",),
        capability_graph_digest="graph-1",
        data_egress_allowed=egress,
    )


def candidate(
    profile_id: str = "profile-a",
    *,
    provider: str = "fireworks",
    success: float = 0.92,
    uncertainty: float | None = 0.05,
    capabilities: tuple[str, ...] = ("cap-a",),
    graph: str = "graph-1",
    tools: tuple[str, ...] = (),
    context_window: int | None = 4096,
) -> dict:
    return {
        "profile_id": profile_id,
        "provider": provider,
        "returned_model": f"{provider}-model",
        "status": "ACTIVE",
        "access_class": "BLACK_BOX",
        "capability_ids": list(capabilities),
        "capability_graph_digest": graph,
        "evidence_split": "SHADOW",
        "verified_success_probability": success,
        "mean_cost_usd": 0.02,
        "mean_time_to_verified_ms": 100.0,
        "mean_repair_attempts": 0.1,
        "scope_violation_rate": 0.0,
        "endpoint_drift_score": 0.0,
        "uncertainty": uncertainty,
        "context_window": context_window,
        "supported_tools": list(tools),
        "evidence_count": 10,
        "evidence_digest": f"evidence-{profile_id}",
    }


def resolution(ctx: TaskContext, candidates: list[dict] | None = None, *, zero: bool = False) -> dict:
    return {
        "ok": True,
        "status": "ADMITTED",
        "graph_digest": ctx.capability_graph_digest,
        "path_digest": "path-1",
        "required_capability_ids": list(ctx.required_capability_ids),
        "model_dependent_capability_ids": [] if zero else ["cap-a"],
        "unresolved_execution_capability_ids": [],
        "zero_model": {"eligible": zero},
        "model_candidates": candidates or [],
    }


def test_store_projects_complete_graph_pinned_candidate(tmp_path: Path) -> None:
    endpoint = ModelEndpointIdentity.create(
        provider="fireworks",
        requested_model="model-a",
        first_seen_at=1.0,
        last_seen_at=1.0,
    )
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        store.upsert_endpoint(endpoint)
        for cap, success, cost, latency in (
            ("cap-a", 0.90, 0.02, 100.0),
            ("cap-b", 0.80, 0.03, 120.0),
        ):
            store.upsert_model_capability_edge(
                ModelCapabilityEdge.create(
                    profile_id=endpoint.profile_id,
                    aura_capability_id=cap,
                    task_bucket="coding",
                    support_level="SUPPORTED",
                    verified_success_probability=success,
                    p50_time_to_verified_ms=latency,
                    p95_time_to_verified_ms=latency + 50,
                    mean_cost_usd=cost,
                    evidence_count=12,
                    evidence_digest=f"edge-{cap}",
                    capability_graph_digest="graph-1",
                    last_validated_at=2.0,
                    status="VALIDATED",
                )
            )
        store.upsert_capability_posterior(
            CapabilityPosterior(
                profile_id=endpoint.profile_id,
                task_bucket="coding",
                context_bucket="small",
                verifier_id="pytest",
                validation_split="SHADOW",
                sample_count=8,
                verified_success_alpha=8.0,
                verified_success_beta=2.0,
                mean_cost_usd=0.025,
                mean_time_to_verified_ms=110.0,
                mean_repair_attempts=0.2,
                scope_violation_rate=0.0,
                calibration_error=0.04,
                last_validated_at=3.0,
                evidence_digest="posterior-shadow",
                status="VALIDATED",
            )
        )
        ctx = TaskContext.create(
            objective="two capabilities",
            purpose_digest="purpose",
            task_family="coding",
            verifier_id="pytest",
            required_capability_ids=("cap-a", "cap-b"),
            capability_path=("cap-a", "cap-b"),
            capability_graph_digest="graph-1",
            data_egress_allowed=True,
        )
        rows = store.query_candidates(ctx)
    assert len(rows) == 1
    row = rows[0]
    assert row["capability_ids"] == ["cap-a", "cap-b"]
    assert row["capability_graph_digest"] == "graph-1"
    assert row["evidence_split"] == "SHADOW"
    assert row["evidence_count"] == 8
    assert row["verified_success_probability"] == 0.8
    assert row["mean_cost_usd"] == 0.025
    assert row["mean_time_to_verified_ms"] == 110.0
    assert row["evidence_digest"]


def test_store_does_not_admit_partial_capability_support(tmp_path: Path) -> None:
    endpoint = ModelEndpointIdentity.create(provider="local", requested_model="local-a", first_seen_at=1, last_seen_at=1)
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        store.upsert_endpoint(endpoint)
        store.upsert_model_capability_edge(
            ModelCapabilityEdge.create(
                profile_id=endpoint.profile_id,
                aura_capability_id="cap-a",
                task_bucket="coding",
                support_level="SUPPORTED",
                verified_success_probability=0.9,
                evidence_count=2,
                evidence_digest="edge",
                capability_graph_digest="graph-1",
                last_validated_at=2,
                status="VALIDATED",
            )
        )
        ctx = TaskContext.create(
            objective="needs two",
            purpose_digest="purpose",
            task_family="coding",
            required_capability_ids=("cap-a", "cap-b"),
            capability_path=("cap-a", "cap-b"),
            capability_graph_digest="graph-1",
        )
        assert store.query_candidates(ctx) == []


def test_zero_model_proposal_is_graph_and_path_bound() -> None:
    ctx = context()
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, zero=True), created_at=1.0)
    assert result.status == "PROPOSED"
    assert result.selected_option.policy_mode == ZERO_MODEL
    assert result.route_decision["proposal_only"] is True
    assert result.route_decision["capability_graph_digest"] == "graph-1"
    assert result.route_decision["path_digest"] == "path-1"


def test_missing_path_digest_fails_closed() -> None:
    ctx = context()
    packet = resolution(ctx, [candidate()])
    packet["path_digest"] = ""
    result = evaluate_shadow_route(context=ctx, path_resolution=packet)
    assert result.status == DENIED
    assert "capability path digest is missing" in result.denial_reasons


def test_missing_candidate_capability_support_fails_closed() -> None:
    ctx = context()
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, [candidate(capabilities=())]))
    assert result.status == DENIED
    assert "missing validated capability support: cap-a" in result.candidate_assessments[0].rejection_reasons


def test_stale_candidate_graph_fails_closed() -> None:
    ctx = context()
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, [candidate(graph="old-graph")]))
    assert result.status == DENIED
    assert "candidate capability evidence is stale or graph-unbound" in result.candidate_assessments[0].rejection_reasons


def test_training_only_evidence_fails_closed() -> None:
    ctx = context()
    row = candidate()
    row["evidence_split"] = "TRAIN"
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, [row]))
    assert result.status == DENIED
    assert "candidate evidence is not validation/shadow isolated" in result.candidate_assessments[0].rejection_reasons


def test_low_risk_direct_route_is_proposal_only() -> None:
    ctx = context()
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, [candidate()]), created_at=2.0)
    assert result.status == "PROPOSED"
    assert result.selected_option.policy_mode == DIRECT
    assert result.route_decision["selected_profile_ids"] == ["profile-a"]
    assert result.route_decision["proposal_only"] is True
    assert result.route_decision["shadow_only"] is True


def test_high_risk_underqualified_direct_route_is_denied() -> None:
    ctx = context(risk="CRITICAL")
    result = evaluate_shadow_route(
        context=ctx,
        path_resolution=resolution(ctx, [candidate(success=0.70, uncertainty=0.30)]),
    )
    assert result.status == DENIED
    assert result.denial_reasons == ("high-risk route requires a diverse admitted panel",)


def test_high_risk_route_uses_provider_diverse_panel() -> None:
    ctx = context(risk="HIGH")
    rows = [
        candidate("p1", provider="fireworks", success=0.80, uncertainty=0.25),
        candidate("p2", provider="anthropic", success=0.82, uncertainty=0.20),
    ]
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, rows))
    assert result.status == "PROPOSED"
    assert result.selected_option.policy_mode == PANEL
    assert set(result.selected_option.profile_ids) == {"p1", "p2"}


def test_required_tools_context_and_egress_are_hard_gates() -> None:
    tool_ctx = context(tools=("code_exec",))
    tool_result = evaluate_shadow_route(context=tool_ctx, path_resolution=resolution(tool_ctx, [candidate()]))
    assert tool_result.status == DENIED
    assert "required tools are unsupported" in tool_result.candidate_assessments[0].rejection_reasons

    context_ctx = context(tokens=5000)
    context_result = evaluate_shadow_route(
        context=context_ctx,
        path_resolution=resolution(context_ctx, [candidate(context_window=1024)]),
    )
    assert context_result.status == DENIED
    assert "context window is insufficient" in context_result.candidate_assessments[0].rejection_reasons

    private_ctx = context(egress=False)
    remote_result = evaluate_shadow_route(context=private_ctx, path_resolution=resolution(private_ctx, [candidate()]))
    assert remote_result.status == DENIED
    local_result = evaluate_shadow_route(
        context=private_ctx,
        path_resolution=resolution(private_ctx, [candidate(provider="local")]),
    )
    assert local_result.status == "PROPOSED"


def test_baseline_comparison_and_no_execution_surface() -> None:
    ctx = context()
    rows = [candidate("static", success=0.75), candidate("best", provider="anthropic", success=0.95)]
    result = evaluate_shadow_route(context=ctx, path_resolution=resolution(ctx, rows))
    comparison = compare_shadow_to_baselines(result)
    assert comparison["ok"] is True
    assert set(comparison["comparisons"]) == {"static_priority", "strongest_only", "cheapest_only"}

    source = inspect.getsource(shadow)
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    assert not {"aura_llm_egress", "requests", "httpx", "aiohttp"}.intersection(imported)
    assert "ExternalLLM" not in source
    assert "subprocess" not in source
'''
(ROOT / "tests/test_aura_shadow_model_router.py").write_text(tests, encoding="utf-8")

workflow = '''name: Model Cognome Governed Routing

on:
  pull_request:
    paths:
      - "aura_model_cognome*.py"
      - "aura_shadow_model_router.py"
      - "aura_empirical_cost_ledger.py"
      - "aura_usage_normalizer.py"
      - "aura_pricing_registry.py"
      - "tests/test_aura_model_cognome*.py"
      - "tests/test_aura_empirical_cost_ledger_v2.py"
      - "tests/test_aura_shadow_model_router.py"
      - ".github/workflows/model-cognome-governed-routing.yml"
  workflow_dispatch:

permissions:
  contents: read

jobs:
  governed-routing:
    name: Governed routing contracts (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    timeout-minutes: 35
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha || github.sha }}
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install tooling
        run: python -m pip install pytest ruff
      - name: Compile governed modules
        run: |
          python -m py_compile \
            aura_model_cognome.py \
            aura_model_cognome_store.py \
            aura_model_cognome_store_records.py \
            aura_model_cognome_telemetry.py \
            aura_model_cognome_call_logger.py \
            aura_empirical_cost_ledger.py \
            aura_shadow_model_router.py
      - name: Fatal lint checks
        run: |
          ruff check --select E9,F63,F7,F82 \
            aura_model_cognome.py \
            aura_model_cognome_store.py \
            aura_model_cognome_store_records.py \
            aura_model_cognome_telemetry.py \
            aura_model_cognome_call_logger.py \
            aura_empirical_cost_ledger.py \
            aura_shadow_model_router.py \
            tests/test_aura_model_cognome_telemetry.py \
            tests/test_aura_model_cognome_telemetry_integration.py \
            tests/test_aura_model_cognome_call_logger.py \
            tests/test_aura_empirical_cost_ledger_v2.py \
            tests/test_aura_shadow_model_router.py
      - name: Run governed routing contracts
        run: |
          python -m pytest -q \
            tests/test_aura_model_cognome.py \
            tests/test_aura_model_cognome_store.py \
            tests/test_aura_model_cognome_telemetry.py \
            tests/test_aura_model_cognome_telemetry_integration.py \
            tests/test_aura_model_cognome_call_logger.py \
            tests/test_aura_empirical_cost_ledger_v2.py \
            tests/test_aura_shadow_model_router.py
'''
workflow_path = ROOT / ".github/workflows/model-cognome-governed-routing.yml"
workflow_path.write_text(workflow, encoding="utf-8")

run("python", "-m", "py_compile", "aura_model_cognome_store_records.py", "aura_shadow_model_router.py")
run("ruff", "check", "--select", "E9,F63,F7,F82", "aura_model_cognome_store_records.py", "aura_shadow_model_router.py", "tests/test_aura_shadow_model_router.py")
run(
    "python",
    "-m",
    "pytest",
    "-q",
    "tests/test_aura_model_cognome.py",
    "tests/test_aura_model_cognome_store.py",
    "tests/test_aura_model_cognome_telemetry.py",
    "tests/test_aura_model_cognome_telemetry_integration.py",
    "tests/test_aura_model_cognome_call_logger.py",
    "tests/test_aura_empirical_cost_ledger_v2.py",
    "tests/test_aura_shadow_model_router.py",
)

for path in (
    ROOT / ".github/workflows/finalize-governed-routing-once.yml",
    ROOT / "tools/one_time_finalize_governed_routing.py",
):
    path.unlink(missing_ok=True)

run("python", "aura_codebase_navigator.py")
first = ROOT / ".aura/CODEMAP.json"
copy = ROOT / ".aura/CODEMAP.finalizer-first.json"
shutil.copy2(first, copy)
run("python", "aura_codebase_navigator.py")
run("python", "-m", "aura_codemap_verify", "--compare-json", str(copy))
copy.unlink(missing_ok=True)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", "-A")
subprocess.run(["git", "commit", "--no-verify", "-m", "refactor(cognome): finalize telemetry and shadow routing"], cwd=ROOT, check=True)
report = ROOT / "finalizer-report"
report.mkdir(exist_ok=True)
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
(report / "commit_sha.txt").write_text(sha + "\n", encoding="utf-8")
run("git", "push", "origin", "HEAD:refs/heads/refactor/model-cognome-governed-routing")
