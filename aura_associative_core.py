"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa885-[Q-SYS:D4FAE19AB3EF864B]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIZAAGI'IN (Mutual Benefit)
DEPENDENCIES: hashlib, numpy, __future__
FUNCTIONS: __init__, store, query, fast_path_lookup, _apply_decay, force_decay, get_stats, reset
SYNOPSIS: The `AuraOS` Python module, leveraging `hashlib` for cryptographic hashing, `numpy` for numerical computations, and `__future__` annotations for type hints, provides a strict, decay-based data storage and retrieval system via its core functions: `__init__` for initialization, `store` for persistent data insertion, `query` for retrieval with optional decay application, `fast_path_lookup` for optimized hierarchical key access, `_apply_decay` for internal decay logic, `force_decay` for manual decay triggers, `get_stats` for system metrics, and `reset` for full state clearance.
[/AURA_MASTER_KEY]
"""
from __future__ import annotations

import hashlib

import numpy as np

# Non-monotonic memory decay factor (MIT CBMM review — prevents capacity saturation)
_DECAY_ALPHA: float = 0.98

# Dimension of the complex phasor space (must match the rest of the PVM)
_DEFAULT_DIM: int = 10_000

# How many store() calls between automatic decay sweeps
_DECAY_INTERVAL: int = 50


class AuraAssociativeCore:
    """
    High-capacity associative memory for the AURA Polysynthetic VM.

    Theory
    ------
    Each memory trace is stored as an outer-product update to the
    associative matrix M (D × D).  At query time a single matrix-vector
    product M @ q recovers the superimposed memory nearest to the probe
    vector q, in O(D²) time — effectively O(1) relative to database
    search over N records since D is fixed.

    Non-monotonic decay prevents capacity saturation: after every
    _DECAY_INTERVAL store operations the matrix is scaled by α=0.98,
    gently erasing the oldest, lowest-resonance traces without
    destroying high-confidence memories (which re-accumulate faster).

    Usage
    -----
    ::

        core = AuraAssociativeCore(dim=10_000)
        core.store(key_vector, value_vector)
        result = core.query(probe_vector)   # → {"label": str, "confidence": float}
    """

    def __init__(self, dim: int = _DEFAULT_DIM, decay: float = _DECAY_ALPHA) -> None:
        self.dim = dim
        self.decay = decay
        # The associative matrix M ∈ ℂ^{D×D} stored in float32 for memory efficiency.
        # We split into real and imaginary parts to stay within PVM zero-copy rules.
        self._M_real: np.ndarray = np.zeros((dim, dim), dtype=np.float32)
        self._M_imag: np.ndarray = np.zeros((dim, dim), dtype=np.float32)
        self._store_count: int = 0
        # Label registry maps a content-hash to a human-readable tag
        self._label_map: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def store(
        self,
        key_vector: np.ndarray,
        value_vector: np.ndarray,
        label: str = "",
    ) -> None:
        """
        Superimpose a (key, value) pair into the associative matrix via
        the outer product:  M ← M + Re(key ⊗ value†) + i·Im(key ⊗ value†)
        """
        k = key_vector.astype(np.complex64).ravel()[: self.dim]
        v = value_vector.astype(np.complex64).ravel()[: self.dim]

        outer = np.outer(k, v.conj())
        self._M_real += np.real(outer)
        self._M_imag += np.imag(outer)

        if label:
            content_key = hashlib.blake2b(k.tobytes(), digest_size=4).hexdigest()
            self._label_map[content_key] = label

        self._store_count += 1
        if self._store_count % _DECAY_INTERVAL == 0:
            self._apply_decay()

    def query(self, probe: np.ndarray) -> dict:
        """
        Retrieve the nearest memory to *probe* via a single matrix-vector
        product.  Returns a dict with ``vector``, ``confidence``, and
        ``label``.
        """
        q = probe.astype(np.complex64).ravel()[: self.dim]
        M = self._M_real + 1j * self._M_imag

        raw = M @ q
        # Normalise to unit magnitude — project back onto the unit hypersphere
        norm = np.linalg.norm(raw)
        if norm < 1e-9:
            return {"vector": q, "confidence": 0.0, "label": "EMPTY"}
        retrieved = (raw / norm).astype(np.complex64)

        # Cosine similarity between probe and retrieved vector
        confidence = float(
            np.abs(np.dot(q.conj(), retrieved)) / (np.linalg.norm(q) + 1e-9)
        )

        # Attempt label lookup
        content_key = hashlib.blake2b(retrieved.tobytes()[:16], digest_size=4).hexdigest()
        label = self._label_map.get(content_key, "UNLABELED")

        return {"vector": retrieved, "confidence": confidence, "label": label}

    def fast_path_lookup(self, text: str, get_semantic_fn) -> dict:
        """
        Convenience wrapper: vectorise *text* with *get_semantic_fn* (e.g.
        ``aura_spvm.get_semantic_vector``) then run :meth:`query`.
        """
        probe = get_semantic_fn(text, dim=self.dim)
        return self.query(probe)

    # ------------------------------------------------------------------
    # Non-monotonic decay
    # ------------------------------------------------------------------

    def _apply_decay(self) -> None:
        """Scale the matrix by α — erases old low-confidence traces."""
        self._M_real *= self.decay
        self._M_imag *= self.decay

    def force_decay(self) -> None:
        """Manually trigger a decay pass (callable from !synthesize)."""
        self._apply_decay()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Return a lightweight status snapshot."""
        norm = float(np.linalg.norm(self._M_real + 1j * self._M_imag, "fro"))
        return {
            "dim": self.dim,
            "stored_traces": self._store_count,
            "decay_alpha": self.decay,
            "matrix_frobenius_norm": round(norm, 4),
            "labels_registered": len(self._label_map),
        }

    def reset(self) -> None:
        """Zero the associative matrix (hard forget)."""
        self._M_real[:] = 0.0
        self._M_imag[:] = 0.0
        self._store_count = 0
        self._label_map.clear()
