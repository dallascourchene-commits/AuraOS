"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fb-[Q-SYS:SINGLE_SEED_LIFT]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GWAYAKWAADIZIWIN (Integrity / Cached Context Lift)
DEPENDENCIES: dataclasses, hashlib, math, re, typing, numpy
FUNCTIONS: SingleSeedTrace, SingleSeedLiftProfile, SingleSeedLiftResult, compile_single_seed_lift, compile_text_single_seed_lift, compact_lift_capsule, encode_text_as_unit_phasor
SYNOPSIS: Cofactor-free single-seed context-lift primitives for Aura's VSA memory and egress paths. Inspired by arXiv:2606.20633, the module derives one deterministic seed vector, caches its inverse once, lifts the seed through bounded local residual layers, and dispatches compact trace metadata to downstream consumers.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
import hashlib
import math
import re
from typing import Any

import numpy as np

LIFT_PROFILE_VERSION = "AURA_SINGLE_SEED_LIFT_V1"
DEFAULT_DIMENSIONS = 10_000
DEFAULT_PRECISION_LAYERS = 4
DEFAULT_TOP_TRACE_COUNT = 6
_EPS = 1e-9


@dataclass(frozen=True)
class SingleSeedTrace:
    trace_id: str
    resonance: float
    dispatch_index: int
    lift_layer: int

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "resonance": self.resonance,
            "dispatch_index": self.dispatch_index,
            "lift_layer": self.lift_layer,
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any]) -> SingleSeedTrace:
        return cls(
            trace_id=str(payload.get("trace_id", "")),
            resonance=float(payload.get("resonance", 0.0) or 0.0),
            dispatch_index=int(payload.get("dispatch_index", 0) or 0),
            lift_layer=int(payload.get("lift_layer", 0) or 0),
        )


@dataclass(frozen=True)
class SingleSeedLiftProfile:
    version: str
    seed_id: str
    seed_digest: str
    seed_index: int
    seed_resonance: float
    inverse_cache_digest: str
    lift_layers: int
    vector_count: int
    top_traces: tuple[SingleSeedTrace, ...] = ()
    complexity_model: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "seed_id": self.seed_id,
            "seed_digest": self.seed_digest,
            "seed_index": self.seed_index,
            "seed_resonance": self.seed_resonance,
            "inverse_cache_digest": self.inverse_cache_digest,
            "lift_layers": self.lift_layers,
            "vector_count": self.vector_count,
            "top_traces": [trace.to_jsonable() for trace in self.top_traces],
            "complexity_model": dict(self.complexity_model),
        }

    @classmethod
    def from_jsonable(cls, payload: dict[str, Any] | None) -> SingleSeedLiftProfile | None:
        if not isinstance(payload, dict) or not payload:
            return None
        return cls(
            version=str(payload.get("version", LIFT_PROFILE_VERSION)),
            seed_id=str(payload.get("seed_id", "")),
            seed_digest=str(payload.get("seed_digest", "")),
            seed_index=int(payload.get("seed_index", 0) or 0),
            seed_resonance=float(payload.get("seed_resonance", 0.0) or 0.0),
            inverse_cache_digest=str(payload.get("inverse_cache_digest", "")),
            lift_layers=int(payload.get("lift_layers", 0) or 0),
            vector_count=int(payload.get("vector_count", 0) or 0),
            top_traces=tuple(
                SingleSeedTrace.from_jsonable(item)
                for item in payload.get("top_traces", ()) or ()
                if isinstance(item, dict)
            ),
            complexity_model=dict(payload.get("complexity_model", {}) or {}),
        )


@dataclass(frozen=True)
class SingleSeedLiftResult:
    profile: SingleSeedLiftProfile
    lifted_vector: np.ndarray


def _digest_bytes(payload: bytes, *, size: int = 16) -> str:
    return hashlib.blake2b(payload, digest_size=size).hexdigest()


def _safe_label(value: str, *, limit: int = 80) -> str:
    clean = re.sub(r"[^A-Za-z0-9_.:-]+", "_", value or "").strip("_")
    return (clean or "AURA_SEED")[:limit]


