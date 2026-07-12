from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from aura_arena_crucible import ArenaCrucibleService
from aura_crucible_cli import build_parser
from aura_crucible_miner import mine_crucible_candidates
from aura_crucible_store import CrucibleStore
from aura_crucible_types import (
    CRYSTALLIZATION_PROPOSED,
    CrystallizationProposal,
    CruciblePolicy,
    canonical_digest,
)
from aura_crucible_validation import validate_crucible_candidate


@dataclass(frozen=True)
class Profile:
    empirical_uncertainty: float = 1.0


@dataclass(frozen=True)
class Transition:
    transition_id: str
    from_state: str
    soft_weight_profile: Profile = Profile()


class Grammar:
    def __init__(self, transition_id="HUMAN.GROUND_CONTEXT"):
        self.arena_id = "human_agent"
        self.grammar_version = "human-agent-wfst-v1"
        self.manifest_digest = "5071cfeedb320e69a4d6d80aaa073fb095240a0d"
        self.source_path = ".aura/arena_routes/human_agent.v1.json"
        self.meta_grammar = False
        self._transition = Transition(transition_id, "GROUND")
    def transition_by_id(self, transition_id):
        return self._transition if transition_id == self._transition.transition_id else None


def rank(transition_id: str, uncertainty: float, risk: float = 0.0, gap: float = 0.0):
    return {
        "transition_id": transition_id,
        "rank": {
            "unresolved_risk": risk,
            "declared_evidence_gap": gap,
            "empirical_uncertainty": uncertainty,
            "semantic_ambiguity": 0.0,
            "context_switch_cost": 0.0,
            "latency_cost": 0.0,
            "token_cost": 0.0,
            "thermal_cost": 0.0,
            "negative_semantic_fit": -1.0,
            "negative_user_fit": -0.5,
            "stable_transition_id": transition_id,
        },
    }


def experience(index: int, *, success: bool = True, objective: str | None = None, selected="HUMAN.GROUND_CONTEXT"):
    available = [rank(selected, 1.0), rank("HUMAN.OTHER", 1.0)]
    return {
        "experience_id": f"EXP-{index:03d}",
        "arena_id": "human_agent",
        "grammar_version": "human-agent-wfst-v1",
        "state_before": "GROUND",
        "state_after": "PLAN" if success else "GROUND",
        "selected_transition": selected,
        "final_outcome": "COMPLETED" if success else "DENIED",
        "completed_at": float(index),
        "objective_hash": objective or f"OBJ-{index % 4}",
        "repository_commit_sha": "abc",
        "payload": {
            "route": {
                "selected": {"transition_id": selected},
                "available": available,
            }
        },
    }


def policy(**updates):
    data = {
        "min_train_records": 6,
        "min_holdout_records": 3,
        "holdout_fraction": 0.25,
        "min_distinct_objectives": 2,
        "min_train_success_rate": 0.7,
        "min_holdout_success_rate": 0.67,
        "min_holdout_wilson_lower": 0.3,
        "min_shadow_records": 1,
        "max_shadow_selection_change_rate": 0.35,
        "minimum_uncertainty_delta": 0.05,
        "max_proposals_per_run": 8,
        "max_source_ids": 200,
    }
    data.update(updates)
    return CruciblePolicy(**data)


def test_miner_is_deterministic_and_uses_disjoint_temporal_holdout():
    rows = [experience(i) for i in range(12)]
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    first = mine_crucible_candidates(rows, index, policy=policy())
    second = mine_crucible_candidates(reversed(rows), index, policy=policy())
    assert [item.to_dict() for item in first] == [item.to_dict() for item in second]
    candidate = first[0]
    assert candidate.train_record_count == 9
    assert candidate.holdout_record_count == 3
    assert not set(candidate.train_experience_ids) & set(candidate.holdout_experience_ids)
    assert candidate.train_experience_ids[-1] == "EXP-008"
    assert candidate.holdout_experience_ids[0] == "EXP-009"


