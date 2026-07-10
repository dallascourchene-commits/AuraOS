"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, aura_icm_workspace, typing, pathlib, dataclasses, hashlib
FUNCTIONS: _hash_payload, _stable_list, _object_key, _object_type, build_world_state_delta, export_arena_to_icm, to_dict, placeholder, to_dict, create, to_dict, create, to_dict, to_dict, schema, action_capsule_from_intent, _regions_for_act, boundary_contract_for_act, action_capsule_from_act, lease_for_action, build_arena, action_capsule_from_intent, action_capsule_from_intent
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
from typing import Any

LIQUID_ARENA_VERSION = "AURA_LIQUID_PLANNING_ARENA_V1"
ACTION_CAPSULE_VERSION = "AURA_ACTION_CAPSULE_V1"
BOUNDARY_CONTRACT_VERSION = "AURA_BOUNDARY_CONTRACT_V1"
ARENA_LEASE_VERSION = "AURA_ARENA_LEASE_V1"
WORLD_STATE_DELTA_VERSION = "AURA_WORLD_STATE_DELTA_V1"


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _stable_list(values: list[Any] | tuple[Any, ...] | None) -> list[str]:
    seen = set()
    result = []
    for value in values or []:
        if value is None:
            continue
        item = str(value).strip()
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


@dataclass
class BoundaryContract:
    contract_version: str
    contract_id: str
    domain: str
    capsule_id: str
    boundary_type: str
    external_system: str
    source_region: dict[str, Any]
    owned_scope: list[str]
    assumptions: list[str]
    required_inputs: list[str]
    promised_outputs: list[str]
    constraints: list[str]
    escalation_triggers: list[str]
    invariant: str
    status: str = "placeholder"
    metadata: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def placeholder(
        cls,
        *,
        domain: str,
        capsule_id: str,
        boundary_type: str,
        external_system: str,
        source_region: dict[str, Any],
        owned_scope: list[str],
        assumptions: list[str],
        required_inputs: list[str],
        promised_outputs: list[str],
        constraints: list[str],
        escalation_triggers: list[str],
        invariant: str,
        metadata: dict[str, Any] | None = None,
    ) -> BoundaryContract:
        payload = {
            "contract_version": BOUNDARY_CONTRACT_VERSION,
            "domain": domain,
            "capsule_id": capsule_id,
            "boundary_type": boundary_type,
            "external_system": external_system,
            "source_region": source_region,
            "owned_scope": _stable_list(owned_scope),
            "assumptions": _stable_list(assumptions),
            "required_inputs": _stable_list(required_inputs),
            "promised_outputs": _stable_list(promised_outputs),
            "constraints": _stable_list(constraints),
            "escalation_triggers": _stable_list(escalation_triggers),
            "invariant": invariant,
            "status": "placeholder",
            "metadata": dict(metadata or {}),
        }
        contract_id = f"BC-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "contract_id": contract_id})
        return cls(contract_id=contract_id, phase_hash=phase_hash, **payload)


@dataclass
class ActionCapsule:
    capsule_version: str
    capsule_id: str
    domain: str
    role: str
    objective: str
    target: dict[str, Any]
    scope: dict[str, Any]
    allowed_actions: list[str]
    forbidden_actions: list[str]
    acceptance_checks: list[str]
    expected_output: str
    escalation_triggers: list[str]
    boundary_contract_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        capsule_id: str,
        domain: str,
        role: str,
        objective: str,
        target: dict[str, Any],
        scope: dict[str, Any],
        allowed_actions: list[str],
        forbidden_actions: list[str],
        acceptance_checks: list[str],
        expected_output: str,
        escalation_triggers: list[str],
        boundary_contract_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ActionCapsule:
        payload = {
            "capsule_version": ACTION_CAPSULE_VERSION,
            "capsule_id": capsule_id,
            "domain": domain,
            "role": role,
            "objective": objective,
            "target": dict(target),
            "scope": dict(scope),
            "allowed_actions": _stable_list(allowed_actions),
            "forbidden_actions": _stable_list(forbidden_actions),
            "acceptance_checks": _stable_list(acceptance_checks),
            "expected_output": expected_output,
            "escalation_triggers": _stable_list(escalation_triggers),
            "boundary_contract_ids": _stable_list(boundary_contract_ids),
            "metadata": dict(metadata or {}),
        }
        return cls(phase_hash=_hash_payload(payload), **payload)


