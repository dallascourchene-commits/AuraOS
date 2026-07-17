"""Tests for the machine-enforced SCO Construction completion audit."""
from __future__ import annotations

from pathlib import Path

import aura_construction_refactor_completion as completion


def test_completion_audit_fails_closed_on_missing_symbol(tmp_path: Path, monkeypatch):
    (tmp_path / "owner.py").write_text("class Present:\n    pass\n", encoding="utf-8")
    (tmp_path / "surface.txt").write_text("READY", encoding="utf-8")
    monkeypatch.setattr(
        completion,
        "_REQUIRED_SYMBOLS",
        {"E9": {"owner.py": ("Present", "Missing")}},
    )
    monkeypatch.setattr(
        completion,
        "_REQUIRED_MARKERS",
        {"surface.txt": ("READY",)},
    )

    result = completion.validate_construction_refactor_completion(tmp_path)

    assert result["ok"] is False
    assert result["runtime_complete"] is False
    assert result["e14_release_status"] == "IMPLEMENTATION_INCOMPLETE"
    assert "missing_symbol:owner.py:Missing" in result["unresolved"]


def test_completion_audit_fails_closed_on_missing_wiring_marker(tmp_path: Path, monkeypatch):
    (tmp_path / "owner.py").write_text("def ready():\n    return True\n", encoding="utf-8")
    (tmp_path / "surface.txt").write_text("NOT_READY", encoding="utf-8")
    monkeypatch.setattr(
        completion,
        "_REQUIRED_SYMBOLS",
        {"E13": {"owner.py": ("ready",)}},
    )
    monkeypatch.setattr(
        completion,
        "_REQUIRED_MARKERS",
        {"surface.txt": ("READY_FOR_PINNED_MERGE",)},
    )

    result = completion.validate_construction_refactor_completion(tmp_path)

    assert result["ok"] is False
    assert any(item.startswith("missing_marker:surface.txt") for item in result["unresolved"])
    assert result["handoff_validation_enforced"] is True


def test_completion_audit_distinguishes_policy_deferral_from_incomplete_work(tmp_path: Path, monkeypatch):
    (tmp_path / "owner.py").write_text("def ready():\n    return True\n", encoding="utf-8")
    (tmp_path / "surface.txt").write_text("READY", encoding="utf-8")
    monkeypatch.setattr(
        completion,
        "_REQUIRED_SYMBOLS",
        {"E9": {"owner.py": ("ready",)}},
    )
    monkeypatch.setattr(
        completion,
        "_REQUIRED_MARKERS",
        {"surface.txt": ("READY",)},
    )

    result = completion.validate_construction_refactor_completion(tmp_path)

    assert result["ok"] is True
    assert result["runtime_complete"] is True
    assert result["e14_release_status"] == "READY_FOR_PINNED_MERGE"
    assert result["policy_deferrals"]
    assert result["policy_deferrals_are_incomplete_work"] is False
    assert result["physical_work_authorized"] is False
    assert result["payment_released"] is False
    assert result["automatic_merge"] is False


def test_repository_completion_audit_is_ready_after_final_wiring():
    repo_root = Path(__file__).resolve().parents[1]
    result = completion.validate_construction_refactor_completion(repo_root)

    assert result["ok"] is True, result["unresolved"]
    assert [item["node_id"] for item in result["runtime_nodes"]] == [
        f"E{index}" for index in range(14)
    ]
    assert all(item["status"] == "INTEGRATED" for item in result["runtime_nodes"])
    assert result["construction_human_agent_integrated"] is True
    assert result["observatory_read_only"] is True
    assert result["handoff_validation_enforced"] is True
    assert result["e14_release_status"] == "READY_FOR_PINNED_MERGE"
