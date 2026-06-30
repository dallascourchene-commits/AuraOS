"""
Aura Ojibwe Dialect Profile
==============================
Schema version: AURA_DIALECT_PROFILE_V1

Defines the canonical dialect profile for Treaty #1 / Plains Ojibwe
(Saulteaux) that all Aura language modules use as their primary reference.

Key principle:
  The tutor targets Plains Ojibwe as spoken in Treaty #1 territory
  (southern Manitoba, Red River Settlement area). The Ojibwe People's
  Dictionary is Central Southwestern (Minnesota/Wisconsin) and is a
  CROSS_REFERENCE only — dialect differences must be surfaced, not hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

AURA_DIALECT_PROFILE_V1 = "AURA_DIALECT_PROFILE_V1"


@dataclass(frozen=True)
class OrthographyConvention:
    """Describes the spelling system used by this dialect profile."""
    name: str                          # e.g. "Double Vowel" or "Fiero"
    description: str
    long_vowel_marker: str             # e.g. "aa / ii / oo / e" or macron
    nasal_marker: Optional[str] = None # e.g. "nh" or None
    notes: Optional[str] = None


@dataclass(frozen=True)
class DialectProfile:
    """
    A fully specified dialect context for language learning modules.

    Every tutor session must bind to a DialectProfile before any morphology
    parse or translation guard can proceed.  The profile is immutable;
    learner sessions may not mutate it.
    """
    schema_version: str
    dialect_id: str
    dialect_name: str
    alternate_names: tuple[str, ...]
    geographic_scope: str
    primary_source_ids: tuple[str, ...]   # LanguageSourceRegistry IDs (VERIFIED/VETTED)
    cross_reference_source_ids: tuple[str, ...]  # e.g. OPD
    orthography: OrthographyConvention

    # Animacy classes relevant to this dialect
    animacy_classes: tuple[str, ...]      # ("animate", "inanimate")

    # High-level phoneme inventory notes (not a full phonological spec)
    vowels_short: tuple[str, ...]
    vowels_long: tuple[str, ...]
    consonant_notes: str

    # Morphological framing used when bridging to Aura FST
    verb_classes: tuple[str, ...]         # ("VAI", "VTA", "VTI", "VII")
    noun_classes: tuple[str, ...]         # ("NA", "NI")

    # Source hierarchy description for user-visible messages
    source_hierarchy_description: str

    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schema_version != AURA_DIALECT_PROFILE_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_DIALECT_PROFILE_V1}"
            )


# ---------------------------------------------------------------------------
# Canonical Treaty #1 / Plains Ojibwe profile
# ---------------------------------------------------------------------------

TREATY1_PLAINS_OJIBWE = DialectProfile(
    schema_version=AURA_DIALECT_PROFILE_V1,
    dialect_id="Treaty1_Plains_Ojibwe",
    dialect_name="Treaty #1 Plains Ojibwe (Saulteaux / Anishinaabemowin)",
    alternate_names=(
        "Plains Ojibwe",
        "Saulteaux",
        "Western Ojibwe",
        "Anishinaabemowin (Treaty #1 territory)",
    ),
    geographic_scope=(
        "Southern Manitoba, Red River Settlement area, Treaty #1 territory. "
        "Communities including Brokenhead Ojibway Nation, Long Plain First Nation, "
        "Roseau River Anishinabe First Nation, Sandy Bay First Nation, "
        "Swan Lake First Nation."
    ),
    primary_source_ids=(
        "treaty1_community_verified",   # placeholder — registered by community program
    ),
    cross_reference_source_ids=(
        "opd_main",                     # OPD: Central Southwestern — cross-reference only
    ),
    orthography=OrthographyConvention(
        name="Double Vowel (Fiero-style)",
        description=(
            "Long vowels written as doubled letters: aa, ii, oo. "
            "Short vowels: a, i, o, e. "
            "Glottal stop: ' (apostrophe). "
            "Nasal final: nh or n at end of some words."
        ),
        long_vowel_marker="doubled (aa / ii / oo / e)",
        nasal_marker="nh",
        notes=(
            "Plains Ojibwe orthography varies across community materials. "
            "Aura normalizes to double-vowel standard before FST parsing, "
            "preserving original form in raw_input field."
        ),
    ),
    animacy_classes=("animate", "inanimate"),
    vowels_short=("a", "i", "o", "e"),
    vowels_long=("aa", "ii", "oo"),
    consonant_notes=(
        "Plains Ojibwe has initial change morphology. "
        "Common consonants: b, d, g, j, k, m, n, p, s, sh, t, w, y, z, zh. "
        "Geminate consonants: bb, gg, kk, ss, tt, zz."
    ),
    verb_classes=("VAI", "VTA", "VTI", "VII"),
    noun_classes=("NA", "NI"),
    source_hierarchy_description=(
        "1. Treaty #1 community teacher / fluent speaker (VERIFIED)\n"
        "2. Plains Ojibwe / Saulteaux reviewed materials (VETTED)\n"
        "3. Aura morphological FST parse (FST_GROUNDED)\n"
        "4. OPD cross-reference — Central Southwestern Ojibwe (CROSS_REFERENCE)\n"
        "5. External LLM explanation only — never translation authority (LLM_EXPLANATION)"
    ),
    notes=(
        "Plains Ojibwe (Saulteaux) differs from Central Southwestern Ojibwe "
        "(the dialect documented in the OPD) in vocabulary, some phonology, "
        "and certain grammatical constructions. "
        "Differences must be surfaced, not hidden. "
        "The tutor prefers Treaty #1 verified forms over OPD forms when conflicts arise."
    ),
)
