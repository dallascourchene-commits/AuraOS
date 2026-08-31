from __future__ import annotations

import unittest

from scripts.aura_github_review_triad_gate import IDENTITY_POLICY, evaluate_review_triad

HEAD = "a" * 40
OLD = "b" * 40
CODEX = {"id": 199175422, "login": "chatgpt-codex-connector[bot]"}
CODERABBIT = {"id": 136622811, "login": "coderabbitai[bot]"}
CODACY_APP = {"id": 56611, "slug": "codacy-production"}
ATTACKER = {"id": 42, "login": "attacker"}


def snapshot(*, codex=True, coderabbit=True, codacy=True, head=HEAD):
    statuses = []
    checks = []
    issue_comments = []
    if codex:
        issue_comments.append(
            {
                "id": 1,
                "user": dict(CODEX),
                "body": f"Codex Review: Didn't find any major issues. Reviewed commit: `{head[:10]}`",
                "created_at": "2026-08-31T03:00:00Z",
                "updated_at": "2026-08-31T03:00:00Z",
            }
        )
    if coderabbit:
        statuses.append(
            {
                "id": 2,
                "context": "CodeRabbit",
                "state": "success",
                "description": "Review completed",
                "creator": dict(CODERABBIT),
                "created_at": "2026-08-31T03:01:00Z",
                "updated_at": "2026-08-31T03:01:00Z",
            }
        )
    if codacy:
        checks.append(
            {
                "id": 3,
                "name": "Codacy Static Code Analysis",
                "status": "completed",
                "conclusion": "success",
                "app": dict(CODACY_APP),
                "output": {"title": "Your pull request is up to standards!", "summary": "Codacy found no issues"},
                "completed_at": "2026-08-31T03:02:00Z",
            }
        )
    pr = {"head": {"sha": head}}
    return {
        "pull_request": pr,
        "pull_request_after": {"head": {"sha": head}},
        "statuses": statuses,
        "check_runs": checks,
        "reviews": [],
        "review_comments": [],
        "issue_comments": issue_comments,
    }


class GitHubReviewTriadGateTests(unittest.TestCase):
    def test_all_three_clean_exact_head_pass(self):
        receipt = evaluate_review_triad(snapshot(), HEAD)
        self.assertTrue(receipt["review_triad_admitted"])
        self.assertEqual({"codex": True, "coderabbit": True, "codacy": True}, receipt["reviewer_pass"])
        self.assertEqual("PINNED_GITHUB_ACTOR_ID_OR_APP_ID_PLUS_SLUG_V2", IDENTITY_POLICY)
        self.assertFalse(receipt["merge_authorized"])
        self.assertFalse(receipt["semantic_correctness_minted"])

    def test_missing_provider_fails_closed(self):
        for provider in ("codex", "coderabbit", "codacy"):
            receipt = evaluate_review_triad(snapshot(**{provider: False}), HEAD)
            self.assertFalse(receipt["review_triad_admitted"])
            self.assertIn(f"MISSING_EXACT_HEAD_{provider.upper()}_CLEAN_COMPLETION", receipt["violations"])

    def test_head_race_fails_closed(self):
        data = snapshot()
        data["pull_request_after"] = {"head": {"sha": OLD}}
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("PULL_REQUEST_HEAD_SHA_CHANGED_OR_MISMATCHED", receipt["violations"])

    def test_user_codex_request_is_not_completion(self):
        data = snapshot(codex=False)
        data["issue_comments"].append({"id": 9, "user": {"id": 7, "login": "developer"}, "body": "@codex review"})
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codex"])

    def test_codex_queued_exact_head_is_not_completion(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {"id": 10, "user": dict(CODEX), "body": f"Codex review queued for {HEAD}; still running."}
        )
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codex"])

    def test_inline_current_head_finding_blocks_even_with_completion(self):
        data = snapshot()
        data["review_comments"].append(
            {
                "id": 11,
                "commit_id": HEAD,
                "user": dict(CODEX),
                "body": "P1: fail closed here",
                "created_at": "2026-08-31T03:04:00Z",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertTrue(receipt["reviewer_completed"]["codex"])
        self.assertFalse(receipt["reviewer_clear"]["codex"])
        self.assertIn("UNRESOLVED_EXACT_HEAD_CODEX_FINDINGS", receipt["violations"])

    def test_old_head_finding_does_not_transfer(self):
        data = snapshot()
        data["review_comments"].append(
            {"id": 12, "commit_id": OLD, "user": dict(CODEX), "body": "P1 old head"}
        )
        self.assertTrue(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codex"])

    def test_copied_bot_login_wrong_id_cannot_spoof(self):
        data = snapshot(coderabbit=False)
        data["statuses"].append(
            {
                "id": 20,
                "context": "CodeRabbit",
                "state": "success",
                "description": "Review completed",
                "creator": {"id": 999, "login": "coderabbitai[bot]"},
            }
        )
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["coderabbit"])

    def test_success_status_that_says_skipped_is_not_completion(self):
        data = snapshot(coderabbit=False)
        data["statuses"].append(
            {
                "id": 21,
                "context": "CodeRabbit",
                "state": "success",
                "description": "Review skipped: manual review required for this OSS repository",
                "creator": dict(CODERABBIT),
                "updated_at": "2026-08-31T03:05:00Z",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["coderabbit"])
        self.assertIn("CODERABBIT_SUCCESS_STATUS_IS_NONCOMPLETION", receipt["notes"])

    def test_mutable_check_name_cannot_spoof_codacy(self):
        data = snapshot(codacy=False)
        data["check_runs"].append(
            {
                "id": 22,
                "name": "Codacy Static Code Analysis",
                "status": "completed",
                "conclusion": "success",
                "app": {"id": 999, "slug": "attacker-app"},
            }
        )
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codacy"])

    def test_wrong_app_id_same_codacy_slug_cannot_spoof(self):
        data = snapshot(codacy=False)
        data["check_runs"].append(
            {
                "id": 23,
                "name": "Codacy Static Code Analysis",
                "status": "completed",
                "conclusion": "success",
                "app": {"id": 999, "slug": "codacy-production"},
            }
        )
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codacy"])

    def test_wrong_slug_same_codacy_app_id_cannot_spoof(self):
        data = snapshot(codacy=False)
        data["check_runs"].append(
            {
                "id": 24,
                "name": "Codacy Static Code Analysis",
                "status": "completed",
                "conclusion": "success",
                "app": {"id": 56611, "slug": "codacy-lookalike"},
            }
        )
        self.assertFalse(evaluate_review_triad(data, HEAD)["reviewer_pass"]["codacy"])


if __name__ == "__main__":
    unittest.main()
