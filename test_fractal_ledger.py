"""
Test suite for Gas-Free Fractal Ledger (Claim N10)

Tests RAM-staking, Proof-of-Presence, consensus computation,
and Merkle-DAG structure.
"""

import sys
import time

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from aura_fractal_ledger import FractalLedger, LedgerBlock, commit_file_change


def test_ledger_initialization():
    """Test that ledger initializes correctly"""
    print("\n=== Test 1: Ledger Initialization ===")

    ledger = FractalLedger(db_path=":memory:")

    stats = ledger.get_ledger_stats()
    assert stats["total_blocks"] == 0
    assert stats["total_stake_bytes"] == 0
    assert stats["unique_nodes"] == 0
    print("✓ Ledger initialized with empty state")

    ledger.close()
    print("✓ Test 1 PASSED\n")


def test_transaction_append():
    """Test appending transactions with RAM staking"""
    print("=== Test 2: Transaction Append ===")

    ledger = FractalLedger(db_path=":memory:", base_rate=1024)

    # Append first transaction
    content1 = b"# Test file content v1"
    block1 = ledger.append_transaction(
        "test.py",
        content1,
        "node_alpha"
    )

    assert len(block1) == 128  # BLAKE2b produces 64-byte hash = 128 hex chars
    print(f"✓ Block 1 created: {block1[:16]}...")

    # Check RAM was staked
    assert "node_alpha" in ledger.ram_stakes
    stake1 = ledger.ram_stakes["node_alpha"]
    expected_stake = len(content1) * 1024  # base_rate * size
    assert stake1 >= expected_stake
    print(f"✓ RAM staked: {stake1} bytes (expected >= {expected_stake})")

    # Append second transaction
    content2 = b"# Test file content v2 - longer content"
    block2 = ledger.append_transaction(
        "test.py",
        content2,
        "node_alpha"
    )

    # Check cumulative stake
    stake2 = ledger.ram_stakes["node_alpha"]
    assert stake2 > stake1
    print(f"✓ Cumulative stake: {stake2} bytes")

    # Check stats
    stats = ledger.get_ledger_stats()
    assert stats["total_blocks"] == 2
    assert stats["unique_nodes"] == 1
    print(f"✓ Ledger stats: {stats['total_blocks']} blocks, {stats['unique_nodes']} nodes")

    ledger.close()
    print("✓ Test 2 PASSED\n")


def test_ram_stake_limits():
    """Test that RAM stake limits are enforced"""
    print("=== Test 3: RAM Stake Limits ===")

    ledger = FractalLedger(db_path=":memory:", base_rate=1024)

    # Try to stake more than 4GB (should fail)
    huge_content = b"X" * (5 * 1024 * 1024)  # 5MB

    try:
        # This should eventually hit the 4GB limit
        for i in range(1000):
            ledger.append_transaction(
                f"file_{i}.py",
                huge_content,
                "node_alpha"
            )
        assert False, "Should have raised ValueError for insufficient RAM"
    except ValueError as e:
        assert "Insufficient RAM" in str(e)
        print(f"✓ RAM limit enforced: {e}")

    ledger.close()
    print("✓ Test 3 PASSED\n")


def test_consensus_computation():
    """Test consensus root computation"""
    print("=== Test 4: Consensus Computation ===")

    ledger = FractalLedger(db_path=":memory:", base_rate=1024)

    # Add transactions from multiple nodes
    block1 = ledger.append_transaction(
        "file1.py",
        b"content1" * 100,  # Larger stake
        "node_alpha"
    )

    block2 = ledger.append_transaction(
        "file2.py",
        b"content2",  # Smaller stake
        "node_beta"
    )

    # Compute consensus (should favor block with higher stake)
    consensus = ledger.compute_consensus_root()

    assert consensus in [block1, block2]
    print(f"✓ Consensus root: {consensus[:16]}...")

    # Check that consensus was stored
    cursor = ledger.db.execute("""
        SELECT root_hash, total_stake, node_count
        FROM consensus_roots
        ORDER BY timestamp DESC LIMIT 1
    """)
    row = cursor.fetchone()
    assert row is not None
    assert row[0] == consensus
    print(f"✓ Consensus stored: stake={row[1]}, nodes={row[2]}")

    ledger.close()
    print("✓ Test 4 PASSED\n")


def test_stake_release():
    """Test RAM stake release"""
    print("=== Test 5: Stake Release ===")

    ledger = FractalLedger(db_path=":memory:", base_rate=1024)

    # Add transaction
    content = b"test content"
    block = ledger.append_transaction(
        "test.py",
        content,
        "node_alpha"
    )

    initial_stake = ledger.ram_stakes["node_alpha"]
    print(f"✓ Initial stake: {initial_stake} bytes")

    # Release stake
    ledger.release_ram_stake("node_alpha", block)

    final_stake = ledger.ram_stakes.get("node_alpha", 0)
    assert final_stake < initial_stake
    print(f"✓ Final stake: {final_stake} bytes")

    # Check block marked as released
    cursor = ledger.db.execute("""
        SELECT released FROM ledger_blocks WHERE block_hash = ?
    """, (block,))
    row = cursor.fetchone()
    assert row[0] == 1
    print("✓ Block marked as released")

    ledger.close()
    print("✓ Test 5 PASSED\n")


