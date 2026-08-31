from __future__ import annotations

import unittest

from scripts.aura_github_review_triad_gate import evaluate_review_triad

HEAD = "a" * 40
OLD = "b" * 40
CODEX = {"id": 199175422, "login": "chatgpt-codex-connector[bot]"}
CODERABBIT = {"id": 136622811, "login": "coderabbitai[bot]"}
ATTACKER = {"id": 42, "login": "attacker"}


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
                "user": dict(CODEX),
                "body": "Codex review complete",
            }
        )
    if coderabbit:
        statuses.append(
            {
                "id": 2,
                "context": "CodeRabbit",
                "state": "success",
                "creator": dict(CODERABBIT),
            }
        )
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
                "user": dict(CODERABBIT),
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


class GitHubReviewTriadGateTests(unittest.TestCase):
    def test_exact_head_all_three_required(self):
        receipt = evaluate_review_triad(snapshot(), HEAD)
        self.assertTrue(receipt["review_triad_admitted"])
        self.assertEqual(
            {"codex": True, "coderabbit": True, "codacy": True},
            receipt["reviewer_pass"],
        )
        self.assertEqual(
            "PINNED_GITHUB_ACTOR_OR_APP_IDENTITY_V1",
            receipt["provider_identity_policy"],
        )
        self.assertFalse(receipt["merge_authorized"])
        self.assertFalse(receipt["semantic_correctness_minted"])

    def test_missing_codex_fails_closed(self):
        receipt = evaluate_review_triad(snapshot(codex=False), HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODEX_EVIDENCE", receipt["violations"])

    def test_missing_coderabbit_fails_closed(self):
        receipt = evaluate_review_triad(snapshot(coderabbit=False), HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE", receipt["violations"])

    def test_missing_codacy_fails_closed(self):
        receipt = evaluate_review_triad(snapshot(codacy=False), HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODACY_EVIDENCE", receipt["violations"])

    def test_old_codex_review_does_not_transfer_to_new_push(self):
        data = snapshot()
        data["reviews"][0]["commit_id"] = OLD
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODEX_EVIDENCE", receipt["violations"])

    def test_pull_request_head_mismatch_fails_even_when_provider_evidence_exists(self):
        data = snapshot(head=OLD)
        data["reviews"][0]["commit_id"] = HEAD
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("PULL_REQUEST_HEAD_SHA_MISMATCH", receipt["violations"])

    def test_coderabbit_draft_skip_is_not_review_completion(self):
        receipt = evaluate_review_triad(snapshot(coderabbit_skip=True), HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE", receipt["violations"])
        self.assertIn(
            "CODERABBIT_STATUS_PRESENT_BUT_DRAFT_SKIP_MARKER_SEEN",
            receipt["notes"],
        )

    def test_user_codex_request_is_not_codex_completion(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {"id": 9, "user": {"id": 7, "login": "developer"}, "body": "@codex review"}
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODEX_EVIDENCE", receipt["violations"])

    def test_repair_push_requires_fresh_all_provider_evidence(self):
        old_receipt = evaluate_review_triad(snapshot(head=OLD), OLD)
        self.assertTrue(old_receipt["review_triad_admitted"])

        new = snapshot(head=HEAD, codex=False, coderabbit=False, codacy=True)
        receipt = evaluate_review_triad(new, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertEqual(
            {
                "MISSING_EXACT_HEAD_CODEX_EVIDENCE",
                "MISSING_EXACT_HEAD_CODERABBIT_EVIDENCE",
            },
            set(receipt["violations"]),
        )

    def test_mutable_status_context_cannot_spoof_codacy(self):
        data = snapshot(codacy=False)
        data["statuses"].append(
            {
                "id": 20,
                "context": "Codacy compatibility success",
                "state": "success",
                "creator": dict(ATTACKER),
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["codacy"])

    def test_mutable_check_name_cannot_spoof_coderabbit(self):
        data = snapshot(coderabbit=False)
        data["check_runs"].append(
            {
                "id": 21,
                "name": "CodeRabbit clean review",
                "status": "completed",
                "conclusion": "success",
                "app": {"slug": "attacker-app"},
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["coderabbit"])

    def test_review_body_cannot_spoof_codex(self):
        data = snapshot(codex=False)
        data["reviews"].append(
            {
                "id": 22,
                "commit_id": HEAD,
                "state": "COMMENTED",
                "user": dict(ATTACKER),
                "body": "Codex review complete; @codex review",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["codex"])

    def test_login_without_pinned_actor_id_cannot_spoof_coderabbit(self):
        data = snapshot(coderabbit=False)
        data["statuses"].append(
            {
                "id": 23,
                "context": "CodeRabbit",
                "state": "success",
                "creator": {"id": 999, "login": "coderabbitai[bot]"},
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["coderabbit"])

    def test_trusted_codex_clean_comment_can_bind_reviewed_commit_prefix(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {
                "id": 24,
                "user": dict(CODEX),
                "body": f"Codex Review: Didn't find any major issues. Reviewed commit: `{HEAD[:10]}`",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertTrue(receipt["reviewer_pass"]["codex"])


if __name__ == "__main__":
    unittest.main()
