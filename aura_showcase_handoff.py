"""Exact Civic-to-Human-Agent handoff for the Winnipeg showcase.

The handoff imports repository facts, hashes, candidate options, and a review-only
patch proposal into the existing Human Agent workflow.  It does not apply the
patch, run a merge, or treat the visual map as source authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from aura_civic_guided_project import get_guide

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def _hash_file(path: Path) -> str:
    return hashlib.blake2b(path.read_bytes(), digest_size=16).hexdigest()


def _line_for(path: Path, marker: str) -> int | None:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if marker in line:
            return number
    return None


def build_handoff_packet(repo_root: str | Path, session_id: str) -> dict[str, Any]:
    guide = get_guide(session_id)
    if not guide.get("ok"):
        return guide
    issue = dict(guide.get("demo_issue") or {})
    root = Path(repo_root).resolve()
    requested_files = list(issue.get("files") or [])
    markers = {
        "aura_showcase/app.js": "INITIAL_MAP_ZOOM",
        "aura_civic_map.py": '"candidate": 12',
        "aura_civic_projects.py": "WP-CANDIDATE-1",
        "tests/test_aura_showcase_guided_project.py": "test_candidate_is_hidden_at_11_and_visible_at_12",
    }
    exact_files: list[dict[str, Any]] = []
    missing_files: list[str] = []
    for relative in requested_files:
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            missing_files.append(relative)
            continue
        if not path.is_file():
            missing_files.append(relative)
            continue
        marker = markers.get(relative, "")
        line = _line_for(path, marker) if marker else None
        exact_files.append({
            "file": relative,
            "source_hash": _hash_file(path),
            "marker": marker,
            "line_range": [line, line] if line else [],
            "truth_class": "EXACT_REPOSITORY_FACTS",
        })

    candidate_diff = """diff --git a/aura_showcase/app.js b/aura_showcase/app.js
--- a/aura_showcase/app.js
+++ b/aura_showcase/app.js
@@
 const INITIAL_MAP_ZOOM = 11;
+const CANDIDATE_FOCUS_ZOOM = 12;
@@
-  await refreshMap();
+  if (guide.current_step?.step_id === 'EXPLORE_MAP') {
+    mapZoom = CANDIDATE_FOCUS_ZOOM;
+  }
+  await refreshMap();
"""
    objective = (
        "Investigate why the Winnipeg Pathways candidate pilot location is hidden when the Civic Arena opens. "
        "Determine whether this is intended map policy, a fixture problem, or a presentation default mismatch. "
        "Preserve the general privacy and zoom policy, stage changes only, and require human review."
    )
    return {
        "ok": not missing_files,
        "handoff_version": "AURA_SHOWCASE_HANDOFF_V1",
        "session_id": session_id,
        "issue": issue,
        "objective": objective,
        "grounding": {
            "localized_files": [item["file"] for item in exact_files],
            "localized_symbols": ["INITIAL_MAP_ZOOM", "DEFAULT_ZOOM_BY_TYPE", "WINNIPEG_PATHWAYS"],
            "line_ranges": exact_files,
            "source_hashes": {item["file"]: item["source_hash"] for item in exact_files},
            "truth_class": "EXACT_REPOSITORY_FACTS",
            "grounding": "grounded" if not missing_files else "NEEDS_GROUNDING",
        },
        "test_targets": list(issue.get("tests") or []),
        "candidate_options": list(issue.get("candidate_options") or []),
        "recommended_option": issue.get("recommended_option", ""),
        "candidate_diff": candidate_diff,
        "missing_files": missing_files,
        "production_mutation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def import_handoff_into_workflow(workflow: Any, repo_root: str | Path, session_id: str) -> dict[str, Any]:
    packet = build_handoff_packet(repo_root, session_id)
    if not packet.get("ok"):
        return packet
    framed = workflow.execute_guarded("set_objective", {"objective": packet["objective"]})
    if not framed.get("ok"):
        return {
            "ok": False,
            "error": "workflow_objective_denied",
            "workflow_result": framed,
            "handoff": packet,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    workflow.evidence.update({
        "grounding": packet["grounding"],
        "affected_files": packet["grounding"]["localized_files"],
        "test_targets": packet["test_targets"],
        "candidate_diff": packet["candidate_diff"],
    })
    if hasattr(workflow, "_event"):
        workflow._event("showcase_handoff", f"Imported exact Civic issue packet for {session_id}")
    return {
        "ok": True,
        "handoff": packet,
        "workflow": workflow.get_state(),
        "next_actions": ["prepare_capsule", "stage_patch", "export_handoff"],
        "note": "Exact evidence was imported. No patch was applied and production remains unchanged.",
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


__all__ = ["build_handoff_packet", "import_handoff_into_workflow"]
