from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import subprocess

from aura_coding_waboose_review_learning import (
    ReviewLessonAwareCodingWaboose,
    scan_python_review_lessons,
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


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "review-lessons@example.test")
    _git(repo, "config", "user.name", "Review Lessons")
    _git(repo, "commit", "--allow-empty", "-m", "bootstrap")
    registry_ancestor = _git(repo, "rev-parse", "HEAD")
    (repo / ".aura" / "review_lessons").mkdir(parents=True)
    source_registry = (
        Path(__file__).resolve().parents[1]
        / ".aura"
        / "review_lessons"
        / "pr164_spatial_review_lessons.json"
    )
    registry_payload = json.loads(source_registry.read_text(encoding="utf-8"))
    registry_payload["repository_head"] = registry_ancestor
    registry_payload["merge_commit"] = registry_ancestor
    unsigned = dict(registry_payload)
    unsigned.pop("registry_digest")
    canonical = json.dumps(
        unsigned,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    registry_payload["registry_digest"] = hashlib.blake2b(
        canonical,
        digest_size=20,
    ).hexdigest()
    (repo / ".aura" / "review_lessons" / source_registry.name).write_text(
        json.dumps(registry_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (repo / "module.py").write_text(
        "def compile_packet(metadata):\n"
        "    links = metadata.get('links', [])\n"
        "    bounded_links = links[:32]\n"
        "    packet = {'automaticMerge': True}\n"
        "    return packet, bounded_links\n",
        encoding="utf-8",
    )
    (repo / "Aura_Memory").mkdir()
    (repo / "Aura_Memory" / "live_topology_ast.json").write_text(
        json.dumps({"nodes": [], "edges": []}),
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")
    (repo / "module.py").write_text(
        "def compile_packet(metadata):\n"
        "    links = metadata.get('links', [])\n"
        "    bounded_links = links[:16]\n"
        "    packet = {'automaticMerge': True}\n"
        "    return packet, bounded_links\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "change")
    return repo


def test_static_source_scan_detects_alias_and_truncate_before_sort() -> None:
    source = (
        "def compile_packet(metadata):\n"
        "    links = metadata.get('links', [])\n"
        "    bounded_links = links[:16]\n"
        "    return {'automaticMerge': True}, bounded_links\n"
    )
    findings = scan_python_review_lessons(
        file="module.py",
        source=source,
        tree=ast.parse(source),
    )
    rules = {item["rule"] for item in findings}
    assert "detect_authority_aliases" in rules
    assert "detect_truncate_before_sort" in rules
    assert all(item["automatic_merge"] is False for item in findings)


def test_review_lesson_aware_waboose_runs_detectors_and_crucible(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = ReviewLessonAwareCodingWaboose(
        repo,
        learning_root=tmp_path / "coderabbit-learning",
        review_learning_root=tmp_path / "review-learning",
    )
    prepared = runtime.prepare(
        {
            "objective": "Review deterministic ordering and authority metadata",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["review_lesson_context"]["lesson_count"] == 13

    scanned = runtime.scan(prepared["review_id"])
    assert scanned["ok"] is True
    assert scanned["review_lesson_findings_added"] >= 2
    assert scanned["review_lesson_crucible"]["status"] == "PASSED"
    assert scanned["review_lesson_crucible"]["passed_count"] == 13
    assert any(
        item["origin"] == "waboose_review_lesson"
        for item in scanned["deterministic_findings"]
    )
    assert scanned["automatic_merge"] is False


def test_external_review_ingestion_preserves_review_only_authority(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    runtime = ReviewLessonAwareCodingWaboose(
        repo,
        learning_root=tmp_path / "coderabbit-learning",
        review_learning_root=tmp_path / "review-learning",
    )
    head = _git(repo, "rev-parse", "HEAD")
    result = runtime.ingest_external_review(
        {
            "head_sha": head,
            "pr_number": 164,
            "findings": [
                {
                    "author": "Codex",
                    "file": "module.py",
                    "line": 4,
                    "title": "Reject authority aliases",
                    "message": "automaticMerge bypasses protected metadata.",
                }
            ],
        },
        current_head=head,
    )
    assert result["stored_count"] == 1
    assert result["automatic_fix"] is False
    assert result["automatic_pull_request"] is False
    assert result["automatic_merge"] is False
