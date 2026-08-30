from __future__ import annotations

from dataclasses import replace
import unittest

import tools.bughound.registered_reproduction_gate as gate
from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1


class ReproductionRegistryIndependenceTests(unittest.TestCase):
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

    def repro(self):
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

    def record(self, repro=None):
        repro = repro or self.repro()
        return gate.BugHoundIndependentReproductionRegistryRecordV1(
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
            registry_receipt_ref="registry://receipt/current",
            registry_observer_ref="registry://observer/independent",
            registry_observer_generation="registry-gen-1",
            registry_current=True,
            independently_observed=True,
        )

    def private_admit(self, record):
        return gate._compose_registered_independent_reproduction(
            mission_input=self.mission(),
            candidate=self.candidate(),
            independent_reproduction=self.repro(),
            duplicate_pressure_state="LOW_OBSERVED_DUPLICATE_PRESSURE",
            duplicate_check_currentness_ref="dup-current-1",
            report_lint_state="REPORT_LINT_CLEAN",
            report_digest="report-1",
            program_admissibility_state="CURRENTLY_ADMISSIBLE",
            program_admissibility_ref="program-current-1",
            record=record,
        )

    def with_canonical_records(self, records, fn):
        prior = gate._CANONICAL_REPRODUCTION_RECORDS
        gate._CANONICAL_REPRODUCTION_RECORDS = tuple(records)
        try:
            return fn()
        finally:
            gate._CANONICAL_REPRODUCTION_RECORDS = prior

    def test_same_reproducer_and_registry_observer_is_not_independent(self):
        repro = self.repro()
        record = replace(self.record(repro), registry_observer_ref=repro.reproducer_ref)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED"):
            self.private_admit(record)

    def test_same_observer_ref_different_generation_is_still_not_independent(self):
        repro = self.repro()
        record = replace(
            self.record(repro),
            registry_observer_ref=repro.reproducer_ref,
            registry_observer_generation="nominally-different-generation",
        )
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED"):
            self.private_admit(record)

    def test_valid_distinct_observer_still_admits_private_fixture(self):
        out = self.private_admit(self.record())
        self.assertTrue(out.independent_reproduction_registry_proven)
        self.assertFalse(out.external_effect)
        self.assertFalse(out.submission_authorized)

    def test_registry_receipt_validates_record_schema_before_counting(self):
        record = replace(self.record(), schema="WrongSchema")
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_SCHEMA_MISMATCH"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_registry_receipt_rejects_truthy_non_boolean_currentness(self):
        record = replace(self.record(), registry_current=1)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REGISTRY_CURRENT_BOOL_REQUIRED"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_registry_receipt_rejects_truthy_non_boolean_independence(self):
        record = replace(self.record(), independently_observed=1)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_INDEPENDENTLY_OBSERVED_BOOL_REQUIRED"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_registry_receipt_rejects_truthy_non_boolean_revocation(self):
        record = replace(self.record(), revoked=0)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_REVOKED_BOOL_REQUIRED"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_registry_receipt_rejects_effect_authority_widening(self):
        record = replace(self.record(), submission_authorized=True)
        with self.assertRaisesRegex(ValueError, "REPRO_REGISTRY_SUBMISSION_AUTHORITY_FORBIDDEN"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_registry_receipt_rejects_same_principal_observer(self):
        repro = self.repro()
        record = replace(self.record(repro), registry_observer_ref=repro.reproducer_ref)
        with self.assertRaisesRegex(ValueError, "INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED"):
            self.with_canonical_records((record,), gate.independent_reproduction_registry_receipt)

    def test_stale_well_formed_record_is_retained_but_not_active(self):
        receipt = self.with_canonical_records(
            (replace(self.record(), registry_current=False),),
            gate.independent_reproduction_registry_receipt,
        )
        self.assertEqual(1, len(receipt.record_digests))
        self.assertEqual(0, receipt.active_record_count)

    def test_unobserved_well_formed_record_is_retained_but_not_active(self):
        receipt = self.with_canonical_records(
            (replace(self.record(), independently_observed=False),),
            gate.independent_reproduction_registry_receipt,
        )
        self.assertEqual(1, len(receipt.record_digests))
        self.assertEqual(0, receipt.active_record_count)

    def test_revoked_well_formed_record_is_retained_but_not_active(self):
        receipt = self.with_canonical_records(
            (replace(self.record(), revoked=True),),
            gate.independent_reproduction_registry_receipt,
        )
        self.assertEqual(1, len(receipt.record_digests))
        self.assertEqual(0, receipt.active_record_count)

    def test_active_count_requires_valid_distinct_observer_record(self):
        receipt = self.with_canonical_records(
            (self.record(),), gate.independent_reproduction_registry_receipt
        )
        self.assertEqual(1, receipt.active_record_count)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)


if __name__ == "__main__":
    unittest.main()
