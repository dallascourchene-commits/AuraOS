from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
from aura_jspace_codec import (
    active_concepts_from_packet,
    attach_jspace_to_capsule,
    build_jspace_packet,
    next_state_for_decision,
    parse_jspace_packet,
)


def _ready_grounding() -> dict:
    return {
        "route": "BUILDER_PATCH",
        "source_spans": [
            {
                "role": "target",
                "file_path": "demo.py",
                "symbol": "answer",
                "start_line": 1,
                "end_line": 2,
                "source_hash": "abc123",
            }
        ],
        "tests": ["test_demo.py"],
        "hashes": {"demo.py": "filehash", "demo.py#function:answer": "abc123"},
        "safety_policy": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }


def _ready_frame() -> RoutingFrame:
    return RoutingFrame(
        intent="code_refactor",
        artifact="python_module",
        action="modify",
        scope="symbol",
        risk="medium",
        grounding=("file_exists", "symbol_exists", "codemap_grounded", "tests_exist"),
        tests="existing",
        quality="balanced",
        cost="local_first",
        target_file="demo.py",
        target_symbol="answer",
    )


def test_routing_frame_compact_input_is_deterministic_and_shorter_than_symbol_input() -> None:
    frame = _ready_frame()

    assert frame.compact_input() == frame.compact_input()
    assert len(frame.compact_input()) < len(frame.symbol_input())


def test_route_decision_compact_output_is_deterministic_and_shorter_than_symbol_output() -> None:
    frame = _ready_frame()
    decision = AuraCodingArenaRouter().route(frame)

    assert decision.compact_output() == decision.compact_output()
    assert len(decision.compact_output()) < len(decision.symbol_output())


def test_build_jspace_packet_returns_expected_ready_patch_form() -> None:
    frame = _ready_frame()
    decision = AuraCodingArenaRouter().route(frame)

    packet = build_jspace_packet(frame, decision, grounding=_ready_grounding())

    assert packet.packet == f"J0/{frame.compact_input()}>{decision.compact_output()}#READY_PATCH"


def test_parse_jspace_packet_round_trips_compact_parts() -> None:
    frame = _ready_frame()
    decision = AuraCodingArenaRouter().route(frame)
    packet = build_jspace_packet(frame, decision, grounding=_ready_grounding())

    parsed = parse_jspace_packet(packet.packet)

    assert parsed["input_compact"] == packet.input_compact
    assert parsed["output_compact"] == packet.output_compact
    assert parsed["next_state"] == "READY_PATCH"


def test_active_concepts_are_sparse_and_policy_defaults_are_safe() -> None:
    frame = _ready_frame()
    decision = AuraCodingArenaRouter().route(frame)
    packet = build_jspace_packet(frame, decision, grounding=_ready_grounding())

    state = active_concepts_from_packet(packet)

    assert len(state.active_concepts) <= 25
    assert state.vsa_patch_authority is False
    assert state.patch_authority == "exact_source_spans_and_hashes_only"


def test_route_next_state_mappings_are_deterministic() -> None:
    assert next_state_for_decision({"route": "TEST_GAP_FILL"}) == "NEED_TEST"
    assert next_state_for_decision({"route": "EXTERNAL_CALL_CONTEXT"}) == "READ_ONLY_CONTEXT"
    assert next_state_for_decision({"route": "EMERGENT_CAPABILITY_AUDIT"}) == "READ_ONLY_AUDIT"
    assert next_state_for_decision({"route": "BLOCKED_WITH_REASON"}) == "BLOCKED"


def test_attach_jspace_to_capsule_preserves_existing_keys_and_adds_state() -> None:
    frame = _ready_frame()
    decision = AuraCodingArenaRouter().route(frame)
    capsule = {"capsule_version": "demo", "existing": {"value": 1}}

    attached = attach_jspace_to_capsule(capsule, frame=frame, decision=decision, grounding=_ready_grounding())

    assert attached["capsule_version"] == "demo"
    assert attached["existing"] == {"value": 1}
    assert attached["jspace_packet"].startswith("J0/")
    assert attached["jspace_state"]["next_state"] == "READY_PATCH"
    assert attached["jspace_state"]["vsa_patch_authority"] is False
