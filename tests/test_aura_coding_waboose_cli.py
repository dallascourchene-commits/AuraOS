from __future__ import annotations

import json
from pathlib import Path

from aura_coding_waboose_cli import main
from test_aura_review_arena import build_review_repo


def _result(capsys) -> dict:
    output = capsys.readouterr().out
    return json.loads(output)


def test_cli_persists_review_across_separate_invocations(
    tmp_path: Path,
    capsys,
) -> None:
    repo = build_review_repo(tmp_path)
    state_file = tmp_path / "waboose-state.json"
    request_file = tmp_path / "request.json"
    request_file.write_text(
        json.dumps(
            {
                "objective": "Review caller compatibility",
                "base_ref": "HEAD~1",
                "head_ref": "HEAD",
                "run_tests": False,
                "run_optional_tools": False,
            }
        ),
        encoding="utf-8",
    )

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "prepare",
            "--request",
            str(request_file),
        ]
    ) == 0
    prepared = _result(capsys)
    review_id = prepared["review_id"]
    assert state_file.is_file()

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "scan",
            "--review-id",
            review_id,
        ]
    ) == 0
    scanned = _result(capsys)
    assert scanned["review_id"] == review_id
    assert any(
        item["rule"] == "callsite-arity-mismatch"
        for item in scanned["deterministic_findings"]
    )

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "status",
            "--review-id",
            review_id,
        ]
    ) == 0
    status = _result(capsys)
    assert status["review_id"] == review_id
    assert status["deterministic_findings"] >= 1

    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "finalize",
            "--review-id",
            review_id,
        ]
    ) == 0
    final = _result(capsys)
    assert final["review_id"] == review_id
    assert final["forge_repair_requests"]


def test_cli_state_revalidation_fails_after_reviewed_contract_changes(
    tmp_path: Path,
    capsys,
) -> None:
    repo = build_review_repo(tmp_path)
    state_file = tmp_path / "waboose-state.json"
    request = json.dumps(
        {
            "objective": "Review exact state",
            "base_ref": "HEAD~1",
            "head_ref": "HEAD",
            "run_tests": False,
            "run_optional_tools": False,
        }
    )
    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "prepare",
            "--request",
            request,
        ]
    ) == 0
    prepared = _result(capsys)
    review_id = prepared["review_id"]

    core = repo / "core.py"
    core.write_text(core.read_text(encoding="utf-8") + "\n# tracked drift\n", encoding="utf-8")
    assert main(
        [
            "--repo-root",
            str(repo),
            "--state-file",
            str(state_file),
            "status",
            "--review-id",
            review_id,
        ]
    ) == 1
    failed = _result(capsys)
    assert failed["ok"] is False
    assert "revalidated" in failed["error"]
