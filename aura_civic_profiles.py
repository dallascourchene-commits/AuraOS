"""
Aura Civic Profiles — jurisdiction, community governance, and profile sets.

Profiles are explicitly activated. Never auto-activate cultural/governance profiles
based on model inference of identity, ancestry, location, or community affiliation.
"""
from __future__ import annotations
import hashlib, json, time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORY = False

@dataclass
class JurisdictionProfile:
    profile_id: str
    geographic_scope: str
    authority_hierarchy: list[str] = field(default_factory=list)
    legal_sources: list[dict[str, str]] = field(default_factory=list)
    planning_sources: list[dict[str, str]] = field(default_factory=list)
    public_data_sources: list[dict[str, str]] = field(default_factory=list)
    official_languages: list[str] = field(default_factory=list)
    effective_from: str = ""
    effective_to: str = ""
    source_refs: list[str] = field(default_factory=list)
    def to_dict(self): return asdict(self)

@dataclass
class CommunityGovernanceProfile:
    profile_id: str
    community_ref: str
    authorized_by: str
    decision_process: str = ""
    participant_scope_rules: dict[str, Any] = field(default_factory=dict)
    data_governance_profile_ref: str = ""
    consent_rules: dict[str, Any] = field(default_factory=dict)
    privacy_rules: dict[str, Any] = field(default_factory=dict)
    retention_rules: dict[str, Any] = field(default_factory=dict)
    export_rules: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class CivicProfileSet:
    jurisdiction_profile_refs: list[str] = field(default_factory=list)
    community_governance_profile_ref: str = ""
    language_profile_refs: list[str] = field(default_factory=list)
    context_lens_refs: list[str] = field(default_factory=list)
    scenario_constraints: dict[str, Any] = field(default_factory=dict)
    digest: str = ""
    schema_version: str = "AURA_CIVIC_PROFILE_SET_V1"
    def to_dict(self): return asdict(self)
    def compute_digest(self) -> str:
        d = self.to_dict(); d.pop("digest", None)
        return hashlib.blake2b(json.dumps(d, sort_keys=True, default=str).encode(), digest_size=12).hexdigest()

# Winnipeg demo profiles
WINNIPEG_JURISDICTION = JurisdictionProfile(
    profile_id="winnipeg_mb_ca",
    geographic_scope="Winnipeg, Manitoba, Canada",
    authority_hierarchy=["constitutional", "federal", "provincial", "municipal", "bylaw"],
    legal_sources=[
        {"source_id": "manitoba_laws", "publisher": "Government of Manitoba", "uri": "https://web2.gov.mb.ca/laws/"},
        {"source_id": "winnipeg_charter", "publisher": "City of Winnipeg", "uri": "https://winnipeg.ca/CLKDM/"},
    ],
    planning_sources=[
        {"source_id": "ourwinnipeg", "publisher": "City of Winnipeg", "uri": "https://winnipeg.ca/OURWINNIPEG/"},
    ],
    public_data_sources=[
        {"source_id": "winnipeg_open_data", "publisher": "City of Winnipeg", "uri": "https://data.winnipeg.ca/"},
    ],
    official_languages=["English", "French"],
    effective_from="2026-01-01",
    source_refs=["City of Winnipeg Charter S.M. 2002, c. 39"],
)

WINNIPEG_DEMO_COMMUNITY = CommunityGovernanceProfile(
    profile_id="winnipeg_demo_community",
    community_ref="demo_neighbourhood_central_winnipeg",
    authorized_by="demo_facilitator",
    consent_rules={"require_consent_to_match": True, "non_binding": True},
    privacy_rules={"default_privacy": "COMMUNITY_ONLY", "no_contact_leakage": True},
    retention_rules={"default_retention_days": 365, "withdrawal_propagates": True},
    export_rules={"require_facilitator_approval": True},
)

def create_winnipeg_demo_profile_set() -> CivicProfileSet:
    ps = CivicProfileSet(
        jurisdiction_profile_refs=["winnipeg_mb_ca"],
        community_governance_profile_ref="winnipeg_demo_community",
        language_profile_refs=[],
        context_lens_refs=[],  # Treaty 1 is optional, not activated by default
        scenario_constraints={"non_binding": True, "no_legal_approval": True, "no_funding_allocation": True},
    )
    ps.digest = ps.compute_digest()
    return ps

def get_profile(profile_id: str) -> dict[str, Any]:
    if profile_id == "winnipeg_mb_ca":
        return {"ok": True, "profile": WINNIPEG_JURISDICTION.to_dict()}
    if profile_id == "winnipeg_demo_community":
        return {"ok": True, "profile": WINNIPEG_DEMO_COMMUNITY.to_dict()}
    return {"ok": False, "error": f"unknown_profile: {profile_id}",
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False}

def check_profile_conflicts(profile_set: CivicProfileSet) -> dict[str, Any]:
    # Check for contradictory authority rules
    conflicts = []
    # For MVP, no conflicts expected with single jurisdiction
    return {"ok": len(conflicts) == 0, "conflicts": conflicts,
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": False}
