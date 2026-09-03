import random
import unittest
from dataclasses import asdict

from constitutional_invariants import *


class ConstitutionalTests(unittest.TestCase):
    def checker(self): return ConstitutionalInvariantChecker()

    def test_empty_snapshot_is_lawful(self):
        r=self.checker().check(ConstitutionalSnapshot())
        self.assertTrue(r.lawful); self.assertEqual(r.checked_laws, LAWS)
        self.assertFalse(r.effect_authority); self.assertFalse(r.gate10)

    def test_cross_domain_evidence_payment_fails(self):
        s=ConstitutionalSnapshot(evidence_payments=(EvidencePayment("OWNER_AUTHORITY","CORRECTNESS","x"),))
        self.assertIn(LAWS[0], {v.law_id for v in self.checker().check(s).violations})

    def test_same_domain_evidence_payment_passes(self):
        s=ConstitutionalSnapshot(evidence_payments=(EvidencePayment("CORRECTNESS","CORRECTNESS","x"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_projection_cannot_mint_owner_authority(self):
        self.assertFalse(self.checker().check(ConstitutionalSnapshot(projections=(ProjectionClaim(False,False,True,False),))).lawful)

    def test_projection_cannot_mint_effect_authority(self):
        self.assertFalse(self.checker().check(ConstitutionalSnapshot(projections=(ProjectionClaim(False,False,False,True),))).lawful)

    def test_provider_only_movement_cannot_mint_semantic_movement(self):
        s=ConstitutionalSnapshot(source_transitions=(SourceTransition("g1","g2","r1","r1",True),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_semantic_root_change_may_claim_semantic_movement(self):
        s=ConstitutionalSnapshot(source_transitions=(SourceTransition("g1","g2","r1","r2",True),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_supersession_cycle_fails(self):
        s=ConstitutionalSnapshot(supersession_edges=(SupersessionEdge("a","b"),SupersessionEdge("b","a")))
        self.assertFalse(self.checker().check(s).lawful)

    def test_supersession_dag_passes(self):
        s=ConstitutionalSnapshot(supersession_edges=(SupersessionEdge("a","b"),SupersessionEdge("b","c")))
        self.assertTrue(self.checker().check(s).lawful)

    def test_cold_work_cannot_self_wake(self):
        s=ConstitutionalSnapshot(wake_claims=(WakeClaim("COLD_ARCHIVE",True,("semantic_root",),()),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_matching_invalidator_may_wake_cold_work(self):
        s=ConstitutionalSnapshot(wake_claims=(WakeClaim("COLD_ARCHIVE",True,("semantic_root",),("semantic_root",)),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_cross_city_cannot_mint_owner_authority(self):
        s=ConstitutionalSnapshot(cross_jurisdiction_claims=(CrossJurisdictionClaim(False,False,True,False,True),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_cross_city_authority_requires_destination_revalidation(self):
        s=ConstitutionalSnapshot(cross_jurisdiction_claims=(CrossJurisdictionClaim(True,False,True,False,False),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_gate10_crossing_requires_human(self):
        s=ConstitutionalSnapshot(gate10_claims=(Gate10Claim(True,"AGENT"),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_human_gate10_crossing_is_structurally_allowed(self):
        s=ConstitutionalSnapshot(gate10_claims=(Gate10Claim(True,"HUMAN"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_unknown_dependencies_cannot_use_selective_revalidation(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",True,False,False,"WIDEN_LOCAL_REVALIDATION"),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_incomplete_local_dependencies_widen_without_owner_authority(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("PARTIAL",False,False,False,"WIDEN_LOCAL_REVALIDATION"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_incomplete_owner_effect_without_authority_holds(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",False,True,False,"HOLD_AUTHORITY"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_incomplete_owner_effect_without_hold_fails(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",False,True,False,"FULL_OWNER_REVALIDATION"),))
        self.assertFalse(self.checker().check(s).lawful)

    def test_complete_dependencies_may_selectively_revalidate(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("COMPLETE",True,False,False,"SELECTIVE"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_pr798_provider_rebind_fixture(self):
        s=ConstitutionalSnapshot(source_transitions=(SourceTransition("provider:g1","provider:g2","sem:r1","sem:r1",False),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_pr800_cold_lifecycle_fixture(self):
        s=ConstitutionalSnapshot(wake_claims=(WakeClaim("RETIRED_NO_REOPEN_WITHOUT_INVALIDATOR",False,("owner","semantic_root"),()),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_pr802_portable_evidence_fixture(self):
        s=ConstitutionalSnapshot(cross_jurisdiction_claims=(CrossJurisdictionClaim(False,False,False,False,True),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_pr311_local_wider_validation_does_not_need_owner_authority(self):
        s=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",False,False,False,"FULL_LOCAL_REVALIDATION"),))
        self.assertTrue(self.checker().check(s).lawful)

    def test_assert_lawful_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"CONSTITUTIONAL_VIOLATION"):
            self.checker().assert_lawful(ConstitutionalSnapshot(gate10_claims=(Gate10Claim(True,"MODEL"),)))

    def test_normalize_mapping_roundtrip(self):
        s=ConstitutionalSnapshot(evidence_payments=(EvidencePayment("CORRECTNESS","CORRECTNESS","d"),),gate10_claims=(Gate10Claim(False,None),))
        n=normalize_mapping({k:v for k,v in asdict(s).items()})
        self.assertTrue(self.checker().check(n).lawful)

    def test_1000_hyperscale_constitutional_cells(self):
        projects=["JSPACE","GLM","BUGHOUND","MEMORY_CITY","COUNCIL","ACCOUNTING","WORLDWIKI","NEWS","BRIDGE","BENCHMARK"]
        mutations=["EVIDENCE","PROJECTION","PROVIDER","CYCLE","WAKE","BRIDGE","GATE10","DEPENDENCY","LEGAL","CONTROL"]
        contexts=[f"CTX{i}" for i in range(10)]
        cells=0
        for project in projects:
            for mutation in mutations:
                for ctx in contexts:
                    cells+=1
                    if mutation == "EVIDENCE": snap=ConstitutionalSnapshot(evidence_payments=(EvidencePayment("CORRECTNESS","TIMING",f"{project}:{ctx}"),))
                    elif mutation == "PROJECTION": snap=ConstitutionalSnapshot(projections=(ProjectionClaim(False,False,True,False),))
                    elif mutation == "PROVIDER": snap=ConstitutionalSnapshot(source_transitions=(SourceTransition("g1","g2","r","r",True),))
                    elif mutation == "CYCLE": snap=ConstitutionalSnapshot(supersession_edges=(SupersessionEdge("a","b"),SupersessionEdge("b","a")))
                    elif mutation == "WAKE": snap=ConstitutionalSnapshot(wake_claims=(WakeClaim("COLD_ARCHIVE",True,("x",),("y",)),))
                    elif mutation == "BRIDGE": snap=ConstitutionalSnapshot(cross_jurisdiction_claims=(CrossJurisdictionClaim(False,False,True,False,True),))
                    elif mutation == "GATE10": snap=ConstitutionalSnapshot(gate10_claims=(Gate10Claim(True,"AGENT"),))
                    elif mutation == "DEPENDENCY": snap=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",True,False,False,"SELECTIVE"),))
                    else: snap=ConstitutionalSnapshot()
                    r=self.checker().check(snap)
                    self.assertEqual(r.lawful, mutation in {"LEGAL","CONTROL"})
        self.assertEqual(cells,1000)

    def test_200000_random_mutations_match_reference_policy(self):
        rng=random.Random(13); c=self.checker()
        for i in range(200000):
            law=rng.randrange(8); violate=bool(rng.randrange(2))
            if law==0: snap=ConstitutionalSnapshot(evidence_payments=(EvidencePayment("CORRECTNESS","TIMING" if violate else "CORRECTNESS",str(i)),))
            elif law==1: snap=ConstitutionalSnapshot(projections=(ProjectionClaim(False,False,violate,False),))
            elif law==2: snap=ConstitutionalSnapshot(source_transitions=(SourceTransition("g1","g2","r1","r1" if violate else "r2",True),))
            elif law==3: snap=ConstitutionalSnapshot(supersession_edges=(SupersessionEdge("a","b"),SupersessionEdge("b","a" if violate else "c")))
            elif law==4: snap=ConstitutionalSnapshot(wake_claims=(WakeClaim("COLD_ARCHIVE",True,("x",),(() if violate else ("x",))),))
            elif law==5: snap=ConstitutionalSnapshot(cross_jurisdiction_claims=(CrossJurisdictionClaim(False,False,violate,False,True),))
            elif law==6: snap=ConstitutionalSnapshot(gate10_claims=(Gate10Claim(True,"AGENT" if violate else "HUMAN"),))
            else: snap=ConstitutionalSnapshot(dependency_claims=(DependencyClaim("UNKNOWN",violate,False,False,"WIDEN_LOCAL_REVALIDATION"),))
            self.assertEqual(c.check(snap).lawful, not violate)


if __name__ == "__main__": unittest.main()
