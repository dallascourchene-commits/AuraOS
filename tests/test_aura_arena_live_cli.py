"""Small deterministic tests for the live guarded Arena HTTP client."""
from __future__ import annotations

import pytest

from aura_arena_live_cli import _parse_payload, build_parser


def test_payload_parser_accepts_objects_and_rejects_other_json():
    assert _parse_payload('{"approved":true}') == {"approved": True}
    assert _parse_payload("") == {}
    with pytest.raises(ValueError):
        _parse_payload('["not", "an", "object"]')


def test_live_cli_declares_human_and_coding_commands():
    parser = build_parser()
    assert parser.parse_args(["human-routes"]).command == "human-routes"
    assert parser.parse_args(["human-command", "help"]).text == "help"
    assert parser.parse_args(["coding-routes"]).command == "coding-routes"
    assert parser.parse_args(["coding-action", "localize_code"]).action_id == "localize_code"
