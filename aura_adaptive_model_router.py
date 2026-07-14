"""Topology-grounded adaptive route planner for Aura's Model Cognome.

The planner never calls a provider.  It composes the dynamic AI context router,
Capability Resolver V2, Connectome bridge, Cognome candidate query, and the
existing governed shadow policy evaluator.  Execution is delegated lazily to
``aura_adaptive_model_executor`` and remains authorization-gated.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

from aura_model_cognome import RouteDecision, TaskContext, stable_digest
from aura_model_connectome_bridge import resolve_candidates_for_path, task_context_from_path
from aura_shadow_model_router import (
    DENIED,
    DIRECT,
    PANEL,
    CandidateAssessment,
    PolicyOption,
    ShadowRoutingPolicy,
    evaluate_shadow_route,
)

ADAPTIVE_ROUTER_VERSION = "AURA_ADAPTIVE_MODEL_ROUTER_V1"
LEGACY = "LEGACY"
SHADOW = "SHADOW"
PAIRED_LIVE = "PAIRED_LIVE"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_HIGH_RISK = frozenset({"HIGH", "CRITICAL", "CONSEQUENTIAL"})


class CognomeRouterStore(Protocol):
    def record_task_context(self, context: TaskContext) -> str: ...
    def record_route_decision(self, decision: RouteDecision) -> str: ...
    def get_endpoint(self, profile_id: str) -> dict[str, Any] | None: ...
    def query_candidates(self, context: TaskContext) -> list[dict[str, Any]]: ...


@dataclass(frozen=True)
class PlannedRoute:
    context: TaskContext
    decision: RouteDecision
    selected_option: PolicyOption
    assessments: tuple[CandidateAssessment, ...]
    payload: dict[str, Any]


def _source_line_count(routing: Mapping[str, Any]) -> int:
    total = 0
    for span in (routing.get("context_packet", {}) or {}).get("source_spans", []) or []:
        try:
            total += max(0, int(span.get("end_line", 0)) - int(span.get("start_line", 0)) + 1)
        except (TypeError, ValueError):
            continue
    return total


def _candidate_matches(assessment: CandidateAssessment, token: str) -> bool:
    query = str(token or "").strip().lower()
    candidate = assessment.candidate
    aliases = {
        candidate.profile_id.lower(),
        candidate.provider.lower(),
        candidate.model.lower(),
        f"{candidate.provider}:{candidate.model}".lower(),
    }
    return query in aliases


def _forced_direct(assessment: CandidateAssessment) -> PolicyOption:
    candidate = assessment.candidate
    if not assessment.admitted or assessment.utility is None:
        raise ValueError("forced candidate is not admitted")
    if candidate.verified_success_probability is None:
        raise ValueError("forced candidate lacks verified-success evidence")
    return PolicyOption(
        policy_mode=DIRECT,
        profile_ids=(candidate.profile_id,),
        expected_success=float(candidate.verified_success_probability),
        expected_cost_usd=candidate.mean_cost_usd,
        expected_time_to_verified_ms=candidate.mean_time_to_verified_ms,
        expected_repair_burden=float(candidate.mean_repair_attempts or 0.0),
        expected_scope_violation_rate=float(candidate.scope_violation_rate or 0.0),
        expected_drift=float(candidate.drift_score or 0.0),
        expected_energy_joules=candidate.energy_joules,
        utility=float(assessment.utility),
        explanation=("explicit human forced-model override after all hard admission gates",),
    )


def _rejected(assessments: Sequence[CandidateAssessment]) -> dict[str, str]:
    return {
        item.candidate.profile_id: "; ".join(item.rejection_reasons)
        for item in assessments
        if not item.admitted
    }


def make_route_decision(
    *,
    context: TaskContext,
    option: PolicyOption,
    assessments: Sequence[CandidateAssessment],
    graph_digest: str,
    path_digest: str,
    policy_version: str,
    policy_evidence_digest: str,
    proposal_only: bool,
    human_override: bool,
    created_at: float,
) -> RouteDecision:
    uncertainties = [
        item.candidate.uncertainty
        for item in assessments
        if item.candidate.profile_id in option.profile_ids and item.candidate.uncertainty is not None
    ]
    return RouteDecision.create(
        task_context_id=context.task_context_id,
        purpose_digest=context.purpose_digest,
        policy_mode=option.policy_mode,
        policy_version=policy_version,
        selected_profile_ids=option.profile_ids,
        admitted_profile_ids=tuple(item.candidate.profile_id for item in assessments if item.admitted),
        rejected_candidates=_rejected(assessments),
        predicted_verified_success=option.expected_success,
        expected_cost_usd=option.expected_cost_usd,
        expected_time_to_verified_ms=option.expected_time_to_verified_ms,
        uncertainty_score=max(uncertainties) if uncertainties else None,
        capability_graph_digest=graph_digest,
        knowledge_snapshot_digest=stable_digest({
            "policy_evidence_digest": policy_evidence_digest,
            "path_digest": path_digest,
            "selected_option": option.to_dict(),
        }),
        human_override=human_override,
        proposal_only=proposal_only,
        created_at=created_at,
    )


class AdaptiveModelRouter:
    """Plan task-conditioned ZERO_MODEL/DIRECT/CASCADE/PANEL routes."""

    def __init__(
        self,
        *,
        repo_root: str | Path = ".",
        store: CognomeRouterStore | None = None,
        policy: ShadowRoutingPolicy | None = None,
        context_router: Callable[..., dict[str, Any]] | None = None,
        capability_resolver: Callable[..., dict[str, Any]] | None = None,
        now: Callable[[], float] = time.time,
        executor_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._owns_store = store is None
        if store is None:
            from aura_model_cognome_store import ModelCognomeStore

            store = ModelCognomeStore(self.repo_root)
        self.store = store
        self.policy = policy or ShadowRoutingPolicy()
        if context_router is None:
            from aura_ai_router import query_router

            context_router = query_router
        if capability_resolver is None:
            from aura_capability_resolver_v2 import resolve_capabilities

            capability_resolver = resolve_capabilities
        self.context_router = context_router
        self.capability_resolver = capability_resolver
        self.now = now
        self.executor_factory = executor_factory

    def close(self) -> None:
        if self._owns_store and hasattr(self.store, "close"):
            self.store.close()

    def __enter__(self) -> "AdaptiveModelRouter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()

    def _resolve(
        self,
        objective: str,
        *,
        target_files: list[str] | None,
        target_symbols: list[str] | None,
        token_budget: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        routing = self.context_router(
            objective,
            repo_root=self.repo_root,
            target_files=target_files,
            target_symbols=target_symbols,
            token_budget=token_budget,
        )
        resolved_files = target_files or (
            [str(routing.get("primary_file"))] if routing.get("primary_file") else None
        )
        resolved_symbols = target_symbols or list(routing.get("key_functions", []) or []) or None
        resolution = self.capability_resolver(
            objective,
            target_files=resolved_files,
            target_symbols=resolved_symbols,
            repo_root=self.repo_root,
            top_k=12,
            token_budget=token_budget,
        )
        return routing, resolution

    def plan(
        self,
        objective: str,
        *,
        purpose_digest: str,
        target_files: list[str] | None = None,
        target_symbols: list[str] | None = None,
        forced_model: str | None = None,
        task_fields: Mapping[str, Any] | None = None,
        token_budget: int = 2400,
        created_at: float | None = None,
    ) -> dict[str, Any]:
        objective_text = str(objective or "").strip()
        purpose = str(purpose_digest or "").strip()
        if not objective_text:
            raise ValueError("objective must not be empty")
        if not purpose:
            raise ValueError("purpose_digest must not be empty")
        created = self.now() if created_at is None else float(created_at)
        began = self.now()
        routing, resolution = self._resolve(
            objective_text,
            target_files=target_files,
            target_symbols=target_symbols,
            token_budget=token_budget,
        )
        path = resolution.get("capability_connectome_path", {}) or {}
        if not path.get("ok"):
            return {
                "status": DENIED,
                "executed": False,
                "execution_mode": SHADOW,
                "denial_reasons": ["capability path is unresolved"],
                "routing": routing,
                "capability_resolution": resolution,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "version": ADAPTIVE_ROUTER_VERSION,
            }

        fields = dict(task_fields or {})
        fields.setdefault("task_family", str(fields.get("domain") or "adaptive_route"))
        fields.setdefault("domain", "code" if routing.get("primary_file") else "general")
        fields.setdefault("artifact", str(routing.get("primary_file") or ""))
        fields.setdefault("action", "route_to_verified_outcome")
        fields.setdefault("risk", "LOW")
        fields.setdefault("data_egress_allowed", False)
        fields.setdefault(
            "privacy_class",
            "APPROVED_EGRESS" if fields.get("data_egress_allowed") else "PRIVATE_LOCAL",
        )
        fields.setdefault("verifier_id", "aura_adaptive_output_verifier_v1")
        fields.setdefault("context_tokens", int(routing.get("context_tokens") or 0))
        fields.setdefault("source_lines_exposed", _source_line_count(routing))
        fields.setdefault("topology_digest", str(routing.get("topology_digest") or ""))
        fields.setdefault("source_hash_digest", stable_digest(routing.get("source_hashes", {})))
        context = task_context_from_path(
            objective=objective_text,
            purpose_digest=purpose,
            path_packet=path,
            **fields,
        )
        self.store.record_task_context(context)
        path_resolution = resolve_candidates_for_path(
            self.store,
            context,
            path,
            repo_root=self.repo_root,
        )
        shadow = evaluate_shadow_route(
            context=context,
            path_resolution=path_resolution,
            policy=self.policy,
            created_at=created,
        )
        assessments = tuple(shadow.candidate_assessments)
        selected = shadow.selected_option
        override = False
        override_errors: list[str] = []
        if forced_model:
            matches = [item for item in assessments if _candidate_matches(item, forced_model)]
            if not matches:
                override_errors.append("forced model is not present in the graph-pinned candidate set")
            elif not matches[0].admitted:
                override_errors.extend(matches[0].rejection_reasons or ("forced model failed admission",))
            elif str(context.risk or "LOW").upper() in _HIGH_RISK and selected and selected.policy_mode == PANEL:
                override_errors.append("forced DIRECT override cannot replace a required high-risk PANEL")
            else:
                selected = _forced_direct(matches[0])
                override = True

        denial = list(shadow.denial_reasons) + override_errors
        if shadow.status == DENIED or selected is None or denial:
            return {
                "status": DENIED,
                "executed": False,
                "execution_mode": SHADOW,
                "denial_reasons": list(dict.fromkeys(denial or ["no policy option was admitted"])),
                "routing": routing,
                "capability_resolution": resolution,
                "path_resolution": path_resolution,
                "task_context": context.to_dict(),
                "shadow_evaluation": shadow.to_dict(),
                "forced_model": forced_model,
                "patch_authority": PATCH_AUTHORITY,
                "vsa_patch_authority": VSA_PATCH_AUTHORITY,
                "version": ADAPTIVE_ROUTER_VERSION,
            }

        evidence_digest = stable_digest({
            "shadow": shadow.to_dict(),
            "forced_model": forced_model or "",
            "topology_digest": routing.get("topology_digest", ""),
            "path_digest": path_resolution.get("path_digest", ""),
        })
        decision = make_route_decision(
            context=context,
            option=selected,
            assessments=assessments,
            graph_digest=str(path_resolution.get("graph_digest") or ""),
            path_digest=str(path_resolution.get("path_digest") or ""),
            policy_version=self.policy.policy_version,
            policy_evidence_digest=evidence_digest,
            proposal_only=True,
            human_override=override,
            created_at=created,
        )
        self.store.record_route_decision(decision)
        candidate_records = {
            item.candidate.profile_id: {
                **dict(item.candidate.raw),
                "profile_id": item.candidate.profile_id,
                "provider": item.candidate.provider,
                "model": item.candidate.model,
                "admitted": item.admitted,
                "rejection_reasons": list(item.rejection_reasons),
            }
            for item in assessments
        }
        return {
            "status": "PROPOSED",
            "executed": False,
            "execution_mode": SHADOW,
            "task_context": context.to_dict(),
            "route_decision": decision.to_dict(),
            "selected_option": selected.to_dict(),
            "candidate_records": candidate_records,
            "routing": routing,
            "capability_resolution": resolution,
            "path_resolution": path_resolution,
            "shadow_evaluation": shadow.to_dict(),
            "forced_model": forced_model,
            "forced_human_override": override,
            "policy_evidence_digest": evidence_digest,
            "explanation": {
                "selected_policy_mode": selected.policy_mode,
                "selected_profile_ids": list(selected.profile_ids),
                "selection_reasons": list(selected.explanation),
                "expected_verified_success": selected.expected_success,
                "expected_cost_usd": selected.expected_cost_usd,
                "expected_time_to_verified_ms": selected.expected_time_to_verified_ms,
                "admitted_candidates": [item.to_dict() for item in assessments if item.admitted],
                "rejected_candidates": [item.to_dict() for item in assessments if not item.admitted],
                "capability_graph_digest": path_resolution.get("graph_digest", ""),
                "capability_path_digest": path_resolution.get("path_digest", ""),
                "topology_digest": routing.get("topology_digest", ""),
                "purpose_digest": purpose,
                "forced_human_override": override,
            },
            "timings": {"planning_ms": max(0.0, (self.now() - began) * 1000.0)},
            "shadow_only": True,
            "proposal_only": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "version": ADAPTIVE_ROUTER_VERSION,
        }

    def revalidate(self, plan: Mapping[str, Any]) -> list[str]:
        context = TaskContext(**dict(plan["task_context"]))
        objective = str(plan.get("capability_resolution", {}).get("objective") or "revalidate route")
        _routing, resolution = self._resolve(
            objective,
            target_files=[plan.get("routing", {}).get("primary_file")]
            if plan.get("routing", {}).get("primary_file") else None,
            target_symbols=list(plan.get("routing", {}).get("key_functions", []) or []),
            token_budget=max(800, int(plan.get("routing", {}).get("context_tokens") or 2400)),
        )
        current = resolve_candidates_for_path(
            self.store,
            context,
            resolution.get("capability_connectome_path", {}) or {},
            repo_root=self.repo_root,
        )
        errors = list(current.get("errors", []) or [])
        if current.get("path_digest") != plan.get("path_resolution", {}).get("path_digest"):
            errors.append("capability path changed after route planning")
        if current.get("graph_digest") != plan.get("path_resolution", {}).get("graph_digest"):
            errors.append("capability graph changed after route planning")
        for profile_id in plan.get("selected_option", {}).get("profile_ids", []) or []:
            endpoint = self.store.get_endpoint(str(profile_id))
            if endpoint is None:
                errors.append(f"selected endpoint disappeared: {profile_id}")
            elif str(endpoint.get("status") or "") != "ACTIVE":
                errors.append(f"selected endpoint is no longer ACTIVE: {profile_id}")
        return list(dict.fromkeys(errors))

    def execute(self, objective: str, **kwargs: Any) -> dict[str, Any]:
        """Delegate to the separately testable authorization/execution boundary."""
        factory = self.executor_factory
        if factory is None:
            from aura_adaptive_model_executor import AdaptiveModelExecutor

            factory = AdaptiveModelExecutor
        executor = factory(router=self)
        return executor.execute(objective, **kwargs)
