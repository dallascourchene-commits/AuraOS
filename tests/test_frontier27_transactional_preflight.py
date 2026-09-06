import math
import unittest
from tools.arena.frontier27_runtime import FrontierOffload, LegacyOffload, StorageTier
from tools.arena.worker_cells.gpt56sol_frontier27_numeric_preflight.transactional_preflight import (
    MAX_GOVERNED_INT, _finite_scalar, _freeze_records, run_frontier_totalized, run_legacy_totalized,
)

class IterRaisesOnIter:
    def __init__(self, exc): self.exc=exc
    def __iter__(self): raise self.exc
class IterRaisesOnNext:
    def __init__(self, first, exc): self.first=first; self.exc=exc; self.done=False
    def __iter__(self): return self
    def __next__(self):
        if not self.done: self.done=True; return self.first
        raise self.exc
class InfiniteRecords:
    def __iter__(self):
        while True: yield (1,)
class InfiniteItems:
    def __iter__(self):
        while True: yield 1
class ControlSignalOnIter:
    def __iter__(self): raise KeyboardInterrupt()

class TransactionalPreflightTests(unittest.TestCase):
    def tier(self, *, bandwidth=1_000_000_000.0, jpgb=2.0, capacity=1_000_000_000):
        return StorageTier('ssd', capacity, bandwidth, jpgb)
    def state(self, f): return (tuple(f.r.r.items()), f.r.hits, f.r.misses)

    def test_01_scalar_totality_rejects_huge_int_without_overflow(self):
        self.assertFalse(_finite_scalar(10**1000)); self.assertTrue(_finite_scalar(MAX_GOVERNED_INT))
    def test_02_frontier_rejects_unbounded_size_before_mutation(self):
        f=FrontierOffload(MAX_GOVERNED_INT+1,4,self.tier(),0.1,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,)],[(1,)])
        self.assertEqual(self.state(f),before)
    def test_03_legacy_rejects_unbounded_size_as_valueerror(self):
        l=LegacyOffload(MAX_GOVERNED_INT+1,1.0,1.0)
        with self.assertRaises(ValueError): run_legacy_totalized(l,[(1,)],[(1,)])
    def test_04_window_product_overflow_rejected_before_mutation(self):
        f=FrontierOffload(1024,4,self.tier(bandwidth=1e308),1000.0,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,)],[(1,)])
        self.assertEqual(self.state(f),before)
    def test_05_tiny_bandwidth_nonfinite_seconds_rejected_before_mutation(self):
        f=FrontierOffload(1024,4,self.tier(bandwidth=5e-324),0.0,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,)],[()])
        self.assertEqual(self.state(f),before)
    def test_06_nonfinite_energy_rejected_before_mutation(self):
        f=FrontierOffload(MAX_GOVERNED_INT,4,self.tier(jpgb=1e308,capacity=MAX_GOVERNED_INT),0.0,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,)],[()])
        self.assertEqual(self.state(f),before)
    def test_07_nested_non_integer_route_rejected(self):
        f=FrontierOffload(1024,4,self.tier(),0.1,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,),('bad',)],[(1,),(2,)])
        self.assertEqual(self.state(f),before)
    def test_08_nested_non_integer_prediction_rejected(self):
        f=FrontierOffload(1024,4,self.tier(),0.1,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,),(2,)],[(1,),(object(),)])
        self.assertEqual(self.state(f),before)
    def test_09_owner_exception_rolls_back_exact_state(self):
        f=FrontierOffload(1024,4,self.tier(),0.1,10.0); run_frontier_totalized(f,[(1,)],[()]); before=self.state(f); original=f.run
        def boom(routes,preds): f.r.access(999); raise RuntimeError('synthetic')
        f.run=boom
        try:
            with self.assertRaises(RuntimeError): run_frontier_totalized(f,[(2,)],[()])
        finally: f.run=original
        self.assertEqual(self.state(f),before)
    def test_10_nonfinite_owner_result_rolls_back_exact_state(self):
        f=FrontierOffload(1024,4,self.tier(),0.1,10.0); before=self.state(f); original=f.run
        def bad(routes,preds): f.r.access(999); return {'bytes':1,'seconds':math.inf,'energy_j':0.0,'hit_rate':0.0,'prefetch_transfers':0}
        f.run=bad
        try:
            with self.assertRaises(ValueError): run_frontier_totalized(f,[(2,)],[()])
        finally: f.run=original
        self.assertEqual(self.state(f),before)
    def test_11_ordinary_frontier_semantics_preserved(self):
        got=run_frontier_totalized(FrontierOffload(1024,4,self.tier(),0.1,10.0),[(1,2)],[(1,3)])
        self.assertTrue(math.isfinite(got['seconds']) and math.isfinite(got['energy_j']))
    def test_12_ordinary_legacy_semantics_preserved(self):
        got=run_legacy_totalized(LegacyOffload(1024,1e9,2.0),[(1,2)],[(1,3)])
        self.assertTrue(math.isfinite(got['seconds']) and math.isfinite(got['energy_j']))
    def test_13_equal_length_checked_before_owner(self):
        f=FrontierOffload(1024,4,self.tier(),0.1,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[(1,)],[(1,),(2,)])
        self.assertEqual(self.state(f),before)
    def test_14_prediction_byte_cap_bound(self):
        f=FrontierOffload(MAX_GOVERNED_INT,4,self.tier(capacity=MAX_GOVERNED_INT),0.0,10.0); before=self.state(f)
        with self.assertRaises(ValueError): run_frontier_totalized(f,[()],[(1,2)])
        self.assertEqual(self.state(f),before)
    def test_15_outer_iter_runtimeerror_translated(self):
        with self.assertRaises(ValueError): _freeze_records(IterRaisesOnIter(RuntimeError('boom')),[],max_records=4,max_items_per_record=4)
    def test_16_outer_next_keyerror_translated(self):
        with self.assertRaises(ValueError): _freeze_records(IterRaisesOnNext((1,),KeyError('boom')),[(1,)],max_records=4,max_items_per_record=4)
    def test_17_inner_iter_lookuperror_translated(self):
        with self.assertRaises(ValueError): _freeze_records([IterRaisesOnIter(LookupError('boom'))],[(1,)],max_records=4,max_items_per_record=4)
    def test_18_inner_next_runtimeerror_translated(self):
        with self.assertRaises(ValueError): _freeze_records([IterRaisesOnNext(1,RuntimeError('boom'))],[(1,)],max_records=4,max_items_per_record=4)
    def test_19_infinite_outer_rejected_after_bounded_work(self):
        with self.assertRaisesRegex(ValueError,'governed cardinality'): _freeze_records(InfiniteRecords(),[(1,)]*4,max_records=4,max_items_per_record=4)
    def test_20_infinite_inner_rejected_after_bounded_work(self):
        with self.assertRaisesRegex(ValueError,'governed cardinality'): _freeze_records([InfiniteItems()],[(1,)],max_records=4,max_items_per_record=4)
    def test_21_bool_expert_id_rejected(self):
        with self.assertRaises(ValueError): _freeze_records([(True,)],[(1,)],max_records=4,max_items_per_record=4)
    def test_22_process_control_signal_not_swallowed(self):
        with self.assertRaises(KeyboardInterrupt): _freeze_records(ControlSignalOnIter(),[],max_records=4,max_items_per_record=4)
    def test_23_legacy_aggregate_finite_but_owner_order_overflows(self):
        size=281_406_274_007_040; bw=float.fromhex('0x1.fffffffffffe1p-962')
        routes=[tuple(range(n)) for n in ([1,4096]*8)]; preds=[() for _ in routes]
        self.assertTrue(math.isfinite(sum(map(len,routes))*size/bw))
        with self.assertRaisesRegex(ValueError,'owner-style accumulation'):
            run_legacy_totalized(LegacyOffload(size,bw,0.0),routes,preds)
    def test_24_frontier_aggregate_finite_but_repeated_transfer_overflows_before_mutation(self):
        size=838_488_366_986_797_800; bw=float.fromhex('0x1.0000000000001p-961')
        routes=[(i,) for i in range(11)]; preds=[() for _ in routes]
        self.assertTrue(math.isfinite(11*size/bw))
        f=FrontierOffload(size,0,StorageTier('ssd',MAX_GOVERNED_INT,bw,0.0),0.0,0.0); before=self.state(f)
        with self.assertRaisesRegex(ValueError,'owner-style accumulation'):
            run_frontier_totalized(f,routes,preds)
        self.assertEqual(self.state(f),before)

if __name__=='__main__': unittest.main()
