"""Local append-only vault for generated refactor plans, code, and evidence.

The vault lives beneath ignored ``Aura_Staging`` storage so full benchmark and
Surgeon evidence remains on the owner's laptop. Public records stay redacted;
the Human Agent Arena can list or load bounded local artifacts. Secret-like text
is removed before persistence while original content digests remain available
for identity and reproducibility checks.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any, Mapping, Sequence

OUTPUT_VAULT_VERSION = "AURA_REFACTOR_OUTPUT_VAULT_V1"
DEFAULT_VAULT_ROOT = Path("Aura_Staging") / "refactor_output_vault"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")
_SECRET_KEYS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "access_token",
    "refresh_token",
    "private_key",
    "authorization",
)
_SECRET_PATTERNS = (
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,})\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(
        r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret)"
        r"(\s*[:=]\s*)(['\"]?)[^\s,'\"}]+\3"
    ),
)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    text = value if isinstance(value, str) else _canonical(value)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=size).hexdigest()


def _safe_id(value: Any, fallback: str) -> str:
    cleaned = _SAFE_ID.sub("-", str(value or "").strip()).strip("-.")
    return (cleaned or fallback)[:120]


def _redact_text(value: Any) -> tuple[str, bool]:
    text = str(value or "")
    changed = False
    for pattern in _SECRET_PATTERNS:
        if pattern.pattern.startswith("(?i)(api"):
            text, count = pattern.subn(r"\1\2\3[REDACTED]\3", text)
        else:
            text, count = pattern.subn("[REDACTED_SECRET]", text)
        changed = changed or count > 0
    return text, changed


def _redact_structured(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if any(secret in normalized for secret in _SECRET_KEYS):
                result[str(key)] = {
                    "redacted": True,
                    "value_digest": _digest(item),
                }
            else:
                result[str(key)] = _redact_structured(item)
        return result
    if isinstance(value, list):
        return [_redact_structured(item) for item in value]
    if isinstance(value, tuple):
        return [_redact_structured(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)[0]
    return value


def _normalize_root(root: str | Path) -> Path:
    raw = str(root).replace("\\", "/").strip().strip("/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        raise ValueError("vault root must be a repository-relative Aura_Staging path")
    if not path.parts or path.parts[0] != "Aura_Staging":
        raise ValueError("vault root must be beneath Aura_Staging")
    return Path(*path.parts)


class RefactorOutputVault:
    """Content-addressed local evidence store with a per-run digest chain."""

    def __init__(self, repo_root: str | Path = ".", *, root: str | Path = DEFAULT_VAULT_ROOT) -> None:
        self.repo_root = Path(repo_root).resolve()
        raw_root = _normalize_root(root)
        self.root = (self.repo_root / raw_root).resolve()
        try:
            self.root.relative_to(self.repo_root)
        except ValueError as exc:
            raise ValueError("vault root escapes repository") from exc

    def start_run(
        self,
        *,
        run_id: str,
        objective: str,
        surface: str,
        control_profile: Mapping[str, Any],
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        safe_run = _safe_id(run_id, f"RUN-{time.time_ns()}")
        run_dir = self.root / safe_run
        run_dir.mkdir(parents=True, exist_ok=True)
        identity = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": safe_run,
            "objective": str(objective),
            "surface": str(surface),
            "control_profile": _redact_structured(dict(control_profile)),
            "metadata": _redact_structured(dict(metadata or {})),
            "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
            "human_review_required": True,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        identity_digest = _digest(identity)
        run_path = run_dir / "run.json"
        if run_path.exists():
            existing = json.loads(run_path.read_text(encoding="utf-8"))
            if existing.get("identity_digest") != identity_digest:
                raise ValueError("run_id already exists with different immutable metadata")
            return {
                **existing,
                "relative_path": run_path.relative_to(self.repo_root).as_posix(),
                "reused": True,
            }
        payload = {
            **identity,
            "identity_digest": identity_digest,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        payload["run_digest"] = _digest(payload)
        self._write_json(run_path, payload)
        self._append_event(run_dir, "run_started", payload)
        return {
            **payload,
            "relative_path": run_path.relative_to(self.repo_root).as_posix(),
            "reused": False,
        }

    def record_plan_candidates(
        self,
        *,
        run_id: str,
        objective: str,
        candidates: Sequence[Mapping[str, Any]],
        comparison: Mapping[str, Any],
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        candidate_dir = run_dir / "plans"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        records: list[dict[str, Any]] = []
        assessments = {
            str(item.get("candidate_id")): dict(item)
            for item in list(comparison.get("assessments") or [])
            if isinstance(item, Mapping)
        }
        for index, candidate in enumerate(candidates, start=1):
            candidate_id = _safe_id(
                candidate.get("candidate_id") or candidate.get("plan_id"),
                f"candidate-{index}",
            )
            plan = dict(candidate.get("plan") or candidate)
            record = {
                "version": OUTPUT_VAULT_VERSION,
                "run_id": _safe_id(run_id, "run"),
                "objective": str(objective),
                "candidate_id": candidate_id,
                "arm_family": str(candidate.get("arm_family") or candidate.get("method") or "UNKNOWN"),
                "provenance": _redact_structured(dict(candidate.get("provenance") or {})),
                "token_usage": _redact_structured(dict(candidate.get("token_usage") or {})),
                "prompt_digest": str(candidate.get("prompt_digest") or ""),
                "response_digest": str(candidate.get("response_digest") or _digest(plan)),
                "plan_digest": _digest(plan),
                "plan": _redact_structured(plan),
                "assessment": assessments.get(candidate_id, {}),
                "selected": candidate_id == str(comparison.get("selected_candidate_id") or ""),
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            path = candidate_dir / f"{index:02d}-{candidate_id}.json"
            self._write_json(path, record)
            self._append_event(
                run_dir,
                "plan_candidate_recorded",
                {
                    "candidate_id": candidate_id,
                    "plan_digest": record["plan_digest"],
                    "assessment": record["assessment"],
                    "selected": record["selected"],
                    "artifact": path.relative_to(self.root).as_posix(),
                },
            )
            records.append({**record, "artifact": path.relative_to(self.repo_root).as_posix()})
        selection_path = run_dir / "plan-comparison.json"
        selection = {
            "version": OUTPUT_VAULT_VERSION,
            "objective": str(objective),
            "comparison": _redact_structured(dict(comparison)),
            "candidate_count": len(records),
            "candidate_digests": {item["candidate_id"]: item["plan_digest"] for item in records},
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        selection["comparison_digest"] = _digest(selection)
        self._write_json(selection_path, selection)
        self._append_event(
            run_dir,
            "plan_selection_recorded",
            {
                "selected_candidate_id": comparison.get("selected_candidate_id"),
                "comparison_digest": selection["comparison_digest"],
                "artifact": selection_path.relative_to(self.root).as_posix(),
            },
        )
        return {
            "ok": True,
            "run_id": _safe_id(run_id, "run"),
            "candidate_records": records,
            "selection_artifact": selection_path.relative_to(self.repo_root).as_posix(),
            "comparison_digest": selection["comparison_digest"],
        }

    def record_generated_output(
        self,
        *,
        run_id: str,
        turn_id: str,
        task_id: str,
        role: str,
        prompt: str,
        response: str,
        result: Mapping[str, Any],
        provider_usage: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        turn_name = _safe_id(turn_id, f"turn-{time.time_ns()}")
        turn_dir = run_dir / "turns" / turn_name
        turn_dir.mkdir(parents=True, exist_ok=True)
        original_prompt = str(prompt)
        original_response = str(response)
        safe_prompt, prompt_redacted = _redact_text(original_prompt)
        safe_response, response_redacted = _redact_text(original_response)
        prompt_path = turn_dir / "prompt.txt"
        response_path = turn_dir / (
            "generated.patch" if self._looks_like_diff(safe_response) else "generated.txt"
        )
        result_path = turn_dir / "result.json"
        prompt_path.write_text(safe_prompt, encoding="utf-8")
        response_path.write_text(safe_response, encoding="utf-8")
        evidence = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": _safe_id(run_id, "run"),
            "turn_id": turn_name,
            "task_id": str(task_id),
            "role": str(role),
            "prompt_digest": _digest(original_prompt),
            "response_digest": _digest(original_response),
            "stored_prompt_digest": _digest(safe_prompt),
            "stored_response_digest": _digest(safe_response),
            "prompt_bytes": len(original_prompt.encode("utf-8")),
            "response_bytes": len(original_response.encode("utf-8")),
            "redaction_applied": prompt_redacted or response_redacted,
            "provider_usage": _redact_structured(dict(provider_usage or {})),
            "result": _redact_structured(dict(result)),
            "artifacts": {
                "prompt": prompt_path.relative_to(self.repo_root).as_posix(),
                "generated_output": response_path.relative_to(self.repo_root).as_posix(),
                "result": result_path.relative_to(self.repo_root).as_posix(),
            },
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
        }
        evidence["evidence_digest"] = _digest(evidence)
        self._write_json(result_path, evidence)
        event = self._append_event(
            run_dir,
            "generated_output_recorded",
            {
                "turn_id": turn_name,
                "task_id": str(task_id),
                "role": str(role),
                "response_digest": evidence["response_digest"],
                "evidence_digest": evidence["evidence_digest"],
                "artifact": result_path.relative_to(self.root).as_posix(),
            },
        )
        return {"ok": True, **evidence, "history_event_digest": event["event_digest"]}

    def record_branch_patch(
        self,
        *,
        run_id: str,
        base_sha: str,
        head_sha: str,
        patch: str,
        changed_files: Sequence[str],
        quality_record: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_dir = self._run_dir(run_id)
        original_patch = str(patch)
        safe_patch, redaction_applied = _redact_text(original_patch)
        patch_path = run_dir / "implemented-branch.patch"
        patch_path.write_text(safe_patch, encoding="utf-8")
        record = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": _safe_id(run_id, "run"),
            "base_sha": str(base_sha),
            "head_sha": str(head_sha),
            "changed_files": [str(item) for item in changed_files],
            "patch_digest": _digest(original_patch),
            "stored_patch_digest": _digest(safe_patch),
            "patch_bytes": len(original_patch.encode("utf-8")),
            "redaction_applied": redaction_applied,
            "quality_record": _redact_structured(dict(quality_record or {})),
            "patch_artifact": patch_path.relative_to(self.repo_root).as_posix(),
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        record["record_digest"] = _digest(record)
        record_path = run_dir / "implemented-branch.json"
        self._write_json(record_path, record)
        event = self._append_event(
            run_dir,
            "branch_patch_recorded",
            {
                "base_sha": base_sha,
                "head_sha": head_sha,
                "patch_digest": record["patch_digest"],
                "record_digest": record["record_digest"],
                "artifact": record_path.relative_to(self.root).as_posix(),
            },
        )
        return {"ok": True, **record, "history_event_digest": event["event_digest"]}

    def list_runs(self, *, limit: int = 50) -> dict[str, Any]:
        bounded = max(1, min(200, int(limit)))
        if not self.root.exists():
            return {"ok": True, "root": self._relative_root(), "runs": []}
        rows: list[dict[str, Any]] = []
        for run_path in self.root.iterdir():
            metadata_path = run_path / "run.json"
            if not run_path.is_dir() or not metadata_path.is_file():
                continue
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            manifest = run_path / "manifest.jsonl"
            rows.append(
                {
                    "run_id": metadata.get("run_id", run_path.name),
                    "objective": metadata.get("objective", ""),
                    "surface": metadata.get("surface", ""),
                    "created_at": metadata.get("created_at", ""),
                    "run_digest": metadata.get("run_digest", ""),
                    "manifest_bytes": manifest.stat().st_size if manifest.is_file() else 0,
                    "relative_path": run_path.relative_to(self.repo_root).as_posix(),
                }
            )
        rows.sort(
            key=lambda item: (str(item.get("created_at")), str(item.get("run_id"))),
            reverse=True,
        )
        return {"ok": True, "root": self._relative_root(), "runs": rows[:bounded]}

    def load_artifact(self, relative_path: str, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
        raw = Path(str(relative_path or "").strip())
        if not raw.parts or raw.is_absolute() or ".." in raw.parts:
            raise ValueError("artifact path must be a relative vault path")
        root_prefix = Path(self._relative_root())
        if raw.parts[: len(root_prefix.parts)] == root_prefix.parts:
            raw = Path(*raw.parts[len(root_prefix.parts) :])
        target = (self.root / raw).resolve()
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("artifact path escapes vault") from exc
        if not target.is_file():
            raise FileNotFoundError(str(relative_path))
        size = target.stat().st_size
        if size > max(1, int(max_bytes)):
            raise ValueError("artifact exceeds load limit")
        text = target.read_text(encoding="utf-8", errors="replace")
        parsed: Any = None
        if target.suffix.lower() in {".json", ".jsonl"}:
            if target.suffix.lower() == ".jsonl":
                parsed = [json.loads(line) for line in text.splitlines() if line.strip()]
            else:
                parsed = json.loads(text)
        return {
            "ok": True,
            "relative_path": target.relative_to(self.repo_root).as_posix(),
            "bytes": size,
            "digest": _digest(text),
            "content": parsed if parsed is not None else text,
            "visibility": "LOCAL_PRIVATE_REDACTED_OUTPUT",
            "production_mutation": False,
        }

    def _run_dir(self, run_id: str) -> Path:
        run_dir = self.root / _safe_id(run_id, "run")
        if not (run_dir / "run.json").is_file():
            raise FileNotFoundError(f"unknown vault run: {run_id}")
        return run_dir

    def _append_event(self, run_dir: Path, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        manifest = run_dir / "manifest.jsonl"
        previous = ""
        sequence = 1
        if manifest.is_file():
            lines = [line for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]
            if lines:
                try:
                    last = json.loads(lines[-1])
                except json.JSONDecodeError as exc:
                    raise ValueError("vault manifest is corrupt") from exc
                previous = str(last.get("event_digest") or "")
                sequence = int(last.get("sequence") or 0) + 1
        event = {
            "version": OUTPUT_VAULT_VERSION,
            "sequence": sequence,
            "event_type": str(event_type),
            "previous_event_digest": previous,
            "payload": _redact_structured(dict(payload)),
            "recorded_at_ns": time.time_ns(),
        }
        event["event_digest"] = _digest(event)
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        return event

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _looks_like_diff(value: str) -> bool:
        text = str(value or "").lstrip()
        return text.startswith(("diff --git ", "--- ", "*** Begin Patch"))

    def _relative_root(self) -> str:
        return self.root.relative_to(self.repo_root).as_posix()


__all__ = ["DEFAULT_VAULT_ROOT", "OUTPUT_VAULT_VERSION", "RefactorOutputVault"]
