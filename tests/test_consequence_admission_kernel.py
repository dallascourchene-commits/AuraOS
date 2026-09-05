import itertools
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))

from consequence_admission_kernel import *


def ready_vector():
    return ConsequenceVector((AxisState.VERIFIED, AxisState.VERIFIED, AxisState.UNKNOWN, AxisState.VERIFIED,
                              AxisState.VERIFIED, AxisState.UNKNOWN, AxisState.UNKNOWN, AxisState.VERIFIED))


def source(current=True):
    return SourceExit("drive:src", "owner:current", "gen25", "semantic-root", current)


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.k = ConsequenceAdmissionKernel()
        self.p = PROJECT_POLICIES["O4_FRONTIER"]

    def assess(self, vec=None, **kw):
        return self.k.assess(AdmissionInput("P", vec or ready_vector(), self.p, kw.get("source_exit", source()),
                                            kw.get("unresolved_dependencies", ()), kw.get("asks_effect_authority", False)))

    def test_ready_nonauthorizing(self):
        r = self.assess()
        self.assertEqual(r.decision, Decision.READY_NONAUTHORIZING)
        self.assertTrue(r.scope_bridge_eligible)
        self.assertFalse(r.truth_authority or r.effect_authority or r.gate10)

    def test_any_hard_invalid_dominates_each_axis(self):
        for i in range(8):
            vals = list(ready_vector().omega8); vals[i] = AxisState.HARD_INVALID
            r = self.assess(ConsequenceVector(tuple(vals)))
            self.assertEqual(r.decision, Decision.HOLD_HARD_INVALID)
            self.assertIn(i, r.hard_invalid_axes)

    def test_trailing_13d_routing_never_repairs_hard_invalid(self):
        vals = list(ready_vector().omega8); vals[2] = AxisState.HARD_INVALID
        for tail in itertools.product((0,1,2), repeat=5):
            r = self.assess(ConsequenceVector(tuple(vals), tail))
            self.assertEqual(r.decision, Decision.HOLD_HARD_INVALID)

    def test_required_unknown_holds(self):
        vals = list(ready_vector().omega8); vals[4] = AxisState.UNKNOWN
        self.assertEqual(self.assess(ConsequenceVector(tuple(vals))).decision, Decision.HOLD_REQUIRED_UNKNOWN)

    def test_missing_source_exit_holds(self):
        self.assertEqual(self.assess(source_exit=None).decision, Decision.HOLD_MISSING_SOURCE_EXIT)

    def test_stale_source_exit_holds(self):
        self.assertEqual(self.assess(source_exit=source(False)).decision, Decision.HOLD_STALE_SOURCE)

    def test_malformed_omega8_value_fails_closed(self):
        vals = list(ready_vector().omega8); vals[2] = 99
        with self.assertRaises(AdmissionError):
            ConsequenceVector(tuple(vals))

    def test_plain_int_even_valid_domain_fails_closed(self):
        vals = list(ready_vector().omega8); vals[2] = 2
        with self.assertRaises(AdmissionError):
            ConsequenceVector(tuple(vals))

    def test_dependency_debt_noncompensatory(self):
        r = self.assess(unresolved_dependencies=("scope_lift_gate", "unrelated"))
        self.assertEqual(r.decision, Decision.HOLD_DEPENDENCY_DEBT)
        self.assertEqual(r.unpaid_dependencies, ("scope_lift_gate",))

    def test_effect_authority_not_minted(self):
        self.assertEqual(self.assess(asks_effect_authority=True).decision, Decision.HOLD_AUTHORITY_CEILING)

    def test_routing_coordinates_do_not_change_ready_decision(self):
        roots = set()
        for tail in itertools.product((0,1,2), repeat=5):
            r = self.assess(ConsequenceVector(ready_vector().omega8, tail))
            self.assertEqual(r.decision, Decision.READY_NONAUTHORIZING)
            roots.add((r.decision, r.hard_invalid_axes, r.required_unknown_axes, r.unpaid_dependencies))
        self.assertEqual(len(roots), 1)

    def test_omega8_census(self):
        c = exhaustive_omega8(self.p)
        self.assertEqual(sum(c.values()), 6561)
        self.assertEqual(c[Decision.READY_NONAUTHORIZING.value], 8)

    def test_hard_invalid_priority_over_other_failures(self):
        vals = list(ready_vector().omega8); vals[6] = AxisState.HARD_INVALID; vals[0] = AxisState.UNKNOWN
        r = self.assess(ConsequenceVector(tuple(vals)), source_exit=source(False), unresolved_dependencies=("semantic_cut",))
        self.assertEqual(r.decision, Decision.HOLD_HARD_INVALID)

    def test_receipt_digest_deterministic(self):
        self.assertEqual(self.assess().receipt_digest, self.assess().receipt_digest)

    def test_unsupported_canonical_values_fail_closed(self):
        with self.assertRaises(AdmissionError):
            digest({"x": object()})


