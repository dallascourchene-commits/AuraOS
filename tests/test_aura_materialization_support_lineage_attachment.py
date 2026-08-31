from __future__ import annotations

from dataclasses import replace
import unittest

from tools import aura_materialization_support_lineage_attachment as o67


class Resolver:
    def __init__(self, attachment=None, raises=False):
        self.attachment = attachment
        self.raises = raises

    def resolve_support_lineage_attachment(self, **kwargs):
        if self.raises:
            raise RuntimeError("owner unavailable")
        return self.attachment


def exact_attachment(support=None, lineage=None):
    support = support or o67.example_support()
    lineage = lineage or o67.example_lineage()
    return o67.SupportLineageAttachment(
        owner_ref="owner:proposal-support-lineage-attachment:v1",
        owner_generation="attachment-generation:o67:1",
        owner_state_epoch="attachment-epoch:o67:1",
        materialization_proposal_basis_digest=support.materialization_proposal_basis_digest,
        materialization_support_digest=support.proposal_evidence_support_digest,
        lineage_proposal_id=lineage.proposal_id,
        lineage_proposal_basis_digest=lineage.proposal_basis_digest,
    )


class O67Tests(unittest.TestCase):
    def setUp(self):
        self.support = o67.example_support()
        self.lineage = o67.example_lineage()

    def evaluate(self, resolver):
        return o67.evaluate_materialization_support_lineage(
            support=self.support, lineage=self.lineage, attachment_resolver=resolver
        )

    def test_missing_attachment_owner_is_lawful_hold(self):
        d = self.evaluate(None)
        self.assertEqual(d.disposition, o67.HOLD_REQUIRED)
        self.assertIsNone(d.relation_id)
        self.assertFalse(d.support_attached_to_lineage_proposal)

    def test_owner_reports_no_attachment_is_hold(self):
        d = self.evaluate(Resolver(None))
        self.assertEqual(d.disposition, o67.HOLD_REQUIRED)
        self.assertIsNone(d.relation_id)

    def test_exact_owner_attachment_binds_deterministically_without_authority(self):
        attachment = exact_attachment(self.support, self.lineage)
        first = self.evaluate(Resolver(attachment))
        second = self.evaluate(Resolver(attachment))
        self.assertEqual(first.disposition, o67.BOUND)
        self.assertEqual(first.relation_id, second.relation_id)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertTrue(first.support_attached_to_lineage_proposal)
        self.assertFalse(first.execution_authority_granted)
        self.assertFalse(first.provider_effect_authority_granted)
        self.assertFalse(first.semantic_k27_authority_minted)

    def test_materialization_basis_substitution_rejected_by_parent_projection(self):
        bad = replace(self.support, materialization_proposal_basis_digest="a" * 64)
        with self.assertRaisesRegex(ValueError, "MATERIALIZATION_BASIS_MISMATCH"):
            o67.evaluate_materialization_support_lineage(
                support=bad, lineage=self.lineage, attachment_resolver=None
            )

    def test_attachment_support_digest_mismatch_holds(self):
        a = replace(exact_attachment(self.support, self.lineage), materialization_support_digest="b" * 64)
        d = self.evaluate(Resolver(a))
        self.assertEqual(d.disposition, "HOLD_ATTACHMENT_IDENTITY_MISMATCH")
        self.assertIsNone(d.relation_id)

    def test_attachment_lineage_identity_mismatch_holds(self):
        a = replace(exact_attachment(self.support, self.lineage), lineage_proposal_id="c" * 64)
        d = self.evaluate(Resolver(a))
        self.assertEqual(d.disposition, "HOLD_ATTACHMENT_IDENTITY_MISMATCH")
        self.assertIsNone(d.relation_id)

    def test_coordinate_cannot_impersonate_attachment_owner(self):
        a = replace(exact_attachment(self.support, self.lineage), owner_ref="k27:123:456:789")
        d = self.evaluate(Resolver(a))
        self.assertEqual(d.disposition, "HOLD_ATTACHMENT_INVALID")
        self.assertIn("OWNER_REF_NOT_COORDINATE", d.reason_code)

    def test_attachment_cannot_smuggle_effect_authority(self):
        a = replace(exact_attachment(self.support, self.lineage), execution_authority_granted=True)
        d = self.evaluate(Resolver(a))
        self.assertEqual(d.disposition, "HOLD_ATTACHMENT_INVALID")
        self.assertIn("CANNOT_CARRY_EFFECT_AUTHORITY", d.reason_code)

    def test_parent_authority_widening_rejected(self):
        bad = replace(self.lineage, execution_lease_minted=True)
        with self.assertRaisesRegex(ValueError, "O66_CLAIM_CEILING_WIDENED"):
            o67.evaluate_materialization_support_lineage(
                support=self.support, lineage=bad, attachment_resolver=None
            )

    def test_owner_resolution_error_fails_closed(self):
        d = self.evaluate(Resolver(raises=True))
        self.assertEqual(d.disposition, "HOLD_ATTACHMENT_OWNER_RESOLUTION_ERROR")
        self.assertIsNone(d.relation_id)


if __name__ == "__main__":
    unittest.main()
