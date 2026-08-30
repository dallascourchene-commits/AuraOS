"""W3 relying-party admission over registered PR340 producer state + PR409 source proof.

This successor closes the producer-provenance residual found after the first V2
composition. It still consumes PR410's official-W2 boundary first. It then
reconstructs PR340's *final* source-bound report from immutable official bytes,
verifies that report against a consumer-side registry pin emitted by exact hosted
PR416, and only then asks the current PR409 appraiser to discharge the MTP
resolver-provenance blocker. Positive output admits only the native synthetic W3
fixture; no official tensor/runtime/G2/provider/authority claim is created.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Callable, Mapping

from tools.awj032.glm53_checkpoint_source_binding import bind_checkpoint_sources
from tools.awj032.glm53_official_mtp_role_source_appraiser import (
    OfficialSourceMTPRoleEvidence,
    _apply_verified_source_role,
    observe_official_mtp_role,
    urllib_read_full,
)
from tools.awj032.glm53_pr340_producer_snapshot import (
    OFFICIAL_CONFIG_SHA256,
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_REVISION,
    emit_pr340_producer_snapshot,
)
from tools.awj032 import glm53_pr340_producer_snapshot_registry as registry
from tools.awj032.glm53_w3_official_producer_admission import (
    W3OfficialProducerAdmissionError,
    evaluate_w3_official_producer_admission,
)

SCHEMA = "AWJ032GLM53W3RegisteredProofPlaneAdmissionV3"
PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"
OFFICIAL_MTP_EVIDENCE_ID = "b0803af6fdb7afd0dcdbf7c5b718605658a02534c960d965cfc1729eb4d9d3a2"


class W3ProofPlaneAdmissionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _official_url(path: str) -> str:
    return f"https://huggingface.co/zai-org/GLM-5.3/resolve/{OFFICIAL_REVISION}/{path}?download=true"


def _observe_registered_pr340(
    *,
    read_full: Callable[[str, int], bytes],
) -> tuple[Any, Mapping[str, Any], OfficialSourceMTPRoleEvidence, Mapping[str, Any]]:
    config_raw = read_full(_official_url("config.json"), 2 * 1024 * 1024)
    index_raw = read_full(_official_url("model.safetensors.index.json"), 16 * 1024 * 1024)
    sources = bind_checkpoint_sources(
        model_revision=OFFICIAL_REVISION,
        config_raw_bytes=config_raw,
        expected_config_sha256=OFFICIAL_CONFIG_SHA256,
        index_raw_bytes=index_raw,
        expected_index_sha256=OFFICIAL_INDEX_SHA256,
    )
    snapshot, report = emit_pr340_producer_snapshot(
        sources,
        producer_execution_head=registry.PRODUCER_EXECUTION_HEAD,
        observation_time="consumer-reobservation",
    )
    registry.verify_registered_pr340_snapshot(snapshot, report)

    evidence = observe_official_mtp_role(read_full=read_full)
    if evidence.evidence_id != OFFICIAL_MTP_EVIDENCE_ID:
        raise W3ProofPlaneAdmissionError("OFFICIAL_MTP_EVIDENCE_ID_MISMATCH")
    admitted = _apply_verified_source_role(
        report,
        evidence,
        expected_pr340_logical_id=registry.CLASSIFICATION_STAGE_LOGICAL_ID,
        expected_pr340_semantic_generation=registry.PRODUCER_BASE_HEAD,
    )
    if admitted.get("blockers") != [] or admitted.get("status") != "READY_FOR_HEADER_AND_TINY_FIXTURE":
        raise W3ProofPlaneAdmissionError("PR409_APPRAISAL_DID_NOT_CLEAR_PROVENANCE")
    if admitted.get("pr340_producer_logical_id_verified") is not True:
        raise W3ProofPlaneAdmissionError("PR409_PRODUCER_VERIFICATION_REQUIRED")
    if admitted.get("pr340_producer_logical_id") != registry.CLASSIFICATION_STAGE_LOGICAL_ID:
        raise W3ProofPlaneAdmissionError("PR409_PRODUCER_LOGICAL_ID_MISMATCH")
    if admitted.get("pr340_producer_semantic_generation") != registry.PRODUCER_BASE_HEAD:
        raise W3ProofPlaneAdmissionError("PR409_PRODUCER_GENERATION_MISMATCH")
    if admitted.get("extra_layer_resolver_provenance_proven") is not True:
        raise W3ProofPlaneAdmissionError("PR409_RESOLVER_PROVENANCE_REQUIRED")
    if admitted.get("extra_layer_resolver_provenance_method") != "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION":
        raise W3ProofPlaneAdmissionError("PR409_PROVENANCE_METHOD_MISMATCH")
    if admitted.get("g2_admitted") or admitted.get("runtime_execution_proven") or admitted.get("large_checkpoint_admitted"):
        raise W3ProofPlaneAdmissionError("PR409_EFFECT_CEILING_WIDENED")
    return snapshot, report, evidence, admitted


@dataclass(frozen=True)
class W3RegisteredAdmissionReceipt:
    status: str
    blockers: tuple[str, ...]
    w2_consumer_receipt_id: str
    official_w2_bound_plan_digest: str
    pr340_registry_schema: str
    pr340_producer_execution_head: str
    pr340_producer_run_id: str
    pr340_producer_job_id: str
    pr340_final_report_digest: str
    pr340_classification_stage_logical_id: str
    pr340_snapshot_digest: str
    official_mtp_source_evidence_id: str
    official_mtp_source_bundle_id: str
    pr340_producer_report_registered: bool = True
    pr409_producer_and_source_appraisal_proven: bool = True
    synthetic_tiny_fixture_admitted: bool = True
    official_tensor_payload_admitted: bool = False
    runtime_mtp_support_proven: bool = False
    runtime_execution_admitted: bool = False
    checkpoint_payload_admitted: bool = False
    provider_effect_admitted: bool = False
    g2_admitted: bool = False
    quality_proven: bool = False
    authority: bool = False
    schema: str = SCHEMA

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "status": self.status,
            "blockers": list(self.blockers),
            "w2_consumer_receipt_id": self.w2_consumer_receipt_id,
            "official_w2_bound_plan_digest": self.official_w2_bound_plan_digest,
            "pr340_registry_schema": self.pr340_registry_schema,
            "pr340_producer_execution_head": self.pr340_producer_execution_head,
            "pr340_producer_run_id": self.pr340_producer_run_id,
            "pr340_producer_job_id": self.pr340_producer_job_id,
            "pr340_final_report_digest": self.pr340_final_report_digest,
            "pr340_classification_stage_logical_id": self.pr340_classification_stage_logical_id,
            "pr340_snapshot_digest": self.pr340_snapshot_digest,
            "official_mtp_source_evidence_id": self.official_mtp_source_evidence_id,
            "official_mtp_source_bundle_id": self.official_mtp_source_bundle_id,
            "pr340_producer_report_registered": True,
            "pr409_producer_and_source_appraisal_proven": True,
            "synthetic_tiny_fixture_admitted": True,
            "official_tensor_payload_admitted": False,
            "runtime_mtp_support_proven": False,
            "runtime_execution_admitted": False,
            "checkpoint_payload_admitted": False,
            "provider_effect_admitted": False,
            "g2_admitted": False,
            "quality_proven": False,
            "authority": False,
        }


def evaluate_w3_proof_plane_admission(
    *,
    pager_plan: Any,
    airllm_security_evidence: Mapping[str, Any],
    glm53_metadata_evidence: Mapping[str, Any],
    read_full: Callable[[str, int], bytes] = urllib_read_full,
) -> W3RegisteredAdmissionReceipt:
    try:
        base = evaluate_w3_official_producer_admission(
            pager_plan=pager_plan,
            airllm_security_evidence=airllm_security_evidence,
            glm53_metadata_evidence=glm53_metadata_evidence,
        )
    except W3OfficialProducerAdmissionError as exc:
        raise W3ProofPlaneAdmissionError("W2_PRODUCER_CONSUMER_ADMISSION_FAILED", exc.code) from exc

    if glm53_metadata_evidence.get("resolver_provenance_proven") is not False:
        raise W3ProofPlaneAdmissionError("CALLER_MTP_PROVENANCE_WIDENING_FORBIDDEN")
    if tuple(base.blockers) != (PROVENANCE_BLOCKER,):
        raise W3ProofPlaneAdmissionError("W3_PRE_MTP_BLOCKERS_REMAIN", ",".join(base.blockers))

    snapshot, _report, evidence, _admitted = _observe_registered_pr340(read_full=read_full)
    return W3RegisteredAdmissionReceipt(
        status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        w2_consumer_receipt_id=base.logical_id,
        official_w2_bound_plan_digest=base.official_w2_bound_plan_digest,
        pr340_registry_schema=registry.REGISTRY_SCHEMA,
        pr340_producer_execution_head=registry.PRODUCER_EXECUTION_HEAD,
        pr340_producer_run_id=registry.PRODUCER_RUN_ID,
        pr340_producer_job_id=registry.PRODUCER_JOB_ID,
        pr340_final_report_digest=snapshot.final_report_digest,
        pr340_classification_stage_logical_id=snapshot.classification_stage_logical_id,
        pr340_snapshot_digest=snapshot.snapshot_digest,
        official_mtp_source_evidence_id=evidence.evidence_id,
        official_mtp_source_bundle_id=evidence.source_bundle_id,
    )
