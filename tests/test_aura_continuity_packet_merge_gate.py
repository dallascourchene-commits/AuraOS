from __future__ import annotations

import base64
import json

import pytest

from aura_arena_state_packet import (
    ARENA_STATE_PACKET_VERSION,
    build_arena_state_packet,
    parse_arena_state_packet,
)
from aura_continuity_packet import (
    J2ArenaView,
    J2RouteView,
    arena_view_from_j1,
    build_j2_continuity_packet,
    parse_continuity_packet,
    parse_j2_continuity_packet,
)
from aura_event_contracts import PATCH_AUTHORITY, stable_digest


def _j2_packet() -> str:
    route_view = J2RouteView(
        route="PLAN_ONLY",
        next_state="PLAN_ONLY",
        verifier_required=False,
        phase_digest=stable_digest({"route_phase": "plan"}),
        source_packet_digest=stable_digest({"route_source": "j0"}),
        active_concept_digests=(),
        active_concept_count=0,
    )
    arena_view = J2ArenaView(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PLAN",
        substate="",
        state_code="PLAN",
        selected_transition="",
        next_state="PLAN",
        verifier_requirement="none",
        focus_digest="",
        evidence_digest="",
        policy_digest="",
        lease_digest="",
        repository_commit_ref="",
        working_tree_digest="",
        phase_digest=stable_digest({"arena_phase": "plan"}),
        source_packet_digest=stable_digest({"arena_source": "j1"}),
    )
    _packet, encoded = build_j2_continuity_packet(
        trace_id="trace-merge-gate",
        board_id="board-merge-gate",
        board_digest=stable_digest({"board": "merge-gate"}),
        history_chain_id="planning-chain-merge-gate",
        history_projection_digest=stable_digest({"projection": "merge-gate"}),
        continuity_report_digest=stable_digest({"continuity": "merge-gate"}),
        event_refs=("event-board",),
        route_view=route_view,
        arena_view=arena_view,
    )
    return encoded


def _j1_packet() -> str:
    _state, encoded = build_arena_state_packet(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PROVE",
        state_code="PROVE",
    )
    return encoded


def _tamper_j1_excluded_field(raw_packet: str, field_name: str, value: object) -> str:
    body = raw_packet.removeprefix("J1/")
    encoded, supplied_hash = body.rsplit("#", 1)
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    payload = json.loads(
        base64.urlsafe_b64decode((encoded + padding).encode("ascii")).decode("utf-8")
    )
    payload[field_name] = value
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    tampered = base64.urlsafe_b64encode(canonical).decode("ascii").rstrip("=")
    return f"J1/{tampered}#{supplied_hash}"


@pytest.mark.parametrize("wrapper", [" {}", "{} ", "\n{}"])
def test_j2_rejects_outer_whitespace_aliases(wrapper: str) -> None:
    encoded = _j2_packet()
    aliased = wrapper.format(encoded)

    expected = {"ok": False, "error": "j2_noncanonical_outer_whitespace"}
    assert parse_j2_continuity_packet(aliased) == expected
    assert parse_continuity_packet(aliased) == expected


def test_j2_parser_rejects_non_string_input_without_coercion() -> None:
    assert parse_j2_continuity_packet(123) == {
        "ok": False,
        "error": "j2_packet_not_string",
    }


def test_j2_parser_fails_closed_on_excessive_nesting() -> None:
    deeply_nested_json = '{"level":' * 1200 + "0" + "}" * 1200
    encoded = base64.urlsafe_b64encode(deeply_nested_json.encode("utf-8")).decode(
        "ascii"
    ).rstrip("=")
    packet = f"J2/{encoded}#{'0' * 32}"

    expected = {"ok": False, "error": "j2_payload_too_deep"}
    assert parse_j2_continuity_packet(packet) == expected
    assert parse_continuity_packet(packet) == expected


def test_unified_parser_preserves_legacy_outer_whitespace_behavior() -> None:
    encoded = _j1_packet()
    assert parse_continuity_packet(f"  {encoded}\n") == parse_arena_state_packet(encoded)


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        ("packet_version", "FORGED_J1", "packet_version"),
        ("patch_authority", "model_may_patch", "patch_authority"),
        ("vsa_patch_authority", True, "cannot be patch authority"),
        ("vsa_patch_authority", 0, "must be a boolean"),
    ],
)
def test_j1_adapter_rejects_excluded_authority_field_tampering(
    field_name: str,
    value: object,
    message: str,
) -> None:
    tampered = _tamper_j1_excluded_field(_j1_packet(), field_name, value)

    # The legacy parser intentionally remains unchanged and its phase hash excludes
    # these compatibility fields. The stricter J2 adapter must therefore gate them.
    assert parse_arena_state_packet(tampered)["ok"] is True
    with pytest.raises(ValueError, match=message):
        arena_view_from_j1(tampered)


def test_j1_adapter_accepts_canonical_authority_constants() -> None:
    encoded = _j1_packet()
    parsed = parse_arena_state_packet(encoded)
    assert parsed["state"]["packet_version"] == ARENA_STATE_PACKET_VERSION
    assert parsed["state"]["patch_authority"] == PATCH_AUTHORITY
    assert parsed["state"]["vsa_patch_authority"] is False

    view = arena_view_from_j1(encoded)
    assert view.arena_id == "human_agent"
    assert view.phase == "PROVE"
