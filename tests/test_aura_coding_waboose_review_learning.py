from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from aura_agent_arena_review_learning_bridge import ReviewLearningAgentArenaBridge
from aura_agent_arena_review_learning_mcp import REVIEW_LEARNING_TOOL_DEFINITIONS
from aura_coding_waboose_review_learning import ReviewLearningCodingWaboose

SOURCE_REGISTRY = (
    Path(__file__).resolve().parents[1]
    / ".aura"
    / "review_lessons"
    / "pr164_spatial_review_lessons.json"
)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "review-learning@example.test")
    _git(repo, "config", "user.name", "Review Learning")
    (repo / ".aura" / "review_lessons").mkdir(parents=True)
    shutil.copy2(SOURCE_REGISTRY, repo / ".aura" / "review_lessons" / SOURCE_REGISTRY.name)
    (repo / "module.py").write_text(
        "MAX_LINK_COUNT = 20\n\n"
        "def compile_packet(metadata, links):\n"
        "    packet = {\n"
        "        'automatic_merge': False,\n"
        "        **metadata,\n"
        "    }\n"
        "    bounded = links[:MAX_LINK_COUNT]\n"
        "    bounded = sorted(bounded)\n"
        "    return packet, bounded\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "fixture")
    return repo


def test_review_learning_waboose_adds_summary_and_probable_findings(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    waboose = ReviewLearningCodingWaboose(
        repo,
        learning_root=tmp_path / "coderabbit-learning",
        review_learning_root=tmp_path / "review-learning",
    )
    prepared = waboose.prepare(
        {
            "objective": "Review the packet compiler for recurring PR164 defect classes",
            "mode": "files",
            "changed_files": ["module.py"],
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["typed_review_lesson_summary"]["lesson_count"] == 13

    scanned = waboose.scan(prepared["review_id"])
    assert scanned["ok"] is True
    codes = {item["code"] for item in scanned["typed_review_lesson_findings"]}
    assert "PROTECTED_AUTHORITY_OVERRIDE_SHAPE" in codes
    assert "TRUNCATE_BEFORE_SORT_SHAPE" in codes
    assert "COUNT_ONLY_BOUND_SHAPE" in codes
    assert all(item["repair_authority"] is False for item in scanned["typed_review_lesson_findings"])

    packet = waboose.agent_packet(prepared["review_id"])
    assert packet["typed_review_lesson_findings"]
    assert any("probable investigative focus" in row for row in packet["agent_instructions"])


def test_external_review_adapter_preserves_head_and_disposition(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    waboose = ReviewLearningCodingWaboose(repo, review_learning_root=tmp_path / "review-learning")
    head = _git(repo, "rev-parse", "HEAD")
    packet = waboose.normalize_external_review(
        {
            "head_sha": head,
            "pr_number": 164,
            "review_threads": [
                {
                    "path": "module.py",
                    "line": 5,
                    "is_outdated": False,
                    "comments": [
                        {
                            "id": 7,
                            "author": {"login": "chatgpt-codex-connector"},
                            "body": "Prevent caller metadata from overriding authority claims.",
                        }
                    ],
                }
            ],
        },
        current_head=head,
    )
    assert packet["finding_count"] == 1
    finding = packet["findings"][0]
    assert finding["reviewer"] == "Codex"
    assert finding["disposition"] == "current_head"
    assert finding["source_grounded"] is False
    assert packet["automatic_merge"] is False


def test_review_learning_rejects_false_current_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    waboose = ReviewLearningCodingWaboose(repo, review_learning_root=tmp_path / "review-learning")
    with pytest.raises(ValueError, match="does not match"):
        waboose.normalize_external_review(
            {"head_sha": "0" * 40, "comments": []},
            current_head="0" * 40,
        )


def test_agent_bridge_projection_and_mcp_registration(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    bridge = ReviewLearningAgentArenaBridge(
        repo_root=str(repo),
        review_learning_root=tmp_path / "review-learning",
    )
    summary = bridge.aura_waboose_review_lesson_summary()
    assert summary["lesson_count"] == 13
    replay = bridge.aura_waboose_crucible_replay()
    assert replay["status"] == "PASSED"
    assert replay["passed_count"] == 13
    source_scan = bridge.coding_waboose.review_lessons.scan_source(
        file="module.py",
        source=(repo / "module.py").read_text(encoding="utf-8"),
    )
    assert source_scan["finding_count"] >= 3

    names = {item["name"] for item in REVIEW_LEARNING_TOOL_DEFINITIONS}
    assert {
        "aura_waboose_ingest_external_review",
        "aura_waboose_review_lesson_summary",
        "aura_waboose_run_review_detector",
        "aura_waboose_crucible_replay",
    } <= names


def test_affordance_cache_shape_is_valid() -> None:
    value = json.loads(
        (Path(__file__).resolve().parents[1] / ".aura" / "AFFORDANCE_MAP.json").read_text(
            encoding="utf-8"
        )
    )
    matches = [
        item for item in value["affordances"]
        if item["id"] == "aura.coding_waboose.review_lessons"
    ]
    assert len(matches) == 1
    assert matches[0]["patch_authority"] is False
    assert matches[0]["vsa_patch_authority"] is False
