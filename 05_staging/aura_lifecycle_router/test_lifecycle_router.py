import random, unittest
from dataclasses import replace
from lifecycle_router import *

class T(unittest.TestCase):
    def setUp(self): self.a=portfolio_fixture()
    def test_portfolio_projects(self): self.assertGreaterEqual(len({x.project for x in self.a.provenance()}),6)
    def test_active_excludes_hold(self): self.assertNotIn("BUGHOUND-CASH-FIDELITY",{x.artifact_id for x in self.a.active()})
    def test_searchability_not_hotness(self): self.assertIn("BUGHOUND-CASH-FIDELITY",{x.artifact_id for x in self.a.provenance()}); self.assertNotIn("BUGHOUND-CASH-FIDELITY",{x.artifact_id for x in self.a.active()})
    def test_exact_wake(self): self.assertEqual(self.a.wake("BUGHOUND-CASH-FIDELITY",kind="AUTHORIZED_REAL_CORPUS",ref="BUGHOUND")["status"],"WAKE_CANDIDATE")
    def test_wrong_wake_noop(self): self.assertEqual(self.a.wake("BUGHOUND-CASH-FIDELITY",kind="PR_HEAD",ref="798")["status"],"NO_WAKE")
    def test_retired_requires_invalidator(self):
        self.a.transition("BUGHOUND-CASH-FIDELITY",Lifecycle.RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR)
        with self.assertRaisesRegex(ValueError,"REOPEN_INVALIDATOR_REQUIRED"): self.a.transition("BUGHOUND-CASH-FIDELITY",Lifecycle.CURRENT_HOT)
        self.assertEqual(self.a.transition("BUGHOUND-CASH-FIDELITY",Lifecycle.CURRENT_HOT,invalidator_ref="AUTHORIZED_REAL_CORPUS").lifecycle,Lifecycle.CURRENT_HOT)
    def test_supersession_retains_old(self):
        old=self.a.get("MEMORY-CITY-PROJECTION")
        new=ArtifactState("MEMORY-CITY-PROJECTION-V2","MemoryCity","r2","drive:new","owner:new",Lifecycle.CURRENT_HOT,old.frame_cut,old.jurisdiction,(WakeCondition("SOURCE_DELTA","MEMORY_CITY"),),supersedes=(old.artifact_id,))
        old2,_=self.a.supersede(old.artifact_id,new); self.assertEqual(old2.lifecycle,Lifecycle.SUPERSEDED_BUT_PROVENANCE_RETAINED); self.assertIn(old.artifact_id,{x.artifact_id for x in self.a.provenance()})
    def test_cross_project_supersession_rejected(self):
        old=self.a.get("PR311-G1"); new=ArtifactState("X","Other","x","s","o",Lifecycle.CURRENT_HOT,old.frame_cut,old.jurisdiction,(WakeCondition("X","Y"),),supersedes=(old.artifact_id,))
        with self.assertRaisesRegex(ValueError,"CROSS_PROJECT_SUPERSESSION"): self.a.supersede(old.artifact_id,new)
    def test_k27_is_routing_only(self): self.assertFalse(self.a.manifest()["k27_authority"])
    def test_invalid_k27_rejected(self):
        with self.assertRaisesRegex(ValueError,"INVALID_K27"):
            self.a.register(ArtifactState("bad","p","r","s","o",Lifecycle.CURRENT_HOT,"f","j",(),k27=(27,0,0)))
    def test_firewall_complete(self):
        c=ClaimContract("speedup",("SOURCE_SECURITY","PHYSICAL_OBSERVATION","CORRECTNESS"),"PR311","d951")
        leaves=[EvidenceLeaf("op1","SOURCE_SECURITY","s","g","r",True,"p"),EvidenceLeaf("op1","PHYSICAL_OBSERVATION","s","g","r",True,"p"),EvidenceLeaf("op1","CORRECTNESS","s","g","r",True,"p")]
        self.assertEqual(EvidenceDomainFirewall().admit(c,leaves)["status"],"CLAIM_EVIDENCE_COMPLETE")
    def test_firewall_no_cross_domain_payment(self):
        c=ClaimContract("speedup",("SOURCE_SECURITY","PHYSICAL_OBSERVATION"),"PR311","d951")
        leaves=[EvidenceLeaf("op1","SOURCE_SECURITY","s","g","r",True,"p"),EvidenceLeaf("op1","SOURCE_SECURITY","s2","g","r2",True,"p")]
        d=EvidenceDomainFirewall().admit(c,leaves); self.assertEqual(d["status"],"HOLD_EVIDENCE_DOMAIN"); self.assertEqual(d["missing_domains"],("PHYSICAL_OBSERVATION",)); self.assertFalse(d["cross_domain_substitution"])
    def test_stale_leaf_cannot_pay_domain(self):
        c=ClaimContract("x",("CORRECTNESS",),"t","g"); d=EvidenceDomainFirewall().admit(c,[EvidenceLeaf("o","CORRECTNESS","s","g","r",False,"p")]); self.assertEqual(d["status"],"HOLD_EVIDENCE_DOMAIN")
    def test_multiplex_operation_keeps_domains_typed(self):
        c=ClaimContract("x",("CORRECTNESS","PHYSICAL_OBSERVATION"),"t","g")
        leaves=[EvidenceLeaf("ONE-P1","CORRECTNESS","s","g","r1",True,"p"),EvidenceLeaf("ONE-P1","PHYSICAL_OBSERVATION","s","g","r2",True,"p")]
        d=EvidenceDomainFirewall().admit(c,leaves); self.assertEqual(d["operation_ids"],("ONE-P1",)); self.assertEqual(set(d["satisfied_domains"]),{"CORRECTNESS","PHYSICAL_OBSERVATION"})
    def test_router_current_same_jurisdiction(self):
        t=TransitionIntent("route","PR798-SOURCECURSOR3D","ResearchOwnerP0","MAIN:5576537","AURAOS","CURRENT","OWNER_INPUT")
        d=TransitionRouter(self.a).compile(t); self.assertEqual(d["status"],"ROUTED_DERIVED_NO_AUTHORITY_PROMOTION"); self.assertEqual(d["new_owner_count"],0)
    def test_router_hold_source_not_hot(self):
        t=TransitionIntent("route","BUGHOUND-CASH-FIDELITY","AuraOS796","BUGHOUND:20260903","BUGHOUND","CURRENT","INPUT")
        self.assertEqual(TransitionRouter(self.a).compile(t)["status"],"HOLD_SOURCE_NOT_HOT")
    def test_router_frame_cut(self):
        t=TransitionIntent("route","PR798-SOURCECURSOR3D","X","WRONG","AURAOS","CURRENT","X")
        self.assertEqual(TransitionRouter(self.a).compile(t)["status"],"HOLD_INCOHERENT_CUT")
    def test_router_jurisdiction_bridge(self):
        t=TransitionIntent("route","PR798-SOURCECURSOR3D","MemoryCity","MAIN:5576537","MEMORY_CITY","CURRENT","X")
        self.assertEqual(TransitionRouter(self.a).compile(t)["status"],"HOLD_JURISDICTION_BRIDGE_REQUIRED")
        t2=replace(t,bridge_ref="TREATY:MC-AURA")
        self.assertEqual(TransitionRouter(self.a).compile(t2)["status"],"ROUTED_DERIVED_NO_AUTHORITY_PROMOTION")
    def test_router_effect_never_promoted(self):
        t=TransitionIntent("route","PR798-SOURCECURSOR3D","X","MAIN:5576537","AURAOS","CURRENT","X",effect_claim="OWNER_EFFECT")
        d=TransitionRouter(self.a).compile(t); self.assertEqual(d["status"],"HOLD_EFFECT_OWNER_REQUIRED"); self.assertFalse(d["effect_authority"])
    def test_manifest_order_stable(self): self.assertEqual(self.a.manifest()["manifest_root"],self.a.manifest()["manifest_root"])
    def test_hyperscale1000_hot_frontier(self):
        a=LifecycleAtlas()
        for i in range(1000):
            life=Lifecycle.CURRENT_HOT if i<25 else Lifecycle.COLD_ARCHIVE
            a.register(ArtifactState(f"A{i}","P",f"R{i}",f"S{i}","O",life,"F","J",(WakeCondition("DELTA",f"A{i}"),)))
        self.assertEqual(len(a.active()),25); self.assertEqual(len(a.provenance()),1000)
    def test_100000_domain_laundering_fails_closed(self):
        rng=random.Random(20260903); fw=EvidenceDomainFirewall(); domains=sorted(EVIDENCE_DOMAINS)
        for i in range(100000):
            req=rng.choice(domains); supplied=rng.choice(domains); current=rng.random()>0.1
            c=ClaimContract(str(i),(req,),"T","G"); leaf=EvidenceLeaf("op",supplied,"s","g","r",current,"p"); d=fw.admit(c,[leaf])
            if d["status"]=="CLAIM_EVIDENCE_COMPLETE": self.assertEqual(req,supplied); self.assertTrue(current)
            self.assertFalse(d["effect_authority"])
    def test_no_artifact_mints_effect(self): self.assertTrue(all(not x.effect_authority for x in self.a.provenance()))

if __name__=="__main__": unittest.main()
