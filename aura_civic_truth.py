"""
Aura Civic Truth Classes — every civic object carries a truth class.

OFFICIAL_PRIMARY_SOURCE, OFFICIAL_DERIVED_DATA, OFFICIAL_SNAPSHOT,
COMMUNITY_VERIFIED, COMMUNITY_ASSERTED, PUBLIC_SUBMISSION,
MODEL_EXTRACTED, MODEL_INFERRED, SYSTEM_RULE_DERIVED, AURA_PROPOSED,
SYNTHETIC_DEMO_DATA, STALE, DISPUTED, REVOKED, UNKNOWN
"""
from __future__ import annotations
from typing import Any

TRUTH_CLASSES = (
    "OFFICIAL_PRIMARY_SOURCE", "OFFICIAL_DERIVED_DATA", "OFFICIAL_SNAPSHOT",
    "COMMUNITY_VERIFIED", "COMMUNITY_ASSERTED", "PUBLIC_SUBMISSION",
    "MODEL_EXTRACTED", "MODEL_INFERRED", "SYSTEM_RULE_DERIVED", "AURA_PROPOSED",
    "SYNTHETIC_DEMO_DATA", "STALE", "DISPUTED", "REVOKED", "UNKNOWN",
)

PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


def validate_truth_class(tc: str) -> bool:
    return tc in TRUTH_CLASSES

def label_record(record: dict[str, Any], truth_class: str) -> dict[str, Any]:
    if not validate_truth_class(truth_class):
        return {"ok": False, "error": f"invalid_truth_class: {truth_class}"}
    r = dict(record)
    r["truth_class"] = truth_class
    r["patch_authority"] = PATCH_AUTHORITY
    r["vsa_patch_authority"] = VSA_PATCH_AUTHORITY
    return {"ok": True, "record": r}

def is_official(tc: str) -> bool:
    return tc.startswith("OFFICIAL")

def is_synthetic(tc: str) -> bool:
    return tc == "SYNTHETIC_DEMO_DATA"

def is_community(tc: str) -> bool:
    return tc in ("COMMUNITY_VERIFIED", "COMMUNITY_ASSERTED", "PUBLIC_SUBMISSION")

def is_model(tc: str) -> bool:
    return tc in ("MODEL_EXTRACTED", "MODEL_INFERRED")
