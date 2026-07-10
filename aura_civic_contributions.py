"""
Aura Civic Contributions — community input with privacy and consent enforcement.
"""
from __future__ import annotations
import hashlib, time
from dataclasses import dataclass, field, asdict
from typing import Any

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

CONTRIBUTION_TYPES = (
    "NEED", "IDEA", "PROPOSAL", "SKILL_OFFER", "SPACE_OFFER", "PROPERTY_OFFER",
    "MATERIAL_OFFER", "EQUIPMENT_OFFER", "FUNDING_OFFER", "VOLUNTEER_TIME",
    "MENTORSHIP_OFFER", "SERVICE_OFFER", "EVIDENCE", "CONSTRAINT", "QUESTION",
    "OBJECTION", "RESERVATION", "ALTERNATIVE", "ENDORSEMENT", "WITHDRAWAL",
)

PRIVACY_CLASSES = (
    "PUBLIC_ATTRIBUTED", "PUBLIC_PSEUDONYMOUS", "COMMUNITY_ONLY",
    "FACILITATOR_ONLY", "PRIVATE_NOT_SHARED",
)

LOCATION_CLASSES = (
    "EXACT_PUBLIC_LOCATION", "APPROXIMATE_LOCATION", "NEIGHBOURHOOD_ONLY",
    "PRIVATE_TO_FACILITATOR", "NOT_MAPPED",
)

@dataclass
class Contribution:
    contribution_id: str
    contribution_type: str
    original_statement: str
    normalized_statement: str = ""
    contributor_ref: str = ""
    privacy_class: str = "COMMUNITY_ONLY"
    location_class: str = "NEIGHBOURHOOD_ONLY"
    consent_to_match: bool = False
    truth_class: str = "COMMUNITY_ASSERTED"
    created_at: float = 0.0
    withdrawn: bool = False
    withdrawn_at: float = 0.0
    def to_dict(self): return asdict(self)

def create_contribution(ctype: str, statement: str, **kwargs) -> Contribution:
    cid = hashlib.blake2b(f"{ctype}{statement}{time.time()}".encode(), digest_size=10).hexdigest()
    c = Contribution(
        contribution_id=f"CONTRIB-{cid}",
        contribution_type=ctype,
        original_statement=statement,
        normalized_statement=kwargs.get("normalized", statement),
        contributor_ref=kwargs.get("contributor", ""),
        privacy_class=kwargs.get("privacy", "COMMUNITY_ONLY"),
        location_class=kwargs.get("location", "NEIGHBOURHOOD_ONLY"),
        consent_to_match=kwargs.get("consent_to_match", False),
        created_at=time.time(),
    )
    return c

def withdraw_contribution(c: Contribution) -> Contribution:
    c.withdrawn = True
    c.withdrawn_at = time.time()
    return c

def check_consent_to_match(c: Contribution) -> dict[str, Any]:
    if not c.consent_to_match:
        return {"ok": False, "error": "consent_to_match_required",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}

def check_no_contact_leakage(c: Contribution) -> dict[str, Any]:
    """Ensure no private contact details are exposed to unauthorized parties."""
    text = c.original_statement.lower()
    import re
    has_email = bool(re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text))
    has_phone = bool(re.search(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', text))
    if c.privacy_class in ("PRIVATE_NOT_SHARED", "FACILITATOR_ONLY") and (has_email or has_phone):
        return {"ok": False, "error": "potential_contact_leakage",
                "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
    return {"ok": True, "patch_authority": PATCH_AUTHORITY, "vsa_patch_authority": VSA_PATCH_AUTHORITY}
