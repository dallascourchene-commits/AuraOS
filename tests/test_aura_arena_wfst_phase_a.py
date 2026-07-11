from __future__ import annotations

import json
from pathlib import Path
import sys
import types

from aura_arena_state_packet import build_arena_state_packet, parse_arena_state_packet
from aura_arena_wfst_compiler import compile_arena_grammar, load_and_compile_arena_grammar
from aura_arena_wfst_runtime import ArenaWFSTRuntime
import aura_cockpit_audit_trail as audit


def _manifest(transitions):
    return {
        "schema_version": "AURA_ARENA_GRAMMAR_MANIFEST_V1",
        "arena_id": "test",
        "arena_version": "test-v1",
        "grammar_version": "test-grammar-v1",
        "start_state": "S0",
        "states": ["S0", "S1"],
        "terminal_states": ["S1"],
        "transitions": transitions,
    }


def test_compiler_is_deterministic_and_rejects_unknown_guard():
    manifest = _manifest([{
        "transition_id": "TEST.GO",
        "from_state": "S0",
        "accepted_input_symbols": ["go"],
        "output_symbol": "ACTION:go",
        "next_state": "S1",
    }])
    first = compile_arena_grammar(manifest)
    second = compile_arena_grammar(json.loads(json.dumps(manifest)))
    assert first.ok and second.ok
    assert first.manifest_digest == second.manifest_digest
    bad = json.loads(json.dumps(manifest))
    bad["transitions"][0]["hard_guards"] = [{"id": "GUARD.DOES_NOT_EXIST"}]
    result = compile_arena_grammar(bad)
    assert not result.ok
    assert any(item.code == "unknown_guard" for item in result.diagnostics)


def test_compiler_rejects_state_local_alias_ambiguity():
    manifest = _manifest([
        {
            "transition_id": "TEST.A",
            "from_state": "S0",
            "accepted_input_symbols": ["same phrase"],
            "output_symbol": "ACTION:a",
            "next_state": "S1",
        },
        {
            "transition_id": "TEST.B",
            "from_state": "S0",
            "aliases": ["same phrase"],
            "output_symbol": "ACTION:b",
            "next_state": "S1",
        },
    ])
    result = compile_arena_grammar(manifest)
    assert not result.ok
    assert any(item.code == "ambiguous_state_local_alias" for item in result.diagnostics)


def test_hard_guard_removes_transition_before_ranking():
    manifest = _manifest([
        {
            "transition_id": "TEST.BLOCKED_HIGH_WEIGHT",
            "from_state": "S0",
            "accepted_input_symbols": ["blocked"],
            "output_symbol": "ACTION:blocked",
            "next_state": "S1",
            "hard_guards": [{"id": "GUARD.EVIDENCE_PRESENT", "args": {"key": "proof"}}],
            "required_evidence": ["proof"],
            "soft_weight_profile": {"base_priority": 1.0, "user_fit": 1.0, "empirical_uncertainty": 0.0},
        },
        {
            "transition_id": "TEST.SAFE_LOW_WEIGHT",
            "from_state": "S0",
            "accepted_input_symbols": ["safe"],
            "output_symbol": "ACTION:safe",
            "next_state": "S1",
            "soft_weight_profile": {"base_priority": 0.0, "user_fit": 0.0, "empirical_uncertainty": 1.0},
        },
    ])
    compiled = compile_arena_grammar(manifest)
    runtime = ArenaWFSTRuntime()
    runtime.register_grammar(compiled.grammar)
    projected = runtime.project_state(arena_id="test", current_state="S0")
    assert [row["transition_id"] for row in projected["available"]] == ["TEST.SAFE_LOW_WEIGHT"]
    assert [row["transition_id"] for row in projected["blocked"]] == ["TEST.BLOCKED_HIGH_WEIGHT"]
    exact = runtime.route(arena_id="test", current_state="S0", input_text="blocked")
    assert exact["selected"] is None
    assert exact["abstention_reason"] == "exact_transition_blocked"


