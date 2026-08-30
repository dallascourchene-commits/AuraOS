from dataclasses import replace
import unittest

from tools.bughound.blind_discovery import (
    BlindDiscoveryError,
    BlindFindingV1,
    EvaluatorFindingResolutionV1,
    compile_blind_case,
)
from tools.bughound.blind_oracle_provenance import (
    DEFAULT_PRODUCER_REF,
    EvaluatorResolutionEnvelopeV1,
    adjudicate_producer_bound_blind_finding,
    issue_evaluator_resolution_envelope,
    verify_evaluator_resolution_envelope,
)
from tools.bughound.seedlab_benchmark import seeded_cases


class BlindOracleProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.bug = seeded_cases()[0]
        self.clean = seeded_cases()[-1]
        self.secret = "evaluator-hidden-secret-v1"
        self.producer_generation = "blind-eval-v1"
        self.packet, self.binding = compile_blind_case(
            self.bug,
            evaluator_salt="opaque-target-salt",
            evaluator_generation=self.producer_generation,
            worker_budget=1,
            tool_budget=3,
        )
        self.finding = BlindFindingV1(
            target_id=self.packet.target_id,
            finding_id="f1",
            localized_symbols=("admit",),
            defect_hypothesis="stale generation accepted",
            evidence_refs=("candidate:source-line",),
        )
        self.resolution = EvaluatorFindingResolutionV1(
            target_id=self.packet.target_id,
            finding_id=self.finding.finding_id,
            hidden_case_digest=self.bug.case_digest,
            oracle_id=self.bug.oracle_id,
            evaluator_generation=self.binding.evaluator_generation,
            corroborates_seeded_bug=True,
            evidence_refs=("evaluator:hidden-oracle",),
            independent_oracle=True,
        )

    def envelope(self):
        return issue_evaluator_resolution_envelope(
            self.resolution,
            evaluator_secret=self.secret,
            producer_ref=DEFAULT_PRODUCER_REF,
            producer_generation=self.producer_generation,
        )

    def test_exact_producer_bound_resolution_can_earn_seeded_tp(self):
        envelope = self.envelope()
        out = adjudicate_producer_bound_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding,
            resolution=self.resolution,
            resolution_envelope=envelope,
            evaluator_secret=self.secret,
            expected_producer_generation=self.producer_generation,
        )
        self.assertEqual("SEEDED_BUG_DISCOVERED", out.inner_adjudication.outcome)
        self.assertTrue(out.inner_adjudication.seeded_true_positive)
        self.assertTrue(out.independent_oracle_producer_proven)
        self.assertEqual(envelope.envelope_digest, out.evaluator_envelope_digest)
        self.assertFalse(out.authority)
        self.assertFalse(out.external_effect)

    def test_resolution_boolean_without_producer_envelope_cannot_earn_tp(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            adjudicate_producer_bound_blind_finding(
                packet=self.packet,
                binding=self.binding,
                case=self.bug,
                finding=self.finding,
                resolution=self.resolution,
                evaluator_secret=self.secret,
                expected_producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_ENVELOPE_REQUIRED", ctx.exception.code)

    def test_forged_mac_fails(self):
        envelope = replace(self.envelope(), producer_mac="0" * 64)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            verify_evaluator_resolution_envelope(
                envelope,
                self.resolution,
                evaluator_secret=self.secret,
                expected_producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_MAC_MISMATCH", ctx.exception.code)

    def test_wrong_secret_fails(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            verify_evaluator_resolution_envelope(
                self.envelope(),
                self.resolution,
                evaluator_secret="different-hidden-secret",
                expected_producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_MAC_MISMATCH", ctx.exception.code)

    def test_producer_ref_substitution_fails(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            verify_evaluator_resolution_envelope(
                self.envelope(),
                self.resolution,
                evaluator_secret=self.secret,
                expected_producer_ref="ATTACKER_EVALUATOR",
                expected_producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_BINDING_MISMATCH", ctx.exception.code)

    def test_producer_generation_substitution_fails(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            verify_evaluator_resolution_envelope(
                self.envelope(),
                self.resolution,
                evaluator_secret=self.secret,
                expected_producer_generation="blind-eval-v2",
            )
        self.assertEqual("EVALUATOR_PRODUCER_BINDING_MISMATCH", ctx.exception.code)

    def test_resolution_mutation_fails_binding(self):
        mutated = replace(self.resolution, corroborates_seeded_bug=False)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            verify_evaluator_resolution_envelope(
                self.envelope(),
                mutated,
                evaluator_secret=self.secret,
                expected_producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_BINDING_MISMATCH", ctx.exception.code)

    def test_nonindependent_resolution_cannot_be_issued(self):
        resolution = replace(self.resolution, independent_oracle=False)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            issue_evaluator_resolution_envelope(
                resolution,
                evaluator_secret=self.secret,
                producer_generation=self.producer_generation,
            )
        self.assertEqual("INDEPENDENT_ORACLE_REQUIRED", ctx.exception.code)

    def test_short_or_missing_secret_fails(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            issue_evaluator_resolution_envelope(
                self.resolution,
                evaluator_secret="short",
                producer_generation=self.producer_generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_SECRET_INVALID", ctx.exception.code)

    def test_same_resolution_and_secret_are_deterministic(self):
        a = self.envelope()
        b = self.envelope()
        self.assertEqual(a.producer_mac, b.producer_mac)
        self.assertEqual(a.envelope_digest, b.envelope_digest)

    def test_different_secret_changes_mac(self):
        a = self.envelope()
        b = issue_evaluator_resolution_envelope(
            self.resolution,
            evaluator_secret="another-hidden-secret-v1",
            producer_generation=self.producer_generation,
        )
        self.assertNotEqual(a.producer_mac, b.producer_mac)

    def test_no_resolution_remains_novelty_without_producer_proof(self):
        out = adjudicate_producer_bound_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding,
            resolution=None,
            resolution_envelope=None,
            evaluator_secret=self.secret,
            expected_producer_generation=self.producer_generation,
        )
        self.assertEqual("POTENTIAL_NOVELTY_UNVERIFIED", out.inner_adjudication.outcome)
        self.assertFalse(out.independent_oracle_producer_proven)
        self.assertIsNone(out.evaluator_envelope_digest)

    def test_clean_abstention_needs_no_oracle_envelope(self):
        packet, binding = compile_blind_case(
            self.clean,
            evaluator_salt="clean-opaque-salt",
            evaluator_generation=self.producer_generation,
        )
        out = adjudicate_producer_bound_blind_finding(
            packet=packet,
            binding=binding,
            case=self.clean,
            finding=None,
            resolution=None,
            resolution_envelope=None,
            evaluator_secret=self.secret,
            expected_producer_generation=self.producer_generation,
        )
        self.assertEqual("CLEAN_CONTROL_CORRECT", out.inner_adjudication.outcome)
        self.assertTrue(out.inner_adjudication.clean_control_correct)
        self.assertFalse(out.independent_oracle_producer_proven)


if __name__ == "__main__":
    unittest.main()
