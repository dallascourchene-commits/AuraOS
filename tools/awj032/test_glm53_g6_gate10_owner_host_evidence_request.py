from __future__ import annotations

from dataclasses import replace
import unittest

import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64


def reuse() -> m.AdmissionReuseProjection:
    return m.AdmissionReuseProjection(
        proof_head=m.REUSE_HEAD,
        proof_run=m.REUSE_RUN,
        proof_job=m.REUSE_JOB,
        source_blob=m.REUSE_SOURCE_BLOB,
        test_blob=m.REUSE_TEST_BLOB,
        admission_family=m.REUSE_FAMILY,
        disposition=m.REUSE_DISPOSITION,
        admission_receipt_digest=D4,
        reuse_digest=D5,
        subject_identity="glm53:q18:representative-e8-c2",
        source_generation_key="source:glm53:7cda819:q18-set",
        evidence_generation_key="evidence:q18:current-generation",
        owner_context_key="owner-context:glm53-c2:g1",
        decision_context_key="decision-context:q18:g1",
    )


def provenance() -> m.ObservationProvenanceContractProjection:
    return m.ObservationProvenanceContractProjection(
        m.PROV_HEAD, m.PROV_RUN, m.PROV_JOB, m.PROV_SOURCE_BLOB, True, True, True
    )


def owner() -> m.OwnerHostTargetProjection:
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


def evidence() -> m.EvidenceContractProjection:
    return m.EvidenceContractProjection(
        D1, D2, D3, D4, m.REQUIRED_EVIDENCE_AXES, m.OPEN_GATE10_DEBT, True
    )