@dataclass
class ArenaLease:
    lease_version: str
    lease_id: str
    domain: str
    capsule_id: str
    holder: str
    regions: list[dict[str, Any]]
    allowed_actions: list[str]
    forbidden_actions: list[str]
    mode: str = "exclusive_write"
    conflict_policy: str = "judge_then_reground"
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(
        cls,
        *,
        domain: str,
        capsule_id: str,
        holder: str,
        regions: list[dict[str, Any]],
        allowed_actions: list[str],
        forbidden_actions: list[str],
        mode: str = "exclusive_write",
        conflict_policy: str = "judge_then_reground",
        metadata: dict[str, Any] | None = None,
    ) -> ArenaLease:
        payload = {
            "lease_version": ARENA_LEASE_VERSION,
            "domain": domain,
            "capsule_id": capsule_id,
            "holder": holder,
            "regions": list(regions),
            "allowed_actions": _stable_list(allowed_actions),
            "forbidden_actions": _stable_list(forbidden_actions),
            "mode": mode,
            "conflict_policy": conflict_policy,
            "status": "active",
            "metadata": dict(metadata or {}),
        }
        lease_id = f"LEASE-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "lease_id": lease_id})
        return cls(lease_id=lease_id, phase_hash=phase_hash, **payload)


@dataclass
class WorldStateDelta:
    delta_version: str
    domain: str
    before_count: int
    after_count: int
    added: list[str]
    removed: list[str]
    changed: list[str]
    stable: list[str]
    object_type_counts: dict[str, dict[str, int]]
    metadata: dict[str, Any] = field(default_factory=dict)
    phase_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiquidPlanningArena:
    arena_version: str
    arena_id: str
    domain: str
    intent: str
    plan_ref: str
    domain_objects: list[str]
    action_capsules: list[dict[str, Any]]
    boundary_contracts: list[dict[str, Any]]
    agent_leases: list[dict[str, Any]]
    shared_action_queue: list[dict[str, Any]]
    verification_ledger: list[dict[str, Any]]
    adapter: dict[str, Any]
    phase_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _object_key(item: dict[str, Any], object_key: str) -> str:
    return str(item.get(object_key) or item.get("id") or item.get("path") or item.get("name") or _hash_payload(item))


def _object_type(item: dict[str, Any]) -> str:
    return str(item.get("object_type") or item.get("type") or "object")


def build_world_state_delta(
    *,
    domain: str,
    before_objects: list[dict[str, Any]],
    after_objects: list[dict[str, Any]],
    object_key: str = "id",
    metadata: dict[str, Any] | None = None,
) -> WorldStateDelta:
    before = {_object_key(item, object_key): item for item in before_objects}
    after = {_object_key(item, object_key): item for item in after_objects}
    before_keys = set(before)
    after_keys = set(after)
    changed = sorted(
        key
        for key in before_keys & after_keys
        if _hash_payload(before[key]) != _hash_payload(after[key])
    )
    stable = sorted((before_keys & after_keys) - set(changed))
    type_counts: dict[str, dict[str, int]] = {}
    for label, objects in (("before", before.values()), ("after", after.values())):
        for item in objects:
            object_type = _object_type(item)
            type_counts.setdefault(object_type, {"before": 0, "after": 0})
            type_counts[object_type][label] += 1
    payload = {
        "delta_version": WORLD_STATE_DELTA_VERSION,
        "domain": domain,
        "before_count": len(before),
        "after_count": len(after),
        "added": sorted(after_keys - before_keys),
        "removed": sorted(before_keys - after_keys),
        "changed": changed,
        "stable": stable,
        "object_type_counts": type_counts,
        "metadata": dict(metadata or {}),
    }
    return WorldStateDelta(phase_hash=_hash_payload(payload), **payload)


