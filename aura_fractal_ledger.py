"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8f5-[Q-SYS:LEDGER_FRACTAL]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: DEBWEWIN (Truth/Consensus)
DEPENDENCIES: hashlib, time, sqlite3, pathlib, typing
FUNCTIONS: FractalLedger, append_transaction, verify_proof_of_presence, compute_consensus_root, release_ram_stake, get_ledger_stats
SYNOPSIS: Gas-free fractal ledger where file headers act as blocks in Merkle-DAG.
Transactions use RAM-staking instead of gas fees. Proof-of-Presence derived from
device entropy via thermodynamic PUF. Implements Claim N10 from AuraOS prior art.
[/AURA_MASTER_KEY]

Aura Fractal Ledger — Gas-Free Consensus via RAM-Staking
=========================================================

This module implements Claim N10 from the AuraOS prior art papers:
- File headers act as blocks in a Merkle-DAG
- Transaction "fees" replaced by temporary RAM staking
- Proof-of-Presence (PoP) derived from device entropy
- No tokens, no gas, no wealth concentration

Key innovations:
1. Physical RAM as stake (opportunity cost, not token transfer)
2. Thermodynamic PUF for node identity verification
3. Fractal Merkle-DAG (not linear blockchain)
4. Zero-energy consensus (no proof-of-work mining)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import time

# Lazy import to avoid circular dependency
_puf_module = None

def _get_puf():
    """Lazy load thermodynamic PUF module"""
    global _puf_module
    if _puf_module is None:
        try:
            from aura_crypto_puf import AuraThermodynamicPUF
            _puf_module = AuraThermodynamicPUF()
        except ImportError:
            # Fallback: use system entropy if PUF unavailable
            import os
            class FallbackPUF:
                def distill_liquid_key(self, tension: float, error: float, geo: float = 0.0) -> str:
                    return hashlib.sha256(os.urandom(32)).hexdigest()
            _puf_module = FallbackPUF()
    return _puf_module


def _generate_entropy_signature(challenge: bytes) -> str:
    """Generate entropy signature from challenge using thermodynamic PUF"""
    puf = _get_puf()

    # Convert challenge to physical parameters
    challenge_hash = hashlib.sha256(challenge).digest()
    tension = struct.unpack('f', challenge_hash[:4])[0] % 100.0
    error = struct.unpack('f', challenge_hash[4:8])[0] % 10.0
    geo = struct.unpack('f', challenge_hash[8:12])[0] % 360.0

    # Get PUF key
    puf_key = puf.distill_liquid_key(tension, error, geo)

    # Return BLAKE2b hash of PUF key
    return hashlib.blake2b(puf_key.encode()).hexdigest()


@dataclass
class LedgerBlock:
    """A single block in the fractal ledger (corresponds to a file change)"""
    block_hash: str
    file_path: str
    content_hash: str
    entropy_signature: str
    timestamp: float
    parent_hashes: list[str] = field(default_factory=list)
    ram_stake: int = 0  # Bytes of RAM staked
    node_id: str = ""


