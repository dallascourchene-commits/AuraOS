#!/usr/bin/env python3
"""Preserve the causal host-envelope evidence class across corroboration.

PR583 proves that causal raw-slice evidence is not a causal host-admission envelope.
PR577 proves that PR568 and PR572 are distinct proof artifacts corroborating one
bounded live-causal fact. This membrane composes those owners only to establish a
negative evidence-type relation: neither corroborating proof receipt may be
cross-cast as the causal host-envelope transport consumed by PR573.

Corroboration does not convert proof-object type, establish producer identity,
semantic truth, resolver trust, host authority, continuation, or effects.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_causal_artifact_qualified_host_envelope import (
    verify_causal_host_admission_envelope,
)
from scripts.aura_workcapsule_causal_envelope_raw_slice_noninterchangeability import (
    admit_causal_envelope_raw_slice_noninterchangeability,
    verify_causal_envelope_raw_slice_noninterchangeability,
)
from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_PRESERVES_CAUSAL_ENVELOPE_CLASS_V1"
MALFORMED = "MALFORMED_CAUSAL_HOST_ADMISSION_ENVELOPE"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def verify_corroboration_preserves_causal_envelope_class(
    *,
    causal_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
    pr568_receipt: Mapping[str, Any],
    pr572_receipt: Mapping[str, Any],
) -> list[str]:
    host = dict(causal_artifact_host_receipt)
    raw = dict(causal_raw_slice_host_separation_receipt)
    a = dict(pr568_receipt)
    b = dict(pr572_receipt)

    violations = [
        "PR583_" + item
        for item in verify_causal_envelope_raw_slice_noninterchangeability(
            causal_artifact_host_receipt=host,
            causal_raw_slice_host_separation_receipt=raw,
        )
    ]
    violations.extend(
        "PR577_" + item
        for item in verify_live_causal_corroboration(
            pr568_receipt=a,
            pr572_receipt=b,
        )
    )
    if violations:
        return list(dict.fromkeys(violations))

    if verify_causal_host_admission_envelope(a) != [MALFORMED]:
        violations.append("PR568_PROOF_CROSS_CAST_AS_CAUSAL_HOST_ENVELOPE")
    if verify_causal_host_admission_envelope(b) != [MALFORMED]:
        violations.append("PR572_PROOF_CROSS_CAST_AS_CAUSAL_HOST_ENVELOPE")

    corroboration = admit_live_causal_corroboration(
        pr568_receipt=a,
        pr572_receipt=b,
    )
    if corroboration.get("proof_artifact_refs_distinct") is not True:
        violations.append("CORROBORATING_PROOF_ARTIFACT_DISTINCTION_LOST")
    return list(dict.fromkeys(violations))


def admit_corroboration_preserves_causal_envelope_class(**kwargs: Any) -> dict[str, Any]:
    violations = verify_corroboration_preserves_causal_envelope_class(**kwargs)
    if violations:
        raise ValueError("corroboration/causal-envelope class membrane failed: " + ",".join(violations))

    separation = admit_causal_envelope_raw_slice_noninterchangeability(
        causal_artifact_host_receipt=kwargs["causal_artifact_host_receipt"],
        causal_raw_slice_host_separation_receipt=kwargs[
            "causal_raw_slice_host_separation_receipt"
        ],
    )
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )

    payload = {
        "version": VERSION,
        "pr583_noninterchangeability_owner_reproved": True,
        "pr577_corroboration_owner_reproved": True,
        "pr568_proof_artifact_ref": corroboration["pr568_artifact_ref"],
        "pr572_proof_artifact_ref": corroboration["pr572_artifact_ref"],
        "proof_artifact_refs_distinct": corroboration["proof_artifact_refs_distinct"],
        "pr583_separation_receipt_identity": separation["receipt_identity"],
        "pr577_corroboration_receipt_identity": corroboration["receipt_identity"],
        "pr568_proof_is_causal_host_envelope": False,
        "pr572_proof_is_causal_host_envelope": False,
        "corroboration_converts_proof_to_causal_host_envelope": False,
        "causal_raw_slice_promoted_to_host_rank": False,
        "proof_artifacts_interchangeable": False,
        "producer_authenticated": False,
        "semantic_equivalence_proven": False,
        "semantic_truth_proven": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
        "host_effect_ready": False,
        "effect_authority_proven": False,
        "semantic_k27_authority_proven": False,
        "authority": {
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    out = dict(payload)
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha(payload),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
