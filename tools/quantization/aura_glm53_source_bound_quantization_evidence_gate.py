#!/usr/bin/env python3
"""Source-bound quantization evidence gate for GLM-5.3.

Q7 is derived from exactly two fresh exact-green other-agent artifacts:
- Q5 / PR639 official quantization source admission; and
- Q6 / PR640 representation-exact quantization evidence transfer.

The gate prevents either parent from laundering the other's missing evidence.
A known official model/index object is not current raw-byte residency, and valid
quantization evidence is not transferable merely because two schemes share an
E8-family label.

Q5's exact source owner is materialized into this tree and traversed through
``current_public_state()``. Historical official W2 evidence is consumed through
the exact-green PR646 bridge blob/generation, not reconstructed inside Q7.
Historical producer evidence constrains current reasoning but never impersonates
current Q5 raw-byte residency.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.quantization.aura_glm53_historical_official_w2_bridge import (
    HistoricalOfficialW2BridgeReceipt,
    PR398_DRIVE_OBSERVATION as HISTORICAL_W2_DRIVE_OBSERVATION,
    PR398_EXPERT as HISTORICAL_W2_EXPERT_ID,
    PR398_HEAD as HISTORICAL_W2_PRODUCER_HEAD,
    PR398_HEADER_SHA256 as HISTORICAL_W2_HEADER_SHA256,
    PR398_JOB as HISTORICAL_W2_JOB,
    PR398_LAYER as HISTORICAL_W2_LAYER_ID,
    PR398_RECEIPT_DIGEST as HISTORICAL_W2_RECEIPT_DIGEST,
    PR398_RUN as HISTORICAL_W2_RUN,
    PR398_SHARD as HISTORICAL_W2_SHARD,
    VERSION as HISTORICAL_BRIDGE_VERSION,
    build_historical_official_w2_bridge,
    canonical_pr398_observation,
)
from tools.quantization.aura_glm53_official_source_admission import (
    AdmissionState,
    OFFICIAL_COMMIT,
    OFFICIAL_INDEX_SHA256,
    OFFICIAL_INDEX_SIZE,
    OFFICIAL_INDEX_XET_HASH,
    OFFICIAL_REPO,
    PR628_E8_PAGE_ARTIFACT_SHA,
    PR628_E8_PAGE_SCHEME,
    current_public_state,
)
from tools.quantization.aura_glm53_quantization_evidence_transfer import (
    SYNTHETIC_DISTORTION_SCOPE,
    q4_to_q5_disposition,
)

VERSION = "AURA_GLM53_SOURCE_BOUND_QUANTIZATION_EVIDENCE_GATE_V5"

Q5_EXACT_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
Q5_EXACT_RUN = 33369967425
Q5_OWNER_BLOB_SHA = "7ed09c57699fe303f555a3b6bdaadb791c64223f"
Q6_EXACT_HEAD = "4137aabd972feff9c4412bb4786ef8fd4de207e0"
Q6_EXACT_RUN = 33370305329

# Exact-green historical bridge owner generation, independently revalidated by
# GitHub Actions run 33371459229. The mutable PR646 tip may move without changing
# this pinned semantic owner.
HISTORICAL_BRIDGE_OWNER_HEAD = "71d4816cf0702a39b57ecf7d6bae6298ec239800"
HISTORICAL_BRIDGE_OWNER_RUN = 33371459229
HISTORICAL_BRIDGE_OWNER_BLOB_SHA = "77a90ea9f5a438aa438103acd4de05432fe7875a"

OFFICIAL_REPOSITORY = OFFICIAL_REPO
OFFICIAL_REVISION = OFFICIAL_COMMIT
Q5_CANDIDATE_PARENT_SHA = PR628_E8_PAGE_ARTIFACT_SHA
Q5_CANDIDATE_SCHEME = PR628_E8_PAGE_SCHEME
Q5_CURRENT_SOURCE_STATE_DIGEST = "583965be30974da13e1bc0cc895cdd2307afc3650fb34ea30e28c45c403094b0"
Q5_CURRENT_BLOCKER = "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class SourceBoundEvidenceGate:
    version: str
    q5_source_head: str
    q5_source_run: int
    q5_source_owner_blob: str
    q6_evidence_head: str
    q6_evidence_run: int
    official_repository: str
    official_revision: str
    official_index_sha256: str
    official_index_size: int
    official_index_xet_hash: str
    source_state_digest: str
    current_source_index_bytes_verified: bool
    current_source_headers_observed: bool
    current_source_header_trial_eligible: bool
    current_source_tensor_payload_bound: bool
    historical_bridge_version: str
    historical_bridge_owner_head: str
    historical_bridge_owner_run: int
    historical_bridge_owner_blob: str
    historical_bridge_digest: str
    historical_official_index_relation_observed: bool
    historical_official_headers_observed: bool
    historical_official_fp8_companions_bound: bool
    historical_observation_representative_only: bool
    historical_producer_head: str
    historical_producer_run: int
    historical_producer_job: int
    historical_drive_observation: str
    historical_receipt_digest: str
    historical_layer_id: int
    historical_expert_id: int
    historical_shard: str
    historical_header_sha256: str
    historical_entry_count: int
    historical_payload_bytes_read: int
    historical_evidence_implies_current_raw_bytes: bool
    historical_evidence_implies_global_layout_uniformity: bool
    transfer_disposition_digest: str
    source_evidence_scope: str
    exact_representation_identity_match: bool
    geometry_family_label_match: bool
    source_bound_evidence_admitted: bool
    disposition: str
    independent_current_source_transport_residual: bool
    independent_representation_evidence_residual: bool
    glm53_tensor_evidence_admitted: bool
    coding_quality_evidence_admitted: bool
    runtime_evidence_admitted: bool
    semantic_k27_authority_minted: bool
    native_transformer_kv_accessed: bool
    gate10_promoted: bool

    @property
    def gate_digest(self) -> str:
        return _sha(asdict(self))


def _current_q5_snapshot() -> AdmissionState:
    """Traverse the materialized exact Q5 producer; do not reconstruct it."""
    return current_public_state()


def _current_historical_bridge() -> HistoricalOfficialW2BridgeReceipt:
    """Traverse the exact-green materialized PR646 producer; do not copy its state."""
    return build_historical_official_w2_bridge(canonical_pr398_observation())


def _validate_source_snapshot(source: AdmissionState) -> None:
    if type(source) is not AdmissionState:
        raise ValueError("Q5_TYPED_SOURCE_STATE_REQUIRED")
    if source.schema != "AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1":
        raise ValueError("Q5_SOURCE_SCHEMA_MISMATCH")
    if source.official_repository != OFFICIAL_REPOSITORY or source.official_revision != OFFICIAL_REVISION:
        raise ValueError("Q5_OFFICIAL_SOURCE_GENERATION_MISMATCH")
    if source.candidate_parent_sha != Q5_CANDIDATE_PARENT_SHA or source.candidate_scheme != Q5_CANDIDATE_SCHEME:
        raise ValueError("Q5_CANDIDATE_REPRESENTATION_MISMATCH")
    if source.semantic_k27_authority or source.native_transformer_kv_accessed or source.gate10_promoted:
        raise ValueError("Q5_AUTHORITY_CEILING_WIDENED")
    if not source.config_profile_bound or not source.index_object_identity_bound or not source.candidate_representation_bound:
        raise ValueError("Q5_BASELINE_BINDING_MISSING")
    if not source.index_bytes_verified:
        forbidden = (
            source.representative_key_to_shard_bound,
            source.representative_headers_observed,
            source.fp8_companions_bound,
            source.header_trial_eligible,
            source.source_tensor_payload_bound,
            source.real_tensor_quantization_eligible,
        )
        if any(forbidden):
            raise ValueError("Q5_SOURCE_EVIDENCE_ORDER_VIOLATION")
    if source.header_trial_eligible and not (
        source.index_bytes_verified
        and source.representative_key_to_shard_bound
        and source.representative_headers_observed
        and source.fp8_companions_bound
    ):
        raise ValueError("Q5_HEADER_TRIAL_PRECONDITIONS_MISSING")
    if source.real_tensor_quantization_eligible and not (
        source.header_trial_eligible and source.source_tensor_payload_bound
    ):
        raise ValueError("Q5_REAL_TENSOR_PRECONDITIONS_MISSING")


def _validate_historical_bridge(bridge: HistoricalOfficialW2BridgeReceipt) -> None:
    if type(bridge) is not HistoricalOfficialW2BridgeReceipt:
        raise ValueError("HISTORICAL_BRIDGE_TYPED_RECEIPT_REQUIRED")
    if bridge.version != HISTORICAL_BRIDGE_VERSION:
        raise ValueError("HISTORICAL_BRIDGE_VERSION_MISMATCH")
    if bridge.parent_heads != (Q5_EXACT_HEAD, HISTORICAL_W2_PRODUCER_HEAD):
        raise ValueError("HISTORICAL_BRIDGE_PARENT_HEAD_MISMATCH")
    if bridge.parent_runs != (Q5_EXACT_RUN, HISTORICAL_W2_RUN):
        raise ValueError("HISTORICAL_BRIDGE_PARENT_RUN_MISMATCH")
    if bridge.producer_job != HISTORICAL_W2_JOB or bridge.producer_drive_observation != HISTORICAL_W2_DRIVE_OBSERVATION:
        raise ValueError("HISTORICAL_BRIDGE_PRODUCER_IDENTITY_MISMATCH")
    if bridge.producer_receipt_digest != HISTORICAL_W2_RECEIPT_DIGEST:
        raise ValueError("HISTORICAL_BRIDGE_RECEIPT_MISMATCH")
    if bridge.producer_header_sha256 != HISTORICAL_W2_HEADER_SHA256:
        raise ValueError("HISTORICAL_BRIDGE_HEADER_DIGEST_MISMATCH")
    if not (
        bridge.historical_raw_index_verification_observed
        and bridge.historical_weight_map_relation_observed
        and bridge.historical_representative_headers_observed
        and bridge.historical_fp8_companions_bound
        and bridge.current_pr639_schema_header_geometry_conforms
        and bridge.representative_per_expert_serialization_proven
    ):
        raise ValueError("HISTORICAL_BRIDGE_REQUIRED_CONSEQUENCE_MISSING")
    forbidden = (
        bridge.all_layers_experts_uniformity_proven,
        bridge.current_consumer_raw_index_bytes_materialized,
        bridge.current_consumer_raw_header_prefixes_materialized,
        bridge.current_pr639_raw_byte_header_trial_eligible,
        bridge.source_tensor_payload_bound,
        bridge.real_tensor_quantization_eligible,
        bridge.semantic_k27_authority,
        bridge.native_transformer_kv_accessed,
        bridge.gate10_promoted,
    )
    if any(forbidden):
        raise ValueError("HISTORICAL_BRIDGE_CEILING_WIDENED")


def _evaluate(source: AdmissionState) -> SourceBoundEvidenceGate:
    _validate_source_snapshot(source)
    bridge = _current_historical_bridge()
    _validate_historical_bridge(bridge)
    transfer = q4_to_q5_disposition()

    current_source_transport_residual = not (
        source.index_bytes_verified
        and source.representative_headers_observed
        and source.header_trial_eligible
    )
    representation_residual = not transfer.exact_representation_identity_match
    admitted = not current_source_transport_residual and not representation_residual

    if current_source_transport_residual and representation_residual:
        disposition = "HOLD_CURRENT_SOURCE_TRANSPORT_AND_REPRESENTATION_EVIDENCE"
    elif current_source_transport_residual:
        disposition = "HOLD_CURRENT_OFFICIAL_SOURCE_TRANSPORT"
    elif representation_residual:
        disposition = "HOLD_REPRESENTATION_EXACT_EVIDENCE"
    else:
        disposition = "HEADER_BOUND_SYNTHETIC_EVIDENCE_ONLY"

    return SourceBoundEvidenceGate(
        version=VERSION,
        q5_source_head=Q5_EXACT_HEAD,
        q5_source_run=Q5_EXACT_RUN,
        q5_source_owner_blob=Q5_OWNER_BLOB_SHA,
        q6_evidence_head=Q6_EXACT_HEAD,
        q6_evidence_run=Q6_EXACT_RUN,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        official_index_sha256=OFFICIAL_INDEX_SHA256,
        official_index_size=OFFICIAL_INDEX_SIZE,
        official_index_xet_hash=OFFICIAL_INDEX_XET_HASH,
        source_state_digest=source.digest(),
        current_source_index_bytes_verified=source.index_bytes_verified,
        current_source_headers_observed=source.representative_headers_observed,
        current_source_header_trial_eligible=source.header_trial_eligible,
        current_source_tensor_payload_bound=source.source_tensor_payload_bound,
        historical_bridge_version=bridge.version,
        historical_bridge_owner_head=HISTORICAL_BRIDGE_OWNER_HEAD,
        historical_bridge_owner_run=HISTORICAL_BRIDGE_OWNER_RUN,
        historical_bridge_owner_blob=HISTORICAL_BRIDGE_OWNER_BLOB_SHA,
        historical_bridge_digest=bridge.digest,
        historical_official_index_relation_observed=bridge.historical_weight_map_relation_observed,
        historical_official_headers_observed=bridge.historical_representative_headers_observed,
        historical_official_fp8_companions_bound=bridge.historical_fp8_companions_bound,
        historical_observation_representative_only=not bridge.all_layers_experts_uniformity_proven,
        historical_producer_head=bridge.parent_heads[1],
        historical_producer_run=bridge.parent_runs[1],
        historical_producer_job=bridge.producer_job,
        historical_drive_observation=bridge.producer_drive_observation,
        historical_receipt_digest=bridge.producer_receipt_digest,
        historical_layer_id=bridge.representative_layer,
        historical_expert_id=bridge.representative_expert,
        historical_shard=bridge.representative_shard,
        historical_header_sha256=bridge.producer_header_sha256,
        historical_entry_count=6,
        historical_payload_bytes_read=bridge.historical_payload_bytes_read,
        historical_evidence_implies_current_raw_bytes=bridge.current_consumer_raw_index_bytes_materialized,
        historical_evidence_implies_global_layout_uniformity=bridge.all_layers_experts_uniformity_proven,
        transfer_disposition_digest=transfer.disposition_digest,
        source_evidence_scope=transfer.source_evidence_scope,
        exact_representation_identity_match=transfer.exact_representation_identity_match,
        geometry_family_label_match=transfer.geometry_family_label_match,
        source_bound_evidence_admitted=admitted,
        disposition=disposition,
        independent_current_source_transport_residual=current_source_transport_residual,
        independent_representation_evidence_residual=representation_residual,
        glm53_tensor_evidence_admitted=False,
        coding_quality_evidence_admitted=False,
        runtime_evidence_admitted=False,
        semantic_k27_authority_minted=False,
        native_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def current_source_bound_evidence_gate() -> SourceBoundEvidenceGate:
    """Return the exact current Q5 x Q6 consequence with no caller overrides."""
    source = _current_q5_snapshot()
    if source.digest() != Q5_CURRENT_SOURCE_STATE_DIGEST:
        raise AssertionError("Q5_CURRENT_SOURCE_STATE_DIGEST_DRIFT")
    if source.blocker != Q5_CURRENT_BLOCKER:
        raise AssertionError("Q5_CURRENT_BLOCKER_DRIFT")
    return _evaluate(source)


def main() -> None:
    gate = current_source_bound_evidence_gate()
    print(json.dumps({**asdict(gate), "gate_digest": gate.gate_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
