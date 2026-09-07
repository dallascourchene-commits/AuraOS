import unittest
from dataclasses import replace
from hashlib import sha256
from tools.awj032.training_o1_reference.training_admission import *
from tools.awj032.training_r1_resolver_reference.training_admission_resolver import AdmissionSemantic,OwnerResolver
from tools.awj032.training_o3_delegated_bridge_reference.delegated_training_bridge import *
R=lambda s:sha256(s.encode()).hexdigest()
def chain():
    sv=SourceAuditVerifier({'s':b's'},'s',2);src=sv._issue_exact(observed_at=1);ts=('l.q_proj','l.v_proj');ks=tuple(sorted(derived_expected_adapter_keys(ts)));vv={k:k.encode() for k in ks};m=AdapterManifest(R('b'),R('c'),R('t'),R('run'),AIRLLM_COMMIT,'qwen3_5','AirLLMLoRA',ts,8,16,False,ks,tuple(h_bytes(vv[k]) for k in ks));a=admit(source_verifier=sv,source=src,manifest=m,observed_base_checkpoint_root=m.base_checkpoint_root,observed_config_root=m.base_config_root,observed_tokenizer_root=m.tokenizer_root,observed_runtime_root=m.runtime_root,observed_target_paths=set(ts),provided_adapter_values=vv,observed_at=2);s=AdmissionSemantic(a.admission_root,a.source_root,a.adapter_root,a.runtime_root,a.target_topology_root,a.base_checkpoint_root,a.base_config_root,a.tokenizer_root,a.adapter_values_root,AIRLLM_COMMIT,a.model_family,a.trainer_class);o=OwnerResolver({'o':b'o'},'o',3);r=o.issue(s,o1_admission=a,source_verifier=sv,now=10,ttl=100);op=TrainingOperation(R('m'),a.source_root,R('i'),R('c'),R('p'),a.base_checkpoint_root,a.base_config_root,a.tokenizer_root,a.runtime_root,a.adapter_root,a.target_topology_root,AIRLLM_COMMIT,a.model_family,a.trainer_class);return sv,m,a,s,o,r,op
class T(unittest.TestCase):
    def setUp(self):
        self.sv,self.m,self.a,self.s,self.o,self.r,self.op=chain();self.host=HostWorkcellAuthority({'h':b'h'},'h',4);self.plan=R('plan');self.handle='WK';self.worker='non_sol_worker';self.steps=64;sub=capsule_subject_root(operation_root=self.op.operation_root,opaque_work_handle=self.handle,source_identity_root=self.op.source_identity_root,adapter_spec_root=self.op.adapter_spec_root,admission_semantic_root=self.s.semantic_root,admission_receipt_root=self.r.receipt_root,test_plan_root=self.plan,worker_class=self.worker,max_steps=self.steps);self.lease=self.host.issue(operation_root=self.op.operation_root,capsule_subject_root=sub,admission_semantic_root=self.s.semantic_root,admission_receipt_root=self.r.receipt_root,now=20,ttl=50);self.cap=DelegatedTrainingCapsule(self.op.operation_root,self.handle,self.op.source_identity_root,self.op.adapter_spec_root,self.s.semantic_root,self.r.receipt_root,self.lease.lease_root,self.plan,self.worker,self.steps);self.attempt=DurableTrainingAttempt(self.op.operation_root,self.cap.capsule_root,R('a'),R('i'),R('rp'));self.rec=RecoveryAuthority({'r':b'r'},'r',2)
    def admit(self,cap=None,lease=None,now=21): return admit_delegation(operation=self.op,admission_receipt=self.r,admission_resolver=self.o,lease=lease or self.lease,workcell_authority=self.host,capsule=cap or self.cap,now=now)
    def test_valid(self): self.assertEqual(self.admit(),'ADMIT_D0_DELEGATED_TRAINING_PROPOSAL_ONLY')
    def test_direct_o1_signing_forbidden(self):
        with self.assertRaises(ValueError): self.sv.sign_admission(action='ADMIT_D0_ADAPTER_LOAD')
    def test_nan_lease_issue(self):
        with self.assertRaises(ValueError): self.host.issue(operation_root=self.op.operation_root,capsule_subject_root=self.cap.subject_root,admission_semantic_root=self.s.semantic_root,admission_receipt_root=self.r.receipt_root,now=float('nan'),ttl=1)
    def test_nan_lease_verify(self): self.assertEqual(self.admit(now=float('nan')),'HOLD_ADMISSION_CURRENTNESS:HOLD_INVALID_TIME')
    def test_empty_host_key(self):
        with self.assertRaises(ValueError): HostWorkcellAuthority({'h':b''},'h',1)
    def test_capsule_worker_mutation_rejected(self):
        c=replace(self.cap,worker_class='isolated_training_worker');self.assertEqual(self.admit(cap=c),'HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_BINDING')
    def test_capsule_steps_mutation_rejected(self):
        c=replace(self.cap,max_steps=65);self.assertEqual(self.admit(cap=c),'HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_BINDING')
    def test_capsule_plan_mutation_rejected(self):
        c=replace(self.cap,test_plan_root=R('other'));self.assertEqual(self.admit(cap=c),'HOLD_WORKCELL_CURRENTNESS:HOLD_WORKCELL_BINDING')
    def test_recovery_stale_not_started_rejected(self):
        old=self.rec.issue(self.attempt.attempt_root,'NOT_STARTED',30);new=self.rec.issue(self.attempt.attempt_root,'COMPLETED',31);self.assertEqual(retry_decision(self.attempt,old,self.rec),'HOLD_RECOVERY_SUPERSEDED');self.assertEqual(retry_decision(self.attempt,new,self.rec),'RETURN_ONLY_COMPLETED')
    def test_recovery_monotonic_time(self):
        self.rec.issue(self.attempt.attempt_root,'UNKNOWN',30)
        with self.assertRaises(ValueError): self.rec.issue(self.attempt.attempt_root,'NOT_STARTED',30)
    def test_empty_recovery_key(self):
        with self.assertRaises(ValueError): RecoveryAuthority({'r':b''},'r',1)
if __name__=='__main__': unittest.main()
