"""Canonical deterministic VSA encoding profiles for Aura route capsules.

This module provides data-only, versioned vector operations. It does not grant
routing, capability, patch, or promotion authority. Live Arena integration is a
later Phase C slice; C1 only stabilizes representation and digest contracts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

import numpy as np

VSA_ENCODING_PROFILE_VERSION = "AURA_VSA_ENCODING_PROFILE_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


@dataclass(frozen=True)
class VSAEncodingProfile:
    profile_id: str
    dimensions: int = 10_000
    dtype: str = "complex64"
    binding: str = "elementwise_multiply"
    unbinding: str = "conjugate_multiply"
    bundling: str = "normalized_sum"
    permutation: str = "cyclic_shift"
    permutation_shift: int = 4_097
    normalization: str = "l2"
    seed_scheme: str = "blake2b-64"

    def validate(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id is required")
        if self.dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if self.dtype != "complex64":
            raise ValueError("C1 supports only complex64 profiles")
        if self.binding != "elementwise_multiply":
            raise ValueError("unsupported binding operation")
        if self.unbinding != "conjugate_multiply":
            raise ValueError("unsupported unbinding operation")
        if self.bundling != "normalized_sum":
            raise ValueError("unsupported bundling operation")
        if self.permutation != "cyclic_shift":
            raise ValueError("unsupported permutation operation")
        if self.normalization != "l2":
            raise ValueError("unsupported normalization operation")
        if self.seed_scheme != "blake2b-64":
            raise ValueError("unsupported seed scheme")

    @classmethod
    def from_dict(cls, value: dict) -> "VSAEncodingProfile":
        if not isinstance(value, dict):
            raise TypeError("VSA profile must be an object")
        payload = dict(value)
        for metadata_key in (
            "schema_version", "kind", "component_id",
            "patch_authority", "vsa_patch_authority",
        ):
            payload.pop(metadata_key, None)
        profile = cls(**payload)
        profile.validate()
        return profile

    def canonical_dict(self) -> dict:
        self.validate()
        return {
            "schema_version": VSA_ENCODING_PROFILE_VERSION,
            **asdict(self),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }

    def digest(self) -> str:
        body = json.dumps(self.canonical_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


DEFAULT_COMPLEX_PHASOR_V1 = VSAEncodingProfile(profile_id="AURA_COMPLEX_PHASOR_V1")


def deterministic_seed(label: str, *, namespace: str = "AURA_VSA") -> int:
    normalized = f"{namespace}::{str(label)}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(normalized, digest_size=8).digest(), "big")


def seeded_hv(label: str, profile: VSAEncodingProfile = DEFAULT_COMPLEX_PHASOR_V1) -> np.ndarray:
    """Allocate a deterministic dense unit-magnitude complex hypervector."""
    profile.validate()
    rng = np.random.default_rng(deterministic_seed(label, namespace=profile.profile_id))
    phases = rng.integers(0, 4, size=profile.dimensions, dtype=np.int8)
    real = np.where((phases == 0) | (phases == 3), 1.0, -1.0).astype(np.float32, copy=False)
    imag = np.where((phases == 0) | (phases == 1), 1.0, -1.0).astype(np.float32, copy=False)
    return ((real + 1j * imag) / np.complex64(np.sqrt(2.0))).astype(np.complex64, copy=False)


def normalize(vector: np.ndarray) -> np.ndarray:
    value = np.asarray(vector, dtype=np.complex64)
    norm = float(np.linalg.norm(value))
    if norm == 0.0:
        return value.copy()
    return (value / np.complex64(norm)).astype(np.complex64, copy=False)


def bind(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.multiply(np.asarray(left, dtype=np.complex64), np.asarray(right, dtype=np.complex64))


def unbind(bound: np.ndarray, role: np.ndarray) -> np.ndarray:
    return np.multiply(np.conjugate(np.asarray(role, dtype=np.complex64)), np.asarray(bound, dtype=np.complex64))


def bundle(vectors: Iterable[np.ndarray], *, normalize_result: bool = True) -> np.ndarray:
    items = [np.asarray(item, dtype=np.complex64) for item in vectors]
    if not items:
        raise ValueError("at least one vector is required for bundling")
    shape = items[0].shape
    if any(item.shape != shape for item in items):
        raise ValueError("all bundled vectors must have the same shape")
    result = np.sum(np.stack(items, axis=0), axis=0, dtype=np.complex64)
    return normalize(result) if normalize_result else result.astype(np.complex64, copy=False)


def permute(vector: np.ndarray, *, steps: int | None = None, profile: VSAEncodingProfile = DEFAULT_COMPLEX_PHASOR_V1) -> np.ndarray:
    shift = profile.permutation_shift if steps is None else int(steps)
    return np.roll(np.asarray(vector, dtype=np.complex64), shift).astype(np.complex64, copy=False)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    a = np.asarray(left, dtype=np.complex64)
    b = np.asarray(right, dtype=np.complex64)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.real(np.vdot(a, b)) / denom)


def encode_text(text: str, profile: VSAEncodingProfile = DEFAULT_COMPLEX_PHASOR_V1) -> np.ndarray:
    """Deterministically encode normalized character bigrams with BLAKE2 seeds."""
    normalized_text = " ".join(str(text or "").casefold().split())
    if not normalized_text:
        return np.zeros(profile.dimensions, dtype=np.complex64)
    grams = [normalized_text[index:index + 2] for index in range(max(1, len(normalized_text) - 1))]
    if len(normalized_text) == 1:
        grams = [normalized_text]
    return bundle(seeded_hv(f"TEXT_BIGRAM::{gram}", profile) for gram in grams)


def vector_digest(vector: np.ndarray) -> str:
    value = np.ascontiguousarray(np.asarray(vector, dtype=np.complex64))
    return hashlib.blake2b(value.view(np.uint8), digest_size=20).hexdigest()
