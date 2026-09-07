import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'arena'))
import memory_city_anchor_locator as al

class AnchorTests(unittest.TestCase):
    def setUp(self): self.text='HEAD\nalpha\nbeta\nTAIL\nafter\n'
    def loc(self): return al.capture_anchored_span(source_id='drive:1',provider_text=self.text,start_anchor='HEAD',end_anchor='TAIL')
    def test_exact(self):
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:1',provider_text=self.text)
        self.assertEqual(r.disposition,al.AnchorDisposition.REUSE_EXACT); self.assertFalse(r.relocated)
    def test_prefix_insertion_relocates_but_rebinds(self):
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:1',provider_text='new\n'+self.text)
        self.assertEqual(r.disposition,al.AnchorDisposition.REBIND_PARENT_CURRENTNESS); self.assertTrue(r.relocated); self.assertEqual((r.start_line,r.end_line),(2,5))
    def test_change_inside_span_rehydrates(self):
        changed=self.text.replace('beta','BETA')
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:1',provider_text=changed)
        self.assertEqual(r.disposition,al.AnchorDisposition.REHYDRATE_SPAN)
    def test_duplicate_anchor_holds(self):
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:1',provider_text='HEAD\nHEAD\nalpha\nbeta\nTAIL\n')
        self.assertEqual(r.disposition,al.AnchorDisposition.HOLD_ANCHOR_AMBIGUITY)
    def test_source_change_holds(self):
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:2',provider_text=self.text)
        self.assertEqual(r.disposition,al.AnchorDisposition.HOLD_SOURCE_IDENTITY)
    def test_reordered_anchors_hold(self):
        r=al.evaluate_anchored_span_at_use(self.loc(),source_id='drive:1',provider_text='TAIL\nalpha\nHEAD\n')
        self.assertEqual(r.disposition,al.AnchorDisposition.HOLD_ANCHOR_AMBIGUITY)

if __name__=='__main__': unittest.main()
