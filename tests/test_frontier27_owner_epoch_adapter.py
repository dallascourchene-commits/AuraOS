import os, sys, unittest
ROOT=os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0,os.path.join(ROOT,'tools','arena'))
from frontier27_runtime import ExpertResidencyLRU, FrontierOffload, StorageTier
from frontier27_owner_epoch_adapter import EpochExpertResidencyLRU, EpochFrontierOffload, snapshot, unchanged, governed_aba_probe

class FrontierOwnerEpochAdapterTests(unittest.TestCase):
    def test_prefetch_equivalence(self):
        a=ExpertResidencyLRU(3); b=EpochExpertResidencyLRU(3)
        for x in (1,2,3,1,2,4): a.prefetch(x); b.prefetch(x)
        self.assertEqual(tuple(a.r.items()),tuple(b.r.items()))
        self.assertEqual((a.hits,a.misses),(b.hits,b.misses))

    def test_access_equivalence(self):
        a=ExpertResidencyLRU(3); b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): a.prefetch(x); b.prefetch(x)
        self.assertEqual([a.access(x) for x in (1,4,2,4)],[b.access(x) for x in (1,4,2,4)])
        self.assertEqual((tuple(a.r.items()),a.hits,a.misses),(tuple(b.r.items()),b.hits,b.misses))

    def test_identical_visible_write_advances(self):
        b=EpochExpertResidencyLRU(3)
        for x in (1,2,3): b.prefetch(x)
        visible=(tuple(b.r.items()),b.hits,b.misses); e=b.mutation_epoch
        b.prefetch(3)
        self.assertEqual((tuple(b.r.items()),b.hits,b.misses),visible)
        self.assertEqual(b.mutation_epoch,e+1)

    def test_governed_aba_detected(self): self.assertTrue(governed_aba_probe())

    def test_public_residency_is_read_only(self):
        b=EpochExpertResidencyLRU(3); b.prefetch(1)
        with self.assertRaises(TypeError): b.r[2]=None
        with self.assertRaises(AttributeError): b.r.move_to_end(1)

    def test_public_counters_are_read_only(self):
        b=EpochExpertResidencyLRU(3)
        with self.assertRaises(AttributeError): b.hits=4
        with self.assertRaises(AttributeError): b.misses=4
        with self.assertRaises(AttributeError): b.mutation_epoch=4

    def test_resident_read_no_epoch(self):
        b=EpochExpertResidencyLRU(1); b.prefetch(1); e=b.mutation_epoch
        self.assertTrue(b.resident(1)); self.assertEqual(b.mutation_epoch,e)

    def test_frontier_result_equivalence(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0)
        a=FrontierOffload(1024,3,tier,1.0,10.0); b=EpochFrontierOffload(1024,3,tier,1.0,10.0)
        routes=[[1,2],[2,3],[]]; preds=[[1],[3],[]]
        self.assertEqual(a.run(routes,preds),b.run(routes,preds))
        self.assertEqual((tuple(a.r.r.items()),a.r.hits,a.r.misses),(tuple(b.r.r.items()),b.r.hits,b.r.misses))

    def test_rejected_stream_no_epoch(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0); b=EpochFrontierOffload(1024,3,tier,1.0,10.0); e=b.r.mutation_epoch
        with self.assertRaises(ValueError): b.run([[1],[2]],[[1]])
        self.assertEqual(b.r.mutation_epoch,e)

    def test_empty_run_no_epoch(self):
        tier=StorageTier('ssd',10**9,1024.0,1.0); b=EpochFrontierOffload(1024,3,tier,1.0,10.0); e=b.r.mutation_epoch
        self.assertEqual(b.run([],[])['hit_rate'],0.0); self.assertEqual(b.r.mutation_epoch,e)

if __name__=='__main__': unittest.main()
