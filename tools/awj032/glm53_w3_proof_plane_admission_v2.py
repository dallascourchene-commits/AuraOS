"""W3 proof-plane admission over official W2 producer proof + official immutable MTP source.

D0/nonpromoting. The consumer first traverses PR410's W2 producer-consumption
membrane. Only when that plane is otherwise blocked solely on the MTP provenance
blocker does it independently observe the immutable official GLM-5.3 config/index
through the PR409 appraiser. Positive output admits only the bounded native
synthetic W3 fixture; it never admits official tensor payload, runtime MTP support,
G2, provider effects, checkpoint materialization, authority, merge, or deployment.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping

from tools.awj032.glm53_official_mtp_role_source_appraiser import (
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_MTP_LAYER,
    OFFICIAL_NUM_HIDDEN_LAYERS,
    OFFICIAL_NUM_NEXTN_PREDICT_LAYERS,
    OFFICIAL_REPO,
    OFFICIAL_REVISION,
    OFFICIAL_ROLE,
    OfficialSourceMTPRoleEvidence,
    observe_official_mtp_role,
)
from tools.awj032.glm53_w3_official_producer_admission import (
    W3OfficialProducerAdmissionError,
    evaluate_w3_official_producer_admission,
)

SCHEMA = "AWJ032GLM53W3ProofPlaneAdmissionV2"
PROVENANCE_BLOCKER = "GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"


class W3ProofPlaneAdmissionError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_official_mtp_evidence(evidence: OfficialSourceMTPRoleEvidence) -> OfficialSourceMTPRoleEvidence:
    if not isinstance(evidence, OfficialSourceMTPRoleEvidence):
        raise W3ProofPlaneAdmissionError("OFFICIAL_MTP_SOURCE_EVIDENCE_REQUIRED")
    if (
        evidence.owner_repo != OFFICIAL_REPO
        or evidence.immutable_model_revision != OFFICIAL_REVISION
        or evidence.index_sha256 != OFFICIAL_INDEX_SHA256
        or evidence.num_hidden_layers != OFFICIAL_NUM_HIDDEN_LAYERS
        or evidence.num_nextn_predict_layers != OFFICIAL_NUM_NEXTN_PREDICT_LAYERS
        or evidence.observed_extra_checkpoint_layer_indices != (OFFICIAL_MTP_LAYER,)
        or evidence.role_index != OFFICIAL_MTP_LAYER
        or evidence.role != OFFICIAL_ROLE
        or evidence.decoder_pager_membership is not False
        or evidence.source_verified is not True
        or not evidence.mtp_marker_keys
        or any(not key.startswith(f"model.layers.{OFFICIAL_MTP_LAYER}.eh_proj") for key in evidence.mtp_marker_keys)
        or evidence.payload_bytes_read != 0
        or evidence.g2_admitted is not False
        or evidence.runtime_executed is not False
        or evidence.authority is not False
    ):
        raise W3ProofPlaneAdmissionError("OFFICIAL_MTP_SOURCE_EVIDENCE_INVARIANT_FAILED")
    return evidence


@dataclass(frozen=True)
class W3ProofPlaneAdmissionReceipt:
    status: str
    blockers: tuple[str, ...]
    w2_consumer_receipt_id: str
    official_w2_bound_plan_digest: str
    official_w2_observation_digest: str
    official_w2_receipt_digest: str
    official_w2_producer_semantic_head: str
    official_mtp_source_evidence_id: str
    official_mtp_source_bundle_id: str
    official_mtp_model_revision: str
    official_mtp_index_sha256: str
    official_mtp_role_index: int
    official_mtp_role: str
    official_w2_producer_proof_consumed: bool = True
    official_mtp_source_role_proven: bool = True
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
            "official_w2_observation_digest": self.official_w2_observation_digest,
            "official_w2_receipt_digest": self.official_w2_receipt_digest,
            "official_w2_producer_semantic_head": self.official_w2_producer_semantic_head,
            "official_mtp_source_evidence_id": self.official_mtp_source_evidence_id,
            "official_mtp_source_bundle_id": self.official_mtp_source_bundle_id,
            "official_mtp_model_revision": self.official_mtp_model_revision,
            "official_mtp_index_sha256": self.official_mtp_index_sha256,
            "official_mtp_role_index": self.official_mtp_role_index,
            "official_mtp_role": self.official_mtp_role,
            "official_w2_producer_proof_consumed": True,
            "official_mtp_source_role_proven": True,
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


def _reduce_with_observed_source(base: Any, evidence: OfficialSourceMTPRoleEvidence) -> W3ProofPlaneAdmissionReceipt:
    blockers = tuple(base.blockers)
    if blockers != (PROVENANCE_BLOCKER,):
        raise W3ProofPlaneAdmissionError("W3_PRE_MTP_BLOCKERS_REMAIN", ",".join(blockers))
    observed = _validate_official_mtp_evidence(evidence)
    return W3ProofPlaneAdmissionReceipt(
        status="ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE",
        blockers=(),
        w2_consumer_receipt_id=base.logical_id,
        official_w2_bound_plan_digest=base.official_w2_bound_plan_digest,
        official_w2_observation_digest=base.official_w2_observation_digest,
        official_w2_receipt_digest=base.official_w2_receipt_digest,
        official_w2_producer_semantic_head=base.official_w2_producer_semantic_head,
        official_mtp_source_evidence_id=observed.evidence_id,
        official_mtp_source_bundle_id=observed.source_bundle_id,
        official_mtp_model_revision=observed.immutable_model_revision,
        official_mtp_index_sha256=observed.index_sha256,
        official_mtp_role_index=observed.role_index,
        official_mtp_role=observed.role,
    )


def evaluate_w3_proof_plane_admission(*, pager_plan: Any, airllm_security_evidence: Mapping[str, Any], glm53_metadata_evidence: Mapping[str, Any]) -> W3ProofPlaneAdmissionReceipt:
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

    return _reduce_with_observed_source(base, observe_official_mtp_role())
