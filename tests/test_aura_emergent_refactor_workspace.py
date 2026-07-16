"""Deterministic tests for persistent emergent evidence and bounded research."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arxiv_forager import ArXivForager
from aura_arena_research_bridge import (
    ARXIV_METADATA_TRUTH,
    GITHUB_METADATA_TRUTH,
    SIDECAR_TRUTH,
    ArenaResearchBridge,
    _github_repository_record,
    _parse_arxiv_atom,
)
from aura_emergent_refactor_workspace import EmergentResultsStore
from aura_human_agent_arena_server import (
    HumanAgentArenaServerState,
    _attach_emergent_refactor_context,
    _prepare_payload_with_emergent_context,
    dispatch_api_request,
)


SAMPLE_CONNECTION = {
    "connection_id": "CONN-1",
    "source": {"file": "aura_human_agent_arena.py", "symbol": "route_command"},
    "target": {"file": "aura_research_manifest.py", "symbol": "ingest_research_manifest"},
    "missing_wire": "arena_refactor_missing_research_evidence",
    "emergent_ability": "Human Agent Arena research-grounded refactoring",
    "evidence": [
        {
            "file": "aura_human_agent_arena.py",
            "source_span": [173, 211],
            "source_hash": "a" * 64,
        },
        {
            "file": "aura_research_manifest.py",
            "source_span": [98, 145],
            "source_hash": "b" * 64,
        },
    ],
    "confidence": 0.84,
    "implementation_feasibility": 0.9,
    "verifier_readiness": 0.65,
    "token_reduction_potential": 0.5,
    "safety_risk": "low",
    "cost_risk": "low",
    "status": "FUTURE_PATCHABLE",
    "required_tests": ["tests/test_aura_human_agent_arena.py"],
    "emergence_score": 3.91,
}


def sample_report() -> dict:
    return {
        "suite_version": "TEST_EMERGENT_SUITE_V1",
        "generated_at": "2026-07-16T00:00:00Z",
        "repository_head": "deadbeef",
        "results": [
            {
                "id": "P_TEST_HUMAN_AGENT_REFACTOR",
                "mode": "discover",
                "focus": "Refactor the Human Agent Arena with research evidence",
                "report": {
                    "summary": {
                        "total_abilities_scanned": 10,
                        "candidate_unwired_connections": 1,
                        "future_patchable": 1,
                    },
                    "connections": [SAMPLE_CONNECTION],
                    "verified_clusters": [
                        {
                            "cluster_id": "CLUSTER-1",
                            "cluster_title": "Arena research grounding",
                            "emergent_ability": SAMPLE_CONNECTION["emergent_ability"],
                            "source_role": "coding_arena",
                            "target_role": "research_manifest",
                            "missing_wire": SAMPLE_CONNECTION["missing_wire"],
                            "best_connection": SAMPLE_CONNECTION,
                            "alternates": [],
                            "suppressed_duplicate_count": 0,
                            "rejected_count": 0,
                            "verifier_notes": ["high_evidence"],
                            "final_score": 0.91,
                            "safe_to_patch": True,
                        }
                    ],
                    "verifier_summary": "1 verified cluster from 1 raw candidate",
                },
            }
        ],
    }


def test_store_preserves_complete_report_and_deduplicates(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    report = sample_report()

    first = store.store_report(report, source="test", label="complete run")
    second = store.store_report(report, source="test", label="complete run")

    assert first["ok"] is True
    assert first["created"] is True
    assert second["created"] is False
    loaded = store.get_run(first["run_id"])
    assert loaded["ok"] is True
    assert loaded["run"]["report"] == report
    assert loaded["run"]["digest"] == first["digest"]


def test_seed_reports_import_idempotently(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    seed_path = store.seed_dir / "suite" / "probe.json"
    seed_path.parent.mkdir(parents=True)
    seed_path.write_text(
        json.dumps({"source": "probe_artifact", "label": "P1", "report": sample_report()}),
        encoding="utf-8",
    )

    first = store.import_seed_reports()
    second = store.import_seed_reports()

    assert first["ok"] is True
    assert len(first["imported"]) == 1
    assert second["imported"] == []
    assert len(second["skipped"]) == 1


def test_search_and_refactor_packet_project_stored_findings(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    store.store_report(sample_report(), source="test")

    search = store.search_findings("Human Agent Arena research refactor", limit=10)
    assert search["ok"] is True
    assert search["count"] >= 1
    finding = search["findings"][0]
    assert finding["source"]["file"] == "aura_human_agent_arena.py"
    assert finding["target"]["file"] == "aura_research_manifest.py"

    packet_result = store.build_refactor_packet(
        "Refactor the Human Agent Arena",
        finding_ids=[finding["finding_id"]],
    )
    packet = packet_result["packet"]
    assert "aura_human_agent_arena.py" in packet["target_files"]
    assert "tests/test_aura_human_agent_arena.py" in packet["required_tests"]
    assert any("Human Agent Arena research-grounded refactoring" in item for item in packet["acceptance_criteria"])
    assert packet["external_evidence_is_patch_authority"] is False
    assert packet["human_approval_required"] is True


def test_research_evidence_is_stored_with_no_patch_authority(tmp_path: Path):
    store = EmergentResultsStore(tmp_path)
    stored = store.store_research_evidence(
        provider="arxiv",
        query="agent verification",
        results=[{"arxiv_id": "2601.00001", "title": "Verification"}],
        linked_finding_ids=["EMF-" + "a" * 20],
    )
    assert stored["ok"] is True
    evidence = store.get_research_evidence(stored["evidence_id"])["evidence"]
    assert evidence["external_evidence_is_patch_authority"] is False
    assert evidence["results"][0]["title"] == "Verification"


def test_arxiv_parser_preserves_canonical_metadata():
    xml = b"""<?xml version='1.0' encoding='UTF-8'?>
    <feed xmlns='http://www.w3.org/2005/Atom'>
      <entry>
        <id>https://arxiv.org/abs/2601.12345v2</id>
        <updated>2026-01-12T00:00:00Z</updated>
        <published>2026-01-10T00:00:00Z</published>
        <title>  Grounded   Agent Systems </title>
        <summary> Exact metadata and bounded sidecars. </summary>
        <author><name>Researcher One</name></author>
        <category term='cs.AI'/>
        <link href='https://arxiv.org/pdf/2601.12345v2' type='application/pdf'/>
      </entry>
    </feed>"""
    records = _parse_arxiv_atom(xml)
    assert records[0]["arxiv_id"] == "2601.12345"
    assert records[0]["versioned_id"] == "2601.12345v2"
    assert records[0]["version"] == 2
    assert records[0]["truth_class"] == ARXIV_METADATA_TRUTH
    assert records[0]["metadata_sha256"]


def test_arxiv_search_uses_forager_api_and_labels_sidecar(monkeypatch: pytest.MonkeyPatch):
    xml = b"""<feed xmlns='http://www.w3.org/2005/Atom'><entry>
    <id>https://arxiv.org/abs/2601.12345v1</id><title>Agent Arena</title>
    <summary>Research evidence.</summary><published>2026-01-01T00:00:00Z</published>
    <updated>2026-01-02T00:00:00Z</updated><author><name>A</name></author>
    <category term='cs.SE'/><link href='https://arxiv.org/pdf/2601.12345v1' type='application/pdf'/>
    </entry></feed>"""

    async def fake_fetch(self, *args, **kwargs):  # noqa: ANN001, ARG001
        return xml, 1

    async def fake_pdf(self, *args, **kwargs):  # noqa: ANN001, ARG001
        return "sidecar full text"

    monkeypatch.setattr(ArXivForager, "_fetch_arxiv_xml", fake_fetch)
    monkeypatch.setattr(ArXivForager, "_fetch_pdf_text", fake_pdf)

    result = ArenaResearchBridge().search_arxiv(
        "agent arena",
        limit=1,
        include_sidecars=True,
        sidecar_limit=1,
    )
    assert result["ok"] is True
    assert result["metadata_truth"] == ARXIV_METADATA_TRUTH
    assert result["results"][0]["sidecar"]["truth_class"] == SIDECAR_TRUTH


def test_github_search_normalizes_public_api_metadata(monkeypatch: pytest.MonkeyPatch):
    item = {
        "id": 1,
        "node_id": "R_1",
        "full_name": "example/agent-arena",
        "name": "agent-arena",
        "owner": {"login": "example"},
        "description": "A grounded arena",
        "html_url": "https://github.com/example/agent-arena",
        "url": "https://api.github.com/repos/example/agent-arena",
        "default_branch": "main",
        "language": "Python",
        "topics": ["agents"],
        "license": {"spdx_id": "MIT"},
        "stargazers_count": 42,
        "forks_count": 3,
        "open_issues_count": 1,
        "archived": False,
        "fork": False,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-02T00:00:00Z",
        "pushed_at": "2026-01-02T00:00:00Z",
        "score": 1.0,
    }

    monkeypatch.setattr(
        "aura_arena_research_bridge._github_json",
        lambda url: ({"total_count": 1, "incomplete_results": False, "items": [item]}, {"x-ratelimit-remaining": "9"}),
    )
    result = ArenaResearchBridge().search_github_repositories("agent arena", limit=1)
    assert result["ok"] is True
    assert result["metadata_truth"] == GITHUB_METADATA_TRUTH
    assert result["results"][0]["full_name"] == "example/agent-arena"
    assert result["results"][0]["metadata_sha256"]

    normalized = _github_repository_record(item)
    assert normalized["license"] == "MIT"
    assert normalized["truth_class"] == GITHUB_METADATA_TRUTH


def test_arena_api_search_packet_and_research_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    state.emergent_store.store_report(sample_report(), source="test")

    status, search = dispatch_api_request(
        state,
        "GET",
        "/api/human-agent/emergent/search?q=Human%20Agent%20Arena&limit=10",
    )
    assert status == 200
    assert search["count"] >= 1
    finding_id = search["findings"][0]["finding_id"]

    status, packet = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/emergent/refactor-packet",
        {"objective": "Refactor the Human Agent Arena", "finding_ids": [finding_id]},
    )
    assert status == 200
    assert packet["packet"]["selected_finding_ids"] == [finding_id]
    assert "emergent_refactor_packet" in state.workflow.evidence

    monkeypatch.setattr(
        state.research_bridge,
        "search",
        lambda *args, **kwargs: {
            "ok": True,
            "provider": "github",
            "query": "agent arena",
            "count": 1,
            "results": [{"full_name": "example/agent-arena", "truth_class": GITHUB_METADATA_TRUTH}],
            "metadata_truth": GITHUB_METADATA_TRUTH,
            "sidecar_truth": SIDECAR_TRUTH,
        },
    )
    status, research = dispatch_api_request(
        state,
        "POST",
        "/api/human-agent/research/search",
        {"provider": "github", "query": "agent arena", "finding_ids": [finding_id]},
    )
    assert status == 200
    assert research["stored_evidence"]["created"] is True

    status, evidence_index = dispatch_api_request(
        state,
        "GET",
        "/api/human-agent/research/evidence",
    )
    assert status == 200
    assert evidence_index["count"] == 1


def test_prepare_payload_merges_emergent_acceptance_criteria(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    state.emergent_store.store_report(sample_report(), source="test")
    state.workflow.objective = "Refactor the Human Agent Arena"
    state.workflow.evidence["objective"] = state.workflow.objective

    merged, context = _prepare_payload_with_emergent_context(
        state,
        {"acceptance_criteria": ["Keep existing server routes compatible"]},
    )

    assert context["ok"] is True
    assert "Keep existing server routes compatible" in merged["acceptance_criteria"]
    assert any("Human Agent Arena research-grounded refactoring" in item for item in merged["acceptance_criteria"])
    assert state.workflow.evidence["emergent_refactor_packet"]["human_approval_required"] is True


def test_state_endpoint_exposes_emergent_workspace(tmp_path: Path):
    state = HumanAgentArenaServerState(tmp_path, demo=True)
    state.emergent_store.store_report(sample_report(), source="test")
    status, result = dispatch_api_request(state, "GET", "/api/human-agent/state")
    assert status == 200
    assert result["emergent_workspace"]["total"] >= 1
    assert result["patch_authority"] == "exact_source_spans_and_hashes_only"
    assert result["vsa_patch_authority"] is False
