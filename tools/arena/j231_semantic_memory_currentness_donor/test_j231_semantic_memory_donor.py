from __future__ import annotations
import copy
import unittest

from j231_semantic_memory_donor import *


def rec(identity="a", sem="k27 semantic memory lifecycle epoch", src="A", gen="g1", rev="r1", epoch=1, current=True):
    return LifecycleRecord(identity, sem, src, gen, rev, epoch, (4,13,0), current)


class DonorTests(unittest.TestCase):
    def test_add_search_capture(self):
        m=GovernedSemanticMemory(index_generation="idx1")
        m.add(rec(), 100)
        p=m.candidate_plane("semantic memory lifecycle")
        self.assertIn("a", p.candidate_ids)
        c=m.capture_at_use("semantic memory lifecycle", p, "a", rec(), now_s=110, max_age_s=20)
        self.assertIsNotNone(c); self.assertFalse(c.authority["effect"])

    def test_aba_epoch_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(epoch=3), now_s=110, max_age_s=20))

    def test_revision_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(rev="r2"), now_s=110, max_age_s=20))

    def test_source_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(src="B"), now_s=110, max_age_s=20))

    def test_semantic_projection_drift_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(sem="different semantic projection"), now_s=110, max_age_s=20))

    def test_generation_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(gen="g2"), now_s=110, max_age_s=20))

    def test_current_false_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(current=False), now_s=110, max_age_s=20))

    def test_future_and_stale_time_block(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        self.assertFalse(m.reopen_current("a", rec(), now_s=99, max_age_s=20))
        self.assertFalse(m.reopen_current("a", rec(), now_s=200, max_age_s=20))

    def test_receipt_tamper_blocks(self):
        m=GovernedSemanticMemory(index_generation="idx1"); m.add(rec(), 100)
        x=m.receipts["a"]
        m.receipts["a"] = LifecycleReceipt(x.identity,x.source_sha256,x.semantic_sha256,x.generation,x.revision_id,x.lifecycle_epoch,x.observed_s,x.index_generation,"0"*64)
        self.assertFalse(m.reopen_current("a", rec(), now_s=110, max_age_s=20))

    def test_budget_pre_effect_no_mutation(self):
        b=WorkBudget(max_records=10,max_semantic_bytes=4,max_record_bytes=4,max_feature_bits=100000,max_lexical_refs=100,max_query_bytes=100,max_query_feature_bits=100000,max_candidate_postings=100)
        m=GovernedSemanticMemory(index_generation="i",budget=b)
        before=(dict(m.records),dict(m.signatures),dict(m.prefix),dict(m.lex))
        with self.assertRaisesRegex(ValueError,"WORK_BUDGET_RECORD_BYTES"):
            m.add(rec(sem="12345"),1)
        after=(dict(m.records),dict(m.signatures),dict(m.prefix),dict(m.lex))
        self.assertEqual(before,after)

    def test_candidate_posting_budget(self):
        b=WorkBudget(max_records=10,max_semantic_bytes=10000,max_record_bytes=1000,max_feature_bits=1000000,max_lexical_refs=1000,max_query_bytes=100,max_query_feature_bits=100000,max_candidate_postings=1)
        m=GovernedSemanticMemory(index_generation="i",budget=b,prefix_bits=1)
        m.add(rec("a",sem="common alpha"),1); m.add(rec("b",sem="common beta"),1)
        with self.assertRaisesRegex(ValueError,"WORK_BUDGET_CANDIDATE_POSTINGS"):
            m.candidate_plane("common", k=1)

    def test_stable_union_preserves_native(self):
        self.assertEqual(GovernedSemanticMemory.stable_union(("n2","n1"),("n1","s1","s2")),("n2","n1","s1","s2"))

    def test_capture_stable_after_caller_mutation(self):
        m=GovernedSemanticMemory(index_generation="i"); r=rec(); m.add(r,100)
        p=m.candidate_plane("semantic memory")
        c=m.capture_at_use("semantic memory",p,"a",r,now_s=101,max_age_s=10)
        external={"a":"CHANGED"}
        self.assertEqual(c.exact_source,"A"); self.assertNotEqual(c.exact_source,external["a"])

    def test_plane_tamper_blocks(self):
        m=GovernedSemanticMemory(index_generation="i"); r=rec(); m.add(r,100)
        p=m.candidate_plane("semantic memory")
        bad=CandidatePlane(p.query_digest,p.candidate_ids,p.index_generation,p.semantic_index_root,"0"*64)
        self.assertIsNone(m.capture_at_use("semantic memory",bad,"a",r,now_s=101,max_age_s=10))

    def test_raw_lifecycle_cone_is_small(self):
        c=set(reproof_cone(["RAW_SOURCE_STATE"]))
        self.assertEqual(c,{"RAW_SOURCE_STATE","CURRENTNESS_RECEIPT","AT_USE_CAPSULE"})

    def test_routing_cone_reuses_signature(self):
        c=set(reproof_cone(["ROUTING_PROFILE"]))
        self.assertNotIn("SIGNATURE",c); self.assertIn("PREFIX_INDEX",c); self.assertIn("AT_USE_CAPSULE",c)

    def test_unknown_reproof_root_blocks(self):
        with self.assertRaises(ValueError): reproof_cone(["NOPE"])

    def test_release_exact_local_pending_hosted(self):
        e=self.ev(hosted_pass=False)
        self.assertEqual(release_gate(e).state,"LOCAL_D0_GREEN_HOSTED_PENDING")

    def test_release_hosted_ready_for_independent(self):
        e=self.ev(hosted_pass=True)
        self.assertEqual(release_gate(e).state,"READY_FOR_INDEPENDENT_REVIEW")

    def test_release_exact_carrier_mismatch_holds(self):
        e=self.ev(observed_carrier_head="carrier2")
        self.assertEqual(release_gate(e).state,"HOLD")

    def test_release_metadata_only_requires_verification(self):
        e=self.ev(movement_kind="METADATA_ONLY",metadata_only_verified=False)
        self.assertEqual(release_gate(e).state,"HOLD")
        e=self.ev(movement_kind="METADATA_ONLY",metadata_only_verified=True)
        self.assertNotEqual(release_gate(e).state,"HOLD")

    def test_release_semantic_drift_holds_even_all_gates_true(self):
        e=self.ev(observed_semantic_head="b",hosted_pass=True,independent_review_pass=True,gate10_pass=True,effect_authority=True)
        d=release_gate(e); self.assertEqual(d.state,"HOLD"); self.assertFalse(d.gate10); self.assertFalse(d.effect_authority)

    @staticmethod
    def ev(**kw):
        d=dict(expected_semantic_head="a",observed_semantic_head="a",observed_carrier_head="a",movement_kind="EXACT",metadata_only_verified=False,
               donor_source_sha256="s",expected_source_sha256="s",donor_test_sha256="t",expected_test_sha256="t",campaign_sha256="c",expected_campaign_sha256="c",local_proof_root="p",expected_local_proof_root="p")
        d.update(kw); return ReleaseEvidence(**d)

if __name__ == "__main__": unittest.main()