class G6Tests(unittest.TestCase):
    def test_exact_inputs_compile_nonexecuting_request(self):
        r = m.compile_gate10_owner_host_evidence_request(
            reuse=reuse(), provenance=provenance(), owner=owner(), evidence=evidence()
        )
        self.assertEqual(r.disposition, m.COMPILED)
        self.assertTrue(r.request_envelope_compiled)
        self.assertEqual(r.admission_receipt_digest, reuse().admission_receipt_digest)
        self.assertEqual(r.reuse_subject_identity, reuse().subject_identity)
        self.assertEqual(r.reuse_source_generation_key, reuse().source_generation_key)
        self.assertFalse(r.reuse_receipt_authenticated_by_this_contract)
        for field in (
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

    def test_exact_glm53_reuse_family_required(self):
        with self.assertRaisesRegex(ValueError, "REUSE_FAMILY_MISMATCH"):
            m.compile_gate10_owner_host_evidence_request(
                reuse=replace(reuse(), admission_family="BOUNDED_C2_PROPOSAL"),
                provenance=provenance(),
                owner=owner(),
                evidence=evidence(),
            )
        with self.assertRaisesRegex(ValueError, "REUSE_FAMILY_MISMATCH"):
            m.compile_gate10_owner_host_evidence_request(
                reuse=replace(reuse(), admission_family="HYDRATION_TRANSACTION"),
                provenance=provenance(),
                owner=owner(),
                evidence=evidence(),
            )

    def test_reuse_must_be_candidate_only(self):
        with self.assertRaisesRegex(ValueError, "REUSE_DISPOSITION_MISMATCH"):
            m.compile_gate10_owner_host_evidence_request(
                reuse=replace(reuse(), disposition="HOLD"),
                provenance=provenance(),
                owner=owner(),
                evidence=evidence(),
            )
        with self.assertRaisesRegex(ValueError, "REUSE_MUST_REMAIN_CANDIDATE_ONLY"):
            m.compile_gate10_owner_host_evidence_request(
                reuse=replace(reuse(), candidate_only=False),
                provenance=provenance(),
                owner=owner(),
                evidence=evidence(),
            )

    def test_pr769_identity_vector_cannot_be_collapsed_or_omitted(self):
        for field in (
            "subject_identity",
            "source_generation_key",
            "evidence_generation_key",
            "owner_context_key",
            "decision_context_key",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=replace(reuse(), **{field: " "}),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=evidence(),
                )
        for field in ("admission_receipt_digest", "reuse_digest"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=replace(reuse(), **{field: "not-a-digest"}),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=evidence(),
                )

    def test_every_reuse_identity_axis_changes_request_identity(self):
        base = m.compile_gate10_owner_host_evidence_request(
            reuse=reuse(), provenance=provenance(), owner=owner(), evidence=evidence()
        )
        substitutions = {
            "admission_receipt_digest": "a" * 64,
            "reuse_digest": "b" * 64,
            "subject_identity": reuse().subject_identity + ":other",
            "source_generation_key": reuse().source_generation_key + ":other",
            "evidence_generation_key": reuse().evidence_generation_key + ":other",
            "owner_context_key": reuse().owner_context_key + ":other",
            "decision_context_key": reuse().decision_context_key + ":other",
        }
        for field, value in substitutions.items():
            with self.subTest(field=field):
                changed = m.compile_gate10_owner_host_evidence_request(
                    reuse=replace(reuse(), **{field: value}),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=evidence(),
                )
                self.assertNotEqual(base.request_digest, changed.request_digest)

    def test_reuse_cannot_self_mint_truth_or_execution(self):
        for field in ("source_currentness_proven", "execution_authorized", "gate10_promoted"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=replace(reuse(), **{field: True}),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=evidence(),
                )

    def test_provenance_contract_requires_operation_observer_backend_and_producer_gates(self):
        for field in (
            "exact_operation_binding_required",
            "observer_backend_provenance_required",
            "producer_authentication_required",
        ):
            r = m.compile_gate10_owner_host_evidence_request(
                reuse=reuse(),
                provenance=replace(provenance(), **{field: False}),
                owner=owner(),
                evidence=evidence(),
            )
            self.assertEqual(r.disposition, m.HOLD_PROVENANCE)

    def test_tiny_fixture_and_structural_provenance_never_become_glm_truth(self):
        for field in (
            "tiny_fixture_is_glm53_evidence",
            "physical_observation_proven",
            "execution_authorized",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=reuse(),
                    provenance=replace(provenance(), **{field: True}),
                    owner=owner(),
                    evidence=evidence(),
                )

    def test_owner_target_is_not_authentication_or_authority(self):
        for field in (
            "owner_authenticated_by_this_contract",
            "execution_authorized_by_this_contract",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=reuse(),
                    provenance=provenance(),
                    owner=replace(owner(), **{field: True}),
                    evidence=evidence(),
                )

    def test_exact_evidence_axes_debt_and_revision_revalidation_are_mandatory(self):
        variants = (
            replace(evidence(), required_evidence_axes=m.REQUIRED_EVIDENCE_AXES[:-1]),
            replace(evidence(), open_gate10_debt=m.OPEN_GATE10_DEBT[:-1]),
            replace(evidence(), official_revision_revalidation_required=False),
        )
        for candidate in variants:
            with self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=reuse(),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=candidate,
                )

    def test_request_cannot_claim_future_observation(self):
        for field in (
            "actual_owner_host_evidence_already_observed",
            "authenticated_physical_observation_already_proven",
            "gate10_promoted",
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.compile_gate10_owner_host_evidence_request(
                    reuse=reuse(),
                    provenance=provenance(),
                    owner=owner(),
                    evidence=replace(evidence(), **{field: True}),
                )

    def test_parent_proof_substitution_rejected(self):
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                reuse=replace(reuse(), proof_job=m.REUSE_JOB + 1),
                provenance=provenance(),
                owner=owner(),
                evidence=evidence(),
            )
        with self.assertRaises(ValueError):
            m.compile_gate10_owner_host_evidence_request(
                reuse=reuse(),
                provenance=replace(provenance(), proof_run=m.PROV_RUN + 1),
                owner=owner(),
                evidence=evidence(),
            )

    def test_receipt_deterministic_and_generation_sensitive(self):
        a = m.compile_gate10_owner_host_evidence_request(
            reuse=reuse(), provenance=provenance(), owner=owner(), evidence=evidence()
        )
        b = m.compile_gate10_owner_host_evidence_request(
            reuse=reuse(), provenance=provenance(), owner=owner(), evidence=evidence()
        )
        self.assertEqual(a, b)
        c = m.compile_gate10_owner_host_evidence_request(
            reuse=reuse(),
            provenance=provenance(),
            owner=replace(owner(), runtime_generation="runtime:g2"),
            evidence=evidence(),
        )
        self.assertNotEqual(a.request_digest, c.request_digest)

    def test_different_j_512(self):
        self.assertEqual(m.prove_different_j(), 512)

    def test_laws(self):
        for law in (
            "AdmissionValidAtProduce!=AdmissionReusableAtUse",
            "ReuseSummaryBoolean!=AdmissionReceiptIdentity",
            "GLM53AdmissionFamilyMustRemainExact",
            "AdmissionReceiptDigest+Subject+Source+Evidence+Owner+DecisionMustSurviveProjection",
            "CallerWitness!=BackendObservationProvenance",
            "RepoHeadChanged!=TensorSourceGenerationChanged",
            "CoordinateMemory!=MODEL_PREFIX_KV",
        ):
            self.assertIn(law, m.LAWS)


if __name__ == "__main__":
    unittest.main()
