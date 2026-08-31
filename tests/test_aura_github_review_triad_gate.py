from __future__ import annotations

from scripts.aura_github_review_triad_gate import evaluate_review_triad

HEAD = "a" * 40
OLD = "b" * 40


def snapshot(*, codex=True, coderabbit=True, codacy=True, head=HEAD, coderabbit_skip=False):
    statuses = []
    checks = []
    reviews = []
    issue_comments = []
    if codex:
        reviews.append(
            {
                "id": 1,
                "commit_id": head,
                "state": "COMMENTED",
                "user": {"login": "openai-codex[bot]"},
                "body": "Codex review complete",
            }
        )
    if coderabbit:
        statuses.append({"id": 2, "context": "CodeRabbit", "state": "success"})
    if codacy:
        checks.append(
            {
                "id": 3,
                "name": "Codacy Static Code Analysis",
                "status": "completed",
                "conclusion": "success",
                "app": {"slug": "codacy"},
            }
        )
    if coderabbit_skip:
        issue_comments.append(
            {
                "id": 4,
                "user": {"login": "coderabbitai[bot]"},
                "body": "Draft PR not reviewed — skip review by coderabbit.ai",
            }
        )
    return {
        "pull_request": {"head": {"sha": head}},
        "statuses": statuses,
        "check_runs": checks,
        "reviews": reviews,
        "review_comments": [],
        "issue_comments": issue_comments,
    }


def test_exact_head_all_three_required():
    receipt = evaluate_review_triad(snapshot(), HEAD)
    assert receipt["review_triad_admitted"] is True
    assert receipt["reviewer_pass"] == {
        "codex": True,
        "coderabbit": True,
        "codacy": True,
    }
    assert receipt["merge_authorized"] is False
    assert receipt["semantic_correctness_minted"] is False


def test_missing_codex_fails_closed():
    receipt = evaluate_review_triad(snapshot(codex=False), HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODEX_EVIDENCE" in receipt["violations"]


def test_missing_coderabbit_fails_closed():
    receipt = evaluate_review_triad(snapshot(coderabbit=False), HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE" in receipt["violations"]


def test_missing_codacy_fails_closed():
    receipt = evaluate_review_triad(snapshot(codacy=False), HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODACY_EVIDENCE" in receipt["violations"]


def test_old_codex_review_does_not_transfer_to_new_push():
    data = snapshot()
    data["reviews"][0]["commit_id"] = OLD
    receipt = evaluate_review_triad(data, HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODEX_EVIDENCE" in receipt["violations"]


def test_pull_request_head_mismatch_fails_even_when_provider_evidence_exists():
    data = snapshot(head=OLD)
    # Commit status/check inputs can exist for expected HEAD while PR already moved.
    data["reviews"][0]["commit_id"] = HEAD
    receipt = evaluate_review_triad(data, HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "PULL_REQUEST_HEAD_SHA_MISMATCH" in receipt["violations"]


def test_coderabbit_draft_skip_is_not_review_completion():
    receipt = evaluate_review_triad(snapshot(coderabbit_skip=True), HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE" in receipt["violations"]
    assert "CODERABBIT_STATUS_PRESENT_BUT_DRAFT_SKIP_MARKER_SEEN" in receipt["notes"]


def test_user_codex_request_is_not_codex_completion():
    data = snapshot(codex=False)
    data["issue_comments"].append(
        {"id": 9, "user": {"login": "developer"}, "body": "@codex review"}
    )
    receipt = evaluate_review_triad(data, HEAD)
    assert receipt["review_triad_admitted"] is False
    assert "MISSING_EXACT_HEAD_CODEX_EVIDENCE" in receipt["violations"]


def test_repair_push_requires_fresh_all_provider_evidence():
    old_receipt = evaluate_review_triad(snapshot(head=OLD), OLD)
    assert old_receipt["review_triad_admitted"] is True

    new = snapshot(head=HEAD, codex=False, coderabbit=False, codacy=True)
    receipt = evaluate_review_triad(new, HEAD)
    assert receipt["review_triad_admitted"] is False
    assert set(receipt["violations"]) == {
        "MISSING_EXACT_HEAD_CODEX_EVIDENCE",
        "MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE",
    }
