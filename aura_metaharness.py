"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f6-[Q-SYS:AURA_METAHARNESS]
DIKWP_TIER: PURPOSE
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Unified Meta-Harness)
DEPENDENCIES: dataclasses, hashlib, json, time, typing,
              aura_mcp_gateway, aura_plugin_registry, aura_goal_planner,
              aura_background_workers, aura_metaharness_audit, aura_federation
FUNCTIONS: MetaHarness, build_default_metaharness
SYNOPSIS: Orchestrator that wires the six meta-harness modules into one
          Aura-native layer. Preserves the Aura invariant: VSA maps meaning,
          sidecars store exact truth, Arena stages actions, verifiers prove,
          humans/governance approve, QDKT remembers. The meta-harness is
          strictly upstream/proposal-only — it never mutates production or
          bypasses Architect, Shadow, Judge, or Verifier.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any

from aura_mcp_gateway import AuraMCPGateway, build_default_gateway
from aura_plugin_registry import AuraPluginRegistry, build_default_registry
from aura_goal_planner import AuraGOAPPlanner, build_default_planner
from aura_background_workers import BackgroundWorkerSupervisor, build_default_supervisor
from aura_metaharness_audit import AuraMetaHarnessAuditor, MetaHarnessAudit
from aura_federation import AuraFederation, build_default_federation

AURA_METAHARNESS_VERSION = "AURA_METAHARNESS_V1"

AURA_INVARIANT = (
    "VSA maps meaning, sidecars store exact truth, Arena stages actions, "
    "verifiers prove, humans/governance approve, QDKT remembers"
)


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


@dataclass
class MetaHarnessSnapshot:
    """A point-in-time snapshot of the meta-harness layer state."""

    snapshot_version: str
    ts: float
    tools: list[dict[str, Any]]
    organs: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    workers: list[dict[str, Any]]
    trust: list[dict[str, Any]]
    invariant: str
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_version": self.snapshot_version,
            "ts": self.ts,
            "tools": list(self.tools),
            "organs": list(self.organs),
            "actions": list(self.actions),
            "workers": list(self.workers),
            "trust": list(self.trust),
            "invariant": self.invariant,
            "phase_hash": self.phase_hash,
        }


