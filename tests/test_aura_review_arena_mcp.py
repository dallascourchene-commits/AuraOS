from __future__ import annotations

import json

from aura_agent_arena_mcp import TOOL_DEFINITIONS, handle_request


class FakeReviewBridge:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def _record(self, name: str, **kwargs):
        self.calls.append((name, kwargs))
        return {"ok": True, "tool": name, **kwargs}

    def aura_review_prepare(self, request):
        return self._record("prepare", request=request)

    def aura_review_scan(self, review_id: str):
        return self._record("scan", review_id=review_id)

    def aura_review_agent_packet(self, review_id: str, **kwargs):
        return self._record("agent_packet", review_id=review_id, **kwargs)

    def aura_review_submit_findings(self, review_id: str, findings, agent_name: str):
        return self._record(
            "submit_findings",
            review_id=review_id,
            findings=findings,
            agent_name=agent_name,
        )

    def aura_review_finalize(self, review_id: str):
        return self._record("finalize", review_id=review_id)

    def aura_review_status(self, review_id: str):
        return self._record("status", review_id=review_id)


def _call(bridge: FakeReviewBridge, name: str, arguments: dict) -> dict:
    response = handle_request(
        bridge,  # type: ignore[arg-type]
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )
    assert response is not None
    assert "result" in response
    return json.loads(response["result"]["content"][0]["text"])


def test_review_tools_are_advertised() -> None:
    names = {item["name"] for item in TOOL_DEFINITIONS}
    assert {
        "aura_review_prepare",
        "aura_review_scan",
        "aura_review_agent_packet",
        "aura_review_submit_findings",
        "aura_review_finalize",
        "aura_review_status",
    }.issubset(names)


def test_review_prepare_dispatches_complete_request() -> None:
    bridge = FakeReviewBridge()
    result = _call(
        bridge,
        "aura_review_prepare",
        {
            "objective": "Review malformed packets",
            "mode": "range",
            "base_ref": "main",
            "head_ref": "feature/x",
            "profile": "precision",
            "focus_directives": [{"name": "packets", "question": "Do packets fail closed?"}],
            "run_tests": False,
        },
    )
    assert result["ok"] is True
    request = result["request"]
    assert request["objective"] == "Review malformed packets"
    assert request["focus_directives"][0]["name"] == "packets"
    assert request["run_tests"] is False


def test_review_lifecycle_tools_dispatch() -> None:
    bridge = FakeReviewBridge()
    scan = _call(bridge, "aura_review_scan", {"review_id": "REVIEW-1"})
    packet = _call(
        bridge,
        "aura_review_agent_packet",
        {"review_id": "REVIEW-1", "include_source": True, "max_files": 8},
    )
    submitted = _call(
        bridge,
        "aura_review_submit_findings",
        {
            "review_id": "REVIEW-1",
            "agent_name": "hermes",
            "findings": [{"title": "x"}],
        },
    )
    final = _call(bridge, "aura_review_finalize", {"review_id": "REVIEW-1"})
    status = _call(bridge, "aura_review_status", {"review_id": "REVIEW-1"})

    assert scan["tool"] == "scan"
    assert packet["include_source"] is True
    assert submitted["agent_name"] == "hermes"
    assert final["tool"] == "finalize"
    assert status["tool"] == "status"


def test_plain_ok_false_review_result_sets_mcp_is_error() -> None:
    class FailingBridge(FakeReviewBridge):
        def aura_review_scan(self, review_id: str):
            return {"ok": False, "error": "review_not_found", "review_id": review_id}

    response = handle_request(
        FailingBridge(),  # type: ignore[arg-type]
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "aura_review_scan", "arguments": {"review_id": "missing"}},
        },
    )
    assert response is not None
    assert response["result"]["isError"] is True
