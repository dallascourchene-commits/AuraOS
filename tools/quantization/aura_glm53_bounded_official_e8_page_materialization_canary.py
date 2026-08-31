#!/usr/bin/env python3
"""Materialize two bounded official GLM-5.3 canonical slices into real E8 pages.

Q14 crosses exactly one evidence boundary beyond Q13: it takes the first 64
canonical float32 weights from each representative model role (``gate_up_proj``
and ``down_proj``), binds those slices to Q13's authenticated full-role source
identities, and packs them with the exact historical PR628 indexed-E8 codec.

The historical codec is reusable support evidence, not a fresh semantic sibling.
Q14 therefore proves a bounded source-slice -> page materialization edge only.
It does not claim that the full representative tensors, the full expert, or the
whole model have been materialized into E8 pages, and it does not execute GLM.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import math
import struct

import numpy as np

from tools.quantization import aura_glm53_e8_indexed_expert_page_reference as page_ref
from tools.quantization import aura_glm53_full_representative_canonical_source_set as q13
from tools.quantization import aura_glm53_live_official_tensor_payload_canary as canary

SCHEMA = "AURA_GLM53_BOUNDED_OFFICIAL_E8_PAGE_MATERIALIZATION_CANARY_V1"
CONVERGENCE_COMMIT = "f93fe24fa5801378815d7094bbf64c815fd48af1"

Q13_HEAD = "eb09b5ffd14577d1676f57bb908e5ddd81125605"
Q13_RUN = 33397035043
Q13_JOB = 99503908177
Q13_RECEIPT_DIGEST = "c143eab6f319689faf1315e32fa9cea1182f7e4ba52372ff5d0c8218d9f4f832"
Q13_SOURCE_SET_DIGEST = "f41495beb566f4c49f5674f2820f3d5c32591647be552048cf711a885a1b71b6"
Q13_GATE_UP_SHA256 = "46eb726b48a423865b50ffe261881dc5b3667344f93e24e5732b2484d6096c4a"
Q13_DOWN_SHA256 = "6ddd0776b011cde6948d5d780630700dfd69ce49907356d371a6d54b59040953"

A6_HEAD = "fa428111f83a0f69319c10c1b28bde910544b776"
A6_RUN = 33397763034
A6_JOB = 99506305907
A6_RECEIPT_DIGEST = "86f7f614167e95c0099c828f91b091675238c177c202beb65e11450bec97f847"

PR628_HEAD = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
# Direct contents reads at PR628 and Q13 prove this executable codec file is
# byte-identical at both generations.  It is historical reusable support, not a
# fresh semantic parent of Q14.
PR628_CODEC_BLOB = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"
REPRESENTATION_REVISION = f"{page_ref.SCHEME}@{PR628_HEAD}"

OFFICIAL_REPOSITORY = q13.OFFICIAL_REPOSITORY
OFFICIAL_REVISION = q13.OFFICIAL_REVISION
SELECTED_SHARD = q13.SELECTED_SHARD
SELECTED_LAYER = q13.SELECTED_LAYER
SELECTED_EXPERT = q13.SELECTED_EXPERT
EXPECTED_HEADER_LENGTH = q13.EXPECTED_HEADER_LENGTH
EXPECTED_HEADER_SHA256 = canary.SELECTED_HEADER_SHA256
SLICE_WEIGHT_COUNT = 64
EXPECTED_NEW_RAW_PAYLOAD_BYTES = 136  # 64+4 bytes for gate plus 64+4 for down.


class BoundedMaterializationError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _object_sha(value: object) -> str:
    return _sha256(_canonical(value))


def _validate_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise BoundedMaterializationError(label + "_SHA256_REQUIRED")
    try:
        bytes.fromhex(value)
    except ValueError as exc:
        raise BoundedMaterializationError(label + "_SHA256_REQUIRED") from exc


@dataclass(frozen=True)
class MaterializedSlicePage:
    tensor_role: str
    parent_full_source_sha256: str
    parent_full_source_shape: tuple[int, ...]
    slice_flat_offset: int
    slice_weight_count: int
    slice_semantics: str
    source_slice_sha256: str
    source_slice_float32_bytes: int
    page_identity_digest: str
    page_payload_sha256: str
    page_payload_bytes: int
    codebook_digest: str
    representation_revision: str
    k27_coordinate: tuple[int, int, int]
    codec_bits_per_weight: float
    serialized_bits_per_weight: float

    def validate(self) -> None:
        if self.tensor_role not in page_ref.TENSOR_ROLES:
            raise BoundedMaterializationError("Q14_ROLE_INVALID")
        _validate_sha256(self.parent_full_source_sha256, "PARENT_FULL_SOURCE")
        _validate_sha256(self.source_slice_sha256, "SOURCE_SLICE")
        _validate_sha256(self.page_identity_digest, "PAGE_IDENTITY")
        _validate_sha256(self.page_payload_sha256, "PAGE_PAYLOAD")
        _validate_sha256(self.codebook_digest, "CODEBOOK")
        if not self.parent_full_source_shape or any(type(x) is not int or x <= 0 for x in self.parent_full_source_shape):
            raise BoundedMaterializationError("Q14_PARENT_SHAPE_INVALID")
        if self.slice_flat_offset != 0 or self.slice_weight_count != SLICE_WEIGHT_COUNT:
            raise BoundedMaterializationError("Q14_SLICE_COORDINATE_DRIFT")
        if self.source_slice_float32_bytes != SLICE_WEIGHT_COUNT * 4:
            raise BoundedMaterializationError("Q14_SLICE_F32_BYTE_COUNT_DRIFT")
        if self.page_payload_bytes <= 0:
            raise BoundedMaterializationError("Q14_PAGE_PAYLOAD_EMPTY")
        if self.representation_revision != REPRESENTATION_REVISION:
            raise BoundedMaterializationError("Q14_REPRESENTATION_REVISION_DRIFT")
        if len(self.k27_coordinate) != 3 or any(type(x) is not int or x < 0 or x >= 27 for x in self.k27_coordinate):
            raise BoundedMaterializationError("Q14_K27_COORDINATE_INVALID")
        if not math.isfinite(self.codec_bits_per_weight) or self.codec_bits_per_weight <= 0:
            raise BoundedMaterializationError("Q14_CODEC_RATE_INVALID")
        if not math.isfinite(self.serialized_bits_per_weight) or self.serialized_bits_per_weight <= 0:
            raise BoundedMaterializationError("Q14_SERIALIZED_RATE_INVALID")


@dataclass(frozen=True)
class BoundedOfficialE8PageMaterializationReceipt:
    schema: str
    convergence_commit: str
    exact_fresh_parent_heads: tuple[str, str]
    exact_fresh_parent_runs: tuple[int, int]
    exact_fresh_parent_jobs: tuple[int, int]
    q13_receipt_digest: str
    q13_source_tensor_set_digest: str
    a6_receipt_digest: str
    pr628_historical_codec_head: str
    pr628_historical_codec_blob: str
    historical_codec_reuse_requires_no_fresh_sibling_credit: bool
    official_repository: str
    official_revision: str
    selected_shard: str
    selected_layer: int
    selected_expert: int
    live_header_length_bytes: int
    live_header_sha256: str
    new_raw_payload_bytes_read: int
    source_slice_count: int
    materialized_page_count: int
    pages: tuple[MaterializedSlicePage, ...]
    q13_full_source_set_parent_bound: bool
    exact_source_slice_coordinates_bound: bool
    actual_e8_page_payloads_materialized: bool
    bounded_source_slice_to_page_derivation_proven: bool
    candidate_page_materialization_owner_bound_for_bounded_canary: bool
    source_slice_identity_is_full_tensor_identity: bool
    bounded_materialization_is_full_representative_source_set_materialization: bool
    baseline_same_official_source_tensor_set_proven: bool
    whole_model_coverage_proven: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _object_sha(asdict(self))


def _decode_first64(weight_raw: bytes, scale_raw: bytes) -> np.ndarray:
    if len(weight_raw) != SLICE_WEIGHT_COUNT or len(scale_raw) != 4:
        raise BoundedMaterializationError("Q14_LIVE_SLICE_LENGTH_MISMATCH")
    codes = np.frombuffer(weight_raw, dtype=np.uint8)
    if np.any((codes == 0x7F) | (codes == 0xFF)):
        raise BoundedMaterializationError("Q14_E4M3FN_NAN_IN_SOURCE_SLICE")
    scale = struct.unpack("<f", scale_raw)[0]
    if not math.isfinite(scale) or scale <= 0.0:
        raise BoundedMaterializationError("Q14_INVALID_SOURCE_SCALE")
    table = q13.decode_e4m3fn_table()
    values = table[codes] * np.float32(scale)
    values = np.asarray(values, dtype="<f4", order="C")
    if values.shape != (SLICE_WEIGHT_COUNT,) or not np.all(np.isfinite(values)):
        raise BoundedMaterializationError("Q14_CANONICAL_SLICE_INVALID")
    return values


def _materialize_slice_page(
    *, tensor_role: str, parent_full_source_sha256: str,
    parent_full_source_shape: tuple[int, ...], canonical_values: np.ndarray,
) -> tuple[MaterializedSlicePage, page_ref.ExpertPage]:
    _validate_sha256(parent_full_source_sha256, "PARENT_FULL_SOURCE")
    values = np.asarray(canonical_values, dtype="<f4", order="C").reshape(-1)
    if values.shape != (SLICE_WEIGHT_COUNT,) or not np.all(np.isfinite(values)):
        raise BoundedMaterializationError("Q14_CANONICAL_SLICE_INVALID")
    source_bytes = values.tobytes(order="C")
    slice_sha = _sha256(source_bytes)
    page = page_ref.pack_expert_page(
        values,
        model_revision=OFFICIAL_REVISION,
        representation_revision=REPRESENTATION_REVISION,
        layer_id=SELECTED_LAYER,
        expert_id=SELECTED_EXPERT,
        tensor_role=tensor_role,
        block_size=page_ref.DEFAULT_BLOCK_SIZE,
    )
    page.validate()
    if page.identity.source_tensor_sha256 != slice_sha:
        raise BoundedMaterializationError("Q14_PAGE_SOURCE_SLICE_IDENTITY_MISMATCH")
    decoded = np.asarray(page_ref.unpack_expert_page(page), dtype=np.float32).reshape(-1)
    if decoded.shape != (SLICE_WEIGHT_COUNT,) or not np.all(np.isfinite(decoded)):
        raise BoundedMaterializationError("Q14_PAGE_DECODE_INVALID")
    item = MaterializedSlicePage(
        tensor_role=tensor_role,
        parent_full_source_sha256=parent_full_source_sha256,
        parent_full_source_shape=parent_full_source_shape,
        slice_flat_offset=0,
        slice_weight_count=SLICE_WEIGHT_COUNT,
        slice_semantics="canonical_<f4_C_order_flat[0:64]",
        source_slice_sha256=slice_sha,
        source_slice_float32_bytes=len(source_bytes),
        page_identity_digest=page.identity.digest(),
        page_payload_sha256=page.payload_sha256,
        page_payload_bytes=len(page.payload),
        codebook_digest=page_ref.codebook_digest(),
        representation_revision=REPRESENTATION_REVISION,
        k27_coordinate=page.k27_coordinate,
        codec_bits_per_weight=page.codec_bits_per_weight,
        serialized_bits_per_weight=page.serialized_bits_per_weight,
    )
    item.validate()
    return item, page


def _fetch_current_source_slices() -> tuple[int, str, np.ndarray, np.ndarray]:
    """Read only the current header plus two 64-weight/one-scale source cones."""
    url = canary.hf_resolve_url(OFFICIAL_REPOSITORY, OFFICIAL_REVISION, SELECTED_SHARD)
    prefix = canary.urllib_read_range(url, 0, 8)
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len != EXPECTED_HEADER_LENGTH:
        raise BoundedMaterializationError("Q14_LIVE_HEADER_LENGTH_DRIFT")
    header_raw = canary.urllib_read_range(url, 8, header_len)
    header_sha = _sha256(header_raw)
    if header_sha != EXPECTED_HEADER_SHA256:
        raise BoundedMaterializationError("Q14_LIVE_HEADER_SHA256_DRIFT")
    base = 8 + header_len

    gate_w = q13.SLICES["gate_weight"]
    gate_s = q13.SLICES["gate_scale"]
    down_w = q13.SLICES["down_weight"]
    down_s = q13.SLICES["down_scale"]

    gate_weight_raw = canary.urllib_read_range(url, base + gate_w["offset"][0], SLICE_WEIGHT_COUNT)
    gate_scale_raw = canary.urllib_read_range(url, base + gate_s["offset"][0], 4)
    down_weight_raw = canary.urllib_read_range(url, base + down_w["offset"][0], SLICE_WEIGHT_COUNT)
    down_scale_raw = canary.urllib_read_range(url, base + down_s["offset"][0], 4)
    if sum(map(len, (gate_weight_raw, gate_scale_raw, down_weight_raw, down_scale_raw))) != EXPECTED_NEW_RAW_PAYLOAD_BYTES:
        raise BoundedMaterializationError("Q14_RAW_PAYLOAD_BUDGET_DRIFT")

    # gate_up_proj is row-concatenate([gate, up]); flat[0:64] is therefore
    # exactly gate_proj canonical flat[0:64]. Down is direct.
    gate_up_values = _decode_first64(gate_weight_raw, gate_scale_raw)
    down_values = _decode_first64(down_weight_raw, down_scale_raw)
    return header_len, header_sha, gate_up_values, down_values


def current_bounded_materialization() -> BoundedOfficialE8PageMaterializationReceipt:
    header_len, header_sha, gate_up_values, down_values = _fetch_current_source_slices()
    gate_up, _ = _materialize_slice_page(
        tensor_role="gate_up_proj",
        parent_full_source_sha256=Q13_GATE_UP_SHA256,
        parent_full_source_shape=(4096, 6144),
        canonical_values=gate_up_values,
    )
    down, _ = _materialize_slice_page(
        tensor_role="down_proj",
        parent_full_source_sha256=Q13_DOWN_SHA256,
        parent_full_source_shape=(6144, 2048),
        canonical_values=down_values,
    )
    pages = tuple(sorted((gate_up, down), key=lambda item: item.tensor_role))
    if {p.tensor_role for p in pages} != page_ref.TENSOR_ROLES:
        raise BoundedMaterializationError("Q14_TWO_ROLE_COVERAGE_REQUIRED")
    if any(p.source_slice_sha256 == p.parent_full_source_sha256 for p in pages):
        raise BoundedMaterializationError("Q14_SLICE_FULL_SOURCE_IDENTITY_COLLISION")

    return BoundedOfficialE8PageMaterializationReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_fresh_parent_heads=(Q13_HEAD, A6_HEAD),
        exact_fresh_parent_runs=(Q13_RUN, A6_RUN),
        exact_fresh_parent_jobs=(Q13_JOB, A6_JOB),
        q13_receipt_digest=Q13_RECEIPT_DIGEST,
        q13_source_tensor_set_digest=Q13_SOURCE_SET_DIGEST,
        a6_receipt_digest=A6_RECEIPT_DIGEST,
        pr628_historical_codec_head=PR628_HEAD,
        pr628_historical_codec_blob=PR628_CODEC_BLOB,
        historical_codec_reuse_requires_no_fresh_sibling_credit=True,
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        selected_shard=SELECTED_SHARD,
        selected_layer=SELECTED_LAYER,
        selected_expert=SELECTED_EXPERT,
        live_header_length_bytes=header_len,
        live_header_sha256=header_sha,
        new_raw_payload_bytes_read=EXPECTED_NEW_RAW_PAYLOAD_BYTES,
        source_slice_count=len(pages),
        materialized_page_count=len(pages),
        pages=pages,
        q13_full_source_set_parent_bound=True,
        exact_source_slice_coordinates_bound=True,
        actual_e8_page_payloads_materialized=True,
        bounded_source_slice_to_page_derivation_proven=True,
        candidate_page_materialization_owner_bound_for_bounded_canary=True,
        source_slice_identity_is_full_tensor_identity=False,
        bounded_materialization_is_full_representative_source_set_materialization=False,
        baseline_same_official_source_tensor_set_proven=False,
        whole_model_coverage_proven=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_bounded_materialization).parameters) != 0


def main() -> None:
    receipt = current_bounded_materialization()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "FullSourceIdentity!=SliceIdentity!=PageIdentity",
        "AuthenticatedCanonicalSource+ExactSliceCoordinates+ExactCodec=>BoundedMaterializationReceipt",
        "HistoricalCodecReuse!=FreshSemanticSibling",
        "BoundedMaterializationCanary!=FullRepresentativePageSet",
        "PagePayloadObserved!=ModelExecution",
        "K27Coordinate!=PageAuthority!=SemanticAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
