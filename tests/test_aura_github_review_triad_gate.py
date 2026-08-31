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
                "app": {"slug": "codacy"},
                "completed_at": "2026-08-31T03:02:00Z",
            }
        )
    if coderabbit_skip:
        issue_comments.append(
            {
                "id": 4,
                "user": dict(CODERABBIT),
                "body": "Draft PR not reviewed — skip review by coderabbit.ai",
                "created_at": "2026-08-31T03:03:00Z",
                "updated_at": "2026-08-31T03:03:00Z",
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
    def test_exact_head_clean_all_three_required(self):
        receipt = evaluate_review_triad(snapshot(), HEAD)
        self.assertTrue(receipt["review_triad_admitted"])
        self.assertEqual({"codex": True, "coderabbit": True, "codacy": True}, receipt["reviewer_pass"])
        self.assertEqual("PINNED_GITHUB_ACTOR_OR_APP_IDENTITY_V1", receipt["provider_identity_policy"])
        self.assertEqual(
            "COMPLETED_AND_NO_UNRESOLVED_EXACT_HEAD_FINDINGS_V1",
            receipt["provider_outcome_policy"],
        )
        self.assertFalse(receipt["merge_authorized"])
        self.assertFalse(receipt["semantic_correctness_minted"])

    def test_missing_provider_completion_fails_closed(self):
        for provider in ("codex", "coderabbit", "codacy"):
            data = snapshot(**{provider: False})
            receipt = evaluate_review_triad(data, HEAD)
            self.assertFalse(receipt["review_triad_admitted"])
            self.assertIn(f"MISSING_EXACT_HEAD_{provider.upper()}_COMPLETION", receipt["violations"])

    def test_old_codex_clean_summary_does_not_transfer_to_new_push(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {
                "id": 5,
                "user": dict(CODEX),
                "body": f"Codex Review: Didn't find any major issues. Reviewed commit: `{OLD[:10]}`",
                "created_at": "2026-08-31T03:00:00Z",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["codex"])

    def test_head_change_during_collection_fails_even_when_provider_evidence_exists(self):
        data = snapshot()
        data["pull_request_after"] = {"head": {"sha": OLD}}
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("PULL_REQUEST_HEAD_SHA_CHANGED_OR_MISMATCHED", receipt["violations"])

    def test_historical_coderabbit_skip_does_not_poison_later_completion(self):
        data = snapshot()
        data["issue_comments"].append(
            {
                "id": 6,
                "user": dict(CODERABBIT),
                "body": "Draft PR not reviewed — skip review by coderabbit.ai",
                "created_at": "2026-08-31T02:00:00Z",
                "updated_at": "2026-08-31T02:00:00Z",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertTrue(receipt["reviewer_pass"]["coderabbit"])

    def test_newer_coderabbit_skip_suppresses_older_completion(self):
        receipt = evaluate_review_triad(snapshot(coderabbit_skip=True), HEAD)
        self.assertFalse(receipt["reviewer_pass"]["coderabbit"])
        self.assertIn("MISSING_EXACT_HEAD_CODERABBIT_COMPLETION", receipt["violations"])

    def test_user_codex_request_is_not_completion(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {"id": 9, "user": {"id": 7, "login": "developer"}, "body": "@codex review"}
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["codex"])

    def test_provider_sha_mention_without_clean_completion_is_not_completion(self):
        data = snapshot(codex=False)
        data["issue_comments"].append(
            {
                "id": 10,
                "user": dict(CODEX),
                "body": f"Codex review queued for {HEAD}; still running.",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertFalse(receipt["reviewer_pass"]["codex"])

    def test_exact_head_codex_inline_finding_blocks_even_with_clean_completion(self):
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
        self.assertFalse(receipt["reviewer_pass"]["codex"])
        self.assertIn("UNRESOLVED_EXACT_HEAD_CODEX_FINDINGS", receipt["violations"])

    def test_exact_head_coderabbit_inline_finding_blocks_success_status(self):
        data = snapshot()
        data["review_comments"].append(
            {
                "id": 12,
                "commit_id": HEAD,
                "user": dict(CODERABBIT),
                "body": "Potential blocking bug",
                "created_at": "2026-08-31T03:04:00Z",
            }
        )
        receipt = evaluate_review_triad(data, HEAD)
        self.assertTrue(receipt["reviewer_completed"]["coderabbit"])
        self.assertFalse(receipt["reviewer_pass"]["coderabbit"])

    def test_repair_push_requires_fresh_all_provider_evidence(self):
        old_receipt = evaluate_review_triad(snapshot(head=OLD), OLD)
        self.assertTrue(old_receipt["review_triad_admitted"])
        new = snapshot(head=HEAD, codex=False, coderabbit=False, codacy=True)
        receipt = evaluate_review_triad(new, HEAD)
        self.assertFalse(receipt["review_triad_admitted"])
        self.assertIn("MISSING_EXACT_HEAD_CODEX_COMPLETION", receipt["violations"])
        self.assertIn("MISSING_EXACT_HEAD_CODERABBIT_COMPLETION", receipt["violations"])

    def test_mutable_status_context_cannot_spoof_codacy(self):
        data = snapshot(codacy=False)
        data["statuses"].append(
            {"id": 20, "context": "Codacy compatibility success", "state": "success", "creator": dict(ATTACKER)}
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
                "state": "APPROVED",
                "user": dict(ATTACKER),
                "body": "Codex Review: no major issues",
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
