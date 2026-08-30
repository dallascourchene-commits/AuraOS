from dataclasses import replace
import json
import unittest

from tools.bughound.blind_discovery import (
    ADJUDICATION_SCHEMA,
    FORBIDDEN_CANDIDATE_FIELDS,
    BlindDiscoveryError,
    BlindFindingV1,
    adjudicate_blind_finding,
    compile_blind_case,
    parse_blind_finding,
    validate_packet_binding,
)
from tools.bughound.seedlab_benchmark import Visibility, seeded_cases


class BlindDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.bug = seeded_cases()[0]
        self.clean = seeded_cases()[-1]
        self.packet, self.binding = compile_blind_case(
            self.bug,
            evaluator_salt="evaluator-secret-salt-A",
            evaluator_generation="blind-eval-v1",
            worker_budget=1,
            tool_budget=3,
        )

    def finding(self, *, symbols=("admit",), hypothesis="stale generation accepted"):
        return BlindFindingV1(
            target_id=self.packet.target_id,
            finding_id="finding-local-1",
            localized_symbols=tuple(symbols),
            defect_hypothesis=hypothesis,
            evidence_refs=("source:admit",),
        )

    def test_candidate_packet_contains_no_forbidden_hidden_fields(self):
        body = self.packet.to_candidate_dict()
        self.assertFalse(FORBIDDEN_CANDIDATE_FIELDS.intersection(body))
        self.assertNotIn("case_id", json.dumps(body, sort_keys=True))
        self.assertFalse(body["fixed_patch_visible"])
        self.assertFalse(body["labels_visible"])
        self.assertFalse(body["authority"])
        self.assertFalse(body["external_effect"])

    def test_hidden_binding_is_separate_from_candidate_packet(self):
        body = self.packet.to_candidate_dict()
        self.assertNotIn(self.binding.hidden_case_digest, json.dumps(body, sort_keys=True))
        self.assertEqual(self.bug.case_digest, self.binding.hidden_case_digest)
        self.assertEqual(self.packet.target_id, self.binding.target_id)

    def test_same_salt_and_case_are_deterministic(self):
        p2, b2 = compile_blind_case(
            self.bug,
            evaluator_salt="evaluator-secret-salt-A",
            evaluator_generation="blind-eval-v1",
            worker_budget=1,
            tool_budget=3,
        )
        self.assertEqual(self.packet.packet_digest, p2.packet_digest)
        self.assertEqual(self.packet.target_id, p2.target_id)
        self.assertEqual(self.binding.binding_digest, b2.binding_digest)

    def test_different_salt_changes_opaque_target_not_source_semantics(self):
        p2, _ = compile_blind_case(
            self.bug,
            evaluator_salt="evaluator-secret-salt-B",
            evaluator_generation="blind-eval-v1",
        )
        self.assertNotEqual(self.packet.target_id, p2.target_id)
        self.assertEqual(self.packet.source_snapshot_digest, p2.source_snapshot_digest)
        self.assertEqual(self.packet.source_snapshot, p2.source_snapshot)

    def test_candidate_case_id_injection_is_blindness_violation(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            parse_blind_finding(
                {
                    "target_id": self.packet.target_id,
                    "finding_id": "f1",
                    "localized_symbols": ["admit"],
                    "defect_hypothesis": "x",
                    "case_id": self.bug.case_id,
                }
            )
        self.assertEqual("BLINDNESS_VIOLATION", ctx.exception.code)

    def test_unknown_finding_field_fails_closed(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            parse_blind_finding(
                {
                    "target_id": self.packet.target_id,
                    "finding_id": "f1",
                    "localized_symbols": ["admit"],
                    "defect_hypothesis": "x",
                    "mystery_label": "hidden",
                }
            )
        self.assertEqual("BLIND_FINDING_UNKNOWN_FIELD", ctx.exception.code)

    def test_seeded_bug_localized_finding_is_discovered(self):
        out = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding(),
        )
        self.assertEqual(ADJUDICATION_SCHEMA, out.schema)
        self.assertEqual("SEEDED_BUG_DISCOVERED", out.outcome)
        self.assertTrue(out.seeded_true_positive)
        self.assertFalse(out.novelty_verification_required)
        self.assertFalse(out.authority)
        self.assertFalse(out.external_effect)

    def test_seeded_bug_without_finding_is_missed(self):
        out = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=None,
        )
        self.assertEqual("SEEDED_BUG_MISSED", out.outcome)
        self.assertFalse(out.seeded_true_positive)

    def test_nonmatching_seeded_finding_is_novelty_unverified(self):
        out = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding(symbols=("other_symbol",), hypothesis="unrelated suspicious behavior"),
        )
        self.assertEqual("POTENTIAL_NOVELTY_UNVERIFIED", out.outcome)
        self.assertFalse(out.seeded_true_positive)
        self.assertTrue(out.novelty_verification_required)

    def test_clean_control_without_finding_is_correct(self):
        packet, binding = compile_blind_case(
            self.clean,
            evaluator_salt="clean-salt",
            evaluator_generation="blind-eval-v1",
        )
        out = adjudicate_blind_finding(packet=packet, binding=binding, case=self.clean, finding=None)
        self.assertEqual("CLEAN_CONTROL_CORRECT", out.outcome)
        self.assertTrue(out.clean_control_correct)

    def test_clean_control_positive_is_false_positive(self):
        packet, binding = compile_blind_case(
            self.clean,
            evaluator_salt="clean-salt",
            evaluator_generation="blind-eval-v1",
        )
        finding = BlindFindingV1(
            target_id=packet.target_id,
            finding_id="clean-fp",
            localized_symbols=("admit",),
            defect_hypothesis="claims a bug",
        )
        out = adjudicate_blind_finding(packet=packet, binding=binding, case=self.clean, finding=finding)
        self.assertEqual("CLEAN_CONTROL_FALSE_POSITIVE", out.outcome)
        self.assertFalse(out.clean_control_correct)

    def test_target_binding_substitution_fails(self):
        bad = replace(self.binding, target_id="other-target")
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("EVALUATOR_BINDING_MISMATCH", ctx.exception.code)

    def test_hidden_case_substitution_fails(self):
        bad = replace(self.binding, hidden_case_digest="0" * 64)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("EVALUATOR_BINDING_MISMATCH", ctx.exception.code)

    def test_source_digest_drift_fails(self):
        bad = replace(self.binding, source_snapshot_digest="0" * 64)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("SOURCE_CURRENTNESS_MISMATCH", ctx.exception.code)

    def test_source_generation_drift_fails(self):
        bad = replace(self.binding, source_generation="old-generation")
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("SOURCE_CURRENTNESS_MISMATCH", ctx.exception.code)

    def test_evaluator_currentness_fails_closed(self):
        bad = replace(self.binding, evaluator_current=False)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("EVALUATOR_CURRENTNESS_REQUIRED", ctx.exception.code)

    def test_fixed_patch_leakage_invalidates_adjudication(self):
        bad = replace(self.binding, fixed_patch_visible=True)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("LEAKAGE_INVALIDATED", ctx.exception.code)

    def test_label_leakage_invalidates_adjudication(self):
        bad = replace(self.binding, labels_visible=True)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            validate_packet_binding(self.packet, bad, self.bug)
        self.assertEqual("LEAKAGE_INVALIDATED", ctx.exception.code)

    def test_finding_for_another_opaque_target_fails(self):
        finding = replace(self.finding(), target_id="other-target")
        with self.assertRaises(BlindDiscoveryError) as ctx:
            adjudicate_blind_finding(
                packet=self.packet,
                binding=self.binding,
                case=self.bug,
                finding=finding,
            )
        self.assertEqual("EVALUATOR_BINDING_MISMATCH", ctx.exception.code)

    def test_holdout_visibility_is_required(self):
        case = replace(self.bug, visibility=Visibility.DEV)
        with self.assertRaises(BlindDiscoveryError) as ctx:
            compile_blind_case(
                case,
                evaluator_salt="salt",
                evaluator_generation="blind-eval-v1",
            )
        self.assertEqual("BLIND_HOLDOUT_REQUIRED", ctx.exception.code)

    def test_neutral_instruction_cannot_be_replaced_with_issue_guidance(self):
        with self.assertRaises(BlindDiscoveryError) as ctx:
            replace(self.packet, instruction="The bug is in admit; fix stale generation acceptance.")
        self.assertEqual("NONNEUTRAL_INSTRUCTION_FORBIDDEN", ctx.exception.code)

    def test_adjudication_identity_is_deterministic(self):
        a = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding(),
        )
        b = adjudicate_blind_finding(
            packet=self.packet,
            binding=self.binding,
            case=self.bug,
            finding=self.finding(),
        )
        self.assertEqual(a.adjudication_digest, b.adjudication_digest)


if __name__ == "__main__":
    unittest.main()
