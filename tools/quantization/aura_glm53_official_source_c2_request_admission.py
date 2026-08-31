#!/usr/bin/env python3
"""Join official GLM-5.3 source admission to the bounded owner-host C2 request.

Derived from two exact-green non-self owners:
- PR639: raw-byte official quantization source/header admission;
- PR582: bounded owner-host C2 canary request/attempt transport.

This module adds only the missing source->C2 admission edge.  It performs no model
execution, downloads no tensor payload, and cannot authorize an effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping

from tools.quantization.aura_glm53_official_source_admission import (
    AdmissionState,
    OFFICIAL_COMMIT,
    OFFICIAL_REPO,
    PR628_E8_PAGE_ARTIFACT_SHA,
    admit_official_header_state,
    current_public_state,
)
from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest

VERSION = "AURA_GLM53_OFFICIAL_SOURCE_C2_REQUEST_ADMISSION_V1"
SOURCE_ADMISSION_HEAD = "730426b82235b0ff4e75fef1cff00707877a84ad"
SOURCE_ADMISSION_RUN = 33369967425
C2_HANDOFF_HEAD = "24a5404ee3b987dee12192917e40b35d3a43e81c"
C2_HANDOFF_RUN = 33360061584


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OfficialSourceC2RequestDisposition:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    source_admission_digest: str
    c2_request_digest: str
    official_repository: str
    official_revision: str
    candidate_parent_sha: str
    candidate_scheme: str
    source_header_trial_eligible: bool
    source_tensor_payload_bound: bool
    real_tensor_quantization_eligible: bool
    c2_request_source_matches: bool
    source_bound_c2_request_admissible: bool
    blocker: str
    execution_authorized_by_this_contract: bool
    owner_host_execution_observed: bool
    physical_io_attested: bool
    lifecycle_producer_authenticated: bool
    g2_admitted: bool
    semantic_k27_authority_minted: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool

    @property
    def disposition_digest(self) -> str:
        return _sha(asdict(self))


def _join_verified_source_state(
    *, source_state: AdmissionState, request: OwnerHostC2CanaryRequest
) -> OfficialSourceC2RequestDisposition:
    """Internal join after PR639 has produced the source state.

    Public callers cannot pass booleans to mint source admission; the public raw
    path below calls PR639's byte-recomputing admission function first.
    """
    if source_state.schema != "AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1":
        raise ValueError("SOURCE_ADMISSION_SCHEMA_MISMATCH")
    if source_state.official_repository != OFFICIAL_REPO or source_state.official_revision != OFFICIAL_COMMIT:
        raise ValueError("OFFICIAL_SOURCE_GENERATION_MISMATCH")
    if source_state.candidate_parent_sha != PR628_E8_PAGE_ARTIFACT_SHA:
        raise ValueError("CANDIDATE_PARENT_MISMATCH")
    source_matches = request.model_repo == source_state.official_repository and request.model_revision == source_state.official_revision
    if not source_matches:
        raise ValueError("C2_REQUEST_OFFICIAL_SOURCE_MISMATCH")
    if request.execution_authorized_by_this_contract or request.g2_admitted:
        raise ValueError("C2_REQUEST_AUTHORITY_WIDENING")

    admitted = bool(
        source_state.config_profile_bound
        and source_state.index_object_identity_bound
        and source_state.index_bytes_verified
        and source_state.representative_key_to_shard_bound
        and source_state.representative_headers_observed
        and source_state.fp8_companions_bound
        and source_state.candidate_representation_bound
        and source_state.header_trial_eligible
    )
    blocker = "NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE" if admitted else source_state.blocker
    return OfficialSourceC2RequestDisposition(
        version=VERSION,
        exact_parent_heads=(SOURCE_ADMISSION_HEAD, C2_HANDOFF_HEAD),
        exact_parent_runs=(SOURCE_ADMISSION_RUN, C2_HANDOFF_RUN),
        source_admission_digest=source_state.digest(),
        c2_request_digest=request.request_digest,
        official_repository=source_state.official_repository,
        official_revision=source_state.official_revision,
        candidate_parent_sha=source_state.candidate_parent_sha,
        candidate_scheme=source_state.candidate_scheme,
        source_header_trial_eligible=source_state.header_trial_eligible,
        source_tensor_payload_bound=source_state.source_tensor_payload_bound,
        real_tensor_quantization_eligible=source_state.real_tensor_quantization_eligible,
        c2_request_source_matches=source_matches,
        source_bound_c2_request_admissible=admitted,
        blocker=blocker,
        execution_authorized_by_this_contract=False,
        owner_host_execution_observed=False,
        physical_io_attested=False,
        lifecycle_producer_authenticated=False,
        g2_admitted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def current_public_source_c2_disposition(
    request: OwnerHostC2CanaryRequest,
) -> OfficialSourceC2RequestDisposition:
    """Evaluate the current public evidence without caller-authored admission flags."""
    return _join_verified_source_state(source_state=current_public_state(), request=request)


def admit_source_bound_c2_request(
    *,
    request: OwnerHostC2CanaryRequest,
    config: Mapping[str, object],
    index_bytes: bytes,
    expert_prefix: str,
    shard_header_prefixes: Mapping[str, bytes],
    candidate_parent_sha: str,
) -> OfficialSourceC2RequestDisposition:
    """Strong public path: recompute PR639 source admission from raw evidence, then join C2."""
    state = admit_official_header_state(
        config,
        index_bytes,
        expert_prefix,
        shard_header_prefixes,
        candidate_parent_sha=candidate_parent_sha,
    )
    return _join_verified_source_state(source_state=state, request=request)


def deterministic_request_fixture() -> OwnerHostC2CanaryRequest:
    """Software-only fixture for the current HOLD receipt, never an execution request."""
    return OwnerHostC2CanaryRequest(
        w3_proof_logical_id="1" * 64,
        preflight_receipt_digest="2" * 64,
        airllm_source_revision="airllm-pinned-fixture",
        airllm_security_evidence_digest="3" * 64,
        host_snapshot_digest="4" * 64,
        storage_plan_digest="5" * 64,
        workspace_root="/tmp/aura-glm53-c2-fixture",
        max_payload_bytes=1_048_576,
        max_wall_seconds=60,
        effect_admission_ref="D0-NONAUTHORIZING-FIXTURE",
    )


def main() -> None:
    out = current_public_source_c2_disposition(deterministic_request_fixture())
    print(json.dumps({**asdict(out), "disposition_digest": out.disposition_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
