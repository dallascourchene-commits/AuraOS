#!/usr/bin/env python3
"""Join one earned live payload pair to the live producer-admission frontier.

Q11 is an evidence-delta membrane.  PR650 proved one exact gate-projection
weight/scale pair at the immutable official GLM-5.3 revision.  PR649 defines the
larger live official-tensor -> concrete-page admission debt.  Q11 subtracts only
those two observed source slices and exposes the exact remaining four slices.

It does not infer full-expert payload coverage, FP8 dequantization semantics,
canonical float32 source identity, gate/up role composition, page
materialization ownership, baseline equivalence, model execution, or authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import math
import re

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary

SCHEMA = "AURA_GLM53_LIVE_PAYLOAD_COVERAGE_DELTA_V1"
CONVERGENCE_COMMIT = "2943d00059247b86696df1899d5d7878be81008f"
PR650_HEAD = "e8e0eecb5fce9f95bf1b71e97b528776ecd8b51c"
PR650_RUN = 33374008643
PR650_JOB = 99431263469
PR650_RECEIPT_DIGEST = "995ba5bd23815dcc76389cec5b4fcc880afc408b29bcd673693b97c4b110b436"
PR649_HEAD = "aa004558af8c46bb9bedeedad3cbd2e4e212ab17"
PR649_RUN = 33373165058
PR649_SOURCE_BLOB = "6821f652939137c55babea7cb37b07e34223a5cc"
LIVE_HEADER_LENGTH_BYTES = 105_424
LIVE_GATE_WEIGHT_SHA256 = "2d4e5f36478b598043431b3691ce6a48639e01b6f804b1db62ca4af4d14063e8"
LIVE_GATE_SCALE_SHA256 = "671dd3b32b3f4cc651b93f3420ae47957ae09c1f745d278c0795d56e5d511c55"
TOTAL_REPRESENTATIVE_PAYLOAD_BYTES = 37_757_952
OBSERVED_PAYLOAD_BYTES = 12_585_984
REMAINING_PAYLOAD_BYTES = 25_171_968
TOTAL_SLICE_COUNT = 6
OBSERVED_SLICE_COUNT = 2
REMAINING_SLICE_COUNT = 4
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_DTYPE_BYTES = {"F8_E4M3": 1, "F32": 4}


@dataclass(frozen=True)
class SourceSlice:
    tensor_key: str
    projection: str
    dtype: str
    shape: tuple[int, ...]
    relative_offsets: tuple[int, int]
    expected_bytes: int
    observed_live: bool
    payload_sha256: str | None

    def validate(self) -> None:
        if self.projection not in {"gate", "up", "down"}:
            raise ValueError("Q11_PROJECTION_INVALID")
        if self.dtype not in _DTYPE_BYTES:
            raise ValueError("Q11_DTYPE_INVALID")
        if not self.shape or any(type(v) is not int or v <= 0 for v in self.shape):
            raise ValueError("Q11_SHAPE_INVALID")
        begin, end = self.relative_offsets
        if type(begin) is not int or type(end) is not int or begin < 0 or end <= begin:
            raise ValueError("Q11_OFFSETS_INVALID")
        by_shape = math.prod(self.shape) * _DTYPE_BYTES[self.dtype]
        if self.expected_bytes != end - begin or self.expected_bytes != by_shape:
            raise ValueError("Q11_BYTE_COUNT_MISMATCH")
        if self.observed_live:
            if self.payload_sha256 is None or not _SHA256_RE.fullmatch(self.payload_sha256):
                raise ValueError("Q11_OBSERVED_SLICE_DIGEST_REQUIRED")
        elif self.payload_sha256 is not None:
            raise ValueError("Q11_UNOBSERVED_SLICE_CANNOT_HAVE_PAYLOAD_DIGEST")


@dataclass(frozen=True)
class LivePayloadCoverageDeltaReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    pr650_job: int
    pr650_receipt_digest: str
    pr649_source_blob: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    historical_header_sha256: str
    live_header_length_bytes: int
    observed_slice_count: int
    remaining_slice_count: int
    total_slice_count: int
    observed_payload_bytes: int
    remaining_payload_bytes: int
    total_representative_payload_bytes: int
    live_gate_weight_sha256: str
    live_gate_scale_sha256: str
    gate_pair_independently_replayed: bool
    partial_representative_payload_observed: bool
    full_representative_expert_payload_observed: bool
    remaining_up_pair_observation_required: bool
    remaining_down_pair_observation_required: bool
    payload_coverage_complete: bool
    raw_fp8_payload_is_canonical_float32_source_identity: bool
    block_fp8_dequantization_semantics_bound: bool
    gate_up_source_layout_relation_bound: bool
    exact_official_tensor_to_concrete_source_tensor_set_relation: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    representative_scope_only: bool
    all_layers_experts_uniformity_proven: bool
    currentness_revalidation_required_at_use: bool
    disposition: str
    real_tensor_quantization_eligible: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        return hashlib.sha256(raw).hexdigest()


def exact_source_slices() -> tuple[SourceSlice, ...]:
    prefix = "model.layers.3.mlp.experts.0."
    rows = (
        (prefix + "gate_proj.weight", "gate", "F8_E4M3", (2048, 6144), (4_070_207_936, 4_082_790_848), LIVE_GATE_WEIGHT_SHA256),
        (prefix + "gate_proj.weight_scale_inv", "gate", "F32", (16, 48), (993_728, 996_800), LIVE_GATE_SCALE_SHA256),
        (prefix + "up_proj.weight", "up", "F8_E4M3", (2048, 6144), (4_082_790_848, 4_095_373_760), None),
        (prefix + "up_proj.weight_scale_inv", "up", "F32", (16, 48), (996_800, 999_872), None),
        (prefix + "down_proj.weight", "down", "F8_E4M3", (6144, 2048), (4_057_625_024, 4_070_207_936), None),
        (prefix + "down_proj.weight_scale_inv", "down", "F32", (48, 16), (990_656, 993_728), None),
    )
    out: list[SourceSlice] = []
    for key, projection, dtype, shape, offsets, digest in rows:
        expected = offsets[1] - offsets[0]
        item = SourceSlice(
            tensor_key=key,
            projection=projection,
            dtype=dtype,
            shape=shape,
            relative_offsets=offsets,
            expected_bytes=expected,
            observed_live=digest is not None,
            payload_sha256=digest,
        )
        item.validate()
        out.append(item)
    if len(out) != TOTAL_SLICE_COUNT:
        raise ValueError("Q11_TOTAL_SLICE_COUNT_DRIFT")
    if sum(x.expected_bytes for x in out) != TOTAL_REPRESENTATIVE_PAYLOAD_BYTES:
        raise ValueError("Q11_TOTAL_PAYLOAD_BYTES_DRIFT")
    observed = tuple(x for x in out if x.observed_live)
    remaining = tuple(x for x in out if not x.observed_live)
    if len(observed) != OBSERVED_SLICE_COUNT or sum(x.expected_bytes for x in observed) != OBSERVED_PAYLOAD_BYTES:
        raise ValueError("Q11_OBSERVED_DELTA_DRIFT")
    if len(remaining) != REMAINING_SLICE_COUNT or sum(x.expected_bytes for x in remaining) != REMAINING_PAYLOAD_BYTES:
        raise ValueError("Q11_REMAINING_DELTA_DRIFT")
    if {x.projection for x in observed} != {"gate"}:
        raise ValueError("Q11_ONLY_GATE_PAIR_MAY_BE_OBSERVED")
    if {x.projection for x in remaining} != {"up", "down"}:
        raise ValueError("Q11_REMAINING_PROJECTIONS_DRIFT")
    return tuple(out)


def current_live_payload_coverage_delta() -> LivePayloadCoverageDeltaReceipt:
    """Return the exact earned partial-coverage snapshot with no caller inputs."""
    canary._validate_parent_metadata()
    slices = exact_source_slices()
    if not _SHA256_RE.fullmatch(PR650_RECEIPT_DIGEST):
        raise ValueError("Q11_PR650_RECEIPT_DIGEST_INVALID")
    if LIVE_HEADER_LENGTH_BYTES <= 1 or LIVE_HEADER_LENGTH_BYTES > canary.MAX_HEADER_BYTES:
        raise ValueError("Q11_LIVE_HEADER_LENGTH_INVALID")
    if OBSERVED_PAYLOAD_BYTES + REMAINING_PAYLOAD_BYTES != TOTAL_REPRESENTATIVE_PAYLOAD_BYTES:
        raise ValueError("Q11_EVIDENCE_DELTA_ACCOUNTING_INVALID")

    return LivePayloadCoverageDeltaReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR650_HEAD, PR649_HEAD),
        exact_parent_runs=(PR650_RUN, PR649_RUN),
        pr650_job=PR650_JOB,
        pr650_receipt_digest=PR650_RECEIPT_DIGEST,
        pr649_source_blob=PR649_SOURCE_BLOB,
        official_repository=canary.OFFICIAL_REPOSITORY,
        official_revision=canary.OFFICIAL_REVISION,
        selected_layer=canary.SELECTED_LAYER,
        selected_expert=canary.SELECTED_EXPERT,
        selected_shard=canary.SELECTED_SHARD,
        historical_header_sha256=canary.SELECTED_HEADER_SHA256,
        live_header_length_bytes=LIVE_HEADER_LENGTH_BYTES,
        observed_slice_count=sum(x.observed_live for x in slices),
        remaining_slice_count=sum(not x.observed_live for x in slices),
        total_slice_count=len(slices),
        observed_payload_bytes=sum(x.expected_bytes for x in slices if x.observed_live),
        remaining_payload_bytes=sum(x.expected_bytes for x in slices if not x.observed_live),
        total_representative_payload_bytes=sum(x.expected_bytes for x in slices),
        live_gate_weight_sha256=LIVE_GATE_WEIGHT_SHA256,
        live_gate_scale_sha256=LIVE_GATE_SCALE_SHA256,
        gate_pair_independently_replayed=True,
        partial_representative_payload_observed=True,
        full_representative_expert_payload_observed=False,
        remaining_up_pair_observation_required=True,
        remaining_down_pair_observation_required=True,
        payload_coverage_complete=False,
        raw_fp8_payload_is_canonical_float32_source_identity=False,
        block_fp8_dequantization_semantics_bound=False,
        gate_up_source_layout_relation_bound=False,
        exact_official_tensor_to_concrete_source_tensor_set_relation=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        representative_scope_only=True,
        all_layers_experts_uniformity_proven=False,
        currentness_revalidation_required_at_use=True,
        disposition="PARTIAL_LIVE_PAYLOAD_COVERAGE_REMAINING_UP_DOWN",
        real_tensor_quantization_eligible=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_live_payload_coverage_delta).parameters) != 0


def main() -> None:
    receipt = current_live_payload_coverage_delta()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["slices"] = [asdict(x) for x in exact_source_slices()]
    body["law"] = (
        "ObservedSubset != FullCoverage; NewLiveEvidenceGeneration => SubtractOnlyProvenSlices; "
        "RawPayloadHash != CanonicalFloat32SourceHash != PageMaterialization"
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
