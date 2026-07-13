from __future__ import annotations

from pathlib import Path

from aura_capability_connectome_v2 import (
    DETERMINISTIC_LOCAL,
    MODEL_DEPENDENT,
    capability_node,
    enrich_connectome,
    enrich_path,
    zero_model_eligibility,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_synthetic_graph_digest_is_order_independent() -> None:
    nodes = [
        {
            "id": "aura.model.worker",
            "name": "Model Worker",
            "implemented_by": ["worker.py"],
            "related_capabilities": ["aura.codemap.lookup"],
        },
        {
            "id": "aura.codemap.lookup",
            "name": "CODEMAP Lookup",
            "implemented_by": ["codemap.py"],
            "related_capabilities": [],
        },
    ]
    edges = [{"source": "aura.model.worker", "target": "aura.codemap.lookup", "type": "related"}]
    first = enrich_connectome({"ok": True, "version": "v1", "nodes": nodes, "edges": edges})
    second = enrich_connectome({"ok": True, "version": "v1", "nodes": list(reversed(nodes)), "edges": edges})
    assert first["graph_digest"] == second["graph_digest"]
    assert all(node["node_digest"] for node in first["nodes"])
    assert capability_node(first, "aura.model.worker")["execution_class"] == MODEL_DEPENDENT
    assert capability_node(first, "aura.codemap.lookup")["execution_class"] == DETERMINISTIC_LOCAL


def test_detailed_path_binds_exact_node_evidence() -> None:
    graph = enrich_connectome(
        {
            "ok": True,
            "version": "v1",
            "nodes": [
                {
                    "id": "aura.codemap.lookup",
                    "name": "CODEMAP Lookup",
                    "implemented_by": ["codemap.py"],
                    "symbols": ["lookup"],
                    "tests": ["tests/test_lookup.py"],
                    "docs": ["docs/lookup.md"],
                    "truth_boundary": "exact_source",
                    "token_savings_role": "localization",
                    "grounding": "VERIFIED",
                    "codemap_verified_files": ["codemap.py"],
                    "codemap_unverified_files": [],
                }
            ],
            "edges": [],
        }
    )
    packet = enrich_path({"ok": True, "version": "v1", "path": ["aura.codemap.lookup"]}, graph)
    assert packet["ok"] is True
    assert packet["graph_digest"] == graph["graph_digest"]
    assert packet["path_details"][0]["node_digest"]
    assert packet["implemented_by"] == ["codemap.py"]
    assert packet["tests"] == ["tests/test_lookup.py"]
    assert zero_model_eligibility(packet)["eligible"] is True


def test_missing_or_unresolved_capability_fails_zero_model_closed() -> None:
    graph = enrich_connectome(
        {
            "ok": True,
            "nodes": [{"id": "aura.ambiguous", "name": "Ambiguous"}],
            "edges": [],
        }
    )
    unresolved = enrich_path({"ok": True, "path": ["aura.ambiguous"]}, graph)
    assert zero_model_eligibility(unresolved)["eligible"] is False
    missing = enrich_path({"ok": True, "path": ["aura.missing"]}, graph)
    assert missing["ok"] is False
    assert missing["missing_capability_ids"] == ["aura.missing"]
