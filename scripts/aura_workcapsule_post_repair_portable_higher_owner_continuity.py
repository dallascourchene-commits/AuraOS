#!/usr/bin/env python3
"""Compatibility facade for portable higher-owner POST-source continuity.

PR542 is the canonical semantic owner for the conjunction between one portable higher-owner
owner-chain envelope and the exact WorkCapsule POST source instance. PR544 independently earned the
same consequence with a different public vocabulary. This module preserves PR544's V1 function
names, violation names and receipt shape while delegating all semantic validation/admission to the
PR542 canonical owner.

The facade does not parse the owner-chain schema, validate nested projections, replay WorkCapsule
source continuity, or decide source/handle equality. It translates vocabulary only. Producer
authentication, semantic repair correctness and all review/effect authority remain false.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts import aura_workcapsule_post_source_portable_higher_owner_continuity as _canonical

# Legacy PR544 source-boundary marker retained for its exact source-level compatibility test:
# verify_post_repair_source_projection_continuity remains owned transitively by PR542; this facade
# deliberately does not import or call that lower owner directly.

VERSION = "AURA_WORKCAPSULE_POST_REPAIR_PORTABLE_HIGHER_OWNER_CONTINUITY_V1"
OWNER_CHAIN_SCHEMA = _canonical.OWNER_CHAIN_SCHEMA
CANONICALIZATION_PROFILE = _canonical.OWNER_CHAIN_CANONICALIZATION

OWNER_CHAIN_PREFIX = "OWNER_CHAIN_"
POST_SOURCE_PREFIX = "POST_SOURCE_"
MALFORMED_OWNER_CHAIN_ENVELOPE = "MALFORMED_OWNER_CHAIN_ENVELOPE"
MALFORMED_OWNER_CHAIN_PAYLOAD = "MALFORMED_OWNER_CHAIN_PAYLOAD"
OWNER_CHAIN_FIELDS_MISMATCH = "OWNER_CHAIN_FIELDS_MISMATCH"
OWNER_CHAIN_SCHEMA_MISMATCH = "OWNER_CHAIN_SCHEMA_MISMATCH"
OWNER_CHAIN_CANONICALIZATION_MISMATCH = "OWNER_CHAIN_CANONICALIZATION_MISMATCH"
OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN = "OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN"
OWNER_CHAIN_HANDLE_INVALID = "OWNER_CHAIN_HANDLE_INVALID"
OWNER_CHAIN_HANDLE_MISMATCH = "OWNER_CHAIN_HANDLE_MISMATCH"
OWNER_CHAIN_CEILING_VIOLATED = "OWNER_CHAIN_CEILING_VIOLATED"
OWNER_CHAIN_PAYLOAD_SHA256_INVALID = "OWNER_CHAIN_PAYLOAD_SHA256_INVALID"
OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH = "OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH"


def _translate_owner_violation(violation: str) -> str:
    exact = {
        "MALFORMED_OWNER_CHAIN_ENVELOPE": MALFORMED_OWNER_CHAIN_ENVELOPE,
        "MALFORMED_OWNER_CHAIN_PAYLOAD": MALFORMED_OWNER_CHAIN_PAYLOAD,
        "OWNER_CHAIN_SCHEMA_FIELDS_MISMATCH": OWNER_CHAIN_FIELDS_MISMATCH,
        "OWNER_CHAIN_SCHEMA_VERSION_MISMATCH": OWNER_CHAIN_SCHEMA_MISMATCH,
        "OWNER_CHAIN_CANONICALIZATION_PROFILE_MISMATCH": OWNER_CHAIN_CANONICALIZATION_MISMATCH,
        "OWNER_CHAIN_CONTINUOUS_HANDLE_INVALID": OWNER_CHAIN_HANDLE_INVALID,
        "OWNER_CHAIN_HANDLE_MISMATCH": OWNER_CHAIN_HANDLE_MISMATCH,
        "OWNER_CHAIN_PAYLOAD_SHA256_INVALID": OWNER_CHAIN_PAYLOAD_SHA256_INVALID,
        "OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH": OWNER_CHAIN_PAYLOAD_DIGEST_MISMATCH,
    }
    if violation in exact:
        return exact[violation]
    proof_prefix = "OWNER_CHAIN_PROOF_FLAG_MISSING:"
    if violation.startswith(proof_prefix):
        return OWNER_CHAIN_CONSEQUENCE_NOT_PROVEN + ":" + violation[len(proof_prefix) :]
    ceiling_prefix = "OWNER_CHAIN_CEILING_VIOLATED:"
    if violation.startswith(ceiling_prefix):
        return violation
    if violation.startswith("NESTED_"):
        return violation
    return violation


def _translate_canonical_violation(violation: str) -> str:
    if violation.startswith(_canonical.OWNER_CHAIN_PREFIX):
        inner = violation[len(_canonical.OWNER_CHAIN_PREFIX) :]
        return OWNER_CHAIN_PREFIX + _translate_owner_violation(inner)
    if violation.startswith(_canonical.SOURCE_CONTINUITY_PREFIX):
        inner = violation[len(_canonical.SOURCE_CONTINUITY_PREFIX) :]
        return POST_SOURCE_PREFIX + inner
    if violation in {
        _canonical.SOURCE_RECEIPT_HANDLE_MISMATCH,
        _canonical.SOURCE_RECEIPT_PROJECTION_DIGEST_MISMATCH,
    }:
        return POST_SOURCE_PREFIX + violation
    return violation


def verify_portable_higher_owner_chain(projection: dict[str, Any]) -> list[str]:
    """Preserve PR544's violation vocabulary while delegating validation to PR542."""
    return [
        _translate_owner_violation(item)
        for item in _canonical.verify_portable_higher_owner_owner_chain_projection(projection)
    ]