class BaseArenaAdapter:
    domain = "generic"
    domain_objects: tuple[str, ...] = ("object",)

    def schema(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "domain_objects": list(self.domain_objects),
            "invariant": "models propose, Arena stages, Shadow critiques, Judge decides, verifier proves, human approves, ledger remembers",
        }

    def action_capsule_from_intent(
        self,
        *,
        objective: str,
        capsule_id: str,
        target: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
    ) -> ActionCapsule:
        raise NotImplementedError


class CodeArenaAdapter(BaseArenaAdapter):
    domain = "code"
    domain_objects = ("files", "symbols", "diffs", "tests", "topology_deltas", "dream_usefulness_scores")

    def _regions_for_act(self, act: Any, evidence: Any | None) -> list[dict[str, Any]]:
        writable_files = _stable_list([getattr(act, "target_file", None), *list(getattr(act, "related_files", []) or [])])
        writable_file_set = set(writable_files)
        files = list(writable_files)
        if evidence is not None:
            files.extend(item for item in _stable_list(getattr(evidence, "neighbor_files", []) or []) if item not in files)
        regions = [{"region_type": "file", "id": file, "mode": "write" if file in writable_file_set else "read"} for file in files]
        symbol = getattr(act, "target_symbol", None)
        if symbol:
            regions.append({"region_type": "symbol", "id": symbol, "file": getattr(act, "target_file", None), "mode": "write"})
        return regions

    def boundary_contract_for_act(self, act: Any, evidence: Any | None) -> BoundaryContract:
        neighbor_files = _stable_list(getattr(evidence, "neighbor_files", []) if evidence else [])
        return BoundaryContract.placeholder(
            domain=self.domain,
            capsule_id=str(getattr(act, "task_id", "")),
            boundary_type="code_boundary",
            external_system="CODEMAP/topology/test-neighbor surface",
            source_region={"file": getattr(act, "target_file", None), "symbol": getattr(act, "target_symbol", None)},
            owned_scope=_stable_list([getattr(act, "target_file", None), *list(getattr(act, "related_files", []) or [])]),
            assumptions=[
                "Only declared files and symbols may be changed.",
                "Neighbor files are read context unless explicitly leased.",
            ],
            required_inputs=[
                "CODEMAP file card",
                "nearby tests",
                "patch diff headers",
            ],
            promised_outputs=[
                "unified diff or refusal",
                "affected_files metadata",
                "tests metadata",
            ],
            constraints=list(getattr(act, "constraints", []) or []),
            escalation_triggers=list(getattr(act, "escalate_if", []) or []),
            invariant="preserve phase_hash, codemap_epoch, target_file, target_symbol, and test boundary",
            metadata={
                "task_id": getattr(act, "task_id", None),
                "target_file": getattr(act, "target_file", None),
                "target_symbol": getattr(act, "target_symbol", None),
                "neighbor_files": neighbor_files,
                "upstream": "aura_fusion.build_task_capsule",
                "downstream": "aura_phase_capsule.capture_phase_capsule",
            },
        )

    def action_capsule_from_act(self, act: Any, evidence: Any | None, boundary_contract: BoundaryContract) -> ActionCapsule:
        acceptance = [str(getattr(act, "acceptance", "") or "Return a bounded patch or refusal.")]
        if evidence is not None:
            acceptance.extend(f"nearby test: {name}" for name in _stable_list(getattr(evidence, "test_files", []) or []))
        return ActionCapsule.create(
            capsule_id=str(getattr(act, "task_id", "")),
            domain=self.domain,
            role=str(getattr(act, "role", "cheap_builder")),
            objective=str(getattr(act, "objective", "")),
            target={"file": getattr(act, "target_file", None), "symbol": getattr(act, "target_symbol", None)},
            scope={"regions": self._regions_for_act(act, evidence), "allowed_scope": getattr(act, "allowed_scope", "")},
            allowed_actions=[
                "read leased files and CODEMAP context",
                "emit one bounded unified diff",
                "declare affected files, symbols, and tests",
                "emit BoundaryContract placeholders for external assumptions",
            ],
            forbidden_actions=[
                "mutate production files directly",
                "touch files outside leased regions",
                "write aura_incubator.py in live Architect mode",
                "invent behavior across a boundary without a BoundaryContract",
            ],
            acceptance_checks=acceptance,
            expected_output=str(getattr(act, "expected_output", "UNIFIED_DIFF")),
            escalation_triggers=list(getattr(act, "escalate_if", []) or []),
            boundary_contract_ids=[boundary_contract.contract_id],
            metadata={
                "source_capsule_version": getattr(act, "capsule_version", ""),
                "size": getattr(act, "size", ""),
                "dream_context_scores": list(getattr(evidence, "dream_scores", []) or [])[:8] if evidence is not None else [],
            },
        )

    def lease_for_action(self, action: ActionCapsule) -> ArenaLease:
        return ArenaLease.create(
            domain=self.domain,
            capsule_id=action.capsule_id,
            holder=action.role,
            regions=list(action.scope.get("regions", [])),
            allowed_actions=action.allowed_actions,
            forbidden_actions=action.forbidden_actions,
            metadata={"action_phase_hash": action.phase_hash},
        )

    def build_arena(
        self,
        *,
        objective: str,
        plan_phase_hash: str,
        act_capsules: list[Any],
        grounding: list[Any],
        shadow_report: Any,
    ) -> LiquidPlanningArena:
        by_task = {getattr(item, "task_id", ""): item for item in grounding}
        contracts: list[BoundaryContract] = []
        actions: list[ActionCapsule] = []
        leases: list[ArenaLease] = []
        for act in act_capsules:
            evidence = by_task.get(getattr(act, "task_id", ""))
            contract = self.boundary_contract_for_act(act, evidence)
            action = self.action_capsule_from_act(act, evidence, contract)
            contracts.append(contract)
            actions.append(action)
            leases.append(self.lease_for_action(action))
        payload = {
            "arena_version": LIQUID_ARENA_VERSION,
            "domain": self.domain,
            "intent": objective,
            "plan_ref": plan_phase_hash,
            "domain_objects": list(self.domain_objects),
            "action_capsules": [item.to_dict() for item in actions],
            "boundary_contracts": [item.to_dict() for item in contracts],
            "agent_leases": [item.to_dict() for item in leases],
            "shared_action_queue": [],
            "verification_ledger": [
                {"stage": "lease", "status": "active", "lease_count": len(leases)},
                {"stage": "shadow", "status": "passed" if getattr(shadow_report, "ok", False) else "blocked"},
            ],
            "adapter": self.schema(),
        }
        arena_id = f"LPA-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "arena_id": arena_id})
        return LiquidPlanningArena(arena_id=arena_id, phase_hash=phase_hash, **payload)


