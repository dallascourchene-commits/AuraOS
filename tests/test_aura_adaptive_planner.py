from __future__ import annotations

from typing import Any

import aura_adaptive_model_router as module
from aura_adaptive_model_router import AdaptiveModelRouter, SHADOW


class Store:
    def __init__(self, candidates: list[dict[str, Any]]) -> None:
        self.candidates = candidates
        self.decisions = []
        self.contexts = []
        self.status = {item["profile_id"]: "ACTIVE" for item in candidates}

    def record_task_context(self, context):
        self.contexts.append(context)
        return context.task_context_id

    def record_route_decision(self, decision):
        self.decisions.append(decision)
        return decision.route_decision_id

    def query_candidates(self, _context):
        return list(self.candidates)

    def get_endpoint(self, profile_id):
        value = self.status.get(profile_id)
        return {"profile_id": profile_id, "status": value} if value else None


def candidate(profile_id="p1", *, status="ACTIVE"):
    return {
        "profile_id": profile_id,
        "provider": "fireworks",
        "requested_model": "model-a",
        "returned_model": "model-a",
        "status": status,
        "access_class": "BLACK_BOX",
        "capability_ids": ["cap.model"],
        "capability_graph_digest": "graph",
        "evidence_split": "SHADOW",
        "verified_success_probability": 0.95,
        "mean_cost_usd": 0.1,
        "mean_time_to_verified_ms": 100,
        "mean_repair_attempts": 0,
        "scope_violation_rate": 0,
        "endpoint_drift_score": 0,
        "uncertainty": 0.05,
        "context_window": 10000,
        "supported_tools": [],
        "evidence_count": 10,
        "evidence_digest": "evidence",
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
    path = {
        "ok": True,
        "graph_digest": "graph",
        "path_digest": "path",
        "path": ["cap.model"],
        "required_capability_ids": ["cap.model"],
        "model_dependent_capability_ids": ["cap.model"],
        "deterministic_capability_ids": [],
        "unresolved_execution_capability_ids": [],
        "truth_boundaries": ["behavioral only"],
        "risks": [],
        "tests": [],
        "token_savings_roles": [],
    }
    return {"objective": "route", "capability_connectome_path": path}


def bridge(store, context, _path, **_kwargs):
    return {
        "ok": True,
        "errors": [],
        "status": "ADMITTED",
        "graph_digest": "graph",
        "path_digest": "path",
        "required_capability_ids": ["cap.model"],
        "model_dependent_capability_ids": ["cap.model"],
        "unresolved_execution_capability_ids": [],
        "zero_model": {"eligible": False},
        "model_candidates": list(store.candidates),
    }


def make_router(monkeypatch, candidates):
    monkeypatch.setattr(module, "resolve_candidates_for_path", bridge)
    store = Store(candidates)
    router = AdaptiveModelRouter(
        store=store,
        context_router=routing,
        capability_resolver=resolution,
        now=lambda: 100.0,
    )
    return router, store


def test_shadow_plan_records_proposal_without_execution(monkeypatch) -> None:
    router, store = make_router(monkeypatch, [candidate()])
    plan = router.execute(
        "route model",
        purpose_digest="purpose",
        execution_mode=SHADOW,
        task_fields={"data_egress_allowed": True},
    )
    assert plan["status"] == "PROPOSED"
    assert plan["selected_option"]["policy_mode"] == "DIRECT"
    assert plan["executed"] is False
    assert store.decisions[-1].proposal_only is True
    assert plan["explanation"]["capability_graph_digest"] == "graph"


def test_forced_model_cannot_bypass_hard_admission(monkeypatch) -> None:
    router, _store = make_router(monkeypatch, [candidate(status="QUARANTINED")])
    plan = router.plan(
        "route model",
        purpose_digest="purpose",
        forced_model="p1",
        task_fields={"data_egress_allowed": True},
    )
    assert plan["status"] == "DENIED"
    assert any("QUARANTINED" in reason for reason in plan["denial_reasons"])
