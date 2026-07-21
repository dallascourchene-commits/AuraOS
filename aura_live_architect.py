"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:6C2848D106FBD645]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: json, __future__, sys, ast, re, subprocess, aura_architect_loop, collections.abc, tempfile, aura_substrate, typing, aura_liquid_planning_arena, os, pathlib, inspect, shutil, dataclasses, hashlib
FUNCTIONS: _hash_payload, _strip_code_fences, _extract_json_object, _diff_path_token, _diff_touched_files, _extract_diff, _git_executable, _run_command, _repo_copy_ignore, _test_files_from_arena, _default_test_commands, _python_topology_signature, _set_delta, _normalize_judge_approval, _safe_topology_file_paths, compute_temp_workspace_topology_delta, _merge_workspace_result, _merge_act_stage_result, _merge_council_plan_judgement, judge_patch_bundle, _merge_council_patch_judgement, _augment_live_hotswap_capsule, verify_arena_in_temp_workspace, run_live_architect_transaction, render_live_architect_summary, to_dict, to_dict, to_dict, to_execution_result, to_dict, add, __init__, ledger_hints, profile_for, call_model, budget_route, infer_target_file, deterministic_plan_spec, plan_with_council, plan_intent, __init__, _normalize_plan_spec, _candidate, _parse_critic_report, _run_shadow_critics, _judge_candidates, select_plan, __init__, _reviewable_attempt, _builder_failure_report, build_patch_submissions, runner, visit_FunctionDef, visit_AsyncFunctionDef, visit_ClassDef, visit_Import, visit_ImportFrom, visit_Call
SYNOPSIS: [CODE]
def optimized_fallback():
    pass
[/CODE]
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from aura_architect_loop import (
    ARCHITECT_LEDGER_PATH,
    ArchitectExecutionResult,
    ArchitectFusionLoop,
    ArchitectLedgerRecord,
    ArchitectLoopResult,
    PatchStageResult,
    RefactorArenaTransaction,
    VerificationResult,
    append_architect_ledger,
    build_architect_ledger_record,
    build_hotswap_capsule,
    stage_arena_patch,
    verify_refactor_arena,
)
from aura_builder_context import BuilderContextPacket, build_builder_context_packet
from aura_coding_arena_grounding import ground_coding_arena_intent
from aura_liquid_planning_arena import build_world_state_delta
from aura_patch_quality_gate import (
    PatchPreflightResult,
    generate_unified_diff_from_before_after,
    parse_before_after_response,
    preflight_patch,
)
from aura_patch_repair import PatchRepairResult, repair_patch_format
from aura_repo_localizer import run_agentless_fallback
from aura_substrate import REPO_ROOT
from aura_test_gap_filler import TestGapFillerResult, detect_missing_test_findings, fill_test_gap

try:
    from aura_qdkt import get_qdkt
except Exception:
    get_qdkt = None  # type: ignore[assignment]

try:
    from aura_dream_retrieval import DreamCandidate, record_arena_retrieval_feedback
except Exception:
    record_arena_retrieval_feedback = None  # type: ignore[assignment]
    DreamCandidate = None  # type: ignore[assignment]

try:
    from aura_coding_arena_workflow import (
        CodingArenaWorkflowMemory,
        WorkflowOutcome,
        get_coding_arena_memory,
    )
except Exception:
    CodingArenaWorkflowMemory = None  # type: ignore[assignment]
    WorkflowOutcome = None  # type: ignore[assignment]
    get_coding_arena_memory = None  # type: ignore[assignment]

try:
    from aura_music_coding_arena import (
        augment_act_tasks_with_music,
        fuse_music_council_plan,
        music_builder_objective,
    )
except Exception:
    augment_act_tasks_with_music = None  # type: ignore[assignment]
    fuse_music_council_plan = None  # type: ignore[assignment]
    music_builder_objective = None  # type: ignore[assignment]

try:
    from aura_symbolic_trace_memory import (
        AuraTraceMemoryConfig,
        build_trace_canvas,
        record_trace_event,
        render_trace_canvas_for_prompt,
        should_inject_canvas,
    )
except Exception:
    AuraTraceMemoryConfig = None  # type: ignore[assignment]
    build_trace_canvas = None  # type: ignore[assignment]
    record_trace_event = None  # type: ignore[assignment]
    render_trace_canvas_for_prompt = None  # type: ignore[assignment]
    should_inject_canvas = None  # type: ignore[assignment]

ARCHITECT_LIVE_VERSION = "AURA_LIVE_ARCHITECT_V1"
ARCHITECT_STAGING_PATH = Path(REPO_ROOT) / "Aura_Staging" / "architect_live_transaction.json"
ModelCaller = Callable[[str, str, dict[str, Any]], Any]


@dataclass
class ArchitectModelProfile:
    role: str
    provider: str
    model_class: str
    cost_tier: str
    purpose: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TempWorkspaceResult:
    ok: bool
    checks: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    test_results: dict[str, dict[str, Any]]
    workspace_path: str | None = None
    topology_delta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ArchitectCouncilDecision:
    selected_plan: dict[str, Any]
    candidates: list[dict[str, Any]]
    critic_reports: list[dict[str, Any]]
    judge_decision: dict[str, Any]
    budget_route: dict[str, Any]
    phase_hash: str
    music_mitosis: dict[str, Any] = field(default_factory=dict)
    topological_grounding: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiveArchitectTransaction:
    live_version: str
    prepared: ArchitectLoopResult
    stage_results: list[PatchStageResult]
    workspace: TempWorkspaceResult
    verification: VerificationResult
    hotswap_capsule: dict[str, Any]
    ledger_record: ArchitectLedgerRecord
    staging_path: str
    model_route: dict[str, Any] = field(default_factory=dict)
    fusion_council: dict[str, Any] = field(default_factory=dict)
    patch_quality: dict[str, Any] = field(default_factory=dict)

    def to_execution_result(self) -> ArchitectExecutionResult:
        return ArchitectExecutionResult(
            prepared=self.prepared,
            stage_results=self.stage_results,
            verification=self.verification,
            hotswap_capsule=self.hotswap_capsule,
            ledger_record=self.ledger_record,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "live_version": self.live_version,
            "prepared": self.prepared.to_dict(),
            "stage_results": [item.to_dict() for item in self.stage_results],
            "workspace": self.workspace.to_dict(),
            "verification": self.verification.to_dict(),
            "hotswap_capsule": self.hotswap_capsule,
            "ledger_record": self.ledger_record.to_dict(),
            "staging_path": self.staging_path,
            "model_route": self.model_route,
            "fusion_council": self.fusion_council,
            "patch_quality": self.patch_quality,
        }


def _hash_payload(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=16).hexdigest()


