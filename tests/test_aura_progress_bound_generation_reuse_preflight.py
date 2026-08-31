import dataclasses
import unittest

from tools.aura_progress_bound_generation_reuse_preflight import (
    AdmissionReuseProjectionV1,
    Disposition,
    NAV14_HEAD,
    NAV14_JOB,
    NAV14_RUN,
    ProgressBoundHandoffProjectionV1,
    REQUIRED_DEBTS,
    REUSE_HEAD,
    REUSE_JOB,
    REUSE_RUN,
    _classify_rules,
    _classify_tree,
    assess_progress_bound_reuse_preflight,
)


class ProgressBoundGenerationReuseTests(unittest.TestCase):
    def handoff(self):
        return ProgressBoundHandoffProjectionV1(
            parent_head=NAV14_HEAD,
            parent_run=NAV14_RUN,
            parent_job=NAV14_JOB,
            disposition="PROGRESS_BOUND_HANDOFF_CANDIDATE",
            progress_handoff_digest="a" * 64,
            retrieval_receipt_digest="b" * 64,
            subject_key="subject:hydration",
            evidence_generation_key="evidence-generation:hydration:1",
            material_digest="c" * 64,
            exact_source_uri="https://example.invalid/source/v1",
        )

    def reuse(self):
        return AdmissionReuseProjectionV1(
            parent_head=REUSE_HEAD,
            parent_run=REUSE_RUN,
            parent_job=REUSE_JOB,
            disposition="REUSE_CANDIDATE",
            family="HYDRATION_TRANSACTION",
            reuse_digest="d" * 64,
            admission_receipt_digest="e" * 64,
            subject_identity="subject:hydration",
            source_generation_key="source-generation:hydration:1",
            evidence_generation_key="evidence-generation:hydration:1",
            owner_context_key="owner-context:hydration:1",
            decision_context_key="decision-context:hydration:1",
        )

    def test_exact_candidate_preserves_debt_and_authority_ceiling(self):
        r = assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=self.reuse())
        self.assertEqual(r.disposition, Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE)
        self.assertEqual(r.unresolved_debts, REQUIRED_DEBTS)
        self.assertFalse(r.source_relation_proven)
        self.assertFalse(r.source_currentness_proven)
        self.assertFalse(r.read_currentness_proven)
        self.assertFalse(r.persistent_use_authorized)
        self.assertFalse(r.execution_authorized)
        self.assertFalse(r.effect_authorized)
        self.assertFalse(r.semantic_k27_authority)
        self.assertFalse(r.native_private_transformer_kv_accessed)

    def test_source_namespaces_are_not_cross_cast(self):
        reuse = dataclasses.replace(self.reuse(), source_generation_key="totally-different-source-generation-namespace")
        r = assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=reuse)
        self.assertTrue(r.ready)
        self.assertEqual(r.source_generation_key, "totally-different-source-generation-namespace")
        self.assertIn("SOURCE_URI_TO_SOURCE_GENERATION_RELATION", r.unresolved_debts)
        self.assertFalse(r.source_relation_proven)

    def test_subject_mismatch_holds(self):
        reuse = dataclasses.replace(self.reuse(), subject_identity="subject:other")
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=reuse).disposition, Disposition.HOLD_SUBJECT_MISMATCH)

    def test_evidence_generation_mismatch_holds(self):
        reuse = dataclasses.replace(self.reuse(), evidence_generation_key="evidence-generation:hydration:2")
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=reuse).disposition, Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH)

    def test_parent_generation_and_proof_substitution_hold(self):
        bad_head = dataclasses.replace(self.handoff(), parent_head="f" * 40)
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=bad_head, reuse=self.reuse()).disposition, Disposition.HOLD_PARENT_GENERATION)
        bad_proof = dataclasses.replace(self.reuse(), parent_job=1)
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=bad_proof).disposition, Disposition.HOLD_PARENT_PROOF)

    def test_nonready_and_wrong_family_hold(self):
        bad_handoff = dataclasses.replace(self.handoff(), disposition="HOLD")
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=bad_handoff, reuse=self.reuse()).disposition, Disposition.HOLD_PARENT_NOT_READY)
        bad_family = dataclasses.replace(self.reuse(), family="GLM53_BOUNDED_C2_PROPOSAL")
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=bad_family).disposition, Disposition.HOLD_REUSE_FAMILY)

    def test_claim_widening_holds(self):
        bad = dataclasses.replace(self.reuse(), execution_authorized=True)
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=bad).disposition, Disposition.HOLD_CLAIM_CEILING)
        bad2 = dataclasses.replace(self.handoff(), read_currentness_proven=True)
        self.assertEqual(assess_progress_bound_reuse_preflight(handoff=bad2, reuse=self.reuse()).disposition, Disposition.HOLD_CLAIM_CEILING)

    def test_receipt_is_deterministic(self):
        a = assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=self.reuse())
        b = assess_progress_bound_reuse_preflight(handoff=self.handoff(), reuse=self.reuse())
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_different_j_complete_128_state_lattice(self):
        checked = 0
        h0, r0 = self.handoff(), self.reuse()
        for mask in range(128):
            h = dataclasses.replace(
                h0,
                parent_head=("f" * 40 if mask & 1 else h0.parent_head),
                parent_job=(1 if mask & 2 else h0.parent_job),
                disposition=("HOLD" if mask & 4 else h0.disposition),
                effect_authorized=bool(mask & 8),
            )
            r = dataclasses.replace(
                r0,
                family=("OTHER" if mask & 16 else r0.family),
                subject_identity=("subject:other" if mask & 32 else r0.subject_identity),
                evidence_generation_key=("evidence:other" if mask & 64 else r0.evidence_generation_key),
            )
            self.assertEqual(_classify_tree(h, r), _classify_rules(h, r))
            checked += 1
        self.assertEqual(checked, 128)


if __name__ == "__main__":
    unittest.main()