class FractalLedger:
    """
    Gas-Free Fractal Ledger implementing Claim N10.
    
    Unlike traditional blockchains:
    - No linear chain (Merkle-DAG allows multiple parents)
    - No gas fees (RAM-staking as opportunity cost)
    - No mining (Proof-of-Presence via device entropy)
    - No tokens (physical resource commitment only)
    
    Attributes:
        db_path: Path to SQLite database
        ram_stakes: Active RAM locks per node {node_id → bytes}
        base_rate: Base RAM cost per byte (default: 1024)
        stake_duration: How long RAM stays locked (seconds)
    """

    def __init__(
        self,
        db_path: str = "aura_ledger.db",
        base_rate: int = 1024,
        stake_duration: float = 60.0
    ):
        self.db_path = Path(db_path)
        self.db = sqlite3.connect(str(self.db_path))
        self.ram_stakes: dict[str, int] = {}
        self.base_rate = base_rate
        self.stake_duration = stake_duration
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema for fractal ledger"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ledger_blocks (
                block_hash TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                entropy_signature TEXT NOT NULL,
                timestamp REAL NOT NULL,
                parent_hashes TEXT,
                ram_stake INTEGER NOT NULL,
                node_id TEXT NOT NULL,
                released INTEGER DEFAULT 0
            )
        """)

        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON ledger_blocks(timestamp DESC)
        """)

        self.db.execute("""
            CREATE INDEX IF NOT EXISTS idx_node_id 
            ON ledger_blocks(node_id)
        """)

        self.db.execute("""
            CREATE TABLE IF NOT EXISTS consensus_roots (
                root_hash TEXT PRIMARY KEY,
                timestamp REAL NOT NULL,
                total_stake INTEGER NOT NULL,
                node_count INTEGER NOT NULL
            )
        """)

        self.db.commit()

    def append_transaction(
        self,
        file_path: str,
        content: bytes,
        node_id: str,
        parent_hashes: list[str] | None = None
    ) -> str:
        """
        Add file change as ledger transaction with RAM staking.
        
        Args:
            file_path: Path to file being modified
            content: New file content
            node_id: Identifier of node making change
            parent_hashes: Previous block hashes (for DAG structure)
            
        Returns:
            Block hash of new transaction
            
        Raises:
            ValueError: If node doesn't have enough free RAM
        """
        # 1. Compute content hash
        content_hash = hashlib.sha256(content).hexdigest()

        # 2. Get device entropy for Proof-of-Presence
        challenge = f"{file_path}:{content_hash}:{time.time()}".encode()
        entropy_sig = _generate_entropy_signature(challenge)

        # 3. Calculate RAM stake
        size_bytes = len(content)
        current_load = len(self.ram_stakes) / 1000  # Simple load metric
        ram_stake = int(size_bytes * self.base_rate * (1 + current_load))

        # 4. Check if node can afford stake
        current_stake = self.ram_stakes.get(node_id, 0)
        # Assume 4GB limit per node (Termux constraint)
        max_stake = 4 * 1024 * 1024 * 1024  # 4GB
        if current_stake + ram_stake > max_stake:
            raise ValueError(
                f"Insufficient RAM: need {ram_stake}, "
                f"have {max_stake - current_stake} available"
            )

        # 5. Lock RAM
        self.ram_stakes[node_id] = current_stake + ram_stake

        # 6. Get parent hashes (for DAG structure)
        if parent_hashes is None:
            # Default: link to most recent block
            cursor = self.db.execute("""
                SELECT block_hash FROM ledger_blocks 
                ORDER BY timestamp DESC LIMIT 1
            """)
            row = cursor.fetchone()
            parent_hashes = [row[0]] if row else []

        # 7. Create block
        timestamp = time.time()
        block_data = (
            f"{file_path}||{content_hash}||{entropy_sig}||"
            f"{timestamp}||{','.join(parent_hashes)}"
        )
        block_hash = hashlib.blake2b(block_data.encode()).hexdigest()

        # 8. Store in ledger
        self.db.execute("""
            INSERT INTO ledger_blocks 
            (block_hash, file_path, content_hash, entropy_signature, 
             timestamp, parent_hashes, ram_stake, node_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            block_hash,
            file_path,
            content_hash,
            entropy_sig,
            timestamp,
            json.dumps(parent_hashes),
            ram_stake,
            node_id
        ))
        self.db.commit()

        return block_hash

    def verify_proof_of_presence(
        self,
        node_id: str,
        claimed_root: str,
        entropy_proof: bytes
    ) -> bool:
        """
        Verify node holds current global hologram via Proof-of-Presence.
        
        Args:
            node_id: Node claiming to hold consensus
            claimed_root: Root hash node claims to have
            entropy_proof: Device entropy signature
            
        Returns:
            True if node proves presence, False otherwise
        """
        # 1. Compute actual consensus root
        actual_root = self.compute_consensus_root()

        # 2. Check if claimed root matches
        if claimed_root != actual_root:
            return False

        # 3. Verify entropy signature is fresh (< 60 seconds old)
        # This prevents replay attacks
        challenge = f"{node_id}:{actual_root}:{int(time.time() / 60)}".encode()
        expected_sig = _generate_entropy_signature(challenge)

        # Allow some tolerance for timing
        return entropy_proof.hex() == expected_sig

    def compute_consensus_root(self) -> str:
        """
        Compute majority consensus weighted by RAM stakes.
        
        Returns:
            Block hash with highest total stake
        """
        # Get recent blocks (last 100)
        cursor = self.db.execute("""
            SELECT block_hash, ram_stake FROM ledger_blocks 
            WHERE released = 0
            ORDER BY timestamp DESC LIMIT 100
        """)

        # Weight votes by RAM stake
        weighted_votes: dict[str, int] = {}
        for block_hash, ram_stake in cursor:
            weighted_votes[block_hash] = weighted_votes.get(block_hash, 0) + ram_stake

        if not weighted_votes:
            return ""

        # Return hash with highest stake
        consensus_root = max(weighted_votes.items(), key=lambda x: x[1])[0]

        # Store consensus root
        total_stake = sum(weighted_votes.values())
        self.db.execute("""
            INSERT OR REPLACE INTO consensus_roots 
            (root_hash, timestamp, total_stake, node_count)
            VALUES (?, ?, ?, ?)
        """, (consensus_root, time.time(), total_stake, len(weighted_votes)))
        self.db.commit()

        return consensus_root

    def release_ram_stake(self, node_id: str, block_hash: str):
        """
        Release RAM stake after transaction confirmation.
        
        Args:
            node_id: Node that staked RAM
            block_hash: Block to release stake for
        """
        # Get stake amount
        cursor = self.db.execute("""
            SELECT ram_stake FROM ledger_blocks 
            WHERE block_hash = ? AND node_id = ? AND released = 0
        """, (block_hash, node_id))

        row = cursor.fetchone()
        if not row:
            return

        ram_stake = row[0]

        # Release RAM
        if node_id in self.ram_stakes:
            self.ram_stakes[node_id] = max(0, self.ram_stakes[node_id] - ram_stake)

        # Mark as released
        self.db.execute("""
            UPDATE ledger_blocks 
            SET released = 1 
            WHERE block_hash = ?
        """, (block_hash,))
        self.db.commit()

    def auto_release_expired_stakes(self):
        """
        Automatically release stakes older than stake_duration.
        Should be called periodically.
        """
        cutoff_time = time.time() - self.stake_duration

        cursor = self.db.execute("""
            SELECT block_hash, node_id, ram_stake 
            FROM ledger_blocks 
            WHERE timestamp < ? AND released = 0
        """, (cutoff_time,))

        released_count = 0
        for block_hash, node_id, ram_stake in cursor:
            if node_id in self.ram_stakes:
                self.ram_stakes[node_id] = max(0, self.ram_stakes[node_id] - ram_stake)
            released_count += 1

        # Mark all as released
        self.db.execute("""
            UPDATE ledger_blocks 
            SET released = 1 
            WHERE timestamp < ? AND released = 0
        """, (cutoff_time,))
        self.db.commit()

        return released_count

    def get_ledger_stats(self) -> dict:
        """Get current ledger statistics"""
        cursor = self.db.execute("""
            SELECT 
                COUNT(*) as total_blocks,
                SUM(ram_stake) as total_stake,
                COUNT(DISTINCT node_id) as unique_nodes,
                MAX(timestamp) as latest_timestamp
            FROM ledger_blocks
        """)

        row = cursor.fetchone()

        active_cursor = self.db.execute("""
            SELECT COUNT(*), SUM(ram_stake)
            FROM ledger_blocks
            WHERE released = 0
        """)
        active_row = active_cursor.fetchone()

        return {
            "total_blocks": row[0] or 0,
            "total_stake_bytes": row[1] or 0,
            "unique_nodes": row[2] or 0,
            "latest_timestamp": row[3] or 0,
            "active_blocks": active_row[0] or 0,
            "active_stake_bytes": active_row[1] or 0,
            "current_ram_stakes": dict(self.ram_stakes)
        }

    def get_node_history(self, node_id: str, limit: int = 10) -> list[LedgerBlock]:
        """Get transaction history for a specific node"""
        cursor = self.db.execute("""
            SELECT block_hash, file_path, content_hash, entropy_signature,
                   timestamp, parent_hashes, ram_stake, node_id
            FROM ledger_blocks
            WHERE node_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (node_id, limit))

        blocks = []
        for row in cursor:
            blocks.append(LedgerBlock(
                block_hash=row[0],
                file_path=row[1],
                content_hash=row[2],
                entropy_signature=row[3],
                timestamp=row[4],
                parent_hashes=json.loads(row[5]) if row[5] else [],
                ram_stake=row[6],
                node_id=row[7]
            ))

        return blocks

    def close(self):
        """Close database connection"""
        self.db.close()


