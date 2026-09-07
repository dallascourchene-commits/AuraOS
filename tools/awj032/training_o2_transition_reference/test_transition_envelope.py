import itertools, unittest
from dataclasses import replace
from hashlib import sha256
from tools.awj032.training_o2_transition_reference.transition_envelope import *
from tools.awj032.training_r1_resolver_reference.training_admission_resolver import AdmissionSemantic, OwnerResolver
from tools.awj032.training_o1_reference.training_admission import SourceAuditVerifier,AdapterManifest,derived_expected_adapter_keys,h_bytes,admit as o1_admit
R=lambda s:sha256(s.encode()).hexdigest()

def o1_fixture():
    sv=SourceAuditVerifier({'src':b'source-secret'},'src',2); src=sv._issue_exact(observed_at=5)
    targets=('layers.0.q_proj','layers.0.v_proj'); keys=tuple(sorted(derived_expected_adapter_keys(targets))); values={k:k.encode() for k in keys}
    m=AdapterManifest(R('base'),R('cfg'),R('tok'),R('infer-runtime'),AIRLLM_COMMIT,'qwen3_8_dense','AirLLMLoRA',targets,16,32,False,keys,tuple(h_bytes(values[k]) for k in keys))
    a=o1_admit(source_verifier=sv,source=src,manifest=m,observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,observed_target_paths=set(targets),provided_adapter_values=values,observed_at=6)
    return sv,m,a

