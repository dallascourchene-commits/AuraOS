from __future__ import annotations

import unittest
from hashlib import sha256

from tools.arena.k27_memory.gate10_reviewer_admission import (
    Decision, EXPECTED_ROUNDS, PROVENANCE_ARCHIVE_SHA256, PROVENANCE_MANIFEST_SHA256,
    REGISTRY_SHA256, SCENE_SOURCE_SHA256, SEMANTIC_REGISTRY_ROOT, build_terminal,
    evaluate_gate10_reviewer_admission, replay_trace_root,
)

HEAD = "67e1062cfab90ce647c7e3450cc613424746e285"
OWNER = "SESSION-WORKER:GPT56SOL:20260906T0846-0500-E4B9-STACK"
REVIEWER = "DIFFERENT-J:PR863:GATE10:REVIEWER:EXAMPLE"


def state_root(i: int) -> str:
    return sha256(f"post-repair:{i}".encode()).hexdigest()


def valid_evidence():
    trace = [{
        "round": i, "concurrent_attempts": 5, "winner_count": 1,
        "store_root_conflict_holds": 4, "stale_dependency_probe": "HOLD_STALE_DEPENDENCY",
        "aba_violations": 0, "false_accepts": 0, "false_holds": 0,
        "post_repair_state_root": state_root(i),
    } for i in range(EXPECTED_ROUNDS)]
    return {
        "reviewer_identity": {
            "authority_status": "EXTERNALLY_AUTHENTICATED",
            "actor_id": "worker:different-j",
            "lineage_root": REVIEWER,
            "generation": "github-app-review:20260906",
            "attestation_root": "b" * 64,
        },
        "replay": {
            "campaign_complete": True, "completed_rounds": 750, "round_failures": 0,
            "concurrent_attempts": 3750, "stale_dependency_probes": 750,
            "aba_violations": 0, "false_accepts": 0, "false_holds": 0,
            "trace": trace, "campaign_root": replay_trace_root(trace),
        },
        "registry": {
            "dataSound": True, "uniqueKeys": 1115, "ambiguousDigests": 0,
            "registry_sha256": REGISTRY_SHA256, "semantic_registry_root": SEMANTIC_REGISTRY_ROOT,
        },
        "provenance": {
            "archive_sha256": PROVENANCE_ARCHIVE_SHA256,
            "manifest_sha256": PROVENANCE_MANIFEST_SHA256,
            "scene_source_sha256": SCENE_SOURCE_SHA256,
            "manifest_payloads_verified": 69, "provider_bytes_bound": True,
        },
        "invalidation": {"bounded": True, "deterministic": True, "ambiguous_edges": 0},
        "authority": {
            "k27_coordinate_authority": False, "truth_authority": False,
            "currentness_authority": False, "authority_minted": False, "gate10": False,
            "canonical_promotion": False, "merge_authority": False, "effect_authority": False,
        },
    }


def terminal_for(evidence, lineage=REVIEWER, head=HEAD):
    return build_terminal(
        terminal_id="terminal:review:1", actor_id="worker:different-j", lineage_root=lineage,
        derivation_root="sha256:" + "a" * 64, reviewed_head_sha=head, evidence=evidence,
    )


