from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import aura_adaptive_model_router as module
from aura_adaptive_fusion import AdaptiveFusionPanelExecutor
from aura_adaptive_model_executor import AdaptiveModelExecutor
from aura_adaptive_model_router import AdaptiveModelRouter, PAIRED_LIVE
from aura_model_cognome_execution_auth import ExecutionAuthorization
from aura_shadow_model_router import CASCADE, DIRECT, ShadowRoutingPolicy


class Store:
    def __init__(self, candidates):
        self.candidates = candidates
        self.status = {item["profile_id"]: "ACTIVE" for item in candidates}
        self.comparisons = []

    def record_task_context(self, context): return context.task_context_id
    def record_route_decision(self, decision): return decision.route_decision_id
    def query_candidates(self, _context): return list(self.candidates)
    def get_endpoint(self, profile_id):
        status = self.status.get(profile_id)
        return {"profile_id": profile_id, "status": status} if status else None
    def record_experiment_comparison(self, comparison):
        self.comparisons.append(dict(comparison))
        return comparison["comparison_id"]


class Egress:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def __call__(self, **identity):
        parent = self
        class Endpoint:
            def generate(self, prompt, **kwargs):
                text = parent.outputs.pop(0)
                parent.calls.append((identity, prompt, kwargs))
                return text, None, 0.01
        return Endpoint()


def candidate(profile_id, provider, model, success, cost, latency):
    return {
        "profile_id": profile_id,
        "provider": provider,
        "requested_model": model,
        "returned_model": model,
        "status": "ACTIVE",
        "access_class": "BLACK_BOX",
        "capability_ids": ["cap.model"],
        "capability_graph_digest": "graph",
        "evidence_split": "SHADOW",
        "verified_success_probability": success,
        "mean_cost_usd": cost,
        "mean_time_to_verified_ms": latency,
        "mean_repair_attempts": 0,
        "scope_violation_rate": 0,
        "endpoint_drift_score": 0,
        "uncertainty": 0.05,
        "context_window": 10000,
        "supported_tools": [],
        "evidence_count": 20,
        "evidence_digest": "evidence-" + profile_id,
    }


def routing(*_args, **_kwargs):
    return {
        "status": "found",
        "primary_file": "aura_router.py",
        "key_functions": ["route_task"],
        "router_context": "def route_task(): pass",
        "context_tokens": 8,
        "context_packet": {"source_spans": [{"start_line": 1, "end_line": 1}]},
        "source_hashes": {"aura_router.py": "hash"},
        "topology_digest": "topology",
    }


def resolution(*_args, **_kwargs):
    return {
        "objective": "route",
        "capability_connectome_path": {
            "ok": True,
            "graph_digest": "graph",
            "path_digest": "path",
            "path": ["cap.model"],
            "required_capability_ids": ["cap.model"],
            "model_dependent_capability_ids": ["cap.model"],
            "deterministic_capability_ids": [],
            "unresolved_execution_capability_ids": [],
            "truth_boundaries": [], "risks": [], "tests": [], "token_savings_roles": [],
        },
    }


def bridge(store, context, _path, **_kwargs):
    return {
        "ok": True, "errors": [], "status": "ADMITTED",
        "graph_digest": "graph", "path_digest": "path",
        "required_capability_ids": ["cap.model"],
        "model_dependent_capability_ids": ["cap.model"],
        "unresolved_execution_capability_ids": [],
        "zero_model": {"eligible": False},
        "model_candidates": list(store.candidates),
    }


def make_router(monkeypatch, candidates, egress, verifier, policy=None):
    monkeypatch.setattr(module, "resolve_candidates_for_path", bridge)
    store = Store(candidates)
    router = AdaptiveModelRouter(
        store=store,
        policy=policy,
        context_router=routing,
        capability_resolver=resolution,
        now=lambda: 100.0,
        executor_factory=lambda router: AdaptiveModelExecutor(
            router=router,
            egress_factory=egress,
            verifier=verifier,
            persist_telemetry=False,
            now=lambda: 100.0,
        ),
    )
    return router, store


