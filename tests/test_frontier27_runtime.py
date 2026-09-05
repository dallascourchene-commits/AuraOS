import math
import os
import sys
import unittest
from dataclasses import replace

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
from frontier27_runtime import *


class T(unittest.TestCase):
    def test_00_manifest(self): self.assertEqual((len(FRONTIER_27), len(set(FRONTIER_27))), (27, 27))
    def test_01_hard_false(self): self.assertFalse(HardFalseSecurityGate.admit(source_audited=True, runtime_hard_false=False, remote_code_widening=False))
    def test_02_hybrid_index(self):
        i = HybridIndexBridge(2); i.add("a", "alpha beta", (1, 2, 3)); self.assertTrue(i.candidates("alpha beta", 64))
    def test_03_export_receipt(self):
        payload = {"x": 1}; r = ExportReceipt.build(payload, ["a"], "g"); self.assertTrue(r.reusable(["a"], "g", payload=payload)); self.assertFalse(r.reusable(["b"], "g", payload=payload)); self.assertFalse(r.reusable(["a"], "g"))
    def test_04_typed_edges(self):
        g = TypedGraphEdges(); g.add(TypedEdge("a", "r", "b", "p", 1)); self.assertEqual(g.lookup("a", "r")[0].target, "b")
    def test_05_native_router(self): self.assertEqual(NativeRouterAuthority.execute([1], [9]), (1,))
    def test_06_prefetch_plan(self): self.assertEqual(RouterPreservingPrefetch.plan([1], [1, 9], [1]), (1,))
    def test_07_page_cache_state(self): self.assertEqual(PageCacheStateGate.classify(None), "CALIBRATION_REQUIRED")
    def test_08_versions(self): self.assertTrue(VersionRangeGate.admit("5.1", "5", "6")); self.assertFalse(VersionRangeGate.admit(None, "5", "6"))
    def test_09_snapshot_ring(self):
        r = SnapshotRing(2); [r.append(i, i) for i in range(4)]; self.assertEqual(len(r), 2)
    def test_10_hot_cold(self):
        c = HotColdCache({"a": 1}, 1); c.get("a"); c.get("a"); self.assertEqual((c.hits,c.misses),(1,1))
    def test_11_storage_placement(self):
        t = [StorageTier("s", 100, 10, 1), StorageTier("f", 100, 20, 2)]; self.assertEqual(StorageTierPlacement.choose(t, 10, 1).name, "f")
    def test_12_lease(self):
        l = StateHandleLease("r", "o", 1, 10); self.assertTrue(l.valid("o", 1, 9)); l.close(); self.assertFalse(l.valid("o", 1, 9))
    def test_13_budget(self): self.assertEqual(WindowAwareBudget.bytes(100, 0.5, 1000), 50)
    def test_14_waste_guard(self): self.assertTrue(PrefetchWasteGuard.admit(20,10)); self.assertFalse(PrefetchWasteGuard.admit(10,20))
    def test_15_energy(self):
        t = StorageTier("x", 10**9, 1e9, 2)
        self.assertTrue(TierEnergyAdmission.admit(t, 10**8, 0.3)); self.assertFalse(TierEnergyAdmission.admit(t, 10**8, 0.1))
        self.assertFalse(TierEnergyAdmission.admit(t, 10**8, True))
        exact = StorageTier("exact", 10**9, 1e9, 1.0); spent = 0.0
        for expected in (0.05, 0.10, 0.15):
            ok, spent, plan = TierEnergyAdmission.admit_cumulative(exact, 50_000_000, spent, 0.15)
            self.assertTrue(ok); self.assertEqual(spent, expected); self.assertEqual(plan, 0.05)
        ok, unchanged, _ = TierEnergyAdmission.admit_cumulative(exact, 50_000_000, spent, 0.15)
        self.assertFalse(ok); self.assertEqual(unchanged, 0.15)
    def test_16_accounting(self): self.assertEqual(UsefulByteAccounting(1,2,3).total,6)
    def test_17_lru(self):
        c=ExpertResidencyLRU(2); self.assertFalse(c.access(1)); self.assertTrue(c.access(1)); c.access(2); c.access(3); self.assertFalse(c.resident(1))
    def test_18_ple(self):
        s=PLEExpertSeparation(1,1); s.access("expert",1); s.access("ple",1); self.assertTrue(s.experts.resident(1)); self.assertIn(1,s.ple)
    def test_19_identity(self):
        e=IdentityEnvelope("m","r","s","h","g"); self.assertTrue(P0IdentityGate.admit(e,e)); self.assertFalse(P0IdentityGate.admit(e,None))
    def test_20_envelope(self):
        a=PerformanceEnvelope("g","warm",60,2000); b=PerformanceEnvelope("g","warm",61,2020); c=PerformanceEnvelope("g","cold",61,2020); self.assertTrue(MatchedEnvelopeGate.comparable(a,b)); self.assertFalse(MatchedEnvelopeGate.comparable(a,c))
    def test_21_composition(self):
        a=ComponentContract("a","1",frozenset({"x"}),frozenset(),frozenset({"r","w"})); b=ComponentContract("b","1",frozenset(),frozenset({"x"}),frozenset({"r"})); o=CompositionMembrane.compose(a,b,{"x"}); self.assertEqual((o["interface"],o["authority"]),(("x",),("r",)))
    def test_22_collision(self):
        c=CollisionBucket(); c.put((1,2,3),"a",1); c.put((1,2,3),"b",2); self.assertEqual(c.identities((1,2,3)),("a","b"))
    def test_23_hard_gate_pin(self):
        self.assertFalse(HardGatePin.admit({"hard":False,"identity":True},999)); self.assertTrue(HardGatePin.admit({"hard":True,"identity":True},0))
    def test_24_capability(self):
        m=CapabilityManifest(frozenset({"read"})); self.assertTrue(m.allows(["read"])); self.assertFalse(m.allows(["write"]))
    def test_25_retrieval_receipt(self):
        a=RetrievalReceipt.build("q",["a"],"g"); b=RetrievalReceipt.build("q",["a"],"g"); self.assertEqual(a.receipt_digest,b.receipt_digest); self.assertTrue(a.valid_for("q",["a"],"g"))
    def test_26_currentness(self):
        c=CurrentnessInvalidator(); c.bind("n1",["d1"]); c.bind("n2",["d2"]); self.assertEqual(c.invalidate(["d1"]),{"n1"}); self.assertTrue(c.current("n2"))
    def test_27_hdc(self):
        h=HDCSemanticKey(); x=h.encode("expert cache"); self.assertEqual(h.distance(x,x),0)
    def test_28_security_campaign(self):
        r=security_campaign(1000); self.assertEqual(r["before_false_admits"],r["after_blocked"])

    def test_29_malformed_versions_fail_closed(self):
        for v in ("5x","5.1-untrusted","5.1.2.3"," 5.1","5.1 ",""):
            self.assertFalse(VersionRangeGate.admit(v,"5","6"),v)

    def test_30_missing_unknown_or_nonbool_hard_gates_fail_closed(self):
        self.assertFalse(HardGatePin.admit({})); self.assertFalse(HardGatePin.admit({"hard":True})); self.assertFalse(HardGatePin.admit({"hard":True,"identity":True,"extra":True})); self.assertFalse(HardGatePin.admit({"hard":1,"identity":True}))

    def test_31_export_receipt_tamper_rejected(self):
        payload={"x":1}; r=ExportReceipt.build(payload,["a"],"g"); self.assertFalse(replace(r,receipt_digest="0"*64).reusable(["a"],"g",payload=payload)); self.assertFalse(replace(r,output_digest="f"*64).reusable(["a"],"g",payload=payload)); self.assertFalse(r.reusable(["a"],"g",payload=payload,output_digest="e"*64))

    def test_32_retrieval_receipt_tamper_and_context_rejected(self):
        r=RetrievalReceipt.build("q",["a"],"g"); self.assertFalse(replace(r,receipt_digest="0"*64).valid_for("q",["a"],"g")); self.assertFalse(r.valid_for("other",["a"],"g")); self.assertFalse(r.valid_for("q",["b"],"g"))

    def test_33_currentness_rebind_removes_old_reverse_edge(self):
        c=CurrentnessInvalidator(); c.bind("n",["d1"]); c.bind("n",["d2"]); self.assertEqual(c.invalidate(["d1"]),set()); self.assertEqual(c.invalidate(["d2"]),{"n"})

    def test_34_reproof_completion_requires_exact_current_dependencies(self):
        c=CurrentnessInvalidator(); c.bind("n",["d2"]); c.invalidate(["d2"]); self.assertFalse(c.current("n")); self.assertFalse(c.complete_reproof("n",["d1"])); self.assertFalse(c.current("n")); self.assertTrue(c.complete_reproof("n",["d2"])); self.assertTrue(c.current("n")); self.assertFalse(c.current("unknown"))

    def test_35_hybrid_index_exact_lexical_backstop(self):
        idx=HybridIndexBridge(10)
        for i in range(200): idx.add(f"R{i}",f"family_{i%10} mechanism_{i%7} record_{i}",(i%27,(i*2)%27,(i*3)%27))
        q="family_3 mechanism_4"; expected={f"R{i}" for i in range(200) if i%10==3 and i%7==4}; got={x[0] for x in idx.candidates(q,0)}; self.assertTrue(expected<=got)

    def test_36_prefetch_time_is_counted_consistently(self):
        size=1024; tier=StorageTier("ssd",10**9,1024.0,1.0); r=FrontierOffload(size,8,tier,1.0,100.0).run([[1]],[[1]]); self.assertGreater(r["seconds"],0); self.assertTrue(math.isclose(r["seconds"],r["bytes"]/tier.bandwidth,rel_tol=0,abs_tol=1e-12))

    def test_37_non_finite_canonical_values_fail_closed(self):
        for value in (float("nan"),float("inf"),float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError): digest({"value":value})
                with self.assertRaises(ValueError): ExportReceipt.build({"value":value},["a"],"g")
                ring=SnapshotRing(1)
                with self.assertRaises(ValueError): ring.append(0,{"value":value})

    def test_38_forged_self_consistent_export_receipt_requires_source_truth(self):
        fake_output="f"*64; dep_root=digest(sorted(["a"])); forged=ExportReceipt(fake_output,dep_root,"g",digest([fake_output,dep_root,"g"])); self.assertTrue(forged.verify()); self.assertFalse(forged.reusable(["a"],"g")); self.assertFalse(forged.reusable(["a"],"g",payload={"x":1}))

    def test_39_snapshot_ring_restores_frozen_state(self):
        state={"x":[1,2]}; ring=SnapshotRing(2); ring.append(7,state); state["x"].append(3); self.assertEqual(ring.restore(7),{"x":[1,2]})

    def test_40_prefetch_respects_energy_budget(self):
        size=1024; tier=StorageTier("ssd",10**9,1024.0,1.0); blocked=FrontierOffload(size,8,tier,1.0,0.0).run([[1]],[[1]]); allowed=FrontierOffload(size,8,tier,1.0,10.0).run([[1]],[[1]]); self.assertEqual(blocked["prefetch_transfers"],0); self.assertGreater(allowed["prefetch_transfers"],0)

    def test_41_security_campaign_independent_oracle_detects_fail_open(self):
        hard_saved=HardFalseSecurityGate.admit; ident_saved=P0IdentityGate.admit
        try:
            HardFalseSecurityGate.admit=staticmethod(lambda **kwargs: True); P0IdentityGate.admit=staticmethod(lambda expected,observed: True); result=security_campaign(1000); self.assertGreater(result["after_false_admits"],0); self.assertLess(result["false_admission_reduction"],1.0)
        finally:
            HardFalseSecurityGate.admit=hard_saved; P0IdentityGate.admit=ident_saved

    def test_42_security_campaign_baseline_has_no_false_admits_or_valid_rejections(self):
        result=security_campaign(1000); self.assertEqual(result["after_false_admits"],0); self.assertEqual(result["valid_rejected"],0)

    def test_43_prefetch_energy_budget_is_cumulative(self):
        tier=StorageTier("ssd",10**9,10**9,1.0)
        result=FrontierOffload(100_000_000,8,tier,1.0,0.15).run([[1],[2]],[[1],[2]])
        self.assertEqual(result["prefetch_transfers"],1)
        self.assertEqual(result["speculative_energy_j"],0.1)
        self.assertEqual(result["speculative_energy_remaining_j"],0.05)
        self.assertLessEqual(result["speculative_energy_j"],result["speculative_energy_budget_j"])
        exact=FrontierOffload(50_000_000,8,tier,1.0,0.15).run([[1],[2],[3]],[[1],[2],[3]])
        self.assertEqual(exact["prefetch_transfers"],3)
        self.assertEqual(exact["speculative_energy_j"],exact["speculative_energy_budget_j"])
        self.assertEqual(exact["speculative_energy_remaining_j"],0.0)


if __name__ == "__main__": unittest.main()
