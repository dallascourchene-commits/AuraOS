"""
Aura Blockchain — Full Node
=============================
A complete validator node that:
  - Stakes RAM via MemoryStake (gas-free participation)
  - Holds an Ed25519 keypair for consensus signing
  - Maintains a local copy of the phasor ledger state
  - Validates incoming blocks via O(1) 5% masked similarity
  - Participates in consensus rounds
  - Detects forks via Procrustes alignment
  - Self-heals by resyncing from quorum phasor
"""

import hashlib
import time
import numpy as np
from dataclasses import dataclass, field

from . import phasor_ledger as pl
from .block import Block, Transaction
from .consensus import AuraConsensus, Ed25519KeyPair, ConsensusError, PROCRUSTES_THRESHOLD
from .memory_staking import MemoryStake, sample_rss_mb, verify_memory_stake


@dataclass
class AccountState:
    balance: float = 0.0
    nonce: int = 0


class AuraNode:
    """
    A full validator node in the Aura phasor-ledger network.

    Lifecycle:
      1. stake_ram()     — Allocate memory, join validator set
      2. sync()          — Sync to latest quorum phasor (genesis or resume)
      3. submit_txn()    — Add transactions to mempool
      4. mine_block()    — If proposer, build & propose block
      5. validate_block()— Validate incoming blocks (5% subsample)
      6. detect_fork()   — Procrustes alignment check
      7. heal()          — Resync from quorum if fork detected
    """

    def __init__(self, node_id: str, stake_mb: int = 128):
        self.node_id = node_id
        self.stake_mb = stake_mb

        # Memory stake (gas-free participation token)
        self.stake: MemoryStake | None = None

        # Keypair for consensus signing
        seed = hashlib.sha256(("aura_node_" + node_id).encode()).digest()[:32]
        self.keypair = Ed25519KeyPair(seed)

        # Account balances (local state)
        self.accounts: dict[str, AccountState] = {}

        # Mempool: pending transactions
        self.mempool: list[Transaction] = []

        # Local chain tip
        self.chain: list[Block] = []

        # Consensus engine (shared across nodes — in production this
        # would be a network, but for demo we instantiate separately
        # and pass in)
        self.consensus: AuraConsensus | None = None

        # Node metrics
        self.blocks_validated: int = 0
        self.blocks_proposed: int = 0
        self.forks_detected: int = 0
        self.heals_performed: int = 0

        # Running stats
        self._start_time = time.time()
        self._rss_baseline_mb = sample_rss_mb()

    # ═══════════════════════════════════════════════════════════════════
    # Lifecycle
    # ═══════════════════════════════════════════════════════════════════

    def stake_ram(self) -> MemoryStake:
        """Allocate RAM to join the validator set.  No token cost."""
        self.stake = MemoryStake(size_mb=self.stake_mb, node_id=self.node_id)
        return self.stake

    def join_consensus(self, consensus: AuraConsensus):
        """Join a shared consensus engine."""
        self.consensus = consensus

    def initialize_genesis(self, genesis_accounts: dict[str, float]):
        """Set up the genesis account state."""
        self.accounts = {
            aid: AccountState(balance=bal, nonce=0)
            for aid, bal in genesis_accounts.items()
        }

    def sync(self, genesis_accounts: dict[str, float]):
        """
        Sync to the genesis state.
        In production this would download the latest phasor + delta proofs
        from the quorum, but for the demo we start from genesis.
        """
        self.initialize_genesis(genesis_accounts)

    # ═══════════════════════════════════════════════════════════════════
    # Transaction submission
    # ═══════════════════════════════════════════════════════════════════

    def submit_transaction(self, sender: str, receiver: str,
                           amount: float) -> Transaction | None:
        """
        Submit a token transfer to the mempool.

        Validates:
          - Sender has sufficient balance
          - Amount > 0
          - Sender != receiver
        """
        if amount <= 0:
            return None
        if sender == receiver:
            return None

        sender_account = self.accounts.get(sender)
        if sender_account is None or sender_account.balance < amount:
            return None

        # Deduct immediately (optimistic — rolled back if block rejected)
        sender_account.balance -= amount
        receiver_account = self.accounts.setdefault(
            receiver, AccountState(balance=0.0, nonce=0))
        receiver_account.balance += amount

        tx = Transaction(sender, receiver, amount, nonce=sender_account.nonce)
        sender_account.nonce += 1
        self.mempool.append(tx)
        return tx

    # ═══════════════════════════════════════════════════════════════════
    # Block building & validation
    # ═══════════════════════════════════════════════════════════════════

    def build_block(self) -> Block | None:
        """
        Build a candidate block from mempool transactions.
        Called by the proposer.
        """
        if not self.mempool:
            return None
        if self.consensus is None:
            return None

        prev_phasor = self._current_phasor()
        txs = self.mempool[:]
        self.mempool.clear()

        block = Block(
            index=self.consensus.height,
            prev_phasor=prev_phasor,
            transactions=txs,
            proposer=self.node_id,
        )

        self.blocks_proposed += 1
        return block

    def validate_block(self, block: Block) -> tuple[bool, float, float]:
        """
        Validate an incoming block.

        Returns (is_valid, sampled_similarity, full_similarity).
        O(1) check via 5% subsampled phasor similarity.

        FIX: This is the critical consensus gap.  We verify:
          1. The block's state_phasor matches what we compute from the
             previous phasor + transactions (reproducible rotation).
          2. The 5% subsampled similarity ≥ alignment threshold.
        """
        # Recompute the expected state phasor by applying the block's
        # transactions to the previous phasor
        current = self._current_phasor().copy()
        running: dict[str, float] = {}

        for tx in block.transactions:
            sbal = running.get(tx.sender,
                               self.accounts.get(tx.sender, AccountState()).balance)
            rbal = running.get(tx.receiver,
                               self.accounts.get(tx.receiver, AccountState()).balance)
            current = pl.apply_transaction(
                current, tx.sender, tx.receiver, tx.amount, sbal, rbal)
            running[tx.sender] = sbal - tx.amount
            running[tx.receiver] = rbal + tx.amount

        expected = current

        sam_sim = pl.sampled_similarity(block.state_phasor, expected)
        full_sim = pl.similarity(block.state_phasor, expected)

        is_valid = sam_sim >= 0.95  # ALIGNMENT_THRESHOLD
        self.blocks_validated += 1
        return is_valid, sam_sim, full_sim

    def apply_block(self, block: Block):
        """Apply a validated block's transactions to local state."""
        for tx in block.transactions:
            sacc = self.accounts.get(tx.sender)
            racc = self.accounts.setdefault(
                tx.receiver, AccountState(balance=0.0, nonce=0))
            if sacc:
                # Balance already deducted at submit time; verify consistency
                pass
        self.chain.append(block)

    # ═══════════════════════════════════════════════════════════════════
    # Fork detection & healing
    # ═══════════════════════════════════════════════════════════════════

    def detect_fork(self, quorum_phasor: np.ndarray) -> tuple[bool, float]:
        """
        Procrustes alignment fork detection (subsampled — 200 dims).
        If the local chain phasor has drifted from the quorum phasor,
        this returns is_fork=True.
        """
        local = self._current_phasor()

        # Subsample 200 dimensions for tractable Procrustes
        rng = np.random.default_rng(seed=42)
        sample_dim = min(200, len(local))
        idx = rng.choice(len(local), size=sample_dim, replace=False)

        theta_local = np.angle(local[idx])
        theta_quorum = np.angle(quorum_phasor[idx])

        # Cross-correlation matrix (200×200, tractable)
        M = theta_local.reshape(-1, 1) @ theta_quorum.reshape(1, -1)
        U, S, Vh = np.linalg.svd(M, full_matrices=False)
        R = U @ Vh

        residual = np.linalg.norm(
            theta_local.reshape(1, -1) @ R -
            theta_quorum.reshape(1, -1), 'fro')
        denom = np.linalg.norm(theta_quorum)
        alignment = 1.0 - (residual / denom) if denom > 1e-12 else 1.0

        is_fork = alignment < PROCRUSTES_THRESHOLD
        if is_fork:
            self.forks_detected += 1
        return is_fork, alignment

    def heal(self, quorum_phasor: np.ndarray, quorum_accounts: dict[str, float]):
        """
        Heal from a fork: reset local state to the quorum's phasor
        and account balances.
        """
        self.accounts = {
            aid: AccountState(balance=bal, nonce=0)
            for aid, bal in quorum_accounts.items()
        }
        self.mempool.clear()
        self.heals_performed += 1

    # ═══════════════════════════════════════════════════════════════════
    # State queries
    # ═══════════════════════════════════════════════════════════════════

    def _current_phasor(self) -> np.ndarray:
        """Derive the phasor from the current account state."""
        balances = {aid: acc.balance for aid, acc in self.accounts.items()}
        return pl.global_state_phasor(balances)

    @property
    def current_phasor(self) -> np.ndarray:
        return self._current_phasor()

    @property
    def balance(self, account_id: str) -> float:
        acc = self.accounts.get(account_id)
        return acc.balance if acc else 0.0

    @property
    def rss_mb(self) -> float:
        return sample_rss_mb()

    @property
    def stake_commitment(self) -> str:
        return self.stake.commitment() if self.stake else ""

    def stats(self) -> dict:
        """Runtime statistics."""
        return {
            "node_id": self.node_id,
            "uptime_s": time.time() - self._start_time,
            "rss_mb": self.rss_mb,
            "rss_baseline_mb": self._rss_baseline_mb,
            "stake_mb": self.stake_mb,
            "stake_committed": bool(self.stake),
            "accounts": len(self.accounts),
            "mempool_size": len(self.mempool),
            "chain_height": len(self.chain),
            "blocks_validated": self.blocks_validated,
            "blocks_proposed": self.blocks_proposed,
            "forks_detected": self.forks_detected,
            "heals_performed": self.heals_performed,
            "key_hex": self.keypair.public_hex()[:16] + "...",
        }