def authorization(plan, policy_mode, profiles, max_calls):
    return ExecutionAuthorization.create(
        approved_by="Dallas",
        verifier_id=plan["task_context"]["verifier_id"],
        purpose_digest="purpose",
        capability_graph_digest="graph",
        allowed_policy_modes=[policy_mode],
        allowed_profile_ids=profiles,
        nonce="approval-nonce",
        issued_at=90.0,
        expires_at=110.0,
        max_calls=max_calls,
    )


def test_direct_execution_is_authorized_linked_and_single_use(monkeypatch) -> None:
    egress = Egress(["good"])
    router, store = make_router(
        monkeypatch,
        [candidate("p1", "fireworks", "model-a", 0.95, 0.1, 100)],
        egress,
        lambda text, error, **_kwargs: {"passed": text == "good" and error is None},
    )
    plan = router.plan("route", purpose_digest="purpose", task_fields={"data_egress_allowed": True})
    auth = authorization(plan, DIRECT, ["p1"], 1)

    result = router.execute(
        "route", purpose_digest="purpose", execution_mode=PAIRED_LIVE,
        authorization=auth, task_fields={"data_egress_allowed": True},
    )
    assert result["status"] == "EXECUTED"
    assert result["verified"] is True
    assert result["live_route_decision"]["proposal_only"] is False
    assert result["calls"][0]["call_id"].startswith("call_")
    assert result["calls"][0]["observation_id"].startswith("observation_")
    assert len(egress.calls) == 1
    assert store.comparisons[-1]["approved_live"] is True

    replay = router.execute(
        "route", purpose_digest="purpose", execution_mode=PAIRED_LIVE,
        authorization=auth, task_fields={"data_egress_allowed": True},
    )
    assert replay["status"] == "DENIED"
    assert "already been consumed" in replay["denial_reasons"][0]


def test_cascade_calls_fallback_only_after_verifier_rejection(monkeypatch) -> None:
    egress = Egress(["bad", "good"])
    candidates = [
        candidate("cheap", "fireworks", "cheap-model", 0.70, 0.01, 50),
        candidate("strong", "deepseek", "strong-model", 0.99, 1.0, 500),
    ]
    router, _store = make_router(
        monkeypatch, candidates, egress,
        lambda text, _error, **_kwargs: {"passed": text == "good"},
        ShadowRoutingPolicy(cascade_min_gain=0.0, allow_panel=False),
    )
    plan = router.plan("route", purpose_digest="purpose", task_fields={"data_egress_allowed": True})
    assert plan["selected_option"]["policy_mode"] == CASCADE
    profiles = plan["selected_option"]["profile_ids"]
    auth = authorization(plan, CASCADE, profiles, 2)

    result = router.execute(
        "route", purpose_digest="purpose", execution_mode=PAIRED_LIVE,
        authorization=auth, task_fields={"data_egress_allowed": True},
    )
    assert result["verified"] is True
    assert [call["verification"]["passed"] for call in result["calls"]] == [False, True]
    assert len(egress.calls) == 2


def test_revalidation_blocks_quarantined_endpoint(monkeypatch) -> None:
    egress = Egress(["good"])
    router, store = make_router(
        monkeypatch,
        [candidate("p1", "fireworks", "model-a", 0.95, 0.1, 100)],
        egress,
        lambda *_args, **_kwargs: {"passed": True},
    )
    plan = router.plan("route", purpose_digest="purpose", task_fields={"data_egress_allowed": True})
    auth = authorization(plan, DIRECT, ["p1"], 1)
    store.status["p1"] = "QUARANTINED"
    result = router.execute(
        "route", purpose_digest="purpose", execution_mode=PAIRED_LIVE,
        authorization=auth, task_fields={"data_egress_allowed": True},
    )
    assert result["status"] == "DENIED"
    assert any("no longer ACTIVE" in reason for reason in result["denial_reasons"])
    assert egress.calls == []


