from pathlib import Path

from aura_repo_localizer import topological_context_fallback_candidates
from aura_topological_context_anchor import CodeTopoAnchor, render_builder_context


def test_indexes_python_functions_and_classes_with_exact_line_spans():
    source = "\n".join(
        [
            "import requests",
            "",
            "class Worker:",
            "    def method(self):",
            "        return helper()",
            "",
            "def helper():",
            "    return 1",
        ]
    )

    nodes = CodeTopoAnchor.index_python_source("worker.py", source)
    by_symbol = {node.symbol: node for node in nodes}

    assert by_symbol["Worker"].kind == "class"
    assert by_symbol["Worker"].start_line == 3
    assert by_symbol["Worker"].end_line == 5
    assert by_symbol["method"].kind == "method"
    assert by_symbol["method"].parent_symbol == "Worker"
    assert by_symbol["helper"].start_line == 7
    assert by_symbol["helper"].source_hash


def test_finds_callers_and_callees_for_simple_file():
    source = "\n".join(
        [
            "def alpha():",
            "    return beta()",
            "",
            "def beta():",
            "    return 2",
        ]
    )
    anchor = CodeTopoAnchor.build_from_files({"demo.py": source})

    callers = anchor.callers_of("beta")
    callees = anchor.callees_of("alpha")

    assert callers.grounding_ok is True
    assert [node.symbol for node, _score in callers.ranked_neighbors] == ["alpha"]
    assert [node.symbol for node, _score in callees.ranked_neighbors] == ["beta"]


def test_finds_external_api_calls_with_exact_evidence():
    source = "\n".join(
        [
            "import requests as rq",
            "from openai import OpenAI",
            "",
            "def fetch():",
            "    client = OpenAI()",
            "    return rq.get('https://example.test')",
        ]
    )
    anchor = CodeTopoAnchor.build_from_files({"api_client.py": source})

    result = anchor.lookup_external_call("requests.get")

    assert result.grounding_ok is True
    assert result.external_calls[0]["caller_symbol"] == "fetch"
    assert result.external_calls[0]["file_path"] == "api_client.py"
    assert result.external_calls[0]["caller_span"] == [4, 6]
    assert result.external_calls[0]["line"] == 6


def test_nearest_context_includes_target_span_and_one_hop_neighbors():
    source = "\n".join(
        [
            "def alpha():",
            "    return beta()",
            "",
            "def beta():",
            "    return 2",
        ]
    )
    test_source = "from demo import beta\n\ndef test_beta():\n    assert beta() == 2\n"
    anchor = CodeTopoAnchor.build_from_files({"demo.py": source, "test_demo.py": test_source})

    packet = anchor.nearest_context("beta", radius=1)

    assert packet.target_nodes[0].symbol == "beta"
    assert any(span["role"] == "target" and span["start_line"] == 4 for span in packet.source_spans)
    assert any(summary["symbol"] == "alpha" for summary in packet.neighbor_summaries)
    assert packet.tests == ["test_demo.py"]


def test_syntax_error_warns_and_grounding_is_false():
    anchor = CodeTopoAnchor.build_from_files({"broken.py": "def bad(:\n    pass\n"})

    result = anchor.lookup_symbol("bad")

    assert result.grounding_ok is False
    assert any("syntax_error:broken.py" in warning for warning in anchor.warnings)
    assert result.route_diagnostics["grounding_ok"] is False


def test_vsa_affinity_ranking_is_deterministic_and_not_patch_authority():
    source = "def alpha_rank_target():\n    return 1\n\ndef other():\n    return 2\n"
    anchor = CodeTopoAnchor.build_from_files({"demo.py": source})
    candidates = [node for node in anchor.nodes.values() if node.kind != "module"]

    first = anchor.rank_affinity("alpha rank", candidates)
    second = anchor.rank_affinity("alpha rank", candidates)
    fake = anchor.lookup_symbol("missing_symbol")

    assert [(node.node_id, score) for node, score in first] == [(node.node_id, score) for node, score in second]
    assert fake.grounding_ok is False
    assert fake.route_diagnostics["vsa_patch_authority"] is False


def test_fake_symbol_explains_target_symbol_unresolved():
    anchor = CodeTopoAnchor.build_from_files({"demo.py": "def real_symbol():\n    return 1\n"})

    result = anchor.lookup_symbol("fake_symbol")
    explanation = anchor.explain_grounding(result)

    assert result.exact_hits == []
    assert "target_symbol_unresolved" in explanation["reasons"]


def test_render_builder_context_includes_source_hash_and_exact_span():
    anchor = CodeTopoAnchor.build_from_files({"demo.py": "def target():\n    return 1\n"})
    packet = anchor.nearest_context("target")

    rendered = render_builder_context(packet)

    assert "source_hash=" in rendered
    assert "exact_span: demo.py:1-2 symbol=target" in rendered
    assert "patch_authority: exact source spans with source_hash only" in rendered


def test_topological_fallback_localization_returns_five_or_fewer_candidates(tmp_path: Path):
    (tmp_path / "worker.py").write_text("def special_anchor():\n    return 1\n", encoding="utf-8")
    (tmp_path / "helper.py").write_text("def helper():\n    return special_anchor()\n", encoding="utf-8")

    candidates = topological_context_fallback_candidates("special_anchor is failing", tmp_path)

    assert len(candidates) <= 5
    assert candidates[0].path == "worker.py"
    assert "special_anchor" in candidates[0].symbols


def test_topological_anchor_requires_no_new_dependencies():
    source = Path("aura_topological_context_anchor.py").read_text(encoding="utf-8")

    assert "import numpy" not in source
    assert "tree_sitter" not in source
