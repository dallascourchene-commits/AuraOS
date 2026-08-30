from pathlib import Path


WORKFLOW = Path(".github/workflows/sync-analysis-codemap.yml")


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _commit_step(text: str) -> str:
    start_marker = "      - name: Commit synchronized navigation artifacts\n"
    end_marker = "      - name: Verify diagnostic secret-safety contract\n"
    assert start_marker in text
    assert end_marker in text
    return text.split(start_marker, 1)[1].split(end_marker, 1)[0]


def test_codemap_push_diagnostics_never_archive_shell_trace() -> None:
    text = _workflow_text()
    commit = _commit_step(text)

    assert "set -x" not in commit
    assert "tee " not in commit
    assert "codemap-push.log" not in text


def test_codemap_push_diagnostics_are_bounded_status_only() -> None:
    text = _workflow_text()

    assert "status_file=/tmp/codemap-push-status.txt" in text
    assert "/tmp/codemap-push-status.txt" in text
    for value in (
        "PUSH_NOT_ATTEMPTED",
        "NO_CHANGES",
        "PUSH_ATTEMPTED",
        "PUSH_SUCCEEDED",
        "PUSH_FAILED",
    ):
        assert value in text


def test_auth_header_is_ephemeral_and_not_uploaded() -> None:
    text = _workflow_text()
    commit = _commit_step(text)
    upload = text.split(
        "      - name: Upload synchronized maps and bounded push diagnostics\n", 1
    )[1]

    assert 'AUTH_HEADER="$(printf \'x-access-token:%s\' "$GH_TOKEN" | base64 -w0)"' in commit
    assert commit.count("unset AUTH_HEADER") >= 2
    assert "AUTH_HEADER" not in upload
    assert "GH_TOKEN" not in upload
