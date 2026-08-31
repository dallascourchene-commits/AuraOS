from __future__ import annotations
from dataclasses import replace
import unittest
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m

D0 = "0" * 64
D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64


def reuse():
    return m.AdmissionReuseProjection(
        m.REUSE_HEAD, m.REUSE_RUN, m.REUSE_JOB, m.REUSE_SOURCE_BLOB, m.REUSE_TEST_BLOB,
        m.REUSE_FAMILY, m.REUSE_DISPOSITION, True,
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
        "owner-host:local:glm53-c2", "principal:g1", "host:g1", "runtime:g1",
        "cache:g1", "storage:g1", D0, "artifact:awj032:g6:owner-host-evidence",
    )


def evidence():
    return m.EvidenceContractProjection(
        D1, D2, D3, D4, m.REQUIRED_EVIDENCE_AXES, m.OPEN_GATE10_DEBT, True,
    )


def compile_(**overrides):
    args = dict(reuse=reuse(), provenance=provenance(), source=source(), owner=owner(), evidence=evidence())
    args.update(overrides)
    return m.compile_gate10_owner_host_evidence_request(**args)


class G6Tests(unittest.TestCase):
    def test_exact_inputs_compile_nonexecuting_request(self):
        r = compile_()
        self.assertEqual(r.disposition, m.COMPILED)
        self.assertTrue(r.request_envelope_compiled)
        self.assertTrue(r.exact_source_request_identity_bound)
        self.assertEqual(r.canonical_c2_handoff_head, m.C2_HANDOFF_HEAD)
        self.assertEqual(r.canonical_c2_handoff_run, m.C2_HANDOFF_RUN)
        self.assertEqual(r.canonical_lifecycle_return_head, m.LIFECYCLE_RETURN_HEAD)
        self.assertEqual(r.canonical_lifecycle_return_run, m.LIFECYCLE_RETURN_RUN)
        for f in (
            "tensor_payload_bound", "real_tensor_quantization_observed", "owner_host_execution_observed",
            "full_flagship_model_loaded", "physical_io_proven", "observer_backend_authenticated",
            "auraos_resident_routing_proven", "replay_recovery_proven", "execution_authorized",
            "gate10_promoted",
        ):
            self.assertFalse(getattr(r, f))

    def test_reuse_must_be_current_candidate(self):
        self.assertEqual(compile_(reuse=replace(reuse(), current_context_exact=False)).disposition, m.HOLD_REUSE)
        self.assertEqual(compile_(reuse=replace(reuse(), disposition="HOLD")).disposition, m.HOLD_REUSE)

    def test_reuse_cannot_self_mint_truth_or_execution(self):
        for f in ("source_currentness_proven", "execution_authorized", "gate10_promoted"):
            with self.subTest(f=f), self.assertRaises(ValueError):
                compile_(reuse=replace(reuse(), **{f: True}))

    def test_provenance_contract_requires_operation_observer_backend_and_producer_gates(self):
        for f in ("exact_operation_binding_required", "observer_backend_provenance_required", "producer_authentication_required"):
            self.assertEqual(compile_(provenance=replace(provenance(), **{f: False})).disposition, m.HOLD_PROVENANCE)

    def test_tiny_fixture_and_structural_provenance_never_become_glm_truth(self):
        for f in ("tiny_fixture_is_glm53_evidence", "physical_observation_proven", "execution_authorized"):
            with self.subTest(f=f), self.assertRaises(ValueError):
                compile_(provenance=replace(provenance(), **{f: True}))

    def test_source_identity_mismatch_reaches_typed_hold_and_suppresses_unaccepted_identity(self):
        variants = (
            replace(source(), repository="example/not-glm"),
            replace(source(), pinned_revision="deadbeef"),
            replace(source(), source_set_digest=D4),
            replace(source(), official_revision_revalidation_required=False),
        )
        for s in variants:
            with self.subTest(source=s):
                r = compile_(source=s)
                self.assertEqual(r.disposition, m.HOLD_SOURCE)
                self.assertFalse(r.exact_source_request_identity_bound)
                self.assertEqual(r.official_repository, "")
                self.assertEqual(r.pinned_official_revision, "")
                self.assertEqual(r.source_set_digest, "")

    def test_source_projection_cannot_self_mint_currentness_or_tensor_binding(self):
        for f in ("source_currentness_proven", "tensor_payload_bound"):
            with self.subTest(f=f), self.assertRaises(ValueError):
                compile_(source=replace(source(), **{f: True}))

    def test_owner_target_is_not_authentication_or_authority(self):
        for f in ("owner_authenticated_by_this_contract", "execution_authorized_by_this_contract"):
            with self.subTest(f=f), self.assertRaises(ValueError):
                compile_(owner=replace(owner(), **{f: True}))

    def test_exact_evidence_axes_debt_and_revision_revalidation_are_mandatory(self):
        for e in (
            replace(evidence(), required_evidence_axes=m.REQUIRED_EVIDENCE_AXES[:-1]),
            replace(evidence(), open_gate10_debt=m.OPEN_GATE10_DEBT[:-1]),
            replace(evidence(), official_revision_revalidation_required=False),
        ):
            with self.assertRaises(ValueError):
                compile_(evidence=e)

    def test_request_cannot_claim_future_observation(self):
        for f in ("actual_owner_host_evidence_already_observed", "authenticated_physical_observation_already_proven", "gate10_promoted"):
            with self.subTest(f=f), self.assertRaises(ValueError):
                compile_(evidence=replace(evidence(), **{f: True}))

    def test_parent_proof_substitution_rejected(self):
        with self.assertRaises(ValueError):
            compile_(reuse=replace(reuse(), proof_job=m.REUSE_JOB + 1))
        with self.assertRaises(ValueError):
            compile_(provenance=replace(provenance(), proof_run=m.PROV_RUN + 1))

    def test_receipt_deterministic_and_generation_sensitive(self):
        a = compile_()
        b = compile_()
        self.assertEqual(a, b)
        c = compile_(owner=replace(owner(), runtime_generation="runtime:g2"))
        self.assertNotEqual(a.request_digest, c.request_digest)

    def test_different_j_512(self):
        self.assertEqual(m.prove_different_j(), 512)

    def test_laws(self):
        self.assertIn("AdmissionValidAtProduce!=AdmissionReusableAtUse", m.LAWS)
        self.assertIn("CallerWitness!=BackendObservationProvenance", m.LAWS)
        self.assertIn("SourceRequestIdentity!=SourceCurrentnessTruth", m.LAWS)
        self.assertIn("CanonicalC2ReturnPath!=ProducerAuthentication", m.LAWS)
        self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV", m.LAWS)


if __name__ == "__main__":
    unittest.main()
