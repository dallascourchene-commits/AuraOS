import sys, unittest
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_navigator import SourceSpanLocator, NavigatorError
from memory_city_contingent_hydration import *
from memory_city_typed_closure import *

def loc(n,size=5):
 z=lambda s:sha256(s.encode()).hexdigest(); return SourceSpanLocator(n,z('p'+n),1,1,z('s'+n),size,())
def it(n,size=5,t=1): return HydrationItem(n,loc(n,size),t)

class TypedClosureTests(unittest.TestCase):
 def base(self):
  items=tuple(it(x) for x in 'abcd'); branches=(DemandBranch('A',('a',)),); support=InvariantSupport(1,(('a','b'),)); influence=InfluenceGraph(1,(('a','c'),('c','d'))); return items,branches,support,influence
 def test_separate_hydration_and_reproof(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); self.assertEqual(c.hydration.branch_plans[0].required_item_ids,('a','b')); self.assertEqual(c.reproof_item_ids,('a','b','c','d'))
 def test_changed_support_peer_is_reproof_seed(self):
  i,b,s,g=self.base(); self.assertEqual(typed_reproof_descendants(('a',),g,s,tuple(x.item_id for x in i)),('a','b','c','d')); self.assertEqual(directed_descendants(('a',),g,tuple(x.item_id for x in i)),('a','c','d'))
 def test_influence_destination_expands_whole_hard_component(self):
  i=tuple(it(x) for x in 'abcd'); s=InvariantSupport(1,(('c','d'),)); g=InfluenceGraph(1,(('a','c'),)); self.assertEqual(typed_reproof_descendants(('a',),g,s,tuple(x.item_id for x in i)),('a','c','d'))
 def test_influence_direction_preserved_across_support_quotient(self):
  i=tuple(it(x) for x in 'abc'); s=InvariantSupport(1,(('a','b'),)); g=InfluenceGraph(1,(('c','a'),)); self.assertEqual(typed_reproof_descendants(('a',),g,s,tuple(x.item_id for x in i)),('a','b'))
 def test_directed_cycle_is_reproof_unit_not_support_identity_rewrite(self):
  i=tuple(it(x) for x in 'abcd'); s=InvariantSupport(1,(('a','b'),)); g=InfluenceGraph(1,(('a','c'),('c','a'))); self.assertEqual(typed_reproof_descendants(('a',),g,s,tuple(x.item_id for x in i)),('a','b','c')); self.assertEqual(invariant_components(tuple(x.item_id for x in i),s),(('a','b'),('c',),('d',)))
 def test_no_support_reduces_to_raw_directed_reachability(self):
  i=tuple(it(x) for x in 'abcd'); s=InvariantSupport(1,()); g=InfluenceGraph(1,(('a','b'),('b','c'))); u=tuple(x.item_id for x in i); self.assertEqual(typed_reproof_descendants(('a',),g,s,u),directed_descendants(('a',),g,u))
 def test_support_only_misses_directed_descendants(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); self.assertIn('d',c.reproof_item_ids); self.assertNotIn('d',c.hydration.branch_plans[0].required_item_ids)
 def test_symmetrized_union_overexpands(self):
  i,b,s,g=self.base(); self.assertEqual(symmetrized_union_closure(('a',),s,g,tuple(x.item_id for x in i)),('a','b','c','d'))
 def test_incomplete_influence_holds(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,InfluenceGraph(1,g.edges,False),changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); self.assertEqual(c.disposition,TypedClosureDisposition.HOLD_INCOMPLETE_RELATION)
 def test_incomplete_support_holds(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t',support_complete=False); self.assertEqual(c.disposition,TypedClosureDisposition.HOLD_INCOMPLETE_RELATION)
 def test_influence_root_move_holds(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); d=validate_typed_closure_at_use(c,branch_id='A',support=s,influence=InfluenceGraph(1,(('a','d'),)),transition_model_root='t'); self.assertEqual(d.disposition,TypedClosureDisposition.HOLD_INFLUENCE_IDENTITY)
 def test_h0_transition_move_requires_rebind(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); d=validate_typed_closure_at_use(c,branch_id='A',support=s,influence=g,transition_model_root='t2'); self.assertEqual(d.disposition,TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE)
 def test_horizon_requires_certificate(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t',horizon=2); self.assertEqual(c.disposition,TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE)
 def test_horizon_certificate_allows_same_semantics(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t',horizon=2,future_congruence_root='fc'); d=validate_typed_closure_at_use(c,branch_id='A',support=s,influence=g,transition_model_root='t',future_congruence_root='fc'); self.assertEqual(d.disposition,TypedClosureDisposition.READY)
 def test_horizon_future_root_move_holds(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t',horizon=2,future_congruence_root='fc'); d=validate_typed_closure_at_use(c,branch_id='A',support=s,influence=g,transition_model_root='t',future_congruence_root='other'); self.assertEqual(d.disposition,TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE)
 def test_support_identity_still_enforced(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); d=validate_typed_closure_at_use(c,branch_id='A',support=InvariantSupport(1,(('a','b','c'),)),influence=g,transition_model_root='t'); self.assertEqual(d.disposition,TypedClosureDisposition.HOLD_SUPPORT_IDENTITY)
 def test_graph_order_canonical(self): self.assertEqual(InfluenceGraph(3,(('b','c'),('a','b'))).influence_root,InfluenceGraph(3,(('a','b'),('b','c'))).influence_root)
 def test_unknown_influence_node_fails(self):
  i,b,s,g=self.base()
  with self.assertRaises(NavigatorError): compile_typed_closure(i,b,s,InfluenceGraph(1,(('a','ghost'),)),changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t')
 def test_no_authority(self):
  i,b,s,g=self.base(); c=compile_typed_closure(i,b,s,g,changed_evidence_item_ids=('a',),max_resident_bytes=20,reveal_tick=0,deadline_tick=5,transition_model_root='t'); self.assertFalse(c.effect_authority); self.assertFalse(c.gate10)
if __name__=='__main__':unittest.main()
