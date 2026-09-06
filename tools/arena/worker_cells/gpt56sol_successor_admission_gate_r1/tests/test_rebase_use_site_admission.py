import unittest
from dataclasses import dataclass,replace
from rebase_use_site_admission import *

@dataclass(frozen=True)
class IR:
    receipt_root:str
@dataclass(frozen=True)
class PE:
    immediate_receipt:IR|None
@dataclass(frozen=True)
class GD:
    value:str
@dataclass(frozen=True)
class GR:
    disposition:GD
    pair_root:str
    authority_ceiling:str='D0'

def R(cid,line,cons,rd=None):return ConveyorReceiptRef(cid,line,cons,rd or digest(('r',cid)),KEEP)
def B(r,term=None):
    tr=term or digest(('terminal',r.capsule_id));return ReceiptParentBinding(r.receipt_digest,PE(IR(tr)),tr,'drive:'+r.capsule_id,digest(('rev',r.capsule_id)))
def gate(status=ACCEPT,auth='D0',root=None): return lambda ev,ctx:GR(GD(status),root or digest(('pair',len(ev))),auth)
class Tests(unittest.TestCase):
 def test_valid_pair_mints_seed(self):
  a,b=R('a','L1',digest('c1')),R('b','L2',digest('c2'));q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),gate());self.assertTrue(q.admitted);self.assertTrue(hex64(q.objective_seed));self.assertFalse(q.effect_authority)
 def test_old_distinct_labels_not_enough(self):
  a,b=R('a','L1',digest('c1')),R('b','L2',digest('c2'));q=compile_rebase_after_parent_admission([a,b],{},object(),gate());self.assertFalse(q.admitted)
 def test_same_lineage_withheld_before_gate(self):
  a,b=R('a','L','c'*64),R('b','L','d'*64);calls=[]
  q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),lambda e,c:calls.append(1));self.assertFalse(q.admitted);self.assertFalse(calls)
 def test_same_consequence_withheld(self):
  a,b=R('a','L1','c'*64),R('b','L2','c'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),gate());self.assertFalse(q.admitted)
 def test_foreign_ancestry_hold_from_gate_blocks(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),gate('FOREIGN_ANCESTRY_ONLY_HOLD'));self.assertFalse(q.admitted)
 def test_binding_receipt_mismatch_blocks(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);ba=replace(B(a),conveyor_receipt_digest='0'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:ba,b.receipt_digest:B(b)},object(),gate());self.assertFalse(q.admitted)
 def test_terminal_receipt_mismatch_blocks(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);ba=replace(B(a),terminal_receipt_root='0'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:ba,b.receipt_digest:B(b)},object(),gate());self.assertFalse(q.admitted)
 def test_missing_immediate_receipt_blocks(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);ba=replace(B(a),parent_evidence=PE(None));q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:ba,b.receipt_digest:B(b)},object(),gate());self.assertFalse(q.admitted)
 def test_gate_authority_widening_blocks(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),gate(auth='D1'));self.assertFalse(q.admitted)
 def test_effect_bearing_receipt_excluded(self):
  a=replace(R('a','L1','c'*64),effect_authority=True);b=R('b','L2','d'*64);q=compile_rebase_after_parent_admission([a,b],{a.receipt_digest:B(a),b.receipt_digest:B(b)},object(),gate());self.assertFalse(q.admitted)
 def test_pair_root_changes_seed(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);bs={a.receipt_digest:B(a),b.receipt_digest:B(b)};q1=compile_rebase_after_parent_admission([a,b],bs,object(),gate(root='1'*64));q2=compile_rebase_after_parent_admission([a,b],bs,object(),gate(root='2'*64));self.assertNotEqual(q1.objective_seed,q2.objective_seed)
 def test_deterministic_order(self):
  a,b=R('a','L1','c'*64),R('b','L2','d'*64);bs={a.receipt_digest:B(a),b.receipt_digest:B(b)};self.assertEqual(compile_rebase_after_parent_admission([a,b],bs,object(),gate()).objective_seed,compile_rebase_after_parent_admission([b,a],bs,object(),gate()).objective_seed)
if __name__=='__main__':unittest.main()
