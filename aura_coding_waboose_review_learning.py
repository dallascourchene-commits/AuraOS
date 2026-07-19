"""Repository-native review-learning extension for Coding Waboose.

The retained CodingWaboose remains the review owner. This subclass adds typed
PR-review lessons, conservative source-shape detectors, external-review
normalization, and Crucible replay without changing repair or promotion
authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import tokenize
from typing import Any

from aura_coding_waboose import (
    CODING_WABOOSE_VERSION,
    CodingWaboose,
    CodingWabooseRequest,
)
from aura_coding_waboose_review_lessons import (
    DEFAULT_LEARNING_ROOT,
    DEFAULT_REGISTRY_PATH,
    ReviewLessonEngine,
)

REVIEW_LEARNING_WABOOSE_VERSION = "AURA_CODING_WABOOSE_REVIEW_LEARNING_V1"


class ReviewLearningCodingWaboose(CodingWaboose):
    """Coding Waboose with typed external-review lesson support."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        command_runner: Any = None,
        learning_root: str | Path | None = None,
        review_lesson_registry: str | Path | None = None,
        review_lesson_learning_root: str | Path | None = None,
        review_registry_path: str | Path | None = None,
        review_learning_root: str | Path | None = None,
    ) -> None:
        super().__init__(
            repo_root,
            command_runner=command_runner,
            learning_root=learning_root,
        )
        registry = review_lesson_registry or review_registry_path or DEFAULT_REGISTRY_PATH
        if not Path(registry).is_absolute():
            registry = self.repo_root / Path(registry)
        self.review_lessons = ReviewLessonEngine(
            self.repo_root,
            registry_path=registry,
            learning_root=(
                review_lesson_learning_root
                or review_learning_root
                or DEFAULT_LEARNING_ROOT
            ),
        )

    @staticmethod
    def _review_learning_brand(packet: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(packet, dict):
            return packet
        packet["review_learning_version"] = REVIEW_LEARNING_WABOOSE_VERSION
        packet["base_waboose_version"] = CODING_WABOOSE_VERSION
        packet["production_mutation"] = False
        packet["automatic_fix"] = False
        packet["automatic_commit"] = False
        packet["automatic_push"] = False
        packet["automatic_pull_request"] = False
        packet["automatic_merge"] = False
        packet["human_review_required"] = True
        return packet

    def prepare(self, value: CodingWabooseRequest | Mapping[str, Any]) -> dict[str, Any]:
        result = super().prepare(value)
        if not result.get("ok"):
            return self._review_learning_brand(result)
        review_id = str(result["review_id"])
        summary = self.review_lessons.summary()
        self._reviews[review_id]["typed_review_lesson_summary"] = summary
        result["typed_review_lesson_summary"] = summary
        result["review_lesson_context"] = summary
        result["agent_packet"] = self._agent_packet_from_state(
            review_id,
            include_source=False,
        )
        return self._review_learning_brand(result)

    def scan(self, review_id: str) -> dict[str, Any]:
        result = super().scan(review_id)
        if not result.get("ok"):
            return self._review_learning_brand(result)
        state = self._reviews[review_id]
        findings: list[dict[str, Any]] = []
        for file in state["contract"].changed_files:
            if not file.endswith(".py"):
                continue
            path = self._resolve_file(file)
            if path is None or not path.is_file():
                continue
            try:
                with tokenize.open(path) as handle:
                    source = handle.read()
                packet = self.review_lessons.scan_source(file=file, source=source)
            except (OSError, SyntaxError, UnicodeError, LookupError, ValueError):
                continue
            findings.extend(
                item for item in packet.get("findings", []) if isinstance(item, Mapping)
            )
        state["typed_review_lesson_findings"] = findings
        result["typed_review_lesson_findings"] = findings
        result["typed_review_lesson_finding_count"] = len(findings)
        result["review_lesson_findings_added"] = len(findings)
        result["review_lesson_crucible"] = self.review_lessons.crucible()
        result["agent_packet"] = self._agent_packet_from_state(
            review_id,
            include_source=False,
        )
        return self._review_learning_brand(result)

    def finalize(self, review_id: str) -> dict[str, Any]:
        result = super().finalize(review_id)
        state = self._reviews.get(review_id, {})
        result["typed_review_lesson_findings"] = list(
            state.get("typed_review_lesson_findings") or []
        )
        result["typed_review_lesson_summary"] = state.get(
            "typed_review_lesson_summary",
            self.review_lessons.summary(),
        )
        result["typed_review_lesson_findings_are_advisory"] = True
        return self._review_learning_brand(result)

    def _agent_packet_from_state(
        self,
        review_id: str,
        *,
        include_source: bool,
        max_files: int = 24,
        max_lines_per_file: int = 120,
    ) -> dict[str, Any]:
        packet = super()._agent_packet_from_state(
            review_id,
            include_source=include_source,
            max_files=max_files,
            max_lines_per_file=max_lines_per_file,
        )
        state = self._reviews[review_id]
        packet["typed_review_lesson_summary"] = state.get(
            "typed_review_lesson_summary",
            self.review_lessons.summary(),
        )
        packet["typed_review_lesson_findings"] = list(
            state.get("typed_review_lesson_findings") or []
        )
        packet.setdefault("agent_instructions", []).extend(
            [
                "Treat typed review-lesson findings as probable investigative focus, never proof or repair authority.",
                "For each lesson finding, reproduce the defect against exact current source or explicitly reject it with evidence.",
                "Bind any accepted repair to the lesson's invariant and required regression before Forge handoff.",
            ]
        )
        return self._review_learning_brand(packet)

    def normalize_external_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        return self._review_learning_brand(
            self.review_lessons.normalize_review(payload, current_head=current_head)
        )

    def ingest_external_review(
        self,
        payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        return self._review_learning_brand(
            self.review_lessons.ingest_review(payload, current_head=current_head)
        )

    def review_lesson_summary(self) -> dict[str, Any]:
        return self._review_learning_brand(self.review_lessons.summary())

    def run_review_lesson_detector(
        self,
        detector_id: str,
        candidate: Any,
    ) -> dict[str, Any]:
        return self._review_learning_brand(
            self.review_lessons.detector(detector_id, candidate)
        )

    def run_review_lesson_crucible(
        self,
        *,
        detector_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        return self._review_learning_brand(
            self.review_lessons.crucible(detector_ids=detector_ids)
        )

    def replay_review_lessons(
        self,
        detector_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        return self.run_review_lesson_crucible(detector_ids=detector_ids)


ReviewLessonAwareCodingWaboose = ReviewLearningCodingWaboose


__all__ = [
    "REVIEW_LEARNING_WABOOSE_VERSION",
    "ReviewLearningCodingWaboose",
    "ReviewLessonAwareCodingWaboose",
]