def test_miner_ignores_stale_or_unknown_transition_records():
    rows = [experience(i, selected="HUMAN.MISSING") for i in range(12)]
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    assert mine_crucible_candidates(rows, index, policy=policy()) == []


def test_miner_requires_support_diversity_and_success():
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    too_few = [experience(i) for i in range(8)]
    assert mine_crucible_candidates(too_few, index, policy=policy()) == []
    one_objective = [experience(i, objective="SAME") for i in range(12)]
    assert mine_crucible_candidates(one_objective, index, policy=policy()) == []
    failures = [experience(i, success=i >= 8) for i in range(12)]
    assert mine_crucible_candidates(failures, index, policy=policy()) == []


def test_candidate_can_only_propose_empirical_uncertainty():
    rows = [experience(i) for i in range(12)]
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    candidate = mine_crucible_candidates(rows, index, policy=policy())[0]
    assert candidate.change_path == "soft_weight_profile.empirical_uncertainty"
    assert 0.0 <= candidate.proposed_value <= 1.0
    assert candidate.learned_weight_patch_authority is False
    assert candidate.crystallization_patch_authority is False
    assert candidate.automatic_grammar_promotion is False


def test_holdout_and_shadow_validation_pass_without_mutation():
    rows = [experience(i) for i in range(12)]
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    candidate = mine_crucible_candidates(rows, index, policy=policy())[0]
    result = validate_crucible_candidate(candidate, rows, policy=policy())
    assert result["passed"] is True
    assert result["shadow"]["replay_record_count"] == 3
    assert result["shadow"]["unsafe_selection_changes"] == 0
    assert result["active_grammar_mutated"] is False


def test_validation_fails_on_bad_holdout():
    rows = [experience(i, success=i < 9) for i in range(12)]
    index = {("human_agent", "human-agent-wfst-v1"): Grammar()}
    candidate = mine_crucible_candidates(rows, index, policy=policy(min_train_success_rate=0.6))[0]
    result = validate_crucible_candidate(candidate, rows, policy=policy(min_train_success_rate=0.6))
    assert result["passed"] is False
    assert result["checks"]["holdout_success_rate"] is False


def proposal(run_id="RUN-1"):
    validation = {"passed": True, "verifier_status": "PASSED"}
    return CrystallizationProposal(
        proposal_id="CPROP-1",
        run_id=run_id,
        candidate_id="CAND-1",
        arena_id="human_agent",
        grammar_version="human-agent-wfst-v1",
        manifest_path=".aura/arena_routes/human_agent.v1.json",
        manifest_digest="5071cfeedb320e69a4d6d80aaa073fb095240a0d",
        state_before="GROUND",
        transition_id="HUMAN.GROUND_CONTEXT",
        change_path="soft_weight_profile.empirical_uncertainty",
        current_value=1.0,
        proposed_value=0.2,
        validation=validation,
        source_experience_ids=("EXP-1", "EXP-2"),
        source_experience_digest=canonical_digest(["EXP-1", "EXP-2"]),
        created_at=1.0,
    )


def test_proposal_is_terminal_and_has_no_promotion_authority():
    packet = proposal().to_dict()
    assert packet["status"] == CRYSTALLIZATION_PROPOSED
    assert packet["required_next_gate"] == "VERIFIER_AND_HUMAN_REVIEW"
    assert packet["crystallization_patch_authority"] is False
    assert packet["automatic_grammar_promotion"] is False
    bad = proposal().to_dict()
    bad.pop("proposal_digest", None)
    bad["status"] = "PROMOTED"
    with pytest.raises(ValueError):
        CrystallizationProposal(**bad)


