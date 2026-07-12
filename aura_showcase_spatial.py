"""Bounded spatial task projection for the unified Aura showcase.

This module does not create a second topology system. It projects the existing
Coding Arena topology into small presenter-safe workspaces for the unified
Civic + Human Agent demo.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

from aura_coding_arena_3d import select_micro_arena

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
SPATIAL_SHOWCASE_VERSION = "AURA_SHOWCASE_SPATIAL_TASKS_V1"
MAX_SELECTED_NODES = 4
MAX_WORKSPACE_NODES = 96
MAX_WORKSPACE_LINKS = 220
SLOT_KEYS = ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")


_TASKS: tuple[dict[str, Any], ...] = (
    {
        "task_id": "version_drift",
        "title": "Trace version and documentation drift",
        "summary": "Find version properties and repository snapshot claims that disagree with the current CODEMAP.",
        "spatial_command": "show everything connected to version properties and documentation drift",
        "intent_slots": {
            "DIR": "repository",
            "ASP": "audit",
            "CLASS": "documentation_consistency",
            "SUBJ": "version_properties",
            "VOICE": "inspect",
            "STEM": "trace_drift",
        },
        "seed_files": [
            "README.md",
            "USER_GUIDE.md",
            ".aura/ARCHITECTURE.md",
            ".aura/CODEMAP.md",
            "aura_showcase_server.py",
        ],
        "seed_symbols": ["SHOWCASE_VERSION", "SERVER_VERSION"],
        "keywords": ["version", "codemap", "architecture", "user_guide"],
        "acceptance_criteria": [
            "Show every selected claim with its exact repository path.",
            "Distinguish generated CODEMAP facts from manually maintained prose.",
            "Prepare review-only synchronization options; do not edit automatically.",
        ],
        "prohibited_actions": ["automatic_commit", "automatic_push", "automatic_merge"],
        "presenter_cue": "Aura traces where version facts and documentation claims connect before proposing any synchronization.",
    },
    {
        "task_id": "memory_friction",
        "title": "Reduce friction in Aura's memory architecture",
        "summary": "Locate repeated lookups, redundant boundaries, and avoidable context switching across Aura's governed memory systems.",
        "spatial_command": "show everything connected to memory apertures context crusher qdkt and st3gg recall",
        "intent_slots": {
            "DIR": "memory",
            "ASP": "diagnose",
            "CLASS": "friction_reduction",
            "SUBJ": "governed_memory",
            "VOICE": "inspect",
            "STEM": "localize_friction",
        },
        "seed_files": [
            "aura_qdkt.py",
            "aura_context_crusher.py",
            "aura_st3gg_recall.py",
            "aura_paper_memory.py",
            "aura_route_capsule_materializer.py",
        ],
        "seed_symbols": ["get_qdkt", "apply_context_crush_to_prompt"],
        "keywords": ["memory", "qdkt", "context", "st3gg", "aperture"],
        "acceptance_criteria": [
            "Expose interfaces and repeated routing boundaries, not private memory contents.",
            "Show callers, dependencies, tests, and likely context-switch costs.",
            "Keep every recommendation bounded to exact source regions.",
        ],
        "prohibited_actions": ["private_memory_exposure", "automatic_mutation", "automatic_merge"],
        "presenter_cue": "The graph shows where memory systems meet, while private contents remain outside the projection.",
    },
    {
        "task_id": "civic_map_overlay",
        "title": "Investigate the Civic map overlay",
        "summary": "Determine why synthetic Civic features may not visibly populate or remain synchronized in the AMD showcase.",
        "spatial_command": "show everything connected to the civic map overlay showcase projection and browser renderer",
        "intent_slots": {
            "DIR": "showcase",
            "ASP": "diagnose",
            "CLASS": "presentation_defect",
            "SUBJ": "civic_map_overlay",
            "VOICE": "investigate",
            "STEM": "trace_render_path",
        },
        "seed_files": [
            "aura_showcase/civic.js",
            "aura_showcase/app.js",
            "aura_showcase_server.py",
            "aura_civic_map.py",
            "aura_civic_winnipeg_fixture.py",
            "tests/test_aura_showcase_guided_interface.py",
        ],
        "seed_symbols": ["project_map_manifest", "dispatch_showcase_request"],
        "keywords": ["map", "overlay", "projection", "showcase", "geojson"],
        "acceptance_criteria": [
            "Trace session state through projection, network response, and canvas draw.",
            "Expose stale-response and visibility risks without assuming a cause.",
            "Preserve privacy, jurisdiction, zoom, and truth-class filtering.",
        ],
        "prohibited_actions": ["person_level_mapping", "automatic_patch", "automatic_merge"],
        "presenter_cue": "Aura follows the visible map from policy-filtered GeoJSON to browser pixels and keeps the diagnosis review-only.",
    },
    {
        "task_id": "emergent_capabilities",
        "title": "Audit emergent Arena capabilities",
        "summary": "Inspect useful capabilities that appear when topology, guarded WFST, tensor evidence, and Agent Arena components are composed.",
        "spatial_command": "show everything connected to emergent potential human agent arena tensor evidence and agent arena bridge",
        "intent_slots": {
            "DIR": "arenas",
            "ASP": "audit",
            "CLASS": "emergent_capability",
            "SUBJ": "composed_architecture",
            "VOICE": "inspect",
            "STEM": "surface_capabilities",
        },
        "seed_files": [
            "aura_emergent_potential_repl.py",
            "aura_human_agent_concepts.py",
            "aura_human_agent_arena.py",
            "aura_tensor_evidence.py",
            "aura_agent_arena_bridge.py",
        ],
        "seed_symbols": ["audit_emergent_potential", "build_concept_workspace", "HumanAgentArena"],
        "keywords": ["emergent", "arena", "tensor", "concept", "bridge"],
        "acceptance_criteria": [
            "Label implemented composition separately from hypotheses.",
            "Show exact supporting files and tests for each capability.",
            "Never convert a visual relationship into patch or governance authority.",
        ],
        "prohibited_actions": ["unsupported_capability_claim", "automatic_promotion", "automatic_merge"],
        "presenter_cue": "Aura distinguishes capabilities already grounded in code from promising connections that still need proof.",
    },
)


def list_spatial_tasks() -> dict[str, Any]:
    """Return presenter-safe task cards without exposing internal topology state."""
    return {
        "ok": True,
        "version": SPATIAL_SHOWCASE_VERSION,
        "tasks": [deepcopy(task) for task in _TASKS],
        "task_count": len(_TASKS),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def get_spatial_task(task_id: str) -> dict[str, Any] | None:
    """Return one declared task by exact identifier."""
    needle = str(task_id or "").strip()
    for task in _TASKS:
        if task["task_id"] == needle:
            return deepcopy(task)
    return None


def build_task_workspace(
    topology: dict[str, Any],
    task_id: str,
    *,
    depth: int = 1,
) -> dict[str, Any]:
    """Project one declared task into the existing bounded Coding Arena topology."""
    task = get_spatial_task(task_id)
    if task is None:
        return _error("unknown_spatial_task")
    selected = _select_seed_node_ids(topology, task)
    if not selected:
        return _error("no_grounded_task_nodes", task=task)
    return _workspace_packet(
        topology,
        selected,
        depth=depth,
        instruction=task["spatial_command"],
        task=task,
    )


def build_selected_workspace(
    topology: dict[str, Any],
    node_ids: Iterable[str],
    *,
    depth: int = 1,
    task_id: str = "",
) -> dict[str, Any]:
    """Expand or focus selected exact node identifiers inside the same topology."""
    task = get_spatial_task(task_id) if task_id else None
    selected = [str(node_id) for node_id in node_ids if str(node_id)]
    if not selected:
        return _error("node_id_required", task=task)
    instruction = task["spatial_command"] if task else "inspect selected topology node"
    return _workspace_packet(topology, selected, depth=depth, instruction=instruction, task=task)


def _workspace_packet(
    topology: dict[str, Any],
    selected: list[str],
    *,
    depth: int,
    instruction: str,
    task: dict[str, Any] | None,
) -> dict[str, Any]:
    micro = select_micro_arena(
        topology,
        selected[:MAX_SELECTED_NODES],
        depth=max(0, min(2, int(depth))),
        human_instruction=instruction,
    )
    bounded = _bound_micro_arena(micro)
    return {
        "ok": True,
        "version": SPATIAL_SHOWCASE_VERSION,
        "task": deepcopy(task) if task else None,
        "workspace": bounded,
        "bounds": {
            "selected_node_limit": MAX_SELECTED_NODES,
            "node_limit": MAX_WORKSPACE_NODES,
            "link_limit": MAX_WORKSPACE_LINKS,
            "depth_limit": 2,
        },
        "truth_policy": (
            "Exact repository topology and source spans are authoritative. "
            "The 3D projection is an orientation and selection surface only."
        ),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def _select_seed_node_ids(topology: dict[str, Any], task: dict[str, Any]) -> list[str]:
    nodes = [node for node in topology.get("nodes", []) if isinstance(node, dict) and node.get("id")]
    scored: list[tuple[int, str]] = []
    files = [str(value).lower().replace("\\", "/") for value in task.get("seed_files", [])]
    symbols = [str(value).lower() for value in task.get("seed_symbols", [])]
    keywords = [str(value).lower() for value in task.get("keywords", [])]
    for node in nodes:
        path = str(node.get("file_path") or "").lower().replace("\\", "/")
        symbol = str(node.get("symbol") or "").lower()
        label = str(node.get("label") or "").lower()
        haystack = " ".join((path, symbol, label, str(node.get("kind") or "").lower()))
        score = 0
        for seed in files:
            if path == seed:
                score += 120
            elif path.endswith("/" + seed) or path.endswith(seed):
                score += 90
            elif seed and seed in path:
                score += 45
        for seed in symbols:
            if symbol == seed:
                score += 110
            elif seed and seed in symbol:
                score += 55
        score += sum(12 for keyword in keywords if keyword and keyword in haystack)
        if score:
            scored.append((score, str(node["id"])))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node_id for _, node_id in scored[:MAX_SELECTED_NODES]]


def _bound_micro_arena(micro: dict[str, Any]) -> dict[str, Any]:
    selected = [str(value) for value in micro.get("selected_node_ids", [])]
    selected_set = set(selected)
    raw_nodes = [deepcopy(node) for node in micro.get("nodes", []) if isinstance(node, dict)]
    raw_nodes.sort(key=lambda node: (0 if str(node.get("id")) in selected_set else 1, str(node.get("id") or "")))
    nodes = raw_nodes[:MAX_WORKSPACE_NODES]
    node_ids = {str(node.get("id")) for node in nodes}
    for node in nodes:
        metadata = dict(node.get("metadata") or {})
        projected = bool(metadata.get("visual_projection_only"))
        node["projection_truth"] = "CODEMAP_PROJECTED" if projected else "EXACT_TOPOLOGY"
        node["patch_authority"] = False
    links = [
        deepcopy(link)
        for link in micro.get("links", [])
        if isinstance(link, dict)
        and str(link.get("source")) in node_ids
        and str(link.get("target")) in node_ids
    ][:MAX_WORKSPACE_LINKS]
    return {
        **{key: deepcopy(value) for key, value in micro.items() if key not in {"nodes", "links"}},
        "nodes": nodes,
        "links": links,
        "selected_node_ids": [node_id for node_id in selected if node_id in node_ids],
        "truncated": len(raw_nodes) > len(nodes) or len(micro.get("links", [])) > len(links),
        "returned_node_count": len(nodes),
        "returned_link_count": len(links),
    }


def _error(error: str, *, task: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        "task": deepcopy(task) if task else None,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
