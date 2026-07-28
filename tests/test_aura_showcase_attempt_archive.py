"""Contracts for preserving successful, denied, and failed Arena attempts."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
NODE_CONTEXT = {
    "stage_hint": "ACT",
    "objective": "Repair the selected renderer without expanding scope.",
    "node_context": {
        "selected_node": {
            "id": "node:aura_showcase/civic.js:refreshMap",
            "label": "refreshMap",
            "file_path": "aura_showcase/civic.js",
            "symbol": "refreshMap",
            "line_range": [120, 180],
        },
        "dependencies": ["drawMap"],
        "callers": ["renderCivicGuide"],
        "tests": ["tests/test_aura_showcase_guided_interface.py"],
    },
    "gate_dialogue": {
        "proposal_id": "GDP-test",
        "status": "APPROVED_FOR_NEXT_GUARDED_GATE",
        "human_comment": "Preserve this failed patch so I can refine it later.",
        "aura_response": "The patch remains proposal-only and must pass the verifier.",
    },
}
FAILED_DIFF = """diff --git a/aura_showcase/civic.js b/aura_showcase/civic.js
--- a/aura_showcase/civic.js
+++ b/aura_showcase/civic.js
@@ -1,2 +1,3 @@
 function refreshMap() {
+  return staleResponse;
 }
"""


def test_failed_attempt_is_persisted_and_copyable(tmp_path):
    from aura_arena_attempt_archive import ArenaAttemptArchive

    archive = ArenaAttemptArchive(REPO_ROOT, db_path=tmp_path / "attempts.db")
    try:
        recorded = archive.record(
            arena_id="human_agent",
            route="/api/human-agent/workflow/action",
            request={"action_id": "stage_patch", "payload": {"candidate_diff": FAILED_DIFF}},
            result={
                "ok": False,
                "status": "DENIED",
                "action_id": "stage_patch",
                "message": "Candidate patch was rejected by the staging gate.",
                "missing_evidence": ["acceptable_staged_patch"],
                "details": {"stderr": "patch does not apply"},
            },
            workflow_state={
                "workflow_id": "HWF-test",
                "current_phase": "ACT",
                "objective": "Repair the selected renderer.",
            },
            archive_context=NODE_CONTEXT,
        )
        assert recorded["ok"] is True
        assert recorded["failure_preserved"] is True
        assert recorded["has_candidate_diff"] is True
        assert recorded["verified"] is False
        assert recorded["production_authority"] is False

        rows = archive.list(failures_only=True)
        assert len(rows) == 1
        assert rows[0]["status"] == "DENIED"
        assert rows[0]["selected_node"]["symbol"] == "refreshMap"
        assert "acceptable_staged_patch" in rows[0]["failure_summary"]

        artifact = archive.get(recorded["artifact_id"])
        assert artifact is not None
        assert artifact["candidate_diff"] == FAILED_DIFF
        assert artifact["copy_diff"] == FAILED_DIFF
        assert "# Aura Arena Attempt" in artifact["copy_text"]
        assert "## Candidate diff" in artifact["copy_text"]
        assert "## Human gate intent" in artifact["copy_text"]
        assert "patch does not apply" in artifact["copy_text"]
        assert artifact["archived_output_authority"] is False
        assert artifact["human_review_required_before_reuse"] is True
    finally:
        archive.close()


def test_archive_sanitizes_secrets_and_private_reasoning(tmp_path):
    from aura_arena_attempt_archive import ArenaAttemptArchive

    archive = ArenaAttemptArchive(REPO_ROOT, db_path=tmp_path / "attempts.db")
    try:
        recorded = archive.record(
            arena_id="coding_workbench",
            route="/api/coding-workbench/action",
            request={
                "action_id": "propose_patch",
                "payload": {
                    "api_key": "sk-this-should-never-be-stored-123456789",
                    "candidate_diff": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz",
                    "chain_of_thought": "private scratchpad",
                },
            },
            result={"ok": False, "status": "FAILED", "stderr": "worker failed"},
            workflow_state={"workflow_id": "CW-test", "current_phase": "ACT"},
        )
        artifact = archive.get(recorded["artifact_id"])
        encoded = json.dumps(artifact, sort_keys=True)
        assert "sk-this-should-never" not in encoded
        assert "abcdefghijklmnopqrstuvwxyz" not in encoded
        assert "private scratchpad" not in encoded
        assert "[REDACTED]" in encoded
        assert artifact["redactions"]
    finally:
        archive.close()


def test_showcase_archive_routes_return_summary_and_full_artifact(tmp_path):
    from aura_arena_attempt_archive import ArenaAttemptArchive
    from aura_showcase_server import dispatch_showcase_request

    archive = ArenaAttemptArchive(REPO_ROOT, db_path=tmp_path / "attempts.db")
    try:
        recorded = archive.record(
            arena_id="human_agent",
            route="/api/human-agent/workflow/action",
            request={"action_id": "verify_patch"},
            result={"ok": False, "status": "DENIED", "message": "Verifier failed."},
            workflow_state={"workflow_id": "HWF-test", "current_phase": "PROVE"},
            archive_context=NODE_CONTEXT,
        )
        state = SimpleNamespace(attempt_archive=archive)

        status, _, raw = dispatch_showcase_request(
            state,
            "GET",
            "/api/showcase/human/attempts?failures_only=true&limit=5",
        )
        listing = json.loads(raw)
        assert status == 200
        assert listing["attempt_count"] == 1
        assert listing["attempts"][0]["artifact_id"] == recorded["artifact_id"]
        assert listing["archived_output_authority"] is False

        status, _, raw = dispatch_showcase_request(
            state,
            "GET",
            f"/api/showcase/human/attempts/{recorded['artifact_id']}",
        )
        detail = json.loads(raw)
        assert status == 200
        assert detail["artifact"]["copy_text"]
        assert detail["artifact"]["production_authority"] is False
    finally:
        archive.close()


def test_browser_archive_exposes_inspect_and_copy_controls():
    source = (REPO_ROOT / "aura_showcase" / "attempt-archive.js").read_text(encoding="utf-8")
    assert "_arena_archive_context" in source
    assert "/api/showcase/human/attempts" in source
    assert "Copy full artifact" in source
    assert "Copy diff" in source
    assert "Show failed only" in source
    assert "navigator.clipboard" in source
    assert "archived refactoring evidence" in source.lower() or "refactoring artifacts" in source.lower()


def test_attempt_archive_rejects_oversized_aggregate_record(tmp_path):
    from aura_arena_attempt_archive import ArenaAttemptArchive

    archive = ArenaAttemptArchive(REPO_ROOT, db_path=tmp_path / "attempts.db")
    try:
        with pytest.raises(ValueError, match="record exceeds"):
            archive.record(
                arena_id="coding",
                route="bounded-record",
                request={"first": "x" * 13_000_000, "second": "y" * 13_000_000},
                result={"ok": False},
            )
    finally:
        archive.close()
