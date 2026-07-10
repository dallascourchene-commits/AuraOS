"""Tests for Aura Cockpit Audit Trail."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_cockpit_audit_trail import (
    record_gate_transition, record_human_approval, record_agent_handoff,
    record_verifier_result, record_research_evidence, export_cockpit_audit_packet,
    PATCH_AUTHORITY,
    _events,
)


class TestAuditTrail:
    def setup_method(self):
        _events.clear()

    def test_record_gate_transition(self):
        result = record_gate_transition("INGESTED", "POLYSYNTHETIC_COMPRESSED")
        assert result["ok"] is True
        assert result["recorded"] is True

    def test_record_human_approval(self):
        result = record_human_approval("HUMAN_APPROVED_FOR_AGENT")
        assert result["ok"] is True

    def test_record_agent_handoff(self):
        result = record_agent_handoff("hermes", {"objective": "test"})
        assert result["ok"] is True

    def test_record_verifier_result(self):
        result = record_verifier_result({"ok": True, "tests_pass": True})
        assert result["ok"] is True

    def test_export_audit_packet(self):
        record_gate_transition("A", "B")
        record_human_approval("C")
        result = export_cockpit_audit_packet()
        assert result["ok"] is True
        assert result["audit_packet"]["count"] >= 2

    def test_invariants(self):
        result = record_gate_transition("A", "B")
        assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
        assert result["vsa_patch_authority"] is False

    def test_works_offline(self):
        result = export_cockpit_audit_packet()
        assert result["ok"] is True
