from pathlib import Path

from aura_civic_map import build_map_manifest, project_map_manifest
from aura_human_agent_workflow import HumanAgentWorkflow


class FakeTools:
    def get_tools(self):
        return {"ok": True, "tools": []}

    def execute(self, tool_id, *, objective="", inputs=None):
        inputs = inputs or {}
        if tool_id == "topology_inspector":
            return {
                "run_id": "TOOL-GROUND",
                "status": "COMPLETED",
                "outputs": {
                    "ok": True,
                    "localized_files": ["aura_human_agent_arena.py", "tests/test_aura_human_agent_arena.py"],
                    "localized_symbols": ["HumanAgentArena"],
                    "line_ranges": [{"file": "aura_human_agent_arena.py", "line_range": [127, 210]}],
                    "ranking": {"tests": ["tests/test_aura_human_agent_arena.py"]},
                    "tests": ["tests/test_aura_human_agent_arena.py"],
                },
                "dissolution_receipt": {"dissolution_verified": True},
            }
        if tool_id == "test_lab":
            return {
                "run_id": "TOOL-TEST",
                "status": "COMPLETED",
                "outputs": {
                    "ok": True,
                    "passed": True,
                    "targets": list(inputs.get("test_targets", [])),
                    "summary": "1 passed",
                    "measurement": "MEASURED",
                },
                "dissolution_receipt": {"dissolution_verified": True},
            }
        raise AssertionError(tool_id)


class FakeBridge:
    def aura_prepare_arena(self, **kwargs):
        return {
            "ok": True,
            "plan_phase_hash": "PLAN-1",
            "act_capsules": [{
                "task_id": "A1",
                "target_file": "aura_human_agent_arena.py",
                "target_symbol": "HumanAgentArena",
            }],
            "grounding_evidence": [{
                "task_id": "A1",
                "test_files": ["tests/test_aura_human_agent_arena.py"],
            }],
            "blockers": [],
            "warnings": [],
        }

    def aura_stage_patch(self, **kwargs):
        return {"ok": True, "patch": {"patch_id": "PATCH-1", "status": "staged"}}

    def aura_verify_arena(self, **kwargs):
        return {"ok": True, "hotswap_ready": True, "stage": "verified", "checks": []}

    def aura_hotswap_status(self, **kwargs):
        return {"ok": True, "status": "ready", "human_review_required": True}

    def aura_export_icm(self, **kwargs):
        return {"ok": True, "workspace": "Aura_Memory/icm_workspaces/PLAN-1"}


def make_workflow(tmp_path: Path) -> HumanAgentWorkflow:
    workflow = HumanAgentWorkflow(tmp_path)
    workflow.tools = FakeTools()
    workflow._bridge = FakeBridge()
    return workflow


def test_buttons_follow_grounded_workflow_order(tmp_path: Path):
    workflow = make_workflow(tmp_path)
    initial = workflow.get_state()
    assert initial["actions"][0]["action_id"] == "set_objective"
    assert initial["actions"][0]["status"] == "READY"
    assert initial["actions"][1]["status"] == "BLOCKED"

    assert workflow.execute("set_objective", {"objective": "Refactor the Human Agent Arena"})["ok"]
    grounded = workflow.execute("ground_context")
    assert grounded["ok"]
    assert workflow.state.evidence["test_targets"] == ["tests/test_aura_human_agent_arena.py"]

    prepared = workflow.execute("prepare_capsule")
    assert prepared["ok"]
    assert workflow.state.evidence["plan_phase_hash"] == "PLAN-1"


def test_denial_explains_missing_patch_evidence(tmp_path: Path):
    workflow = make_workflow(tmp_path)
    workflow.execute("set_objective", {"objective": "Refactor arena"})
    workflow.execute("ground_context")
    workflow.execute("prepare_capsule")

    denied = workflow.execute("stage_patch")
    assert denied["ok"] is False
    assert "candidate_diff" in denied["missing_evidence"]
    assert any(item["action"] == "prepare_agent_task" for item in denied["remediation"])


def test_ephemeral_test_evidence_can_unlock_verifier_and_hotswap(tmp_path: Path):
    workflow = make_workflow(tmp_path)
    workflow.execute("set_objective", {"objective": "Refactor arena"})
    workflow.execute("ground_context")
    workflow.execute("prepare_capsule")
    workflow.state.evidence["candidate_diff"] = "--- a/a.py\n+++ b/a.py\n"
    workflow.state.evidence["affected_files"] = ["aura_human_agent_arena.py"]

    assert workflow.execute("stage_patch")["ok"]
    assert workflow.execute("run_tests")["ok"]
    assert workflow.execute("verify_patch")["ok"]
    assert workflow.execute("check_hotswap")["ok"]
    review = workflow.execute("human_review", {"approved": False})
    assert review["ok"]
    assert review["produced_evidence"]["human_review"]["merge_performed"] is False
    assert review["produced_evidence"]["human_review"]["production_mutation"] is False


def test_civic_projection_filters_by_jurisdiction_zoom_and_privacy():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Boundary", "type": "boundary", "jurisdiction_id": "A"},
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Public facility", "type": "facility", "jurisdiction_id": "A"},
                "geometry": {"type": "Point", "coordinates": [1, 1]},
            },
            {
                "type": "Feature",
                "properties": {"name": "Other jurisdiction", "type": "facility", "jurisdiction_id": "B"},
                "geometry": {"type": "Point", "coordinates": [1, 1]},
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Private record", "type": "facility", "jurisdiction_id": "A",
                    "privacy_class": "PRIVATE_NOT_SHARED",
                },
                "geometry": {"type": "Point", "coordinates": [1, 1]},
            },
        ],
    }
    manifest = build_map_manifest(geojson, ["boundary", "facility"], jurisdiction_id="A")

    regional = project_map_manifest(manifest, zoom=5, jurisdiction_id="A")
    assert regional["visible_feature_count"] == 1
    assert regional["visible_layer_types"] == ["boundary"]

    local = project_map_manifest(manifest, zoom=11, jurisdiction_id="A")
    names = [row["name"] for row in local["accessible_rows"]]
    assert "Public facility" in names
    assert "Other jurisdiction" not in names
    assert "Private record" not in names
    assert local["suppressed_counts"]["jurisdiction"] == 1
    assert local["suppressed_counts"]["privacy"] == 1
