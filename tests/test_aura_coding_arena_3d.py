import json
import os
from pathlib import Path

from aura_coding_arena_3d import (
    compile_action_capsule,
    demo_topology,
    detect_wiring_faults,
    estimate_token_costs,
    load_arena_topology,
    simulate_model_route,
)
from aura_coding_arena_server import CodingArenaServerState, dispatch_api_request


def test_capsule_compiler_returns_valid_json_for_demo_topology(tmp_path: Path):
    graph = demo_topology(tmp_path)
    node_id = graph["nodes"][0]["id"]

    capsule = compile_action_capsule(graph, [node_id], human_instruction="compile capsule")

    encoded = json.dumps(capsule)
    assert json.loads(encoded)["capsule_version"] == "AURA_CODING_ARENA_CAPSULE_V1"
    assert capsule["selected"]["node_ids"] == [node_id]
    assert "NO_NEW_DEPS" in capsule["constraints"]
    assert capsule["route_decision"]["network_calls_made"] is False


def test_capsule_compiler_never_includes_nonexistent_paths(tmp_path: Path):
    existing = tmp_path / "real.py"
    existing.write_text("def real():\n    return 1\n", encoding="utf-8")
    graph = {
        "nodes": [
            {
                "id": "real.py::real",
                "label": "real",
                "node_type": "function",
                "file_path": "real.py",
                "symbol": "real",
                "line_range": [1, 2],
                "metadata": {"codemap_match": True},
            },
            {
                "id": "missing.py::ghost",
                "label": "ghost",
                "node_type": "function",
                "file_path": "missing.py",
                "symbol": "ghost",
                "line_range": [1, 2],
                "metadata": {"codemap_match": False},
            },
        ],
        "links": [],
        "meta": {"repo_root": str(tmp_path), "raw_repo_tokens": 1000},
    }

    capsule = compile_action_capsule(graph, ["real.py::real", "missing.py::ghost"])

    assert capsule["context"]["target_files"] == ["real.py"]
    assert "missing.py" not in capsule["context"]["target_files"]
    assert any(fault["kind"] == "stale_or_missing_file" for fault in capsule["wiring_faults"])


def test_wiring_fault_detector_flags_node_with_no_tests(tmp_path: Path):
    (tmp_path / "worker.py").write_text("def work():\n    return 1\n", encoding="utf-8")
    graph = {
        "nodes": [
            {
                "id": "worker.py::work",
                "label": "work",
                "node_type": "function",
                "file_path": "worker.py",
                "symbol": "work",
                "line_range": [1, 2],
                "metadata": {"codemap_match": True},
            }
        ],
        "links": [],
        "meta": {"repo_root": str(tmp_path), "raw_repo_tokens": 1000},
    }

    faults = detect_wiring_faults(graph, ["worker.py::work"])

    assert any(fault.kind == "missing_test_edge" for fault in faults)


def test_token_estimator_shows_capsule_smaller_than_raw_topology(tmp_path: Path):
    graph = demo_topology(tmp_path)
    capsule = compile_action_capsule(graph, [graph["nodes"][0]["id"]], human_instruction="compile capsule")
    estimate = estimate_token_costs(graph, capsule_payload=capsule)

    assert estimate.capsule_tokens < estimate.raw_repo_tokens
    assert estimate.savings_vs_raw_pct > 0


def test_server_dispatch_returns_topology_and_capsule_without_socket(tmp_path: Path):
    state = CodingArenaServerState(tmp_path, demo=True)
    status, topology = dispatch_api_request(state, "GET", "/api/topology?demo=1")
    assert status == 200
    node_id = topology["nodes"][0]["id"]

    status, capsule = dispatch_api_request(
        state,
        "POST",
        "/api/compile-capsule",
        {"node_ids": [node_id], "human_instruction": "compile capsule"},
    )

    assert status == 200
    assert capsule["selected"]["node_ids"] == [node_id]
    assert capsule["route_decision"]["network_calls_made"] is False


def test_frontend_loads_sample_topology_in_demo_mode():
    index = Path("aura_coding_arena/index.html").read_text(encoding="utf-8")
    script = Path("aura_coding_arena/main.js").read_text(encoding="utf-8")

    assert "arena-canvas" in index
    assert "/api/topology" in script
    assert "/api/simulate-route" in script
    assert "demo-toggle" in index
    assert "?demo=1" in script


def test_no_external_network_call_occurs_during_route_simulation(tmp_path: Path):
    graph = demo_topology(tmp_path)
    capsule = compile_action_capsule(graph, [graph["nodes"][0]["id"]], human_instruction="send to worker")

    decision = simulate_model_route(capsule)

    assert decision.network_calls_made is False
    assert all(candidate.route_id for candidate in decision.candidates)
    fireworks = next(candidate for candidate in decision.candidates if candidate.route_id == "FIREWORKS_TEXT_REASONER")
    assert fireworks.requires_network is True
    assert "mvp_offline_default" in fireworks.blocked_for


def test_no_secret_env_value_is_emitted(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("AURA_TEST_SECRET_VALUE", "super-secret-do-not-print")
    graph = demo_topology(tmp_path)

    capsule = compile_action_capsule(graph, [graph["nodes"][0]["id"]], human_instruction="compile capsule")
    rendered = json.dumps(capsule)

    assert os.environ["AURA_TEST_SECRET_VALUE"] not in rendered


def test_load_arena_topology_falls_back_to_demo_without_codemap(tmp_path: Path):
    graph = load_arena_topology(tmp_path)

    assert graph["source"] == "offline_demo"
    assert graph["meta"]["demo"] is True
