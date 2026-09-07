import unittest,itertools
from tools.arena.worker_cells.gpt56sol_astra_uncertainty_bounded_evidence_choreography_r1 import *

def T(fn,n=3):return tuple(bool(fn(*[((m>>i)&1) for i in range(n)])) for m in range(1<<n))
class TestChoreo(unittest.TestCase):
    def q(self,name,bit,cost=1,lo=1,hi=1,private=False,current=True):return EvidenceQuery(name,bit,cost,DurationInterval(lo,hi),private,0,current)
    def ref(self,lo=1,hi=1,current=True):return RefreshAction('refresh',1,DurationInterval(lo,hi),current)
    def test_exact_private_premise(self):
        t=T(lambda p,a,b:p and a and b);qs=(self.q('p',0),self.q('a',1,private=True),self.q('b',2,private=True));p=compile_choreography(t,qs,self.ref(),10);self.assertEqual(p.status,'READY_D0');self.assertFalse(validate_tree(t,qs,self.ref(),p.tree,10)['failures'])
    def test_negative_avoids_private(self):
        t=T(lambda p,a,b:p and (a or b));qs=(self.q('p',0),self.q('a',1,private=True),self.q('b',2,private=True));p=compile_choreography(t,qs,self.ref(),10);self.assertEqual(p.tree.action,'p');self.assertFalse(p.tree.zero.decision)
    def test_positive_refresh(self):
        t=T(lambda p,a,b:p and a);qs=(self.q('p',0),self.q('a',1,private=True),self.q('b',2,private=True));p=compile_choreography(t,qs,self.ref(),10);self.assertFalse(validate_tree(t,qs,self.ref(),p.tree,10)['failures'])
    def test_midpoint_false_ready(self):
        t=T(lambda p,a,b:p and a);qs=(self.q('p',0,lo=1,hi=5),self.q('a',1,lo=1,hi=5,private=True),self.q('b',2,private=True));r=self.ref(lo=1,hi=5);n=compile_choreography(t,qs,r,9,duration_mode='midpoint');rb=compile_choreography(t,qs,r,9);self.assertEqual(n.status,'READY_D0');self.assertEqual(rb.status,'HOLD_NO_CHOREOGRAPHY');self.assertTrue(validate_tree(t,qs,r,n.tree,9)['failures'])
    def test_robust_ready_all_traces(self):
        t=T(lambda p,a,b:p and a);qs=(self.q('p',0,lo=1,hi=2),self.q('a',1,lo=1,hi=2,private=True),self.q('b',2,private=True));r=self.ref(lo=1,hi=2);p=compile_choreography(t,qs,r,6);self.assertFalse(validate_tree(t,qs,r,p.tree,6)['failures'])
    def test_stale_needed_query_holds(self):
        t=T(lambda p,a,b:p and a);qs=(self.q('p',0),self.q('a',1,private=True,current=False),self.q('b',2,private=True));self.assertEqual(compile_choreography(t,qs,self.ref(),20).status,'HOLD_NO_CHOREOGRAPHY')
    def test_stale_unused_query_ok(self):
        t=T(lambda p,a,b:p);qs=(self.q('p',0),self.q('a',1,private=True,current=False),self.q('b',2,private=True,current=False));self.assertEqual(compile_choreography(t,qs,self.ref(),20).status,'READY_D0')
    def test_stale_refresh_holds(self):
        t=T(lambda p,a,b:p);qs=(self.q('p',0),self.q('a',1),self.q('b',2));self.assertEqual(compile_choreography(t,qs,self.ref(current=False),20).status,'HOLD_NO_CHOREOGRAPHY')
    def test_k27_nonauthority(self):
        t=T(lambda p,a,b:p);qs=(self.q('p',0),self.q('a',1),self.q('b',2));p=compile_choreography(t,qs,self.ref(),20,k27_coordinate='K27:0');self.assertFalse(p.gate10);self.assertFalse(p.effect_authority);self.assertEqual(p.authority,D0)
    def test_weighted_avoids_irrelevant_expensive(self):
        t=T(lambda p,a,b:p and a);qs=(self.q('p',0,1),self.q('a',1,2,private=True),self.q('b',2,9,private=True));p=compile_choreography(t,qs,self.ref(),50);self.assertEqual(p.tree.action,'p');self.assertEqual(p.tree.one.action,'a')
    def test_permutation_invariant(self):
        t=T(lambda p,a,b:p and (a or b));qs=(self.q('p',0),self.q('a',1,private=True),self.q('b',2,private=True));roots={compile_choreography(t,p,self.ref(),20).plan_root for p in itertools.permutations(qs)};self.assertEqual(len(roots),1)
    def test_bad_truth_shape(self):
        with self.assertRaises(ValueError):compile_choreography((0,1),(self.q('p',0),self.q('a',1)),self.ref(),10)
if __name__=='__main__':unittest.main()
