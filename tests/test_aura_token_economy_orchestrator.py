"""Tests for Aura Token Economy Orchestrator.

Tests cover:
- compute_token_economy returns all required fields
- savings_sources includes expected sources
- method is local_chars_div_4_estimate
- warning present
- estimate_cost_saved_usd returns float
- token_economy_markdown returns markdown string
- patch_authority and vsa_patch_authority invariants
"""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_token_economy_orchestrator import (
    compute_token_economy,
    compute_savings_sources,
    estimate_cost_saved_usd,
    token_economy_markdown,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)


class TestComputeTokenEconomy:
    def test_has_required_fields(self):
        result = compute_token_economy("Refactor Fireworks egress", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "raw_prompt_tokens_est" in result
        assert "raw_file_tokens_est" in result
        assert "aura_packet_tokens_est" in result
        assert "codemap_search_tokens_est" in result
        assert "read_slice_tokens_est" in result
        assert "context_crush_tokens_est" in result
        assert "st3gg_tokens_est" in result
        assert "hermes_contract_tokens_est" in result
        assert "total_aura_tokens_est" in result
        assert "estimated_tokens_saved" in result
        assert "estimated_percent_saved" in result
        assert "savings_sources" in result

    def test_method_is_local_estimate(self):
        result = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert result["method"] == "local_chars_div_4_estimate"

    def test_warning_present(self):
        result = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert "estimate" in result["warning"].lower()
        assert "not provider billing" in result["warning"].lower()

    def test_savings_sources_include_expected(self):
        result = compute_token_economy("Refactor Fireworks egress", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        sources = result["savings_sources"]
        expected_any = {"polysynthetic_packet", "codemap_localization", "read_slice", "context_crusher", "hermes_contract"}
        assert len(set(sources) & expected_any) > 0

    def test_invariants(self):
        result = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY

    def test_cost_saved_is_float(self):
        result = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        assert isinstance(result["estimated_cost_saved_usd"], (int, float))


class TestComputeSavingsSources:
    def test_returns_list(self):
        report = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        sources = compute_savings_sources(report)
        assert isinstance(sources, list)


class TestEstimateCostSaved:
    def test_returns_float(self):
        cost = estimate_cost_saved_usd(10000, "claude-sonnet-4-6")
        assert isinstance(cost, float)
        assert cost > 0

    def test_zero_tokens(self):
        cost = estimate_cost_saved_usd(0, "claude-sonnet-4-6")
        assert cost == 0.0


class TestMarkdown:
    def test_returns_markdown(self):
        report = compute_token_economy("Test", ["aura_llm_egress.py"], repo_root=REPO_ROOT)
        md = token_economy_markdown(report)
        assert "# Aura Token Economy Report" in md
        assert "Raw prompt tokens" in md
        assert "Total Aura tokens" in md
        assert "Savings Sources" in md
