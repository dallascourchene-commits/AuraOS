from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from scripts.aura_spatial_s5_s6_construction_architect_harness import (
    _marked_analysis_process_ids,
    _terminate_process_group,
    run,
)


def test_s5_s6_structural_harness_is_bounded_and_non_mutating(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    before = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True).stdout
    receipt = run(
        root,
        base_ref="main",
        head_ref="HEAD",
        observed_head=subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip(),
        structural_only=True,
    )
    after = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True).stdout
    assert receipt["status"] == "PASSED"
    assert receipt["ok"] is True
    assert all(receipt["checks"].values())
    assert receipt["lifecycle"]["forbidden_construction_fields"] == []
    assert receipt["lifecycle"]["active_sessions_after_dissolution"] == 0
    assert len(json.dumps(receipt, sort_keys=True).encode("utf-8")) < 1_048_576
    assert after == before


def test_full_harness_timeout_fails_closed_and_still_writes_receipt(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    output = tmp_path / "receipt.json"
    result = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/aura_spatial_s5_s6_construction_architect_harness.py"),
            "--repo-root",
            str(root),
            "--base-ref",
            "main",
            "--head-ref",
            "HEAD",
            "--observed-head",
            subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
            ).stdout.strip(),
            "--receipt",
            str(output),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
        env={
            "PATH": str(Path(sys.executable).parent) + ":/usr/bin:/bin",
            "AURA_S5_S6_ARCHITECT_TOTAL_TIMEOUT_SECONDS": "1",
        },
    )
    assert result.returncode == 1
    packet = json.loads(output.read_text(encoding="utf-8"))
    assert packet["status"] == "FAILED"
    assert packet["architecture"]["mode"] == "failed_closed"
    assert packet["architecture"]["error_type"] == "TimeoutError"
    assert packet["production_mutation"] is False
    assert packet["automatic_merge"] is False


def test_marked_analysis_process_ids_are_scoped_to_unique_token(tmp_path: Path) -> None:
    (tmp_path / "101").mkdir()
    (tmp_path / "101" / "environ").write_bytes(b"PATH=/bin\0AURA_S5_S6_ARCHITECT_RUN_TOKEN=target\0")
    (tmp_path / "102").mkdir()
    (tmp_path / "102" / "environ").write_bytes(b"AURA_S5_S6_ARCHITECT_RUN_TOKEN=other\0")
    assert _marked_analysis_process_ids("target", tmp_path) == (101,)


def test_architecture_wrapper_reaps_group_and_token_marked_helpers(monkeypatch) -> None:
    group_calls: list[tuple[int, int]] = []
    process_calls: list[tuple[int, int]] = []

    class _Process:
        pid = 4242

    monkeypatch.setattr(os, "killpg", lambda pid, sig: group_calls.append((pid, sig)))
    monkeypatch.setattr(os, "kill", lambda pid, sig: process_calls.append((pid, sig)))
    monkeypatch.setattr(
        "scripts.aura_spatial_s5_s6_construction_architect_harness._marked_analysis_process_ids",
        lambda token: (4343,) if token == "run-token" else (),
    )
    _terminate_process_group(_Process(), run_token="run-token")  # type: ignore[arg-type]
    assert group_calls == [(4242, signal.SIGKILL)]
    assert process_calls == [(4343, signal.SIGKILL)]
