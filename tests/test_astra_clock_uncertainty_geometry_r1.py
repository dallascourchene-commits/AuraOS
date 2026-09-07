import unittest
from tools.arena.worker_cells.gpt56sol_astra_clock_uncertainty_geometry_r1 import *

class ClockGeometryTests(unittest.TestCase):
    def rel(self,src,dst,lo=0,hi=0,skew=0,current=True,valid=10_000_000,id='r'):
        return ClockRelation(src,dst,lo,hi,skew,1_000_000,valid,current,id)
    def test_exact_relation_ready(self):
        r=compile_route('causal','media',[self.rel('causal','media',100,100)])
        self.assertEqual(decide(r,TimeInterval(1_000_000,1_000_000),DeadlineRequirement(1_000_100)).status,'READY_D0')
    def test_uncertainty_straddles_deadline(self):
        r=compile_route('causal','media',[self.rel('causal','media',0,10_000)])
        src=TimeInterval(1_000_000,1_000_000)
        self.assertTrue(naive_midpoint_deadline_accept(r,src,1_005_000))
        self.assertEqual(decide(r,src,DeadlineRequirement(1_005_000)).status,'HOLD_TEMPORAL_UNCERTAINTY')
    def test_definite_miss(self):
        r=compile_route('causal','media',[self.rel('causal','media',10_000,20_000)])
        self.assertEqual(decide(r,TimeInterval(1_000_000,1_000_000),DeadlineRequirement(1_005_000)).status,'HOLD_DEADLINE_MISS')
    def test_window_uncertainty(self):
        r=compile_route('media','externalization',[self.rel('media','externalization',-2_000,2_000)])
        self.assertEqual(decide(r,TimeInterval(1_000_000,1_000_000),WindowRequirement(999_000,1_001_000)).status,'HOLD_TEMPORAL_UNCERTAINTY')
    def test_stale_relation_holds(self):
        r=compile_route('causal','validity',[self.rel('causal','validity',current=False)])
        self.assertEqual(decide(r,TimeInterval(1_000_000,1_000_000),DeadlineRequirement(2_000_000)).status,'HOLD_CURRENTNESS')
    def test_k27_cannot_authorize(self):
        r=compile_route('causal','validity',[self.rel('causal','validity',current=False)])
        d=decide(r,TimeInterval(1_000_000,1_000_000),DeadlineRequirement(2_000_000),k27_coordinate='K27:HOT')
        self.assertEqual(d.status,'HOLD_CURRENTNESS'); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)
    def test_brute_oracle_matches(self):
        rels=[self.rel('causal','media',-100,200,50,id='a'),self.rel('media','externalization',10,40,75,id='b')]
        r=compile_route('causal','externalization',rels); src=TimeInterval(900_000,1_100_000)
        mapped,_=propagate(r,src); self.assertEqual(mapped,brute_extrema(r,src))
    def test_declaration_permutation_invariant(self):
        rels=[self.rel('causal','media',id='a'),self.rel('media','validity',id='b'),self.rel('validity','externalization',id='c')]
        self.assertEqual(len(permutation_roots('causal','externalization',rels)),1)
    def test_ambiguous_route_rejected(self):
        with self.assertRaises(ValueError): compile_route('causal','media',[self.rel('causal','media',id='a'),self.rel('causal','validity',id='b')])
    def test_unused_relation_rejected(self):
        with self.assertRaises(ValueError): compile_route('causal','media',[self.rel('causal','media',id='a'),self.rel('simulation','validity',id='b')])
    def test_audio_like_clock_relation_requires_uncertainty(self):
        r=compile_route('media','externalization',[self.rel('media','externalization',-2667,2667,20,id='audio-output')])
        self.assertEqual(decide(r,TimeInterval(1_000_000,1_000_000),WindowRequirement(999_000,1_001_000)).status,'HOLD_TEMPORAL_UNCERTAINTY')

if __name__=='__main__': unittest.main()
