from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from tests import test_bughound_candidate_evidence_trust_join as fixtures
from tools.bughound import candidate_evidence_trust_join as leaf_registry
from tools.bughound import registered_reproduction_gate as repro_registry
from tools.bughound.cash_scheduler import CashBountyWorkStateV1, schedule_next_cash_bounty_step
from tools.bughound.four_leaf_human_review import (
    compile_four_leaf_cash_human_review_packet,
    four_leaf_human_review_parameter_names,
)
from tools.bughound.registered_reproduction_gate import registered_reproduction_parameter_names


class FourLeafHumanReviewV2Tests(unittest.TestCase):
    def f(self):
        return fixtures.CandidateEvidenceTrustJoinTests()

    def scheduler(self, *, gaps=(), **changes):
        f = self.f()
        decision = schedule_next_cash_bounty_step(
            mission_input=f.mission(),
            work_state=CashBountyWorkStateV1(
                work_item_id="work-1",
                unresolved_gaps=tuple(gaps),
                duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
                probe_budget_minutes=60,
                active_probe_minutes=10,
                survivor_state="REPRODUCED_SURVIVOR",
                source_generation="repo-gen-1",
                currentness_ref="source-v1",
            ),
        )
        return replace(decision, **changes) if changes else decision

    def call(self, *, duplicate=None, report_lint=None, program=None, scheduler=None):
        f = self.f()
        return compile_four_leaf_cash_human_review_packet(
            mission_input=f.mission(),
            candidate=f.candidate(),
            independent_reproduction=f.reproduction(),
            duplicate=duplicate or f.duplicate(),
            report_lint=report_lint or f.report_lint(),
            program=program or f.program(),
            scheduler_decision=scheduler or self.scheduler(),
        )

    def exact_private_path(self, *, duplicate=None, report_lint=None, program=None, records=None, repro_record=None, scheduler=None):
        f = self.f()
        duplicate = duplicate or f.duplicate()
        report_lint = report_lint or f.report_lint()
        program = program or f.program()
        records = records or f.leaf_records(duplicate, report_lint, program)
        repro_record = repro_record or f.reproduction_record()
        with patch.object(repro_registry, "_CANONICAL_REPRODUCTION_RECORDS", (repro_record,)), patch.object(
            leaf_registry, "_CANONICAL_LEAF_RECORDS", records
        ):
            return self.call(
                duplicate=duplicate,
                report_lint=report_lint,
                program=program,
                scheduler=scheduler,
            )

    def reproduction_prerequisite_only(self):
        return patch.object(
            repro_registry,
            "_CANONICAL_REPRODUCTION_RECORDS",
            (self.f().reproduction_record(),),
        )

    def test_public_human_review_abi_is_raw_and_has_no_trust_shortcut(self):
        self.assertEqual(
            {
                "mission_input", "candidate", "independent_reproduction",
                "duplicate", "report_lint", "program", "scheduler_decision",
            },
            set(four_leaf_human_review_parameter_names()),
        )
        forbidden = {
            "candidate_receipt", "producer_receipt", "join_receipt", "registry",
            "registry_lookup", "record", "records", "trusted", "producer_secret",
            "expected_producer_ref", "expected_producer_generation",
            "reproduction_admission", "registered_reproduction_admission",
        }
        self.assertTrue(forbidden.isdisjoint(four_leaf_human_review_parameter_names()))

    def test_reproduction_public_abi_has_no_registry_override(self):
        forbidden = {
            "registry_lookup", "registry", "records", "record",
            "expected_independent_reproduction_digest", "expected_reproducer_ref",
            "expected_reproducer_generation", "trusted",
        }
        self.assertTrue(forbidden.isdisjoint(registered_reproduction_parameter_names()))

    def test_production_hold_precedes_downstream_leaf_diagnosis(self):
        f = self.f()
        cases = (
            dict(duplicate=replace(f.duplicate(), duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE")),
            dict(report_lint=replace(f.report_lint(), report_lint_state="REPORT_LINT_DIRTY")),
            dict(program=replace(f.program(), program_admissibility_state="NOT_ADMISSIBLE")),
        )
        for kwargs in cases:
            with self.subTest(kwargs=tuple(kwargs)):
                with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
                    self.call(**kwargs)

    def test_downstream_duplicate_is_reachable_after_private_reproduction_prerequisite(self):
        duplicate = replace(self.f().duplicate(), duplicate_pressure_state="PUBLICLY_KNOWN_ROOT_CAUSE")
        with self.reproduction_prerequisite_only():
            with self.assertRaisesRegex(ValueError, "PUBLIC_ROOT_CAUSE_ALREADY_KNOWN"):
                self.call(duplicate=duplicate)

    def test_downstream_lint_and_program_are_reachable_after_private_reproduction_prerequisite(self):
        with self.reproduction_prerequisite_only():
            with self.assertRaisesRegex(ValueError, "REPORT_LINT_REQUIRED"):
                self.call(report_lint=replace(self.f().report_lint(), report_lint_state="REPORT_LINT_DIRTY"))
        with self.reproduction_prerequisite_only():
            with self.assertRaisesRegex(ValueError, "PROGRAM_ADMISSIBILITY_REQUIRED"):
                self.call(program=replace(self.f().program(), program_admissibility_state="NOT_ADMISSIBLE"))

    def test_reproduction_record_without_leaf_records_still_holds(self):
        with self.reproduction_prerequisite_only():
            with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
                self.call()

    def test_exact_private_four_leaf_path_reaches_human_review_only(self):
        packet = self.exact_private_path()
        self.assertTrue(packet.ready_for_human_review)
        self.assertTrue(packet.candidate_evidence_trust_proven)
        self.assertTrue(packet.independent_reproduction_registry_proven)
        self.assertTrue(packet.duplicate_check_producer_proven)
        self.assertTrue(packet.report_lint_producer_proven)
        self.assertTrue(packet.program_admissibility_producer_proven)
        self.assertFalse(packet.human_authorization_verified)
        self.assertFalse(packet.live_target_testing_authorized)
        self.assertFalse(packet.credential_use_authorized)
        self.assertFalse(packet.submission_authorized)
        self.assertFalse(packet.claim_or_payment_authorized)
        self.assertFalse(packet.authority)
        self.assertFalse(packet.external_effect)

    def test_mutated_leaf_same_producer_cannot_cross_human_boundary(self):
        f = self.f()
        cases = (
            ("duplicate", replace(f.duplicate(), duplicate_check_currentness_ref="dup-current-2"), f.leaf_records(), "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"),
            ("report_lint", replace(f.report_lint(), lint_policy_generation="lint-policy-2"), f.leaf_records(), "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"),
            ("program", replace(f.program(), program_admissibility_ref="program-current-2"), f.leaf_records(), "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"),
        )
        for field, changed, records, code in cases:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, code):
                    self.exact_private_path(records=records, **{field: changed})

    def test_stale_leaf_record_cannot_be_hidden_by_current_reproduction(self):
        f = self.f()
        records = list(f.leaf_records())
        records[0] = replace(records[0], current=False)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_STALE"):
            self.exact_private_path(records=tuple(records))

    def test_scheduler_must_be_at_human_gate(self):
        scheduler = self.scheduler(gaps=("G_DUPLICATE",))
        with self.assertRaisesRegex(ValueError, "BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE"):
            self.exact_private_path(scheduler=scheduler)

    def test_scheduler_effect_authority_widening_fails(self):
        scheduler = self.scheduler(external_effect=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_EXTERNAL_EFFECT_MUST_BE_FALSE"):
            self.exact_private_path(scheduler=scheduler)

    def test_program_mission_binding_is_reachable_after_reproduction_prerequisite(self):
        f = self.f()
        cases = (
            ("scope_rules_digest", "scope-other", "PROGRAM_SCOPE_MISSION_SCOPE_MISMATCH"),
            ("payout_rules_digest", "payout-other", "PROGRAM_PAYOUT_MISSION_PAYOUT_MISMATCH"),
            ("source_currentness_ref", "source-other", "PROGRAM_SOURCE_MISSION_SOURCE_MISMATCH"),
        )
        for field, value, code in cases:
            with self.subTest(field=field):
                with self.reproduction_prerequisite_only():
                    with self.assertRaisesRegex(ValueError, code):
                        self.call(program=replace(f.program(), **{field: value}))

    def test_packet_digest_is_deterministic_under_same_private_state(self):
        self.assertEqual(self.exact_private_path().packet_digest, self.exact_private_path().packet_digest)


if __name__ == "__main__":
    unittest.main()
