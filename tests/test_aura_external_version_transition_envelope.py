from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_external_version_transition_envelope import (
    EKI2_REQUIRED_AXES,
    PR737_BLOB,
    PR737_HEAD,
    PR737_REQUIRED_AXES,
    PR738_BLOB,
    PR738_HEAD,
    PR738_REQUIRED_HOLD,
    CurrentEvidenceDescriptorV1,
    EnvelopeDisposition,
    FutureReadObligationV1,
    VersionTransitionRequestV1,
    VersionedRowBindingV1,
    WriteAdmissionWitnessV1,
    build_version_transition_envelope,
    current_evidence_generation_key,
    current_subject_key,
    legacy_semantic_id,
    versioned_record_key,
)


CANONICAL_ID = "2606.26511"
CANONICAL_URI = "https://arxiv.org/abs/2606.26511"
LEGACY_KIND = "ARXIV"
PROVIDER = "ARXIV"
SOURCE_KIND = "PAPER"
R1 = "f" * 64
R2 = "0" * 64
STORE_REF = "memory://eki4-fixture"
STORE_GENERATION = "EKI4::STORE::fixture"
STORE_SHA = "9" * 64
CONTENT_SHA = "8" * 64


def _evidence() -> CurrentEvidenceDescriptorV1:
    subject = current_subject_key(provider=PROVIDER, source_kind=SOURCE_KIND, canonical_id=CANONICAL_ID)
    evidence = current_evidence_generation_key(
        subject_key=subject,
        provider_revision="v2",
        content_digest=CONTENT_SHA,
        source_generated_at="2026-06-25T01:31:53Z",
        exact_source_uri=CANONICAL_URI,
        verifier_generation="fixture-verifier-v1",
        verified_fields=("content_digest", "exact_source_uri"),
        etag="eki4-etag-v2",
    )
    return CurrentEvidenceDescriptorV1(
        provider=PROVIDER,
        source_kind=SOURCE_KIND,
        canonical_id=CANONICAL_ID,
        canonical_uri=CANONICAL_URI,
        provider_revision="v2",
        content_digest=CONTENT_SHA,
        source_generated_at="2026-06-25T01:31:53Z",
        exact_source_uri=CANONICAL_URI,
        verifier_generation="fixture-verifier-v1",
        verified_fields=("content_digest", "exact_source_uri"),
        claimed_subject_key=subject,
        claimed_evidence_generation_key=evidence,
        etag="eki4-etag-v2",
    )


def _rows() -> tuple[VersionedRowBindingV1, VersionedRowBindingV1]:
    legacy = legacy_semantic_id(legacy_source_kind=LEGACY_KIND, canonical_id=CANONICAL_ID)
    k1 = versioned_record_key(legacy_id=legacy, record_generation=R1)
    k2 = versioned_record_key(legacy_id=legacy, record_generation=R2)
    return (
        VersionedRowBindingV1(
            key=k1,
            record_generation=R1,
            legacy_semantic_id=legacy,
            canonical_id=CANONICAL_ID,
            canonical_uri=CANONICAL_URI,
            successor=k2,
        ),
        VersionedRowBindingV1(
            key=k2,
            record_generation=R2,
            legacy_semantic_id=legacy,
            canonical_id=CANONICAL_ID,
            canonical_uri=CANONICAL_URI,
            successor=None,
        ),
    )


def _write(evidence: CurrentEvidenceDescriptorV1 | None = None) -> WriteAdmissionWitnessV1:
    evidence = evidence or _evidence()
    return WriteAdmissionWitnessV1(
        pr738_head=PR738_HEAD,
        pr738_blob=PR738_BLOB,
        stable_subject_disposition=PR738_REQUIRED_HOLD,
        subject_key=evidence.claimed_subject_key,
        proposed_evidence_generation_key=evidence.claimed_evidence_generation_key,
        store_ref=STORE_REF,
        store_generation=STORE_GENERATION,
        store_sha256=STORE_SHA,
        proposed_source_current=True,
        observed_store_current=True,
        independently_resolved=True,
    )


def _read() -> FutureReadObligationV1:
    return FutureReadObligationV1(
        pr737_head=PR737_HEAD,
        pr737_blob=PR737_BLOB,
        required_guard_axes=PR737_REQUIRED_AXES,
        required_eki2_axes=EKI2_REQUIRED_AXES,
        persisted_currentness_is_witness=False,
        resolve_at_read_required=True,
    )


def _request() -> VersionTransitionRequestV1:
    evidence = _evidence()
    predecessor, successor = _rows()
    return VersionTransitionRequestV1(
        legacy_source_kind=LEGACY_KIND,
        evidence=evidence,
        predecessor=predecessor,
        successor=successor,
        write_witness=_write(evidence),
        future_read=_read(),
        expected_store_ref=STORE_REF,
        expected_store_generation=STORE_GENERATION,
        expected_store_sha256=STORE_SHA,
    )


