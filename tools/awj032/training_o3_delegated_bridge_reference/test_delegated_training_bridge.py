import itertools, unittest
from dataclasses import replace
from hashlib import sha256

from tools.awj032.training_r1_resolver_reference.training_admission_resolver import AdmissionSemantic, OwnerResolver
from tools.awj032.training_o1_reference.training_admission import SourceAuditVerifier
from tools.awj032.training_o3_delegated_bridge_reference.delegated_training_bridge import *
R=lambda s:sha256(s.encode()).hexdigest()

class T(unittest.TestCase):
    def setUp(self):
        self.op=TrainingOperation(R('mission'),R('source'),R('intent'),R('contract'),R('payload'),R('base'),R('config'),R('tokenizer'),R('runtime'),R('adapter'),R('topology'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA')
        self.source_ver=SourceAuditVerifier({'src':b'source-secret'},'src',2)
        self.o1=self.source_ver.sign_admission(action='ADMIT_D0_ADAPTER_LOAD',reason='O3_TEST_INHERITED_O1',source_root=self.op.source_identity_root,adapter_root=self.op.adapter_spec_root,runtime_root=self.op.runtime_root,target_topology_root=self.op.target_topology_root,observed_at=990)
        self.adm_res=OwnerResolver({'a1':b'admission-secret'},'a1',4)
        self.sem=AdmissionSemantic(self.o1.admission_root,self.op.source_identity_root,self.op.adapter_spec_root,self.op.runtime_root,self.op.target_topology_root,AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA')
        self.receipt=self.adm_res.issue(self.sem,o1_admission=self.o1,source_verifier=self.source_ver,now=1000,ttl=100)
        self.host=HostWorkcellAuthority({'h1':b'host-secret'},'h1',9)
        self.current_capsule=R('current-capsule')
        self.lease=self.host.issue(operation_root=self.op.operation_root,current_capsule_root=self.current_capsule,admission_semantic_root=self.sem.semantic_root,admission_receipt_root=self.receipt.receipt_root,now=1000,ttl=80)
        self.capsule=DelegatedTrainingCapsule(self.op.operation_root,'WK-opaque-7',self.op.source_identity_root,self.op.adapter_spec_root,self.sem.semantic_root,self.receipt.receipt_root,self.lease.lease_root,R('test-plan'),'non_sol_worker',64)
        self.attempt=DurableTrainingAttempt(self.op.operation_root,self.capsule.capsule_root,R('attempt'),R('idem'),R('recovery-policy'))
        self.proposal=WorkerProposal(self.capsule.capsule_root,self.attempt.attempt_root,R('proposal-adapter'),R('metrics'),R('tests'),'non_sol_worker',R('output'))
        self.recovery=RecoveryAuthority({'r1':b'recovery-secret'},'r1',2)
    def admit(self,**kw):
        d=dict(operation=self.op,admission_receipt=self.receipt,admission_resolver=self.adm_res,lease=self.lease,workcell_authority=self.host,capsule=self.capsule,current_capsule_root=self.current_capsule,now=1030);d.update(kw);return admit_delegation(**d)
    def validate(self,**kw):
        d=dict(operation=self.op,admission_receipt=self.receipt,admission_resolver=self.adm_res,lease=self.lease,workcell_authority=self.host,capsule=self.capsule,attempt=self.attempt,proposal=self.proposal,current_capsule_root=self.current_capsule,now=1030);d.update(kw);return validate_worker_proposal(**d)
    def test_valid_delegation(self): self.assertEqual('ADMIT_D0_DELEGATED_TRAINING_PROPOSAL_ONLY',self.admit())
    def test_valid_proposal(self): self.assertEqual('ADMIT_D0_ADAPTER_PROPOSAL_FOR_HOST_REVIEW',self.validate())
    def test_glm_denied(self):
        with self.assertRaises(ValueError): TrainingOperation(R('m'),R('s'),R('i'),R('c'),R('p'),R('b'),R('g'),R('t'),R('r'),R('a'),R('top'),AIRLLM_COMMIT,'glm','AirLLMLoRA')
    def test_forged_admission(self):
        bad=replace(self.receipt,mac=R('fake')); c=replace(self.capsule,admission_receipt_root=bad.receipt_root)
        l=self.host.issue(operation_root=self.op.operation_root,current_capsule_root=self.current_capsule,admission_semantic_root=self.sem.semantic_root,admission_receipt_root=bad.receipt_root,now=1000,ttl=80)
        c=replace(c,workcell_lease_root=l.lease_root)
        self.assertTrue(self.admit(admission_receipt=bad,lease=l,capsule=c).startswith('HOLD_ADMISSION_CURRENTNESS:HOLD_BAD_SIGNATURE'))
    def test_expired_admission(self): self.assertTrue(self.admit(now=1100).startswith('HOLD_ADMISSION_CURRENTNESS:HOLD_EXPIRED'))
    def test_expired_workcell(self): self.assertTrue(self.admit(now=1080).startswith('HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_EXPIRED'))
    def test_workcell_generation(self):
        h=HostWorkcellAuthority({'h1':b'host-secret'},'h1',10); self.assertTrue(self.admit(workcell_authority=h).startswith('HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_GENERATION'))
    def test_wrong_current_capsule(self): self.assertTrue(self.admit(current_capsule_root=R('other')).startswith('HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_BINDING'))
    def test_source_movement_rotates_operation(self):
        n=replace(self.op,source_identity_root=R('source2')); self.assertEqual('NEW_SEMANTIC_OPERATION',semantic_operation_reopen(self.op,n))
    def test_benign_workcell_reissue_preserves_operation(self):
        l2=self.host.issue(operation_root=self.op.operation_root,current_capsule_root=R('capsule2'),admission_semantic_root=self.sem.semantic_root,admission_receipt_root=self.receipt.receipt_root,now=1010,ttl=80)
        self.assertEqual(self.op.operation_root,l2.operation_root); self.assertNotEqual(self.lease.lease_root,l2.lease_root)
    def test_capsule_operation_mismatch(self): self.assertEqual('HOLD_OPERATION_BINDING',self.admit(capsule=replace(self.capsule,operation_root=R('bad'))))
    def test_capsule_source_mismatch(self): self.assertEqual('HOLD_SOURCE_IDENTITY',self.admit(capsule=replace(self.capsule,source_identity_root=R('bad'))))
    def test_capsule_adapter_mismatch(self): self.assertEqual('HOLD_ADAPTER_SPEC',self.admit(capsule=replace(self.capsule,adapter_spec_root=R('bad'))))
    def test_capsule_lease_mismatch(self): self.assertEqual('HOLD_WORKCELL_LEASE_ROOT',self.admit(capsule=replace(self.capsule,workcell_lease_root=R('bad'))))
    def test_private_fields_absent(self): self.assertTrue(validate_delegate_payload(self.capsule)); self.assertFalse(set(self.capsule.public_payload()) & PROHIBITED_DELEGATE_FIELDS)
    def test_attempt_binding(self): self.assertEqual('HOLD_DURABLE_ATTEMPT_BINDING',self.validate(attempt=replace(self.attempt,capsule_root=R('bad'))))
    def test_proposal_capsule(self): self.assertEqual('HOLD_PROPOSAL_CAPSULE',self.validate(proposal=replace(self.proposal,capsule_root=R('bad'))))
    def test_proposal_attempt(self): self.assertEqual('HOLD_PROPOSAL_ATTEMPT',self.validate(proposal=replace(self.proposal,attempt_root=R('bad'))))
    def test_proposal_worker(self): self.assertEqual('HOLD_PROPOSAL_WORKER_CLASS',self.validate(proposal=replace(self.proposal,worker_class='isolated_training_worker')))
    def test_worker_authority_widening_constructor(self):
        with self.assertRaises(ValueError): replace(self.proposal,authority='CHECKPOINT_MUTATION')
    def test_retry_not_started(self): self.assertEqual('RETRY_CANDIDATE_D0',retry_decision(self.attempt,self.recovery.issue(self.attempt.attempt_root,'NOT_STARTED',1040),self.recovery))
    def test_retry_unknown(self): self.assertEqual('HOLD_RECONCILE_UNKNOWN',retry_decision(self.attempt,self.recovery.issue(self.attempt.attempt_root,'UNKNOWN',1040),self.recovery))
    def test_retry_completed(self): self.assertEqual('RETURN_ONLY_COMPLETED',retry_decision(self.attempt,self.recovery.issue(self.attempt.attempt_root,'COMPLETED',1040),self.recovery))
    def test_retry_forged(self):
        v=self.recovery.issue(self.attempt.attempt_root,'NOT_STARTED',1040); self.assertEqual('HOLD_RECOVERY_SIGNATURE',retry_decision(self.attempt,replace(v,mac=R('bad')),self.recovery))
    def test_minimum_reopen(self):
        c2=replace(self.capsule,opaque_work_handle='WK2',test_plan_root=R('plan2'))
        op3=replace(self.op,source_identity_root=R('source3'),adapter_spec_root=R('adapter3')); o13=self.source_ver.sign_admission(action='ADMIT_D0_ADAPTER_LOAD',reason='O3_TEST_NEW_OPERATION',source_root=op3.source_identity_root,adapter_root=op3.adapter_spec_root,runtime_root=op3.runtime_root,target_topology_root=op3.target_topology_root,observed_at=991); sem3=AdmissionSemantic(o13.admission_root,op3.source_identity_root,op3.adapter_spec_root,op3.runtime_root,op3.target_topology_root,AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA'); r3=self.adm_res.issue(sem3,o1_admission=o13,source_verifier=self.source_ver,now=1000,ttl=100)
        l3=self.host.issue(operation_root=op3.operation_root,current_capsule_root=self.current_capsule,admission_semantic_root=sem3.semantic_root,admission_receipt_root=r3.receipt_root,now=1000,ttl=80)
        c3=DelegatedTrainingCapsule(op3.operation_root,'WK3',op3.source_identity_root,sem3.adapter_root,sem3.semantic_root,r3.receipt_root,l3.lease_root,R('plan3'),'non_sol_worker',64)
        self.assertEqual((0,1),minimum_reopen_cone(self.op.operation_root,[self.capsule,c2,c3]))
    def test_omega8(self): self.assertEqual(1,sum(omega8(s)=='KEEPER' for s in itertools.product(range(3),repeat=8)))
    def test_factored13d(self): self.assertEqual(1,sum(factored13d(s)=='KEEPER' for s in itertools.product(range(3),repeat=13)))

if __name__=='__main__': unittest.main()
