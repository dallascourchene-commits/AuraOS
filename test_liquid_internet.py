"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa8fe-[Q-SYS:LIP_TEST]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / LIP Verification)
DEPENDENCIES: pytest, numpy, aura_liquid_internet
SYNOPSIS: Tests for Claim N14 - VSA-Addressed Liquid Internet Protocol.
[/AURA_MASTER_KEY]
"""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aura_liquid_internet import (
    LiquidInternetProtocol,
    VSAAddress,
    _bind,
    _bundle,
    _cosine_res,
    _dequantize_address,
    _quantize_address,
    _seeded_phasor,
)


class TestVSAAddress:
    def test_deterministic(self):
        a = VSAAddress.from_properties({"id": "x"})
        b = VSAAddress.from_properties({"id": "x"})
        assert np.allclose(a.phasor, b.phasor)

    def test_different_props_different_address(self):
        a = VSAAddress.from_properties({"id": "alpha"})
        b = VSAAddress.from_properties({"id": "beta"})
        res = a.resonance_with(b)
        assert res < 0.9  # Different entities

    def test_self_resonance_is_one(self):
        a = VSAAddress.from_properties({"id": "test", "type": "node"})
        assert a.resonance_with(a) > 0.99

    def test_quantized_size(self):
        a = VSAAddress.from_properties({"id": "x"})
        assert len(a.quantized) == 1200

    def test_from_label(self):
        a = VSAAddress.from_label("my_node")
        assert a.phasor.shape == (10000,)

class TestResonanceRouting:
    def test_route_finds_best_match(self):
        lip = LiquidInternetProtocol()
        lip.register_peer("10.0.0.1", label="compute",
            properties={"type": "compute", "role": "worker"})
        lip.register_peer("10.0.0.2", label="storage",
            properties={"type": "storage", "role": "archive"})

        dest = VSAAddress.from_properties({"type": "compute", "role": "worker"})
        peer, report = lip.route(dest)
        assert peer is not None
        assert report["decision"] == "ROUTE"
        assert peer.label == "compute"

    def test_route_no_peers(self):
        lip = LiquidInternetProtocol()
        dest = VSAAddress.from_label("anything")
        peer, report = lip.route(dest)
        assert peer is None
        assert report["decision"] == "NO_PEERS"

    def test_routing_table_size_always_zero(self):
        lip = LiquidInternetProtocol()
        lip.register_peer("1.1.1.1", label="a")
        lip.register_peer("2.2.2.2", label="b")
        assert lip.get_routing_table_size() == 0

    def test_hop_bound(self):
        lip = LiquidInternetProtocol()
        peer = lip.register_peer("10.0.0.1", label="far",
            properties={"type": "node"})
        peer_rec = next(iter(lip._peers.values()))
        peer_rec.hop_count = 99
        dest = VSAAddress.from_properties({"type": "node"})
        result_peer, report = lip.route(dest, max_hops=3)
        # Should not route to peer beyond max_hops
        assert result_peer is None or report.get("decision") == "NO_ROUTE"

class TestDecentralizedNaming:
    def test_publish_and_resolve(self):
        lip = LiquidInternetProtocol()
        addr = VSAAddress.from_label("my_service")
        lip.publish_name("my_service", addr)
        resolved = lip.resolve_name("my_service")
        assert resolved is not None
        assert resolved.resonance_with(addr) > 0.99

    def test_resolve_unknown_name(self):
        lip = LiquidInternetProtocol()
        assert lip.resolve_name("nonexistent") is None

    def test_route_by_name(self):
        lip = LiquidInternetProtocol()
        addr = VSAAddress.from_properties({"type": "compute"})
        lip.publish_name("compute_node", addr)
        lip.register_peer("10.0.0.1", label="c",
            properties={"type": "compute"})
        _peer, report = lip.route_by_name("compute_node")
        # Should resolve the name and then route
        assert report["decision"] in ("ROUTE", "NO_ROUTE")

    def test_list_names(self):
        lip = LiquidInternetProtocol()
        lip.publish_name("svc_a", VSAAddress.from_label("a"))
        lip.publish_name("svc_b", VSAAddress.from_label("b"))
        names = lip.list_names()
        assert len(names) == 2

class TestMeshIntegration:
    def test_import_mesh_peers(self):
        lip = LiquidInternetProtocol()
        mesh_peers = {"10.0.0.1": "node_a", "10.0.0.2": "node_b"}
        count = lip.import_mesh_peers(mesh_peers)
        assert count == 2
        assert lip.peer_count == 2

class TestPhasorOps:
    def test_bind_invertible(self):
        a = _seeded_phasor("hello")
        b = _seeded_phasor("world")
        bound = _bind(a, b)
        unbound = _bind(bound, np.conj(b))
        res = _cosine_res(a, unbound)
        assert res > 0.95  # Should recover a

    def test_bundle_preserves_similarity(self):
        a = _seeded_phasor("alpha")
        b = _seeded_phasor("beta")
        bundled = _bundle(a, b)
        # Bundled should have some resonance with both components
        res_a = _cosine_res(bundled, a)
        res_b = _cosine_res(bundled, b)
        assert res_a > 0.3
        assert res_b > 0.3

    def test_quantize_roundtrip(self):
        p = _seeded_phasor("test")
        q = _quantize_address(p)
        assert len(q) == 1200
        dq = _dequantize_address(q)
        assert dq.shape == (10000,)

class TestNoDeps:
    def test_only_stdlib_and_numpy(self):
        fp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "aura_liquid_internet.py")
        with open(fp, encoding="utf-8") as f:
            source = f.read()
        import ast
        tree = ast.parse(source)
        allowed = {"__future__", "asyncio", "hashlib", "json", "os",
                    "time", "dataclasses", "typing", "numpy", "np"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] in allowed
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] in allowed

class TestReport:
    def test_format_report(self):
        lip = LiquidInternetProtocol()
        lip.register_peer("1.2.3.4", label="test")
        report = lip.format_report()
        assert "[LIQUID_INTERNET_PROTOCOL]" in report
        assert "ROUTING_TABLE_SIZE: 0" in report

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