def test_public_router_remains_legacy_by_default_and_adaptive_is_explicit(monkeypatch) -> None:
    from aura_router import AutoRouter
    import aura_router_adaptive_compat as compat

    router = AutoRouter()
    monkeypatch.setattr(router, "route_task", lambda task, **kwargs: {"ok": True, "legacy": task.key})
    assert router.route("mesh_offload") == {"ok": True, "legacy": "mesh_offload"}

    captured = {}
    def fake_adaptive(_router, task, **kwargs):
        captured.update(kwargs)
        return {"ok": True, "router_mode": kwargs["routing_mode"], "task": task.key}
    monkeypatch.setattr(compat, "route_test_case", fake_adaptive)
    result = router.route("mesh_offload", routing_mode="SHADOW", purpose_digest="purpose")
    assert result["router_mode"] == "SHADOW"
    assert captured["purpose_digest"] == "purpose"


def test_adaptive_fusion_links_every_panel_and_judge_call() -> None:
    class Registry:
        def get_provider_config(self, provider):
            return {"base_url": f"https://{provider}.invalid", "api_key_env": f"{provider.upper()}_KEY"}

    class Result:
        def __init__(self, payload): self.payload = payload
        def to_dict(self): return dict(self.payload)

    class Coordinator:
        def __init__(self, *, panel, judge, caller, **_kwargs):
            self.panel, self.judge, self.caller = panel, judge, caller
        def run(self, task, **_kwargs):
            panel_outputs = []
            for agent in self.panel:
                payload = {"agent": {"name": agent.name, "role": agent.role}}
                text, error, latency, schema = self.caller(
                    provider=agent.provider, model=agent.model,
                    messages=[{"role": "user", "content": json.dumps(payload)}],
                )
                panel_outputs.append({"agent": agent.name, "ok": not error, "content": text})
            agent = self.judge
            payload = {"agent": {"name": agent.name, "role": agent.role}}
            text, error, latency, schema = self.caller(
                provider=agent.provider, model=agent.model,
                messages=[{"role": "user", "content": json.dumps(payload)}],
            )
            return Result({
                "ok": not error, "task": task, "mode": "adaptive_panel", "phase_hash": "phase",
                "panel_outputs": panel_outputs,
                "judge_output": {"agent": agent.name, "ok": not error, "content": text},
                "final_answer": "judged", "metrics": {"panel_count": len(panel_outputs)},
            })

    def caller(**kwargs):
        agent = json.loads(kwargs["messages"][-1]["content"])["agent"]
        if agent["role"] == "JUDGE":
            content = {
                "consensus": [], "contradictions": [], "coverage_gaps": [],
                "unique_insights": [], "blind_spots": [], "winning_approach": "x",
                "final_answer": "judged", "confidence": 1.0,
                "should_escalate_to_human": False,
            }
        else:
            content = {
                "role": agent["role"], "answer": "x", "claims": [], "risks": [],
                "missing_info": [], "recommended_action": "review", "confidence": 1.0,
            }
        return json.dumps(content), None, 0.01, True

    records = {
        "p1": {"profile_id": "p1", "provider": "fireworks", "model": "m1"},
        "p2": {"profile_id": "p2", "provider": "deepseek", "model": "m2"},
        "p3": {"profile_id": "p3", "provider": "groq", "model": "m3"},
    }
    executor = AdaptiveFusionPanelExecutor(
        store=object(), provider_registry=Registry(), caller=caller,
        coordinator_factory=Coordinator, persist_telemetry=False,
    )
    result = executor(
        objective="analyze",
        plan={
            "selected_option": {"profile_ids": ["p1", "p2", "p3"]},
            "candidate_records": records,
            "routing": {"primary_file": "", "key_functions": []},
            "path_resolution": {"path_digest": "path"},
        },
        context=SimpleNamespace(task_context_id="task", capability_graph_digest="graph"),
        live_decision=SimpleNamespace(route_decision_id="route"),
        authorization=SimpleNamespace(authorization_id="auth"),
        comparison_id="comparison",
        correlation_id="correlation",
    )
    assert result["ok"] is True
    assert len(result["calls"]) == 3
    assert all(call["call_id"].startswith("call_") for call in result["calls"])
    assert all(output["profile_id"] for output in result["panel_outputs"])
    assert result["judge_output"]["profile_id"] == "p3"