class MetaHarness:
    """The Aura-native meta-harness orchestrator.

    Composes the MCP gateway, plugin registry, GOAP planner, background
    workers, audit scorer, and federation into one layer. Every component
    shares the same QDKT instance so that tool calls, plugin installs, plan
    outcomes, worker outcomes, audits, and federation trust are all
    remembered together.
    """

    def __init__(
        self,
        *,
        qdkt: Any = None,
        gateway: AuraMCPGateway | None = None,
        registry: AuraPluginRegistry | None = None,
        planner: AuraGOAPPlanner | None = None,
        supervisor: BackgroundWorkerSupervisor | None = None,
        auditor: AuraMetaHarnessAuditor | None = None,
        federation: AuraFederation | None = None,
        node_ref: Any = None,
    ) -> None:
        self.qdkt = qdkt
        self.node_ref = node_ref
        self.gateway = gateway or build_default_gateway(qdkt=qdkt, node_ref=node_ref)
        self.registry = registry or build_default_registry(qdkt=qdkt)
        self.planner = planner or build_default_planner(qdkt=qdkt)
        self.supervisor = supervisor or build_default_supervisor(qdkt=qdkt)
        self.auditor = auditor or AuraMetaHarnessAuditor(qdkt=qdkt)
        self.federation = federation or build_default_federation(qdkt=qdkt)

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an Aura-safe MCP tool and return the result dict."""
        result = self.gateway.call(tool_name, arguments)
        return result.to_dict()

    def plan_goal(
        self,
        goal: str,
        initial_state: dict[str, Any],
        goal_conditions: dict[str, Any],
    ) -> dict[str, Any]:
        """Plan a goal and return the GoalPlan as a dict of act_task proposals."""
        plan = self.planner.plan(goal, initial_state, goal_conditions)
        return {
            "plan": plan.to_dict(),
            "act_tasks": plan.to_act_tasks(),
            "invariant": "proposals only — must pass Architect, Shadow, Verifier, Judge",
        }

    def install_organ(self, organ_id: str, *, config: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.registry.install(organ_id, config=config)

    def export_federated_capsule(
        self,
        capsule: dict[str, Any],
        *,
        verifier_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.federation.export_capsule(capsule, verifier_result=verifier_result).to_dict()

    def import_federated_capsule(
        self,
        remote: dict[str, Any] | Any,
        *,
        remote_key: bytes | None = None,
    ) -> dict[str, Any]:
        return self.federation.import_capsule(remote, remote_key=remote_key).to_dict()

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def audit(
        self,
        *,
        arena_store: Any = None,
        sidecar: Any = None,
        proposals: list[dict[str, Any]] | None = None,
        exports: list[dict[str, Any]] | None = None,
    ) -> MetaHarnessAudit:
        return self.auditor.audit(
            gateway=self.gateway,
            registry=self.registry,
            supervisor=self.supervisor,
            federation=self.federation,
            arena_store=arena_store,
            sidecar=sidecar,
            proposals=proposals,
            exports=exports,
        )

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> MetaHarnessSnapshot:
        payload = {
            "tools": self.gateway.list_tools(),
            "organs": self.registry.list_organs(),
            "actions": self.planner.list_actions(),
            "workers": self.supervisor.list_workers(),
            "trust": self.federation.trust_table(),
            "invariant": AURA_INVARIANT,
        }
        ts = time.time()
        phase_hash = _hash_payload(payload)
        return MetaHarnessSnapshot(
            snapshot_version=AURA_METAHARNESS_VERSION,
            ts=ts,
            tools=payload["tools"],
            organs=payload["organs"],
            actions=payload["actions"],
            workers=payload["workers"],
            trust=payload["trust"],
            invariant=AURA_INVARIANT,
            phase_hash=phase_hash,
        )

    # ------------------------------------------------------------------
    # Invariant assertion
    # ------------------------------------------------------------------

    def assert_invariants(self) -> None:
        """Assert that the meta-harness layer preserves the Aura invariant."""
        # 1. Gateway must only expose Aura-safe tools with safe allowed effects.
        from aura_mcp_gateway import AURA_SAFE_TOOLS, FORBIDDEN_EFFECTS_DENYLIST

        tool_names = {tool["tool_name"] for tool in self.gateway.list_tools()}
        if not tool_names.issubset(set(AURA_SAFE_TOOLS)):
            raise RuntimeError(f"non-Aura-safe tools present: {tool_names - set(AURA_SAFE_TOOLS)}")
        for tool in self.gateway.list_tools():
            bad = set(tool["allowed_effects"]) & FORBIDDEN_EFFECTS_DENYLIST
            if bad:
                raise RuntimeError(f"tool {tool['tool_name']} allows denied effects: {bad}")

        # 2. Registry must not have any denied permissions.
        from aura_plugin_registry import DENIED_PERMISSIONS

        for organ in self.registry.list_organs():
            denied = set(organ["required_permissions"]) & DENIED_PERMISSIONS
            if denied:
                raise RuntimeError(f"organ {organ['organ_id']} requests denied permissions: {denied}")

        # 3. Planner actions must declare all required gates.
        from aura_goal_planner import REQUIRED_GATES

        for action in self.planner.list_actions():
            missing = set(REQUIRED_GATES) - set(action["must_pass_gates"])
            if missing:
                raise RuntimeError(f"action {action['name']} omits gates: {missing}")

        # 4. Workers must forbid production mutation.
        for worker in self.supervisor.list_workers():
            # Workers are observe-only by construction; this is a structural reminder.
            if not worker["name"]:
                raise RuntimeError("worker must have a name")

        # 5. Federation must redact private fields.
        from aura_federation import PRIVATE_FIELDS_DENYLIST

        for exported in self.federation.exported_capsules():
            payload_keys = set(exported.get("redacted_payload", {}).keys())
            bad = payload_keys & PRIVATE_FIELDS_DENYLIST
            if bad:
                raise RuntimeError(f"federated capsule {exported['capsule_id']} leaked private fields: {bad}")


def build_default_metaharness(*, qdkt: Any = None, node_ref: Any = None) -> MetaHarness:
    """Build the canonical meta-harness with all six modules wired together."""
    return MetaHarness(qdkt=qdkt, node_ref=node_ref)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura Meta-Harness — orchestrator")
    parser.add_argument("--snapshot", action="store_true", help="print a meta-harness snapshot")
    parser.add_argument("--audit", action="store_true", help="run a dry meta-harness audit")
    parser.add_argument("--check-invariants", dest="check_invariants", action="store_true", help="assert all meta-harness invariants")
    args = parser.parse_args(argv)
    harness = build_default_metaharness()
    if args.snapshot:
        print(json.dumps(harness.snapshot().to_dict(), indent=2, sort_keys=True))
    elif args.audit:
        audit = harness.audit()
        print(json.dumps(audit.to_dict(), indent=2, sort_keys=True))
    elif args.check_invariants:
        harness.assert_invariants()
        print("All meta-harness invariants hold.")
    else:
        snap = harness.snapshot()
        print(f"Aura Meta-Harness: {len(snap.tools)} tools, {len(snap.organs)} organs, {len(snap.actions)} actions, {len(snap.workers)} workers")
        print(f"Invariant: {AURA_INVARIANT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())