def _unit_phase(vector: np.ndarray, *, dimensions: int = DEFAULT_DIMENSIONS) -> np.ndarray:
    arr = np.asarray(vector, dtype=np.complex64).reshape(-1)
    if arr.size != dimensions:
        padded = np.ones(dimensions, dtype=np.complex64)
        padded[: min(arr.size, dimensions)] = arr[:dimensions]
        arr = padded
    if not np.any(arr):
        return np.ones(dimensions, dtype=np.complex64)
    return np.exp(1j * np.angle(arr)).astype(np.complex64, copy=False)


def _seeded_unit_phasor(label: str, *, dimensions: int = DEFAULT_DIMENSIONS) -> np.ndarray:
    seed = int.from_bytes(
        hashlib.blake2b(label.encode("utf-8"), digest_size=8).digest(),
        "big",
    )
    rng = np.random.default_rng(seed)
    phases = rng.uniform(-math.pi, math.pi, dimensions).astype(np.float32)
    return np.exp(1j * phases).astype(np.complex64, copy=False)


def encode_text_as_unit_phasor(text: str, *, dimensions: int = DEFAULT_DIMENSIONS) -> np.ndarray:
    clean = " ".join((text or "").split())
    if not clean:
        return _seeded_unit_phasor("EMPTY::SINGLE_SEED", dimensions=dimensions)
    width = 1800
    step = 1640
    field = np.zeros(dimensions, dtype=np.complex64)
    for idx, pos in enumerate(range(0, min(len(clean), 220_000), step)):
        chunk = clean[pos : pos + width]
        digest = hashlib.blake2b(chunk.encode("utf-8"), digest_size=16).hexdigest()
        field += np.roll(_seeded_unit_phasor(f"TEXT::{digest}", dimensions=dimensions), idx * 4097)
    return _unit_phase(field, dimensions=dimensions)


def _phasor_digest(vector: np.ndarray) -> str:
    return _digest_bytes(np.asarray(vector, dtype=np.complex64).reshape(-1).tobytes())


def _resonance(lhs: np.ndarray, rhs: np.ndarray, *, dimensions: int) -> float:
    left = np.asarray(lhs, dtype=np.complex64).reshape(dimensions)
    right = np.asarray(rhs, dtype=np.complex64).reshape(dimensions)
    return float(np.real(np.dot(left, np.conjugate(right))) / max(1, dimensions))


def _resonance_with_cached_inverse(lhs: np.ndarray, inverse_rhs: np.ndarray, *, dimensions: int) -> float:
    left = np.asarray(lhs, dtype=np.complex64).reshape(dimensions)
    inverse = np.asarray(inverse_rhs, dtype=np.complex64).reshape(dimensions)
    return float(np.real(np.dot(left, inverse)) / max(1, dimensions))


def _normalise_vectors(vectors: Iterable[np.ndarray], *, dimensions: int) -> list[np.ndarray]:
    normalised: list[np.ndarray] = []
    for idx, vector in enumerate(vectors):
        try:
            normalised.append(_unit_phase(vector, dimensions=dimensions))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid single-seed lift vector at index {idx}") from exc
    return normalised


