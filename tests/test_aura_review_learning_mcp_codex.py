from __future__ import annotations

from typing import Any

from aura_agent_arena_review_learning_mcp import (
    REVIEW_LEARNING_TOOL_DEFINITIONS,
    handle_request,
)


class _Bridge:
    def aura_waboose_ingest_external_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "stored", "payload": payload}


def test_ingest_tool_schema_does_not_accept_current_head() -> None:
    ingest = next(
        tool for tool in REVIEW_LEARNING_TOOL_DEFINITIONS
        if tool["name"] == "aura_waboose_ingest_external_review"
    )
    assert "current_head" not in ingest["inputSchema"]["properties"]
    assert ingest["inputSchema"]["additionalProperties"] is False


def test_mcp_rejects_forged_current_head_argument() -> None:
    response = handle_request(
        _Bridge(),
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "aura_waboose_ingest_external_review",
                "arguments": {
                    "review_payload": {"head_sha": "a" * 40},
                    "current_head": "a" * 40,
                },
            },
        },
    )
    assert response is not None
    assert response["error"]["code"] == -32603
    assert "server-derived" in response["error"]["message"]
