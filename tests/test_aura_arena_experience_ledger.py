from __future__ import annotations

from pathlib import Path
import shutil

from aura_arena_experience import build_arena_experience
from aura_arena_experience_ledger import ArenaExperienceLedger
from aura_human_agent_wfst_adapter import HumanAgentWFSTController


def _experience(**overrides):
    values = {
        "arena_id": "human_agent",
        "arena_version": "v1",
        "grammar_version": "g1",
        "grammar_manifest_digest": "digest-g1",
        "runtime_version": "r1",
        "compiler_version": "c1",
        "state_before": "FRAME",
        "state_after": "GROUND",
        "selected_transition": "HUMAN.SET_OBJECTIVE",
        "final_outcome": "COMPLETED",
        "experience_id": "EXP-fixed",
        "payload": {
            "observable_rationale": "state-local exact symbol",
            "api_key": "sk-abcdefghijklmnopqrstuvwxyz",
            "chain_of_thought": "must never persist",
            "nested": {"authorization": "Bearer abcdefghijklmnopqrstuvwxyz"},
        },
    }
    values.update(overrides)
    return build_arena_experience(**values)


def test_ledger_uses_wal_redacts_secrets_and_is_idempotent(tmp_path: Path):
    with ArenaExperienceLedger(tmp_path) as ledger:
        status = ledger.status()
        assert status["journal_mode"] == "wal"
        assert status["schema_version"] == 4
        assert status["v2_complete_record_count"] == 0
        exp = _experience()
        first = ledger.record(exp)
        second = ledger.record(exp)
        assert first["ok"] and second["ok"]
        assert not first["idempotent_replay"]
        assert second["idempotent_replay"]
        stored = ledger.get("EXP-fixed")
        assert stored["payload"]["api_key"] == "[REDACTED]"
        assert "chain_of_thought" not in stored["payload"]
        assert stored["payload"]["nested"]["authorization"] == "[REDACTED]"
        assert stored["grammar_manifest_digest"] == "digest-g1"
        assert stored["outcome_vector"]["proposal_only"] is True
        assert stored["legacy_record"] is False
        assert stored["learned_weight_patch_authority"] is False
        assert stored["crystallization_patch_authority"] is False


def test_same_id_with_different_digest_fails_closed(tmp_path: Path):
    with ArenaExperienceLedger(tmp_path) as ledger:
        assert ledger.record(_experience())["ok"]
        conflict = ledger.record(_experience(final_outcome="DENIED"))
        assert not conflict["ok"]
        assert conflict["reason"] == "experience_id_digest_conflict"


def test_jsonl_export_is_sanitized(tmp_path: Path):
    output = tmp_path / "export" / "experience.jsonl"
    with ArenaExperienceLedger(tmp_path) as ledger:
        ledger.record(_experience())
        result = ledger.export_jsonl(output)
        assert result["record_count"] == 1
    text = output.read_text(encoding="utf-8")
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in text
    assert "must never persist" not in text


class StubWorkflow:
    def __init__(self):
        self.workflow_id = "HWF-test"
        self.objective = ""
        self.evidence = {}
        self.phase = "FRAME"

    def get_state(self):
        return {"current_phase": self.phase, "evidence": self.evidence}

    def execute(self, action_id, payload=None):
        payload = dict(payload or {})
        if action_id != "set_objective":
            return {"ok": False, "status": "DENIED", "action_id": action_id, "message": "unexpected"}
        self.objective = payload["objective"]
        self.evidence["objective"] = self.objective
        self.phase = "GROUND"
        return {
            "ok": True,
            "status": "ALLOWED",
            "action_id": action_id,
            "message": "objective framed",
            "produced_evidence": {"objective": self.objective},
            "missing_evidence": [],
        }


def test_free_form_frame_command_records_manifest_and_complete_choice_set(tmp_path: Path):
    source = Path(__file__).resolve().parents[1] / ".aura" / "arena_routes"
    target = tmp_path / ".aura" / "arena_routes"
    target.mkdir(parents=True)
    shutil.copy(source / "human_agent.v1.json", target / "human_agent.v1.json")
    shutil.copy(source / "meta.v1.json", target / "meta.v1.json")

    workflow = StubWorkflow()
    controller = HumanAgentWFSTController(workflow, repo_root=tmp_path)
    result = controller.route_command("Refactor the routing system")
    controller.close()

    assert result["ok"]
    assert result["action_id"] == "set_objective"
    assert workflow.objective == "Refactor the routing system"
    assert workflow.phase == "GROUND"
    route = result["route_decision"]
    assert route["selected"]["transition_id"] == "HUMAN.SET_OBJECTIVE"
    assert route["all_state_local_alternatives_evaluated"] is True
    assert len(route["available"]) > 1

    with ArenaExperienceLedger(tmp_path) as ledger:
        stored = ledger.history(arena_id="human_agent", limit=1)[0]
    available_ids = [row["transition_id"] for row in route["available"]]
    assert stored["grammar_manifest_digest"] == route["grammar_digest"]
    assert [row["transition_id"] for row in stored["admissible_alternatives"]] == available_ids
    assert [row["transition_id"] for row in stored["predictions"]] == available_ids
    assert sum(bool(row["predicted_selected"]) for row in stored["predictions"]) == 1
    assert stored["outcome_vector"]["terminal_class"] == "COMPLETED"
    assert result["experience_recording"]["persistent"] is True