def test_meta_transition_preserves_arena_state(tmp_path: Path):
    arena_manifest = _manifest([{
        "transition_id": "TEST.GO",
        "from_state": "S0",
        "accepted_input_symbols": ["go"],
        "output_symbol": "ACTION:go",
        "next_state": "S1",
    }])
    meta_manifest = {
        "schema_version": "AURA_ARENA_GRAMMAR_MANIFEST_V1",
        "arena_id": "meta",
        "arena_version": "meta-v1",
        "grammar_version": "meta-grammar-v1",
        "meta_grammar": True,
        "start_state": "*",
        "states": ["*"],
        "transitions": [{
            "transition_id": "META.STATUS",
            "from_state": "*",
            "accepted_input_symbols": ["status"],
            "output_symbol": "META:status",
            "next_state": "*",
        }],
    }
    runtime = ArenaWFSTRuntime(repo_root=tmp_path)
    runtime.register_grammar(compile_arena_grammar(arena_manifest).grammar)
    runtime.register_grammar(compile_arena_grammar(meta_manifest).grammar)
    routed = runtime.route(arena_id="test", current_state="S0", input_text="status")
    assert routed["selected"]["transition_id"] == "META.STATUS"
    assert routed["selected"]["next_state"] == "S0"
    assert routed["state_packet"]["next_state"] == "S0"


def test_j1_state_packet_round_trip_and_tamper_detection():
    state, encoded = build_arena_state_packet(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PROVE",
        substate="RUN_TESTS",
        state_code="PROVE/RUN_TESTS",
        evidence_digest="abc",
        selected_transition="HUMAN.RUN_TESTS",
        next_state="PROVE/RUN_TESTS",
        verifier_requirement="measured_tests",
    )
    parsed = parse_arena_state_packet(encoded)
    assert parsed["ok"]
    assert parsed["state"]["phase_hash"] == state.phase_hash
    assert parsed["canonical_identity"][0] == "human_agent"
    tampered = encoded[:-1] + ("0" if encoded[-1] != "0" else "1")
    assert not parse_arena_state_packet(tampered)["ok"]


def test_repository_manifests_compile():
    root = Path(__file__).resolve().parents[1]
    for relative in (
        ".aura/arena_routes/human_agent.v1.json",
        ".aura/arena_routes/meta.v1.json",
    ):
        result = load_and_compile_arena_grammar(root / relative)
        assert result.ok, [item.to_dict() for item in result.diagnostics]


def test_audit_uses_canonical_record_trace_event(monkeypatch, tmp_path):
    calls = []

    class Atom:
        atom_id = "AT-test"

    module = types.ModuleType("aura_symbolic_trace_memory")

    def record_trace_event(event, memory_root):
        calls.append((event, memory_root))
        return Atom()

    module.record_trace_event = record_trace_event
    monkeypatch.setitem(sys.modules, "aura_symbolic_trace_memory", module)
    result = audit.record_gate_transition("A", "B", {"proof": True}, repo_root=str(tmp_path))
    assert result["persistent"] is True
    assert result["trace_atom_id"] == "AT-test"
    assert calls[0][0]["event_type"] == "gate_transition"
    assert str(calls[0][1]).endswith("Aura_Memory/symbolic_trace")


def test_audit_surfaces_persistence_failure(monkeypatch, tmp_path):
    module = types.ModuleType("aura_symbolic_trace_memory")

    def record_trace_event(event, memory_root):
        raise OSError("disk unavailable")

    module.record_trace_event = record_trace_event
    monkeypatch.setitem(sys.modules, "aura_symbolic_trace_memory", module)
    result = audit.record_verifier_result({"ok": True}, repo_root=str(tmp_path))
    assert result["ok"] is True
    assert result["persistent"] is False
    assert result["persistence_error"] == "symbolic_trace_persistence_failed:OSError"
