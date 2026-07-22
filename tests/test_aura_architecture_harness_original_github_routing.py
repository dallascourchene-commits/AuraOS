from __future__ import annotations

import json
from pathlib import Path

from scripts import aura_architecture_harness as harness


def test_original_harness_exposes_workflow_discovery_policy() -> None:
    policy = harness._github_publication_route_policy()
    discovery = policy["workflow_discovery"]

    assert policy["version"] == harness.GITHUB_PUBLICATION_ROUTE_VERSION
    assert discovery["pull_request_definition_source"] == "base_branch"
    assert discovery["branch_new_pull_request_workflow_jobs_reliable"] is False
    assert discovery["preferred_fallback"] == "atomic_git_object_route"
    assert policy["authority"]["automatic_ref_update"] is False
    assert policy["authority"]["force_ref_update"] is False
    assert policy["authority"]["automatic_merge"] is False


def test_original_doctor_includes_atomic_route(monkeypatch) -> None:
    monkeypatch.setattr(
        harness,
        "_ORIGINAL_DOCTOR",
        lambda root, python: {"ok": True, "repo_root": str(root)},
    )
    result = harness.doctor(Path("/tmp/example"), None)

    assert result["ok"] is True
    assert result["github_publication_route"]["preferred_fallback"] == (
        "atomic_git_object_route"
    )


def test_original_handoff_manifest_includes_atomic_route(tmp_path, monkeypatch) -> None:
    output = tmp_path / "handoff"
    output.mkdir()
    manifest_path = output / "ai_handoff_manifest.json"
    manifest_path.write_text('{"version":"test"}\n', encoding="utf-8")

    monkeypatch.setattr(
        harness,
        "_ORIGINAL_CREATE_AI_HANDOFF",
        lambda *args, **kwargs: {
            "ok": True,
            "manifest_path": str(manifest_path),
        },
    )
    result = harness.create_ai_handoff(Path("/tmp/repo"), output_dir=output)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert result["github_publication_route"]["status"] == (
        "PROPOSAL_ONLY_EXTERNAL_CONNECTOR_REQUIRED"
    )
    assert manifest["github_publication_route"]["connector_sequence"][-1][
        "action"
    ] == "verify"


def test_original_run_summary_includes_atomic_route(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        harness,
        "_ORIGINAL_RUN_ARCHITECTURE",
        lambda root, **kwargs: {"ok": True, "version": "test", "run_digest": "stale"},
    )
    result = harness.run_architecture(Path("/tmp/repo"), output_dir=tmp_path)
    summary = json.loads((tmp_path / "harness_summary.json").read_text())

    assert result["github_publication_route"]["case_study"][
        "confirmed_force_required"
    ] is False
    assert summary["run_digest"] == result["run_digest"]
    digest_free = dict(result)
    digest = digest_free.pop("run_digest")
    assert digest != "stale"
    assert digest == harness._core._digest(digest_free)
    assert summary["github_publication_route"]["authority"][
        "base_branch_update_authorized"
    ] is False
