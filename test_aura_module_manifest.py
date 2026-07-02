import json
from pathlib import Path

from aura_module_manifest import (
    generate_module_manifest,
    inject_manifest_constraint,
    module_exists,
    symbol_exists,
)


def test_generate_module_manifest_finds_module_and_excludes_runtime_dirs(tmp_path: Path):
    (tmp_path / "demo.py").write_text("class Demo:\n    pass\n\n\ndef useful():\n    return 1\n", encoding="utf-8")
    (tmp_path / "test_demo.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "cached.py").write_text("def cached():\n    pass\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "ignored.py").write_text("def ignored():\n    pass\n", encoding="utf-8")
    (tmp_path / "Aura_Memory").mkdir()
    (tmp_path / "Aura_Memory" / "memory.py").write_text("def memory():\n    pass\n", encoding="utf-8")

    manifest = generate_module_manifest(tmp_path)
    paths = {item["path"] for item in manifest["modules"]}

    assert "demo.py" in paths
    assert "test_demo.py" not in paths
    assert "__pycache__/cached.py" not in paths
    assert ".git/ignored.py" not in paths
    assert "Aura_Memory/memory.py" not in paths
    assert module_exists(manifest, "demo.py") is True
    assert module_exists(manifest, "hallucinated.py") is False
    assert symbol_exists(manifest, "demo.py", "useful") is True


def test_inject_manifest_constraint_is_compact(tmp_path: Path):
    modules = [{"path": f"module_{index}.py", "public_symbols": []} for index in range(100)]
    modules.append({"path": "aura_live_architect.py", "public_symbols": ["run_live_architect_transaction"]})
    aura_dir = tmp_path / ".aura"
    aura_dir.mkdir()
    (aura_dir / "MODULE_MANIFEST.json").write_text(
        json.dumps({"manifest_version": "1.0", "modules": modules}),
        encoding="utf-8",
    )

    constraint = inject_manifest_constraint(tmp_path)

    assert "manifest_hash:" in constraint
    assert "module_count: 101" in constraint
    assert "- aura_live_architect.py" in constraint
    assert "module_99.py" not in constraint
    assert len(constraint) < 2500
