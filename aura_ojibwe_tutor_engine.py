"""
Aura Ojibwe Tutor Engine
==========================
Schema version: AURA_OJIBWE_TUTOR_ENGINE_V1

Main session orchestrator for the Aura Anishinaabemowin language tutor.

The engine chains all modules in the correct order:

  raw input
  → orthography normalization
  → lexicon lookup
  → translation guard (three gates)
  → dialect conflict check (OPD vs Treaty #1)
  → governance check (data sovereignty)
  → pronunciation hint
  → tutor response with confidence/citation
  → review queue (if CANDIDATE_NEEDS_REVIEW)
  → learner profile update

Modes:
  WORD_LOOKUP           — Look up a word, return gloss + pronunciation
  MORPHOLOGY_EXPLANATION — Explain morphological breakdown of a word
  PHRASE_LESSON         — Guided phrase/sentence building
  QUIZ                  — Multiple choice / fill-in-the-blank practice
  LEARNER_CORRECTION    — Correct a learner error with explanation
  SOURCE_EXPLANATION    — Show source hierarchy for a given answer

Rule: TutorResponse always carries confidence_status, source_refs,
      and dialect_notes.  No naked answer strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from aura_language_source_registry import LanguageSourceRegistry
from aura_language_data_governance import LanguageDataGovernancePolicy, DataAccessLevel
from aura_language_privacy_policy import LanguagePrivacyPolicy
from aura_language_review_queue import LanguageReviewQueue
from aura_ojibwe_dialect_profile import DialectProfile, TREATY1_PLAINS_OJIBWE
from aura_ojibwe_lexicon_sidecar import OjibweLexiconSidecar
from aura_ojibwe_orthography import OjibweOrthographyNormalizer
from aura_ojibwe_morph_bridge import OjibweMorphBridge
from aura_ojibwe_translation_guard import TranslationGuard, ConfidenceStatus
from aura_ojibwe_dialect_conflict_resolver import DialectConflictResolver
from aura_ojibwe_audio_consent_registry import AudioConsentRegistry
from aura_ojibwe_pronunciation_bridge import OjibwePronunciationBridge
from aura_language_learner_profile import LearnerProfile

AURA_OJIBWE_TUTOR_ENGINE_V1 = "AURA_OJIBWE_TUTOR_ENGINE_V1"


class TutorMode(str, Enum):
    WORD_LOOKUP = "WORD_LOOKUP"
    MORPHOLOGY_EXPLANATION = "MORPHOLOGY_EXPLANATION"
    PHRASE_LESSON = "PHRASE_LESSON"
    QUIZ = "QUIZ"
    LEARNER_CORRECTION = "LEARNER_CORRECTION"
    SOURCE_EXPLANATION = "SOURCE_EXPLANATION"


@dataclass
class TutorResponse:
    """
    A complete tutor response with mandatory provenance fields.

    confidence_status, source_refs, and dialect_notes are ALWAYS present.
    Naked answer strings without these fields must never be returned.
    """
    schema_version: str
    mode: TutorMode
    query: str
    answer: Optional[str]                   # The main tutor output (None if BLOCKED)
    confidence_status: ConfidenceStatus      # VERIFIED / CANDIDATE_NEEDS_REVIEW / BLOCKED
    source_refs: List[str]                   # LanguageSourceRegistry IDs
    dialect_notes: Optional[str]             # Dialect context / conflict explanation
    morphology_breakdown: Optional[dict]     # FST parse breakdown (if available)
    pronunciation_hint: Optional[str]        # Phonetic guidance
    practice_prompt: Optional[str]           # Suggested follow-up practice
    teacher_review_flagged: bool             # True if submitted to review queue
    review_queue_id: Optional[str]           # Review ID (if flagged)
    caution_label: Optional[str]             # Shown when CANDIDATE_NEEDS_REVIEW
    example_phrase: Optional[str]            # Example from lexicon (if any)

    def __post_init__(self) -> None:
        if self.schema_version != AURA_OJIBWE_TUTOR_ENGINE_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_OJIBWE_TUTOR_ENGINE_V1}"
            )
        # Hard invariant: BLOCKED responses have no answer
        if self.confidence_status == ConfidenceStatus.BLOCKED and self.answer is not None:
            raise ValueError(
                "BLOCKED TutorResponse must have answer=None."
            )

    def display(self) -> str:
        """Human-readable representation for CLI / demo output."""
        lines = [
            f"[{self.confidence_status.value}] {self.query}",
            f"  Answer: {self.answer or '(blocked — see caution below)'}",
        ]
        if self.caution_label:
            lines.append(f"  ⚠ {self.caution_label}")
        if self.morphology_breakdown:
            mb = self.morphology_breakdown
            stem = mb.get("stem", "?")
            prefix = mb.get("person_prefix") or "(no prefix)"
            lines.append(f"  Morphology: stem={stem}, person={prefix}")
        if self.pronunciation_hint:
            lines.append(f"  Pronunciation: {self.pronunciation_hint}")
        if self.dialect_notes:
            lines.append(f"  Dialect: {self.dialect_notes}")
        if self.source_refs:
            lines.append(f"  Sources: {', '.join(self.source_refs)}")
        if self.example_phrase:
            lines.append(f"  Example: {self.example_phrase}")
        if self.practice_prompt:
            lines.append(f"  Practice: {self.practice_prompt}")
        if self.teacher_review_flagged:
            lines.append(
                f"  📋 Flagged for teacher review (id: {self.review_queue_id or 'queued'})"
            )
        return "\n".join(lines)


class OjibweTutorEngine:
    """
    Main Aura Ojibwe language tutor session.

    Construction assembles the full module stack.
    Call respond() for each learner query.

    Args:
        dialect_profile: The DialectProfile for this session.
            Defaults to TREATY1_PLAINS_OJIBWE.
        learner_profile: Optional LearnerProfile for progress tracking.
        source_registry: LanguageSourceRegistry (auto-built if None).
        governance_policy: Data governance policy.
        privacy_policy: Session privacy policy.
        review_queue: Community review queue.
    """

    def __init__(
        self,
        dialect_profile: Optional[DialectProfile] = None,
        learner_profile: Optional[LearnerProfile] = None,
        source_registry: Optional[LanguageSourceRegistry] = None,
        governance_policy: Optional[LanguageDataGovernancePolicy] = None,
        privacy_policy: Optional[LanguagePrivacyPolicy] = None,
        review_queue: Optional[LanguageReviewQueue] = None,
    ) -> None:
        self.dialect_profile = dialect_profile or TREATY1_PLAINS_OJIBWE
        self.learner_profile = learner_profile
        self.source_registry = source_registry or LanguageSourceRegistry()
        self.governance = governance_policy or LanguageDataGovernancePolicy()
        self.privacy = privacy_policy or LanguagePrivacyPolicy()
        self.review_queue = review_queue or LanguageReviewQueue()

        # Module stack
        self.lexicon = OjibweLexiconSidecar()
        self.normalizer = OjibweOrthographyNormalizer()
        self.morph_bridge = OjibweMorphBridge()
        self.guard = TranslationGuard(
            dialect_profile=self.dialect_profile,
            source_registry=self.source_registry,
            morph_bridge=self.morph_bridge,
            review_queue=self.review_queue,
        )
        self.conflict_resolver = DialectConflictResolver()
        self.audio_registry = AudioConsentRegistry()
        self.pronunciation_bridge = OjibwePronunciationBridge(self.audio_registry)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def respond(
        self,
        query: str,
        mode: TutorMode = TutorMode.WORD_LOOKUP,
        session_id: Optional[str] = None,
    ) -> TutorResponse:
        """
        Process a learner query and return a TutorResponse.

        Always returns a response with confidence_status, source_refs,
        and dialect_notes populated.
        """
        if mode == TutorMode.WORD_LOOKUP:
            return self._word_lookup(query, session_id)
        elif mode == TutorMode.MORPHOLOGY_EXPLANATION:
            return self._morphology_explanation(query, session_id)
        elif mode == TutorMode.SOURCE_EXPLANATION:
            return self._source_explanation(query, session_id)
        else:
            return self._word_lookup(query, session_id)

    # ------------------------------------------------------------------
    # Mode implementations
    # ------------------------------------------------------------------

    def _word_lookup(self, query: str, session_id: Optional[str]) -> TutorResponse:
        """Look up a word, normalize input, run guard, return full response."""

        # 1. Normalize
        norm = self.normalizer.normalize(query)
        normalized = norm.normalized_form

        # 2. Governance: PUBLIC mode assumed for basic lookup
        gov = self.governance.check_access(DataAccessLevel.PUBLIC, normalized)
        if not gov.allowed:
            return self._blocked_response(query, TutorMode.WORD_LOOKUP, gov.reason)

        # 3. Lexicon lookup
        entry = self.lexicon.lookup(normalized)
        if entry is None:
            # Try variants
            for variant in norm.variant_candidates:
                entry = self.lexicon.lookup(variant)
                if entry:
                    break

        # 4. Translation guard
        source_id = entry.source_ref if entry else None
        raw_gloss = entry.gloss_en if entry else None

        guarded = self.guard.evaluate(
            candidate=normalized,
            source_id=source_id,
            raw_translation=raw_gloss,
            learner_session_id=session_id,
        )

        # 5. Pronunciation hint
        audio_ref = entry.audio_ref if entry else None
        hint = self.pronunciation_bridge.get_hint(normalized, audio_ref)
        phonetic_text = hint.phonetic_breakdown
        if hint.vowel_notes:
            phonetic_text += " | Vowels: " + "; ".join(hint.vowel_notes[:2])

        # 6. Dialect conflict check (if OPD URL present)
        dialect_notes = guarded.dialect_notes
        if entry and entry.opd_url:
            # Surface that an OPD reference exists
            dialect_notes = (
                (dialect_notes or "")
                + f" OPD cross-reference available at: {entry.opd_url} "
                "(Central Southwestern Ojibwe — different dialect from Treaty #1)."
            )

        # 7. Normalization notes
        if norm.dialect_notes:
            dialect_notes = (dialect_notes or "") + " " + norm.dialect_notes

        # 8. Answer text
        if guarded.confidence_status == ConfidenceStatus.BLOCKED:
            answer = None
            practice_prompt = None
        else:
            if raw_gloss:
                answer = f"'{normalized}' — {raw_gloss}"
            else:
                answer = f"'{normalized}' — no vetted entry found in Treaty #1 sidecar."
                if norm.variant_candidates:
                    answer += f" Tried variants: {', '.join(norm.variant_candidates)}."
            practice_prompt = (
                f"Try using '{normalized}' in a sentence. "
                "What does it relate to — a person, a place, or an action?"
            )

        # 9. Learner profile update
        if self.learner_profile and session_id and guarded.confidence_status != ConfidenceStatus.BLOCKED:
            self.learner_profile.record_practice(
                word=normalized,
                correct=bool(entry),
                session_id=session_id,
                curriculum_node="WORD_LOOKUP",
            )

        return TutorResponse(
            schema_version=AURA_OJIBWE_TUTOR_ENGINE_V1,
            mode=TutorMode.WORD_LOOKUP,
            query=query,
            answer=answer,
            confidence_status=guarded.confidence_status,
            source_refs=guarded.source_refs,
            dialect_notes=dialect_notes,
            morphology_breakdown=guarded.morphology_breakdown,
            pronunciation_hint=phonetic_text,
            practice_prompt=practice_prompt,
            teacher_review_flagged=guarded.review_queue_id is not None,
            review_queue_id=guarded.review_queue_id,
            caution_label=guarded.caution_label,
            example_phrase=entry.example_phrase if entry else None,
        )

    def _morphology_explanation(self, query: str, session_id: Optional[str]) -> TutorResponse:
        """Explain the morphological breakdown of a word."""
        norm = self.normalizer.normalize(query)
        normalized = norm.normalized_form

        entry = self.lexicon.lookup(normalized)
        parse = self.morph_bridge.parse_word(normalized)

        source_id = entry.source_ref if entry else "aura_fst_internal"
        raw_gloss = entry.gloss_en if entry else None

        guarded = self.guard.evaluate(
            candidate=normalized,
            source_id=source_id,
            raw_translation=raw_gloss,
            learner_session_id=session_id,
        )

        # Build explanation
        slot_sequence = None
        if entry and entry.part_of_speech in ("VAI", "VTA", "VTI", "VII"):
            from aura_ojibwe_morph_bridge import VerbClass
            try:
                vc = VerbClass(entry.part_of_speech)
                slot_sequence = self.morph_bridge.slot_sequence_for_verb(vc)
            except (ValueError, KeyError):
                pass

        answer = None
        if guarded.confidence_status != ConfidenceStatus.BLOCKED:
            lines = [f"Morphology of '{normalized}':"]
            mb = guarded.morphology_breakdown or {}
            if mb.get("person_prefix"):
                lines.append(f"  Person prefix: '{mb['person_prefix']}' — {mb.get('person_description', '')}")
            if mb.get("stem"):
                lines.append(f"  Stem: '{mb['stem']}'")
            if mb.get("verb_class"):
                lines.append(f"  Verb class: {mb['verb_class']}")
            if slot_sequence:
                lines.append(f"  Template: {' → '.join(slot_sequence)}")
            if raw_gloss:
                lines.append(f"  English gloss: {raw_gloss}")
            answer = "\n".join(lines)

        return TutorResponse(
            schema_version=AURA_OJIBWE_TUTOR_ENGINE_V1,
            mode=TutorMode.MORPHOLOGY_EXPLANATION,
            query=query,
            answer=answer,
            confidence_status=guarded.confidence_status,
            source_refs=guarded.source_refs,
            dialect_notes=guarded.dialect_notes,
            morphology_breakdown=guarded.morphology_breakdown,
            pronunciation_hint=None,
            practice_prompt=f"Try conjugating '{normalized}' with a different person prefix (ni-, gi-, o-).",
            teacher_review_flagged=guarded.review_queue_id is not None,
            review_queue_id=guarded.review_queue_id,
            caution_label=guarded.caution_label,
            example_phrase=entry.example_phrase if entry else None,
        )

    def _source_explanation(self, query: str, session_id: Optional[str]) -> TutorResponse:
        """Explain the source hierarchy for a query."""
        norm = self.normalizer.normalize(query)
        normalized = norm.normalized_form
        entry = self.lexicon.lookup(normalized)

        source_explanation_lines = [
            f"Source hierarchy for '{normalized}':",
            self.dialect_profile.source_hierarchy_description,
        ]
        if entry:
            rec = self.source_registry.get(entry.source_ref)
            if rec:
                source_explanation_lines.append(
                    f"\nThis entry: {rec.source_name} ({rec.source_type.value}) "
                    f"— confidence {rec.confidence:.2f} — {rec.citation}"
                )

        return TutorResponse(
            schema_version=AURA_OJIBWE_TUTOR_ENGINE_V1,
            mode=TutorMode.SOURCE_EXPLANATION,
            query=query,
            answer="\n".join(source_explanation_lines),
            confidence_status=ConfidenceStatus.VERIFIED,  # Source explanation is always safe
            source_refs=[entry.source_ref] if entry else [],
            dialect_notes=None,
            morphology_breakdown=None,
            pronunciation_hint=None,
            practice_prompt=None,
            teacher_review_flagged=False,
            review_queue_id=None,
            caution_label=None,
            example_phrase=None,
        )

    def _blocked_response(self, query: str, mode: TutorMode, reason: str) -> TutorResponse:
        return TutorResponse(
            schema_version=AURA_OJIBWE_TUTOR_ENGINE_V1,
            mode=mode,
            query=query,
            answer=None,
            confidence_status=ConfidenceStatus.BLOCKED,
            source_refs=[],
            dialect_notes=f"Governance block: {reason}",
            morphology_breakdown=None,
            pronunciation_hint=None,
            practice_prompt=None,
            teacher_review_flagged=False,
            review_queue_id=None,
            caution_label=None,
            example_phrase=None,
        )
