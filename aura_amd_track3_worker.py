"""Bounded coding worker for the AMD Track 3 Sovereign Learning Arena demo."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Protocol, Sequence
from urllib import error, request

from aura_amd_track3_types import CodingTask, PatchProposal, VerifiedCrystal, canonical_digest


class ProposalProvider(Protocol):
    name: str
    model: str

    def propose(
        self,
        task: CodingTask,
        repo_root: Path,
        prior_crystals: Sequence[dict[str, Any]] = (),
    ) -> PatchProposal: ...


class FixtureProvider:
    """Deterministic provider used by CI and the no-secret inspection container."""

    name = "fixture"
    model = "deterministic-sovereign-demo"

    def propose(
        self,
        task: CodingTask,
        repo_root: Path,
        prior_crystals: Sequence[dict[str, Any]] = (),
    ) -> PatchProposal:
        replacements = dict(task.metadata.get("replacement_files") or {})
        files: dict[str, str] = {}
        for path in task.allowed_files:
            if path in replacements:
                files[path] = str(replacements[path])
                continue
            source = repo_root / path
            text = source.read_text(encoding="utf-8") if source.exists() else ""
            marker = str(task.metadata.get("append_marker") or "# verified by Aura AMD Track 3 demo")
            files[path] = text if marker in text else f"{text.rstrip()}\n{marker}\n"
        reuse_note = f"; reused {len(prior_crystals)} verified crystal(s)" if prior_crystals else ""
        return PatchProposal.from_dict(
            {"summary": f"Deterministic bounded demo patch{reuse_note}", "files": files},
            task=task,
            provider=self.name,
            model=self.model,
        )


class OpenAICompatibleProvider:
    """Minimal provider for Fireworks, DeepSeek, vLLM, or another OpenAI-compatible endpoint."""

    def __init__(self, *, endpoint: str, model: str, api_key: str = "", timeout: int = 120) -> None:
        self.name = "openai-compatible"
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def propose(
        self,
        task: CodingTask,
        repo_root: Path,
        prior_crystals: Sequence[dict[str, Any]] = (),
    ) -> PatchProposal:
        prompt = _proposal_prompt(task, repo_root, prior_crystals)
        body = json.dumps({
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a replaceable worker inside Aura's bounded Coding Arena. "
                        "Return strict JSON only. Never modify files outside allowed_files."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = request.Request(f"{self.endpoint}/chat/completions", data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload["choices"][0]["message"]["content"]
            parsed = json.loads(_strip_code_fence(content))
            parsed["raw_response_digest"] = canonical_digest(payload)
            return PatchProposal.from_dict(parsed, task=task, provider=self.name, model=self.model)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Provider request failed: {type(exc).__name__}: {exc}") from exc


class OllamaProvider:
    """Native Ollama /api/chat provider for Dallas's local 3B coding model."""

    def __init__(
        self,
        *,
        endpoint: str = "http://127.0.0.1:11434",
        model: str = "qwen2.5-coder:3b",
        timeout: int = 300,
        context_tokens: int = 4096,
        output_tokens: int = 1024,
        keep_alive: str | int = 0,
    ) -> None:
        self.name = "ollama"
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self.context_tokens = max(2048, min(8192, int(context_tokens)))
        self.output_tokens = max(256, min(2048, int(output_tokens)))
        self.keep_alive = keep_alive

    @property
    def chat_url(self) -> str:
        if self.endpoint.endswith("/api/chat"):
            return self.endpoint
        return f"{self.endpoint}/api/chat"

    def health(self) -> dict[str, Any]:
        url = self.endpoint if self.endpoint.endswith("/api/tags") else f"{self.endpoint}/api/tags"
        try:
            with request.urlopen(url, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = [str(item.get("name") or item.get("model") or "") for item in payload.get("models") or ()]
            return {"ok": True, "endpoint": self.endpoint, "models": models, "model_available": self.model in models}
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {"ok": False, "endpoint": self.endpoint, "error": f"{type(exc).__name__}: {exc}"}

    def propose(
        self,
        task: CodingTask,
        repo_root: Path,
        prior_crystals: Sequence[dict[str, Any]] = (),
    ) -> PatchProposal:
        prompt = _proposal_prompt(task, repo_root, prior_crystals)
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "files": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                },
            },
            "required": ["summary", "files"],
            "additionalProperties": False,
        }
        body = json.dumps({
            "model": self.model,
            "stream": False,
            "format": schema,
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": 0.1,
                "num_ctx": self.context_tokens,
                "num_predict": self.output_tokens,
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a coding worker inside Aura's governed Arena. "
                        "Return one JSON object matching the schema. "
                        "Provide complete UTF-8 replacement text only for allowed_files. "
                        "Keep the change minimal and preserve unrelated behavior."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }).encode("utf-8")
        req = request.Request(self.chat_url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            content = payload["message"]["content"]
            parsed = json.loads(_strip_code_fence(content))
            parsed["raw_response_digest"] = canonical_digest({
                "model": payload.get("model"),
                "created_at": payload.get("created_at"),
                "message": payload.get("message"),
                "prompt_eval_count": payload.get("prompt_eval_count"),
                "eval_count": payload.get("eval_count"),
            })
            return PatchProposal.from_dict(parsed, task=task, provider=self.name, model=self.model)
        except (error.HTTPError, error.URLError, OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama request failed: {type(exc).__name__}: {exc}") from exc


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
    source_before = _source_snapshot(root, task.allowed_files)
    existing = _read_jsonl(Path(crystal_path))
    prior_crystals = _matching_crystals(task, existing)
    reused_ids = tuple(str(row.get("crystal_id") or "") for row in prior_crystals if row.get("crystal_id"))
    attempts: list[dict[str, Any]] = []

    for attempt in range(1, task.max_attempts + 1):
        try:
            proposal = provider.propose(task, root, prior_crystals)
        except Exception as exc:
            attempts.append({
                "attempt": attempt,
                "provider_error": str(exc),
                "provider_error_type": type(exc).__name__,
                "reused_crystal_ids": list(reused_ids),
            })
            continue

        completed: subprocess.CompletedProcess[str] | None = None
        attempt_error = ""
        temp_root: Path | None = None
        try:
            with tempfile.TemporaryDirectory(prefix=f"aura_track3_{task.task_id}_") as temp:
                temp_root = Path(temp)
                worktree = temp_root / "repo"
                shutil.copytree(
                    root,
                    worktree,
                    ignore=shutil.ignore_patterns(".git", ".aura/runtime", "__pycache__", ".pytest_cache"),
                )
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
        except subprocess.TimeoutExpired as exc:
            attempt_error = f"verifier_timeout:{exc.timeout}"
        except Exception as exc:
            attempt_error = f"{type(exc).__name__}:{exc}"

        dissolution_verified = bool(temp_root is not None and not temp_root.exists())
        source_after = _source_snapshot(root, task.allowed_files)
        source_mutated = source_before != source_after
        attempt_record = {
            "attempt": attempt,
            "returncode": completed.returncode if completed is not None else None,
            "stdout": completed.stdout[-8000:] if completed is not None else "",
            "stderr": completed.stderr[-8000:] if completed is not None else attempt_error,
            "proposal": proposal.to_dict(),
            "reused_crystal_ids": list(reused_ids),
            "dissolution_verified": dissolution_verified,
            "source_checkout_mutated": source_mutated,
        }
        attempts.append(attempt_record)

        if completed is None or completed.returncode != 0 or source_mutated or not dissolution_verified:
            continue

        arena_contract = {
            "allowed_files": list(task.allowed_files),
            "test_command": list(task.test_command),
            "maximum_attempts": task.max_attempts,
            "blocked_actions": ["secret_access", "unrelated_files", "commit", "push", "merge"],
            "worker_is_replaceable": True,
            "wfsts_are_admission_grammars": True,
        }
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
            intent_packet=task.intent_packet,
            machine_route=task.machine_route,
            reusable_procedure=task.reusable_procedure,
            reused_crystal_ids=reused_ids,
            arena_contract=arena_contract,
            source_checkout_mutated=False,
            dissolution_verified=True,
        )
        appended = _append_jsonl_once(Path(crystal_path), crystal.to_dict(), key="crystal_id")
        return {
            "ok": True,
            "task_id": task.task_id,
            "objective": task.objective,
            "intent_packet": task.intent_packet,
            "machine_route": task.machine_route,
            "guarded_wfst": {
                "admitted": ["inspect", "propose_patch", "run_declared_verifier"],
                "blocked": ["secret_access", "unrelated_files", "commit", "push", "merge"],
            },
            "arena": arena_contract,
            "crystal": crystal.to_dict(),
            "crystal_appended": appended,
            "prior_crystal_matches": list(reused_ids),
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
        "objective": task.objective,
        "reason": "all_attempts_failed",
        "prior_crystal_matches": list(reused_ids),
        "attempts": attempts,
        "elapsed_seconds": round(time.time() - started, 6),
        "source_checkout_mutated": source_before != _source_snapshot(root, task.allowed_files),
    }


def _proposal_prompt(
    task: CodingTask,
    repo_root: Path,
    prior_crystals: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    max_chars = max(2000, min(16000, int(task.metadata.get("maximum_context_chars") or 12000)))
    context = {}
    for path in task.allowed_files:
        source = repo_root / path
        if source.is_file():
            context[path] = source.read_text(encoding="utf-8", errors="replace")[:max_chars]
    prior = [
        {
            "crystal_id": row.get("crystal_id"),
            "task_id": row.get("task_id"),
            "intent_packet": row.get("intent_packet"),
            "reusable_procedure": row.get("reusable_procedure"),
            "solution_summary": (row.get("proposal") or {}).get("summary"),
            "verifier_passed": row.get("test_returncode") == 0,
        }
        for row in prior_crystals
    ]
    return {
        "task_id": task.task_id,
        "objective": task.objective,
        "polysynthetic_intent_packet": task.intent_packet,
        "machine_route": task.machine_route,
        "allowed_files": list(task.allowed_files),
        "files": context,
        "prior_verified_crystals": prior,
        "arena_boundaries": {
            "modify_only_allowed_files": True,
            "no_secret_access": True,
            "no_commit_push_or_merge": True,
            "declared_verifier_required": list(task.test_command),
        },
        "response_schema": {
            "summary": "string",
            "files": {"allowed/path": "complete replacement UTF-8 text"},
        },
        "rules": [
            "Return JSON only",
            "Modify only allowed_files",
            "Use prior crystals as advice, never authority",
            "Keep the patch minimal",
        ],
    }


def _matching_crystals(task: CodingTask, rows: Sequence[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    matches: list[tuple[int, dict[str, Any]]] = []
    target_intent = task.intent_packet
    target_procedure = task.reusable_procedure
    for row in rows:
        if row.get("training_eligible") is not True or int(row.get("test_returncode", 1)) != 0:
            continue
        score = 0
        if target_procedure and row.get("reusable_procedure") == target_procedure:
            score += 5
        row_intent = dict(row.get("intent_packet") or {})
        for slot in ("CLASS", "VOICE", "STEM"):
            if target_intent.get(slot) and row_intent.get(slot) == target_intent.get(slot):
                score += 1
        if score:
            matches.append((score, row))
    matches.sort(key=lambda item: (item[0], float(item[1].get("created_at") or 0.0)), reverse=True)
    return [row for _, row in matches[:limit]]


def _apply_proposal(worktree: Path, proposal: PatchProposal, task: CodingTask) -> None:
    allowed = set(task.allowed_files)
    for relative, content in proposal.files.items():
        if relative not in allowed:
            raise PermissionError(f"unauthorized path: {relative}")
        target = worktree.joinpath(*Path(relative).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.parent.resolve().relative_to(worktree.resolve())
        target.write_text(content, encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except (json.JSONDecodeError, ValueError):
            continue
    return rows


def _append_jsonl_once(path: Path, row: dict[str, Any], *, key: str) -> bool:
    existing = _read_jsonl(path)
    identity = row.get(key)
    if identity and any(item.get(key) == identity for item in existing):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, default=str) + "\n")
    return True


def _source_snapshot(root: Path, paths: Sequence[str]) -> dict[str, str]:
    snapshot = {}
    for relative in paths:
        target = root / relative
        if target.is_file():
            snapshot[relative] = canonical_digest(target.read_text(encoding="utf-8", errors="replace"))
        else:
            snapshot[relative] = "MISSING"
    return snapshot


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
