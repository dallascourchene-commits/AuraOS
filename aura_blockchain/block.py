"""
Aura Blockchain — Block Structure
==================================
Blocks in the Aura ledger carry a *phasor rotation delta* instead of a
cryptographic hash chain.  Each block records the transactions that
rotate the global phasor state, and the resulting state root is the
phasor vector itself — not a Merkle root hash.

Block validity is checked via phasor alignment:
  similarity(expected_rotation, actual_phasor) >= ALIGNMENT_THRESHOLD
"""

import time
import hashlib
import struct
import numpy as np
from . import phasor_ledger as pl

ALIGNMENT_THRESHOLD = 0.95  # Must be ≥ 0.95 for block to be valid
MAX_TXNS_PER_BLOCK = 256


class Transaction:
    """A single transfer within a block."""

    __slots__ = ("sender", "receiver", "amount", "nonce", "timestamp", "sig")

    def __init__(self, sender: str, receiver: str, amount: float,
                 nonce: int = 0):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.nonce = nonce
        self.timestamp = time.time()
        self.sig = b""  # filled by consensus.py when signed

    def digest(self) -> bytes:
        """Deterministic hash of transaction fields (for signing)."""
        h = hashlib.sha256()
        h.update(self.sender.encode())
        h.update(self.receiver.encode())
        h.update(f"{self.amount:.8f}".encode())
        h.update(f"{self.nonce}".encode())
        return h.digest()

    def __repr__(self) -> str:
        return (f"Tx({self.sender[:8]}→{self.receiver[:8]} "
                f"amt={self.amount:.2f} nonce={self.nonce})")


class Block:
    """
    A block in the Aura phasor ledger.

    Attributes:
        index: Block height.
        prev_phasor: Global phasor state *before* this block's transactions.
        transactions: List of Transactions included.
        state_phasor: Global phasor state *after* applying all transactions.
        phasor_delta: The rotation between prev_phasor and state_phasor.
        timestamp: Block creation time.
        proposer: Node ID of the block proposer.
        signatures: Collected Ed25519 signatures (from consensus).
    """

    __slots__ = ("index", "prev_phasor", "transactions", "state_phasor",
                 "phasor_delta", "timestamp", "proposer", "signatures",
                 "_hash")

    def __init__(self, index: int, prev_phasor: np.ndarray,
                 transactions: list[Transaction], proposer: str = ""):
        self.index = index
        self.prev_phasor = prev_phasor.copy()
        self.transactions = transactions
        self.proposer = proposer
        self.timestamp = time.time()
        self.signatures: list[bytes] = []

        # Compute the state phasor after applying all transactions
        self.state_phasor = self._compute_state_phasor()

        # Phasor delta = the rotation from prev to current
        self.phasor_delta = pl.unbind(self.state_phasor, self.prev_phasor)

        self._hash: bytes | None = None

    def _compute_state_phasor(self) -> np.ndarray:
        """
        Apply all transactions to the previous phasor to produce the new
        state commitment.  This is the phasor rotation that the block
        proposes.
        """
        current = self.prev_phasor.copy()

        # Track running balances for the transactions in this block
        # (in production this comes from the full account state)
        running: dict[str, float] = {}

        for tx in self.transactions:
            sender_bal = running.get(tx.sender, 100.0)  # default dummy
            receiver_bal = running.get(tx.receiver, 0.0)

            current = pl.apply_transaction(
                current, tx.sender, tx.receiver,
                tx.amount, sender_bal, receiver_bal,
            )

            running[tx.sender] = sender_bal - tx.amount
            running[tx.receiver] = receiver_bal + tx.amount

        return current

    def hash(self) -> bytes:
        """SHA-256 hash of the block header (for consensus signing)."""
        if self._hash is None:
            h = hashlib.sha256()
            h.update(struct.pack("<I", self.index))
            h.update(self.prev_phasor.tobytes())
            h.update(self.state_phasor.tobytes())
            h.update(self.proposer.encode())
            h.update(struct.pack("<d", self.timestamp))
            self._hash = h.digest()
        return self._hash

    def validate_phasor(self, expected_state: np.ndarray) -> float:
        """
        Validate that this block's state_phasor is consistent with
        the expected state given the previous phasor and transactions.

        Returns:
            similarity score ∈ [-1, 1].  Block is valid if ≥ ALIGNMENT_THRESHOLD.
        """
        return pl.similarity(self.state_phasor, expected_state)

    def validate_sampled(self, expected_state: np.ndarray) -> tuple[float, float]:
        """
        O(1) validation using 5% subsampled similarity.
        Returns (sampled_similarity, full_similarity).
        """
        return (
            pl.sampled_similarity(self.state_phasor, expected_state),
            pl.similarity(self.state_phasor, expected_state),
        )

    def phase_drift_from(self, other_phasor: np.ndarray) -> float:
        """Δφ in radians between this block's state and another phasor."""
        return pl.phase_drift(self.state_phasor, other_phasor)

    @property
    def alignment_score(self) -> float:
        """Normalised alignment ∈ [0, 1] between prev and current phasor."""
        return pl.similarity(self.state_phasor, self.prev_phasor)

    def __repr__(self) -> str:
        return (f"Block({self.index} | {len(self.transactions)} txns | "
                f"align={self.alignment_score:.4f} | sigs={len(self.signatures)})")


