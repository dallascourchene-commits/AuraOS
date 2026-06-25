"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa903-[Q-SYS:LIVE_ARCHITECT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Live / Bounded Refactor Execution)
DEPENDENCIES: dataclasses, inspect, json, pathlib, shutil, subprocess, tempfile, typing, aura_architect_loop, aura_substrate
FUNCTIONS: ArchitectModelProfile, ArchitectModelRouter, ArchitectBuilderBridge, TempWorkspaceResult, LiveArchitectTransaction, run_live_architect_transaction, render_live_architect_summary, verify_arena_in_temp_workspace
SYNOPSIS: Live bridge for Architect mode. Routes a user intent through premium planning, cheap bounded Act workers, temp-workspace patch application, verifier-gated hot-swap readiness, rollback, and ledger output without writing model code directly to production or aura_incubator.py.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

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

    async def plan_intent(
        self,
        intent: str,
        *,
        target_file: str | None = None,
        target_symbol: str | None = None,
    ) -> dict[str, Any]:
        hints = self.ledger_hints()
        inferred_file = target_file or self.infer_target_file(intent)
        prompt = (
            "Return JSON only for a bounded Aura Architect refactor plan. "
            "Fields: architecture_decision, target_file, target_symbol, act_tasks. "
            "Each act task must include task_id, objective, target_file, target_symbol, acceptance, expected_output=UNIFIED_DIFF. "
            "Never write code directly to production. "
            f"Ledger hints: {json.dumps(hints, sort_keys=True)}. "
            f"Intent: {intent}. Suggested target_file: {inferred_file or 'unknown'}."
        )
        response = await self.call_model("planner", prompt, intensity=4 if hints.get("prefer_premium") else 1)
        data = _extract_json_object(response or "") if response else None
        if data:
            tasks = data.get("act_tasks") if isinstance(data.get("act_tasks"), list) else []
            if tasks:
                return {
                    "architecture_decision": str(data.get("architecture_decision") or "Use the live Architect loop."),
                    "target_file": str(data.get("target_file") or inferred_file) if data.get("target_file") or inferred_file else None,
                    "target_symbol": str(data.get("target_symbol") or target_symbol) if data.get("target_symbol") or target_symbol else None,
                    "act_tasks": tasks,
                    "source": "premium_planner",
                    "ledger_hints": hints,
                }
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
                "source": "deterministic_fallback_blocked",
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
            "source": "deterministic_fallback",
            "ledger_hints": hints,
        }


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
        return TempWorkspaceResult(ok=not failures, checks=checks, failures=failures, test_results=test_results, workspace_path=str(workspace))
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
    plan_spec = await router.plan_intent(intent, target_file=target_file, target_symbol=target_symbol)
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
    workspace = verify_arena_in_temp_workspace(prepared.arena, repo_root=effective_root, test_commands=test_commands)

    def runner(test_name: str) -> dict[str, Any]:
        return workspace.test_results.get(test_name, {"status": "passed" if workspace.ok else "failed"})

    verification = verify_refactor_arena(prepared.arena, repo_root=effective_root, runner=runner)
    verification = _merge_act_stage_result(verification, prepared, stage_results)
    verification = _merge_workspace_result(verification, workspace)
    hotswap_capsule = build_hotswap_capsule(prepared.arena, verification, repo_root=effective_root)
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
        },
    )
    output_path.write_text(json.dumps(transaction.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return transaction


def render_live_architect_summary(transaction: LiveArchitectTransaction) -> str:
    status = "HOTSWAP READY" if transaction.verification.hotswap_ready else "BLOCKED"
    staged = sum(1 for item in transaction.stage_results if item.ok)
    blocked = len(transaction.verification.failures)
    target_files = ", ".join(transaction.prepared.arena.affected_files) or "none"
    return (
        "LIVE ARCHITECT TRANSACTION\n"
        f"Status        : {status}\n"
        f"Intensity     : {transaction.prepared.intensity}\n"
        f"Target files  : {target_files}\n"
        f"Patches staged: {staged}\n"
        f"Verifier fails: {blocked}\n"
        f"Staging file  : {transaction.staging_path}\n"
        f"Ledger hash   : {transaction.ledger_record.phase_hash}\n"
    )
