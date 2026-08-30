from dataclasses import replace
import unittest

from tools.bughound.candidate_evidence_trust_join import (
    DUPLICATE_PLANE,
    PROGRAM_PLANE,
    REPRODUCTION_PLANE,
    REPORT_LINT_PLANE,
    CandidateEvidenceLeafProducerRecordV1,
    DuplicateEvidenceV1,
    ProgramAdmissibilityEvidenceV1,
    ReproductionEvidenceV1,
    ReportLintEvidenceV1,
    _compose_with_records,
    _resolve_leaf_from_records,
    admit_registered_candidate_evidence_trust,
    candidate_evidence_leaf_registry_receipt,
    candidate_evidence_trust_parameter_names,
)


class CandidateEvidenceTrustJoinTests(unittest.TestCase):
    def reproduction(self, **changes):
        data = dict(candidate_id="candidate-1", target_ref="target://repo", target_generation="gen-1", reproduction_receipt_digest="repro-1", reproducer_ref="reproducer-1", reproducer_generation="repro-gen-1", witness_digest="witness-1", environment_digest="env-1", scope_rules_digest="scope-1", source_currentness_ref="source-1", producer_ref="producer-repro", producer_generation="producer-repro-gen-1", producer_currentness_ref="producer-repro-current-1")
        data.update(changes)
        return ReproductionEvidenceV1(**data)

    def duplicate(self, **changes):
        data = dict(candidate_id="candidate-1", target_ref="target://repo", target_generation="gen-1", duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE", duplicate_check_currentness_ref="dup-current-1", publicly_known_root_cause=False, producer_ref="producer-dup", producer_generation="producer-dup-gen-1", producer_currentness_ref="producer-dup-current-1")
        data.update(changes)
        return DuplicateEvidenceV1(**data)

    def lint(self, **changes):
        data = dict(candidate_id="candidate-1", target_ref="target://repo", target_generation="gen-1", report_lint_state="REPORT_LINT_CLEAN", report_digest="report-1", lint_policy_generation="lint-policy-1", producer_ref="producer-lint", producer_generation="producer-lint-gen-1", producer_currentness_ref="producer-lint-current-1")
        data.update(changes)
        return ReportLintEvidenceV1(**data)

    def program(self, **changes):
        data = dict(candidate_id="candidate-1", target_ref="target://repo", target_generation="gen-1", program_admissibility_state="CURRENTLY_ADMISSIBLE", program_admissibility_ref="program-1", scope_rules_digest="scope-1", payout_rules_digest="payout-1", source_currentness_ref="source-1", producer_ref="producer-program", producer_generation="producer-program-gen-1", producer_currentness_ref="producer-program-current-1")
        data.update(changes)
        return ProgramAdmissibilityEvidenceV1(**data)

    def record(self, plane, leaf, **changes):
        data = dict(proof_plane=plane, artifact_digest=leaf.artifact_digest, candidate_id=leaf.candidate_id, target_ref=leaf.target_ref, target_generation=leaf.target_generation, producer_ref=leaf.producer_ref, producer_generation=leaf.producer_generation, producer_currentness_ref=leaf.producer_currentness_ref, registry_receipt_ref=f"registry://{plane}", registry_observer_ref=f"observer://{plane}", registry_observer_generation="observer-gen-1", registry_currentness_ref=f"current://{plane}")
        data.update(changes)
        return CandidateEvidenceLeafProducerRecordV1(**data)

    def leaves(self):
        return self.reproduction(), self.duplicate(), self.lint(), self.program()

    def records(self, leaves=None):
        reproduction, duplicate, lint, program = leaves or self.leaves()
        return (
            self.record(REPRODUCTION_PLANE, reproduction),
            self.record(DUPLICATE_PLANE, duplicate),
            self.record(REPORT_LINT_PLANE, lint),
            self.record(PROGRAM_PLANE, program),
        )

    def compose(self, leaves=None, records=None):
        reproduction, duplicate, lint, program = leaves or self.leaves()
        return _compose_with_records(reproduction=reproduction, duplicate=duplicate, report_lint=lint, program=program, records=records or self.records((reproduction, duplicate, lint, program)))

    def test_public_api_has_no_trust_override(self):
        self.assertEqual({"reproduction", "duplicate", "report_lint", "program"}, set(candidate_evidence_trust_parameter_names()))

    def test_production_registry_is_empty_for_all_four_planes(self):
        receipt = candidate_evidence_leaf_registry_receipt()
        self.assertEqual((0, 0, 0, 0), (receipt.reproduction_record_count, receipt.duplicate_record_count, receipt.lint_record_count, receipt.program_record_count))
        self.assertEqual((), receipt.record_digests)

    def test_public_admission_fails_closed_without_source_owned_records(self):
        reproduction, duplicate, lint, program = self.leaves()
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_FOUR_LEAF_REGISTRY_REQUIRED"):
            admit_registered_candidate_evidence_trust(reproduction=reproduction, duplicate=duplicate, report_lint=lint, program=program)

    def test_exact_four_leaf_fixture_reaches_review_evidence_only(self):
        receipt = self.compose()
        self.assertTrue(receipt.candidate_evidence_trust_proven)
        self.assertTrue(receipt.ready_for_human_review_evidence)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.external_effect)

    def test_reproduction_is_not_trusted_by_shape(self):
        reproduction = self.reproduction()
        wrong = self.record(DUPLICATE_PLANE, reproduction)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
            _resolve_leaf_from_records(records=(wrong,), leaf=reproduction)

    def test_one_leaf_cannot_authenticate_another(self):
        reproduction, duplicate, _, _ = self.leaves()
        record = self.record(REPRODUCTION_PLANE, reproduction)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CHECK_REGISTRY_REQUIRED"):
            _resolve_leaf_from_records(records=(record,), leaf=duplicate)

    def test_duplicate_currentness_change_reopens_only_duplicate_leaf(self):
        leaves = self.leaves()
        records = self.records(leaves)
        changed_duplicate = replace(leaves[1], duplicate_check_currentness_ref="dup-current-2")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CHECK_REGISTRY_REQUIRED"):
            _resolve_leaf_from_records(records=records, leaf=changed_duplicate)
        for index in (0, 2, 3):
            self.assertEqual(records[index].record_digest, _resolve_leaf_from_records(records=records, leaf=leaves[index]).record_digest)

    def test_each_record_has_independent_lifecycle(self):
        leaves = self.leaves()
        records = self.records(leaves)
        stale = (records[0], replace(records[1], revoked=True), records[2], records[3])
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CHECK_REGISTRY_REVOKED"):
            _resolve_leaf_from_records(records=stale, leaf=leaves[1])
        self.assertEqual(records[0].record_digest, _resolve_leaf_from_records(records=stale, leaf=leaves[0]).record_digest)
        self.assertEqual(records[2].record_digest, _resolve_leaf_from_records(records=stale, leaf=leaves[2]).record_digest)
        self.assertEqual(records[3].record_digest, _resolve_leaf_from_records(records=stale, leaf=leaves[3]).record_digest)

    def test_cross_subject_and_effect_state_fail_closed(self):
        reproduction, duplicate, lint, program = self.leaves()
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_LEAF_SUBJECT_MISMATCH"):
            self.compose((reproduction, replace(duplicate, candidate_id="other"), lint, program))
        with self.assertRaisesRegex(ValueError, "REPRODUCTION_EVIDENCE_EXTERNAL_EFFECT_FORBIDDEN"):
            self.compose((replace(reproduction, external_effect=True), duplicate, lint, program))

    def test_receipt_is_deterministic(self):
        self.assertEqual(self.compose().receipt_digest, self.compose().receipt_digest)


if __name__ == "__main__":
    unittest.main()
