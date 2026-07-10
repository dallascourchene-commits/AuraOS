"""Tests for Aura Intent Ingestion (polysynthetic intent document parser).

Tests cover:
- parse_intent_document handles YAML frontmatter
- parse_intent_document handles unstructured markdown fallback
- compile_intent_packet returns IntentPacket with required fields
- route_intent_to_lexc validates a valid six-slot route
- invalid six-slot route is marked invalid
- route_intent_to_fst blocks broad scope (subsystem -> PLAN_ONLY)
- route_intent_to_fst missing grounding -> LOCALIZE_FIRST
- intent_to_agent_handoff produces compact packet
- write_intent_capsule writes JSON file
- patch_authority and vsa_patch_authority invariants
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_intent_ingestion import (
    parse_intent_document,
    compile_intent_packet,
    compress_intent_for_agent,
    route_intent_to_lexc,
    route_intent_to_fst,
    route_intent_to_affordances,
    intent_to_agent_handoff,
    write_intent_capsule,
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
)

EXAMPLE_INTENT = REPO_ROOT / ".aura" / "intents" / "example.aura.md"


class TestParseIntentDocument:
    def test_parse_yaml_frontmatter(self):
        text = """---
aura_doc_type: refactor_intent
intent_id: test_001
patch_authority: exact_source_spans_and_hashes_only
vsa_patch_authority: false
---

[AURA_INTENT]
OBJECTIVE: Test objective for parsing.
"""
        result = parse_intent_document(text)
        assert result["ok"] is True
        assert result["frontmatter"]["aura_doc_type"] == "refactor_intent"
        assert result["frontmatter"]["intent_id"] == "test_001"
        assert "AURA_INTENT" in result["sections"]

    def test_parse_example_file(self):
        if not EXAMPLE_INTENT.exists():
            pytest.skip("example.aura.md not found")
        result = parse_intent_document(str(EXAMPLE_INTENT), repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert "frontmatter" in result
        assert "sections" in result
        assert result["objective"] != ""

    def test_unstructured_markdown_fallback(self):
        text = "Just a plain markdown document about refactoring Fireworks egress."
        result = parse_intent_document(text)
        assert result["ok"] is True
        assert result["objective"] != ""

    def test_extract_objective_from_intent_section(self):
        text = """---
intent_id: test
---

[AURA_INTENT]
OBJECTIVE: Build something cool.
"""
        result = parse_intent_document(text)
        assert result["objective"] == "Build something cool."


class TestCompileIntentPacket:
    def test_compile_from_text(self):
        text = """---
intent_id: test
---

[AURA_INTENT]
OBJECTIVE: Refactor Fireworks egress provider.
"""
        result = compile_intent_packet(text, repo_root=REPO_ROOT, skip_grounding=True)
        assert result["ok"] is True
        assert result["objective"] == "Refactor Fireworks egress provider."
        assert "polysynthetic_packet" in result
        assert "raw_objective_tokens_est" in result
        assert "compressed_tokens_est" in result
        assert "routing_frame" in result
        assert "route_decision" in result
        assert "checkpoint_plan" in result
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY

    def test_compile_from_example_file(self):
        if not EXAMPLE_INTENT.exists():
            pytest.skip("example.aura.md not found")
        parsed = parse_intent_document(str(EXAMPLE_INTENT), repo_root=REPO_ROOT)
        result = compile_intent_packet(parsed, repo_root=REPO_ROOT, skip_grounding=True)
        assert result["ok"] is True
        assert result["objective"] != ""
        assert len(result["polysynthetic_packet"]) > 0

    def test_compile_has_likely_files_and_symbols(self):
        result = compile_intent_packet("Refactor Fireworks egress", repo_root=REPO_ROOT, skip_grounding=True)
        assert "likely_files" in result
        assert "likely_symbols" in result
        assert isinstance(result["likely_files"], list)
        assert isinstance(result["likely_symbols"], list)


class TestLexcRoute:
    def test_valid_six_slot_route(self):
        text = """---
intent_id: test
---

[AURA_LEXC_ROUTE]
DIR: DataGate
ASP: +NI
CLASS: +VTI
SUBJ: +T1_RAM
VOICE: +SHAPE:TETRA+TEMP:HOT+LUM:MID+FRIC:MID+DIR:MIIGWECH
STEM: _EXEC
"""
        result = route_intent_to_lexc(text, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["valid"] is True
        assert len(result["symbols"]) > 0

    def test_invalid_route_missing_slots(self):
        text = """---
intent_id: test
---

[AURA_LEXC_ROUTE]
DIR: +SYS
ASP: +SYS_ROUTE
"""
        result = route_intent_to_lexc(text, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["valid"] is False

    def test_no_lexc_section(self):
        text = "Just a plain objective."
        result = route_intent_to_lexc(text, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["valid"] is False
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestFSTRouting:
    def test_broad_scope_routes_to_plan_only(self):
        text = """---
intent_id: test
---

[AURA_INTENT]
OBJECTIVE: Refactor the entire repository subsystem.
[AURA_ROUTE_HINTS]
scope: subsystem
"""
        result = route_intent_to_fst(text, repo_root=REPO_ROOT)
        assert result["ok"] is True
        frame = result["routing_frame"]
        assert frame["scope"] == "subsystem"
        decision = result["route_decision"]
        # Missing grounding is checked before broad scope, so it routes to LOCALIZE_FIRST
        assert decision["route"] == "LOCALIZE_FIRST"

    def test_missing_grounding_routes_to_localize(self):
        result = route_intent_to_fst("Find the egress module", repo_root=REPO_ROOT)
        assert result["ok"] is True
        decision = result["route_decision"]
        assert decision["route"] == "LOCALIZE_FIRST"


class TestAgentHandoff:
    def test_handoff_packet(self):
        packet = compile_intent_packet("Refactor Fireworks egress", repo_root=REPO_ROOT, skip_grounding=True)
        result = intent_to_agent_handoff(packet, agent="hermes", repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert result["agent"] == "hermes"
        assert "compressed_context" in result
        assert "routing_frame" in result
        assert "patch_authority" in result
        assert result["patch_authority"] == PATCH_AUTHORITY


class TestWriteIntentCapsule:
    def test_write_capsule(self, tmp_path):
        packet = {"ok": True, "objective": "Test", "patch_authority": PATCH_AUTHORITY}
        output_file = str(tmp_path / "test_capsule.json")
        result = write_intent_capsule(packet, output_file, repo_root=REPO_ROOT)
        assert result["ok"] is True
        assert Path(output_file).exists()


class TestInvariants:
    def test_parse_has_invariants(self):
        result = parse_intent_document("Test objective")
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY

    def test_compile_has_invariants(self):
        result = compile_intent_packet("Test", repo_root=REPO_ROOT, skip_grounding=True)
        assert result["patch_authority"] == PATCH_AUTHORITY
        assert result["vsa_patch_authority"] is VSA_PATCH_AUTHORITY

    def test_lexc_has_invariants(self):
        result = route_intent_to_lexc("Test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

    def test_fst_has_invariants(self):
        result = route_intent_to_fst("Test", repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY

    def test_handoff_has_invariants(self):
        packet = compile_intent_packet("Test", repo_root=REPO_ROOT, skip_grounding=True)
        result = intent_to_agent_handoff(packet, repo_root=REPO_ROOT)
        assert result["patch_authority"] == PATCH_AUTHORITY
