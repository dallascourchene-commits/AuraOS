from __future__ import annotations

from pathlib import Path
import subprocess

from aura_coding_waboose import CodingWaboose
from aura_review_arena import AuraReviewRequest


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _repo(tmp_path: Path, source: str) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "waboose@example.test")
    _git(repo, "config", "user.name", "Coding Waboose")
    (repo / "sample.py").write_text(source, encoding="utf-8")
    _git(repo, "add", "sample.py")
    _git(repo, "commit", "-m", "fixture")
    return repo


def test_review_request_rejects_truthy_non_boolean_controls() -> None:
    try:
        AuraReviewRequest.from_value(
            {
                "objective": "review",
                "mode": "files",
                "changed_files": ["sample.py"],
                "run_tests": "false",
            }
        )
    except ValueError as exc:
        assert "boolean" in str(exc)
    else:
        raise AssertionError("truthy string must not be accepted as a boolean")


def test_deterministic_run_blocks_unexecuted_agent_focus(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "def value():\n    return 1\n")
    packet = CodingWaboose(repo).run_once(
        {
            "objective": "Review external research authority",
            "mode": "files",
            "changed_files": ["sample.py"],
            "run_tests": False,
            "run_optional_tools": False,
            "focus_directives": [
                {
                    "name": "research_authority",
                    "question": "Can external research become patch authority?",
                    "required_evidence": ["semantic_review"],
                }
            ],
        }
    )
    assert packet["ok"] is False
    assert packet["error"] == "semantic_review_incomplete"
    assert packet["semantic_review_complete"] is False
    assert packet["unverified_focus_directives"][0]["name"] == "research_authority"
    assert packet["automatic_merge"] is False


def test_registered_semantic_pack_can_complete_agent_focus(tmp_path: Path) -> None:
    repo = _repo(
        tmp_path,
        "def parse(value):\n"
        "    return bool(value.get('include_source', True))\n",
    )
    packet = CodingWaboose(repo).run_once(
        {
            "objective": "Review strict boolean option parsing",
            "mode": "files",
            "changed_files": ["sample.py"],
            "run_tests": False,
            "run_optional_tools": False,
            "focus_directives": [
                {
                    "name": "strict_boolean_options",
                    "question": "Are boolean options parsed with strict types?",
                    "required_evidence": ["semantic_rule"],
                }
            ],
        }
    )
    assert packet["ok"] is True
    assert packet["semantic_review_complete"] is True
    assert any(
        item["rule"] == "truthy-boolean-option-coercion"
        for item in packet["findings"]
    )
    assert packet["forge_repair_requests"]


def test_semantic_rule_packs_are_reported_in_final_packet(tmp_path: Path) -> None:
    repo = _repo(tmp_path, "def value():\n    return 1\n")
    packet = CodingWaboose(repo).run_once(
        {
            "objective": "Run deterministic semantic packs",
            "mode": "files",
            "changed_files": ["sample.py"],
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert packet["ok"] is True
    assert set(packet["semantic_rule_packs_executed"]) == {
        "bounded_graph_integrity",
        "source_integrity",
        "strict_input_types",
        "symbol_identity",
        "test_evidence_preservation",
    }
