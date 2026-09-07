import random, unittest
from dataclasses import replace
from hashlib import sha256
from itertools import product
from transition_envelope import *
R=lambda s: sha256(s.encode()).hexdigest()
def core(tag='a'): return AdapterCore(R('base'),R('adapter-'+tag),R('config'),R('tok'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA',R('topology'))
def env(c=None,tag='e'):
    c=c or core(); return TransitionEnvelope(O1_RECEIPT_ROOT,R('base-core'),R('previous'),c.identity_root,R('runtime'),R('cache'),tag)
def trace(t,c):
    k=dict(command_id='cmd',attempt_id='att',idempotency_key='idem',source_envelope_digest=t.source_envelope_digest,transition_root=t.transition_root,training_admission_root=t.training_admission_root,adapter_core_root=c.identity_root,runtime_root=t.inference_runtime_root)
    return Ack(**k,ordinal=1),Result(**k,ordinal=2)
class T(unittest.TestCase):
    def test_exact_admit(self):
        c=core(); t=env(c); a,r=trace(t,c); self.assertEqual(verify_transition(c,t,a,r,t.source_envelope_digest),'ADMIT_D0_PROOF_CARRYING_TRANSITION')
    def test_no_trace(self):
        c=core(); t=env(c); self.assertEqual(verify_transition(c,t,None,None,t.source_envelope_digest),'HOLD_UNBOUND_PHYSICAL_SUCCESS')
    def test_independent_digest_required(self):
        c=core(); t=env(c); a,r=trace(t,c); self.assertEqual(verify_transition(c,t,a,r,R('shared-only')),'HOLD_SOURCE_RECOMPUTE_MISMATCH')
    def test_core_mismatch(self):
        c=core(); t=env(c); a,r=trace(t,c); self.assertEqual(verify_transition(core('b'),t,a,r,t.source_envelope_digest),'HOLD_ADAPTER_CORE_MISMATCH')
    def test_runtime_tamper(self):
        c=core(); t=env(c); a,r=trace(t,c); r=replace(r,runtime_root=R('other')); self.assertEqual(verify_transition(c,t,a,r,t.source_envelope_digest),'HOLD_TRANSITION_IDENTITY_MISMATCH')
    def test_command_tamper(self):
        c=core(); t=env(c); a,r=trace(t,c); r=replace(r,attempt_id='other'); self.assertEqual(verify_transition(c,t,a,r,t.source_envelope_digest),'HOLD_COMMAND_BINDING_MISMATCH')
    def test_order(self):
        c=core(); t=env(c); a,r=trace(t,c); r=replace(r,ordinal=1); self.assertEqual(verify_transition(c,t,a,r,t.source_envelope_digest),'HOLD_TEMPORAL_ORDER')
    def test_provider_fail(self):
        c=core(); t=env(c); a,r=trace(t,c); r=replace(r,provider_success=False); self.assertEqual(verify_transition(c,t,a,r,t.source_envelope_digest),'HOLD_PROVIDER_RESULT')
    def test_glm_still_not_admitted(self):
        with self.assertRaises(ValueError): AdapterCore(R('b'),R('a'),R('c'),R('t'),AIRLLM_COMMIT,'glm53','AirLLMLoRA',R('x'))
    def test_source_drift(self):
        with self.assertRaises(ValueError): AdapterCore(R('b'),R('a'),R('c'),R('t'),'0'*40,'qwen3_5','AirLLMLoRA',R('x'))
    def test_runtime_adapter_forbids_merge_grid(self):
        c=core()
        with self.assertRaises(ValueError): TransitionEnvelope(O1_RECEIPT_ROOT,R('b'),R('f'),c.identity_root,R('r'),R('p'),'g',merge_grid_root=R('grid'))
    def test_merge_requires_grid(self):
        c=core()
        with self.assertRaises(ValueError): TransitionEnvelope(O1_RECEIPT_ROOT,R('b'),R('f'),c.identity_root,R('r'),R('p'),'g',activation_mode='merged_checkpoint')
    def test_merge_exact(self):
        c=core(); t=TransitionEnvelope(O1_RECEIPT_ROOT,R('b'),R('f'),c.identity_root,R('r'),R('p'),'g','merged_checkpoint',R('grid')); self.assertTrue(isroot(t.transition_root))
    def test_locality_adapter(self):
        c1,c2,c3=core('1'),core('2'),core('3'); ts=[env(c1,'1'),env(c2,'2'),env(c3,'3')]; self.assertEqual(minimum_reopen_cone(c2.identity_root,ts),(1,))
    def test_locality_runtime(self):
        c1,c2=core('1'),core('2'); t1,t2=env(c1,'1'),env(c2,'2'); t2=replace(t2,inference_runtime_root=R('r2')); self.assertEqual(minimum_reopen_cone(R('r2'),[t1,t2]),(1,))
    def test_omega8(self):
        k=sum(omega8(s)=='KEEPER' for s in product(range(3),repeat=8)); self.assertEqual(k,1)
    def test_factored13d(self):
        k=sum(factored13d(s)=='KEEPER' for s in product(range(3),repeat=13)); self.assertEqual(k,1)
    def test_random_tamper_campaign(self):
        rng=random.Random(90802); c=core(); t=env(c); a,r=trace(t,c); killed=0
        fields=['source_envelope_digest','transition_root','training_admission_root','adapter_core_root','runtime_root']
        for i in range(10000):
            f=fields[rng.randrange(len(fields))]; rr=replace(r,**{f:R(f+str(i))})
            if verify_transition(c,t,a,rr,t.source_envelope_digest)!='ADMIT_D0_PROOF_CARRYING_TRANSITION': killed+=1
        self.assertEqual(killed,10000)
    def test_identity_deterministic(self): self.assertEqual(core().identity_root,core().identity_root)
    def test_transition_deterministic(self):
        c=core(); self.assertEqual(env(c).transition_root,env(c).transition_root)
    def test_parent_ids_frozen(self): self.assertNotEqual(PARENT_BOUNDARY,PARENT_PHYSICAL)
if __name__=='__main__': unittest.main()