def _strip_code_fences(text: str) -> str:
    body = str(text or "").strip()
    fenced = re.search(r"```(?:json|diff|patch|text|python)?\s*(.*?)```", body, re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return body


def _extract_json_object(text: str) -> dict[str, Any] | None:
    body = _strip_code_fences(text)
    candidates = [body]
    match = re.search(r"\{.*\}", body, re.DOTALL)
    if match:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _diff_path_token(path: str) -> str | None:
    token = path.strip().strip('"').strip("'")
    if not token or token == "/dev/null":
        return None
    if "\t" in token:
        token = token.split("\t", 1)[0]
    if token.startswith("a/") or token.startswith("b/"):
        token = token[2:]
    normalized = token.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized or None


def _diff_touched_files(diff: str) -> list[str]:
    files: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        normalized = _diff_path_token(path)
        if normalized and normalized not in seen:
            files.append(normalized)
            seen.add(normalized)

    previous_was_minus = False
    for line in str(diff or "").splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            if len(parts) >= 4:
                add(parts[2])
                add(parts[3])
            previous_was_minus = False
            continue
        if line.startswith("--- "):
            add(line[4:])
            previous_was_minus = True
            continue
        if line.startswith("+++ ") and previous_was_minus:
            add(line[4:])
            previous_was_minus = False
            continue
        previous_was_minus = False
        for marker in ("*** Update File: ", "*** Add File: ", "*** Delete File: "):
            if line.startswith(marker):
                add(line[len(marker):])
                break
    return files


def _extract_diff(text: str) -> str:
    body = str(text or "").strip()
    patch_match = re.search(r"\[PATCH\](.*?)\[/PATCH\]", body, re.DOTALL | re.IGNORECASE)
    if patch_match:
        diff = patch_match.group(1).strip()
        return diff + ("\n" if diff else "")
    body = _strip_code_fences(body)
    marker_positions = [
        pos for pos in (
            body.find("diff --git "),
            body.find("*** Begin Patch"),
            body.find("--- "),
        )
        if pos >= 0
    ]
    if marker_positions:
        diff = body[min(marker_positions):].strip()
        return diff + ("\n" if diff else "")
    return body + ("\n" if body else "")


def _patch_submission_is_patchable(submission: dict[str, Any]) -> bool:
    diff = str(submission.get("diff") or "")
    return bool(diff.strip() and _diff_touched_files(diff))


def _patchable_submissions(submissions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [submission for submission in submissions if _patch_submission_is_patchable(submission)]


def _has_patchable_submission(submissions: list[dict[str, Any]]) -> bool:
    return bool(_patchable_submissions(submissions))


def _git_executable() -> str | None:
    found = shutil.which("git")
    if found:
        return found
    windows_git = Path("C:/Program Files/Git/cmd/git.exe")
    if windows_git.exists():
        return str(windows_git)
    return None


def _run_command(command: list[str], *, cwd: Path, stdin: str | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            input=stdin,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {"status": "error", "returncode": 1, "cmd": command, "error": str(exc)}
    return {
        "status": "passed" if proc.returncode == 0 else "failed",
        "returncode": proc.returncode,
        "cmd": command,
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }


def _repo_copy_ignore(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "node_modules",
        "venv",
        ".venv",
    }
    return {name for name in names if name in ignored}


def _test_files_from_arena(arena: RefactorArenaTransaction) -> list[str]:
    tests: list[str] = []
    seen: set[str] = set()
    for item in arena.verification_ledger:
        if item.get("stage") == "tests":
            for name in item.get("test_files", []) or []:
                normalized = _diff_path_token(str(name))
                if normalized and normalized not in seen:
                    tests.append(normalized)
                    seen.add(normalized)
    for patch in arena.shared_patch_queue:
        for name in patch.get("tests", []) or []:
            normalized = _diff_path_token(str(name))
            if normalized and normalized not in seen:
                tests.append(normalized)
                seen.add(normalized)
    return tests


def _default_test_commands(arena: RefactorArenaTransaction, repo_root: Path) -> list[list[str]]:
    tests = _test_files_from_arena(arena)
    py_files = sorted({
        file
        for file in [*arena.affected_files, *tests]
        if str(file).endswith(".py") and (repo_root / file).exists()
    })
    commands: list[list[str]] = []
    if py_files:
        commands.append([sys.executable, "-m", "py_compile", *py_files])
    if tests:
        commands.append([sys.executable, "-m", "pytest", *tests, "-q"])
    return commands


def _python_topology_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "definitions": [], "imports": [], "calls": [], "parse_error": None}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception as exc:
        return {"exists": True, "definitions": [], "imports": [], "calls": [], "parse_error": str(exc)}

    definitions: set[str] = set()
    imports: set[str] = set()
    calls: set[str] = set()

    class TopologyVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
            definitions.add(node.name)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
            definitions.add(node.name)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> Any:
            definitions.add(node.name)
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> Any:
            for alias in node.names:
                imports.add(alias.name.split(".", 1)[0])
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
            if node.module:
                imports.add(node.module.split(".", 1)[0])
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> Any:
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
            self.generic_visit(node)

    TopologyVisitor().visit(tree)
    return {
        "exists": True,
        "definitions": sorted(definitions),
        "imports": sorted(imports),
        "calls": sorted(calls),
        "parse_error": None,
    }


def _set_delta(before: list[str], after: list[str]) -> dict[str, list[str]]:
    before_set = set(before)
    after_set = set(after)
    return {
        "added": sorted(after_set - before_set),
        "removed": sorted(before_set - after_set),
        "stable": sorted(before_set & after_set),
    }


def _normalize_judge_approval(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1", "approved"}
    return False


def _safe_topology_file_paths(repo_root: Path, workspace: Path, raw_path: str) -> tuple[tuple[str, Path, Path] | None, dict[str, Any] | None]:
    normalized = _diff_path_token(raw_path)
    if not normalized or not normalized.endswith(".py"):
        return None, None
    if Path(normalized).is_absolute():
        return None, {"path": raw_path, "normalized_path": normalized, "reason": "absolute_path"}

    resolved_repo = repo_root.resolve()
    resolved_workspace = workspace.resolve()
    before = (resolved_repo / normalized).resolve()
    after = (resolved_workspace / normalized).resolve()
    try:
        before.relative_to(resolved_repo)
        after.relative_to(resolved_workspace)
    except ValueError:
        return None, {"path": raw_path, "normalized_path": normalized, "reason": "path_escapes_repo"}
    return (normalized, before, after), None


def compute_temp_workspace_topology_delta(
    arena: RefactorArenaTransaction,
    *,
    repo_root: Path,
    workspace: Path,
) -> dict[str, Any]:
    """Compare affected Python file topology before and after temp patch application."""
    files: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    before_objects: list[dict[str, Any]] = []
    after_objects: list[dict[str, Any]] = []
    for raw_path in sorted({str(item) for item in arena.affected_files}):
        safe_paths, boundary_failure = _safe_topology_file_paths(repo_root, workspace, raw_path)
        if boundary_failure:
            failures.append(boundary_failure)
            continue
        if not safe_paths:
            continue
        rel, before_path, after_path = safe_paths
        before = _python_topology_signature(before_path)
        after = _python_topology_signature(after_path)
        if before.get("exists"):
            before_objects.append(
                {
                    "id": rel,
                    "object_type": "python_file_topology",
                    "exists": before.get("exists"),
                    "definitions": before.get("definitions", []),
                    "imports": before.get("imports", []),
                    "calls": before.get("calls", []),
                    "parse_error": before.get("parse_error"),
                }
            )
        if after.get("exists"):
            after_objects.append(
                {
                    "id": rel,
                    "object_type": "python_file_topology",
                    "exists": after.get("exists"),
                    "definitions": after.get("definitions", []),
                    "imports": after.get("imports", []),
                    "calls": after.get("calls", []),
                    "parse_error": after.get("parse_error"),
                }
            )
        if before.get("parse_error") or after.get("parse_error"):
            failures.append(
                {
                    "path": rel,
                    "before_error": before.get("parse_error"),
                    "after_error": after.get("parse_error"),
                }
            )
        files.append(
            {
                "path": rel,
                "before_exists": before.get("exists"),
                "after_exists": after.get("exists"),
                "definitions": _set_delta(before.get("definitions", []), after.get("definitions", [])),
                "imports": _set_delta(before.get("imports", []), after.get("imports", [])),
                "calls": _set_delta(before.get("calls", []), after.get("calls", [])),
            }
        )
    world_state_delta = build_world_state_delta(
        domain="code",
        before_objects=before_objects,
        after_objects=after_objects,
        metadata={"source": "compute_temp_workspace_topology_delta", "arena_plan_phase_hash": getattr(arena, "plan_phase_hash", None)},
    ).to_dict()
    summary = {
        "files_checked": len(files),
        "files_with_definition_delta": sum(1 for item in files if item["definitions"]["added"] or item["definitions"]["removed"]),
        "files_with_import_delta": sum(1 for item in files if item["imports"]["added"] or item["imports"]["removed"]),
        "files_with_call_delta": sum(1 for item in files if item["calls"]["added"] or item["calls"]["removed"]),
        "world_objects_changed": len(world_state_delta["changed"]),
    }
    payload = {
        "stage": "topology_delta",
        "status": "passed" if not failures else "failed",
        "summary": summary,
        "files": files,
        "world_state_delta": world_state_delta,
        "failures": failures,
    }
    return {**payload, "phase_hash": _hash_payload(payload)}


def _merge_workspace_result(
    verification: VerificationResult,
    workspace: TempWorkspaceResult,
) -> VerificationResult:
    if workspace.ok:
        return verification
    checks = [*verification.checks, *workspace.checks]
    failures = [
        *verification.failures,
        {
            "stage": "temp_workspace",
            "status": "failed",
            "message": "Temporary workspace patch application or validation failed.",
            "failures": workspace.failures,
        },
    ]
    phase_payload = {
        "base_phase_hash": verification.phase_hash,
        "workspace": workspace.to_dict(),
        "failures": failures,
    }
    return VerificationResult(
        verification_version=verification.verification_version,
        ok=False,
        stage="blocked",
        checks=checks,
        failures=failures,
        hotswap_ready=False,
        phase_hash=_hash_payload(phase_payload),
    )


def _merge_act_stage_result(
    verification: VerificationResult,
    prepared: ArchitectLoopResult,
    stage_results: list[PatchStageResult],
) -> VerificationResult:
    expected_task_ids = {act.task_id for act in prepared.plan.act_capsules}
    staged_task_ids = {result.patch.task_id for result in stage_results if result.ok and result.patch}
    missing_task_ids = sorted(expected_task_ids - staged_task_ids)
    failed_task_ids = sorted(
        {
            finding.task_id
            for result in stage_results
            if not result.ok
            for finding in result.findings
        }
    )
    if not missing_task_ids and not failed_task_ids:
        return verification

    failure = {
        "stage": "act_stage",
        "status": "failed",
        "message": "Every planned Act Capsule must produce one staged patch before hot-swap readiness.",
        "missing_task_ids": missing_task_ids,
        "failed_task_ids": failed_task_ids,
    }
    failures = [*verification.failures, failure]
    checks = [*verification.checks, failure]
    phase_payload = {
        "base_phase_hash": verification.phase_hash,
        "expected_task_ids": sorted(expected_task_ids),
        "staged_task_ids": sorted(staged_task_ids),
        "failures": failures,
    }
    return VerificationResult(
        verification_version=verification.verification_version,
        ok=False,
        stage="blocked",
        checks=checks,
        failures=failures,
        hotswap_ready=False,
        phase_hash=_hash_payload(phase_payload),
    )


def _merge_council_plan_judgement(
    verification: VerificationResult,
    council_decision: ArchitectCouncilDecision,
) -> VerificationResult:
    judge_decision = council_decision.judge_decision
    if _normalize_judge_approval(judge_decision.get("approved"), default=True):
        return verification
    failure = {
        "stage": "council_plan_judge",
        "status": "failed",
        "message": "Premium Judge rejected the selected plan before patch execution.",
        "judgement": judge_decision,
    }
    failures = [*verification.failures, failure]
    checks = [*verification.checks, failure]
    phase_payload = {
        "base_phase_hash": verification.phase_hash,
        "council_phase_hash": council_decision.phase_hash,
        "judge_decision": judge_decision,
        "failures": failures,
    }
    return VerificationResult(
        verification_version=verification.verification_version,
        ok=False,
        stage="blocked",
        checks=checks,
        failures=failures,
        hotswap_ready=False,
        phase_hash=_hash_payload(phase_payload),
    )


class ArchitectModelRouter:
    """Select premium/cheap model roles and keep ledger-informed routing hints."""

    def __init__(
        self,
        *,
        repo_root: str | Path = REPO_ROOT,
        model_caller: ModelCaller | None = None,
        ledger_path: str | Path = ARCHITECT_LEDGER_PATH,
    ):
        self.repo_root = Path(repo_root)
        self.model_caller = model_caller
        self.ledger_path = Path(ledger_path)
        self.profiles = {
            "planner": ArchitectModelProfile(
                role="planner",
                provider=os.getenv("AURA_ARCHITECT_PLANNER_PROVIDER", "ANTHROPIC"),
                model_class="premium_planner",
                cost_tier="premium",
                purpose="fractal plan capsule synthesis",
            ),
            "planner_alt": ArchitectModelProfile(
                role="planner_alt",
                provider=os.getenv("AURA_ARCHITECT_ALT_PLANNER_PROVIDER", "KIMI"),
                model_class="premium_alternate_planner",
                cost_tier="premium",
                purpose="alternate fractal plan capsule synthesis",
            ),
            "worker": ArchitectModelProfile(
                role="worker",
                provider=os.getenv("AURA_ARCHITECT_WORKER_PROVIDER", "GROQ"),
                model_class="cheap_act_worker",
                cost_tier="cheap",
                purpose="bounded Act Capsule patch generation",
            ),
            "shadow": ArchitectModelProfile(
                role="shadow",
                provider=os.getenv("AURA_ARCHITECT_SHADOW_PROVIDER", "GROQ"),
                model_class="cheap_shadow_critic",
                cost_tier="cheap",
                purpose="cheap critique before verifier",
            ),
            "judge": ArchitectModelProfile(
                role="judge",
                provider=os.getenv("AURA_ARCHITECT_JUDGE_PROVIDER", "ANTHROPIC"),
                model_class="premium_judge",
                cost_tier="premium",
                purpose="escalation and conflict decision",
            ),
        }

    def ledger_hints(self, *, limit: int = 20) -> dict[str, Any]:
        if not self.ledger_path.exists():
            return {"recent_records": 0, "recent_blocks": 0, "prefer_premium": False}
        rows = []
        with self.ledger_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped_line = line.strip()
                if not stripped_line:
                    continue
                try:
                    rows.append(json.loads(stripped_line))
                except json.JSONDecodeError:
                    continue
        recent = rows[-limit:]
        recent_blocks = sum(
            1
            for row in recent
            if row.get("verification", {}).get("hotswap_ready") is False
            or row.get("hotswap_capsule", {}).get("status") == "blocked"
        )
        return {
            "recent_records": len(recent),
            "recent_blocks": recent_blocks,
            "prefer_premium": recent_blocks >= max(2, len(recent) // 2) if recent else False,
        }

    def profile_for(self, role: str, *, intensity: int = 0) -> ArchitectModelProfile:
        if role == "worker" and intensity >= 3:
            return ArchitectModelProfile(
                role="worker",
                provider=os.getenv("AURA_ARCHITECT_ESCALATED_WORKER_PROVIDER", self.profiles["judge"].provider),
                model_class="premium_act_worker",
                cost_tier="premium",
                purpose="high-risk Act Capsule patch generation",
            )
        return self.profiles.get(role, self.profiles["worker"])

    async def call_model(self, role: str, prompt: str, *, intensity: int = 0, meta: dict[str, Any] | None = None) -> str | None:
        if self.model_caller is None:
            return None
        profile = self.profile_for(role, intensity=intensity)
        payload = {"role": role, "profile": profile.to_dict(), **(meta or {})}
        try:
            result = self.model_caller(profile.provider, prompt, payload)
            if inspect.isawaitable(result):
                result = await result
        except Exception:
            return None
        return str(result) if result is not None else None

    def budget_route(self, hints: dict[str, Any], *, target_file: str | None = None) -> dict[str, Any]:
        mode = os.getenv("AURA_ARCHITECT_PREMIUM_BUDGET", "auto").strip().lower() or "auto"
        premium_allowed = mode not in {"off", "free", "cheap", "local"}
        high_risk_target = target_file in {"aura_node.py", "aura_architect_loop.py", "aura_live_architect.py"}
        planner_roles = ["planner", "planner_alt"] if premium_allowed and self.model_caller is not None else []
        return {
            "mode": mode,
            "free_first": True,
            "free_candidates": ["deterministic_codemap_plan"],
            "premium_allowed": premium_allowed,
            "premium_planner_roles": planner_roles,
            "cheap_shadow_critics": ["scope", "tests", "cost"],
            "premium_judge": bool(premium_allowed and self.model_caller is not None and (hints.get("prefer_premium") or high_risk_target or len(planner_roles) > 1)),
            "reasons": {
                "ledger_prefer_premium": bool(hints.get("prefer_premium")),
                "high_risk_target": high_risk_target,
                "model_caller_available": self.model_caller is not None,
            },
        }

    def infer_target_file(self, intent: str, *, fallback: str = "aura_node.py") -> str | None:
        lowered = intent.lower()
        for match in re.findall(r"[\w./\\-]+\.py", intent):
            candidate = match.replace("\\", "/").lstrip("./")
            if (self.repo_root / candidate).exists():
                return candidate
        codemap_path = self.repo_root / ".aura" / "CODEMAP.json"
        if codemap_path.exists():
            try:
                codemap = json.loads(codemap_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                codemap = {}
            scored: list[tuple[int, str]] = []
            for card in codemap.get("file_cards", []) or []:
                path = str(card.get("path", ""))
                if not path.endswith(".py"):
                    continue
                words = {Path(path).stem.lower(), *Path(path).stem.lower().split("_")}
                symbols = {str(item.get("name", "")).lower() for item in card.get("symbols", []) or [] if isinstance(item, dict)}
                score = sum(1 for word in [*words, *symbols] if word and word in lowered)
                if score:
                    scored.append((score, path))
            if scored:
                return sorted(scored, reverse=True)[0][1]
        return fallback if (self.repo_root / fallback).exists() else None

    def deterministic_plan_spec(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
        topological_grounding: dict[str, Any] | None = None,
        source: str = "deterministic_fallback",
    ) -> dict[str, Any]:
        grounding_packet = dict(topological_grounding or {})
        inferred_file = target_file or grounding_packet.get("target_file") or self.infer_target_file(intent)
        hints = self.ledger_hints()
        if inferred_file is None:
            return {
                "architecture_decision": "Prepare a blocked live Architect transaction until a concrete target file is known.",
                "target_file": None,
                "target_symbol": target_symbol,
                "act_tasks": [
                    {
                        "task_id": "A-LIVE-1",
                        "objective": intent,
                        "expected_output": "UNIFIED_DIFF",
                        "acceptance": "Resolve target file before Builder execution.",
                        "topological_grounding": grounding_packet,
                    }
                ],
                "topological_grounding": grounding_packet,
                "source": "deterministic_fallback_blocked" if source == "deterministic_fallback" else source,
                "ledger_hints": hints,
            }
        return {
            "architecture_decision": "Route live Architect intent through Plan/Act, temp verification, hot-swap, rollback, and ledger gates.",
            "target_file": inferred_file,
            "target_symbol": target_symbol or grounding_packet.get("target_symbol"),
            "act_tasks": [
                {
                    "task_id": "A-LIVE-1",
                    "objective": intent,
                    "target_file": inferred_file,
                    "target_symbol": target_symbol or grounding_packet.get("target_symbol"),
                    "allowed_scope": "single live Architect Act Capsule",
                    "acceptance": "Return a unified diff that applies cleanly in the temporary workspace and passes local verification.",
                    "expected_output": "UNIFIED_DIFF",
                    "topological_grounding": grounding_packet,
                }
            ],
            "topological_grounding": grounding_packet,
            "source": source,
            "ledger_hints": hints,
        }

    async def plan_with_council(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> ArchitectCouncilDecision:
        council = ArchitectFusionCouncil(self)
        return await council.select_plan(intent, target_file=target_file, target_symbol=target_symbol)

    async def plan_intent(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> dict[str, Any]:
        return (await self.plan_with_council(intent, target_file=target_file, target_symbol=target_symbol)).selected_plan


def _planner_grounding_summary(grounding: dict[str, Any]) -> dict[str, Any]:
    source_spans = list(grounding.get("source_spans", []) or [])
    return {
        "route": grounding.get("route"),
        "target_file": grounding.get("target_file"),
        "target_symbol": grounding.get("target_symbol"),
        "exact_hit_count": len(grounding.get("exact_hits", []) or []),
        "external_call_count": len(grounding.get("external_calls", []) or []),
        "candidate_files": [
            item.get("path")
            for item in list(grounding.get("candidate_files", []) or [])[:5]
            if isinstance(item, dict)
        ],
        "source_spans": [
            {
                "file_path": item.get("file_path"),
                "symbol": item.get("symbol"),
                "start_line": item.get("start_line"),
                "end_line": item.get("end_line"),
                "source_hash": item.get("source_hash"),
            }
            for item in source_spans[:6]
            if isinstance(item, dict)
        ],
        "tests": list(grounding.get("tests", []) or [])[:5],
        "route_reasons": list(grounding.get("route_reasons", []) or [])[:8],
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }


def _attach_grounding_to_plan(plan: dict[str, Any], grounding: dict[str, Any]) -> dict[str, Any]:
    packet = dict(grounding or {})
    if not packet:
        return plan
    updated = dict(plan)
    updated["topological_grounding"] = packet
    if not updated.get("target_file") and packet.get("target_file"):
        updated["target_file"] = packet.get("target_file")
    if not updated.get("target_symbol") and packet.get("target_symbol"):
        updated["target_symbol"] = packet.get("target_symbol")
    tasks: list[Any] = []
    for raw_task in updated.get("act_tasks", []) or []:
        if isinstance(raw_task, dict):
            task = dict(raw_task)
            task["topological_grounding"] = packet
            if not task.get("target_file") and updated.get("target_file"):
                task["target_file"] = updated.get("target_file")
            if not task.get("target_symbol") and updated.get("target_symbol"):
                task["target_symbol"] = updated.get("target_symbol")
            tasks.append(task)
        else:
            tasks.append(raw_task)
    updated["act_tasks"] = tasks
    return updated


def _trace_task_key(*parts: Any) -> str:
    body = "|".join(str(part or "") for part in parts)
    return f"trace-{hashlib.blake2b(body.encode('utf-8'), digest_size=6).hexdigest()}"


def _estimate_prompt_tokens(text: str) -> int:
    return max(1, len(str(text)) // 4)


def _record_symbolic_trace(repo_root: str | Path, event: dict[str, Any]) -> None:
    """Best-effort advisory memory write. Never affects verifier gates."""
    if record_trace_event is None:
        return
    try:
        record_trace_event(event, repo_root)
    except Exception:
        pass


def _maybe_trace_canvas_prompt(repo_root: str | Path, task_id: str, current_prompt: str) -> str:
    if (
        AuraTraceMemoryConfig is None
        or build_trace_canvas is None
        or render_trace_canvas_for_prompt is None
        or should_inject_canvas is None
    ):
        return ""
    try:
        config = AuraTraceMemoryConfig()
        context_window = int(os.getenv("AURA_TRACE_CONTEXT_WINDOW", "16000"))
        pressure = should_inject_canvas(_estimate_prompt_tokens(current_prompt), context_window, config)
        if pressure == "none":
            return ""
        canvas = build_trace_canvas(task_id, repo_root)
        if not canvas.nodes:
            return ""
        if canvas.token_estimate > max(1, int(context_window * config.canvas_max_token_ratio)):
            return ""
        rendered = render_trace_canvas_for_prompt(canvas)
        if _estimate_prompt_tokens(rendered) > max(1, int(context_window * config.canvas_max_token_ratio)):
            return ""
        combined_tokens = _estimate_prompt_tokens(current_prompt) + _estimate_prompt_tokens(rendered)
        if combined_tokens > context_window:
            return ""
        return rendered
    except Exception:
        return ""


class ArchitectFusionCouncil:
    """Orchestrate multi-candidate planning, cheap critique, and premium judging."""

    def __init__(self, router: ArchitectModelRouter):
        self.router = router

    def _normalize_plan_spec(
        self,
        data: dict[str, Any],
        *,
        intent: str,
        inferred_file: str | None,
        target_symbol: str | None,
        topological_grounding: dict[str, Any] | None = None,
        source: str,
    ) -> dict[str, Any] | None:
        tasks = data.get("act_tasks") if isinstance(data.get("act_tasks"), list) else []
        if not tasks:
            return None
        plan = {
            "architecture_decision": str(data.get("architecture_decision") or "Use the live Architect loop."),
            "target_file": str(data.get("target_file") or inferred_file) if data.get("target_file") or inferred_file else None,
            "target_symbol": str(data.get("target_symbol") or target_symbol) if data.get("target_symbol") or target_symbol else None,
            "act_tasks": tasks,
            "source": source,
            "ledger_hints": self.router.ledger_hints(),
            "objective": intent,
        }
        return _attach_grounding_to_plan(plan, topological_grounding or {})

    def _candidate(self, candidate_id: str, plan: dict[str, Any], *, cost_tier: str, source: str) -> dict[str, Any]:
        base_score = 0.42 if cost_tier == "free" else 0.62
        task_count = len(plan.get("act_tasks", []) or [])
        if plan.get("target_file"):
            base_score += 0.12
        if task_count:
            base_score += min(0.18, task_count * 0.06)
        payload = {
            "candidate_id": candidate_id,
            "source": source,
            "cost_tier": cost_tier,
            "score": round(base_score, 4),
            "plan": plan,
            "critic_reports": [],
        }
        return {**payload, "phase_hash": _hash_payload(payload)}

    def _parse_critic_report(self, response: str | None, candidate: dict[str, Any], critic_id: str) -> dict[str, Any]:
        data = _extract_json_object(response or "") if response else None
        blockers = []
        score = candidate["score"]
        approved = True
        rationale = "Local cheap-shadow heuristic accepted the candidate."
        if data:
            raw_blockers = data.get("blockers", [])
            blockers = [str(item) for item in raw_blockers] if isinstance(raw_blockers, list) else []
            try:
                score = float(data.get("score", score))
            except (TypeError, ValueError):
                score = candidate["score"]
            approved = bool(data.get("approved", not blockers))
            rationale = str(data.get("rationale") or rationale)
        elif not candidate.get("plan", {}).get("target_file"):
            approved = False
            blockers = ["missing_target_file"]
            score = min(score, 0.2)
            rationale = "Candidate has no grounded target file."
        report = {
            "critic_id": critic_id,
            "role": "cheap_shadow_critic",
            "candidate_id": candidate["candidate_id"],
            "approved": approved,
            "score": max(0.0, min(1.0, score)),
            "blockers": blockers,
            "rationale": rationale,
        }
        return {**report, "phase_hash": _hash_payload(report)}

    async def _run_shadow_critics(self, candidates: list[dict[str, Any]], budget_route: dict[str, Any]) -> list[dict[str, Any]]:
        reports: list[dict[str, Any]] = []
        for candidate in candidates:
            candidate_reports = []
            for critic_id in budget_route.get("cheap_shadow_critics", []):
                prompt = (
                    "You are an Aura cheap Shadow critic. Return JSON only with approved, score, blockers, rationale. "
                    f"Critic lane: {critic_id}. Candidate: {json.dumps(candidate['plan'], sort_keys=True)}"
                )
                response = await self.router.call_model(
                    "shadow",
                    prompt,
                    intensity=0,
                    meta={"candidate_id": candidate["candidate_id"], "critic_id": critic_id, "council_phase": "plan_shadow"},
                )
                report = self._parse_critic_report(response, candidate, critic_id)
                candidate_reports.append(report)
                reports.append(report)
            candidate["critic_reports"] = candidate_reports
            if candidate_reports:
                average = sum(item["score"] for item in candidate_reports) / len(candidate_reports)
                blockers = sum(1 for item in candidate_reports if item.get("blockers"))
                candidate["score"] = round((candidate["score"] + average) / 2 - blockers * 0.12, 4)
        return reports

    async def _judge_candidates(self, candidates: list[dict[str, Any]], budget_route: dict[str, Any]) -> dict[str, Any]:
        fallback = max(candidates, key=lambda item: item.get("score", 0.0))
        decision = {
            "role": "premium_judge" if budget_route.get("premium_judge") else "local_judge",
            "selected_candidate_id": fallback["candidate_id"],
            "approved": not any(report.get("blockers") for report in fallback.get("critic_reports", [])),
            "rationale": "Selected the highest-scoring candidate after cheap Shadow critique.",
            "premium_called": False,
        }
        if budget_route.get("premium_judge") and len(candidates) > 1:
            prompt = (
                "You are Aura's premium Judge. Return JSON only with selected_candidate_id, approved, rationale. "
                "Compare these candidate plans and choose the safest staged refactor path: "
                f"{json.dumps([{k: v for k, v in candidate.items() if k != 'plan'} | {'plan': candidate['plan']} for candidate in candidates], sort_keys=True)}"
            )
            response = await self.router.call_model(
                "judge",
                prompt,
                intensity=4,
                meta={"candidate_ids": [item["candidate_id"] for item in candidates], "council_phase": "plan_judge"},
            )
            data = _extract_json_object(response or "") if response else None
            if data:
                selected = str(data.get("selected_candidate_id") or decision["selected_candidate_id"])
                known = {item["candidate_id"] for item in candidates}
                if selected in known:
                    decision["selected_candidate_id"] = selected
                decision["approved"] = _normalize_judge_approval(data.get("approved"), default=bool(decision["approved"]))
                decision["rationale"] = str(data.get("rationale") or decision["rationale"])
                decision["premium_called"] = True
        return {**decision, "phase_hash": _hash_payload(decision)}

    async def select_plan(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> ArchitectCouncilDecision:
        hints = self.router.ledger_hints()
        topological_grounding: dict[str, Any] = {}
        planning_source = "deterministic_codemap_plan"
        compass_error = ""
        if target_file is None:
            try:
                from aura_coding_relationship_compass import (
                    compile_coding_relationship_compass,
                    is_coding_relationship_compass_intent,
                    relationship_compass_grounding,
                )

                if is_coding_relationship_compass_intent(intent):
                    compass_packet = compile_coding_relationship_compass(
                        intent,
                        self.router.repo_root,
                        target_symbols=(target_symbol,) if target_symbol else (),
                        max_atomic_nodes=32,
                        max_atlas_participants=24,
                        max_atlas_assessments=64,
                        include_source=False,
                    )
                    topological_grounding = relationship_compass_grounding(compass_packet)
                    planning_source = "deterministic_relationship_compass_plan"
            except (FileNotFoundError, ImportError, OSError, TypeError, ValueError) as exc:
                compass_error = f"{type(exc).__name__}: {exc}"
        if not topological_grounding:
            topological_grounding = ground_coding_arena_intent(
                intent,
                self.router.repo_root,
                target_symbol=target_symbol,
            )
            if compass_error:
                topological_grounding = {
                    **topological_grounding,
                    "relationship_compass_status": "FAIL_CLOSED",
                    "relationship_compass_error": compass_error,
                }
        trace_task_id = _trace_task_key("council", intent, target_file, target_symbol)
        inferred_file = target_file or topological_grounding.get("target_file") or self.router.infer_target_file(intent)
        budget_route = self.router.budget_route(hints, target_file=inferred_file)
        local_plan = self.router.deterministic_plan_spec(
            intent,
            target_file=inferred_file,
            target_symbol=target_symbol or topological_grounding.get("target_symbol"),
            topological_grounding=topological_grounding,
            source=planning_source,
        )
        local_plan = _attach_grounding_to_plan(local_plan, topological_grounding)
        candidates = [self._candidate("local_free", local_plan, cost_tier="free", source=local_plan.get("source", "deterministic_codemap_plan"))]
        grounding_summary = _planner_grounding_summary(topological_grounding)
        _record_symbolic_trace(
            self.router.repo_root,
            {
                "event_type": "council_topological_grounding_summary",
                "task_id": trace_task_id,
                "node_id": f"{trace_task_id}:topological_grounding",
                "status": topological_grounding.get("route", "proposed"),
                "route": topological_grounding.get("route", ""),
                "summary": f"Council grounding route={topological_grounding.get('route')} target={inferred_file or 'unknown'}",
                "raw_text": json.dumps(grounding_summary, indent=2, sort_keys=True, default=str),
                "metadata": {
                    "target_file": inferred_file,
                    "target_symbol": target_symbol or topological_grounding.get("target_symbol"),
                    "related_files": [inferred_file] if inferred_file else [],
                    "related_symbols": [target_symbol or topological_grounding.get("target_symbol")] if (target_symbol or topological_grounding.get("target_symbol")) else [],
                },
            },
        )
        prompt = (
            "Return JSON only for a bounded Aura Architect refactor plan. "
            "Fields: architecture_decision, target_file, target_symbol, act_tasks. "
            "Each act task must include task_id, objective, target_file, target_symbol, acceptance, expected_output=UNIFIED_DIFF. "
            "Every patch task must preserve the supplied topological_grounding packet; exact source spans and source_hash values are patch authority, and VSA/MUSIC resonance is advisory only. "
            "Never write code directly to production. "
            f"Ledger hints: {json.dumps(hints, sort_keys=True)}. "
            f"Topological grounding: {json.dumps(grounding_summary, sort_keys=True)}. "
            f"Intent: {intent}. Suggested target_file: {inferred_file or 'unknown'}."
        )
        trace_canvas = _maybe_trace_canvas_prompt(self.router.repo_root, trace_task_id, prompt)
        if trace_canvas:
            prompt = f"{prompt}\n{trace_canvas}"
        for index, role in enumerate(budget_route.get("premium_planner_roles", []), start=1):
            candidate_id = f"{role}_{index}"
            response = await self.router.call_model(
                role,
                f"{prompt} Candidate id: {candidate_id}. Produce an alternative plan from your model perspective.",
                intensity=4 if hints.get("prefer_premium") else 2,
                meta={"candidate_id": candidate_id, "council_phase": "plan_candidate"},
            )
            data = _extract_json_object(response or "") if response else None
            plan = self._normalize_plan_spec(
                data or {},
                intent=intent,
                inferred_file=inferred_file,
                target_symbol=target_symbol or topological_grounding.get("target_symbol"),
                topological_grounding=topological_grounding,
                source=f"premium_{role}",
            )
            if plan:
                candidates.append(self._candidate(candidate_id, plan, cost_tier="premium", source=plan["source"]))

        music_mitosis: dict[str, Any] = {"status": "disabled", "reason": "music_coding_arena_unavailable"}
        if planning_source == "deterministic_relationship_compass_plan":
            music_mitosis = {
                "status": "disabled",
                "reason": "relationship_compass_already_contains_bounded_emergent_and_relational_evidence",
            }
        elif fuse_music_council_plan is not None:
            try:
                music_mitosis = fuse_music_council_plan(
                    intent,
                    candidates,
                    repo_root=self.router.repo_root,
                    target_file=inferred_file,
                    target_symbol=target_symbol,
                )
            except Exception as exc:
                music_mitosis = {"status": "failed", "reason": type(exc).__name__}
        if music_mitosis.get("status") == "ready":
            best_by_candidate = music_mitosis.get("best_by_candidate", {}) or {}
            for candidate in candidates:
                candidate_id = str(candidate.get("candidate_id", ""))
                related = best_by_candidate.get(candidate_id)
                if related:
                    candidate["music_mitosis"] = {
                        "status": "ready",
                        "candidate_id": candidate_id,
                        "selected_research": related.get("selected_research", {}),
                        "synthesis": related.get("synthesis", ""),
                        "classification": related.get("classification", ""),
                        "grounding": related.get("grounding", {}),
                        "builder_hint": (
                            "MUSIC_MITOSIS: "
                            f"{related.get('synthesis', '')} Keep the patch scoped to the selected Act Capsule and preserve verifier gates."
                        ),
                        "acceptance_test": related.get("selected_research", {}).get("acceptance_test", ""),
                        "combined_score": related.get("combined_score", 0.0),
                    }
                    candidate["phase_hash"] = _hash_payload(candidate)
            fused_plan = music_mitosis.get("fused_plan")
            if isinstance(fused_plan, dict):
                fused_candidate = self._candidate(
                    str(music_mitosis.get("fusion_candidate_id") or "music_mitosis_fusion"),
                    fused_plan,
                    cost_tier="free",
                    source="music_mitosis_fusion",
                )
                try:
                    fused_candidate["score"] = max(float(fused_candidate.get("score", 0.0)), float(music_mitosis.get("fused_score", 0.0)))
                except Exception:
                    pass
                fused_candidate["music_mitosis"] = {
                    key: value
                    for key, value in music_mitosis.items()
                    if key not in {"fused_plan", "ranked_pairs", "best_by_candidate"}
                }
                fused_candidate["phase_hash"] = _hash_payload(fused_candidate)
                candidates.append(fused_candidate)

        critic_reports = await self._run_shadow_critics(candidates, budget_route)
        judge_decision = await self._judge_candidates(candidates, budget_route)
        selected_id = judge_decision["selected_candidate_id"]
        selected = next((item for item in candidates if item["candidate_id"] == selected_id), candidates[0])
        selected_plan = dict(selected["plan"])
        selected_plan = _attach_grounding_to_plan(selected_plan, topological_grounding)
        selected_plan["source"] = selected.get("source", selected_plan.get("source", "fusion_council"))
        selected_plan["council_candidate_id"] = selected["candidate_id"]
        selected_plan["ledger_hints"] = hints
        if selected.get("music_mitosis"):
            selected_plan["music_mitosis"] = selected["music_mitosis"]
        elif music_mitosis.get("status") == "ready":
            selected_plan["music_mitosis"] = {
                key: value
                for key, value in music_mitosis.items()
                if key not in {"fused_plan", "ranked_pairs", "best_by_candidate"}
            }
        payload = {
            "selected_plan": selected_plan,
            "candidates": candidates,
            "critic_reports": critic_reports,
            "judge_decision": judge_decision,
            "budget_route": budget_route,
            "music_mitosis": music_mitosis,
            "topological_grounding": topological_grounding,
        }
        for candidate in candidates:
            _record_symbolic_trace(
                self.router.repo_root,
                {
                    "event_type": "council_candidate_summary",
                    "task_id": trace_task_id,
                    "node_id": f"{trace_task_id}:candidate:{candidate.get('candidate_id', 'unknown')}",
                    "status": "proposed",
                    "route": "fusion_council",
                    "summary": (
                        f"Candidate {candidate.get('candidate_id')} score={candidate.get('score')} "
                        f"source={candidate.get('source')}"
                    ),
                    "raw_text": json.dumps(candidate, indent=2, sort_keys=True, default=str),
                    "metadata": {
                        "candidate_id": candidate.get("candidate_id", ""),
                        "target_file": candidate.get("plan", {}).get("target_file", ""),
                        "target_symbol": candidate.get("plan", {}).get("target_symbol", ""),
                    },
                },
            )
        for report in critic_reports:
            _record_symbolic_trace(
                self.router.repo_root,
                {
                    "event_type": "council_critic_report",
                    "task_id": trace_task_id,
                    "node_id": f"{trace_task_id}:critic:{report.get('critic_id', 'unknown')}:{report.get('candidate_id', 'unknown')}",
                    "status": "done" if report.get("approved", False) else "blocked",
                    "route": "fusion_council",
                    "summary": f"Critic {report.get('critic_id')} candidate={report.get('candidate_id')} approved={report.get('approved')}",
                    "raw_text": json.dumps(report, indent=2, sort_keys=True, default=str),
                    "metadata": {
                        "critic_id": report.get("critic_id", ""),
                        "candidate_id": report.get("candidate_id", ""),
                    },
                },
            )
        _record_symbolic_trace(
            self.router.repo_root,
            {
                "event_type": "council_judge_decision",
                "task_id": trace_task_id,
                "node_id": f"{trace_task_id}:judge_decision",
                "status": "done" if judge_decision.get("approved", False) else "blocked",
                "route": "fusion_council",
                "summary": f"Judge selected {judge_decision.get('selected_candidate_id')} approved={judge_decision.get('approved')}",
                "raw_text": json.dumps(judge_decision, indent=2, sort_keys=True, default=str),
                "metadata": {"candidate_id": judge_decision.get("selected_candidate_id", "")},
            },
        )
        _record_symbolic_trace(
            self.router.repo_root,
            {
                "event_type": "council_music_grounding",
                "task_id": trace_task_id,
                "node_id": f"{trace_task_id}:music_grounding",
                "status": str(music_mitosis.get("status", "disabled")),
                "route": "music_mitosis",
                "summary": f"MUSIC grounding status={music_mitosis.get('status', 'disabled')}",
                "raw_text": json.dumps(music_mitosis, indent=2, sort_keys=True, default=str),
            },
        )
        _record_symbolic_trace(
            self.router.repo_root,
            {
                "event_type": "council_selected_plan",
                "task_id": trace_task_id,
                "node_id": f"{trace_task_id}:selected_plan",
                "status": "selected",
                "route": "fusion_council",
                "summary": f"Selected plan target={selected_plan.get('target_file')} candidate={selected_plan.get('council_candidate_id')}",
                "raw_text": json.dumps(selected_plan, indent=2, sort_keys=True, default=str),
                "metadata": {
                    "target_file": selected_plan.get("target_file", ""),
                    "target_symbol": selected_plan.get("target_symbol", ""),
                    "candidate_id": selected_plan.get("council_candidate_id", ""),
                },
            },
        )
        return ArchitectCouncilDecision(phase_hash=_hash_payload(payload), **payload)


class ArchitectBuilderBridge:
    """Calls bounded Act workers with grounded context and converts model replies into patch submissions.

    Research basis: SWE-agent/RepoGraph source grounding; Agentless patch validation;
    Self-Refine bounded repair; Context Engineering survey's retrieve-then-ground pattern.
    """

    def __init__(self, router: ArchitectModelRouter, *, workflow_memory: Any = None, workflow_id: str = ""):
        self.router = router
        self.patch_quality: dict[str, Any] = {}
        self._workflow_memory = workflow_memory
        self._workflow_id = workflow_id

    def _trace_builder_event(
        self,
        *,
        act: Any,
        event_type: str,
        status: str,
        summary: str,
        raw_text: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        _record_symbolic_trace(
            self.router.repo_root,
            {
                "event_type": event_type,
                "task_id": act.task_id,
                "node_id": f"{act.task_id}:{event_type}",
                "status": status,
                "route": "builder",
                "summary": summary,
                "raw_text": raw_text,
                "metadata": {
                    "target_file": act.target_file,
                    "target_symbol": act.target_symbol,
                    "related_files": [act.target_file] if act.target_file else [],
                    "related_symbols": [act.target_symbol] if act.target_symbol else [],
                    **(metadata or {}),
                },
            },
        )

    def _trace_builder_failure(self, act: Any, failure: dict[str, Any]) -> None:
        self._trace_builder_event(
            act=act,
            event_type="builder_failure_report",
            status=str(failure.get("status", "blocked")),
            summary=(
                f"Builder failure {failure.get('status')} reasons="
                f"{','.join(str(item) for item in list(failure.get('reason_codes', []) or [])[:5])}"
            ),
            raw_text=json.dumps(failure, indent=2, sort_keys=True, default=str),
            metadata={"reason_codes": list(failure.get("reason_codes", []) or [])},
        )

    def _load_codemap(self) -> dict[str, Any] | None:
        codemap_path = self.router.repo_root / ".aura" / "CODEMAP.json"
        if not codemap_path.exists():
            return None
        try:
            return json.loads(codemap_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _record_qdkt(self, event_type: str, task_id: str, status: str, extra: dict[str, Any]) -> None:
        if get_qdkt is None:
            return
        try:
            get_qdkt().observe(
                event_type,
                {"task_id": task_id, "status": status, **extra},
                rationale=f"Patch attempt {task_id}: {status}",
                concept=f"patch_quality:{task_id}",
                confidence=0.8 if status == "staged" else 0.3,
                subsystem="aura_live_architect",
            )
        except Exception:
            pass

    def _jspace_route_for_context(
        self,
        context_packet: BuilderContextPacket | None,
        grounding: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if context_packet is not None:
            topology = context_packet.topological_context or {}
            direct = topology.get("jspace_route")
            if isinstance(direct, dict):
                return dict(direct)
            preplanning = topology.get("preplanning_grounding")
            if isinstance(preplanning, dict) and isinstance(preplanning.get("jspace_route"), dict):
                return dict(preplanning["jspace_route"])
            packet = topology.get("packet")
            if isinstance(packet, dict) and isinstance(packet.get("jspace_route"), dict):
                return dict(packet["jspace_route"])
        if isinstance(grounding, dict) and isinstance(grounding.get("jspace_route"), dict):
            return dict(grounding["jspace_route"])
        return {}

    def _reviewable_attempt(
        self,
        *,
        act: Any,
        context_packet: BuilderContextPacket,
        status: str,
        raw_response: str = "",
        extracted_diff: str = "",
        before_after: Any = None,
        preflight: PatchPreflightResult | None = None,
        repair: PatchRepairResult | None = None,
        builder_prompt: str = "",
    ) -> dict[str, Any]:
        """Build a durable review packet for successful and failed builder attempts."""
        return {
            "task_id": act.task_id,
            "target_file": act.target_file,
            "target_symbol": act.target_symbol,
            "objective": act.objective,
            "status": status,
            "builder_prompt": builder_prompt,
            "builder_context": context_packet.to_dict(),
            "jspace_route": self._jspace_route_for_context(context_packet),
            "raw_model_response": raw_response,
            "extracted_diff": extracted_diff,
            "before_after": before_after.to_dict() if before_after is not None else None,
            "preflight": preflight.to_dict() if preflight is not None else None,
            "repair": repair.to_dict() if repair is not None else None,
            "review_hint": "Review raw_model_response, extracted_diff, and repair.candidate_diff even when the transaction is blocked.",
        }

    def _builder_patch_grounding_eligibility(
        self,
        context_packet: BuilderContextPacket,
    ) -> dict[str, Any]:
        topology = context_packet.topological_context or {}
        packet = topology.get("packet") if isinstance(topology.get("packet"), dict) else {}
        route_diagnostics = packet.get("route_diagnostics", {}) if isinstance(packet, dict) else {}
        route = str(route_diagnostics.get("route") or "")
        spans = [item for item in packet.get("source_spans", []) or [] if isinstance(item, dict)] if isinstance(packet, dict) else []
        target_spans = [
            item
            for item in spans
            if item.get("role") == "target"
            and item.get("file_path")
            and item.get("start_line")
            and item.get("end_line")
            and item.get("source_hash")
        ]
        tests = list(packet.get("tests", []) or []) if isinstance(packet, dict) else []
        if route == "LOCALIZE_FIRST" and target_spans and tests:
            route = "BUILDER_PATCH"
        reasons: list[str] = []
        if not target_spans:
            reasons.append("missing_exact_topological_span")
        if context_packet.target_symbol and not context_packet.target_file:
            reasons.append("missing_exact_target_file")
        if context_packet.target_symbol and not any(span.get("symbol") == context_packet.target_symbol for span in target_spans):
            reasons.append("missing_exact_target_symbol")
        if route != "TEST_GAP_FILL" and not tests:
            reasons.append("missing_test_neighbors")
        if route not in {"BUILDER_PATCH", "TEST_GAP_FILL"}:
            reasons.append(f"patch_route_not_authorized:{route or 'unknown'}")
        return {
            "ok": not reasons and route == "BUILDER_PATCH",
            "route": route,
            "reasons": reasons,
            "tests": tests,
            "source_spans": target_spans,
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        }

    def _builder_failure_report(
        self,
        act: Any,
        grounding: dict[str, Any] | None,
        context_packet: BuilderContextPacket | None,
        *,
        status: str,
        shadow_report: Any = None,
        response: Any = None,
        preflight: PatchPreflightResult | None = None,
        repair_result: PatchRepairResult | None = None,
    ) -> dict[str, Any]:
        """Normalize Builder blocks into one reviewable failure packet."""
        grounding_dict = dict(grounding or {})
        shadow_payload: dict[str, Any] = {}
        if shadow_report is not None:
            if hasattr(shadow_report, "to_dict"):
                shadow_payload = shadow_report.to_dict()
            elif isinstance(shadow_report, dict):
                shadow_payload = dict(shadow_report)
        shadow_findings = list(shadow_payload.get("findings", []) or [])
        missing_context_excerpt = not bool(context_packet and str(context_packet.source_excerpt or "").strip())
        missing_tests = not bool(grounding_dict.get("test_files") or (context_packet.nearby_tests if context_packet else []))
        reason_codes: list[str] = []

        def add_reason(code: str) -> None:
            if code and code not in reason_codes:
                reason_codes.append(code)

        if status == "arena_not_ready":
            add_reason("arena_not_ready")
        if status == "repair_failed_blocked":
            add_reason("repair_failed_blocked")
        if status == "topological_grounding_blocked":
            add_reason("topological_grounding_blocked")
        if status == "external_call_context":
            add_reason("external_call_context")
        if status == "localize_first":
            add_reason("localize_first")
        if status == "test_gap_fill_required":
            add_reason("test_gap_fill_required")
        if status == "emergent_capability_audit":
            add_reason("emergent_capability_audit")
        if status == "missing_patch_diff":
            add_reason("missing_patch_diff")
        if status == "before_after_diff_generation_failed":
            add_reason("before_after_diff_generation_failed")
        if status == "no_response":
            add_reason("no_response")
        if status == "no_patch_staged" or response == "":
            add_reason("builder_refusal")
        if missing_context_excerpt:
            add_reason("missing_context_excerpt")
        if missing_tests:
            add_reason("missing_tests")
        if grounding_dict.get("file_exists") is False:
            add_reason("missing_target_file")
        if grounding_dict.get("symbol_exists") is False:
            add_reason("missing_target_symbol")

        shadow_gate = str(shadow_payload.get("gate") or "")
        shadow_gate_blocked = shadow_gate == "BLOCK_BUILDER" or bool(shadow_findings and not shadow_payload.get("ok", True))
        if shadow_gate_blocked:
            add_reason("shadow_gate_blocked")
        for finding in shadow_findings:
            shadow_type = str(finding.get("shadow_type") or "")
            if shadow_type == "fake_symbol":
                add_reason("missing_target_symbol")
            elif shadow_type == "fake_file":
                add_reason("missing_target_file")
            elif shadow_type == "missing_test":
                add_reason("missing_tests")
            elif shadow_type:
                add_reason(shadow_type)
        if preflight is not None and not preflight.ok:
            add_reason("preflight_failed")
            for rejection in preflight.rejections:
                add_reason(str(rejection))
        if repair_result is not None and not repair_result.ok:
            for rejection in repair_result.rejections_after_repair:
                add_reason(str(rejection))

        report = {
            "failed_task_id": act.task_id,
            "target_file": act.target_file,
            "target_symbol": act.target_symbol,
            "objective": act.objective,
            "status": status,
            "builder_refusal": "builder_refusal" in reason_codes,
            "shadow_gate": shadow_gate,
            "shadow_gate_blocked": shadow_gate_blocked,
            "shadow_findings": shadow_findings,
            "missing_context_excerpt": missing_context_excerpt,
            "missing_tests": missing_tests,
            "grounding": grounding_dict,
            "context_available": context_packet is not None,
            "context_source_refs": list(context_packet.source_refs if context_packet else []),
            "topological_context": context_packet.topological_context if context_packet else {},
            "jspace_route": self._jspace_route_for_context(context_packet, grounding_dict),
            "reason_codes": reason_codes,
            "response_empty": response == "",
            "preflight": preflight.to_dict() if preflight is not None else None,
            "repair": repair_result.to_dict() if repair_result is not None else None,
        }
        report["phase_hash"] = _hash_payload(report)
        return report

    def _non_patch_grounding_status(
        self,
        act: Any,
        grounding: dict[str, Any],
        grounding_eligibility: dict[str, Any],
    ) -> str | None:
        route = str(grounding.get("route") or "").strip()
        if route == "EXTERNAL_CALL_CONTEXT":
            return "external_call_context"
        if route == "EMERGENT_CAPABILITY_AUDIT":
            return "emergent_capability_audit"
        if route == "TEST_GAP_FILL":
            return "test_gap_fill_required"
        if route == "BLOCKED_WITH_REASON":
            return "topological_grounding_blocked"
        if route == "LOCALIZE_FIRST" and not grounding_eligibility.get("ok"):
            return "localize_first"
        return None

    async def build_patch_submissions(self, prepared: ArchitectLoopResult, *, objective: str) -> list[dict[str, Any]]:
        if not prepared.arena.ready_for_incubator:
            builder_failures = []
            grounding_by_task = {item.task_id: item.to_dict() for item in prepared.grounding}
            for act in prepared.plan.act_capsules:
                grounding_dict = grounding_by_task.get(act.task_id, {})
                raw_topological_grounding = getattr(act, "topological_grounding", {})
                topological_grounding = dict(raw_topological_grounding if isinstance(raw_topological_grounding, dict) else {})
                route = str(topological_grounding.get("route") or "").strip()
                non_patch_status = None
                if route in {"EXTERNAL_CALL_CONTEXT", "EMERGENT_CAPABILITY_AUDIT", "TEST_GAP_FILL", "BLOCKED_WITH_REASON"}:
                    non_patch_status = self._non_patch_grounding_status(act, topological_grounding, {"ok": False, "reasons": [route]})
                elif route == "LOCALIZE_FIRST" and not (act.target_file and act.target_symbol):
                    non_patch_status = "localize_first"
                failure = self._builder_failure_report(
                    act,
                    grounding_dict,
                    None,
                    status=non_patch_status or "arena_not_ready",
                    shadow_report=prepared.shadow_report,
                )
                failure["act_topological_grounding"] = topological_grounding
                if isinstance(topological_grounding.get("jspace_route"), dict):
                    failure["jspace_route"] = dict(topological_grounding["jspace_route"])
                builder_failures.append(failure)
                self._trace_builder_failure(act, failure)
            self.patch_quality = {
                "attempts": [
                    {
                        "task_id": failure["failed_task_id"],
                        "status": failure.get("status", "arena_not_ready"),
                        "preflight": None,
                        "failure_reason": failure,
                    }
                    for failure in builder_failures
                ],
                "builder_failures": builder_failures,
                "total_attempts": len(builder_failures),
                "preflight_passed": 0,
                "repair_succeeded": 0,
                "repair_failed_blocked": 0,
                "no_patch_staged": True,
            }
            return []
        codemap = self._load_codemap()
        submissions: list[dict[str, Any]] = []
        patch_attempts: list[dict[str, Any]] = []
        for act in prepared.plan.act_capsules:
            # Find grounding evidence for this act
            grounding_dict: dict[str, Any] = {}
            for evidence in prepared.grounding:
                if evidence.task_id == act.task_id:
                    grounding_dict = evidence.to_dict()
                    break
            raw_topological_grounding = getattr(act, "topological_grounding", {})
            topological_grounding = dict(raw_topological_grounding if isinstance(raw_topological_grounding, dict) else {})

            # Build grounded context packet from CODEMAP/Graphify
            context_packet = build_builder_context_packet(
                target_file=act.target_file,
                target_symbol=act.target_symbol,
                grounding_evidence=grounding_dict,
                codemap=codemap,
                repo_root=self.router.repo_root,
                objective=objective,
                task_id=act.task_id,
                topological_grounding=topological_grounding,
            )
            grounding_eligibility = self._builder_patch_grounding_eligibility(context_packet)
            non_patch_status = self._non_patch_grounding_status(act, topological_grounding, grounding_eligibility)
            if non_patch_status:
                failure = self._builder_failure_report(
                    act,
                    grounding_dict,
                    context_packet,
                    status=non_patch_status,
                )
                for reason in grounding_eligibility.get("reasons", []):
                    if reason not in failure["reason_codes"]:
                        failure["reason_codes"].append(reason)
                failure["grounding_eligibility"] = grounding_eligibility
                failure["act_topological_grounding"] = topological_grounding
                if isinstance(topological_grounding.get("jspace_route"), dict):
                    failure["jspace_route"] = dict(topological_grounding["jspace_route"])
                attempt_record = self._reviewable_attempt(
                    act=act,
                    context_packet=context_packet,
                    status=non_patch_status,
                )
                attempt_record["failure_reason"] = failure
                patch_attempts.append(attempt_record)
                self._trace_builder_failure(act, failure)
                self._record_qdkt("patch_attempt", act.task_id, "failed", {
                    "grounding_route": topological_grounding.get("route"),
                    "grounding_status": non_patch_status,
                })
                continue

            if not grounding_eligibility["ok"]:
                failure = self._builder_failure_report(
                    act,
                    grounding_dict,
                    context_packet,
                    status="topological_grounding_blocked",
                )
                for reason in grounding_eligibility.get("reasons", []):
                    if reason not in failure["reason_codes"]:
                        failure["reason_codes"].append(reason)
                failure["grounding_eligibility"] = grounding_eligibility
                attempt_record = self._reviewable_attempt(
                    act=act,
                    context_packet=context_packet,
                    status="topological_grounding_blocked",
                )
                attempt_record["failure_reason"] = failure
                patch_attempts.append(attempt_record)
                self._trace_builder_failure(act, failure)
                self._record_qdkt("patch_attempt", act.task_id, "failed", {
                    "grounding_reasons": grounding_eligibility.get("reasons", []),
                })
                continue

            # Record builder context packet to workflow memory
            if self._workflow_memory is not None and self._workflow_id:
                try:
                    self._workflow_memory.record_builder_context(self._workflow_id, context_packet, act.task_id)
                except Exception:
                    pass

            prompt = (
                "You are an Aura Act worker. Return one unified diff OR a before/after JSON object. "
                "Do not write files. Do not include prose. "
                f"Objective: {objective}\n"
                f"Act Capsule: {json.dumps(act.to_dict(), sort_keys=True)}\n"
                f"{context_packet.to_prompt_section()}"
            )
            trace_canvas = _maybe_trace_canvas_prompt(self.router.repo_root, act.task_id, prompt)
            if trace_canvas:
                prompt = f"{prompt}\n{trace_canvas}"
            self._trace_builder_event(
                act=act,
                event_type="builder_prompt",
                status="doing",
                summary=f"Builder prompt for {act.task_id} with exact context packet retained",
                raw_text=prompt,
                metadata={"context_source_refs": list(context_packet.source_refs)},
            )
            response = await self.router.call_model("worker", prompt, intensity=prepared.intensity, meta={"task_id": act.task_id})
            if not response:
                attempt_record = self._reviewable_attempt(
                    act=act,
                    context_packet=context_packet,
                    status="no_response",
                    builder_prompt=prompt,
                )
                attempt_record["failure_reason"] = self._builder_failure_report(
                    act,
                    grounding_dict,
                    context_packet,
                    status="no_response",
                    response="",
                )
                self._trace_builder_failure(act, attempt_record["failure_reason"])
                patch_attempts.append(attempt_record)
                continue

            self._trace_builder_event(
                act=act,
                event_type="builder_model_response",
                status="done",
                summary=f"Builder model response for {act.task_id}",
                raw_text=str(response),
            )

            # Check for before/after replacement object (requirement 3 & 4)
            before_after = parse_before_after_response(response)
            if before_after is not None:
                diff = generate_unified_diff_from_before_after(before_after, repo_root=self.router.repo_root)
                if not diff.strip():
                    attempt_record = self._reviewable_attempt(
                        act=act,
                        context_packet=context_packet,
                        status="before_after_diff_generation_failed",
                        raw_response=str(response),
                        extracted_diff=diff,
                        before_after=before_after,
                        builder_prompt=prompt,
                    )
                    attempt_record["failure_reason"] = self._builder_failure_report(
                        act,
                        grounding_dict,
                        context_packet,
                        status="before_after_diff_generation_failed",
                        response=response,
                    )
                    self._trace_builder_failure(act, attempt_record["failure_reason"])
                    patch_attempts.append(attempt_record)
                    continue
            else:
                diff = _extract_diff(response)

            self._trace_builder_event(
                act=act,
                event_type="builder_extracted_diff",
                status="done" if diff.strip() else "blocked",
                summary=f"Builder extracted diff touched={','.join(_diff_touched_files(diff)[:5]) or 'none'}",
                raw_text=diff,
                metadata={"affected_files": _diff_touched_files(diff)},
            )

            touched = _diff_touched_files(diff)
            if not diff.strip() or not touched:
                attempt_record = self._reviewable_attempt(
                    act=act,
                    context_packet=context_packet,
                    status="missing_patch_diff",
                    raw_response=str(response),
                    extracted_diff=diff,
                    before_after=before_after,
                    builder_prompt=prompt,
                )
                attempt_record["failure_reason"] = self._builder_failure_report(
                    act,
                    grounding_dict,
                    context_packet,
                    status="missing_patch_diff",
                    response=response,
                )
                self._trace_builder_failure(act, attempt_record["failure_reason"])
                patch_attempts.append(attempt_record)
                self._record_qdkt("patch_attempt", act.task_id, "failed", {
                    "missing_patch_diff": True,
                })
                continue

            # Run patch preflight before premium patch judge (requirement 5)
            preflight = preflight_patch(diff, repo_root=self.router.repo_root)
            attempt_record = self._reviewable_attempt(
                act=act,
                context_packet=context_packet,
                status="preflight_passed" if preflight.ok else "preflight_failed",
                raw_response=str(response),
                extracted_diff=diff,
                before_after=before_after,
                preflight=preflight,
                builder_prompt=prompt,
            )
            self._trace_builder_event(
                act=act,
                event_type="builder_preflight_result",
                status="preflight_passed" if preflight.ok else "preflight_failed",
                summary=f"Preflight ok={preflight.ok} rejections={len(preflight.rejections)}",
                raw_text=json.dumps(preflight.to_dict(), indent=2, sort_keys=True, default=str),
                metadata={"preflight_ok": preflight.ok, "rejections": preflight.rejections},
            )

            # Record patch preflight result to workflow memory
            if self._workflow_memory is not None and self._workflow_id:
                try:
                    self._workflow_memory.record_patch_preflight(self._workflow_id, act.task_id, preflight)
                except Exception:
                    pass

            # If preflight fails, run exactly one PATCH_FORMAT_REPAIR attempt (requirement 6 & 7)
            repair_result: PatchRepairResult | None = None
            if not preflight.ok:
                stderr = ""
                if preflight.git_check_result:
                    stderr = str(preflight.git_check_result.get("stderr") or preflight.git_check_result.get("error") or "")
                repair_result = await repair_patch_format(
                    diff,
                    stderr,
                    context_packet,
                    self.router.model_caller,
                    role="worker",
                    repo_root=str(self.router.repo_root),
                    rejections=preflight.rejections,
                    intensity=prepared.intensity,
                )
                attempt_record["repair"] = repair_result.to_dict()
                self._trace_builder_event(
                    act=act,
                    event_type="builder_repair_result",
                    status="repair_succeeded" if repair_result.ok else "repair_failed_blocked",
                    summary=f"Repair ok={repair_result.ok}",
                    raw_text=json.dumps(repair_result.to_dict(), indent=2, sort_keys=True, default=str),
                    metadata={"repair_ok": repair_result.ok},
                )

                # Record repair attempt to workflow memory
                if self._workflow_memory is not None and self._workflow_id:
                    try:
                        self._workflow_memory.record_repair_attempt(self._workflow_id, act.task_id, repair_result)
                    except Exception:
                        pass

                if repair_result.ok:
                    diff = repair_result.repaired_diff
                    attempt_record["status"] = "repair_succeeded"
                else:
                    attempt_record["status"] = "repair_failed_blocked"
                    attempt_record["failure_reason"] = self._builder_failure_report(
                        act,
                        grounding_dict,
                        context_packet,
                        status="repair_failed_blocked",
                        response=response,
                        preflight=preflight,
                        repair_result=repair_result,
                    )
                    self._trace_builder_failure(act, attempt_record["failure_reason"])
                    patch_attempts.append(attempt_record)
                    self._record_qdkt("patch_attempt", act.task_id, "failed", {
                        "preflight_rejections": preflight.rejections,
                        "repair_rejections": repair_result.rejections_after_repair,
                    })
                    continue  # Do not hot-swap — skip this submission

            touched = _diff_touched_files(diff)
            if not touched:
                attempt_record["status"] = "missing_patch_diff"
                attempt_record["failure_reason"] = self._builder_failure_report(
                    act,
                    grounding_dict,
                    context_packet,
                    status="missing_patch_diff",
                    response=response,
                    preflight=preflight,
                    repair_result=repair_result,
                )
                self._trace_builder_failure(act, attempt_record["failure_reason"])
                patch_attempts.append(attempt_record)
                self._record_qdkt("patch_attempt", act.task_id, "failed", {
                    "missing_patch_diff": True,
                })
                continue

            submission = {
                "task_id": act.task_id,
                "owner": self.router.profile_for("worker", intensity=prepared.intensity).model_class,
                "diff": diff,
                "affected_files": touched,
                "affected_symbols": [act.target_symbol] if act.target_symbol else [],
                "tests": [],
            }
            submissions.append(submission)

            # Record patch submission to workflow memory
            if self._workflow_memory is not None and self._workflow_id:
                try:
                    self._workflow_memory.record_patch_submission(self._workflow_id, submission)
                except Exception:
                    pass

            self._record_qdkt("patch_attempt", act.task_id, "staged", {
                "preflight_ok": preflight.ok,
                "rejections": preflight.rejections,
            })
            patch_attempts.append(attempt_record)

        builder_failures = [attempt["failure_reason"] for attempt in patch_attempts if attempt.get("failure_reason")]
        if not submissions and not builder_failures:
            grounding_by_task = {item.task_id: item.to_dict() for item in prepared.grounding}
            for act in prepared.plan.act_capsules:
                builder_failures.append(
                    self._builder_failure_report(
                        act,
                        grounding_by_task.get(act.task_id, {}),
                        None,
                        status="no_patch_staged",
                    )
                )
        self.patch_quality = {
            "attempts": patch_attempts,
            "review_artifacts": patch_attempts,
            "builder_failures": builder_failures,
            "total_attempts": len(patch_attempts),
            "preflight_passed": sum(1 for a in patch_attempts if a.get("status") == "preflight_passed"),
            "repair_succeeded": sum(1 for a in patch_attempts if a.get("status") == "repair_succeeded"),
            "repair_failed_blocked": sum(1 for a in patch_attempts if a.get("status") == "repair_failed_blocked"),
            "no_patch_staged": not bool(submissions),
        }
        return submissions


async def judge_patch_bundle(
    router: ArchitectModelRouter,
    prepared: ArchitectLoopResult,
    patch_submissions: list[dict[str, Any]],
    stage_results: list[PatchStageResult],
    council_decision: ArchitectCouncilDecision,
    workspace_result: TempWorkspaceResult | None = None,
) -> dict[str, Any]:
    expected_task_ids = [act.task_id for act in prepared.plan.act_capsules]
    staged_task_ids = [result.patch.task_id for result in stage_results if result.ok and result.patch]
    stage_failures = [
        finding.to_dict()
        for result in stage_results
        if not result.ok
        for finding in result.findings
    ]
    workspace_ok = workspace_result.ok if workspace_result is not None else True
    base_decision = {
        "role": "premium_judge",
        "phase": "patch_bundle_judge",
        "approved": sorted(expected_task_ids) == sorted(staged_task_ids) and not stage_failures and workspace_ok,
        "premium_called": False,
        "selected_candidate_id": council_decision.judge_decision.get("selected_candidate_id"),
        "rationale": "Local Judge accepted staged patch coverage and workspace verification." if sorted(expected_task_ids) == sorted(staged_task_ids) and not stage_failures and workspace_ok else "Patch bundle is incomplete, has staging failures, or workspace verification failed.",
        "expected_task_ids": expected_task_ids,
        "staged_task_ids": staged_task_ids,
        "stage_failures": stage_failures,
        "workspace_ok": workspace_ok,
    }
    budget_route = council_decision.budget_route
    if budget_route.get("premium_judge") and patch_submissions:
        workspace_summary: dict[str, Any] = {}
        if workspace_result is not None:
            workspace_summary = {
                "workspace_ok": workspace_result.ok,
                "workspace_failures": workspace_result.failures,
                "topology_delta_summary": workspace_result.topology_delta.get("summary", {}) if workspace_result.topology_delta else {},
                "test_results": workspace_result.test_results,
            }
        prompt = (
            "You are Aura's premium Judge. Return JSON only with approved and rationale. "
            "Compare the selected plan, staged patch bundle, temp workspace apply/test/topology results, and cheap Shadow critique before hot-swap promotion. "
            f"Plan: {json.dumps(prepared.plan.to_dict(), sort_keys=True)}\n"
            f"Patch submissions: {json.dumps(patch_submissions, sort_keys=True)}\n"
            f"Stage results: {json.dumps([item.to_dict() for item in stage_results], sort_keys=True, default=str)}\n"
            f"Temp workspace result: {json.dumps(workspace_summary, sort_keys=True, default=str)}\n"
            f"Council: {json.dumps(council_decision.to_dict(), sort_keys=True, default=str)}"
        )
        response = await router.call_model(
            "judge",
            prompt,
            intensity=prepared.intensity,
            meta={"council_phase": "patch_bundle_judge", "candidate_id": council_decision.judge_decision.get("selected_candidate_id")},
        )
        data = _extract_json_object(response or "") if response else None
        if data:
            base_decision["approved"] = _normalize_judge_approval(data.get("approved"), default=bool(base_decision["approved"]))
            base_decision["rationale"] = str(data.get("rationale") or base_decision["rationale"])
            base_decision["premium_called"] = True
    return {**base_decision, "phase_hash": _hash_payload(base_decision)}


def _merge_council_patch_judgement(
    verification: VerificationResult,
    patch_judgement: dict[str, Any],
) -> VerificationResult:
    if _normalize_judge_approval(patch_judgement.get("approved"), default=False):
        return verification
    failure = {
        "stage": "council_judge",
        "status": "failed",
        "message": "Premium Judge blocked hot-swap promotion for the staged patch bundle.",
        "judgement": patch_judgement,
    }
    failures = [*verification.failures, failure]
    checks = [*verification.checks, failure]
    phase_payload = {
        "base_phase_hash": verification.phase_hash,
        "patch_judgement": patch_judgement,
        "failures": failures,
    }
    return VerificationResult(
        verification_version=verification.verification_version,
        ok=False,
        stage="blocked",
        checks=checks,
        failures=failures,
        hotswap_ready=False,
        phase_hash=_hash_payload(phase_payload),
    )


def _augment_live_hotswap_capsule(
    capsule: dict[str, Any],
    *,
    council_decision: ArchitectCouncilDecision,
    patch_judgement: dict[str, Any],
    topology_delta: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        **{key: value for key, value in capsule.items() if key != "phase_hash"},
        "fusion_council_phase_hash": council_decision.phase_hash,
        "patch_judge_phase_hash": patch_judgement.get("phase_hash"),
        "topology_delta": topology_delta,
        "promotion_entrypoint": {
            "review_command": "!stage",
            "promote_command": "!stage_merge",
            "staging_file": "Aura_Staging/architect_live_transaction.json",
        },
    }
    return {**payload, "phase_hash": _hash_payload(payload)}


def verify_arena_in_temp_workspace(
    arena: RefactorArenaTransaction,
    *,
    repo_root: str | Path = REPO_ROOT,
    test_commands: list[list[str]] | None = None,
    keep_workspace: bool = False,
) -> TempWorkspaceResult:
    """Apply staged patches in a copied workspace and run local verification there."""
    root = Path(repo_root).resolve()
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    test_results: dict[str, dict[str, Any]] = {}
    if not arena.shared_patch_queue:
        return TempWorkspaceResult(ok=False, checks=[], failures=[{"stage": "temp_workspace", "message": "No patches to apply."}], test_results={})

    git = _git_executable()
    if git is None:
        return TempWorkspaceResult(ok=False, checks=[], failures=[{"stage": "temp_workspace", "message": "git executable is unavailable."}], test_results={})

    temp_root = Path(tempfile.mkdtemp(prefix="aura_architect_workspace_"))
    workspace = temp_root / "repo"
    try:
        shutil.copytree(root, workspace, ignore=_repo_copy_ignore)
        checks.append({"stage": "temp_workspace_copy", "status": "passed", "workspace": str(workspace)})
        for patch in arena.shared_patch_queue:
            result = _run_command([git, "apply", "--whitespace=nowarn", "-"], cwd=workspace, stdin=str(patch.get("diff", "")))
            result["stage"] = "temp_workspace_apply"
            result["patch_id"] = patch.get("patch_id")
            checks.append(result)
            if result.get("returncode") != 0:
                failures.append(result)
                return TempWorkspaceResult(ok=False, checks=checks, failures=failures, test_results=test_results, workspace_path=str(workspace))

        topology_delta = compute_temp_workspace_topology_delta(arena, repo_root=root, workspace=workspace)
        checks.append(topology_delta)
        if topology_delta.get("status") != "passed":
            failures.append(
                {
                    "stage": "topology_delta",
                    "status": "failed",
                    "message": "Temporary workspace topology delta could not be parsed.",
                    "failures": topology_delta.get("failures", []),
                }
            )

        commands = test_commands if test_commands is not None else _default_test_commands(arena, workspace)
        if not commands:
            checks.append({"stage": "temp_workspace_tests", "status": "passed", "cmd": []})
        for command in commands:
            result = _run_command(command, cwd=workspace)
            result["stage"] = "temp_workspace_tests"
            checks.append(result)
            if result.get("returncode") != 0:
                failures.append(result)
        status = "passed" if not failures else "failed"
        for test_name in _test_files_from_arena(arena):
            test_results[test_name] = {"status": status, "workspace_checks": checks[-len(commands):] if commands else []}
        if not test_results:
            test_results["temp_workspace"] = {"status": status, "workspace_checks": checks}
        return TempWorkspaceResult(ok=not failures, checks=checks, failures=failures, test_results=test_results, workspace_path=str(workspace), topology_delta=topology_delta)
    finally:
        if not keep_workspace:
            shutil.rmtree(temp_root, ignore_errors=True)


def _record_patch_dream_usefulness(
    intent: str,
    context_packets: list[BuilderContextPacket],
    workspace: TempWorkspaceResult,
    verification: VerificationResult,
    phase_hash: str,
) -> None:
    """Record DREAM usefulness rows for source context, tests, graph nodes, and verifier diagnostics.

    Research basis: DREAM usefulness tracking; CoverUp test-usefulness; Context Engineering survey.
    """
    if record_arena_retrieval_feedback is None or DreamCandidate is None:
        return
    verifier_result = {"approved": verification.ok, "hotswap_ready": verification.hotswap_ready}
    candidates: list[Any] = []
    for packet in context_packets:
        if packet.source_excerpt:
            candidates.append(DreamCandidate(
                candidate_id=f"source:{packet.target_file}",
                candidate_type="source_excerpt",
                source="CODEMAP/source_file",
                content=packet.source_excerpt[:200],
                semantic_score=0.85,
                verifier_result=verifier_result,
            ))
        for test in packet.nearby_tests:
            candidates.append(DreamCandidate(
                candidate_id=f"test:{test}",
                candidate_type="nearby_test",
                source="CODEMAP/test-neighbor",
                content=test,
                semantic_score=0.72,
                verifier_result=verifier_result,
            ))
        for caller in packet.callers:
            candidates.append(DreamCandidate(
                candidate_id=f"caller:{caller}",
                candidate_type="graph_node",
                source="CODEMAP/topology",
                content=caller,
                semantic_score=0.65,
                verifier_result=verifier_result,
            ))
        for neighbor in packet.neighbors:
            candidates.append(DreamCandidate(
                candidate_id=f"neighbor:{neighbor}",
                candidate_type="graph_node",
                source="CODEMAP/topology",
                content=neighbor,
                semantic_score=0.58,
                verifier_result=verifier_result,
            ))
    if workspace.failures:
        candidates.append(DreamCandidate(
            candidate_id="verifier:workspace_failures",
            candidate_type="verifier_diagnostic",
            source="temp_workspace",
            content=json.dumps(workspace.failures[:3], default=str)[:200],
            semantic_score=0.70,
            verifier_result=verifier_result,
        ))
    if workspace.topology_delta and workspace.topology_delta.get("summary"):
        candidates.append(DreamCandidate(
            candidate_id="verifier:topology_delta",
            candidate_type="verifier_diagnostic",
            source="temp_workspace_topology",
            content=json.dumps(workspace.topology_delta.get("summary"), default=str)[:200],
            semantic_score=0.68,
            verifier_result=verifier_result,
        ))
    if not candidates:
        return
    try:
        record_arena_retrieval_feedback(
            intent,
            candidates,
            target_type="code_context",
            verifier_result=verifier_result,
            arena_domain="code",
        )
    except Exception:
        pass


async def run_live_architect_transaction(
    intent: str,
    *,
    repo_root: str | Path = REPO_ROOT,
    model_caller: ModelCaller | None = None,
    target_file: str | None = None,
    target_symbol: str | None = None,
    ledger_path: str | Path | None = None,
    staging_path: str | Path | None = None,
    test_commands: list[list[str]] | None = None,
) -> LiveArchitectTransaction:
    """Run the live Architect path without direct production or incubator writes."""
    effective_root = Path(repo_root).resolve()
    effective_ledger_path = Path(ledger_path) if ledger_path is not None else effective_root / "Aura_Memory" / "architect_loop_ledger.jsonl"
    effective_staging_path = Path(staging_path) if staging_path is not None else effective_root / "Aura_Staging" / "architect_live_transaction.json"

    router = ArchitectModelRouter(repo_root=effective_root, model_caller=model_caller, ledger_path=effective_ledger_path)

    # Begin Coding Arena workflow memory tracking (scope ledger to repo root)
    workflow_memory = None
    workflow_id = ""
    if CodingArenaWorkflowMemory is not None:
        try:
            ledger = effective_root / "Aura_Memory" / "coding_arena_workflows.jsonl"
            workflow_memory = CodingArenaWorkflowMemory(ledger_path=ledger)
            workflow_id = workflow_memory.begin_workflow(intent, target_file or "")
        except Exception:
            workflow_memory = None
    trace_task_id = workflow_id or _trace_task_key("transaction", intent, target_file, target_symbol)

    council_decision = await router.plan_with_council(intent, target_file=target_file, target_symbol=target_symbol)

    # Record plan candidates and shadow critiques to workflow memory
    if workflow_memory is not None and workflow_id:
        try:
            for candidate in council_decision.candidates:
                workflow_memory.record_plan_candidate(workflow_id, candidate)
            for critic_report in council_decision.critic_reports:
                workflow_memory.record_shadow_critique(workflow_id, critic_report)
        except Exception:
            pass

    plan_spec = council_decision.selected_plan
    selected_music_mitosis = plan_spec.get("music_mitosis") or council_decision.music_mitosis
    arena_objective = intent
    if music_builder_objective is not None:
        try:
            arena_objective = music_builder_objective(intent, selected_music_mitosis)
        except Exception:
            arena_objective = intent
    act_tasks = plan_spec["act_tasks"]
    if augment_act_tasks_with_music is not None:
        try:
            act_tasks = augment_act_tasks_with_music(act_tasks, selected_music_mitosis)
        except Exception:
            act_tasks = plan_spec["act_tasks"]
    loop = ArchitectFusionLoop(repo_root=effective_root)
    prepared = loop.prepare(
        arena_objective,
        architecture_decision=plan_spec["architecture_decision"],
        target_file=plan_spec.get("target_file"),
        target_symbol=plan_spec.get("target_symbol"),
        act_tasks=act_tasks,
        acceptance_criteria=[
            "Builder output is staged as a patch submission, never written directly to production.",
            "Patch applies in a temporary workspace before hot-swap readiness.",
            "Architect ledger records the verified or blocked transaction.",
        ],
        rollback_conditions=[
            "Shadow blocker",
            "Patch boundary mismatch",
            "Temporary workspace apply or test failure",
        ],
        risk_map=[
            "legacy aura_incubator.py path is bypassed",
            "model output must be unified diff only",
            "local verifier decides hot-swap readiness",
        ],
    )
    builder = ArchitectBuilderBridge(router, workflow_memory=workflow_memory, workflow_id=workflow_id)
    patch_submissions = await builder.build_patch_submissions(prepared, objective=arena_objective)
    patchable_submissions = _patchable_submissions(patch_submissions)
    agentless_fallback: dict[str, Any] | None = None
    if not _has_patchable_submission(patch_submissions):
        agentless_fallback = run_agentless_fallback(intent, effective_root)
        if agentless_fallback.get("localized_files"):
            agentless_fallback["localized_files"] = list(agentless_fallback.get("localized_files", []) or [])[:5]
    stage_results = [
        stage_arena_patch(
            prepared.arena,
            task_id=str(submission.get("task_id", "")),
            owner=str(submission.get("owner", "cheap_act_worker")),
            diff=str(submission.get("diff", "")),
            affected_files=list(submission.get("affected_files", []) or []),
            affected_symbols=list(submission.get("affected_symbols", []) or []),
            tests=list(submission.get("tests", []) or []),
        )
        for submission in patchable_submissions
    ]

    # Run workspace verification BEFORE judge so the premium judge sees apply/test/topology results (requirement 8)
    workspace = verify_arena_in_temp_workspace(prepared.arena, repo_root=effective_root, test_commands=test_commands)
    _record_symbolic_trace(
        effective_root,
        {
            "event_type": "workspace_apply_test_result",
            "task_id": trace_task_id,
            "node_id": f"{trace_task_id}:workspace_apply_test",
            "status": "passed" if workspace.ok else "failed",
            "route": "verifier",
            "summary": f"Temp workspace ok={workspace.ok} failures={len(workspace.failures)}",
            "raw_text": json.dumps(workspace.to_dict(), indent=2, sort_keys=True, default=str),
            "metadata": {
                "related_files": list(prepared.arena.affected_files),
                "workspace_path": workspace.workspace_path,
            },
        },
    )

    # Record temp workspace apply and py_compile/test/topology_delta results to workflow memory
    if workflow_memory is not None and workflow_id:
        try:
            workflow_memory.record_temp_workspace_apply(workflow_id, workspace)
            workflow_memory.record_py_compile_test_topology(workflow_id, workspace)
        except Exception:
            pass

    # Test gap filling: if Shadow reports missing tests, generate minimal regression tests in temp workspace only (requirement 9)
    test_gap_result: TestGapFillerResult | None = None
    shadow_findings_dicts = [finding.to_dict() for finding in prepared.shadow_report.findings]
    missing_test_findings = detect_missing_test_findings(shadow_findings_dicts)
    if missing_test_findings:
        gap_filler_temp = Path(tempfile.mkdtemp(prefix="aura_test_gap_"))
        try:
            first_finding = missing_test_findings[0]
            gap_target_file = first_finding.get("target_file") or plan_spec.get("target_file")
            gap_target_symbol = first_finding.get("target_symbol") or plan_spec.get("target_symbol")
            gap_grounding: dict[str, Any] = {}
            for evidence in prepared.grounding:
                if evidence.target_file == gap_target_file:
                    gap_grounding = evidence.to_dict()
                    break
            codemap_path = effective_root / ".aura" / "CODEMAP.json"
            gap_codemap: dict[str, Any] | None = None
            if codemap_path.exists():
                try:
                    gap_codemap = json.loads(codemap_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    gap_codemap = None
            gap_context_packet = build_builder_context_packet(
                target_file=gap_target_file,
                target_symbol=gap_target_symbol,
                grounding_evidence=gap_grounding,
                codemap=gap_codemap,
                repo_root=effective_root,
                objective=arena_objective,
                task_id="test_gap_filler",
                topological_grounding=plan_spec.get("topological_grounding", {}),
            )
            test_gap_result = await fill_test_gap(
                shadow_findings_dicts,
                gap_context_packet,
                gap_filler_temp,
                model_caller,
                role="worker",
            )
        finally:
            shutil.rmtree(gap_filler_temp, ignore_errors=True)

    # Premium patch judge now sees temp workspace apply/test/topology results before approving hot-swap (requirement 8)
    patch_judgement = await judge_patch_bundle(
        router, prepared, patchable_submissions, stage_results, council_decision, workspace_result=workspace,
    )
    _record_symbolic_trace(
        effective_root,
        {
            "event_type": "verifier_patch_judge_decision",
            "task_id": trace_task_id,
            "node_id": f"{trace_task_id}:patch_judge",
            "status": "done" if patch_judgement.get("approved", False) else "blocked",
            "route": "verifier",
            "summary": f"Patch judge approved={patch_judgement.get('approved')} premium_called={patch_judgement.get('premium_called')}",
            "raw_text": json.dumps(patch_judgement, indent=2, sort_keys=True, default=str),
        },
    )

    # Record premium judge decision to workflow memory
    if workflow_memory is not None and workflow_id:
        try:
            workflow_memory.record_premium_judge_decision(workflow_id, patch_judgement)
        except Exception:
            pass

    def runner(test_name: str) -> dict[str, Any]:
        return workspace.test_results.get(test_name, {"status": "passed" if workspace.ok else "failed"})

    verification = verify_refactor_arena(prepared.arena, repo_root=effective_root, runner=runner)
    verification = _merge_act_stage_result(verification, prepared, stage_results)
    verification = _merge_council_plan_judgement(verification, council_decision)
    verification = _merge_council_patch_judgement(verification, patch_judgement)
    verification = _merge_workspace_result(verification, workspace)
    _record_symbolic_trace(
        effective_root,
        {
            "event_type": "verifier_decision",
            "task_id": trace_task_id,
            "node_id": f"{trace_task_id}:verifier_decision",
            "status": "done" if verification.hotswap_ready else "blocked",
            "route": "verifier",
            "summary": f"Verifier hotswap_ready={verification.hotswap_ready} stage={verification.stage}",
            "raw_text": json.dumps(verification.to_dict(), indent=2, sort_keys=True, default=str),
            "metadata": {"related_files": list(prepared.arena.affected_files)},
        },
    )
    hotswap_capsule = build_hotswap_capsule(prepared.arena, verification, repo_root=effective_root)
    hotswap_capsule = _augment_live_hotswap_capsule(
        hotswap_capsule,
        council_decision=council_decision,
        patch_judgement=patch_judgement,
        topology_delta=workspace.topology_delta,
    )
    _record_symbolic_trace(
        effective_root,
        {
            "event_type": "rollback_metadata",
            "task_id": trace_task_id,
            "node_id": f"{trace_task_id}:rollback_metadata",
            "status": "proposed",
            "route": "hotswap",
            "summary": "Rollback metadata preserved for staged Architect transaction",
            "raw_text": json.dumps(
                {
                    "rollback_hint": prepared.arena.rollback_hint,
                    "rollback_conditions": prepared.plan.rollback_conditions,
                    "promotion_entrypoint": hotswap_capsule.get("promotion_entrypoint", {}),
                },
                indent=2,
                sort_keys=True,
                default=str,
            ),
            "metadata": {"related_files": list(prepared.arena.affected_files)},
        },
    )
    _record_symbolic_trace(
        effective_root,
        {
            "event_type": "hotswap_readiness",
            "task_id": trace_task_id,
            "node_id": f"{trace_task_id}:hotswap_readiness",
            "status": "ready" if hotswap_capsule.get("hotswap_ready") else "blocked",
            "route": "hotswap",
            "summary": f"Hotswap status={hotswap_capsule.get('status')} ready={hotswap_capsule.get('hotswap_ready')}",
            "raw_text": json.dumps(hotswap_capsule, indent=2, sort_keys=True, default=str),
            "metadata": {"related_files": list(prepared.arena.affected_files)},
        },
    )

    # Record hotswap decision to workflow memory
    if workflow_memory is not None and workflow_id:
        try:
            workflow_memory.record_hotswap_decision(workflow_id, hotswap_capsule)
        except Exception:
            pass

    ledger_record = build_architect_ledger_record(prepared, stage_results, verification, hotswap_capsule)
    append_architect_ledger(ledger_record, ledger_path=effective_ledger_path)

    # Record final verifier decision to QDKT (requirement 10)
    if get_qdkt is not None:
        try:
            get_qdkt().observe(
                "patch_verifier_decision",
                {
                    "hotswap_ready": verification.hotswap_ready,
                    "failures_count": len(verification.failures),
                    "stage": verification.stage,
                },
                rationale=f"Final verifier decision: {'hotswap_ready' if verification.hotswap_ready else 'blocked'}",
                concept=f"verifier_decision:{prepared.plan.phase_hash}",
                confidence=0.9 if verification.hotswap_ready else 0.4,
                subsystem="aura_live_architect",
            )
        except Exception:
            pass

    # Record DREAM usefulness rows for source context, tests, graph nodes, and verifier diagnostics (requirement 11)
    context_packets_for_dream: list[BuilderContextPacket] = []
    dream_codemap: dict[str, Any] | None = None
    dream_codemap_path = effective_root / ".aura" / "CODEMAP.json"
    if dream_codemap_path.exists():
        try:
            dream_codemap = json.loads(dream_codemap_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            dream_codemap = None
    for act in prepared.plan.act_capsules:
        act_grounding: dict[str, Any] = {}
        for evidence in prepared.grounding:
            if evidence.task_id == act.task_id:
                act_grounding = evidence.to_dict()
                break
        context_packets_for_dream.append(
            build_builder_context_packet(
                target_file=act.target_file,
                target_symbol=act.target_symbol,
                grounding_evidence=act_grounding,
                codemap=dream_codemap,
                repo_root=effective_root,
                objective=arena_objective,
                task_id=act.task_id,
                topological_grounding=act.topological_grounding,
            )
        )
    _record_patch_dream_usefulness(intent, context_packets_for_dream, workspace, verification, prepared.plan.phase_hash)

    # Assemble patch quality metadata
    patch_quality = {
        **builder.patch_quality,
        "agentless_fallback": agentless_fallback,
        "patch_submission_count": len(patch_submissions),
        "patchable_submission_count": len(patchable_submissions),
        "music_mitosis": selected_music_mitosis,
        "test_gap_filler": test_gap_result.to_dict() if test_gap_result else None,
        "verifier_decision": {
            "hotswap_ready": verification.hotswap_ready,
            "stage": verification.stage,
            "failures_count": len(verification.failures),
        },
    }

    output_path = effective_staging_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    transaction = LiveArchitectTransaction(
        live_version=ARCHITECT_LIVE_VERSION,
        prepared=prepared,
        stage_results=stage_results,
        workspace=workspace,
        verification=verification,
        hotswap_capsule=hotswap_capsule,
        ledger_record=ledger_record,
        staging_path=str(output_path),
        model_route={
            "plan_source": plan_spec.get("source"),
            "profiles": {name: profile.to_dict() for name, profile in router.profiles.items()},
            "ledger_hints": plan_spec.get("ledger_hints", {}),
            "budget_route": council_decision.budget_route,
            "music_mitosis": selected_music_mitosis,
            "topological_grounding": plan_spec.get("topological_grounding", {}),
        },
        fusion_council={
            **council_decision.to_dict(),
            "patch_judgement": patch_judgement,
        },
        patch_quality=patch_quality,
    )
    output_path.write_text(json.dumps(transaction.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")

    # Record final workflow outcome to Coding Arena workflow memory (wires to QDKT + DREAM)
    if workflow_memory is not None and workflow_id and WorkflowOutcome is not None:
        try:
            outcome = WorkflowOutcome(
                workflow_id=workflow_id,
                success=verification.hotswap_ready,
                hotswap_ready=verification.hotswap_ready,
                failures_count=len(verification.failures),
                stage=verification.stage,
                phase_hash=prepared.plan.phase_hash,
                intent=intent,
                target_file=plan_spec.get("target_file") or "",
                outcome_summary=f"{'hotswap_ready' if verification.hotswap_ready else 'blocked'}: {verification.stage}",
            )
            workflow_memory.record_outcome(workflow_id, outcome, context_packets=context_packets_for_dream)
        except Exception:
            pass

    return transaction


def render_live_architect_summary(transaction: LiveArchitectTransaction) -> str:
    status = "HOTSWAP READY" if transaction.verification.hotswap_ready else "BLOCKED"
    staged = sum(1 for item in transaction.stage_results if item.ok)
    blocked = len(transaction.verification.failures)
    target_files = ", ".join(transaction.prepared.arena.affected_files) or "none"
    council = transaction.fusion_council or {}
    judge = council.get("judge_decision", {})
    topology_summary = transaction.workspace.topology_delta.get("summary", {}) if transaction.workspace.topology_delta else {}
    return (
        "LIVE ARCHITECT TRANSACTION\n"
        f"Status        : {status}\n"
        f"Intensity     : {transaction.prepared.intensity}\n"
        f"Target files  : {target_files}\n"
        f"Patches staged: {staged}\n"
        f"Verifier fails: {blocked}\n"
        f"Council pick  : {judge.get('selected_candidate_id', 'n/a')}\n"
        f"Judge path    : {judge.get('role', 'n/a')}\n"
        f"Topology delta: {topology_summary.get('files_checked', 0)} files checked\n"
        f"Staging file  : {transaction.staging_path}\n"
        f"Ledger hash   : {transaction.ledger_record.phase_hash}\n"
    )
