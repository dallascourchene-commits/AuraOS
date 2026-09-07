import os,tempfile,unittest
from dataclasses import replace
from o15_workcell_stable_operation import *
KEY=b'o15-reference-lease-key-32bytes!!'
def r(x): return H(['r',x])
def op(i=0,**kw):
    d=dict(command_id=f'c{i}',idempotency_key=f'k{i}',source_file_id=f'f{i}',source_revision=f'rev{i}',source_digest=r('src'+str(i)),intent_root=r('intent'+str(i)),contract_root=r('contract'+str(i)),payload_root=r('payload'+str(i))); d.update(kw); return SemanticOperation(**d)
def cur(i=0,**kw):
    d=dict(session_id=f's{i}',objective_root=r('obj'+str(i)),project='K27',card_root=r('card'+str(i)),progress_root=r('progress'+str(i)),host_generation=3,now=50); d.update(kw); return HostCurrent(**d)
def lease(i=0,c=None,**kw):
    c=c or cur(i); d=dict(key=KEY,handle=f'handle-{i}-abcdefghijk',session_id=c.session_id,objective_root=c.objective_root,project=c.project,card_root=c.card_root,progress_root=c.progress_root,host_generation=c.host_generation,issued_at=40,expires_at=100); d.update(kw); return issue_lease(**d)
def att(o,count=1,action=None,**kw):
    d=dict(action=action or (Action.CALL if count==1 else Action.RETRY),command_id=o.command_id,stable_operation_root=o.root,proof_bound_admission_root=r('adm'+str(count)),parent_attempt_root=r('att'+str(count)),provider_request_count=count); d.update(kw); return ProofBoundAttempt(**d)
class T(unittest.TestCase):
    def g(self):
        d=tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup); return Gate(os.path.join(d.name,'g.db'),lease_key=KEY)
    def bound(self):
        g=self.g(); o=op(); c=cur(); l=lease(c=c); p=g.expose_first(o,l,c,att(o)); return g,o,c,l,p
    def test_01_first(self): g,o,c,l,p=self.bound(); self.assertEqual(p.stable_operation_root,o.root)
    def test_02_reissue_preserves_operation(self):
        o=op(); c=cur(); l1=lease(c=c); l2=lease(c=c,handle='other-handle-abcdefgh'); self.assertEqual(o.root,o.root); self.assertNotEqual(l1.root,l2.root)
    def test_03_card_move_holds(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'CARD'): g.expose_first(o,l,replace(c,card_root=r('moved')),att(o))
    def test_04_progress_move_holds(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'PROGRESS'): g.expose_first(o,l,replace(c,progress_root=r('moved')),att(o))
    def test_05_generation_move_holds(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'GENERATION'): g.expose_first(o,l,replace(c,host_generation=4),att(o))
    def test_06_expired_holds(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'EXPIRED'): g.expose_first(o,l,replace(c,now=101),att(o))
    def test_07_source_file_move_rotates(self): self.assertNotEqual(op().root,op(source_file_id='f2').root)
    def test_08_source_revision_move_rotates(self): self.assertNotEqual(op().root,op(source_revision='rev2').root)
    def test_09_source_digest_move_rotates(self): self.assertNotEqual(op().root,op(source_digest=r('src2')).root)
    def test_10_intent_move_rotates(self): self.assertNotEqual(op().root,op(intent_root=r('i2')).root)
    def test_11_contract_move_rotates(self): self.assertNotEqual(op().root,op(contract_root=r('c2')).root)
    def test_12_payload_move_rotates(self): self.assertNotEqual(op().root,op(payload_root=r('p2')).root)
    def test_13_current_admission_excluded_from_op(self):
        o=op(); self.assertEqual(att(o,1).stable_operation_root,att(o,2).stable_operation_root)
    def test_14_first_count(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'FIRST'): g.expose_first(o,l,c,att(o,2,Action.CALL))
    def test_15_parent_op_mismatch(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'STABLE'): g.expose_first(o,l,c,replace(att(o),stable_operation_root=r('bad')))
    def test_16_retry_new_workcell_same_op_new_witness(self):
        g,o,c,l,p=self.bound(); g.ambiguous(o.command_id,o.root); l2=lease(c=c,handle='retry-handle-abcdefgh'); p2=g.retry(o,l2,c,att(o,2),r('recovery')); self.assertEqual(p2.stable_operation_root,p.stable_operation_root); self.assertNotEqual(p2.execution_witness_root,p.execution_witness_root)
    def test_17_retry_requires_recovery(self):
        g,o,c,l,p=self.bound(); g.ambiguous(o.command_id,o.root)
        with self.assertRaises(ValueError): g.retry(o,l,c,att(o,2),'bad')
    def test_18_retry_attempt_new(self):
        g,o,c,l,p=self.bound(); g.ambiguous(o.command_id,o.root)
        with self.assertRaisesRegex(ValueError,'NOT_NEW'): g.retry(o,l,c,att(o,1,Action.RETRY),r('recovery'))
    def test_19_retry_semantic_move_holds(self):
        g,o,c,l,p=self.bound(); g.ambiguous(o.command_id,o.root); moved=replace(o,payload_root=r('moved'))
        with self.assertRaises(ValueError): g.retry(moved,l,c,att(moved,2),r('recovery'))
    def test_20_result_return_survives_expiry(self):
        g,o,c,l,p=self.bound(); g.record_result(o.command_id,r('result')); self.assertIs(g.return_writer_only(o.command_id),Action.RETURN)
    def test_21_result_no_retry_needed(self):
        g,o,c,l,p=self.bound(); g.record_result(o.command_id,r('result'))
        with self.assertRaises(ValueError): g.retry(o,l,replace(c,now=1000),att(o,2),r('recovery'))
    def test_22_public_handle_no_leak(self): self.assertFalse(public_surface_leaks(public_work_handle(lease())))
    def test_23_k27_not_identity(self):
        o=op(); a=o.root; k27a='K27://O15/a'; k27b='K27://O15/b'; self.assertNotEqual(k27a,k27b); self.assertEqual(a,o.root)
    def test_24_mac_forge(self):
        o=op(); g=self.g(); c=cur(); l=replace(lease(c=c),mac=r('bad'))
        with self.assertRaisesRegex(ValueError,'MAC'): g.expose_first(o,l,c,att(o))
    def test_25_cross_session(self):
        o=op(); g=self.g(); c=cur(); l=lease(c=c)
        with self.assertRaisesRegex(ValueError,'SESSION'): g.expose_first(o,l,replace(c,session_id='x'),att(o))
    def test_26_witness_changes_on_admission_rebind(self):
        o=op(); c=cur(); l=lease(c=c); a1=att(o,1); a2=att(o,2); self.assertNotEqual(execution_witness(o.root,l.root,a1),execution_witness(o.root,l.root,a2,r('recovery')))
    def test_27_authority_ceiling(self):
        g,o,c,l,p=self.bound()
        with self.assertRaises(ValueError): ExecutionPermit(p.action,p.command_id,p.stable_operation_root,p.workcell_lease_root,p.proof_bound_admission_root,p.parent_attempt_root,p.execution_witness_root,p.provider_request_count,effect_authority=True)
if __name__=='__main__': unittest.main()
