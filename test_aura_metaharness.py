"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f7-[Q-SYS:AURA_METAHARNESS_TESTS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Invariant Verification)
DEPENDENCIES: asyncio, json, unittest
FUNCTIONS: TestAuraMCPGateway, TestAuraPluginRegistry, TestAuraGOAPPlanner,
           TestAuraBackgroundWorkers, TestAuraMetaHarnessAudit, TestAuraFederation,
           TestMetaHarnessOrchestrator
SYNOPSIS: Smoke tests for the Aura meta-harness layer. Verifies that every
          module preserves the Aura invariant: no production mutation, no
          verifier bypass, no raw private memory export, and all gates remain
          mandatory.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from typing import Any

# Ensure the repo root is importable when run directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_mcp_gateway import (
    AURA_SAFE_TOOLS,
    FORBIDDEN_EFFECTS_DENYLIST,
    AuraMCPGateway,
    AuraMCPTool,
    build_default_gateway,
)
from aura_plugin_registry import (
    AURA_ORGANS,
    DENIED_PERMISSIONS,
    AuraPluginManifest,
    AuraPluginRegistry,
    build_default_registry,
)
from aura_goal_planner import (
    REQUIRED_GATES,
    AuraGOAPPlanner,
    GoalAction,
    build_default_planner,
)
from aura_background_workers import (
    BackgroundWorkerSupervisor,
    DreamUsefulnessWorker,
    WorkerProposal,
    build_default_supervisor,
)
from aura_metaharness_audit import AuraMetaHarnessAuditor, audit_metaharness
from aura_federation import (
    PRIVATE_FIELDS_DENYLIST,
    AuraFederation,
    build_default_federation,
)
from aura_metaharness import MetaHarness, build_default_metaharness


# ---------------------------------------------------------------------------
# Stub QDKT (avoids touching real SQLite during tests)
# ---------------------------------------------------------------------------

class StubQDKT:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.crystals: dict[str, dict[str, Any]] = {}

    def observe(self, event_type: str, payload: dict[str, Any], *, rationale: str = "", concept: str = "", confidence: float = 0.5, subsystem: str = "unknown", node_ref: Any = None) -> str:
        event_id = f"STUB-{len(self.events):08d}"
        self.events.append({
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "rationale": rationale,
            "concept": concept,
            "confidence": confidence,
        })
        return event_id

    def observe_retrieval_usefulness(self, score_row: dict[str, Any]) -> str:
        return self.observe("retrieval_usefulness", score_row)

    def query(self, concept: str, *, top_k: int = 5, include_binary: bool = False) -> dict[str, Any]:
        return {"concept": concept, "knowledge_index": [], "fast_path": None}

    def crystallize(self, concept: str, recommended_action: str, *, confidence: float = 1.0, source: str = "explicit") -> None:
        self.crystals[concept] = {"action": recommended_action, "confidence": confidence, "source": source}


# ---------------------------------------------------------------------------
# MCP Gateway
# ---------------------------------------------------------------------------

