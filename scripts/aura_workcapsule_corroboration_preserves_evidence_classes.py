#!/usr/bin/env python3
"""Preserve evidence-class noninterchangeability across a live causal corroboration edge.

PR580 owns the negative relation between two exact evidence classes: live-artifact host
evidence and causal raw-slice local evidence are not substitutable. PR577 owns a
corroboration edge between distinct PR568 and PR572 proof artifacts that establish the
same bounded live causal fact.

This membrane closes one graph-typing seam. Adding the PR577 corroboration edge must
not erase PR580's evidence-class boundary. The PR580 live target must map explicitly
to the PR568 member of the corroboration edge, while the PR572 sibling must remain
invalid in both PR580 parent-evidence slots.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from scripts.aura_workcapsule_live_artifact_raw_slice_noninterchangeability import (
    admit_live_artifact_raw_slice_noninterchangeability,
    verify_live_artifact_raw_slice_noninterchangeability,
)
from scripts.aura_workcapsule_live_causal_corroboration import (
    admit_live_causal_corroboration,
    verify_live_causal_corroboration,
)

VERSION = "AURA_WORKCAPSULE_CORROBORATION_PRESERVES_EVIDENCE_CLASSES_V1"
HOST_TARGET_PREFIX = "aura-workcapsule-target-sha256:"
PROOF_ARTIFACT_PREFIX = "aura-proof-artifact-sha256:"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _ref_digest(value: Any, prefix: str) -> str | None:
    if not isinstance(value, str) or not value.startswith(prefix):
        return None
    digest = value[len(prefix):]
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        return None
    return digest


def verify_corroboration_preserves_evidence_classes(
    *,
    live_artifact_host_receipt: Mapping[str, Any],
    causal_raw_slice_host_separation_receipt: Mapping[str, Any],
    pr568_receipt: Mapping[str, Any],
    pr572_receipt: Mapping[str, Any],
) -> list[str]:
    """Require both exact parent relations and reject sibling evidence-class substitution."""
    live = dict(live_artifact_host_receipt)
    raw = dict(causal_raw_slice_host_separation_receipt)
    a = dict(pr568_receipt)
    b = dict(pr572_receipt)

    violations = [
        "NONINTERCHANGEABILITY_" + item
        for item in verify_live_artifact_raw_slice_noninterchangeability(
            live_artifact_host_receipt=live,
            causal_raw_slice_host_separation_receipt=raw,
        )
    ]
    violations.extend(
        "CORROBORATION_" + item
        for item in verify_live_causal_corroboration(
            pr568_receipt=a,
            pr572_receipt=b,
        )
    )
    if violations:
        return list(dict.fromkeys(violations))

    corroboration = admit_live_causal_corroboration(
        pr568_receipt=a,
        pr572_receipt=b,
    )
    live_digest = _ref_digest(live.get("live_causal_artifact_target_ref"), HOST_TARGET_PREFIX)
    pr568_digest = _ref_digest(corroboration.get("pr568_artifact_ref"), PROOF_ARTIFACT_PREFIX)
    if live_digest is None:
        violations.append("LIVE_ARTIFACT_TARGET_REF_INVALID")
    if pr568_digest is None:
        violations.append("PR568_CORROBORATION_ARTIFACT_REF_INVALID")
    if live_digest is not None and pr568_digest is not None and live_digest != pr568_digest:
        violations.append("LIVE_ARTIFACT_TARGET_NOT_PR568_CORROBORATION_MEMBER")

    # Ask PR580's own verifier whether the PR572 sibling can replace either evidence class.
    sibling_as_live = verify_live_artifact_raw_slice_noninterchangeability(
        live_artifact_host_receipt=b,
        causal_raw_slice_host_separation_receipt=raw,
    )
    if sibling_as_live != ["PR575_LIVE_RECEIPT_SCHEMA_MISMATCH"]:
        violations.append("PR572_SIBLING_LIVE_HOST_CLASS_SUBSTITUTION_NOT_REJECTED")

    sibling_as_raw = verify_live_artifact_raw_slice_noninterchangeability(
        live_artifact_host_receipt=live,
        causal_raw_slice_host_separation_receipt=b,
    )
    if sibling_as_raw != ["PR574_RAW_RECEIPT_SCHEMA_MISMATCH"]:
        violations.append("PR572_SIBLING_RAW_SLICE_CLASS_SUBSTITUTION_NOT_REJECTED")

    if corroboration.get("proof_artifact_refs_distinct") is not True:
        violations.append("CORROBORATION_PROOF_ARTIFACT_DISTINCTION_LOST")
    return list(dict.fromkeys(violations))


def admit_corroboration_preserves_evidence_classes(**kwargs: Any) -> dict[str, Any]:
    violations = verify_corroboration_preserves_evidence_classes(**kwargs)
    if violations:
        raise ValueError("corroboration/evidence-class membrane failed: " + ",".join(violations))

    live = dict(kwargs["live_artifact_host_receipt"])
    noninterchangeability = admit_live_artifact_raw_slice_noninterchangeability(
        live_artifact_host_receipt=kwargs["live_artifact_host_receipt"],
        causal_raw_slice_host_separation_receipt=kwargs[
            "causal_raw_slice_host_separation_receipt"
        ],
    )
    corroboration = admit_live_causal_corroboration(
        pr568_receipt=kwargs["pr568_receipt"],
        pr572_receipt=kwargs["pr572_receipt"],
    )
    live_digest = _ref_digest(live["live_causal_artifact_target_ref"], HOST_TARGET_PREFIX)
    pr568_digest = _ref_digest(corroboration["pr568_artifact_ref"], PROOF_ARTIFACT_PREFIX)
    assert live_digest is not None and pr568_digest is not None and live_digest == pr568_digest

    out = {
        "version": VERSION,
        "noninterchangeability_owner_reproved": True,
        "corroboration_owner_reproved": True,
        "live_artifact_target_is_pr568_corroboration_member": True,
        "same_underlying_pr568_digest_across_reference_schemes": True,
        "reference_scheme_identity_preserved": True,
        "corroboration_preserves_evidence_class_boundary": True,
        "pr572_sibling_substitutable_for_live_artifact_host_evidence": False,
        "pr572_sibling_substitutable_for_causal_raw_slice_evidence": False,
        "raw_slice_and_live_artifact_host_evidence_interchangeable_after_corroboration": False,
        "live_artifact_target_ref": live["live_causal_artifact_target_ref"],
        "pr568_proof_artifact_ref": corroboration["pr568_artifact_ref"],
        "pr572_proof_artifact_ref": corroboration["pr572_artifact_ref"],
        "pr580_noninterchangeability_receipt_identity": noninterchangeability[
            "receipt_identity"
        ],
        "pr577_corroboration_receipt_identity": corroboration["receipt_identity"],
        "proof_artifact_refs_distinct": corroboration["proof_artifact_refs_distinct"],
        "producer_authentication_proven": False,
        "semantic_equivalence_proven": False,
        "semantic_truth_proven": False,
        "host_resolver_trust_proven": False,
        "host_observation_authority_proven": False,
        "trusted_continuation_ready": False,
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
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_UTF8_V1",
        "scope_profile": VERSION,
        "value": _sha(out),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
