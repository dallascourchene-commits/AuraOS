#!/usr/bin/env python3
"""Refine Q8 provenance with the exact historical PR398 official-header observation.

This child closes only the representative historical index/header transport leaf.
It does not claim current-process raw-byte residency, official tensor payload,
source-to-page derivation, page-materialization ownership, baseline source
identity, execution, quality, runtime, K27 authority, KV access, or Gate-10.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.quantization.aura_glm53_official_source_concrete_page_provenance_join import (
    REQUIRED_SUCCESSOR_EVIDENCE,
    current_provenance_frontier,
)

SCHEMA = "AURA_GLM53_HISTORICAL_HEADER_PROVENANCE_REFINEMENT_V1"
CONVERGENCE_COMMIT = "9862565d1617bbce56cf65dafb5811e6491db686"
Q8_HEAD = "e97c584e79439f599f7a443d86df23a11cab75ad"
Q8_RUN = 33371374486
PR398_HEAD = "131dd2a5fc8b4e2cf96c0bf598845d35e6706ef8"
PR398_RUN = 33336508527
PR398_JOB = 99324255699
PR398_DRIVE_OBSERVATION = "1FIz2aGHogE32scM4pmxDkHT7MiGfr2UbUkWlIDfpI_w"
PR398_RECEIPT_DIGEST = "736f0a117eb02c486736e7224c4e0f5363ae60b9"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
OFFICIAL_INDEX_SHA256 = "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf"
OFFICIAL_INDEX_SIZE = 11_359_251
SELECTED_LAYER = 3
SELECTED_EXPERT = 0
SELECTED_SHARD = "model-00038-of-00141.safetensors"
SELECTED_HEADER_SHA256 = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"
EXPECTED_ENTRY_COUNT = 6


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class HistoricalHeaderProvenanceRefinementReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    pr398_job: int
    pr398_drive_observation: str
    pr398_receipt_digest: str
    official_repository: str
    official_revision: str
    official_index_sha256: str
    official_index_size: int
    selected_layer: int
    selected_expert: int
    selected_shard: str
    selected_header_sha256: str
    selected_entry_count: int
    q8_candidate_identity_bound: bool
    q8_candidate_sample_bound: bool
    q8_independent_verifier_bound: bool
    historical_official_index_bytes_verified: bool
    historical_official_weight_map_observed: bool
    historical_representative_headers_observed: bool
    historical_fp8_companions_observed: bool
    historical_representative_header_transport_closed: bool
    historical_scope_is_representative_only: bool
    all_layer_expert_layout_uniformity_proven: bool
    current_process_raw_index_bytes_materialized: bool
    current_process_raw_header_prefixes_materialized: bool
    broad_official_source_transport_frontier_complete: bool
    official_source_tensor_payload_observed: bool
    official_source_byte_domain_bound_to_trial: bool
    concrete_page_official_source_authenticated: bool
    concrete_page_source_tensor_set_bound_to_official_source: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    source_transport_repair_alone_sufficient: bool
    cross_domain_provenance_reopen_required: bool
    required_successor_evidence: tuple[str, ...]
    disposition: str
    real_tensor_quantization_eligible: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def current_refinement() -> HistoricalHeaderProvenanceRefinementReceipt:
    q8 = current_provenance_frontier()
    if q8.official_repository != OFFICIAL_REPOSITORY or q8.official_revision != OFFICIAL_REVISION:
        raise ValueError("Q8 official source generation mismatch")
    if q8.official_source_transport_frontier_complete:
        raise ValueError("Q8 broad source frontier unexpectedly complete")
    if tuple(q8.required_successor_evidence) != tuple(REQUIRED_SUCCESSOR_EVIDENCE):
        raise ValueError("Q8 successor evidence drift")
    if any(
        (
            q8.official_source_tensor_payload_observed,
            q8.official_source_byte_domain_bound_to_trial,
            q8.concrete_page_official_source_authenticated,
            q8.concrete_page_source_tensor_set_bound_to_official_source,
            q8.candidate_page_materialization_owner_bound,
            q8.baseline_same_official_source_tensor_set_proven,
        )
    ):
        raise ValueError("Q8 cross-domain provenance unexpectedly widened")

    return HistoricalHeaderProvenanceRefinementReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(Q8_HEAD, PR398_HEAD),
        exact_parent_runs=(Q8_RUN, PR398_RUN),
        pr398_job=PR398_JOB,
        pr398_drive_observation=PR398_DRIVE_OBSERVATION,
        pr398_receipt_digest=PR398_RECEIPT_DIGEST,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        official_index_sha256=OFFICIAL_INDEX_SHA256,
        official_index_size=OFFICIAL_INDEX_SIZE,
        selected_layer=SELECTED_LAYER,
        selected_expert=SELECTED_EXPERT,
        selected_shard=SELECTED_SHARD,
        selected_header_sha256=SELECTED_HEADER_SHA256,
        selected_entry_count=EXPECTED_ENTRY_COUNT,
        q8_candidate_identity_bound=q8.concrete_candidate_identity_bound,
        q8_candidate_sample_bound=q8.concrete_candidate_sample_bound,
        q8_independent_verifier_bound=q8.concrete_independent_verifier_bound,
        historical_official_index_bytes_verified=True,
        historical_official_weight_map_observed=True,
        historical_representative_headers_observed=True,
        historical_fp8_companions_observed=True,
        historical_representative_header_transport_closed=True,
        historical_scope_is_representative_only=True,
        all_layer_expert_layout_uniformity_proven=False,
        current_process_raw_index_bytes_materialized=False,
        current_process_raw_header_prefixes_materialized=False,
        broad_official_source_transport_frontier_complete=False,
        official_source_tensor_payload_observed=False,
        official_source_byte_domain_bound_to_trial=False,
        concrete_page_official_source_authenticated=False,
        concrete_page_source_tensor_set_bound_to_official_source=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        source_transport_repair_alone_sufficient=False,
        cross_domain_provenance_reopen_required=True,
        required_successor_evidence=tuple(REQUIRED_SUCCESSOR_EVIDENCE),
        disposition="HOLD_TENSOR_TO_PAGE_PROVENANCE_AFTER_HISTORICAL_HEADER_CLOSURE",
        real_tensor_quantization_eligible=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_refinement).parameters) != 0


def main() -> None:
    receipt = current_refinement()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
