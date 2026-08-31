#!/usr/bin/env python3
"""Project exact AWJ032 owner-host C2 handoff integrity into typed persistent cognition."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.awj032.glm53_owner_host_c2_handoff import (
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    join_owner_host_c2_attempt,
)

VERSION = "AURA_AWJ032_OWNER_HOST_C2_MEMORY_BRIDGE_V1"
PR582_EXACT_HEAD = "24a5404ee3b987dee12192917e40b35d3a43e81c"
EVIDENCE_TYPE = "owner-host-c2-contract-join"
CURRENTNESS_DOMAIN = "contract-generation"
CONTRACT_CONTEXT = {
    "scope": "awj032",
    "use_class": "retrieval",
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
HOST_OBSERVATION_CONTEXT = {
    "scope": "awj032",
    "use_class": "retrieval",
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": ["host-observation"],
}


def _sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def project_owner_host_c2_attempt_memory(
    *,
    request: OwnerHostC2CanaryRequest,
    receipt: OwnerHostC2CanaryReceipt,
) -> dict[str, Any]:
    """Re-run exact PR582 join, then project only contract-generation evidence."""
    join = join_owner_host_c2_attempt(request=request, receipt=receipt)
    outcome_ref = "aura-awj032-c2-outcome-sha256:" + _sha(
        {
            "canary_process_succeeded": join.canary_process_succeeded,
            "generated_output_observed": join.generated_output_observed,
        }
    )
    node = seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": "aura-awj032-c2-join-sha256:" + join.logical_id,
            "artifact_ref_scheme": "aura-awj032-c2-join-sha256",
            "artifact_ref_value": join.logical_id,
            "evidence_type": EVIDENCE_TYPE,
            "currentness_domain": CURRENTNESS_DOMAIN,
            "claim_key": "awj032:owner-host-c2-attempt-outcome",
            "claim_value_ref": outcome_ref,
            "world_ref": "aura-awj032-c2-request-sha256:" + join.request_digest,
            "dependency_class_ref": "aura-awj032-c2-attempt-sha256:" + join.attempt_receipt_digest,
            "generation_ref": "pr582:" + PR582_EXACT_HEAD,
            "allowed_scopes": ["arena", "awj032"],
            "allowed_use_classes": ["diagnostic", "historical", "retrieval"],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )
    admitted = admit_evidence_nodes([node], CONTRACT_CONTEXT)
    if admitted["eligible_artifact_refs"] != [node["artifact_ref"]]:
        raise ValueError("CONTRACT_GENERATION_EVIDENCE_NOT_ADMITTED")
    host_probe = admit_evidence_nodes([node], HOST_OBSERVATION_CONTEXT)
    if host_probe["eligible_artifact_refs"]:
        raise ValueError("CONTRACT_CURRENTNESS_CROSS_CAST_TO_HOST_OBSERVATION")
    return {
        "version": VERSION,
        "pr582_exact_head": PR582_EXACT_HEAD,
        "parent_join_logical_id": join.logical_id,
        "evidence_node": node,
        "contract_generation_admission_receipt": admitted,
        "host_observation_admission_rejected": True,
        "host_observation_currentness_proven": False,
        "owner_host_producer_authenticated": False,
        "lifecycle_registry_satisfied": False,
        "real_w4_policy_winner_proven": False,
        "full_model_runtime_proven": False,
        "g2_admitted": False,
        "host_rank_transition_performed": False,
        "effect_authority_proven": False,
        "native_private_transformer_kv_accessed": False,
    }
