import inspect
import unittest

from tools.bughound.blind_discovery import (
    BlindDiscoveryError,
    BlindFindingV1,
    EvaluatorFindingResolutionV1,
    adjudicate_blind_finding,
    compile_blind_case,
)
from tools.bughound.blind_oracle_provenance import (
    issue_evaluator_resolution_envelope,
)
from tools.bughound.blind_score_admission import (
    SCHEMA,
    score_producer_bound_blind_finding,
)
from tools.bughound.seedlab_benchmark import seeded_cases


class BlindScoreAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.bug = seeded_cases()[0]
        self.clean = seeded_cases()[-1]
        self.secret = "evaluator-hidden-secret-v1"
        self.generation = "blind-eval-v1"
        self.packet, self.binding = compile_blind_case(
            self.bug,
            evaluator_salt="score-admission-salt",
            evaluator_generation=self.generation,
            worker_budget=1,
            tool_budget=3,
        )
        self.finding = BlindFindingV1(
            target_id=self.packet.target_id,
            finding_id="score-f1",
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
            producer_generation=self.generation,
        )

    def score(self, **overrides):
        args = dict(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding,
            resolution=self.resolution,
            resolution_envelope=self.envelope(),
            evaluator_secret=self.secret,
            expected_producer_generation=self.generation,
        )
        args.update(overrides)
        return score_producer_bound_blind_finding(**args)

    def test_canonical_score_api_accepts_no_precomputed_adjudication(self):
        params = inspect.signature(score_producer_bound_blind_finding).parameters
        self.assertNotIn("adjudication", params)
        self.assertNotIn("inner_adjudication", params)
        self.assertIn("resolution_envelope", params)
        self.assertIn("evaluator_secret", params)

    def test_legacy_shape_only_tp_cannot_be_laundered_into_canonical_score(self):
        legacy = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding,
            resolution=self.resolution,
        )
        # This demonstrates the exact bypass-shaped object that existed before
        # score admission. It is diagnostic only and is not an input type to the
        # canonical scoring function.
        self.assertTrue(legacy.seeded_true_positive)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            score_producer_bound_blind_finding(
                packet=self.packet,
                binding=self.binding,
                case=self.bug,
                finding=self.finding,
                resolution=self.resolution,
                resolution_envelope=None,
                evaluator_secret=self.secret,
                expected_producer_generation=self.generation,
            )
        self.assertEqual("EVALUATOR_PRODUCER_ENVELOPE_REQUIRED", ctx.exception.code)

    def test_exact_producer_bound_path_emits_score_receipt(self):
        out = self.score()
        self.assertEqual(SCHEMA, out.schema)
        self.assertEqual("SEEDED_BUG_DISCOVERED", out.outcome)
        self.assertTrue(out.seeded_true_positive)
        self.assertTrue(out.independent_oracle_producer_proven)
        self.assertEqual(self.envelope().envelope_digest, out.evaluator_envelope_digest)
        self.assertFalse(out.authority)
        self.assertFalse(out.external_effect)

    def test_wrong_secret_cannot_score_seeded_tp(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            self.score(evaluator_secret="different-hidden-secret")
        self.assertEqual("EVALUATOR_PRODUCER_MAC_MISMATCH", ctx.exception.code)

    def test_wrong_expected_producer_generation_cannot_score(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            self.score(expected_producer_generation="blind-eval-v2")
        self.assertEqual("EVALUATOR_PRODUCER_BINDING_MISMATCH", ctx.exception.code)

    def test_no_resolution_novelty_remains_uncredited(self):
        out = self.score(resolution=None, resolution_envelope=None)
        self.assertEqual("POTENTIAL_NOVELTY_UNVERIFIED", out.outcome)
        self.assertFalse(out.seeded_true_positive)
        self.assertTrue(out.novelty_verification_required)
        self.assertFalse(out.independent_oracle_producer_proven)
        self.assertIsNone(out.evaluator_envelope_digest)

    def test_clean_abstention_is_scoreable_without_oracle_envelope(self):
        packet, binding = compile_blind_case(
            self.clean,
            evaluator_salt="score-clean-salt",
            evaluator_generation=self.generation,
        )
        out = score_producer_bound_blind_finding(
            packet=packet,
            binding=binding,
            case=self.clean,
            finding=None,
            resolution=None,
            resolution_envelope=None,
            evaluator_secret=self.secret,
            expected_producer_generation=self.generation,
        )
        self.assertEqual("CLEAN_CONTROL_CORRECT", out.outcome)
        self.assertTrue(out.clean_control_correct)
        self.assertFalse(out.seeded_true_positive)
        self.assertFalse(out.independent_oracle_producer_proven)

    def test_score_receipt_is_deterministic_for_same_bound_inputs(self):
        a = self.score()
        b = self.score()
        self.assertEqual(a.score_receipt_digest, b.score_receipt_digest)
        self.assertEqual(a.producer_bound_adjudication_digest, b.producer_bound_adjudication_digest)


if __name__ == "__main__":
    unittest.main()
