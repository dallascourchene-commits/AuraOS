#!/usr/bin/env python3
"""Fail-closed admission for a live official-tensor -> concrete-page producer.

Q9 joins two exact-green consequence owners:
- Q8/PR645: the pinned official-source -> concrete-page provenance frontier.
- Q6/PR646: exact historical official W2 representative-header evidence rebound
  through the current Q5 source grammar.

Historical source evidence may constrain expected schema/geometry and provenance,
but it cannot mint present tensor-byte residency, a source-tensor -> page relation,
or a page materialization owner. V2 also distinguishes equality inside the pinned
frontier generation from ambient repository-head currentness. The deterministic Q9
process does not observe ambient repository head and therefore cannot claim it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.quantization import aura_glm53_historical_official_w2_bridge as historical
from tools.quantization import aura_glm53_official_source_concrete_page_provenance_join as provenance

SCHEMA = "AURA_GLM53_LIVE_TENSOR_CONCRETE_PAGE_PRODUCER_ADMISSION_V2"
CONVERGENCE_COMMIT = "fa9f17fba4f9e0011c35fc6404789bf13692b4ec"
PR645_HEAD = "e97c584e79439f599f7a443d86df23a11cab75ad"
PR645_RUN = 33371374486
PR645_PROVENANCE_BLOB = "7951124182a0ed9396cf294a8c811bf8555391a9"
PR646_HEAD = "71d4816cf0702a39b57ecf7d6bae6298ec239800"
PR646_RUN = 33371459229
PR646_HISTORICAL_BRIDGE_BLOB = "77a90ea9f5a438aa438103acd4de05432fe7875a"

REQUIRED_LIVE_EVIDENCE = (
    "LIVE_OFFICIAL_SOURCE_TENSOR_PAYLOAD_OBSERVATION",
    "EXACT_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_SOURCE_TENSOR_SET_RELATION",
    "CANDIDATE_PAGE_MATERIALIZATION_OWNER_RECEIPT",
    "BASELINE_SAME_LIVE_OFFICIAL_SOURCE_TENSOR_SET_RELATION",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class LiveTensorConcretePageProducerAdmissionReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    exact_parent_source_blobs: tuple[str, str]
    official_repository: str
    official_revision: str
    historical_representative_header_schema_qualified: bool
    historical_representative_header_provenance_bound: bool
    historical_fp8_companion_geometry_bound: bool
    historical_evidence_revision_matches_pinned_frontier_revision: bool
    ambient_repository_head_observed_by_q9_process: bool
    current_concrete_page_frontier_bound: bool
    current_concrete_candidate_identity_bound: bool
    current_concrete_candidate_sample_bound: bool
    historical_evidence_reduces_header_schema_uncertainty: bool
    historical_header_evidence_sufficient_for_live_producer: bool
    current_consumer_raw_index_bytes_materialized: bool
    current_consumer_raw_header_prefixes_materialized: bool
    live_official_tensor_payload_observed: bool
    exact_live_official_tensor_to_concrete_source_tensor_set_relation: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_live_official_source_tensor_set_proven: bool
    live_tensor_to_concrete_page_producer_admissible: bool
    currentness_revalidation_required_at_use: bool
    representative_scope_only: bool
    all_layers_experts_uniformity_proven: bool
    disposition: str
    required_live_evidence: tuple[str, ...]
    real_tensor_quantization_eligible: bool
    model_execution_eligible: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _join_exact_parents(
    current: provenance.OfficialSourceConcretePageProvenanceReceipt,
    past: historical.HistoricalOfficialW2BridgeReceipt,
) -> LiveTensorConcretePageProducerAdmissionReceipt:
    if current.official_repository != past.official_repository:
        raise ValueError("Q9_OFFICIAL_REPOSITORY_MISMATCH")
    if current.official_revision != past.official_revision:
        raise ValueError("Q9_OFFICIAL_REVISION_MISMATCH")
    if current.disposition != "HOLD_OFFICIAL_SOURCE_TO_CONCRETE_PAGE_PROVENANCE":
        raise ValueError("Q9_PR645_DISPOSITION_DRIFT")
    if not current.concrete_candidate_identity_bound or not current.concrete_candidate_sample_bound:
        raise ValueError("Q9_PR645_CONCRETE_CANDIDATE_BINDING_INCOMPLETE")
    if current.official_source_tensor_payload_observed:
        raise ValueError("Q9_PR645_PARENT_UNEXPECTEDLY_HAS_TENSOR_PAYLOAD")
    if current.concrete_page_source_tensor_set_bound_to_official_source:
        raise ValueError("Q9_PR645_PARENT_UNEXPECTEDLY_HAS_SOURCE_TO_PAGE_RELATION")
    if current.candidate_page_materialization_owner_bound:
        raise ValueError("Q9_PR645_PARENT_UNEXPECTEDLY_HAS_MATERIALIZATION_OWNER")
    if current.baseline_same_official_source_tensor_set_proven:
        raise ValueError("Q9_PR645_PARENT_UNEXPECTEDLY_HAS_BASELINE_SOURCE_EQUIVALENCE")

    if not past.historical_representative_headers_observed:
        raise ValueError("Q9_PR646_HISTORICAL_HEADERS_NOT_OBSERVED")
    if not past.historical_fp8_companions_bound:
        raise ValueError("Q9_PR646_HISTORICAL_FP8_COMPANIONS_NOT_BOUND")
    if not past.current_pr639_schema_header_geometry_conforms:
        raise ValueError("Q9_PR646_CURRENT_SCHEMA_GEOMETRY_NOT_CONFORMANT")
    if not past.representative_per_expert_serialization_proven:
        raise ValueError("Q9_PR646_REPRESENTATIVE_SERIALIZATION_NOT_PROVEN")
    if past.historical_payload_bytes_read != 0 or past.source_tensor_payload_bound:
        raise ValueError("Q9_PR646_HISTORICAL_HEADER_EVIDENCE_PROMOTED_TO_PAYLOAD")
    if past.current_consumer_raw_index_bytes_materialized:
        raise ValueError("Q9_PR646_HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT_INDEX_BYTES")
    if past.current_consumer_raw_header_prefixes_materialized:
        raise ValueError("Q9_PR646_HISTORICAL_EVIDENCE_PROMOTED_TO_CURRENT_HEADER_BYTES")
    if past.all_layers_experts_uniformity_proven:
        raise ValueError("Q9_PR646_REPRESENTATIVE_SCOPE_PROMOTED_TO_GLOBAL")

    return LiveTensorConcretePageProducerAdmissionReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR645_HEAD, PR646_HEAD),
        exact_parent_runs=(PR645_RUN, PR646_RUN),
        exact_parent_source_blobs=(PR645_PROVENANCE_BLOB, PR646_HISTORICAL_BRIDGE_BLOB),
        official_repository=current.official_repository,
        official_revision=current.official_revision,
        historical_representative_header_schema_qualified=True,
        historical_representative_header_provenance_bound=True,
        historical_fp8_companion_geometry_bound=True,
        historical_evidence_revision_matches_pinned_frontier_revision=True,
        ambient_repository_head_observed_by_q9_process=False,
        current_concrete_page_frontier_bound=True,
        current_concrete_candidate_identity_bound=True,
        current_concrete_candidate_sample_bound=True,
        historical_evidence_reduces_header_schema_uncertainty=True,
        historical_header_evidence_sufficient_for_live_producer=False,
        current_consumer_raw_index_bytes_materialized=False,
        current_consumer_raw_header_prefixes_materialized=False,
        live_official_tensor_payload_observed=False,
        exact_live_official_tensor_to_concrete_source_tensor_set_relation=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_live_official_source_tensor_set_proven=False,
        live_tensor_to_concrete_page_producer_admissible=False,
        currentness_revalidation_required_at_use=True,
        representative_scope_only=True,
        all_layers_experts_uniformity_proven=False,
        disposition="HOLD_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_PAGE_PRODUCER",
        required_live_evidence=REQUIRED_LIVE_EVIDENCE,
        real_tensor_quantization_eligible=False,
        model_execution_eligible=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def current_live_producer_admission() -> LiveTensorConcretePageProducerAdmissionReceipt:
    """Recompute exact pinned-parent consequences and return fail-closed Q9 state."""
    current = provenance.current_provenance_frontier()
    past = historical.build_historical_official_w2_bridge(historical.canonical_pr398_observation())
    return _join_exact_parents(current, past)


def public_api_has_promotion_inputs() -> bool:
    """V2 must not accept caller-authored booleans that can self-mint producer authority."""
    return len(inspect.signature(current_live_producer_admission).parameters) != 0


def main() -> None:
    receipt = current_live_producer_admission()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["law"] = (
        "HistoricalRepresentativeOfficialHeaderEvidence != LiveTensorPayloadResidency != "
        "ExactOfficialTensorToConcretePageProducerRelation; "
        "PinnedFrontierRevisionMatch != AmbientRepositoryHeadCurrentness"
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
