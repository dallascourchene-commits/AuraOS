"""Tests for Aura Capability Connectome.

Tests cover:
- build_capability_connectome includes 18 nodes
- connectome includes Context Crusher, ST3GG, QDKT, DREAM-lite, AI Router, Agent Arena Bridge
- find_capability_path returns recommended capabilities
- explain_capability returns capability details
- token_savings_for_capability returns role
- future_potentials_for_capability returns list
- capability_graph_packet returns compact packet
- patch_authority and vsa_patch_authority invariants
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_capability_connectome import (
    build_capability_connectome,
    find_capability_path,
    explain_capability,
    future_potentials_for_capability,
    token_savings_for_capability,
    capability_graph_packet,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)


class TestBuildConnectome:
    def test_has_18_nodes(self):
        result = build_capability_connectome(repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["node_count"] >= 18

    def test_includes_key_capabilities(self):
        result = build_capability_connectome(repo_root=REPO_ROOT)
        node_ids = {n["id"] for n in result["nodes"]}
        expected = {
            "aura.context_crusher",
            "aura.st3gg.egress",
            "aura.qdkt.memory",
            "aura.dream.reranking",
            "aura.agent_arena.bridge",
        }
        assert expected.issubset(node_ids), f"Missing: {expected - node_ids}"

    def test_has_edges(self):
        result = build_capability_connectome(repo_root=REPO_ROOT)
        assert result["edge_count"] > 0

    def test_invariants(self):
        result = build_capability_connectome(repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


class TestFindCapabilityPath:
    def test_returns_recommended(self):
        result = find_capability_path("refactor coding arena", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["path"]) > 0
        assert "recommended_capabilities" in result
        assert "token_savings_roles" in result

    def test_invariants(self):
        result = find_capability_path("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestExplainCapability:
    def test_explain_existing(self):
        result = explain_capability("aura.context_crusher", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "capability" in result
        cap = result["capability"]
        assert cap["id"] == "aura.context_crusher"
        assert "token_savings_role" in cap
        assert "truth_boundary" in cap

    def test_explain_nonexistent(self):
        result = explain_capability("nonexistent.capability", repo_root=REPO_ROOT)
        assert result["ok"] is False

    def test_invariants(self):
        result = explain_capability("aura.context_crusher", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestFuturePotentials:
    def test_returns_list(self):
        result = future_potentials_for_capability("aura.fst.intent_routing", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert isinstance(result["future_potentials"], list)
        assert len(result["future_potentials"]) > 0

    def test_invariants(self):
        result = future_potentials_for_capability("aura.context_crusher", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestTokenSavingsRole:
    def test_returns_role(self):
        result = token_savings_for_capability("aura.context_crusher", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["token_savings_role"] in (
            "compression", "localization", "routing", "verification",
            "grounding", "safety", "advisory", "context_reduction",
        )

    def test_invariants(self):
        result = token_savings_for_capability("aura.context_crusher", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestGraphPacket:
    def test_compact_packet(self):
        result = capability_graph_packet(repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["nodes_count"] >= 18
        assert "capabilities" in result

    def test_invariants(self):
        result = capability_graph_packet(repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
