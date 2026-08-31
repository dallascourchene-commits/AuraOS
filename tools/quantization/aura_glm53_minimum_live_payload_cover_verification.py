#!/usr/bin/env python3
"""Execute the minimum admitted live-payload verification cone for GLM-5.3.

Q12 consumes two exact other-agent consequences without duplicating their owners:
* PR653/Q11 owns the exact partial live-payload delta: gate weight+scale are
  observed, while up/down weight+scale remain unresolved.
* PR654/A4 owns HyperScale work admission: the cheapest complete verification
  cover is exactly the bounded up-pair + down-pair observation, 25,171,968 bytes.

This module crosses only that read-only evidence boundary.  It does not perform
FP8 dequantization, source-layout composition, quantization, page materialization,
model execution, KV-cache access, Gate-10 promotion, merge, or deployment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import struct

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary
from tools.quantization import aura_glm53_live_payload_coverage_delta as q11

SCHEMA = "AURA_GLM53_MINIMUM_LIVE_PAYLOAD_COVER_VERIFICATION_V1"
PR653_PROOF_HEAD = "b2da1ada1568b6e7c3629001b4ecca3c1ba4fe76"
PR653_RUN = 33375061325
PR653_SOURCE_BLOB = "314ab1bb75278b18d8d5a3335ffeede1a0f2b57b"
PR654_PROOF_HEAD = "26e377fe543b8c1906832b8c1e968dfe63480005"
PR654_RUN = 33375530171
PR654_SOURCE_BLOB = "0b6a53612d4d2d9993da49180cfc74d5f4996548"
ADMITTED_OBSERVATIONS = ("down-pair", "up-pair")
ADMITTED_NEW_BYTES = 25_171_968
EXPECTED_HEADER_LENGTH = 105_424
RESULT_CONSEQUENCE = "FULL_REPRESENTATIVE_RAW_PAYLOAD_COVERAGE_OBSERVED"
PREVIOUS_CONSEQUENCE = "PARTIAL_LIVE_PAYLOAD_COVERAGE_REMAINING_UP_DOWN"


class MinimumCoverObservationError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _receipt_sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def remaining_source_slices() -> tuple[q11.SourceSlice, ...]:
    remaining = tuple(x for x in q11.exact_source_slices() if not x.observed_live)
    if len(remaining) != 4:
        raise MinimumCoverObservationError("Q12_REMAINING_SLICE_COUNT_DRIFT")
    if sum(x.expected_bytes for x in remaining) != ADMITTED_NEW_BYTES:
        raise MinimumCoverObservationError("Q12_REMAINING_BYTE_COUNT_DRIFT")
    if {x.projection for x in remaining} != {"up", "down"}:
        raise MinimumCoverObservationError("Q12_REMAINING_PROJECTION_DRIFT")
    ordered = sorted(remaining, key=lambda x: ({"down": 0, "up": 1}[x.projection], x.tensor_key))
    return tuple(ordered)


@dataclass(frozen=True)
class LiveSliceObservation:
    tensor_key: str
    projection: str
    dtype: str
    shape: tuple[int, ...]
    relative_offsets: tuple[int, int]
    absolute_range: tuple[int, int]
    payload_bytes: int
    payload_sha256: str


@dataclass(frozen=True)
class MinimumLivePayloadCoverReceipt:
    schema: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    exact_parent_source_blobs: tuple[str, str]
    parent_work_mode: str
    parent_semantic_disposition: str
    admitted_observation_ids: tuple[str, str]
    admitted_new_byte_cost: int
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    live_header_length_bytes: int
    prior_observed_slice_count: int
    newly_observed_slice_count: int
    total_observed_slice_count: int
    remaining_slice_count: int
    prior_observed_payload_bytes: int
    newly_observed_payload_bytes: int
    total_observed_payload_bytes: int
    gate_weight_sha256: str
    gate_scale_sha256: str
    new_observations: tuple[LiveSliceObservation, ...]
    full_representative_raw_payload_coverage_observed: bool
    representative_scope_only: bool
    result_consequence: str
    previous_consequence: str
    consequence_state_changed: bool
    result_new_sck_candidate: bool
    admission_itself_counts_as_terminal_semantic_sibling: bool
    terminal_sibling_requires_exact_hosted_proof: bool
    block_fp8_dequantization_semantics_bound: bool
    gate_up_source_layout_relation_bound: bool
    raw_fp8_payload_is_canonical_float32_source_identity: bool
    exact_official_tensor_to_concrete_source_tensor_set_relation: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    all_layers_experts_uniformity_proven: bool
    real_tensor_quantization_eligible: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _receipt_sha(asdict(self))


def _validate_parent_delta() -> None:
    prior = q11.current_live_payload_coverage_delta()
    if prior.disposition != PREVIOUS_CONSEQUENCE:
        raise MinimumCoverObservationError("Q12_Q11_DISPOSITION_DRIFT")
    if (prior.observed_slice_count, prior.remaining_slice_count, prior.total_slice_count) != (2, 4, 6):
        raise MinimumCoverObservationError("Q12_Q11_SLICE_DELTA_DRIFT")
    if prior.observed_payload_bytes != 12_585_984 or prior.remaining_payload_bytes != ADMITTED_NEW_BYTES:
        raise MinimumCoverObservationError("Q12_Q11_BYTE_DELTA_DRIFT")
    if prior.total_representative_payload_bytes != 37_757_952:
        raise MinimumCoverObservationError("Q12_Q11_TOTAL_BYTE_DRIFT")
    if prior.payload_coverage_complete:
        raise MinimumCoverObservationError("Q12_Q11_ALREADY_COMPLETE")
    remaining_source_slices()


def _build_receipt(*, header_len: int, payloads: dict[str, bytes]) -> MinimumLivePayloadCoverReceipt:
    _validate_parent_delta()
    if header_len != EXPECTED_HEADER_LENGTH:
        raise MinimumCoverObservationError("Q12_LIVE_HEADER_LENGTH_DRIFT")

    expected = remaining_source_slices()
    if set(payloads) != {x.tensor_key for x in expected}:
        raise MinimumCoverObservationError("Q12_PAYLOAD_KEY_SET_MISMATCH")

    data_base = 8 + header_len
    observations: list[LiveSliceObservation] = []
    for item in expected:
        raw = payloads[item.tensor_key]
        if len(raw) != item.expected_bytes:
            raise MinimumCoverObservationError("Q12_PAYLOAD_LENGTH_MISMATCH")
        start = data_base + item.relative_offsets[0]
        observations.append(
            LiveSliceObservation(
                tensor_key=item.tensor_key,
                projection=item.projection,
                dtype=item.dtype,
                shape=item.shape,
                relative_offsets=item.relative_offsets,
                absolute_range=(start, start + item.expected_bytes),
                payload_bytes=item.expected_bytes,
                payload_sha256=_sha256(raw),
            )
        )

    newly_observed = sum(x.payload_bytes for x in observations)
    if newly_observed != ADMITTED_NEW_BYTES:
        raise MinimumCoverObservationError("Q12_EXECUTED_BYTE_CONE_DRIFT")

    receipt = MinimumLivePayloadCoverReceipt(
        schema=SCHEMA,
        exact_parent_heads=(PR653_PROOF_HEAD, PR654_PROOF_HEAD),
        exact_parent_runs=(PR653_RUN, PR654_RUN),
        exact_parent_source_blobs=(PR653_SOURCE_BLOB, PR654_SOURCE_BLOB),
        parent_work_mode="VERIFICATION",
        parent_semantic_disposition="SUPPORT_MERGE",
        admitted_observation_ids=ADMITTED_OBSERVATIONS,
        admitted_new_byte_cost=ADMITTED_NEW_BYTES,
        official_repository=canary.OFFICIAL_REPOSITORY,
        official_revision=canary.OFFICIAL_REVISION,
        selected_layer=canary.SELECTED_LAYER,
        selected_expert=canary.SELECTED_EXPERT,
        selected_shard=canary.SELECTED_SHARD,
        live_header_length_bytes=header_len,
        prior_observed_slice_count=2,
        newly_observed_slice_count=4,
        total_observed_slice_count=6,
        remaining_slice_count=0,
        prior_observed_payload_bytes=12_585_984,
        newly_observed_payload_bytes=newly_observed,
        total_observed_payload_bytes=37_757_952,
        gate_weight_sha256=q11.LIVE_GATE_WEIGHT_SHA256,
        gate_scale_sha256=q11.LIVE_GATE_SCALE_SHA256,
        new_observations=tuple(observations),
        full_representative_raw_payload_coverage_observed=True,
        representative_scope_only=True,
        result_consequence=RESULT_CONSEQUENCE,
        previous_consequence=PREVIOUS_CONSEQUENCE,
        consequence_state_changed=True,
        result_new_sck_candidate=True,
        admission_itself_counts_as_terminal_semantic_sibling=False,
        terminal_sibling_requires_exact_hosted_proof=True,
        block_fp8_dequantization_semantics_bound=False,
        gate_up_source_layout_relation_bound=False,
        raw_fp8_payload_is_canonical_float32_source_identity=False,
        exact_official_tensor_to_concrete_source_tensor_set_relation=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        all_layers_experts_uniformity_proven=False,
        real_tensor_quantization_eligible=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )
    return receipt


def current_live_minimum_cover_observation() -> MinimumLivePayloadCoverReceipt:
    """Execute only the exact A4-admitted up/down read-only evidence cone."""
    _validate_parent_delta()
    url = canary.hf_resolve_url(canary.OFFICIAL_REPOSITORY, canary.OFFICIAL_REVISION, canary.SELECTED_SHARD)
    prefix = canary.urllib_read_range(url, 0, 8)
    if len(prefix) != 8:
        raise MinimumCoverObservationError("Q12_HEADER_PREFIX_LENGTH_MISMATCH")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len != EXPECTED_HEADER_LENGTH:
        raise MinimumCoverObservationError("Q12_CURRENT_HEADER_REVALIDATION_FAILED")
    data_base = 8 + header_len
    payloads: dict[str, bytes] = {}
    for item in remaining_source_slices():
        payloads[item.tensor_key] = canary.urllib_read_range(
            url,
            data_base + item.relative_offsets[0],
            item.expected_bytes,
        )
    return _build_receipt(header_len=header_len, payloads=payloads)


def public_api_has_effect_boolean() -> bool:
    forbidden = {"execute", "authorize", "promote", "deploy", "gate10", "materialize", "dequantize"}
    return bool(set(inspect.signature(current_live_minimum_cover_observation).parameters) & forbidden)


def main() -> None:
    receipt = current_live_minimum_cover_observation()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "VerificationAdmission!=VerificationResult",
        "PartialPayloadCoverage+ExactMinimumCoverObservation=>FullRepresentativeRawPayloadCoverage",
        "FullRepresentativeRawPayloadCoverage!=FP8DequantizationSemantics",
        "FullRepresentativeRawPayloadCoverage!=SourceToPageMaterialization",
        "VerificationWorkMayRevealNewSemanticConsequenceWithoutAdmissionInflatingSemanticMass",
        "K27Coordinate!=SourceAuthority!=ProducerAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
