#!/usr/bin/env python3
"""Observe exactly the four official GLM-5.3 payload slices left open by Q11.

Q12 is verification/EGK work, not a new semantic-authority claim.  It composes
Q11's exact 2/6 live coverage delta with A4's independently green minimum-cover
admission.  The live effect is therefore restricted to the missing up/down
weight+scale pairs: exactly 25,171,968 tensor-payload bytes.

Completing 6/6 raw representative payload coverage does NOT prove block-FP8
 dequantization, canonical float32 source identity, gate/up composition, page
materialization, model execution, quality, runtime, or deployment authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import re
import struct
from typing import Callable

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary
from tools.quantization import aura_glm53_live_payload_coverage_delta as delta

SCHEMA = "AURA_GLM53_REMAINING_OFFICIAL_PAYLOAD_SLICES_V1"
CONVERGENCE_COMMIT = "2db0e70fdd4d8534d7f640a437b864ff97ccbae9"
PR653_HEAD = "fe5fc943b950d7ba97808aca4886f3043518b3c8"
PR653_RUN = 33395890155
PR654_HEAD = "5cf5587945949ac2a0150fb0958ad937bd6d0434"
PR654_RUN = 33395920243
EXPECTED_NEW_SLICE_COUNT = 4
EXPECTED_INHERITED_SLICE_COUNT = 2
EXPECTED_TOTAL_SLICE_COUNT = 6
EXPECTED_NEW_PAYLOAD_BYTES = 25_171_968
EXPECTED_INHERITED_PAYLOAD_BYTES = 12_585_984
EXPECTED_TOTAL_PAYLOAD_BYTES = 37_757_952
MAX_NEW_PAYLOAD_BYTES = 32 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RangeReader = Callable[[str, int, int], bytes]


class RemainingPayloadError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class ObservedSlice:
    tensor_key: str
    projection: str
    dtype: str
    shape: tuple[int, ...]
    relative_range: tuple[int, int]
    absolute_range: tuple[int, int]
    payload_bytes: int
    payload_sha256: str

    def validate(self) -> None:
        if self.projection not in {"up", "down"}:
            raise RemainingPayloadError("Q12_ONLY_UP_DOWN_MAY_BE_NEW")
        if self.dtype not in {"F8_E4M3", "F32"}:
            raise RemainingPayloadError("Q12_DTYPE_INVALID")
        rb, re_ = self.relative_range
        ab, ae = self.absolute_range
        if re_ - rb != self.payload_bytes or ae - ab != self.payload_bytes:
            raise RemainingPayloadError("Q12_RANGE_LENGTH_MISMATCH")
        if not _SHA256_RE.fullmatch(self.payload_sha256):
            raise RemainingPayloadError("Q12_PAYLOAD_DIGEST_INVALID")


@dataclass(frozen=True)
class RemainingPayloadReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    current_header_length_bytes: int
    current_header_sha256: str
    current_header_exactly_revalidated: bool
    strict_http_range_only: bool
    full_shard_fallback_accepted: bool
    inherited_gate_weight_sha256: str
    inherited_gate_scale_sha256: str
    inherited_slice_count: int
    newly_observed_slice_count: int
    combined_slice_count: int
    newly_observed_payload_bytes: int
    inherited_payload_bytes: int
    combined_representative_payload_bytes: int
    observed_slices: tuple[ObservedSlice, ...]
    up_pair_observed: bool
    down_pair_observed: bool
    representative_expert_raw_payload_coverage_complete: bool
    full_shard_payload_observed: bool
    all_layers_experts_payload_coverage_proven: bool
    raw_fp8_payload_is_canonical_float32_source_identity: bool
    block_fp8_dequantization_semantics_bound: bool
    gate_up_source_layout_relation_bound: bool
    exact_official_tensor_to_pr628_source_tensor_relation_proven: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    representative_scope_only: bool
    real_tensor_quantization_eligible: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool
    disposition: str

    @property
    def receipt_digest(self) -> str:
        return _sha256(_canonical(asdict(self)))


def missing_source_slices() -> tuple[delta.SourceSlice, ...]:
    all_slices = delta.exact_source_slices()
    missing = tuple(item for item in all_slices if not item.observed_live)
    if len(missing) != EXPECTED_NEW_SLICE_COUNT:
        raise RemainingPayloadError("Q12_MISSING_SLICE_COUNT_DRIFT")
    if sum(item.expected_bytes for item in missing) != EXPECTED_NEW_PAYLOAD_BYTES:
        raise RemainingPayloadError("Q12_MISSING_PAYLOAD_BYTE_DRIFT")
    if {item.projection for item in missing} != {"up", "down"}:
        raise RemainingPayloadError("Q12_MISSING_PROJECTION_DRIFT")
    if sum(item.projection == "up" for item in missing) != 2:
        raise RemainingPayloadError("Q12_UP_PAIR_DRIFT")
    if sum(item.projection == "down" for item in missing) != 2:
        raise RemainingPayloadError("Q12_DOWN_PAIR_DRIFT")
    if EXPECTED_NEW_PAYLOAD_BYTES > MAX_NEW_PAYLOAD_BYTES:
        raise RemainingPayloadError("Q12_MINIMUM_COVER_BYTE_CEILING_EXCEEDED")
    return missing


def _validate_header_metadata(header: dict[str, object]) -> None:
    """Bind the current header to every exact Q11 source-slice coordinate."""
    if not isinstance(header, dict):
        raise RemainingPayloadError("Q12_HEADER_OBJECT_REQUIRED")
    for spec in delta.exact_source_slices():
        raw = header.get(spec.tensor_key)
        if not isinstance(raw, dict):
            raise RemainingPayloadError("Q12_HEADER_TENSOR_MISSING:" + spec.tensor_key)
        if raw.get("dtype") != spec.dtype:
            raise RemainingPayloadError("Q12_HEADER_DTYPE_DRIFT:" + spec.tensor_key)
        if tuple(raw.get("shape", ())) != spec.shape:
            raise RemainingPayloadError("Q12_HEADER_SHAPE_DRIFT:" + spec.tensor_key)
        if tuple(raw.get("data_offsets", ())) != spec.relative_offsets:
            raise RemainingPayloadError("Q12_HEADER_OFFSET_DRIFT:" + spec.tensor_key)


def _read_and_validate_current_header(url: str, fetch_range: RangeReader) -> tuple[int, str]:
    prefix = fetch_range(url, 0, 8)
    if len(prefix) != 8:
        raise RemainingPayloadError("Q12_HEADER_PREFIX_LENGTH_MISMATCH")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 1 or header_len > canary.MAX_HEADER_BYTES:
        raise RemainingPayloadError("Q12_HEADER_LENGTH_OUT_OF_BOUNDS")
    header_raw = fetch_range(url, 8, header_len)
    header_sha = _sha256(header_raw)
    if header_sha != canary.SELECTED_HEADER_SHA256:
        raise RemainingPayloadError("Q12_CURRENT_HEADER_DIGEST_DRIFT")
    try:
        header = json.loads(header_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RemainingPayloadError("Q12_HEADER_JSON_INVALID") from exc
    _validate_header_metadata(header)
    return header_len, header_sha


def _build_receipt(*, header_len: int, header_sha: str, payloads: dict[str, bytes]) -> RemainingPayloadReceipt:
    missing = missing_source_slices()
    expected_keys = {item.tensor_key for item in missing}
    if set(payloads) != expected_keys:
        raise RemainingPayloadError("Q12_EXACT_MISSING_PAYLOAD_KEYSET_REQUIRED")
    if header_len <= 1 or header_len > canary.MAX_HEADER_BYTES:
        raise RemainingPayloadError("Q12_HEADER_LENGTH_OUT_OF_BOUNDS")
    if header_sha != canary.SELECTED_HEADER_SHA256:
        raise RemainingPayloadError("Q12_HEADER_DIGEST_DRIFT")

    data_base = 8 + header_len
    observed: list[ObservedSlice] = []
    for spec in missing:
        raw = payloads[spec.tensor_key]
        if len(raw) != spec.expected_bytes:
            raise RemainingPayloadError("Q12_PAYLOAD_LENGTH_MISMATCH:" + spec.tensor_key)
        start = data_base + spec.relative_offsets[0]
        item = ObservedSlice(
            tensor_key=spec.tensor_key,
            projection=spec.projection,
            dtype=spec.dtype,
            shape=spec.shape,
            relative_range=spec.relative_offsets,
            absolute_range=(start, start + spec.expected_bytes),
            payload_bytes=spec.expected_bytes,
            payload_sha256=_sha256(raw),
        )
        item.validate()
        observed.append(item)

    new_bytes = sum(item.payload_bytes for item in observed)
    if new_bytes != EXPECTED_NEW_PAYLOAD_BYTES:
        raise RemainingPayloadError("Q12_NEW_PAYLOAD_ACCOUNTING_DRIFT")
    if EXPECTED_INHERITED_PAYLOAD_BYTES + new_bytes != EXPECTED_TOTAL_PAYLOAD_BYTES:
        raise RemainingPayloadError("Q12_COMBINED_PAYLOAD_ACCOUNTING_DRIFT")

    receipt = RemainingPayloadReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR653_HEAD, PR654_HEAD),
        exact_parent_runs=(PR653_RUN, PR654_RUN),
        official_repository=canary.OFFICIAL_REPOSITORY,
        official_revision=canary.OFFICIAL_REVISION,
        selected_layer=canary.SELECTED_LAYER,
        selected_expert=canary.SELECTED_EXPERT,
        selected_shard=canary.SELECTED_SHARD,
        current_header_length_bytes=header_len,
        current_header_sha256=header_sha,
        current_header_exactly_revalidated=True,
        strict_http_range_only=True,
        full_shard_fallback_accepted=False,
        inherited_gate_weight_sha256=delta.LIVE_GATE_WEIGHT_SHA256,
        inherited_gate_scale_sha256=delta.LIVE_GATE_SCALE_SHA256,
        inherited_slice_count=EXPECTED_INHERITED_SLICE_COUNT,
        newly_observed_slice_count=len(observed),
        combined_slice_count=EXPECTED_INHERITED_SLICE_COUNT + len(observed),
        newly_observed_payload_bytes=new_bytes,
        inherited_payload_bytes=EXPECTED_INHERITED_PAYLOAD_BYTES,
        combined_representative_payload_bytes=EXPECTED_INHERITED_PAYLOAD_BYTES + new_bytes,
        observed_slices=tuple(observed),
        up_pair_observed=sum(item.projection == "up" for item in observed) == 2,
        down_pair_observed=sum(item.projection == "down" for item in observed) == 2,
        representative_expert_raw_payload_coverage_complete=True,
        full_shard_payload_observed=False,
        all_layers_experts_payload_coverage_proven=False,
        raw_fp8_payload_is_canonical_float32_source_identity=False,
        block_fp8_dequantization_semantics_bound=False,
        gate_up_source_layout_relation_bound=False,
        exact_official_tensor_to_pr628_source_tensor_relation_proven=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        representative_scope_only=True,
        real_tensor_quantization_eligible=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
        disposition="REPRESENTATIVE_EXPERT_RAW_PAYLOAD_COVERAGE_COMPLETE",
    )
    if receipt.combined_slice_count != EXPECTED_TOTAL_SLICE_COUNT:
        raise RemainingPayloadError("Q12_COMBINED_SLICE_COUNT_DRIFT")
    return receipt


def _observe_with(fetch_range: RangeReader) -> RemainingPayloadReceipt:
    url = canary.hf_resolve_url(canary.OFFICIAL_REPOSITORY, canary.OFFICIAL_REVISION, canary.SELECTED_SHARD)
    header_len, header_sha = _read_and_validate_current_header(url, fetch_range)
    data_base = 8 + header_len
    payloads: dict[str, bytes] = {}
    for spec in missing_source_slices():
        start = data_base + spec.relative_offsets[0]
        payloads[spec.tensor_key] = fetch_range(url, start, spec.expected_bytes)
    return _build_receipt(header_len=header_len, header_sha=header_sha, payloads=payloads)


def current_live_remaining_observation() -> RemainingPayloadReceipt:
    """Execute exactly the A4-admitted four-slice read cone."""
    return _observe_with(canary.urllib_read_range)


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_live_remaining_observation).parameters) != 0


def main() -> None:
    receipt = current_live_remaining_observation()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "PartialCoverage+MinimumEvidenceCover=>FetchOnlyMissingFourSlices",
        "RepresentativeRawPayloadCoverageComplete!=CanonicalFloat32SourceTensor",
        "PayloadCoverage!=DequantizationSemantics!=SourceIdentity!=PageMaterialization",
        "K27Coordinate!=SourceAuthority!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
