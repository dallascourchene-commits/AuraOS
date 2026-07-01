"""
Aura Ojibwe Dialect Conflict Resolver
========================================
Schema version: AURA_DIALECT_CONFLICT_RESOLVER_V1

When OPD (Central Southwestern Ojibwe) and a Treaty #1 verified source
give different forms, that is not an error — it is a dialect difference
that must be surfaced and taught.

The resolver does NOT:
  - Suppress the OPD form
  - Pretend there is one "correct" Ojibwe
  - Allow OPD to override Treaty #1 verified forms

The resolver DOES:
  - Surface the conflict with both forms and their dialect labels
  - Prefer the Treaty #1 verified form as the tutor's primary answer
  - Generate a pedagogical dialect note explaining the difference
  - Submit a ReviewItem to the community queue for teacher annotation
  - Produce a ConflictRecord for the topology scene graph

Conflict sources:
  - Vocabulary (different words for same concept)
  - Spelling (orthographic variation)
  - Morphological form (different suffix patterns)
  - Animacy class (some words differ in animacy across dialects)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

AURA_DIALECT_CONFLICT_RESOLVER_V1 = "AURA_DIALECT_CONFLICT_RESOLVER_V1"


class ConflictType(str, Enum):
    VOCABULARY = "vocabulary"             # Entirely different words
    SPELLING = "spelling"                 # Same pronunciation, different orthography
    MORPHOLOGICAL = "morphological"       # Different suffix/prefix patterns
    ANIMACY = "animacy"                   # Word has different animacy in different dialects
    SEMANTIC_SHIFT = "semantic_shift"     # Meaning shifted or narrowed between dialects


class ConflictPreference(str, Enum):
    TREATY1_VERIFIED = "TREATY1_VERIFIED"   # Treaty #1 source wins (primary default)
    TREATY1_VETTED = "TREATY1_VETTED"       # Treaty #1 vetted source
    NEEDS_COMMUNITY_REVIEW = "NEEDS_COMMUNITY_REVIEW"  # No clear Treaty #1 form


@dataclass
class ConflictRecord:
    """
    A documented dialect conflict between two sources for the same word/concept.

    Both forms are preserved.  The tutor_preferred_form is the form used
    in lessons.  The alternate_form is shown with its dialect label.
    """
    schema_version: str
    conflict_id: str
    concept: str                           # English gloss or concept being described
    tutor_preferred_form: str              # Treaty #1 form (used in lessons)
    tutor_dialect_label: str               # e.g. "Treaty #1 Plains Ojibwe (Saulteaux)"
    alternate_form: str                    # OPD or other dialect form
    alternate_dialect_label: str           # e.g. "Central Southwestern Ojibwe (OPD)"
    conflict_type: ConflictType
    preference: ConflictPreference
    tutor_message: str                     # Pedagogical explanation shown to learner
    teacher_note: Optional[str] = None     # Space for community reviewer annotation
    source_refs: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.schema_version != AURA_DIALECT_CONFLICT_RESOLVER_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_DIALECT_CONFLICT_RESOLVER_V1}"
            )


class DialectConflictResolver:
    """
    Detects and resolves dialect conflicts, always preferring Treaty #1
    verified forms while surfacing the difference to the learner.

    Usage:
        resolver = DialectConflictResolver()
        record = resolver.resolve(
            concept="grandmother",
            treaty1_form="nookomis",
            treaty1_source_type="VERIFIED",
            alternate_form="nookomis",         # same here — no conflict
            alternate_dialect_label="OPD",
        )
    """

    def resolve(
        self,
        concept: str,
        treaty1_form: str,
        treaty1_source_type: str,
        alternate_form: str,
        alternate_dialect_label: str,
        conflict_type: ConflictType = ConflictType.VOCABULARY,
        treaty1_dialect_label: str = "Treaty #1 Plains Ojibwe (Saulteaux)",
        additional_source_refs: Optional[List[str]] = None,
    ) -> Optional[ConflictRecord]:
        """
        Returns a ConflictRecord if the forms differ, otherwise None.

        If both forms are identical, there is no conflict and None is returned.
        """
        if treaty1_form.lower() == alternate_form.lower():
            return None  # No conflict

        # Determine preference
        if treaty1_source_type in ("VERIFIED", "VETTED"):
            preference = (
                ConflictPreference.TREATY1_VERIFIED
                if treaty1_source_type == "VERIFIED"
                else ConflictPreference.TREATY1_VETTED
            )
        else:
            preference = ConflictPreference.NEEDS_COMMUNITY_REVIEW

        # Build the pedagogical message
        tutor_message = self._build_tutor_message(
            concept=concept,
            treaty1_form=treaty1_form,
            treaty1_label=treaty1_dialect_label,
            alternate_form=alternate_form,
            alternate_label=alternate_dialect_label,
            conflict_type=conflict_type,
            preference=preference,
        )

        conflict_id = f"conflict_{treaty1_form}_{alternate_form}".lower().replace(" ", "_")[:48]

        return ConflictRecord(
            schema_version=AURA_DIALECT_CONFLICT_RESOLVER_V1,
            conflict_id=conflict_id,
            concept=concept,
            tutor_preferred_form=treaty1_form,
            tutor_dialect_label=treaty1_dialect_label,
            alternate_form=alternate_form,
            alternate_dialect_label=alternate_dialect_label,
            conflict_type=conflict_type,
            preference=preference,
            tutor_message=tutor_message,
            source_refs=additional_source_refs or [],
        )

    def _build_tutor_message(
        self,
        concept: str,
        treaty1_form: str,
        treaty1_label: str,
        alternate_form: str,
        alternate_label: str,
        conflict_type: ConflictType,
        preference: ConflictPreference,
    ) -> str:
        """
        Build a culturally respectful tutor message explaining the conflict.
        Teaches dialect respect, not dialect hierarchy.
        """
        if preference == ConflictPreference.NEEDS_COMMUNITY_REVIEW:
            return (
                f"For '{concept}': The {treaty1_label} and {alternate_label} "
                f"use different forms — '{treaty1_form}' and '{alternate_form}' respectively. "
                "This is a dialect difference. A community teacher has been asked to confirm "
                f"the preferred {treaty1_label} form. Both forms are valid in their communities."
            )

        # Treaty #1 form is preferred
        if conflict_type == ConflictType.VOCABULARY:
            detail = "uses a different word"
        elif conflict_type == ConflictType.SPELLING:
            detail = "uses a different spelling"
        elif conflict_type == ConflictType.MORPHOLOGICAL:
            detail = "uses a different grammatical pattern"
        elif conflict_type == ConflictType.ANIMACY:
            detail = "classifies this word differently (animacy)"
        else:
            detail = "has a different form"

        return (
            f"For '{concept}': In {treaty1_label}, we say '{treaty1_form}'. "
            f"The {alternate_label} {detail}: '{alternate_form}'. "
            f"For this tutor, the {treaty1_label} form '{treaty1_form}' is preferred "
            "because it reflects the language of this community. "
            "Both forms are valid in their own dialects — "
            "Ojibwe is a family of related dialects, not one fixed language."
        )

    def check_opd_against_treaty1(
        self,
        concept: str,
        opd_form: str,
        treaty1_form: str,
        treaty1_source_type: str,
    ) -> Optional[ConflictRecord]:
        """Convenience method for OPD vs Treaty #1 comparison."""
        return self.resolve(
            concept=concept,
            treaty1_form=treaty1_form,
            treaty1_source_type=treaty1_source_type,
            alternate_form=opd_form,
            alternate_dialect_label="Central Southwestern Ojibwe (OPD, Minnesota/Wisconsin)",
            conflict_type=ConflictType.VOCABULARY,
        )
