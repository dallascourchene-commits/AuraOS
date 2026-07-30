from __future__ import annotations

from pathlib import Path

import pytest

from aura_construction_foundry_decision import (
    CONSTRUCTION_FOUNDRY_DECISION_VERSION,
    ConstructionFoundryDecisionCompiler,
    public_projection,
)
from aura_pascal_spatial_presentation import (
    PascalPresentationError,
    load_pascal_compatibility_fixture,
    sha256_digest,
)


ROOT = Path(__file__).resolve().parents[1]


def _compiler() -> ConstructionFoundryDecisionCompiler:
    _lock, manifest, coordinate, _scene = load_pascal_compatibility_fixture(str(ROOT))
    return ConstructionFoundryDecisionCompiler(
        manifest=manifest,
        coordinate_receipt=coordinate,
    )


def test_p3_compiles_three_role_distinct_candidates_and_authority_false_exports() -> None:
    compiler = _compiler()
    packet = compiler.compile(active_view="COMPARE", timeline_day=12.0)
    public = public_projection(packet)

    assert public["version"] == CONSTRUCTION_FOUNDRY_DECISION_VERSION
    assert public["presentation"]["active_view"] == "COMPARE"
    assert public["presentation"]["selection_survives_view_switch"] is True
    assert [item["role"] for item in public["coordination_candidates"]] == [
        "HARD_BLOCKED",
        "NEEDS_EVIDENCE",
        "READY_FOR_HUMAN_REVIEW",
    ]
    assert public["coordination_candidates"][0]["closure_count"] == 0
    assert public["coordination_candidates"][1]["closure_count"] < public[
        "coordination_candidates"
    ][1]["closure_total"]
    assert public["coordination_candidates"][2]["closure_count"] == public[
        "coordination_candidates"
    ][2]["closure_total"]
    assert public["domain_decision"]["status"] == "READY_FOR_HUMAN_REVIEW"
    assert public["authority"] == {
        "visual_truth": False,
        "construction_truth_owner": "ConstructionProjectState",
        "survey_authority": False,
        "professional_approval": False,
        "physical_work_authorized": False,
        "payment_released": False,
        "access_granted": False,
        "automatic_execution": False,
        "source_records_mutated": False,
        "construction_event_appended": False,
        "human_review_required": True,
    }
    assert packet["_export_pdf"].startswith(b"%PDF-1.4")
    assert packet["_as_built_packet_json"]
    assert packet["spatial_interactions"]["selected_issue_focus"]["intent_slots"] == {
        "DIR": "scene",
        "ASP": "navigate",
        "CLASS": "spatial_focus",
        "SUBJ": "domain_projection",
        "VOICE": "focus",
        "STEM": "center_view",
    }
    assert packet["construction"]["geofences"]
    assert packet["construction"]["crew_projection"]
    assert packet["construction"]["schedule_projection"]
    assert packet["construction"]["material_staging"]
    assert packet["construction"]["waste_and_bin_zones"]
    assert packet["exports"]["json_sha256"] == sha256_digest(packet["_export_json"])
    assert packet["exports"]["pdf_sha256"] == sha256_digest(packet["_export_pdf"])
    assert packet["exports"]["canonical_project_record"] is False
    assert packet["exports"]["approved_change_order"] is False


def test_p3_rejects_hidden_storey_selection_and_preserves_selection_across_views() -> None:
    compiler = _compiler()
    first_storey, second_storey = compiler.manifest.storey_ids[:2]
    first_node = compiler.manifest.first_selectable_on_storey(first_storey).node_id
    hidden_node = compiler.manifest.first_selectable_on_storey(second_storey).node_id

    design = compiler.compile(
        active_view="DESIGN",
        selected_storey=first_storey,
        selected_node=first_node,
    )
    floor_plan = compiler.compile(
        active_view="FLOOR_PLAN",
        selected_storey=first_storey,
        selected_node=first_node,
    )
    assert design["presentation"]["selected_node"] == floor_plan["presentation"][
        "selected_node"
    ]
    assert design["presentation"]["selected_target_ref"] == floor_plan[
        "presentation"
    ]["selected_target_ref"]

    with pytest.raises(PascalPresentationError, match="hidden-storey"):
        compiler.compile(
            selected_storey=first_storey,
            selected_node=hidden_node,
        )


def test_p3_compare_receipt_keeps_pascal_and_as_built_truth_separate() -> None:
    packet = _compiler().compile(active_view="COMPARE")
    receipt = packet["artifacts"]["compare_receipt"]

    assert receipt["split_screen_only"] is True
    assert receipt["same_canvas_depth_composition"] is False
    assert receipt["visual_alignment_only"] is True
    assert receipt["survey_authority"] is False
    assert receipt["construction_truth"] is False
    assert receipt["pascal_spatial_scene_digest"] != receipt["as_built_scene_digest"]
    assert packet["presentation"]["design_truth_class"] == "PROPOSAL"
    assert packet["presentation"]["as_built_truth_class"] == "DERIVED_PRESENTATION"


def test_p3_projection_rejects_unadmitted_view_storey_candidate_and_time() -> None:
    compiler = _compiler()
    with pytest.raises(ValueError, match="unsupported Construction Foundry view"):
        compiler.compile(active_view="APPROVE")
    with pytest.raises(PascalPresentationError, match="not admitted"):
        compiler.compile(selected_storey="L999")
    with pytest.raises(ValueError, match="not admitted"):
        compiler.compile(selected_candidate_id="candidate-not-admitted")
    with pytest.raises(ValueError, match="between 0 and 30"):
        compiler.compile(timeline_day=31.0)


def test_p3_rejects_stale_candidate_digest_and_as_built_identity_is_exact() -> None:
    compiler = _compiler()
    packet = compiler.compile()
    candidate = packet["coordination_candidates"][2]["artifact"]
    with pytest.raises(ValueError, match="candidate digest is stale"):
        compiler.compile(
            selected_candidate_id=candidate["candidate_id"],
            selected_candidate_digest="0" * len(candidate["candidate_digest"]),
        )
    as_built = packet["_as_built_packet_json"].decode("utf-8")
    assert packet["domain"]["state_digest"] in as_built
    assert packet["artifacts"]["as_built_scene_digest"] in as_built
