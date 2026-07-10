"""
Aura Civic Resource Graph and Matcher — explainable resource constellation matching.

Returns candidate constellations. Never creates a contract.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

EDGE_TYPES = (
    "CAN_SATISFY", "CAN_SUPPORT", "REQUIRES", "CONFLICTS_WITH",
    "LOCATED_NEAR", "ELIGIBLE_FOR", "POSSIBLY_ELIGIBLE_FOR",
    "HAS_CONSENT_TO_MATCH", "REQUIRES_VERIFICATION", "BLOCKED_BY", "ALTERNATIVE_TO",
)

HARD_BLOCKERS = (
    "no_consent", "privacy_conflict", "expired_offer", "legal_prohibition",
    "unverified_mandatory_credential", "unsafe_condition",
)


@dataclass
class ResourceNode:
    node_id: str
    node_type: str  # need, skill, space, equipment, material, funding, time, mentor, etc.
    label: str
    truth_class: str = "COMMUNITY_ASSERTED"
    consent_to_match: bool = False
    privacy_class: str = "COMMUNITY_ONLY"
    expired: bool = False
    def to_dict(self): return asdict(self)

@dataclass
class ResourceEdge:
    source_id: str
    target_id: str
    edge_type: str
    score: float = 0.0
    evidence: str = ""
    def to_dict(self): return asdict(self)

@dataclass
class ResourceConstellation:
    constellation_id: str
    need_id: str
    matched_offers: list[dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    score_explanation: dict[str, float] = field(default_factory=dict)
    hard_blockers: list[str] = field(default_factory=list)
    legal_blocks: list[str] = field(default_factory=list)
    missing_resources: list[str] = field(default_factory=list)
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    def to_dict(self): return asdict(self)


def match_resources(need: dict[str, Any], offers: list[dict[str, Any]]) -> dict[str, Any]:
    """Match a need against available offers. Returns candidate constellations."""
    constellations: list[dict[str, Any]] = []
    for offer in offers:
        blockers = []
        score_components = {}

        # Check consent
        if not offer.get("consent_to_match", False):
            blockers.append("no_consent")

        # Check expiry
        if offer.get("expired", False):
            blockers.append("expired_offer")

        # Check privacy
        if offer.get("privacy_class") == "PRIVATE_NOT_SHARED":
            blockers.append("privacy_conflict")

        # Calculate score components
        score_components["capability_fit"] = 0.8 if offer.get("offer_type") in ("skill", "space", "equipment") else 0.5
        score_components["consent_fit"] = 1.0 if offer.get("consent_to_match") else 0.0
        score_components["evidence_strength"] = 0.5
        score_components["legal_uncertainty"] = -0.2
        score_components["verification_gap"] = -0.1 if not offer.get("verified") else 0.0

        total_score = sum(score_components.values())
        if blockers:
            total_score = 0.0

        const = ResourceConstellation(
            constellation_id=f"CONST-{need.get('need_id', 'x')}-{offer.get('offer_id', 'y')}",
            need_id=need.get("need_id", ""),
            matched_offers=([] if {"no_consent", "privacy_conflict"} & set(blockers) else [offer]),
            score=total_score,
            score_explanation=score_components,
            hard_blockers=blockers,
        )
        constellations.append(const.to_dict())

    # Sort by score
    constellations.sort(key=lambda c: c["score"], reverse=True)
    return {"ok": True, "constellations": constellations, "count": len(constellations),
            "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
