from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_proposal_support_lifecycle_lineage import (
    Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS,
    attach_bounded_support_to_lineage,
    example_lineage,
    example_support,
)


class O67ProposalSupportLifecycleLineageTests(unittest.TestCase):
    def test_exact_relation_is_deterministic_and_nonpromoting(self):
        first = attach_bounded_support_to_lineage(
            support=example_support(), lineage=example_lineage()
        )
        second = attach_bounded_support_to_lineage(
            support=example_support(), lineage=example_lineage()
        )
        self.assertEqual(first, second)
        self.assertEqual(first.disposition, "EXACT_BOUNDED_SUPPORT_LINEAGE")
        self.assertTrue(first.bounded_support_attached_to_exact_lineage)
        self.assertEqual(first.proposal_basis_digest, Q20_MATERIALIZATION_BOUND_PROPOSAL_BASIS)
        self.assertIsNotNone(first.support_lineage_digest)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertFalse(first.live_proposal_currentness_resolved)
        self.assertFalse(first.host_consumption_or_causality_proven)
        self.assertFalse(first.lifecycle_terminality_reinterpreted)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.provider_effect_authorized)
        self.assertFalse(first.semantic_k27_authority)
        self.assertFalse(first.native_private_transformer_kv_accessed)
        self.assertFalse(first.gate10_promoted)
        self.assertFalse(first.merge_deploy_spend_public_financial_human_effect_authorized)

    def test_proposal_basis_substitution_becomes_review_not_support(self):
        lineage = replace(example_lineage(), proposal_basis_digest="d" * 64)
        result = attach_bounded_support_to_lineage(
            support=example_support(), lineage=lineage
        )
        self.assertEqual(result.disposition, "REVIEW")
        self.assertEqual(result.reason_code, "PROPOSAL_BASIS_DIVERGENCE")
        self.assertFalse(result.bounded_support_attached_to_exact_lineage)
        self.assertIsNone(result.support_lineage_digest)

    def test_o65r_parent_substitution_fails_closed(self):
        support = replace(example_support(), proof_head="0" * 40)
        with self.assertRaisesRegex(ValueError, "O67_O65R_EXACT_HOSTED_PARENT_REQUIRED"):
            attach_bounded_support_to_lineage(support=support, lineage=example_lineage())

    def test_q21_parent_substitution_fails_closed(self):
        lineage = replace(example_lineage(), run_id=1)
        with self.assertRaisesRegex(ValueError, "O67_Q21_EXACT_HOSTED_PARENT_REQUIRED"):
            attach_bounded_support_to_lineage(support=example_support(), lineage=lineage)

    def test_support_cannot_smuggle_currentness_or_effect_authority(self):
        for field in (
            "live_proposal_currentness_resolved",
            "execution_authorized",
            "provider_effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            with self.subTest(field=field):
                support = replace(example_support(), **{field: True})
                with self.assertRaisesRegex(ValueError, "O67_O65R_CLAIM_CEILING_WIDENED"):
                    attach_bounded_support_to_lineage(support=support, lineage=example_lineage())

    def test_q21_lineage_cannot_smuggle_causal_or_effect_authority(self):
        for field in (
            "route_observer_to_host_witness_relation_proven",
            "pre_attempt_caused_execution",
            "pre_attempt_authorized_execution",
            "terminal_result_retroactively_authorizes_pre_attempt",
            "execution_lease_minted",
            "execution_authority_granted",
            "provider_effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect_authorized",
        ):
            with self.subTest(field=field):
                lineage = replace(example_lineage(), **{field: True})
                with self.assertRaisesRegex(ValueError, "O67_Q21_CAUSAL_OR_EFFECT_CEILING_WIDENED"):
                    attach_bounded_support_to_lineage(support=example_support(), lineage=lineage)

    def test_q21_effect_boundary_revalidation_must_remain_required(self):
        lineage = replace(
            example_lineage(), effect_boundary_revalidation_still_required=False
        )
        with self.assertRaisesRegex(ValueError, "O67_Q21_EFFECT_BOUNDARY_REVALIDATION_REQUIRED"):
            attach_bounded_support_to_lineage(support=example_support(), lineage=lineage)

    def test_distinct_support_or_lineage_receipt_changes_relation_identity(self):
        exact = attach_bounded_support_to_lineage(
            support=example_support(), lineage=example_lineage()
        )
        support_changed = attach_bounded_support_to_lineage(
            support=replace(example_support(), proposal_evidence_support_digest="e" * 64),
            lineage=example_lineage(),
        )
        lineage_changed = attach_bounded_support_to_lineage(
            support=example_support(),
            lineage=replace(example_lineage(), lineage_receipt_digest="f" * 64),
        )
        self.assertNotEqual(exact.support_lineage_digest, support_changed.support_lineage_digest)
        self.assertNotEqual(exact.support_lineage_digest, lineage_changed.support_lineage_digest)
        self.assertNotEqual(support_changed.support_lineage_digest, lineage_changed.support_lineage_digest)


if __name__ == "__main__":
    unittest.main()