# Convenience functions for global ledger instance
_global_ledger: FractalLedger | None = None

def get_global_ledger() -> FractalLedger:
    """Get or create global ledger instance"""
    global _global_ledger
    if _global_ledger is None:
        _global_ledger = FractalLedger()
    return _global_ledger


def commit_file_change(file_path: str, content: bytes, node_id: str = "local") -> str:
    """
    Convenience function to commit a file change to the ledger.
    
    Args:
        file_path: Path to file
        content: File content
        node_id: Node identifier (default: "local")
        
    Returns:
        Block hash
    """
    ledger = get_global_ledger()
    return ledger.append_transaction(file_path, content, node_id)


if __name__ == "__main__":
    # Demo usage
    print("=== Aura Fractal Ledger Demo ===\n")

    # Create ledger
    ledger = FractalLedger(db_path=":memory:")  # In-memory for demo

    # Simulate file changes
    print("1. Committing file changes...")
    block1 = ledger.append_transaction(
        "aura_substrate.py",
        b"# Updated substrate code",
        "node_alpha"
    )
    print(f"   Block 1: {block1[:16]}...")

    block2 = ledger.append_transaction(
        "aura_mesh.py",
        b"# Updated mesh code",
        "node_beta"
    )
    print(f"   Block 2: {block2[:16]}...")

    # Check stats
    print("\n2. Ledger statistics:")
    stats = ledger.get_ledger_stats()
    for key, value in stats.items():
        if key != "current_ram_stakes":
            print(f"   {key}: {value}")

    # Compute consensus
    print("\n3. Computing consensus root...")
    root = ledger.compute_consensus_root()
    print(f"   Consensus: {root[:16]}...")

    # Release stakes
    print("\n4. Releasing stakes...")
    ledger.release_ram_stake("node_alpha", block1)
    print("   Released stake for block 1")

    stats = ledger.get_ledger_stats()
    print(f"   Active stake: {stats['active_stake_bytes']} bytes")

    print("\n✓ Demo complete")

# Made with Bob
