"""Contracts for the bounded spatial topology integration in the unified showcase."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parent.parent
SLOT_KEYS = {"DIR", "ASP", "CLASS", "SUBJ", "VOICE", "STEM"}


def _topology() -> dict:
    nodes = [
        {
            "id": "file:civic-js",
            "label": "aura_showcase/civic.js",
            "node_type": "file",
            "file_path": "aura_showcase/civic.js",
            "symbol": "",
            "line_range": [1, 313],
            "tokens_est": 1700,
            "color": "#4f8cff",
            "x": -80,
            "y": 10,
            "z": 20,
            "metadata": {},
        },
        {
            "id": "function:project-map",
            "label": "project_map_manifest",
            "node_type": "function",
            "file_path": "aura_civic_map.py",
            "symbol": "project_map_manifest",
            "line_range": [228, 308],
            "tokens_est": 620,
            "color": "#38c98b",
            "x": 40,
            "y": -20,
            "z": 25,
            "metadata": {},
        },
        {
            "id": "file:test-showcase",
            "label": "test_aura_showcase_guided_interface.py",
            "node_type": "test",
            "file_path": "tests/test_aura_showcase_guided_interface.py",
            "symbol": "",
            "line_range": [1, 278],
            "tokens_est": 900,
            "color": "#ef5da8",
            "x": 95,
            "y": 40,
            "z": -10,
            "metadata": {},
        },
        {
            "id": "file:readme",
            "label": "README.md",
            "node_type": "file",
            "file_path": "README.md",
            "symbol": "",
            "line_range": [1, 50],
            "tokens_est": 400,
            "color": "#4f8cff",
            "x": -20,
            "y": 90,
            "z": 15,
            "metadata": {},
        },
    ]
    links = [
        {"source": "file:civic-js", "target": "function:project-map", "type": "calls", "status": "known"},
        {"source": "file:test-showcase", "target": "file:civic-js", "type": "tests", "status": "known"},
    ]
    return {"nodes": nodes, "links": links, "meta": {"truth_policy": "exact"}}


def test_spatial_task_registry_is_six_slot_and_review_only():
    from aura_showcase_spatial import list_spatial_tasks

    result = list_spatial_tasks()
    assert result["ok"] is True
    assert result["task_count"] == 4
    assert result["automatic_commit"] is False
    assert result["automatic_push"] is False
    assert result["automatic_merge"] is False
    task_ids = {task["task_id"] for task in result["tasks"]}
    assert task_ids == {
        "version_drift",
        "memory_friction",
        "civic_map_overlay",
        "emergent_capabilities",
    }
    for task in result["tasks"]:
        assert set(task["intent_slots"]) == SLOT_KEYS
        assert task["acceptance_criteria"]
        assert task["prohibited_actions"]
        assert task["seed_files"]


def test_task_workspace_reuses_existing_micro_arena_and_stays_bounded():
    from aura_showcase_spatial import build_task_workspace

    result = build_task_workspace(_topology(), "civic_map_overlay", depth=2)
    assert result["ok"] is True
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["vsa_patch_authority"] is False
    assert result["production_mutation"] is False
    workspace = result["workspace"]
    assert workspace["selected_node_ids"]
    assert workspace["returned_node_count"] <= result["bounds"]["node_limit"]
    assert workspace["returned_link_count"] <= result["bounds"]["link_limit"]
    assert all(node["patch_authority"] is False for node in workspace["nodes"])
    assert {node["projection_truth"] for node in workspace["nodes"]} <= {
        "EXACT_TOPOLOGY",
        "CODEMAP_PROJECTED",
    }


def test_unknown_task_fails_closed():
    from aura_showcase_spatial import build_task_workspace

    result = build_task_workspace(_topology(), "missing")
    assert result["ok"] is False
    assert result["error"] == "unknown_spatial_task"


def test_showcase_dispatch_exposes_task_and_bounded_workspace_routes():
    from aura_showcase_server import dispatch_showcase_request

    arena = SimpleNamespace(topology=_topology())
    human_agent = SimpleNamespace(arena=arena)
    state = SimpleNamespace(
        default_session_id="",
        demo_project="winnipeg_pathways",
        human_agent=human_agent,
    )

    status, _, raw = dispatch_showcase_request(state, "GET", "/api/showcase/coding-tasks")
    tasks = json.loads(raw)
    assert status == 200
    assert tasks["task_count"] == 4

    status, _, raw = dispatch_showcase_request(
        state,
        "GET",
        "/api/showcase/topology/tasks/civic_map_overlay?depth=1",
    )
    workspace = json.loads(raw)
    assert status == 200
    assert workspace["ok"] is True
    assert workspace["workspace"]["nodes"]

    status, _, raw = dispatch_showcase_request(
        state,
        "POST",
        "/api/showcase/topology/select",
        {"node_id": "file:civic-js", "depth": 2, "task_id": "civic_map_overlay"},
    )
    selected = json.loads(raw)
    assert status == 200
    assert selected["workspace"]["selected_node_ids"] == ["file:civic-js"]


def test_browser_assets_embed_spatial_tasks_and_topology_lens():
    index = (REPO_ROOT / "aura_showcase" / "index.html").read_text(encoding="utf-8")
    topology = (REPO_ROOT / "aura_showcase" / "topology.js").read_text(encoding="utf-8")
    server = (REPO_ROOT / "aura_showcase_server.py").read_text(encoding="utf-8")

    assert 'id="spatial-task-list"' in index
    assert 'id="topology-canvas"' in index
    assert 'id="topology-inspector"' in index
    assert 'href="topology.css"' in index
    assert 'src="topology.js"' in index
    assert "/api/showcase/coding-tasks" in topology
    assert "/api/showcase/topology/select" in topology
    assert "full_topology_sent_to_browser" in server
    assert "demo=False" in server
    assert '"topology.js"' in server
    assert '"topology.css"' in server
