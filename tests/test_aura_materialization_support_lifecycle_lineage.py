from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import unittest

from tools import aura_materialization_support_lifecycle_lineage as q22
from tools import aura_authority_materialization_proposal_conformance as support_owner


def reseal_lineage(receipt):
    body = deepcopy(receipt)
    body.pop("receipt_digest", None)
    body["receipt_digest"] = q22._sha({"domain": q22.LINEAGE_SCHEMA, "receipt": body})
    return body


class MaterializationSupportLifecycleLineageTests(unittest.TestCase):
    def bind(self, support=None, lineage=None):
        return q22.bind_materialization_support_to_lineage(
            support=support or q22.example_support(),
            lineage=lineage or q22.example_lineage(),
        )

    def test_exact_parent_consequences_bind_deterministically_without_promotion(self):
        first = self.bind()
        second = self.bind(q22.example_support(), deepcopy(q22.example_lineage()))
        self.assertTrue(first.bounded_support_associated_with_lineage)
        self.assertEqual(first.supported_lineage_digest, second.supported_lineage_digest)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(
            first.base_proposal_basis_digest,
            support_owner.Q20_Q19_PROPOSAL_BASIS,
        )
        self.assertEqual(
            first.materialization_bound_proposal_basis_digest,
            support_owner.q20_materialization_bound_basis_digest(),
        )
        self.assertNotEqual(
            first.base_proposal_basis_digest,
            first.materialization_bound_proposal_basis_digest,
        )
        self.assertFalse(first.support_live_currentness_revalidated_for_lineage)
        self.assertFalse(first.support_fresh_at_pre_attempt_proven)
        self.assertFalse(first.support_fresh_at_effect_boundary_proven)
        self.assertFalse(first.support_caused_execution)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.execution_lease_minted)
        self.assertFalse(first.provider_effect_authorized)
        self.assertFalse(first.semantic_k27_authority)
        self.assertFalse(first.native_private_transformer_kv_accessed)
        self.assertFalse(first.gate10_promoted)

    def test_lineage_must_name_exact_base_proposal_basis(self):
        lineage = q22.example_lineage()
        lineage["proposal_basis_digest"] = "d" * 64
        lineage = reseal_lineage(lineage)
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_NOT_FOR_SUPPORT_BASE_PROPOSAL"):
            self.bind(lineage=lineage)

    def test_materialization_bound_basis_is_not_collapsed_into_base_basis(self):
        support = replace(
            q22.example_support(),
            proposal_basis_digest=support_owner.Q20_Q19_PROPOSAL_BASIS,
        )
        with self.assertRaisesRegex(ValueError, "Q22_MATERIALIZATION_BOUND_BASIS_MISMATCH"):
            self.bind(support=support)

    def test_support_must_be_exact_conformant_bounded_support(self):
        support = replace(q22.example_support(), disposition="REVIEW")
        with self.assertRaisesRegex(ValueError, "Q22_SUPPORT_NOT_CONFORMANT"):
            self.bind(support=support)

    def test_support_representation_crosscast_is_rejected(self):
        support = replace(
            q22.example_support(),
            evidence_representation_fingerprint="e" * 64,
        )
        with self.assertRaisesRegex(ValueError, "Q22_SUPPORT_EVIDENCE_REPRESENTATION_DIVERGENCE"):
            self.bind(support=support)

    def test_q21_lineage_must_remain_association_only(self):
        lineage = q22.example_lineage()
        lineage["pre_attempt_authorized_execution"] = True
        lineage = reseal_lineage(lineage)
        with self.assertRaisesRegex(ValueError, "MUST_BE_EXACT_FALSE"):
            self.bind(lineage=lineage)

    def test_terminal_result_cannot_make_support_fresh_or_causal(self):
        lineage = q22.example_lineage()
        lineage["lifecycle_terminal_state"] = "COMMITTED"
        lineage["lifecycle_reason_code"] = "SUCCESS"
        lineage = reseal_lineage(lineage)
        result = self.bind(lineage=lineage)
        self.assertFalse(result.support_live_currentness_revalidated_for_lineage)
        self.assertFalse(result.support_fresh_at_effect_boundary_proven)
        self.assertFalse(result.support_caused_execution)
        self.assertFalse(result.execution_authorized)

    def test_policy_or_owner_epoch_change_changes_supported_lineage(self):
        first = self.bind()
        lineage = q22.example_lineage()
        lineage["owner_state_epoch"] = "epoch-q22-next"
        lineage["pre_attempt_policy_generation"] = "policy-gen-q22-next"
        lineage["lineage_digest"] = "9" * 64
        lineage = reseal_lineage(lineage)
        second = self.bind(lineage=lineage)
        self.assertNotEqual(first.supported_lineage_digest, second.supported_lineage_digest)

    def test_parent_receipt_digest_tamper_is_rejected(self):
        lineage = q22.example_lineage()
        lineage["receipt_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Q22_LINEAGE_RECEIPT_DIGEST_MISMATCH"):
            self.bind(lineage=lineage)

    def test_support_currentness_cannot_be_self_promoted(self):
        support = replace(q22.example_support(), live_proposal_currentness_resolved=True)
        with self.assertRaisesRegex(ValueError, "Q22_SUPPORT_LIVE_CURRENTNESS_MUST_BE_EXACT_FALSE"):
            self.bind(support=support)

    def test_parent_proof_coordinates_are_pinned_in_result(self):
        result = self.bind()
        self.assertEqual(result.support_proof_head, q22.SUPPORT_PROOF_HEAD)
        self.assertEqual(result.support_run, q22.SUPPORT_RUN)
        self.assertEqual(result.support_job, q22.SUPPORT_JOB)
        self.assertEqual(result.lineage_proof_head, q22.LINEAGE_PROOF_HEAD)
        self.assertEqual(result.lineage_run, q22.LINEAGE_RUN)
        self.assertEqual(result.lineage_job, q22.LINEAGE_JOB)


if __name__ == "__main__":
    unittest.main()
