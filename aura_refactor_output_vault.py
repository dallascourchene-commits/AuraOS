"""Local append-only vault for generated refactor plans, code, and evidence.

The vault is intentionally stored beneath an ignored repository-local directory so
full prompts, generated diffs, verifier output, and quality records remain on the
owner's laptop.  Public benchmark summaries can remain redacted while the Human
Agent Arena can list and load these private records for inspection or another
bounded refactor pass.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Mapping, Sequence

OUTPUT_VAULT_VERSION = "AURA_REFACTOR_OUTPUT_VAULT_V1"
DEFAULT_VAULT_ROOT = Path("Aura_Staging") / "refactor_output_vault"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
_SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: Any, *, size: int = 16) -> str:
    text = value if isinstance(value, str) else _canonical(value)
    return hashlib.blake2b(text.encode("utf-8"), digest_size=size).hexdigest()


def _safe_id(value: Any, fallback: str) -> str:
    cleaned = _SAFE_ID.sub("-", str(value or "").strip()).strip("-.")
    return (cleaned or fallback)[:120]


class RefactorOutputVault:
    """Content-addressed local evidence store with a per-run digest chain."""

    def __init__(self, repo_root: str | Path = ".", *, root: str | Path = DEFAULT_VAULT_ROOT) -> None:
        self.repo_root = Path(repo_root).resolve()
        raw_root = Path(root)
        if raw_root.is_absolute() or ".." in raw_root.parts:
            raise ValueError("vault root must be repository-relative")
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
        payload = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": safe_run,
            "objective": str(objective),
            "surface": str(surface),
            "control_profile": dict(control_profile),
            "metadata": dict(metadata or {}),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
            "human_review_required": True,
            "production_mutation": False,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        payload["run_digest"] = _digest(payload)
        run_path = run_dir / "run.json"
        if run_path.exists():
            existing = json.loads(run_path.read_text(encoding="utf-8"))
            if existing.get("run_digest") != payload["run_digest"]:
                raise ValueError("run_id already exists with different metadata")
        else:
            self._write_json(run_path, payload)
            self._append_event(run_dir, "run_started", payload)
        return {**payload, "relative_path": run_path.relative_to(self.repo_root).as_posix()}

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
                candidate.get("candidate_id") or candidate.get("plan_id"), f"candidate-{index}"
            )
            plan = dict(candidate.get("plan") or candidate)
            record = {
                "version": OUTPUT_VAULT_VERSION,
                "run_id": _safe_id(run_id, "run"),
                "objective": str(objective),
                "candidate_id": candidate_id,
                "arm_family": str(candidate.get("arm_family") or candidate.get("method") or "UNKNOWN"),
                "provenance": dict(candidate.get("provenance") or {}),
                "token_usage": dict(candidate.get("token_usage") or {}),
                "prompt_digest": str(candidate.get("prompt_digest") or ""),
                "response_digest": str(candidate.get("response_digest") or _digest(plan)),
                "plan_digest": _digest(plan),
                "plan": plan,
                "assessment": assessments.get(candidate_id, {}),
                "selected": candidate_id == str(comparison.get("selected_candidate_id") or ""),
                "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            path = candidate_dir / f"{index:02d}-{candidate_id}.json"
            self._write_json(path, record)
            self._append_event(run_dir, "plan_candidate_recorded", {
                "candidate_id": candidate_id,
                "plan_digest": record["plan_digest"],
                "assessment": record["assessment"],
                "selected": record["selected"],
                "artifact": path.relative_to(self.root).as_posix(),
            })
            records.append({**record, "artifact": path.relative_to(self.repo_root).as_posix()})
        selection_path = run_dir / "plan-comparison.json"
        selection = {
            "version": OUTPUT_VAULT_VERSION,
            "objective": str(objective),
            "comparison": dict(comparison),
            "candidate_count": len(records),
            "candidate_digests": {item["candidate_id"]: item["plan_digest"] for item in records},
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        selection["comparison_digest"] = _digest(selection)
        self._write_json(selection_path, selection)
        self._append_event(run_dir, "plan_selection_recorded", {
            "selected_candidate_id": comparison.get("selected_candidate_id"),
            "comparison_digest": selection["comparison_digest"],
            "artifact": selection_path.relative_to(self.root).as_posix(),
        })
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
        prompt_path = turn_dir / "prompt.txt"
        response_path = turn_dir / ("generated.patch" if self._looks_like_diff(response) else "generated.txt")
        result_path = turn_dir / "result.json"
        prompt_path.write_text(str(prompt), encoding="utf-8")
        response_path.write_text(str(response), encoding="utf-8")
        evidence = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": _safe_id(run_id, "run"),
            "turn_id": turn_name,
            "task_id": str(task_id),
            "role": str(role),
            "prompt_digest": _digest(prompt),
            "response_digest": _digest(response),
            "prompt_bytes": len(str(prompt).encode("utf-8")),
            "response_bytes": len(str(response).encode("utf-8")),
            "provider_usage": dict(provider_usage or {}),
            "result": dict(result),
            "artifacts": {
                "prompt": prompt_path.relative_to(self.repo_root).as_posix(),
                "generated_output": response_path.relative_to(self.repo_root).as_posix(),
                "result": result_path.relative_to(self.repo_root).as_posix(),
            },
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
        }
        evidence["evidence_digest"] = _digest(evidence)
        self._write_json(result_path, evidence)
        event = self._append_event(run_dir, "generated_output_recorded", {
            "turn_id": turn_name,
            "task_id": str(task_id),
            "role": str(role),
            "response_digest": evidence["response_digest"],
            "evidence_digest": evidence["evidence_digest"],
            "artifact": result_path.relative_to(self.root).as_posix(),
        })
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
        patch_path = run_dir / "implemented-branch.patch"
        patch_path.write_text(str(patch), encoding="utf-8")
        record = {
            "version": OUTPUT_VAULT_VERSION,
            "run_id": _safe_id(run_id, "run"),
            "base_sha": str(base_sha),
            "head_sha": str(head_sha),
            "changed_files": [str(item) for item in changed_files],
            "patch_digest": _digest(patch),
            "patch_bytes": len(str(patch).encode("utf-8")),
            "quality_record": dict(quality_record or {}),
            "patch_artifact": patch_path.relative_to(self.repo_root).as_posix(),
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        record["record_digest"] = _digest(record)
        record_path = run_dir / "implemented-branch.json"
        self._write_json(record_path, record)
        event = self._append_event(run_dir, "branch_patch_recorded", {
            "base_sha": base_sha,
            "head_sha": head_sha,
            "patch_digest": record["patch_digest"],
            "record_digest": record["record_digest"],
            "artifact": record_path.relative_to(self.root).as_posix(),
        })
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
            rows.append({
                "run_id": metadata.get("run_id", run_path.name),
                "objective": metadata.get("objective", ""),
                "surface": metadata.get("surface", ""),
                "created_at": metadata.get("created_at", ""),
                "run_digest": metadata.get("run_digest", ""),
                "manifest_bytes": manifest.stat().st_size if manifest.is_file() else 0,
                "relative_path": run_path.relative_to(self.repo_root).as_posix(),
            })
        rows.sort(key=lambda item: (str(item.get("created_at")), str(item.get("run_id"))), reverse=True)
        return {"ok": True, "root": self._relative_root(), "runs": rows[:bounded]}

    def load_artifact(self, relative_path: str, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
        raw = Path(str(relative_path or "").strip())
        if not raw.parts or raw.is_absolute() or ".." in raw.parts:
            raise ValueError("artifact path must be a relative vault path")
        root_prefix = Path(self._relative_root())
        if raw.parts[: len(root_prefix.parts)] == root_prefix.parts:
            raw = Path(*raw.parts[len(root_prefix.parts):])
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
            "visibility": "LOCAL_PRIVATE_FULL_OUTPUT",
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
                last = json.loads(lines[-1])
                previous = str(last.get("event_digest") or "")
                sequence = int(last.get("sequence") or 0) + 1
        event = {
            "version": OUTPUT_VAULT_VERSION,
            "sequence": sequence,
            "event_type": str(event_type),
            "previous_event_digest": previous,
            "payload": dict(payload),
            "recorded_at_ns": time.time_ns(),
        }
        event["event_digest"] = _digest(event)
        with manifest.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        return event

    @staticmethod
    def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(dict(payload), indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    @staticmethod
    def _looks_like_diff(value: str) -> bool:
        text = str(value or "").lstrip()
        return text.startswith(("diff --git ", "--- ", "*** Begin Patch"))

    def _relative_root(self) -> str:
        return self.root.relative_to(self.repo_root).as_posix()


__all__ = ["DEFAULT_VAULT_ROOT", "OUTPUT_VAULT_VERSION", "RefactorOutputVault"]
