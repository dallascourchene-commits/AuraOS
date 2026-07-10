"""Aura Civic Evidence — legal/policy hierarchy and applicability.

This is a retrieval/applicability graph, not automatic legal reasoning.
Aura is not providing legal advice.
"""
from __future__ import annotations
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

LEGAL_HIERARCHY = [
    "constitutional_and_indigenous_rights",
    "federal_acts_and_regulations",
    "manitoba_acts_and_regulations",
    "city_of_winnipeg_charter",
    "city_bylaws",
    "development_plans",
    "secondary_and_local_plans",
    "zoning_and_implementation",
    "permits_licences_approvals",
]

APPLICABILITY_STATUSES = (
    "DIRECTLY_APPLICABLE","POSSIBLY_APPLICABLE","INFORMATIONAL",
    "NOT_APPLICABLE","CONFLICTING_INSTRUMENTS","STALE_SOURCE",
    "INSUFFICIENT_FACTS","REQUIRES_OFFICIAL_INTERPRETATION",
)

def assess_legal_applicability(instrument: dict[str, Any], scenario_facts: dict[str, Any]) -> dict[str, Any]:
    level = instrument.get("level", "")
    if level in LEGAL_HIERARCHY:
        applicability = "POSSIBLY_APPLICABLE"
    else:
        applicability = "INFORMATIONAL"
    if not scenario_facts:
        applicability = "INSUFFICIENT_FACTS"
    return {
        "ok": True,
        "instrument": instrument,
        "applicability": applicability,
        "required_language": "Potentially applicable based on the current scenario facts. Official interpretation or approval is required.",
        "disclaimer": "Aura is not providing legal advice.",
        "prohibited_outputs": ["This project is legal.", "This use is permitted.", "The City will approve it."],
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }

def check_no_legal_approval(output: dict[str, Any]) -> dict[str, Any]:
    for key in ("legal_approval","approved","permitted","compliant"):
        if output.get(key) is True:
            return {"ok": False, "error": f"prohibited_legal_claim: {key}"}
    return {"ok": True}