class TestAuraMCPGateway(unittest.TestCase):
    def test_default_gateway_registers_nine_aura_safe_tools(self) -> None:
        gateway = build_default_gateway()
        tool_names = {tool["tool_name"] for tool in gateway.list_tools()}
        self.assertEqual(tool_names, set(AURA_SAFE_TOOLS))
        self.assertEqual(len(tool_names), 9)

    def test_gateway_rejects_unsafe_allowed_effects(self) -> None:
        gateway = AuraMCPGateway()
        with self.assertRaises(ValueError):
            gateway.register(
                AuraMCPTool(
                    tool_name="run_arena",
                    description="bad",
                    required_inputs=(),
                    forbidden_effects=(),
                    allowed_effects=("mutate_production",),  # denied effect in allowed set
                    handler=lambda args, **kw: {},
                )
            )

    def test_gateway_rejects_unknown_tool_name(self) -> None:
        gateway = AuraMCPGateway()
        with self.assertRaises(ValueError):
            gateway.register(
                AuraMCPTool(
                    tool_name="delete_database",
                    description="bad",
                    required_inputs=(),
                    forbidden_effects=(),
                    allowed_effects=(),
                    handler=lambda args, **kw: {},
                )
            )

    def test_stage_action_capsule_returns_proposal(self) -> None:
        gateway = build_default_gateway()
        result = gateway.call("stage_action_capsule", {"capsule": {"capsule_id": "C1", "objective": "test"}})
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.result["status"], "staged_proposal")
        self.assertIn("mutate_production", result.result["forbidden_actions"])

    def test_verify_fintech_ledger_blocks_missing_fields(self) -> None:
        gateway = build_default_gateway()
        result = gateway.call("verify_fintech_ledger", {"entry": {"entry_id": "E1"}})
        self.assertTrue(result.ok)
        self.assertFalse(result.result["approved"])
        self.assertIn("missing_account_id", result.result["blockers"])

    def test_scan_social_luminance_redacts(self) -> None:
        gateway = build_default_gateway()
        result = gateway.call(
            "scan_social_luminance",
            {"query": "test", "candidates": [{"candidate_id": "c1", "luminance_score": 0.9}]},
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.result["status"], "proposed")
        self.assertIn("raw_private_post_export", result.result["forbidden_actions"])

    def test_gateway_logs_to_qdkt(self) -> None:
        qdkt = StubQDKT()
        gateway = build_default_gateway(qdkt=qdkt)
        gateway.call("stage_action_capsule", {"capsule": {"capsule_id": "C2"}})
        self.assertTrue(any(e["event_type"] == "mcp_tool_call" for e in qdkt.events))


# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------

class TestAuraPluginRegistry(unittest.TestCase):
    def test_default_registry_has_eleven_organs(self) -> None:
        registry = build_default_registry()
        organ_ids = {organ["organ_id"] for organ in registry.list_organs()}
        self.assertEqual(organ_ids, set(AURA_ORGANS))
        self.assertEqual(len(organ_ids), 11)

    def test_registry_rejects_denied_permissions(self) -> None:
        registry = AuraPluginRegistry()
        with self.assertRaises(ValueError):
            registry.register(
                AuraPluginManifest(
                    organ_id="core",
                    domain="core",
                    entry_module="x",
                    description="bad",
                    required_permissions=("bypass_verifier",),
                    provided_tools=(),
                    sidecar_tables=(),
                    verifier_gates=(),
                    boundary_invariant="bad",
                )
            )

    def test_install_and_uninstall(self) -> None:
        qdkt = StubQDKT()
        registry = build_default_registry(qdkt=qdkt)
        record = registry.install("core")
        self.assertEqual(record["status"], "installed")
        self.assertTrue(registry.is_installed("core"))
        registry.uninstall("core", reason="test")
        self.assertFalse(registry.is_installed("core"))
        self.assertTrue(any(e["event_type"] == "plugin_install" for e in qdkt.events))
        self.assertTrue(any(e["event_type"] == "plugin_uninstall" for e in qdkt.events))

    def test_permission_audit_max_risk_below_one(self) -> None:
        registry = build_default_registry()
        audit = registry.permission_audit()
        self.assertLess(audit["max_permission_risk"], 1.0)
        for organ in audit["organs"]:
            self.assertEqual(organ["denied_permissions_requested"], [])


# ---------------------------------------------------------------------------
# GOAP Planner
# ---------------------------------------------------------------------------

