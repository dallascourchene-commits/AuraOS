#!/usr/bin/env python3
"""Fail-closed bridge from quantized trial evidence to official GLM-5.3 source evidence.

This module composes two exact parent evidence domains without promoting either:
- PR629 V2: matched frozen-corpus quantized-representation trial evidence;
- PR639: official GLM-5.3 source admission.

A trial can be internally comparable at one model/topology/static-byte domain while
still lacking any proof that the compared bytes came from the current official source
generation.  Likewise, a future header-eligible official source does not prove that a
candidate representation was materialized from those exact source tensors.
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

VERSION = "AURA_GLM53_OFFICIAL_SOURCE_TRIAL_BRIDGE_V1"
PR629_EXACT_SHA = "475fc346670bc56951ee6e4262bf23af00f70b7b"
PR629_EXACT_RUN = 33369419860
PR639_EXACT_SHA = "730426b82235b0ff4e75fef1cff00707877a84ad"
PR639_EXACT_RUN = 33369967425


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class OfficialSourceTrialBridgeReceipt:
    schema: str
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


def _validate_source_state(state: AdmissionState) -> None:
    if state.official_repository != OFFICIAL_REPO or state.official_revision != OFFICIAL_COMMIT:
        raise ValueError("OFFICIAL_SOURCE_IDENTITY_MISMATCH")
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


def classify_official_source_trial(
    *,
    source_state: AdmissionState,
    request: QuantizedTrialRequest,
    comparison: QuantizedRepresentationComparison,
) -> OfficialSourceTrialBridgeReceipt:
    """Classify only the evidence intersection that both parents actually support.

    V1 deliberately has no path to official-source trial admission because neither
    parent supplies a typed relation from official source bytes/tensors to PR629's
    candidate representation digest/static-byte manifest.  A later producer-owner
    membrane must add that observation boundary rather than setting a boolean here.
    """
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

    # Neither exact parent proves either cross-domain relation below.
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

    admissible = False
    return OfficialSourceTrialBridgeReceipt(
        schema=VERSION,
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
        official_source_trial_admissible=admissible,
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
    """Apply the current exact PR639 public HOLD state to one PR629 trial."""
    return classify_official_source_trial(
        source_state=current_public_state(), request=request, comparison=comparison
    )