def test_auto_release():
    """Test automatic stake release after timeout"""
    print("=== Test 6: Auto Release ===")

    ledger = FractalLedger(db_path=":memory:", stake_duration=0.1)  # 100ms

    # Add transaction
    block = ledger.append_transaction(
        "test.py",
        b"content",
        "node_alpha"
    )

    initial_stake = ledger.ram_stakes["node_alpha"]
    print(f"✓ Initial stake: {initial_stake} bytes")

    # Wait for expiration
    time.sleep(0.2)

    # Auto-release expired stakes
    released_count = ledger.auto_release_expired_stakes()

    assert released_count == 1
    print(f"✓ Auto-released {released_count} stakes")

    final_stake = ledger.ram_stakes.get("node_alpha", 0)
    assert final_stake == 0
    print(f"✓ Final stake: {final_stake} bytes")

    ledger.close()
    print("✓ Test 6 PASSED\n")


def test_merkle_dag_structure():
    """Test that ledger forms a DAG (not linear chain)"""
    print("=== Test 7: Merkle-DAG Structure ===")

    ledger = FractalLedger(db_path=":memory:")

    # Create initial block
    block1 = ledger.append_transaction(
        "file1.py",
        b"content1",
        "node_alpha"
    )
    print(f"✓ Block 1: {block1[:16]}...")

    # Create two blocks with same parent (branching)
    block2a = ledger.append_transaction(
        "file2a.py",
        b"content2a",
        "node_alpha",
        parent_hashes=[block1]
    )
    print(f"✓ Block 2a: {block2a[:16]}... (parent: block1)")

    block2b = ledger.append_transaction(
        "file2b.py",
        b"content2b",
        "node_beta",
        parent_hashes=[block1]
    )
    print(f"✓ Block 2b: {block2b[:16]}... (parent: block1)")

    # Create block with multiple parents (merging)
    block3 = ledger.append_transaction(
        "file3.py",
        b"content3",
        "node_alpha",
        parent_hashes=[block2a, block2b]
    )
    print(f"✓ Block 3: {block3[:16]}... (parents: block2a, block2b)")

    # Verify DAG structure
    cursor = ledger.db.execute("""
        SELECT block_hash, parent_hashes FROM ledger_blocks
    """)

    dag_edges = 0
    for block_hash, parent_json in cursor:
        import json
        parents = json.loads(parent_json) if parent_json else []
        dag_edges += len(parents)

    print(f"✓ DAG has {dag_edges} edges (not a linear chain)")
    assert dag_edges > 3  # More edges than blocks = DAG

    ledger.close()
    print("✓ Test 7 PASSED\n")


def test_node_history():
    """Test retrieving node transaction history"""
    print("=== Test 8: Node History ===")

    ledger = FractalLedger(db_path=":memory:")

    # Add multiple transactions for same node
    for i in range(5):
        ledger.append_transaction(
            f"file{i}.py",
            f"content{i}".encode(),
            "node_alpha"
        )

    # Get history
    history = ledger.get_node_history("node_alpha", limit=3)

    assert len(history) == 3
    print(f"✓ Retrieved {len(history)} transactions")

    # Check they're in reverse chronological order
    for i in range(len(history) - 1):
        assert history[i].timestamp >= history[i+1].timestamp
    print("✓ History in reverse chronological order")

    # Check block structure
    block = history[0]
    assert isinstance(block, LedgerBlock)
    assert block.node_id == "node_alpha"
    assert len(block.block_hash) == 128
    print(f"✓ Block structure valid: {block.file_path}")

    ledger.close()
    print("✓ Test 8 PASSED\n")


def test_convenience_function():
    """Test convenience function for file commits"""
    print("=== Test 9: Convenience Function ===")

    # Use convenience function
    block = commit_file_change(
        "test.py",
        b"# Test content",
        "test_node"
    )

    assert len(block) == 128
    print(f"✓ Committed via convenience function: {block[:16]}...")

    # Check it was added to global ledger
    from aura_fractal_ledger import get_global_ledger
    ledger = get_global_ledger()
    stats = ledger.get_ledger_stats()
    assert stats["total_blocks"] > 0
    print(f"✓ Global ledger has {stats['total_blocks']} blocks")

    print("✓ Test 9 PASSED\n")


def run_all_tests():
    """Run all fractal ledger tests"""
    print("\n" + "="*60)
    print("GAS-FREE FRACTAL LEDGER (N10) TEST SUITE")
    print("="*60)

    try:
        test_ledger_initialization()
        test_transaction_append()
        test_ram_stake_limits()
        test_consensus_computation()
        test_stake_release()
        test_auto_release()
        test_merkle_dag_structure()
        test_node_history()
        test_convenience_function()

        print("="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60 + "\n")
        return True

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

# Made with Bob
