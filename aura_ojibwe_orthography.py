"""
Aura Ojibwe Orthography Normalizer
=====================================
Schema version: AURA_OJIBWE_ORTHOGRAPHY_V1

Ojibwe orthography varies significantly across communities, teachers,
and historical materials.  Before any FST parse or lexicon lookup,
raw input must be normalized to the canonical form for this dialect profile
while preserving the original form for audit and dialect note generation.

Supported normalization rules (double-vowel / Fiero-style):
  - Long vowel variants:  â → aa, î → ii, ô → oo, macrons → doubled
  - Syllabics → Romanized (minimal subset for demo)
  - Apostrophe variants:  ʼ ʻ ` → '
  - Whitespace normalization
  - Lowercase folding (Ojibwe is not case-sensitive in double-vowel)

Output includes:
  - normalized_form: canonical form for lookup and parsing
  - variant_candidates: other plausible forms tried
  - raw_input: original, unmodified
  - dialect_notes: explanation of transformations applied
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

AURA_OJIBWE_ORTHOGRAPHY_V1 = "AURA_OJIBWE_ORTHOGRAPHY_V1"


@dataclass
class NormalizationResult:
    """Output of the orthography normalizer."""
    schema_version: str
    raw_input: str
    normalized_form: str
    variant_candidates: List[str]
    transformations_applied: List[str]
    dialect_notes: Optional[str]


# ---------------------------------------------------------------------------
# Substitution tables
# ---------------------------------------------------------------------------

# Long vowel macron / acute / circumflex → double-vowel
_LONG_VOWEL_MAP = {
    "â": "aa", "Â": "aa",
    "î": "ii", "Î": "ii",
    "ô": "oo", "Ô": "oo",
    "ā": "aa", "Ā": "aa",
    "ī": "ii", "Ī": "ii",
    "ō": "oo", "Ō": "oo",
    "á": "aa", "Á": "aa",
    "í": "ii", "Í": "ii",
    "ó": "oo", "Ó": "oo",
    "é": "e",  "É": "e",   # Ojibwe 'e' is already long; no doubling needed
}

# Apostrophe/glottal variants → standard apostrophe
_APOSTROPHE_MAP = {
    "\u02bc": "'",  # Modifier letter apostrophe ʼ
    "\u02bb": "'",  # Modifier letter turned comma ʻ
    "\u2018": "'",  # Left single quotation mark '
    "\u2019": "'",  # Right single quotation mark '
    "`": "'",
    "\u0060": "'",
}

# Minimal Ojibwe syllabics → Romanized mapping (common characters only)
# Full syllabics support would require a complete conversion table.
# This covers the most common characters seen in Plains Ojibwe materials.
_SYLLABICS_MAP = {
    "ᐁ": "e",   "ᐃ": "i",   "ᐅ": "o",   "ᐊ": "a",
    "ᐯ": "pe",  "ᐱ": "pi",  "ᐳ": "po",  "ᐸ": "pa",
    "ᑌ": "te",  "ᑎ": "ti",  "ᑐ": "to",  "ᑕ": "ta",
    "ᑫ": "ke",  "ᑭ": "ki",  "ᑯ": "ko",  "ᑲ": "ka",
    "ᒉ": "che", "ᒋ": "chi", "ᒍ": "cho", "ᒐ": "cha",
    "ᒣ": "me",  "ᒥ": "mi",  "ᒧ": "mo",  "ᒪ": "ma",
    "ᓀ": "ne",  "ᓂ": "ni",  "ᓄ": "no",  "ᓇ": "na",
    "ᓭ": "se",  "ᓯ": "si",  "ᓱ": "so",  "ᓴ": "sa",
    "ᔦ": "ye",  "ᔨ": "yi",  "ᔪ": "yo",  "ᔭ": "ya",
    "ᕓ": "ve",  "ᕕ": "vi",  "ᕗ": "vo",  "ᕙ": "va",
    "ᐤ": "w",   "ᐣ": "n",   "ᑊ": "p",   "ᑦ": "t",
    "ᒃ": "k",   "ᒡ": "j",   "ᒻ": "m",   "ᔅ": "s",
    "ᓴ": "sa",
}


# ---------------------------------------------------------------------------
# Normalizer
# ---------------------------------------------------------------------------

class OjibweOrthographyNormalizer:
    """
    Normalizes raw Ojibwe input to canonical double-vowel form.

    Preserves the original in NormalizationResult.raw_input.
    Generates plausible variant candidates for fuzzy lookup.
    """

    def normalize(self, raw_input: str) -> NormalizationResult:
        """
        Normalize raw_input to canonical double-vowel Romanized form.

        Steps (applied in order):
          1. Syllabics conversion
          2. Unicode NFC normalization
          3. Apostrophe normalization
          4. Long vowel diacritics → double vowel
          5. Lowercase folding
          6. Whitespace normalization
        """
        transformations: List[str] = []
        text = raw_input

        # 1. Syllabics
        text, t = self._apply_syllabics(text)
        if t:
            transformations.extend(t)

        # 2. Unicode NFC
        nfc = unicodedata.normalize("NFC", text)
        if nfc != text:
            transformations.append("unicode_NFC_normalization")
            text = nfc

        # 3. Apostrophes
        text, t = self._apply_map(text, _APOSTROPHE_MAP)
        if t:
            transformations.append("apostrophe_normalization")

        # 4. Long vowel diacritics
        text, t = self._apply_map(text, _LONG_VOWEL_MAP)
        if t:
            transformations.append(f"long_vowel_diacritics_to_double_vowel: {', '.join(t)}")

        # 5. Lowercase
        lower = text.lower()
        if lower != text:
            transformations.append("lowercase_folding")
            text = lower

        # 6. Whitespace
        clean = re.sub(r"\s+", " ", text).strip()
        if clean != text:
            transformations.append("whitespace_normalization")
            text = clean

        # Variant candidates
        variants = self._generate_variants(text)

        # Dialect notes
        notes = self._build_notes(raw_input, text, transformations)

        return NormalizationResult(
            schema_version=AURA_OJIBWE_ORTHOGRAPHY_V1,
            raw_input=raw_input,
            normalized_form=text,
            variant_candidates=variants,
            transformations_applied=transformations,
            dialect_notes=notes,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_syllabics(self, text: str) -> tuple[str, list[str]]:
        """Convert syllabic characters to Romanized form."""
        changes = []
        for syl, roman in _SYLLABICS_MAP.items():
            if syl in text:
                text = text.replace(syl, roman)
                changes.append(f"syllabics_{syl}→{roman}")
        return text, changes

    def _apply_map(self, text: str, mapping: dict) -> tuple[str, list[str]]:
        """Apply a character substitution mapping."""
        changes = []
        for src, dst in mapping.items():
            if src in text:
                text = text.replace(src, dst)
                changes.append(f"{src}→{dst}")
        return text, changes

    def _generate_variants(self, normalized: str) -> List[str]:
        """
        Generate plausible variant spellings for fuzzy lookup fallback.
        Covers common spelling variations in community materials.
        """
        variants: List[str] = []

        # Variant 1: single apostrophe → no apostrophe (some older texts omit it)
        no_apos = normalized.replace("'", "")
        if no_apos != normalized:
            variants.append(no_apos)

        # Variant 2: double vowel → single vowel (older or informal spelling)
        single_v = re.sub(r"(aa|ii|oo)", lambda m: m.group(0)[0], normalized)
        if single_v != normalized:
            variants.append(single_v)

        # Variant 3: 'zh' ↔ 'j' (regional variation)
        zh_to_j = normalized.replace("zh", "j")
        if zh_to_j != normalized:
            variants.append(zh_to_j)

        # Variant 4: final 'w' elision (some speakers drop final w)
        if normalized.endswith("w"):
            variants.append(normalized[:-1])

        return list(dict.fromkeys(variants))  # dedup, preserve order

    def _build_notes(
        self,
        raw_input: str,
        normalized: str,
        transformations: List[str],
    ) -> Optional[str]:
        if not transformations or raw_input == normalized:
            return None
        return (
            f"Input '{raw_input}' was normalized to '{normalized}'. "
            f"Transformations applied: {'; '.join(transformations)}. "
            "Original form preserved in raw_input."
        )
