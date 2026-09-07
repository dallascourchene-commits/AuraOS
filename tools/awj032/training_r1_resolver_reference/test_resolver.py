import itertools, random, unittest
from dataclasses import replace
from hashlib import sha256
from training_admission_resolver import *
R=lambda c: sha256(c.encode()).hexdigest()

class T(unittest.TestCase):
    def setUp(self):
        self.sem=AdmissionSemantic(R('source'),R('adapter'),R('runtime'),R('topology'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA')
        self.res=OwnerResolver({'k1':b'secret-one','k2':b'secret-two'},'k1',7)
        self.rcpt=self.res.issue(self.sem,now=1000,ttl=60)
        self.bind=TransitionAdmissionBinding(R('transition'),self.sem.semantic_root,self.rcpt.receipt_root,self.sem.adapter_root,self.sem.runtime_root,'deploy-7')
    def test_valid(self): self.assertEqual('VERIFIED_D0_ADMISSION',verify_transition_admission(self.bind,self.rcpt,self.res,now=1030))
    def test_plain_shape_forgery(self):
        fake=replace(self.rcpt,mac=R('fake')); self.assertEqual('HOLD_BAD_SIGNATURE',verify_transition_admission(replace(self.bind,admission_receipt_root=fake.receipt_root),fake,self.res,now=1030))
    def test_expired(self): self.assertEqual('HOLD_EXPIRED',verify_transition_admission(self.bind,self.rcpt,self.res,now=1060))
    def test_future(self): self.assertEqual('HOLD_NOT_YET_VALID',verify_transition_admission(self.bind,self.rcpt,self.res,now=999))
    def test_generation(self):
        newer=OwnerResolver({'k1':b'secret-one'},'k1',8); self.assertEqual('HOLD_GENERATION_CURRENTNESS',verify_transition_admission(self.bind,self.rcpt,newer,now=1030))
    def test_key_rotation(self):
        rot=OwnerResolver({'k1':b'secret-one','k2':b'secret-two'},'k2',7); self.assertEqual('HOLD_KEY_CURRENTNESS',verify_transition_admission(self.bind,self.rcpt,rot,now=1030))
    def test_semantic_stable_receipt_rotates(self):
        r2=self.res.issue(self.sem,now=1010,ttl=60); self.assertEqual(self.sem.semantic_root,r2.semantic.semantic_root); self.assertNotEqual(self.rcpt.receipt_root,r2.receipt_root)
    def test_binding_receipt(self): self.assertEqual('HOLD_RECEIPT_BINDING_MISMATCH',verify_transition_admission(replace(self.bind,admission_receipt_root=R('other')),self.rcpt,self.res,now=1030))
    def test_binding_semantic(self): self.assertEqual('HOLD_SEMANTIC_BINDING_MISMATCH',verify_transition_admission(replace(self.bind,admission_semantic_root=R('other')),self.rcpt,self.res,now=1030))
    def test_binding_adapter(self): self.assertEqual('HOLD_ADAPTER_BINDING_MISMATCH',verify_transition_admission(replace(self.bind,adapter_root=R('other')),self.rcpt,self.res,now=1030))
    def test_binding_runtime(self): self.assertEqual('HOLD_RUNTIME_BINDING_MISMATCH',verify_transition_admission(replace(self.bind,runtime_root=R('other')),self.rcpt,self.res,now=1030))
    def test_external_expected_source(self): self.assertEqual('HOLD_SOURCE_MISMATCH',self.res.verify(self.rcpt,now=1030,expected_source_root=R('bad'),expected_adapter_root=self.sem.adapter_root,expected_runtime_root=self.sem.runtime_root,expected_target_topology_root=self.sem.target_topology_root))
    def test_external_expected_runtime(self): self.assertEqual('HOLD_RUNTIME_MISMATCH',self.res.verify(self.rcpt,now=1030,expected_source_root=self.sem.source_root,expected_adapter_root=self.sem.adapter_root,expected_runtime_root=R('bad'),expected_target_topology_root=self.sem.target_topology_root))
    def test_external_expected_target(self): self.assertEqual('HOLD_TARGET_TOPOLOGY_MISMATCH',self.res.verify(self.rcpt,now=1030,expected_source_root=self.sem.source_root,expected_adapter_root=self.sem.adapter_root,expected_runtime_root=self.sem.runtime_root,expected_target_topology_root=R('bad')))
    def test_glm_hold_constructor(self):
        with self.assertRaises(ValueError): AdmissionSemantic(R('s'),R('a'),R('r'),R('t'),AIRLLM_COMMIT,'glm','AirLLMLoRA')
    def test_source_generation_hold(self):
        with self.assertRaises(ValueError): AdmissionSemantic(R('s'),R('a'),R('r'),R('t'),'0'*40,'qwen3_5','AirLLMLoRA')
    def test_authority_widening_rejected(self):
        with self.assertRaises(ValueError): AdmissionSemantic(R('s'),R('a'),R('r'),R('t'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA',authority='EXECUTE')
    def test_minimum_reopen(self):
        r2=self.res.issue(self.sem,now=1010,ttl=60); b2=replace(self.bind,transition_root=R('t2'),admission_receipt_root=r2.receipt_root)
        sem3=AdmissionSemantic(R('source3'),R('adapter3'),R('runtime3'),R('topology3'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA')
        r3=self.res.issue(sem3,now=1010,ttl=60)
        b3=TransitionAdmissionBinding(R('t3'),sem3.semantic_root,r3.receipt_root,sem3.adapter_root,sem3.runtime_root,'deploy-3')
        self.assertEqual((0,1),minimum_reopen_cone(self.sem.semantic_root,[self.bind,b2,b3]))
        self.assertEqual((1,),minimum_reopen_cone(r2.receipt_root,[self.bind,b2,b3]))
    def test_omega8(self):
        keep=0
        for s in itertools.product(range(3),repeat=8): keep += omega8(s)=='KEEPER'
        self.assertEqual(1,keep)
    def test_factored13d(self):
        keep=0
        for s in itertools.product(range(3),repeat=13): keep += factored13d(s)=='KEEPER'
        self.assertEqual(1,keep)
    def test_random_forgery_campaign(self):
        rng=random.Random(7321); escapes=0
        for i in range(10000):
            fake=replace(self.rcpt,mac=sha256(str(rng.random()).encode()).hexdigest())
            b=replace(self.bind,admission_receipt_root=fake.receipt_root)
            escapes += verify_transition_admission(b,fake,self.res,now=1030)=='VERIFIED_D0_ADMISSION'
        self.assertEqual(0,escapes)
    def test_random_currentness_campaign(self):
        rng=random.Random(881); bad=0
        for _ in range(10000):
            now=rng.randrange(900,1150)
            got=verify_transition_admission(self.bind,self.rcpt,self.res,now=now)
            expected='VERIFIED_D0_ADMISSION' if 1000<=now<1060 else ('HOLD_NOT_YET_VALID' if now<1000 else 'HOLD_EXPIRED')
            bad += got!=expected
        self.assertEqual(0,bad)

if __name__=='__main__': unittest.main()
