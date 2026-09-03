import random
import tempfile
import threading
import time
import unittest
from pathlib import Path
from reference_kernel import *

class KernelTests(unittest.TestCase):
    def setUp(self): self.tmp=tempfile.TemporaryDirectory(); self.store=JSpaceStore(Path(self.tmp.name)/"jspace.db")
    def tearDown(self): self.tmp.cleanup()
    def event(self,event_id="e1",event_type="CHECKIN",generation="g1",payload=None,source="src"):
        return JSpaceEvent(event_id,event_type,1,"v1",source,generation,"epoch1",source,payload or {},time.time_ns())

    def test_jid_monotonic(self): self.assertEqual([self.store.allocate_jid()[0] for _ in range(3)],[1,2,3])
    def test_jid_concurrent_unique(self):
        out=[]; lock=threading.Lock()
        def allocate():
            value=self.store.allocate_jid()[0]
            with lock: out.append(value)
        threads=[threading.Thread(target=allocate) for _ in range(30)]; [t.start() for t in threads]; [t.join() for t in threads]
        self.assertEqual(sorted(out),list(range(1,31)))
    def test_event_duplicate_idempotent(self): self.assertEqual(self.store.append(self.event())[0],"APPENDED"); self.assertEqual(self.store.append(self.event())[0],"DUPLICATE_COLLAPSED")
    def test_conflicting_replay_fails(self):
        self.store.append(self.event())
        with self.assertRaisesRegex(ValueError,"CONFLICTING_EVENT_REPLAY"): self.store.append(self.event(payload={"x":1}))
    def test_authority_widening_fails(self):
        event=self.event(); object.__setattr__(event,"effect_authority",True)
        with self.assertRaisesRegex(ValueError,"AUTHORITY_WIDENING"): self.store.append(event)
    def test_lower_sequence_does_not_regress(self):
        self.store.append(self.event("new","WORK_STATE","g2",{"status":"DONE","source_sequence":2}))
        self.store.append(self.event("old","WORK_STATE","g1",{"status":"WORKING","source_sequence":1}))
        self.assertEqual(self.store.project()[1]["status"],"DONE")
    def test_equal_sequence_exact_semantic_replay_noop(self):
        p={"status":"DONE","source_sequence":2}
        self.store.append(self.event("a","WORK_STATE","g2",p)); self.store.append(self.event("b","WORK_STATE","g2",p))
        self.assertEqual(self.store.project()[1]["status"],"DONE")
    def test_equal_sequence_same_generation_semantic_fork_fails(self):
        self.store.append(self.event("a","WORK_STATE","g2",{"status":"DONE","source_sequence":2}))
        self.store.append(self.event("b","WORK_STATE","g2",{"status":"WORKING","source_sequence":2}))
        with self.assertRaisesRegex(ValueError,"SOURCE_SEQUENCE_CONFLICT"): self.store.project()
    def test_equal_sequence_conflicting_generation_and_root_fails_closed(self):
        self.store.append(self.event("a","WORK_STATE","g2",{"status":"DONE","source_sequence":2}))
        self.store.append(self.event("b","WORK_STATE","g2b",{"status":"WORKING","source_sequence":2}))
        with self.assertRaisesRegex(ValueError,"SOURCE_SEQUENCE_CONFLICT"): self.store.project()
    def test_equal_sequence_generation_rebind_same_root_no_semantic_wake(self):
        self.store.append(self.event("a","WORK_STATE","g1",{"status":"DONE","source_sequence":2,"semantic_root":"R"}))
        self.store.append(self.event("b","WORK_STATE","g2",{"status":"IGNORED","source_sequence":2,"semantic_root":"R"}))
        state=self.store.project()[1]
        self.assertEqual(state["status"],"DONE"); self.assertEqual(state["sources"]["src"],"g2")
        self.assertEqual(state["source_cursors"]["src|src"]["semantic_root"],"R")
    def test_higher_sequence_same_root_cursor_advance_no_semantic_wake(self):
        self.store.append(self.event("a","WORK_STATE","g1",{"status":"DONE","source_sequence":1,"semantic_root":"R"}))
        self.store.append(self.event("b","WORK_STATE","g2",{"status":"IGNORED","source_sequence":2,"semantic_root":"R"}))
        state=self.store.project()[1]
        self.assertEqual(state["status"],"DONE"); self.assertEqual(state["sources"]["src"],"g2"); self.assertEqual(state["source_sequences"]["src|src"],2)
    def test_higher_sequence_new_root_semantic_advance(self):
        self.store.append(self.event("a","WORK_STATE","g1",{"status":"WORKING","source_sequence":1,"semantic_root":"R1"}))
        self.store.append(self.event("b","WORK_STATE","g2",{"status":"DONE","source_sequence":2,"semantic_root":"R2"}))
        self.assertEqual(self.store.project()[1]["status"],"DONE")
    def test_cursor_transition_table(self):
        p=SourceCursor3D(2,"g1","R1")
        cases=[(SourceCursor3D(1,"g0","R0"),"HISTORICAL_RECEIPT_ONLY"),(SourceCursor3D(2,"g1","R1"),"EXACT_REPLAY_NOOP"),(SourceCursor3D(2,"g2","R1"),"CURRENTNESS_REBIND_ONLY"),(SourceCursor3D(2,"g1","R2"),"SOURCE_POSITION_SEMANTIC_CONFLICT"),(SourceCursor3D(3,"g1","R1"),"CURSOR_ADVANCE_NO_SEMANTIC_WAKE"),(SourceCursor3D(3,"g2","R2"),"SEMANTIC_ADVANCE")]
        for observed,expected in cases: self.assertEqual(classify_source_cursor_transition(p,observed),expected)
    def test_owner_ref_requires_repository_qualification(self):
        with self.assertRaises(ValueError): OwnerRef("github","AuraOS","issue",796).validate()
    def test_owner_ref_issue_pr_are_distinct(self): self.assertNotEqual(OwnerRef("github","dallascourchene-commits/AuraOS","issue",796).canonical,OwnerRef("github","dallascourchene-commits/AuraOS","pull",796).canonical)
    def test_same_ordinal_other_repo_is_distinct(self): self.assertNotEqual(OwnerRef("github","dallascourchene-commits/AuraOS","issue",796).canonical,OwnerRef("github","UnknownAlienHuman/eliot-memory-os","issue",796).canonical)
    def test_lease_exact_reuse(self):
        lease=EvidenceLease("A","rev1","root1","drive"); decision=EvidenceLeaseGate(self.store,{"A":lease}).compare({"A":lease},{"A","B"})
        self.assertEqual(decision.disposition,"CURRENT_PLANNING_CANDIDATE"); self.assertFalse(decision.effect_authority)
    def test_lease_revision_drift_selective(self):
        self.store.add_dep("A","B"); self.store.add_dep("X","Y"); expected=EvidenceLease("A","rev1","root1","drive"); observed=EvidenceLease("A","rev2","root1","drive")
        d=EvidenceLeaseGate(self.store,{"A":expected}).compare({"A":observed},{"A","B","X","Y"}); self.assertEqual(set(d.affected),{"A","B"}); self.assertEqual(set(d.reusable),{"X","Y"})
    def test_lease_semantic_root_drift_selective(self):
        self.store.add_dep("A","B"); expected=EvidenceLease("A","rev1","root1","drive"); observed=EvidenceLease("A","rev1","root2","drive")
        d=EvidenceLeaseGate(self.store,{"A":expected}).compare({"A":observed},{"A","B","C"}); self.assertEqual(set(d.affected),{"A","B"}); self.assertEqual(set(d.reusable),{"C"})
    def test_missing_lease_holds(self): self.assertEqual(EvidenceLeaseGate(self.store,{"A":EvidenceLease("A","rev1","root1","drive")}).compare({}, {"A"}).disposition,"HOLD_REVALIDATE_SOURCE")
    def test_reconcile_older_sequence_is_noop(self):
        self.store.append(self.event("initial","RECONCILIATION","g2",{"source_sequence":2,"semantic_root":"R"}))
        r=ReconcileEngine(self.store,jid=1,visit_id="v1",owner_epoch="epoch1").reconcile([SourceState("src","g1",True,1,"OLD")],all_nodes={"src"},capability_nodes={"src"})
        self.assertEqual(r.disposition,"NOOP_SOURCE_SNAPSHOT"); self.assertEqual(r.appended_events,())
    def test_reconcile_equal_sequence_semantic_conflict_fails(self):
        self.store.append(self.event("initial","RECONCILIATION","g2",{"source_sequence":2,"semantic_root":"R1"}))
        with self.assertRaisesRegex(ValueError,"SOURCE_SEQUENCE_CONFLICT"):
            ReconcileEngine(self.store,jid=1,visit_id="v1",owner_epoch="epoch1").reconcile([SourceState("src","g2",True,2,"R2")],all_nodes={"src"},capability_nodes={"src"})
    def test_reconcile_equal_sequence_generation_rebind_no_wake(self):
        self.store.add_dep("src","consumer"); self.store.append(self.event("initial","RECONCILIATION","g1",{"source_sequence":2,"semantic_root":"R"}))
        r=ReconcileEngine(self.store,jid=1,visit_id="v1",owner_epoch="epoch1").reconcile([SourceState("src","g2",True,2,"R")],all_nodes={"src","consumer"},capability_nodes={"src","consumer"})
        self.assertEqual(r.disposition,"RECONCILED_CURRENTNESS_ONLY"); self.assertEqual(r.changed_sources,()); self.assertEqual(r.rebound_sources,("src",)); self.assertEqual(r.affected,())
        self.assertEqual(self.store.project()[1]["sources"]["src"],"g2")
    def test_reconcile_higher_sequence_same_root_cursor_only(self):
        self.store.add_dep("src","consumer"); self.store.append(self.event("initial","RECONCILIATION","g1",{"source_sequence":1,"semantic_root":"R"}))
        r=ReconcileEngine(self.store,jid=1,visit_id="v1",owner_epoch="epoch1").reconcile([SourceState("src","g2",True,2,"R")],all_nodes={"src","consumer"},capability_nodes={"src","consumer"})
        self.assertEqual(r.changed_sources,()); self.assertEqual(r.cursor_advanced_sources,("src",)); self.assertEqual(r.affected,())
    def test_reconcile_higher_sequence_new_root_selective_wake(self):
        self.store.add_dep("src","consumer"); self.store.add_dep("other","other_consumer"); self.store.append(self.event("initial","RECONCILIATION","g1",{"source_sequence":1,"semantic_root":"R1"}))
        r=ReconcileEngine(self.store,jid=1,visit_id="v1",owner_epoch="epoch1").reconcile([SourceState("src","g2",True,2,"R2")],all_nodes={"src","consumer","other","other_consumer"},capability_nodes={"src","consumer"})
        self.assertEqual(set(r.affected),{"src","consumer"}); self.assertEqual(set(r.cold_preserved),{"other","other_consumer"})
    def test_github_prejob_action_required_not_test_failure(self):
        owner=OwnerRef("github","dallascourchene-commits/AuraOS","pull",311); d=GitHubObservationNormalizer().workflow(WorkflowObservation(owner,33347688964,"G1","d951404","github-actions[bot]","completed","action_required",0))
        self.assertEqual(d["admission_state"],"PRE_JOB_ACTION_REQUIRED"); self.assertFalse(d["semantic_test_failure_proven"])
    def test_joincontext_bounded(self):
        self.store.append(self.event("one","WORK_STATE","g1",{"source_sequence":1})); ctx=JoinContextCompiler().compile(store=self.store,jid=1,protocol_root="p",intent_root="i",current_branch_head="h",active_residual="r",affected={"src"},required_sources={"src"},next_obligation="verify")
        self.assertEqual(ctx.current_sources,(("src","g1"),)); self.assertFalse(ctx.effect_authority)
    def test_joincontext_rejects_broad_hydration(self):
        with self.assertRaisesRegex(ValueError,"AFFECTED_NEIGHBORHOOD_TOO_BROAD"): JoinContextCompiler().compile(store=self.store,jid=1,protocol_root="p",intent_root="i",current_branch_head=None,active_residual=None,affected={f"N{i}" for i in range(26)},required_sources=set(),next_obligation=None)
    def test_random_selective_cones_never_touch_unrelated_components(self):
        for i in range(100): self.store.add_dep(f"S{i}",f"C{i}")
        nodes={f"S{i}" for i in range(100)}|{f"C{i}" for i in range(100)}; rng=random.Random(9)
        for _ in range(2000):
            i=rng.randrange(100); cone=self.store.affected_cone({f"S{i}"}); self.assertEqual(cone,{f"S{i}",f"C{i}"}); self.assertEqual(len(nodes-cone),198)
    def test_no_owner_or_lease_mints_effect(self):
        owner=OwnerRef("github","dallascourchene-commits/AuraOS","issue",796); lease=EvidenceLease("A","rev1","root1","drive")
        self.assertTrue(owner.canonical.endswith("/issue/796")); self.assertFalse(EvidenceLeaseGate(self.store,{"A":lease}).compare({"A":lease},{"A"}).effect_authority)
    def test_100000_cursor_fuzz_invariants(self):
        rng=random.Random(796); counts={}
        for _ in range(100000):
            prior=SourceCursor3D(rng.randrange(0,8),f"g{rng.randrange(0,4)}",f"R{rng.randrange(0,5)}")
            observed=SourceCursor3D(rng.randrange(0,8),f"g{rng.randrange(0,4)}",f"R{rng.randrange(0,5)}")
            t=classify_source_cursor_transition(prior,observed); counts[t]=counts.get(t,0)+1
            if t=="EXACT_REPLAY_NOOP": self.assertEqual(prior,observed)
            if t=="CURRENTNESS_REBIND_ONLY": self.assertEqual(prior.source_sequence,observed.source_sequence); self.assertEqual(prior.semantic_root,observed.semantic_root); self.assertNotEqual(prior.provider_generation,observed.provider_generation)
            if t=="SOURCE_POSITION_SEMANTIC_CONFLICT": self.assertEqual(prior.source_sequence,observed.source_sequence); self.assertNotEqual(prior.semantic_root,observed.semantic_root)
            if t=="CURSOR_ADVANCE_NO_SEMANTIC_WAKE": self.assertGreater(observed.source_sequence,prior.source_sequence); self.assertEqual(prior.semantic_root,observed.semantic_root)
        self.assertGreater(len(counts),4)

if __name__=="__main__": unittest.main()