class VersionTransitionEnvelopeTests(unittest.TestCase):
    def test_exact_explicit_transition_is_ready_and_nonwriting(self) -> None:
        receipt = build_version_transition_envelope(_request())
        self.assertIs(receipt.disposition, EnvelopeDisposition.VERSION_TRANSITION_PLAN_READY)
        self.assertEqual(receipt.explicit_supersession_edge, (_request().predecessor.key, _request().successor.key))
        self.assertTrue(receipt.write_currentness_resolved)
        self.assertTrue(receipt.read_currentness_debt_carried)
        self.assertEqual(receipt.required_future_read_axes, ("source",))
        self.assertEqual(receipt.required_eki2_read_axes, EKI2_REQUIRED_AXES)
        self.assertFalse(receipt.store_mutated)
        self.assertFalse(receipt.write_authority)
        self.assertFalse(receipt.effect_authority)
        self.assertFalse(receipt.semantic_truth_granted)
        self.assertFalse(receipt.semantic_k27_authority)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)

    def test_four_identity_generation_domains_remain_distinct(self) -> None:
        receipt = build_version_transition_envelope(_request())
        values = {
            receipt.current_subject_key,
            receipt.current_evidence_generation_key,
            receipt.legacy_semantic_id,
            receipt.successor_record_generation,
        }
        self.assertEqual(len(values), 4)

    def test_stable_subject_overwrite_requires_pr738_representation_hold(self) -> None:
        req = _request()
        bad = replace(req.write_witness, stable_subject_disposition="INSERT_NEW_PLAN")
        receipt = build_version_transition_envelope(replace(req, write_witness=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.REPRESENTATION_OWNER_HOLD)

    def test_distinct_versioned_keys_do_not_pay_write_currentness(self) -> None:
        req = _request()
        bad = replace(req.write_witness, proposed_source_current=False)
        receipt = build_version_transition_envelope(replace(req, write_witness=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.WRITE_CURRENTNESS_REQUIRED)

    def test_read_obligation_cannot_be_paid_by_persisted_current_state(self) -> None:
        req = _request()
        bad = replace(req.future_read, persisted_currentness_is_witness=True)
        receipt = build_version_transition_envelope(replace(req, future_read=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.READ_OBLIGATION_REQUIRED)

    def test_missing_source_read_axis_fails_closed(self) -> None:
        req = _request()
        bad = replace(req.future_read, required_guard_axes=())
        receipt = build_version_transition_envelope(replace(req, future_read=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.READ_OBLIGATION_REQUIRED)

    def test_explicit_successor_beats_lexical_order(self) -> None:
        # R1 ('f...') is lexically after R2 ('0...'); the edge still owns version order.
        receipt = build_version_transition_envelope(_request())
        self.assertIs(receipt.disposition, EnvelopeDisposition.VERSION_TRANSITION_PLAN_READY)
        self.assertEqual(receipt.predecessor_record_generation, R1)
        self.assertEqual(receipt.successor_record_generation, R2)
        self.assertFalse(receipt.chronological_order_inferred)

    def test_missing_explicit_successor_edge_does_not_infer_latest(self) -> None:
        req = _request()
        bad_predecessor = replace(req.predecessor, successor=None)
        receipt = build_version_transition_envelope(replace(req, predecessor=bad_predecessor))
        self.assertIs(receipt.disposition, EnvelopeDisposition.SUPERSESSION_EDGE_REQUIRED)

    def test_same_record_generation_is_not_a_version_transition(self) -> None:
        req = _request()
        legacy = req.predecessor.legacy_semantic_id
        same_key = versioned_record_key(legacy_id=legacy, record_generation=R1)
        successor = replace(req.successor, key=same_key, record_generation=R1)
        predecessor = replace(req.predecessor, successor=same_key)
        receipt = build_version_transition_envelope(replace(req, predecessor=predecessor, successor=successor))
        self.assertIs(receipt.disposition, EnvelopeDisposition.GENERATION_BINDING_HOLD)

    def test_cross_subject_successor_is_rejected(self) -> None:
        req = _request()
        foreign_id = "different-subject"
        foreign_legacy = legacy_semantic_id(legacy_source_kind=LEGACY_KIND, canonical_id=foreign_id)
        foreign = replace(
            req.successor,
            key=versioned_record_key(legacy_id=foreign_legacy, record_generation=R2),
            legacy_semantic_id=foreign_legacy,
            canonical_id=foreign_id,
        )
        predecessor = replace(req.predecessor, successor=foreign.key)
        receipt = build_version_transition_envelope(replace(req, predecessor=predecessor, successor=foreign))
        self.assertIs(receipt.disposition, EnvelopeDisposition.IDENTITY_BRIDGE_HOLD)

    def test_write_witness_must_bind_exact_subject_and_evidence_generation(self) -> None:
        req = _request()
        bad = replace(req.write_witness, proposed_evidence_generation_key="7" * 64)
        receipt = build_version_transition_envelope(replace(req, write_witness=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.GENERATION_BINDING_HOLD)

    def test_store_integrity_is_exact(self) -> None:
        req = _request()
        bad = replace(req.write_witness, store_sha256="6" * 64)
        receipt = build_version_transition_envelope(replace(req, write_witness=bad))
        self.assertIs(receipt.disposition, EnvelopeDisposition.STORE_INTEGRITY_HOLD)

    def test_model_prefix_kv_is_a_different_owner(self) -> None:
        receipt = build_version_transition_envelope(replace(_request(), responsibility="MODEL_PREFIX_KV"))
        self.assertIs(receipt.disposition, EnvelopeDisposition.WRONG_RESPONSIBILITY_OWNER)
        self.assertFalse(receipt.native_private_transformer_kv_accessed)


if __name__ == "__main__":
    unittest.main()
