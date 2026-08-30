from dataclasses import replace
import unittest
from unittest.mock import patch

import tools.bughound.candidate_evidence_trust_join as leaf_registry
import tools.bughound.registered_reproduction_gate as repro_registry
from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.candidate_evidence_trust_join import (
    DUPLICATE_PLANE,
    PROGRAM_PLANE,
    REPORT_LINT_PLANE,
    CandidateEvidenceProducerRecordV1,
    DuplicateEvidenceV1,
    ProgramAdmissibilityEvidenceV1,
    ReportLintEvidenceV1,
)
from tools.bughound.cash_scheduler import CashBountyWorkStateV1, schedule_next_cash_bounty_step
from tools.bughound.four_leaf_human_review import (
    compile_four_leaf_cash_human_review_packet,
    four_leaf_human_review_parameter_names,
)
from tools.bughound.registered_reproduction_gate import (
    BugHoundIndependentReproductionRegistryRecordV1,
    registered_reproduction_parameter_names,
)


class FourLeafHumanReviewTests(unittest.TestCase):
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
            security_invariant_digest="invariant-1",
            causal_cone_digest="cone-1",
            discovery_receipt_digest="discovery-1",
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
            source_currentness_ref="source-v1",
            producer_ref="producer://program/1",
            producer_generation="program-gen-1",
            producer_currentness_ref="program-producer-current-1",
        )
        values.update(changes)
        return ProgramAdmissibilityEvidenceV1(**values)

    def scheduler(self, *, gaps=(), **changes):
        decision = schedule_next_cash_bounty_step(
            mission_input=self.mission(),
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

    def repro_record(self, repro=None):
        repro = repro or self.reproduction()
        return BugHoundIndependentReproductionRegistryRecordV1(
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
            registry_receipt_ref="registry://repro/1",
            registry_observer_ref="observer://repro/1",
            registry_observer_generation="observer-gen-1",
            registry_current=True,
            independently_observed=True,
        )

    def leaf_record(self, plane, leaf, **changes):
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

    def leaf_records(self, duplicate=None, lint=None, program=None):
        duplicate = duplicate or self.duplicate()
        lint = lint or self.lint()
        program = program or self.program()
        return (
            self.leaf_record(DUPLICATE_PLANE, duplicate),
            self.leaf_record(REPORT_LINT_PLANE, lint),
            self.leaf_record(PROGRAM_PLANE, program),
        )

    def call(self, *, candidate=None, reproduction=None, duplicate=None, lint=None, program=None, scheduler=None):
        return compile_four_leaf_cash_human_review_packet(
            mission_input=self.mission(),
            candidate=candidate or self.candidate(),
            independent_reproduction=reproduction or self.reproduction(),
            duplicate=duplicate or self.duplicate(),
            report_lint=lint or self.lint(),
            program=program or self.program(),
            scheduler_decision=scheduler or self.scheduler(),
        )

    def exact_private_path(self, *, duplicate=None, lint=None, program=None, repro_record=None, leaf_records=None, scheduler=None):
        duplicate = duplicate or self.duplicate()
        lint = lint or self.lint()
        program = program or self.program()
        repro_record = repro_record or self.repro_record()
        leaf_records = leaf_records or self.leaf_records(duplicate, lint, program)
        with patch.object(repro_registry, "_CANONICAL_REPRODUCTION_RECORDS", (repro_record,)), patch.object(
            leaf_registry, "_CANONICAL_RECORDS", leaf_records
        ):
            return self.call(duplicate=duplicate, lint=lint, program=program, scheduler=scheduler)

    def test_public_human_review_abi_is_raw_and_has_no_trust_shortcut(self):
        self.assertEqual(
            {
                "mission_input",
                "candidate",
                "independent_reproduction",
                "duplicate",
                "report_lint",
                "program",
                "scheduler_decision",
            },
            set(four_leaf_human_review_parameter_names()),
        )
        for forbidden in (
            "candidate_receipt",
            "producer_receipt",
            "join_receipt",
            "registry",
            "registry_lookup",
            "record",
            "records",
            "trusted",
            "producer_secret",
            "expected_producer_ref",
            "expected_producer_generation",
        ):
            self.assertNotIn(forbidden, four_leaf_human_review_parameter_names())

    def test_reproduction_public_abi_has_no_registry_override(self):
        forbidden = {
            "registry_lookup",
            "registry",
            "records",
            "record",
            "expected_independent_reproduction_digest",
            "expected_reproducer_ref",
            "expected_reproducer_generation",
            "trusted",
        }
        self.assertTrue(forbidden.isdisjoint(registered_reproduction_parameter_names()))

    def test_production_path_fails_at_source_owned_reproduction_hold(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED"):
            self.call()

    def test_reproduction_record_without_leaf_records_still_holds(self):
        with patch.object(repro_registry, "_CANONICAL_REPRODUCTION_RECORDS", (self.repro_record(),)):
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

    def test_mutated_duplicate_same_producer_cannot_cross_human_boundary(self):
        original = self.duplicate()
        mutated = replace(original, duplicate_check_currentness_ref="dup-current-2")
        records = self.leaf_records(original, self.lint(), self.program())
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.exact_private_path(duplicate=mutated, leaf_records=records)

    def test_mutated_lint_same_producer_cannot_cross_human_boundary(self):
        original = self.lint()
        mutated = replace(original, report_digest="report-2")
        records = self.leaf_records(self.duplicate(), original, self.program())
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.exact_private_path(lint=mutated, leaf_records=records)

    def test_mutated_program_same_producer_cannot_cross_human_boundary(self):
        original = self.program()
        mutated = replace(original, program_admissibility_ref="program-2")
        records = self.leaf_records(self.duplicate(), self.lint(), original)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_REQUIRED"):
            self.exact_private_path(program=mutated, leaf_records=records)

    def test_stale_leaf_record_cannot_be_hidden_by_current_reproduction(self):
        duplicate = self.duplicate()
        records = list(self.leaf_records(duplicate, self.lint(), self.program()))
        records[0] = replace(records[0], current=False)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_REGISTRY_STALE"):
            self.exact_private_path(duplicate=duplicate, leaf_records=tuple(records))

    def test_scheduler_must_be_at_human_gate(self):
        scheduler = self.scheduler(gaps=("G_DUPLICATE",))
        with self.assertRaisesRegex(ValueError, "BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE"):
            self.exact_private_path(scheduler=scheduler)

    def test_scheduler_effect_authority_widening_fails(self):
        scheduler = self.scheduler(external_effect=True)
        with self.assertRaisesRegex(ValueError, "BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_EXTERNAL_EFFECT_MUST_BE_FALSE"):
            self.exact_private_path(scheduler=scheduler)

    def test_program_exact_mission_scope_payout_and_source_are_required(self):
        cases = (
            (replace(self.program(), scope_rules_digest="scope-other"), "PROGRAM_SCOPE"),
            (replace(self.program(), payout_rules_digest="payout-other"), "PROGRAM_PAYOUT"),
            (replace(self.program(), source_currentness_ref="source-other"), "PROGRAM_SOURCE"),
        )
        for program, code in cases:
            with self.subTest(code=code):
                with self.assertRaisesRegex(ValueError, f"BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_{code}_MISMATCH"):
                    self.call(program=program)

    def test_public_known_duplicate_never_reaches_human_review(self):
        duplicate = replace(self.duplicate(), publicly_known_root_cause=True)
        with self.assertRaisesRegex(ValueError, "PUBLIC_ROOT_CAUSE_ALREADY_KNOWN"):
            self.call(duplicate=duplicate)

    def test_unclean_lint_and_nonadmissible_program_never_reach_human_review(self):
        with self.assertRaisesRegex(ValueError, "REPORT_LINT_REQUIRED"):
            self.call(lint=replace(self.lint(), report_lint_state="REPORT_LINT_DIRTY"))
        with self.assertRaisesRegex(ValueError, "PROGRAM_ADMISSIBILITY_REQUIRED"):
            self.call(program=replace(self.program(), program_admissibility_state="STALE"))

    def test_packet_digest_is_deterministic_under_same_private_state(self):
        self.assertEqual(self.exact_private_path().packet_digest, self.exact_private_path().packet_digest)


if __name__ == "__main__":
    unittest.main()