class Gate10ReviewerAdmissionTests(unittest.TestCase):
    def evaluate(self, e, t):
        return evaluate_gate10_reviewer_admission(owner_lineage_root=OWNER, current_head_sha=HEAD, terminal=t, evidence=e)

    def test_valid_complete_evidence_is_ready_non_authorizing(self):
        e = valid_evidence(); t = terminal_for(e); r = self.evaluate(e, t)
        self.assertEqual(r.decision, Decision.READY_FOR_GATE10_DIFFERENT_J_DISPOSITION)
        self.assertTrue(all(r.axes.values())); self.assertFalse(r.authority_minted); self.assertFalse(r.gate10)

    def test_same_lineage_is_hard_hold(self):
        e = valid_evidence(); e["reviewer_identity"]["lineage_root"] = OWNER
        r = self.evaluate(e, terminal_for(e, lineage=OWNER))
        self.assertIn("HOLD_SAME_OR_UNAUTHENTICATED_LINEAGE_REVIEW", r.reasons)

    def test_different_string_without_external_identity_authentication_holds(self):
        e = valid_evidence(); e["reviewer_identity"]["authority_status"] = "OBSERVED"; t = terminal_for(e)
        self.assertIn("HOLD_REVIEWER_IDENTITY_NOT_EXTERNALLY_AUTHENTICATED_AND_BOUND", self.evaluate(e, t).reasons)

    def test_external_identity_projection_must_cross_bind_actor(self):
        e = valid_evidence(); e["reviewer_identity"]["actor_id"] = "worker:other"; t = terminal_for(e)
        self.assertIn("HOLD_REVIEWER_IDENTITY_NOT_EXTERNALLY_AUTHENTICATED_AND_BOUND", self.evaluate(e, t).reasons)

    def test_stale_review_head_is_hard_hold(self):
        e = valid_evidence(); r = self.evaluate(e, terminal_for(e, head="0" * 40))
        self.assertIn("HOLD_REVIEW_HEAD_NOT_EXACT_CURRENT_HEAD", r.reasons)

    def test_projected_trace_cannot_verify_campaign_root(self):
        e = valid_evidence(); e["replay"]["trace"] = e["replay"]["trace"][-1:]; t = terminal_for(e)
        self.assertIn("HOLD_REPLAY_TRACE_NOT_COMPLETE_RECOMPUTABLE", self.evaluate(e, t).reasons)

    def test_tampered_trace_with_old_root_holds(self):
        e = valid_evidence(); e["replay"]["trace"][100]["winner_count"] = 2; t = terminal_for(e)
        self.assertIn("HOLD_REPLAY_TRACE_NOT_COMPLETE_RECOMPUTABLE", self.evaluate(e, t).reasons)

    def test_wrong_registry_shape_holds(self):
        e = valid_evidence(); e["registry"]["uniqueKeys"] = 1114; t = terminal_for(e)
        self.assertIn("HOLD_REGISTRY_SHAPE_OR_IDENTITY_MISMATCH", self.evaluate(e, t).reasons)

    def test_provider_projection_without_exact_bytes_holds(self):
        e = valid_evidence(); e["provenance"]["provider_bytes_bound"] = False; t = terminal_for(e)
        self.assertIn("HOLD_PROVIDER_BYTES_NOT_EXACTLY_BOUND", self.evaluate(e, t).reasons)

    def test_coordinate_authority_escalation_holds(self):
        e = valid_evidence(); e["authority"]["k27_coordinate_authority"] = True; t = terminal_for(e)
        self.assertIn("HOLD_COORDINATE_AUTHORITY_NOT_DECOUPLED", self.evaluate(e, t).reasons)

    def test_premature_gate10_claim_holds(self):
        e = valid_evidence(); e["authority"]["gate10"] = True; t = terminal_for(e)
        self.assertIn("HOLD_REVIEWER_PREMATURE_AUTHORITY_CLAIM", self.evaluate(e, t).reasons)

    def test_terminal_receipt_tamper_holds(self):
        e = valid_evidence(); t = terminal_for(e); t["actor_id"] = "worker:rewritten"
        self.assertIn("HOLD_TERMINAL_RECEIPT_ROOT_MISMATCH", self.evaluate(e, t).reasons)

    def test_evidence_mutation_after_terminal_seal_holds(self):
        e = valid_evidence(); t = terminal_for(e); e["invalidation"]["bounded"] = False; r = self.evaluate(e, t)
        self.assertIn("HOLD_EVIDENCE_ROOT_MISMATCH", r.reasons)
        self.assertIn("HOLD_INVALIDATION_CONE_NOT_BOUNDED_DETERMINISTIC", r.reasons)

    def test_all_13_axes_are_noncompensatory(self):
        e = valid_evidence(); r = self.evaluate(e, terminal_for(e))
        self.assertEqual(len(r.axes), 13); self.assertTrue(all(r.axes.values()))
