from dataclasses import replace
import unittest

from tools import arena_portable_semantic_evidence_transfer as o61
from tools import aura_fresh_portable_semantic_evidence_admission as a6


class FreshPortableSemanticEvidenceAdmissionTests(unittest.TestCase):
    def test_q6_exact_portable_evidence_is_reusable_but_not_fresh(self):
        q6 = o61.q6_descriptor()
        receipt = a6.classify_fresh_portable_evidence(
            evidence=q6,
            consumer=o61.native_expectation(q6),
            producer_semantic_generated_at=a6.Q6_SEMANTIC_GENERATED_AT,
            transfer_observed_at="2026-08-31T13:23:03Z",
            terminal_at="2026-08-31T13:23:04Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:q6",
        )
        self.assertTrue(receipt.portable_semantic_evidence_admitted)
        self.assertTrue(receipt.portable_evidence_reuse_allowed)
        self.assertEqual(receipt.freshness_disposition, "PRE_CUT_SEMANTIC_GENERATION")
        self.assertFalse(receipt.semantic_sibling_credit)

    def test_r3_exact_portable_evidence_is_reusable_but_not_fresh(self):
        r3 = o61.r3_descriptor()
        receipt = a6.classify_fresh_portable_evidence(
            evidence=r3,
            consumer=o61.native_expectation(r3),
            producer_semantic_generated_at=a6.R3_SEMANTIC_GENERATED_AT,
            transfer_observed_at="2026-08-31T13:23:03Z",
            terminal_at="2026-08-31T13:23:04Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:r3",
        )
        self.assertEqual(receipt.freshness_disposition, "PRE_CUT_SEMANTIC_GENERATION")
        self.assertFalse(receipt.semantic_sibling_credit)

    def test_cross_domain_transfer_holds_before_freshness(self):
        q6 = o61.q6_descriptor()
        r3 = o61.r3_descriptor()
        receipt = a6.classify_fresh_portable_evidence(
            evidence=q6,
            consumer=o61.native_expectation(r3),
            producer_semantic_generated_at="2026-08-31T13:20:00Z",
            transfer_observed_at="2026-08-31T13:21:00Z",
            terminal_at="2026-08-31T13:22:00Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:cross-domain",
        )
        self.assertFalse(receipt.portable_semantic_evidence_admitted)
        self.assertEqual(receipt.freshness_disposition, "TRANSFER_NOT_ADMITTED")
        self.assertFalse(receipt.portable_evidence_reuse_allowed)
        self.assertFalse(receipt.semantic_sibling_credit)

    def test_genuinely_post_cut_semantic_generation_can_receive_sibling_credit(self):
        q6 = o61.q6_descriptor()
        fresh = replace(
            q6,
            artifact_name="FRESH_POST_CUT_FIXTURE",
            producer_head="a" * 40,
            producer_run=44444444444,
            producer_job=55555555555,
        )
        receipt = a6.classify_fresh_portable_evidence(
            evidence=fresh,
            consumer=o61.native_expectation(fresh),
            producer_semantic_generated_at="2026-08-31T13:20:00Z",
            transfer_observed_at="2026-08-31T13:21:00Z",
            terminal_at="2026-08-31T13:22:00Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:fresh",
        )
        self.assertTrue(receipt.portable_semantic_evidence_admitted)
        self.assertEqual(receipt.freshness_disposition, "SEMANTIC_SIBLING")
        self.assertTrue(receipt.semantic_sibling_credit)
        self.assertFalse(receipt.producer_generation_authenticated)

    def test_post_cut_transfer_of_pre_cut_semantics_never_resets_clock(self):
        q6 = o61.q6_descriptor()
        dispositions = []
        for observed, terminal in (
            ("2026-08-31T13:23:03Z", "2026-08-31T13:23:04Z"),
            ("2026-08-31T14:23:03Z", "2026-08-31T14:23:04Z"),
        ):
            r = a6.classify_fresh_portable_evidence(
                evidence=q6,
                consumer=o61.native_expectation(q6),
                producer_semantic_generated_at=a6.Q6_SEMANTIC_GENERATED_AT,
                transfer_observed_at=observed,
                terminal_at=terminal,
                cut=a6.CURRENT_CUT,
                artifact_id="portable:q6:replay",
            )
            dispositions.append(r.freshness_disposition)
            self.assertFalse(r.semantic_sibling_credit)
        self.assertEqual(dispositions, ["PRE_CUT_SEMANTIC_GENERATION"] * 2)

    def test_self_artifact_is_rejected_after_exact_transfer(self):
        q6 = o61.q6_descriptor()
        fresh = replace(q6, producer_head="b" * 40, producer_run=7, producer_job=8)
        receipt = a6.classify_fresh_portable_evidence(
            evidence=fresh,
            consumer=o61.native_expectation(fresh),
            producer_semantic_generated_at="2026-08-31T13:20:00Z",
            transfer_observed_at="2026-08-31T13:21:00Z",
            terminal_at="2026-08-31T13:22:00Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:self",
            agent_id="GPT56SOL_A6",
            current_agent_id="GPT56SOL_A6",
        )
        self.assertEqual(receipt.freshness_disposition, "SELF_ARTIFACT")
        self.assertFalse(receipt.semantic_sibling_credit)

    def test_observation_before_cut_is_rejected_even_if_semantics_are_newer_than_old_history(self):
        q6 = o61.q6_descriptor()
        fresh = replace(q6, producer_head="c" * 40, producer_run=9, producer_job=10)
        receipt = a6.classify_fresh_portable_evidence(
            evidence=fresh,
            consumer=o61.native_expectation(fresh),
            producer_semantic_generated_at="2026-08-31T13:10:00Z",
            transfer_observed_at="2026-08-31T13:11:00Z",
            terminal_at="2026-08-31T13:11:30Z",
            cut=a6.CURRENT_CUT,
            artifact_id="portable:old-observation",
        )
        self.assertEqual(receipt.freshness_disposition, "STALE_PRE_CUT_OBSERVATION")
        self.assertFalse(receipt.semantic_sibling_credit)

    def test_fixture_is_deterministic_and_nonpromoting(self):
        first = a6.current_historical_transfer_fixture()
        second = a6.current_historical_transfer_fixture()
        self.assertEqual(first, second)
        for lane in ("q6", "r3"):
            r = first[lane]
            self.assertTrue(r["portable_evidence_reuse_allowed"])
            self.assertFalse(r["semantic_sibling_credit"])
            self.assertFalse(r["producer_generation_authenticated"])
            self.assertFalse(r["semantic_truth_minted"])
            self.assertFalse(r["broader_claims_inherited"])
            self.assertFalse(r["effect_authority_granted"])
            self.assertFalse(r["semantic_k27_authority_minted"])
            self.assertFalse(r["native_private_transformer_kv_accessed"])
            self.assertFalse(r["gate10_promoted"])
            self.assertFalse(r["merge_or_deployment_authorized"])

    def test_bad_timestamp_order_fails_closed(self):
        q6 = o61.q6_descriptor()
        with self.assertRaisesRegex(ValueError, "SEMANTIC_GENERATION_AFTER_OBSERVATION"):
            a6.classify_fresh_portable_evidence(
                evidence=q6,
                consumer=o61.native_expectation(q6),
                producer_semantic_generated_at="2026-08-31T13:24:00Z",
                transfer_observed_at="2026-08-31T13:23:00Z",
                terminal_at="2026-08-31T13:25:00Z",
                cut=a6.CURRENT_CUT,
                artifact_id="portable:bad-clock",
            )


if __name__ == "__main__":
    unittest.main()
