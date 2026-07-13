"""Contracts for the Aura Observatory, Learning Arena Crucible, and egress order."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _trace() -> dict:
    return {
        "ok": True,
        "objective": "Inspect the intent router, preserve tests, and prepare a review-only improvement.",
        "compressed_objective": "[OP:INSPECT][TARGET:INTENT_ROUTER][OUTPUT:TEST_RESULT]",
        "likely_files": ["aura_intent_ingestion.py", "aura_fst_routing.py"],
        "likely_symbols": ["compile_intent_packet"],
        "routing_frame": {"intent": "inspect", "scope": "symbol"},
        "machine_route": {
            "rule_name": "grounded_code_route",
            "route": "HUMAN_AGENT_ARENA",
            "model": "external_worker",
            "verifier_required": True,
        },
        "six_slot_packet": {
            "slots": {
                "DIR": "PLAN_ONLY",
                "ASP": "BOUNDED",
                "CLASS": "CODE_REFACTOR",
                "SUBJ": "PYTHON_MODULE:SYMBOL",
                "VOICE": "REVIEW_ONLY",
                "STEM": "INSPECT",
            }
        },
        "grounding": {
            "target_file": "aura_intent_ingestion.py",
            "target_symbol": "compile_intent_packet",
            "source_spans": [
                {
                    "file_path": "aura_intent_ingestion.py",
                    "symbol": "compile_intent_packet",
                    "line_range": [477, 735],
                }
            ],
            "hashes": {"aura_intent_ingestion.py": "abc123"},
            "tests": ["tests/test_aura_intent_ingestion.py"],
        },
        "agent_handoff": {"compressed_context": "bounded worker packet"},
        "topology_packet": {
            "workspace": {
                "returned_node_count": 8,
                "returned_link_count": 11,
                "selected_node_ids": ["symbol:compile-intent"],
            }
        },
    }


class _Workflow:
    def __init__(self) -> None:
        self.objective = "stale civic objective"
        self.evidence = {"stale": True, "candidate_diff": "do not retain"}
        self.last_result = {"stale": True}
        self.events: list[tuple[str, str]] = []

    def execute_guarded(self, action_id: str, payload: dict) -> dict:
        assert action_id == "set_objective"
        self.objective = payload["objective"]
        self.evidence.clear()
        self.evidence["objective"] = self.objective
        return {"ok": True, "status": "ALLOWED"}

    def _event(self, kind: str, detail: str) -> None:
        self.events.append((kind, detail))

    def get_state(self) -> dict:
        return {
            "ok": True,
            "objective": self.objective,
            "evidence": dict(self.evidence),
            "evidence_keys": sorted(self.evidence),
            "current_phase": "GROUND",
            "actions": [],
            "routing": {"recommended": [], "available": [], "blocked": []},
        }


def test_observatory_handoff_is_bounded_review_only_and_clears_stale_workflow_state():
    from aura_showcase_observatory_handoff import import_observatory_trace_into_workflow

    workflow = _Workflow()
    result = import_observatory_trace_into_workflow(workflow, _trace())

    assert result["ok"] is True
    assert result["handoff"]["handoff_kind"] == "OBSERVATORY_TO_HUMAN_AGENT"
    assert result["handoff"]["topology_summary"]["full_topology_transferred"] is False
    assert result["handoff"]["production_mutation"] is False
    assert result["handoff"]["automatic_commit"] is False
    assert result["handoff"]["automatic_push"] is False
    assert result["handoff"]["automatic_merge"] is False
    assert "stale" not in workflow.evidence
    assert "candidate_diff" not in workflow.evidence
    assert workflow.evidence["observatory_trace_digest"]
    assert workflow.evidence["affected_files"] == ["aura_intent_ingestion.py", "aura_fst_routing.py"]
    assert workflow.evidence["test_targets"] == ["tests/test_aura_intent_ingestion.py"]
    assert workflow.events and workflow.events[-1][0] == "observatory_handoff"


def test_learning_intake_refuses_to_treat_raw_intention_as_verified_learning():
    from aura_showcase_observatory_handoff import build_learning_intake

    result = build_learning_intake(_trace())

    assert result["ok"] is True
    assert result["status"] == "AWAITING_VERIFIED_EXPERIENCE"
    assert result["eligible_for_crucible"] is False
    assert result["required_sequence"][:4] == [
        "HUMAN_AGENT_OR_OTHER_GOVERNED_ARENA_EXECUTION",
        "VERIFIER_EVIDENCE",
        "OUTCOME_VECTOR",
        "ARENA_EXPERIENCE_V3_RECORD",
    ]
    assert result["required_sequence"][-2:] == [
        "CRYSTALLIZATION_PROPOSED",
        "VERIFIER_AND_HUMAN_REVIEW",
    ]
    assert result["automatic_grammar_promotion"] is False
    assert result["automatic_merge"] is False


def test_learning_arena_facade_uses_real_empty_ledgers_without_fabricating_experience(tmp_path: Path):
    from aura_showcase_crucible import LearningArenaShowcase

    arena = LearningArenaShowcase(tmp_path)
    try:
        status = arena.status(intake={"ok": True, "status": "AWAITING_VERIFIED_EXPERIENCE"})
        assert status["identity"] == "LEARNING_ARENA_CRUCIBLE"
        assert status["experience_count"] == 0
        assert status["eligible_experience_count"] == 0
        assert status["recent_experiences"] == []
        assert status["dataset_split"] == ["TRAIN", "VALIDATION", "SHADOW"]
        assert status["terminal_status"] == "CRYSTALLIZATION_PROPOSED"
        assert status["required_next_gate"] == "VERIFIER_AND_HUMAN_REVIEW"
        assert status["binary_outcome_used"] is False

        run = arena.run_once(experience_limit=10)
        assert run["ok"] is True
        assert run["source_record_count"] == 0
        assert run["proposal_count"] == 0
        assert run["active_grammar_mutated"] is False
        assert run["automatic_grammar_promotion"] is False
        assert run["automatic_merge"] is False
    finally:
        arena.close()


def test_fireworks_is_primary_and_model_roles_use_official_identifiers(monkeypatch):
    import aura_llm_egress
    from aura_provider_registry import (
        DEEPSEEK_V4_FLASH,
        DEEPSEEK_V4_PRO,
        FIREWORKS_DEEPSEEK_V4_FLASH,
        FIREWORKS_GLM_5P2,
        ProviderRegistry,
    )

    registry = ProviderRegistry()
    assert registry.provider_priority[:3] == ["fireworks", "deepseek", "anthropic"]
    assert registry.providers["fireworks"]["model_priority"] == [
        FIREWORKS_GLM_5P2,
        FIREWORKS_DEEPSEEK_V4_FLASH,
    ]
    assert registry.providers["deepseek"]["model_priority"] == [DEEPSEEK_V4_FLASH, DEEPSEEK_V4_PRO]
    assert aura_llm_egress.provider_priority()[:3] == ["fireworks", "deepseek", "anthropic"]

    secrets = {
        "FIREWORKS_API_KEY": "fw-real-key",
        "DEEPSEEK_API_KEY": "ds-real-key",
        "ANTHROPIC_API_KEY": "ant-real-key",
    }
    primary = aura_llm_egress.ExternalLLM(secrets=secrets)
    assert primary.provider == "fireworks"
    assert primary.model == "accounts/fireworks/models/glm-5p2"

    budget = aura_llm_egress.ExternalLLM(model="cheap", secrets=secrets)
    assert budget.provider == "fireworks"
    assert budget.model == "accounts/fireworks/models/deepseek-v4-flash"

    direct = aura_llm_egress.ExternalLLM(secrets={"DEEPSEEK_API_KEY": "ds-real-key"})
    assert direct.provider == "deepseek"
    assert direct.model == "deepseek-v4-flash"

    direct_premium = aura_llm_egress.ExternalLLM(
        provider="deepseek",
        model="premium",
        secrets={"DEEPSEEK_API_KEY": "ds-real-key"},
    )
    assert direct_premium.model == "deepseek-v4-pro"

    monkeypatch.setenv("FIREWORKS_API_KEY", "fw-env-key")
    env_primary = aura_llm_egress.ExternalLLM(secrets={})
    assert env_primary.provider == "fireworks"


def test_browser_assets_distinguish_observatory_from_real_learning_arena():
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    crucible_js = (REPO_ROOT / "aura_showcase" / "crucible.js").read_text(encoding="utf-8")
    crucible_css = (REPO_ROOT / "aura_showcase" / "crucible.css").read_text(encoding="utf-8")
    server = (REPO_ROOT / "aura_showcase_server.py").read_text(encoding="utf-8")

    assert 'data-tab="learning">Aura Observatory' in index
    assert 'data-tab="crucible">Learning Arena / Crucible' in index
    assert 'data-surface-identity="AURA_OBSERVATORY"' in index
    assert 'src="crucible.js"' in index
    assert 'href="crucible.css"' in index
    assert "Open in Human Agent Arena" in crucible_js
    assert "Send question to Learning Arena" in crucible_js
    assert "Learn only from verified experience." in crucible_js
    assert "TRAIN · VALIDATION · SHADOW" in crucible_js
    assert "/api/showcase/observatory/handoff/human" in crucible_js
    assert "/api/showcase/observatory/handoff/learning" in crucible_js
    assert "/api/showcase/learning/run" in crucible_js
    assert ".crucible-pipeline" in crucible_css
    assert '"crucible.js"' in server
    assert '"crucible.css"' in server
    assert "automatic_grammar_promotion" in server
