#!/usr/bin/env python3
"""Bind one live official GLM-5.3 FP8 gate tensor to canonical float32 identity.

Q12 crosses exactly one representation boundary beyond PR650: the already-earned
raw FP8 gate payload plus its F32 ``weight_scale_inv`` grid are re-observed from
the immutable source and deterministically dequantized into the same canonical
little-endian float32 byte domain used by PR628 source-tensor identity.

It does not compose gate+up, materialize an E8 page, bind a PR641 page set to the
official source, establish a baseline relation, execute the model, or grant any
authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct

import numpy as np

from tools.quantization import aura_glm53_live_official_tensor_payload_canary as live

SCHEMA = "AURA_GLM53_LIVE_GATE_FP8_CANONICAL_F32_IDENTITY_V1"
CONVERGENCE_COMMIT = "e5a981234bd8c1a48bfc8711faa5458929c217fa"
PR650_HEAD = "e8e0eecb5fce9f95bf1b71e97b528776ecd8b51c"
PR650_RUN = 33374008643
PR650_JOB = 99431263469
PR641_HEAD = "a8d4605a36e04d64cf03f43f457be4bde553e602"
PR641_RUN = 33370700852
PR641_SOURCE_BLOB = "7951124182a0ed9396cf294a8c811bf8555391a9"
PR628_HEAD = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
PR628_SOURCE_BLOB = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"

E4M3FN_SPEC = "S1E4M3_BIAS7_FINITE_OUTER_NAN"
CANONICAL_FLOAT32_DOMAIN = "IEEE754_BINARY32_LITTLE_ENDIAN_C_ORDER"
BLOCK_SHAPE = (128, 128)
EXPECTED_WEIGHT_SHA256 = "2d4e5f36478b598043431b3691ce6a48639e01b6f804b1db62ca4af4d14063e8"
EXPECTED_SCALE_SHA256 = "671dd3b32b3f4cc651b93f3420ae47957ae09c1f745d278c0795d56e5d511c55"
EXPECTED_WEIGHT_BYTES = 12_582_912
EXPECTED_SCALE_BYTES = 3_072
EXPECTED_CANONICAL_F32_BYTES = 50_331_648


class GateDequantizationError(ValueError):
    pass


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def decode_e4m3fn_byte(code: int) -> float:
    """Decode one OCP-style finite E4M3FN byte to an exactly representable float.

    Layout is S1E4M3 with exponent bias 7. Exponent 0 is subnormal/zero. The
    outer codes S1111111 are NaN; exponent 15 with mantissa 0..6 remains finite,
    giving maximum magnitude 448.
    """
    if isinstance(code, bool) or not isinstance(code, int) or not 0 <= code <= 0xFF:
        raise GateDequantizationError("invalid E4M3FN byte")
    sign = -1.0 if code & 0x80 else 1.0
    exponent = (code >> 3) & 0x0F
    mantissa = code & 0x07
    if exponent == 0x0F and mantissa == 0x07:
        raise GateDequantizationError("E4M3FN NaN code in weight payload")
    if exponent == 0:
        magnitude = math.ldexp(float(mantissa), -9)  # 2^(1-bias) * mantissa/8
    else:
        magnitude = math.ldexp(1.0 + mantissa / 8.0, exponent - 7)
    if magnitude == 0.0 and sign < 0:
        return -0.0
    return sign * magnitude


def e4m3fn_lookup_table() -> np.ndarray:
    table = np.empty(256, dtype="<f4")
    for code in range(256):
        if code in (0x7F, 0xFF):
            table[code] = np.nan
        else:
            table[code] = decode_e4m3fn_byte(code)
    return table


def dequantize_blockwise_to_canonical_f32(
    weight_raw: bytes,
    scale_raw: bytes,
    *,
    weight_shape: tuple[int, int],
    scale_shape: tuple[int, int],
) -> bytes:
    """Dequantize row-major E4M3FN weights by an exact F32 inverse-scale grid."""
    if len(weight_shape) != 2 or len(scale_shape) != 2:
        raise GateDequantizationError("rank-2 weight/scale required")
    rows, cols = weight_shape
    scale_rows, scale_cols = scale_shape
    if min(rows, cols, scale_rows, scale_cols) <= 0:
        raise GateDequantizationError("non-positive tensor geometry")
    if rows % scale_rows or cols % scale_cols:
        raise GateDequantizationError("weight shape not divisible by scale grid")
    block_rows, block_cols = rows // scale_rows, cols // scale_cols
    if (block_rows, block_cols) != BLOCK_SHAPE:
        raise GateDequantizationError("unexpected FP8 block geometry")
    if len(weight_raw) != rows * cols:
        raise GateDequantizationError("weight payload length mismatch")
    if len(scale_raw) != scale_rows * scale_cols * 4:
        raise GateDequantizationError("scale payload length mismatch")

    codes = np.frombuffer(weight_raw, dtype=np.uint8)
    if np.any((codes == 0x7F) | (codes == 0xFF)):
        raise GateDequantizationError("NaN E4M3FN code in live weight payload")
    scales = np.frombuffer(scale_raw, dtype="<f4").reshape(scale_shape)
    if not np.all(np.isfinite(scales)) or not np.all(scales > 0.0):
        raise GateDequantizationError("scale grid must be positive finite float32")

    table = e4m3fn_lookup_table()
    q = table[codes].reshape(weight_shape)
    q_blocks = q.reshape(scale_rows, block_rows, scale_cols, block_cols)
    dequant_blocks = q_blocks * scales[:, None, :, None]
    dequant = np.asarray(dequant_blocks.reshape(weight_shape), dtype="<f4", order="C")
    raw = dequant.tobytes(order="C")
    if len(raw) != rows * cols * 4:
        raise GateDequantizationError("canonical float32 byte length mismatch")
    return raw


def _read_live_gate_pair() -> tuple[int, bytes, bytes]:
    url = live.hf_resolve_url(live.OFFICIAL_REPOSITORY, live.OFFICIAL_REVISION, live.SELECTED_SHARD)
    prefix = live.urllib_read_range(url, 0, 8)
    if len(prefix) != 8:
        raise GateDequantizationError("header prefix length mismatch")
    header_len = struct.unpack("<Q", prefix)[0]
    if header_len <= 1 or header_len > live.MAX_HEADER_BYTES:
        raise GateDequantizationError("header length out of bounds")
    data_base = 8 + header_len
    weight_raw = live.urllib_read_range(url, data_base + live.WEIGHT_OFFSETS[0], EXPECTED_WEIGHT_BYTES)
    scale_raw = live.urllib_read_range(url, data_base + live.SCALE_OFFSETS[0], EXPECTED_SCALE_BYTES)
    return header_len, weight_raw, scale_raw


@dataclass(frozen=True)
class LiveGateCanonicalF32IdentityReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    pr650_job: int
    pr641_source_blob: str
    pr628_source_blob: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    selected_shard: str
    weight_key: str
    scale_key: str
    weight_shape: tuple[int, int]
    scale_shape: tuple[int, int]
    block_shape: tuple[int, int]
    live_header_length_bytes: int
    weight_payload_bytes: int
    weight_payload_sha256: str
    scale_payload_bytes: int
    scale_payload_sha256: str
    fp8_format: str
    canonical_float32_domain: str
    canonical_float32_bytes: int
    canonical_float32_sha256: str
    live_gate_pair_reobserved: bool
    exact_pr650_payload_generation_reproduced: bool
    fp8_dequantization_semantics_bound: bool
    official_gate_canonical_float32_source_identity_bound: bool
    pr628_source_hash_byte_domain_matched: bool
    up_payload_observed: bool
    down_payload_observed: bool
    full_expert_payload_observed: bool
    gate_up_composition_bound: bool
    official_tensor_to_pr641_page_set_relation_proven: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_official_source_tensor_set_proven: bool
    real_e8_page_materialized: bool
    model_execution_observed: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha256(_canonical(asdict(self)))


def current_live_gate_identity() -> LiveGateCanonicalF32IdentityReceipt:
    header_len, weight_raw, scale_raw = _read_live_gate_pair()
    weight_sha = _sha256(weight_raw)
    scale_sha = _sha256(scale_raw)
    if weight_sha != EXPECTED_WEIGHT_SHA256 or scale_sha != EXPECTED_SCALE_SHA256:
        raise GateDequantizationError("live payload generation drifted from exact-green PR650")

    canonical = dequantize_blockwise_to_canonical_f32(
        weight_raw,
        scale_raw,
        weight_shape=tuple(live.WEIGHT_SHAPE),
        scale_shape=tuple(live.SCALE_SHAPE),
    )
    if len(canonical) != EXPECTED_CANONICAL_F32_BYTES:
        raise GateDequantizationError("unexpected canonical gate tensor byte count")

    return LiveGateCanonicalF32IdentityReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR650_HEAD, PR641_HEAD),
        exact_parent_runs=(PR650_RUN, PR641_RUN),
        pr650_job=PR650_JOB,
        pr641_source_blob=PR641_SOURCE_BLOB,
        pr628_source_blob=PR628_SOURCE_BLOB,
        official_repository=live.OFFICIAL_REPOSITORY,
        official_revision=live.OFFICIAL_REVISION,
        selected_layer=live.SELECTED_LAYER,
        selected_expert=live.SELECTED_EXPERT,
        selected_shard=live.SELECTED_SHARD,
        weight_key=live.WEIGHT_KEY,
        scale_key=live.SCALE_KEY,
        weight_shape=tuple(live.WEIGHT_SHAPE),
        scale_shape=tuple(live.SCALE_SHAPE),
        block_shape=BLOCK_SHAPE,
        live_header_length_bytes=header_len,
        weight_payload_bytes=len(weight_raw),
        weight_payload_sha256=weight_sha,
        scale_payload_bytes=len(scale_raw),
        scale_payload_sha256=scale_sha,
        fp8_format=E4M3FN_SPEC,
        canonical_float32_domain=CANONICAL_FLOAT32_DOMAIN,
        canonical_float32_bytes=len(canonical),
        canonical_float32_sha256=_sha256(canonical),
        live_gate_pair_reobserved=True,
        exact_pr650_payload_generation_reproduced=True,
        fp8_dequantization_semantics_bound=True,
        official_gate_canonical_float32_source_identity_bound=True,
        pr628_source_hash_byte_domain_matched=True,
        up_payload_observed=False,
        down_payload_observed=False,
        full_expert_payload_observed=False,
        gate_up_composition_bound=False,
        official_tensor_to_pr641_page_set_relation_proven=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_official_source_tensor_set_proven=False,
        real_e8_page_materialized=False,
        model_execution_observed=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def main() -> None:
    receipt = current_live_gate_identity()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.receipt_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
