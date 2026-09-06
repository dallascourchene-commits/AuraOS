import math
import unittest
from tools.arena.frontier27_runtime import FrontierOffload, StorageTier
from tools.arena.worker_cells.gpt56sol_frontier27_exact_projection.exact_projection import (
    freeze_records_with_aggregate_budget,
    run_frontier_exact_projected,
)
class ExactProjectionR11Tests(unittest.TestCase):
    def tier(self, *, bandwidth=1e9, jpgb=2.0, capacity=(1<<63)-1):
        return StorageTier('ssd', capacity, bandwidth, jpgb)
    def state(self, f): return (tuple(f.r.r.items()), f.r.hits, f.r.misses)
    def test_valid_result_and_state_match_direct_owner(self):
        a=FrontierOffload(1024,8,self.tier(),0.1,10.0); b=FrontierOffload(1024,8,self.tier(),0.1,10.0)
        routes=[(1,2),(2,3)]; preds=[(1,4),(3,5)]
        expected=b.run(routes,preds); got=run_frontier_exact_projected(a,routes,preds)
        self.assertEqual(got,expected); self.assertEqual(self.state(a),self.state(b))
    def test_exact_projection_preserves_preexisting_state(self):
        a=FrontierOffload(1024,8,self.tier(),0.1,10.0); b=FrontierOffload(1024,8,self.tier(),0.1,10.0)
        for x in (9,10,11): a.r.access(x); b.r.access(x)
        expected=b.run([(9,12)],[(12,)]); got=run_frontier_exact_projected(a,[(9,12)],[(12,)])
        self.assertEqual(got,expected); self.assertEqual(self.state(a),self.state(b))
    def test_all_hit_collision_admitted_where_worst_case_overflows(self):
        size=838_488_366_986_797_800; bw=float.fromhex('0x1.0000000000001p-961')
        f=FrontierOffload(size,11,self.tier(bandwidth=bw,jpgb=0.0),0.0,0.0)
        for x in range(11): f.r.access(x)
        before=self.state(f); got=run_frontier_exact_projected(f,[(i,) for i in range(11)],[() for _ in range(11)])
        self.assertEqual(got['seconds'],0.0); self.assertEqual(got['energy_j'],0.0); self.assertTrue(math.isfinite(got['hit_rate']))
        self.assertNotEqual(self.state(f),before)
    def test_true_overflow_rejected_before_real_mutation(self):
        size=838_488_366_986_797_800; bw=float.fromhex('0x1.0000000000001p-961')
        f=FrontierOffload(size,0,self.tier(bandwidth=bw,jpgb=0.0),0.0,0.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_exact_projected(f,[(i,) for i in range(11)],[() for _ in range(11)])
        self.assertEqual(self.state(f),before)

    def test_all_hit_high_energy_admitted_despite_aggregate_potential_overflow(self):
        size=600_000_000; jpgb=1.7e308
        f=FrontierOffload(size,2,self.tier(bandwidth=1e9,jpgb=jpgb),0.0,0.0)
        for x in range(2): f.r.access(x)
        got=run_frontier_exact_projected(f,[(0,),(1,)],[(),()])
        self.assertEqual(got['bytes'],0); self.assertEqual(got['seconds'],0.0); self.assertEqual(got['energy_j'],0.0)
    def test_actual_high_energy_overflow_rejected_before_real_mutation(self):
        size=600_000_000; jpgb=1.7e308
        f=FrontierOffload(size,0,self.tier(bandwidth=1e9,jpgb=jpgb),0.0,0.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_exact_projected(f,[(0,),(1,)],[(),()])
        self.assertEqual(self.state(f),before)
    def test_shared_aggregate_budget_rejects_routes_plus_preds(self):
        routes=[tuple(range(3)),tuple(range(3))]; preds=[tuple(range(3)),tuple(range(3))]
        with self.assertRaises(ValueError): freeze_records_with_aggregate_budget(routes,preds,max_records=4,max_items_per_record=4,max_aggregate_items=10)
    def test_aggregate_rejection_is_failure_atomic(self):
        f=FrontierOffload(1024,8,self.tier(),0.1,10.0); before=self.state(f)
        many=tuple(range(4096)); routes=[many]*25; preds=[many]*25
        with self.assertRaises(ValueError): run_frontier_exact_projected(f,routes,preds)
        self.assertEqual(self.state(f),before)
    def test_projection_does_not_mutate_real_owner_on_rejection(self):
        f=FrontierOffload((1<<63)-1,0,self.tier(bandwidth=5e-324,jpgb=0.0),0.0,0.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_exact_projected(f,[(1,)],[()])
        self.assertEqual(self.state(f),before)
if __name__=='__main__': unittest.main()
