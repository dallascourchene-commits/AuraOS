from __future__ import annotations

from copy import deepcopy
import unittest

from tools import aura_pre_attempt_lifecycle_lineage as q21


class PreAttemptLifecycleLineageTests(unittest.TestCase):
    def bind(self, o65=None, lifecycle=None):
        return q21.bind_pre_attempt_lifecycle(
            o65_receipt=o65 or q21.example_o65(),
            lifecycle_receipt=lifecycle or q21.example_lifecycle(),
        )

    def test_exact_receipts_bind_one_deterministic_lineage(self):
        first = self.bind()
        second = self.bind(deepcopy(q21.example_o65()), deepcopy(q21.example_lifecycle()))
        self.assertTrue(first.proposal_identity_shared)
        self.assertTrue(first.lineage_association_bound)
        self.assertEqual(first.lineage_digest, second.lineage_digest)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_proposal_id_mismatch_fails_closed(self):
        lifecycle = q21.example_lifecycle()
        lifecycle["proposal_id"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "Q21_PROPOSAL_IDENTITY_OR_BASIS_MISMATCH"):
            self.bind(lifecycle=lifecycle)

    def test_proposal_basis_mismatch_fails_closed(self):
        lifecycle = q21.example_lifecycle()
        lifecycle["proposal_basis_digest"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "Q21_PROPOSAL_IDENTITY_OR_BASIS_MISMATCH"):
            self.bind(lifecycle=lifecycle)

    def test_pre_attempt_must_be_eligible(self):
        o65 = q21.example_o65()
        o65["disposition"] = "HOLD_POLICY_NOT_CURRENT"
        with self.assertRaisesRegex(ValueError, "O65_PRE_ATTEMPT_NOT_ELIGIBLE"):
            self.bind(o65=o65)

    def test_pre_attempt_epoch_is_identity_bearing(self):
        first = self.bind()
        o65 = q21.example_o65()
        o65["owner_state_epoch"] = "epoch-18"
        second = self.bind(o65=o65)
        self.assertNotEqual(first.lineage_digest, second.lineage_digest)

    def test_pre_attempt_policy_generation_is_identity_bearing(self):
        first = self.bind()
        o65 = q21.example_o65()
        o65["policy_generation"] = "policy-gen-10"
        second = self.bind(o65=o65)
        self.assertNotEqual(first.lineage_digest, second.lineage_digest)

    def test_o65_execution_authority_widening_is_rejected(self):
        o65 = q21.example_o65()
        o65["execution_authorized"] = True
        with self.assertRaisesRegex(ValueError, "O65_CLAIM_CEILING_WIDENED"):
            self.bind(o65=o65)

    def test_lifecycle_must_be_current_nonexecuting(self):
        lifecycle = q21.example_lifecycle()
        lifecycle["proposal_currentness_state"] = "INVALIDATED"
        with self.assertRaisesRegex(ValueError, "LIFECYCLE_PROPOSAL_NOT_CURRENT_NONEXECUTABLE"):
            self.bind(lifecycle=lifecycle)

    def test_lifecycle_relational_gate_failure_is_rejected(self):
        for key in (
            "proposal_ref_present",
            "proposal_ref_required_by_policy",
            "source_generation_bound_to_proposal",
            "authority_scope_bound_to_proposal",
            "consequence_key_bound_to_proposal",
        ):
            with self.subTest(key=key):
                lifecycle = q21.example_lifecycle()
                lifecycle[key] = False
                with self.assertRaisesRegex(ValueError, "REQUIRED_TRUE"):
                    self.bind(lifecycle=lifecycle)

    def test_lifecycle_semantic_commit_must_be_eligible(self):
        lifecycle = q21.example_lifecycle()
        lifecycle["semantic_commit_eligible"] = False
        lifecycle["semantic_commit_key"] = None
        with self.assertRaisesRegex(ValueError, "LIFECYCLE_SEMANTIC_COMMIT_NOT_ELIGIBLE"):
            self.bind(lifecycle=lifecycle)

    def test_lifecycle_effect_authority_widening_is_rejected(self):
        lifecycle = q21.example_lifecycle()
        lifecycle["provider_effect_authority_granted"] = True
        with self.assertRaisesRegex(ValueError, "LIFECYCLE_CLAIM_CEILING_WIDENED"):
            self.bind(lifecycle=lifecycle)

    def test_route_observer_change_changes_lineage_but_never_claims_host_causality(self):
        first = self.bind()
        o65 = q21.example_o65()
        o65["expected_route_fingerprint"] = "route:bounded:v2"
        o65["expected_observer_identity"] = "HOST_OBSERVER_V2"
        second = self.bind(o65=o65)
        self.assertNotEqual(first.lineage_digest, second.lineage_digest)
        self.assertFalse(second.route_observer_to_host_witness_relation_proven)
        self.assertFalse(second.pre_attempt_caused_execution)

    def test_terminal_result_cannot_retroactively_authorize_pre_attempt(self):
        result = self.bind()
        self.assertFalse(result.pre_attempt_authorized_execution)
        self.assertFalse(result.terminal_result_retroactively_authorizes_pre_attempt)
        self.assertFalse(result.execution_lease_minted)
        self.assertTrue(result.effect_boundary_revalidation_still_required)

    def test_k27_or_cache_metadata_is_not_identity_bearing(self):
        baseline = self.bind()
        o65 = q21.example_o65()
        lifecycle = q21.example_lifecycle()
        o65["k27_coordinate"] = [1, 2, 3]
        lifecycle["cache_key"] = "external:lookup-only"
        with_context = self.bind(o65=o65, lifecycle=lifecycle)
        self.assertEqual(baseline.lineage_digest, with_context.lineage_digest)
        self.assertEqual(baseline.receipt_digest, with_context.receipt_digest)


if __name__ == "__main__":
    unittest.main()
