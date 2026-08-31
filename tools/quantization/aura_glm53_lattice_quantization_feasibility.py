#!/usr/bin/env python3
"""Bounded feasibility/falsification membrane for a supplied GLM-5.3 lattice-quantization proposal.

This module deliberately separates four questions:
1. Does the D_n / E8 nearest-lattice geometry work?
2. Does a proposed storage representation actually achieve its advertised bits/weight?
3. Does phase-only KV normalization preserve attention logits?
4. What static storage follows from a current GLM-5.3-scale parameter count?

It is a software arithmetic/reference witness only. It does not quantize the real model,
measure model quality, access native/private KV state, perform physical I/O, or authorize deployment.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Iterable, Sequence

VERSION = "AURA_GLM53_LATTICE_QUANTIZATION_FEASIBILITY_V1"
SUPPLIED_SOURCE_SHA256 = "f03d16c029a809f04c8ae069c51f9d07f0f10aeb0745bc8e3ee276ead22df582"
GLM53_HF_PARAMETER_COUNT = 753_329_900_000

# Published normalized second moments used only as geometry reference constants.
SCALAR_Z_NSM = 1.0 / 12.0
D4_NSM = 0.0766032
E8_NSM = 0.0716821
LEECH24_NSM = 0.06577


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def decode_dn(vector: Sequence[float]) -> tuple[float, ...]:
    """Nearest point in D_n = {z in Z^n : sum(z) even}."""
    if not vector:
        raise ValueError("VECTOR_REQUIRED")
    if any(not math.isfinite(float(v)) for v in vector):
        raise ValueError("FINITE_VECTOR_REQUIRED")
    rounded = [float(round(float(v))) for v in vector]
    if int(sum(rounded)) % 2 == 0:
        return tuple(rounded)
    errors = [abs(float(v) - r) for v, r in zip(vector, rounded)]
    k = max(range(len(errors)), key=errors.__getitem__)
    # Change the coordinate to its second-nearest integer; ties are deterministic.
    rounded[k] += 1.0 if float(vector[k]) >= rounded[k] else -1.0
    return tuple(rounded)


def squared_distance(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("DIMENSION_MISMATCH")
    return sum((float(x) - float(y)) ** 2 for x, y in zip(a, b))


def decode_e8(vector: Sequence[float]) -> tuple[float, ...]:
    """Nearest point in E8 = D8 union (D8 + 1/2 * 1)."""
    if len(vector) != 8:
        raise ValueError("E8_REQUIRES_8D")
    x = tuple(float(v) for v in vector)
    y0 = decode_dn(x)
    shifted = tuple(v - 0.5 for v in x)
    y1 = tuple(v + 0.5 for v in decode_dn(shifted))
    return y0 if squared_distance(x, y0) <= squared_distance(x, y1) else y1


def doubled_lattice_coordinates(point: Sequence[float]) -> tuple[int, ...]:
    """Losslessly represent integer/half-integer E8 coordinates as 2*y integers."""
    doubled = []
    for value in point:
        twice = 2.0 * float(value)
        rounded = round(twice)
        if not math.isclose(twice, rounded, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("NOT_HALF_INTEGER_LATTICE_POINT")
        doubled.append(int(rounded))
    return tuple(doubled)


def pasted_int8_cast(point: Sequence[float]) -> tuple[int, ...]:
    """Model float->int truncation used by the pasted `tensor.to(torch.int8)` storage idea."""
    out = []
    for value in point:
        integer = int(float(value))  # truncates toward zero
        if not -128 <= integer <= 127:
            raise ValueError("INT8_OVERFLOW")
        out.append(integer)
    return tuple(out)


def pasted_weight_representation_bpw(block_size: int = 64, scale_bits: int = 16) -> float:
    """Actual advertised-data representation: one int8 coordinate/weight + one scale/block."""
    if type(block_size) is not int or block_size <= 0:
        raise ValueError("INVALID_BLOCK_SIZE")
    if type(scale_bits) is not int or scale_bits <= 0:
        raise ValueError("INVALID_SCALE_BITS")
    return 8.0 + scale_bits / block_size


def indexed_vq_bpw(index_bits_per_vector: float, vector_dim: int, block_size: int = 64, scale_bits: int = 16) -> float:
    """Bitrate for a real finite indexed VQ, including one shared scale per block."""
    if index_bits_per_vector <= 0 or vector_dim <= 0 or block_size <= 0 or scale_bits < 0:
        raise ValueError("INVALID_INDEX_ACCOUNTING")
    if block_size % vector_dim:
        raise ValueError("BLOCK_VECTOR_DIM_MISMATCH")
    return float(index_bits_per_vector) / vector_dim + float(scale_bits) / block_size


def static_weight_bytes(parameter_count: int, bits_per_weight: float) -> int:
    if type(parameter_count) is not int or parameter_count <= 0:
        raise ValueError("INVALID_PARAMETER_COUNT")
    if not math.isfinite(bits_per_weight) or bits_per_weight <= 0:
        raise ValueError("INVALID_BITS_PER_WEIGHT")
    return math.ceil(parameter_count * bits_per_weight / 8.0)


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        raise ValueError("DOT_DIMENSION_MISMATCH")
    return sum(float(x) * float(y) for x, y in zip(a, b))


def unit_direction(vector: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(dot(vector, vector))
    if norm == 0:
        raise ValueError("ZERO_VECTOR")
    return tuple(float(v) / norm for v in vector)


def phase_only_attention_counterexample() -> dict[str, float | bool]:
    """Small witness that discarding magnitudes changes query-key logits.

    Collinear keys [1,0] and [4,0] have identical direction/phase but logits 1 and 4
    against q=[1,0]. Any phase-only representation that normalizes both to the same
    direction cannot preserve both original logits without carrying magnitude separately.
    """
    q = (1.0, 0.0)
    k_small = (1.0, 0.0)
    k_large = (4.0, 0.0)
    original_small = dot(q, k_small)
    original_large = dot(q, k_large)
    phase_small = dot(unit_direction(q), unit_direction(k_small))
    phase_large = dot(unit_direction(q), unit_direction(k_large))
    return {
        "original_small_logit": original_small,
        "original_large_logit": original_large,
        "phase_only_small_logit": phase_small,
        "phase_only_large_logit": phase_large,
        "original_logits_distinct": original_small != original_large,
        "phase_only_logits_collide": phase_small == phase_large,
    }


@dataclass(frozen=True)
class FeasibilityReceipt:
    version: str
    supplied_source_sha256: str
    glm53_parameter_count_reference: int
    pasted_representation_bpw: float
    glm53_raw_fp8_weight_bytes: int
    glm53_raw_2bit_weight_bytes: int
    glm53_raw_2_5bit_weight_bytes: int
    glm53_raw_3bit_weight_bytes: int
    e8_half_coset_exists: bool
    pasted_int8_preserves_half_coset: bool
    doubled_integer_representation_preserves_half_coset: bool
    pasted_e8_nsm_matches_reference: bool
    lattice_vq_mechanism_feasible: bool
    practical_sub4bit_requires_finite_index_or_equivalent_coding: bool
    practical_sub2bit_glm53_quality_proven: bool
    toroidal_phase_only_kv_preserves_attention_logits: bool
    magnitude_must_be_preserved_or_accounted_for: bool
    rope_aware_kv_quantization_is_viable_research_direction: bool
    expert_wise_mixed_precision_is_viable_moe_direction: bool
    coordinate_address_is_physical_sector_proof: bool
    out_of_core_expert_streaming_proven_on_owner_host: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    model_execution_performed: bool
    deployment_authorized: bool

    @property
    def digest(self) -> str:
        return _sha(asdict(self))


def build_feasibility_receipt() -> FeasibilityReceipt:
    # Half-coset witness chosen so E8 decoder returns (0.5,...,0.5).
    half = decode_e8((0.5,) * 8)
    cast = pasted_int8_cast(half)
    doubled = doubled_lattice_coordinates(half)
    kv = phase_only_attention_counterexample()
    return FeasibilityReceipt(
        version=VERSION,
        supplied_source_sha256=SUPPLIED_SOURCE_SHA256,
        glm53_parameter_count_reference=GLM53_HF_PARAMETER_COUNT,
        pasted_representation_bpw=pasted_weight_representation_bpw(),
        glm53_raw_fp8_weight_bytes=static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 8.0),
        glm53_raw_2bit_weight_bytes=static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 2.0),
        glm53_raw_2_5bit_weight_bytes=static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 2.5),
        glm53_raw_3bit_weight_bytes=static_weight_bytes(GLM53_HF_PARAMETER_COUNT, 3.0),
        e8_half_coset_exists=all(v == 0.5 for v in half),
        pasted_int8_preserves_half_coset=cast == half,
        doubled_integer_representation_preserves_half_coset=tuple(v / 2 for v in doubled) == half,
        pasted_e8_nsm_matches_reference=math.isclose(E8_NSM, 0.0658, rel_tol=0.0, abs_tol=1e-6),
        lattice_vq_mechanism_feasible=True,
        practical_sub4bit_requires_finite_index_or_equivalent_coding=True,
        practical_sub2bit_glm53_quality_proven=False,
        toroidal_phase_only_kv_preserves_attention_logits=not bool(kv["phase_only_logits_collide"]),
        magnitude_must_be_preserved_or_accounted_for=True,
        rope_aware_kv_quantization_is_viable_research_direction=True,
        expert_wise_mixed_precision_is_viable_moe_direction=True,
        coordinate_address_is_physical_sector_proof=False,
        out_of_core_expert_streaming_proven_on_owner_host=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        model_execution_performed=False,
        deployment_authorized=False,
    )


def main() -> None:
    receipt = build_feasibility_receipt()
    print(json.dumps({**asdict(receipt), "receipt_digest": receipt.digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
