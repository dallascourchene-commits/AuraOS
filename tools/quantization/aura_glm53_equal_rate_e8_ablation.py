#!/usr/bin/env python3
"""D0 equal-rate structured-codebook ablation for GLM-5.3 quantization research.

This module does not quantize GLM-5.3.  It builds two *real, finite, packed*
1.25-bits/weight reference representations over synthetic 64-weight blocks:

* E8_ROOT_240_U8_V1: one byte selects one of the 240 E8 roots per 8 weights.
* HYPERCUBE_SIGN_256_U8_V1: one byte selects one of 256 {-1,+1}^8 vectors.

Both schemes share one IEEE-754 binary16 scale per 64 weights.  Therefore the
codec payload is exactly 8 index bytes + 2 scale bytes = 10 bytes per 64
weights = 1.25 bpw.  Container/header bytes, if any, are a separate accounting
plane and are never hidden inside that codec-rate claim.

The purpose is to test whether E8 geometry earns any distortion advantage at
an exactly matched representation rate.  Synthetic distortion is not model
quality, runtime, or deployment evidence.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import statistics
import struct
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

VECTOR_DIM = 8
GROUP_WEIGHTS = 64
INDICES_PER_GROUP = GROUP_WEIGHTS // VECTOR_DIM
INDEX_BITS = 8
SCALE_BITS = 16
CODEC_BITS_PER_GROUP = INDICES_PER_GROUP * INDEX_BITS + SCALE_BITS
CODEC_BPW = CODEC_BITS_PER_GROUP / GROUP_WEIGHTS
E8_SCHEME = "E8_ROOT_240_U8_V1"
HYPERCUBE_SCHEME = "HYPERCUBE_SIGN_256_U8_V1"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def e8_root_codebook() -> tuple[tuple[float, ...], ...]:
    """Return the 240 roots of E8 in deterministic index order.

    112 roots are permutations of (±1, ±1, 0^6).
    128 roots are (±1/2)^8 with an even number of minus signs.
    Every root has squared norm 2.
    """
    roots: list[tuple[float, ...]] = []
    for i in range(VECTOR_DIM):
        for j in range(i + 1, VECTOR_DIM):
            for a in (-1.0, 1.0):
                for b in (-1.0, 1.0):
                    value = [0.0] * VECTOR_DIM
                    value[i] = a
                    value[j] = b
                    roots.append(tuple(value))
    for signs in itertools.product((-0.5, 0.5), repeat=VECTOR_DIM):
        if sum(1 for x in signs if x < 0.0) % 2 == 0:
            roots.append(tuple(signs))
    result = tuple(roots)
    if len(result) != 240 or len(set(result)) != 240:
        raise AssertionError("E8 root-system construction drift")
    if any(not math.isclose(sum(x * x for x in root), 2.0) for root in result):
        raise AssertionError("E8 root norm drift")
    return result


def hypercube_codebook() -> tuple[tuple[float, ...], ...]:
    result = tuple(itertools.product((-1.0, 1.0), repeat=VECTOR_DIM))
    if len(result) != 256 or len(set(result)) != 256:
        raise AssertionError("hypercube construction drift")
    return result


E8_ROOTS = e8_root_codebook()
HYPERCUBE = hypercube_codebook()


def codebook_digest(codebook: Sequence[Sequence[float]]) -> str:
    # Doubled integer coordinates represent both codebooks losslessly.
    doubled = [[int(round(2.0 * x)) for x in row] for row in codebook]
    payload = json.dumps(doubled, separators=(",", ":"), sort_keys=False).encode()
    return _sha256(payload)


E8_CODEBOOK_SHA256 = codebook_digest(E8_ROOTS)
HYPERCUBE_CODEBOOK_SHA256 = codebook_digest(HYPERCUBE)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _nearest_index(vector: Sequence[float], codebook: Sequence[Sequence[float]], scale: float) -> int:
    best_index = 0
    best_error = math.inf
    for index, codeword in enumerate(codebook):
        error = sum((x - scale * c) ** 2 for x, c in zip(vector, codeword))
        if error < best_error:
            best_error = error
            best_index = index
    return best_index


def _pack_half(value: float) -> bytes:
    return struct.pack("<e", value)


def _unpack_half(payload: bytes) -> float:
    return struct.unpack("<e", payload)[0]


def _validate_group(group: Sequence[float]) -> tuple[float, ...]:
    if len(group) != GROUP_WEIGHTS:
        raise ValueError(f"expected {GROUP_WEIGHTS} weights")
    values = tuple(float(x) for x in group)
    if not all(math.isfinite(x) for x in values):
        raise ValueError("weights must be finite")
    return values


def encode_group(group: Sequence[float], scheme: str, *, iterations: int = 8) -> bytes:
    """Encode one 64-weight group into the exact 10-byte codec payload."""
    values = _validate_group(group)
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    if scheme == E8_SCHEME:
        codebook = E8_ROOTS
    elif scheme == HYPERCUBE_SCHEME:
        codebook = HYPERCUBE
    else:
        raise ValueError("unknown scheme")

    vectors = [values[i : i + VECTOR_DIM] for i in range(0, GROUP_WEIGHTS, VECTOR_DIM)]
    code_norm2 = sum(x * x for x in codebook[0])
    energy = sum(x * x for x in values)
    scale = math.sqrt(energy / len(vectors) / code_norm2) if energy else 0.0
    indices = [0] * INDICES_PER_GROUP

    for _ in range(iterations):
        new_indices = [_nearest_index(vector, codebook, scale) for vector in vectors]
        selected = [codebook[index] for index in new_indices]
        denominator = sum(sum(x * x for x in codeword) for codeword in selected)
        numerator = sum(_dot(vector, codeword) for vector, codeword in zip(vectors, selected))
        new_scale = numerator / denominator if denominator else 0.0
        indices = new_indices
        if math.isclose(new_scale, scale, rel_tol=0.0, abs_tol=1e-12):
            scale = new_scale
            break
        scale = new_scale

    # The stored reconstruction really uses binary16, not the optimizer's Python float.
    scale_bytes = _pack_half(scale)
    index_bytes = bytes(indices)
    payload = scale_bytes + index_bytes
    if len(payload) != CODEC_BITS_PER_GROUP // 8:
        raise AssertionError("codec payload-size drift")
    return payload


def decode_group(payload: bytes, scheme: str) -> tuple[float, ...]:
    if len(payload) != CODEC_BITS_PER_GROUP // 8:
        raise ValueError("invalid group payload length")
    if scheme == E8_SCHEME:
        codebook = E8_ROOTS
        limit = 240
    elif scheme == HYPERCUBE_SCHEME:
        codebook = HYPERCUBE
        limit = 256
    else:
        raise ValueError("unknown scheme")
    scale = _unpack_half(payload[:2])
    indices = payload[2:]
    if any(index >= limit for index in indices):
        raise ValueError("index outside finite codebook")
    return tuple(scale * value for index in indices for value in codebook[index])


def mse(original: Sequence[float], reconstructed: Sequence[float]) -> float:
    if len(original) != len(reconstructed) or not original:
        raise ValueError("MSE requires equal non-empty sequences")
    return sum((float(a) - float(b)) ** 2 for a, b in zip(original, reconstructed)) / len(original)


def frozen_gaussian_blocks(count: int = 64) -> tuple[tuple[float, ...], ...]:
    rng = random.Random(1337)
    return tuple(tuple(rng.gauss(0.0, 1.0) for _ in range(GROUP_WEIGHTS)) for _ in range(count))


def frozen_heavy_tail_blocks(count: int = 64) -> tuple[tuple[float, ...], ...]:
    rng = random.Random(7331)
    blocks = []
    for _ in range(count):
        row = []
        for _ in range(GROUP_WEIGHTS):
            sigma = 4.0 if rng.random() < 0.10 else 1.0
            row.append(rng.gauss(0.0, sigma))
        blocks.append(tuple(row))
    return tuple(blocks)


@dataclass(frozen=True)
class AblationLane:
    fixture: str
    blocks: int
    e8_mse: float
    hypercube_mse: float
    e8_over_hypercube: float
    e8_better: bool


@dataclass(frozen=True)
class AblationReceipt:
    schema: str
    vector_dim: int
    group_weights: int
    index_bits_per_vector: int
    scale_bits_per_group: int
    codec_bpw_e8: float
    codec_bpw_hypercube: float
    equal_rate: bool
    e8_codewords: int
    hypercube_codewords: int
    e8_codebook_sha256: str
    hypercube_codebook_sha256: str
    lanes: tuple[AblationLane, ...]
    synthetic_distortion_evidence_only: bool
    real_glm_tensor_quantized: bool
    glm_quality_proven: bool
    runtime_performance_proven: bool
    geometry_privileged: bool
    gate10_promoted: bool

    def digest(self) -> str:
        return _sha256(json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode())


def run_ablation() -> AblationReceipt:
    lanes = []
    for name, blocks in (
        ("FROZEN_GAUSSIAN_V1", frozen_gaussian_blocks()),
        ("FROZEN_HEAVY_TAIL_V1", frozen_heavy_tail_blocks()),
    ):
        e8_errors = []
        hypercube_errors = []
        for block in blocks:
            e8_payload = encode_group(block, E8_SCHEME)
            hc_payload = encode_group(block, HYPERCUBE_SCHEME)
            if len(e8_payload) != len(hc_payload):
                raise AssertionError("matched-rate payload length drift")
            e8_errors.append(mse(block, decode_group(e8_payload, E8_SCHEME)))
            hypercube_errors.append(mse(block, decode_group(hc_payload, HYPERCUBE_SCHEME)))
        e8_mean = statistics.fmean(e8_errors)
        hc_mean = statistics.fmean(hypercube_errors)
        lanes.append(
            AblationLane(
                fixture=name,
                blocks=len(blocks),
                e8_mse=e8_mean,
                hypercube_mse=hc_mean,
                e8_over_hypercube=e8_mean / hc_mean,
                e8_better=e8_mean < hc_mean,
            )
        )
    return AblationReceipt(
        schema="AURA_GLM53_EQUAL_RATE_E8_ABLATION_V1",
        vector_dim=VECTOR_DIM,
        group_weights=GROUP_WEIGHTS,
        index_bits_per_vector=INDEX_BITS,
        scale_bits_per_group=SCALE_BITS,
        codec_bpw_e8=CODEC_BPW,
        codec_bpw_hypercube=CODEC_BPW,
        equal_rate=True,
        e8_codewords=len(E8_ROOTS),
        hypercube_codewords=len(HYPERCUBE),
        e8_codebook_sha256=E8_CODEBOOK_SHA256,
        hypercube_codebook_sha256=HYPERCUBE_CODEBOOK_SHA256,
        lanes=tuple(lanes),
        synthetic_distortion_evidence_only=True,
        real_glm_tensor_quantized=False,
        glm_quality_proven=False,
        runtime_performance_proven=False,
        geometry_privileged=False,
        gate10_promoted=False,
    )


def main() -> None:
    receipt = run_ablation()
    body = asdict(receipt)
    body["receipt_sha256"] = receipt.digest()
    print(json.dumps(body, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
