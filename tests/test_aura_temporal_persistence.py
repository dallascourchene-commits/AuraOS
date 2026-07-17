"""Adversarial tests for Aura temporal persistence."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_refactor_state_ledger import build_state_ledger, build_state_sidecar
from aura_temporal_persistence import (
    TemporalCheckpoint,
    TemporalCheckpointRegistry,
    checkpoint_refactor_state,
    verify_refactor_checkpoint,
)


HEAD_A = "a" * 40
HEAD_B = "b" * 40


class _Pending:
    role = "surgeon"


class _Session:
    session_id = "SESSION-1"
    plan_phase_hash = "phase-1"
    objective = "Refactor one exact symbol"
    active_task_index = 1
    pending_turn = _Pending()
    status = "EXECUTING"
    act_capsules = [
        {"task_id": "A1", "target_file": "a.py"},
        {"task_id": "A2", "target_file": "b.py", "depends_on": ["A1"]},
    ]
    event_history = [
        {"kind": "plan", "task_id": "A1"},
        {"kind": "complete", "task_id": "A1"},
    ]
    stage_results = [{"patch_id": "PATCH-1"}]
    verification_results = [{"ok": True, "check": "focused"}]
    assumptions = ["repo head remains unchanged"]
    unresolved_questions = []
    accepted_decisions = ["preserve exact patch authority"]
    rejected_alternatives = ["broad rewrite"]


def _registry(tmp_path: Path) -> TemporalCheckpointRegistry:
    return TemporalCheckpointRegistry(tmp_path)


def _write(registry: TemporalCheckpointRegistry, **overrides):
    kwargs = {
        "arena_id": "coding_arena",
        "session_id": "SESSION-1",
        "repo_head": HEAD_A,
        "payload": {"state": "PLAN", "completed": ["A1"]},
        "invariant_values": {"phase": "one", "authority": "exact"},
        "created_at": 10.0,
    }
    kwargs.update(overrides)
    return registry.write_checkpoint(**kwargs)


def test_checkpoint_is_content_addressed_idempotent_and_registry_chained(tmp_path: Path):
    registry = _registry(tmp_path)

    first = _write(registry)
    second = _write(registry, created_at=999.0)

    assert first["created"] is True
    assert second["created"] is False
    assert first["checkpoint"]["checkpoint_id"] == second["checkpoint"]["checkpoint_id"]
    loaded = registry.load_checkpoint(first["checkpoint"]["checkpoint_id"])
    assert loaded.payload == {"completed": ["A1"], "state": "PLAN"}
    verified = registry.verify_registry()
    assert verified["entry_count"] == 1
    assert verified["last_entry_digest"]


def test_checkpoint_file_tampering_fails_closed(tmp_path: Path):
    registry = _registry(tmp_path)
    result = _write(registry)
    entry = result["registry_entry"]
    path = tmp_path / entry["checkpoint_path"]
    value = json.loads(path.read_text(encoding="utf-8"))
    value["payload"]["state"] = "MUTATED"
    path.write_text(json.dumps(value), encoding="utf-8")

    with pytest.raises(ValueError, match="payload digest mismatch"):
        registry.load_checkpoint(result["checkpoint"]["checkpoint_id"])


def test_parent_chain_and_named_fork_are_preserved(tmp_path: Path):
    registry = _registry(tmp_path)
    root = _write(registry)
    parent_id = root["checkpoint"]["checkpoint_id"]

    child = registry.fork_checkpoint(
        parent_id,
        branch_name="budget-cut",
        repo_head=HEAD_B,
        created_at=20.0,
    )
    checkpoint = TemporalCheckpoint.from_dict(child["checkpoint"])

    assert checkpoint.parent_checkpoint_id == parent_id
    assert checkpoint.branch_name == "budget-cut"
    assert checkpoint.sequence_number == 1
    assert checkpoint.invariant_digests == TemporalCheckpoint.from_dict(
        root["checkpoint"]
    ).invariant_digests
    assert registry.verify_registry()["entry_count"] == 2


def test_cross_session_parent_and_sequence_gaps_are_rejected(tmp_path: Path):
    registry = _registry(tmp_path)
    root = _write(registry)
    parent_id = root["checkpoint"]["checkpoint_id"]

    with pytest.raises(ValueError, match="another arena session"):
        registry.write_checkpoint(
            arena_id="coding_arena",
            session_id="SESSION-2",
            repo_head=HEAD_A,
            payload={"state": "X"},
            parent_checkpoint_id=parent_id,
        )
    with pytest.raises(ValueError, match="continue the parent chain"):
        registry.write_checkpoint(
            arena_id="coding_arena",
            session_id="SESSION-1",
            repo_head=HEAD_A,
            payload={"state": "X"},
            parent_checkpoint_id=parent_id,
            sequence_number=9,
        )


def test_restore_assessment_routes_direct_rebase_and_mitosis(tmp_path: Path):
    registry = _registry(tmp_path)
    result = _write(registry)
    checkpoint_id = result["checkpoint"]["checkpoint_id"]

    direct = registry.assess_restore(
        checkpoint_id,
        current_repo_head=HEAD_A,
        current_invariant_values={"phase": "one", "authority": "exact"},
    )
    assert direct.status == "DIRECT_RESUME_REVIEW_REQUIRED"
    assert direct.can_direct_resume is True
    assert direct.automatic_resume is False

    changed = registry.assess_restore(
        checkpoint_id,
        current_repo_head=HEAD_B,
        current_invariant_values={"phase": "two", "authority": "exact"},
    )
    assert changed.status == "RESTORATION_COUNCIL_REQUIRED"
    assert "repo_head_changed" in changed.mismatches
    assert "invariant_changed:phase" in changed.mismatches

    sliced = registry.assess_restore(
        checkpoint_id,
        current_repo_head=HEAD_A,
        current_invariant_values={"phase": "one", "authority": "exact"},
        remaining_context_tokens=7601,
        surgeon_context_limit=10000,
    )
    assert sliced.status == "MITOSIS_REQUIRED"
    assert sliced.mitosis_required is True


def test_refactor_ledger_checkpoint_reconstructs_exact_state(tmp_path: Path):
    registry = _registry(tmp_path)
    session = _Session()
    ledger = build_state_ledger(session)
    sidecar = build_state_sidecar(session)

    stored = checkpoint_refactor_state(
        registry,
        ledger=ledger,
        sidecar=sidecar,
        repo_head=HEAD_A,
        created_at=30.0,
    )
    checkpoint = registry.load_checkpoint(stored["checkpoint"]["checkpoint_id"])
    verified = verify_refactor_checkpoint(checkpoint)

    assert verified["ok"] is True
    assert verified["projection"]["current_task_id"] == "A2"
    assert verified["projection"]["completed_task_ids"] == ["A1"]


def test_registry_rejects_escape_roots_and_unknown_checkpoint_fields(tmp_path: Path):
    with pytest.raises(ValueError, match="repository-relative"):
        TemporalCheckpointRegistry(tmp_path, memory_root=tmp_path / "outside")

    registry = _registry(tmp_path)
    result = _write(registry)
    value = dict(result["checkpoint"])
    value["unknown"] = True
    with pytest.raises(ValueError, match="unknown temporal checkpoint fields"):
        TemporalCheckpoint.from_dict(value)
