"""Focused contracts for the AMD Track 3 Sovereign Learning Arena demo."""
from __future__ import annotations

import json
from pathlib import Path

from aura_amd_track3_cli import _dashboard_html, build_parser, demo_sequence, run_cycle, status
from aura_amd_track3_types import CodingTask, PatchProposal
from aura_amd_track3_worker import FixtureProvider, OllamaProvider, load_tasks, run_task

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


def test_polysynthetic_packet_requires_all_six_slots():
    raw = {
        "task_id": "T",
        "objective": "test",
        "allowed_files": ["safe.py"],
        "test_command": ["python", "-c", "pass"],
        "metadata": {"intent_packet": {"DIR": "LOCAL"}},
    }
    try:
        CodingTask.from_dict(raw)
    except ValueError as exc:
        assert "canonical slots" in str(exc)
    else:
        raise AssertionError("incomplete intent packet was accepted")


def test_fixture_sequence_creates_two_crystals_and_reuses_first(tmp_path):
    crystal_path = tmp_path / "verified_crystals.jsonl"
    parser = build_parser()
    args = parser.parse_args([
        "--repo-root", str(REPO_ROOT),
        "--tasks", str(TASKS),
        "--crystals", str(crystal_path),
        "demo-sequence",
        "--provider", "fixture",
        "--reset-demo",
    ])
    originals = {
        path: (REPO_ROOT / path).read_text(encoding="utf-8")
        for task in load_tasks(TASKS)
        for path in task.allowed_files
    }
    result = demo_sequence(args)
    assert result["ok"] is True
    assert result["verified_count"] == 2
    assert result["reuse_count"] >= 1
    rows = [json.loads(line) for line in crystal_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert rows[0]["reused_crystal_ids"] == []
    assert rows[1]["reused_crystal_ids"] == [rows[0]["crystal_id"]]
    assert all(row["training_eligible"] is True for row in rows)
    assert all(row["test_returncode"] == 0 for row in rows)
    assert all(row["dissolution_verified"] is True for row in rows)
    assert all(row["source_checkout_mutated"] is False for row in rows)
    for path, original in originals.items():
        assert (REPO_ROOT / path).read_text(encoding="utf-8") == original


def test_direct_run_task_exposes_arena_and_guarded_route(tmp_path):
    task = load_tasks(TASKS)[0]
    result = run_task(
        task=task,
        provider=FixtureProvider(),
        repo_root=REPO_ROOT,
        crystal_path=tmp_path / "crystals.jsonl",
        amd_backend="CI fixture",
    )
    assert result["ok"] is True
    assert result["intent_packet"]["CLASS"] == "VALIDATION"
    assert "commit" in result["guarded_wfst"]["blocked"]
    assert result["arena"]["worker_is_replaceable"] is True
    assert result["automatic_commit"] is False
    assert result["automatic_push"] is False
    assert result["automatic_merge"] is False


def test_ollama_provider_defaults_to_local_3b_model_and_native_chat_endpoint():
    provider = OllamaProvider()
    assert provider.model == "qwen2.5-coder:3b"
    assert provider.chat_url == "http://127.0.0.1:11434/api/chat"
    assert provider.keep_alive == 0


def test_cli_and_dashboard_expose_demo_paths(tmp_path):
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    assert set(commands) == {"run-once", "run-loop", "demo-sequence", "status", "serve"}
    args = parser.parse_args([
        "--repo-root", str(REPO_ROOT),
        "--tasks", str(TASKS),
        "--crystals", str(tmp_path / "crystals.jsonl"),
        "run-once",
        "--provider", "fixture",
    ])
    result = run_cycle(args)
    assert result["ok"] is True
    report = status(args)
    assert report["track"] == "AMD Hackathon Act II Track 3"
    assert report["product"] == "Aura Sovereign Learning Arena"
    assert report["c3_authority_preserved"] is True
    assert report["amd_path"]["implemented"] is True
    html = _dashboard_html().decode("utf-8")
    assert "Aura Sovereign Learning Arena" in html
    assert "Polysynthetic Intent" in html
    assert "Sovereign Knowledge" in html