class LedgerTests(unittest.TestCase):
    def test_append_and_verify(self):
        k = ConsequenceAdmissionKernel(); p = PROJECT_POLICIES["BUGHOUND_O12"]
        r = k.assess(AdmissionInput("BUGHOUND_O12", ready_vector(), p, source()))
        l = ConsequenceEventLedger(); e = l.append_receipt(r, p.dependency_keys, event_id="e1")
        self.assertEqual(e.event_type, "ADMIT")
        self.assertTrue(l.verify()["ok"])

    def test_invalidation_wakes_smallest_cutset(self):
        k = ConsequenceAdmissionKernel(); l = ConsequenceEventLedger()
        for project, policy in PROJECT_POLICIES.items():
            r = k.assess(AdmissionInput(project, ready_vector(), policy, source()))
            l.append_receipt(r, policy.dependency_keys, event_id="admit-" + project)
        inv = l.invalidate(("semantic_root",), event_id="inv-1")
        self.assertEqual(inv["affected_projects"], ["AURAOS_796"])
        self.assertEqual(inv["count"], 1)

    def test_invalidation_never_auto_readmits(self):
        l = ConsequenceEventLedger(); inv = l.invalidate(("x",), event_id="i")
        self.assertEqual(inv["affected_projects"], [])
        self.assertTrue(l.verify()["ok"])

    def test_duplicate_event_id_fails(self):
        k = ConsequenceAdmissionKernel(); p = PROJECT_POLICIES["O4_FRONTIER"]
        r = k.assess(AdmissionInput("O4", ready_vector(), p, source()))
        l = ConsequenceEventLedger(); l.append_receipt(r, p.dependency_keys, event_id="same")
        with self.assertRaises(AdmissionError):
            l.append_receipt(r, p.dependency_keys, event_id="same")

    def test_tamper_detected(self):
        k = ConsequenceAdmissionKernel(); p = PROJECT_POLICIES["O4_FRONTIER"]
        r = k.assess(AdmissionInput("O4", ready_vector(), p, source()))
        l = ConsequenceEventLedger(); l.append_receipt(r, p.dependency_keys, event_id="x")
        object.__setattr__(l._events[0], "receipt_digest", "tampered")
        self.assertFalse(l.verify()["ok"])


class SuccessionTests(unittest.TestCase):
    def test_successor_neutral_envelope(self):
        e = ReadjudicationEnvelope("P", "c", "pol", source(), ("d",), ("source_changed",), ("scar",), "r")
        self.assertEqual(len(e.envelope_digest), 64)

    def test_inherited_truth_rejected(self):
        e = ReadjudicationEnvelope("P", "c", "pol", source(), (), (), (), "r", inherited_truth=True)
        with self.assertRaises(AdmissionError): e.validate()

    def test_inherited_authority_rejected(self):
        e = ReadjudicationEnvelope("P", "c", "pol", source(), (), (), (), "r", inherited_authority=True)
        with self.assertRaises(AdmissionError): e.validate()

    def test_missing_source_exit_rejected(self):
        e = ReadjudicationEnvelope("P", "c", "pol", SourceExit("", "", "", "", True), (), (), (), "r")
        with self.assertRaises(AdmissionError): e.validate()

    def test_stale_source_exit_rejected(self):
        e = ReadjudicationEnvelope("P", "c", "pol", source(False), (), (), (), "r")
        with self.assertRaises(AdmissionError): e.validate()


if __name__ == "__main__":
    unittest.main()
