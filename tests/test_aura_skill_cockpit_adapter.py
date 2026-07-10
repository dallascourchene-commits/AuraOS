"""Tests for Aura Skill Cockpit Adapter."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_skill_cockpit_adapter import (
    discover_skills_for_objective, weave_skills_for_intent,
    skillweaver_to_affordance_cards, skillweaver_to_qdkt_feedback,
    PATCH_AUTHORITY,
)


class TestSkillDiscovery:
    def test_discover(self):
        result = discover_skills_for_objective("refactor coding arena", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert isinstance(result["skills"], list)

    def test_invariants(self):
        result = discover_skills_for_objective("test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestWeaveSkills:
    def test_weave(self):
        packet = {"objective": "test", "ok": True}
        result = weave_skills_for_intent(packet, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "woven_skills" in result


class TestAffordanceCards:
    def test_convert(self):
        skills = [{"id": "skill1", "name": "Test Skill", "status": "existing"}]
        result = skillweaver_to_affordance_cards(skills, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert len(result["cards"]) == 1
        assert result["cards"][0]["patch_authority"] is False


class TestQDKTFeedback:
    def test_does_not_fail(self):
        result = skillweaver_to_qdkt_feedback([], repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "logged" in result