class CivicArenaAdapter(BaseArenaAdapter):
    domain = "civic"
    domain_objects = (
        "neighborhoods", "services", "funding", "legal_constraints",
        "intervention_modules", "community_governance", "dream_evidence_scores",
        # V3 expanded domain objects
        "community_needs", "resource_offers", "proposals", "objections",
        "reservations", "representation_gaps", "consent_arcs",
        "mitosis_workstreams", "music_scenarios", "legal_instruments",
        "council_items", "what_if_simulations", "pilot_packets",
        "decision_packets", "organ_manifests", "organ_receipts",
        "community_memory", "civic_sessions", "official_snapshots",
    )

    def action_capsule_from_intent(
        self,
        *,
        objective: str,
        capsule_id: str,
        target: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
    ) -> ActionCapsule:
        return ActionCapsule.create(
            capsule_id=capsule_id,
            domain=self.domain,
            role="civic_planner",
            objective=objective,
            target=dict(target or {}),
            scope={"regions": [{"region_type": "civic_scope", "id": key, "value": value} for key, value in dict(target or {}).items()]},
            allowed_actions=[
                "propose interventions", "request missing data", "rank evidence by downstream usefulness",
                "draft BoundaryContract placeholders", "run MITOSIS decomposition", "run MUSIC comparison",
                "match resources", "collect consent", "run What-If simulation", "prepare pilot packet",
                "assemble decision packet", "map needs and assets", "inspect legal evidence",
                "display council issues", "project systemic context",
            ],
            forbidden_actions=[
                "claim legal approval", "allocate funding", "promise service delivery",
                "submit to government", "cast binding vote", "transfer property",
                "manufacture consensus", "erase dissent", "infer identity",
                "auto-activate cultural profiles", "scrape social media",
            ],
            acceptance_checks=[
                "surface funding, legal, service, and governance constraints",
                "verify consent-to-match before resource matching",
                "preserve dissent and representation gaps",
                "label all truth classes correctly",
                "enforce privacy classes",
            ],
            expected_output="CIVIC_DECISION_PACKET",
            escalation_triggers=list(constraints or ["legal uncertainty", "community governance conflict", "funding ambiguity", "representation gap", "critical objection"]),
        )

    def create_civic_boundary_contract(
        self,
        *,
        contract_id: str,
        capsule: ActionCapsule,
        profile_refs: list[str] | None = None,
        privacy_classes: list[str] | None = None,
    ) -> BoundaryContract:
        """Create a boundary contract for civic organ execution."""
        return BoundaryContract(
            contract_version=1,
            contract_id=contract_id,
            domain=self.domain,
            capsule_id=capsule.capsule_id,
            boundary_type="civic_organ",
            external_system="civic_session",
            source_region="civic_world_model",
            owned_scope="civic_decision_packet",
            assumptions={},
            required_inputs=["session_data", "profile_set", "story_fixtures"],
            promised_outputs=["verified_organ_result"],
            constraints={
                "forbidden_effects": ["submit_official", "allocate_funds", "bind_participant"],
                "secrets_access": False,
                "privacy_classes_allowed": privacy_classes or ["PUBLIC_ATTRIBUTED", "PUBLIC_PSEUDONYMOUS", "COMMUNITY_ONLY"],
            },
            escalation_triggers=["legal_uncertainty", "community_governance_conflict", "funding_ambiguity"],
            invariant="non_binding: True, dissolution_policy: mandatory",
            status="ACTIVE",
            metadata={"profile_refs": profile_refs or []},
        )

    def create_civic_lease(
        self,
        *,
        lease_id: str,
        capsule: ActionCapsule,
        capabilities: list[str],
        ttl_seconds: int = 300,
    ) -> ArenaLease:
        """Create a minimum-capability lease for a civic organ."""
        import time as _time
        return ArenaLease(
            lease_version=1,
            lease_id=lease_id,
            domain=self.domain,
            capsule_id=capsule.capsule_id,
            holder="civic_organ",
            regions=[{"region_type": "capability", "id": c, "value": True} for c in capabilities],
            allowed_actions=capabilities,
            forbidden_actions=["submit_official", "allocate_funds", "bind_participant"],
            mode="bounded",
            conflict_policy="deny",
            status="ACTIVE",
            metadata={"expires_at": _time.time() + ttl_seconds, "non_binding": True, "dissolution_policy": "mandatory"},
        )


