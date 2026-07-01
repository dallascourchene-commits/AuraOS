"""
Aura Language Learner Profile
================================
Schema version: AURA_LEARNER_PROFILE_V1

Tracks learner progress independently of all source truth.

Critical invariant:
  The LearnerProfile tracks what the learner knows and how they are
  progressing.  It does NOT contain, modify, or override any LexiconEntry.
  QDKT scores may influence lesson sequencing, but they never mutate the
  lexicon or the source records.

Fields:
  learner_id              — local-only identifier (no PII by default)
  dialect_profile         — the dialect being learned
  known_words             — words with at least one correct response
  mastered_curriculum_nodes — curriculum graph nodes completed
  common_errors           — recurring error patterns for personalized feedback
  practice_history        — lightweight session log (word, correct, timestamp)
  teacher_review_items_seen — review_ids the learner has been informed about

Privacy:
  All fields are local-only by default.
  aura_language_privacy_policy.py enforces no external egress without consent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

AURA_LEARNER_PROFILE_V1 = "AURA_LEARNER_PROFILE_V1"


@dataclass
class PracticeRecord:
    """Single practice event — immutable once created."""
    word: str
    correct: bool
    session_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    curriculum_node: Optional[str] = None


@dataclass
class LearnerProfile:
    """
    A learner's progress and history.  Completely separate from lexicon truth.

    learner_id defaults to a locally generated UUID.  It is NEVER sent to
    external LLMs (privacy policy enforces this).
    """
    schema_version: str
    dialect_profile: str                        # dialect_id being studied
    learner_id: str = field(
        default_factory=lambda: f"learner_{uuid.uuid4().hex[:8]}"
    )
    known_words: List[str] = field(default_factory=list)
    mastered_curriculum_nodes: List[str] = field(default_factory=list)
    common_errors: List[Dict] = field(default_factory=list)
    practice_history: List[PracticeRecord] = field(default_factory=list)
    teacher_review_items_seen: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.schema_version != AURA_LEARNER_PROFILE_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_LEARNER_PROFILE_V1}"
            )

    # ------------------------------------------------------------------
    # Progress updates (learner-side only — no lexicon side effects)
    # ------------------------------------------------------------------

    def record_practice(
        self,
        word: str,
        correct: bool,
        session_id: str,
        curriculum_node: Optional[str] = None,
    ) -> None:
        """Log a practice event."""
        self.practice_history.append(
            PracticeRecord(
                word=word,
                correct=correct,
                session_id=session_id,
                curriculum_node=curriculum_node,
            )
        )
        if correct and word not in self.known_words:
            self.known_words.append(word)

    def mark_node_mastered(self, node_id: str) -> None:
        """Mark a curriculum node as mastered."""
        if node_id not in self.mastered_curriculum_nodes:
            self.mastered_curriculum_nodes.append(node_id)

    def record_error(
        self,
        word: str,
        error_type: str,
        learner_input: str,
        expected: str,
    ) -> None:
        """Track a recurring error pattern for personalized feedback."""
        self.common_errors.append(
            {
                "word": word,
                "error_type": error_type,
                "learner_input": learner_input,
                "expected": expected,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def mark_review_item_seen(self, review_id: str) -> None:
        if review_id not in self.teacher_review_items_seen:
            self.teacher_review_items_seen.append(review_id)

    # ------------------------------------------------------------------
    # QDKT-compatible progress summary
    # ------------------------------------------------------------------

    def qdkt_summary(self) -> dict:
        """
        Returns a progress summary suitable for QDKT lesson ranking.
        Does not expose learner_id — anonymised for internal use.
        """
        correct = sum(1 for r in self.practice_history if r.correct)
        total = len(self.practice_history)
        return {
            "schema_version": AURA_LEARNER_PROFILE_V1,
            "dialect_profile": self.dialect_profile,
            "known_word_count": len(self.known_words),
            "mastered_node_count": len(self.mastered_curriculum_nodes),
            "practice_events": total,
            "accuracy_pct": round(100 * correct / total, 1) if total > 0 else 0.0,
            "error_pattern_count": len(self.common_errors),
        }

    def to_dict_safe(self) -> dict:
        """
        Export profile as dict, omitting learner_id for privacy-safe display.
        Full export (with learner_id) requires explicit teacher permission —
        enforced by aura_language_privacy_policy.py.
        """
        return {
            "schema_version": self.schema_version,
            "dialect_profile": self.dialect_profile,
            # learner_id deliberately omitted
            "known_words": list(self.known_words),
            "mastered_curriculum_nodes": list(self.mastered_curriculum_nodes),
            "practice_event_count": len(self.practice_history),
            "common_error_count": len(self.common_errors),
        }


def new_learner_profile(dialect_profile_id: str) -> LearnerProfile:
    """Convenience factory for creating a new LearnerProfile."""
    return LearnerProfile(
        schema_version=AURA_LEARNER_PROFILE_V1,
        dialect_profile=dialect_profile_id,
    )
