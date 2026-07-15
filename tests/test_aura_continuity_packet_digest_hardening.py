from __future__ import annotations

import base64
import json
import re

import pytest

from aura_arena_state_packet import build_arena_state_packet
from aura_continuity_packet import (
    J2RouteView,
    arena_view_from_j1,
    parse_j2_continuity_packet,
    route_view_from_j0,
)
from aura_event_contracts import canonical_json, stable_digest
from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
from aura_jspace_codec import AuraJPacket, build_jspace_packet

_DIGEST_RE = re.compile(r"[0-9a-f]{32}")


def _j0_packet():
    frame = RoutingFrame(
        intent="code_refactor",
        artifact="python_module",
        action="modify",
        scope="symbol",
        risk="medium",
        grounding=(
            "file_exists",
            "symbol_exists",
            "codemap_grounded",
            "tests_exist",
        ),
        tests="existing",
        quality="balanced",
        cost="local_first",
        target_file="demo.py",
        target_symbol="answer",
    )
    decision = AuraCodingArenaRouter().route(frame)
    return build_jspace_packet(
        frame,
        decision,
        grounding={
            "route": "BUILDER_PATCH",
            "source_spans": [
                {
                    "file_path": "demo.py",
                    "symbol": "answer",
                    "start_line": 1,
                    "end_line": 2,
                    "source_hash": "abc123",
                }
            ],
            "tests": ["test_demo.py"],
            "hashes": {"demo.py": "filehash"},
        },
    )


def _encode_payload(payload: dict) -> str:
    text = canonical_json(payload)
    encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    return f"J2/{encoded}#{stable_digest(payload)}"


def test_j0_adapter_ignores_unbound_aurajpacket_metadata() -> None:
    source = _j0_packet()
    forged = AuraJPacket(
        version="FORGED",
        input_compact="forged-input",
        output_compact="forged-output",
        next_state="FORGED_STATE",
        packet=source.packet,
        phase_hash="0" * 32,
        warnings=("forged-warning",),
    )

    from_string = route_view_from_j0(source.packet)
    from_forged_object = route_view_from_j0(forged)

    assert from_forged_object == from_string
    assert from_forged_object.phase_digest != forged.phase_hash
    assert _DIGEST_RE.fullmatch(from_forged_object.phase_digest)
    assert _DIGEST_RE.fullmatch(from_forged_object.source_packet_digest)


def test_j1_adapter_hashes_legacy_digest_fields_instead_of_copying_values() -> None:
    legacy_values = {
        "focus_digest": "focus payload accidentally mislabeled as digest",
        "evidence_digest": "evidence payload accidentally mislabeled as digest",
        "policy_digest": "policy payload accidentally mislabeled as digest",
        "lease_digest": "lease payload accidentally mislabeled as digest",
        "working_tree_digest": "working tree payload accidentally mislabeled as digest",
    }
    _state, raw = build_arena_state_packet(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PROVE",
        substate="RUN_TESTS",
        state_code="PROVE/RUN_TESTS",
        repository_commit="commit-ref",
        selected_transition="HUMAN.RUN_TESTS",
        next_state="PROVE/RUN_TESTS",
        verifier_requirement="measured_tests",
        **legacy_values,
    )

    view = arena_view_from_j1(raw)

    for field_name, legacy_value in legacy_values.items():
        projected = getattr(view, field_name)
        assert projected != legacy_value
        assert _DIGEST_RE.fullmatch(projected)
    assert view.repository_commit_ref == "commit-ref"
    assert _DIGEST_RE.fullmatch(view.phase_digest)
    assert _DIGEST_RE.fullmatch(view.source_packet_digest)


def test_digest_contracts_reject_labels_masquerading_as_digests() -> None:
    with pytest.raises(ValueError, match="32-character lowercase hexadecimal digest"):
        J2RouteView(
            route="BUILDER_PATCH",
            next_state="READY_PATCH",
            verifier_required=True,
            phase_digest="phase-digest",
            source_packet_digest="0" * 32,
            active_concept_digests=(),
            active_concept_count=0,
        )


def test_parser_rejects_recomputed_packet_with_invalid_nested_digest() -> None:
    source = _j0_packet()
    route = route_view_from_j0(source)
    _state, raw_j1 = build_arena_state_packet(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PROVE",
        state_code="PROVE",
    )
    arena = arena_view_from_j1(raw_j1)
    payload = {
        "arena_view": arena.to_dict(),
        "board_digest": stable_digest({"board": "j2"}),
        "board_id": "board-j2",
        "continuity_report_digest": stable_digest({"continuity": "j2"}),
        "event_refs": ["event_board"],
        "history_chain_id": "planning-chain-j2",
        "history_projection_digest": stable_digest({"projection": "j2"}),
        "patch_authority": "exact_source_spans_and_hashes_only",
        "proposal_only": True,
        "route_view": route.to_dict(),
        "trace_id": "trace-j2",
        "version": "AURA_CONTINUITY_PACKET_J2",
        "vsa_patch_authority": False,
    }
    payload["route_view"]["phase_digest"] = "not-a-digest"

    assert parse_j2_continuity_packet(_encode_payload(payload)) == {
        "ok": False,
        "error": "j2_contract_invalid",
    }
