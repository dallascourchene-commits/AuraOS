from __future__ import annotations
from dataclasses import replace
import unittest
import tools.awj032.glm53_g6_gate10_owner_host_evidence_request as m
D0="0"*64; D1="1"*64; D2="2"*64; D3="3"*64; D4="4"*64

def reuse(): return m.AdmissionReuseProjection(m.REUSE_HEAD,m.REUSE_RUN,m.REUSE_JOB,m.REUSE_SOURCE_BLOB,m.REUSE_TEST_BLOB,m.REUSE_FAMILY,m.REUSE_DISPOSITION,True)
def provenance(): return m.ObservationProvenanceContractProjection(m.PROV_HEAD,m.PROV_RUN,m.PROV_JOB,m.PROV_SOURCE_BLOB,True,True,True)
def owner(): return m.OwnerHostTargetProjection("owner-host:local:glm53-c2","principal:g1","host:g1","runtime:g1","cache:g1","storage:g1",D0,"artifact:awj032:g6:owner-host-evidence")
def evidence(): return m.EvidenceContractProjection(D1,D2,D3,D4,m.REQUIRED_EVIDENCE_AXES,m.OPEN_GATE10_DEBT,True)

class G6Tests(unittest.TestCase):
    def test_exact_inputs_compile_nonexecuting_request(self):
        r=m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=owner(),evidence=evidence())
        self.assertEqual(r.disposition,m.COMPILED); self.assertTrue(r.request_envelope_compiled)
        for f in ("tensor_payload_bound","real_tensor_quantization_observed","owner_host_execution_observed","full_flagship_model_loaded","physical_io_proven","observer_backend_authenticated","auraos_resident_routing_proven","replay_recovery_proven","execution_authorized","gate10_promoted"): self.assertFalse(getattr(r,f))
    def test_reuse_must_be_current_candidate(self):
        r=m.compile_gate10_owner_host_evidence_request(reuse=replace(reuse(),current_context_exact=False),provenance=provenance(),owner=owner(),evidence=evidence()); self.assertEqual(r.disposition,m.HOLD_REUSE)
        r=m.compile_gate10_owner_host_evidence_request(reuse=replace(reuse(),disposition="HOLD"),provenance=provenance(),owner=owner(),evidence=evidence()); self.assertEqual(r.disposition,m.HOLD_REUSE)
    def test_reuse_cannot_self_mint_truth_or_execution(self):
        for f in ("source_currentness_proven","execution_authorized","gate10_promoted"):
            with self.subTest(f=f), self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=replace(reuse(),**{f:True}),provenance=provenance(),owner=owner(),evidence=evidence())
    def test_provenance_contract_requires_operation_observer_backend_and_producer_gates(self):
        for f in ("exact_operation_binding_required","observer_backend_provenance_required","producer_authentication_required"):
            r=m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=replace(provenance(),**{f:False}),owner=owner(),evidence=evidence()); self.assertEqual(r.disposition,m.HOLD_PROVENANCE)
    def test_tiny_fixture_and_structural_provenance_never_become_glm_truth(self):
        for f in ("tiny_fixture_is_glm53_evidence","physical_observation_proven","execution_authorized"):
            with self.subTest(f=f), self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=replace(provenance(),**{f:True}),owner=owner(),evidence=evidence())
    def test_owner_target_is_not_authentication_or_authority(self):
        for f in ("owner_authenticated_by_this_contract","execution_authorized_by_this_contract"):
            with self.subTest(f=f), self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=replace(owner(),**{f:True}),evidence=evidence())
    def test_exact_evidence_axes_debt_and_revision_revalidation_are_mandatory(self):
        for e in (replace(evidence(),required_evidence_axes=m.REQUIRED_EVIDENCE_AXES[:-1]),replace(evidence(),open_gate10_debt=m.OPEN_GATE10_DEBT[:-1]),replace(evidence(),official_revision_revalidation_required=False)):
            with self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=owner(),evidence=e)
    def test_request_cannot_claim_future_observation(self):
        for f in ("actual_owner_host_evidence_already_observed","authenticated_physical_observation_already_proven","gate10_promoted"):
            with self.subTest(f=f), self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=owner(),evidence=replace(evidence(),**{f:True}))
    def test_parent_proof_substitution_rejected(self):
        with self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=replace(reuse(),proof_job=m.REUSE_JOB+1),provenance=provenance(),owner=owner(),evidence=evidence())
        with self.assertRaises(ValueError): m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=replace(provenance(),proof_run=m.PROV_RUN+1),owner=owner(),evidence=evidence())
    def test_receipt_deterministic_and_generation_sensitive(self):
        a=m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=owner(),evidence=evidence()); b=m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=owner(),evidence=evidence()); self.assertEqual(a,b)
        c=m.compile_gate10_owner_host_evidence_request(reuse=reuse(),provenance=provenance(),owner=replace(owner(),runtime_generation="runtime:g2"),evidence=evidence()); self.assertNotEqual(a.request_digest,c.request_digest)
    def test_different_j_512(self): self.assertEqual(m.prove_different_j(),512)
    def test_laws(self):
        self.assertIn("AdmissionValidAtProduce!=AdmissionReusableAtUse",m.LAWS); self.assertIn("CallerWitness!=BackendObservationProvenance",m.LAWS); self.assertIn("CoordinateMemory!=MODEL_PREFIX_KV",m.LAWS)
if __name__=="__main__": unittest.main()