from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_directed_support_attachment_addendum import (
    BOUND,
    HOLD,
    O67_SCHEMA,
    O67_SOURCE_HEAD,
    Q22_SCHEMA,
    Q22_SOURCE_HEAD,
    O67AttachmentProjection,
    Q22DirectedSupportProjection,
    bind_directed_provenance_addendum,
)


def h(ch: str) -> str:
    return ch * 64


def q22() -> Q22DirectedSupportProjection:
    return Q22DirectedSupportProjection(
        schema=Q22_SCHEMA,
        source_head=Q22_SOURCE_HEAD,
        proposal_id=h("1"),
        base_proposal_basis_digest=h("2"),
        materialization_bound_proposal_basis_digest=h("3"),
        base_to_materialization_relation_digest=h("4"),
        proposal_evidence_support_digest=h("5"),
        supported_lineage_digest=h("6"),
        bounded_support_associated_with_lineage=True,
    )


def o67(bound: bool = True) -> O67AttachmentProjection:
    return O67AttachmentProjection(
        schema=O67_SCHEMA,
        source_head=O67_SOURCE_HEAD,
        disposition="MATERIALIZATION_SUPPORT_LINEAGE_BOUND" if bound else "HOLD_EXPLICIT_SUPPORT_ATTACHMENT_REQUIRED",
        relation_id=h("7") if bound else None,
        materialization_proposal_basis_digest=h("3"),
        materialization_support_digest=h("5"),
        lineage_proposal_id=h("1"),
        lineage_proposal_basis_digest=h("2"),
        lineage_relation_id=h("8"),
        attachment_id=h("9") if bound else None,
        attachment_owner_ref="owner:q22-o67:addendum" if bound else None,
        attachment_owner_generation="attachment-generation:q22-o67:v1" if bound else None,
        attachment_owner_state_epoch="epoch:q22-o67:1" if bound else None,
        support_attached_to_lineage_proposal=bound,
    )


class DirectedSupportAttachmentAddendumTests(unittest.TestCase):
    def test_exact_directed_relation_is_preserved_in_attachment(self):
        a = bind_directed_provenance_addendum(q22=q22(), o67=o67())
        b = bind_directed_provenance_addendum(q22=q22(), o67=o67())
        self.assertEqual(a.disposition, BOUND)
        self.assertTrue(a.directed_provenance_bound_to_attachment)
        self.assertTrue(a.collision_cognition_preserved_as_addendum)
        self.assertEqual(a.directed_attachment_addendum_id, b.directed_attachment_addendum_id)
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        self.assertFalse(a.live_support_currentness_resolved)
        self.assertFalse(a.host_causality_proven)
        self.assertFalse(a.execution_authorized)
        self.assertFalse(a.provider_effect_authorized)
        self.assertFalse(a.semantic_k27_authority)
        self.assertFalse(a.native_private_transformer_kv_accessed)
        self.assertFalse(a.gate10_promoted)

    def test_missing_o67_attachment_is_lawful_hold_not_discard(self):
        result = bind_directed_provenance_addendum(q22=q22(), o67=o67(False))
        self.assertEqual(result.disposition, HOLD)
        self.assertFalse(result.directed_provenance_bound_to_attachment)
        self.assertTrue(result.collision_cognition_preserved_as_addendum)
        self.assertIsNone(result.directed_attachment_addendum_id)

    def test_base_to_materialization_identity_collapse_rejected(self):
        item = replace(q22(), materialization_bound_proposal_basis_digest=h("2"))
        with self.assertRaisesRegex(ValueError, "DIRECTED_BASIS_MUST_NOT_COLLAPSE"):
            bind_directed_provenance_addendum(q22=item, o67=o67())

    def test_lineage_base_basis_crosscast_holds(self):
        item = replace(o67(), lineage_proposal_basis_digest=h("a"))
        result = bind_directed_provenance_addendum(q22=q22(), o67=item)
        self.assertEqual(result.disposition, "HOLD_DIRECTED_ATTACHMENT_IDENTITY_MISMATCH")
        self.assertFalse(result.directed_provenance_bound_to_attachment)

    def test_materialization_basis_crosscast_holds(self):
        item = replace(o67(), materialization_proposal_basis_digest=h("b"))
        result = bind_directed_provenance_addendum(q22=q22(), o67=item)
        self.assertEqual(result.disposition, "HOLD_DIRECTED_ATTACHMENT_IDENTITY_MISMATCH")

    def test_support_digest_crosscast_holds(self):
        item = replace(o67(), materialization_support_digest=h("c"))
        result = bind_directed_provenance_addendum(q22=q22(), o67=item)
        self.assertEqual(result.disposition, "HOLD_DIRECTED_ATTACHMENT_IDENTITY_MISMATCH")

    def test_proposal_id_crosscast_holds(self):
        item = replace(o67(), lineage_proposal_id=h("d"))
        result = bind_directed_provenance_addendum(q22=q22(), o67=item)
        self.assertEqual(result.disposition, "HOLD_DIRECTED_ATTACHMENT_IDENTITY_MISMATCH")

    def test_q22_authority_widening_rejected(self):
        for field in (
            "support_live_currentness_revalidated_for_lineage",
            "support_fresh_at_pre_attempt_proven",
            "support_fresh_at_effect_boundary_proven",
            "support_caused_execution",
            "execution_authorized",
            "provider_effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "Q22_CLAIM_CEILING_WIDENED"):
                    bind_directed_provenance_addendum(q22=replace(q22(), **{field: True}), o67=o67())

    def test_o67_authority_widening_rejected(self):
        for field in (
            "support_currentness_self_resolved",
            "execution_authority_granted",
            "execution_lease_minted",
            "provider_effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "O67_CLAIM_CEILING_WIDENED"):
                    bind_directed_provenance_addendum(q22=q22(), o67=replace(o67(), **{field: True}))

    def test_relation_receipt_drift_changes_addendum_identity(self):
        baseline = bind_directed_provenance_addendum(q22=q22(), o67=o67())
        changed_q22 = bind_directed_provenance_addendum(
            q22=replace(q22(), base_to_materialization_relation_digest=h("e")), o67=o67()
        )
        changed_owner = bind_directed_provenance_addendum(
            q22=q22(), o67=replace(o67(), attachment_owner_state_epoch="epoch:q22-o67:2")
        )
        self.assertNotEqual(baseline.directed_attachment_addendum_id, changed_q22.directed_attachment_addendum_id)
        self.assertNotEqual(baseline.directed_attachment_addendum_id, changed_owner.directed_attachment_addendum_id)


if __name__ == "__main__":
    unittest.main()
