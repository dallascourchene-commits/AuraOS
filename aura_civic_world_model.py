"""
Aura Civic World Model — core object classes for civic planning.

Separates: observed_state, asserted_state, inferred_state, simulated_state, desired_state.
Not a complete Winnipeg digital twin.
"""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

@dataclass
class CivicNeed:
    need_id: str
    description: str
    community_ref: str = ""
    truth_class: str = "COMMUNITY_ASSERTED"
    privacy_class: str = "PUBLIC_PSEUDONYMOUS"
    location_class: str = "NEIGHBOURHOOD_ONLY"
    consent_to_match: bool = False
    contributor_ref: str = ""
    created_at: float = 0.0
    def to_dict(self): return asdict(self)

@dataclass
class ResourceOffer:
    offer_id: str
    offer_type: str  # skill, space, equipment, material, funding, time, mentor
    description: str
    consent_to_match: bool = False
    truth_class: str = "COMMUNITY_ASSERTED"
    privacy_class: str = "COMMUNITY_ONLY"
    location_class: str = "NEIGHBOURHOOD_ONLY"
    contributor_ref: str = ""
    availability: str = ""
    expires_at: float = 0.0
    def to_dict(self): return asdict(self)

@dataclass
class Proposal:
    proposal_id: str
    title: str
    description: str
    scenario_ref: str = ""
    truth_class: str = "AURA_PROPOSED"
    parent_objective_hash: str = ""
    def to_dict(self): return asdict(self)

@dataclass
class Objection:
    objection_id: str
    proposal_ref: str
    reason: str
    severity: str = "OBJECTION"  # OBJECTION, CRITICAL_OBJECTION
    contributor_ref: str = ""
    truth_class: str = "COMMUNITY_ASSERTED"
    def to_dict(self): return asdict(self)

@dataclass
class LegalInstrument:
    instrument_id: str
    name: str
    level: str  # constitutional, federal, provincial, municipal, bylaw
    source_ref: str = ""
    applicability: str = "INFORMATIONAL"  # DIRECTLY_APPLICABLE, POSSIBLY_APPLICABLE, etc.
    truth_class: str = "OFFICIAL_PRIMARY_SOURCE"
    as_of_date: str = ""
    def to_dict(self): return asdict(self)

@dataclass
class CouncilItem:
    item_id: str
    title: str
    body: str = ""  # committee/council body
    meeting_date: str = ""
    disposition: str = ""
    vote_record: str = ""
    source_ref: str = ""
    truth_class: str = "OFFICIAL_PRIMARY_SOURCE"
    extraction_confidence: float = 0.0
    def to_dict(self): return asdict(self)

@dataclass
class Scenario:
    scenario_id: str
    title: str
    description: str
    metrics: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    truth_class: str = "AURA_PROPOSED"
    parent_objective_hash: str = ""
    pareto_label: str = ""  # e.g., "lowest cost", "balanced candidate"
    def to_dict(self): return asdict(self)

@dataclass
class DecisionPacket:
    packet_id: str
    objective: str
    active_profiles: list[str] = field(default_factory=list)
    participant_scope: str = ""
    needs: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    workstreams: list[dict] = field(default_factory=list)
    scenarios: list[dict] = field(default_factory=list)
    legal_questions: list[dict] = field(default_factory=list)
    consent_arc: dict[str, Any] = field(default_factory=dict)
    reservations: list[dict] = field(default_factory=list)
    objections: list[dict] = field(default_factory=list)
    minority_report: str = ""
    representation_gaps: list[str] = field(default_factory=list)
    bridge_options: list[dict] = field(default_factory=list)
    pilot_option: dict[str, Any] = field(default_factory=dict)
    audit_references: list[str] = field(default_factory=list)
    disclaimer: str = "This packet records a bounded deliberation and planning process. It is not a City approval, legal opinion, funding commitment, binding community referendum, or representation of all residents."
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)
    def compute_digest(self) -> str:
        d = self.to_dict()
        return hashlib.blake2b(str(d).encode(), digest_size=12).hexdigest()