class TransitionTest(unittest.TestCase):
    def setUp(self):
        self.sv,self.m,self.o1=o1_fixture()
        self.semantic=AdmissionSemantic(self.o1.admission_root,self.o1.source_root,self.o1.adapter_root,self.o1.runtime_root,self.o1.target_topology_root,AIRLLM_COMMIT,'qwen3_8_dense','AirLLMLoRA')
        self.resolver=OwnerResolver({'owner':b'owner-secret'},'owner',4)
        self.receipt=self.resolver.issue(self.semantic,o1_admission=self.o1,source_verifier=self.sv,now=10,ttl=30)
        values_root=jhash(self.m.adapter_value_roots)
        self.core=AdapterCore(self.semantic.adapter_root,self.m.base_checkpoint_root,values_root,self.m.base_config_root,self.m.tokenizer_root,self.semantic.source_root,AIRLLM_COMMIT,'qwen3_8_dense','AirLLMLoRA',self.semantic.target_topology_root)
        self.intent=TransitionIntent(self.semantic.adapter_root,R('base-core'),R('from-core'),self.core.identity_root,self.semantic.runtime_root,R('cache'),'dep-1')
        self.permit=self.resolver.issue_transition_permit(self.receipt,transition_root=self.intent.intent_root,transition_subject_root=self.core.identity_root,deployment_generation='dep-1',now=12,ttl=20,observed_source_root=self.semantic.source_root,observed_adapter_root=self.semantic.adapter_root,observed_runtime_root=self.semantic.runtime_root,observed_target_topology_root=self.semantic.target_topology_root)
        self.env=TransitionEnvelope(self.intent,self.permit.permit_root)
        self.trace=PhysicalTraceAuthority({'provider':b'provider-secret'},'provider',5)
    def pair(self,provider_success=True):
        common=dict(command_id='cmd-1',attempt_id='att-1',idempotency_key='idem-1',source_envelope_digest=self.env.source_envelope_digest,transition_root=self.env.transition_root,admission_permit_root=self.env.admission_permit_root,adapter_core_root=self.core.identity_root,runtime_root=self.env.intent.inference_runtime_root)
        return self.trace.issue_ack(AckPayload(**common,ordinal=1)),self.trace.issue_result(ResultPayload(**common,ordinal=2,provider_success=provider_success))
    def verify(self,ack=None,result=None,**kw):
        if ack is None or result is None: ack,result=self.pair()
        args=dict(core=self.core,env=self.env,permit=self.permit,admission_resolver=self.resolver,trace_authority=self.trace,ack=ack,result=result,independently_recomputed_source_digest=self.env.source_envelope_digest,now=13,observed_source_root=self.semantic.source_root,observed_target_topology_root=self.semantic.target_topology_root); args.update(kw); return verify_transition(**args)
    def test_valid(self): self.assertEqual(self.verify(),'ADMIT_D0_PROOF_CARRYING_TRANSITION')
    def test_empty_ids_rejected(self):
        with self.assertRaises(ValueError): AckPayload('', 'a','i',R('s'),R('t'),R('p'),R('a'),R('r'),1)
    def test_success_explicit(self):
        with self.assertRaises(TypeError): ResultPayload('c','a','i',R('s'),R('t'),R('p'),R('a'),R('r'),2)
    def test_bad_ack_signature(self):
        a,r=self.pair(); self.assertEqual(self.verify(ack=replace(a,mac=R('bad')),result=r),'HOLD_ACK_SIGNATURE')
    def test_bad_result_signature(self):
        a,r=self.pair(); self.assertEqual(self.verify(ack=a,result=replace(r,mac=R('bad'))),'HOLD_RESULT_SIGNATURE')
    def test_provider_false(self):
        a,r=self.pair(False); self.assertEqual(self.verify(ack=a,result=r),'HOLD_PROVIDER_RESULT')
    def test_source_digest_recomputed(self): self.assertEqual(self.verify(independently_recomputed_source_digest=R('bad')),'HOLD_SOURCE_RECOMPUTE_MISMATCH')
    def test_permit_forgery_fails_before_or_at_signature(self):
        bad=replace(self.permit,mac=R('bad'))
        verdict=self.verify(permit=bad)
        self.assertIn(verdict,{'HOLD_ADMISSION_PERMIT_ROOT','HOLD_ADMISSION_PERMIT:HOLD_BAD_SIGNATURE'})
    def test_forged_permit_with_matching_envelope_hits_signature(self):
        bad=replace(self.permit,mac=R('bad')); env=TransitionEnvelope(self.intent,bad.permit_root)
        verdict=self.verify(permit=bad,env=env,independently_recomputed_source_digest=env.source_envelope_digest)
        self.assertEqual(verdict,'HOLD_ADMISSION_PERMIT:HOLD_BAD_SIGNATURE')
    def test_permit_adapter_specific(self):
        other=replace(self.core,o1_adapter_root=R('other')); self.assertEqual(self.verify(core=other),'HOLD_ADAPTER_CORE_MISMATCH')
    def test_subject_bound(self):
        bad=replace(self.permit,transition_subject_root=R('bad'),mac=self.permit.mac)
        verdict=self.verify(permit=bad)
        self.assertIn(verdict,{'HOLD_ADMISSION_PERMIT_ROOT','HOLD_TRANSITION_SUBJECT_BINDING'})
    def test_trace_identity_mismatch(self):
        a,r=self.pair(); bad=self.trace.issue_result(replace(r.payload,adapter_core_root=R('bad'))); self.assertEqual(self.verify(ack=a,result=bad),'HOLD_TRANSITION_IDENTITY_MISMATCH')
    def test_command_mismatch(self):
        a,r=self.pair(); bad=self.trace.issue_result(replace(r.payload,command_id='cmd-2')); self.assertEqual(self.verify(ack=a,result=bad),'HOLD_COMMAND_BINDING_MISMATCH')
    def test_temporal(self):
        a,r=self.pair(); bad=self.trace.issue_result(replace(r.payload,ordinal=0)); self.assertEqual(self.verify(ack=a,result=bad),'HOLD_TEMPORAL_ORDER')
    def test_qwen38(self): self.assertEqual(self.core.model_family,'qwen3_8_dense')
    def test_omega(self): self.assertEqual(1,sum(omega8(s)=='KEEPER' for s in itertools.product(range(3),repeat=8)))
    def test_13d(self): self.assertEqual(1,sum(factored13d(s)=='KEEPER' for s in itertools.product(range(3),repeat=13)))
if __name__=='__main__': unittest.main()
