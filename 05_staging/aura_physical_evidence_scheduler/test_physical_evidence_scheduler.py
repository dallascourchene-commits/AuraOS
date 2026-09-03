import random, unittest
from dataclasses import replace
from physical_evidence_scheduler import *

class T(unittest.TestCase):
    def setUp(self): self.cache=NegativeKnowledgeCache(); self.s=PhysicalEvidenceScheduler(self.cache)
    def test_glm_hard_predecessor_zero(self):
        c=portfolio_fixture()[0]; d=self.s.assess(c,unresolved_domains={"PHYSICAL_OBSERVATION","CORRECTNESS"}); self.assertEqual(d.disposition,"HOLD_PREDECESSOR"); self.assertEqual(d.score,0)
    def test_glm_training_zero_before_p1(self):
        c=portfolio_fixture()[1]; d=self.s.assess(c,unresolved_domains={"CAUSAL_BENEFIT"}); self.assertEqual(d.disposition,"HOLD_PREDECESSOR"); self.assertEqual(d.score,0)
    def test_bug_physical_requires_authority(self):
        c=replace(portfolio_fixture()[2],satisfied_prerequisites=(BUG_CORPUS,)); d=self.s.assess(c,unresolved_domains={"CORRECTNESS"}); self.assertEqual(d.disposition,"HOLD_OWNER_AUTHORITY")
    def test_no_material_delta_zero(self): self.assertEqual(self.s.assess(portfolio_fixture()[4],unresolved_domains={"CORRECTNESS"}).disposition,"NOOP_NO_MATERIAL_DELTA")
    def test_closed_provider_replay_zero(self): self.assertEqual(self.s.assess(portfolio_fixture()[5],unresolved_domains={"CORRECTNESS"}).disposition,"NOOP_NO_MATERIAL_DELTA")
    def test_admissible_after_hard_gates(self):
        c=replace(portfolio_fixture()[0],satisfied_prerequisites=(GLM_G1,GLM_P0A,AWJ032_ACK)); d=self.s.assess(c,unresolved_domains={"PHYSICAL_OBSERVATION","CORRECTNESS","RUNTIME_CAPABILITY"}); self.assertEqual(d.disposition,"ADMISSIBLE_PRIORITY_CANDIDATE"); self.assertGreater(d.score,0)
    def test_one_operation_multiplexes_typed_leaves(self):
        c=replace(portfolio_fixture()[0],satisfied_prerequisites=(GLM_G1,GLM_P0A,AWJ032_ACK)); d=self.s.assess(c,unresolved_domains={"PHYSICAL_OBSERVATION","CORRECTNESS","RUNTIME_CAPABILITY"}); leaves=evidence_commitments(c,d)
        self.assertEqual({x["operation_id"] for x in leaves},{"GLM-P1-TRACE"}); self.assertEqual({x["domain"] for x in leaves},{"PHYSICAL_OBSERVATION","CORRECTNESS","RUNTIME_CAPABILITY"}); self.assertTrue(all(not x["effect_authority"] for x in leaves))
    def test_no_unresolved_domain_zero(self):
        c=replace(portfolio_fixture()[0],satisfied_prerequisites=(GLM_G1,GLM_P0A,AWJ032_ACK)); self.assertEqual(self.s.assess(c,unresolved_domains={"OWNER_AUTHORITY"}).disposition,"NOOP_NO_UNRESOLVED_DOMAIN")
    def test_negative_knowledge_exact_generation_reuse(self):
        self.cache.record(NegativeKnowledge("X","g1","NO_BENEFIT","f",("HEAD_CHANGE",))); c=ExperimentCandidate("X","P","g1","LOCAL",(),(),1,2,("CORRECTNESS",),True,True,False,"s","t")
        self.assertEqual(self.s.assess(c,unresolved_domains={"CORRECTNESS"}).disposition,"DEPRIORITIZE_NEGATIVE_KNOWLEDGE_REUSE")
    def test_negative_knowledge_reopens_on_invalidator(self):
        self.cache.record(NegativeKnowledge("X","g1","NO_BENEFIT","f",("HEAD_CHANGE",))); c=ExperimentCandidate("X","P","g1","LOCAL",(),(),1,2,("CORRECTNESS",),True,True,False,"s","t")
        self.assertEqual(self.s.assess(c,unresolved_domains={"CORRECTNESS"},observed_invalidators=("HEAD_CHANGE",)).disposition,"ADMISSIBLE_PRIORITY_CANDIDATE")
    def test_negative_knowledge_new_generation_not_reused(self):
        self.cache.record(NegativeKnowledge("X","g1","NO_BENEFIT","f",("HEAD_CHANGE",))); c=ExperimentCandidate("X","P","g2","LOCAL",(),(),1,2,("CORRECTNESS",),True,True,False,"s","t")
        self.assertEqual(self.s.assess(c,unresolved_domains={"CORRECTNESS"}).disposition,"ADMISSIBLE_PRIORITY_CANDIDATE")
    def test_rank_prefers_information_per_cost_after_gates(self):
        a=ExperimentCandidate("A","P","g","L",(),(),2,2,("CORRECTNESS",),True,True,False,"s","t"); b=ExperimentCandidate("B","P","g","L",(),(),2,4,("CORRECTNESS",),True,True,False,"s","t")
        self.assertEqual(self.s.select((a,b),unresolved_domains={"CORRECTNESS"}).experiment_id,"B")
    def test_multi_domain_can_outscore_single_domain(self):
        a=ExperimentCandidate("A","P","g","L",(),(),4,4,("CORRECTNESS","PHYSICAL_OBSERVATION"),True,True,False,"s","t"); b=ExperimentCandidate("B","P","g","L",(),(),3,4,("CORRECTNESS",),True,True,False,"s","t")
        self.assertEqual(self.s.select((a,b),unresolved_domains={"CORRECTNESS","PHYSICAL_OBSERVATION"}).experiment_id,"A")
    def test_score_is_not_authority(self):
        c=ExperimentCandidate("A","P","g","L",(),(),1,100,("CORRECTNESS",),True,True,False,"s","t"); self.assertFalse(self.s.assess(c,unresolved_domains={"CORRECTNESS"}).effect_authority)
    def test_physical_high_score_still_blocked_without_authority(self):
        c=ExperimentCandidate("A","P","g","PHYS",(),(),1,1000,("CORRECTNESS",),False,True,True,"s","t"); d=self.s.assess(c,unresolved_domains={"CORRECTNESS"}); self.assertEqual(d.disposition,"HOLD_OWNER_AUTHORITY"); self.assertEqual(d.score,0)
    def test_10000_exact_generation_negative_reuse(self):
        for i in range(100): self.cache.record(NegativeKnowledge(f"X{i}","g1","KNOWN_FAIL","f",("DELTA",)))
        rng=random.Random(17); reused=0
        for _ in range(10000):
            i=rng.randrange(100); c=ExperimentCandidate(f"X{i}","P","g1","LOCAL",(),(),1,1,("CORRECTNESS",),True,True,False,"s","t"); reused+=self.s.assess(c,unresolved_domains={"CORRECTNESS"}).disposition=="DEPRIORITIZE_NEGATIVE_KNOWLEDGE_REUSE"
        self.assertEqual(reused,10000)
    def test_100000_hard_gate_mutations(self):
        rng=random.Random(20260903)
        for i in range(100000):
            need=("SECURITY",); sat=need if rng.random()>0.5 else (); auth=rng.random()>0.5; physical=rng.random()>0.5
            c=ExperimentCandidate(str(i),"P","g","X",need,sat,1+rng.random()*9,rng.random()*10,("CORRECTNESS",),auth,True,physical,"s","t"); d=self.s.assess(c,unresolved_domains={"CORRECTNESS"})
            if d.disposition=="ADMISSIBLE_PRIORITY_CANDIDATE": self.assertEqual(sat,need); self.assertTrue(auth or not physical)
            if sat!=need: self.assertEqual(d.score,0)
            self.assertFalse(d.effect_authority)
    def test_portfolio_all_current_blocked_or_closed(self):
        rows=self.s.rank(portfolio_fixture(),unresolved_domains={"CORRECTNESS","PHYSICAL_OBSERVATION","CAUSAL_BENEFIT","RUNTIME_CAPABILITY"}); self.assertFalse(any(x.disposition=="ADMISSIBLE_PRIORITY_CANDIDATE" for x in rows))
    def test_cache_conflict_fails(self):
        self.cache.record(NegativeKnowledge("X","g","A","f",()))
        with self.assertRaisesRegex(ValueError,"CONFLICT"): self.cache.record(NegativeKnowledge("X","g","B","f",()))

if __name__=="__main__": unittest.main()
