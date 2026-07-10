"""Tests for Aura Ephemeral Lifecycle."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_ephemeral_lifecycle import (
    EphemeralState, TRANSITIONS, can_transition, transition,
    get_state_info, lifecycle_state_machine, check_ttl_expired,
)


class TestLifecycle:
    def test_16_states(self):
        assert len(EphemeralState) == 16

    def test_state_names(self):
        states = [s.value for s in EphemeralState]
        assert "DRAFTED" in states
        assert "RUNNING" in states
        assert "DISSOLVED" in states
        assert "BLOCKED" in states
        assert "FAILED" in states
        assert "CRYSTALLIZATION_PROPOSED" in states

    def test_legal_transition(self):
        assert can_transition(EphemeralState.DRAFTED, EphemeralState.CAPABILITIES_RESOLVED) is True

    def test_illegal_transition(self):
        assert can_transition(EphemeralState.DRAFTED, EphemeralState.RUNNING) is False

    def test_transition_result(self):
        result = transition(EphemeralState.DRAFTED, EphemeralState.CAPABILITIES_RESOLVED)
        assert result["ok"] is True

    def test_illegal_transition_result(self):
        result = transition(EphemeralState.DRAFTED, EphemeralState.RUNNING)
        assert result["ok"] is False
        assert "illegal" in result["reason"]

    def test_no_running_before_sandbox(self):
        # Cannot go from MANIFEST_DIGESTED to RUNNING directly
        assert can_transition(EphemeralState.MANIFEST_DIGESTED, EphemeralState.RUNNING) is False

    def test_dissolved_is_terminal(self):
        assert can_transition(EphemeralState.DISSOLVED, EphemeralState.RUNNING) is False
        assert can_transition(EphemeralState.DISSOLVED, EphemeralState.DRAFTED) is False

    def test_state_info(self):
        info = get_state_info(EphemeralState.RUNNING)
        assert info["ok"] is True
        assert "allowed_actions" in info
        assert "blocked_actions" in info

    def test_state_machine_packet(self):
        sm = lifecycle_state_machine()
        assert sm["ok"] is True
        assert sm["state_count"] == 16

    def test_ttl_expired(self):
        assert check_ttl_expired(expires_at=0.0, now=100.0) is True
        assert check_ttl_expired(expires_at=200.0, now=100.0) is False

    def test_crystallization_goes_to_dissolve(self):
        assert can_transition(EphemeralState.CRYSTALLIZATION_PROPOSED, EphemeralState.DISSOLVING) is True
        # No automatic promotion
        assert can_transition(EphemeralState.CRYSTALLIZATION_PROPOSED, EphemeralState.RUNNING) is False
