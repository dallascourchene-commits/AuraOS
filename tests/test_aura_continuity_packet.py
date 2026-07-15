from __future__ import annotations

import base64
import json

import pytest

from aura_arena_state_packet import (
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
    route_view_from_j0,
)
from aura_event_contracts import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_json,
    stable_digest,
)
from aura_fst_routing import AuraCodingArenaRouter, RoutingFrame
from aura_jspace_codec import build_jspace_packet


def _grounding() -> dict:
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
        "hashes": {
            "demo.py": "filehash",
            "demo.py#function:answer": "abc123",
        },
        "safety_policy": PATCH_AUTHORITY,
        "vsa_patch_authority": False,
    }


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
    return build_jspace_packet(frame, decision, grounding=_grounding())


def _j1_packet() -> tuple[object, str]:
    return build_arena_state_packet(
        arena_id="human_agent",
        arena_version="v1",
        grammar_version="g1",
        phase="PROVE",
        substate="RUN_TESTS",
        state_code="PROVE/RUN_TESTS",
        focus_digest="focus-digest",
        evidence_digest="evidence-digest",
        policy_digest="policy-digest",
        lease_digest="lease-digest",
        repository_commit="commit-ref",
        working_tree_digest="tree-digest",
        selected_transition="HUMAN.RUN_TESTS",
        next_state="PROVE/RUN_TESTS",
        verifier_requirement="measured_tests",
    )


def _views() -> tuple[J2RouteView, J2ArenaView, str, str]:
    j0 = _j0_packet()
    _state, j1 = _j1_packet()
    return route_view_from_j0(j0), arena_view_from_j1(j1), j0.packet, j1


def _built():
    route_view, arena_view, j0, j1 = _views()
    packet, encoded = build_j2_continuity_packet(
        trace_id="trace-j2",
        board_id="board-j2",
        board_digest=stable_digest({"board": "j2"}),
        history_chain_id="planning-chain_j2",
        history_projection_digest=stable_digest({"projection": "j2"}),
        continuity_report_digest=stable_digest({"continuity": "j2"}),
        event_refs=("event_board", "event_regression", "event_frontier"),
        route_view=route_view,
        arena_view=arena_view,
    )
    return packet, encoded, j0, j1


def _decode_j2(encoded: str) -> tuple[dict, str]:
    body = encoded.removeprefix("J2/")
    payload_text, supplied_digest = body.rsplit("#", 1)
    padding = "=" * ((4 - len(payload_text) % 4) % 4)
    raw = base64.urlsafe_b64decode((payload_text + padding).encode("ascii"))
    return json.loads(raw.decode("utf-8")), supplied_digest


def _encode_payload(payload: dict, *, canonical: bool = True) -> str:
    text = (
        canonical_json(payload)
        if canonical
        else json.dumps(payload, sort_keys=False, separators=(", ", ": "))
    )
    encoded = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")
    return f"J2/{encoded}#{stable_digest(payload)}"


def _all_mapping_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = {str(key) for key in value}
        for item in value.values():
            keys.update(_all_mapping_keys(item))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_all_mapping_keys(item))
        return keys
    return set()


def test_j2_packet_is_deterministic_and_round_trips() -> None:
    first, first_encoded, _j0, _j1 = _built()
    second, second_encoded, _j0_second, _j1_second = _built()

    assert first.to_dict() == second.to_dict()
    assert first.digest == second.digest
    assert first_encoded == second_encoded

    parsed = parse_j2_continuity_packet(first_encoded)
    assert parsed["ok"] is True
    assert parsed["legacy"] is False
    assert parsed["state"] == first.to_dict()
    assert parsed["packet_digest"] == first.digest
    assert parsed["patch_authority"] == PATCH_AUTHORITY
    assert parsed["vsa_patch_authority"] is VSA_PATCH_AUTHORITY


