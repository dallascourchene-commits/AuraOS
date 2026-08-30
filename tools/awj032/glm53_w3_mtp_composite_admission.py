"""Compose current GLM-5.3 W3 producer admission with verified MTP provenance.

D0/nonpromoting consumer adapter. This module does not re-observe official source,
does not read tensor payloads, does not execute a model, and grants only
eligibility for the deterministic native synthetic W3 fixture.

The two upstream proof planes remain independently owned:
- PR410: official-W2 producer proof is consumed at the W3 boundary.
- PR409: immutable official source discharges only MTP resolver provenance.

Composition succeeds only when the W3 receipt is blocked *solely* on MTP
provenance and the PR409-shaped report carries the exact hosted immutable-source
evidence generation. No caller boolean can substitute for either receipt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import re
from typing import Any, Mapping

from tools.awj032.glm53_official_w2_observation import OFFICIAL_W2_OBSERVATION
from tools.awj032.glm53_w3_official_producer_admission import (
    CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
    CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
)

SCHEMA = "AWJ032GLM53W3CompositeAdmissionV1"
W3_SCHEMA = "AWJ032GLM53W3OfficialProducerAdmissionV1"
MTP_REPORT_SCHEMA = "GLM53CheckpointLayoutProbeV1"
MTP_EVIDENCE_SCHEMA = "OfficialSourceMTPRoleEvidenceV1"

PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"
OFFICIAL_REPO = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_SOURCE_BUNDLE_ID = "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b"
OFFICIAL_SOURCE_EVIDENCE_ID = "b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2"
OFFICIAL_NUM_HIDDEN_LAYERS = 78
OFFICIAL_NUM_NEXTN_PREDICT_LAYERS = 1
OFFICIAL_MTP_LAYER = 78
OFFICIAL_ROLE = "MTP_NON_DECODER"
PROVENANCE_METHOD = "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION"

PR409_VERIFIED_HEAD = "530c828add572d3e17fce3a980ae6e3f4a7d93d6"
PR409_VERIFIED_RUN_REF = "github-actions:run:33338482387:job:99329599405"
PR410_PARENT_HEAD = "f894de232968e03b9ad7b94b0e8a4b6f05026b00"
PR410_PARENT_RUN_REF = "github-actions:run:33338735868:job:99330301144"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class W3CompositeAdmissionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise W3CompositeAdmissionError("NONCANONICAL_RECEIPT") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _as_mapping(value: Any, code: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, Mapping):
            return dict(raw)
    raise W3CompositeAdmissionError(code)


def _exact_bool(value: Any, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        raise W3CompositeAdmissionError(code)


def _sha256(value: Any, code: str) -> str:
    if not isinstance(value, str):
        raise W3CompositeAdmissionError(code)
    out = value.strip().lower()
    if not _SHA256.fullmatch(out):
        raise W3CompositeAdmissionError(code)
    return out


def _validate_w3_receipt(value: Any) -> dict[str, Any]:
    receipt = _as_mapping(value, "W3_RECEIPT_REQUIRED")
    if receipt.get("schema") != W3_SCHEMA:
        raise W3CompositeAdmissionError("W3_RECEIPT_SCHEMA_MISMATCH")
    if receipt.get("status") != "BLOCKED":
        raise W3CompositeAdmissionError("W3_PRECOMPOSITION_STATUS_REQUIRED")

    blockers = receipt.get("blockers")
    if blockers != [PROVENANCE_BLOCKER] and blockers != (PROVENANCE_BLOCKER,):
        raise W3CompositeAdmissionError("W3_BLOCKER_SET_NOT_COMPOSABLE")

    _exact_bool(
        receipt.get("official_w2_producer_proof_consumed"),
        True,
        "W3_OFFICIAL_W2_PRODUCER_PROOF_REQUIRED",
    )
    for field in (
        "synthetic_tiny_fixture_admitted",
        "g2_admitted",
        "runtime_execution_admitted",
        "checkpoint_payload_admitted",
        "provider_effect_admitted",
        "authority",
    ):
        _exact_bool(receipt.get(field), False, f"W3_EFFECT_CEILING_WIDENED:{field}")

    _sha256(receipt.get("official_w2_bound_plan_digest"), "W3_BOUND_PLAN_DIGEST_REQUIRED")
    _sha256(receipt.get("inner_source_plan_digest"), "W3_INNER_PLAN_DIGEST_REQUIRED")

    o = OFFICIAL_W2_OBSERVATION
    expected = {
        "official_w2_observation_digest": o.observation_digest,
        "official_w2_receipt_digest": o.receipt_digest,
        "official_w2_producer_semantic_head": o.producer_semantic_head,
        "official_w2_producer_run_ref": o.producer_run_ref,
        "official_w2_drive_observation_ref": o.drive_observation_ref,
        "representative_layer": o.layer,
        "representative_expert": o.expert,
        "airllm_security_semantic_head": CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
        "glm53_metadata_semantic_head": CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
    }
    for key, expected_value in expected.items():
        if receipt.get(key) != expected_value:
            raise W3CompositeAdmissionError("W3_RECEIPT_GENERATION_MISMATCH", key)
    return receipt


def _validate_mtp_report(value: Any) -> tuple[dict[str, Any], str]:
    report = _as_mapping(value, "MTP_VERIFIED_REPORT_REQUIRED")
    if report.get("schema") != MTP_REPORT_SCHEMA:
        raise W3CompositeAdmissionError("MTP_REPORT_SCHEMA_MISMATCH")
    if report.get("status") != "READY_FOR_HEADER_AND_TINY_FIXTURE":
        raise W3CompositeAdmissionError("MTP_REPORT_STATUS_NOT_COMPOSABLE")
    if report.get("source_binding_proven") is not True:
        raise W3CompositeAdmissionError("MTP_SOURCE_BINDING_REQUIRED")
    if report.get("extra_layer_resolver_provenance_proven") is not True:
        raise W3CompositeAdmissionError("MTP_PROVENANCE_REQUIRED")
    if report.get("extra_layer_resolver_provenance_method") != PROVENANCE_METHOD:
        raise W3CompositeAdmissionError("MTP_PROVENANCE_METHOD_MISMATCH")

    blockers = report.get("blockers")
    if blockers not in ([], ()):
        raise W3CompositeAdmissionError("MTP_UNRELATED_BLOCKER_REMAINS")
    if report.get("model_revision") != OFFICIAL_REVISION:
        raise W3CompositeAdmissionError("MTP_OFFICIAL_REVISION_MISMATCH")
    if report.get("index_sha256") != OFFICIAL_INDEX_SHA256:
        raise W3CompositeAdmissionError("MTP_OFFICIAL_INDEX_MISMATCH")
    if report.get("source_bundle_id") != OFFICIAL_SOURCE_BUNDLE_ID:
        raise W3CompositeAdmissionError("MTP_SOURCE_BUNDLE_MISMATCH")
    if report.get("num_hidden_layers") != OFFICIAL_NUM_HIDDEN_LAYERS:
        raise W3CompositeAdmissionError("MTP_HIDDEN_LAYER_COUNT_MISMATCH")
    if report.get("extra_checkpoint_layer_indices") != [OFFICIAL_MTP_LAYER]:
        raise W3CompositeAdmissionError("MTP_EXTRA_LAYER_SET_MISMATCH")
    if report.get("unclassified_extra_checkpoint_layer_indices") not in ([], ()):
        raise W3CompositeAdmissionError("MTP_UNCLASSIFIED_EXTRA_LAYER_REMAINS")
    if report.get("classified_extra_checkpoint_layers") != [
        {
            "index": OFFICIAL_MTP_LAYER,
            "role": OFFICIAL_ROLE,
            "decoder_pager_membership": False,
        }
    ]:
        raise W3CompositeAdmissionError("MTP_ROLE_CLASSIFICATION_MISMATCH")

    for field in (
        "g2_admitted",
        "large_checkpoint_admitted",
        "runtime_execution_proven",
    ):
        _exact_bool(report.get(field), False, f"MTP_EFFECT_CEILING_WIDENED:{field}")

    evidence = report.get("official_mtp_role_source_evidence")
    if not isinstance(evidence, Mapping):
        raise W3CompositeAdmissionError("MTP_SOURCE_EVIDENCE_REQUIRED")
    evidence = dict(evidence)
    if evidence.get("schema") != MTP_EVIDENCE_SCHEMA:
        raise W3CompositeAdmissionError("MTP_SOURCE_EVIDENCE_SCHEMA_MISMATCH")
    expected_evidence = {
        "owner_repo": OFFICIAL_REPO,
        "immutable_model_revision": OFFICIAL_REVISION,
        "index_sha256": OFFICIAL_INDEX_SHA256,
        "source_bundle_id": OFFICIAL_SOURCE_BUNDLE_ID,
        "num_hidden_layers": OFFICIAL_NUM_HIDDEN_LAYERS,
        "num_nextn_predict_layers": OFFICIAL_NUM_NEXTN_PREDICT_LAYERS,
        "observed_extra_checkpoint_layer_indices": [OFFICIAL_MTP_LAYER],
        "role_index": OFFICIAL_MTP_LAYER,
        "role": OFFICIAL_ROLE,
        "decoder_pager_membership": False,
        "source_verified": True,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
    }
    for key, expected_value in expected_evidence.items():
        actual = evidence.get(key)
        if key == "observed_extra_checkpoint_layer_indices" and actual == (OFFICIAL_MTP_LAYER,):
            actual = [OFFICIAL_MTP_LAYER]
        if actual != expected_value:
            raise W3CompositeAdmissionError("MTP_SOURCE_EVIDENCE_INVARIANT_FAILED", key)

    marker_keys = evidence.get("mtp_marker_keys")
    if not isinstance(marker_keys, (list, tuple)) or not marker_keys:
        raise W3CompositeAdmissionError("MTP_MARKER_REQUIRED")
    marker_prefix = f"model.layers.{OFFICIAL_MTP_LAYER}.eh_proj"
    if any(not isinstance(k, str) or not k.startswith(marker_prefix) for k in marker_keys):
        raise W3CompositeAdmissionError("MTP_MARKER_MISMATCH")

    report_evidence_pairs = {
        "config_parsed_sha256": "config_parsed_sha256",
        "index_parsed_sha256": "index_parsed_sha256",
        "weight_map_digest": "weight_map_digest",
        "source_bundle_id": "source_bundle_id",
        "index_sha256": "index_sha256",
        "num_hidden_layers": "num_hidden_layers",
    }
    for report_key, evidence_key in report_evidence_pairs.items():
        if report.get(report_key) != evidence.get(evidence_key):
            raise W3CompositeAdmissionError("MTP_REPORT_EVIDENCE_MISMATCH", report_key)

    evidence_id = _sha256(
        report.get("official_mtp_role_source_evidence_id"),
        "MTP_SOURCE_EVIDENCE_ID_REQUIRED",
    )
    recomputed_evidence_id = _digest(evidence)
    if evidence_id != recomputed_evidence_id:
        raise W3CompositeAdmissionError("MTP_SOURCE_EVIDENCE_DIGEST_MISMATCH")
    if evidence_id != OFFICIAL_SOURCE_EVIDENCE_ID:
        raise W3CompositeAdmissionError("MTP_SOURCE_EVIDENCE_GENERATION_MISMATCH")

    return report, evidence_id


@dataclass(frozen=True)
class W3CompositeAdmissionReceipt:
    status: str
    blockers: tuple[str, ...]
    w3_input_receipt_digest: str
    mtp_input_report_digest: str
    official_mtp_source_evidence_id: str
    pr410_parent_head: str = PR410_PARENT_HEAD
    pr410_parent_run_ref: str = PR410_PARENT_RUN_REF
    pr409_verified_head: str = PR409_VERIFIED_HEAD
    pr409_verified_run_ref: str = PR409_VERIFIED_RUN_REF
    official_w2_producer_proof_consumed: bool = True
    official_mtp_source_provenance_consumed: bool = True
    native_synthetic_w3_eligible: bool = True
    official_tensor_payload_admitted: bool = False
    runtime_execution_admitted: bool = False
    g2_admitted: bool = False
    provider_effect_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "blockers": list(self.blockers),
        }

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def compose_w3_mtp_admission(
    *,
    w3_receipt: Any,
    mtp_verified_report: Any,
) -> W3CompositeAdmissionReceipt:
    """Open only the native synthetic W3 fixture lane from exact upstream receipts."""
    w3 = _validate_w3_receipt(w3_receipt)
    mtp, evidence_id = _validate_mtp_report(mtp_verified_report)

    return W3CompositeAdmissionReceipt(
        status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        w3_input_receipt_digest=_digest(w3),
        mtp_input_report_digest=_digest(mtp),
        official_mtp_source_evidence_id=evidence_id,
    )
