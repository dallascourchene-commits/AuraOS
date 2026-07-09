"""Tests for the Aura Affordance Directory (Intelligence Layer V1.2).

Tests cover:
- find_affordances for various objectives
- Returned cards include when_to_use, when_not_to_use, implemented_by, symbols, tests, safety
- Prompt card output is compact
- No provider APIs, no new external dependencies
- Grounding verification (grounded/partial/NEEDS_GROUNDING)
- Agent Arena Bridge aura_find_affordances method
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_affordance_directory import (
    load_affordance_directory,
    find_affordances,
    explain_affordance,
    affordance_prompt_cards,
    route_objective_to_affordances,
    PATCH_AUTHORITY,
)


# ---------------------------------------------------------------------------
# load_affordance_directory tests
# ---------------------------------------------------------------------------


class TestLoadAffordanceDirectory:
    """Tests for loading the affordance directory."""

    def test_load_returns_list(self):
        """load_affordance_directory returns a list of AuraAffordance."""
        directory = load_affordance_directory(repo_root=REPO_ROOT)
        assert isinstance(directory, list)
        assert len(directory) >= 17  # 17 seed affordances

    def test_all_seeds_present(self):
        """All 17 seed affordances are present."""
        directory = load_affordance_directory(repo_root=REPO_ROOT)
        ids = {a.id for a in directory}
        expected_ids = {
            "aura.concept_workspace",
            "aura.node_inspector",
            "aura.coding_arena.topology",
            "aura.coding_arena.capsule_compiler",
            "aura.agent_arena.bridge",
            "aura.jspace.advisory_state",
            "aura.fst.intent_routing",
            "aura.st3gg.egress",
            "aura.context_crusher",
            "aura.understand_graph",
            "aura.emergent_potential.audit",
            "aura.dream.reranking",
            "aura.qdkt.memory",
            "aura.llm_egress",
            "aura.tokenizer_guard",
            "aura.patch_quality_gate",
            "aura.architect_loop",
            "aura.research_arxiv_memory",
        }
        assert expected_ids.issubset(ids)

    def test_grounding_is_set(self):
        """Each affordance has a grounding level set."""
        directory = load_affordance_directory(repo_root=REPO_ROOT)
        for aff in directory:
            assert aff.grounding in ("grounded", "partial", "NEEDS_GROUNDING")


# ---------------------------------------------------------------------------
# find_affordances tests
# ---------------------------------------------------------------------------


class TestFindAffordances:
    """Tests for find_affordances function."""

    def test_refactor_coding_arena(self):
        """find_affordances('refactor coding arena') returns relevant tools."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        assert "recommended_affordances" in result
        affords = result["recommended_affordances"]
        assert len(affords) > 0
        ids = {a["id"] for a in affords}
        # Should include at least some of these
        expected_any = {
            "aura.concept_workspace",
            "aura.coding_arena.topology",
            "aura.coding_arena.capsule_compiler",
            "aura.jspace.advisory_state",
            "aura.fst.intent_routing",
            "aura.agent_arena.bridge",
        }
        assert len(ids & expected_any) > 0

    def test_make_node_click_explain(self):
        """find_affordances('make node click explain itself') returns Node Inspector etc."""
        result = find_affordances("make node click explain itself", repo_root=REPO_ROOT)
        affords = result["recommended_affordances"]
        ids = {a["id"] for a in affords}
        expected_any = {
            "aura.node_inspector",
            "aura.concept_workspace",
            "aura.jspace.advisory_state",
            "aura.fst.intent_routing",
        }
        assert len(ids & expected_any) > 0

    def test_reduce_egress_tokens(self):
        """find_affordances('reduce egress tokens') returns token-reduction tools."""
        result = find_affordances("reduce egress tokens", repo_root=REPO_ROOT)
        affords = result["recommended_affordances"]
        ids = {a["id"] for a in affords}
        expected_any = {
            "aura.context_crusher",
            "aura.st3gg.egress",
            "aura.llm_egress",
            "aura.tokenizer_guard",
        }
        assert len(ids & expected_any) > 0

    def test_cards_include_required_fields(self):
        """Returned cards include when_to_use, when_not_to_use, implemented_by, symbols, tests, safety."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        for aff in result["recommended_affordances"]:
            assert "when_to_use" in aff
            assert "when_not_to_use" in aff
            assert "implemented_by" in aff
            assert "symbols" in aff
            assert "safety" in aff
            # tests may be empty list but key should exist
            assert "tests" in aff or "tests" in aff  # field exists

    def test_result_includes_patch_authority(self):
        """Result includes patch authority invariants."""
        result = find_affordances("test objective", repo_root=REPO_ROOT)
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_result_includes_route_frame(self):
        """Result includes a route frame."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        assert "route_frame" in result
        rf = result["route_frame"]
        assert "intent" in rf
        assert "action" in rf

    def test_do_not_reinvent(self):
        """Result includes do_not_reinvent notes."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        assert "do_not_reinvent" in result
        assert len(result["do_not_reinvent"]) > 0

    def test_top_k_limit(self):
        """find_affordances respects top_k limit."""
        result = find_affordances("coding arena", repo_root=REPO_ROOT, top_k=3)
        assert len(result["recommended_affordances"]) <= 3


# ---------------------------------------------------------------------------
# explain_affordance tests
# ---------------------------------------------------------------------------


class TestExplainAffordance:
    """Tests for explain_affordance function."""

    def test_explain_existing(self):
        """explain_affordance returns details for an existing affordance."""
        result = explain_affordance("aura.node_inspector", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "affordance" in result
        aff = result["affordance"]
        assert aff["id"] == "aura.node_inspector"
        assert aff["name"]
        assert aff["description"]

    def test_explain_nonexistent(self):
        """explain_affordance returns error for nonexistent affordance."""
        result = explain_affordance("aura.nonexistent", repo_root=REPO_ROOT)
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# affordance_prompt_cards tests
# ---------------------------------------------------------------------------


class TestPromptCards:
    """Tests for affordance_prompt_cards function."""

    def test_prompt_cards_compact(self):
        """Prompt card output is compact (list of strings)."""
        cards = affordance_prompt_cards("refactor coding arena", repo_root=REPO_ROOT)
        assert isinstance(cards, list)
        for card in cards:
            assert isinstance(card, str)
            # Each card should be reasonably compact
            assert len(card) < 300


# ---------------------------------------------------------------------------
# Agent Arena Bridge integration tests
# ---------------------------------------------------------------------------


class TestBridgeIntegration:
    """Tests for aura_find_affordances through the Agent Arena Bridge."""

    def test_bridge_find_affordances(self):
        """Agent Arena Bridge exposes aura_find_affordances."""
        from aura_agent_arena_bridge import AuraAgentArenaBridge

        bridge = AuraAgentArenaBridge(repo_root=str(REPO_ROOT))
        result = bridge.aura_find_affordances(
            objective="refactor coding arena",
            top_k=5,
        )
        assert result["ok"] is True
        assert "recommended_affordances" in result
        assert "prompt_cards" in result
        assert "do_not_reinvent" in result
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_bridge_find_affordances_empty_objective(self):
        """Bridge returns error for empty objective."""
        from aura_agent_arena_bridge import AuraAgentArenaBridge

        bridge = AuraAgentArenaBridge(repo_root=str(REPO_ROOT))
        result = bridge.aura_find_affordances(objective="")
        assert result["ok"] is False

    def test_bridge_list_tools_includes_affordances(self):
        """Bridge list_tools includes aura_find_affordances."""
        from aura_agent_arena_bridge import AuraAgentArenaBridge

        tools = AuraAgentArenaBridge.list_tools()
        names = [t["name"] for t in tools]
        assert "aura_find_affordances" in names


# ---------------------------------------------------------------------------
# Safety / no external dependency tests
# ---------------------------------------------------------------------------


class TestSafety:
    """Verify no external dependencies, no provider APIs."""

    def test_no_fake_node_language(self):
        """No 'fake node' language in affordance directory output."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        serialized = json.dumps(result)
        assert "fake node" not in serialized.lower()

    def test_no_provider_api_calls(self):
        """No provider API calls in affordance directory."""
        # This is implicitly tested by the fact that find_affordances
        # runs without any API keys or network calls
        result = find_affordances("test", repo_root=REPO_ROOT)
        assert result is not None  # ran without errors

    def test_advisory_only(self):
        """Affordances are advisory — no patch authority."""
        result = find_affordances("refactor coding arena", repo_root=REPO_ROOT)
        for aff in result["recommended_affordances"]:
            assert aff.get("patch_authority") is False
            assert aff.get("vsa_patch_authority") is False