def test_j2_adapters_store_digests_not_legacy_packet_payloads() -> None:
    packet, encoded, j0, j1 = _built()
    payload, _digest = _decode_j2(encoded)
    serialized = canonical_json(payload)
    keys = _all_mapping_keys(payload)

    assert j0 not in serialized
    assert j1 not in serialized
    assert packet.route_view.source_packet_digest == stable_digest(
        {"legacy_packet": j0}
    )
    assert packet.arena_view.source_packet_digest == stable_digest(
        {"legacy_packet": j1}
    )
    assert "source_spans" not in keys
    assert "policy_body" not in keys
    assert "lease_body" not in keys
    assert "goal" not in keys
    assert "actions" not in keys


def test_unified_parser_preserves_existing_j0_and_j1_results() -> None:
    j0 = _j0_packet().packet
    _state, j1 = _j1_packet()

    assert parse_continuity_packet(j0) == parse_arena_state_packet(j0)
    assert parse_continuity_packet(j1) == parse_arena_state_packet(j1)


def test_j2_suffix_tampering_fails_closed() -> None:
    _packet, encoded, _j0, _j1 = _built()
    prefix, digest = encoded.rsplit("#", 1)
    tampered_digest = ("0" if digest[0] != "0" else "1") + digest[1:]

    parsed = parse_j2_continuity_packet(f"{prefix}#{tampered_digest}")

    assert parsed == {"ok": False, "error": "j2_digest_suffix_mismatch"}


def test_j2_payload_tampering_with_original_digest_fails_closed() -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, supplied_digest = _decode_j2(encoded)
    payload["board_id"] = "board-tampered"
    text = canonical_json(payload)
    encoded_payload = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii").rstrip("=")

    parsed = parse_j2_continuity_packet(
        f"J2/{encoded_payload}#{supplied_digest}"
    )

    assert parsed == {"ok": False, "error": "j2_digest_suffix_mismatch"}


@pytest.mark.parametrize("field_name", ["private_reasoning", "api_key"])
def test_j2_sensitive_fields_are_rejected_before_schema_parsing(field_name: str) -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)
    payload[field_name] = "forbidden-value"

    parsed = parse_j2_continuity_packet(_encode_payload(payload))

    assert parsed == {"ok": False, "error": "j2_sensitive_field_forbidden"}


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("proposal_only", False),
        ("patch_authority", "model_may_patch"),
        ("vsa_patch_authority", True),
    ],
)
def test_j2_authority_tampering_fails_even_with_recomputed_digest(
    field_name: str,
    value: object,
) -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)
    payload[field_name] = value

    parsed = parse_j2_continuity_packet(_encode_payload(payload))

    assert parsed == {"ok": False, "error": "j2_contract_invalid"}


def test_noncanonical_j2_json_bytes_fail_closed() -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)

    parsed = parse_j2_continuity_packet(
        _encode_payload(payload, canonical=False)
    )

    assert parsed == {"ok": False, "error": "j2_noncanonical_payload"}


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("event_refs",), "event_board"),
        (("route_view", "active_concept_digests"), "concept-digest"),
    ],
)
def test_j2_array_fields_require_json_arrays(path: tuple[str, ...], value: object) -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    parsed = parse_j2_continuity_packet(_encode_payload(payload))

    assert parsed == {"ok": False, "error": "j2_schema_invalid"}


def test_legacy_adapters_reject_invalid_inputs_and_limits() -> None:
    with pytest.raises(ValueError, match="active_limit"):
        route_view_from_j0(_j0_packet(), active_limit=0)
    with pytest.raises(ValueError, match="valid J1"):
        arena_view_from_j1(_j0_packet().packet)
    with pytest.raises(ValueError, match="valid J1"):
        arena_view_from_j1("J1/not-valid")


def test_builder_rejects_secret_shaped_values() -> None:
    route_view, arena_view, _j0, _j1 = _views()
    with pytest.raises(ValueError, match="secret-shaped"):
        build_j2_continuity_packet(
            trace_id="trace-j2 api_key=super-secret-value-123456789",
            board_id="board-j2",
            board_digest=stable_digest({"board": "j2"}),
            history_chain_id="planning-chain_j2",
            history_projection_digest=stable_digest({"projection": "j2"}),
            continuity_report_digest=stable_digest({"continuity": "j2"}),
            event_refs=("event_board",),
            route_view=route_view,
            arena_view=arena_view,
        )


