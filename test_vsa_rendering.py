#!/usr/bin/env python3
"""
Test suite for Aura VSA-Addressed Decoupled Rendering (N12)
"""

import hashlib

import numpy as np

from aura_vsa_rendering import (
    AssetProperties,
    DecoupledRenderProtocol,
    Pose6DOF,
    RenderClient,
    VSAAssetAddressGenerator,
    VSARenderingBenchmark,
)


def test_address_generation():
    """Test VSA address generation from asset properties"""
    print("[TEST] VSA address generation...", end=" ")

    addr_gen = VSAAssetAddressGenerator(dimensions=10000)

    props = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="a" * 64,
        lod_level=2,
        semantic_tags=["tree", "oak"]
    )

    address = addr_gen.generate_address(props)

    # Check dimensions
    assert address.shape == (10000,), f"Expected 10000 dimensions, got {address.shape}"

    # Check normalization
    norm = np.linalg.norm(address)
    assert abs(norm - 1.0) < 1e-6, f"Address not normalized: {norm}"

    # Check determinism (same props → same address)
    address2 = addr_gen.generate_address(props)
    similarity = np.abs(np.vdot(address, address2))
    assert similarity > 0.99, f"Address generation not deterministic: {similarity}"

    print("[PASS]")


def test_address_similarity():
    """Test similarity computation between addresses"""
    print("[TEST] Address similarity computation...", end=" ")

    addr_gen = VSAAssetAddressGenerator(dimensions=10000)

    # Similar assets (same type, different content)
    props1 = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="a" * 64,
        lod_level=2,
        semantic_tags=["tree", "oak"]
    )
    props2 = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="b" * 64,
        lod_level=2,
        semantic_tags=["tree", "pine"]
    )

    addr1 = addr_gen.generate_address(props1)
    addr2 = addr_gen.generate_address(props2)

    similarity = addr_gen.compute_similarity(addr1, addr2)

    # Should have some similarity (same type, geohash, LOD)
    assert 0.0 <= similarity <= 1.0, f"Invalid similarity: {similarity}"

    # Different assets (different type)
    props3 = AssetProperties(
        asset_type="texture",
        geohash="9q8yz",
        content_hash="c" * 64,
        lod_level=5,
        semantic_tags=["rock"]
    )
    addr3 = addr_gen.generate_address(props3)

    similarity_diff = addr_gen.compute_similarity(addr1, addr3)

    # Should be less similar
    assert similarity_diff < similarity, "Different asset types should be less similar"

    print("[PASS]")


def test_decoupled_protocol():
    """Test decoupled rendering protocol"""
    print("[TEST] Decoupled rendering protocol...", end=" ")

    protocol = DecoupledRenderProtocol()
    addr_gen = VSAAssetAddressGenerator()

    # Add objects
    props = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="a" * 64,
        lod_level=2,
        semantic_tags=["tree"]
    )
    address = addr_gen.generate_address(props)
    pose = Pose6DOF(position=(10.0, 0.0, 5.0), rotation=(1.0, 0.0, 0.0, 0.0))

    protocol.add_object("obj_001", address, pose)

    assert len(protocol.world_state) == 1, "Object not added"
    assert "obj_001" in protocol.world_state, "Object ID not found"

    # Update pose
    new_pose = Pose6DOF(position=(15.0, 0.0, 5.0), rotation=(1.0, 0.0, 0.0, 0.0))
    protocol.update_pose("obj_001", new_pose)

    assert protocol.world_state["obj_001"].pose.position == (15.0, 0.0, 5.0), "Pose not updated"

    print("[PASS]")


def test_frame_transmission():
    """Test frame transmission size"""
    print("[TEST] Frame transmission...", end=" ")

    protocol = DecoupledRenderProtocol()
    addr_gen = VSAAssetAddressGenerator()

    # Add multiple objects
    for i in range(10):
        props = AssetProperties(
            asset_type="mesh",
            geohash=f"9q8y{i}",
            content_hash=f"{i}" * 64,
            lod_level=2,
            semantic_tags=["object"]
        )
        address = addr_gen.generate_address(props)
        pose = Pose6DOF(position=(float(i), 0.0, 0.0), rotation=(1.0, 0.0, 0.0, 0.0))
        protocol.add_object(f"obj_{i:03d}", address, pose)

    # Transmit frame
    frame_data = protocol.transmit_frame()
    frame_size = protocol.get_frame_size()

    # Check size (80 bytes per object)
    expected_size = 10 * 80
    assert frame_size == expected_size, f"Expected {expected_size} bytes, got {frame_size}"
    assert len(frame_data) == expected_size, "Frame data size mismatch"

    print("[PASS]")


