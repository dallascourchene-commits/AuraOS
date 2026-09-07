from __future__ import annotations
import tempfile,unittest
from physical_wake_acceptance import *

C=AcceptanceContract('T','CMD','a'*64,'b'*64,0)
def ev(i,kind=None,t=None): return WakeEvent('T','CMD',str(i),kind or REQUIRED_KINDS[i],'c'*64,t if t is not None else i)
class Tests(unittest.TestCase):
    def fresh(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); return WakeAcceptanceLedger(td.name+'/l.db')
    def fill(self,l):
        for i in range(8): self.assertEqual(l.append(ev(i)),'APPENDED')
    def test_happy_execution_false_acceptance(self):
        l=self.fresh(); self.fill(l); self.assertTrue(l.evaluate(C,0,'a'*64,'b'*64)['accepted'])
    def test_missing_event_holds(self):
        l=self.fresh(); [l.append(ev(i)) for i in range(7)]; self.assertFalse(l.evaluate(C,0,'a'*64,'b'*64)['accepted'])
    def test_ordered_subset_not_complete(self):
        l=self.fresh(); [l.append(ev(i)) for i in [0,1,2,3,4,5,7]]; r=l.evaluate(C,0,'a'*64,'b'*64); self.assertIn('COVERAGE_INCOMPLETE',r['reasons'])
    def test_duplicate_collapses(self):
        l=self.fresh(); self.assertEqual(l.append(ev(0)),'APPENDED'); self.assertEqual(l.append(ev(0)),'DUPLICATE_COLLAPSED')
    def test_equivocation_holds_at_append(self):
        l=self.fresh(); l.append(ev(0));
        with self.assertRaisesRegex(WitnessError,'SEQUENCE_EQUIVOCATION'): l.append(WakeEvent('T','CMD','0',EventKind.WSL_STOP_OBSERVED,'c'*64,0))
    def test_wrong_kind_sequence_holds(self):
        l=self.fresh();
        for i in range(8): l.append(ev(i,REQUIRED_KINDS[(i+1)%8]))
        self.assertIn('EVENT_KIND_SEQUENCE_MISMATCH',l.evaluate(C,0,'a'*64,'b'*64)['reasons'])
    def test_time_reversal_holds(self):
        l=self.fresh();
        for i in range(8): l.append(ev(i,t=100-i))
        self.assertIn('CAUSAL_TIME_ORDER_MISMATCH',l.evaluate(C,0,'a'*64,'b'*64)['reasons'])
    def test_provider_count_must_match_contract(self):
        l=self.fresh(); self.fill(l); self.assertFalse(l.evaluate(C,1,'a'*64,'b'*64)['accepted'])
    def test_currentness_move_holds(self):
        l=self.fresh(); self.fill(l); self.assertIn('CURRENTNESS_MOVED',l.evaluate(C,0,'d'*64,'b'*64)['reasons'])
    def test_authority_move_holds(self):
        l=self.fresh(); self.fill(l); self.assertIn('AUTHORITY_MOVED',l.evaluate(C,0,'a'*64,'d'*64)['reasons'])
    def test_crash_reopen_preserves_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            p=td+'/l.db'; l=WakeAcceptanceLedger(p); [l.append(ev(i)) for i in range(4)]; del l
            l=WakeAcceptanceLedger(p); [l.append(ev(i)) for i in range(4,8)]; self.assertTrue(l.evaluate(C,0,'a'*64,'b'*64)['accepted'])
    def test_command_scope_isolated(self):
        l=self.fresh(); self.fill(l); l.append(WakeEvent('T','OTHER','0',EventKind.WINDOWS_GUARDIAN_ALIVE,'c'*64,0)); self.assertTrue(l.evaluate(C,0,'a'*64,'b'*64)['accepted'])
if __name__=='__main__':unittest.main()
