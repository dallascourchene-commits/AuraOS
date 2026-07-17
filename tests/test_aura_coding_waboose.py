from __future__ import annotations

import json
from pathlib import Path
import subprocess

from aura_coding_waboose import CODING_WABOOSE_VERSION, CodingWaboose


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _write(repo: Path, relative: str, content: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "waboose"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "waboose@example.test")
    _git(repo, "config", "user.name", "Coding Waboose")
    _write(repo, "core.py", "def compute(value=1):\n    return value + 1\n")
    _write(repo, "caller.py", "from core import compute\n\ndef use():\n    return compute(1)\n")
    _write(
        repo,
        "Aura_Memory/live_topology_ast.json",
        json.dumps(
            {
                "nodes": [
                    {"id": "core.py::compute", "file": "core.py", "label": "compute", "kind": "function", "line": 1},
                    {"id": "caller.py::use", "file": "caller.py", "label": "use", "kind": "function", "line": 3},
                ],
                "edges": [
                    {"source": "caller.py::use", "target": "core.py::compute", "kind": "call"}
                ],
            }
        ),
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")
    _write(repo, "core.py", "def compute(value, increment):\n    return value + increment\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "change")
    return repo


def test_prepare_brands_public_owner_and_adds_unpowered_breadboard(tmp_path: Path) -> None:
    runtime = CodingWaboose(_repo(tmp_path))
    result = runtime.prepare(
        {
            "objective": "Review caller impact and malformed packet behavior",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )

    assert result["ok"] is True
    assert result["version"] == CODING_WABOOSE_VERSION
    assert result["product"] == "Coding Waboose"
    assert result["waboose_id"].startswith("WABOOSE-")
    assert result["diagnostic_breadboard"]["board"]["arena_id"] == "coding_waboose"
    assert result["diagnostic_breadboard"]["circuit_status"] == "GROUNDED_DIAGNOSTIC_CIRCUIT_UNPOWERED"
    assert result["contract"]["product"] == "Coding Waboose"
    assert result["automatic_merge"] is False


def test_scan_energizes_only_deterministic_components(tmp_path: Path) -> None:
    runtime = CodingWaboose(_repo(tmp_path))
    prepared = runtime.prepare(
        {
            "objective": "Review caller impact",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    scanned = runtime.scan(prepared["review_id"])

    components = {
        item["name"]: item for item in scanned["diagnostic_breadboard"]["components"]
    }
    assert components["standard_correctness"]["energized"] is True
    assert components["dependency_impact"]["energized"] is True
    assert components["test_adequacy"]["energized"] is False
    assert scanned["diagnostic_breadboard"]["circuit_status"] == "PARTIALLY_ENERGIZED_DIAGNOSTIC_CIRCUIT"
    assert scanned["agent_packet"]["packet_type"] == "AURA_CODING_WABOOSE_AGENT_PACKET_V1"


def test_exact_agent_finding_can_energize_named_focus_without_self_confirmation(tmp_path: Path) -> None:
    runtime = CodingWaboose(_repo(tmp_path))
    prepared = runtime.prepare(
        {
            "objective": "Review caller impact",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
            "focus_directives": [
                {
                    "name": "caller_contract",
                    "question": "Does the caller still satisfy the changed signature?",
                    "risk": "compatibility",
                    "direction": "callers",
                    "target_patterns": ["caller.py"],
                }
            ],
        }
    )
    runtime.scan(prepared["review_id"])
    directive = next(
        item
        for item in prepared["contract"]["focus_directives"]
        if item["name"] == "caller_contract"
    )
    submitted = runtime.submit_findings(
        prepared["review_id"],
        [
            {
                "category": "compatibility",
                "severity": "high",
                "title": "Caller supplies too few arguments",
                "message": "The direct caller still supplies one positional argument.",
                "impact": "The function raises TypeError at runtime.",
                "file": "caller.py",
                "line_start": 4,
                "evidence_excerpt": "return compute(1)",
                "suggested_fix": "Update the caller or add a compatible default.",
                "focus_directive_ids": [directive["directive_id"]],
                "confirmed": True,
            }
        ],
        agent_name="codex",
    )

    component = next(
        item
        for item in submitted["diagnostic_breadboard"]["components"]
        if item["directive_id"] == directive["directive_id"]
    )
    assert component["energized"] is True
    assert submitted["automatic_fix"] is False
    final = runtime.finalize(prepared["review_id"])
    agent_finding = next(item for item in final["findings"] if item["origin"] == "agent")
    assert agent_finding["agent_claimed_confirmation_ignored"] is True
    assert final["diagnostic_breadboard"]["authority"]["patch_authority"] is False


def test_status_exposes_breadboard_without_granting_execution(tmp_path: Path) -> None:
    runtime = CodingWaboose(_repo(tmp_path))
    prepared = runtime.prepare(
        {
            "objective": "Review",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    status = runtime.status(prepared["review_id"])
    assert status["product"] == "Coding Waboose"
    assert status["breadboard_status"] == "GROUNDED_DIAGNOSTIC_CIRCUIT_UNPOWERED"
    assert status["production_mutation"] is False
    assert status["automatic_pull_request"] is False
