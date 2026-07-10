"""
Aura Ephemeral Arena — Arena integration for ephemeral organs.

Reuses: BaseArenaAdapter, ActionCapsule, BoundaryContract, ArenaLease,
WorldStateDelta from aura_liquid_planning_arena.py.

Invariant:
  Intent selects possibilities.
  Capability Resolver proves what exists.
  FST rejects invalid structure.
  Manifest requests authority.
  Lease grants the minimum authority.
  Sandbox contains execution.
  Verifier proves the result.
  Human/governance approves consequential effects.
  QDKT remembers only governed knowledge.
  Dissolution revokes the organ.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
EPHEMERAL_ARENA_VERSION = "AURA_EPHEMERAL_ARENA_V1"


def create_ephemeral_boundary_contracts(
    organ_id: str,
    temp_dir: str,
) -> list[dict[str, Any]]:
    """Create boundary contracts for an ephemeral organ.

    At minimum: capability, filesystem, network, data/privacy, resource,
    lifecycle/TTL, UI, crystallization boundaries.
    """
    try:
        from aura_liquid_planning_arena import BoundaryContract
        contracts = [
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="capability",
                external_system="aura_substrate",
                source_region={"organ_id": organ_id},
                owned_scope=["read_only_adapters"],
                assumptions=["capabilities are explicitly granted"],
                required_inputs=["manifest"],
                promised_outputs=["bounded_execution"],
                constraints=["no_capability_escalation"],
                escalation_triggers=["unknown_capability_requested"],
                invariant="requested_capabilities ⊆ granted_lease",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="filesystem",
                external_system="host_filesystem",
                source_region={"temp_dir": temp_dir},
                owned_scope=[temp_dir],
                assumptions=["temp_dir is unique per organ"],
                required_inputs=["sandbox_receipt"],
                promised_outputs=["audit_artifacts_in_temp"],
                constraints=["no_write_outside_temp", "no_path_traversal", "no_symlink_escape"],
                escalation_triggers=["write_outside_temp_detected"],
                invariant="all_writes_confined_to_temp_dir",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="network",
                external_system="external_network",
                source_region={},
                owned_scope=[],
                assumptions=["network_calls = 0"],
                required_inputs=[],
                promised_outputs=["no_network_access"],
                constraints=["network_forbidden_in_mvp"],
                escalation_triggers=["network_call_attempted"],
                invariant="network_calls = 0",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="data_privacy",
                external_system="private_memory",
                source_region={},
                owned_scope=[],
                assumptions=["no_secrets_accessible"],
                required_inputs=[],
                promised_outputs=["no_secret_export"],
                constraints=["private_memory_export = false", "raw_sidecar_dump = false", "secrets_access = false"],
                escalation_triggers=["secret_access_attempted"],
                invariant="no_secrets_in_outputs",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="resource",
                external_system="host_resources",
                source_region={"budget": "resource_budget"},
                owned_scope=["bounded_execution"],
                assumptions=["budget_enforced"],
                required_inputs=["resource_budget"],
                promised_outputs=["within_budget"],
                constraints=["wall_time_bounded", "memory_bounded", "output_bounded", "tool_calls_bounded"],
                escalation_triggers=["budget_exceeded"],
                invariant="resource_budget_enforced",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="lifecycle_ttl",
                external_system="time",
                source_region={"ttl_seconds": 300},
                owned_scope=["ephemeral_existence"],
                assumptions=["ttl_set_at_creation"],
                required_inputs=["expires_at"],
                promised_outputs=["automatic_dissolution"],
                constraints=["no_permanent_existence"],
                escalation_triggers=["ttl_expired"],
                invariant="dissolution_is_mandatory",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="ui",
                external_system="human_agent_arena",
                source_region={},
                owned_scope=["declarative_json_schema"],
                assumptions=["ui_is_declarative_only"],
                required_inputs=["ui_manifest"],
                promised_outputs=["non_executable_schema"],
                constraints=["no_executable_script", "no_browser_code_execution"],
                escalation_triggers=["executable_code_in_ui"],
                invariant="ui_is_declarative_json_only",
            ),
            BoundaryContract.placeholder(
                domain="ephemeral", capsule_id=organ_id,
                boundary_type="crystallization",
                external_system="plugin_registry",
                source_region={},
                owned_scope=["proposal_only"],
                assumptions=["no_automatic_promotion"],
                required_inputs=[],
                promised_outputs=["review_packet"],
                constraints=["crystallization_policy = proposal_only"],
                escalation_triggers=["automatic_promotion_attempted"],
                invariant="no_automatic_permanent_install",
            ),
        ]
        return [c.to_dict() for c in contracts]
    except Exception:
        # Fallback: return contract specs as plain dicts
        return [
            {"boundary_type": bt, "organ_id": organ_id, "invariant": inv}
            for bt, inv in [
                ("capability", "requested ⊆ granted"),
                ("filesystem", "writes confined to temp"),
                ("network", "network_calls = 0"),
                ("data_privacy", "no secrets"),
                ("resource", "budget enforced"),
                ("lifecycle_ttl", "dissolution mandatory"),
                ("ui", "declarative only"),
                ("crystallization", "proposal only"),
            ]
        ]


def create_ephemeral_action_capsule(
    organ_id: str,
    objective: str,
    granted_capabilities: list[str],
) -> dict[str, Any]:
    """Create an Action Capsule for the ephemeral organ."""
    try:
        from aura_liquid_planning_arena import ActionCapsule
        capsule = ActionCapsule(
            capsule_version="AURA_ACTION_CAPSULE_V1",
            capsule_id=f"CAP-{organ_id}",
            domain="ephemeral",
            role="read_only_investigation",
            objective=objective,
            target={"organ_id": organ_id},
            scope={"capabilities": granted_capabilities},
            allowed_actions=granted_capabilities,
            forbidden_actions=["network", "install", "shell", "production_mutation", "secret_access", "commit", "push"],
            acceptance_checks=["no_production_mutation", "no_secret_access", "no_network_access"],
            expected_output="capability_resolution_and_ui_schema",
            escalation_triggers=["capability_escalation_attempted", "budget_exceeded"],
        )
        return capsule.__dict__ if hasattr(capsule, '__dict__') else asdict(capsule)
    except Exception:
        return {
            "capsule_id": f"CAP-{organ_id}", "domain": "ephemeral",
            "objective": objective, "allowed_actions": granted_capabilities,
            "forbidden_actions": ["network", "install", "shell", "production_mutation", "secret_access"],
        }


def create_ephemeral_lease(
    organ_id: str,
    granted_capabilities: list[str],
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Create an Arena Lease for the ephemeral organ."""
    try:
        from aura_liquid_planning_arena import ArenaLease
        lease = ArenaLease.create(
            domain="ephemeral",
            capsule_id=organ_id,
            holder=organ_id,
            regions=[{"organ_id": organ_id, "scope": "read_only"}],
            allowed_actions=granted_capabilities,
            forbidden_actions=["network", "install", "shell", "production_mutation", "secret_access", "commit", "push", "automatic_crystallization"],
            mode="read_only",
        )
        return lease.to_dict()
    except Exception:
        return {
            "lease_id": f"LEASE-{organ_id}", "domain": "ephemeral",
            "holder": organ_id, "allowed_actions": granted_capabilities,
            "forbidden_actions": ["network", "install", "shell", "production_mutation"],
            "mode": "read_only", "status": "active",
        }


def create_ephemeral_arena(
    organ_id: str,
    objective: str,
    granted_capabilities: list[str],
    temp_dir: str,
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Create a complete ephemeral arena with capsules, contracts, and lease."""
    contracts = create_ephemeral_boundary_contracts(organ_id, temp_dir)
    capsule = create_ephemeral_action_capsule(organ_id, objective, granted_capabilities)
    lease = create_ephemeral_lease(organ_id, granted_capabilities, ttl_seconds)
    return {
        "ok": True,
        "arena_version": EPHEMERAL_ARENA_VERSION,
        "organ_id": organ_id,
        "boundary_contracts": contracts,
        "action_capsule": capsule,
        "arena_lease": lease,
        "contract_count": len(contracts),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
