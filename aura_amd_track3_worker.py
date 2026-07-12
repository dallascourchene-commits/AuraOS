"""Bounded coding worker that converts verified tasks into reusable crystals."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Protocol
from urllib import request

from aura_amd_track3_types import CodingTask, PatchProposal, VerifiedCrystal, canonical_digest


class ProposalProvider(Protocol):
    name: str
    model: str

    def propose(self, task: CodingTask, repo_root: Path) -> PatchProposal: ...


class FixtureProvider:
    """Deterministic provider used by CI and the public demo container."""

    name = "fixture"
    model = "deterministic-demo"

    def propose(self, task: CodingTask, repo_root: Path) -> PatchProposal:
        files: dict[str, str] = {}
        for path in task.allowed_files:
            source = repo_root / path
            text = source.read_text(encoding="utf-8") if source.exists() else ""
            marker = str(task.metadata.get("append_marker") or "# verified by Aura AMD Track 3 demo")
            files[path] = text if marker in text else f"{text.rstrip()}\n{marker}\n"
        return PatchProposal.from_dict(
            {"summary": "Deterministic bounded demo patch", "files": files},
            task=task,
            provider=self.name,
            model=self.model,
        )


class OpenAICompatibleProvider:
    """Minimal provider for Fireworks, vLLM, or another OpenAI-compatible AMD endpoint."""

    def __init__(self, *, endpoint: str, model: str, api_key: str = "", timeout: int = 120) -> None:
        self.name = "openai-compatible"
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def propose(self, task: CodingTask, repo_root: Path) -> PatchProposal:
        context = {
            path: (repo_root / path).read_text(encoding="utf-8", errors="replace")
            for path in task.allowed_files
            if (repo_root / path).is_file()
        }
        prompt = {
            "task_id": task.task_id,
            "objective": task.objective,
            "allowed_files": list(task.allowed_files),
            "files": context,
            "response_schema": {"summary": "string", "files": {"path": "complete replacement UTF-8 text"}},
            "rules": ["Return JSON only", "Modify only allowed_files", "Keep the patch minimal"],
        }
        body = json.dumps({
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": "You are Aura's bounded coding worker. Return strict JSON only."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(f"{self.endpoint}/chat/completions", data=body, headers=headers, method="POST")
        with request.urlopen(req, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        content = payload["choices"][0]["message"]["content"]
        parsed = json.loads(_strip_code_fence(content))
        parsed["raw_response_digest"] = canonical_digest(payload)
        return PatchProposal.from_dict(parsed, task=task, provider=self.name, model=self.model)


def load_tasks(path: str | Path) -> list[CodingTask]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    tasks = [CodingTask.from_dict(item) for item in raw.get("tasks") or ()]
    ids = [task.task_id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("task IDs must be unique")
    return tasks


def run_task(
    *,
    task: CodingTask,
    provider: ProposalProvider,
    repo_root: str | Path,
    crystal_path: str | Path,
    amd_backend: str = "unknown",
) -> dict[str, Any]:
    """Run one task in a detached copy and persist only a fully verified crystal."""
    root = Path(repo_root).resolve()
    started = time.time()
    source_commit = _git_output(root, ["rev-parse", "HEAD"]) or "unversioned"
    attempts: list[dict[str, Any]] = []
    for attempt in range(1, task.max_attempts + 1):
        proposal = provider.propose(task, root)
        with tempfile.TemporaryDirectory(prefix=f"aura_track3_{task.task_id}_") as temp:
            worktree = Path(temp) / "repo"
            shutil.copytree(root, worktree, ignore=shutil.ignore_patterns(".git", ".aura/runtime", "__pycache__", ".pytest_cache"))
            _apply_proposal(worktree, proposal, task)
            completed = subprocess.run(
                list(task.test_command),
                cwd=worktree,
                text=True,
                capture_output=True,
                timeout=max(10, int(task.metadata.get("timeout_seconds") or 120)),
                env={**os.environ, "PYTHONPATH": str(worktree)},
                check=False,
            )
            attempt_record = {
                "attempt": attempt,
                "returncode": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-8000:],
                "proposal": proposal.to_dict(),
            }
            attempts.append(attempt_record)
            if completed.returncode == 0:
                crystal = VerifiedCrystal(
                    crystal_id=f"CRYSTAL-{canonical_digest([task.digest(), proposal.to_dict(), source_commit])[:24]}",
                    task_id=task.task_id,
                    task_digest=task.digest(),
                    proposal=proposal.to_dict(),
                    test_command=task.test_command,
                    test_returncode=completed.returncode,
                    test_stdout=completed.stdout[-8000:],
                    test_stderr=completed.stderr[-8000:],
                    source_commit=source_commit,
                    created_at=time.time(),
                    amd_backend=amd_backend,
                )
                _append_jsonl(Path(crystal_path), crystal.to_dict())
                return {
                    "ok": True,
                    "task_id": task.task_id,
                    "crystal": crystal.to_dict(),
                    "attempts": attempts,
                    "elapsed_seconds": round(time.time() - started, 6),
                    "source_checkout_mutated": False,
                    "automatic_commit": False,
                    "automatic_push": False,
                    "automatic_merge": False,
                }
    return {
        "ok": False,
        "task_id": task.task_id,
        "reason": "all_attempts_failed",
        "attempts": attempts,
        "elapsed_seconds": round(time.time() - started, 6),
        "source_checkout_mutated": False,
    }


def _apply_proposal(worktree: Path, proposal: PatchProposal, task: CodingTask) -> None:
    allowed = set(task.allowed_files)
    for relative, content in proposal.files.items():
        if relative not in allowed:
            raise PermissionError(f"unauthorized path: {relative}")
        target = worktree.joinpath(*Path(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        resolved_parent = target.parent.resolve()
        resolved_parent.relative_to(worktree.resolve())
        target.write_text(content, encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def _git_output(root: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=15, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _strip_code_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:-1] if len(lines) >= 2 else lines
        return "\n".join(lines).strip()
    return text
