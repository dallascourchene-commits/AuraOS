#!/usr/bin/env python3
"""Source-bound quantization evidence gate for GLM-5.3.

Q7 is derived from exactly two fresh exact-green other-agent artifacts:
- Q5 / PR639 official quantization source admission; and
- Q6 / PR640 representation-exact quantization evidence transfer.

The gate prevents either parent from laundering the other's missing evidence.
A known official model/index object is not an observed source tensor, and valid
quantization evidence is not transferable merely because two schemes share an
E8-family label.  The current public path is intentionally zero-input and HOLD.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json

from tools.quantization.aura_glm53_quantization_evidence_transfer import (
    SYNTHETIC_DISTORTION_SCOPE,
    q4_to_q5_disposition,
)

VERSION = "AURA_GLM53_SOURCE_BOUND_QUANTIZATION_EVIDENCE_GATE_V1"

Q5_EXACT_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
Q5_EXACT_RUN = 33369967425
Q6_EXACT_HEAD = "4137aabd972feff9c4412bb4786ef8fd4de207e0"
Q6_EXACT_RUN = 33370305329

OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_INDEX_SIZE = 11_359_251
OFFICIAL_INDEX_XET_HASH = "cc559a187bc99b20039b572a3161f394c51ad19eb2c8eed41371f54740af5f94"

Q5_CANDIDATE_PARENT_SHA = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
Q5_CANDIDATE_SCHEME = "AURA_E8_BALL10_16BIT_REF_V1"
Q5_CURRENT_SOURCE_STATE_DIGEST = "583965be30974da13e1bc0cc895cdd2307afc3650fb34ea30e28c45c403094b0"
Q5_CURRENT_BLOCKER = "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class SourceAdmissionSnapshot:
    schema: str
    official_repository: str
    official_revision: str
    candidate_parent_sha: str
    candidate_scheme: str
    config_profile_bound: bool
    index_object_identity_bound: bool
    index_bytes_verified: bool
    representative_key_to_shard_bound: bool
    representative_headers_observed: bool
    fp8_companions_bound: bool
    candidate_representation_bound: bool
    header_trial_eligible: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    blocker: str
    semantic_k27_authority: bool
    native_transformer_kv_accessed: bool
    gate10_promoted: bool

    @property
    def digest(self) -> str:
        return _sha(asdict(self))


@dataclass(frozen=True)
class SourceBoundEvidenceGate:
    version: str
    q5_source_head: str
    q5_source_run: int
    q6_evidence_head: str
    q6_evidence_run: int
    official_repository: str
    official_revision: str
    official_index_sha256: str
    official_index_size: int
    official_index_xet_hash: str
    source_state_digest: str
    source_index_bytes_verified: bool
    source_headers_observed: bool
    source_header_trial_eligible: bool
    source_tensor_payload_bound: bool
    transfer_disposition_digest: str
    source_evidence_scope: str
    exact_representation_identity_match: bool
    geometry_family_label_match: bool
    source_bound_evidence_admitted: bool
    disposition: str
    independent_source_transport_residual: bool
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


def _current_q5_snapshot() -> SourceAdmissionSnapshot:
    return SourceAdmissionSnapshot(
        schema="AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1",
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        candidate_parent_sha=Q5_CANDIDATE_PARENT_SHA,
        candidate_scheme=Q5_CANDIDATE_SCHEME,
        config_profile_bound=True,
        index_object_identity_bound=True,
        index_bytes_verified=False,
        representative_key_to_shard_bound=False,
        representative_headers_observed=False,
        fp8_companions_bound=False,
        candidate_representation_bound=True,
        header_trial_eligible=False,
        source_tensor_payload_bound=False,
        real_tensor_quantization_eligible=False,
        blocker=Q5_CURRENT_BLOCKER,
        semantic_k27_authority=False,
        native_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def _validate_source_snapshot(source: SourceAdmissionSnapshot) -> None:
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


def _evaluate(source: SourceAdmissionSnapshot) -> SourceBoundEvidenceGate:
    _validate_source_snapshot(source)
    transfer = q4_to_q5_disposition()

    source_transport_residual = not (
        source.index_bytes_verified
        and source.representative_headers_observed
        and source.header_trial_eligible
    )
    representation_residual = not transfer.exact_representation_identity_match
    admitted = not source_transport_residual and not representation_residual

    if source_transport_residual and representation_residual:
        disposition = "HOLD_SOURCE_TRANSPORT_AND_REPRESENTATION_EVIDENCE"
    elif source_transport_residual:
        disposition = "HOLD_OFFICIAL_SOURCE_TRANSPORT"
    elif representation_residual:
        disposition = "HOLD_REPRESENTATION_EXACT_EVIDENCE"
    else:
        # Q6's current evidence scope is synthetic distortion only, so even this
        # state remains below GLM tensor/task/runtime evidence.
        disposition = "HEADER_BOUND_SYNTHETIC_EVIDENCE_ONLY"

    return SourceBoundEvidenceGate(
        version=VERSION,
        q5_source_head=Q5_EXACT_HEAD,
        q5_source_run=Q5_EXACT_RUN,
        q6_evidence_head=Q6_EXACT_HEAD,
        q6_evidence_run=Q6_EXACT_RUN,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        official_index_sha256=OFFICIAL_INDEX_SHA256,
        official_index_size=OFFICIAL_INDEX_SIZE,
        official_index_xet_hash=OFFICIAL_INDEX_XET_HASH,
        source_state_digest=source.digest,
        source_index_bytes_verified=source.index_bytes_verified,
        source_headers_observed=source.representative_headers_observed,
        source_header_trial_eligible=source.header_trial_eligible,
        source_tensor_payload_bound=source.source_tensor_payload_bound,
        transfer_disposition_digest=transfer.disposition_digest,
        source_evidence_scope=transfer.source_evidence_scope,
        exact_representation_identity_match=transfer.exact_representation_identity_match,
        geometry_family_label_match=transfer.geometry_family_label_match,
        source_bound_evidence_admitted=admitted,
        disposition=disposition,
        independent_source_transport_residual=source_transport_residual,
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
    if source.digest != Q5_CURRENT_SOURCE_STATE_DIGEST:
        raise AssertionError("Q5_CURRENT_SOURCE_STATE_DIGEST_DRIFT")
    return _evaluate(source)


def main() -> None:
    gate = current_source_bound_evidence_gate()
    print(json.dumps({**asdict(gate), "gate_digest": gate.gate_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
