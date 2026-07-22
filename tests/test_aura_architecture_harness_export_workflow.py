from pathlib import Path


WORKFLOW = Path(".github/workflows/aura-architecture-harness-export.yml")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_export_uses_request_harness_against_exact_main() -> None:
    workflow = _workflow_text()

    assert "refs/remotes/origin/main" in workflow
    assert "refs/remotes/origin/harness-request" in workflow
    assert 'test "$REQUEST_SHA" = "$GITHUB_SHA"' in workflow
    assert 'git show "$REQUEST_SHA:scripts/aura_architecture_harness.py"' in workflow
    assert 'python "${RUNNER_TEMP}/aura_architecture_harness.py"' in workflow
    assert '"source_main_sha": os.environ["SOURCE_SHA"]' in workflow
    assert '"request_harness_sha": os.environ["REQUEST_HARNESS_SHA"]' in workflow


def test_forensic_snapshot_upload_precedes_ai_handoff() -> None:
    workflow = _workflow_text()

    snapshot = workflow.index("- name: Upload exact repository snapshot")
    handoff = workflow.index("- name: Build AI-first bounded review handoff")
    assert snapshot < handoff
