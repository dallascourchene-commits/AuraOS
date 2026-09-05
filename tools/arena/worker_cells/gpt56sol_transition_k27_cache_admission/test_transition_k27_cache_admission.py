import itertools, random, unittest
from dataclasses import replace
from transition_k27_cache_admission import *

class Tests(unittest.TestCase):
    def test_valid_neutral_rebind_admits(self):
        t,e,c,s=demo_fixture(); r=decide(t,e,c,s)
        self.assertEqual(r.decision,Decision.ADMIT_RUNTIME_REUSE); self.assertIsNotNone(r.route_score)
    def test_exact_unchanged_admits(self):
        t,e,c,s=demo_fixture(TransitionDisposition.EXACT_UNCHANGED)
        self.assertEqual(decide(t,e,c,s).decision,Decision.ADMIT_RUNTIME_REUSE)
    def test_consequence_change_recomputes(self):
        t,e,c,s=demo_fixture(TransitionDisposition.CONSEQUENCE_CHANGED)
        self.assertEqual(decide(t,e,c,s).decision,Decision.RECOMPUTE)
    def test_unknown_recomputes(self):
        t,e,c,s=demo_fixture(TransitionDisposition.UNKNOWN)
        self.assertEqual(decide(t,e,c,s).decision,Decision.RECOMPUTE)
    def test_dependency_change_blocks_neutral(self):
        t,e,c,s=demo_fixture(); bad=make_transition_receipt(disposition=TransitionDisposition.PROOF_NEUTRAL_REBIND,
            prior_generation=t.prior_generation,current_generation=t.current_generation,provider_anchor_root=t.provider_anchor_root,
            dependency_root=t.dependency_root,prior_consequence_root=t.prior_consequence_root,current_consequence_root=t.current_consequence_root,
            dependency_keys=t.dependency_keys,changed_keys=("trace",),provider_observation_verified=True)
        self.assertEqual(decide(bad,e,c,s).decision,Decision.HOLD)
    def test_provider_anchor_drift_holds(self):
        t,e,c,s=demo_fixture(); c=replace(c,provider_anchor_root=digest("new"))
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_semantic_root_drift_holds(self):
        t,e,c,s=demo_fixture(); c=replace(c,semantic_root=digest("new"))
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_runtime_owner_drift_holds(self):
        t,e,c,s=demo_fixture(); c=replace(c,expected_runtime_owner="other")
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_compatibility_drift_holds(self):
        t,e,c,s=demo_fixture(); c=replace(c,compatibility_profile="kv-v2")
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_benchmark_drift_holds(self):
        t,e,c,s=demo_fixture(); c=replace(c,benchmark_generation="5"*40)
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_coordinate_tamper_holds(self):
        t,e,c,s=demo_fixture(); e=replace(e,coordinate=((e.coordinate[0]+1)%27,e.coordinate[1],e.coordinate[2]))
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_entry_root_tamper_holds(self):
        t,e,c,s=demo_fixture(); e=replace(e,payload_hash=digest("forged"))
        self.assertEqual(decide(t,e,c,s).decision,Decision.HOLD)
    def test_routing_cannot_repair_semantics(self):
        t,e,c,s=demo_fixture(); c=replace(c,semantic_root=digest("stale")); huge=RoutingSignals(1e12,1000000,1e9,1e9,0)
        r=decide(t,e,c,huge); self.assertEqual(r.decision,Decision.HOLD); self.assertIsNone(r.route_score)
    def test_invalid_routing_only_matters_after_admission(self):
        t,e,c,s=demo_fixture(); c=replace(c,semantic_root=digest("stale")); bad=RoutingSignals(float('nan'),0,0,0,0)
        self.assertEqual(decide(t,e,c,bad).decision,Decision.HOLD)
    def test_invalid_routing_on_valid_semantics_holds(self):
        t,e,c,s=demo_fixture(); bad=RoutingSignals(float('nan'),0,0,0,0)
        r=decide(t,e,c,bad); self.assertEqual(r.decision,Decision.HOLD); self.assertIn("INVALID_ROUTING_FLOAT",r.reasons)
    def test_routing_overflow_on_valid_semantics_holds(self):
        t,e,c,s=demo_fixture(); bad=RoutingSignals(1e308,10,1e308,1e308,0)
        r=decide(t,e,c,bad); self.assertEqual(r.decision,Decision.HOLD); self.assertIn("ROUTING_SCORE_OVERFLOW",r.reasons)
    def test_coordinate_is_deterministic(self):
        _,e,_,_=demo_fixture(); self.assertEqual(e.coordinate,coordinate_for(e.identity_root))
    def test_omega8_noncompensatory(self):
        self.assertEqual(sum(classify8(x) for x in itertools.product(range(3),repeat=8)),1)
    def test_13d_tail_cannot_repair_bad_core(self):
        core=(0,2,2,2,2,2,2,2); self.assertFalse(any(classify13(core+tail) for tail in itertools.product(range(3),repeat=5)))
    def test_hs1000_mutations_no_false_admit(self):
        t,e,c,s=demo_fixture(); rng=random.Random(20260905); false=0
        mutators=[
          lambda e,c: (replace(e,semantic_root=digest(str(rng.random()))),c),
          lambda e,c: (e,replace(c,provider_anchor_root=digest(str(rng.random())))),
          lambda e,c: (e,replace(c,dependency_root=digest(str(rng.random())))),
          lambda e,c: (e,replace(c,expected_runtime_owner="other")),
          lambda e,c: (e,replace(c,runtime_generation="5"*40)),
          lambda e,c: (e,replace(c,compatibility_profile="kv-v2")),
          lambda e,c: (e,replace(c,benchmark_generation="6"*40)),
          lambda e,c: (e,replace(c,payload_hash=digest(str(rng.random())))),
          lambda e,c: (replace(e,coordinate=((e.coordinate[0]+1)%27,e.coordinate[1],e.coordinate[2])),c),
          lambda e,c: (replace(e,entry_root=digest(str(rng.random()))),c),
        ]
        for m in mutators:
            for _ in range(100):
                ee,cc=m(e,c)
                false += decide(t,ee,cc,s).decision is Decision.ADMIT_RUNTIME_REUSE
        self.assertEqual(false,0)

if __name__=='__main__': unittest.main()
