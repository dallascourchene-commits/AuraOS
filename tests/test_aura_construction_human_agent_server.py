"""HTTP-surface tests for the Construction Human Agent profile."""
from __future__ import annotations

from pathlib import Path

from aura_human_agent_arena_server import HumanAgentArenaServerState, dispatch_api_request


HEAD = "a" * 40


def test_demo_server_exposes_profile_observatory_candidate_and_handoff(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    try:
        status, summary = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/status"
        )
        assert status == 200
        assert summary["available"] is True
        assert summary["read_only"] is True

        status, profile_result = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/profile"
        )
        assert status == 200
        profile = profile_result["profile"]
        assert profile["raw_records_included"] is False
        assert profile["physical_work_authorized"] is False
        assert profile["payment_released"] is False

        blocked = next(item for item in profile["candidates"] if not item["admissible"])
        status, candidate = dispatch_api_request(
            state,
            "GET",
            f"/api/human-agent/construction/candidates/{blocked['candidate_id']}",
        )
        assert status == 200
        assert candidate["candidate"]["blockers"]
        assert candidate["raw_records_included"] is False

        status, observatory = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/observatory"
        )
        assert status == 200
        assert observatory["execution_methods"] == []
        assert observatory["payload_included"] is False
        assert "projected_cost_delta_cad" not in str(observatory)

        status, handoff = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/handoff",
            {"target_arena_id": "agent_bridge_arena"},
        )
        assert status == 200
        assert handoff["digital_baton_only"] is True
        assert handoff["target_arena_mutated"] is False
    finally:
        state.close()


def test_demo_server_checkpoints_exact_state_and_binds_profile_reference(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    try:
        status, stored = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/checkpoint",
            {"repo_head": HEAD, "branch_name": "human-review"},
        )
        assert status == 200
        checkpoint_id = stored["checkpoint"]["checkpoint_id"]
        assert checkpoint_id
        assert stored["profile_id"]
        assert stored["profile_digest"]

        status, profile_result = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/profile"
        )
        assert status == 200
        assert profile_result["profile"]["checkpoint_id"] == checkpoint_id

        status, missing_head = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/checkpoint",
            {},
        )
        assert status == 400
        assert missing_head["error"] == "repo_head is required"
    finally:
        state.close()


def test_non_demo_server_does_not_invent_construction_state(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=False)
    try:
        status, summary = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/status"
        )
        assert status == 200
        assert summary["available"] is False

        status, profile = dispatch_api_request(
            state, "GET", "/api/human-agent/construction/profile"
        )
        assert status == 404
        assert profile["ok"] is False

        status, checkpoint = dispatch_api_request(
            state,
            "POST",
            "/api/human-agent/construction/checkpoint",
            {"repo_head": HEAD},
        )
        assert status == 404
        assert checkpoint["ok"] is False
    finally:
        state.close()


def test_main_state_and_browser_surface_advertise_bounded_construction_profile(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    try:
        status, payload = dispatch_api_request(state, "GET", "/api/human-agent/state")
        assert status == 200
        assert payload["construction_profile"]["available"] is True
        assert payload["construction_profile"]["physical_work_authorized"] is False
    finally:
        state.close()

    repo_root = Path(__file__).resolve().parents[1]
    index = (repo_root / "aura_human_agent_arena/index.html").read_text(encoding="utf-8")
    script = (repo_root / "aura_human_agent_arena/construction.js").read_text(encoding="utf-8")
    assert 'data-surface="construction-workspace"' in index
    assert 'id="construction-workspace"' in index
    assert 'src="construction.js"' in index
    assert "/api/human-agent/construction/observatory" in script
    assert "authorize physical work" not in script
