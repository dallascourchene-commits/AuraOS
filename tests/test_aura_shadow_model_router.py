from __future__ import annotations

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
