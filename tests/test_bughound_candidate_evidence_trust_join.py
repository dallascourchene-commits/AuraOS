from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch
import unittest

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound import registered_reproduction_gate as repro_gate
from tools.bughound import candidate_evidence_trust_join as g


class CandidateEvidenceTrustJoinTests(unittest.TestCase):
    def mission(self):
        return BugHoundCashMissionInputV1(
            profile_id="BUGHOUND_CASH_BOUNTY_V1",
            program_ref="program://cash",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            program_state="ACTIVE",
            cash_reward_state="VERIFIED_CURRENT_CASH_REWARD",
            reward_currency="USD",
            reward_floor_minor=10000,
            reward_ceiling_minor=50000,
            payout_rules_digest="payout-v1",
            scope_state="CURRENT_SCOPE_BOUND",
            scope_rules_digest="scope-v1",
            source_state="CURRENT_SOURCE_BOUND",
            source_currentness_ref="source-v1",
            testing_ceiling="PUBLIC_SOURCE_AND_LOCAL_AUTHORIZED_ONLY",
        )

    def candidate(self):
        return BountyCandidateEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            security_invariant_digest="inv-1",
            causal_cone_digest="cone-1",
            discovery_receipt_digest="disc-1",
            discovery_reproduction_state="REPRODUCED_CURRENT",
            claimed_consequence_band="CONSERVATIVE_MEDIUM",
        )

    def reproduction(self):
        return IndependentBountyReproductionReceiptV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproducer_ref="reproducer://independent-1",
            reproducer_generation="repro-gen-1",
            result="REPRODUCED_CURRENT",
            witness_digest="witness-1",
            environment_digest="env-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
        )

    def reproduction_record(self):
        repro = self.reproduction()
        return repro_gate.BugHoundIndependentReproductionRegistryRecordV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            reproduction_receipt_digest=repro.receipt_digest,
            reproducer_ref=repro.reproducer_ref,
            reproducer_generation=repro.reproducer_generation,
            witness_digest=repro.witness_digest,
            environment_digest=repro.environment_digest,
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
            registry_receipt_ref="registry://repro/current",
            registry_observer_ref="observer://repro/independent",
            registry_observer_generation="observer-gen-1",
            registry_current=True,
            independently_observed=True,
        )

    def duplicate(self):
        return g.DuplicateCheckEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            producer_ref="producer://duplicate-independent",
            producer_generation="dup-producer-gen-1",
            producer_currentness_ref="dup-producer-current-1",
        )

    def report_lint(self):
        return g.ReportLintEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            lint_policy_generation="lint-policy-1",
            producer_ref="producer://lint-independent",
            producer_generation="lint-producer-gen-1",
            producer_currentness_ref="lint-producer-current-1",
        )

    def program(self):
        return g.ProgramAdmissibilityEvidenceV1(
            candidate_id="candidate-1",
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-current-1",
            scope_rules_digest="scope-v1",
            payout_rules_digest="payout-v1",
            source_currentness_ref="source-v1",
            producer_ref="producer://program-independent",
            producer_generation="program-producer-gen-1",
            producer_currentness_ref="program-producer-current-1",
        )

    def record(self, plane, leaf):
        return g.CandidateLeafProducerRecordV1(
            proof_plane=plane,
            artifact_digest=leaf.artifact_digest,
            candidate_id=leaf.candidate_id,
            target_ref=leaf.target_ref,
            target_generation=leaf.target_generation,
            producer_ref=leaf.producer_ref,
            producer_generation=leaf.producer_generation,
            producer_currentness_ref=leaf.producer_currentness_ref,
            registry_receipt_ref=f"registry://{plane.lower()}/current",
            registry_observer_ref=f"observer://{plane.lower()}/independent",
            registry_observer_generation="observer-gen-1",
            registry_currentness_ref="registry-current-1",
        )

    def leaf_records(self, duplicate=None, report_lint=None, program=None):
        duplicate = duplicate or self.duplicate()
        report_lint = report_lint or self.report_lint()
        program = program or self.program()
        return (
            self.record(g.DUPLICATE_PLANE, duplicate),
            self.record(g.REPORT_LINT_PLANE, report_lint),
            self.record(g.PROGRAM_PLANE, program),
        )

    def kwargs(self, duplicate=None, report_lint=None, program=None):
        return dict(
            mission_input=self.mission(),
            candidate=self.candidate(),
            independent_reproduction=self.reproduction(),
            duplicate=duplicate or self.duplicate(),
            report_lint=report_lint or self.report_lint(),
            program=program or self.program(),
        )

    def public_admit(self, *, duplicate=None, report_lint=None, program=None, records=None):
        duplicate = duplicate or self.duplicate()
        report_lint = report_lint or self.report_lint()
        program = program or self.program()
        records = records or self.leaf_records(duplicate, report_lint, program)
        with patch.object(
            repro_gate,
            "_CANONICAL_REPRODUCTION_RECORDS",
            (self.reproduction_record(),),
        ), patch.object(g, "_CANONICAL_LEAF_RECORDS", records):
            return g.admit_registered_candidate_evidence_trust(
                **self.kwargs(duplicate, report_lint, program)
            )

    def test_exact_four_leaf_public_path_reaches_evidence_boundary_only(self):
        out = self.public_admit()
        self.assertTrue(out.independent_reproduction_registry_proven)
        self.assertTrue(out.duplicate_check_producer_proven)
        self.assertTrue(out.report_lint_producer_proven)
        self.assertTrue(out.program_admissibility_producer_proven)
        self.assertTrue(out.candidate_evidence_trust_proven)
        self.assertTrue(out.ready_for_human_review_evidence)
        self.assertFalse(out.human_authorization_verified)
        self.assertFalse(out.ready_for_human_review)
        self.assertFalse(out.live_target_testing_authorized)
        self.assertFalse(out.credential_use_authorized)
        self.assertFalse(out.submission_authorized)
        self.assertFalse(out.claim_or_payment_authorized)
        self.assertFalse(out.authority)
        self.assertFalse(out.external_effect)

    def test_production_registries_are_empty_and_fail_closed(self):
        repro_receipt = repro_gate.independent_reproduction_registry_receipt()
        leaf_receipt = g.candidate_leaf_registry_receipt()
        self.assertEqual(0, repro_receipt.active_record_count)
        self.assertEqual((), leaf_receipt.record_digests)
        self.assertEqual(0, leaf_receipt.duplicate_record_count)
        self.assertEqual(0, leaf_receipt.report_lint_record_count)
        self.assertEqual(0, leaf_receipt.program_record_count)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
            g.admit_registered_candidate_evidence_trust(**self.kwargs())

    def test_reproduction_only_does_not_preclaim_other_leaves(self):
        with patch.object(
            repro_gate,
            "_CANONICAL_REPRODUCTION_RECORDS",
            (self.reproduction_record(),),
        ):
            with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
                g.admit_registered_candidate_evidence_trust(**self.kwargs())

    def test_public_signature_has_no_caller_trust_root_or_prebuilt_admission(self):
        params = set(g.candidate_evidence_trust_parameter_names())
        for forbidden in (
            "registry", "registry_lookup", "records", "record", "trusted",
            "expected_producer", "producer_secret", "verifier_secret",
            "reproduction_admission", "registered_reproduction_admission",
        ):
            self.assertNotIn(forbidden, params)
        self.assertEqual(
            {"mission_input", "candidate", "independent_reproduction", "duplicate", "report_lint", "program"},
            params,
        )

    def test_caller_registry_or_prebuilt_admission_arguments_are_rejected(self):
        for field, value in (
            ("registry_lookup", lambda _: None),
            ("records", self.leaf_records()),
            ("record", self.leaf_records()[0]),
            ("reproduction_admission", object()),
        ):
            with self.subTest(field=field):
                with self.assertRaises(TypeError):
                    g.admit_registered_candidate_evidence_trust(
                        **self.kwargs(), **{field: value}
                    )

    def test_same_producer_different_duplicate_artifact_fails(self):
        changed = replace(self.duplicate(), duplicate_check_currentness_ref="dup-current-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.public_admit(duplicate=changed, records=self.leaf_records())

    def test_same_producer_different_lint_artifact_fails(self):
        changed = replace(self.report_lint(), lint_policy_generation="lint-policy-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.public_admit(report_lint=changed, records=self.leaf_records())

    def test_same_producer_different_program_artifact_fails(self):
        changed = replace(self.program(), program_admissibility_ref="program-current-2")
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.public_admit(program=changed, records=self.leaf_records())

    def test_cross_plane_record_cannot_authenticate_artifact(self):
        records = list(self.leaf_records())
        records[0] = replace(records[0], proof_plane=g.REPORT_LINT_PLANE)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.public_admit(records=tuple(records))

    def test_stale_nonindependent_revoked_or_effect_widened_record_fails(self):
        originals = self.leaf_records()
        mutations = (
            ("current", False, "REGISTRY_STALE"),
            ("independently_observed", False, "INDEPENDENT_OBSERVER_REQUIRED"),
            ("revoked", True, "REGISTRY_REVOKED"),
            ("authority", True, "AUTHORITY_WIDENED"),
            ("external_effect", True, "EXTERNAL_EFFECT_FORBIDDEN"),
        )
        for field, value, code in mutations:
            with self.subTest(field=field):
                records = (replace(originals[0], **{field: value}),) + originals[1:]
                with self.assertRaisesRegex(ValueError, code):
                    self.public_admit(records=records)

    def test_subject_substitution_fails_before_registry(self):
        changed = replace(self.duplicate(), candidate_id="candidate-other")
        with self.assertRaisesRegex(ValueError, "LEAF_SUBJECT_MISMATCH"):
            self.public_admit(duplicate=changed)

    def test_duplicate_high_public_or_unknown_states_fail(self):
        for state, code in (
            ("HIGH_DUPLICATE_PRESSURE", "MANUAL_DUPLICATE_REVIEW_REQUIRED"),
            ("PUBLICLY_KNOWN_ROOT_CAUSE", "PUBLIC_ROOT_CAUSE_ALREADY_KNOWN"),
            ("UNKNOWN", "DUPLICATE_PRESSURE_UNRESOLVED"),
        ):
            with self.subTest(state=state):
                changed = replace(self.duplicate(), duplicate_pressure_state=state)
                with self.assertRaisesRegex(ValueError, code):
                    self.public_admit(duplicate=changed)

    def test_dirty_report_lint_fails(self):
        changed = replace(self.report_lint(), report_lint_state="REPORT_LINT_DIRTY")
        with self.assertRaisesRegex(ValueError, "REPORT_LINT_REQUIRED"):
            self.public_admit(report_lint=changed)

    def test_program_not_admissible_fails(self):
        changed = replace(self.program(), program_admissibility_state="NOT_ADMISSIBLE")
        with self.assertRaisesRegex(ValueError, "PROGRAM_ADMISSIBILITY_REQUIRED"):
            self.public_admit(program=changed)

    def test_program_scope_payout_and_source_are_mission_bound(self):
        for field, value, code in (
            ("scope_rules_digest", "other", "PROGRAM_SCOPE_MISSION_SCOPE_MISMATCH"),
            ("payout_rules_digest", "other", "PROGRAM_PAYOUT_MISSION_PAYOUT_MISMATCH"),
            ("source_currentness_ref", "other", "PROGRAM_SOURCE_MISSION_SOURCE_MISMATCH"),
        ):
            with self.subTest(field=field):
                changed = replace(self.program(), **{field: value})
                with self.assertRaisesRegex(ValueError, code):
                    self.public_admit(program=changed)

    def test_leaf_authority_or_external_effect_widening_fails(self):
        for field in ("authority", "external_effect"):
            with self.subTest(field=field):
                changed = replace(self.duplicate(), **{field: True})
                with self.assertRaises(ValueError):
                    self.public_admit(duplicate=changed)

    def test_output_is_deterministic_for_same_four_exact_leaves(self):
        self.assertEqual(self.public_admit().receipt_digest, self.public_admit().receipt_digest)


if __name__ == "__main__":
    unittest.main()
