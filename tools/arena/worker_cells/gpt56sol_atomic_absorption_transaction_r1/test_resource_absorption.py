import unittest,itertools,hashlib
from atomic_absorption import Proposal,OwnerSnapshot,digest
from resource_absorption import *
H='1'*64; T='2'*64; NOW=1000

def lease(id,key,actor='A',line='LA',mode=LeaseMode.EXCLUSIVE,issued=900,expires=1100,gen=1,released=None):
    return Lease(id,key,actor,line,mode,issued,expires,gen,released)
def reg(*ls,gen=1): return LeaseRegistrySnapshot(gen,tuple(ls))
def prop(pid='P',actor='A',line='LA',files=None,cons=None,rec=None,base=H):
    return Proposal(pid,actor,line,base,cons or digest('c'+pid),rec or digest('r'+pid),files or {pid+'.py':digest('b'+pid)},False)
def rp(p=None,reqs=()): return ResourceProposal(p or prop(),tuple(reqs))
def req(key,id,mode=RequirementMode.WRITE): return ResourceRequirement(key,mode,id)
class Tests(unittest.TestCase):
    def owner(self): return OwnerSnapshot(H,T)
    def test_01_no_resource_ready(self):
        q=plan_resource_absorption(self.owner(),reg(),[rp()],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.READY)
    def test_02_exact_exclusive_write_ready(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','port:3000')),[rp(reqs=(req('port:3000','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.READY)
    def test_03_missing_lease_holds(self):
        q=plan_resource_absorption(self.owner(),reg(),[rp(reqs=(req('db:test','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_MISSING_HOLD)
    def test_04_expired_lease_is_missing(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','db:test',expires=NOW)),[rp(reqs=(req('db:test','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_STALE_HOLD)
    def test_05_future_lease_rejected(self):
        with self.assertRaisesRegex(ResourceError,'FUTURE_LEASE'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=NOW+1,expires=NOW+2)),[rp()],now_s=NOW)
    def test_06_holder_actor_mismatch(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','x',actor='B')),[rp(reqs=(req('x','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_07_holder_lineage_mismatch(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','x',line='LB')),[rp(reqs=(req('x','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_08_shared_read_cannot_write(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','x',mode=LeaseMode.SHARED_READ)),[rp(reqs=(req('x','L',RequirementMode.WRITE),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_IDENTITY_HOLD)
    def test_09_shared_read_can_read(self):
        q=plan_resource_absorption(self.owner(),reg(lease('L','x',mode=LeaseMode.SHARED_READ)),[rp(reqs=(req('x','L',RequirementMode.READ),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.READY)
    def test_10_two_shared_readers_ready(self):
        r=reg(lease('A1','cache:c',actor='A',line='LA',mode=LeaseMode.SHARED_READ),lease('B1','cache:c',actor='B',line='LB',mode=LeaseMode.SHARED_READ))
        a=rp(prop('A','A','LA'),(req('cache:c','A1',RequirementMode.READ),)); b=rp(prop('B','B','LB'),(req('cache:c','B1',RequirementMode.READ),))
        self.assertEqual(plan_resource_absorption(self.owner(),r,[a,b],now_s=NOW).disposition,ResourceDisposition.READY)
    def test_11_exclusive_plus_shared_registry_conflict(self):
        r=reg(lease('A1','db:x'),lease('B1','db:x',actor='B',line='LB',mode=LeaseMode.SHARED_READ))
        self.assertEqual(plan_resource_absorption(self.owner(),r,[rp()],now_s=NOW).disposition,ResourceDisposition.LEASE_CONFLICT_HOLD)
    def test_12_two_exclusive_registry_conflict(self):
        r=reg(lease('A1','port:1'),lease('B1','port:1',actor='B',line='LB'))
        self.assertEqual(plan_resource_absorption(self.owner(),r,[rp()],now_s=NOW).disposition,ResourceDisposition.LEASE_CONFLICT_HOLD)
    def test_13_two_write_claims_hold(self):
        # registry itself would already reject simultaneous exclusive leases
        r=reg(lease('A1','db:x'),lease('B1','db:y',actor='B',line='LB'))
        a=rp(prop('A','A','LA'),(req('db:x','A1'),)); b=rp(prop('B','B','LB'),(req('db:x','B1'),))
        self.assertEqual(plan_resource_absorption(self.owner(),r,[a,b],now_s=NOW).disposition,ResourceDisposition.LEASE_MISSING_HOLD)
    def test_14_owner_head_stale_base_holds_via_base(self):
        p=prop(base='0'*64); q=plan_resource_absorption(self.owner(),reg(),[rp(p)],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.BASE_HOLD); self.assertEqual(q.base_disposition,'REBASE_REQUIRED')
    def test_15_path_conflict_holds_via_base(self):
        a=prop('A',files={'x':'1'*64}); b=prop('B',actor='B',line='LB',files={'x':'2'*64}); q=plan_resource_absorption(self.owner(),reg(),[rp(a),rp(b)],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.BASE_HOLD)
    def test_16_owner_move_at_commit_zero(self):
        q=plan_resource_absorption(self.owner(),reg(),[rp()],now_s=NOW); r=commit_resource_absorption(q,observed_owner_head='9'*64,observed_lease_root=reg().root); self.assertFalse(r.committed); self.assertEqual(r.write_count,0)
    def test_17_lease_registry_move_at_commit_zero(self):
        rr=reg(); q=plan_resource_absorption(self.owner(),rr,[rp()],now_s=NOW); moved=reg(gen=2).root; r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=moved); self.assertFalse(r.committed); self.assertEqual(r.write_count,0)
    def test_18_both_current_commit(self):
        rr=reg(lease('L','service:s')); q=plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('service:s','L'),))],now_s=NOW); r=commit_resource_absorption(q,observed_owner_head=H,observed_lease_root=rr.root); self.assertTrue(r.committed); self.assertEqual(r.lost_consequence_count,0)
    def test_19_lease_binding_changes_manifest(self):
        r1=reg(lease('L1','x')); r2=reg(lease('L2','x'))
        q1=plan_resource_absorption(self.owner(),r1,[rp(reqs=(req('x','L1'),))],now_s=NOW); q2=plan_resource_absorption(self.owner(),r2,[rp(reqs=(req('x','L2'),))],now_s=NOW); self.assertNotEqual(q1.manifest_root,q2.manifest_root)
    def test_20_now_currentness_changes_manifest(self):
        rr=reg(lease('L','x')); q1=plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('x','L'),))],now_s=NOW); q2=plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('x','L'),))],now_s=NOW+1); self.assertNotEqual(q1.manifest_root,q2.manifest_root)
    def test_21_registry_authority_widening_rejected(self):
        with self.assertRaisesRegex(ResourceError,'REGISTRY_AUTHORITY_WIDENING'): plan_resource_absorption(self.owner(),LeaseRegistrySnapshot(1,(),authority_ceiling='D1'),[rp()],now_s=NOW)
    def test_22_duplicate_lease_id_rejected(self):
        with self.assertRaisesRegex(ResourceError,'DUPLICATE_LEASE_ID'): plan_resource_absorption(self.owner(),reg(lease('L','x'),lease('L','y')),[rp()],now_s=NOW)
    def test_23_time_inversion_rejected(self):
        with self.assertRaisesRegex(ResourceError,'LEASE_TIME_INVERSION'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=950,expires=900)),[rp()],now_s=NOW)
    def test_24_exact_redelivery_same_resource_collapses(self):
        rr=reg(lease('L','x')); base=prop('A'); same=Proposal('B',base.actor_id,base.lineage_root,base.base_head,base.consequence_root,base.receipt_root,base.files,False)
        q=plan_resource_absorption(self.owner(),rr,[rp(base,(req('x','L'),)),rp(same,(req('x','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.READY); self.assertEqual(q.base_plan.collapsed_proposals,('B',))
    def test_24a_released_lease_stale(self):
        rr=reg(lease('L','x',released=NOW-1)); q=plan_resource_absorption(self.owner(),rr,[rp(reqs=(req('x','L'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.LEASE_STALE_HOLD)
    def test_24b_future_release_rejected(self):
        with self.assertRaisesRegex(ResourceError,'FUTURE_RELEASE'): plan_resource_absorption(self.owner(),reg(lease('L','x',released=NOW+1)),[rp()],now_s=NOW)
    def test_24c_release_before_issue_rejected(self):
        with self.assertRaisesRegex(ResourceError,'LEASE_RELEASE_BEFORE_ISSUE'): plan_resource_absorption(self.owner(),reg(lease('L','x',issued=900,released=899)),[rp()],now_s=NOW)
    def test_25_same_consequence_different_resource_binding_holds(self):
        rr=reg(lease('L1','x'),lease('L2','y'))
        a=prop('A'); b=Proposal('B',a.actor_id,a.lineage_root,a.base_head,a.consequence_root,a.receipt_root,a.files,False)
        q=plan_resource_absorption(self.owner(),rr,[rp(a,(req('x','L1'),)),rp(b,(req('y','L2'),))],now_s=NOW); self.assertEqual(q.disposition,ResourceDisposition.BASE_HOLD); self.assertEqual(q.base_disposition,'CONFLICT_HOLD')
    def test_26_omega8_one_keeper(self): self.assertEqual(sum(omega8_resource_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_27_13d_no_repair(self): self.assertFalse(any(context13_resource_preserves_invalid((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5)))
if __name__=='__main__': unittest.main()
