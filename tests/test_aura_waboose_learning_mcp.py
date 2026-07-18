from __future__ import annotations

import json
from typing import Any

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request


class FakeBridge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def aura_waboose_learn_coderabbit(
        self,
        review_payload: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("learn", review_payload))
        return {
            "ok": True,
            "learned_count": 2,
            "teacher_is_patch_authority": False,
            "production_mutation": False,
        }

    def aura_waboose_learning_summary(self) -> dict[str, Any]:
        self.calls.append(("summary", {}))
        return {
            "ok": True,
            "episode_count": 4,
            "pattern_count": 2,
            "production_mutation": False,
        }


def _call(bridge: FakeBridge, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = handle_request(
        bridge,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response is not None
    return json.loads(response["result"]["content"][0]["text"])


def test_learning_tools_are_advertised() -> None:
    definitions = {item["name"]: item for item in TOOL_DEFINITIONS}
    assert "aura_waboose_learn_coderabbit" in definitions
    assert "aura_waboose_learning_summary" in definitions
    required = definitions["aura_waboose_learn_coderabbit"]["inputSchema"]["required"]
    assert required == ["review_payload"]


def test_learning_payload_dispatches_without_authority() -> None:
    bridge = FakeBridge()
    payload = {
        "success": True,
        "head_sha": "a" * 40,
        "findings": [{"file": "core.py", "line": 1}],
    }
    result = _call(
        bridge,
        "aura_waboose_learn_coderabbit",
        {"review_payload": payload},
    )
    assert result["ok"] is True
    assert result["teacher_is_patch_authority"] is False
    assert bridge.calls == [("learn", payload)]


def test_learning_summary_dispatches() -> None:
    bridge = FakeBridge()
    result = _call(bridge, "aura_waboose_learning_summary", {})
    assert result["episode_count"] == 4
    assert bridge.calls == [("summary", {})]
