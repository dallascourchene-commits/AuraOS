"""Tests for FST provenance, canonical slot order, and cultural attribution."""
from __future__ import annotations
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aura_lexc import (
    SLOT_ORDER, SlotName, CANONICAL_SLOT_ORDER, SLOT_ALIASES,
    canonicalize_slot_name, AuraLexc,
)


class TestCanonicalSlotOrder:
    def test_canonical_order(self):
        assert CANONICAL_SLOT_ORDER == ("DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM")

    def test_slot_aliases(self):
        assert SLOT_ALIASES["SPATIAL"] == "DIR"
        assert SLOT_ALIASES["DIRECTION"] == "DIR"
        assert SLOT_ALIASES["ASPECT"] == "ASP"

    def test_canonicalize_slot_name(self):
        assert canonicalize_slot_name("SPATIAL") == "DIR"
        assert canonicalize_slot_name("DIR") == "DIR"


class TestLexcValidation:
    def test_strict_compilation(self):
        lexc = AuraLexc.from_path(REPO_ROOT / "aura.lexc", strict=False)
        errors = [d for d in lexc.diagnostics if d.severity == "error"]
        assert len(errors) == 0

    def test_complete_routes(self):
        lexc = AuraLexc.from_path(REPO_ROOT / "aura.lexc", strict=False)
        routes = lexc.complete_routes()
        assert len(routes) > 0


class TestProvenanceDoc:
    def test_provenance_doc_exists(self):
        assert (REPO_ROOT / "docs" / "AURA_FST_PROVENANCE_AND_SECURITY.md").exists()

    def test_provenance_doc_content(self):
        doc = (REPO_ROOT / "docs" / "AURA_FST_PROVENANCE_AND_SECURITY.md").read_text(encoding="utf-8")
        assert "Anishinaabemowin" in doc
        assert "Athabaskan" in doc
        assert "admission grammar" in doc.lower()
        assert "DIR" in doc
