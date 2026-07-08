"""
Aura Agent Arena Bridge — Structured Error System.

Every tool failure returns a machine-readable error packet so external agents
can repair and retry without guessing.  VSA/JSpace/ST3GG are advisory only;
exact source files, CODEMAP facts, tests, and verifier gates are authority.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

ERROR_SCHEMA_VERSION = "AURA_AGENT_ARENA_ERROR_V1"

# ---------------------------------------------------------------------------
# Error categories — kept in sync with the task specification
# ---------------------------------------------------------------------------

ERROR_CATEGORIES = (
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
)

_ERROR_CATEGORY_SET = frozenset(ERROR_CATEGORIES)

# Map architect-loop shadow finding types to bridge error categories.
_SHADOW_TYPE_TO_CATEGORY: dict[str, str] = {
    "missing_grounding": "missing_grounding",
    "fake_symbol": "target_symbol_unresolved",
    "weak_codemap_grounding": "missing_grounding",
    "act_capsule_too_large": "scope_too_broad",
    "missing_test": "missing_tests",
    "cross_boundary_patch": "patch_outside_arena",
    "cross_task_boundary_patch": "patch_outside_task",
    "lease_scope_violation": "lease_scope_violation",
    "unparseable_patch_diff": "unparseable_diff",
    "empty_patch": "empty_patch",
    "undeclared_diff_file": "patch_outside_arena",
    "declared_file_missing_from_diff": "unparseable_diff",
    "arena_route_blocks_builder": "missing_grounding",
    "unassigned_patch_task": "patch_outside_task",
    "missing_patch_files": "unparseable_diff",
}

# Map verification failure stages to error categories.
_VERIFY_STAGE_TO_CATEGORY: dict[str, str] = {
    "tests": "test_failed",
    "patch_diff": "unparseable_diff",
    "patch_diff_files": "unparseable_diff",
    "patch_boundary": "patch_outside_arena",
    "patch_task_boundary": "patch_outside_task",
    "patch_lease_boundary": "lease_scope_violation",
    "patch_conflict": "lease_scope_violation",
    "repo_boundary": "patch_outside_arena",
    "arena_gate": "missing_grounding",
    "arena_lease": "lease_scope_violation",
    "arena_route": "missing_grounding",
}

# Default next-allowed-tools per error category.
_DEFAULT_NEXT_TOOLS: dict[str, list[str]] = {
    "missing_grounding": ["aura_search_code", "aura_read_slice", "aura_prepare_arena"],
    "target_symbol_unresolved": ["aura_search_code", "aura_read_slice"],
    "scope_too_broad": ["aura_prepare_arena"],
    "missing_tests": ["aura_search_code", "aura_read_slice"],
    "patch_outside_arena": ["aura_get_micro_context", "aura_stage_patch"],
    "patch_outside_task": ["aura_get_micro_context", "aura_stage_patch"],
    "lease_scope_violation": ["aura_get_micro_context", "aura_stage_patch"],
    "unparseable_diff": ["aura_stage_patch"],
    "empty_patch": ["aura_stage_patch"],
    "test_failed": ["aura_repair_packet", "aura_stage_patch"],
    "ast_parse_failed": ["aura_repair_packet", "aura_read_slice"],
    "codemap_refresh_failed": ["aura_repo_digest", "aura_search_code"],
    "fireworks_call_failed": ["aura_fireworks_patch_worker", "aura_stage_patch"],
    "mcp_protocol_error": ["aura_repo_digest"],
}


class ArenaBridgeError(Exception):
    """Structured error raised by bridge tools.

    The ``to_packet`` method converts it to the JSON-serialisable dict that
    every tool returns on failure.
    """

    def __init__(
        self,
        category: str,
        message: str,
        *,
        repair_hint: str = "",
        next_allowed_tools: list[str] | None = None,
        compressed_context: str = "",
    ) -> None:
        super().__init__(message)
        if category not in _ERROR_CATEGORY_SET:
            category = "mcp_protocol_error"
        self.category = category
        self.message = message
        self.repair_hint = repair_hint
        self.next_allowed_tools = next_allowed_tools or list(_DEFAULT_NEXT_TOOLS.get(category, ["aura_repo_digest"]))
        self.compressed_context = compressed_context

    def to_packet(self) -> dict[str, Any]:
        return make_error_packet(
            self.category,
            self.message,
            repair_hint=self.repair_hint,
            next_allowed_tools=self.next_allowed_tools,
            compressed_context=self.compressed_context,
        )


def _short_hash(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=12).hexdigest()


def make_error_packet(
    category: str,
    message: str,
    *,
    repair_hint: str = "",
    next_allowed_tools: list[str] | None = None,
    compressed_context: str = "",
) -> dict[str, Any]:
    """Build a structured error packet dict."""
    if category not in _ERROR_CATEGORY_SET:
        category = "mcp_protocol_error"
    tools = next_allowed_tools or list(_DEFAULT_NEXT_TOOLS.get(category, ["aura_repo_digest"]))
    payload = {
        "error_schema_version": ERROR_SCHEMA_VERSION,
        "ok": False,
        "error_category": category,
        "message": str(message)[:512],
        "repair_hint": str(repair_hint)[:512],
        "next_allowed_tools": list(tools),
        "compressed_context": str(compressed_context)[:4096] if compressed_context else "",
    }
    payload["error_id"] = _short_hash(json.dumps(payload, sort_keys=True, default=str))
    return payload


def error_from_shadow_finding(finding: dict[str, Any]) -> ArenaBridgeError:
    """Convert an architect-loop ShadowFinding dict to an ArenaBridgeError."""
    shadow_type = str(finding.get("shadow_type") or finding.get("type") or "")
    category = _SHADOW_TYPE_TO_CATEGORY.get(shadow_type, "mcp_protocol_error")
    message = str(finding.get("message") or finding.get("severity") or "Arena stage rejected patch.")
    task_id = finding.get("task_id", "")
    target_file = finding.get("target_file") or ""
    repair_hint = f"Task {task_id}: {message}"
    if target_file:
        repair_hint += f" (file: {target_file})"
    return ArenaBridgeError(category, message, repair_hint=repair_hint)


def error_from_verification_failure(failure: dict[str, Any]) -> ArenaBridgeError:
    """Convert a verification failure dict to an ArenaBridgeError."""
    stage = str(failure.get("stage") or "")
    category = _VERIFY_STAGE_TO_CATEGORY.get(stage, "test_failed")
    message = str(failure.get("message") or f"Verification failed at stage: {stage}")
    repair_hint = f"Stage {stage}: {message}"
    if failure.get("test"):
        repair_hint += f" (test: {failure['test']})"
    if failure.get("files"):
        repair_hint += f" (files: {', '.join(failure['files'])})"
    return ArenaBridgeError(category, message, repair_hint=repair_hint)


def is_error_packet(obj: Any) -> bool:
    """Return True if *obj* looks like a structured error packet."""
    if not isinstance(obj, dict):
        return False
    return obj.get("ok") is False and "error_category" in obj and "error_schema_version" in obj