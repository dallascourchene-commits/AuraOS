#!/usr/bin/env python3
"""Q6: compare Q14 official-source E8 page canaries to an optimized scalar control.

Exactly two derivation artifacts:
- Q14 exact-green official-source E8 page materialization canary.
- AGELF no-privilege research map: geometry must beat a serious matched baseline.

The scalar lane is a real packed 2-bit representation: 64 labels are packed into
16 bytes and one IEEE-754 binary16 scale adds 2 bytes, for exactly 18 bytes / 64
weights = 2.25 bits/weight, matching PR628/Q14 codec accounting.  The scale is
chosen deterministically by evaluating every sign-symmetric four-level assignment
partition plus assignment-boundary candidates after actual binary16 rounding.

E8 win, scalar win, and tie are all valid evidence.  This module measures only two
64-weight official-source canaries and grants no model-quality/runtime authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import struct
from typing import Iterable, Sequence

import numpy as np

from tools.quantization import aura_glm53_official_source_e8_materialization_canary as q14

SCHEMA = "AURA_GLM53_OFFICIAL_E8_VS_OPTIMIZED_SCALAR_CANARY_V1"
Q14_HEAD = "ee70934e0c45572588829e742e512a897b23863f"
Q14_RUN = 33399560819
Q14_SOURCE_BLOB = "ef26cf18731b2f6dfc3c63d08260fb64aded96f6"
AGELF_DRIVE_ID = "1qgf9Q0vt2ns5KlyS7Cb21zWsvzI1rre4-f4MgK_OLNQ"
SCALAR_SCHEME = "AURA_OPT_SYMMETRIC_4LEVEL_FP16_V1"
SCALAR_LEVELS = (-3.0, -1.0, 1.0, 3.0)
SCALAR_BITS_PER_WEIGHT = 2.25
SCALAR_PAYLOAD_BYTES = 18
TILE_WEIGHTS = 64


class ScalarCanaryError(ValueError):
    pass


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def scalar_representation_digest() -> str:
    return _sha(_canonical({
        "scheme": SCALAR_SCHEME,
        "levels": SCALAR_LEVELS,
        "labels_bits_per_weight": 2,
        "scale_dtype": "IEEE754_BINARY16_LE",
        "scale_bits_per_64_weights": 16,
        "codec_bits_per_weight": SCALAR_BITS_PER_WEIGHT,
    }))


def _pack_labels(labels: Sequence[int]) -> bytes:
    if len(labels) != TILE_WEIGHTS or any((int(x) < 0 or int(x) > 3) for x in labels):
        raise ScalarCanaryError("EXACT_64_TWO_BIT_LABELS_REQUIRED")
    out = bytearray(16)
    for byte_index in range(16):
        base = byte_index * 4
        value = 0
        for shift in range(4):
            value |= int(labels[base + shift]) << (2 * shift)
        out[byte_index] = value
    return bytes(out)


def _unpack_labels(raw: bytes) -> tuple[int, ...]:
    if len(raw) != 16:
        raise ScalarCanaryError("EXACT_16_LABEL_BYTES_REQUIRED")
    labels: list[int] = []
    for byte in raw:
        labels.extend(((byte >> (2 * shift)) & 0x3) for shift in range(4))
    return tuple(labels)


def _f16_candidates(base_scale: float) -> Iterable[float]:
    if not math.isfinite(base_scale) or base_scale < 0.0:
        return ()
    h = np.float16(base_scale)
    values = {float(h)}
    if math.isfinite(float(h)):
        values.add(float(np.nextafter(h, np.float16(0.0))))
        values.add(float(np.nextafter(h, np.float16(np.inf))))
    return tuple(sorted(x for x in values if math.isfinite(x) and x >= 0.0))


def _candidate_scales(values: np.ndarray) -> tuple[float, ...]:
    magnitudes = np.sort(np.abs(values.astype(np.float64)))
    if float(magnitudes[-1]) == 0.0:
        return (0.0,)
    prefix = np.concatenate(([0.0], np.cumsum(magnitudes)))
    total = float(prefix[-1])
    bases: set[float] = set()
    n = len(magnitudes)
    for small_count in range(n + 1):
        small_sum = float(prefix[small_count])
        large_sum = total - small_sum
        denominator = float(small_count + 9 * (n - small_count))
        if denominator > 0.0:
            bases.add((small_sum + 3.0 * large_sum) / denominator)
    for magnitude in magnitudes:
        if magnitude > 0.0:
            bases.add(float(magnitude) / 2.0)
    scales: set[float] = set()
    for base in bases:
        scales.update(_f16_candidates(base))
    scales.discard(float("inf"))
    return tuple(sorted(scales))


def _quantize_for_scale(values: np.ndarray, scale: float) -> tuple[tuple[int, ...], np.ndarray, float]:
    levels = np.asarray(SCALAR_LEVELS, dtype=np.float64) * float(scale)
    distances = np.abs(values.astype(np.float64)[:, None] - levels[None, :])
    labels = np.argmin(distances, axis=1).astype(np.uint8)
    reconstructed = levels[labels].astype(np.float64)
    mse = float(np.mean((values.astype(np.float64) - reconstructed) ** 2))
    return tuple(int(x) for x in labels), reconstructed, mse


def encode_optimized_scalar(values: Sequence[float]) -> bytes:
    array = np.asarray(tuple(values), dtype=np.float64)
    if array.shape != (TILE_WEIGHTS,) or not np.all(np.isfinite(array)):
        raise ScalarCanaryError("EXACT_FINITE_64_WEIGHT_TILE_REQUIRED")
    best: tuple[float, bytes, bytes] | None = None
    for scale in _candidate_scales(array):
        try:
            scale_bytes = struct.pack("<e", float(scale))
        except (OverflowError, struct.error):
            continue
        serialized_scale = float(struct.unpack("<e", scale_bytes)[0])
        labels, _reconstructed, mse = _quantize_for_scale(array, serialized_scale)
        label_bytes = _pack_labels(labels)
        key = (mse, scale_bytes, label_bytes)
        if best is None or key < best:
            best = key
    if best is None:
        raise ScalarCanaryError("NO_FINITE_SCALAR_SOLUTION")
    _mse, scale_bytes, label_bytes = best
    payload = scale_bytes + label_bytes
    if len(payload) != SCALAR_PAYLOAD_BYTES:
        raise ScalarCanaryError("SCALAR_PAYLOAD_RATE_DRIFT")
    return payload


def decode_optimized_scalar(payload: bytes) -> tuple[float, ...]:
    if len(payload) != SCALAR_PAYLOAD_BYTES:
        raise ScalarCanaryError("EXACT_18_BYTE_SCALAR_PAYLOAD_REQUIRED")
    scale = float(struct.unpack("<e", payload[:2])[0])
    if not math.isfinite(scale) or scale < 0.0:
        raise ScalarCanaryError("INVALID_SERIALIZED_SCALAR_SCALE")
    labels = _unpack_labels(payload[2:])
    levels = SCALAR_LEVELS
    return tuple(float(levels[label] * scale) for label in labels)


def _mse(source: Sequence[float], reconstructed: Sequence[float]) -> float:
    a = np.asarray(tuple(source), dtype=np.float64)
    b = np.asarray(tuple(reconstructed), dtype=np.float64)
    if a.shape != (TILE_WEIGHTS,) or b.shape != (TILE_WEIGHTS,):
        raise ScalarCanaryError("MSE_TILE_SHAPE_DRIFT")
    return float(np.mean((a - b) ** 2))


def _classify(e8_mse: float, scalar_mse: float) -> str:
    if math.isclose(e8_mse, scalar_mse, rel_tol=0.0, abs_tol=1e-15):
        return "TIE"
    return "E8_WIN" if e8_mse < scalar_mse else "SCALAR_WIN"


@dataclass(frozen=True)
class RoleComparison:
    tensor_role: str
    q14_page_identity_digest: str
    q14_page_payload_sha256: str
    q14_canonical_tile_sha256: str
    scalar_scheme: str
    scalar_representation_digest: str
    scalar_payload_sha256: str
    q14_e8_codec_bits_per_weight: float
    scalar_codec_bits_per_weight: float
    equal_codec_rate: bool
    e8_mse: float
    scalar_mse: float
    e8_over_scalar: float
    outcome: str


@dataclass(frozen=True)
class OfficialE8VsScalarReceipt:
    schema: str
    q14_head: str
    q14_run: int
    q14_source_blob: str
    agelf_drive_id: str
    official_repository: str
    official_revision: str
    selected_layer: int
    selected_expert: int
    q14_canary_page_set_digest: str
    q14_representation_scheme: str
    scalar_scheme: str
    scalar_representation_digest: str
    exact_codec_rate_bpw: float
    roles: tuple[RoleComparison, ...]
    aggregate_e8_mse: float
    aggregate_scalar_mse: float
    aggregate_e8_over_scalar: float
    aggregate_outcome: str
    same_official_source_tiles_compared: bool
    optimized_scalar_control_used: bool
    official_source_equal_rate_distortion_evidence: bool
    representative_canary_scope_only: bool
    geometry_privileged: bool
    full_role_quantized: bool
    whole_model_quantized: bool
    glm_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(_canonical(asdict(self)))


def current_official_e8_vs_scalar_canary() -> OfficialE8VsScalarReceipt:
    q14_receipt = q14.current_official_source_materialization_canary()
    if not q14_receipt.two_official_source_bound_tile_pages_materialized:
        raise ScalarCanaryError("Q14_MATERIALIZATION_NOT_PROVEN")
    if q14_receipt.full_role_page_payloads_materialized or q14_receipt.model_execution_observed:
        raise ScalarCanaryError("Q14_CLAIM_BOUNDARY_DRIFT")
    by_role = {x.tensor_role: x for x in q14_receipt.role_canaries}
    if set(by_role) != set(q14.ROLE_SOURCE):
        raise ScalarCanaryError("Q14_ROLE_SET_DRIFT")

    results: list[RoleComparison] = []
    e8_errors: list[float] = []
    scalar_errors: list[float] = []
    for role in sorted(q14.ROLE_SOURCE):
        _header_len, weight_raw, scale_raw, component = q14._fetch_live_role_tile(role)
        tile = q14.canonical_first_block(weight_raw, scale_raw)
        tile_values = tuple(float(x) for x in np.asarray(tile, dtype=np.float64).reshape(-1))
        reproduced_q14 = q14.materialize_role_canary(
            q13_receipt=q14.q13.current_full_representative_source_set(),
            role=role,
            weight_raw=weight_raw,
            scale_raw=scale_raw,
            source_component=component,
        )
        expected = by_role[role]
        if reproduced_q14.page_identity_digest != expected.page_identity_digest or reproduced_q14.page_payload_sha256 != expected.page_payload_sha256:
            raise ScalarCanaryError("Q14_PAGE_REPRODUCTION_DRIFT")
        page = q14.page_ref.pack_expert_page(
            np.asarray(tile, dtype="<f4"),
            model_revision=q14.q13.OFFICIAL_REVISION,
            representation_revision=q14.REPRESENTATION_REVISION,
            layer_id=q14.q13.SELECTED_LAYER,
            expert_id=q14.q13.SELECTED_EXPERT,
            tensor_role=role,
            block_size=q14.page_ref.DEFAULT_BLOCK_SIZE,
        )
        if page.identity.digest() != expected.page_identity_digest or page.payload_sha256 != expected.page_payload_sha256:
            raise ScalarCanaryError("Q14_PAGE_OWNER_DRIFT")
        e8_reconstructed = tuple(float(x) for x in np.asarray(q14.page_ref.unpack_expert_page(page), dtype=np.float64).reshape(-1))
        scalar_payload = encode_optimized_scalar(tile_values)
        scalar_reconstructed = decode_optimized_scalar(scalar_payload)
        if len(page.payload) != SCALAR_PAYLOAD_BYTES or page.codec_bits_per_weight != SCALAR_BITS_PER_WEIGHT:
            raise ScalarCanaryError("Q14_SCALAR_CODEC_RATE_MISMATCH")
        e8_mse = _mse(tile_values, e8_reconstructed)
        scalar_mse = _mse(tile_values, scalar_reconstructed)
        e8_errors.append(e8_mse)
        scalar_errors.append(scalar_mse)
        results.append(RoleComparison(
            tensor_role=role,
            q14_page_identity_digest=expected.page_identity_digest,
            q14_page_payload_sha256=expected.page_payload_sha256,
            q14_canonical_tile_sha256=expected.canonical_tile_sha256,
            scalar_scheme=SCALAR_SCHEME,
            scalar_representation_digest=scalar_representation_digest(),
            scalar_payload_sha256=_sha(scalar_payload),
            q14_e8_codec_bits_per_weight=page.codec_bits_per_weight,
            scalar_codec_bits_per_weight=SCALAR_BITS_PER_WEIGHT,
            equal_codec_rate=True,
            e8_mse=e8_mse,
            scalar_mse=scalar_mse,
            e8_over_scalar=e8_mse / scalar_mse if scalar_mse else math.inf,
            outcome=_classify(e8_mse, scalar_mse),
        ))
    aggregate_e8 = sum(e8_errors) / len(e8_errors)
    aggregate_scalar = sum(scalar_errors) / len(scalar_errors)
    return OfficialE8VsScalarReceipt(
        schema=SCHEMA,
        q14_head=Q14_HEAD,
        q14_run=Q14_RUN,
        q14_source_blob=Q14_SOURCE_BLOB,
        agelf_drive_id=AGELF_DRIVE_ID,
        official_repository=q14.q13.OFFICIAL_REPOSITORY,
        official_revision=q14.q13.OFFICIAL_REVISION,
        selected_layer=q14.q13.SELECTED_LAYER,
        selected_expert=q14.q13.SELECTED_EXPERT,
        q14_canary_page_set_digest=q14_receipt.canary_page_set_digest,
        q14_representation_scheme=q14.page_ref.SCHEME,
        scalar_scheme=SCALAR_SCHEME,
        scalar_representation_digest=scalar_representation_digest(),
        exact_codec_rate_bpw=SCALAR_BITS_PER_WEIGHT,
        roles=tuple(results),
        aggregate_e8_mse=aggregate_e8,
        aggregate_scalar_mse=aggregate_scalar,
        aggregate_e8_over_scalar=aggregate_e8 / aggregate_scalar if aggregate_scalar else math.inf,
        aggregate_outcome=_classify(aggregate_e8, aggregate_scalar),
        same_official_source_tiles_compared=True,
        optimized_scalar_control_used=True,
        official_source_equal_rate_distortion_evidence=True,
        representative_canary_scope_only=True,
        geometry_privileged=False,
        full_role_quantized=False,
        whole_model_quantized=False,
        glm_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
    )


def main() -> None:
    receipt = current_official_e8_vs_scalar_canary()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    print(json.dumps(body, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
