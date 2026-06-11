"""
Aura Blockchain — Phasor Ledger Core
=====================================
10,000-D hyperdimensional VSA (Vector Symbolic Architecture) state
commitment layer.  The entire ledger state is a single complex phasor
vector that rotates with each transaction — no hash chains, no Merkle
patrcia tries, no O(n) block scanning.

Operations:
  - bind   : Hadamard product (⊗) — entangle two vectors
  - unbind : Hadamard product with conjugate (⊘) — disentangle
  - bundle : Normalised superposition — merge many accounts into one state
  - similarity : Masked cosine similarity (5% subsample) — O(1) validation

Based on the mathematics in AuraOS/liquid_fhrr.py and vsa_resonator.py
"""

import hashlib
import numpy as np

DIMENSIONS = 10000
MASK_SIZE = 500  # 5 % subsample for accelerated similarity

# ---------------------------------------------------------------------------
# Seeded random generator — deterministic across boots for reproducibility
# ---------------------------------------------------------------------------
_rng = np.random.default_rng(seed=0xA0B0C0D0)


def _seed_for(name: str) -> np.random.Generator:
    """Deterministic per-account / per-concept seed."""
    h = int(hashlib.sha256(name.encode()).hexdigest(), 16) & 0xFFFF_FFFF
    return np.random.default_rng(seed=h)


# ═══════════════════════════════════════════════════════════════════════════
# Core VSA operations (matching liquid_fhrr.py semantics)
# ═══════════════════════════════════════════════════════════════════════════

def generate_phasor(name: str = "") -> np.ndarray:
    """
    Generate a 10,000-D unitary phasor vector e^{iθ}, θ ~ U(-π, π).
    If *name* is provided the vector is deterministic (repeatable).
    """
    rng = _seed_for(name) if name else _rng
    theta = rng.uniform(-np.pi, np.pi, DIMENSIONS)
    return np.exp(1j * theta).astype(np.complex128)


def bind(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """⊗ — Coordinate-wise Hadamard product (binding)."""
    return a * b


def unbind(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """⊘ — Unbinding via complex conjugate of b."""
    return a * np.conj(b)


def bundle(vectors: list[np.ndarray]) -> np.ndarray:
    """
    ⊕ — Normalised superposition.
    Sum vectors then project back onto the unit circle (angle only).
    """
    stacked = np.sum(np.array(vectors), axis=0)
    angles = np.angle(stacked)
    return np.exp(1j * angles)


def similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine similarity on the full 10,000-D space.
    Returns value ∈ [-1, 1] — near 1.0 = identical.
    """
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom < 1e-12:
        return 0.0
    return float(np.real(np.dot(a, np.conj(b)) / denom))


def sampled_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    O(1) similarity via 5 % random mask — 20× speedup on mobile.
    (See vsa_resonator.py — sampled_similarity)
    """
    mask = _rng.choice(DIMENSIONS, size=MASK_SIZE, replace=False)
    a_sub, b_sub = a[mask], b[mask]
    # Cosine on the sub-sample
    return float(np.real(np.dot(a_sub, np.conj(b_sub)) /
                         (np.linalg.norm(a_sub) * np.linalg.norm(b_sub) + 1e-12)))


def phase_drift(a: np.ndarray, b: np.ndarray) -> float:
    """Δφ — angular deviation in radians ∈ [0, π]."""
    return float(np.arccos(max(-1.0, min(1.0, similarity(a, b)))))


# ═══════════════════════════════════════════════════════════════════════════
# Ledger-specific helpers
# ═══════════════════════════════════════════════════════════════════════════

INTENSITY_SCALE = 100.0  # maps 1 balance unit → phasor intensity multiplier


def account_phasor(account_id: str, balance: float) -> np.ndarray:
    """Derive an account's phasor from its ID and balance."""
    base = generate_phasor(account_id)
    # Scale phase intensity by balance (fractional binding from liquid_fhrr.py)
    return np.exp(1j * (np.angle(base) * (1.0 + balance / INTENSITY_SCALE)))


def global_state_phasor(accounts: dict[str, float]) -> np.ndarray:
    """Bundle all account phasors into the single global ledger phasor."""
    if not accounts:
        return np.ones(DIMENSIONS, dtype=np.complex128)
    vecs = [account_phasor(aid, bal) for aid, bal in accounts.items()]
    return bundle(vecs)


def apply_transaction(
    global_phasor: np.ndarray,
    sender: str,
    receiver: str,
    amount: float,
    sender_balance: float,
    receiver_balance: float,
) -> np.ndarray:
    """
    Apply a transfer by:
      (1) unbinding the old sender/receiver phasors
      (2) binding the new ones
    The result is a rotation of the global phasor.
    """
    # Remove old state
    old_sender = account_phasor(sender, sender_balance)
    old_receiver = account_phasor(receiver, receiver_balance)

    # Intermediate = global ⊘ old_sender ⊘ old_receiver
    intermediate = unbind(global_phasor, old_sender)
    intermediate = unbind(intermediate, old_receiver)

    # Add new state
    new_sender = account_phasor(sender, sender_balance - amount)
    new_receiver = account_phasor(receiver, receiver_balance + amount)

    intermediate = bind(intermediate, new_sender)
    intermediate = bind(intermediate, new_receiver)

    # Normalise back to unit hypersphere
    angles = np.angle(intermediate)
    return np.exp(1j * angles)