import itertools, unittest
from dataclasses import replace
from hashlib import sha256
from tools.awj032.training_r1_resolver_reference.training_admission_resolver import *
from tools.awj032.training_o1_reference.training_admission import (
    SourceAuditVerifier, AdapterManifest, derived_expected_adapter_keys, h_bytes, admit as o1_admit,
)
R=lambda s:sha256(s.encode()).hexdigest()

def o1_fixture():
    sv=SourceAuditVerifier({'src':b'source-secret'},'src',2); src=sv._issue_exact(observed_at=5)
    targets=('layers.0.q_proj','layers.0.v_proj'); keys=tuple(sorted(derived_expected_adapter_keys(targets))); values={k:k.encode() for k in keys}
    m=AdapterManifest(R('base'),R('cfg'),R('tok'),R('runtime'),AIRLLM_COMMIT,'qwen3_8_dense','AirLLMLoRA',targets,16,32,False,keys,tuple(h_bytes(values[k]) for k in keys))
    a=o1_admit(source_verifier=sv,source=src,manifest=m,observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,observed_target_paths=set(targets),provided_adapter_values=values,observed_at=6)
    return sv,m,a

class ResolverTest(unittest.TestCase):
    def setUp(self):
        self.sv,self.m,self.o1=o1_fixture(); self.o=OwnerResolver({'k':b'owner-secret'},'k',3)
        self.s=AdmissionSemantic(self.o1.admission_root,self.o1.source_root,self.o1.adapter_root,self.o1.runtime_root,self.o1.target_topology_root,AIRLLM_COMMIT,'qwen3_8_dense','AirLLMLoRA')
        self.r=self.o.issue(self.s,o1_admission=self.o1,source_verifier=self.sv,now=10,ttl=20)
    def test_issue_rejects_forged_o1(self):
        bad=replace(self.o1,mac=R('bad'))
        with self.assertRaises(ValueError): self.o.issue(self.s,o1_admission=bad,source_verifier=self.sv,now=10,ttl=20)
    def test_issue_rejects_wrong_o1_root(self):
        bads=replace(self.s,o1_admission_root=R('bad'))
        with self.assertRaises(ValueError): self.o.issue(bads,o1_admission=self.o1,source_verifier=self.sv,now=10,ttl=20)
    def test_admission_valid(self): self.assertEqual(self.o.verify(self.r,now=15,expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root,expected_o1_admission_root=self.o1.admission_root),'VERIFIED_D0_ADMISSION')
    def test_nan_fails(self): self.assertEqual(self.o.verify(self.r,now=float('nan'),expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root),'HOLD_INVALID_TIME')
    def test_expired(self): self.assertEqual(self.o.verify(self.r,now=30,expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root),'HOLD_EXPIRED')
    def test_forgery(self):
        bad=replace(self.r,mac=R('bad')); self.assertEqual(self.o.verify(bad,now=15,expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root),'HOLD_BAD_SIGNATURE')
    def permit(self): return self.o.issue_transition_permit(self.r,transition_root=R('transition'),transition_subject_root=R('subject'),deployment_generation='dep-1',now=15,ttl=10,observed_source_root=self.s.source_root,observed_adapter_root=self.s.adapter_root,observed_runtime_root=self.s.runtime_root,observed_target_topology_root=self.s.target_topology_root)
    def pv(self,p=None,**kw):
        p=p or self.permit(); args=dict(now=16,expected_transition_root=R('transition'),expected_transition_subject_root=R('subject'),expected_deployment_generation='dep-1',observed_source_root=self.s.source_root,observed_adapter_root=self.s.adapter_root,observed_runtime_root=self.s.runtime_root,observed_target_topology_root=self.s.target_topology_root); args.update(kw); return self.o.verify_transition_permit(p,**args)
    def test_permit_valid(self): self.assertEqual(self.pv(),'VERIFIED_D0_TRANSITION_PERMIT')
    def test_transition_bound(self): self.assertEqual(self.pv(expected_transition_root=R('bad')),'HOLD_TRANSITION_CONTEXT')
    def test_subject_bound(self): self.assertEqual(self.pv(expected_transition_subject_root=R('bad')),'HOLD_TRANSITION_SUBJECT')
    def test_deployment_bound(self): self.assertEqual(self.pv(expected_deployment_generation='dep-2'),'HOLD_DEPLOYMENT_CONTEXT')
    def test_source_currentness(self): self.assertEqual(self.pv(observed_source_root=R('new')),'HOLD_SOURCE_MISMATCH')
    def test_topology_currentness(self): self.assertEqual(self.pv(observed_target_topology_root=R('new')),'HOLD_TARGET_TOPOLOGY_MISMATCH')
    def test_permit_forgery(self): self.assertEqual(self.pv(replace(self.permit(),mac=R('bad'))),'HOLD_BAD_SIGNATURE')
    def test_permit_expired(self): self.assertEqual(self.pv(now=25),'HOLD_EXPIRED')
    def test_qwen38(self): self.assertEqual(self.s.model_family,'qwen3_8_dense')
    def test_omega(self): self.assertEqual(1,sum(omega8(s)=='KEEPER' for s in itertools.product(range(3),repeat=8)))
    def test_13d(self): self.assertEqual(1,sum(factored13d(s)=='KEEPER' for s in itertools.product(range(3),repeat=13)))
if __name__=='__main__': unittest.main()
