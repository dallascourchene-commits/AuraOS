import json
from pathlib import Path

from aura_repair_kg import build_repair_kg


def test_repair_kg_builds_with_valid_codemap(tmp_path: Path):
    (tmp_path / ".aura").mkdir()
    (tmp_path / ".aura" / "CODEMAP.json").write_text(
        json.dumps(
            {
                "files": [{"path": "demo.py", "role": "core", "topology": {"neighbor_files": ["test_demo.py"]}}],
                "symbol_index": {"answer": [{"file": "demo.py", "kind": "function", "line": 1}]},
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    (tmp_path / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")

    kg = build_repair_kg(tmp_path)

    assert "file:demo.py" in kg.nodes
    assert "symbol:answer@demo.py" in kg.nodes
    assert kg.get_related_nodes("file:demo.py")


def test_repair_kg_builds_with_no_codemap(tmp_path: Path):
    (tmp_path / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    (tmp_path / "test_demo.py").write_text("from demo import answer\n", encoding="utf-8")

    kg = build_repair_kg(tmp_path)

    assert "file:demo.py" in kg.nodes
    assert "symbol:answer@demo.py" in kg.nodes
    assert "test:test_demo.py" in kg.nodes


def test_repair_kg_records_patch_and_research_lineage(tmp_path: Path):
    (tmp_path / "demo.py").write_text("def answer():\n    return 1\n", encoding="utf-8")
    kg = build_repair_kg(tmp_path)

    kg.add_patch_attempt(
        patch_id="patch-1",
        touched_files=["demo.py"],
        gate="temp_workspace",
        ok=False,
        failures=["pytest failed"],
    )
    kg.add_research_paper_support(
        arxiv_id="2509.06503",
        target_modules=["demo.py"],
        lesson="Use scorable tasks.",
        acceptance_test="Score is reproducible.",
    )
    packet = kg.evidence_packet_for_file("demo.py", depth=1)

    assert "patch_attempt:patch-1" in kg.nodes
    assert any(edge["type"] == "patch_touched" for edge in kg.edges["patch_attempt:patch-1"])
    assert "research_paper:2509.06503" in kg.nodes
    assert any(edge["type"] == "paper_supports" for edge in kg.edges["research_paper:2509.06503"])
    assert packet["nodes"]
    assert packet["edges"]
