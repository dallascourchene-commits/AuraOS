"""
Aura Live Architect Cockpit Adapter — stage/review/merge/purge plan generator.

Produces plans only — no mutation, no destructive execution.
Dependencies: stdlib only. All Aura imports are lazy.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
ADAPTER_VERSION = "AURA_LIVE_ARCHITECT_COCKPIT_ADAPTER_V1"


def live_stage_review_packet(task_id: str, repo_root: str = ".") -> dict:
    """Create a stage review plan (not execution)."""
    review_plan = {"steps": ["review_patch", "check_boundaries", "verify_tests", "check_scope"]}
    try:
        from aura_live_architect import ArchitectFusionCouncil
        # Try to get real review data
    except Exception:
        pass
    return {"ok": True, "task_id": task_id, "review_plan": review_plan,
             "advisory_only": True, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY,
             "note": "Live Architect adapter creates plans only. No mutation."}


def live_stage_merge_plan(task_id: str, repo_root: str = ".") -> dict:
    """Create merge plan (not execution)."""
    return {"ok": True, "task_id": task_id,
             "merge_plan": {"steps": ["verify_all_tests_pass", "human_approval", "merge_to_target"]},
             "advisory_only": True, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY,
             "note": "Merge plan only. Human approval required."}


def live_stage_purge_plan(task_id: str, repo_root: str = ".") -> dict:
    """Create purge plan (not execution)."""
    return {"ok": True, "task_id": task_id,
             "purge_plan": {"steps": ["identify_staged_patches", "human_approval", "purge"]},
             "advisory_only": True, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY,
             "note": "Purge plan only. Does not delete anything."}


def live_architect_to_workflow_gate(review_packet: dict, repo_root: str = ".") -> dict:
    """Map review packet to workflow gate state."""
    gate = "PATCH_PROPOSED"
    if review_packet.get("review_plan", {}).get("tests_pass"):
        gate = "VERIFIED"
    return {"ok": True, "gate_state": gate, "patch_authority": PATCH_AUTHORITY,
             "vsa_patch_authority": VSA_PATCH_AUTHORITY}
