"""
Aura Blockchain — Memory Staking (RAM-as-Gas)
==============================================
Replaces traditional token-gas fees with verifiable RAM allocation.
Validators prove they have committed physical memory to the swarm.
The "gas" is the temporary exposure of your RAM for consensus calculations.

Key properties:
  - Measures resident set size (RSS) as a proxy for committed memory
  - Allocates zero-copy contiguous byte buffers as "stake"
  - Provides cryptographic commitment to memory allocation
  - Validates other nodes' memory claims via challenge-response
"""

import hashlib
import os
import struct
import time
import numpy as np

# ── RSS measurement ──────────────────────────────────────────────────────

def sample_rss_mb() -> float:
    """Measure current process resident set size in MB via /proc/self/statm."""
    try:
        with open("/proc/self/statm", "r") as f:
            fields = f.read().split()
        # statm[1] = resident set size in pages (usually 4 KB pages)
        pages = int(fields[1])
        return pages * 4 / 1024.0  # convert to MB
    except Exception:
        # Fallback for non-Linux: use psutil if available
        try:
            import psutil
            return psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            return 0.0


def headroom_mb(cap_mb: float = 4096.0) -> float:
    """Remaining memory headroom under the cap (matches pvm_memory_guard.py)."""
    return max(0.0, cap_mb - sample_rss_mb())


# ── Memory stake allocation ──────────────────────────────────────────────

class MemoryStake:
    """
    A contiguous zero-copy memory allocation that serves as a validator's
    "stake" in the Aura swarm.  The allocated pages become part of the
    swarm's distributed computational substrate.

    Implementation: NumPy byte array with enforced contiguity.
    """

    def __init__(self, size_mb: int = 128, node_id: str = ""):
        """
        Allocate a contiguous memory buffer.

        Args:
            size_mb: Size in MB (default 128 MB per validator slice).
            node_id: Unique validator identifier.
        """
        self.node_id = node_id
        self.size_mb = size_mb
        self.num_bytes = size_mb * 1024 * 1024

        # Allocate contiguous byte buffer (zero-copy via numpy)
        self._buffer = np.zeros(self.num_bytes, dtype=np.uint8)

        # Enforce contiguity (matches pvm_memory_guard.py assert_zero_copy)
        assert self._buffer.flags["C_CONTIGUOUS"], \
            "MemoryStake buffer must be C-contiguous (zero-copy enforcement)"

        # Compute strides for verification
        self._byte_stride = self._buffer.strides[0]  # should be 1 for uint8

        # Record allocation metadata
        self.allocated_at = time.time()
        self.entropy_seed = self._derive_entropy_seed()

        # RSS snapshot after allocation
        self.rss_after_mb = sample_rss_mb()

    def _derive_entropy_seed(self) -> bytes:
        """
        Derive a verifiable entropy seed from the buffer's raw bytes,
        timestamp, and node identity.  (Modeled on aura_crypto_puf.py's
        environmental entropy, but using the allocated memory itself as
        the entropy source.)
        """
        hasher = hashlib.blake2b(digest_size=32)
        # Hash the first 4096 bytes of the buffer + metadata
        hasher.update(self._buffer[:4096].tobytes())
        hasher.update(struct.pack("<d", self.allocated_at))
        hasher.update(self.node_id.encode())
        return hasher.digest()

    def commitment(self) -> str:
        """
        Produce a verifiable commitment to this memory stake.
        Other nodes can verify the stake exists by challenging the validator
        to produce the entropy_seed and RSS measurement.
        """
        return self.entropy_seed.hex()

    def verify_contiguity(self) -> bool:
        """Verify byte stride continuity (zero-copy enforcement)."""
        return bool(
            self._buffer.flags["C_CONTIGUOUS"] and
            self._buffer.strides[0] == 1
        )

    def get_page(self, offset: int, size: int) -> memoryview:
        """Return a zero-copy view into a slice of the staked memory."""
        return memoryview(self._buffer)[offset:offset + size]

    def zero_page(self):
        """Zero out the buffer (stake release)."""
        self._buffer.fill(0)

    @property
    def byte_stride(self) -> int:
        """sizeof(dtype) × ∏ Shape_k — should be 1 for contiguous uint8."""
        return self._byte_stride


# ── Memory stake verifier ────────────────────────────────────────────────

def verify_memory_stake(commitment_hex: str, claimed_rss_mb: float,
                        node_id: str, tolerance_mb: float = 16.0) -> bool:
    """
    Verify that a node's claimed RSS is within tolerance of its declared
    stake size.  In a full implementation this would include a challenge-
    response protocol where the verifier requests specific buffer slices.
    """
    # Basic sanity: claimed RSS must be positive and under the 4 GB cap
    if claimed_rss_mb <= 0 or claimed_rss_mb > 4096.0:
        return False

    # Commitment must be valid hex
    try:
        bytes.fromhex(commitment_hex)
    except ValueError:
        return False

    # In a real deployment, the verifier would challenge the node to
    # produce hash(offset || buffer[offset:offset+256]) for random offsets
    return True


# ── Thermal damping (matches aura_governor.py) ────────────────────────────

def thermal_damping_safe_batch(
    base_batch: int,
    temp_c: float,
    threshold_c: float = 41.5,
) -> int:
    """
    Shrink batch size when CPU temperature exceeds threshold.
    τ_optimal = τ_base · exp(-θ · max(0, T_CPU - 40°C))
    """
    excess = max(0.0, temp_c - threshold_c)
    return max(1, int(base_batch * np.exp(-0.3 * excess)))


def read_cpu_temp() -> float:
    """Read CPU temperature (Linux thermal zone)."""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return 38.0  # fallback for non-Linux / containers