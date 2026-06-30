"""
Aura Ojibwe Translation Guard
================================
Schema version: AURA_TRANSLATION_GUARD_V1

The three-gate enforcement pipeline for all language output.

Gate 1 — Dialect profile: Is a DialectProfile bound to this session?
Gate 2 — Source record: Is there a SourceRecord meeting the confidence threshold?
Gate 3 — FST parse: Is the morphology grammatically coherent?

Confidence status:
  VERIFIED            — All three gates pass
  CANDIDATE_NEEDS_REVIEW — One or two gates fail
  BLOCKED             — No grounding at all, or governance/privacy block

Rule: The guard NEVER returns a naked translation string.
Every output is wrapped in a GuardedTranslation with a confidence_status field.
Uncertain outputs trigger a ReviewItem in the LanguageReviewQueue.

This is the outermost enforcement module — everything passes through here
before reaching the learner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

AURA_TRANSLATION_GUARD_V1 = "AURA_TRANSLATION_GUARD_V1"

# Minimum source confidence required for VERIFIED status
VERIFIED_CONFIDENCE_THRESHOLD = 0.80


class ConfidenceStatus(str, Enum):
    VERIFIED = "VERIFIED"
    CANDIDATE_NEEDS_REVIEW = "CANDIDATE_NEEDS_REVIEW"
    BLOCKED = "BLOCKED"


@dataclass
class GuardedTranslation:
    """
    A translation or language output wrapped with its confidence status.

    confidence_status is always present.
    translation is None if BLOCKED.
    When CANDIDATE_NEEDS_REVIEW, translation is shown with a caution label.
    """
    schema_version: str
    confidence_status: ConfidenceStatus
    translation: Optional[str]             # None if BLOCKED
    source_refs: List[str]
    dialect_notes: Optional[str]
    gate_results: dict                     # Which gates passed/failed and why
    review_queue_id: Optional[str] = None  # Set if a review item was submitted
    morphology_breakdown: Optional[dict] = None
    caution_label: Optional[str] = None    # Shown to learner when CANDIDATE_NEEDS_REVIEW

    def __post_init__(self) -> None:
        if self.schema_version != AURA_TRANSLATION_GUARD_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_TRANSLATION_GUARD_V1}"
            )
        if self.confidence_status == ConfidenceStatus.BLOCKED and self.translation is not None:
            raise ValueError(
                "BLOCKED GuardedTranslation must have translation=None. "
                "A blocked output must never carry a translation string."
            )


class TranslationGuard:
    """
    Three-gate enforcement pipeline for all language output.

    Usage:
        guard = TranslationGuard(
            dialect_profile=TREATY1_PLAINS_OJIBWE,
            source_registry=registry,
            morph_bridge=bridge,
            review_queue=queue,
        )
        result = guard.evaluate(
            candidate="boozhoo",
            source_id="treaty1_community_verified",
            raw_translation="Hello / Greetings",
        )
    """

    def __init__(
        self,
        dialect_profile,          # DialectProfile
        source_registry,          # LanguageSourceRegistry
        morph_bridge,             # OjibweMorphBridge
        review_queue=None,        # LanguageReviewQueue (optional — review items submitted if set)
    ) -> None:
        self._dialect_profile = dialect_profile
        self._source_registry = source_registry
        self._morph_bridge = morph_bridge
        self._review_queue = review_queue

    def evaluate(
        self,
        candidate: str,
        source_id: Optional[str],
        raw_translation: Optional[str],
        word_for_parse: Optional[str] = None,
        governance_decision=None,  # GovernanceDecision (if already checked)
        learner_session_id: Optional[str] = None,
    ) -> GuardedTranslation:
        """
        Run the three gates and return a GuardedTranslation.

        Args:
            candidate: The Ojibwe word or phrase being evaluated.
            source_id: The LanguageSourceRegistry ID for the claimed source.
            raw_translation: The proposed English gloss or translation.
            word_for_parse: Word to parse morphologically (defaults to candidate).
            governance_decision: Pre-computed governance decision (if any).
            learner_session_id: For review queue items.
        """
        gate_results = {}
        failed_gates = []
        source_refs = []

        # ------------------------------------------------------------------
        # Gate 1: Dialect profile
        # ------------------------------------------------------------------
        if self._dialect_profile is None:
            gate_results["dialect_profile"] = {
                "passed": False,
                "reason": "No dialect profile is bound to this session.",
            }
            failed_gates.append("dialect_profile")
        else:
            gate_results["dialect_profile"] = {
                "passed": True,
                "dialect_id": self._dialect_profile.dialect_id,
            }

        # ------------------------------------------------------------------
        # Gate 2: Source record
        # ------------------------------------------------------------------
        if source_id is None:
            gate_results["source_record"] = {
                "passed": False,
                "reason": "No source_id provided. Every translation requires a source.",
            }
            failed_gates.append("source_record")
        else:
            record = self._source_registry.get(source_id)
            if record is None:
                gate_results["source_record"] = {
                    "passed": False,
                    "reason": f"Source '{source_id}' not found in registry.",
                }
                failed_gates.append("source_record")
            elif record.confidence < VERIFIED_CONFIDENCE_THRESHOLD:
                gate_results["source_record"] = {
                    "passed": False,
                    "reason": (
                        f"Source '{source_id}' confidence {record.confidence:.2f} is below "
                        f"VERIFIED threshold {VERIFIED_CONFIDENCE_THRESHOLD}."
                    ),
                    "source_type": record.source_type.value,
                }
                failed_gates.append("source_record")
                source_refs.append(source_id)
            else:
                gate_results["source_record"] = {
                    "passed": True,
                    "source_id": source_id,
                    "source_type": record.source_type.value,
                    "confidence": record.confidence,
                }
                source_refs.append(source_id)

        # ------------------------------------------------------------------
        # Gate 3: FST morphology parse
        # ------------------------------------------------------------------
        word_to_parse = word_for_parse or candidate
        parse = self._morph_bridge.parse_word(word_to_parse)

        from aura_ojibwe_morph_bridge import ParseStatus
        morph_ok = parse.status in (ParseStatus.PARSED, ParseStatus.PARTIAL)
        gate_results["fst_parse"] = {
            "passed": morph_ok,
            "status": parse.status.value,
            "confidence": parse.confidence,
            "notes": parse.notes,
        }
        if not morph_ok:
            failed_gates.append("fst_parse")

        morph_breakdown = {
            "stem": parse.stem,
            "person_prefix": parse.person_prefix,
            "person_description": parse.person_description,
            "verb_class": parse.verb_class.value if parse.verb_class else None,
            "animacy": parse.animacy.value,
            "fst_route": parse.fst_route,
        }

        # ------------------------------------------------------------------
        # Determine confidence status
        # ------------------------------------------------------------------
        if not failed_gates:
            status = ConfidenceStatus.VERIFIED
            caution_label = None
            dialect_notes = None
        elif "dialect_profile" in failed_gates or source_id is None:
            # Hard block: no dialect context or no source at all
            status = ConfidenceStatus.BLOCKED
            caution_label = None
            dialect_notes = "Blocked: Missing dialect profile or source record."
        else:
            status = ConfidenceStatus.CANDIDATE_NEEDS_REVIEW
            failed_str = ", ".join(failed_gates)
            caution_label = (
                f"⚠ CANDIDATE (needs community review): "
                f"Not all verification gates passed ({failed_str}). "
                "Do not treat this as confirmed Treaty #1 language."
            )
            dialect_notes = (
                f"Source confidence or FST parse did not meet VERIFIED threshold. "
                f"Failed gates: {failed_str}. Submitted for teacher review."
            )

        # ------------------------------------------------------------------
        # Submit to review queue if CANDIDATE
        # ------------------------------------------------------------------
        review_id = None
        if status == ConfidenceStatus.CANDIDATE_NEEDS_REVIEW and self._review_queue is not None:
            from aura_language_review_queue import make_review_item, ReviewItemType
            review_item = make_review_item(
                item_type=ReviewItemType.PHRASE_CANDIDATE,
                dialect_profile_id=self._dialect_profile.dialect_id,
                candidate=candidate,
                reason=f"Failed gates: {', '.join(failed_gates)}",
                source_refs=source_refs,
                confidence_score=parse.confidence,
                morphology_breakdown=morph_breakdown,
                learner_session_id=learner_session_id,
            )
            review_id = self._review_queue.submit(review_item)

        return GuardedTranslation(
            schema_version=AURA_TRANSLATION_GUARD_V1,
            confidence_status=status,
            translation=raw_translation if status != ConfidenceStatus.BLOCKED else None,
            source_refs=source_refs,
            dialect_notes=dialect_notes,
            gate_results=gate_results,
            review_queue_id=review_id,
            morphology_breakdown=morph_breakdown,
            caution_label=caution_label,
        )
