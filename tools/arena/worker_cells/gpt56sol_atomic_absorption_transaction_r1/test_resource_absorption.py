import unittest,itertools
from dataclasses import replace
from atomic_absorption import Proposal,OwnerSnapshot,digest
from resource_absorption import *
H='1'*64; T='2'*64; NOW=1000

def lease(id,key,actor='A',line='LA',mode=LeaseMode.EXCLUSIVE,issued=900,expires=1100,gen=1,released=None): return Lease(id,key,actor,line,mode,issued,expires,gen,released)
def reg(*ls,gen=1): return LeaseRegistrySnapshot(gen,tuple(ls))
def prop(pid='P',actor='A',line='LA',files=None,cons=None,rec=None,base=H): return Proposal(pid,actor,line,base,cons or digest('c'+pid),rec or digest('r'+pid),files or {pid+'.py':digest('b'+pid)},False)
def rp(p=None,reqs=()): return ResourceProposal(p or prop(),tuple(reqs))
def req(key,id,mode=RequirementMode.WRITE): return ResourceRequirement(key,mode,id)

class Tests(unittest.TestCase):
    def owner(self): return OwnerSnapshot(H,T)
    def test_01_no_resource_ready(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(),[rp()],now_s=NOW).disposition,ResourceDisposition.READY)
    def test_02_exact_exclusive_write_ready(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','port:3000')),[rp(reqs=(req('port:3000','L'),))],now_s=NOW).disposition,ResourceDisposition.READY)
    def test_03_missing_lease_holds(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(),[rp(reqs=(req('db:test','L'),))],now_s=NOW).disposition,ResourceDisposition.LEASE_MISSING_HOLD)
    def test_04_expired_lease_is_stale(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','db:test',expires=NOW)),[rp(reqs=(req('db:test','L'),))],now_s=NOW).disposition,ResourceDisposition.LEASE_STALE_HOLD)
    def test_05_future_lease_rejected(self):
        with self.assertRaisesRegex(ResourceError,'FUTURE_LEASE'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=NOW+1,expires=NOW+2)),[rp()],now_s=NOW)
    def test_06_holder_actor_mismatch(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','x',actor='B')),[rp(reqs=(req('x','L'),))],now_s=NOW).disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_07_holder_lineage_mismatch(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','x',line='LB')),[rp(reqs=(req('x','L'),))],now_s=NOW).disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_08_shared_read_cannot_write(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','x',mode=LeaseMode.SHARED_READ)),[rp(reqs=(req('x','L',RequirementMode.WRITE),))],now_s=NOW).disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_09_shared_read_can_read(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','x',mode=LeaseMode.SHARED_READ)),[rp(reqs=(req('x','L',RequirementMode.READ),))],now_s=NOW).disposition,ResourceDisposition.READY)
    def test_10_two_shared_readers_ready(self):
        r=reg(lease('A1','cache:c',actor='A',line='LA',mode=LeaseMode.SHARED_READ),lease('B1','cache:c',actor='B',line='LB',mode=LeaseMode.SHARED_READ)); a=rp(prop('A','A','LA'),(req('cache:c','A1',RequirementMode.READ),)); b=rp(prop('B','B','LB'),(req('cache:c','B1',RequirementMode.READ),)); self.assertEqual(plan_resource_absorption(self.owner(),r,[a,b],now_s=NOW).disposition,ResourceDisposition.READY)
    def test_11_exclusive_plus_shared_registry_conflict(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('A1','db:x'),lease('B1','db:x',actor='B',line='LB',mode=LeaseMode.SHARED_READ)),[rp()],now_s=NOW).disposition,ResourceDisposition.LEASE_CONFLICT_HOLD)
    def test_12_two_exclusive_registry_conflict(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('A1','port:1'),lease('B1','port:1',actor='B',line='LB')),[rp()],now_s=NOW).disposition,ResourceDisposition.LEASE_CONFLICT_HOLD)
    def test_12a_two_write_claims_hold(self):
        r=reg(lease('A1','db:x'),lease('B1','db:y',actor='B',line='LB'))
        a=rp(prop('A','A','LA'),(req('db:x','A1'),)); b=rp(prop('B','B','LB'),(req('db:x','B1'),))
        self.assertEqual(plan_resource_absorption(self.owner(),r,[a,b],now_s=NOW).disposition,ResourceDisposition.LEASE_MISSING_HOLD)
    def test_13_owner_head_stale_base_holds_via_base(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(),[rp(prop(base='0'*64))],now_s=NOW).disposition,ResourceDisposition.BASE_HOLD)
    def test_14_path_conflict_holds_via_base(self):
        a=prop('A',files={'x':'1'*64}); b=prop('B',actor='B',line='LB',files={'x':'2'*64}); self.assertEqual(plan_resource_absorption(self.owner(),reg(),[rp(a),rp(b)],now_s=NOW).disposition,ResourceDisposition.BASE_HOLD)
    def test_15_owner_move_at_commit_zero(self):
        rr=reg(); ps=[rp()]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); r=commit_resource_absorption(q,observed_owner_head='9'*64,observed_lease_root=rr.root,owner=self.owner(),registry=rr,proposals=ps,now_s=NOW); self.assertFalse(r.committed)
    def test_16_lease_registry_move_at_commit_zero(self):
        rr=reg(); ps=[rp()]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); moved=reg(gen=2); r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=moved.root,owner=self.owner(),registry=moved,proposals=ps,now_s=NOW); self.assertFalse(r.committed)
    def test_17_both_current_commit(self):
        rr=reg(lease('L','service:s')); ps=[rp(reqs=(req('service:s','L'),))]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=rr.root,owner=self.owner(),registry=rr,proposals=ps,now_s=NOW+1); self.assertTrue(r.committed)
    def test_18_lease_binding_changes_manifest(self):
        r1=reg(lease('L1','x')); r2=reg(lease('L2','x')); self.assertNotEqual(plan_resource_absorption(self.owner(),r1,[rp(reqs=(req('x','L1'),))],now_s=NOW).manifest_root,plan_resource_absorption(self.owner(),r2,[rp(reqs=(req('x','L2'),))],now_s=NOW).manifest_root)
    def test_19_now_currentness_changes_manifest(self):
        rr=reg(lease('L','x')); self.assertNotEqual(plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('x','L'),))],now_s=NOW).manifest_root,plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('x','L'),))],now_s=NOW+1).manifest_root)
    def test_20_registry_authority_widening_rejected(self):
        with self.assertRaisesRegex(ResourceError,'REGISTRY_AUTHORITY_WIDENING'): plan_resource_absorption(self.owner(),LeaseRegistrySnapshot(1,(),authority_ceiling='D1'),[rp()],now_s=NOW)
    def test_21_duplicate_lease_id_rejected(self):
        with self.assertRaisesRegex(ResourceError,'DUPLICATE_LEASE_ID'): plan_resource_absorption(self.owner(),reg(lease('L','x'),lease('L','y')),[rp()],now_s=NOW)
    def test_22_time_inversion_rejected(self):
        with self.assertRaisesRegex(ResourceError,'LEASE_TIME_INVERSION'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=950,expires=900)),[rp()],now_s=NOW)
    def test_23_exact_redelivery_same_resource_collapses(self):
        rr=reg(lease('L','x')); base=prop('A'); same=Proposal('B',base.actor_id,base.lineage_root,base.base_head,base.consequence_root,base.receipt_root,base.files,False); q=plan_resource_absorption(self.owner(),rr,[rp(base,(req('x','L'),)),rp(same,(req('x','L'),))],now_s=NOW); self.assertEqual(q.base_plan.collapsed_proposals,('B',))
    def test_24_released_lease_stale(self): self.assertEqual(plan_resource_absorption(self.owner(),reg(lease('L','x',released=NOW-1)),[rp(reqs=(req('x','L'),))],now_s=NOW).disposition,ResourceDisposition.LEASE_STALE_HOLD)
    def test_24a_future_release_rejected(self):
        with self.assertRaisesRegex(ResourceError,'FUTURE_RELEASE'): plan_resource_absorption(self.owner(),reg(lease('L','x',released=NOW+1)),[rp()],now_s=NOW)
    def test_24b_release_before_issue_rejected(self):
        with self.assertRaisesRegex(ResourceError,'LEASE_RELEASE_BEFORE_ISSUE'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=900,released=899)),[rp()],now_s=NOW)
    def test_25_same_consequence_different_resource_binding_holds(self):
        rr=reg(lease('L1','x'),lease('L2','y')); a=prop('A'); b=Proposal('B',a.actor_id,a.lineage_root,a.base_head,a.consequence_root,a.receipt_root,a.files,False); self.assertEqual(plan_resource_absorption(self.owner(),rr,[rp(a,(req('x','L1'),)),rp(b,(req('y','L2'),))],now_s=NOW).disposition,ResourceDisposition.BASE_HOLD)
    def test_26_omega8_one_keeper(self): self.assertEqual(sum(omega8_resource_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_27_13d_no_repair(self): self.assertFalse(any(context13_resource_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5)))
    def test_28_legacy_commit_without_authoritative_inputs_fails_closed(self):
        rr=reg(lease('L','x')); ps=[rp(reqs=(req('x','L'),))]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); self.assertFalse(commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=rr.root).committed)
    def test_29_forged_resource_plan_fails_closed(self):
        rr=reg(lease('L','x')); ps=[rp(reqs=(req('x','L'),))]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); forged=replace(q,manifest_root='f'*64,effect_authority=True,gate10=True); self.assertFalse(commit_resource_absorption(forged,observed_owner_head=H,observed_lease_root=rr.root,owner=self.owner(),registry=rr,proposals=ps,now_s=NOW+1).committed)
    def test_30_lease_can_expire_after_plan_without_registry_root_change(self):
        rr=reg(lease('L','x',expires=NOW+2)); ps=[rp(reqs=(req('x','L'),))]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); self.assertEqual(rr.root,q.expected_lease_root); r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=rr.root,owner=self.owner(),registry=rr,proposals=ps,now_s=NOW+2); self.assertFalse(r.committed); self.assertEqual(r.write_count,0)
    def test_31_near_expiry_before_deadline_still_commits(self):
        rr=reg(lease('L','x',expires=NOW+2)); ps=[rp(reqs=(req('x','L'),))]; q=plan_resource_absorption(self.owner(),rr,ps,now_s=NOW); r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=rr.root,owner=self.owner(),registry=rr,proposals=ps,now_s=NOW+1); self.assertTrue(r.committed)

if __name__=='__main__': unittest.main()
