"""Aura Civic Sources — Winnipeg data-source registry."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

@dataclass
class CivicSourceDefinition:
    source_id: str
    publisher: str
    jurisdiction: str
    source_type: str
    base_uri: str = ""
    allowed_domains: list[str] = field(default_factory=list)
    retrieval_mode: str = "fixture"  # fixture, snapshot, live
    licence: str = ""
    authority_class: str = "OFFICIAL_PRIMARY_SOURCE"
    schema_hint: str = ""
    refresh_policy: str = "manual"
    privacy_policy: str = ""
    parser_version: str = "1.0"
    def to_dict(self): return asdict(self)

SOURCES = [
    CivicSourceDefinition("city_of_winnipeg_open_data","City of Winnipeg","winnipeg","open_data_portal",
        "https://data.winnipeg.ca/",["data.winnipeg.ca"],"snapshot","Open Government License - Winnipeg"),
    CivicSourceDefinition("winnipeg_bylaws","City of Winnipeg","winnipeg","bylaws",
        "https://winnipeg.ca/CLKDM/ByLaws/",["winnipeg.ca"],"snapshot","Open Government License"),
    CivicSourceDefinition("manitoba_laws","Government of Manitoba","manitoba","provincial_laws",
        "https://web2.gov.mb.ca/laws/",["web2.gov.mb.ca"],"snapshot","Open Government License - Manitoba"),
    CivicSourceDefinition("ourwinnipeg","City of Winnipeg","winnipeg","planning_policy",
        "https://winnipeg.ca/OURWINNIPEG/",["winnipeg.ca"],"snapshot","Open Government License"),
    CivicSourceDefinition("winnipeg_council_minutes","City of Winnipeg","winnipeg","council_records",
        "https://winnipeg.ca/CLKDM/",["winnipeg.ca"],"snapshot","Open Government License"),
    CivicSourceDefinition("winnipeg_open_budget","City of Winnipeg","winnipeg","budget",
        "https://winnipeg.ca/finance/",["winnipeg.ca"],"snapshot","Open Government License"),
    CivicSourceDefinition("statistics_canada","Statistics Canada","canada","federal_statistics",
        "https://www.statcan.gc.ca/",["statcan.gc.ca"],"snapshot","Statistics Canada Open License"),
    CivicSourceDefinition("justice_laws_canada","Government of Canada","canada","federal_laws",
        "https://laws-lois.justice.gc.ca/",["laws-lois.justice.gc.ca"],"snapshot","Open Government License - Canada"),
]

def list_sources() -> dict[str, Any]:
    return {"ok": True, "sources": [s.to_dict() for s in SOURCES], "count": len(SOURCES)}
def get_source(source_id: str) -> dict[str, Any]:
    for s in SOURCES:
        if s.source_id == source_id:
            return {"ok": True, "source": s.to_dict()}
    return {"ok": False, "error": f"unknown source: {source_id}"}
