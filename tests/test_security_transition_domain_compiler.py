import hashlib
import unittest

from tools.arena.worker_cells.gpt56sol_security_transition_domain.security_transition_domain import (
    CrossPlaneBinding, Decision, ParentReceipt, TransitionDomainError, TransitionDomainSpec,
    TransitionEvidence, causal_time_order, compile_reproof_cone, exact_nonnegative_int,
    finite_positive_duration, readjudicate, terminal_transition_allowed,
)

H = lambda s: hashlib.sha256(s.encode()).hexdigest()
GRAPH = {
    "generation": ("semantic_domain", "semantic_projection"),
    "semantic_domain": ("cross_plane_binding", "value_domain"),
    "semantic_projection": ("cross_plane_binding",),
    "cross_plane_binding": ("evidence_current",),
    "value_domain": ("causal_order", "lifecycle_transition"),
    "causal_order": ("evidence_current",),
    "lifecycle_transition": ("evidence_current",),
    "evidence_current": ("reproducible",),
    "reproducible": (),
}

def binding():
    spec = TransitionDomainSpec(H("domain"), H("projection"), H("schema"))
    return CrossPlaneBinding(
        ParentReceipt("AGENT_13_PR839", "1a66ff9162abd69dc0223842e672f38f271a686f", H("839")),
        ParentReceipt("GPT56SOL_PR845", "423a437a10e8252130cc1e74f0c2693c80284c34", H("845")),
        spec.spec_root,
    )

def green(**kw):
    base = dict(generation_current=True, semantic_domain_current=True, semantic_projection_current=True,
                cross_plane_binding_current=True, value_domain_valid=True, causal_order_valid=True,
                lifecycle_transition_valid=True, external_auth_complete=True, evidence_current=True,
                reproducible=True, authority_ceiling_intact=True)
    base.update(kw)
    return TransitionEvidence(**base)

class DomainTests(unittest.TestCase):
    def test_exact_int_rejects_bool_and_float(self):
        for bad in (True, False, 1.0, -1, "1", None):
            with self.subTest(bad=bad), self.assertRaises(TransitionDomainError): exact_nonnegative_int(bad)
    def test_finite_positive_duration_rejects_exceptional_values(self):
        for bad in (True, False, 0, -1, float("nan"), float("inf"), -float("inf"), 10**10000, "1", None):
            with self.subTest(bad=bad), self.assertRaises(TransitionDomainError): finite_positive_duration(bad)
        self.assertEqual(finite_positive_duration(3), 3.0)
        self.assertEqual(finite_positive_duration(0.25), 0.25)
    def test_causal_time_requires_partial_order(self):
        self.assertTrue(causal_time_order(observed_at_ms=1000, issued_at_ms=1100, now_ms=1200, expires_at_ms=2000, max_age_ms=500))
        self.assertFalse(causal_time_order(observed_at_ms=1000, issued_at_ms=900, now_ms=1200, expires_at_ms=2000, max_age_ms=500))
        self.assertFalse(causal_time_order(observed_at_ms=1300, issued_at_ms=1400, now_ms=1200, expires_at_ms=2000, max_age_ms=500))
    def test_terminal_completed_is_monotone(self):
        self.assertFalse(terminal_transition_allowed("COMPLETED", "NOT_STARTED"))
        self.assertFalse(terminal_transition_allowed("COMPLETED", "UNKNOWN"))
        self.assertTrue(terminal_transition_allowed("COMPLETED", "COMPLETED"))
        self.assertTrue(terminal_transition_allowed("UNKNOWN", "NOT_STARTED"))
    def test_reproof_cone_is_descendant_closed(self):
        self.assertEqual(compile_reproof_cone(GRAPH, ("value_domain",)), ("causal_order", "evidence_current", "lifecycle_transition", "reproducible", "value_domain"))
    def test_local_transition_debt_precedes_external_auth(self):
        r = readjudicate(evidence=green(value_domain_valid=False, external_auth_complete=False), binding=binding(), dependency_graph=GRAPH, changed_dimensions=("value_domain",))
        self.assertEqual(r.decision, Decision.REPROVE_LOCAL_FIRST)
        self.assertIn("causal_order", r.reproof_cone)
    def test_declared_changes_cannot_hide_failed_axis(self):
        r = readjudicate(evidence=green(value_domain_valid=False), binding=binding(), dependency_graph=GRAPH, changed_dimensions=("semantic_projection",))
        self.assertEqual(r.decision, Decision.REPROVE_LOCAL_FIRST)
        self.assertIn("semantic_projection", r.reproof_cone)
        self.assertIn("value_domain", r.reproof_cone)
        self.assertIn("causal_order", r.reproof_cone)
        self.assertIn("lifecycle_transition", r.reproof_cone)
    def test_external_auth_only_after_local_exact(self):
        r = readjudicate(evidence=green(external_auth_complete=False), binding=binding(), dependency_graph=GRAPH)
        self.assertEqual(r.decision, Decision.READJUDICATE_EXTERNAL_AUTH)
        self.assertEqual(r.reproof_cone, ())
    def test_authority_cannot_be_compensated(self):
        self.assertEqual(readjudicate(evidence=green(authority_ceiling_intact=False), binding=binding(), dependency_graph=GRAPH).decision, Decision.HOLD_AUTHORITY)
    def test_green_is_only_eligible_path(self):
        self.assertEqual(readjudicate(evidence=green(), binding=binding(), dependency_graph=GRAPH).decision, Decision.ELIGIBLE_FOR_FRESH_READJUDICATION)
    def test_parent_labels_must_be_distinct(self):
        spec = TransitionDomainSpec(H("d"), H("p"), H("s")); x = ParentReceipt("same", "g1", H("1")); y = ParentReceipt("same", "g2", H("2"))
        with self.assertRaises(TransitionDomainError): CrossPlaneBinding(x, y, spec.spec_root).validate()
    def test_boolean_evidence_cannot_alias_integer_truth(self):
        e = green(); object.__setattr__(e, "generation_current", 1)
        with self.assertRaises(TransitionDomainError): e.validate()

if __name__ == "__main__": unittest.main()
