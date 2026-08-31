#!/usr/bin/env python3
"""Materialize the minimum official-source-bound E8 page canary for GLM-5.3.

Q14 composes two exact-green other-agent owners:
- Q13 / PR663: full representative canonical official source-set identity.
- A6 / PR661: execution evidence must be decisive before HyperScale meaning is assigned.

The existing PR628 codec is deliberately reused unchanged.  Its exhaustive
58,112-codeword nearest search is suitable for a falsifying canary but is not
silently promoted into a full two-role producer: the full representative roles
contain 4,718,592 8D vectors, which would require 274,206,818,304 codeword
scores under the current reference search.  HS1 therefore materializes one
exact 64-weight source block from each official role and leaves full-role page
production open for a separately earned scalable encoder/materializer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct
from typing import Any

import numpy as np

from tools.quantization import aura_glm53_full_representative_canonical_source_set as q13
from tools.quantization import aura_glm53_e8_indexed_expert_page_reference as page_ref

SCHEMA = "AURA_GLM53_OFFICIAL_SOURCE_E8_MATERIALIZATION_CANARY_V1"
CONVERGENCE_COMMIT = "c32fe9d8d97c6e879b3e49baf5b2415d3c846453"
Q13_HEAD = "eb09b5ffd14577d1676f57bb908e5ddd81125605"
Q13_RUN = 33397035043
Q13_JOB = 99503908177
A6_HEAD = "8179ffe054abc2ec144757888957c9ca27df991c"
A6_RUN = 33396942368
PR628_SOURCE_BLOB = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"
A6_SOURCE_BLOB = "1ba4a33a05dd643d8be911d8fc103fb110bc3bb0"
A6_CLASSIFIER_BLOB = "150aba95dc1aed3e938892a742a6d5f65d75e41d"
REPRESENTATION_REVISION = "AURA_Q14_OFFICIAL_TILE_CANARY_R1"
TILE_WEIGHTS = 64
FULL_ROLE_WEIGHTS = 4096 * 6144 + 6144 * 2048
FULL_ROLE_VECTOR_COUNT = FULL_ROLE_WEIGHTS // page_ref.VECTOR_DIM
REFERENCE_CODEBOOK_SIZE = 58_112
NAIVE_FULL_ROLE_CODEWORD_SCORES = FULL_ROLE_VECTOR_COUNT * REFERENCE_CODEBOOK_SIZE

ROLE_SOURCE = {
    "gate_up_proj": ("gate_weight", "gate_scale", "gate_prefix"),
    "down_proj": ("down_weight", "down_scale", "down_prefix"),
}


class MaterializationCanaryError(ValueError):
    pass


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object_sha(value: object) -> str:
    return _sha(_canonical(value))


def canonical_first_block(weight_raw: bytes, scale_raw: bytes) -> np.ndarray:
    """Decode exactly the first 64 C-order weights of one 128x128 FP8 block."""
    if len(weight_raw) != TILE_WEIGHTS or len(scale_raw) != 4:
        raise MaterializationCanaryError("EXACT_TILE_PAYLOAD_LENGTH_REQUIRED")
    codes = np.frombuffer(weight_raw, dtype=np.uint8)
    if np.any((codes == 0x7F) | (codes == 0xFF)):
        raise MaterializationCanaryError("E4M3FN_NAN_IN_TILE")
    scale = float(np.frombuffer(scale_raw, dtype="<f4")[0])
    if not math.isfinite(scale) or scale <= 0.0:
        raise MaterializationCanaryError("INVALID_TILE_SCALE")
    values = q13.decode_e4m3fn_table()[codes] * np.float32(scale)
    return np.asarray(values, dtype="<f4", order="C").reshape(1, TILE_WEIGHTS)


def _validate_q13_receipt(receipt: q13.FullRepresentativeCanonicalSourceSetReceipt) -> dict[str, dict[str, Any]]:
    if not receipt.full_representative_canonical_source_set_bound:
        raise MaterializationCanaryError("Q13_SOURCE_SET_NOT_BOUND")
    if not receipt.representative_official_source_tensor_set_authenticated:
        raise MaterializationCanaryError("Q13_OFFICIAL_SOURCE_NOT_AUTHENTICATED")
    if receipt.source_set_schema != q13.SOURCE_SET_SCHEMA:
        raise MaterializationCanaryError("Q13_SOURCE_SET_SCHEMA_DRIFT")
    if receipt.actual_e8_page_payload_materialized:
        raise MaterializationCanaryError("Q13_CLAIM_BOUNDARY_DRIFT")
    by_role = {str(entry["tensor_role"]): dict(entry) for entry in receipt.source_set_entries}
    if set(by_role) != set(ROLE_SOURCE):
        raise MaterializationCanaryError("Q13_ROLE_SET_DRIFT")
    return by_role


def _fetch_live_role_tile(role: str) -> tuple[int, bytes, bytes, str]:
    if role not in ROLE_SOURCE:
        raise MaterializationCanaryError("UNSUPPORTED_CANARY_ROLE")
    weight_name, scale_name, component = ROLE_SOURCE[role]
    url = q13.canary.hf_resolve_url(q13.OFFICIAL_REPOSITORY, q13.OFFICIAL_REVISION, q13.SELECTED_SHARD)
    prefix = q13.canary.urllib_read_range(url, 0, 8)
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len != q13.EXPECTED_HEADER_LENGTH:
        raise MaterializationCanaryError("LIVE_HEADER_LENGTH_DRIFT")
    base = 8 + header_len
    wspec = q13.SLICES[weight_name]
    sspec = q13.SLICES[scale_name]
    weight_raw = q13.canary.urllib_read_range(url, base + int(wspec["offset"][0]), TILE_WEIGHTS)
    scale_raw = q13.canary.urllib_read_range(url, base + int(sspec["offset"][0]), 4)
    return int(header_len), weight_raw, scale_raw, component


@dataclass(frozen=True)
class RoleCanary:
    tensor_role: str
    full_role_source_sha256: str
    full_role_source_shape: tuple[int, int]
    full_source_set_digest: str
    source_component: str
    source_weight_offset: int
    source_weight_count: int
    raw_fp8_tile_sha256: str
    raw_scale_cell_sha256: str
    canonical_tile_sha256: str
    canonical_tile_shape: tuple[int, int]
    page_identity_digest: str
    page_payload_sha256: str
    page_payload_bytes: int
    page_k27_coordinate: tuple[int, int, int]
    codec_bits_per_weight: float
    serialized_bits_per_weight: float
    decoded_page_shape: tuple[int, int]
    decoded_page_sha256: str
    page_source_identity_matches_canonical_tile: bool
    tile_relation_to_q13_role_bound: bool
    actual_e8_page_payload_materialized: bool
    official_source_to_e8_page_derivation_proven_for_tile: bool
    page_materialization_owner_bound_for_tile: bool


@dataclass(frozen=True)
class OfficialSourceE8MaterializationCanaryReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    q13_job: int
    inherited_source_set_digest: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    live_header_length_bytes: int
    representation_scheme: str
    representation_revision: str
    pr628_source_blob: str
    a6_source_blob: str
    a6_classifier_blob: str
    role_canaries: tuple[RoleCanary, ...]
    canary_page_set_digest: str
    full_role_weights: int
    full_role_vector_count: int
    reference_codebook_size: int
    naive_full_role_codeword_scores: int
    minimum_canary_cone_weights: int
    execution_state_must_terminalize_outside_semantic_owner: bool
    provider_gate_counts_as_materialization_failure: bool
    provider_gate_counts_as_materialization_success: bool
    two_official_source_bound_tile_pages_materialized: bool
    full_role_page_payloads_materialized: bool
    full_source_set_page_set_materialized: bool
    baseline_same_official_source_tensor_set_proven: bool
    whole_model_coverage_proven: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    physical_io_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    merge_or_deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _object_sha(asdict(self))


def materialize_role_canary(
    *,
    q13_receipt: q13.FullRepresentativeCanonicalSourceSetReceipt,
    role: str,
    weight_raw: bytes,
    scale_raw: bytes,
    source_component: str,
) -> RoleCanary:
    entries = _validate_q13_receipt(q13_receipt)
    if role not in entries or role not in ROLE_SOURCE:
        raise MaterializationCanaryError("ROLE_NOT_IN_Q13_SOURCE_SET")
    expected_component = ROLE_SOURCE[role][2]
    if source_component != expected_component:
        raise MaterializationCanaryError("ROLE_COMPONENT_MISMATCH")

    tile = canonical_first_block(weight_raw, scale_raw)
    tile_bytes = np.asarray(tile, dtype="<f4", order="C").tobytes(order="C")
    tile_sha = _sha(tile_bytes)
    page = page_ref.pack_expert_page(
        tile,
        model_revision=q13.OFFICIAL_REVISION,
        representation_revision=REPRESENTATION_REVISION,
        layer_id=q13.SELECTED_LAYER,
        expert_id=q13.SELECTED_EXPERT,
        tensor_role=role,
        block_size=page_ref.DEFAULT_BLOCK_SIZE,
    )
    decoded = np.asarray(page_ref.unpack_expert_page(page), dtype="<f4", order="C")
    decoded_bytes = decoded.tobytes(order="C")
    entry = entries[role]
    shape = tuple(int(x) for x in entry["source_shape"])
    if len(shape) != 2:
        raise MaterializationCanaryError("FULL_ROLE_SHAPE_INVALID")
    if page.identity.source_tensor_sha256 != tile_sha or page.identity.source_shape != (1, TILE_WEIGHTS):
        raise MaterializationCanaryError("PAGE_SOURCE_TILE_IDENTITY_DRIFT")

    return RoleCanary(
        tensor_role=role,
        full_role_source_sha256=str(entry["source_tensor_sha256"]),
        full_role_source_shape=(shape[0], shape[1]),
        full_source_set_digest=q13_receipt.source_tensor_set_digest,
        source_component=source_component,
        source_weight_offset=0,
        source_weight_count=TILE_WEIGHTS,
        raw_fp8_tile_sha256=_sha(weight_raw),
        raw_scale_cell_sha256=_sha(scale_raw),
        canonical_tile_sha256=tile_sha,
        canonical_tile_shape=(1, TILE_WEIGHTS),
        page_identity_digest=page.identity.digest(),
        page_payload_sha256=page.payload_sha256,
        page_payload_bytes=len(page.payload),
        page_k27_coordinate=page.k27_coordinate,
        codec_bits_per_weight=page.codec_bits_per_weight,
        serialized_bits_per_weight=page.serialized_bits_per_weight,
        decoded_page_shape=tuple(int(x) for x in decoded.shape),
        decoded_page_sha256=_sha(decoded_bytes),
        page_source_identity_matches_canonical_tile=True,
        tile_relation_to_q13_role_bound=True,
        actual_e8_page_payload_materialized=True,
        official_source_to_e8_page_derivation_proven_for_tile=True,
        page_materialization_owner_bound_for_tile=True,
    )


def current_official_source_materialization_canary() -> OfficialSourceE8MaterializationCanaryReceipt:
    q13_receipt = q13.current_full_representative_source_set()
    _validate_q13_receipt(q13_receipt)
    if page_ref.codebook()[0].shape != (REFERENCE_CODEBOOK_SIZE, page_ref.VECTOR_DIM):
        raise MaterializationCanaryError("PR628_CODEBOOK_GEOMETRY_DRIFT")

    role_canaries: list[RoleCanary] = []
    header_lengths: set[int] = set()
    for role in sorted(ROLE_SOURCE):
        header_len, weight_raw, scale_raw, component = _fetch_live_role_tile(role)
        header_lengths.add(header_len)
        role_canaries.append(
            materialize_role_canary(
                q13_receipt=q13_receipt,
                role=role,
                weight_raw=weight_raw,
                scale_raw=scale_raw,
                source_component=component,
            )
        )
    if header_lengths != {q13.EXPECTED_HEADER_LENGTH}:
        raise MaterializationCanaryError("INCONSISTENT_HEADER_GENERATION")

    canary_body = {
        "schema": "AURA_Q14_OFFICIAL_SOURCE_E8_TILE_PAGE_SET_V1",
        "source_tensor_set_digest": q13_receipt.source_tensor_set_digest,
        "representation_revision": REPRESENTATION_REVISION,
        "roles": [asdict(x) for x in role_canaries],
    }
    canary_digest = _object_sha(canary_body)
    return OfficialSourceE8MaterializationCanaryReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(Q13_HEAD, A6_HEAD),
        exact_parent_runs=(Q13_RUN, A6_RUN),
        q13_job=Q13_JOB,
        inherited_source_set_digest=q13_receipt.source_tensor_set_digest,
        official_repository=q13.OFFICIAL_REPOSITORY,
        official_revision=q13.OFFICIAL_REVISION,
        selected_layer=q13.SELECTED_LAYER,
        selected_expert=q13.SELECTED_EXPERT,
        selected_shard=q13.SELECTED_SHARD,
        live_header_length_bytes=q13.EXPECTED_HEADER_LENGTH,
        representation_scheme=page_ref.SCHEME,
        representation_revision=REPRESENTATION_REVISION,
        pr628_source_blob=PR628_SOURCE_BLOB,
        a6_source_blob=A6_SOURCE_BLOB,
        a6_classifier_blob=A6_CLASSIFIER_BLOB,
        role_canaries=tuple(role_canaries),
        canary_page_set_digest=canary_digest,
        full_role_weights=FULL_ROLE_WEIGHTS,
        full_role_vector_count=FULL_ROLE_VECTOR_COUNT,
        reference_codebook_size=REFERENCE_CODEBOOK_SIZE,
        naive_full_role_codeword_scores=NAIVE_FULL_ROLE_CODEWORD_SCORES,
        minimum_canary_cone_weights=len(role_canaries) * TILE_WEIGHTS,
        execution_state_must_terminalize_outside_semantic_owner=True,
        provider_gate_counts_as_materialization_failure=False,
        provider_gate_counts_as_materialization_success=False,
        two_official_source_bound_tile_pages_materialized=len(role_canaries) == 2,
        full_role_page_payloads_materialized=False,
        full_source_set_page_set_materialized=False,
        baseline_same_official_source_tensor_set_proven=False,
        whole_model_coverage_proven=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        physical_io_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_or_deployment_authorized=False,
    )


def main() -> None:
    receipt = current_official_source_materialization_canary()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["laws"] = (
        "CanonicalOfficialSourceSet!=MaterializedE8PageSet",
        "ExactOfficialSourceTile+ExactExistingCodec=>OfficialSourceBoundPageCanary",
        "TilePageCanary!=FullRolePageMaterialization",
        "ReferenceCodecCorrectness!=ReferenceCodecScalability",
        "MinimumEvidenceConeBeforeHyperScaleFanout",
        "PreJobProviderGate!=MaterializationFailure!=MaterializationSuccess",
        "K27Coordinate!=SourceAuthority!=ProducerAuthority",
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
