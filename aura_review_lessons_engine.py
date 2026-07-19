"""Repository-bound review lesson engine with bounded persistence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
from pathlib import Path
from typing import Any

from aura_review_lessons_contracts import (
    _MAX_FINDINGS_FILE_BYTES,
    _MAX_PERSISTED_FINDINGS,
    _MAX_STORED_FINDING_BYTES,
    DEFAULT_LEARNING_ROOT,
    DEFAULT_REGISTRY_PATH,
    PATCH_AUTHORITY,
    REVIEW_LESSON_VERSION,
    VSA_PATCH_AUTHORITY,
    ReviewLessonError,
    _canonical_json,
    _digest,
    _git_head,
    _safe_repo_path,
)
from aura_review_lessons_external import normalize_external_review
from aura_review_lessons_registry import DETECTORS, load_review_lesson_registry
from aura_review_lessons_replay import run_crucible_replay, run_review_detector
from aura_review_lessons_source_scan import scan_source_for_review_lessons


class ReviewLessonEngine:
    """Repository-bound typed lesson and external-review adapter."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        registry_path: str | Path = DEFAULT_REGISTRY_PATH,
        learning_root: str | Path = DEFAULT_LEARNING_ROOT,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.registry_path = Path(registry_path)
        if not self.registry_path.is_absolute():
            self.registry_path = self.repo_root / self.registry_path
        self.learning_root = Path(learning_root).expanduser().resolve()
        self.findings_path = self.learning_root / "external_review_findings.jsonl"

    def summary(self) -> dict[str, Any]:
        registry = load_review_lesson_registry(self.registry_path)
        stored = 0
        stored_bytes = 0
        if self.findings_path.exists():
            stored_bytes = self.findings_path.stat().st_size
            if stored_bytes > _MAX_FINDINGS_FILE_BYTES:
                raise ReviewLessonError("external review findings file exceeds byte limit")
            with self.findings_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        stored += 1
                        if stored > _MAX_PERSISTED_FINDINGS:
                            raise ReviewLessonError("external review findings file exceeds count limit")
        return {
            "version": REVIEW_LESSON_VERSION,
            "registry_path": str(self.registry_path),
            "registry_digest": registry["registry_digest"],
            "lesson_count": len(registry["lessons"]),
            "scenario_count": len(registry["scenarios"]),
            "detectors": sorted(DETECTORS),
            "stored_external_finding_count": stored,
            "stored_external_finding_bytes": stored_bytes,
            "max_persisted_external_findings": _MAX_PERSISTED_FINDINGS,
            "max_persisted_external_finding_bytes": _MAX_FINDINGS_FILE_BYTES,
            "truth_boundary": "review_learning_only",
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def normalize_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        observed_head = _git_head(self.repo_root)
        if (
            current_head
            and observed_head != "UNAVAILABLE"
            and current_head != observed_head
        ):
            raise ReviewLessonError("current_head does not match the repository HEAD")
        head = observed_head if observed_head != "UNAVAILABLE" else current_head
        return normalize_external_review(payload, current_head=head)

    def ingest_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        packet = self.normalize_review(payload, current_head=current_head)
        known: set[str] = set()
        existing_count = 0
        existing_bytes = 0
        if self.findings_path.exists():
            existing_bytes = self.findings_path.stat().st_size
            if existing_bytes > _MAX_FINDINGS_FILE_BYTES:
                raise ReviewLessonError("external review findings file exceeds byte limit")
            with self.findings_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    existing_count += 1
                    if existing_count > _MAX_PERSISTED_FINDINGS:
                        raise ReviewLessonError("external review findings file exceeds count limit")
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    finding_id = str(row.get("finding_id") or "")
                    if finding_id:
                        known.add(finding_id)

        stored: list[str] = []
        rejected: list[dict[str, str]] = []
        pending: list[bytes] = []
        count = existing_count
        total_bytes = existing_bytes
        for finding in packet["findings"]:
            finding_id = str(finding.get("finding_id") or "")
            if finding_id in known or finding.get("disposition") == "duplicate":
                rejected.append({"finding_id": finding_id, "reason": "duplicate"})
                continue
            encoded = (_canonical_json(finding) + "\n").encode("utf-8")
            if len(encoded) > _MAX_STORED_FINDING_BYTES:
                rejected.append({"finding_id": finding_id, "reason": "finding_byte_limit"})
                continue
            if count >= _MAX_PERSISTED_FINDINGS:
                rejected.append({"finding_id": finding_id, "reason": "storage_count_limit"})
                continue
            if total_bytes + len(encoded) > _MAX_FINDINGS_FILE_BYTES:
                rejected.append({"finding_id": finding_id, "reason": "storage_byte_limit"})
                continue
            pending.append(encoded)
            known.add(finding_id)
            stored.append(finding_id)
            count += 1
            total_bytes += len(encoded)

        if pending:
            self.findings_path.parent.mkdir(parents=True, exist_ok=True)
            with self.findings_path.open("ab") as handle:
                for encoded in pending:
                    handle.write(encoded)
        return {
            **packet,
            "status": "stored" if stored else "no_new_findings",
            "stored_count": len(stored),
            "stored_finding_ids": stored,
            "persisted_finding_count": count,
            "persisted_finding_bytes": total_bytes,
            "rejected": rejected,
        }


    def scan_source(self, *, file: str, source: str) -> dict[str, Any]:
        canonical_file = _safe_repo_path(file)
        if not canonical_file:
            raise ReviewLessonError("source scan file is required")
        findings = scan_source_for_review_lessons(file=canonical_file, source=source)
        packet = {
            "version": REVIEW_LESSON_VERSION,
            "file": canonical_file,
            "finding_count": len(findings),
            "findings": findings,
            "truth_boundary": "probable_static_review_lesson",
            "production_mutation": False,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        packet["packet_digest"] = _digest(packet, size=16)
        return packet

    def detector(self, detector_id: str, candidate: Any) -> dict[str, Any]:
        return run_review_detector(detector_id, candidate)

    def crucible(self, *, detector_ids: Sequence[str] = ()) -> dict[str, Any]:
        return run_crucible_replay(self.registry_path, detector_ids=detector_ids)

__all__ = ["ReviewLessonEngine"]
