import json

from aura_spectral_topology import (
    SPECTRAL_TOPOLOGY_VERSION,
    augment_topology_payload,
    build_fusion_topology_snapshot,
    normalize_topology_payload,
)


def _sample_payload():
    return {
        "nodes": [
            {"id": "aura_router.py::route", "label": "route", "file": "aura_router.py", "shape": "Sphere"},
            {"id": "aura_llm_egress.py::generate", "label": "generate", "file": "aura_llm_egress.py", "shape": "Sphere"},
            {"id": "aura_fusion.py::run", "label": "run", "file": "aura_fusion.py", "shape": "Cube"},
        ],
        "edges": [
            {"source": "aura_router.py::route", "target": "aura_llm_egress.py::generate", "strength": 0.9},
            {"source": "aura_llm_egress.py::generate", "target": "aura_router.py::route", "strength": 0.9},
            {"source": "aura_fusion.py::run", "target": "aura_router.py::route", "strength": 0.7},
        ],
    }


def test_augment_topology_payload_adds_spectral_coordinates_and_warnings():
    augmented = augment_topology_payload(_sample_payload())

    assert augmented["spectral_topology"]["version"] == SPECTRAL_TOPOLOGY_VERSION
    assert augmented["spectral_topology"]["laplacian"] == "L = D - A"
    assert len(augmented["nodes"]) == 3
    assert all(len(node["position"]) == 3 for node in augmented["nodes"])
    assert all(0.05 <= node["luminance"] <= 1.0 for node in augmented["nodes"])

    warning_nodes = [node for node in augmented["nodes"] if node["phaseShiftWarning"]]
    assert {node["id"] for node in warning_nodes} == {
        "aura_router.py::route",
        "aura_llm_egress.py::generate",
    }


def test_normalize_topology_payload_accepts_dict_payloads():
    payload = {
        "nodes": {
            "A": {"label": "alpha"},
            "B": {"label": "beta"},
        },
        "edges": {
            "A_to_B": {"sourceId": "A", "targetId": "B"},
            "dangling": {"sourceId": "A", "targetId": "Z"},
        },
    }

    nodes, edges = normalize_topology_payload(payload)

    assert [node["id"] for node in nodes] == ["A", "B"]
    assert len(edges) == 1
    assert edges[0]["source"] == "A"
    assert edges[0]["target"] == "B"


def test_build_fusion_topology_snapshot_limits_to_target_neighbors(tmp_path):
    memory_dir = tmp_path / "Aura_Memory"
    memory_dir.mkdir()
    (memory_dir / "live_topology_ast.json").write_text(
        json.dumps(augment_topology_payload(_sample_payload())),
        encoding="utf-8",
    )

    snapshot = build_fusion_topology_snapshot(
        repo_root=tmp_path,
        target_file="aura_router.py",
        target_symbol="route",
    )

    assert snapshot is not None
    assert snapshot["version"] == SPECTRAL_TOPOLOGY_VERSION
    assert snapshot["target_file"] == "aura_router.py"
    assert [node["id"] for node in snapshot["targets"]] == ["aura_router.py::route"]
    neighbor_ids = {node["id"] for node in snapshot["neighbors"]}
    assert "aura_llm_egress.py::generate" in neighbor_ids
    assert "aura_fusion.py::run" in neighbor_ids
