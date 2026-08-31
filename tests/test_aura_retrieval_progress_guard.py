import importlib.util
from pathlib import Path
import sys
import unittest


MODULE = Path(__file__).resolve().parents[1] / "tools" / "aura_retrieval_progress_guard.py"
SPEC = importlib.util.spec_from_file_location("aura_retrieval_progress_guard", MODULE)
assert SPEC and SPEC.loader
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
SPEC.loader.exec_module(m)


class RetrievalProgressGuardTests(unittest.TestCase):
    def fp(self, tool="search"):
        return m.RetrievalFingerprint(
            provider="drive",
            tool=tool,
            resource="aura-drive-2",
            query_or_pattern="Front Door",
            page_or_range="0:20",
            semantic_purpose="orientation",
        )

    def obs(self, *, tool="search", state="g0", evidence="e0"):
        return m.RetrievalObservation(self.fp(tool), state, evidence)

    def test_initial_is_allowed_but_nonpromoting(self):
        r = m.assess_retrieval_progress(previous=None, current=self.obs())
        self.assertEqual(r.decision, m.RetrievalDecision.ALLOW_INITIAL)
        self.assertEqual(r.next_no_progress_count, 0)
        r.validate_claim_ceiling()

    def test_first_identical_no_progress_requires_axis_change(self):
        r = m.assess_retrieval_progress(
            previous=self.obs(), current=self.obs(), prior_no_progress_count=0
        )
        self.assertEqual(r.decision, m.RetrievalDecision.CHANGE_AXIS_REQUIRED)
        self.assertEqual(r.next_no_progress_count, 1)

    def test_second_identical_no_progress_collapses_cone(self):
        r = m.assess_retrieval_progress(
            previous=self.obs(), current=self.obs(), prior_no_progress_count=1
        )
        self.assertEqual(r.decision, m.RetrievalDecision.COLLAPSE_CONE)
        self.assertEqual(r.next_no_progress_count, 2)

    def test_changed_tool_is_changed_axis(self):
        r = m.assess_retrieval_progress(
            previous=self.obs(), current=self.obs(tool="fetch"), prior_no_progress_count=1
        )
        self.assertEqual(r.decision, m.RetrievalDecision.ALLOW_CHANGED_AXIS)
        self.assertEqual(r.next_no_progress_count, 0)

    def test_changed_provider_state_is_progress_without_currentness_promotion(self):
        r = m.assess_retrieval_progress(
            previous=self.obs(), current=self.obs(state="g1"), prior_no_progress_count=1
        )
        self.assertEqual(r.decision, m.RetrievalDecision.ALLOW_STATE_TRANSITION)
        self.assertTrue(r.provider_state_changed)
        self.assertFalse(r.source_currentness_proven)

    def test_changed_evidence_is_progress(self):
        r = m.assess_retrieval_progress(
            previous=self.obs(), current=self.obs(evidence="e1")
        )
        self.assertEqual(r.decision, m.RetrievalDecision.ALLOW_STATE_TRANSITION)
        self.assertTrue(r.evidence_changed)

    def test_initial_cannot_inherit_no_progress_debt(self):
        with self.assertRaises(ValueError):
            m.assess_retrieval_progress(
                previous=None, current=self.obs(), prior_no_progress_count=1
            )

    def test_blank_fingerprint_axis_rejected(self):
        with self.assertRaises(ValueError):
            m.RetrievalFingerprint("", "search", "r", "q", "p", "purpose")

    def test_blank_state_or_evidence_rejected(self):
        with self.assertRaises(ValueError):
            m.RetrievalObservation(self.fp(), "", "e")
        with self.assertRaises(ValueError):
            m.RetrievalObservation(self.fp(), "g", "")

    def test_negative_or_boolean_counter_rejected(self):
        with self.assertRaises(ValueError):
            m.assess_retrieval_progress(
                previous=self.obs(), current=self.obs(), prior_no_progress_count=-1
            )
        with self.assertRaises(ValueError):
            m.assess_retrieval_progress(
                previous=self.obs(), current=self.obs(), prior_no_progress_count=True
            )

    def test_receipt_is_deterministic(self):
        a = m.assess_retrieval_progress(previous=self.obs(), current=self.obs())
        b = m.assess_retrieval_progress(previous=self.obs(), current=self.obs())
        self.assertEqual(a.receipt_digest, b.receipt_digest)

    def test_different_j_exhausts_24_state_matrix(self):
        self.assertEqual(m.prove_different_j(), 24)


if __name__ == "__main__":
    unittest.main()
