import unittest
from dataclasses import replace
from hashlib import sha256
from tools.awj032.training_o1_reference.training_admission import *
from tools.awj032.training_r1_resolver_reference.training_admission_resolver import *
R=lambda s:sha256(s.encode()).hexdigest()
def fixture(fam='qwen3_8_dense',trainer='AirLLMLoRA'):
    sv=SourceAuditVerifier({'src':b's'},'src',2);src=sv._issue_exact(observed_at=1);ts=('l.q_proj','l.v_proj');ks=tuple(sorted(derived_expected_adapter_keys(ts)));vv={k:k.encode() for k in ks};m=AdapterManifest(R('b'),R('c'),R('t'),R('r'),AIRLLM_COMMIT,fam,trainer,ts,8,16,False,ks,tuple(h_bytes(vv[k]) for k in ks));a=admit(source_verifier=sv,source=src,manifest=m,observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,observed_target_paths=set(ts),provided_adapter_values=vv,observed_at=2);return sv,m,a
def sem(a): return AdmissionSemantic(a.admission_root,a.source_root,a.adapter_root,a.runtime_root,a.target_topology_root,a.base_checkpoint_root,a.base_config_root,a.tokenizer_root,a.adapter_values_root,AIRLLM_COMMIT,a.model_family,a.trainer_class)
class T(unittest.TestCase):
    def setUp(self): self.sv,self.m,self.a=fixture();self.s=sem(self.a);self.o=OwnerResolver({'k':b'owner'},'k',3);self.r=self.o.issue(self.s,o1_admission=self.a,source_verifier=self.sv,now=10,ttl=20)
    def test_valid(self): self.assertEqual(self.o.verify(self.r,now=15,expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root),'VERIFIED_D0_ADMISSION')
    def test_empty_key(self):
        with self.assertRaises(ValueError): OwnerResolver({'k':b''},'k',3)
    def test_family_launder_rejected(self):
        bad=replace(self.s,model_family='qwen4_exp',trainer_class='AirLLMLoRAQwen4Exp')
        with self.assertRaises(ValueError): self.o.issue(bad,o1_admission=self.a,source_verifier=self.sv,now=10,ttl=20)
    def test_preimage_launder_rejected(self):
        bad=replace(self.s,base_checkpoint_root=R('other'))
        with self.assertRaises(ValueError): self.o.issue(bad,o1_admission=self.a,source_verifier=self.sv,now=10,ttl=20)
    def test_nan(self): self.assertEqual(self.o.verify(self.r,now=float('nan'),expected_source_root=self.s.source_root,expected_adapter_root=self.s.adapter_root,expected_runtime_root=self.s.runtime_root,expected_target_topology_root=self.s.target_topology_root),'HOLD_INVALID_TIME')
    def permit(self,ttl=100): return self.o.issue_transition_permit(self.r,transition_root=R('tr'),transition_subject_root=R('sub'),deployment_generation='d1',now=15,ttl=ttl,observed_source_root=self.s.source_root,observed_adapter_root=self.s.adapter_root,observed_runtime_root=self.s.runtime_root,observed_target_topology_root=self.s.target_topology_root)
    def test_permit_cap(self): self.assertEqual(self.permit().expires_at,self.r.expires_at)
    def test_permit_family_preimage_copied(self):
        p=self.permit();self.assertEqual((p.model_family,p.base_checkpoint_root,p.adapter_values_root),(self.a.model_family,self.a.base_checkpoint_root,self.a.adapter_values_root))
    def test_permit_context(self):
        p=self.permit();self.assertEqual(self.o.verify_transition_permit(p,now=16,expected_transition_root=R('bad'),expected_transition_subject_root=R('sub'),expected_deployment_generation='d1',observed_source_root=self.s.source_root,observed_adapter_root=self.s.adapter_root,observed_runtime_root=self.s.runtime_root,observed_target_topology_root=self.s.target_topology_root),'HOLD_TRANSITION_CONTEXT')
if __name__=='__main__': unittest.main()
