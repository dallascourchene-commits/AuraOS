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
    def __init__(
        self,
        repo_root: Path | None = None,
        *,
        admit: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else REPO_ROOT
        self.workflow_id = "HWF-OBSERVATORY-TEST"
        self.objective = "stale civic objective"
        self.evidence = {"stale": True, "candidate_diff": "do not retain"}
        self.last_result = {"stale": True}
        self.events: list[tuple[str, str]] = [("prior", "keep")]
        self.admit = admit

    def execute_guarded(self, action_id: str, payload: dict) -> dict:
        assert action_id == "set_objective"
        if not self.admit:
            self.objective = "mutated-before-denial"
            self.evidence["denied_mutation"] = True
            self.events.append(("denied", "temporary"))
            return {"ok": False, "status": "DENIED"}
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


def test_observatory_handoff_is_bounded_review_only_and_clears_stale_workflow_state(
    tmp_path: Path,
):
    from aura_empirical_cost_ledger import EmpiricalCostLedger
    from aura_showcase_observatory_handoff import (
        import_observatory_trace_into_workflow,
    )

    workflow = _Workflow(tmp_path)
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
    assert workflow.evidence["affected_files"] == [
        "aura_intent_ingestion.py",
        "aura_fst_routing.py",
    ]
    assert workflow.evidence["test_targets"] == [
        "tests/test_aura_intent_ingestion.py"
    ]

    compiled = result["phase_capsule_compilation"]
    assert compiled["ok"] is True
    assert compiled["grounding_evidence_id"].startswith("GPE-")
    assert len(compiled["phase_capsules"]) == 9
    assert compiled["grounding_evidence"]["allowed_files"] == [
        "aura_intent_ingestion.py"
    ]
    assert "aura_fst_routing.py" not in compiled["grounding_evidence"]["allowed_files"]
    assert compiled["context_cost_accounting"]["measurement_class"] == "ESTIMATED"
    assert compiled["context_cost_accounting"]["avoided_token_proxy"] > 0

    cost = workflow.evidence["phase_capsule_cost_observatory"]
    assert cost["ok"] is True
    assert cost["measurement_class"] == "ESTIMATED"
    assert cost["savings_status"] == "SAVINGS_PROVISIONAL"
    assert cost["eligible_for_crucible"] is False
    assert cost["pair_atomic"] is True
    assert workflow.evidence["cost_run_id"] == cost["actual_run_id"]

    with EmpiricalCostLedger(repo_root=tmp_path) as ledger:
        actual = ledger.get_run(cost["actual_run_id"])
        shadow = ledger.get_run(cost["shadow_run_id"])
    assert actual is not None and shadow is not None
    assert actual["mode"] == "AURA_SHARED_GROUNDING_EVIDENCE"
    assert shadow["mode"] == "SHADOW_REPEATED_GROUNDING_EVIDENCE"
    assert actual["measurement_class"] == "ESTIMATED"
    assert actual["context_bytes_after"] < shadow["context_bytes_after"]

    intake = workflow.evidence["learning_arena_intake"]
    assert intake["status"] == "AWAITING_VERIFIED_EXPERIENCE"
    assert intake["eligible_for_crucible"] is False
    assert "ARENA_EXPERIENCE_V3_RECORD" in intake["required_sequence"]
    assert workflow.events[-2][0] == "observatory_handoff"
    assert workflow.events[-1][0] == "phase_capsule_compiled"


def test_denied_objective_restores_prior_workflow_state(tmp_path: Path):
    from aura_showcase_observatory_handoff import (
        import_observatory_trace_into_workflow,
    )

    workflow = _Workflow(tmp_path, admit=False)
    before = (
        workflow.objective,
        dict(workflow.evidence),
        dict(workflow.last_result),
        list(workflow.events),
    )
    result = import_observatory_trace_into_workflow(workflow, _trace())

    assert result["ok"] is False
    assert result["error"] == "workflow_objective_denied"
    assert (
        workflow.objective,
        workflow.evidence,
        workflow.last_result,
        workflow.events,
    ) == before


def test_advisory_only_grounding_opens_handoff_without_expanding_patch_scope(
    tmp_path: Path,
):
    from aura_showcase_observatory_handoff import (
        import_observatory_trace_into_workflow,
    )

    trace = _trace()
    trace["grounding"] = {
        "target_file": "advisory.py",
        "source_spans": [],
        "hashes": {},
        "tests": [],
    }
    workflow = _Workflow(tmp_path)
    result = import_observatory_trace_into_workflow(workflow, trace)

    assert result["ok"] is True
    assert result["phase_capsule_compilation"]["ok"] is False
    assert "grounded_phase_capsules" not in workflow.evidence
    assert "phase_capsule_cost_observatory" not in workflow.evidence
    assert result["next_actions"][0] == "ground_context"


def test_structural_projection_rejects_tampered_accounting(tmp_path: Path):
    from aura_cost_experiment_runner import record_structural_context_projection

    accounting = {
        "classification": "PROJECTED_STRUCTURAL_TOKEN_PROXY",
        "measurement_class": "ESTIMATED",
        "method": "deterministic_utf8_bytes_divided_by_4_ceiling",
        "provider_reported": False,
        "tokenizer_exact": False,
        "shared_evidence_total_bytes": 100,
        "repeated_evidence_counterfactual_bytes": 200,
        "shared_evidence_total_token_proxy": 999,
        "repeated_evidence_counterfactual_token_proxy": 50,
    }
    result = record_structural_context_projection(
        accounting,
        repo_root=tmp_path,
        objective="test",
    )
    assert result["ok"] is False
    assert result["persistent"] is False
    assert result["reason"] == "shared_token_proxy_mismatch"
    assert not (tmp_path / "Aura_Memory" / "empirical_cost_ledger.db").exists()


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


def test_learning_arena_facade_uses_real_empty_ledgers_without_fabricating_experience(
    tmp_path: Path,
):
    from aura_showcase_crucible import LearningArenaShowcase

    arena = LearningArenaShowcase(tmp_path)
    try:
        status = arena.status(
            intake={"ok": True, "status": "AWAITING_VERIFIED_EXPERIENCE"}
        )
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
    assert registry.providers["deepseek"]["model_priority"] == [
        DEEPSEEK_V4_FLASH,
        DEEPSEEK_V4_PRO,
    ]
    assert aura_llm_egress.provider_priority()[:3] == [
        "fireworks",
        "deepseek",
        "anthropic",
    ]

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

    direct = aura_llm_egress.ExternalLLM(
        secrets={"DEEPSEEK_API_KEY": "ds-real-key"}
    )
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
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(
        encoding="utf-8"
    )
    crucible_js = (REPO_ROOT / "aura_showcase" / "crucible.js").read_text(
        encoding="utf-8"
    )
    crucible_css = (REPO_ROOT / "aura_showcase" / "crucible.css").read_text(
        encoding="utf-8"
    )
    server = (REPO_ROOT / "aura_showcase_server.py").read_text(
        encoding="utf-8"
    )

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
