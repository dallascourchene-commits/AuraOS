#!/usr/bin/env python3
"""Current frontier joining official-source, historical W2 and concrete-page evidence.

Q9 preserves three independent planes:
1. exact historical official representative header evidence exists and conforms to
   the current PR639 FP8/F32 header grammar;
2. current consumer raw index/header bytes and tensor payload are not resident;
3. no producer relation binds the exact official tensor payload to PR641's concrete
   source tensor set or candidate page materialization.

Historical evidence may close a historical header-geometry uncertainty leaf.  It
cannot mint current byte residency or source-to-page provenance.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.quantization.aura_glm53_historical_official_w2_bridge import (
    PR398_EXPERT,
    PR398_LAYER,
    PR398_SHARD,
    build_historical_official_w2_bridge,
    canonical_pr398_observation,
)

SCHEMA = "AURA_GLM53_OFFICIAL_SOURCE_CONCRETE_PAGE_PROVENANCE_JOIN_V2"
ORIGINAL_CONVERGENCE_COMMIT = "22625150948c3143b57400e58a6d09af418a9a28"
HISTORICAL_EVIDENCE_CONVERGENCE_COMMIT = "718c51ddc07463912a16a5ff43cdc2387a367cef"
OFFICIAL_BRIDGE_HEAD = "023cc10c25372f0e871f287cc5a22b9196c8a094"
OFFICIAL_BRIDGE_RUN = 33370777504
OFFICIAL_BRIDGE_SOURCE_BLOB = "733e6cb7a0ef404b8d8348410ecfc56e70f0e987"
CONCRETE_TRIAL_HEAD = "a8d4605a36e04d64cf03f43f457be4bde553e602"
CONCRETE_TRIAL_RUN = 33370700852
CONCRETE_TRIAL_SOURCE_BLOB = "157afcb2e457c630d03a8c72aef09f0a6ba04a4d"
HISTORICAL_W2_HEAD = "71d4816cf0702a39b57ecf7d6bae6298ec239800"
HISTORICAL_W2_RUN = 33371459229
HISTORICAL_W2_SOURCE_BLOB = "77a90ea9f5a438aa438103acd4de05432fe7875a"
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"

REQUIRED_SUCCESSOR_EVIDENCE = (
    "OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
    "EXACT_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
    "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
    "BASELINE_SAME_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class OfficialSourceConcretePageProvenanceReceipt:
    schema: str
    original_convergence_commit: str
    historical_evidence_convergence_commit: str
    exact_original_parent_heads: tuple[str, str]
    exact_original_parent_runs: tuple[int, int]
    exact_original_parent_source_blobs: tuple[str, str]
    historical_w2_head: str
    historical_w2_run: int
    historical_w2_source_blob: str
    historical_w2_receipt_digest: str
    official_repository: str
    official_revision: str
    concrete_candidate_identity_bound: bool
    concrete_candidate_sample_bound: bool
    concrete_independent_verifier_bound: bool
    historical_raw_index_verification_observed: bool
    historical_weight_map_relation_observed: bool
    historical_representative_headers_observed: bool
    historical_fp8_companions_bound: bool
    historical_payload_bytes_read: int
    historical_representative_header_geometry_conforms_current_schema: bool
    historical_representative_layer: int
    historical_representative_expert: int
    historical_representative_shard: str
    representative_per_expert_serialization_proven: bool
    all_layers_experts_uniformity_proven: bool
    current_consumer_raw_index_bytes_materialized: bool
    current_consumer_raw_header_prefixes_materialized: bool
    official_source_transport_frontier_complete: bool
    official_source_tensor_payload_observed: bool
    official_source_byte_domain_bound_to_trial: bool
    concrete_page_official_source_authenticated: bool
    concrete_page_source_tensor_set_bound_to_official_source: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    historical_header_evidence_closes_current_transport: bool
    historical_header_evidence_closes_materialization_provenance: bool
    source_transport_repair_alone_sufficient: bool
    cross_domain_provenance_reopen_required: bool
    disposition: str
    required_successor_evidence: tuple[str, ...]
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


def current_provenance_frontier() -> OfficialSourceConcretePageProvenanceReceipt:
    """Regenerate exact historical W2 consequence and join only its earned scope."""
    historical = build_historical_official_w2_bridge(canonical_pr398_observation())
    if not (
        historical.historical_raw_index_verification_observed
        and historical.historical_weight_map_relation_observed
        and historical.historical_representative_headers_observed
        and historical.historical_fp8_companions_bound
        and historical.current_pr639_schema_header_geometry_conforms
        and historical.representative_per_expert_serialization_proven
    ):
        raise RuntimeError("EXACT_HISTORICAL_W2_EVIDENCE_NOT_CLOSED")
    if historical.historical_payload_bytes_read != 0:
        raise RuntimeError("HISTORICAL_W2_UNEXPECTED_PAYLOAD_BYTES")
    if (
        historical.current_consumer_raw_index_bytes_materialized
        or historical.current_consumer_raw_header_prefixes_materialized
        or historical.source_tensor_payload_bound
        or historical.real_tensor_quantization_eligible
    ):
        raise RuntimeError("HISTORICAL_W2_CURRENTNESS_CEILING_WIDENED")

    return OfficialSourceConcretePageProvenanceReceipt(
        schema=SCHEMA,
        original_convergence_commit=ORIGINAL_CONVERGENCE_COMMIT,
        historical_evidence_convergence_commit=HISTORICAL_EVIDENCE_CONVERGENCE_COMMIT,
        exact_original_parent_heads=(OFFICIAL_BRIDGE_HEAD, CONCRETE_TRIAL_HEAD),
        exact_original_parent_runs=(OFFICIAL_BRIDGE_RUN, CONCRETE_TRIAL_RUN),
        exact_original_parent_source_blobs=(OFFICIAL_BRIDGE_SOURCE_BLOB, CONCRETE_TRIAL_SOURCE_BLOB),
        historical_w2_head=HISTORICAL_W2_HEAD,
        historical_w2_run=HISTORICAL_W2_RUN,
        historical_w2_source_blob=HISTORICAL_W2_SOURCE_BLOB,
        historical_w2_receipt_digest=historical.digest,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        concrete_candidate_identity_bound=True,
        concrete_candidate_sample_bound=True,
        concrete_independent_verifier_bound=True,
        historical_raw_index_verification_observed=True,
        historical_weight_map_relation_observed=True,
        historical_representative_headers_observed=True,
        historical_fp8_companions_bound=True,
        historical_payload_bytes_read=0,
        historical_representative_header_geometry_conforms_current_schema=True,
        historical_representative_layer=PR398_LAYER,
        historical_representative_expert=PR398_EXPERT,
        historical_representative_shard=PR398_SHARD,
        representative_per_expert_serialization_proven=True,
        all_layers_experts_uniformity_proven=False,
        current_consumer_raw_index_bytes_materialized=False,
        current_consumer_raw_header_prefixes_materialized=False,
        official_source_transport_frontier_complete=False,
        official_source_tensor_payload_observed=False,
        official_source_byte_domain_bound_to_trial=False,
        concrete_page_official_source_authenticated=False,
        concrete_page_source_tensor_set_bound_to_official_source=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        historical_header_evidence_closes_current_transport=False,
        historical_header_evidence_closes_materialization_provenance=False,
        source_transport_repair_alone_sufficient=False,
        cross_domain_provenance_reopen_required=True,
        disposition="HOLD_OFFICIAL_SOURCE_TO_CONCRETE_PAGE_PROVENANCE",
        required_successor_evidence=REQUIRED_SUCCESSOR_EVIDENCE,
        real_tensor_quantization_eligible=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_provenance_frontier).parameters) != 0


def main() -> None:
    receipt = current_provenance_frontier()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
