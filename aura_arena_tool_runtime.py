"""
Aura Arena Tool Runtime — bounded ephemeral tools for the Human Agent Arena.

Trusted built-in tools may run with explicit inputs and resource limits. Arbitrary
or generated components never fall back to native execution: they require a
configured Wasmtime/WASI runtime and otherwise fail closed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from aura_ephemeral_sandbox import (
    destroy_sandbox,
    prepare_sandbox,
    revoke_capabilities,
    verify_dissolution,
)

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
TOOL_RUNTIME_VERSION = "AURA_ARENA_TOOL_RUNTIME_V1"


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    title: str
    purpose: str
    capability: str
    stage: str
    risk: str = "low"
    runtime: str = "builtin_only"
    requires: tuple[str, ...] = ()
    produces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["requires"] = list(self.requires)
        data["produces"] = list(self.produces)
        return data


@dataclass
class ToolRun:
    run_id: str
    tool_id: str
    objective: str
    status: str
    started_at: float
    completed_at: float = 0.0
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    denial: dict[str, Any] = field(default_factory=dict)
    sandbox_receipt: dict[str, Any] = field(default_factory=dict)
    dissolution_receipt: dict[str, Any] = field(default_factory=dict)
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TOOLS: dict[str, ToolDefinition] = {
    "topology_inspector": ToolDefinition(
        "topology_inspector", "Topology Inspector",
        "Inspect exact CODEMAP relationships and bounded source regions.",
        "search_code", "GROUND", requires=("objective",),
        produces=("localized_files", "localized_symbols", "line_ranges"),
    ),
    "test_lab": ToolDefinition(
        "test_lab", "Ephemeral Test Lab",
        "Run explicit, repo-local pytest targets inside a temporary tool lifecycle.",
        "run_tests", "PROVE", risk="medium",
        requires=("test_targets",), produces=("test_evidence", "test_log"),
    ),
    "verifier": ToolDefinition(
        "verifier", "Patch Verifier",
        "Evaluate provided test or verifier evidence against the current gate.",
        "verify_patch", "PROVE", requires=("test_evidence",),
        produces=("verification_packet",),
    ),
    "hotswap_gate": ToolDefinition(
        "hotswap_gate", "Hotswap Gate",
        "Explain whether a staged patch has enough evidence for human review.",
        "hotswap_status", "DECIDE",
        requires=("staged_patch", "test_evidence", "verification_packet"),
        produces=("hotswap_status", "missing_evidence"),
    ),
    "wasm_component": ToolDefinition(
        "wasm_component", "Rust / WebAssembly Organ",
        "Run a generated or external WebAssembly component through configured Wasmtime/WASI.",
        "wasm_component", "ACT", risk="high", runtime="wasmtime",
        requires=("component_ref", "configured_wasi_runtime"),
        produces=("component_output", "sandbox_receipt"),
    ),
}


def list_tools() -> dict[str, Any]:
    return {
        "ok": True,
        "version": TOOL_RUNTIME_VERSION,
        "tools": [tool.to_dict() for tool in TOOLS.values()],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }


def _run_id(tool_id: str, objective: str) -> str:
    payload = f"{tool_id}:{objective}:{time.time()}"
    return f"TOOL-{hashlib.blake2b(payload.encode(), digest_size=8).hexdigest()}"


def _deny(run: ToolRun, reason: str, *, missing: list[str] | None = None,
          remediation: list[dict[str, str]] | None = None) -> dict[str, Any]:
    run.status = "DENIED"
    run.completed_at = time.time()
    run.denial = {
        "reason": reason,
        "missing": list(missing or []),
        "remediation": list(remediation or []),
        "fail_closed": True,
    }
    return run.to_dict()


def _safe_test_targets(targets: list[str], repo_root: Path) -> tuple[list[str], list[str]]:
    safe: list[str] = []
    rejected: list[str] = []
    for raw in targets:
        value = str(raw or "").strip().replace("\\", "/")
        if not value or value.startswith("-") or ".." in Path(value).parts:
            rejected.append(value)
            continue
        path_part = value.split("::", 1)[0]
        candidate = (repo_root / path_part).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            rejected.append(value)
            continue
        if not candidate.exists() or candidate.suffix != ".py":
            rejected.append(value)
            continue
        safe.append(value)
    return safe, rejected


def _summarize_pytest(stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
    combined = "\n".join(part for part in (stdout, stderr) if part).strip()
    lines = combined.splitlines()
    summary = next((line for line in reversed(lines) if " passed" in line or " failed" in line or " error" in line), "")
    return {
        "ok": returncode == 0,
        "returncode": returncode,
        "summary": summary or ("pytest passed" if returncode == 0 else "pytest failed"),
        "log_tail": lines[-80:],
        "measurement": "MEASURED",
    }


class ArenaToolRuntime:
    def __init__(self, repo_root: str | Path = ".") -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runs: dict[str, dict[str, Any]] = {}

    def get_tools(self) -> dict[str, Any]:
        return list_tools()

    def get_run(self, run_id: str) -> dict[str, Any]:
        run = self.runs.get(str(run_id))
        if run is None:
            return {"ok": False, "error": "tool_run_not_found", "run_id": run_id}
        return {"ok": True, "run": run}

    def execute(self, tool_id: str, *, objective: str = "",
                inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        tool = TOOLS.get(str(tool_id))
        run = ToolRun(
            run_id=_run_id(str(tool_id), objective),
            tool_id=str(tool_id), objective=str(objective), status="PLANNING",
            started_at=time.time(), inputs=dict(inputs or {}),
        )
        if tool is None:
            result = _deny(run, "unknown_tool", missing=[str(tool_id)])
            self.runs[run.run_id] = result
            return result

        if tool.runtime == "wasmtime":
            result = self._execute_wasm(tool, run)
        else:
            result = self._execute_builtin(tool, run)
        self.runs[run.run_id] = result
        return result

    def _execute_wasm(self, tool: ToolDefinition, run: ToolRun) -> dict[str, Any]:
        try:
            import wasmtime  # noqa: F401
            wasmtime_available = True
        except ImportError:
            wasmtime_available = False
        if not wasmtime_available:
            return _deny(
                run,
                "Wasmtime/WASI is not available; arbitrary components cannot execute.",
                missing=["configured_wasi_runtime"],
                remediation=[
                    {"label": "Use a trusted built-in tool", "action": "show available tools"},
                    {"label": "Configure Wasmtime/WASI", "action": "inspect wasm runtime requirements"},
                ],
            )
        return _deny(
            run,
            "Wasmtime is installed but the arbitrary-component host contract is not configured.",
            missing=["wasi_host_contract", "component_import_allowlist", "resource_limits"],
            remediation=[{"label": "Inspect sandbox contract", "action": "show wasm sandbox contract"}],
        )

    def _execute_builtin(self, tool: ToolDefinition, run: ToolRun) -> dict[str, Any]:
        manifest = {
            "organ_id": run.run_id,
            "resource_budget": {"wall_time_ms": 30000, "memory_mb": 256,
                                "output_bytes": 1000000, "tool_calls": 4},
        }
        sandbox = prepare_sandbox(manifest, repo_root=str(self.repo_root))
        if not sandbox.get("ok"):
            return _deny(run, str(sandbox.get("error", "sandbox_unavailable")))
        run.sandbox_receipt = sandbox.get("receipt", {})
        run.status = "RUNNING"
        temp_dir = str(sandbox.get("temp_dir", ""))
        try:
            if tool.tool_id == "topology_inspector":
                output = self._topology_inspector(run.objective)
            elif tool.tool_id == "test_lab":
                output = self._test_lab(run.inputs)
            elif tool.tool_id == "verifier":
                output = self._verify(run.inputs)
            elif tool.tool_id == "hotswap_gate":
                output = self._hotswap(run.inputs)
            else:
                output = {"ok": False, "error": "builtin_tool_not_implemented"}
            run.outputs = output
            run.status = "COMPLETED" if output.get("ok") else "FAILED"
        except Exception as exc:  # noqa: BLE001
            run.outputs = {"ok": False, "error": str(exc)}
            run.status = "FAILED"
        finally:
            revoked = revoke_capabilities(run.run_id)
            destroyed = destroy_sandbox(temp_dir)
            verified = verify_dissolution(temp_dir, revoked.get("ok", False))
            run.dissolution_receipt = {
                "capabilities_revoked": revoked.get("ok", False),
                "temp_dir_removed": destroyed.get("temp_dir_removed", False),
                "dissolution_verified": verified.get("ok", False),
            }
            run.completed_at = time.time()
        return run.to_dict()

    def _topology_inspector(self, objective: str) -> dict[str, Any]:
        try:
            from aura_coding_workbench_actions import localize_code, rank_code_regions
            localized = localize_code(objective, repo_root=self.repo_root)
            ranked = rank_code_regions(objective, repo_root=self.repo_root, max_regions=8, max_lines=240)
            return {
                "ok": bool(localized.get("ok", True)),
                "localized_files": localized.get("localized_files", ranked.get("files", [])),
                "localized_symbols": localized.get("localized_symbols", ranked.get("symbols", [])),
                "line_ranges": localized.get("line_ranges", ranked.get("line_ranges", [])),
                "ranking": ranked,
                "truth_class": "EXACT_REPOSITORY_FACTS",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _test_lab(self, inputs: dict[str, Any]) -> dict[str, Any]:
        targets_raw = inputs.get("test_targets", inputs.get("tests", []))
        if isinstance(targets_raw, str):
            targets_raw = [targets_raw]
        safe, rejected = _safe_test_targets(list(targets_raw or []), self.repo_root)
        if not safe:
            return {
                "ok": False,
                "error": "No explicit safe pytest targets were provided.",
                "rejected_targets": rejected,
                "missing_evidence": ["explicit_test_target"],
                "next_actions": ["show tests for selected", "choose a focused test", "run test lab"],
            }
        command = [sys.executable, "-m", "pytest", "-q", *safe]
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=self.repo_root,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False, "error": "test_timeout", "targets": safe,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                "log_tail": str(exc).splitlines()[-40:],
            }
        evidence = _summarize_pytest(completed.stdout, completed.stderr, completed.returncode)
        evidence.update({
            "targets": safe,
            "rejected_targets": rejected,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
            "command": [sys.executable, "-m", "pytest", "-q", *safe],
            "evidence_digest": hashlib.sha256(
                json.dumps({"targets": safe, "returncode": completed.returncode,
                            "stdout": completed.stdout, "stderr": completed.stderr}, sort_keys=True).encode()
            ).hexdigest()[:20],
        })
        return evidence

    @staticmethod
    def _verify(inputs: dict[str, Any]) -> dict[str, Any]:
        evidence = inputs.get("test_evidence", {})
        if not isinstance(evidence, dict) or not evidence:
            return {
                "ok": False, "error": "missing_test_evidence",
                "missing_evidence": ["test_evidence"],
                "next_actions": ["run test lab"],
            }
        passed = bool(evidence.get("ok")) and int(evidence.get("returncode", 1)) == 0
        return {
            "ok": passed,
            "verified": passed,
            "evidence_digest": evidence.get("evidence_digest", ""),
            "checks": {
                "tests_executed": bool(evidence.get("targets")),
                "tests_passed": passed,
                "measured_result": evidence.get("measurement") == "MEASURED",
            },
            "next_gate": "HUMAN_REVIEW" if passed else "REPAIR_REQUIRED",
        }

    @staticmethod
    def _hotswap(inputs: dict[str, Any]) -> dict[str, Any]:
        staged = bool(inputs.get("staged_patch"))
        test_evidence = inputs.get("test_evidence") or {}
        verification = inputs.get("verification_packet") or {}
        tests_passed = bool(test_evidence.get("ok"))
        verified = bool(verification.get("verified") or verification.get("ok"))
        missing: list[str] = []
        if not staged:
            missing.append("staged_patch")
        if not test_evidence:
            missing.append("test_evidence")
        elif not tests_passed:
            missing.append("passing_test_evidence")
        if not verification:
            missing.append("verification_packet")
        elif not verified:
            missing.append("passing_verification")
        ready = not missing
        actions = []
        if "staged_patch" in missing:
            actions.append({"label": "Stage candidate patch", "action": "stage patch"})
        if "test_evidence" in missing or "passing_test_evidence" in missing:
            actions.append({"label": "Open Test Lab", "action": "run test lab"})
        if "verification_packet" in missing or "passing_verification" in missing:
            actions.append({"label": "Run verifier", "action": "run verifier"})
        return {
            "ok": ready,
            "hotswap_ready": ready,
            "decision": "READY_FOR_HUMAN_REVIEW" if ready else "DENIED",
            "missing_evidence": missing,
            "remediation": actions,
            "human_approval_required": True,
            "note": "Ready means eligible for human review, never automatic promotion.",
        }
