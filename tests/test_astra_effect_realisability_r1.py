import itertools, unittest
from tools.arena.worker_cells.gpt56sol_astra_realisability_r1 import *

def p(edges=False,cap='*',epoch=3,we=3,irr=False,execd=False):
    effects=(Effect('choose','A',emits_choice='mode',emits_value='x',witness_epoch=we),Effect('visual','B',('choose',),'mode','x',witness_epoch=we,irreversible=irr),Effect('audio','C',('visual',),witness_epoch=we))
    info=(InfoEdge('choose','B','done:choose'),InfoEdge('choose','B','choice:mode=x'),InfoEdge('visual','C','done:visual')) if edges else ()
    return Program(effects,10,epoch,info,(Capability('B',frozenset({cap}),4),Capability('C',frozenset({cap}),4)),frozenset({'visual'}) if execd else frozenset())

class TestAstraRealisabilityR1(unittest.TestCase):
    def test_global_legality_is_not_local_realisability(self):
        self.assertEqual(legal(p()),(True,'LEGAL')); self.assertFalse(realisable(p())[0])
    def test_exact_information_edges_repair_projection(self): self.assertTrue(realisable(p(True))[0])
    def test_minimal_repair_is_non_authoritative(self):
        d=repair(p()); self.assertEqual(d.status,'READY_WITH_MINIMAL_INFO_REPAIR'); self.assertEqual(len(d.repair_edges),3); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)
    def test_capability_block_returns_hold(self): self.assertEqual(repair(p(cap='other')).status,'HOLD_UNREALISABLE')
    def test_stale_witness_holds_before_projection(self): self.assertEqual(repair(p(epoch=4,we=3)).status,'HOLD_STALE_WITNESS')
    def test_irreversible_completed_effect_cannot_be_retro_repaired(self): self.assertEqual(repair(p(irr=True,execd=True)).status,'HOLD_UNREALISABLE')
    def test_capability_is_revalidated_at_use(self):
        d=repair(p()); self.assertEqual(revalidate_at_use(p(),d,[Capability('B',frozenset({'other'})),Capability('C',frozenset({'*'}))]).status,'HOLD_CAPABILITY_REVOKED_AT_USE')
    def test_k27_is_locality_hint(self): self.assertEqual(candidate_k27(p()),(2,1,2))
    def test_omega8_cannot_compensate_hard_failure(self):
        for tail in itertools.product(range(3),repeat=5): self.assertEqual(crystalline_gate((0,2,2,2,2,2,2,2),tail),'HOLD_HARD_AXIS')
    def test_hs1000_freezes_before_quotient(self):
        rows=hs1000_candidates(); self.assertEqual(len(rows),1000); self.assertEqual(len(hs1000_quotient(rows)),100); self.assertTrue(all(x['expected_gain']=='UNSCORED_AT_FREEZE' for x in rows)); self.assertEqual(hs1000_freeze_root(rows),'a0e6dbcbccad351205616dbe8e4dc430c1cc8384954a2b831a8d1a0e16452a44')

if __name__=='__main__': unittest.main()
