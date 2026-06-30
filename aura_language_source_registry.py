"""
Aura Language Source Registry
==============================
Schema version: AURA_LANGUAGE_SOURCE_REGISTRY_V1

Stores and queries vetted sources for Indigenous language content.
Every piece of language data that Aura produces must be traceable to a
SourceRecord in this registry.  Without a SourceRecord, the TranslationGuard
will return BLOCKED.

Source hierarchy for Treaty #1 / Plains Ojibwe:
  1. VERIFIED      — Fluent speaker / community teacher confirmed
  2. VETTED        — Plains Ojibwe / Saulteaux reviewed materials
  3. FST_GROUNDED  — Aura morphological parse only
  4. CROSS_REFERENCE — OPD or external dialect comparison
  5. LLM_EXPLANATION — External model explanation (never translation truth)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

AURA_LANGUAGE_SOURCE_REGISTRY_V1 = "AURA_LANGUAGE_SOURCE_REGISTRY_V1"


class SourceType(str, Enum):
    VERIFIED = "VERIFIED"              # Community teacher / fluent speaker confirmed
    VETTED = "VETTED"                  # Plains Ojibwe / Saulteaux reviewed materials
    FST_GROUNDED = "FST_GROUNDED"      # Morphological parse, no community review yet
    CROSS_REFERENCE = "CROSS_REFERENCE"  # External dialect (e.g., OPD)
    LLM_EXPLANATION = "LLM_EXPLANATION"  # Model explanation — never translation truth


# Minimum confidence thresholds per source type (0.0–1.0)
SOURCE_CONFIDENCE_FLOOR: Dict[SourceType, float] = {
    SourceType.VERIFIED: 0.95,
    SourceType.VETTED: 0.80,
    SourceType.FST_GROUNDED: 0.60,
    SourceType.CROSS_REFERENCE: 0.40,
    SourceType.LLM_EXPLANATION: 0.10,
}


@dataclass(frozen=True)
class SourceRecord:
    """
    A single vetted source for language content.

    All language data must trace to a SourceRecord.
    Fields must be populated at construction; defaults are not allowed for
    source_id, source_name, source_type, or permission_ref.
    """

    schema_version: str
    source_id: str
    source_name: str
    source_type: SourceType
    dialect_tags: tuple[str, ...]          # e.g. ("Treaty1", "Plains_Ojibwe", "Saulteaux")
    permission_ref: str                    # e.g. "community_consent_2024_001" or "CC-BY-NC-SA-4.0"
    license: str                           # SPDX or plain description
    confidence: float                      # 0.0–1.0
    citation: str                          # Human-readable bibliographic reference
    url: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"SourceRecord confidence must be 0.0–1.0, got {self.confidence!r}"
            )
        floor = SOURCE_CONFIDENCE_FLOOR[self.source_type]
        if self.confidence < floor:
            raise ValueError(
                f"SourceRecord confidence {self.confidence} is below minimum "
                f"{floor} for source type {self.source_type}"
            )
        if not self.permission_ref:
            raise ValueError("SourceRecord requires a non-empty permission_ref")
        if self.schema_version != AURA_LANGUAGE_SOURCE_REGISTRY_V1:
            raise ValueError(
                f"Unknown schema version {self.schema_version!r}. "
                f"Expected {AURA_LANGUAGE_SOURCE_REGISTRY_V1}"
            )


class LanguageSourceRegistry:
    """
    Registry of all vetted language sources known to Aura.

    Usage:
        registry = LanguageSourceRegistry()
        registry.register(my_source_record)
        record = registry.get("opd_main")
        verified = registry.by_dialect("Treaty1", min_type=SourceType.VETTED)
    """

    def __init__(self) -> None:
        self._records: Dict[str, SourceRecord] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        """Seed minimal built-in sources. Real deployment adds community records."""
        self.register(
            SourceRecord(
                schema_version=AURA_LANGUAGE_SOURCE_REGISTRY_V1,
                source_id="opd_main",
                source_name="Ojibwe People's Dictionary",
                source_type=SourceType.CROSS_REFERENCE,
                dialect_tags=("Central_Southwestern_Ojibwe", "Minnesota", "Wisconsin"),
                permission_ref="CC-BY-NC-SA-4.0",
                license="Creative Commons Attribution-NonCommercial-ShareAlike 4.0",
                confidence=0.40,
                citation=(
                    "Nichols, J., Golla, V. et al. Ojibwe People's Dictionary. "
                    "University of Minnesota. https://ojibwe.lib.umn.edu/"
                ),
                url="https://ojibwe.lib.umn.edu/",
                notes=(
                    "Cross-reference only. Central Southwestern Ojibwe (MN/WI) differs "
                    "from Plains Ojibwe / Treaty #1. Tag as CROSS_REFERENCE, not VERIFIED."
                ),
            )
        )
        self.register(
            SourceRecord(
                schema_version=AURA_LANGUAGE_SOURCE_REGISTRY_V1,
                source_id="aura_fst_internal",
                source_name="Aura Morphological FST Parse",
                source_type=SourceType.FST_GROUNDED,
                dialect_tags=("Ojibwe", "Anishinaabemowin"),
                permission_ref="aura_internal_fst_v4",
                license="Aura Internal (not redistributable separately)",
                confidence=0.60,
                citation="Aura PWFST Master Lexicon v4.01 — aura.lexc, aura_fst_routing.py",
                notes=(
                    "FST parse provides grammatical grounding only. "
                    "Does not confer dialect authority."
                ),
            )
        )
        self.register(
            SourceRecord(
                schema_version=AURA_LANGUAGE_SOURCE_REGISTRY_V1,
                source_id="llm_explanation_bounded",
                source_name="External LLM Explanation (Bounded)",
                source_type=SourceType.LLM_EXPLANATION,
                dialect_tags=(),
                permission_ref="aura_llm_egress_policy",
                license="Aura LLM Egress Policy — explanation only",
                confidence=0.10,
                citation="Aura LLM Egress — bounded explanation, never translation authority",
                notes=(
                    "LLM output is NEVER used as translation truth. "
                    "Used only for pedagogical explanation after guard approves."
                ),
            )
        )

    def register(self, record: SourceRecord) -> None:
        """Add or replace a SourceRecord."""
        self._records[record.source_id] = record

    def get(self, source_id: str) -> Optional[SourceRecord]:
        """Return a SourceRecord by ID, or None."""
        return self._records.get(source_id)

    def require(self, source_id: str) -> SourceRecord:
        """Return a SourceRecord by ID, raising if not found."""
        rec = self.get(source_id)
        if rec is None:
            raise KeyError(f"No source registered with id={source_id!r}")
        return rec

    def by_dialect(
        self,
        dialect_tag: str,
        min_type: Optional[SourceType] = None,
    ) -> List[SourceRecord]:
        """Return all records matching a dialect tag, optionally filtered by minimum source type."""
        type_rank = list(SourceType)
        results = [
            r for r in self._records.values()
            if dialect_tag in r.dialect_tags
        ]
        if min_type is not None:
            min_rank = type_rank.index(min_type)
            results = [r for r in results if type_rank.index(r.source_type) <= min_rank]
        return results

    def all_ids(self) -> List[str]:
        return list(self._records.keys())

    def health_report(self) -> dict:
        """Safe summary — does not expose permission_refs."""
        return {
            "schema_version": AURA_LANGUAGE_SOURCE_REGISTRY_V1,
            "total_sources": len(self._records),
            "by_type": {
                st.value: sum(
                    1 for r in self._records.values() if r.source_type == st
                )
                for st in SourceType
            },
        }
