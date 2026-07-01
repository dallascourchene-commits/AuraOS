"""
Aura Ojibwe Lexicon Sidecar
==============================
Schema version: AURA_OJIBWE_LEXICON_SIDECAR_V1

Local, queryable dictionary of vetted Plains Ojibwe / Treaty #1 lexical entries.
Each LexiconEntry is immutable and carries full provenance: source, permission,
access level, and audio reference.

Key principle:
  LexiconEntry records are the source of truth.
  Learner profiles and QDKT scores MUST NOT mutate entries.
  The lexicon grows only through registered community review.

Seed vocabulary:
  Common greetings, kinship terms, land/water words, and numbers.
  These are minimal manually-entered examples, not bulk OPD copies.
  Every entry carries a source_ref and access_level.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aura_language_data_governance import DataAccessLevel
from aura_language_source_registry import SourceType

AURA_OJIBWE_LEXICON_SIDECAR_V1 = "AURA_OJIBWE_LEXICON_SIDECAR_V1"


@dataclass(frozen=True)
class LexiconEntry:
    """
    A single lexical record in the Aura Ojibwe sidecar.

    All fields are immutable.  No learner action may modify a LexiconEntry.
    New entries may only be added by the community review pipeline.
    """
    schema_version: str
    word: str                              # Surface form (normalized, double-vowel)
    stem: str                              # Base stem
    part_of_speech: str                    # "NA", "NI", "VAI", "VTA", "VTI", "VII", "ADV", "PRT"
    animacy_class: str                     # "animate" | "inanimate" | "N/A"
    dialect_tags: tuple[str, ...]          # e.g. ("Treaty1", "Plains_Ojibwe")
    gloss_en: str                          # English gloss (minimal, not a full translation)
    example_phrase: Optional[str]          # Example phrase in Ojibwe
    example_gloss: Optional[str]           # Gloss of the example phrase
    source_ref: str                        # LanguageSourceRegistry source_id
    source_type: str                       # SourceType value string
    permission_ref: str                    # Consent record or license identifier
    access_level: DataAccessLevel
    audio_ref: Optional[str] = None        # AudioConsentRegistry audio_id (if any)
    opd_url: Optional[str] = None          # OPD cross-reference URL (if applicable)
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schema_version != AURA_OJIBWE_LEXICON_SIDECAR_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_OJIBWE_LEXICON_SIDECAR_V1}"
            )
        if not self.permission_ref:
            raise ValueError(f"LexiconEntry {self.word!r} requires a non-empty permission_ref")


# ---------------------------------------------------------------------------
# Seed vocabulary
# ---------------------------------------------------------------------------
# These entries are minimal manually-entered examples.
# source_ref "treaty1_community_verified" is a placeholder for a real
# community consent record. In production, replace with the actual record ID.

def _make_entry(**kw) -> LexiconEntry:
    return LexiconEntry(schema_version=AURA_OJIBWE_LEXICON_SIDECAR_V1, **kw)


_SEED_ENTRIES: list[LexiconEntry] = [
    # ---- Greetings --------------------------------------------------------
    _make_entry(
        word="boozhoo",
        stem="boozhoo",
        part_of_speech="PRT",
        animacy_class="N/A",
        dialect_tags=("Treaty1", "Plains_Ojibwe", "Anishinaabe"),
        gloss_en="Hello / Greetings",
        example_phrase="Boozhoo, aaniin ezhinikaazoyaan.",
        example_gloss="Hello, what is your name?",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
        notes="Pan-Anishinaabe greeting. Widely used across dialects.",
    ),
    _make_entry(
        word="aaniin",
        stem="aaniin",
        part_of_speech="PRT",
        animacy_class="N/A",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="Hello / How are you",
        example_phrase="Aaniin, ambe omaa.",
        example_gloss="Hello, come here.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="miigwech",
        stem="miigwech",
        part_of_speech="PRT",
        animacy_class="N/A",
        dialect_tags=("Treaty1", "Plains_Ojibwe", "Anishinaabe"),
        gloss_en="Thank you",
        example_phrase="Miigwech, gichi-miigwech.",
        example_gloss="Thank you, thank you very much.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="gaawin",
        stem="gaawin",
        part_of_speech="ADV",
        animacy_class="N/A",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="No / Not",
        example_phrase="Gaawin ningikendanziin.",
        example_gloss="I don't know.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    # ---- Kinship ----------------------------------------------------------
    _make_entry(
        word="nimishoomis",
        stem="mishoomis",
        part_of_speech="NA",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="My grandfather",
        example_phrase="Nimishoomis ogii-tibaajimotaw.",
        example_gloss="My grandfather told us a story.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="nookomis",
        stem="ookomis",
        part_of_speech="NA",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="My grandmother",
        example_phrase="Nookomis ogii-miizhid asemaan.",
        example_gloss="My grandmother gave me tobacco.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="nimaamaaa",
        stem="omaamaaa",
        part_of_speech="NA",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="My mother",
        example_phrase=None,
        example_gloss=None,
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="nindede",
        stem="odede",
        part_of_speech="NA",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="My father",
        example_phrase=None,
        example_gloss=None,
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    # ---- Land / Water / Territory -----------------------------------------
    _make_entry(
        word="aki",
        stem="aki",
        part_of_speech="NI",
        animacy_class="inanimate",
        dialect_tags=("Treaty1", "Plains_Ojibwe", "Anishinaabe"),
        gloss_en="Earth / Land / Ground / Soil",
        example_phrase="Maampii omaa aki.",
        example_gloss="This is the land here.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
        notes="Core relational term. 'Aki' is central to Anishinaabe worldview.",
    ),
    _make_entry(
        word="zaaga'igan",
        stem="zaaga'igan",
        part_of_speech="NI",
        animacy_class="inanimate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="Lake",
        example_phrase="Animikiins zaaga'igan.",
        example_gloss="Thunderbird Lake.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="ziibi",
        stem="ziibi",
        part_of_speech="NI",
        animacy_class="inanimate",
        dialect_tags=("Treaty1", "Plains_Ojibwe", "Anishinaabe"),
        gloss_en="River",
        example_phrase=None,
        example_gloss=None,
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="ishkode",
        stem="ishkode",
        part_of_speech="NI",
        animacy_class="inanimate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="Fire",
        example_phrase=None,
        example_gloss=None,
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    # ---- Common verbs (VAI) -----------------------------------------------
    _make_entry(
        word="nibaa",
        stem="nibaa",
        part_of_speech="VAI",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="S/he sleeps",
        example_phrase="Nibaa a'aw ikwe.",
        example_gloss="That woman is sleeping.",
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
    _make_entry(
        word="miijiw",
        stem="miijii",
        part_of_speech="VAI",
        animacy_class="animate",
        dialect_tags=("Treaty1", "Plains_Ojibwe"),
        gloss_en="S/he eats",
        example_phrase=None,
        example_gloss=None,
        source_ref="treaty1_community_verified",
        source_type=SourceType.VERIFIED.value,
        permission_ref="community_consent_placeholder_001",
        access_level=DataAccessLevel.PUBLIC,
    ),
]


# ---------------------------------------------------------------------------
# Sidecar dictionary
# ---------------------------------------------------------------------------

class OjibweLexiconSidecar:
    """
    In-memory queryable dictionary of vetted Treaty #1 / Plains Ojibwe entries.

    Thread-safety: not guaranteed; single-session use only.
    Entries are immutable.  Learner progress is tracked separately.
    """

    def __init__(self) -> None:
        self._by_word: Dict[str, LexiconEntry] = {}
        self._by_stem: Dict[str, List[LexiconEntry]] = {}
        for entry in _SEED_ENTRIES:
            self._add(entry)

    def _add(self, entry: LexiconEntry) -> None:
        self._by_word[entry.word] = entry
        self._by_stem.setdefault(entry.stem, []).append(entry)

    def add_community_entry(self, entry: LexiconEntry) -> None:
        """
        Add a new entry from the community review pipeline.
        Only entries with VERIFIED or VETTED source_type are accepted.
        """
        if entry.source_type not in (SourceType.VERIFIED.value, SourceType.VETTED.value):
            raise ValueError(
                f"Only VERIFIED or VETTED entries may be added to the sidecar. "
                f"Got source_type={entry.source_type!r} for word={entry.word!r}."
            )
        self._add(entry)

    def lookup(self, word: str) -> Optional[LexiconEntry]:
        """Return the entry for an exact (normalized) word form, or None."""
        return self._by_word.get(word)

    def lookup_stem(self, stem: str) -> List[LexiconEntry]:
        """Return all entries sharing a stem."""
        return list(self._by_stem.get(stem, []))

    def search(
        self,
        gloss_fragment: str,
        max_results: int = 10,
    ) -> List[LexiconEntry]:
        """Simple substring search on the English gloss."""
        frag = gloss_fragment.lower()
        results = [
            e for e in self._by_word.values()
            if frag in e.gloss_en.lower()
        ]
        return results[:max_results]

    def by_dialect(self, dialect_tag: str) -> List[LexiconEntry]:
        return [e for e in self._by_word.values() if dialect_tag in e.dialect_tags]

    def by_pos(self, part_of_speech: str) -> List[LexiconEntry]:
        return [e for e in self._by_word.values() if e.part_of_speech == part_of_speech]

    def all_words(self) -> List[str]:
        return list(self._by_word.keys())

    def entry_count(self) -> int:
        return len(self._by_word)
