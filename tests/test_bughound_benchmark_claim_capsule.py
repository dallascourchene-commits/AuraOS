import random, unittest
from dataclasses import replace
from tools.bughound.benchmark_claim_capsule import *

def iv(p,w=.01): return IntervalV1(max(0,p-w),p,min(1,p+w))
def cv(p,w=1): return IntervalV1(max(0,p-w),p,p+w)
def run(system="bughound",gen="g1",boost=0.0,cost=100,observer="obs-a"):
    q=tuple((a,iv(min(.99,.70+boost+i*.02))) for i,a in enumerate(QUALITY_AXES))
    c=(("tool_calls",cv(cost,2)),("tokens",cv(cost*100,200)),("elapsed_ms",cv(cost*50,100)))
    return BenchmarkRunReceiptV1(system,gen,"VULNGYM","0.1.4","bench-root","cut-d","split-d","cases-d","eval-g","tools-d","budget-d",gen*40 if len(gen)==1 else "a"*40,"run-1","job-1",True,True,True,True,True,q,c,observer)

class ClaimCapsuleTests(unittest.TestCase):
    def test_valid_run(self): validate_run(run())
    def test_effect_fails(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),authority=True))
    def test_incomplete_fails(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),completed=False))
    def test_exact_head_required(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),exact_head_verified=False))
    def test_historical_blind_required(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),historical_blind=False))
    def test_repo_disjoint_required(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),repo_group_disjoint=False))
    def test_contamination_free_required(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),contamination_free=False))
    def test_missing_axis_fails(self):
        with self.assertRaises(ClaimCapsuleError): validate_run(replace(run(),quality=run().quality[:-1]))
    def test_unmatched_cut_fails(self):
        with self.assertRaises(ClaimCapsuleError): compare(run(boost=.2),[replace(run(system="base",observer="obs-b"),historical_cut_digest="other")],claim_scope="heldout")
    def test_unmatched_budget_fails(self):
        with self.assertRaises(ClaimCapsuleError): compare(run(boost=.2),[replace(run(system="base",observer="obs-b"),resource_budget_digest="other")],claim_scope="heldout")
    def test_unmatched_cases_fail(self):
        with self.assertRaises(ClaimCapsuleError): compare(run(boost=.2),[replace(run(system="base",observer="obs-b"),case_set_digest="other")],claim_scope="heldout")
    def test_same_observer_fails(self):
        with self.assertRaises(ClaimCapsuleError): compare(run(boost=.2),[run(system="base")],claim_scope="heldout")
    def test_self_comparison_fails(self):
        with self.assertRaises(ClaimCapsuleError): compare(run(),[replace(run(),independent_observer_ref="obs-b")],claim_scope="heldout")
    def test_strict_dominance_supports_scoped_superiority(self):
        c=run(boost=.20,cost=80,observer="obs-a")
        b=run(system="baseline",boost=0,cost=100,observer="obs-b")
        r=compare(c,[b],claim_scope="VulnGym historical blind v0.1.4 exact case set")
        self.assertEqual("SCOPED_SUPERIORITY_SUPPORTED",r.status)
        self.assertFalse(r.generalized_real_world_superiority)
        self.assertFalse(r.authority)
    def test_one_overlapping_quality_interval_holds(self):
        c=run(boost=.20,cost=80,observer="obs-a")
        b=run(system="baseline",observer="obs-b")
        q=dict(c.quality); q["precision"]=IntervalV1(.70,.72,.74)
        r=compare(replace(c,quality=tuple(q.items())),[b],claim_scope="heldout")
        self.assertEqual("CLAIM_HOLD_INSUFFICIENT_DOMINANCE",r.status)
    def test_worse_cost_holds(self):
        r=compare(run(boost=.20,cost=130,observer="obs-a"),[run(system="base",cost=100,observer="obs-b")],claim_scope="heldout")
        self.assertEqual("CLAIM_HOLD_INSUFFICIENT_DOMINANCE",r.status)
    def test_multiple_baselines_all_must_be_dominated(self):
        c=run(boost=.20,cost=80,observer="a")
        b1=run(system="b1",boost=0,cost=100,observer="b")
        b2=run(system="b2",boost=.19,cost=100,observer="c")
        self.assertEqual("CLAIM_HOLD_INSUFFICIENT_DOMINANCE",compare(c,[b1,b2],claim_scope="heldout").status)
    def test_receipt_deterministic(self):
        c=run(boost=.20,cost=80,observer="a"); b=run(system="b",observer="b")
        self.assertEqual(compare(c,[b],claim_scope="x").receipt_digest,compare(c,[b],claim_scope="x").receipt_digest)
    def test_basis_changes_change_receipt(self):
        c=run(boost=.20,cost=80,observer="a"); b=run(system="b",observer="b")
        r1=compare(c,[b],claim_scope="x")
        c2=replace(c,benchmark_semantic_root="r2"); b2=replace(b,benchmark_semantic_root="r2")
        r2=compare(c2,[b2],claim_scope="x")
        self.assertNotEqual(r1.basis_digest,r2.basis_digest)
    def test_hyper1000(self): self.assertEqual(1000,len(set(hyper1000())))
    def test_randomized_reference_policy(self):
        rng=random.Random(11011)
        for i in range(100_000):
            boost=rng.random()*.3
            costc=rng.randint(50,150); costb=rng.randint(70,130)
            c=run(boost=boost,cost=costc,observer="a")
            b=run(system="base",boost=0,cost=costb,observer="b")
            r=compare(c,[b],claim_scope="stress")
            cq,cc=dict(c.quality),dict(c.costs); bq,bc=dict(b.quality),dict(b.costs)
            expected=all(cq[a].low>bq[a].high for a in QUALITY_AXES) and all(cc[a].high<=bc[a].high for a in COST_AXES)
            self.assertEqual(expected,r.status=="SCOPED_SUPERIORITY_SUPPORTED")

if __name__=="__main__": unittest.main()
