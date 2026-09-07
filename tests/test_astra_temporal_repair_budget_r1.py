import unittest
from tools.arena.worker_cells.gpt56sol_astra_temporal_repair_budget_r1 import *

S=(Sensitivity('causal',100,2),Sensitivity('validity',100,2),Sensitivity('media',4,8),Sensitivity('simulation',2,3),Sensitivity('commitment',100,2),Sensitivity('externalization',100,2))

class TestTemporalBudget(unittest.TestCase):
    def test_scalar_clock_aliases_distinct_time(self):
        a=TemporalPoint(5,9,100,7,2,0); b=TemporalPoint(5,8,100,7,2,0)
        self.assertTrue(scalar_collision(a,b,('causal',)))
    def test_hard_domains_noncompensatory(self):
        p=compile_exactness(S,ConsequenceBudget(999,8)); self.assertEqual(p.status,'READY_D0'); self.assertTrue(HARD.issubset(p.exact_domains))
    def test_soft_domains_can_coarsen_under_error_budget(self):
        p=compile_exactness(S,ConsequenceBudget(6,8)); self.assertEqual(p.exact_domains,HARD); self.assertEqual(p.bounded_error,6)
    def test_tighter_error_compiles_media_exactness(self):
        p=compile_exactness(S,ConsequenceBudget(2,16)); self.assertIn('media',p.exact_domains); self.assertNotIn('simulation',p.exact_domains); self.assertEqual(p.bounded_error,2)
    def test_zero_error_compiles_both_soft_domains(self):
        p=compile_exactness(S,ConsequenceBudget(0,19)); self.assertEqual(p.exact_domains,frozenset(DOMAINS))
    def test_insufficient_cost_holds(self): self.assertTrue(compile_exactness(S,ConsequenceBudget(0,7)).status.startswith('HOLD'))
    def test_plan_time_invalid_hard_rule_refused(self):
        p=compile_exactness(S,ConsequenceBudget(6,8)); now=TemporalPoint(5,9,1,1,2,0)
        with self.assertRaises(ValueError): issue_lease('e',now,[TemporalRule('validity','eq',10)],p)
    def test_at_use_validity_drift_reopens(self):
        p=compile_exactness(S,ConsequenceBudget(6,8)); at=TemporalPoint(5,9,1,1,2,0)
        lease=issue_lease('e',at,[TemporalRule('validity','eq',9)],p)
        self.assertEqual(validate_at_use(lease,TemporalPoint(6,8,5,2,3,0)).status,'HOLD_TEMPORAL_REPROOF')
    def test_soft_media_rule_not_accidentally_authoritative_when_coarse(self):
        p=compile_exactness(S,ConsequenceBudget(6,8)); at=TemporalPoint(5,9,100,1,2,0)
        lease=issue_lease('e',at,[TemporalRule('validity','eq',9),TemporalRule('media','within',100,1)],p)
        self.assertEqual(validate_at_use(lease,TemporalPoint(5,9,999,1,2,0)).status,'READY_D0')
    def test_externalization_frontier_cannot_be_bought_off(self):
        p=compile_exactness(S,ConsequenceBudget(999,8)); at=TemporalPoint(5,9,100,1,2,0)
        lease=issue_lease('e',at,[TemporalRule('externalization','le',0)],p)
        self.assertEqual(validate_at_use(lease,TemporalPoint(6,9,101,2,3,1)).status,'HOLD_TEMPORAL_REPROOF')
    def test_no_authority_promotion(self):
        p=compile_exactness(S,ConsequenceBudget(6,8)); self.assertFalse(p.gate10); self.assertFalse(p.effect_authority); self.assertEqual(p.authority,D0)

if __name__=='__main__':unittest.main()
