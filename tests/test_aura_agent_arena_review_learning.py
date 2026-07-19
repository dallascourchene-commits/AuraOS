from __future__ import annotations

import json
from pathlib import Path
import subprocess

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_agent_arena_review_learning_mcp import handle_request


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


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "bridge@example.test")
    _git(repo, "config", "user.name", "Review Bridge")
    (repo / ".aura" / "review_lessons").mkdir(parents=True)
    source_registry = (
        Path(__file__).resolve().parents[1]
        / ".aura"
        / "review_lessons"
        / "pr164_spatial_review_lessons.json"
    )
    (repo / ".aura" / "review_lessons" / source_registry.name).write_text(
        source_registry.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    return repo


def test_bridge_lists_and_runs_review_learning_tools(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo),
        review_learning_root=tmp_path / "learning",
    )
    names = {item["name"] for item in bridge.list_tools()}
    assert {
        "aura_waboose_ingest_external_review",
        "aura_waboose_review_lesson_summary",
        "aura_waboose_run_review_detector",
        "aura_waboose_crucible_replay",
    } <= names

    summary = bridge.aura_waboose_review_lesson_summary()
    replay = bridge.aura_waboose_crucible_replay()
    finding = bridge.aura_waboose_run_review_detector(
        "detect_authority_aliases",
        {"automaticMerge": True},
    )

    assert summary["lesson_count"] == 13
    assert replay["status"] == "PASSED"
    assert finding["finding_count"] == 1
    assert all(packet["automatic_merge"] is False for packet in (summary, replay, finding))


def test_mcp_extension_delegates_base_tools_and_exposes_new_tools(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo),
        review_learning_root=tmp_path / "learning",
    )
    listed = handle_request(
        bridge,
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert listed is not None
    names = {item["name"] for item in listed["result"]["tools"]}
    assert "aura_repo_digest" in names
    assert "aura_waboose_crucible_replay" in names

    response = handle_request(
        bridge,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "aura_waboose_crucible_replay",
                "arguments": {},
            },
        },
    )
    assert response is not None
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["status"] == "PASSED"
    assert payload["automatic_pull_request"] is False


def test_bridge_normalizes_current_head_external_review(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    head = _git(repo, "rev-parse", "HEAD")
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo),
        review_learning_root=tmp_path / "learning",
    )
    result = bridge.aura_waboose_ingest_external_review(
        {
            "head_sha": head,
            "pr_number": 164,
            "comments": [
                {
                    "id": 1,
                    "author": {"login": "coderabbitai[bot]"},
                    "body": "Reject encoded separators in asset URIs.",
                    "path": "module.py",
                    "line": 1,
                }
            ],
        },
        current_head=head,
    )
    assert result["stored_count"] == 1
    assert result["findings"][0]["disposition"] == "current_head"
    assert result["findings"][0]["reviewer"] == "CodeRabbit"
    assert result["automatic_merge"] is False
