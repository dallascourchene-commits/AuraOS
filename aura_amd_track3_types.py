"""Typed contracts for the AMD Track 3 Crucible demo layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

TRACK3_SCHEMA_VERSION = "AURA_AMD_TRACK3_V1"


def canonical_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.blake2b(payload.encode("utf-8"), digest_size=20).hexdigest()


@dataclass(frozen=True)
class CodingTask:
    task_id: str
    objective: str
    allowed_files: tuple[str, ...]
    test_command: tuple[str, ...]
    max_attempts: int = 2
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "CodingTask":
        task_id = str(raw.get("task_id") or "").strip()
        objective = str(raw.get("objective") or "").strip()
        allowed_files = tuple(str(item) for item in raw.get("allowed_files") or () if str(item))
        test_command = tuple(str(item) for item in raw.get("test_command") or () if str(item))
        max_attempts = max(1, min(5, int(raw.get("max_attempts") or 2)))
        if not task_id or not objective or not allowed_files or not test_command:
            raise ValueError("task_id, objective, allowed_files, and test_command are required")
        if any(path.startswith("/") or ".." in path.split("/") for path in allowed_files):
            raise ValueError("allowed_files must be repository-relative and traversal-free")
        return cls(task_id, objective, allowed_files, test_command, max_attempts, dict(raw.get("metadata") or {}))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class PatchProposal:
    task_id: str
    summary: str
    files: dict[str, str]
    provider: str
    model: str
    raw_response_digest: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, task: CodingTask, provider: str, model: str) -> "PatchProposal":
        files = {str(path): str(content) for path, content in dict(raw.get("files") or {}).items()}
        if not files:
            raise ValueError("proposal must contain at least one file")
        unauthorized = sorted(set(files) - set(task.allowed_files))
        if unauthorized:
            raise ValueError(f"proposal contains unauthorized files: {unauthorized}")
        return cls(
            task_id=task.task_id,
            summary=str(raw.get("summary") or "").strip(),
            files=files,
            provider=provider,
            model=model,
            raw_response_digest=str(raw.get("raw_response_digest") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifiedCrystal:
    crystal_id: str
    task_id: str
    task_digest: str
    proposal: dict[str, Any]
    test_command: tuple[str, ...]
    test_returncode: int
    test_stdout: str
    test_stderr: str
    source_commit: str
    created_at: float
    amd_backend: str
    training_eligible: bool = True

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema_version"] = TRACK3_SCHEMA_VERSION
        return payload
