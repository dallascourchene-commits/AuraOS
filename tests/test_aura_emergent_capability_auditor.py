from pathlib import Path

from aura_coding_arena_grounding import ground_coding_arena_intent
from aura_emergent_capability_auditor import (
    AUDIT_ROUTE,
    CapabilitySymbol,
    audit_emergent_capabilities,
    find_unwired_capability_pairs,
    project_future_potentials,
    query_capability_audit,
    render_capability_audit_report,
)
from aura_topological_context_anchor import CodeTopoAnchor


def _write_capability_repo(root: Path, *, direct_edge: bool = False) -> None:
    if direct_edge:
        (root / "aura_st3gg_codec.py").write_text(
            "\n".join(
                [
                    "def render_topological_context():",
                    "    return 'source_hash topology'",
                    "",
                    "def encode_st3gg_token():",
                    "    return render_topological_context()",
                ]
            ),
            encoding="utf-8",
        )
    else:
        (root / "aura_st3gg_codec.py").write_text(
            "def encode_st3gg_token():\n    return 'st3gg token budget codec'\n",
            encoding="utf-8",
        )
        (root / "aura_topological_context_anchor.py").write_text(
            "def render_topological_context():\n    return 'source_hash topology exact span'\n",
            encoding="utf-8",
        )
    (root / "aura_verifier.py").write_text(
        "def verify_source_hash_context():\n    return 'verification pytest quality_gate'\n",
        encoding="utf-8",
    )
    (root / "test_aura_st3gg_codec.py").write_text(
        "from aura_st3gg_codec import encode_st3gg_token\n\n\ndef test_encode_st3gg_token():\n    assert encode_st3gg_token()\n",
        encoding="utf-8",
    )


def test_audit_emergent_capabilities_finds_unwired_complementary_pair(tmp_path: Path):
    _write_capability_repo(tmp_path)

    report = audit_emergent_capabilities(tmp_path)

    assert report.route == AUDIT_ROUTE
    assert report.safe_to_patch is False
    assert report.findings
    finding = report.findings[0]
    assert finding.safe_to_patch is False
    assert {"ST3GG_ENCODING", "TOPOLOGICAL_CONTEXT"} <= {symbol.role for symbol in finding.symbols}
    assert finding.proposed_edges[0].exists_now is False
    assert all(symbol.source_hash for symbol in finding.symbols)


def test_direct_topology_edge_suppresses_unwired_pair(tmp_path: Path):
    _write_capability_repo(tmp_path, direct_edge=True)
    anchor = CodeTopoAnchor.build_from_files(
        {path.name: path.read_text(encoding="utf-8") for path in tmp_path.glob("*.py")}
    )

    findings = find_unwired_capability_pairs(anchor)

    assert not [
        finding
        for finding in findings
        if {"encode_st3gg_token", "render_topological_context"} == {symbol.symbol for symbol in finding.symbols}
    ]


def test_project_future_potentials_is_read_only_and_deterministic(tmp_path: Path):
    _write_capability_repo(tmp_path)
    first = audit_emergent_capabilities(tmp_path).future_potentials
    second = audit_emergent_capabilities(tmp_path).future_potentials

    assert [item.finding_id for item in first] == [item.finding_id for item in second]
    assert any("ST3GG" in item.title for item in first)
    assert all(item.safe_to_patch is False for item in first)


def test_render_capability_audit_report_has_required_header(tmp_path: Path):
    _write_capability_repo(tmp_path)
    report = audit_emergent_capabilities(tmp_path)

    rendered = render_capability_audit_report(report)

    assert rendered.startswith("=== AURA EMERGENT CAPABILITY AUDIT ===")
    assert "safe_to_patch: False" in rendered
    assert "patch_authority: exact source spans and hashes only" in rendered


def test_query_capability_audit_returns_report_packet(tmp_path: Path):
    _write_capability_repo(tmp_path)

    packet = query_capability_audit("show emergent capability audit for all", tmp_path)

    assert packet["route"] == AUDIT_ROUTE
    assert packet["safe_to_patch"] is False
    assert packet["report"]["route"] == AUDIT_ROUTE
    assert packet["target_file"] is None
    assert packet["target_symbol"] is None


def test_grounding_query_path_routes_capability_audit_without_builder_target(tmp_path: Path):
    _write_capability_repo(tmp_path)

    packet = ground_coding_arena_intent("audit future potentials for all capabilities", tmp_path)

    assert packet["route"] == AUDIT_ROUTE
    assert packet["route_diagnostics"]["safe_to_patch"] is False
    assert packet["target_file"] is None


def test_subsystem_filter_limits_future_potentials(tmp_path: Path):
    (tmp_path / "aura_music_coding_arena.py").write_text(
        "def rank_music_candidates():\n    return 'music resonance ranking'\n",
        encoding="utf-8",
    )
    (tmp_path / "aura_builder_context.py").write_text(
        "def build_builder_context_packet():\n    return 'builder_context packet localization'\n",
        encoding="utf-8",
    )

    report = audit_emergent_capabilities(tmp_path, subsystem="music")

    assert report.subsystem == "music"
    assert all(finding.subsystem == "music" for finding in report.findings)


def test_find_unwired_capability_pairs_accepts_symbol_lists():
    left = CapabilitySymbol(
        symbol_id="left",
        role="ST3GG_ENCODING",
        file_path="aura_st3gg_codec.py",
        symbol="encode",
        kind="function",
        start_line=1,
        end_line=2,
        source_hash="hash-left",
        role_tags=["ST3GG_ENCODING"],
        subsystem_tags=["st3gg"],
        evidence={"source_hash": "hash-left"},
    )
    right = CapabilitySymbol(
        symbol_id="right",
        role="TOPOLOGICAL_CONTEXT",
        file_path="aura_topological_context_anchor.py",
        symbol="context",
        kind="function",
        start_line=1,
        end_line=2,
        source_hash="hash-right",
        role_tags=["TOPOLOGICAL_CONTEXT"],
        subsystem_tags=["st3gg"],
        evidence={"source_hash": "hash-right"},
    )

    findings = find_unwired_capability_pairs([left, right], [])

    assert len(findings) == 1
    assert findings[0].safe_to_patch is False


def test_project_future_potentials_accepts_symbol_lists():
    symbols = [
        CapabilitySymbol("st3gg", "ST3GG_ENCODING", "a.py", "encode", "function", 1, 2, "a", role_tags=["ST3GG_ENCODING"], subsystem_tags=["coding_arena"]),
        CapabilitySymbol("topo", "TOPOLOGICAL_CONTEXT", "b.py", "context", "function", 1, 2, "b", role_tags=["TOPOLOGICAL_CONTEXT"], subsystem_tags=["coding_arena"]),
        CapabilitySymbol("verify", "VERIFICATION", "c.py", "verify", "function", 1, 2, "c", role_tags=["VERIFICATION"], subsystem_tags=["coding_arena"]),
    ]

    potentials = project_future_potentials(symbols, [], subsystem="coding_arena")

    assert potentials
    assert potentials[0].safe_to_patch is False


def test_audit_query_is_passed_to_find_unwired_capability_pairs(tmp_path: Path):
    _write_capability_repo(tmp_path)

    report = audit_emergent_capabilities(tmp_path, query="st3gg topological")

    assert report.query == "st3gg topological"
    if report.findings:
        assert report.findings[0].confidence > 0.5


def test_subsystem_from_intent_prioritizes_exact_subsystem_names(tmp_path: Path):
    _write_capability_repo(tmp_path)

    packet = query_capability_audit("builder capability audit", tmp_path)

    assert packet["report"]["subsystem"] == "capability_audit"
