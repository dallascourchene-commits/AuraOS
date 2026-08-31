from __future__ import annotations

from dataclasses import replace
import unittest

import tools.aura_generation_bound_admission_reuse as r769
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def parent_reuse_receipt():
    admission, current = r769.fixture(r769.AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL)
    receipt = r769.revalidate_admission_reuse(admission=admission, current=current)
    assert receipt.disposition is r769.ReuseDisposition.REUSE_CANDIDATE
    return receipt


def reuse():
    receipt = parent_reuse_receipt()
    return m.AdmissionReuseProjection(
        proof_head=m.REUSE_HEAD,
        proof_run=m.REUSE_RUN,
        proof_job=m.REUSE_JOB,
        source_blob=m.REUSE_SOURCE_BLOB,
        test_blob=m.REUSE_TEST_BLOB,
        admission_family=receipt.family.value,
        disposition=receipt.disposition.value,
        admission_receipt_digest=receipt.admission_receipt_digest,
        reuse_digest=receipt.reuse_digest,
        subject_identity=receipt.subject_identity or "",
        source_generation_key=receipt.source_generation_key or "",
        evidence_generation_key=receipt.evidence_generation_key or "",
        owner_context_key=receipt.owner_context_key or "",
        decision_context_key=receipt.decision_context_key or "",
        current_context_exact=True,
    )


def provenance():
    return m.ObservationProvenanceContractProjection(
        m.PROV_HEAD, m.PROV_RUN, m.PROV_JOB, m.PROV_SOURCE_BLOB, True, True, True,
    )


def source():
    return m.SourceIdentityProjection(
        m.OFFICIAL_REPOSITORY, m.PINNED_OFFICIAL_REVISION, m.SOURCE_SET_DIGEST, True,
    )


def owner():
    return m.OwnerHostTargetProjection(
        "owner-host:local:glm53-c2",
        "principal:g1",
        "host:g1",
        "runtime:g1",
        "cache:g1",
        "storage:g1",
        D0,
        "artifact:awj032:g6:owner-host-evidence",
    )


def evidence():
    return m.EvidenceContractProjection(
        D1, D2, D3, D4, m.REQUIRED_EVIDENCE_AXES, m.OPEN_GATE10_DEBT, True,
    )


def compile_(**overrides):
    args = dict(
        reuse=reuse(), provenance=provenance(), source=source(), owner=owner(), evidence=evidence()
    )
    args.update(overrides)
    return m.compile_gate10_owner_host_evidence_request(**args)


