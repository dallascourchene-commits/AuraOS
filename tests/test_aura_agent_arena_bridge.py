"""
Tests for the Aura Agent Arena Bridge.

These tests exercise the bridge against the real repo's CODEMAP and
architect loop pipeline.  They verify safety invariants, structured errors,
and that VSA/JSpace/ST3GG fields always declare vsa_patch_authority=false.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from aura_agent_arena_bridge import (
    BRIDGE_VERSION,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    AuraAgentArenaBridge,
)
from aura_agent_arena_errors import (
    ERROR_CATEGORIES,
    ERROR_SCHEMA_VERSION,
    ArenaBridgeError,
    is_error_packet,
    make_error_packet,
)
from aura_agent_arena_fireworks import fireworks_patch_worker, is_fireworks_available

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def bridge() -> AuraAgentArenaBridge:
    return AuraAgentArenaBridge(repo_root=REPO_ROOT)


def _has_codemap() -> bool:
    return (REPO_ROOT / ".aura" / "CODEMAP.json").exists()


# ---------------------------------------------------------------------------
# Test 1: aura_repo_digest returns CODEMAP status and no huge raw file content
# ---------------------------------------------------------------------------

def test_repo_digest_returns_codemap_status(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    result = bridge.aura_repo_digest()
    assert result["ok"] is True
    assert result["version"] == BRIDGE_VERSION
    assert result["codemap_status"] == "AURA_CODEMAP_ACTIVE"
    assert "file_count" in result
    assert isinstance(result["file_count"], int)
    assert result["file_count"] > 0
    # No huge raw file content.
    result_str = json.dumps(result)
    assert len(result_str) < 10000  # digest should be tiny
    # No raw file contents.
    assert "raw_content" not in result
    assert "file_contents" not in result


# ---------------------------------------------------------------------------
# Test 2: aura_prepare_arena creates plan, grounding, shadow, arena transaction
# ---------------------------------------------------------------------------

def test_prepare_arena_creates_plan_and_arena(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    result = bridge.aura_prepare_arena(
        objective="Add a docstring to AuraCodingArenaRouter",
        target_file="aura_fst_routing.py",
        target_symbol="AuraCodingArenaRouter",
    )
    assert result["ok"] is True
    assert "plan_phase_hash" in result
    assert result["plan_phase_hash"]
    assert len(result["act_capsules"]) > 0
    assert "grounding_evidence" in result
    assert "shadow_findings" in result
    assert "routing_decisions" in result
    assert "liquid_arena_lease_count" in result
    assert "builder_patch_authorized" in result
    # Session should be stored.
    session = bridge._get_session(result["plan_phase_hash"])
    assert session is not None
    assert session["arena"] is not None


# ---------------------------------------------------------------------------
# Test 3: aura_get_micro_context returns target file/symbol/line/test context
# ---------------------------------------------------------------------------

def test_get_micro_context_returns_grounding(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Add a docstring to AuraCodingArenaRouter",
        target_file="aura_fst_routing.py",
        target_symbol="AuraCodingArenaRouter",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed — likely missing grounding")
    phase_hash = prep["plan_phase_hash"]
    task_id = prep["act_capsules"][0]["task_id"]

    result = bridge.aura_get_micro_context(
        plan_phase_hash=phase_hash,
        task_id=task_id,
    )
    assert result["ok"] is True
    assert result["task_id"] == task_id
    assert result["target_file"] == "aura_fst_routing.py"
    assert result["target_symbol"] == "AuraCodingArenaRouter"
    assert "line_ranges" in result
    assert "tests" in result
    assert "route_decision" in result
    assert result["patch_authority"] == PATCH_AUTHORITY
    assert result["vsa_patch_authority"] is False


# ---------------------------------------------------------------------------
# Test 4: aura_read_slice refuses oversized hub file reads
# ---------------------------------------------------------------------------

def test_read_slice_refuses_hub_file(bridge: AuraAgentArenaBridge):
    result = bridge.aura_read_slice(file="aura_node.py")
    assert result["ok"] is False
    assert result["error_category"] == "scope_too_broad"
    assert "aura_search_code" in result["next_allowed_tools"]


# ---------------------------------------------------------------------------
# Test 5: aura_read_slice returns bounded symbol slice
# ---------------------------------------------------------------------------

def test_read_slice_returns_symbol_slice(bridge: AuraAgentArenaBridge):
    result = bridge.aura_read_slice(
        file="aura_fst_routing.py",
        symbol="RoutingFrame",
    )
    assert result["ok"] is True
    assert result["file"] == "aura_fst_routing.py"
    assert result["symbol"] == "RoutingFrame"
    assert result["line_start"] > 0
    assert result["line_end"] >= result["line_start"]
    assert result["total_lines"] > 0
    assert len(result["content"]) > 0
    # Should be bounded.
    assert result["line_end"] - result["line_start"] + 1 <= 120


# ---------------------------------------------------------------------------
# Test 6: aura_stage_patch rejects empty diff
# ---------------------------------------------------------------------------

def test_stage_patch_rejects_empty_diff(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Test empty diff rejection",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed")
    phase_hash = prep["plan_phase_hash"]
    task_id = prep["act_capsules"][0]["task_id"]

    result = bridge.aura_stage_patch(
        plan_phase_hash=phase_hash,
        task_id=task_id,
        diff="",
        affected_files=["aura_fst_routing.py"],
    )
    assert result["ok"] is False
    assert result["error_category"] == "empty_patch"


# ---------------------------------------------------------------------------
# Test 7: aura_stage_patch rejects diff touching undeclared file
# ---------------------------------------------------------------------------

def test_stage_patch_rejects_undeclared_file(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Test undeclared file rejection",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed")
    phase_hash = prep["plan_phase_hash"]
    task_id = prep["act_capsules"][0]["task_id"]

    # Diff touches a file not in affected_files.
    diff = """diff --git a/aura_fst_routing.py b/aura_fst_routing.py
