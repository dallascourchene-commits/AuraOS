"""
Aura Ojibwe Morphology Bridge
================================
Schema version: AURA_OJIBWE_MORPH_BRIDGE_V1

Wraps the OjibweMorph FST (ELF-Lab, UBC) for real morphological analysis
and generation of Ojibwe words, with graceful fallback when the FST is
unavailable.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Acknowledgement — OjibweMorph (ELF-Lab, University of British Columbia)
  ─────────────────────────────────────────────────────────────────────
  The morphological parser in this module is powered by OjibweMorph, an
  open, collaborative project to build a finite-state transducer for the
  Ojibwe language. We are grateful to the team for making this resource
  freely available to the community.

  Citation:
    Hammerly, C., Livesay, N., Arppe, A., Stacey, A., & Silfverberg, M.
    (2026). "OjibweMorph: An approachable finite-state transducer for
    Ojibwe (and beyond)." ELF-Lab, University of British Columbia.
    https://github.com/ELF-Lab/OjibweMorph

  License: CC BY-NC-SA 4.0
    Non-commercial use, attribution required, share-alike.
    This Aura module is non-commercial and open-source.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dialect caveat:
  OjibweMorph is primarily validated against Central Southwestern Ojibwe
  (OPD / Minnesota-Wisconsin fieldwork). Plains Ojibwe / Treaty #1 shares
  core morphological structure but has dialect-level differences.
  Parses from this bridge are tagged FST_GROUNDED — not VERIFIED for
  Treaty #1. All outputs still pass through TranslationGuard Gate 3.

Six-slot mapping (Aura native ↔ OjibweMorph tags):
  DIR   → Preverb / directional prefix
  ASP   → Tense/aspect/mode tags (Ind, Conj, Pret, Dub)
  CLASS → Part-of-speech gate (VAI, VII, VTA, VTI, NA, NI, etc.)
  SUBJ  → Person/number agreement tags
  VOICE → Stem / transitivity marker
  STEM  → Final inflectional suffix
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

AURA_OJIBWE_MORPH_BRIDGE_V1 = "AURA_OJIBWE_MORPH_BRIDGE_V1"

OJIBWEMORPH_CITATION = (
    "OjibweMorph — Hammerly, C., Livesay, N., Arppe, A., Stacey, A., "
    "& Silfverberg, M. (2026). ELF-Lab, UBC. "
    "https://github.com/ELF-Lab/OjibweMorph — CC BY-NC-SA 4.0."
)


class ParseStatus(str, Enum):
    PARSED = "PARSED"                   # OjibweMorph returned ≥1 full analysis
    PARTIAL = "PARTIAL"                 # Prefix detection only (no OjibweMorph hit)
    UNRECOGNIZED = "UNRECOGNIZED"       # OjibweMorph loaded but returned no analysis
    FST_UNAVAILABLE = "FST_UNAVAILABLE" # FST not loaded (file missing or load error)


class VerbClass(str, Enum):
    VAI = "VAI"
    VTA = "VTA"
    VTI = "VTI"
    VII = "VII"
    VAIO = "VAIO"


class NounClass(str, Enum):
    NA = "NA"
    NI = "NI"
    NAD = "NAD"
    NID = "NID"


class AnimacyClass(str, Enum):
    ANIMATE = "animate"
    INANIMATE = "inanimate"
    NOT_APPLICABLE = "N/A"


# ---------------------------------------------------------------------------
# OjibweMorph tag parsing helpers
# ---------------------------------------------------------------------------

# Tags that indicate animate verb/noun classes
_ANIMATE_POS = {"VAI", "VTA", "VAIO", "NA", "NAD"}
_INANIMATE_POS = {"VII", "VTI", "NI", "NID"}

# Tense/mode tags
_TENSE_TAGS = {"Ind", "Conj", "Imp", "Pret", "Dub"}

# Person tags (OjibweMorph convention)
_PERSON_TAG_MAP = {
    "1Sg":   "1st person singular (I)",
    "2Sg":   "2nd person singular (you)",
    "3Sg":   "3rd person singular (s/he)",
    "1Pl":   "1st person plural exclusive (we, not you)",
    "21":    "1st person plural inclusive (we, including you)",
    "2Pl":   "2nd person plural (you all)",
    "3Pl":   "3rd person plural (they)",
    "3Sg/Pl":"3rd person singular or plural",
    "Obv":   "obviative (the other one)",
}

# Preverb prefix surface forms
_PERSON_PREFIXES: Dict[str, str] = {
    "ni": "1SG (ni- / n-)",
    "gi": "2SG (gi- / g-)",
    "o":  "3SG (o- / w-)",
    "n":  "1SG short form",
    "g":  "2SG short form",
    "w":  "3SG short form (before vowels)",
}


def _parse_ojibwemorph_analysis(analysis: str) -> dict:
    """
    Parse an OjibweMorph analysis string like:
      "nibaa+VAI+Ind+Pos+Neu+1Sg"
    into a structured dict.
    """
    parts = analysis.split("+")
    lemma = parts[0] if parts else ""
    tags = parts[1:] if len(parts) > 1 else []

    pos = None
    tense = None
    person_tags = []
    other_tags = []

    for tag in tags:
        if tag in {v.value for v in VerbClass} | {n.value for n in NounClass}:
            pos = tag
        elif tag in _TENSE_TAGS:
            tense = tag
        elif tag in _PERSON_TAG_MAP:
            person_tags.append(tag)
        else:
            other_tags.append(tag)

    animacy = AnimacyClass.NOT_APPLICABLE
    if pos in _ANIMATE_POS:
        animacy = AnimacyClass.ANIMATE
    elif pos in _INANIMATE_POS:
        animacy = AnimacyClass.INANIMATE

    person_desc = " / ".join(_PERSON_TAG_MAP[t] for t in person_tags if t in _PERSON_TAG_MAP)

    return {
        "lemma": lemma,
        "pos": pos,
        "tense": tense,
        "person_tags": person_tags,
        "person_description": person_desc or None,
        "animacy": animacy,
        "other_tags": other_tags,
        "raw_tags": tags,
        "full_analysis": analysis,
    }


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class MorphParseResult:
    schema_version: str
    word: str
    status: ParseStatus
    stem: Optional[str]
    person_prefix: Optional[str]
    person_description: Optional[str]
    verb_class: Optional[VerbClass]
    noun_class: Optional[NounClass]
    animacy: AnimacyClass
    suffix: Optional[str]
    fst_route: Optional[List[str]]
    confidence: float
    analyses: List[str] = field(default_factory=list)   # Raw OjibweMorph analysis strings
    parsed_analysis: Optional[dict] = None              # First analysis parsed to dict
    citation: str = OJIBWEMORPH_CITATION
    notes: Optional[str] = None


@dataclass
class MorphGenerateResult:
    schema_version: str
    stem: str
    params: dict
    candidate_form: Optional[str]
    confidence: float
    status: ParseStatus
    citation: str = OJIBWEMORPH_CITATION
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class OjibweMorphBridge:
    """
    Ojibwe morphological analysis and generation via OjibweMorph FST.

    Powered by the pre-built OjibweMorph transducer (ELF-Lab, UBC).
    Falls back to deterministic prefix detection if FST is unavailable.

    FST file: ojibwemorph_fst/ojibwe.att (loaded once, cached)
    """

    def __init__(self, att_path: Optional[Path] = None) -> None:
        self._transducer = None
        self._fst_available = False
        self._load_note = ""
        self._try_load(att_path)

    def _try_load(self, att_path: Optional[Path]) -> None:
        from aura_att_fst_runtime import load_ojibwe_transducer, load_error
        t = load_ojibwe_transducer(att_path)
        if t is not None:
            self._transducer = t
            self._fst_available = True
            self._load_note = (
                f"OjibweMorph FST loaded. {OJIBWEMORPH_CITATION}"
            )
        else:
            err = load_error() or "unknown error"
            self._load_note = (
                f"OjibweMorph FST unavailable ({err}). "
                "Using deterministic prefix detection fallback."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_word(self, word: str) -> MorphParseResult:
        """
        Parse an Ojibwe word. Returns OjibweMorph analysis if FST is
        loaded, otherwise deterministic prefix stub.
        """
        if self._fst_available and self._transducer is not None:
            return self._ojibwemorph_parse(word)
        return self._stub_parse(word)

    def validate_morphology(
        self,
        stem: str,
        person: Optional[str] = None,
        animacy: Optional[str] = None,
        verb_class: Optional[str] = None,
    ) -> Tuple[bool, Optional[MorphParseResult]]:
        candidate = (person or "") + stem
        result = self.parse_word(candidate)
        valid = result.status in (ParseStatus.PARSED, ParseStatus.PARTIAL)
        return valid, result

    def generate_form(self, stem: str, params: dict) -> MorphGenerateResult:
        """Generate a candidate inflected form from stem + morphological params."""
        if not self._fst_available or self._transducer is None:
            return MorphGenerateResult(
                schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
                stem=stem,
                params=params,
                candidate_form=None,
                confidence=0.0,
                status=ParseStatus.FST_UNAVAILABLE,
                notes=self._load_note,
            )
        # Build an analysis string and run the transducer downward
        pos = params.get("verb_class", "VAI")
        tense = params.get("tense", "Ind")
        polarity = params.get("polarity", "Pos")
        mode = params.get("mode", "Neu")
        person = params.get("person", "3Sg")
        analysis = f"{stem}+{pos}+{tense}+{polarity}+{mode}+{person}"
        forms = self._transducer.generate(analysis)
        if forms:
            return MorphGenerateResult(
                schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
                stem=stem,
                params=params,
                candidate_form=forms[0],
                confidence=0.80,
                status=ParseStatus.PARSED,
                notes=f"OjibweMorph generated {len(forms)} candidate(s). Using first: {forms[0]}",
            )
        return MorphGenerateResult(
            schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
            stem=stem,
            params=params,
            candidate_form=None,
            confidence=0.0,
            status=ParseStatus.UNRECOGNIZED,
            notes=f"OjibweMorph returned no generation for: {analysis}",
        )

    def slot_sequence_for_verb(self, verb_class: VerbClass) -> List[str]:
        base = ["DIR (preverb / directional)", "ASP (tense/mode)", f"CLASS ({verb_class.value})"]
        if verb_class in (VerbClass.VTA, VerbClass.VTI, VerbClass.VAIO):
            base.append("SUBJ (object agreement)")
        base.extend(["VOICE (stem / transitivity)", "STEM (final inflectional suffix)"])
        return base

    def animacy_for_pos(self, part_of_speech: str) -> AnimacyClass:
        if part_of_speech in _ANIMATE_POS:
            return AnimacyClass.ANIMATE
        elif part_of_speech in _INANIMATE_POS:
            return AnimacyClass.INANIMATE
        return AnimacyClass.NOT_APPLICABLE

    def fst_status(self) -> dict:
        return {
            "fst_available": self._fst_available,
            "note": self._load_note,
            "citation": OJIBWEMORPH_CITATION if self._fst_available else None,
        }

    # ------------------------------------------------------------------
    # Internal: OjibweMorph FST parse
    # ------------------------------------------------------------------

    def _ojibwemorph_parse(self, word: str) -> MorphParseResult:
        analyses = self._transducer.analyse(word)
        if not analyses:
            return MorphParseResult(
                schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
                word=word,
                status=ParseStatus.UNRECOGNIZED,
                stem=word,
                person_prefix=None,
                person_description=None,
                verb_class=None,
                noun_class=None,
                animacy=AnimacyClass.NOT_APPLICABLE,
                suffix=None,
                fst_route=None,
                confidence=0.0,
                analyses=[],
                notes=(
                    f"OjibweMorph returned no analysis for '{word}'. "
                    "May be a Plains Ojibwe form not covered by the Central "
                    "Southwestern lexicon, or an unrecognized word form."
                ),
            )

        # Parse the first (best) analysis
        parsed = _parse_ojibwemorph_analysis(analyses[0])

        # Resolve class enums
        verb_class = None
        noun_class = None
        pos = parsed.get("pos")
        if pos in {v.value for v in VerbClass}:
            verb_class = VerbClass(pos)
        elif pos in {n.value for n in NounClass}:
            noun_class = NounClass(pos)

        # Build Aura six-slot route from tags
        fst_route = []
        if parsed.get("other_tags"):
            fst_route.append("DIR: " + ",".join(t for t in parsed["other_tags"] if "PV" in t or "Dir" in t) or "DIR")
        fst_route.append(f"ASP: {parsed.get('tense', '?')}")
        fst_route.append(f"CLASS: {pos or '?'}")
        if parsed.get("person_tags"):
            fst_route.append(f"SUBJ: {','.join(parsed['person_tags'])}")
        fst_route.append(f"STEM: {parsed.get('lemma', word)}")

        notes = (
            f"OjibweMorph analysis ({len(analyses)} result(s)). "
            f"Primary: {analyses[0]}. "
            "Dialect note: OjibweMorph validated on Central Southwestern Ojibwe. "
            "Plains Ojibwe / Treaty #1 forms may differ — tagged FST_GROUNDED, not VERIFIED."
        )

        return MorphParseResult(
            schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
            word=word,
            status=ParseStatus.PARSED,
            stem=parsed.get("lemma") or word,
            person_prefix=None,
            person_description=parsed.get("person_description"),
            verb_class=verb_class,
            noun_class=noun_class,
            animacy=parsed.get("animacy", AnimacyClass.NOT_APPLICABLE),
            suffix=None,
            fst_route=fst_route,
            confidence=0.85,
            analyses=analyses,
            parsed_analysis=parsed,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Internal: prefix-only stub fallback
    # ------------------------------------------------------------------

    def _stub_parse(self, word: str) -> MorphParseResult:
        person_prefix = None
        person_desc = None
        remaining = word
        for prefix, desc in _PERSON_PREFIXES.items():
            if word.startswith(prefix) and len(word) > len(prefix):
                person_prefix = prefix
                person_desc = desc
                remaining = word[len(prefix):]
                break
        return MorphParseResult(
            schema_version=AURA_OJIBWE_MORPH_BRIDGE_V1,
            word=word,
            status=ParseStatus.FST_UNAVAILABLE,
            stem=remaining or word,
            person_prefix=person_prefix,
            person_description=person_desc,
            verb_class=None,
            noun_class=None,
            animacy=AnimacyClass.NOT_APPLICABLE,
            suffix=None,
            fst_route=None,
            confidence=0.0,
            notes=self._load_note,
        )
