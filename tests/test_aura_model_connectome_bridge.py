from __future__ import annotations

from pathlib import Path
import time

import pytest

from aura_capability_connectome_v2 import enrich_path
from aura_model_cognome import ModelCapabilityEdge, ModelEndpointIdentity
from aura_model_cognome_store import ModelCognomeStore
from aura_model_connectome_bridge import (
    current_connectome,
    record_model_capability_edge,
    resolve_candidates_for_path,
    task_context_from_path,
    validate_model_capability_edge,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _path(*capability_ids: str) -> dict:
    graph = current_connectome(REPO_ROOT)
    return enrich_path(
        {"ok": True, "version": "test", "path": list(capability_ids)},
        graph,
    )


def _model_path() -> dict:
    return _path("aura.dream.reranking")


def test_edge_must_reference_current_model_dependent_capability(tmp_path: Path) -> None:
    graph = current_connectome(REPO_ROOT)
    endpoint = ModelEndpointIdentity.create(provider="local", requested_model="test-model")
    edge = ModelCapabilityEdge.create(
        profile_id=endpoint.profile_id,
        aura_capability_id="aura.missing.capability",
        task_bucket="research_rank",
        support_level="VALIDATED",
        status="VALIDATED",
        evidence_count=1,
        evidence_digest="evidence",
        capability_graph_digest=graph["graph_digest"],
        last_validated_at=time.time(),
    )
    result = validate_model_capability_edge(edge, repo_root=REPO_ROOT)
    assert result["ok"] is False
    assert any("not present" in error for error in result["errors"])


def test_deterministic_capability_rejects_model_support_edge() -> None:
    graph = current_connectome(REPO_ROOT)
    endpoint = ModelEndpointIdentity.create(provider="local", requested_model="test-model")
    edge = ModelCapabilityEdge.create(
        profile_id=endpoint.profile_id,
        aura_capability_id="aura.concept_workspace",
        task_bucket="localization",
        support_level="VALIDATED",
        status="VALIDATED",
        evidence_count=1,
        evidence_digest="evidence",
        capability_graph_digest=graph["graph_digest"],
        last_validated_at=time.time(),
    )
    result = validate_model_capability_edge(edge, repo_root=REPO_ROOT)
    assert result["ok"] is False
    assert any("DETERMINISTIC_LOCAL" in error for error in result["errors"])


def test_record_and_resolve_candidate_for_exact_path(tmp_path: Path) -> None:
    path_packet = _model_path()
    assert path_packet["ok"] is True
    assert path_packet["model_dependent_capability_ids"] == ["aura.dream.reranking"]
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="test-model")
        store.upsert_endpoint(endpoint)
        edge = ModelCapabilityEdge.create(
            profile_id=endpoint.profile_id,
            aura_capability_id="aura.dream.reranking",
            task_bucket="research_rank",
            support_level="VALIDATED",
            status="VALIDATED",
            evidence_count=3,
            evidence_digest="verified-evidence",
            capability_graph_digest=path_packet["graph_digest"],
            last_validated_at=time.time(),
        )
        recorded = record_model_capability_edge(store, edge, repo_root=REPO_ROOT)
        assert recorded["ok"] is True
        context = task_context_from_path(
            objective="rank research evidence",
            purpose_digest="human-purpose",
            path_packet=path_packet,
            task_family="research_rank",
            verifier_id="research-verifier",
        )
        resolved = resolve_candidates_for_path(
            store, context, path_packet, repo_root=REPO_ROOT
        )
        assert resolved["ok"] is True
        assert resolved["candidate_count"] == 1
        assert resolved["model_candidates"][0]["profile_id"] == endpoint.profile_id
        assert resolved["zero_model"]["eligible"] is False


def test_mixed_path_scores_only_model_dependent_subset(tmp_path: Path) -> None:
    path_packet = _path("aura.concept_workspace", "aura.dream.reranking")
    assert path_packet["deterministic_capability_ids"] == ["aura.concept_workspace"]
    assert path_packet["model_dependent_capability_ids"] == ["aura.dream.reranking"]
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        endpoint = ModelEndpointIdentity.create(provider="local", requested_model="test-model")
        store.upsert_endpoint(endpoint)
        record_model_capability_edge(
            store,
            ModelCapabilityEdge.create(
                profile_id=endpoint.profile_id,
                aura_capability_id="aura.dream.reranking",
                task_bucket="research_rank",
                support_level="VALIDATED",
                status="VALIDATED",
                evidence_count=2,
                evidence_digest="verified-evidence",
                capability_graph_digest=path_packet["graph_digest"],
                last_validated_at=time.time(),
            ),
            repo_root=REPO_ROOT,
        )
        context = task_context_from_path(
            objective="localize and rank research evidence",
            purpose_digest="human-purpose",
            path_packet=path_packet,
            task_family="research_rank",
            verifier_id="research-verifier",
        )
        resolved = resolve_candidates_for_path(store, context, path_packet, repo_root=REPO_ROOT)
        assert resolved["ok"] is True
        assert resolved["required_capability_ids"] == [
            "aura.concept_workspace", "aura.dream.reranking"
        ]
        assert resolved["model_dependent_capability_ids"] == ["aura.dream.reranking"]
        assert resolved["candidate_count"] == 1


def test_task_context_rejects_path_bound_field_overrides() -> None:
    path_packet = _model_path()
    with pytest.raises(ValueError, match="cannot be overridden"):
        task_context_from_path(
            objective="rank research evidence",
            purpose_digest="human-purpose",
            path_packet=path_packet,
            task_family="research_rank",
            required_capability_ids=("aura.missing",),
        )


def test_stale_graph_digest_denies_candidate_resolution(tmp_path: Path) -> None:
    path_packet = _model_path()
    context = task_context_from_path(
        objective="rank research evidence",
        purpose_digest="human-purpose",
        path_packet=path_packet,
        task_family="research_rank",
        verifier_id="research-verifier",
    )
    stale = dict(path_packet)
    stale["graph_digest"] = "stale"
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        result = resolve_candidates_for_path(store, context, stale, repo_root=REPO_ROOT)
    assert result["ok"] is False
    assert result["status"] == "DENIED"
    assert any("stale" in error.lower() for error in result["errors"])


def test_tampered_path_digest_is_denied(tmp_path: Path) -> None:
    path_packet = _model_path()
    context = task_context_from_path(
        objective="rank research evidence",
        purpose_digest="human-purpose",
        path_packet=path_packet,
        task_family="research_rank",
        verifier_id="research-verifier",
    )
    tampered = dict(path_packet)
    tampered["path_digest"] = "tampered"
    with ModelCognomeStore(db_path=tmp_path / "cognome.db") as store:
        result = resolve_candidates_for_path(store, context, tampered, repo_root=REPO_ROOT)
    assert result["ok"] is False
    assert any("path digest" in error.lower() for error in result["errors"])
