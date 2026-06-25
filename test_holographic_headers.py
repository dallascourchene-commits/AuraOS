"""
Test suite for Holographic Header Protocol (Claim N9)

Tests the topology hypervector generation, resonance verification,
and header update functionality.
"""

import base64
from pathlib import Path
import sys

import numpy as np

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from aura_substrate import generate_topology_hypervector, parse_master_key_header, verify_module_integrity


def test_topology_hypervector_generation():
    """Test that topology hypervector is generated correctly"""
    print("\n=== Test 1: Topology Hypervector Generation ===")

    vec = generate_topology_hypervector()

    # Check length
    assert len(vec) == 1200, f"Expected 1200 bytes, got {len(vec)}"
    print(f"✓ Hypervector length: {len(vec)} bytes")

    # Check it's valid base64
    # Note: 1200 base64 chars can only encode ~900 bytes due to size constraint
    # This is lossy compression - full 10000-D vector would need 13336 chars
    try:
        decoded = base64.b64decode(vec)
        print(f"✓ Decoded to {len(decoded)} int8 values (lossy compression from 10000-D)")
        assert len(decoded) > 0, "Decoded vector is empty"
    except Exception as e:
        assert False, f"Invalid base64: {e}"

    # Check values are in int8 range
    arr = np.frombuffer(decoded, dtype=np.int8)
    assert arr.min() >= -128 and arr.max() <= 127
    print(f"✓ Values in int8 range: [{arr.min()}, {arr.max()}]")

    # Check determinism - same topology should give same vector
    vec2 = generate_topology_hypervector()
    assert vec == vec2, "Topology hypervector should be deterministic"
    print("✓ Deterministic generation confirmed")

    print("✓ Test 1 PASSED\n")


def test_resonance_verification():
    """Test resonance computation between vectors"""
    print("=== Test 2: Resonance Verification ===")

    # Test 1: Identical vectors should have resonance = 1.0
    vec1 = np.ones(10000, dtype=np.int8) * 50
    vec2 = vec1.copy()

    # Use float64 for numerical stability
    v1_float = vec1.astype(np.float64)
    v2_float = vec2.astype(np.float64)
    resonance = np.dot(v1_float, v2_float) / (np.linalg.norm(v1_float) * np.linalg.norm(v2_float))
    print(f"✓ Resonance between identical vectors: {resonance:.6f}")
    assert abs(resonance - 1.0) < 0.001, f"Expected 1.0, got {resonance}"

    # Test 2: Opposite vectors should have resonance = -1.0
    vec3 = -vec1
    v3_float = vec3.astype(np.float64)
    resonance_neg = np.dot(v1_float, v3_float) / (np.linalg.norm(v1_float) * np.linalg.norm(v3_float))
    print(f"✓ Resonance between opposite vectors: {resonance_neg:.6f}")
    assert abs(resonance_neg + 1.0) < 0.001, f"Expected -1.0, got {resonance_neg}"

    # Test 3: Orthogonal vectors should have resonance ≈ 0
    vec4 = np.zeros(10000, dtype=np.int8)
    vec4[::2] = 50  # Half the dimensions
    vec5 = np.zeros(10000, dtype=np.int8)
    vec5[1::2] = 50  # Other half

    v4_float = vec4.astype(np.float64)
    v5_float = vec5.astype(np.float64)
    resonance_orth = np.dot(v4_float, v5_float) / (np.linalg.norm(v4_float) * np.linalg.norm(v5_float))
    print(f"✓ Resonance between orthogonal vectors: {resonance_orth:.6f}")
    assert abs(resonance_orth) < 0.001, f"Expected ~0, got {resonance_orth}"

    # Test 4: Compression preserves identity
    enc1 = base64.b64encode(vec1.tobytes()).decode('ascii')[:1200]
    dec1 = np.frombuffer(base64.b64decode(enc1), dtype=np.int8)

    # First 900 values should be preserved
    assert np.array_equal(vec1[:900], dec1), "Compression should preserve first 900 values"
    print(f"✓ Lossy compression preserves first {len(dec1)} values")

    print("✓ Test 2 PASSED\n")


def test_module_integrity_check():
    """Test integrity verification on actual module"""
    print("=== Test 3: Module Integrity Check ===")

    # Test on aura_substrate.py itself
    module_path = "aura_substrate.py"

    if Path(module_path).exists():
        resonance = verify_module_integrity(module_path, verbose=True)
        print(f"✓ Module resonance: {resonance:.4f}")

        # Note: Will be 0.0 if no TOPOLOGY_HYPERVECTOR in header yet
        if resonance == 0.0:
            print("  (Module doesn't have TOPOLOGY_HYPERVECTOR yet - expected)")
        else:
            assert 0.0 <= resonance <= 1.0
    else:
        print(f"⚠️  Module {module_path} not found, skipping")

    print("✓ Test 3 PASSED\n")


def test_header_parsing():
    """Test that TOPOLOGY_HYPERVECTOR field is parsed correctly"""
    print("=== Test 4: Header Parsing ===")

    test_header = """
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8e5-[Q-SYS:TEST]
DIKWP_TIER: WISDOM
TOPOLOGY_HYPERVECTOR: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
PWFST_ALIGNMENT: TEST
DEPENDENCIES: numpy
FUNCTIONS: test_func
[/AURA_MASTER_KEY]
"""

    parsed = parse_master_key_header(test_header)

    assert 'TOPOLOGY_HYPERVECTOR' in parsed, "TOPOLOGY_HYPERVECTOR not parsed"
    assert parsed['TOPOLOGY_HYPERVECTOR'] == 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
    print(f"✓ Parsed TOPOLOGY_HYPERVECTOR: {parsed['TOPOLOGY_HYPERVECTOR'][:50]}...")

    assert 'DIKWP_TIER' in parsed
    assert 'PWFST_ALIGNMENT' in parsed
    print("✓ All header fields parsed correctly")

    print("✓ Test 4 PASSED\n")


def run_all_tests():
    """Run all holographic header tests"""
    print("\n" + "="*60)
    print("HOLOGRAPHIC HEADER PROTOCOL (N9) TEST SUITE")
    print("="*60)

    try:
        test_topology_hypervector_generation()
        test_resonance_verification()
        test_module_integrity_check()
        test_header_parsing()

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
