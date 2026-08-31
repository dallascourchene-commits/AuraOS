"""D0 magnitude-aware polar/RoPE key-cache quantization reference.

This salvages the useful angular structure from a phase/toroidal proposal without
discarding magnitude. It is a synthetic falsifier/reference, not a GLM-5.3 KV
format and not a production cache implementation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any

import numpy as np

SCHEMA = "AURA_ROPE_POLAR_KEY_CACHE_REFERENCE_V1"
FORMAT = "RADIAL_X_CIRCULAR_ROPE_BLOCK_V1"
K27_SCHEME = "K27-SHA256-MOD27-v1"


def _json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wrap_angle(theta: np.ndarray) -> np.ndarray:
    theta = np.asarray(theta, dtype=np.float64)
    return (theta + np.pi) % (2.0 * np.pi) - np.pi


def to_polar_blocks(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(x, dtype=np.float64)
    if x.ndim < 1 or x.shape[-1] <= 0 or x.shape[-1] % 2:
        raise ValueError("last dimension must be positive and even")
    b = x.reshape(*x.shape[:-1], x.shape[-1] // 2, 2)
    radius = np.linalg.norm(b, axis=-1)
    angle = np.arctan2(b[..., 1], b[..., 0])
    return radius, angle


def from_polar_blocks(radius: np.ndarray, angle: np.ndarray) -> np.ndarray:
    r = np.asarray(radius, dtype=np.float64)
    a = np.asarray(angle, dtype=np.float64)
    if r.shape != a.shape:
        raise ValueError("radius and angle shapes must match")
    b = np.stack((r * np.cos(a), r * np.sin(a)), axis=-1)
    return b.reshape(*b.shape[:-2], b.shape[-2] * 2)


def rope_rotate_blocks(x: np.ndarray, rope_angles: np.ndarray) -> np.ndarray:
    """Apply one RoPE angle per 2-D block by theta addition."""
    r, theta = to_polar_blocks(x)
    a = np.asarray(rope_angles, dtype=np.float64)
    if a.shape != (x.shape[-1] // 2,):
        raise ValueError("rope_angles must have head_dim/2 values")
    return from_polar_blocks(r, wrap_angle(theta + a))


def rope_rotate_cartesian(x: np.ndarray, rope_angles: np.ndarray) -> np.ndarray:
    """Independent Cartesian rotation oracle."""
    x = np.asarray(x, dtype=np.float64)
    a = np.asarray(rope_angles, dtype=np.float64)
    if x.shape[-1] % 2 or a.shape != (x.shape[-1] // 2,):
        raise ValueError("shape mismatch")
    b = x.reshape(*x.shape[:-1], x.shape[-1] // 2, 2)
    c, s = np.cos(a), np.sin(a)
    x0, x1 = b[..., 0], b[..., 1]
    y = np.stack((x0 * c - x1 * s, x0 * s + x1 * c), axis=-1)
    return y.reshape(x.shape)


def _quantize_unit_interval(v: np.ndarray, bits: int) -> np.ndarray:
    if type(bits) is not int or bits <= 0 or bits > 16:
        raise ValueError("bits must be an integer in [1,16]")
    levels = (1 << bits) - 1
    return np.rint(np.clip(v, 0.0, 1.0) * levels) / levels


def _quantize_angle(theta: np.ndarray, bits: int) -> np.ndarray:
    levels = 1 << bits
    if type(bits) is not int or bits <= 0 or bits > 16:
        raise ValueError("bits must be an integer in [1,16]")
    u = (wrap_angle(theta) + np.pi) / (2.0 * np.pi)
    q = np.floor(u * levels + 0.5) % levels
    return wrap_angle(-np.pi + (q / levels) * 2.0 * np.pi)


@dataclass(frozen=True)
class QuantizedKeys:
    reconstructed: np.ndarray
    scale: np.ndarray
    bits_per_dimension: float
    radial_bits: int
    angle_bits: int


def phase_only_quantize(keys: np.ndarray, angle_bits: int = 4) -> QuantizedKeys:
    """Information-losing phase-only comparator: radius forced to one."""
    r, theta = to_polar_blocks(keys)
    tq = _quantize_angle(theta, angle_bits)
    out = from_polar_blocks(np.ones_like(r), tq).astype(np.float32)
    return QuantizedKeys(out, np.ones((*keys.shape[:-1], 1), dtype=np.float16),
                         angle_bits / 2.0, 0, angle_bits)


def polar_quantize_keys(keys: np.ndarray, radial_bits: int = 4, angle_bits: int = 4) -> QuantizedKeys:
    """Magnitude-aware per-key polar quantization with one FP16 max-radius scale/key."""
    k = np.asarray(keys, dtype=np.float32)
    r, theta = to_polar_blocks(k)
    scale = np.max(r, axis=-1, keepdims=True)
    scale = np.maximum(scale, 1e-12)
    rq = _quantize_unit_interval(r / scale, radial_bits) * scale
    tq = _quantize_angle(theta, angle_bits)
    out = from_polar_blocks(rq, tq).astype(np.float32)
    d = k.shape[-1]
    bpw = ((radial_bits + angle_bits) * (d // 2) + 16) / d
    return QuantizedKeys(out, scale.astype(np.float16), float(bpw), radial_bits, angle_bits)


def cartesian_quantize_keys(keys: np.ndarray, bits: int = 4) -> QuantizedKeys:
    """Matched-scale Cartesian scalar comparator with one FP16 scale/key."""
    k = np.asarray(keys, dtype=np.float32)
    if k.ndim < 2:
        raise ValueError("keys must include key-vector dimension")
    scale = np.max(np.abs(k), axis=-1, keepdims=True)
    scale = np.maximum(scale, 1e-12)
    levels = (1 << bits) - 1
    u = np.clip((k / scale + 1.0) * 0.5, 0.0, 1.0)
    q = np.rint(u * levels) / levels
    out = ((q * 2.0 - 1.0) * scale).astype(np.float32)
    d = k.shape[-1]
    return QuantizedKeys(out, scale.astype(np.float16), float(bits + 16 / d), bits, bits)


def attention_logits(query: np.ndarray, keys: np.ndarray) -> np.ndarray:
    q = np.asarray(query, dtype=np.float64)
    k = np.asarray(keys, dtype=np.float64)
    if q.ndim != 1 or k.ndim != 2 or k.shape[1] != q.shape[0]:
        raise ValueError("query must be [D] and keys [N,D]")
    return (k @ q) / math.sqrt(q.shape[0])


def k27_from_digest(digest: str) -> tuple[int, int, int]:
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("SHA-256 digest required")
    raw = bytes.fromhex(digest)
    return raw[0] % 27, raw[1] % 27, raw[2] % 27


@dataclass(frozen=True)
class KVFormatIdentity:
    model_revision: str
    representation_revision: str
    cache_generation: str
    layer_id: int
    kv_head_id: int
    head_dim: int
    rope_config_sha256: str
    key_format: str = FORMAT
    value_format: str = "UNMODIFIED_REFERENCE_ONLY"

    def validate(self) -> None:
        if not self.model_revision or not self.representation_revision or not self.cache_generation:
            raise ValueError("revision/generation identity required")
        if type(self.layer_id) is not int or self.layer_id < 0:
            raise ValueError("invalid layer")
        if type(self.kv_head_id) is not int or self.kv_head_id < 0:
            raise ValueError("invalid KV head")
        if type(self.head_dim) is not int or self.head_dim <= 0 or self.head_dim % 2:
            raise ValueError("head_dim must be positive and even")
        if len(self.rope_config_sha256) != 64:
            raise ValueError("RoPE config SHA-256 required")
        bytes.fromhex(self.rope_config_sha256)
        if self.key_format != FORMAT or self.value_format != "UNMODIFIED_REFERENCE_ONLY":
            raise ValueError("format mismatch")

    def digest(self) -> str:
        self.validate()
        return _sha(_json(asdict(self)).encode())


def benchmark_receipt(seed: int = 42, tokens: int = 512, head_dim: int = 64) -> dict[str, Any]:
    if tokens <= 0 or head_dim <= 0 or head_dim % 2:
        raise ValueError("invalid fixture dimensions")
    rng = np.random.default_rng(seed)
    radius = np.exp(rng.normal(-0.2, 0.7, size=(tokens, head_dim // 2)))
    theta = rng.uniform(-np.pi, np.pi, size=(tokens, head_dim // 2))
    base_keys = from_polar_blocks(radius, theta).astype(np.float32)
    rope_angles = rng.uniform(-np.pi, np.pi, size=(head_dim // 2,))
    keys = rope_rotate_blocks(base_keys, rope_angles).astype(np.float32)
    query = rng.normal(size=(head_dim,)).astype(np.float32)

    phase = phase_only_quantize(keys, 4)
    polar = polar_quantize_keys(keys, 4, 4)
    cart = cartesian_quantize_keys(keys, 4)
    exact_logits = attention_logits(query, keys)
    metrics: dict[str, float] = {}
    for name, candidate in (("phase_only", phase), ("polar_4plus4", polar), ("cartesian_int4", cart)):
        metrics[f"{name}_mse"] = float(np.mean((keys - candidate.reconstructed) ** 2, dtype=np.float64))
        metrics[f"{name}_attention_mae"] = float(
            np.mean(np.abs(attention_logits(query, candidate.reconstructed) - exact_logits), dtype=np.float64)
        )

    r = {
        "schema": SCHEMA,
        "seed": seed,
        "tokens": tokens,
        "head_dim": head_dim,
        "fixture": "SYNTHETIC_HEAVY_TAILED_RADIAL_ROPE_BLOCKS_V1",
        "phase_only_bits_per_dimension": phase.bits_per_dimension,
        "polar_bits_per_dimension_including_fp16_key_scale": polar.bits_per_dimension,
        "cartesian_bits_per_dimension_including_fp16_key_scale": cart.bits_per_dimension,
        **metrics,
        "polar_beats_phase_only_on_fixture": metrics["polar_4plus4_attention_mae"] < metrics["phase_only_attention_mae"],
        "polar_beats_matched_cartesian_on_fixture": metrics["polar_4plus4_attention_mae"] < metrics["cartesian_int4_attention_mae"],
        "claim_ceiling": {
            "fixture_is_glm53_distribution": False,
            "glm53_attention_quality_preserved": False,
            "polar_quantization_generally_superior": False,
            "value_cache_quantized_by_this_reference": False,
            "production_kv_format_ready": False,
            "native_transformer_kv_accessed": False,
            "gate10_promoted": False,
        },
    }
    r["receipt_sha256"] = _sha(_json(r).encode())
    return r


def verify_benchmark_receipt(receipt: dict[str, Any]) -> bool:
    if receipt.get("schema") != SCHEMA or not isinstance(receipt.get("receipt_sha256"), str):
        return False
    x = dict(receipt)
    got = x.pop("receipt_sha256")
    return got == _sha(_json(x).encode())


def format_receipt(identity: KVFormatIdentity, benchmark: dict[str, Any]) -> dict[str, Any]:
    identity.validate()
    if not verify_benchmark_receipt(benchmark):
        raise ValueError("benchmark receipt invalid")
    out = {
        "schema": "AURA_ROPE_POLAR_KEY_CACHE_FORMAT_RECEIPT_V1",
        "format_identity_digest": identity.digest(),
        "format_identity": asdict(identity),
        "benchmark_receipt_sha256": benchmark["receipt_sha256"],
        "k27_scheme": K27_SCHEME,
        "k27_coordinate": list(k27_from_digest(identity.digest())),
        "laws": [
            "ROPE_BLOCK_GEOMETRY=RADIAL_MAGNITUDE_X_CIRCULAR_PHASE",
            "PHASE_ONLY_KEY!=ATTENTION_EQUIVALENT_KEY_UNLESS_RADIUS_FIXED",
            "K27_COORDINATE!=TRANSFORMER_KV_IDENTITY",
        ],
        "claim_ceiling": {
            "k27_coordinate_is_kv_identity": False,
            "runtime_cache_reuse_authorized": False,
            "glm53_compatibility_proven": False,
            "value_format_defined": False,
            "physical_cache_performance_proven": False,
            "gate10_promoted": False,
        },
    }
    out["receipt_sha256"] = _sha(_json(out).encode())
    return out


if __name__ == "__main__":
    print(json.dumps(benchmark_receipt(), sort_keys=True))