def test_store_pause_resume_wal_and_idempotent_proposal(tmp_path: Path):
    store = CrucibleStore(tmp_path)
    assert store.status()["journal_mode"] == "wal"
    assert store.pause("review")["paused"] is True
    store.close()

    # Verify paused state persists across store instances
    store2 = CrucibleStore(tmp_path)
    assert store2.status()["paused"] is True
    assert store2.resume()["paused"] is False
    store2.close()

    # Verify resumed state persists across store instances
    store3 = CrucibleStore(tmp_path)
    assert store3.status()["paused"] is False
    first = store3.record_proposal(proposal())
    second = store3.record_proposal(proposal())
    assert first["ok"] is True and first["idempotent_replay"] is False
    assert second["ok"] is True and second["idempotent_replay"] is True
    assert store3.get_proposal("CPROP-1")["status"] == CRYSTALLIZATION_PROPOSED
    store3.close()


def test_store_rejects_non_proposal_status_and_digest_conflict(tmp_path: Path):
    store = CrucibleStore(tmp_path)
    invalid = proposal().to_dict()
    invalid["status"] = "PROMOTED"
    assert store.record_proposal(invalid)["ok"] is False
    assert store.record_proposal(proposal())["ok"] is True
    changed = proposal().to_dict()
    changed["proposed_value"] = 0.1
    assert store.record_proposal(changed)["reason"] == "proposal_id_digest_conflict"
    store.close()


def test_store_rejects_forged_authority_flags(tmp_path: Path):
    store = CrucibleStore(tmp_path)
    forged = proposal().to_dict()
    forged["automatic_grammar_promotion"] = True
    result = store.record_proposal(forged)
    store.close()
    assert result["ok"] is False
    assert result["reason"].startswith("invalid_proposal_contract")


def test_service_pauses_fail_closed(tmp_path: Path):
    service = ArenaCrucibleService(tmp_path)
    service.pause("operator")
    result = service.run_once(policy=policy())
    service.close()
    assert result["ok"] is False
    assert result["reason"] == "crucible_paused"
    assert result["automatic_grammar_promotion"] is False


def test_service_run_emits_only_proposals(monkeypatch, tmp_path: Path):
    rows = [experience(i) for i in range(12)]
    service = ArenaCrucibleService(tmp_path)
    monkeypatch.setattr(service, "_load_grammar_index", lambda: ({("human_agent", "human-agent-wfst-v1"): Grammar()}, []))

    class FakeLedger:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def history(self, **kwargs): return rows

    monkeypatch.setattr("aura_arena_crucible.ArenaExperienceLedger", FakeLedger)
    result = service.run_once(arena_id="human_agent", policy=policy())
    service.close()
    assert result["ok"] is True
    assert result["proposal_count"] == 1
    assert result["terminal_status"] == CRYSTALLIZATION_PROPOSED
    assert result["active_grammar_mutated"] is False
    assert result["automatic_commit"] is False
    assert result["automatic_merge"] is False


def test_repeated_service_cycle_reuses_identical_candidate_proposal(monkeypatch, tmp_path: Path):
    rows = [experience(i) for i in range(12)]
    service = ArenaCrucibleService(tmp_path)
    monkeypatch.setattr(service, "_load_grammar_index", lambda: ({("human_agent", "human-agent-wfst-v1"): Grammar()}, []))

    class FakeLedger:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def history(self, **kwargs): return rows

    monkeypatch.setattr("aura_arena_crucible.ArenaExperienceLedger", FakeLedger)
    first = service.run_once(arena_id="human_agent", policy=policy())
    second = service.run_once(arena_id="human_agent", policy=policy())
    status = service.store.status()
    service.close()
    assert first["proposal_count"] == 1
    assert second["proposal_count"] == 1
    assert second["proposals"][0]["storage"]["existing_candidate"] is True
    assert status["proposal_count"] == 1


def test_cli_has_no_apply_promote_or_merge_command():
    parser = build_parser()
    choices = parser._subparsers._group_actions[0].choices
    assert {"status", "pause", "resume", "run-once", "service", "proposals", "proposal"} == set(choices)
    assert not {"apply", "promote", "commit", "push", "merge"} & set(choices)
