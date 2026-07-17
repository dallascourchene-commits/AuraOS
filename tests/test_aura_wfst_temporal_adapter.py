"""Tests for temporal WFST guard semantics."""
from __future__ import annotations

from pathlib import Path

from aura_temporal_persistence import TemporalCheckpointRegistry
from aura_wfst_temporal_adapter import (
    TemporalAspect,
    classify_temporal_state,
    guard_temporal_action,
)


HEAD = "a" * 40


def _checkpoint(tmp_path: Path):
    registry = TemporalCheckpointRegistry(tmp_path)
    result = registry.write_checkpoint(
        arena_id="construction_arena",
        session_id="PROJECT-1",
        repo_head=HEAD,
        payload={"zone": "floor-5", "aspect": "BLOCKED"},
        invariant_values={"state_digest": "state-1"},
        created_at=100.0,
    )
    return registry.load_checkpoint(result["checkpoint"]["checkpoint_id"])


def test_current_temporal_state_passes_to_existing_guards(tmp_path: Path):
    checkpoint = _checkpoint(tmp_path)
    decision = classify_temporal_state(
        checkpoint,
        observed_at=110.0,
        evaluated_at=120.0,
        max_age_seconds=60.0,
    )

    assert decision.allowed is True
    assert decision.aspect == TemporalAspect.CURRENT.value
    assert decision.active_grammar_mutated is False


def test_stale_future_and_branch_offset_fail_closed(tmp_path: Path):
    checkpoint = _checkpoint(tmp_path)

    stale = classify_temporal_state(
        checkpoint,
        observed_at=90.0,
        evaluated_at=120.0,
    )
    future = classify_temporal_state(
        checkpoint,
        observed_at=130.0,
        evaluated_at=120.0,
    )
    branch = classify_temporal_state(
        checkpoint,
        observed_at=110.0,
        evaluated_at=120.0,
        current_checkpoint_id="CHK-" + "f" * 40,
    )

    assert stale.aspect == TemporalAspect.STALE.value
    assert future.aspect == TemporalAspect.FUTURE.value
    assert branch.aspect == TemporalAspect.BRANCH_OFFSET.value
    assert not stale.allowed and not future.allowed and not branch.allowed


def test_action_guard_combines_temporal_aspect_and_domain_blockers(tmp_path: Path):
    checkpoint = _checkpoint(tmp_path)
    result = guard_temporal_action(
        checkpoint,
        action_scope={"dir": "floor-5"},
        stored_state={
            "dir": "floor-5",
            "aspect": "BLOCKED",
            "observed_at": 110.0,
        },
        evaluated_at=120.0,
    )

    assert result["allowed"] is False
    assert result["blockers"] == ["ASP:BLOCKED"]
    assert result["next_gate"] == "REFRESH_AND_VERIFY"
    assert result["state_applied"] is False
    assert result["active_grammar_mutated"] is False


def test_direction_mismatch_never_uses_similarity_as_authority(tmp_path: Path):
    checkpoint = _checkpoint(tmp_path)
    result = guard_temporal_action(
        checkpoint,
        action_scope={"dir": "floor-6"},
        stored_state={
            "dir": "floor-5",
            "aspect": "OPEN",
            "observed_at": 110.0,
        },
        evaluated_at=120.0,
    )

    assert result["allowed"] is False
    assert "DIR:SCOPE_MISMATCH" in result["blockers"]
    assert result["vsa_patch_authority"] is False
