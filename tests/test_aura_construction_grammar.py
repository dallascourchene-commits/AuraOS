from __future__ import annotations

import json
from pathlib import Path

from aura_arena_wfst_compiler import load_and_compile_arena_grammar
from aura_arena_wfst_runtime import ArenaWFSTRuntime


MANIFEST = Path(".aura/arena_routes/construction.v1.json")


def _runtime() -> ArenaWFSTRuntime:
    compiled = load_and_compile_arena_grammar(MANIFEST)
    assert compiled.ok is True
    assert compiled.grammar is not None
    runtime = ArenaWFSTRuntime(repo_root=".")
    runtime.register_grammar(compiled.grammar)
    return runtime


def test_construction_grammar_compiles_with_proposal_only_authority():
    compiled = load_and_compile_arena_grammar(MANIFEST)
    assert compiled.ok is True
    assert compiled.grammar is not None
    assert compiled.grammar.arena_id == "sco_construction"
    assert compiled.grammar.grammar_version == "sco-construction-wfst-v1"

    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    authority = raw["authority"]
    assert authority["vsa_patch_authority"] is False
    assert authority["learned_weight_patch_authority"] is False
    assert authority["crystallization_patch_authority"] is False
    assert authority["automatic_grammar_promotion"] is False
    assert authority["physical_work_authorized"] is False
    assert authority["payment_released"] is False
    assert authority["access_controlled"] is False


def test_construction_route_blocks_exact_match_without_required_evidence():
    route = _runtime().route(
        arena_id="sco_construction",
        current_state="DECIDE",
        input_text="advance electrical package",
    )
    assert route["selected"] is None
    assert route["abstained"] is True
    assert route["abstention_reason"] == "exact_transition_blocked"
    blocked = {item["transition_id"]: item for item in route["blocked"]}
    assert "CONSTRUCTION.ADVANCE_ELECTRICAL" in blocked
    assert blocked["CONSTRUCTION.ADVANCE_ELECTRICAL"]["fail_closed"] is True
    assert set(blocked["CONSTRUCTION.ADVANCE_ELECTRICAL"]["missing_evidence"]) == {
        "benchmark_report",
        "verification_packet",
    }


def test_construction_route_blocks_failed_verifier_packet():
    route = _runtime().route(
        arena_id="sco_construction",
        current_state="DECIDE",
        input_text="advance electrical package",
        evidence={
            "benchmark_report": {"ok": True},
            "verification_packet": {"verification_ok": False},
        },
    )
    assert route["selected"] is None
    assert route["abstention_reason"] == "exact_transition_blocked"
    blocked = next(
        item
        for item in route["blocked"]
        if item["transition_id"] == "CONSTRUCTION.ADVANCE_ELECTRICAL"
    )
    assert any(
        result["guard_id"] == "GUARD.VERIFIER_PASS" and result["passed"] is False
        for result in blocked["failed_guards"]
    )


def test_construction_route_admits_verified_proposal_without_runtime_authority():
    route = _runtime().route(
        arena_id="sco_construction",
        current_state="DECIDE",
        input_text="advance electrical package",
        evidence={
            "benchmark_report": {"ok": True},
            "verification_packet": {"verification_ok": True},
        },
    )
    assert route["selected"]["transition_id"] == "CONSTRUCTION.ADVANCE_ELECTRICAL"
    assert route["selected"]["approval_requirement"] == "human_review"
    assert route["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert route["vsa_patch_authority"] is False
    assert route["learned_weight_patch_authority"] is False
    assert route["automatic_grammar_promotion"] is False
