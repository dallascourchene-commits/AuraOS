import os,tempfile,unittest,hashlib
from tools.project006.runtime_activation_transaction import *
H=lambda s:hashlib.sha256(s.encode()).hexdigest()
KEY=b'activation-key'

def plan(): return ActivationPlan('act-1',H('capsule'),H('prepare'),H('target'),'host-1',H('old-proc'),H('old-pop'))
def loaded(p=None,**kw):
    p=p or plan(); base=dict(process_binding_root=H('new-proc'),effect_time_witness_root=H('effect'),serving_population_root=H('new-pop'))
    base.update(kw); return sign_loaded(KEY,p,**base)
class T(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(); self.j=ActivationJournal(os.path.join(self.t.name,'a.db')); self.p=plan(); self.j.prepare(self.p,o21_state='COMMITTED',o21_target_release_root=self.p.target_release_root,o21_commit_receipt_root=H('commit'))
    def tearDown(self): self.t.cleanup()
    def retire(self,**kw): return self.j.retire_old(self.p,sign_retirement(KEY,self.p,**kw),key=KEY,now_ms=1500)
    def load(self,e=None): return self.j.bind_loaded(self.p,e or loaded(self.p),key=KEY,now_ms=1500)
    def test_happy(self):
        self.retire(); e=loaded(self.p); self.load(e); pp=sign_postinstall(KEY,self.p,e,o20_receipt_root=H('o20'),o19_receipt_root=H('o19')); self.j.bind_postinstall(self.p,pp,e,key=KEY,now_ms=1500); x=self.j.mark_activated(self.p,o21_state='ACCEPTED',o21_acceptance_receipt_root=H('accepted')); self.assertEqual(x['state'],'ACTIVATED'); self.assertFalse(x['effect_authority'])
    def test_requires_committed(self):
        q=ActivationJournal(os.path.join(self.t.name,'b.db'))
        with self.assertRaisesRegex(ActivationError,'O21_NOT_COMMITTED'): q.prepare(self.p,o21_state='ACCEPTED',o21_target_release_root=self.p.target_release_root,o21_commit_receipt_root=H('c'))
    def test_old_workers_hold(self):
        with self.assertRaisesRegex(ActivationError,'OLD_SERVING_GENERATION_REMAINS'): self.retire(remaining_old_workers=1)
    def test_retirement_mac(self):
        e=sign_retirement(KEY,self.p); object.__setattr__(e,'mac_hex',H('bad'))
        with self.assertRaisesRegex(ActivationError,'RETIREMENT_UNAUTHENTICATED'): self.j.retire_old(self.p,e,key=KEY,now_ms=1500)
    def test_loaded_legacy_process_alias(self):
        self.retire(); e=loaded(self.p,process_binding_root=self.p.prior_process_binding_root)
        with self.assertRaisesRegex(ActivationError,'OLD_GENERATION_ALIAS'): self.load(e)
    def test_loaded_population_alias(self):
        self.retire(); e=loaded(self.p,serving_population_root=self.p.prior_serving_population_root)
        with self.assertRaisesRegex(ActivationError,'OLD_GENERATION_ALIAS'): self.load(e)
    def test_loaded_hold_disposition(self):
        self.retire(); e=loaded(self.p,disposition='HOLD')
        with self.assertRaisesRegex(ActivationError,'LOADED_PROCESS_NOT_CURRENT'): self.load(e)
    def test_loaded_stale(self):
        self.retire(); e=loaded(self.p,valid_until_ms=1400)
        with self.assertRaisesRegex(ActivationError,'LOADED_ADMISSION_STALE'): self.load(e)
    def test_postinstall_false(self):
        self.retire(); e=loaded(self.p); self.load(e); pp=sign_postinstall(KEY,self.p,e,o20_receipt_root=H('o20'),o19_receipt_root=H('o19'),o19_physical_wake_accepted=False)
        with self.assertRaisesRegex(ActivationError,'POSTINSTALL_OWNER_PROOF_NOT_ACCEPTED'): self.j.bind_postinstall(self.p,pp,e,key=KEY,now_ms=1500)
    def test_postinstall_wrong_loaded(self):
        self.retire(); e=loaded(self.p); self.load(e); other=loaded(self.p,effect_time_witness_root=H('different')); pp=sign_postinstall(KEY,self.p,other,o20_receipt_root=H('o20'),o19_receipt_root=H('o19'))
        with self.assertRaisesRegex(ActivationError,'POSTINSTALL_LOADED_BINDING_MISMATCH'): self.j.bind_postinstall(self.p,pp,e,key=KEY,now_ms=1500)
    def test_activation_requires_o21_accepted(self):
        self.retire(); e=loaded(self.p); self.load(e); pp=sign_postinstall(KEY,self.p,e,o20_receipt_root=H('o20'),o19_receipt_root=H('o19')); self.j.bind_postinstall(self.p,pp,e,key=KEY,now_ms=1500)
        with self.assertRaisesRegex(ActivationError,'O21_ACCEPTANCE_NOT_PROVEN'): self.j.mark_activated(self.p,o21_state='COMMITTED',o21_acceptance_receipt_root=H('x'))
    def test_restart_persistence(self):
        self.retire(); j2=ActivationJournal(self.j.path); self.assertEqual(j2.status(self.p.activation_id)['state'],'OLD_GENERATION_RETIRED')
    def test_identity_conflict(self):
        p2=ActivationPlan(self.p.activation_id,H('other'),self.p.o22_prepare_root,self.p.target_release_root,self.p.expected_host_id,self.p.prior_process_binding_root,self.p.prior_serving_population_root)
        with self.assertRaisesRegex(ActivationError,'ACTIVATION_IDENTITY_CONFLICT'): self.j.prepare(p2,o21_state='COMMITTED',o21_target_release_root=p2.target_release_root,o21_commit_receipt_root=H('commit'))
    def test_k27_absent_from_identity(self): self.assertNotIn('k27',ActivationPlan.__dataclass_fields__)
    def test_no_authority_fields(self): self.assertFalse(self.j.status(self.p.activation_id)['effect_authority']); self.assertFalse(self.j.status(self.p.activation_id)['gate10'])
if __name__=='__main__': unittest.main()
