"""Tests for Aura Ephemeral FST — product automaton."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_ephemeral_fst import (
    EphemeralRoutingFrame, evaluate_ephemeral_product_automaton,
    compile_ephemeral_route, explain_ephemeral_denial,
    MVP_ALLOWED_EFFECTS, MVP_BLOCKED_EFFECTS, MVP_BLOCKED_TARGETS,
)


class TestLEXCRoute:
    def test_complete_route(self):
        result = compile_ephemeral_route(
            ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"],
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is True

    def test_incomplete_route_rejected(self):
        result = compile_ephemeral_route(["CREATE", "TTL"], repo_root=REPO_ROOT)
        assert result["ok"] is False


class TestProductAutomaton:
    def test_read_only_allowed(self):
        frame = EphemeralRoutingFrame(effect="READ", target="CODEMAP", grounding="codemap_exists")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"],
            frame, granted_capabilities=["search_code", "resolve_capabilities"],
            repo_root=REPO_ROOT,
        )
        assert result.allowed is True

    def test_network_blocked(self):
        frame = EphemeralRoutingFrame(effect="NETWORK", target="EXTERNAL_ENDPOINT")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "NETWORK", "EXTERNAL_ENDPOINT", "HUMAN_REQUESTED", "QUERY"],
            frame, repo_root=REPO_ROOT,
        )
        assert result.allowed is False
        assert "NETWORK" in " ".join(result.denial_reasons)

    def test_install_blocked(self):
        frame = EphemeralRoutingFrame(effect="INSTALL", target="TEMP_WORKSPACE")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "INSTALL", "TEMP_WORKSPACE", "HUMAN_REQUESTED", "QUERY"],
            frame, repo_root=REPO_ROOT,
        )
        assert result.allowed is False

    def test_secret_access_blocked(self):
        frame = EphemeralRoutingFrame(effect="SECRET_ACCESS", target="PRIVATE_MEMORY")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "SECRET_ACCESS", "PRIVATE_MEMORY", "HUMAN_REQUESTED", "QUERY"],
            frame, repo_root=REPO_ROOT,
        )
        assert result.allowed is False

    def test_production_mutation_blocked(self):
        frame = EphemeralRoutingFrame(effect="PRODUCTION_MUTATION", target="PRODUCTION_SOURCE")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "PRODUCTION_MUTATION", "PRODUCTION_SOURCE", "HUMAN_REQUESTED", "QUERY"],
            frame, repo_root=REPO_ROOT,
        )
        assert result.allowed is False

    def test_unknown_symbol_rejected(self):
        result = compile_ephemeral_route(
            ["UNKNOWN", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "QUERY"],
            repo_root=REPO_ROOT,
        )
        assert result["ok"] is False

    def test_incomplete_route_rejected(self):
        result = compile_ephemeral_route(["CREATE"], repo_root=REPO_ROOT)
        assert result["ok"] is False

    def test_ttl_expired_denied(self):
        frame = EphemeralRoutingFrame(effect="READ", target="CODEMAP", ttl=0)
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"],
            frame, repo_root=REPO_ROOT,
        )
        assert result.allowed is False
        assert any("TTL" in r for r in result.denial_reasons)

    def test_fst_cannot_grant_missing_capability(self):
        frame = EphemeralRoutingFrame(effect="WRITE_TEMP", target="TEMP_WORKSPACE")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "WRITE_TEMP", "TEMP_WORKSPACE", "HUMAN_REQUESTED", "QUERY"],
            frame, granted_capabilities=[],  # No write_temp_audit in lease
            repo_root=REPO_ROOT,
        )
        assert result.allowed is False
        assert any("Lease" in r for r in result.denial_reasons)

    def test_denial_explanation(self):
        frame = EphemeralRoutingFrame(effect="NETWORK", target="EXTERNAL_ENDPOINT")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "NETWORK", "EXTERNAL_ENDPOINT", "HUMAN_REQUESTED", "QUERY"],
            frame, repo_root=REPO_ROOT,
        )
        explanation = explain_ephemeral_denial(result)
        assert "DENIED" in explanation

    def test_invariants(self):
        frame = EphemeralRoutingFrame(effect="READ", target="CODEMAP")
        result = evaluate_ephemeral_product_automaton(
            ["CREATE", "TTL", "READ", "CODEMAP", "HUMAN_REQUESTED", "RESOLVE_CAPABILITIES"],
            frame, repo_root=REPO_ROOT,
        )
        d = result.to_dict()
        assert d["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert d["vsa_patch_authority"] is False