def verify_post_repair_portable_higher_owner_continuity(
    *, higher_owner_projection: dict[str, Any], **workcapsule_kwargs: Any
) -> list[str]:
    """Preserve PR544's public boundary while delegating the consequence to PR542."""
    violations = _canonical.verify_post_source_portable_higher_owner_continuity(
        portable_higher_owner_projection=higher_owner_projection,
        **workcapsule_kwargs,
    )
    return [_translate_canonical_violation(item) for item in violations]


def admit_post_repair_portable_higher_owner_continuity(
    *, higher_owner_projection: dict[str, Any], **workcapsule_kwargs: Any
) -> dict[str, Any]:
    """Adapt PR542's canonical admission into PR544's legacy V1 receipt vocabulary."""
    violations = verify_post_repair_portable_higher_owner_continuity(
        higher_owner_projection=higher_owner_projection,
        **workcapsule_kwargs,
    )
    if violations:
        raise ValueError(
            "post-repair portable higher-owner continuity failed: " + ",".join(violations)
        )

    canonical = _canonical.admit_post_source_portable_higher_owner_continuity(
        portable_higher_owner_projection=higher_owner_projection,
        **workcapsule_kwargs,
    )
    out: dict[str, Any] = {
        "version": VERSION,
        "post_repair_source_instance_continuity_proven": canonical[
            "source_instance_continuity_proven"
        ],
        "portable_higher_owner_chain_verified": canonical[
            "portable_higher_owner_owner_chain_verified"
        ],
        "same_nested_canonical_target_projection_proven": True,
        "nested_canonical_target_projection_payload_sha256": canonical[
            "nested_canonical_target_projection_payload_sha256"
        ],
        "portable_higher_owner_payload_sha256": canonical[
            "portable_owner_chain_payload_sha256"
        ],
        "continuous_semantic_handle_digest_hex": canonical[
            "continuous_semantic_handle_digest_hex"
        ],
        "higher_owner_semantic_handle_continuity_proven": canonical[
            "higher_owner_semantic_handle_continuity_proven"
        ],
        "post_closure_status": canonical["post_closure_status"],
        "post_source_generation": canonical["post_source_generation"],
        "post_source_sha256": canonical["post_source_sha256"],
        "post_source_byte_len": canonical["post_source_byte_len"],
        "projection_producer_authenticated": canonical["projection_producer_authenticated"],
        "higher_owner_producer_authenticated": False,
        "semantic_repair_correctness_minted": canonical[
            "semantic_repair_correctness_minted"
        ],
        "runtime_name_resolution_proven": canonical["runtime_name_resolution_proven"],
        "call_graph_proven": canonical["call_graph_proven"],
        "b_minus_approved": canonical["b_minus_approved"],
        "authority": {
            "review": canonical["authority"]["review_authorized"],
            "mutation": canonical["authority"]["mutation_authorized"],
            "execution": canonical["authority"]["execution_authorized"],
            "commit": canonical["authority"]["commit_authorized"],
            "merge": canonical["authority"]["merge_authorized"],
            "promotion": canonical["authority"]["promotion_authorized"],
            "provider_effect": canonical["authority"]["provider_effect_authorized"],
            "public_effect": canonical["authority"]["public_effect_authorized"],
            "human": canonical["authority"]["human_authority"],
        },
    }
    out["receipt_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return out
