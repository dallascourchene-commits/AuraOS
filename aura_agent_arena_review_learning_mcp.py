"""MCP extension exposing typed Coding Waboose review-learning tools.

Base Agent Bridge tools are delegated unchanged. Only four review-learning
projections are added, each review-only and non-mutating.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import sys
from typing import Any

from aura_agent_arena_mcp import PROTOCOL_VERSION, SERVER_INFO
from aura_agent_arena_mcp import TOOL_DEFINITIONS as BASE_TOOL_DEFINITIONS
from aura_agent_arena_mcp import handle_request as handle_base_request
from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge

MCP_REVIEW_LEARNING_VERSION = "AURA_AGENT_ARENA_REVIEW_LEARNING_MCP_V1"

REVIEW_LEARNING_TOOL_DEFINITIONS = [
    {
        "name": "aura_waboose_ingest_external_review",
        "description": "Normalize and store bounded CodeRabbit, Codex, or manual review evidence.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "review_payload": {"type": "object"},
                "current_head": {"type": "string"},
            },
            "required": ["review_payload"],
        },
    },
    {
        "name": "aura_waboose_review_lesson_summary",
        "description": "Return typed review-lesson registry and detector status.",
        "inputSchema": {"type": "object", "additionalProperties": False, "properties": {}},
    },
    {
        "name": "aura_waboose_run_review_detector",
        "description": "Run one bounded deterministic review-lesson detector.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "detector_id": {"type": "string"},
                "candidate": {},
            },
            "required": ["detector_id", "candidate"],
        },
    },
    {
        "name": "aura_waboose_crucible_replay",
        "description": "Replay selected or all PR164 review lessons and emit receipts.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "detector_ids": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
]


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def handle_request(
    bridge: ReviewLearningAgentArenaBridge,
    request: dict[str, Any],
) -> dict[str, Any] | None:
    request_id = request.get("id")
    method = str(request.get("method") or "")
    params = request.get("params") or {}
    if not isinstance(params, Mapping):
        return _error(request_id, -32602, "params must be an object")
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {**SERVER_INFO, "reviewLearningVersion": MCP_REVIEW_LEARNING_VERSION},
            },
        )
    if method == "tools/list":
        return _response(
            request_id,
            {"tools": [*BASE_TOOL_DEFINITIONS, *REVIEW_LEARNING_TOOL_DEFINITIONS]},
        )
    if method != "tools/call":
        return handle_base_request(bridge, request)
    tool_name = str(params.get("name") or "")
    arguments = params.get("arguments") or {}
    if not isinstance(arguments, Mapping):
        return _error(request_id, -32602, "tool arguments must be an object")
    try:
        if tool_name == "aura_waboose_ingest_external_review":
            payload = arguments.get("review_payload")
            if not isinstance(payload, Mapping):
                raise ValueError("review_payload must be an object")
            result = bridge.aura_waboose_ingest_external_review(
                dict(payload),
                current_head=str(arguments.get("current_head") or ""),
            )
        elif tool_name == "aura_waboose_review_lesson_summary":
            result = bridge.aura_waboose_review_lesson_summary()
        elif tool_name == "aura_waboose_run_review_detector":
            result = bridge.aura_waboose_run_review_detector(
                str(arguments.get("detector_id") or ""),
                arguments.get("candidate"),
            )
        elif tool_name == "aura_waboose_crucible_replay":
            raw = arguments.get("detector_ids") or []
            if isinstance(raw, (str, bytes)) or not isinstance(raw, list):
                raise ValueError("detector_ids must be an array")
            result = bridge.aura_waboose_crucible_replay([str(item) for item in raw])
        else:
            return handle_base_request(bridge, request)
        return _response(
            request_id,
            {
                "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}],
                "isError": (
                    isinstance(result, Mapping)
                    and (result.get("ok") is False or result.get("status") == "FAILED")
                ),
            },
        )
    except Exception as exc:
        return _error(request_id, -32603, f"Tool execution error: {exc}")


def serve_stdio(bridge: ReviewLearningAgentArenaBridge | None = None) -> None:
    runtime = bridge or ReviewLearningAgentArenaBridge()
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle_request(runtime, request)
        if response is not None:
            sys.stdout.write(json.dumps(response, default=str) + "\n")
            sys.stdout.flush()


def main() -> int:
    serve_stdio()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
