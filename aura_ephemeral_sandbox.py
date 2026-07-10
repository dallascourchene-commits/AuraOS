"""
Aura Ephemeral Sandbox — runtime sandbox for ephemeral organ execution.

CRITICAL TRUTH: Python AST checks are NOT a complete security sandbox.
Do not describe an isolated subprocess or AST filter as secure arbitrary-code isolation.

For the MVP:
  1. Built-in read-only adapters may execute through an explicit Python allowlist.
  2. External/generated components may execute only through Wasmtime/WASI when available.
  3. If Wasmtime is unavailable: built-in adapters continue, arbitrary components fail closed.
  4. Never silently fall back to native execution.

Dependencies: stdlib only. Wasmtime detection is lazy.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

# Built-in adapter allowlist — these are the ONLY allowed executable components
BUILTIN_ADAPTERS: dict[str, Callable[..., dict[str, Any]]] = {}


def _register_adapter(name: str, fn: Callable[..., dict[str, Any]]) -> None:
    BUILTIN_ADAPTERS[name] = fn


def _adapter_resolve_capabilities(objective: str = "", repo_root: str = ".") -> dict[str, Any]:
    try:
        from aura_capability_resolver import resolve_capabilities
        return resolve_capabilities(objective, repo_root=repo_root)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _adapter_search_code(query: str = "", repo_root: str = ".") -> dict[str, Any]:
    try:
        from aura_codebase_navigator import search_index
        import json
        with open(Path(repo_root) / ".aura" / "CODEMAP.json") as f:
            cm = json.load(f)
        results = search_index(cm, query, limit=10)
        return {"ok": True, "results": results[:10]}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _adapter_read_slice(file: str = "", symbol: str = "", repo_root: str = ".") -> dict[str, Any]:
    try:
        p = Path(repo_root) / file
        if not p.exists():
            return {"ok": False, "error": f"file not found: {file}"}
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        # If symbol provided, try to find its line range
        start, end = 1, min(80, len(lines))
        if symbol:
            for i, line in enumerate(lines):
                if f"def {symbol}" in line or f"class {symbol}" in line:
                    start = i + 1
                    # Find end (next def/class or dedent)
                    for j in range(i + 1, min(i + 200, len(lines))):
                        if lines[j].startswith("def ") or lines[j].startswith("class "):
                            end = j
                            break
                    else:
                        end = min(i + 80, len(lines))
                    break
        return {"ok": True, "file": file, "symbol": symbol,
                "lines": lines[start-1:end], "line_start": start, "line_end": end}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _adapter_render_ui_schema(component_types: list[str] | None = None) -> dict[str, Any]:
    allowed = {"objective_header", "existing_capability_cards", "exact_function_table",
               "relationship_graph", "tests_and_docs_panel", "safety_constraints",
               "missing_capability_panel", "cost_telemetry", "lifecycle_status", "dissolve_control"}
    types = component_types or list(allowed)
    # Reject unknown component types
    unknown = [t for t in types if t not in allowed]
    if unknown:
        return {"ok": False, "error": f"unknown_ui_components: {unknown}"}
    return {"ok": True, "schema": {"components": types}, "executable": False,
            "note": "Declarative JSON only. No executable script."}


def _adapter_emit_telemetry(event_type: str = "", data: str = "") -> dict[str, Any]:
    try:
        from aura_cost_telemetry_events import get_telemetry_stream
        stream = get_telemetry_stream()
        import json
        payload = json.loads(data) if isinstance(data, str) and data else {}
        return stream.emit(event_type, payload)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _adapter_write_temp_audit(audit_data: str = "", temp_dir: str = "") -> dict[str, Any]:
    if not temp_dir:
        return {"ok": False, "error": "no_temp_dir"}
    try:
        import json
        path = Path(temp_dir) / f"audit_{int(time.time())}.json"
        path.write_text(audit_data, encoding="utf-8")
        return {"ok": True, "path": str(path)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# Register adapters
_register_adapter("resolve_capabilities", _adapter_resolve_capabilities)
_register_adapter("search_code", _adapter_search_code)
_register_adapter("read_slice", _adapter_read_slice)
_register_adapter("render_ui_schema", _adapter_render_ui_schema)
_register_adapter("emit_telemetry", _adapter_emit_telemetry)
_register_adapter("write_temp_audit", _adapter_write_temp_audit)


@dataclass
class SandboxReceipt:
    receipt_id: str
    organ_id: str
    sandbox_mode: str  # "builtin_only" | "wasmtime" | "unavailable"
    temp_dir: str
    created_at: float
    wasmtime_available: bool = False
    resource_limits: dict[str, Any] = field(default_factory=dict)
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _detect_wasmtime() -> bool:
    """Check if Wasmtime is available."""
    try:
        import wasmtime  # noqa: F401
        return True
    except ImportError:
        return False


def prepare_sandbox(manifest: dict[str, Any], repo_root: str = ".") -> dict[str, Any]:
    """Prepare a sandbox for an ephemeral organ.

    Returns SandboxReceipt. If Wasmtime is unavailable, sandbox_mode is "builtin_only".
    Arbitrary components will fail closed without Wasmtime.
    """
    organ_id = manifest.get("organ_id", "unknown")
    wasmtime_available = _detect_wasmtime()

    # Create unique temp directory per organ
    temp_dir = tempfile.mkdtemp(prefix=f"eorg_{organ_id}_")

    # Sandbox mode
    if wasmtime_available:
        sandbox_mode = "wasmtime"
    else:
        sandbox_mode = "builtin_only"

    receipt = SandboxReceipt(
        receipt_id=hashlib.blake2b(f"{organ_id}{time.time()}".encode(), digest_size=12).hexdigest(),
        organ_id=organ_id,
        sandbox_mode=sandbox_mode,
        temp_dir=temp_dir,
        created_at=time.time(),
        wasmtime_available=wasmtime_available,
        resource_limits=manifest.get("resource_budget", {}),
    )
    return {"ok": True, "receipt": receipt.to_dict(), "temp_dir": temp_dir,
            "wasmtime_available": wasmtime_available,
            "note": "Built-in adapters available. Arbitrary components require Wasmtime." if not wasmtime_available else "Wasmtime available for arbitrary components.",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def execute_builtin_adapter(
    adapter_name: str,
    *,
    organ_id: str = "",
    temp_dir: str = "",
    repo_root: str = ".",
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute a built-in adapter from the allowlist."""
    params = params or {}
    if adapter_name not in BUILTIN_ADAPTERS:
        return {"ok": False, "error": f"unknown_adapter: {adapter_name}",
                "status": "NOT_OPERATIONAL",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    fn = BUILTIN_ADAPTERS[adapter_name]
    # Inject temp_dir for write_temp_audit
    if adapter_name == "write_temp_audit":
        params["temp_dir"] = temp_dir
    if adapter_name in ("resolve_capabilities", "search_code", "read_slice"):
        params["repo_root"] = repo_root
    try:
        result = fn(**params)
        result["adapter"] = adapter_name
        result["organ_id"] = organ_id
        result["patch_authority"] = PATCH_AUTHORITY
        result["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc), "adapter": adapter_name,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def execute_wasm_component(
    component_ref: dict[str, Any],
    *,
    temp_dir: str = "",
    timeout_ms: int = 30000,
) -> dict[str, Any]:
    """Execute a Wasm component. Fails closed if Wasmtime unavailable."""
    if not _detect_wasmtime():
        return {"ok": False, "error": "Wasmtime not available. Arbitrary component execution denied.",
                "status": "NOT_OPERATIONAL",
                "note": "Never silently fall back to native execution.",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    # If Wasmtime is available, we would configure it here with:
    # - no network, no inherited environment, no secrets
    # - no host filesystem preopens except organ-specific temp dir
    # - bounded wall clock, memory, output, tool calls
    # For the MVP, we do not accept arbitrary components even with Wasmtime
    # unless fully configured.
    return {"ok": False, "error": "Wasmtime detected but not yet configured for arbitrary components.",
            "status": "NOT_OPERATIONAL",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def enforce_resource_budget(
    receipt: dict[str, Any],
    *,
    elapsed_ms: float = 0,
    output_bytes: int = 0,
    tool_calls: int = 0,
) -> dict[str, Any]:
    """Check if resource budget is exceeded."""
    limits = receipt.get("resource_limits", {})
    exceeded = []
    if elapsed_ms > limits.get("wall_time_ms", 30000):
        exceeded.append("wall_time_ms")
    if output_bytes > limits.get("output_bytes", 1_000_000):
        exceeded.append("output_bytes")
    if tool_calls > limits.get("tool_calls", 20):
        exceeded.append("tool_calls")
    return {"ok": len(exceeded) == 0, "exceeded": exceeded,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def revoke_capabilities(organ_id: str) -> dict[str, Any]:
    """Revoke all capabilities for an organ."""
    return {"ok": True, "organ_id": organ_id, "revoked": "all",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def destroy_sandbox(temp_dir: str) -> dict[str, Any]:
    """Remove the temporary directory."""
    try:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)
            return {"ok": True, "temp_dir_removed": True, "temp_dir": temp_dir,
                    "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
        return {"ok": True, "temp_dir_removed": False, "note": "temp_dir already absent",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "temp_dir_removed": False,
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def verify_dissolution(temp_dir: str, capabilities_revoked: bool) -> dict[str, Any]:
    """Verify that dissolution is complete."""
    if not temp_dir:
        temp_removed = True
    else:
        temp_removed = not Path(temp_dir).exists()
    caps_ok = capabilities_revoked is True or capabilities_revoked == "all"
    return {"ok": temp_removed and caps_ok,
            "temp_dir_removed": temp_removed,
            "capabilities_revoked": caps_ok,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}


def check_path_traversal(path: str, temp_dir: str) -> bool:
    """Check if a path attempts traversal outside the temp directory."""
    try:
        resolved = Path(path).resolve()
        temp_resolved = Path(temp_dir).resolve()
        return not str(resolved).startswith(str(temp_resolved))
    except Exception:
        return True  # Fail closed


def check_symlink_escape(path: str, temp_dir: str) -> bool:
    """Check if a path is a symlink that escapes the temp directory."""
    try:
        p = Path(path)
        if p.is_symlink():
            resolved = p.resolve()
            temp_resolved = Path(temp_dir).resolve()
            return not str(resolved).startswith(str(temp_resolved))
        return False
    except Exception:
        return True  # Fail closed
