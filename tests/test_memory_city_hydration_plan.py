import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'arena'))
import memory_city_navigator as nav
import memory_city_hydration_plan as hp

class HydrationPlanTests(unittest.TestCase):
    def setUp(self): self.text='alpha\nbeta\ngamma\ndelta\n'
    def loc(self, source='d1', a=1, b=1, text=None):
        return nav.capture_source_span(source_id=source,provider_text=self.text if text is None else text,start_line=a,end_line=b)
    def test_exact_duplicates_compile_away(self):
        a=self.loc(); p=hp.compile_hydration_plan((a,a),max_hydration_bytes=100)
        self.assertEqual(p.disposition,hp.HydrationPlanDisposition.READY); self.assertEqual(len(p.required_spans),1); self.assertEqual(p.selected_bytes,a.span_bytes)
    def test_budget_holds_noncompensatory(self):
        a=self.loc(a=1,b=4); p=hp.compile_hydration_plan((a,),max_hydration_bytes=a.span_bytes-1)
        self.assertEqual(p.disposition,hp.HydrationPlanDisposition.HOLD_BUDGET)
    def test_same_logical_span_different_parent_collides(self):
        a=self.loc(); b=self.loc(text='ALPHA\nbeta\ngamma\ndelta\n')
        p=hp.compile_hydration_plan((a,b),max_hydration_bytes=100)
        self.assertEqual(p.disposition,hp.HydrationPlanDisposition.HOLD_COLLISION)
    def test_plan_receipt_deterministic(self):
        a=self.loc(source='b'); b=self.loc(source='a',a=2,b=2)
        x=hp.compile_hydration_plan((a,b),max_hydration_bytes=100)
        y=hp.compile_hydration_plan((b,a),max_hydration_bytes=100)
        self.assertEqual(x.receipt_root,y.receipt_root)

if __name__ == '__main__': unittest.main()