def test_parser_returns_stable_prefix_and_malformed_errors() -> None:
    assert parse_continuity_packet("K9/nope") == {
        "ok": False,
        "error": "unsupported_continuity_packet_prefix",
    }
    assert parse_j2_continuity_packet("J2/no-suffix") == {
        "ok": False,
        "error": "malformed_j2_packet",
    }
    assert parse_j2_continuity_packet("J2/***#abc") == {
        "ok": False,
        "error": "invalid_j2_base64",
    }


def _noncanonical_base64_alias(encoded_packet: str) -> str:
    body = encoded_packet.removeprefix("J2/")
    encoded, digest = body.rsplit("#", 1)
    padding = "=" * ((4 - len(encoded) % 4) % 4)
    raw = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    for character in alphabet:
        candidate = encoded[:-1] + character
        if candidate == encoded:
            continue
        candidate_padding = "=" * ((4 - len(candidate) % 4) % 4)
        try:
            decoded = base64.urlsafe_b64decode(
                (candidate + candidate_padding).encode("ascii")
            )
        except ValueError:
            continue
        if decoded == raw:
            return f"J2/{candidate}#{digest}"
    raise AssertionError("fixture did not expose an alternate base64url spelling")


def test_noncanonical_base64url_spelling_fails_closed() -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)
    for suffix in ("x", "xx", "xxx"):
        payload["trace_id"] = f"trace-j2-{suffix}"
        canonical_packet = _encode_payload(payload)
        canonical_body = canonical_packet.removeprefix("J2/").split("#", 1)[0]
        padding = "=" * ((4 - len(canonical_body) % 4) % 4)
        raw = base64.urlsafe_b64decode(
            (canonical_body + padding).encode("ascii")
        )
        if len(raw) % 3:
            break
    else:
        raise AssertionError("could not construct a padded base64url fixture")

    alias = _noncanonical_base64_alias(canonical_packet)

    assert parse_j2_continuity_packet(alias) == {
        "ok": False,
        "error": "j2_noncanonical_base64",
    }


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("trace_id",), {"unexpected": "object"}),
        (("arena_view", "arena_version"), 7),
        (("route_view", "route"), ["BUILDER_PATCH"]),
        (("event_refs",), ["event_board", 7]),
    ],
)
def test_j2_string_fields_reject_primitive_type_coercion(
    path: tuple[str, ...],
    value: object,
) -> None:
    _packet, encoded, _j0, _j1 = _built()
    payload, _digest = _decode_j2(encoded)
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    assert parse_j2_continuity_packet(_encode_payload(payload)) == {
        "ok": False,
        "error": "j2_contract_invalid",
    }


def test_builder_bounds_event_references() -> None:
    route_view, arena_view, _j0, _j1 = _views()
    with pytest.raises(ValueError, match="exceeds 64 entries"):
        build_j2_continuity_packet(
            trace_id="trace-j2",
            board_id="board-j2",
            board_digest=stable_digest({"board": "j2"}),
            history_chain_id="planning-chain_j2",
            history_projection_digest=stable_digest({"projection": "j2"}),
            continuity_report_digest=stable_digest({"continuity": "j2"}),
            event_refs=tuple(f"event_{index}" for index in range(65)),
            route_view=route_view,
            arena_view=arena_view,
        )


def test_parser_bounds_packet_size_and_digest_shape() -> None:
    assert parse_j2_continuity_packet(
        f"J2/{'A' * 32769}#{'0' * 32}"
    ) == {"ok": False, "error": "j2_packet_too_large"}
    assert parse_j2_continuity_packet("J2/e30#abc") == {
        "ok": False,
        "error": "invalid_j2_digest",
    }
