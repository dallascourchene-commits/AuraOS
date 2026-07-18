from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

import aura_emergent_evidence_spine as spine_module
from aura_emergent_evidence_spine import (
    AuraEmergentEvidenceSpine,
    build_atomic_function_inventory,
)


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


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "emergent-spine"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "spine@example.test")
    _git(repo, "config", "user.name", "Emergent Spine")
    _write(
        repo,
        "core.py",
        "def helper(value):\n"
        "    return value * 2\n\n"
        "def compute(value):\n"
        "    return helper(value) + 1\n\n"
        "class Worker:\n"
        "    def run(self, value):\n"
        "        return compute(value)\n\n"
        "def outer(value):\n"
        "    def inner(item):\n"
        "        return helper(item)\n"
        "    return inner(value)\n",
    )
    _write(
        repo,
        "caller.py",
        "from core import compute\n\n"
        "def use_compute(value):\n"
        "    return compute(value)\n",
    )
    _write(
        repo,
        "unrelated.py",
        "def unrelated_action():\n"
        "    return 'outside selected closure'\n",
    )
    _write(
        repo,
        "tests/test_core.py",
        "from core import compute\n\n"
        "def test_compute():\n"
        "    assert compute(2) == 5\n",
    )
    _write(
        repo,
        ".aura/CODEMAP.json",
        json.dumps(
            {
                "summary": {"file_count": 4, "topology_nodes": 8},
                "symbol_index": {
                    "compute": [
                        {
                            "file": "core.py",
                            "kind": "function",
                            "line": 4,
                            "end_line": 5,
                            "semantic_id": "core.py#function:compute",
                            "signature_hash": "compute-hash",
                        }
                    ]
                },
                "files": [
                    {"path": "core.py"},
                    {"path": "caller.py"},
                    {"path": "unrelated.py"},
                    {"path": "tests/test_core.py"},
                ],
                "command_index": {},
            }
        ),
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    return repo


def _resolution(objective: str, **_: object) -> dict:
    return {
        "version": "AURA_CAPABILITY_RESOLUTION_V2",
        "objective": objective,
        "exact_matches": [
            {
                "file": "core.py",
                "symbol": "compute",
                "kind": "function",
                "line_start": 4,
                "line_end": 5,
                "grounding_class": "EXACT",
            }
        ],
        "related_functions": [
            {
                "file": "caller.py",
                "symbol": "use_compute",
                "relationship": "topology_neighbor",
                "grounding_class": "EXACT",
            }
        ],
        "capability_connectome_path": {
            "ok": True,
            "graph_digest": "graph-digest",
            "path_digest": "path-digest",
            "path": ["grounding.compute"],
            "path_details": [
                {
                    "id": "grounding.compute",
                    "name": "Compute Grounding",
                    "implemented_by": ["core.py", "caller.py"],
                    "symbols": ["compute", "use_compute"],
                    "tests": ["tests/test_core.py"],
                    "risks": "Verify the exact caller closure.",
                }
            ],
        },
        "capability_path_digest": "path-digest",
        "capability_risks": ["Verify the exact caller closure."],
        "missing_capabilities": [],
    }


def _connectome(_: Path) -> dict:
    return {
        "ok": True,
        "version": "AURA_CAPABILITY_CONNECTOME_V1",
        "nodes": [
            {
                "id": "grounding.compute",
                "name": "Compute Grounding",
                "implemented_by": ["core.py", "caller.py"],
                "symbols": ["compute", "use_compute"],
                "tests": ["tests/test_core.py"],
                "truth_boundary": "exact_source",
            }
        ],
        "edges": [],
    }


@pytest.fixture
def grounded_services(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spine_module, "resolve_capabilities", _resolution)
    monkeypatch.setattr(spine_module, "build_capability_connectome", _connectome)
    monkeypatch.setattr(
        spine_module,
        "build_research_evidence_packet",
        lambda *args, **kwargs: {
            "ok": True,
            "advisory_only": True,
            "evidence_packet": {"papers": []},
        },
    )


def test_atomic_inventory_lists_all_callable_atoms_with_stable_identity(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    packet = build_atomic_function_inventory(repo)

    symbols = {
        (item["qualified_symbol"], item["kind"])
        for item in packet["atomic_functions"]
    }
    assert packet["ok"] is True
    assert ("helper", "function") in symbols
    assert ("compute", "function") in symbols
    assert ("Worker.run", "method") in symbols
    assert ("outer", "function") in symbols
    assert ("outer.inner", "nested_function") in symbols
    assert ("use_compute", "function") in symbols
    assert ("test_compute", "function") in symbols
    assert packet["total_count"] == len(packet["atomic_functions"])
    assert len(packet["inventory_digest"]) == 40
    assert all(item["source_hash"] for item in packet["atomic_functions"])
    assert packet["production_mutation"] is False


def test_inventory_computes_full_set_before_bounding_emission(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    full = build_atomic_function_inventory(repo)
    bounded = build_atomic_function_inventory(repo, query="compute", limit=2)

    assert bounded["total_count"] == full["total_count"]
    assert bounded["inventory_digest"] == full["inventory_digest"]
    assert bounded["emitted_count"] == 2
    assert bounded["truncated"] is True
    assert all("compute" in json.dumps(item).lower() for item in bounded["atomic_functions"])


def test_spine_uses_connectome_then_exact_atomic_dependency_closure(
    tmp_path: Path,
    grounded_services: None,
) -> None:
    repo = _repo(tmp_path)
    packet = AuraEmergentEvidenceSpine(repo).run(
        {
            "objective": "Assess emergent caller and verifier behavior around compute",
            "target_symbols": ["compute"],
            "target_arena": "agent_bridge",
            "radius": 1,
            "max_atomic_nodes": 16,
            "include_source": True,
        }
    )

    selected = {
        item["symbol"] for item in packet["atomic_inventory"]["selected_atomic_functions"]
    }
    assert packet["ok"] is True
    assert packet["status"] == "GROUNDED_ATOMIC_CLOSURE"
    assert packet["grounding_ok"] is True
    assert "compute" in selected
    assert "helper" in selected
    assert "use_compute" in selected
    assert "unrelated_action" not in selected
    assert packet["capability_connectome"]["path"]["path"] == ["grounding.compute"]
    assert packet["atomic_inventory"]["total_count"] > packet["atomic_inventory"]["selected_count"]
    assert any(edge["edge_type"] == "call" for edge in packet["dependency_edges"])
    assert any(item["symbol"] == "compute" and item["source"] for item in packet["source_slices"])
    assert "tests/test_core.py" in packet["tests"]
    assert packet["active_projection"]["selected_atomic_functions"]
    assert packet["waboose_focus_directives"][0]["name"] == "atomic_closure_integrity"
    assert packet["safe_to_patch"] is False
    assert packet["automatic_merge"] is False


def test_spine_projects_same_grounded_packet_to_coding_and_human_arenas(
    tmp_path: Path,
    grounded_services: None,
) -> None:
    repo = _repo(tmp_path)
    spine = AuraEmergentEvidenceSpine(repo)
    coding = spine.run(
        {
            "objective": "Improve compute safely",
            "target_symbols": ["compute"],
            "target_arena": "coding_arena",
        }
    )
    human = spine.run(
        {
            "objective": "Improve compute safely",
            "target_symbols": ["compute"],
            "target_arena": "human_agent",
        }
    )

    assert "core.py" in coding["active_projection"]["target_files"]
    assert "compute" in coding["active_projection"]["target_symbols"]
    assert coding["active_projection"]["waboose_focus_directives"]
    assert human["active_projection"]["review_questions"]
    assert coding["atomic_inventory"]["inventory_digest"] == human["atomic_inventory"]["inventory_digest"]


def test_affinity_only_fallback_never_claims_exact_grounding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = _repo(tmp_path)
    monkeypatch.setattr(
        spine_module,
        "resolve_capabilities",
        lambda *args, **kwargs: {
            "exact_matches": [],
            "related_functions": [],
            "capability_connectome_path": {"path_details": []},
            "missing_capabilities": [],
        },
    )
    monkeypatch.setattr(spine_module, "build_capability_connectome", lambda _: {"ok": True, "nodes": [], "edges": []})
    monkeypatch.setattr(
        spine_module,
        "build_research_evidence_packet",
        lambda *args, **kwargs: {"ok": True, "advisory_only": True},
    )

    packet = AuraEmergentEvidenceSpine(repo).run(
        {
            "objective": "an entirely novel capability phrase",
            "target_arena": "research",
            "max_atomic_nodes": 6,
        }
    )

    assert packet["ok"] is True
    assert packet["grounding_ok"] is False
    assert packet["approximate_only"] is True
    assert packet["safe_to_patch"] is False
    assert packet["active_projection"]["advisory_only"] is True


def test_invalid_repository_path_fails_closed_before_inventory_use(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    packet = AuraEmergentEvidenceSpine(repo).run(
        {
            "objective": "Inspect escaped file",
            "target_files": ["../outside.py"],
        }
    )

    assert packet["ok"] is False
    assert packet["safe_to_patch"] is False
    assert packet["production_mutation"] is False
    assert packet["automatic_pull_request"] is False
