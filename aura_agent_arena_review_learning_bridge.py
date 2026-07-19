"""Narrow Agent Bridge adapter for Coding Waboose review-learning tools."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from aura_agent_arena_persistence_bridge import PersistentAuraAgentArenaBridge
from aura_coding_waboose_review_learning import ReviewLessonAwareCodingWaboose

AGENT_ARENA_REVIEW_LEARNING_BRIDGE_VERSION = (
    "AURA_AGENT_ARENA_REVIEW_LEARNING_BRIDGE_V1"
)


class ReviewLearningAgentArenaBridge(PersistentAuraAgentArenaBridge):
    """Existing Agent Bridge plus typed external-review lesson projections."""

    def __init__(
        self,
        *,
        repo_root: str | None = None,
        review_registry_path: str | Path = ".aura/review_lessons/pr164_spatial_review_lessons.json",
        review_learning_root: str | Path | None = None,
    ) -> None:
        super().__init__(repo_root=repo_root)
        kwargs: dict[str, Any] = {"review_registry_path": review_registry_path}
        if review_learning_root is not None:
            kwargs["review_learning_root"] = review_learning_root
        self.coding_waboose = ReviewLessonAwareCodingWaboose(
            self.repo_root,
            **kwargs,
        )

    def aura_waboose_ingest_external_review(
        self,
        review_payload: Mapping[str, Any],
        *,
        current_head: str = "",
    ) -> dict[str, Any]:
        return self.coding_waboose.ingest_external_review(
            review_payload,
            current_head=current_head,
        )

    def aura_waboose_review_lesson_summary(self) -> dict[str, Any]:
        return self.coding_waboose.review_lesson_summary()

    def aura_waboose_run_review_detector(
        self,
        detector_id: str,
        candidate: Any,
    ) -> dict[str, Any]:
        return self.coding_waboose.run_review_lesson_detector(detector_id, candidate)

    def aura_waboose_crucible_replay(
        self,
        detector_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        return self.coding_waboose.replay_review_lessons(detector_ids)

    @staticmethod
    def list_tools() -> list[dict[str, Any]]:
        return [
            *PersistentAuraAgentArenaBridge.list_tools(),
            {
                "name": "aura_waboose_ingest_external_review",
                "description": (
                    "Normalize and store CodeRabbit, Codex, or manual PR review evidence "
                    "with current/historical/resolved/outdated/duplicate disposition."
                ),
                "required_inputs": ["review_payload"],
            },
            {
                "name": "aura_waboose_review_lesson_summary",
                "description": "Show the typed review-lesson registry, detector, and replay status.",
                "required_inputs": [],
            },
            {
                "name": "aura_waboose_run_review_detector",
                "description": "Run one deterministic review-lesson detector on a bounded candidate.",
                "required_inputs": ["detector_id", "candidate"],
            },
            {
                "name": "aura_waboose_crucible_replay",
                "description": "Replay PR164 adversarial review lessons and emit typed receipts.",
                "required_inputs": [],
            },
        ]


__all__ = [
    "AGENT_ARENA_REVIEW_LEARNING_BRIDGE_VERSION",
    "ReviewLearningAgentArenaBridge",
]
