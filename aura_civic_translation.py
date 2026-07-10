"""Aura Civic Translation — verified translation with cultural provenance.

Never invent translations. Cultural-language labels appear only when verified.
Truth classes: VERIFIED_TRANSLATION, COMMUNITY_APPROVED_TRANSLATION, DRAFT_TRANSLATION, MACHINE_TRANSLATION, UNAVAILABLE
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

TRANSLATION_TRUTH_CLASSES = ("VERIFIED_TRANSLATION","COMMUNITY_APPROVED_TRANSLATION","DRAFT_TRANSLATION","MACHINE_TRANSLATION","UNAVAILABLE")

@dataclass
class TranslationRecord:
    concept_id: str
    source_language: str
    target_language: str
    source_text: str
    translated_text: str
    authority_class: str = "UNAVAILABLE"
    translator_or_source_ref: str = ""
    dialect_or_variety: str = ""
    approved_for_public_display: bool = False
    notes: str = ""
    def to_dict(self): return asdict(self)

def validate_translation(t: TranslationRecord) -> dict[str, Any]:
    if t.authority_class not in TRANSLATION_TRUTH_CLASSES:
        return {"ok": False, "error": "invalid translation truth class"}
    if t.authority_class == "UNAVAILABLE" and t.translated_text:
        return {"ok": False, "error": "cannot display unverified translation as if verified"}
    return {"ok": True, "translation": t.to_dict()}

def reject_invented_translation(target_language: str, text: str) -> dict[str, Any]:
    """Reject any invented translation."""
    return {"ok": False, "error": f"invented_{target_language}_translation_rejected",
            "rejected_text": text,
            "note": "Never invent Anishinaabemowin, Michif, French, Dene, Navajo, or any translation."}
