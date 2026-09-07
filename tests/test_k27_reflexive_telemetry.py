import itertools, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_reflexive_telemetry import ProbeTransition,ReflexiveTelemetryGate,hard13d_admission


def p(pid='p',pre='a',post='a',effect='PASSIVE',c='new',material=True,collision=True,lawful=True,cx='cx',polarity='positive'):
    return ProbeTransition(pid,pre,post,effect,c,material,collision,lawful,cx,polarity)

class ReflexiveTelemetryTests(unittest.TestCase):
    def test_passive_probe_that_changes_state_holds(self):
        r=ReflexiveTelemetryGate().admit(p(post='b'))
        self.assertEqual(r.status,'HOLD_UNDECLARED_PROBE_EFFECT'); self.assertFalse(r.telemetry_reusable)

    def test_declared_mutating_probe_can_be_admitted_but_not_reused(self):
        r=ReflexiveTelemetryGate().admit(p(post='b',effect='MAY_MUTATE'))
        self.assertEqual(r.status,'ADMISSION_READY'); self.assertTrue(r.novelty_admitted); self.assertFalse(r.telemetry_reusable)

    def test_duplicate_consequence_is_support_not_discovery(self):
        g=ReflexiveTelemetryGate({'known'})
        r=g.admit(p(c='known'))
        self.assertEqual(r.status,'SUPPORT_NOT_DISCOVERY'); self.assertFalse(r.novelty_admitted)

    def test_missing_counterexample_holds(self):
        r=ReflexiveTelemetryGate().admit(p(cx=''))
        self.assertEqual(r.status,'HOLD_NEEDS_COUNTEREXAMPLE')

    def test_failed_admission_prerequisite_rejects(self):
        for kwargs in ({'material':False},{'collision':False},{'lawful':False}):
            self.assertEqual(ReflexiveTelemetryGate().admit(p(**kwargs)).status,'REJECT')

    def test_consumed_once_probe_cannot_replay(self):
        g=ReflexiveTelemetryGate(); q=p(effect='CONSUMED_ONCE')
        self.assertEqual(g.admit(q).status,'ADMISSION_READY')
        self.assertEqual(g.admit(q).status,'HOLD_CONSUMED_ONCE')

    def test_sequence_requires_exact_post_to_pre_chain(self):
        g=ReflexiveTelemetryGate()
        out=g.compile_sequence([p('p1','a','b','MAY_MUTATE','c1'),p('p2','x','x','PASSIVE','c2')])
        self.assertEqual(out[-1].status,'HOLD_STATE_CHAIN_GAP')

    def test_sequence_accepts_exact_chain(self):
        g=ReflexiveTelemetryGate()
        out=g.compile_sequence([p('p1','a','b','MAY_MUTATE','c1'),p('p2','b','b','PASSIVE','c2')])
        self.assertEqual([x.status for x in out],['ADMISSION_READY','ADMISSION_READY'])

    def test_admitted_consequence_cannot_be_counted_twice(self):
        g=ReflexiveTelemetryGate()
        self.assertEqual(g.admit(p('p1',c='c1')).status,'ADMISSION_READY')
        self.assertEqual(g.admit(p('p2',c='c1')).status,'SUPPORT_NOT_DISCOVERY')

    def test_negative_polarity_is_typed_not_authoritative(self):
        r=ReflexiveTelemetryGate().admit(p(polarity='negative'))
        self.assertEqual(r.status,'ADMISSION_READY'); self.assertFalse(r.authority_minted); self.assertFalse(r.gate10)

    def test_13d_context_cannot_repair_hard_invalid(self):
        for tail in itertools.product(range(3),repeat=5):
            self.assertEqual(hard13d_admission((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')

    def test_13d_all_hard_ready_ignores_context_for_admission(self):
        for tail in itertools.product(range(3),repeat=5):
            self.assertEqual(hard13d_admission((2,)*8+tail),'READY_D0')

if __name__=='__main__': unittest.main()
