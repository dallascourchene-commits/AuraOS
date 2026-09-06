import inspect
import itertools
import unittest
from dataclasses import replace

from atomic_absorption import Proposal, OwnerSnapshot, digest
from resource_absorption import (
    Lease, LeaseMode, LeaseRegistrySnapshot, RequirementMode,
    ResourceProposal, ResourceRequirement, plan_resource_absorption,
)
from clock_admission_r42 import guarded_resource_commit, make_admission, make_witness
from clock_admission_registry_r43 import (
    ClockAdmissionRegistrySnapshot, collapse13_r43, guarded_resource_commit_r43,
    make_registry, omega8_r43_keeper, trusted_entry,
)

H='1'*64; T='2'*64; PLAN=1000; EXP=1100

def fixture():
    owner=OwnerSnapshot(H,T)
    lease=Lease('L','db:x','A','LA',LeaseMode.EXCLUSIVE,900,EXP,1)
    registry=LeaseRegistrySnapshot(1,(lease,))
    p=Proposal('P','A','LA',H,digest('c'),digest('r'),{'x.py':digest('b')},False)
    rp=ResourceProposal(p,(ResourceRequirement('db:x',RequirementMode.WRITE,'L'),))
    submitted=plan_resource_absorption(owner,registry,(rp,),now_s=PLAN)
    return owner,registry,(rp,),submitted

def pair(t=1050,nonce='n',gen='g1'):
    w=make_witness('owner-clock',gen,t,nonce); a=make_admission(w,'adm-'+gen); return w,a

def call(w,a,clock_registry,observed_clock_root=None):
    owner,registry,proposals,submitted=fixture()
    return guarded_resource_commit_r43(submitted,observed_owner_head=H,observed_lease_root=registry.root,
        clock_witness=w,clock_admission=a,clock_registry=clock_registry,
        observed_clock_registry_root=clock_registry.root if observed_clock_root is None and clock_registry is not None else observed_clock_root,
        owner=owner,registry=registry,proposals=proposals)

class ClockAdmissionRegistryR43Tests(unittest.TestCase):
    def test_01_valid_pretrusted_admission_commits_and_consumes(self):
        w,a=pair(); reg=make_registry((trusted_entry(w,a),)); r=call(w,a,reg)
        self.assertTrue(r.admitted); self.assertTrue(r.downstream.admitted); self.assertIsNotNone(r.next_registry)
        consumed=[e for e in r.next_registry.entries if e.admission_root==a.currentness_root][0]
        self.assertTrue(consumed.consumed); self.assertNotEqual(r.prior_registry_root,r.next_registry_root)
    def test_02_current_r42_self_asserted_expected_root_accepts_without_registry(self):
        owner,registry,proposals,submitted=fixture(); w,a=pair()
        r=guarded_resource_commit(submitted,observed_owner_head=H,observed_lease_root=registry.root,
            clock_witness=w,clock_admission=a,expected_clock_admission_root=a.currentness_root,
            owner=owner,registry=registry,proposals=proposals)
        self.assertTrue(r.admitted)
    def test_03_r43_self_issued_unregistered_root_holds(self):
        w,a=pair(); reg=make_registry(()); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_ADMISSION_NOT_PRETRUSTED',r.reasons)
    def test_04_r43_has_no_expected_root_parameter(self):
        self.assertNotIn('expected_clock_admission_root',inspect.signature(guarded_resource_commit_r43).parameters)
    def test_05_registry_root_movement_holds(self):
        w,a=pair(); reg=make_registry((trusted_entry(w,a),)); r=call(w,a,reg,'f'*64)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_MOVED',r.reasons)
    def test_06_consumed_admission_replay_holds(self):
        w,a=pair(); reg=make_registry((replace(trusted_entry(w,a),consumed=True),),2); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_ADMISSION_ALREADY_CONSUMED',r.reasons)
    def test_07_success_next_registry_rejects_same_replay(self):
        w,a=pair(); reg=make_registry((trusted_entry(w,a),)); first=call(w,a,reg); second=call(w,a,first.next_registry)
        self.assertTrue(first.admitted); self.assertFalse(second.admitted); self.assertIn('CLOCK_ADMISSION_ALREADY_CONSUMED',second.reasons)
    def test_08_wrong_witness_for_registered_admission_holds(self):
        w,a=pair(nonce='a'); w2,_=pair(nonce='b'); reg=make_registry((trusted_entry(w,a),)); r=call(w2,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_WITNESS_MISMATCH',r.reasons)
    def test_09_registry_time_mismatch_holds(self):
        w,a=pair(); e=replace(trusted_entry(w,a),observed_s=1049); reg=make_registry((e,)); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_TIME_MISMATCH',r.reasons)
    def test_10_duplicate_admission_root_rejected(self):
        w,a=pair(); e=trusted_entry(w,a); reg=make_registry((e,e)); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_DUPLICATE_ADMISSION_ROOT',r.reasons)
    def test_11_registry_authority_widening_holds(self):
        w,a=pair(); reg=ClockAdmissionRegistrySnapshot(1,(trusted_entry(w,a),),'D1',False); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_AUTHORITY_WIDENING',r.reasons)
    def test_12_registry_gate10_holds(self):
        w,a=pair(); reg=ClockAdmissionRegistrySnapshot(1,(trusted_entry(w,a),),'D0',True); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_AUTHORITY_WIDENING',r.reasons)
    def test_13_before_plan_does_not_consume(self):
        w,a=pair(999); reg=make_registry((trusted_entry(w,a),)); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertEqual(r.prior_registry_root,r.next_registry_root)
    def test_14_expiry_does_not_consume(self):
        w,a=pair(EXP); reg=make_registry((trusted_entry(w,a),)); r=call(w,a,reg)
        self.assertFalse(r.admitted); self.assertEqual(r.prior_registry_root,r.next_registry_root)
    def test_15_multiple_entries_consume_only_exact_root(self):
        w1,a1=pair(nonce='1'); w2,a2=pair(1051,'2','g2'); reg=make_registry((trusted_entry(w1,a1),trusted_entry(w2,a2)))
        r=call(w1,a1,reg); self.assertTrue(r.admitted)
        states={e.admission_root:e.consumed for e in r.next_registry.entries}; self.assertTrue(states[a1.currentness_root]); self.assertFalse(states[a2.currentness_root])
    def test_16_missing_registry_holds(self):
        owner,registry,proposals,submitted=fixture(); w,a=pair()
        r=guarded_resource_commit_r43(submitted,observed_owner_head=H,observed_lease_root=registry.root,
            clock_witness=w,clock_admission=a,clock_registry=None,observed_clock_registry_root=None,
            owner=owner,registry=registry,proposals=proposals)
        self.assertFalse(r.admitted); self.assertIn('CLOCK_REGISTRY_REQUIRED',r.reasons)
    def test_17_omega8_one_keeper(self): self.assertEqual(sum(omega8_r43_keeper(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_18_13d_no_repair(self): self.assertFalse(any(collapse13_r43((2,2,2,2,2,2,2,1),t) for t in itertools.product(range(3),repeat=5)))
if __name__=='__main__': unittest.main()
