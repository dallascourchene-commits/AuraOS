"""Tests for Aura Research Cockpit Adapter."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_research_cockpit_adapter import (
    research_manifest_search, paper_memory_recall, arxiv_forager_plan,
    research_to_cockpit_evidence_packet, research_to_agent_context_capsule,
    PATCH_AUTHORITY,
)


class TestResearchManifest:
    def test_offline_search(self):
        result = research_manifest_search("agentless", repo_root=REPO_ROOT, offline=True)
        assert result["ok"] is True
        assert result["offline"] is True
        assert isinstance(result["papers"], list)

    def test_invariants(self):
        result = research_manifest_search("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is False


class TestPaperMemory:
    def test_recall(self):
        result = paper_memory_recall("test", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert isinstance(result["recalled_papers"], list)


class TestEvidencePacket:
    def test_advisory_only(self):
        search = research_manifest_search("test", repo_root=REPO_ROOT)
        result = research_to_cockpit_evidence_packet(search, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["advisory_only"] is True
        assert "advisory" in result["note"].lower()

    def test_has_token_estimates(self):
        search = research_manifest_search("test", repo_root=REPO_ROOT)
        result = research_to_cockpit_evidence_packet(search, repo_root=REPO_ROOT)
        ep = result["evidence_packet"]
        assert "raw_paper_tokens" in ep
        assert "compressed_evidence_tokens" in ep


class TestContextCapsule:
    def test_produces_capsule(self):
        search = research_manifest_search("test", repo_root=REPO_ROOT)
        result = research_to_agent_context_capsule(search, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "context_capsule" in result
