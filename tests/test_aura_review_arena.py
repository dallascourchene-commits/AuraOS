from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from aura_review_arena import (
    AuraReviewArena,
    AuraReviewRequest,
    REVIEW_CONTRACT_VERSION,
    validate_review_contract,
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


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def build_review_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "review-repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "review@example.test")
    _git(repo, "config", "user.name", "Aura Review Test")
    _write(
        repo,
        "core.py",
        """def compute(value=1):
    return value + 1


def guarded(packet):
    try:
        return packet.get(\"ok\")
    except Exception:
        pass
""",
    )
    _write(
        repo,
        "caller.py",
        """from core import compute


def use_compute():
    return compute(1)
""",
    )
    _write(
        repo,
        "tests/test_core.py",
        """from core import compute


def test_compute():
    assert compute(1) == 2
""",
    )
    _write(repo, ".aura/ARCHITECTURE.md", "# Test architecture\n")
    _write(
        repo,
        "Aura_Memory/live_topology_ast.json",
        json.dumps(
            {
                "nodes": [
                    {"id": "core.py::compute", "file": "core.py", "label": "compute", "kind": "function", "line": 1},
                    {"id": "core.py::guarded", "file": "core.py", "label": "guarded", "kind": "function", "line": 5},
                    {"id": "caller.py::use_compute", "file": "caller.py", "label": "use_compute", "kind": "function", "line": 4},
                    {"id": "tests/test_core.py::test_compute", "file": "tests/test_core.py", "label": "test_compute", "kind": "function", "line": 4},
                ],
                "edges": [
                    {"source": "caller.py::use_compute", "target": "core.py::compute", "kind": "call"},
                    {"source": "tests/test_core.py::test_compute", "target": "core.py::compute", "kind": "call"},
                ],
                "meta": {"generated_by": "test"},
            },
            indent=2,
        ),
    )
    _commit(repo, "base")
    _write(
        repo,
        "core.py",
        """def compute(value, increment):
    return value + increment


def guarded(packet):
    try:
        return packet.get(\"ok\")
    except Exception:
        pass
""",
    )
    _commit(repo, "change signature")
    return repo


def test_prepare_is_graph_guided_and_run_ids_are_unique(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)
    request = {
        "objective": "Review fail-closed authority and dependency impact",
        "base_ref": "HEAD~1",
        "head_ref": "HEAD",
        "profile": "precision",
        "run_tests": False,
        "run_optional_tools": False,
        "invariants": ["no automatic merge", "malformed packets fail closed"],
    }

    first = arena.prepare(request)
    second = arena.prepare(request)

    assert first["ok"] is True
    assert second["ok"] is True
    assert first["review_id"] != second["review_id"]
    assert first["contract"]["contract_id"] == second["contract"]["contract_id"]
    assert first["contract"]["changed_files"] == ["core.py"]
    impact_files = {item["file"] for item in first["contract"]["impact_slice"]}
    assert "caller.py" in impact_files
    assert "tests/test_core.py" in impact_files
    names = {item["name"] for item in first["contract"]["focus_directives"]}
    assert "dependency_impact" in names
    assert "fail_closed_dependency_packets" in names
    assert "authority_non_mutation" in names
    assert validate_review_contract(first["contract"]) == []


def test_scan_finds_ast_and_cascading_signature_defects(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review the changed function and every dependent call site",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "profile": "precision",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )

    scanned = arena.scan(prepared["review_id"])
    rules = {item["rule"] for item in scanned["deterministic_findings"]}

    assert scanned["ok"] is True
    assert "broad-exception-swallow" in rules
    assert "callsite-arity-mismatch" in rules
    mismatch = next(item for item in scanned["deterministic_findings"] if item["rule"] == "callsite-arity-mismatch")
    assert mismatch["file"] in {"caller.py", "tests/test_core.py"}
    assert mismatch["related_files"] == ["core.py"]

    final = arena.finalize(prepared["review_id"])
    assert final["status"] == "READY_FOR_HUMAN_REVIEW"
    assert final["production_mutation"] is False
    assert final["automatic_fix"] is False
    assert final["automatic_merge"] is False
    assert any(item["rule"] == "callsite-arity-mismatch" for item in final["findings"])
    assert final["forge_repair_requests"]
    assert all(item["constraints"][-1] == "human_review_required" for item in final["forge_repair_requests"])


def test_syntax_failure_is_confirmed_without_an_agent(tmp_path: Path) -> None:
    repo = tmp_path / "syntax"
    repo.mkdir()
    _write(repo, "broken.py", "def broken(:\n    return 1\n")
    arena = AuraReviewArena(repo)

    prepared = arena.prepare(
        {
            "objective": "Review syntax",
            "mode": "files",
            "changed_files": ["broken.py"],
            "agent_name": "none",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    scanned = arena.scan(prepared["review_id"])
    syntax = next(item for item in scanned["deterministic_findings"] if item["rule"] == "python-syntax-error")

    assert syntax["status"] == "confirmed"
    assert syntax["severity"] == "blocker"
    final = arena.finalize(prepared["review_id"])
    assert final["summary"]["blocking"] is True


def test_agent_finding_requires_scope_and_exact_evidence(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review semantic behavior",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "profile": "precision",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    arena.scan(prepared["review_id"])

    result = arena.submit_findings(
        prepared["review_id"],
        [
            {
                "category": "logic",
                "severity": "high",
                "title": "The new required argument breaks existing callers",
                "message": "The changed signature requires increment but caller.py still supplies one positional argument.",
                "impact": "use_compute raises TypeError at runtime.",
                "file": "caller.py",
                "line_start": 5,
                "line_end": 5,
                "evidence_excerpt": "return compute(1)",
                "suggested_fix": "Update the caller or provide a backwards-compatible default.",
                "confirmed": True,
            },
            {
                "category": "logic",
                "severity": "high",
                "title": "Out of scope",
                "message": "This should be rejected.",
                "impact": "None",
                "file": "unrelated.py",
                "line_start": 1,
                "evidence_excerpt": "x",
                "suggested_fix": "None",
            },
        ],
        agent_name="codex",
    )

    assert result["accepted_count"] == 1
    assert result["rejected"][0]["reason"] == "finding_file_outside_review_scope"
    state_packet = arena.finalize(prepared["review_id"])
    finding = next(item for item in state_packet["findings"] if item["origin"] == "agent")
    assert finding["status"] == "corroborated"
    assert finding["agent_claimed_confirmation_ignored"] is True
    assert finding["confidence"] <= 0.95


def test_agent_finding_without_matching_excerpt_is_advisory_and_suppressed(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Precision review",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "profile": "precision",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    arena.scan(prepared["review_id"])
    result = arena.submit_findings(
        prepared["review_id"],
        [
            {
                "category": "maintainability",
                "severity": "low",
                "title": "Uncorroborated preference",
                "message": "The code might be clearer another way.",
                "impact": "No demonstrated runtime impact.",
                "file": "core.py",
                "line_start": 1,
                "evidence_excerpt": "text not present in source",
                "suggested_fix": "Rename the function.",
            }
        ],
    )
    assert result["accepted_count"] == 1
    final = arena.finalize(prepared["review_id"])
    assert not any(item["title"] == "Uncorroborated preference" for item in final["findings"])
    assert final["suppressed_advisories"] >= 1


def test_request_and_contract_tampering_fail_closed(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)

    unsafe_path = arena.prepare({"objective": "x", "mode": "files", "changed_files": ["../escape.py"]})
    unsafe_ref = arena.prepare({"objective": "x", "base_ref": "--output=/tmp/x", "head_ref": "HEAD"})
    prepared = arena.prepare(
        {
            "objective": "Review contract",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    contract = prepared["contract"]
    contract["authority"]["automatic_merge"] = True
    contract["lifecycle"] = ["FRAME", "DECIDE"]

    errors = validate_review_contract(contract)
    assert unsafe_path["ok"] is False
    assert unsafe_ref["ok"] is False
    assert "invalid_authority:automatic_merge" in errors
    assert "invalid_lifecycle" in errors


def test_request_dataclass_round_trip_preserves_agent_focus() -> None:
    request = AuraReviewRequest.from_value(
        {
            "objective": "Review credential redaction",
            "mode": "files",
            "changed_files": [".aura/ARCHITECTURE.md"],
            "focus_directives": [
                {
                    "name": "token_boundary",
                    "question": "Are secret tokens removed while usage token counters remain visible?",
                    "risk": "security",
                    "direction": "both",
                    "target_patterns": ["token", "sanitize"],
                }
            ],
            "metadata": {"github_token": "secret", "input_tokens": 321},
        }
    )
    identity = request.identity_dict()
    assert identity["changed_files"] == [".aura/ARCHITECTURE.md"]
    assert identity["focus_directives"][0]["name"] == "token_boundary"
    assert "github_token" not in identity["metadata"]
    assert identity["metadata"]["input_tokens"] == 321
    assert REVIEW_CONTRACT_VERSION == "AURA_REVIEW_CONTRACT_V1"


def test_invalid_findings_collection_returns_error(tmp_path: Path) -> None:
    repo = build_review_repo(tmp_path)
    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    result = arena.submit_findings(prepared["review_id"], "not-an-array")  # type: ignore[arg-type]
    assert result["ok"] is False
    assert result["stage"] == "CORROBORATE"
    assert result["automatic_fix"] is False



def test_range_review_requires_requested_head_to_be_checked_out_and_clean(
    tmp_path: Path,
) -> None:
    repo = build_review_repo(tmp_path)
    reviewed_head = _git(repo, "rev-parse", "HEAD")
    base = _git(repo, "rev-parse", "HEAD~1")
    _git(repo, "checkout", "--detach", base)

    wrong_head = AuraReviewArena(repo).prepare(
        {
            "objective": "Review an exact branch head",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert wrong_head["ok"] is False
    assert wrong_head["error"] == "range_head_ref_not_checked_out"

    _git(repo, "checkout", "main")
    _write(repo, "core.py", (repo / "core.py").read_text(encoding="utf-8") + "\n# dirty\n")
    dirty = AuraReviewArena(repo).prepare(
        {
            "objective": "Review an exact clean head",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert dirty["ok"] is False
    assert dirty["error"] == "range_review_requires_clean_tracked_worktree"

    _git(repo, "checkout", "--", "core.py")
    prepared = AuraReviewArena(repo).prepare(
        {
            "objective": "Review materialized head source",
            "base_ref": base,
            "head_ref": reviewed_head,
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["contract"]["repository_head"] == reviewed_head
    compute = next(
        item
        for item in prepared["contract"]["changed_symbols"]
        if item["symbol"] == "compute"
    )
    assert "increment" in compute["signature"]


def test_deletion_only_range_tracks_removed_symbols_and_surviving_callers(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "deletion-review"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "review@example.test")
    _git(repo, "config", "user.name", "Aura Review Test")
    _write(repo, "core.py", "def compute(value):\n    return value + 1\n")
    _write(
        repo,
        "caller.py",
        "from core import compute\n\ndef use():\n    return compute(1)\n",
    )
    _write(
        repo,
        "Aura_Memory/live_topology_ast.json",
        json.dumps(
            {
                "nodes": [
                    {
                        "id": "caller.py::use",
                        "file": "caller.py",
                        "label": "use",
                        "kind": "function",
                        "line": 3,
                    }
                ],
                "edges": [],
            }
        ),
    )
    _commit(repo, "base")
    (repo / "core.py").unlink()
    _commit(repo, "delete core")

    arena = AuraReviewArena(repo)
    prepared = arena.prepare(
        {
            "objective": "Review deleted API callers",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert prepared["ok"] is True
    assert prepared["contract"]["changed_files"] == ["core.py"]
    removed = next(
        item
        for item in prepared["contract"]["changed_symbols"]
        if item["symbol"] == "compute"
    )
    assert removed["change_kind"] == "deleted"
    assert any(
        item["file"] == "caller.py"
        and item["edge_kind"] == "deleted_symbol_call"
        for item in prepared["contract"]["impact_slice"]
    )

    scanned = arena.scan(prepared["review_id"])
    finding = next(
        item
        for item in scanned["deterministic_findings"]
        if item["rule"] == "removed-symbol-callsite"
    )
    assert finding["file"] == "caller.py"
    assert finding["status"] == "corroborated"
    final = arena.finalize(prepared["review_id"])
    assert any(
        item["target_file"] == "caller.py"
        for item in final["forge_repair_requests"]
    )
