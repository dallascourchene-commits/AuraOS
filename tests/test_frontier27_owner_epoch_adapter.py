import os
import sys
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
import unittest
from frontier27_runtime import ExpertResidencyLRU, FrontierOffload, StorageTier
from frontier27_owner_epoch_adapter import EpochExpertResidencyLRU, EpochFrontierOffload, snapshot, unchanged


class FrontierOwnerEpochAdapterTests(unittest.TestCase):
    def test_governed_prefetch_equivalence(self):
        a=ExpertResidencyLRU(3); b=EpochExpertResidencyLRU(3)
        for x in (1,2,3,1,2,4): a.prefetch(x); b.prefetch(x)
        self.assertEqual(tuple(a.r.items()), tuple(b.r.items()))
        self.assertEqual((a.hits,a.misses),(b.hits,b.misses))

    def test_governed_access_equivalence(self):
        a=ExpertResidencyLRU(3); b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): a.prefetch(x); b.prefetch(x)
        self.assertEqual([a.access(x) for x in (1,4,2,4)], [b.access(x) for x in (1,4,2,4)])
        self.assertEqual((tuple(a.r.items()),a.hits,a.misses),(tuple(b.r.items()),b.hits,b.misses))

    def test_identical_visible_prefetch_advances_epoch(self):
        b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): b.prefetch(x)
        before=tuple(b.r.items()); e=b.mutation_epoch
        b.prefetch(3)
        self.assertEqual(tuple(b.r.items()),before)
        self.assertEqual(b.mutation_epoch,e+1)

    def test_governed_aba_is_detected(self):
        b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): b.prefetch(x)
        before=snapshot(b); order=tuple(b.r.items())
        for x in (1,2,3): b.prefetch(x)
        self.assertEqual(tuple(b.r.items()),order)
        self.assertFalse(unchanged(b,before))

    def test_raw_mapping_bypass_is_explicit_negative_control(self):
        b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): b.prefetch(x)
        before=snapshot(b); order=tuple(b.r.items())
        for x in (1,2,3): b.r.move_to_end(x)
        self.assertEqual(tuple(b.r.items()),order)
        self.assertTrue(unchanged(b,before))

    def test_resident_read_does_not_advance_epoch(self):
        b=EpochExpertResidencyLRU(1); b.prefetch(1); e=b.mutation_epoch
        self.assertTrue(b.resident(1)); self.assertEqual(b.mutation_epoch,e)

    def test_frontier_result_equivalence(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0)
        a=FrontierOffload(1024,3,tier,1.0,10.0)
        b=EpochFrontierOffload(1024,3,tier,1.0,10.0)
        routes=[[1,2],[2,3],[]]; preds=[[1],[3],[]]
        self.assertEqual(a.run(routes,preds),b.run(routes,preds))
        self.assertEqual((tuple(a.r.r.items()),a.r.hits,a.r.misses),(tuple(b.r.r.items()),b.r.hits,b.r.misses))
        self.assertGreater(b.r.mutation_epoch,0)

    def test_rejected_stream_does_not_advance_epoch(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0)
        b=EpochFrontierOffload(1024,3,tier,1.0,10.0); e=b.r.mutation_epoch
        with self.assertRaises(ValueError): b.run([[1],[2]],[[1]])
        self.assertEqual(b.r.mutation_epoch,e)

    def test_empty_run_does_not_advance_epoch(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0)
        b=EpochFrontierOffload(1024,3,tier,1.0,10.0); e=b.r.mutation_epoch
        self.assertEqual(b.run([],[])['hit_rate'],0.0)
        self.assertEqual(b.r.mutation_epoch,e)

    def test_epoch_monotone_for_governed_writes(self):
        b=EpochExpertResidencyLRU(2)
        b.prefetch(1); e1=b.mutation_epoch
        b.access(1); e2=b.mutation_epoch
        b.prefetch(1); e3=b.mutation_epoch
        self.assertEqual((e1,e2,e3),(1,2,3))

if __name__=='__main__': unittest.main()