def test_render_client():
    """Test render client address resolution"""
    print("[TEST] Render client address resolution...", end=" ")

    client = RenderClient()
    addr_gen = VSAAssetAddressGenerator()

    # Register assets
    props = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="a" * 64,
        lod_level=2,
        semantic_tags=["tree"]
    )
    address = addr_gen.generate_address(props)

    client.register_asset(address, "gpu_mesh_001")

    # Resolve address
    addr_hash = hashlib.sha256(address.tobytes()).digest()
    gpu_resource = client.resolve_address(addr_hash)

    assert gpu_resource == "gpu_mesh_001", f"Expected gpu_mesh_001, got {gpu_resource}"

    # Check cache stats
    stats = client.get_cache_stats()
    assert stats['hit_rate'] == 1.0, "Cache hit rate should be 100%"

    # Test cache miss
    fake_hash = hashlib.sha256(b"fake").digest()
    result = client.resolve_address(fake_hash)
    assert result is None, "Should return None for unknown address"

    stats = client.get_cache_stats()
    assert stats['hit_rate'] == 0.5, "Cache hit rate should be 50%"

    print("[PASS]")


def test_foveated_rendering():
    """Test foveated rendering LOD computation"""
    print("[TEST] Foveated rendering LOD...", end=" ")

    client = RenderClient()

    # Set fovea center
    client.set_fovea_center(0.5, 0.5)

    # Test LOD at center (should be highest detail)
    lod_center = client.compute_lod_from_attention((0.5, 0.5))
    assert lod_center == 0, f"Expected LOD 0 at center, got {lod_center}"

    # Test LOD at periphery (should be lower detail)
    lod_periphery = client.compute_lod_from_attention((0.0, 0.0))
    assert lod_periphery > lod_center, "Periphery should have lower detail"
    assert 0 <= lod_periphery <= 7, f"LOD out of range: {lod_periphery}"

    # Test without fovea set
    client2 = RenderClient()
    lod_default = client2.compute_lod_from_attention((0.5, 0.5))
    assert lod_default == 3, "Default LOD should be 3"

    print("[PASS]")


def test_bandwidth_comparison():
    """Test bandwidth comparison"""
    print("[TEST] Bandwidth comparison...", end=" ")

    stats = VSARenderingBenchmark.compare_bandwidth(100)

    # Check keys
    assert 'traditional_kb' in stats, "Missing traditional_kb"
    assert 'vsa_kb' in stats, "Missing vsa_kb"
    assert 'reduction_percent' in stats, "Missing reduction_percent"
    assert 'speedup_factor' in stats, "Missing speedup_factor"

    # Check values
    assert stats['traditional_kb'] > stats['vsa_kb'], "VSA should use less bandwidth"
    assert stats['reduction_percent'] > 90, "Should have >90% reduction"
    assert stats['speedup_factor'] > 100, "Should have >100x speedup"

    print("[PASS]")


def test_integration_with_substrate():
    """Test integration with existing substrate"""
    print("[TEST] Integration with substrate...", end=" ")

    # Test that VSA rendering can use substrate's hypervector operations
    addr_gen = VSAAssetAddressGenerator(dimensions=10000)

    props = AssetProperties(
        asset_type="mesh",
        geohash="9q8yy",
        content_hash="a" * 64,
        lod_level=2,
        semantic_tags=["tree"]
    )

    address = addr_gen.generate_address(props)

    # Verify address is compatible with substrate operations
    assert isinstance(address, np.ndarray), "Address should be numpy array"
    assert address.dtype == np.complex128, "Address should be complex128"
    assert address.shape == (10000,), "Address should be 10000-D"

    print("[PASS]")


if __name__ == "__main__":
    print("=== Aura VSA Rendering Test Suite ===\n")

    try:
        test_address_generation()
        test_address_similarity()
        test_decoupled_protocol()
        test_frame_transmission()
        test_render_client()
        test_foveated_rendering()
        test_bandwidth_comparison()
        test_integration_with_substrate()

        print("\n" + "="*50)
        print("All tests passed!")
        print("="*50)

    except AssertionError as e:
        print(f"[FAIL] {e}")
        exit(1)
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        exit(1)

# Made with Bob
