import json
from pathlib import Path

import aura_coding_arena_3d
from aura_arena_st3gg_codec import (
    PATCH_AUTHORITY,
    encode_arena_capsule_for_egress,
    retrieve_arena_capsule,
    should_st3gg_encode_arena_capsule,
)
from aura_coding_arena_3d import compile_action_capsule, demo_topology


def _small_capsule() -> dict:
    return {
        "capsule_version": "demo",
        "op": "inspect",
        "selected": {"node_ids": ["a.py::f"]},
        "context": {"target_files": ["a.py"], "target_symbols": ["f"]},
        "phase_hash": "small",
    }


def _large_capsule() -> dict:
    repeated_neighbors = [
        {
            "id": f"module.py::symbol_{index}",
            "file_path": "module.py",
            "symbol": f"symbol_{index}",
            "node_type": "function",
            "summary": "deterministic repeated topology evidence " * 8,
        }
        for index in range(80)
    ]
    return {
        "capsule_version": "AURA_CODING_ARENA_CAPSULE_V1",
        "op": "patch",
        "selected": {"node_ids": ["module.py::symbol_1"]},
        "context": {
            "target_files": ["module.py"],
            "target_symbols": ["symbol_1"],
            "line_ranges": [{"node_id": "module.py::symbol_1", "file_path": "module.py", "line_range": [1, 20]}],
            "tests": ["test_module.py"],
            "neighbors": repeated_neighbors,
        },
        "route_decision": {"route": "LOCAL_DETERMINISTIC", "network_calls_made": False},
        "jspace_packet": "J0/S=code>A=patch#READY_PATCH",
        "jspace_state": {
            "next_state": "READY_PATCH",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
        },
        "phase_hash": "large",
    }


def _has_forbidden_carrier(text: str) -> bool:
    for ch in text:
        codepoint = ord(ch)
        if codepoint in range(0xE0000, 0xE0080):
            return True
        if codepoint in range(0xE000, 0xF900) or codepoint in range(0xF0000, 0x110000):
            return True
        if codepoint in range(0xFE00, 0xFE10) or codepoint in range(0xE0100, 0xE01F0):
            return True
        if codepoint in range(0x202A, 0x202F) or codepoint in range(0x2066, 0x206A):
            return True
        if codepoint in (0x200B, 0x200C, 0x200D, 0x2060):
            return True
    return False


def test_small_capsule_does_not_encode(tmp_path: Path):
    view = encode_arena_capsule_for_egress(_small_capsule(), recall_root=tmp_path)

    assert view.decision.enabled is False
    assert view.payload == ""
    assert view.decision.reason in {"below_min_raw_chars", "compact_not_smaller", "below_savings_threshold"}


def test_large_repeated_capsule_encodes(tmp_path: Path):
    view = encode_arena_capsule_for_egress(_large_capsule(), recall_root=tmp_path)

    assert view.decision.enabled is True
    assert view.payload.startswith("ST3GG1|")
    assert view.retrieval_marker
    assert view.original_hash
    assert view.decision.savings_ratio >= 0.08


def test_encoded_payload_is_visible_ascii(tmp_path: Path):
    view = encode_arena_capsule_for_egress(_large_capsule(), recall_root=tmp_path)

    view.payload.encode("ascii")
    assert all(32 <= ord(ch) <= 126 for ch in view.payload)


def test_encoded_payload_contains_no_hidden_unicode_carriers(tmp_path: Path):
    capsule = _large_capsule()
    capsule["context"]["neighbors"][0]["summary"] += "\u200b\U000e0041\ue000\u202e\ufe0f"

    view = encode_arena_capsule_for_egress(capsule, recall_root=tmp_path)

    assert not _has_forbidden_carrier(view.payload)
    assert any("tokenizer_guard_removed" in warning for warning in view.decision.warnings)


def test_retrieve_arena_capsule_restores_original_from_pointer_and_hash(tmp_path: Path):
    original = _large_capsule()
    view = encode_arena_capsule_for_egress(original, recall_root=tmp_path)

    by_pointer = retrieve_arena_capsule(view.decision.st3gg_pointer or "", recall_root=tmp_path)
    by_hash = retrieve_arena_capsule(view.original_hash or "", recall_root=tmp_path)

    assert by_pointer == original
    assert by_hash == original


def test_decision_reports_positive_savings_only_when_compact_payload_is_smaller():
    small = should_st3gg_encode_arena_capsule(_small_capsule(), min_raw_chars=0)
    large = should_st3gg_encode_arena_capsule(_large_capsule(), min_raw_chars=0)

    assert small.compact_tokens_est >= small.raw_tokens_est
    assert small.savings_ratio == 0.0
    assert large.compact_tokens_est < large.raw_tokens_est
    assert large.savings_ratio > 0


def test_egress_payload_preserves_patch_authority_flags(tmp_path: Path):
    view = encode_arena_capsule_for_egress(_large_capsule(), recall_root=tmp_path)

    assert f"AUTH={PATCH_AUTHORITY}" in view.payload
    assert "VSA_AUTH=false" in view.payload


def test_compile_action_capsule_includes_st3gg_egress(tmp_path: Path):
    graph = demo_topology(tmp_path)
    capsule = compile_action_capsule(graph, [graph["nodes"][0]["id"]], human_instruction="compile capsule")
    egress = capsule["st3gg_egress"]

    assert "decision" in egress
    assert egress["patch_authority"] == PATCH_AUTHORITY
    assert egress["vsa_patch_authority"] is False
    json.dumps(capsule)


def test_compile_action_capsule_continues_when_st3gg_fails(monkeypatch, tmp_path: Path):
    def fail_encode(*args, **kwargs):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(aura_coding_arena_3d, "encode_arena_capsule_for_egress", fail_encode)
    graph = demo_topology(tmp_path)

    capsule = aura_coding_arena_3d.compile_action_capsule(
        graph,
        [graph["nodes"][0]["id"]],
        human_instruction="compile capsule",
    )

    assert capsule["capsule_version"] == "AURA_CODING_ARENA_CAPSULE_V1"
    assert capsule["st3gg_egress"]["enabled"] is False
    assert capsule["st3gg_egress"]["decision"]["reason"] == "st3gg_encode_failed:RuntimeError"
