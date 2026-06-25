"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa903-[Q-SYS:LIVE_ARCHITECT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Live / Bounded Refactor Execution)
DEPENDENCIES: ast, dataclasses, inspect, json, pathlib, shutil, subprocess, tempfile, typing, aura_architect_loop, aura_substrate
FUNCTIONS: ArchitectModelProfile, ArchitectFusionCouncil, ArchitectModelRouter, ArchitectBuilderBridge, TempWorkspaceResult, LiveArchitectTransaction, run_live_architect_transaction, render_live_architect_summary, verify_arena_in_temp_workspace
SYNOPSIS: Live bridge for Architect mode. Routes a user intent through multi-candidate premium planning, cheap Shadow critics, premium judge selection, cheap bounded Act workers, temp-workspace patch application, topology delta verification, verifier-gated hot-swap readiness, rollback, and ledger output without writing model code directly to production or aura_incubator.py.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import ast
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
from typing import Any, Callable

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
from aura_liquid_planning_arena import build_world_state_delta
from aura_substrate import REPO_ROOT


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
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
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
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
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
        source: str = "deterministic_fallback",
    ) -> dict[str, Any]:
        inferred_file = target_file or self.infer_target_file(intent)
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
                    }
                ],
                "source": "deterministic_fallback_blocked" if source == "deterministic_fallback" else source,
                "ledger_hints": hints,
            }
        return {
            "architecture_decision": "Route live Architect intent through Plan/Act, temp verification, hot-swap, rollback, and ledger gates.",
            "target_file": inferred_file,
            "target_symbol": target_symbol,
            "act_tasks": [
                {
                    "task_id": "A-LIVE-1",
                    "objective": intent,
                    "target_file": inferred_file,
                    "target_symbol": target_symbol,
                    "allowed_scope": "single live Architect Act Capsule",
                    "acceptance": "Return a unified diff that applies cleanly in the temporary workspace and passes local verification.",
                    "expected_output": "UNIFIED_DIFF",
                }
            ],
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
        source: str,
    ) -> dict[str, Any] | None:
        tasks = data.get("act_tasks") if isinstance(data.get("act_tasks"), list) else []
        if not tasks:
            return None
        return {
            "architecture_decision": str(data.get("architecture_decision") or "Use the live Architect loop."),
            "target_file": str(data.get("target_file") or inferred_file) if data.get("target_file") or inferred_file else None,
            "target_symbol": str(data.get("target_symbol") or target_symbol) if data.get("target_symbol") or target_symbol else None,
            "act_tasks": tasks,
            "source": source,
            "ledger_hints": self.router.ledger_hints(),
            "objective": intent,
        }

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
        inferred_file = target_file or self.router.infer_target_file(intent)
        budget_route = self.router.budget_route(hints, target_file=inferred_file)
        local_plan = self.router.deterministic_plan_spec(
            intent,
            target_file=inferred_file,
            target_symbol=target_symbol,
            source="deterministic_codemap_plan",
        )
        candidates = [self._candidate("local_free", local_plan, cost_tier="free", source=local_plan.get("source", "deterministic_codemap_plan"))]
        prompt = (
            "Return JSON only for a bounded Aura Architect refactor plan. "
            "Fields: architecture_decision, target_file, target_symbol, act_tasks. "
            "Each act task must include task_id, objective, target_file, target_symbol, acceptance, expected_output=UNIFIED_DIFF. "
            "Never write code directly to production. "
            f"Ledger hints: {json.dumps(hints, sort_keys=True)}. "
            f"Intent: {intent}. Suggested target_file: {inferred_file or 'unknown'}."
        )
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
                target_symbol=target_symbol,
                source=f"premium_{role}",
            )
            if plan:
                candidates.append(self._candidate(candidate_id, plan, cost_tier="premium", source=plan["source"]))

        critic_reports = await self._run_shadow_critics(candidates, budget_route)
        judge_decision = await self._judge_candidates(candidates, budget_route)
        selected_id = judge_decision["selected_candidate_id"]
        selected = next((item for item in candidates if item["candidate_id"] == selected_id), candidates[0])
        selected_plan = dict(selected["plan"])
        selected_plan["source"] = selected.get("source", selected_plan.get("source", "fusion_council"))
        selected_plan["council_candidate_id"] = selected["candidate_id"]
        selected_plan["ledger_hints"] = hints
        payload = {
            "selected_plan": selected_plan,
            "candidates": candidates,
            "critic_reports": critic_reports,
            "judge_decision": judge_decision,
            "budget_route": budget_route,
        }
        return ArchitectCouncilDecision(phase_hash=_hash_payload(payload), **payload)


