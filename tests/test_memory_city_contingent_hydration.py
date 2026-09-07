import sys, unittest
from pathlib import Path
from hashlib import sha256
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'arena'))
from memory_city_navigator import SourceSpanLocator, NavigatorError
from memory_city_contingent_hydration import *

def loc(name, size=10, k27=()):
    return SourceSpanLocator(source_id=f"src-{name}",parent_export_sha256=sha256(f"parent-{name}".encode()).hexdigest(),start_line=1,end_line=1,span_sha256=sha256(f"span-{name}".encode()).hexdigest(),span_bytes=size,k27_hint=k27)

def item(name,size=10,ticks=1,k27=()): return HydrationItem(name,loc(name,size,k27),ticks)

class TestContingentHydration(unittest.TestCase):
    def test_invariant_closure_expands_demand(self):
        st=compile_contingent_hydration((item("a"),item("b"),item("c")),(DemandBranch("x",("a",)),),InvariantSupport(1,(("a","b"),)),max_resident_bytes=30,reveal_tick=0,deadline_tick=5)
        self.assertEqual(st.disposition,StrategyDisposition.READY); self.assertEqual(st.branch_plans[0].required_item_ids,("a","b"))
    def test_clairvoyant_false_ready_is_held(self):
        items=(item("a",10,6),item("b",10,6)); s=InvariantSupport(1,()); branches=(DemandBranch("A",("a",)),DemandBranch("B",("b",)))
        self.assertTrue(all(clairvoyant_branch_feasible(items,b,s,max_resident_bytes=10,reveal_tick=6,deadline_tick=8) for b in branches))
        self.assertEqual(compile_contingent_hydration(items,branches,s,max_resident_bytes=10,reveal_tick=6,deadline_tick=8).disposition,StrategyDisposition.HOLD_NO_CONTROLLABLE_POLICY)
    def test_common_component_prefetch_restores_ready(self):
        items=(item("c",10,5),item("a",5,2),item("b",5,2)); branches=(DemandBranch("A",("c","a")),DemandBranch("B",("c","b")))
        st=compile_contingent_hydration(items,branches,InvariantSupport(2,()),max_resident_bytes=15,reveal_tick=5,deadline_tick=7)
        self.assertEqual(st.prefetch_item_ids,("c",)); self.assertEqual({p.branch_id:p.remaining_item_ids for p in st.branch_plans},{"A":("a",),"B":("b",)})
    def test_fixed_union_false_hold_can_be_avoided(self):
        items=(item("a",10,2),item("b",10,2)); branches=(DemandBranch("A",("a",)),DemandBranch("B",("b",))); s=InvariantSupport(1,())
        self.assertFalse(fixed_union_feasible(items,branches,s,max_resident_bytes=10,deadline_tick=4)); self.assertEqual(compile_contingent_hydration(items,branches,s,max_resident_bytes=10,reveal_tick=0,deadline_tick=4).disposition,StrategyDisposition.READY)
    def test_support_generation_change_invalidates(self):
        st=compile_contingent_hydration((item("a"),),(DemandBranch("A",("a",)),),InvariantSupport(7,()),max_resident_bytes=20,reveal_tick=0,deadline_tick=2)
        self.assertEqual(validate_strategy_at_use(st,branch_id="A",support=InvariantSupport(8,())).disposition,StrategyDisposition.HOLD_SUPPORT_GENERATION)
    def test_unknown_branch_holds(self):
        st=compile_contingent_hydration((item("a"),),(DemandBranch("A",("a",)),),InvariantSupport(7,()),max_resident_bytes=20,reveal_tick=0,deadline_tick=2)
        self.assertEqual(validate_strategy_at_use(st,branch_id="B",support=InvariantSupport(7,())).disposition,StrategyDisposition.HOLD_BRANCH)
    def test_dense_support_collapses_global(self):
        items=tuple(item(x,3,1) for x in "abcd"); st=compile_contingent_hydration(items,(DemandBranch("A",("a",)),),InvariantSupport(1,(("a","b","c","d"),)),max_resident_bytes=12,reveal_tick=0,deadline_tick=4)
        self.assertEqual(st.branch_plans[0].required_item_ids,("a","b","c","d"))
    def test_order_is_canonical(self):
        items1=(item("b"),item("a"),item("c")); items2=(items1[2],items1[0],items1[1]); branches1=(DemandBranch("B",("b",)),DemandBranch("A",("a",))); branches2=(branches1[1],branches1[0])
        a=compile_contingent_hydration(items1,branches1,InvariantSupport(3,(("a","c"),)),max_resident_bytes=30,reveal_tick=0,deadline_tick=3); b=compile_contingent_hydration(items2,branches2,InvariantSupport(3,(("c","a"),)),max_resident_bytes=30,reveal_tick=0,deadline_tick=3)
        self.assertEqual(a.receipt_root,b.receipt_root)
    def test_k27_hint_does_not_change_safety_disposition(self):
        a=(item("a",10,2,(1,2,3)),item("b",10,2,(4,5,6))); b=(item("a",10,2,(9,9,9)),item("b",10,2,(0,0,0))); branches=(DemandBranch("A",("a",)),DemandBranch("B",("b",))); s=InvariantSupport(1,())
        x=compile_contingent_hydration(a,branches,s,max_resident_bytes=10,reveal_tick=0,deadline_tick=2); y=compile_contingent_hydration(b,branches,s,max_resident_bytes=10,reveal_tick=0,deadline_tick=2)
        self.assertEqual(x.disposition,y.disposition); self.assertEqual(tuple(p.required_item_ids for p in x.branch_plans),tuple(p.required_item_ids for p in y.branch_plans))
    def test_capacity_holds_even_when_deadline_fits(self):
        self.assertEqual(compile_contingent_hydration((item("a",20,1),),(DemandBranch("A",("a",)),),InvariantSupport(1,()),max_resident_bytes=10,reveal_tick=0,deadline_tick=10).disposition,StrategyDisposition.HOLD_NO_CONTROLLABLE_POLICY)
    def test_unknown_support_item_fails_closed(self):
        with self.assertRaises(NavigatorError): compile_contingent_hydration((item("a"),),(DemandBranch("A",("a",)),),InvariantSupport(1,(("a","ghost"),)),max_resident_bytes=20,reveal_tick=0,deadline_tick=2)
    def test_exact_component_limit_fails_closed(self):
        with self.assertRaises(NavigatorError): compile_contingent_hydration(tuple(item(str(i),1,1) for i in range(17)),(DemandBranch("A",("0",)),),InvariantSupport(1,()),max_resident_bytes=100,reveal_tick=0,deadline_tick=5)
    def test_no_authority_promotion(self):
        st=compile_contingent_hydration((item("a"),),(DemandBranch("A",("a",)),),InvariantSupport(1,()),max_resident_bytes=20,reveal_tick=0,deadline_tick=2); d=validate_strategy_at_use(st,branch_id="A",support=InvariantSupport(1,()))
        self.assertFalse(st.authority_minted); self.assertFalse(st.effect_authority); self.assertFalse(st.gate10); self.assertFalse(d.authority_minted); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)
    def test_same_generation_different_support_identity_holds(self):
        items=(item("a"),item("b")); compiled=InvariantSupport(9,()); st=compile_contingent_hydration(items,(DemandBranch("A",("a",)),),compiled,max_resident_bytes=20,reveal_tick=0,deadline_tick=2); moved=InvariantSupport(9,(("a","b"),)); d=validate_strategy_at_use(st,branch_id="A",support=moved)
        self.assertEqual(d.disposition,StrategyDisposition.HOLD_SUPPORT_GENERATION); self.assertEqual(d.reason,"support_identity_changed_same_generation")
    def test_support_root_canonical_under_edge_order(self):
        self.assertEqual(InvariantSupport(4,(("b","a"),("d","c"))).support_root,InvariantSupport(4,(("c","d"),("a","b"))).support_root)
    def test_duplicate_support_edge_fails_closed(self):
        with self.assertRaises(NavigatorError): InvariantSupport(1,(("a","b"),("b","a")))

if __name__=='__main__': unittest.main()
