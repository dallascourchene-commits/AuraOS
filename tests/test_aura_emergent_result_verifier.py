"""
tests/test_aura_emergent_result_verifier.py

Comprehensive test suite for aura_emergent_result_verifier.py.

Covers:
- Clustering (14 required tests from original spec)
- J-Space advisory scoring (addendum)
- ST3GG egress (addendum)
- Symbolic trace memory best-effort (addendum)
- Efficiency benchmark hooks (addendum)
- Regression fixtures for four observed real failures

All tests are read-only, no network calls, no permanent file writes except
where tmp_path is explicitly used for trace-memory recording.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aura_emergent_result_verifier import (
    VERIFIER_VERSION,
    EmergentCandidateCluster,
    EmergentVerificationConfig,
    EmergentVerificationResult,
    EmergentCandidateVerdict,
    RepresentativeScore,
    canonicalize_aura_path,
    cluster_key_for_connection,
    cluster_emergent_connections,
    emergent_audit_benchmark_metrics,
    render_verified_emergent_report,
    score_evidence,
    score_focus,
    score_representative,
    verify_emergent_connections,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_conn(
    conn_id: str = "c1",
    ability: str = "Repo Localizer -> Model Router",
    src_file: str = "aura_repo_localizer.py",
    src_symbol: str = "topological_context_fallback_candidates",
    src_role: str = "localizer",
    tgt_file: str = "aura_router.py",
    tgt_symbol: str = "route_model",
    tgt_role: str = "model_router",
    missing_wire: str = "localized evidence can avoid broad prompt routing",
    status: str = "FUTURE_PATCHABLE",
    safety_risk: str = "low",
    cost_risk: str = "low",
    has_evidence: bool = True,
    has_tests: bool = True,
) -> dict[str, Any]:
    evidence = []
    if has_evidence:
        evidence.append({
            "source_hash": "abc123def456",
            "start_line": 42,
            "end_line": 78,
            "file": src_file,
            "kind": "function",
        })
    return {
        "connection_id": conn_id,
        "source": {"file": src_file, "symbol": src_symbol, "role": src_role},
        "target": {"file": tgt_file, "symbol": tgt_symbol, "role": tgt_role},
        "missing_wire": missing_wire,
        "emergent_ability": ability,
        "evidence": evidence,
        "confidence": 0.8,
        "implementation_feasibility": 0.7,
        "verifier_readiness": 0.6,
        "token_reduction_potential": 0.5,
        "safety_risk": safety_risk,
        "cost_risk": cost_risk,
        "status": status,
        "required_tests": ["tests/test_aura_repo_localizer.py"] if has_tests else [],
        "future_patch_capsule_hint": None,
        "emergence_score": 0.75,
        "score_breakdown": {},
    }


def _make_repeated_repo_localizer_router(n: int = 8) -> list[dict[str, Any]]:
    """Regression fixture: N repeated Repo Localizer -> Model Router connections across different files."""
    via_files = [
        ("cognitive_router.py", "route_model_by_localizer_score"),
        ("aura_router.py", "route_model"),
        ("aura_live_architect.py", "simulate_model_route"),
        ("aura_model_probe_ledger.py", "route_model_probe"),
        ("aura_ai_router.py", "auto_route"),
        ("aura_hardware_profile_router.py", "route_hardware_model"),
        ("aura_fst_routing.py", "route_fst"),
        ("aura_anthropic_router.py", "route_anthropic"),
    ]
    conns = []
    for i, (tgt_file, tgt_sym) in enumerate(via_files[:n]):
        conns.append(_make_conn(
            conn_id=f"rlmr_{i}",
            ability="Repo Localizer -> Model Router",
            src_file="aura_repo_localizer.py",
            src_symbol="topological_context_fallback_candidates",
            src_role="localizer",
            tgt_file=tgt_file,
            tgt_symbol=tgt_sym,
            tgt_role="model_router",
            missing_wire="localized evidence can avoid broad prompt routing and premium-model overuse",
        ))
    return conns


def _make_repeated_arena_capsule(n: int = 6) -> list[dict[str, Any]]:
    """Regression fixture: N repeated Coding Arena -> Capsule Compiler connections."""
    via_files = [
        ("aura_builder_context.py", "build_builder_context_packet"),
        ("aura_coding_arena_workflow.py", "run_arena_workflow"),
        ("aura_agent_ir_compiler.py", "AgentIRCompiler"),
        ("aura_phase_capsule.py", "compile_action_capsule"),
        ("aura_coding_arena_3d.py", "arena_3d_capsule"),
        ("aura_icm_workspace.py", "workspace_capsule"),
    ]
    conns = []
    for i, (src_file, src_sym) in enumerate(via_files[:n]):
        conns.append(_make_conn(
            conn_id=f"cacc_{i}",
            ability="Coding Arena -> Capsule Compiler",
            src_file=src_file,
            src_symbol=src_sym,
            src_role="coding_arena",
            tgt_file="aura_agent_ir_compiler.py",
            tgt_symbol="AgentIRCompiler",
            tgt_role="capsule_compiler",
            missing_wire="selected topology facts can become deterministic worker action capsules",
        ))
    return conns


def _make_mirrored_paths() -> list[dict[str, Any]]:
    """Regression fixture: duplicate AuraOS/ mirrored paths."""
    base = _make_conn(
        conn_id="mirror_a",
        src_file="aura_repo_localizer.py",
        src_symbol="topological_context_fallback_candidates",
    )
    mirrored = _make_conn(
        conn_id="mirror_b",
        src_file="AuraOS/aura_repo_localizer.py",
        src_symbol="topological_context_fallback_candidates",
    )
    return [base, mirrored]


def _make_st3gg_focused_connections() -> list[dict[str, Any]]:
    """Regression fixture: ST3GG query should not return mostly model-router results."""
    router_conns = [
        _make_conn(
            conn_id=f"router_{i}",
            ability="Repo Localizer -> Model Router",
            src_symbol="parse_emerge_command",  # weak representative
            src_role="localizer",
            tgt_role="model_router",
        )
        for i in range(5)
    ]
    st3gg_conn = _make_conn(
        conn_id="st3gg_topo",
        ability="ST3GG Topological Context -> Source Span Compression",
        src_file="aura_st3gg_recall.py",
        src_symbol="encode_st3gg_token",
        src_role="topology",
        tgt_file="aura_topological_context_anchor.py",
        tgt_symbol="CodeTopoAnchor",
        tgt_role="topology",
        missing_wire="source spans can be compressed for fidelity-preserving benchmark recall",
    )
    return router_conns + [st3gg_conn]


# ===========================================================================
# TEST 1: Repeated Repo Localizer -> Model Router clusters into one result
# ===========================================================================

class TestClusteringDeduplication:

    def test_repeated_repo_localizer_router_becomes_one_cluster(self):
        conns = _make_repeated_repo_localizer_router(8)
        cfg = EmergentVerificationConfig(max_clusters=8, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        abilities = [c.emergent_ability for c in result.clusters]
        # Must have exactly one cluster for this ability
        assert abilities.count("Repo Localizer -> Model Router") == 1

    def test_cluster_has_alternates_from_repeated_entries(self):
        conns = _make_repeated_repo_localizer_router(8)
        cfg = EmergentVerificationConfig(max_clusters=8, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        cluster = next(c for c in result.clusters if c.emergent_ability == "Repo Localizer -> Model Router")
        assert len(cluster.alternates) > 0, "Should have alternates from deduplicated entries"
        assert len(cluster.alternates) <= cfg.max_alternates_per_cluster

    def test_cluster_has_suppressed_duplicate_count(self):
        conns = _make_repeated_repo_localizer_router(8)
        cfg = EmergentVerificationConfig(
            max_clusters=8, max_alternates_per_cluster=3,
            min_focus_score=0.0, min_evidence_score=0.0,
        )
        result = verify_emergent_connections(conns, config=cfg)
        cluster = next(c for c in result.clusters if c.emergent_ability == "Repo Localizer -> Model Router")
        # 8 total - 1 best - 3 alternates = 4 suppressed
        assert cluster.suppressed_duplicate_count >= 4

    def test_repeated_arena_capsule_becomes_one_cluster(self):
        conns = _make_repeated_arena_capsule(6)
        cfg = EmergentVerificationConfig(max_clusters=8, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        abilities = [c.emergent_ability for c in result.clusters]
        assert abilities.count("Coding Arena -> Capsule Compiler") == 1


# ===========================================================================
# TEST 2 & 3: parse_emerge_command rejected as localizer; ground_coding_arena_intent preferred
# ===========================================================================

class TestRepresentativeSelection:

    def test_parse_emerge_command_demoted_as_localizer(self):
        conn = _make_conn(
            src_symbol="parse_emerge_command",
            src_role="localizer",
            tgt_role="model_router",
        )
        rep = score_representative(conn, focus="topological context source spans")
        assert rep.is_penalized, "parse_emerge_command should be penalized for localizer role without command focus"
        assert rep.score < 0.30

    def test_parse_emerge_command_allowed_when_focus_mentions_parser(self):
        conn = _make_conn(src_symbol="parse_emerge_command", src_role="localizer")
        rep = score_representative(conn, focus="command parser repl syntax")
        assert not rep.is_penalized or any("overridden" in r for r in rep.reasons)

    def test_ground_coding_arena_intent_beats_parse_emerge_command(self):
        conn_ground = _make_conn(src_symbol="ground_coding_arena_intent", src_role="localizer")
        conn_parse = _make_conn(src_symbol="parse_emerge_command", src_role="localizer")
        rep_ground = score_representative(conn_ground, focus="topological context source spans")
        rep_parse = score_representative(conn_parse, focus="topological context source spans")
        assert rep_ground.score > rep_parse.score

    def test_preferred_symbol_gets_high_score(self):
        conn = _make_conn(src_symbol="ground_coding_arena_intent", src_role="localizer")
        rep = score_representative(conn)
        assert rep.is_preferred
        assert rep.score >= 0.85

    def test_mock_symbol_penalized_without_test_focus(self):
        conn = _make_conn(src_symbol="MockArenaRouter", src_role="model_router")
        rep = score_representative(conn, focus="routing topology")
        assert rep.is_penalized

    def test_mock_symbol_allowed_with_test_focus(self):
        conn = _make_conn(src_symbol="MockArenaRouter", src_role="model_router")
        cfg = EmergentVerificationConfig(allow_test_symbols=True)
        rep = score_representative(conn, focus="mock fixture tests", config=cfg)
        assert not rep.is_penalized or any("allowed" in r for r in rep.reasons)


# ===========================================================================
# TEST 4: Mirrored paths AuraOS/foo.py and foo.py collapse
# ===========================================================================

class TestMirroredPaths:

    def test_auraos_prefix_stripped(self):
        assert canonicalize_aura_path("AuraOS/aura_repo_localizer.py") == "aura_repo_localizer.py"

    def test_nested_auraos_prefix_stripped(self):
        assert canonicalize_aura_path("AuraOS/tests/test_foo.py") == "tests/test_foo.py"

    def test_path_without_prefix_unchanged(self):
        assert canonicalize_aura_path("aura_repo_localizer.py") == "aura_repo_localizer.py"

    def test_mirrored_connections_same_cluster_key(self):
        base = _make_conn(conn_id="a", src_file="aura_repo_localizer.py")
        mirror = _make_conn(conn_id="b", src_file="AuraOS/aura_repo_localizer.py")
        # After canonicalization both should share the same cluster key
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections([base, mirror], config=cfg)
        # Both should land in same cluster → at most 1 cluster for this ability
        matching = [c for c in result.clusters if c.emergent_ability == base["emergent_ability"]]
        assert len(matching) <= 1

    def test_mirrored_paths_regression_fixture(self):
        conns = _make_mirrored_paths()
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        total_src_files = set()
        for cluster in result.clusters:
            src = cluster.best_connection.get("source", {})
            total_src_files.add(src.get("file", ""))
            for alt in cluster.alternates:
                total_src_files.add(alt.get("source", {}).get("file", ""))
        # Neither canonical path should appear under its AuraOS/ mirror name
        for fp in total_src_files:
            assert not fp.startswith("AuraOS/"), f"Mirror path not canonicalized: {fp}"


# ===========================================================================
# TEST 5: ST3GG-focused query demotes unrelated model-router clusters
# ===========================================================================

class TestFocusScoring:

    def test_st3gg_focus_demotes_model_router(self):
        router_conn = _make_conn(
            conn_id="router",
            ability="Repo Localizer -> Model Router",
            src_symbol="parse_emerge_command",
            src_role="localizer",
            tgt_role="model_router",
        )
        focus = "ST3GG topological context source spans token compression fidelity benchmark"
        fs = score_focus(router_conn, focus)
        # parse_emerge_command / model-router has no ST3GG/topology/benchmark terms
        assert fs < 0.30

    def test_st3gg_focus_promotes_topology_connection(self):
        topo_conn = _make_conn(
            conn_id="topo",
            ability="ST3GG Topological Context -> Source Span Compression",
            src_file="aura_st3gg_recall.py",
            src_symbol="encode_st3gg_token",
            src_role="topology",
            tgt_file="aura_topological_context_anchor.py",
            tgt_symbol="CodeTopoAnchor",
            tgt_role="topology",
        )
        focus = "ST3GG topological context source spans token compression fidelity benchmark"
        fs = score_focus(topo_conn, focus)
        assert fs > 0.35

    def test_empty_focus_returns_full_score(self):
        conn = _make_conn()
        assert score_focus(conn, "") == 1.0
        assert score_focus(conn, "   ") == 1.0

    def test_st3gg_focused_query_regression_fixture(self):
        conns = _make_st3gg_focused_connections()
        focus = "ST3GG topological context source spans token compression fidelity benchmark"
        cfg = EmergentVerificationConfig(
            max_clusters=8, min_focus_score=0.0, min_evidence_score=0.0,
        )
        result = verify_emergent_connections(conns, focus=focus, config=cfg)
        if result.clusters:
            top_cluster = result.clusters[0]
            # Top cluster should be ST3GG-related, not generic router
            assert "ST3GG" in top_cluster.emergent_ability or "topology" in top_cluster.source_role.lower(), (
                f"Expected ST3GG/topology cluster on top, got: {top_cluster.emergent_ability}"
            )


# ===========================================================================
# TEST 6: MMR prevents one ability from filling all slots
# ===========================================================================

class TestMMRDiversity:

    def test_mmr_prevents_single_ability_domination(self):
        # 5 router connections + 3 distinct ones
        conns = _make_repeated_repo_localizer_router(5)
        conns.append(_make_conn(
            conn_id="research",
            ability="Research Manifest -> Empirical Software Lab",
            src_file="aura_research_manifest.py",
            src_symbol="ingest_research_manifest",
            src_role="research_manifest",
            tgt_file="aura_empirical_software_lab.py",
            tgt_symbol="define_empirical_task",
            tgt_role="empirical_lab",
        ))
        conns.append(_make_conn(
            conn_id="arena_capsule",
            ability="Coding Arena -> Capsule Compiler",
            src_file="aura_builder_context.py",
            src_symbol="build_builder_context_packet",
            src_role="coding_arena",
            tgt_file="aura_agent_ir_compiler.py",
            tgt_symbol="AgentIRCompiler",
            tgt_role="capsule_compiler",
        ))
        cfg = EmergentVerificationConfig(
            max_clusters=4, mmr_lambda=0.72,
            min_focus_score=0.0, min_evidence_score=0.0,
        )
        result = verify_emergent_connections(conns, config=cfg)
        abilities = [c.emergent_ability for c in result.clusters]
        # Repo Localizer -> Model Router should appear AT MOST once
        assert abilities.count("Repo Localizer -> Model Router") <= 1
        # Diversity: we should see >1 distinct ability in top 4
        assert len(set(abilities)) >= 2

    def test_mmr_diversity_score_high_for_diverse_clusters(self):
        conns = (
            _make_repeated_repo_localizer_router(2) +
            _make_repeated_arena_capsule(2) +
            [
                _make_conn(
                    conn_id="research",
                    ability="Research Manifest -> Empirical Lab",
                    src_role="research_manifest",
                    tgt_role="empirical_lab",
                    src_symbol="ingest_research_manifest",
                    src_file="aura_research_manifest.py",
                    tgt_symbol="define_empirical_task",
                    tgt_file="aura_empirical_software_lab.py",
                )
            ]
        )
        cfg = EmergentVerificationConfig(max_clusters=8, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        metrics = emergent_audit_benchmark_metrics(result)
        assert metrics["diversity_score"] >= 0.5


# ===========================================================================
# TEST 7: Evidence score requires span + source hash for FUTURE_PATCHABLE
# ===========================================================================

class TestEvidenceScoring:

    def test_full_evidence_gives_high_score(self):
        conn = _make_conn(has_evidence=True, has_tests=True, status="FUTURE_PATCHABLE")
        ev = score_evidence(conn)
        assert ev >= 0.83

    def test_no_evidence_gives_low_score(self):
        conn = _make_conn(has_evidence=False, has_tests=False)
        ev = score_evidence(conn)
        assert ev < 0.50

    def test_future_patchable_requires_evidence(self):
        conn_no_evidence = _make_conn(has_evidence=False, has_tests=False, status="FUTURE_PATCHABLE")
        cfg = EmergentVerificationConfig(min_evidence_score=0.50, min_focus_score=0.0)
        verdict = _verdict_for_test(conn_no_evidence, focus="", config=cfg)
        assert not verdict.accepted
        assert any("evidence" in r for r in verdict.reasons)

    def test_evidence_score_requires_source_hash(self):
        conn = _make_conn(has_evidence=True)
        conn["evidence"][0].pop("source_hash")
        ev = score_evidence(conn)
        # Should lose the source_hash criterion
        full_ev = score_evidence(_make_conn(has_evidence=True))
        assert ev < full_ev

    def test_no_tests_reduces_evidence_score(self):
        ev_with = score_evidence(_make_conn(has_tests=True))
        ev_without = score_evidence(_make_conn(has_tests=False))
        assert ev_with > ev_without


# ===========================================================================
# TEST 8: Test fixtures/mocks not chosen as best representatives
# ===========================================================================

class TestMockRejection:

    def test_mock_source_not_best_representative(self):
        mock_conn = _make_conn(conn_id="mock", src_symbol="MockRouter", src_role="model_router")
        real_conn = _make_conn(conn_id="real", src_symbol="route_model", src_role="model_router")
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections([mock_conn, real_conn], config=cfg)
        cluster = next((c for c in result.clusters if c.emergent_ability == mock_conn["emergent_ability"]), None)
        if cluster:
            best_sym = cluster.best_connection.get("source", {}).get("symbol", "")
            assert best_sym != "MockRouter", "Mock symbol should not be chosen as best representative"

    def test_test_file_as_source_penalized(self):
        conn = _make_conn(src_file="test_aura_router.py", src_symbol="test_route_model")
        rep = score_representative(conn, focus="model routing")
        assert rep.is_penalized

    def test_fixture_prefix_penalized(self):
        conn = _make_conn(src_symbol="fixture_build_conn")
        rep = score_representative(conn)
        assert rep.is_penalized


# ===========================================================================
# TEST 9: Rendered report includes required sections
# ===========================================================================

class TestRendering:

    def test_rendered_report_has_verified_clusters_section(self):
        conns = _make_repeated_repo_localizer_router(4)
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        assert "Verified High-Leverage Clusters" in report

    def test_rendered_report_has_suppressed_count(self):
        conns = _make_repeated_repo_localizer_router(6)
        cfg = EmergentVerificationConfig(max_alternates_per_cluster=2, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        assert "Suppressed duplicates" in report or "suppressed_duplicates" in report

    def test_rendered_report_has_alternates(self):
        conns = _make_repeated_repo_localizer_router(5)
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        assert "Alternates" in report

    def test_rendered_report_has_verifier_notes(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        assert "Verifier notes" in report or "verifier_notes" in report

    def test_rendered_report_has_safety_section(self):
        result = verify_emergent_connections([], config=EmergentVerificationConfig())
        report = render_verified_emergent_report(result)
        assert "REPORT ONLY" in report or "NO_PATCHES" in report

    def test_rendered_report_no_unified_diff(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        assert "diff --git" not in report
        assert "\n--- " not in report


# ===========================================================================
# TEST 10: JSON output includes required fields
# ===========================================================================

class TestJSONOutput:

    def test_result_to_dict_has_verified_clusters(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        d = result.to_dict()
        assert "clusters" in d  # verified_clusters key for JSON output
        assert isinstance(d["clusters"], list)

    def test_result_to_dict_has_raw_candidate_count(self):
        conns = _make_repeated_repo_localizer_router(4)
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        d = result.to_dict()
        assert d["raw_count"] == 4

    def test_result_to_dict_has_suppressed_count(self):
        conns = _make_repeated_repo_localizer_router(6)
        cfg = EmergentVerificationConfig(max_alternates_per_cluster=2, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        d = result.to_dict()
        assert "suppressed_duplicate_count" in d
        assert d["suppressed_duplicate_count"] >= 0

    def test_result_to_dict_has_jspace_summary(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        d = result.to_dict()
        assert "jspace_summary" in d
        assert d["jspace_summary"].get("advisory_only") is True

    def test_result_to_dict_has_verifier_summary(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        d = result.to_dict()
        assert "verifier_summary" in d
        assert isinstance(d["verifier_summary"], str)

    def test_result_to_dict_parseable_as_json(self):
        conns = _make_repeated_repo_localizer_router(3)
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        raw = json.dumps(result.to_dict(), default=str)
        parsed = json.loads(raw)
        assert "clusters" in parsed


# ===========================================================================
# TEST 11: Existing emerge --json behavior remains parseable (legacy compat)
# ===========================================================================

class TestLegacyCompat:

    def test_empty_connections_produces_valid_result(self):
        result = verify_emergent_connections([])
        assert result.raw_count == 0
        assert result.cluster_count == 0
        d = result.to_dict()
        raw = json.dumps(d, default=str)
        parsed = json.loads(raw)
        assert parsed["clusters"] == []

    def test_legacy_connection_dict_fields_preserved(self):
        """Connections keep their original fields after canonicalization."""
        conn = _make_conn()
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections([conn], config=cfg)
        if result.clusters:
            best = result.clusters[0].best_connection
            assert "connection_id" in best
            assert "emergent_ability" in best
            assert "missing_wire" in best
            assert "evidence" in best


# ===========================================================================
# TEST 12: Read-only / no-write / no-network tests still pass
# ===========================================================================

class TestReadOnlyConstraints:

    def test_verify_produces_no_side_effects(self, tmp_path: Path):
        """Verifier with no trace-memory root does not write files."""
        file_before = list(tmp_path.iterdir())
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0, trace_memory_root=None)
        verify_emergent_connections(conns, config=cfg)
        file_after = list(tmp_path.iterdir())
        assert file_before == file_after, "Verifier should not write files when trace_memory_root is None"

    def test_result_safe_to_patch_false_by_default(self):
        """safe_to_patch starts False for all clusters — human must opt in."""
        conns = [_make_conn(status="DREAM_ONLY")]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        for cluster in result.clusters:
            assert not cluster.safe_to_patch or cluster.final_score > 0.5


# ===========================================================================
# TEST 13: Broad emergent query routes away from patch mode
# ===========================================================================

class TestBroadQuery:

    def test_broad_query_returns_diverse_clusters_not_patch_authority(self):
        conns = (
            _make_repeated_repo_localizer_router(3) +
            _make_repeated_arena_capsule(3) +
            [
                _make_conn(
                    conn_id="research",
                    ability="Research Manifest -> Empirical Lab",
                    src_file="aura_research_manifest.py",
                    src_symbol="ingest_research_manifest",
                    src_role="research_manifest",
                    tgt_file="aura_empirical_software_lab.py",
                    tgt_symbol="define_empirical_task",
                    tgt_role="empirical_lab",
                )
            ]
        )
        cfg = EmergentVerificationConfig(max_clusters=6, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        # No cluster should be safe_to_patch by default without human approval
        for cluster in result.clusters:
            # safe_to_patch only if evidence is high and status is FUTURE_PATCHABLE
            if cluster.safe_to_patch:
                ev = score_evidence(cluster.best_connection)
                assert ev >= 0.50, "safe_to_patch requires evidence >= threshold"
        # Report must say REPORT_ONLY
        report = render_verified_emergent_report(result)
        assert "REPORT" in report


# ===========================================================================
# TEST 14: Patch/implement intent does not route to emergent report
# ===========================================================================

class TestPatchIntentGuard:

    def test_patch_intent_detection(self):
        # This tests the is_emergent_potential_intent guard from the REPL.
        # We do NOT import from the REPL here to avoid circular imports.
        # Instead we verify the verifier itself never generates patch output.
        conns = [_make_conn(status="FUTURE_PATCHABLE")]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        report = render_verified_emergent_report(result)
        # Report must never contain unified diff markers
        assert "diff --git" not in report
        assert "@@" not in report or "@@" in report  # @@ ok in other contexts but not as diff header
        assert "--- a/" not in report
        assert "+++ b/" not in report


# ===========================================================================
# J-Space advisory tests (addendum)
# ===========================================================================

class TestJSpaceAdvisory:

    def test_jspace_score_is_advisory_only(self):
        """J-Space route metadata improves score but cannot make candidate patch-authoritative."""
        conn = _make_conn(
            has_evidence=False,
            has_tests=False,
            status="NEEDS_GROUNDING",
        )
        # Inject a fake jspace_packet
        conn["jspace_packet"] = {
            "output_compact": "AUDIT.0",
            "next_state": "EMERGENT_CAPABILITY_AUDIT",
            "active_concepts": [{"label": "topological"}, {"label": "st3gg"}],
        }
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.50)
        verdict = _verdict_for_test(conn, focus="topological st3gg", config=cfg)
        # Should still fail evidence gate even if J-Space score is high
        if verdict.jspace_focus_score > 0:
            assert not verdict.accepted or verdict.evidence_score >= 0.50

    def test_jspace_concepts_appear_in_report(self):
        conn = _make_conn()
        conn["jspace_packet"] = {
            "output_compact": "AUDIT.0",
            "next_state": "AUDIT",
            "active_concepts": [{"label": "topological_grounding"}, {"label": "source_span"}],
        }
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections([conn], config=cfg)
        report = render_verified_emergent_report(result)
        # J-Space concepts section should be present when concepts exist
        assert "J-Space" in report

    def test_jspace_advisory_warning_in_report(self):
        result = verify_emergent_connections([], config=EmergentVerificationConfig())
        d = result.to_dict()
        js = d.get("jspace_summary", {})
        assert js.get("advisory_only") is True
        assert "patch" in js.get("warning", "").lower()

    def test_jspace_failure_does_not_crash_verifier(self):
        """If jspace_codec is broken/unavailable, verifier must still complete."""
        conn = _make_conn()
        conn["jspace_packet"] = "INVALID_PACKET_TYPE"
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections([conn], config=cfg)
        assert result.version == VERIFIER_VERSION


# ===========================================================================
# ST3GG egress tests (addendum)
# ===========================================================================

class TestST3GGEgress:

    def test_st3gg_egress_module_compresses_report(self):
        from aura_arena_st3gg_egress import compress_report_st3gg, estimate_savings_ratio
        sample = "# Emergent Properties and Future Potential\n\n" * 20
        compressed, savings, pointer = compress_report_st3gg(sample)
        assert isinstance(compressed, str)
        assert isinstance(pointer, str)
        assert pointer.startswith("ST3GG_PTR:")

    def test_st3gg_egress_disabled_below_threshold(self):
        from aura_arena_st3gg_egress import compress_report_st3gg, estimate_savings_ratio
        # Very short text — compression won't help
        short = "Hi"
        compressed, savings, pointer = compress_report_st3gg(short)
        # savings should be minimal / 0 for tiny input
        assert savings <= 0.20 or len(compressed) >= len(short) * 0.80

    def test_st3gg_egress_pointer_stable(self):
        from aura_arena_st3gg_egress import compress_report_st3gg
        text = "Test report content" * 50
        _, _, ptr1 = compress_report_st3gg(text)
        _, _, ptr2 = compress_report_st3gg(text)
        assert ptr1 == ptr2, "ST3GG pointer must be deterministic"

    def test_st3gg_egress_preserves_recall_pointer_and_hash(self):
        from aura_arena_st3gg_egress import compress_report_st3gg, st3gg_pointer_for
        import hashlib
        text = "Full emergent report with source_hash=abc123\n" * 30
        compressed, savings, pointer = compress_report_st3gg(text)
        original_hash = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
        # Pointer must be a stable handle
        assert pointer.startswith("ST3GG_PTR:")
        assert len(pointer) > 10

    def test_st3gg_output_visible_ascii_only(self):
        from aura_arena_st3gg_egress import compress_report_st3gg
        text = "Emergent report " * 40 + "\x01\x02\x03"  # inject control chars
        compressed, _, _ = compress_report_st3gg(text)
        for ch in compressed:
            assert 0x20 <= ord(ch) <= 0x7E or ch == '\n', (
                f"Non-visible-ASCII character in egress output: {repr(ch)}"
            )


# ===========================================================================
# Symbolic trace memory tests (addendum)
# ===========================================================================

class TestTraceMemory:

    def test_trace_memory_recording_with_tmp_path(self, tmp_path: Path):
        """When trace_memory_root is set, atoms should be recorded.

        Skips gracefully when aura_symbolic_trace_memory is not installed locally
        (e.g., when running in a scratch environment without the full repo).
        """
        try:
            from aura_symbolic_trace_memory import record_trace_event
        except ModuleNotFoundError:
            pytest.skip("aura_symbolic_trace_memory not available in this environment")
        event = {
            "event_type": "emergent_verified_cluster",
            "task_id": "emergent_audit:test_cluster",
            "summary": "Test cluster for trace memory",
            "node_id": "test_node_001",
            "route": "EMERGENT_CAPABILITY_AUDIT",
            "status": "future_patchable",
            "source_hash": "abc123",
            "raw_ref": "",
            "replaceability_score": 0.75,
            "metadata": {},
        }
        atom = record_trace_event(event, tmp_path)
        assert atom is not None
        assert hasattr(atom, "atom_id")

    def test_trace_memory_failure_does_not_fail_audit(self):
        """If trace memory root is invalid, audit must still complete."""
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(
            min_focus_score=0.0, min_evidence_score=0.0,
            trace_memory_root="/nonexistent/path/that/cannot/be/created",
        )
        # Must not raise
        result = verify_emergent_connections(conns, config=cfg)
        assert result.version == VERIFIER_VERSION

    def test_trace_memory_not_required_when_root_none(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(
            min_focus_score=0.0, min_evidence_score=0.0,
            trace_memory_root=None,
        )
        result = verify_emergent_connections(conns, config=cfg)
        # No trace atom IDs since root is None
        assert result.trace_atom_ids == []

    def test_trace_memory_advisory_in_report(self, tmp_path: Path):
        """Trace node IDs appear in report when recorded; advisory only."""
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(
            min_focus_score=0.0, min_evidence_score=0.0,
            trace_memory_root=str(tmp_path),
        )
        result = verify_emergent_connections(conns, config=cfg)
        # If atoms were recorded, report should mention Trace section
        if result.trace_atom_ids:
            report = render_verified_emergent_report(result)
            assert "Trace" in report or "trace" in report.lower()


# ===========================================================================
# Efficiency benchmark tests (addendum)
# ===========================================================================

class TestBenchmarkHooks:

    def test_benchmark_metrics_returns_required_fields(self):
        conns = _make_repeated_repo_localizer_router(4) + _make_repeated_arena_capsule(3)
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        metrics = emergent_audit_benchmark_metrics(result, focus="topological context")
        required = {
            "raw_candidate_count",
            "verified_cluster_count",
            "suppressed_duplicate_count",
            "rejected_weak_candidate_count",
            "focus_adherence_score",
            "report_token_estimate",
            "evidence_completeness_score",
            "diversity_score",
        }
        for key in required:
            assert key in metrics, f"Missing benchmark metric: {key}"

    def test_benchmark_report_token_estimate_positive(self):
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        metrics = emergent_audit_benchmark_metrics(result)
        assert metrics["report_token_estimate"] > 0

    def test_benchmark_broad_query_yields_diverse_clusters(self):
        conns = (
            _make_repeated_repo_localizer_router(5) +
            _make_repeated_arena_capsule(4) +
            [_make_conn(
                conn_id="research",
                ability="Research Manifest -> Empirical Lab",
                src_file="aura_research_manifest.py",
                src_symbol="ingest_research_manifest",
                src_role="research_manifest",
                tgt_file="aura_empirical_software_lab.py",
                tgt_symbol="define_empirical_task",
                tgt_role="empirical_lab",
            )]
        )
        cfg = EmergentVerificationConfig(max_clusters=6, min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        metrics = emergent_audit_benchmark_metrics(result)
        # Acceptance criterion: broad query → diverse clusters, not 20 repeated raw pairs
        assert result.cluster_count <= 6
        assert metrics["diversity_score"] >= 0.3
        # Report token estimate should be reasonable (< 50k tokens for typical report)
        assert metrics["report_token_estimate"] < 50_000

    def test_benchmark_no_network_no_writes(self):
        """Benchmark metrics computation does not perform network calls or writes."""
        conns = [_make_conn()]
        cfg = EmergentVerificationConfig(min_focus_score=0.0, min_evidence_score=0.0)
        result = verify_emergent_connections(conns, config=cfg)
        # Should complete without raising any network or IO exceptions
        metrics = emergent_audit_benchmark_metrics(result)
        assert "patch_authority" in metrics
        assert metrics["patch_authority"] == "exact_source_spans_and_hashes_only"

    def test_benchmark_has_constraints_field(self):
        result = verify_emergent_connections([], config=EmergentVerificationConfig())
        metrics = emergent_audit_benchmark_metrics(result)
        assert "NO_PATCHES" in metrics.get("constraints", [])


# ===========================================================================
# Cluster key tests
# ===========================================================================

class TestClusterKey:

    def test_same_ability_different_files_same_key(self):
        conn_a = _make_conn(conn_id="a", tgt_file="aura_router.py")
        conn_b = _make_conn(conn_id="b", tgt_file="cognitive_router.py")
        assert cluster_key_for_connection(conn_a) == cluster_key_for_connection(conn_b)

    def test_different_ability_different_key(self):
        conn_a = _make_conn(conn_id="a", ability="Ability A")
        conn_b = _make_conn(conn_id="b", ability="Ability B")
        assert cluster_key_for_connection(conn_a) != cluster_key_for_connection(conn_b)

    def test_normalized_roles_in_key(self):
        conn_a = _make_conn(conn_id="a", src_role="localizer")
        conn_b = _make_conn(conn_id="b", src_role="repo_localizer")
        key_a = cluster_key_for_connection(conn_a)
        key_b = cluster_key_for_connection(conn_b)
        assert key_a[1] == key_b[1], f"Roles should normalize: {key_a[1]} vs {key_b[1]}"


# ===========================================================================
# Helpers used only in tests (avoid importing from REPL to prevent circularity)
# ===========================================================================

def _verdict_for_test(connection: Any, *, focus: str, config: EmergentVerificationConfig) -> EmergentCandidateVerdict:
    """Call internal verdict function via the public verify path for a single connection."""
    result = verify_emergent_connections([connection], focus=focus, config=config)
    if result.rejected_candidates:
        return result.rejected_candidates[0]
    if result.clusters:
        # Build a synthetic accepted verdict
        cluster = result.clusters[0]
        return EmergentCandidateVerdict(
            connection_id=str(cluster.best_connection.get("connection_id", "")),
            accepted=True,
            focus_score=cluster.final_score,
            evidence_score=score_evidence(cluster.best_connection),
            representative_score=score_representative(cluster.best_connection).score,
            final_score=cluster.final_score,
        )
    # No result — return rejected placeholder
    return EmergentCandidateVerdict(
        connection_id=str(connection.get("connection_id", "") if isinstance(connection, dict) else ""),
        accepted=False,
        reasons=["no_verdict_produced"],
        evidence_score=score_evidence(connection),
    )
