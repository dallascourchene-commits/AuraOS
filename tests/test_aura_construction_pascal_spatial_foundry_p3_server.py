from __future__ import annotations

import json
from pathlib import Path

from aura_construction_pascal_spatial_foundry_p3_server import (
    P3FoundryShowcaseState,
    _static_response,
    dispatch_p3_foundry_request,
)


ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "http://127.0.0.1:8765"
HOST = "127.0.0.1:8765"


def _state() -> P3FoundryShowcaseState:
    return P3FoundryShowcaseState(
        ROOT,
        demo_project="winnipeg_pathways",
        auto_start=False,
        presentation_origin=ORIGIN,
    )


def _json_body(response: tuple[int, str, bytes]) -> dict:
    return json.loads(response[2].decode("utf-8"))


def test_p3_server_composes_over_p2_and_exposes_projection_only_surface() -> None:
    state = _state()
    try:
        assert state.pascal_available is True
        assert state.p3_available is True
        status = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction/decision-lane/status",
            request_host=HOST,
        )
        assert status[0] == 200
        assert _json_body(status)["physical_work_authorized"] is False

        response = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction/decision-lane",
            request_host=HOST,
        )
        packet = _json_body(response)["projection"]
        assert response[0] == 200
        assert packet["domain"]["arena_id"] == "construction"
        assert packet["authority"]["construction_event_appended"] is False

        html = _static_response("/", state)
        assert html[0] == 200
        assert b'id="pascal-construction-foundry"' in html[2]
        assert b'id="construction-decision-foundry"' in html[2]
        assert b"construction-decision-foundry.js" in html[2]

        as_built = _static_response("/construction-as-built", state)
        assert as_built[0] == 200
        assert b"construction-decision-as-built-sync.js" in as_built[2]
        assert b'id="construction-canvas"' in as_built[2]

        renderer_asset = _static_response(
            "/aura_spatial_web/construction_scene_renderer.js",
            state,
        )
        assert renderer_asset[0] == 200
        assert renderer_asset[1] == "application/javascript; charset=utf-8"

        renderer_packet = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction-demo",
            request_host=HOST,
        )
        renderer_json = _json_body(renderer_packet)
        assert renderer_packet[0] == 200
        assert renderer_json["state_digest"] == packet["domain"]["state_digest"]
        assert renderer_json["scene"]["scene_digest"] == packet["artifacts"][
            "as_built_scene_digest"
        ]
    finally:
        state.close()


def test_p3_server_rejects_stale_identity_hidden_storey_and_authority_fields() -> None:
    state = _state()
    try:
        initial = state.require_p3().compile()
        presentation = initial["presentation"]
        other_storey = next(
            item
            for item in state.require_p3().manifest.storey_ids
            if item != presentation["selected_storey"]
        )
        hidden = state.require_p3().manifest.first_selectable_on_storey(other_storey)
        exact = {
            "state_digest": initial["domain"]["state_digest"],
            "pascal_artifact_digest": initial["artifacts"]["pascal_artifact_digest"],
            "coordinate_receipt_digest": initial["artifacts"]["coordinate_receipt_digest"],
        }

        stale = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {**exact, "state_digest": "0" * 32},
            request_origin=ORIGIN,
            request_host=HOST,
        )
        assert stale[0] == 409
        assert "stale" in _json_body(stale)["error"]

        hidden_response = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {
                **exact,
                "selected_storey": presentation["selected_storey"],
                "selected_node": hidden.node_id,
            },
            request_origin=ORIGIN,
            request_host=HOST,
        )
        assert hidden_response[0] == 409
        assert "hidden-storey" in _json_body(hidden_response)["error"]

        candidate = initial["coordination_candidates"][2]["artifact"]
        stale_candidate = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {
                **exact,
                "selected_candidate_id": candidate["candidate_id"],
                "selected_candidate_digest": "0" * len(candidate["candidate_digest"]),
            },
            request_origin=ORIGIN,
            request_host=HOST,
        )
        assert stale_candidate[0] == 409
        assert "candidate digest is stale" in _json_body(stale_candidate)["error"]

        stale_as_built = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {**exact, "as_built_scene_digest": "0" * 64},
            request_origin=ORIGIN,
            request_host=HOST,
        )
        assert stale_as_built[0] == 409
        assert "as_built_scene_digest is stale" in _json_body(stale_as_built)["error"]

        authority = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {**exact, "physical_work_authorized": True},
            request_origin=ORIGIN,
            request_host=HOST,
        )
        assert authority[0] == 409
        assert "unknown fields" in _json_body(authority)["error"]
    finally:
        state.close()


def test_p3_server_exports_are_digest_bound_decision_support_only() -> None:
    state = _state()
    try:
        current = state.require_p3().compile(active_view="COMPARE", timeline_day=14.0)
        query = (
            "?active_view=COMPARE&timeline_day=14"
            f"&state_digest={current['domain']['state_digest']}"
            f"&runtime_packet_digest={current['domain']['runtime_packet_digest']}"
            f"&pascal_artifact_digest={current['artifacts']['pascal_artifact_digest']}"
            f"&coordinate_receipt_digest={current['artifacts']['coordinate_receipt_digest']}"
            f"&as_built_scene_digest={current['artifacts']['as_built_scene_digest']}"
        )
        json_response = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction/decision-lane/export.json" + query,
            request_host=HOST,
        )
        pdf_response = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction/decision-lane/export.pdf" + query,
            request_host=HOST,
        )
        assert json_response[0:2] == (200, "application/json; charset=utf-8")
        exported = json.loads(json_response[2])
        assert exported["canonical_project_record"] is False
        assert exported["approved_change_order"] is False
        assert exported["physical_work_authorized"] is False
        assert exported["automatic_execution"] is False
        assert pdf_response[0:2] == (200, "application/pdf")
        assert pdf_response[2].startswith(b"%PDF-1.4")
    finally:
        state.close()


def test_p3_mutable_route_requires_exact_origin_and_host() -> None:
    state = _state()
    try:
        without_origin = dispatch_p3_foundry_request(
            state,
            "POST",
            "/api/construction/decision-lane/project",
            {},
            request_host=HOST,
        )
        wrong_host = dispatch_p3_foundry_request(
            state,
            "GET",
            "/api/construction/decision-lane",
            request_host="localhost:9999",
        )
        assert without_origin[0] == 409
        assert "Origin" in _json_body(without_origin)["error"]
        assert wrong_host[0] == 409
        assert "Host" in _json_body(wrong_host)["error"]
    finally:
        state.close()
