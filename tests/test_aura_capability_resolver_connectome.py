from __future__ import annotations

from pathlib import Path

from aura_capability_resolver_v2 import resolve_capabilities

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_resolver_returns_first_class_connectome_packet() -> None:
    result = resolve_capabilities(
        "route research through DREAM reranking and exact verification",
        repo_root=REPO_ROOT,
        top_k=8,
        token_budget=4000,
    )
    packet = result["capability_connectome_path"]
    assert packet["ok"] is True
    assert packet["graph_digest"]
    assert packet["path_digest"]
    assert packet["required_capability_ids"] == packet["path"]
    assert result["capability_graph_digest"] == packet["graph_digest"]
    assert result["required_capability_ids"] == packet["required_capability_ids"]
    assert isinstance(result["model_execution_requirements"], list)
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"


def test_resolver_exposes_execution_class_and_exact_path_evidence() -> None:
    result = resolve_capabilities(
        "localize code with CODEMAP and node inspector",
        repo_root=REPO_ROOT,
        top_k=8,
        token_budget=4000,
    )
    packet = result["capability_connectome_path"]
    assert packet["path_details"]
    for detail in packet["path_details"]:
        assert detail["node_digest"]
        assert detail["execution_class"] in {
            "DETERMINISTIC_LOCAL", "MODEL_DEPENDENT", "UNRESOLVED_EXECUTION"
        }
        assert isinstance(detail["implemented_by"], list)
        assert isinstance(detail["tests"], list)
        assert "truth_boundary" in detail
    assert result["deterministic_capability_ids"] == packet["deterministic_capability_ids"]
    assert result["model_dependent_capability_ids"] == packet["model_dependent_capability_ids"]