class TestAuraGOAPPlanner(unittest.TestCase):
    def test_default_planner_has_actions(self) -> None:
        planner = build_default_planner()
        self.assertGreater(len(planner.list_actions()), 0)

    def test_planner_rejects_action_missing_gates(self) -> None:
        planner = AuraGOAPPlanner()
        with self.assertRaises(ValueError):
            planner.register_action(
                GoalAction(
                    name="bad",
                    domain="code",
                    must_pass_gates=("architect",),  # missing shadow, verifier, judge
                )
            )

    def test_plan_finds_path(self) -> None:
        planner = build_default_planner()
        plan = planner.plan(
            "build verified travel package",
            initial_state={"vsa_id_set": True, "sidecar_available": True},
            goal_conditions={"package_proposed": True},
        )
        action_names = [a.name for a in plan.actions]
        self.assertIn("resolve_vsa_pointer", action_names)
        self.assertIn("verify_price_freshness", action_names)
        self.assertIn("build_travel_package", action_names)

    def test_plan_emits_act_tasks_with_gate_constraints(self) -> None:
        planner = build_default_planner()
        plan = planner.plan(
            "emit patch",
            initial_state={"codemap_available": True, "target_file_set": True},
            goal_conditions={"patch_proposed": True},
        )
        tasks = plan.to_act_tasks()
        self.assertGreater(len(tasks), 0)
        for task in tasks:
            gate_constraints = [c for c in task["constraints"] if c.startswith("must_pass_gate:")]
            self.assertGreaterEqual(len(gate_constraints), len(REQUIRED_GATES))

    def test_plan_records_to_qdkt(self) -> None:
        qdkt = StubQDKT()
        planner = build_default_planner(qdkt=qdkt)
        planner.plan("goal", initial_state={"codemap_available": True, "target_file_set": True}, goal_conditions={"patch_proposed": True})
        self.assertTrue(any(e["event_type"] == "goal_plan" for e in qdkt.events))


# ---------------------------------------------------------------------------
# Background Workers
# ---------------------------------------------------------------------------

class TestAuraBackgroundWorkers(unittest.TestCase):
    def test_default_supervisor_has_workers(self) -> None:
        supervisor = build_default_supervisor()
        self.assertGreater(len(supervisor.list_workers()), 0)

    def test_proposals_are_observe_only(self) -> None:
        supervisor = build_default_supervisor()
        supervisor.add_worker(DreamUsefulnessWorker(retrieval_events=[{"candidate_id": "c1"}]))
        asyncio.run(supervisor.run_once_all())
        proposals = supervisor.drain_proposals()
        self.assertGreater(len(proposals), 0)
        for proposal in proposals:
            self.assertEqual(proposal.status, "proposed")
            self.assertIn("mutate_production", proposal.forbidden_actions)
            self.assertTrue(proposal.requires_verifier_gate)

    def test_worker_outcome_recorded(self) -> None:
        qdkt = StubQDKT()
        supervisor = build_default_supervisor(qdkt=qdkt)
        supervisor.add_worker(DreamUsefulnessWorker(qdkt=qdkt, retrieval_events=[{"candidate_id": "c2"}]))
        asyncio.run(supervisor.run_once_all())
        self.assertTrue(any(e["event_type"] == "worker_outcome" for e in qdkt.events))


# ---------------------------------------------------------------------------
# MetaHarness Audit
# ---------------------------------------------------------------------------

class TestAuraMetaHarnessAudit(unittest.TestCase):
    def test_dry_audit_returns_eight_dimensions(self) -> None:
        audit = audit_metaharness()
        scores = audit.to_dict()["scores"]
        expected = {
            "verifier_coverage",
            "sidecar_truth_separation",
            "qdkt_coverage",
            "dream_usefulness_coverage",
            "stale_data_risk",
            "secret_exposure",
            "plugin_permission_risk",
            "boundary_contracts",  # Added: 8th dimension
        }
        self.assertEqual(set(scores.keys()), expected)

    def test_secret_exposure_detected(self) -> None:
        audit = audit_metaharness(proposals=[{"api_key": "sk-1234567890abcdef"}])
        self.assertEqual(audit.secret_exposure, 0.0)
        self.assertIn("secret_exposure_detected=0.00", audit.blockers)

    def test_audit_writes_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = os.path.join(tmp, "audit.jsonl")
            auditor = AuraMetaHarnessAuditor(ledger_path=ledger)
            auditor.audit()
            self.assertTrue(os.path.exists(ledger))


