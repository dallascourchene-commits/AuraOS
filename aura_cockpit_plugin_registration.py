"""
Aura Cockpit Plugin Registration — register cockpit capabilities as plugins.

Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
PLUGIN_VERSION = "AURA_COCKPIT_PLUGIN_REGISTRATION_V1"

# Shared registry instance to persist registrations across calls
_SHARED_REGISTRY = None


def register_cockpit_plugins(repo_root: str = ".") -> dict:
    """Register all 17 capability lanes as plugins."""
    global _SHARED_REGISTRY
    try:
        from aura_capability_lane_registry import load_capability_lanes
        from aura_plugin_registry import AuraPluginRegistry, AuraPluginManifest

        lanes = load_capability_lanes()
        registry = AuraPluginRegistry()
        _SHARED_REGISTRY = registry
        registered = []

        # Map lane types to valid AURA_ORGANS
        lane_organ_map = {
            "music_coding_lane": "code",
            "mitosis_decomposition_lane": "code",
            "research_arxiv_lane": "dream",
            "skillweaver_lane": "code",
            "mesh_swarm_lane": "federation",
            "mcp_gateway_lane": "icm",
            "plugin_registry_lane": "core",
            "goap_planner_lane": "graph",
            "phase_capsule_lane": "travel",
            "live_architect_lane": "civic",
            "audit_staking_lane": "qdkt",
            "token_economy_lane": "fintech",
            "capability_router_lane": "social",
        }

        for lane in lanes:
            try:
                # Convert lane to AuraPluginManifest
                # Map to a valid organ_id from AURA_ORGANS
                organ_id = lane_organ_map.get(lane.lane_id, "code")
                manifest = AuraPluginManifest(
                    organ_id=organ_id,
                    domain="cockpit",
                    entry_module=lane.source_modules[0] if lane.source_modules else "",
                    description=lane.purpose,
                    required_permissions=tuple(),
                    provided_tools=tuple(lane.public_symbols),
                    sidecar_tables=tuple(),
                    verifier_gates=tuple(),
                    boundary_invariant=lane.patch_authority,
                    arena_adapter="",
                    risk_score=0.0,
                    metadata={"lane_id": lane.lane_id, "lane_name": lane.name, "when_to_use": lane.when_to_use},
                )
                registry.register(manifest)
                registered.append({"id": lane.lane_id, "name": lane.name})
            except Exception:
                # Skip lanes that fail to register (e.g., duplicate organ_id)
                pass

        return {"ok": True, "registered": registered, "count": len(registered),
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "patch_authority": PATCH_AUTHORITY,
                 "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def list_registered_plugins(repo_root: str = ".") -> dict:
    """List registered plugins."""
    global _SHARED_REGISTRY
    try:
        from aura_plugin_registry import AuraPluginRegistry
        # Reuse shared registry instance if available
        registry = _SHARED_REGISTRY if _SHARED_REGISTRY is not None else AuraPluginRegistry()
        plugins = registry.list_organs()
        return {"ok": True, "plugins": plugins, "patch_authority": PATCH_AUTHORITY,
                 "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception:
        return {"ok": True, "plugins": [], "note": "Plugin registry unavailable",
                 "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def cockpit_plugin_manifest(repo_root: str = ".") -> dict:
    """Return plugin manifest for the cockpit."""
    return {"ok": True, "manifest": {"name": "Aura Native Cockpit", "version": "1.0",
             "capabilities": ["intent_ingestion", "capability_connectome", "workflow_gates",
                              "token_economy", "capability_lanes", "swarm_plan", "audit_trail"]},
             "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
