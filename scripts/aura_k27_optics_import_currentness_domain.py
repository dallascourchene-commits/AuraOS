#!/usr/bin/env python3
"""Project the exact K27 optics import receipt into its own typed currentness domain.

PR607 owns a deterministic source-bound optics falsifier/reference receipt. PR606
owns the current generation-scoped evidence discipline. This adapter composes only
the missing relation: the exact imported optics reference may be current in its own
import generation without becoming a measured optical-system observation or a
display-deployment qualification.

Eye-pose calibration/currentness is deliberately outside this module; that is a
separate Arena owner seam. No physical optics, safety, privacy, deployment, K27
semantic authority, native transformer KV state, or external effect is established.
"""
from __future__ import annotations

from typing import Any

from scripts.aura_provenance_corroboration_memory_admission import (
    NODE_VERSION,
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.k27_optics_candidate_falsifier import (
    NEGATIVE_CEILING,
    build_import_receipt,
    verify_import_receipt,
)

VERSION = "AURA_K27_OPTICS_IMPORT_CURRENTNESS_DOMAIN_V1"
PR606_EXACT_HEAD = "91a591d7208ff66b679cbb03ee9adc2118f29cc3"
PR607_EXACT_HEAD = "deef7bf05dd0bc3274f6a79d56ba22654c343208"
IMPORTED_SOURCE_SHA256 = "56d8593284d37ce03a2762dedc2390878ee6d271a0f1f100a5e245ad01080d6d"
EVIDENCE_TYPE = "k27-optics-imported-reference"
CURRENTNESS_DOMAIN = "k27-optics-import-generation"
RETRIEVAL_USE = "retrieval"
IMPORT_CURRENTNESS_USE = "k27-optics-import-currentness"
MEASURED_OPTICS_USE = "optical-system-measurement-currentness"
DISPLAY_DEPLOYMENT_USE = "display-deployment-currentness"
CROSS_DOMAIN_REJECTION = [
    "USE_CLASS_NOT_ALLOWED",
    "EVIDENCE_TYPE_NOT_ACCEPTED",
    "CURRENTNESS_DOMAIN_NOT_ACCEPTED",
]

RETRIEVAL_CONTEXT = {
    "scope": "arena",
    "use_class": RETRIEVAL_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
IMPORT_CURRENTNESS_CONTEXT = {
    "scope": "arena",
    "use_class": IMPORT_CURRENTNESS_USE,
    "accepted_evidence_types": [EVIDENCE_TYPE],
    "accepted_currentness_domains": [CURRENTNESS_DOMAIN],
}
MEASURED_OPTICAL_SYSTEM_CURRENTNESS_CONTEXT = {
    "scope": "arena",
    "use_class": MEASURED_OPTICS_USE,
    "accepted_evidence_types": ["k27-optics-measured-system-observation"],
    "accepted_currentness_domains": ["k27-optics-measured-system-generation"],
}
DISPLAY_DEPLOYMENT_CURRENTNESS_CONTEXT = {
    "scope": "arena",
    "use_class": DISPLAY_DEPLOYMENT_USE,
    "accepted_evidence_types": ["k27-optics-display-deployment-qualification"],
    "accepted_currentness_domains": ["k27-optics-display-deployment-generation"],
}


def _exact_import_receipt() -> dict[str, Any]:
    receipt = dict(
        build_import_receipt(
            imported_source_sha256=IMPORTED_SOURCE_SHA256,
            external_evidence_refs=(),
        )
    )
    if not verify_import_receipt(receipt):
        raise ValueError("PR607_EXACT_IMPORT_RECEIPT_INVALID")
    if receipt.get("imported_source_sha256") != IMPORTED_SOURCE_SHA256:
        raise ValueError("PR607_IMPORTED_SOURCE_IDENTITY_DRIFT")
    if receipt.get("claim_ceiling") != dict(sorted(NEGATIVE_CEILING.items())):
        raise ValueError("PR607_OPTICS_CLAIM_CEILING_DRIFT")
    if any(value is not False for value in receipt["claim_ceiling"].values()):
        raise ValueError("PR607_OPTICS_CLAIM_CEILING_WIDENED")
    return receipt


def project_k27_optics_import_currentness() -> dict[str, Any]:
    """Admit the exact source-bound optics reference only in its owned domain."""
    receipt = _exact_import_receipt()
    digest = receipt["receipt_sha256"]
    artifact_ref = "k27-optics-import-sha256:" + digest
    node = seal_evidence_node(
        {
            "version": NODE_VERSION,
            "artifact_ref": artifact_ref,
            "artifact_ref_scheme": "k27-optics-import-sha256",
            "artifact_ref_value": digest,
            "evidence_type": EVIDENCE_TYPE,
            "currentness_domain": CURRENTNESS_DOMAIN,
            "claim_key": "k27-optics:source-bound-import-reference",
            "claim_value_ref": artifact_ref,
            "world_ref": "k27-optics-source-sha256:" + IMPORTED_SOURCE_SHA256,
            "dependency_class_ref": "k27-optics-import-source-sha256:" + IMPORTED_SOURCE_SHA256,
            "generation_ref": "pr607:" + PR607_EXACT_HEAD,
            "allowed_scopes": ["arena"],
            "allowed_use_classes": [RETRIEVAL_USE, IMPORT_CURRENTNESS_USE],
            "current": True,
            "digest_verified": True,
            "schema_ok": True,
            "revoked": False,
            "supersedes_artifact_refs": [],
        }
    )

    retrieval = admit_evidence_nodes([node], RETRIEVAL_CONTEXT)
    own = admit_evidence_nodes([node], IMPORT_CURRENTNESS_CONTEXT)
    measured = admit_evidence_nodes([node], MEASURED_OPTICAL_SYSTEM_CURRENTNESS_CONTEXT)
    deployment = admit_evidence_nodes([node], DISPLAY_DEPLOYMENT_CURRENTNESS_CONTEXT)

    ref = node["artifact_ref"]
    if retrieval["eligible_artifact_refs"] != [ref]:
        raise ValueError("OPTICS_IMPORT_REFERENCE_NOT_RETRIEVABLE")
    if own["eligible_artifact_refs"] != [ref]:
        raise ValueError("OPTICS_IMPORT_REFERENCE_NOT_CURRENT_IN_OWN_DOMAIN")
    for name, admission in (("MEASURED_OPTICS", measured), ("DISPLAY_DEPLOYMENT", deployment)):
        if admission["eligible_artifact_refs"]:
            raise ValueError(name + "_CURRENTNESS_CROSS_CAST")
        if admission["excluded_by_artifact_ref"].get(ref) != CROSS_DOMAIN_REJECTION:
            raise ValueError(name + "_REJECTION_NOT_THREE_AXIS_FAIL_CLOSED")

    return {
        "version": VERSION,
        "pr606_exact_head": PR606_EXACT_HEAD,
        "pr607_exact_head": PR607_EXACT_HEAD,
        "imported_source_sha256": IMPORTED_SOURCE_SHA256,
        "import_receipt": receipt,
        "evidence_node": node,
        "retrieval_admission": retrieval,
        "optics_import_currentness_admission": own,
        "measured_optical_system_currentness_admission": measured,
        "display_deployment_currentness_admission": deployment,
        "optics_import_current_in_generation": True,
        "measured_optical_system_currentness_proven": False,
        "display_deployment_currentness_proven": False,
        "calibrated_eye_pose_currentness_proven": False,
        "eye_pose_calibration_owned_by_this_module": False,
        "optical_energy_conservation_proven": False,
        "speckle_free_proven": False,
        "zero_light_leakage_proven": False,
        "metric_eye_pose_proven": False,
        "exact_scene_unbinding_proven": False,
        "varifocal_correctness_proven": False,
        "hardware_latency_proven": False,
        "display_safety_proven": False,
        "deployment_ready": False,
        "producer_authenticated": False,
        "semantic_truth_proven": False,
        "effect_authority_proven": False,
        "semantic_k27_authority_minted": False,
        "native_private_transformer_kv_accessed": False,
        "gate10_promoted": False,
    }
