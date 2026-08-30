from __future__ import annotations

from dataclasses import replace
import unittest

from tools.bughound.candidate_evidence_registry import (
    CandidateEvidenceProducerRecordV1,
    _resolve_from_records,
    candidate_evidence_registry_receipt,
    validate_candidate_evidence_producer_record,
)


class CandidateEvidenceRegistryValidationTests(unittest.TestCase):
    def record(self, **changes):
        values = dict(
            producer_ref="producer://candidate-evidence",
            producer_generation="producer-gen-1",
            producer_currentness_ref="producer-current-1",
            evidence_bundle_digest="a" * 64,
            target_ref="target://repo/current",
            target_generation="repo-gen-1",
            scope_rules_digest="scope-v1",
            source_currentness_ref="source-v1",
            independent_reproduction_digest="b" * 64,
            duplicate_check_currentness_ref="dup-current-1",
            report_digest="report-v1",
            program_admissibility_ref="program-admission-v1",
            observer_ref="observer://independent-reviewer",
            observer_generation="observer-gen-1",
            observer_currentness_ref="observer-current-1",
        )
        values.update(changes)
        return CandidateEvidenceProducerRecordV1(**values)

    def resolve(self, records):
        record = self.record()
        return _resolve_from_records(
            records=tuple(records),
            producer_ref=record.producer_ref,
            producer_generation=record.producer_generation,
            producer_currentness_ref=record.producer_currentness_ref,
            evidence_bundle_digest=record.evidence_bundle_digest,
            target_ref=record.target_ref,
            target_generation=record.target_generation,
            scope_rules_digest=record.scope_rules_digest,
            source_currentness_ref=record.source_currentness_ref,
            independent_reproduction_digest=record.independent_reproduction_digest,
            duplicate_check_currentness_ref=record.duplicate_check_currentness_ref,
            report_digest=record.report_digest,
            program_admissibility_ref=record.program_admissibility_ref,
        )

    def test_valid_source_owned_record_self_validates(self):
        record = self.record()
        self.assertEqual(record, validate_candidate_evidence_producer_record(record))

    def test_observer_identity_is_required_for_trust_even_on_legacy_constructible_shape(self):
        with self.assertRaisesRegex(ValueError, "OBSERVER_REF_REQUIRED"):
            validate_candidate_evidence_producer_record(self.record(observer_ref=""))

    def test_observer_must_differ_from_producer(self):
        record = self.record()
        with self.assertRaisesRegex(
            ValueError, "CANDIDATE_EVIDENCE_OBSERVER_MUST_DIFFER_FROM_PRODUCER"
        ):
            validate_candidate_evidence_producer_record(
                replace(record, observer_ref=record.producer_ref)
            )

    def test_record_schema_is_exact(self):
        with self.assertRaisesRegex(ValueError, "CANDIDATE_EVIDENCE_RECORD_SCHEMA_MISMATCH"):
            validate_candidate_evidence_producer_record(
                self.record(schema="CandidateEvidenceProducerRecordV2")
            )

    def test_bundle_and_reproduction_digests_must_be_lowercase_sha256(self):
        for changes, code in (
            ({"evidence_bundle_digest": "not-a-digest"}, "EVIDENCE_BUNDLE_DIGEST_SHA256_REQUIRED"),
            ({"independent_reproduction_digest": "B" * 64}, "INDEPENDENT_REPRODUCTION_DIGEST_SHA256_REQUIRED"),
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, code):
                    validate_candidate_evidence_producer_record(self.record(**changes))

    def test_truthy_integer_cannot_substitute_for_exact_boolean(self):
        with self.assertRaisesRegex(ValueError, "INDEPENDENTLY_OBSERVED_EXACT_BOOL_REQUIRED"):
            validate_candidate_evidence_producer_record(
                self.record(independently_observed=1)
            )

    def test_registry_record_cannot_carry_authority_or_external_effect(self):
        for changes in ({"authority": True}, {"external_effect": True}):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(
                    ValueError, "CANDIDATE_EVIDENCE_RECORD_AUTHORITY_WIDENED"
                ):
                    validate_candidate_evidence_producer_record(self.record(**changes))

    def test_exact_valid_record_resolves(self):
        record = self.record()
        self.assertEqual(record, self.resolve((record,)))

    def test_malformed_neighbor_poison_fails_entire_registry_before_match(self):
        exact = self.record()
        malformed_neighbor = self.record(
            producer_ref="producer://unrelated",
            evidence_bundle_digest="not-a-digest",
        )
        with self.assertRaisesRegex(ValueError, "EVIDENCE_BUNDLE_DIGEST_SHA256_REQUIRED"):
            self.resolve((exact, malformed_neighbor))

    def test_production_registry_remains_empty_hold(self):
        receipt = candidate_evidence_registry_receipt()
        self.assertEqual(0, receipt.active_producer_count)
        self.assertEqual((), receipt.record_digests)
        self.assertFalse(receipt.authority)
        self.assertFalse(receipt.external_effect)


if __name__ == "__main__":
    unittest.main()
