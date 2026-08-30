from dataclasses import replace
import inspect
import unittest

from tools.bughound.candidate_evidence_trust_join import (
    DUPLICATE_PLANE,
    PROGRAM_PLANE,
    REPORT_LINT_PLANE,
    CandidateEvidenceProducerRecordV1,
    DuplicateEvidenceV1,
    ProgramAdmissibilityEvidenceV1,
    RegisteredReproductionAdmissionV1,
    ReportLintEvidenceV1,
    _compose_with_records,
    admit_registered_candidate_evidence_trust,
    candidate_evidence_leaf_registry_receipt,
    candidate_evidence_trust_parameter_names,
)


class CandidateEvidenceTrustJoinTests(unittest.TestCase):
    def reproduction(self, **changes):
        values = dict(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproduction_receipt_digest="repro-receipt-1",
            reproducer_ref="reproducer://independent-1",
            reproducer_generation="repro-gen-1",
            witness_digest="witness-1",
            environment_digest="env-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-current-1",
            registry_record_digest="repro-registry-record-1",
            registry_receipt_ref="registry://reproduction/1",
            registry_observer_ref="observer://reproduction/1",
            registry_observer_generation="observer-gen-1",
            registry_currentness_ref="repro-registry-current-1",
        )
        values.update(changes)
        return RegisteredReproductionAdmissionV1(**values)

    def duplicate(self, **changes):
        values = dict(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            publicly_known_root_cause=False,
            producer_ref="producer://duplicate/1",
            producer_generation="dup-gen-1",
            producer_currentness_ref="dup-producer-current-1",
        )
        values.update(changes)
        return DuplicateEvidenceV1(**values)

    def lint(self, **changes):
        values = dict(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            lint_policy_generation="lint-policy-gen-1",
            producer_ref="producer://lint/1",
            producer_generation="lint-gen-1",
            producer_currentness_ref="lint-producer-current-1",
        )
        values.update(changes)
        return ReportLintEvidenceV1(**values)

    def program(self, **changes):
        values = dict(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-admission-1",
            scope_rules_digest="scope-v1",
            payout_rules_digest="payout-v1",
            source_currentness_ref="source-current-1",
            producer_ref="producer://program/1",
            producer_generation="program-gen-1",
            producer_currentness_ref="program-producer-current-1",
        )
        values.update(changes)
        return ProgramAdmissibilityEvidenceV1(**values)

    def record(self, plane, leaf, **changes):
        values = dict(
            proof_plane=plane,
            artifact_digest=leaf.artifact_digest,
            candidate_id=leaf.candidate_id,
            target_ref=leaf.target_ref,
            target_generation=leaf.target_generation,
            producer_ref=leaf.producer_ref,
            producer_generation=leaf.producer_generation,
            producer_currentness_ref=leaf.producer_currentness_ref,
            registry_receipt_ref=f"registry://{plane.lower()}/1",
            registry_observer_ref=f"observer://{plane.lower()}/1",
            registry_observer_generation="observer-gen-1",
            registry_currentness_ref="registry-current-1",
        )
        values.update(changes)
        return CandidateEvidenceProducerRecordV1(**values)

    def records(self, duplicate=None, lint=None, program=None):
        duplicate = duplicate or self.duplicate()
        lint = lint or self.lint()
        program = program or self.program()
        return (
            self.record(DUPLICATE_PLANE, duplicate),
            self.record(REPORT_LINT_PLANE, lint),
            self.record(PROGRAM_PLANE, program),
        )

    def compose(self, *, reproduction=None, duplicate=None, lint=None, program=None, records=None):
        reproduction = reproduction or self.reproduction()
        duplicate = duplicate or self.duplicate()
        lint = lint or self.lint()
        program = program or self.program()
        return _compose_with_records(
            reproduction=reproduction,
            duplicate=duplicate,
            report_lint=lint,
            program=program,
            records=records or self.records(duplicate, lint, program),
        )

    def test_public_api_has_only_four_evidence_leaves(self):
        self.assertEqual(
            {"reproduction", "duplicate", "report_lint", "program"},
            set(candidate_evidence_trust_parameter_names()),
        )
        for forbidden in (
            "registry",
            "registry_lookup",
            "records",
            "producer_secret",
            "verifier_held_producer_secret",
            "expected_producer_ref",
            "expected_producer_generation",
            "expected_bundle_digest",
            "trusted",
        ):
            self.assertNotIn(forbidden, inspect.signature(admit_registered_candidate_evidence_trust).parameters)

    def test_production_leaf_registry_is_empty_hold(self):
        registry = candidate_evidence_leaf_registry_receipt()
        self.assertEqual((), registry.record_digests)
        self.assertEqual(0, registry.duplicate_record_count)
        self.assertEqual(0, registry.lint_record_count)
        self.assertEqual(0, registry.program_record_count)
        self.assertFalse(registry.authority)
        self.assertFalse(registry.external_effect)

    def test_production_admission_fails_closed_without_leaf_records(self):
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            admit_registered_candidate_evidence_trust(
                reproduction=self.reproduction(),
                duplicate=self.duplicate(),
                report_lint=self.lint(),
                program=self.program(),
            )

    def test_exact_four_leaf_private_fixture_reaches_human_review_evidence_only(self):
        receipt = self.compose()
        self.assertTrue(receipt.independent_reproduction_registry_proven)
        self.assertTrue(receipt.duplicate_check_producer_proven)
        self.assertTrue(receipt.report_lint_producer_proven)
        self.assertTrue(receipt.program_admissibility_producer_proven)
        self.assertTrue(receipt.candidate_evidence_trust_proven)
        self.assertTrue(receipt.ready_for_human_review_evidence)
        self.assertFalse(receipt.live_target_testing_authorized)
        self.assertFalse(receipt.credential_use_authorized)
        self.assertFalse(receipt.submission_authorized)
        self.assertFalse(receipt.claim_or_payment_authorized)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)

    def test_mutated_duplicate_same_producer_identity_fails(self):
        original = self.duplicate()
        mutated = replace(original, duplicate_check_currentness_ref="dup-current-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.compose(duplicate=mutated, records=self.records(original, self.lint(), self.program()))

    def test_mutated_lint_same_producer_identity_fails(self):
        original = self.lint()
        mutated = replace(original, report_digest="report-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.compose(lint=mutated, records=self.records(self.duplicate(), original, self.program()))

    def test_mutated_program_same_producer_identity_fails(self):
        original = self.program()
        mutated = replace(original, program_admissibility_ref="program-admission-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.compose(program=mutated, records=self.records(self.duplicate(), self.lint(), original))

    def test_reproduction_cannot_preclaim_other_producer_leaves(self):
        for field in (
            "duplicate_check_producer_proven",
            "report_lint_producer_proven",
            "program_admissibility_producer_proven",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "REPRODUCTION_CANNOT_PRECLAIM_OTHER_PROOF_LEAVES"):
                    self.compose(reproduction=replace(self.reproduction(), **{field: True}))

    def test_cross_candidate_target_or_generation_fails(self):
        for leaf_name, leaf in (
            ("duplicate", replace(self.duplicate(), candidate_id="candidate-other")),
            ("lint", replace(self.lint(), target_ref="target://other")),
            ("program", replace(self.program(), target_generation="repo-gen-2")),
        ):
            with self.subTest(leaf=leaf_name):
                kwargs = {leaf_name: leaf}
                with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_LEAF_SUBJECT_MISMATCH"):
                    self.compose(**kwargs)

    def test_duplicate_public_known_high_or_unknown_blocks(self):
        cases = (
            (replace(self.duplicate(), publicly_known_root_cause=True), "PUBLIC_ROOT_CAUSE_ALREADY_KNOWN"),
            (replace(self.duplicate(), duplicate_pressure_state="HIGH_DUPLICATE_PRESSURE"), "MANUAL_DUPLICATE_REVIEW_REQUIRED"),
            (replace(self.duplicate(), duplicate_pressure_state="UNKNOWN"), "DUPLICATE_PRESSURE_UNRESOLVED"),
        )
        for duplicate, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, code):
                    self.compose(duplicate=duplicate)

    def test_unclean_lint_and_nonadmissible_program_block(self):
        with self.assertRaisesRegex(ValueError, "REPORT_LINT_REQUIRED"):
            self.compose(lint=replace(self.lint(), report_lint_state="REPORT_LINT_DIRTY"))
        with self.assertRaisesRegex(ValueError, "PROGRAM_ADMISSIBILITY_REQUIRED"):
            self.compose(program=replace(self.program(), program_admissibility_state="STALE"))

    def test_program_scope_and_source_must_match_reproduction(self):
        with self.assertRaisesRegex(ValueError, "PROGRAM_SCOPE_REPRODUCTION_SCOPE_MISMATCH"):
            self.compose(program=replace(self.program(), scope_rules_digest="scope-other"))
        with self.assertRaisesRegex(ValueError, "PROGRAM_SOURCE_REPRODUCTION_SOURCE_MISMATCH"):
            self.compose(program=replace(self.program(), source_currentness_ref="source-other"))

    def test_stale_revoked_unobserved_or_effectful_record_fails(self):
        duplicate = self.duplicate()
        base = self.records(duplicate, self.lint(), self.program())
        changes = (
            ({"current": False}, "CANDIDATE_EVIDENCE_REGISTRY_STALE"),
            ({"revoked": True}, "CANDIDATE_EVIDENCE_REGISTRY_REVOKED"),
            ({"independently_observed": False}, "CANDIDATE_EVIDENCE_INDEPENDENT_OBSERVER_REQUIRED"),
            ({"authority": True}, "CANDIDATE_EVIDENCE_REGISTRY_RECORD_AUTHORITY_WIDENED"),
            ({"external_effect": True}, "CANDIDATE_EVIDENCE_REGISTRY_RECORD_EXTERNAL_EFFECT_FORBIDDEN"),
        )
        for patch, code in changes:
            records = (replace(base[0], **patch), base[1], base[2])
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, code):
                    self.compose(records=records)

    def test_effectful_leaf_fails_before_registry_join(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EVIDENCE_EXTERNAL_EFFECT_FORBIDDEN"):
            self.compose(duplicate=replace(self.duplicate(), external_effect=True))
        with self.assertRaisesRegex(ValueError, "REPORT_LINT_EVIDENCE_AUTHORITY_WIDENED"):
            self.compose(lint=replace(self.lint(), authority=True))

    def test_receipt_identity_is_deterministic(self):
        self.assertEqual(self.compose().receipt_digest, self.compose().receipt_digest)

    def test_producer_record_digest_binds_artifact_digest(self):
        duplicate = self.duplicate()
        record = self.record(DUPLICATE_PLANE, duplicate)
        changed = replace(record, artifact_digest="different-artifact")
        self.assertNotEqual(record.record_digest, changed.record_digest)


if __name__ == "__main__":
    unittest.main()
