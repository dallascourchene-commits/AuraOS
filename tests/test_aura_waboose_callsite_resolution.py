from __future__ import annotations

import json
from pathlib import Path
import subprocess

from aura_review_arena import AuraReviewArena


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _build_repo(tmp_path: Path, caller_source: str) -> Path:
    repo = tmp_path / "callsite-resolution"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "waboose@example.test")
    _git(repo, "config", "user.name", "Coding Waboose")
    _write(repo, "core.py", "def compute(value=1):\n    return value + 1\n")
    _write(repo, "caller.py", caller_source)
    _write(
        repo,
        "Aura_Memory/live_topology_ast.json",
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "core.py::compute",
                        "file": "core.py",
                        "label": "compute",
                        "kind": "function",
                        "line": 1,
                    },
                    {
                        "id": "caller.py::use",
                        "file": "caller.py",
                        "label": "use",
                        "kind": "function",
                        "line": 1,
                    },
                ],
                "edges": [
                    {
                        "source": "caller.py::use",
                        "target": "core.py::compute",
                        "kind": "call",
                    }
                ],
            }
        ),
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")
    _write(repo, "core.py", "def compute(value, increment):\n    return value + increment\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "change signature")
    return repo


def _review(repo: Path, *, profile: str = "precision") -> tuple[dict, dict]:
    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review cascading compatibility after signature change",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "profile": profile,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    scanned = arena.scan(prepared["review_id"])
    final = arena.finalize(prepared["review_id"])
    return scanned, final


def test_direct_from_import_is_corroborated_and_repair_eligible(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        "from core import compute\n\ndef use():\n    return compute(1)\n",
    )
    scanned, final = _review(repo)

    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "callsite-arity-mismatch"
    )
    callsite = next(
        item for item in finding["evidence"] if item["kind"] == "callsite"
    )
    assert finding["status"] == "corroborated"
    assert finding["confidence"] == 0.97
    assert callsite["target_resolved"] is True
    assert callsite["resolution"] == "from_import"
    assert final["forge_repair_requests"]


def test_module_alias_attribute_is_corroborated(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        "import core as c\n\ndef use():\n    return c.compute(1)\n",
    )
    scanned, final = _review(repo)

    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "callsite-arity-mismatch"
    )
    callsite = next(
        item for item in finding["evidence"] if item["kind"] == "callsite"
    )
    assert finding["status"] == "corroborated"
    assert callsite["resolution"] == "module_attribute"
    assert callsite["target_module"] == "core"
    assert final["forge_repair_requests"]


def test_imported_symbol_alias_is_corroborated(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        "from core import compute as calculate\n\ndef use():\n    return calculate(1)\n",
    )
    scanned, final = _review(repo)

    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "callsite-arity-mismatch"
    )
    callsite = next(
        item for item in finding["evidence"] if item["kind"] == "callsite"
    )
    assert callsite["target_resolved"] is True
    assert callsite["resolution"] == "from_import"
    assert final["forge_repair_requests"]


def test_unrelated_object_method_remains_probable_and_cannot_trigger_repair(
    tmp_path: Path,
) -> None:
    repo = _build_repo(
        tmp_path,
        "class Other:\n"
        "    def compute(self, value):\n"
        "        return value\n\n"
        "def use(obj):\n"
        "    return obj.compute(1)\n",
    )
    scanned, final = _review(repo, profile="exhaustive")

    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "callsite-arity-mismatch"
    )
    callsite = next(
        item for item in finding["evidence"] if item["kind"] == "callsite"
    )
    assert finding["status"] == "probable"
    assert finding["confidence"] == 0.72
    assert callsite["target_resolved"] is False
    assert callsite["resolution"] == "ambiguous_attribute"
    assert final["forge_repair_requests"] == []


def test_unimported_same_name_call_remains_ambiguous(tmp_path: Path) -> None:
    repo = _build_repo(
        tmp_path,
        "def compute(value):\n"
        "    return value\n\n"
        "def use():\n"
        "    return compute(1)\n",
    )
    scanned, final = _review(repo, profile="exhaustive")

    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "callsite-arity-mismatch"
    )
    callsite = next(
        item for item in finding["evidence"] if item["kind"] == "callsite"
    )
    assert callsite["target_resolved"] is False
    assert callsite["resolution"] == "ambiguous_name"
    assert finding["status"] == "probable"
    assert final["forge_repair_requests"] == []