class G6Tests(unittest.TestCase):
    def test_parent_fixture_is_exact_glm53_reuse_candidate(self):
        p = parent_reuse_receipt()
        self.assertEqual(p.family.value, m.REUSE_FAMILY)
        self.assertEqual(p.disposition.value, m.REUSE_DISPOSITION)
        self.assertEqual(len(p.admission_receipt_digest), 64)
        self.assertEqual(len(p.reuse_digest), 64)

    def test_exact_parent_consequence_compiles_nonexecuting_request(self):
        p = parent_reuse_receipt()
        r = compile_()
        self.assertEqual(r.disposition, m.COMPILED)
        self.assertTrue(r.request_envelope_compiled)
        self.assertTrue(r.current_reuse_candidate_bound)
        self.assertTrue(r.exact_glm53_reuse_identity_bound)
        self.assertTrue(r.exact_source_request_identity_bound)
        self.assertEqual(r.admission_receipt_digest, p.admission_receipt_digest)
        self.assertEqual(r.reuse_digest, p.reuse_digest)
        self.assertEqual(r.subject_identity, p.subject_identity)
        self.assertEqual(r.source_generation_key, p.source_generation_key)
        self.assertEqual(r.evidence_generation_key, p.evidence_generation_key)
        self.assertEqual(r.owner_context_key, p.owner_context_key)
        self.assertEqual(r.decision_context_key, p.decision_context_key)
        self.assertEqual(r.canonical_c2_handoff_head, m.C2_HANDOFF_HEAD)
        self.assertEqual(r.canonical_c2_handoff_run, m.C2_HANDOFF_RUN)
        self.assertEqual(r.canonical_lifecycle_return_head, m.LIFECYCLE_RETURN_HEAD)
        self.assertEqual(r.canonical_lifecycle_return_run, m.LIFECYCLE_RETURN_RUN)
        for field in (
            "reuse_receipt_authenticated_by_this_contract",
            "source_currentness_proven_by_this_contract",
            "tensor_payload_bound",
            "real_tensor_quantization_observed",
            "owner_host_execution_observed",
            "full_flagship_model_loaded",
            "physical_io_proven",
            "observer_backend_authenticated",
            "auraos_resident_routing_proven",
            "replay_recovery_proven",
            "execution_authorized",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(r, field))

    def test_summary_cross_casts_cannot_impersonate_glm_reuse_identity(self):
        variants = (
            replace(reuse(), admission_family="BOUNDED_C2_PROPOSAL"),
            replace(reuse(), disposition="REUSE_CANDIDATE_GENERIC"),
            replace(reuse(), current_context_exact=False),
        )
        for candidate in variants:
            with self.subTest(candidate=candidate):
                r = compile_(reuse=candidate)
                self.assertEqual(r.disposition, m.HOLD_REUSE)
                self.assertFalse(r.current_reuse_candidate_bound)
                self.assertFalse(r.exact_glm53_reuse_identity_bound)
                self.assertEqual(r.admission_reuse_identity_digest, "")
                self.assertEqual(r.admission_receipt_digest, "")
                self.assertEqual(r.reuse_digest, "")
                self.assertEqual(r.subject_identity, "")

    def test_each_reuse_identity_axis_survives_and_changes_request_identity(self):
        base = compile_()
        mutations = {
            "admission_receipt_digest": D3,
            "reuse_digest": D4,
            "subject_identity": "subject:q18:changed",
            "source_generation_key": "source-generation:q18:changed",
            "evidence_generation_key": "evidence-generation:q18:changed",
            "owner_context_key": "owner-context:q18:changed",
            "decision_context_key": "decision-context:q18:changed",
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                changed = compile_(reuse=replace(reuse(), **{field: value}))
                self.assertEqual(changed.disposition, m.COMPILED)
                self.assertNotEqual(changed.request_digest, base.request_digest)
                self.assertNotEqual(changed.admission_reuse_identity_digest, base.admission_reuse_identity_digest)
                self.assertEqual(getattr(changed, field), value)
                self.assertFalse(changed.reuse_receipt_authenticated_by_this_contract)

    def test_reuse_projection_cannot_self_mint_auth_truth_or_effect(self):
        for field in (
            "reuse_receipt_authenticated_by_this_projection",
            "source_currentness_proven",
            "execution_authorized",
            "effect_authorized",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(reuse=replace(reuse(), **{field: True}))
        with self.assertRaises(ValueError):
            compile_(reuse=replace(reuse(), candidate_only=False))

    def test_malformed_or_incomplete_reuse_identity_rejected(self):
        for field, value in (
            ("admission_receipt_digest", "bad"),
            ("reuse_digest", "bad"),
            ("subject_identity", ""),
            ("source_generation_key", ""),
            ("evidence_generation_key", ""),
            ("owner_context_key", ""),
            ("decision_context_key", ""),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(reuse=replace(reuse(), **{field: value}))

    def test_provenance_contract_requires_operation_observer_backend_and_producer_gates(self):
        for field in (
            "exact_operation_binding_required",
            "observer_backend_provenance_required",
            "producer_authentication_required",
        ):
            r = compile_(provenance=replace(provenance(), **{field: False}))
            self.assertEqual(r.disposition, m.HOLD_PROVENANCE)

    def test_structural_provenance_never_becomes_glm_physical_truth(self):
        for field in ("tiny_fixture_is_glm53_evidence", "physical_observation_proven", "execution_authorized"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(provenance=replace(provenance(), **{field: True}))

    def test_source_identity_mismatch_reaches_hold_and_suppresses_unaccepted_identity(self):
        variants = (
            replace(source(), repository="example/not-glm"),
            replace(source(), pinned_revision="deadbeef"),
            replace(source(), source_set_digest=D4),
            replace(source(), official_revision_revalidation_required=False),
        )
        for candidate in variants:
            with self.subTest(source=candidate):
                r = compile_(source=candidate)
                self.assertEqual(r.disposition, m.HOLD_SOURCE)
                self.assertFalse(r.exact_source_request_identity_bound)
                self.assertEqual(r.official_repository, "")
                self.assertEqual(r.pinned_official_revision, "")
                self.assertEqual(r.source_set_digest, "")

    def test_source_projection_cannot_self_mint_currentness_or_tensor_binding(self):
        for field in ("source_currentness_proven", "tensor_payload_bound"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(source=replace(source(), **{field: True}))

    def test_owner_target_is_not_authentication_or_authority(self):
        for field in ("owner_authenticated_by_this_contract", "execution_authorized_by_this_contract"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(owner=replace(owner(), **{field: True}))

    def test_exact_evidence_axes_debt_and_revision_revalidation_are_mandatory(self):
        variants = (
            replace(evidence(), required_evidence_axes=m.REQUIRED_EVIDENCE_AXES[:-1]),
            replace(evidence(), open_gate10_debt=m.OPEN_GATE10_DEBT[:-1]),
            replace(evidence(), official_revision_revalidation_required=False),
        )
        for candidate in variants:
            with self.assertRaises(ValueError):
                compile_(evidence=candidate)

    def test_request_cannot_claim_future_observation(self):
        for field in (
            "actual_owner_host_evidence_already_observed",
            "authenticated_physical_observation_already_proven",
            "gate10_promoted",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                compile_(evidence=replace(evidence(), **{field: True}))

    def test_parent_proof_substitution_rejected(self):
        with self.assertRaises(ValueError):
            compile_(reuse=replace(reuse(), proof_job=m.REUSE_JOB + 1))
        with self.assertRaises(ValueError):
            compile_(provenance=replace(provenance(), proof_run=m.PROV_RUN + 1))

    def test_receipt_deterministic_and_runtime_generation_sensitive(self):
        a = compile_()
        b = compile_()
        self.assertEqual(a, b)
        c = compile_(owner=replace(owner(), runtime_generation="runtime:g2"))
        self.assertNotEqual(a.request_digest, c.request_digest)

    def test_different_j_512(self):
        self.assertEqual(m.prove_different_j(), 512)

    def test_laws(self):
        for law in (
            "AdmissionValidAtProduce!=AdmissionReusableAtUse",
            "ReuseCandidateSummary!=AdmissionReuseReceiptIdentity",
            "GLM53AdmissionFamilyMustRemainExact",
            "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+Decision+ReuseDigestMustSurviveProjection",
            "IdentityBinding!=ReceiptProducerAuthentication",
            "IdentityBinding!=SourceCurrentnessTruth",
            "CallerWitness!=BackendObservationProvenance",
            "SourceRequestIdentity!=SourceCurrentnessTruth",
            "CanonicalC2ReturnPath!=ProducerAuthentication",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, m.LAWS)


if __name__ == "__main__":
    unittest.main()
