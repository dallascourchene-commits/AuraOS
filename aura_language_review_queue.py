"""
Aura Language Community Review Queue
=======================================
Schema version: AURA_LANGUAGE_REVIEW_QUEUE_V1

Captures every uncertain translation, morphology generation, phrase lesson,
or dialect conflict as a ReviewItem for fluent speaker / community teacher
review.

Uncertainty is NOT treated as failure — it is a contribution to community-
governed language revitalization. CANDIDATE_NEEDS_REVIEW items become the
input for the next round of verified content.

Item types:
  phrase_candidate     — A phrase that passed some checks but not all
  word_candidate       — A single word that lacks full Treaty #1 grounding
  morphology_candidate — A generated morphological form needing verification
  dialect_conflict     — OPD and Treaty #1 forms differ
  audio_flag           — Audio reference that needs consent verification
  learner_error        — A learner error pattern that needs pedagogical review

Status transitions:
  pending_teacher_review → approved | rejected | needs_more_context
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

AURA_LANGUAGE_REVIEW_QUEUE_V1 = "AURA_LANGUAGE_REVIEW_QUEUE_V1"


class ReviewItemType(str, Enum):
    PHRASE_CANDIDATE = "phrase_candidate"
    WORD_CANDIDATE = "word_candidate"
    MORPHOLOGY_CANDIDATE = "morphology_candidate"
    DIALECT_CONFLICT = "dialect_conflict"
    AUDIO_FLAG = "audio_flag"
    LEARNER_ERROR = "learner_error"


class ReviewStatus(str, Enum):
    PENDING_TEACHER_REVIEW = "pending_teacher_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_MORE_CONTEXT = "needs_more_context"


@dataclass
class ReviewItem:
    """
    A single item awaiting community / teacher review.

    review_id is auto-generated if not supplied.
    created_at is set to now (UTC) on construction.
    reviewer_decision starts as None and is set when a teacher responds.
    """
    schema_version: str
    item_type: ReviewItemType
    dialect_profile: str                   # dialect_id, e.g. "Treaty1_Plains_Ojibwe"
    candidate: str                         # The uncertain word, phrase, or form
    reason: str                            # Why it was flagged
    source_refs: List[str]                 # LanguageSourceRegistry IDs consulted
    review_id: str = field(default_factory=lambda: f"review_{uuid.uuid4().hex[:8]}")
    status: ReviewStatus = ReviewStatus.PENDING_TEACHER_REVIEW
    reviewer_decision: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    learner_session_id: Optional[str] = None
    confidence_score: Optional[float] = None  # 0.0–1.0, from TranslationGuard
    morphology_breakdown: Optional[dict] = None

    def __post_init__(self) -> None:
        if self.schema_version != AURA_LANGUAGE_REVIEW_QUEUE_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_LANGUAGE_REVIEW_QUEUE_V1}"
            )

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "item_type": self.item_type.value,
            "dialect_profile": self.dialect_profile,
            "candidate": self.candidate,
            "reason": self.reason,
            "source_refs": self.source_refs,
            "status": self.status.value,
            "reviewer_decision": self.reviewer_decision,
            "reviewer_notes": self.reviewer_notes,
            "created_at": self.created_at,
            "learner_session_id": self.learner_session_id,
            "confidence_score": self.confidence_score,
            "morphology_breakdown": self.morphology_breakdown,
        }


class LanguageReviewQueue:
    """
    In-process community review queue.

    In production this would be persisted (JSON file or lightweight DB).
    For the hackathon MVP, it is in-memory with export to dict for inspection.

    Usage:
        queue = LanguageReviewQueue()
        queue.submit(ReviewItem(...))
        items = queue.pending()
        queue.decide("review_abc123de", ReviewStatus.APPROVED, "Correct form for Treaty #1.")
    """

    def __init__(self) -> None:
        self._items: Dict[str, ReviewItem] = {}

    def submit(self, item: ReviewItem) -> str:
        """Add a ReviewItem to the queue. Returns review_id."""
        self._items[item.review_id] = item
        return item.review_id

    def get(self, review_id: str) -> Optional[ReviewItem]:
        return self._items.get(review_id)

    def pending(self) -> List[ReviewItem]:
        """Return all items awaiting teacher review."""
        return [
            i for i in self._items.values()
            if i.status == ReviewStatus.PENDING_TEACHER_REVIEW
        ]

    def by_type(self, item_type: ReviewItemType) -> List[ReviewItem]:
        return [i for i in self._items.values() if i.item_type == item_type]

    def decide(
        self,
        review_id: str,
        status: ReviewStatus,
        reviewer_notes: Optional[str] = None,
        reviewer_decision: Optional[str] = None,
    ) -> None:
        """Record a teacher/reviewer decision on an item."""
        item = self._items.get(review_id)
        if item is None:
            raise KeyError(f"No review item with id={review_id!r}")
        if item.status != ReviewStatus.PENDING_TEACHER_REVIEW:
            raise ValueError(
                f"Review item {review_id!r} is already {item.status.value}. "
                "Cannot re-decide."
            )
        item.status = status
        item.reviewer_notes = reviewer_notes
        item.reviewer_decision = reviewer_decision

    def export(self) -> List[dict]:
        """Export all items as dicts (for persistence / display)."""
        return [i.to_dict() for i in self._items.values()]

    def stats(self) -> dict:
        total = len(self._items)
        by_status: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        for item in self._items.values():
            by_status[item.status.value] = by_status.get(item.status.value, 0) + 1
            by_type[item.item_type.value] = by_type.get(item.item_type.value, 0) + 1
        return {
            "schema_version": AURA_LANGUAGE_REVIEW_QUEUE_V1,
            "total_items": total,
            "by_status": by_status,
            "by_type": by_type,
        }


def make_review_item(
    item_type: ReviewItemType,
    dialect_profile_id: str,
    candidate: str,
    reason: str,
    source_refs: Optional[List[str]] = None,
    confidence_score: Optional[float] = None,
    morphology_breakdown: Optional[dict] = None,
    learner_session_id: Optional[str] = None,
) -> ReviewItem:
    """Convenience factory for creating ReviewItems with required schema version."""
    return ReviewItem(
        schema_version=AURA_LANGUAGE_REVIEW_QUEUE_V1,
        item_type=item_type,
        dialect_profile=dialect_profile_id,
        candidate=candidate,
        reason=reason,
        source_refs=source_refs or [],
        confidence_score=confidence_score,
        morphology_breakdown=morphology_breakdown,
        learner_session_id=learner_session_id,
    )
