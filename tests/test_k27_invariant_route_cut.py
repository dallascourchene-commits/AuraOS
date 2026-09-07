import itertools,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_invariant_route_cut import SupportHyperedge,SupportBeliefState,compile_invariant_route_cut,affected_by_change,hard13d_route_cut

def e(i,*m): return SupportHyperedge(i,frozenset(m))
def s(root,*edges,complete=True,current=True): return SupportBeliefState(root,tuple(edges),complete,current)

class InvariantRouteCutTests(unittest.TestCase):
    def test_crossing_invariant_expands_direct_dependency_cut(self):
        out=compile_invariant_route_cut(['A'],[s('r1',e('i1','A','B'),e('i2','B','C'))])
        self.assertEqual(out.status,'READY_INVARIANT_ROUTE_CUT_D0')
        self.assertEqual(out.safe_support_cut,('A','B','C'))
        self.assertEqual(out.crossing_invariants,('i1','i2'))
    def test_disjoint_invariant_does_not_expand_cut(self):
        out=compile_invariant_route_cut(['A'],[s('r1',e('i1','X','Y'))])
        self.assertEqual(out.safe_support_cut,('A',)); self.assertTrue(out.local_reuse_allowed)
    def test_incomplete_support_holds_and_cannot_prove_unaffected(self):
        out=compile_invariant_route_cut(['A'],[s('r1',e('i1','A','B'),complete=False)])
        self.assertEqual(out.status,'HOLD_SUPPORT_INCOMPLETE'); self.assertTrue(affected_by_change(out,'Z'))
    def test_stale_support_holds(self):
        out=compile_invariant_route_cut(['A'],[s('r1',e('i1','A','B'),current=False)])
        self.assertEqual(out.status,'HOLD_SUPPORT_STALE')
    def test_unknown_support_holds(self):
        self.assertEqual(compile_invariant_route_cut(['A'],[]).status,'HOLD_SUPPORT_UNKNOWN')
    def test_reflexive_support_change_holds_and_overcouples_union(self):
        a=s('pre',e('i1','A','B')); b=s('post',e('i1','A','C'))
        out=compile_invariant_route_cut(['A'],[a,b])
        self.assertEqual(out.status,'HOLD_REFLEXIVE_SUPPORT_AMBIGUITY')
        self.assertEqual(out.safe_support_cut,('A','B','C')); self.assertFalse(out.local_reuse_allowed)
    def test_reflexive_identical_support_can_commit(self):
        a=s('p1',e('i1','A','B')); b=s('p2',e('i1','A','B'))
        out=compile_invariant_route_cut(['A'],[a,b])
        self.assertEqual(out.status,'READY_INVARIANT_ROUTE_CUT_D0'); self.assertEqual(out.safe_support_cut,('A','B'))
    def test_missing_invariant_in_one_belief_state_holds(self):
        out=compile_invariant_route_cut(['A'],[s('p1',e('i1','A','B')),s('p2')])
        self.assertEqual(out.status,'HOLD_REFLEXIVE_SUPPORT_AMBIGUITY')
    def test_dense_support_honestly_collapses_global(self):
        nodes=[f'N{i}' for i in range(20)]
        out=compile_invariant_route_cut(['N0'],[s('r',e('global',*nodes))])
        self.assertEqual(len(out.safe_support_cut),20)
    def test_ready_cut_change_outside_is_unaffected(self):
        out=compile_invariant_route_cut(['A'],[s('r',e('i','A','B'))])
        self.assertTrue(affected_by_change(out,'B')); self.assertFalse(affected_by_change(out,'Z'))
    def test_no_authority(self):
        out=compile_invariant_route_cut(['A'],[s('r')])
        self.assertFalse(out.authority_minted); self.assertFalse(out.gate10)
    def test_13d_context_cannot_repair_hard_invalid(self):
        for tail in itertools.product(range(3),repeat=5): self.assertEqual(hard13d_route_cut((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')

if __name__=='__main__':unittest.main()
