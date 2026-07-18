from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = ROOT / ".github" / "workflows" / "coderabbit-waboose-learning.yml"
PERSIST = ROOT / ".github" / "workflows" / "coderabbit-waboose-learning-persist.yml"


def test_dispatcher_routes_coderabbit_review_to_default_branch_workflow() -> None:
    text = DISPATCHER.read_text(encoding="utf-8")
    assert "pull_request_review:" in text
    assert "contains(github.actor, 'coderabbit')" in text
    assert "actions: write" in text
    assert "contents: read" in text
    assert "coderabbit-waboose-learning-persist.yml/dispatches" in text
    assert '"ref": os.environ["DEFAULT_BRANCH"]' in text
    assert '"head_sha": os.environ["HEAD_SHA"]' in text
    assert "actions/checkout" not in text


def test_persistence_workflow_uses_trusted_runtime_and_exact_reviewed_head() -> None:
    text = PERSIST.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "cancel-in-progress: false" in text
    assert "contents: read" in text
    assert "contents: write" not in text
    assert "ref: ${{ github.event.repository.default_branch }}" in text
    assert '"pull/${PR_NUMBER}/head:refs/remotes/origin/waboose-reviewed-head"' in text
    assert 'test "$ACTUAL_HEAD_SHA" = "$EXPECTED_HEAD_SHA"' in text
    assert "worktree add --detach /tmp/aura-reviewed" in text
    assert "PYTHONPATH=\"$PWD/aura-runtime\"" in text
    assert "--repo-root /tmp/aura-reviewed" in text
    assert "actions/cache/restore@v4" in text
    assert "actions/cache/save@v4" in text
    assert "pull_request_target" not in text


def test_learning_workflow_never_executes_reviewed_pr_python() -> None:
    text = PERSIST.read_text(encoding="utf-8")
    forbidden = (
        "python /tmp/aura-reviewed/",
        "pytest /tmp/aura-reviewed",
        "pip install -r /tmp/aura-reviewed",
        "source /tmp/aura-reviewed",
    )
    assert all(item not in text for item in forbidden)
    assert "python aura-runtime/aura_coderabbit_learning_cli.py" in text
