import json
from pathlib import Path

from aura_repo_localizer import ast_symbol_index, localize_fault, parse_traceback_targets, run_agentless_fallback


def _write_codemap(root: Path) -> None:
    aura_dir = root / ".aura"
    aura_dir.mkdir()
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(
            {
                "files": [
                    {"path": "target.py", "role": "worker", "topology": {"neighbor_files": ["test_target.py"]}},
                    {"path": "keyword_only.py", "role": "target helper", "topology": {}},
                ],
                "symbol_index": {
                    "broken_symbol": [{"file": "target.py", "kind": "function", "line": 1}],
                },
            }
        ),
        encoding="utf-8",
    )


def test_parse_traceback_targets():
    text = 'Traceback\n  File "pkg/target.py", line 12, in run\nValueError: no'
    assert parse_traceback_targets(text) == ["pkg/target.py"]


def test_localizer_ranks_traceback_above_keyword_only_and_returns_evidence(tmp_path: Path):
    _write_codemap(tmp_path)
    (tmp_path / "target.py").write_text("def broken_symbol():\n    return 1\n", encoding="utf-8")
    (tmp_path / "keyword_only.py").write_text("def helper():\n    return 2\n", encoding="utf-8")
    (tmp_path / "test_target.py").write_text("def test_target():\n    assert True\n", encoding="utf-8")

    results = localize_fault(
        'Traceback\n  File "target.py", line 1, in broken_symbol\nplease repair target helper',
        tmp_path,
    )

    assert len(results) <= 5
    assert results[0].path == "target.py"
    assert any(reason.startswith("traceback_target") for reason in results[0].reasons)
    assert "broken_symbol" in results[0].symbols
    assert results[0].tests == ["test_target.py"]


def test_ast_symbol_match_works_without_codemap(tmp_path: Path):
    (tmp_path / "worker.py").write_text("def special_symbol():\n    return 1\n", encoding="utf-8")

    index = ast_symbol_index(tmp_path)
    results = localize_fault("special_symbol is failing", tmp_path)

    assert index["special_symbol"][0]["file"] == "worker.py"
    assert results[0].path == "worker.py"
    assert "symbol_match:special_symbol" in results[0].reasons


def test_agentless_fallback_is_structured(tmp_path: Path):
    (tmp_path / "worker.py").write_text("def special_symbol():\n    return 1\n", encoding="utf-8")

    packet = run_agentless_fallback("special_symbol is failing", tmp_path)

    assert packet["ok"] is True
    assert packet["localized_files"][0]["path"] == "worker.py"
    assert packet["suggested_task_id"] == "fallback_localize_repair"
