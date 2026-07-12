"""Focused contracts for the AMD Track 3 operational Crucible demo."""
from __future__ import annotations

import json
from pathlib import Path

from aura_amd_track3_cli import build_parser, run_cycle, status
from aura_amd_track3_types import CodingTask, PatchProposal
from aura_amd_track3_worker import FixtureProvider, load_tasks, run_task

REPO_ROOT = Path(__file__).resolve().parents[1]
TASKS = REPO_ROOT / ".aura" / "amd_track3_demo_tasks.json"


def test_task_contract_rejects_unauthorized_paths():
    task = CodingTask.from_dict({
        "task_id": "T",
        "objective": "test",
        "allowed_files": ["safe.py"],
        "test_command": ["python", "-c", "pass"],
    })
    try:
        PatchProposal.from_dict(
            {"summary": "bad", "files": {"unsafe.py": "x"}},
            task=task,
            provider="fixture",
            model="fixture",
        )
    except ValueError as exc:
        assert "unauthorized" in str(exc)
    else:
        raise AssertionError("unauthorized proposal was accepted")


def test_fixture_cycle_creates_verified_crystals_without_mutating_source(tmp_path):
    tasks = load_tasks(TASKS)
    crystal_path = tmp_path / "verified_crystals.jsonl"
    originals = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for task in tasks
        for path in task.allowed_files
    }
    results = [
        run_task(
            task=task,
            provider=FixtureProvider(),
            repo_root=REPO_ROOT,
            crystal_path=crystal_path,
            amd_backend="CI fixture",
        )
        for task in tasks
    ]
    assert all(item["ok"] for item in results)
    rows = [json.loads(line) for line in crystal_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 3
    assert all(row["training_eligible"] is True for row in rows)
    assert all(row["test_returncode"] == 0 for row in rows)
    for path, original in originals.items():
        assert (REPO_ROOT / path).read_text(encoding="utf-8") == original


def test_cli_exposes_operational_paths_and_no_git_automation(tmp_path):
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert set(commands) == {"run-once", "run-loop", "status", "serve"}
    args = parser.parse_args([
        "--repo-root", str(REPO_ROOT),
        "--tasks", str(TASKS),
        "--crystals", str(tmp_path / "crystals.jsonl"),
        "run-once",
        "--provider", "fixture",
    ])
    result = run_cycle(args)
    assert result["ok"] is True
    assert result["automatic_commit"] is False
    assert result["automatic_push"] is False
    assert result["automatic_merge"] is False
    report = status(args)
    assert report["track"] == "AMD Hackathon Act II Track 3"
    assert report["c3_authority_preserved"] is True
