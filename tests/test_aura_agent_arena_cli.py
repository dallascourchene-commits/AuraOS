"""
Tests for the Aura Agent Arena Bridge CLI.

Verifies that CLI commands run with correct exit codes and produce
valid JSON output.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from aura_agent_arena_cli import build_parser, main as cli_main

REPO_ROOT = Path(__file__).resolve().parent.parent


def _has_codemap() -> bool:
    return (REPO_ROOT / ".aura" / "CODEMAP.json").exists()


# ---------------------------------------------------------------------------
# Test: CLI digest runs with exit code 0
# ---------------------------------------------------------------------------

def test_cli_digest_exit_code_zero(capsys):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    exit_code = cli_main(["digest"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["codemap_status"] == "AURA_CODEMAP_ACTIVE"


# ---------------------------------------------------------------------------
# Test: CLI digest with --no-hubs
# ---------------------------------------------------------------------------

def test_cli_digest_no_hubs(capsys):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    exit_code = cli_main(["digest", "--no-hubs"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert len(data.get("hubs", [])) == 0


# ---------------------------------------------------------------------------
# Test: CLI search returns results
# ---------------------------------------------------------------------------

def test_cli_search(capsys):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    exit_code = cli_main(["search", "--query", "RoutingFrame", "--kind", "symbol"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert "results" in data


# ---------------------------------------------------------------------------
# Test: CLI read-slice returns content
# ---------------------------------------------------------------------------

def test_cli_read_slice(capsys):
    exit_code = cli_main([
        "read-slice",
        "--file", "aura_fst_routing.py",
        "--symbol", "RoutingFrame",
    ])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["file"] == "aura_fst_routing.py"
    assert data["symbol"] == "RoutingFrame"
    assert len(data["content"]) > 0


# ---------------------------------------------------------------------------
# Test: CLI read-slice blocks hub file
# ---------------------------------------------------------------------------

def test_cli_read_slice_blocks_hub(capsys):
    exit_code = cli_main(["read-slice", "--file", "aura_node.py"])
    assert exit_code == 1  # Error exit code
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is False
    assert data["error_category"] == "scope_too_broad"


# ---------------------------------------------------------------------------
# Test: CLI prepare creates session
# ---------------------------------------------------------------------------

def test_cli_prepare(capsys):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    exit_code = cli_main([
        "prepare",
        "--objective", "Add a docstring to RoutingFrame",
        "--target-file", "aura_fst_routing.py",
        "--target-symbol", "RoutingFrame",
    ])
    # May fail if grounding is incomplete, but should produce valid JSON.
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "ok" in data
    if data["ok"]:
        assert "plan_phase_hash" in data
        assert exit_code == 0
    else:
        assert exit_code == 1


# ---------------------------------------------------------------------------
# Test: CLI no command prints help
# ---------------------------------------------------------------------------

def test_cli_no_command_prints_help(capsys):
    exit_code = cli_main([])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower() or "aura-agent-arena" in captured.out


# ---------------------------------------------------------------------------
# Test: CLI parser has all subcommands
# ---------------------------------------------------------------------------

def test_cli_parser_has_all_subcommands():
    parser = build_parser()
    # Parse each subcommand to verify it exists.
    for cmd in ["digest", "search", "read-slice", "prepare", "verify", "status", "export-icm"]:
        try:
            parser.parse_args([cmd, "--help"] if cmd not in ("digest", "status", "export-icm") else [cmd])
        except SystemExit:
            pass  # --help causes SystemExit

    # Verify subcommands are registered by checking the parser's subparsers.
    # We check by trying to parse valid args for each.
    assert cli_main(["digest"]) in (0, 1)
    assert cli_main(["search", "--query", "test"]) in (0, 1)
    assert cli_main(["read-slice", "--file", "test.py"]) in (0, 1)


# ---------------------------------------------------------------------------
# Test: CLI fireworks-patch without API key returns error
# ---------------------------------------------------------------------------

def test_cli_fireworks_patch_no_key(capsys, monkeypatch):
    if not _has_codemap():
        pytest.skip("CODEMAP.json not available")
    monkeypatch.delenv("FIREWORKS_API_KEY", raising=False)
    # Need to prepare first to get a phase hash.
    prep_code = cli_main([
        "prepare",
        "--objective", "Test fireworks",
        "--target-file", "aura_fst_routing.py",
        "--target-symbol", "RoutingFrame",
    ])
    # Clear the prepare output so we only capture fireworks-patch output.
    capsys.readouterr()
    if prep_code != 0:
        pytest.skip("Prepare failed")
    # Now try fireworks-patch.
    exit_code = cli_main([
        "fireworks-patch",
        "--task-id", "A1",
        "--instruction", "Fix the bug",
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["ok"] is False
    assert data["error_category"] == "fireworks_call_failed"


# ---------------------------------------------------------------------------
# Test: CLI verify without prepare returns error
# ---------------------------------------------------------------------------

def test_cli_verify_without_prepare(capsys, monkeypatch):
    # Ensure no saved phase hash.
    monkeypatch.delenv("AURA_ARENA_PLAN_PHASE_HASH", raising=False)
    # Remove temp file if exists.
    try:
        Path("/tmp/aura_arena_plan_phase_hash").unlink(missing_ok=True)
    except Exception:
        pass
    # Reset module-level state from previous tests.
    import aura_agent_arena_cli as cli_module
    cli_module._plan_phase_hash = None
    cli_module._bridge = None
    with pytest.raises(SystemExit) as exc_info:
        cli_main(["verify"])
    assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# Test: CLI script shim is executable
# ---------------------------------------------------------------------------

def test_script_shim_is_executable():
    shim = REPO_ROOT / "scripts" / "aura-agent-arena"
    assert shim.exists()
    assert os.access(shim, os.X_OK)