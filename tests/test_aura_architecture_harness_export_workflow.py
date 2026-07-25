from pathlib import Path


WORKFLOW = Path(".github/workflows/aura-architecture-harness-export.yml")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_export_uses_request_harness_against_exact_main() -> None:
    workflow = _workflow_text()

    assert "refs/remotes/origin/main" in workflow
    assert "refs/remotes/origin/harness-request" in workflow
    assert 'test "$REQUEST_SHA" = "$GITHUB_SHA"' in workflow
    assert 'git archive "$REQUEST_SHA" | tar -x -C "$REQUEST_TOOLS_DIR"' in workflow
    assert 'python "$REQUEST_TOOLS_DIR/scripts/aura_architecture_harness.py"' in workflow
    assert 'python scripts/aura_architecture_harness.py' not in workflow
    assert '"source_main_sha": os.environ["SOURCE_SHA"]' in workflow
    assert '"request_harness_sha": os.environ["REQUEST_HARNESS_SHA"]' in workflow


def test_export_keeps_generated_artifacts_outside_checkout() -> None:
    workflow = _workflow_text()

    assert 'REQUEST_EXPORT_DIR="${RUNNER_TEMP}/AuraOS-request-export"' in workflow
    assert 'FULL_EXPORT_DIR="${RUNNER_TEMP}/AuraOS-full-export"' in workflow
    assert 'python "$REQUEST_TOOLS_DIR/scripts/aura_exact_head_transport.py"' in workflow
    assert '--output-dir "$REQUEST_EXPORT_DIR"' in workflow
    assert '--output-dir "$FULL_EXPORT_DIR"' not in workflow
    assert '${{ runner.temp }}/AuraOS-full-export/AuraOS-full-repository.zip' in workflow
    assert 'test -z "$(git status --porcelain=v1 --untracked-files=all)"' in workflow
    assert "--output=AuraOS-full-repository.zip" not in workflow


def test_export_independently_binds_request_output_to_trusted_git_archive() -> None:
    workflow = _workflow_text()

    assert "git archive \\" in workflow
    assert "--prefix=AuraOS/" in workflow
    assert '"$SOURCE_SHA"' in workflow
    assert "cmp \\" in workflow
    assert '"$REQUEST_EXPORT_DIR/AuraOS-full-repository.zip"' in workflow
    assert '"$FULL_EXPORT_DIR/AuraOS-full-repository.zip"' in workflow
    assert "sha256sum AuraOS-full-repository.zip" in workflow


def test_export_includes_exact_request_harness_and_digest() -> None:
    workflow = _workflow_text()

    assert "AuraOS-request-harness.py" in workflow
    assert "AuraOS-request-harness.py.sha256" in workflow
    assert '"request_harness": "AuraOS-request-harness.py"' in workflow


def test_forensic_snapshot_upload_precedes_ai_handoff() -> None:
    workflow = _workflow_text()

    snapshot = workflow.index("- name: Upload exact repository snapshot")
    handoff = workflow.index("- name: Build AI-first bounded review handoff")
    assert snapshot < handoff


def test_export_workflow_uses_exact_head_transport_and_external_diagnostics() -> None:
    workflow = Path(".github/workflows/aura-architecture-harness-export.yml").read_text(encoding="utf-8")
    assert 'python "$REQUEST_TOOLS_DIR/scripts/aura_exact_head_transport.py"' in workflow
    assert "${RUNNER_TEMP}/AuraOS-export-diagnostics" in workflow
    assert 'python "$REQUEST_TOOLS_DIR/scripts/aura_architecture_harness.py"' in workflow
    assert "python scripts/aura_architecture_harness.py" not in workflow
    assert "Upload failure diagnostics outside checkout" in workflow