def compile_single_seed_lift(
    label: str,
    vectors: Sequence[np.ndarray] | Iterable[np.ndarray],
    *,
    base_vector: np.ndarray | None = None,
    precision_layers: int = DEFAULT_PRECISION_LAYERS,
    top_trace_count: int = DEFAULT_TOP_TRACE_COUNT,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> SingleSeedLiftResult:
    """Compile a cached single-seed lift over already-local VSA vectors."""
    dims = max(1, int(dimensions))
    layers = max(1, int(precision_layers))
    trace_limit = max(1, int(top_trace_count))
    local_vectors = _normalise_vectors(vectors, dimensions=dims)
    if not local_vectors:
        local_vectors = [_seeded_unit_phasor(label, dimensions=dims)]

    if base_vector is None:
        base = _unit_phase(np.sum(np.stack(local_vectors), axis=0), dimensions=dims)
    else:
        base = _unit_phase(base_vector, dimensions=dims)

    seed_scores = [
        (_resonance(vector, base, dimensions=dims), idx, vector)
        for idx, vector in enumerate(local_vectors)
    ]
    seed_scores.sort(key=lambda item: item[0], reverse=True)
    seed_resonance, seed_index, seed_vector = seed_scores[0]
    inverse_cache = np.conjugate(seed_vector).astype(np.complex64, copy=False)

    traces: list[SingleSeedTrace] = []
    residual = np.zeros(dims, dtype=np.complex64)
    for idx, vector in enumerate(local_vectors):
        trace_resonance = _resonance_with_cached_inverse(vector, inverse_cache, dimensions=dims)
        residual += (1.0 - max(-1.0, min(1.0, trace_resonance))) * vector
        traces.append(
            SingleSeedTrace(
                trace_id=_digest_bytes(f"{label}:{idx}:{trace_resonance:.8f}".encode(), size=8),
                resonance=round(trace_resonance, 6),
                dispatch_index=idx,
                lift_layer=1 + (idx % layers),
            )
        )
    residual /= max(1, len(local_vectors))

    lifted = seed_vector.copy()
    for layer in range(layers):
        lifted = _unit_phase(
            lifted + residual * (1.0 / (layer + 2.0)),
            dimensions=dims,
        )

    top_traces = tuple(
        sorted(traces, key=lambda trace: abs(trace.resonance), reverse=True)[:trace_limit]
    )
    seed_id = f"{_safe_label(label)}:{_digest_bytes(label.encode('utf-8'), size=6)}"
    profile = SingleSeedLiftProfile(
        version=LIFT_PROFILE_VERSION,
        seed_id=seed_id,
        seed_digest=_phasor_digest(seed_vector),
        seed_index=seed_index,
        seed_resonance=round(seed_resonance, 6),
        inverse_cache_digest=_phasor_digest(inverse_cache),
        lift_layers=layers,
        vector_count=len(local_vectors),
        top_traces=top_traces,
        complexity_model={
            "source_paper": "arXiv:2606.20633",
            "portable_pattern": "single_seed_cached_inverse_trace_dispatch",
            "cache_once": True,
            "paper_lift_bound": "O(n + m^3 log p + e*m^2)",
            "aura_vector_bound": "O(C*D + e*D)",
            "chunk_count": len(local_vectors),
            "dimensions": dims,
            "precision_layers": layers,
        },
    )
    return SingleSeedLiftResult(profile=profile, lifted_vector=lifted)


def compile_text_single_seed_lift(
    label: str,
    text_blocks: Sequence[str] | Iterable[str],
    *,
    precision_layers: int = DEFAULT_PRECISION_LAYERS,
    top_trace_count: int = DEFAULT_TOP_TRACE_COUNT,
    dimensions: int = DEFAULT_DIMENSIONS,
) -> SingleSeedLiftResult:
    vectors = [
        encode_text_as_unit_phasor(block, dimensions=dimensions)
        for block in text_blocks
        if str(block or "").strip()
    ]
    return compile_single_seed_lift(
        label,
        vectors,
        precision_layers=precision_layers,
        top_trace_count=top_trace_count,
        dimensions=dimensions,
    )


def compact_lift_capsule(profile: SingleSeedLiftProfile | dict[str, Any] | None, *, limit: int = 360) -> str:
    if isinstance(profile, dict):
        profile = SingleSeedLiftProfile.from_jsonable(profile)
    if profile is None:
        return ""
    trace_text = ",".join(
        f"{trace.dispatch_index}:{trace.resonance:.3f}"
        for trace in profile.top_traces[:4]
    )
    capsule = (
        f"SEED={profile.seed_id}|IDX={profile.seed_index}|"
        f"LAYERS={profile.lift_layers}|VECTORS={profile.vector_count}|"
        f"R={profile.seed_resonance:.3f}|TRACE={trace_text}|"
        f"PATTERN=single_seed_cached_inverse_dispatch"
    )
    return capsule[: max(1, int(limit))]