index 1234567..abcdefg 100644
--- a/aura_fst_routing.py
+++ b/aura_fst_routing.py
@@ -1,1 +1,2 @@
- old line
+ new line
"""
    result = bridge.aura_stage_patch(
        plan_phase_hash=phase_hash,
        task_id=task_id,
        diff=diff,
        affected_files=["aura_context_crusher.py"],  # different file
    )
    assert result["ok"] is False
    # Should be rejected for undeclared file or cross-boundary.
    assert result["error_category"] in (
        "patch_outside_arena",
        "unparseable_diff",
        "missing_grounding",
    )


# ---------------------------------------------------------------------------
# Test 8: aura_stage_patch rejects patch outside arena lease
# ---------------------------------------------------------------------------

def test_stage_patch_rejects_outside_lease(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Test lease violation",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed")
    phase_hash = prep["plan_phase_hash"]
    task_id = prep["act_capsules"][0]["task_id"]

    # Diff touches a file completely outside the arena.
    diff = """diff --git a/aura_node.py b/aura_node.py
index 1234567..abcdefg 100644
--- a/aura_node.py
+++ b/aura_node.py
@@ -1,1 +1,2 @@
- old line
+ new line
"""
    result = bridge.aura_stage_patch(
        plan_phase_hash=phase_hash,
        task_id=task_id,
        diff=diff,
        affected_files=["aura_node.py"],
    )
    assert result["ok"] is False


# ---------------------------------------------------------------------------
# Test 9: aura_verify_arena returns structured failures and compressed logs
# ---------------------------------------------------------------------------

def test_verify_arena_returns_structured_result(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Test verify without patches",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed")
    phase_hash = prep["plan_phase_hash"]

    result = bridge.aura_verify_arena(
        plan_phase_hash=phase_hash,
        test_scope="focused",
    )
    # Without any staged patches, verification should fail.
    assert "ok" in result
    assert "stage" in result
    assert "checks" in result
    assert "failures" in result
    assert "compressed_log" in result
    assert "next_action" in result
    assert result["next_action"] in (
        "promote_hotswap",
        "repair_with_builder",
        "escalate_to_judge",
        "wait_for_builder",
    )


# ---------------------------------------------------------------------------
# Test 10: aura_repair_packet returns minimal repair context
# ---------------------------------------------------------------------------

def test_repair_packet_returns_minimal_context(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    prep = bridge.aura_prepare_arena(
        objective="Test repair packet",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if not prep["ok"]:
        pytest.skip("Prepare failed")
    phase_hash = prep["plan_phase_hash"]
    task_id = prep["act_capsules"][0]["task_id"]

    # Run verify first (will fail without patches).
    bridge.aura_verify_arena(plan_phase_hash=phase_hash)

    result = bridge.aura_repair_packet(
        plan_phase_hash=phase_hash,
        task_id=task_id,
    )
    assert result["ok"] is True
    assert result["task_id"] == task_id
    assert "failed_check" in result
    assert "compressed_error" in result
    assert "allowed_files" in result
    assert "do_not_touch" in result
    assert result["required_response"] == "unified diff only"


# ---------------------------------------------------------------------------
# Test 11: Fireworks worker is skipped safely when FIREWORKS_API_KEY is absent
# ---------------------------------------------------------------------------

def test_fireworks_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    result = fireworks_patch_worker(
        task_id="A1",
        compressed_context="some context",
        instruction="fix the bug",
    )
    assert result["ok"] is False
    assert result["error_category"] == "fireworks_call_failed"
    assert "FIREWORKS_API_KEY" in result["message"]
    assert is_fireworks_available() is False


# ---------------------------------------------------------------------------
# Test 12: CLI digest runs with exit code 0
# ---------------------------------------------------------------------------

def test_cli_digest_exit_code_zero():
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    from aura_agent_arena_cli import main as cli_main

    exit_code = cli_main(["digest"])
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Test 13: MCP tool list contains the expected Aura Arena tools
# ---------------------------------------------------------------------------

def test_mcp_tool_list_contains_expected_tools():
    from aura_agent_arena_mcp import TOOL_DEFINITIONS

    tool_names = {t["name"] for t in TOOL_DEFINITIONS}
    expected = {
        "aura_repo_digest",
        "aura_prepare_arena",
        "aura_get_micro_context",
        "aura_search_code",
        "aura_read_slice",
        "aura_stage_patch",
        "aura_verify_arena",
        "aura_repair_packet",
        "aura_hotswap_status",
        "aura_export_icm",
        "aura_fireworks_patch_worker",
    }
    assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"


# ---------------------------------------------------------------------------
# Test 14: No tool output includes raw private memory fields
# ---------------------------------------------------------------------------

def test_no_raw_private_memory_in_output(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    # Test digest.
    digest = bridge.aura_repo_digest()
    digest_str = json.dumps(digest)
    for forbidden in ("raw_snapshot_bytes", "raw_sidecar_bytes", "raw_private_memory", "api_key", "password"):
        assert forbidden not in digest_str.lower(), f"Forbidden field '{forbidden}' in digest output"

    # Test read_slice.
    slice_result = bridge.aura_read_slice(file="aura_fst_routing.py", symbol="RoutingFrame")
    slice_str = json.dumps(slice_result)
    for forbidden in ("raw_snapshot_bytes", "raw_sidecar_bytes", "raw_private_memory", "api_key", "password"):
        assert forbidden not in slice_str.lower(), f"Forbidden field '{forbidden}' in read_slice output"


# ---------------------------------------------------------------------------
# Test 15: ST3GG/JSpace/VSA fields always declare vsa_patch_authority=false
# ---------------------------------------------------------------------------

def test_vsa_patch_authority_always_false(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    # Digest.
    digest = bridge.aura_repo_digest()
    assert digest.get("vsa_patch_authority") is False
    assert digest.get("patch_authority") == PATCH_AUTHORITY

    # Read slice.
    slice_result = bridge.aura_read_slice(file="aura_fst_routing.py", symbol="RoutingFrame")
    assert slice_result.get("vsa_patch_authority") is False

    # Search.
    search_result = bridge.aura_search_code(query="RoutingFrame", search_kind="symbol")
    assert search_result.get("vsa_patch_authority") is False

    # Prepare.
    prep = bridge.aura_prepare_arena(
        objective="Test VSA authority",
        target_file="aura_fst_routing.py",
        target_symbol="RoutingFrame",
    )
    if prep["ok"]:
        assert prep.get("vsa_patch_authority") is False
        task_id = prep["act_capsules"][0]["task_id"]
        ctx = bridge.aura_get_micro_context(
            plan_phase_hash=prep["plan_phase_hash"],
            task_id=task_id,
        )
        assert ctx.get("vsa_patch_authority") is False


# ---------------------------------------------------------------------------
# Additional tests: error system
# ---------------------------------------------------------------------------

def test_error_packet_structure():
    packet = make_error_packet("empty_patch", "No diff body provided.")
    assert packet["ok"] is False
    assert packet["error_schema_version"] == ERROR_SCHEMA_VERSION
    assert packet["error_category"] == "empty_patch"
    assert "message" in packet
    assert "repair_hint" in packet
    assert "next_allowed_tools" in packet
    assert "error_id" in packet
    assert is_error_packet(packet) is True


def test_error_categories_complete():
    expected = {
        "missing_grounding",
        "target_symbol_unresolved",
        "scope_too_broad",
        "missing_tests",
        "patch_outside_arena",
        "patch_outside_task",
        "lease_scope_violation",
        "unparseable_diff",
        "empty_patch",
        "test_failed",
        "ast_parse_failed",
        "codemap_refresh_failed",
        "fireworks_call_failed",
        "mcp_protocol_error",
    }
    assert set(ERROR_CATEGORIES) == expected


def test_bridge_error_to_packet():
    err = ArenaBridgeError("test_failed", "Tests failed.", repair_hint="Fix the test.")
    packet = err.to_packet()
    assert packet["error_category"] == "test_failed"
    assert packet["message"] == "Tests failed."
    assert packet["repair_hint"] == "Fix the test."


def test_read_slice_rejects_absolute_path(bridge: AuraAgentArenaBridge):
    result = bridge.aura_read_slice(file="/etc/passwd")
    assert result["ok"] is False
    assert result["error_category"] in ("patch_outside_arena", "missing_grounding")


def test_search_code_returns_results(bridge: AuraAgentArenaBridge):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    result = bridge.aura_search_code(query="AuraCodingArenaRouter", search_kind="symbol")
    assert result["ok"] is True
    assert len(result["results"]) > 0
    # Results should be cards, not full files.
    for r in result["results"]:
        assert "file" in r
        assert "symbol" in r
        assert "line_range" in r
        assert "reason" in r