class TravelArenaAdapter(BaseArenaAdapter):
    domain = "travel"
    domain_objects = (
        "traveler_preferences",
        "destinations",
        "routes",
        "budget",
        "time_windows",
        "bookable_options",
        "price_observations",
        "raw_snapshots",
        "vsa_sidecar_pointers",
        "dream_usefulness_scores",
        "media_assets",
    )

    def action_capsule_from_intent(
        self,
        *,
        objective: str,
        capsule_id: str,
        target: dict[str, Any] | None = None,
        constraints: list[str] | None = None,
    ) -> ActionCapsule:
        return ActionCapsule.create(
            capsule_id=capsule_id,
            domain=self.domain,
            role="travel_planner",
            objective=objective,
            target=dict(target or {}),
            scope={"regions": [{"region_type": "travel_scope", "id": key, "value": value} for key, value in dict(target or {}).items()]},
            allowed_actions=[
                "compare routes",
                "rank options",
                "resolve VSA pointers into exact sidecar records",
                "rank semantic pointers by downstream usefulness",
                "request live bookability check",
                "draft BoundaryContract placeholders",
            ],
            forbidden_actions=[
                "book without approval",
                "invent prices",
                "show vector-only prices",
                "store exact prices only in VSA",
                "ignore visa or time-window constraints",
            ],
            acceptance_checks=[
                "preserve budget, dates, traveler preferences, and approval requirements",
                "every displayed price resolves to sidecar price_observations",
                "block stale, missing, unverified, or vector-only prices",
            ],
            expected_output="TRAVEL_PLAN_OPTIONS",
            escalation_triggers=list(
                dict.fromkeys(
                    [
                        "price unavailable",
                        "stale sidecar price",
                        "missing source provenance",
                        "visa ambiguity",
                        "booking policy mismatch",
                        "payment or legal boundary",
                        *(constraints or []),
                    ]
                )
            ),
        )


