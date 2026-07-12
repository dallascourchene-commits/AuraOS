"""Bridge a compiled bulk-intent trace into the existing showcase topology adapter.

The graph, selection algorithm, and response bounds remain owned by
``aura_showcase_spatial``. This module only supplies a generated task descriptor from
sanitized intent output so the Learning Arena can reuse the same 3D lens.
"""
from __future__ import annotations

from typing import Any

from aura_showcase_spatial import _select_seed_node_ids, _workspace_packet

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def build_intent_workspace(
    topology: dict[str, Any],
    trace: dict[str, Any],
    *,
    depth: int = 1,
) -> dict[str, Any]:
    """Project parsed files and symbols through the existing bounded micro-arena."""
    if not trace.get("ok"):
        return _error("compiled_intent_required")
    objective = str(trace.get("objective") or "").strip()
    task = {
        "task_id": "compiled_bulk_intent",
        "title": "Topology localized from bulk intention",
        "summary": objective[:320],
        "spatial_command": "inspect exact files and symbols localized from the compiled bulk intention",
        "intent_slots": dict((trace.get("six_slot_packet") or {}).get("slots") or {}),
        "seed_files": [str(value) for value in trace.get("likely_files", []) if str(value)][:10],
        "seed_symbols": [str(value) for value in trace.get("likely_symbols", []) if str(value)][:10],
        "keywords": [str(value) for value in trace.get("keywords", []) if str(value)][:16],
        "acceptance_criteria": [
            "Show only the exact CODEMAP neighborhood localized from the human intention.",
            "Keep visual relationships separate from exact source and verifier authority.",
            "Prepare bounded context only; do not invoke a model or mutate source.",
        ],
        "prohibited_actions": [
            "private_memory_exposure",
            "secret_access",
            "automatic_commit",
            "automatic_push",
            "automatic_pull_request",
            "automatic_merge",
        ],
        "presenter_cue": (
            "Aura converted ordinary bulk language into a bounded repository neighborhood before "
            "any replaceable LLM worker was contacted."
        ),
    }
    selected = _select_seed_node_ids(topology, task)
    if not selected:
        return _error("no_grounded_intent_nodes", task=task)
    return _workspace_packet(
        topology,
        selected,
        depth=max(0, min(2, int(depth))),
        instruction=task["spatial_command"],
        task=task,
    )


def _error(error: str, **extra: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": error,
        **extra,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }
