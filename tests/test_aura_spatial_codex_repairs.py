from __future__ import annotations

from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sqlite3
import sys

import pytest

from aura_agent_arena_mcp import serve_stdio
from aura_event_contracts import stable_digest, stable_id
from aura_spatial_agent_bridge import AuraSpatialAgentBridge
from tests.test_aura_spatial_s5_arena import _construction_packet, _prepared, _repo


def _attempt_count(root: Path) -> int:
    db_path = root / "Aura_Memory" / "arena_attempt_artifacts.db"
    with sqlite3.connect(db_path) as connection:
        return int(connection.execute("SELECT COUNT(*) FROM arena_attempt_artifacts").fetchone()[0])


@pytest.mark.parametrize(
    "metrics",
    [
        {"camera_frame": "raw-pixels"},
        {"frame_ms": {"value": 4.0}},
        {"fixture": "data:image/png;base64,secret"},
        {"rendered_entities": False},
        {"fixture": b"synthetic"},
        {"frame_ms": float("inf")},
    ],
)
def test_generic_spatial_proof_rejects_raw_or_structured_metrics_before_archive(
    tmp_path: Path,
    metrics: dict[str, object],
) -> None:
    _, _, arena, bridge, prepared = _prepared(tmp_path)
    try:
        before = _attempt_count(tmp_path)
        with pytest.raises(ValueError, match="generic Spatial proof metric"):
            bridge.prove(prepared["run_id"], repo_head="a" * 40, metrics=metrics)
        assert _attempt_count(tmp_path) == before
        assert arena._runs[prepared["run_id"]].proof_receipt_ids == []
    finally:
        bridge.close()


def test_generic_spatial_proof_metrics_are_scalar_sorted_and_archived(tmp_path: Path) -> None:
    _, _, _, bridge, prepared = _prepared(tmp_path)
    expected = {
        "fixture": "synthetic",
        "frame_ms": 4.0,
        "rendered_entities": len(prepared["scene"]["entities"]),
        "renderer_allocated": False,
    }
    try:
        proof = bridge.prove(
            prepared["run_id"],
            repo_head="b" * 40,
            metrics=dict(reversed(tuple(expected.items()))),
        )
        observed = proof["render_receipt"]["metrics"]
        assert observed == expected
        assert list(observed) == sorted(observed)
        db_path = tmp_path / "Aura_Memory" / "arena_attempt_artifacts.db"
        with sqlite3.connect(db_path) as connection:
            raw = connection.execute(
                "SELECT result_json FROM arena_attempt_artifacts ORDER BY created_at DESC LIMIT 1"
            ).fetchone()[0]
        assert json.loads(raw)["receipt"]["metrics"] == expected
    finally:
        bridge.close()


def test_default_stdio_server_uses_persistent_bridge_for_spatial_tools(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "aura_spatial_status",
            "arguments": {"run_id": "spatial-run:missing"},
        },
    }
    stdin = StringIO(json.dumps(request) + "\n")
    stdout = StringIO()
    monkeypatch.chdir(root)
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    serve_stdio()
    response = json.loads(stdout.getvalue().strip())
    assert response["error"]["code"] == -32603
    assert "unknown or dissolved Spatial Arena run" in response["error"]["message"]
    assert "AttributeError" not in response["error"]["message"]


def _redigest_evaluation(packet: dict[str, object]) -> None:
    evaluation = dict(packet["evaluation"])
    payload = dict(evaluation)
    payload.pop("evaluation_id", None)
    payload.pop("evaluation_digest", None)
    evaluation["evaluation_id"] = stable_id("construction-evaluation", payload)
    evaluation["evaluation_digest"] = stable_digest(payload)
    packet["evaluation"] = evaluation


def test_construction_prepare_accepts_exact_canonical_json_copy(tmp_path: Path) -> None:
    fixture, packet = _construction_packet()
    bridge = AuraSpatialAgentBridge(_repo(tmp_path))
    try:
        prepared = bridge.prepare_construction_projection(
            objective="review canonical Construction packet",
            state=fixture.state,
            construction_runtime_packet=json.loads(json.dumps(packet)),
        )
        assert prepared["status"]["phase"] == "PRESENT"
    finally:
        bridge.close()


def test_construction_prepare_rejects_recomputed_noncanonical_substitutions(tmp_path: Path) -> None:
    fixture, packet = _construction_packet()
    mutations: list[dict[str, object]] = []

    assessment = deepcopy(packet)
    assessment["evaluation"]["assessments"][0]["uncertainty"] = 0.123
    _redigest_evaluation(assessment)
    mutations.append(assessment)

    candidate = deepcopy(packet)
    candidate["evaluation"]["assessments"][0]["candidate_id"] = "construction-candidate:" + "0" * 40
    _redigest_evaluation(candidate)
    mutations.append(candidate)

    recommendation = deepcopy(packet)
    recommendation["evaluation"]["recommended_candidate_id"] = ""
    recommendation["evaluation"]["next_authority_route"] = ""
    _redigest_evaluation(recommendation)
    mutations.append(recommendation)

    action = deepcopy(packet)
    action["action_capsule"]["objective"] = "forged objective"
    mutations.append(action)

    boundary = deepcopy(packet)
    boundary["boundary_contract"]["promised_outputs"].append("forged authoritative output")
    mutations.append(boundary)

    lease = deepcopy(packet)
    lease["arena_lease"]["holder"] = "forged-holder"
    mutations.append(lease)

    release = deepcopy(packet)
    release["patch_authority"] = "full_repository"
    mutations.append(release)

    bridge = AuraSpatialAgentBridge(_repo(tmp_path))
    try:
        for mutated in mutations:
            with pytest.raises(ValueError, match="canonical Construction adapter"):
                bridge.prepare_construction_projection(
                    objective="reject forged Construction packet",
                    state=fixture.state,
                    construction_runtime_packet=mutated,
                )
    finally:
        bridge.close()
