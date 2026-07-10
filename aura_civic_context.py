"""Aura Civic Context Lens Registry — optional context lenses.

Each lens declares applicable_profiles, authority_refs, required_evidence.
Lenses only activate under explicit profile selection.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

@dataclass
class ContextLens:
    lens_id: str
    applicable_profiles: list[str] = field(default_factory=list)
    authority_refs: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    output_schema: dict[str, Any] = field(default_factory=dict)
    advisory_status: str = "advisory"
    def to_dict(self): return asdict(self)

LENSES = {
    "accessibility": ContextLens("accessibility", advisory_status="advisory"),
    "youth_participation": ContextLens("youth_participation", advisory_status="advisory"),
    "disability_justice": ContextLens("disability_justice", advisory_status="advisory"),
    "anti_displacement": ContextLens("anti_displacement", advisory_status="advisory"),
    "climate_resilience": ContextLens("climate_resilience", advisory_status="advisory"),
    "language_access": ContextLens("language_access", advisory_status="advisory"),
    "winnipeg_treaty1": ContextLens("winnipeg_treaty1",
        applicable_profiles=["treaty1_context"],
        authority_refs=["treaty1_context"],
        advisory_status="advisory"),
    "indigenous_data_governance": ContextLens("indigenous_data_governance",
        applicable_profiles=["indigenous_data_governance"],
        authority_refs=["indigenous_data_governance"],
        advisory_status="advisory"),
}

def get_lens(lens_id: str) -> dict[str, Any]:
    l = LENSES.get(lens_id)
    if not l: return {"ok": False, "error": f"unknown lens: {lens_id}"}
    return {"ok": True, "lens": l.to_dict()}

def list_lenses() -> dict[str, Any]:
    return {"ok": True, "lenses": [l.to_dict() for l in LENSES.values()], "count": len(LENSES)}

def check_activation(lens_id: str, active_profile_refs: list[str]) -> dict[str, Any]:
    l = LENSES.get(lens_id)
    if not l: return {"ok": False, "error": "unknown lens"}
    if not l.applicable_profiles: return {"ok": True, "activated": True}
    activated = any(p in active_profile_refs for p in l.applicable_profiles)
    return {"ok": True, "activated": activated,
            "note": "Cultural/governance lenses activate only through explicit profile selection" if not activated else ""}