# ---------------------------------------------------------------------------
# Federation
# ---------------------------------------------------------------------------

class TestAuraFederation(unittest.TestCase):
    def test_export_redacts_private_fields(self) -> None:
        federation = build_default_federation()
        fed = federation.export_capsule({"objective": "test", "api_key": "leaked", "data": {"secret": "x"}})
        self.assertNotIn("api_key", fed.redacted_payload)
        self.assertNotIn("secret", fed.redacted_payload.get("data", {}))

    def test_export_raises_on_raw_private_memory(self) -> None:
        federation = build_default_federation()
        with self.assertRaises(ValueError):
            federation.export_capsule({"raw_private_memory": b"bytes"})

    def test_export_raises_on_raw_sidecar_bytes(self) -> None:
        federation = build_default_federation()
        with self.assertRaises(ValueError):
            federation.export_capsule({"raw_sidecar_bytes": b"bytes"})

    def test_import_rejects_bad_signature(self) -> None:
        federation = build_default_federation(node_key=b"key-A")
        fed = federation.export_capsule({"objective": "test"}, verifier_result={"approved": True})
        # Tamper: import with a different key.
        federation_b = build_default_federation(node_key=b"key-B")
        with self.assertRaises(ValueError):
            federation_b.import_capsule(fed)

    def test_import_rejects_unverified_capsule(self) -> None:
        federation = build_default_federation()
        fed = federation.export_capsule({"objective": "test"}, verifier_result={"approved": False})
        with self.assertRaises(ValueError):
            federation.import_capsule(fed)

    def test_import_accepts_verified_capsule(self) -> None:
        federation = build_default_federation()
        fed = federation.export_capsule({"objective": "test"}, verifier_result={"approved": True})
        imported = federation.import_capsule(fed)
        self.assertEqual(imported.status, "imported_verified")

    def test_trust_updates_on_accept_and_reject(self) -> None:
        federation = build_default_federation()
        fed_ok = federation.export_capsule({"objective": "ok"}, verifier_result={"approved": True})
        federation.import_capsule(fed_ok)
        trust = federation.trust_record("aura-local")
        self.assertIsNotNone(trust)
        self.assertGreater(trust.accepted_count, 0)

    def test_federation_logs_to_qdkt(self) -> None:
        qdkt = StubQDKT()
        federation = build_default_federation(qdkt=qdkt)
        fed = federation.export_capsule({"objective": "test"}, verifier_result={"approved": True})
        federation.import_capsule(fed)
        self.assertTrue(any(e["event_type"] == "federation_export" for e in qdkt.events))
        self.assertTrue(any(e["event_type"] == "federation_import" for e in qdkt.events))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class TestMetaHarnessOrchestrator(unittest.TestCase):
    def test_snapshot_contains_all_components(self) -> None:
        harness = build_default_metaharness()
        snap = harness.snapshot()
        self.assertEqual(len(snap.tools), 9)
        self.assertEqual(len(snap.organs), 11)
        self.assertGreater(len(snap.actions), 0)
        self.assertGreater(len(snap.workers), 0)
        self.assertIn("VSA maps meaning", snap.invariant)

    def test_assert_invariants_holds(self) -> None:
        harness = build_default_metaharness()
        # Export a clean capsule so the federation invariant check has data.
        harness.export_federated_capsule({"objective": "clean"}, verifier_result={"approved": True})
        harness.assert_invariants()

    def test_plan_goal_returns_act_tasks(self) -> None:
        harness = build_default_metaharness()
        result = harness.plan_goal(
            "build patch",
            initial_state={"codemap_available": True, "target_file_set": True},
            goal_conditions={"patch_proposed": True},
        )
        self.assertGreater(len(result["act_tasks"]), 0)
        self.assertIn("proposals only", result["invariant"])

    def test_audit_runs_through_orchestrator(self) -> None:
        harness = build_default_metaharness()
        audit = harness.audit()
        self.assertGreaterEqual(audit.overall_score, 0.0)


if __name__ == "__main__":
    unittest.main()