class ArchitectBuilderBridge:
    """Calls bounded Act workers and converts model replies into patch submissions."""

    def __init__(self, router: ArchitectModelRouter):
        self.router = router

    async def build_patch_submissions(self, prepared: ArchitectLoopResult, *, objective: str) -> list[dict[str, Any]]:
        if not prepared.arena.ready_for_incubator:
            return []
        submissions: list[dict[str, Any]] = []
        for act in prepared.plan.act_capsules:
            prompt = (
                "You are an Aura cheap Act worker. Return one unified diff only. "
                "Do not write files. Do not include prose. "
                f"Objective: {objective}\n"
                f"Act Capsule: {json.dumps(act.to_dict(), sort_keys=True)}"
            )
            response = await self.router.call_model("worker", prompt, intensity=prepared.intensity, meta={"task_id": act.task_id})
            if not response:
                continue
            diff = _extract_diff(response)
            touched = _diff_touched_files(diff)
            submissions.append(
                {
                    "task_id": act.task_id,
                    "owner": self.router.profile_for("worker", intensity=prepared.intensity).model_class,
                    "diff": diff,
                    "affected_files": touched or ([act.target_file] if act.target_file else []),
                    "affected_symbols": [act.target_symbol] if act.target_symbol else [],
                    "tests": [],
                }
            )
        return submissions


async def judge_patch_bundle(
    router: ArchitectModelRouter,
    prepared: ArchitectLoopResult,
    patch_submissions: list[dict[str, Any]],
    stage_results: list[PatchStageResult],
    council_decision: ArchitectCouncilDecision,
) -> dict[str, Any]:
    expected_task_ids = [act.task_id for act in prepared.plan.act_capsules]
    staged_task_ids = [result.patch.task_id for result in stage_results if result.ok and result.patch]
    stage_failures = [
        finding.to_dict()
        for result in stage_results
        if not result.ok
        for finding in result.findings
    ]
    base_decision = {
        "role": "premium_judge",
        "phase": "patch_bundle_judge",
        "approved": sorted(expected_task_ids) == sorted(staged_task_ids) and not stage_failures,
        "premium_called": False,
        "selected_candidate_id": council_decision.judge_decision.get("selected_candidate_id"),
        "rationale": "Local Judge accepted staged patch coverage." if sorted(expected_task_ids) == sorted(staged_task_ids) and not stage_failures else "Patch bundle is incomplete or has staging failures.",
        "expected_task_ids": expected_task_ids,
        "staged_task_ids": staged_task_ids,
        "stage_failures": stage_failures,
    }
    budget_route = council_decision.budget_route
    if budget_route.get("premium_judge") and patch_submissions:
        prompt = (
            "You are Aura's premium Judge. Return JSON only with approved and rationale. "
            "Compare the selected plan, staged patch bundle, and cheap Shadow critique before hot-swap promotion. "
            f"Plan: {json.dumps(prepared.plan.to_dict(), sort_keys=True)}\n"
            f"Patch submissions: {json.dumps(patch_submissions, sort_keys=True)}\n"
            f"Stage results: {json.dumps([item.to_dict() for item in stage_results], sort_keys=True, default=str)}\n"
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
    council_decision = await router.plan_with_council(intent, target_file=target_file, target_symbol=target_symbol)
    plan_spec = council_decision.selected_plan
    loop = ArchitectFusionLoop(repo_root=effective_root)
    prepared = loop.prepare(
        intent,
        architecture_decision=plan_spec["architecture_decision"],
        target_file=plan_spec.get("target_file"),
        target_symbol=plan_spec.get("target_symbol"),
        act_tasks=plan_spec["act_tasks"],
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
    builder = ArchitectBuilderBridge(router)
    patch_submissions = await builder.build_patch_submissions(prepared, objective=intent)
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
        for submission in patch_submissions
    ]
    patch_judgement = await judge_patch_bundle(router, prepared, patch_submissions, stage_results, council_decision)
    workspace = verify_arena_in_temp_workspace(prepared.arena, repo_root=effective_root, test_commands=test_commands)

    def runner(test_name: str) -> dict[str, Any]:
        return workspace.test_results.get(test_name, {"status": "passed" if workspace.ok else "failed"})

    verification = verify_refactor_arena(prepared.arena, repo_root=effective_root, runner=runner)
    verification = _merge_act_stage_result(verification, prepared, stage_results)
    verification = _merge_council_plan_judgement(verification, council_decision)
    verification = _merge_council_patch_judgement(verification, patch_judgement)
    verification = _merge_workspace_result(verification, workspace)
    hotswap_capsule = build_hotswap_capsule(prepared.arena, verification, repo_root=effective_root)
    hotswap_capsule = _augment_live_hotswap_capsule(
        hotswap_capsule,
        council_decision=council_decision,
        patch_judgement=patch_judgement,
        topology_delta=workspace.topology_delta,
    )
    ledger_record = build_architect_ledger_record(prepared, stage_results, verification, hotswap_capsule)
    append_architect_ledger(ledger_record, ledger_path=effective_ledger_path)

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
        },
        fusion_council={
            **council_decision.to_dict(),
            "patch_judgement": patch_judgement,
        },
    )
    output_path.write_text(json.dumps(transaction.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
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
