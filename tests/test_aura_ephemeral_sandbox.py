"""Tests for Aura Ephemeral Sandbox."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest
import tempfile

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_ephemeral_sandbox import (
    prepare_sandbox, execute_builtin_adapter, execute_wasm_component,
    revoke_capabilities, destroy_sandbox, verify_dissolution,
    check_path_traversal, check_symlink_escape, BUILTIN_ADAPTERS,
)


class TestSandbox:
    def test_prepare_sandbox(self):
        manifest = {"organ_id": "EORG-test", "resource_budget": {"wall_time_ms": 30000}}
        result = prepare_sandbox(manifest)
        assert result["ok"] is True
        assert "temp_dir" in result
        assert result["wasmtime_available"] is False  # Expected in test env
        # Cleanup
        destroy_sandbox(result["temp_dir"])

    def test_builtin_adapter_allowlist(self):
        assert "resolve_capabilities" in BUILTIN_ADAPTERS
        assert "search_code" in BUILTIN_ADAPTERS
        assert "read_slice" in BUILTIN_ADAPTERS
        assert "render_ui_schema" in BUILTIN_ADAPTERS

    def test_unknown_adapter_rejected(self):
        result = execute_builtin_adapter("nonexistent_adapter")
        assert result["ok"] is False

    def test_render_ui_schema_declarative(self):
        result = execute_builtin_adapter("render_ui_schema", params={})
        assert result["ok"] is True
        assert result["executable"] is False

    def test_unknown_ui_component_rejected(self):
        result = execute_builtin_adapter("render_ui_schema", params={"component_types": ["evil_script"]})
        assert result["ok"] is False

    def test_wasm_component_fails_closed(self):
        result = execute_wasm_component({"component_id": "test"})
        assert result["ok"] is False
        assert "NOT_OPERATIONAL" in result.get("status", "")

    def test_no_silent_native_fallback(self):
        result = execute_wasm_component({"component_id": "test"})
        # Must NOT say "native" as a fallback
        assert "native" not in result.get("error", "").lower() or "not" in result.get("error", "").lower()

    def test_revoke_capabilities(self):
        result = revoke_capabilities("EORG-test")
        assert result["ok"] is True

    def test_destroy_sandbox(self):
        tmp = tempfile.mkdtemp()
        result = destroy_sandbox(tmp)
        assert result["ok"] is True
        assert result["temp_dir_removed"] is True

    def test_verify_dissolution(self):
        # Use a path that definitely doesn't exist
        import tempfile, os
        nonexistent = os.path.join(tempfile.gettempdir(), "definitely_nonexistent_eorg_test_dir_12345")
        result = verify_dissolution(nonexistent, True)
        assert result["ok"] is True

    def test_path_traversal_blocked(self):
        assert check_path_traversal("../../etc/passwd", "/tmp/safe") is True

    def test_path_within_temp_ok(self):
        tmp = tempfile.mkdtemp()
        assert check_path_traversal(f"{tmp}/audit.json", tmp) is False
        destroy_sandbox(tmp)

    def test_resource_budget_enforced(self):
        from aura_ephemeral_sandbox import enforce_resource_budget
        receipt = {"resource_limits": {"wall_time_ms": 1000, "output_bytes": 1000, "tool_calls": 5}}
        result = enforce_resource_budget(receipt, elapsed_ms=500, output_bytes=500, tool_calls=3)
        assert result["ok"] is True
        result = enforce_resource_budget(receipt, elapsed_ms=2000, output_bytes=500, tool_calls=3)
        assert result["ok"] is False
        assert "wall_time_ms" in result["exceeded"]

    def test_invariants(self):
        result = execute_builtin_adapter("render_ui_schema", params={})
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False
