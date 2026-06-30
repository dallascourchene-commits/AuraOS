"""
Aura Ojibwe Pronunciation Bridge
===================================
Schema version: AURA_PRONUNCIATION_BRIDGE_V1

Provides pronunciation coaching for Plains Ojibwe learners using
phonetic text hints and (where permitted) audio references.

MVP audio level support:
  LEVEL_0 — Phonetic text hints only (always available)
  LEVEL_1 — Public audio reference link (if registered)
  LEVEL_2+ — Not active in MVP (requires AudioConsentRegistry entry)

Never:
  - Generates synthetic speech without community-approved TTS dataset
  - Accesses audio without AudioConsentRegistry approval
  - Claims pronunciation accuracy beyond the phonetic hint level

Phonetic guide is based on double-vowel Fiero orthography conventions
for Plains Ojibwe (Treaty #1 / Saulteaux).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aura_ojibwe_audio_consent_registry import AudioConsentRegistry, AudioLevel

AURA_PRONUNCIATION_BRIDGE_V1 = "AURA_PRONUNCIATION_BRIDGE_V1"


# ---------------------------------------------------------------------------
# Phonetic hint tables (double-vowel Romanization for Plains Ojibwe)
# ---------------------------------------------------------------------------

# Short vowels
_SHORT_VOWEL_GUIDE = {
    "a": "as in 'cup' (short, central)",
    "i": "as in 'bit' (short, front)",
    "o": "as in 'book' (short, back)",
    "e": "as in 'bet' (always long in Ojibwe; marks a distinct vowel quality)",
}

# Long vowels (double-vowel spelling)
_LONG_VOWEL_GUIDE = {
    "aa": "as in 'father' — long, held longer than 'a'",
    "ii": "as in 'see' — long, held longer than 'i'",
    "oo": "as in 'boat' — long, held longer than 'o'",
}

# Common consonant notes
_CONSONANT_GUIDE = {
    "zh": "as in 'measure' or 'vision'",
    "sh": "as in 'shoe'",
    "ch": "as in 'church'",
    "j":  "as in 'judge' (Ojibwe 'j' is like English 'j' or 'dzh')",
    "'":  "glottal stop — a brief catch in the throat (like the break in 'uh-oh')",
    "nh": "nasal final — 'n' with a slight nasal release at the end of the word",
    "bb, gg, kk, ss, tt": "geminate (double) consonants — held slightly longer",
}


@dataclass
class PronunciationHint:
    """Pronunciation guidance for a single word."""
    schema_version: str
    word: str
    phonetic_breakdown: str        # Syllable-by-syllable phonetic description
    vowel_notes: list[str]         # Relevant vowel guidance for this word's vowels
    consonant_notes: list[str]     # Relevant consonant guidance
    audio_level: AudioLevel
    audio_url: Optional[str]       # Only set if LEVEL_1 and registered
    audio_source: Optional[str]
    mvp_note: str


class OjibwePronunciationBridge:
    """
    Provides pronunciation hints and (where permitted) audio references.

    Args:
        audio_registry: AudioConsentRegistry instance for audio access checks.
    """

    def __init__(self, audio_registry: Optional[AudioConsentRegistry] = None) -> None:
        self._audio_registry = audio_registry or AudioConsentRegistry()

    def get_hint(self, word: str, audio_ref: Optional[str] = None) -> PronunciationHint:
        """
        Return a pronunciation hint for the given word.

        If audio_ref is provided and the AudioConsentRegistry permits access,
        the hint will include the audio URL.  Otherwise, phonetic text only.
        """
        phonetic = self._build_phonetic_breakdown(word)
        vowel_notes = self._extract_vowel_notes(word)
        consonant_notes = self._extract_consonant_notes(word)

        # Check audio
        audio_level = AudioLevel.LEVEL_0_TEXT_ONLY
        audio_url = None
        audio_source = None

        if audio_ref:
            decision = self._audio_registry.check_access(audio_ref)
            if decision.allowed and decision.audio_level is not None:
                audio_level = decision.audio_level
                audio_url = decision.url
                record = self._audio_registry._records.get(audio_ref)
                audio_source = record.source_name if record else None

        mvp_note = (
            "MVP: Pronunciation coaching uses phonetic text (Level 0)"
            + (
                " and a public audio reference link (Level 1)."
                if audio_level == AudioLevel.LEVEL_1_PUBLIC_LINK
                else ". No audio available for this entry."
            )
            + " For teacher-recorded audio (Level 2+), contact the community program."
        )

        return PronunciationHint(
            schema_version=AURA_PRONUNCIATION_BRIDGE_V1,
            word=word,
            phonetic_breakdown=phonetic,
            vowel_notes=vowel_notes,
            consonant_notes=consonant_notes,
            audio_level=audio_level,
            audio_url=audio_url,
            audio_source=audio_source,
            mvp_note=mvp_note,
        )

    # ------------------------------------------------------------------
    # Phonetic analysis helpers
    # ------------------------------------------------------------------

    def _build_phonetic_breakdown(self, word: str) -> str:
        """
        Produce a simple phonetic breakdown by identifying syllable boundaries.
        For Plains Ojibwe double-vowel spelling, the pattern is largely:
          (C)(C)V(C) — consonant cluster + vowel nucleus + optional coda
        """
        # Mark long vowels first
        annotated = word
        for lv in ("aa", "ii", "oo"):
            annotated = annotated.replace(lv, f"[{lv}:long]")

        # Mark glottal stop
        annotated = annotated.replace("'", "[']:glottal]")

        return f"Phonetic reading of '{word}': {annotated}"

    def _extract_vowel_notes(self, word: str) -> list[str]:
        notes = []
        w = word.lower()
        for long_v, guide in _LONG_VOWEL_GUIDE.items():
            if long_v in w:
                notes.append(f"'{long_v}' — {guide}")
        for short_v, guide in _SHORT_VOWEL_GUIDE.items():
            # Only add short vowel note if long version not already present
            pattern = short_v + short_v
            if short_v in w and pattern not in w:
                notes.append(f"'{short_v}' — {guide}")
        return list(dict.fromkeys(notes))  # dedup

    def _extract_consonant_notes(self, word: str) -> list[str]:
        notes = []
        w = word.lower()
        for consonant, guide in _CONSONANT_GUIDE.items():
            # Check for single characters
            if len(consonant) <= 2 and consonant in w:
                notes.append(f"'{consonant}' — {guide}")
        return list(dict.fromkeys(notes))