ARENA_ADAPTERS = {
    "code": CodeArenaAdapter,
    "civic": CivicArenaAdapter,
    "travel": TravelArenaAdapter,
}


# ---------------------------------------------------------------------------
# ICM export bridge (Aura-ICM workspace control surface)
# ---------------------------------------------------------------------------

def export_arena_to_icm(
    arena: "LiquidPlanningArena",
    workspace_root: str | Path,
    *,
    qdkt: Any = None,
    dream_candidates: list[Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Any:
    """Export an arena run into an ICM-compatible workspace.

    This is a thin bridge: ICM stores references, reports, and audit
    artifacts; exact truth remains in the arena's own ledger and sidecars.
    """
    from aura_icm_workspace import (
        ICMStageDescriptor,
        export_arena_transaction,
        _hash_payload,
    )

    stages: list[ICMStageDescriptor] = []
    all_contracts: list[Any] = []
    for idx, capsule in enumerate(arena.action_capsules, start=1):
        contracts = []
        for c in arena.boundary_contracts:
            if c.get("capsule_id") == capsule.get("capsule_id"):
                contracts.append(c)
        stage = ICMStageDescriptor(
            stage_number=idx,
            stage_name=capsule.get("capsule_id", f"stage_{idx}"),
            capsule=capsule,
            contracts=contracts,
            inputs=capsule.get("required_inputs", []),
            process=capsule.get("role", ""),
            outputs=capsule.get("promised_outputs", []),
            allowed_actions=capsule.get("allowed_actions", []),
            forbidden_actions=capsule.get("forbidden_actions", []),
            verifier_gates=[
                v.get("verifier_id", "")
                for v in arena.verification_ledger
                if v.get("capsule_id") == capsule.get("capsule_id")
            ],
            human_review_status="pending",
            references={"adapter_schema": arena.adapter},
            artifacts={
                "lease": arena.agent_leases[idx - 1] if idx <= len(arena.agent_leases) else {}
            },
        )
        stages.append(stage)
        all_contracts.extend(contracts)

    txn = {
        "objective": arena.intent,
        "domain": arena.domain,
        "arena_id": arena.arena_id,
        "arena_version": arena.arena_version,
        "phase_hash": arena.phase_hash,
    }
    return export_arena_transaction(
        txn,
        workspace_root,
        domain=arena.domain,
        arena_id=arena.arena_id,
        arena_version=arena.arena_version,
        stages=stages,
        qdkt=qdkt,
        dream_candidates=dream_candidates,
        metadata={
            "adapter_type": arena.adapter.get("domain", arena.domain),
            "action_capsule_count": len(arena.action_capsules),
            **(dict(metadata or {})),
        },
    )

