#!/usr/bin/env python3
"""Fail-closed bridge from quantized trial evidence to official GLM-5.3 source evidence.

The public bridge traverses PR639's exact materialized source producer itself.
Synthetic future AdmissionState values remain useful for adversarial transition
tests, but are explicitly marked synthetic/non-producer evidence and can never
become evidence merely by reaching a deeper HOLD label.

Core law:
    HoldDispositionDepth != EvidenceAdvance.
Only a producer-traversed change in the underlying source evidence vector may
advance the evidence frontier.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.quantization.aura_glm53_official_source_admission import (
    AdmissionState,
    OFFICIAL_COMMIT,
    OFFICIAL_REPO,
    current_public_state,
)
from tools.quantization.aura_glm53_quantized_representation_trial import (
    QuantizedRepresentationComparison,
    QuantizedTrialRequest,
    VERSION as TRIAL_VERSION,
)

VERSION = "AURA_GLM53_OFFICIAL_SOURCE_TRIAL_BRIDGE_V2"
PR629_EXACT_SHA = "475fc346670bc56951ee6e4262bf23af00f70b7b"
PR629_EXACT_RUN = 33369419860
PR629_TRIAL_BLOB_SHA = "3985095e122e9d3a7867452c6ae0fdba41d200f1"
PR639_EXACT_SHA = "730426b82235b0ff4e75fef1cff00707877a84ad"
PR639_EXACT_RUN = 33369967425
PR639_SOURCE_BLOB_SHA = "7ed09c57699fe303f555a3b6bdaadb791c64223f"

SOURCE_EVIDENCE_VECTOR_ORDER = (
    "config_profile_bound",
    "index_object_identity_bound",
    "index_bytes_verified",
    "representative_key_to_shard_bound",
    "representative_headers_observed",
    "fp8_companions_bound",
    "source_tensor_payload_bound",
)

__all__ = (
    "OfficialSourceTrialBridgeReceipt",
    "current_official_source_trial_hold",
)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _source_evidence_vector(state: AdmissionState) -> tuple[bool, ...]:
    return tuple(bool(getattr(state, name)) for name in SOURCE_EVIDENCE_VECTOR_ORDER)


def _validate_source_state(state: AdmissionState) -> None:
    if type(state) is not AdmissionState:
        raise ValueError("Q5_TYPED_ADMISSION_STATE_REQUIRED")
    if state.official_repository != OFFICIAL_REPO or state.official_revision != OFFICIAL_COMMIT:
        raise ValueError("OFFICIAL_SOURCE_IDENTITY_MISMATCH")
    if state.semantic_k27_authority or state.native_transformer_kv_accessed or state.gate10_promoted:
        raise ValueError("SOURCE_AUTHORITY_CEILING_WIDENED")
    header_prereqs = (
        state.config_profile_bound,
        state.index_object_identity_bound,
        state.index_bytes_verified,
        state.representative_key_to_shard_bound,
        state.representative_headers_observed,
        state.fp8_companions_bound,
        state.candidate_representation_bound,
    )
    if state.header_trial_eligible and not all(header_prereqs):
        raise ValueError("HEADER_ELIGIBILITY_PREREQUISITE_MISMATCH")
    if state.real_tensor_quantization_eligible and not (
        state.header_trial_eligible and state.source_tensor_payload_bound
    ):
        raise ValueError("REAL_TENSOR_ELIGIBILITY_PREREQUISITE_MISMATCH")


@dataclass(frozen=True)
class OfficialSourceTrialBridgeReceipt:
    schema: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    q5_source_blob_sha: str
    q3_trial_blob_sha: str
    source_producer_traversed: bool
    source_state_synthetic: bool
    source_evidence_vector_order: tuple[str, ...]
    source_evidence_vector: tuple[bool, ...]
    source_evidence_vector_digest: str
    hold_disposition_is_evidence: bool
    source_admission_digest: str
    trial_request_digest: str
    trial_comparison_digest: str
    official_repository: str
    official_revision: str
    model_revision_matches_official_source: bool
    trial_internal_byte_domain_bound: bool
    official_source_headers_trial_eligible: bool
    official_source_tensor_payload_bound: bool
    official_source_real_tensor_quantization_eligible: bool
    official_source_byte_domain_bound_to_trial: bool
    candidate_materialization_owner_bound: bool
    official_source_trial_admissible: bool
    disposition: str
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    owner_host_authenticated: bool
    physical_io_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _digest(asdict(self))


def _classify_source_state_for_test(
    *,
    source_state: AdmissionState,
    request: QuantizedTrialRequest,
    comparison: QuantizedRepresentationComparison,
    source_producer_traversed: bool = False,
) -> OfficialSourceTrialBridgeReceipt:
    """Internal transition/falsification helper; synthetic state is not admission evidence."""
    _validate_source_state(source_state)
    request.validate()
    req_digest = request.request_digest
    if comparison.version != TRIAL_VERSION:
        raise ValueError("TRIAL_SCHEMA_MISMATCH")
    if comparison.request_digest != req_digest:
        raise ValueError("TRIAL_REQUEST_BINDING_MISMATCH")
    if comparison.static_weight_byte_domain != request.baseline.static_weight_byte_domain:
        raise ValueError("TRIAL_BYTE_DOMAIN_MISMATCH")
    if comparison.static_weight_byte_domain_digest != request.baseline.static_weight_byte_domain_digest:
        raise ValueError("TRIAL_BYTE_DOMAIN_MANIFEST_MISMATCH")

    model_match = (
        request.baseline.model_revision == source_state.official_revision
        and request.candidate.model_revision == source_state.official_revision
    )
    trial_internal_byte_domain_bound = (
        request.baseline.static_weight_byte_domain == request.candidate.static_weight_byte_domain
        and request.baseline.static_weight_byte_domain_digest
        == request.candidate.static_weight_byte_domain_digest
    )

    vector = _source_evidence_vector(source_state)
    vector_digest = _digest(
        {name: value for name, value in zip(SOURCE_EVIDENCE_VECTOR_ORDER, vector)}
    )

    official_source_byte_domain_bound_to_trial = False
    candidate_materialization_owner_bound = False

    if not model_match:
        disposition = "HOLD_MODEL_REVISION_NOT_OFFICIAL_SOURCE"
    elif not source_state.header_trial_eligible:
        disposition = "HOLD_OFFICIAL_INDEX_HEADER_EVIDENCE"
    elif not source_state.source_tensor_payload_bound:
        disposition = "HOLD_OFFICIAL_SOURCE_TENSOR_PAYLOAD"
    elif not source_state.real_tensor_quantization_eligible:
        disposition = "HOLD_OFFICIAL_REAL_TENSOR_QUANTIZATION"
    elif not official_source_byte_domain_bound_to_trial:
        disposition = "HOLD_OFFICIAL_SOURCE_TO_TRIAL_BYTE_DOMAIN_RELATION"
    else:
        disposition = "HOLD_CANDIDATE_MATERIALIZATION_OWNER_RELATION"

    return OfficialSourceTrialBridgeReceipt(
        schema=VERSION,
        exact_parent_heads=(PR639_EXACT_SHA, PR629_EXACT_SHA),
        exact_parent_runs=(PR639_EXACT_RUN, PR629_EXACT_RUN),
        q5_source_blob_sha=PR639_SOURCE_BLOB_SHA,
        q3_trial_blob_sha=PR629_TRIAL_BLOB_SHA,
        source_producer_traversed=source_producer_traversed,
        source_state_synthetic=not source_producer_traversed,
        source_evidence_vector_order=SOURCE_EVIDENCE_VECTOR_ORDER,
        source_evidence_vector=vector,
        source_evidence_vector_digest=vector_digest,
        hold_disposition_is_evidence=False,
        source_admission_digest=source_state.digest(),
        trial_request_digest=req_digest,
        trial_comparison_digest=comparison.comparison_digest,
        official_repository=source_state.official_repository,
        official_revision=source_state.official_revision,
        model_revision_matches_official_source=model_match,
        trial_internal_byte_domain_bound=trial_internal_byte_domain_bound,
        official_source_headers_trial_eligible=source_state.header_trial_eligible,
        official_source_tensor_payload_bound=source_state.source_tensor_payload_bound,
        official_source_real_tensor_quantization_eligible=source_state.real_tensor_quantization_eligible,
        official_source_byte_domain_bound_to_trial=official_source_byte_domain_bound_to_trial,
        candidate_materialization_owner_bound=candidate_materialization_owner_bound,
        official_source_trial_admissible=False,
        disposition=disposition,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        owner_host_authenticated=False,
        physical_io_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def current_official_source_trial_hold(
    *, request: QuantizedTrialRequest, comparison: QuantizedRepresentationComparison
) -> OfficialSourceTrialBridgeReceipt:
    """Traverse the exact Q5 producer and classify one exact PR629 trial at the current source frontier."""
    return _classify_source_state_for_test(
        source_state=current_public_state(),
        request=request,
        comparison=comparison,
        source_producer_traversed=True,
    )
