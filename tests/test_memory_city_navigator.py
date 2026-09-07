import sys, unittest
from dataclasses import replace
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'arena'))
import memory_city_navigator as nav

HEAD = '64374fb4e235297050e37b003943c79bce14ff00'

def projection():
    return {'schema':'AURA-K27-ROUTE-PROJECTION-v1','binding':{'object_id':'MCXR-0001','revision_id':'r1','epoch':7,'path':[2,4,6],'local_registry_current':True,'upstream_currentness_asserted':False,'truth_authority':False,'effect_authority':False,'gate10':False},'payload':{'steps':['a','b']},'dependencies':{'MC-1':'ra'},'dependency_epochs':{'MC-1':2},'review_only':True,'execution_authority':False,'gate10':False}
class Runtime:
    consumed=False
    def __init__(self,p=None): self.p = projection() if p is None else p
    def route_projection(self, object_id): return self.p

def cut(epoch=11, head=HEAD, inc='runtime-1'): return nav.OwnerCut(863,head,epoch,inc)

class RouteCardTests(unittest.TestCase):
    def test_happy(self):
        c=nav.compile_route_card(Runtime(),objective='find current route',object_id='MCXR-0001',owner_cut=cut())
        self.assertEqual(c.target_k27,(2,4,6)); self.assertFalse(c.authority_minted); self.assertEqual(len(c.receipt_root),64)
    def test_deterministic(self):
        a=nav.compile_route_card(Runtime(),objective='x',object_id='MCXR-0001',owner_cut=cut())
        b=nav.compile_route_card(Runtime(),objective='x',object_id='MCXR-0001',owner_cut=cut())
        self.assertEqual(a.receipt_root,b.receipt_root)
    def test_consumed_holds(self):
        r=Runtime(); r.consumed=True
        with self.assertRaises(nav.NavigatorError): nav.compile_route_card(r,objective='x',object_id='MCXR-0001',owner_cut=cut())
    def test_nonroute_holds_before_read(self):
        with self.assertRaises(nav.NavigatorError): nav.compile_route_card(Runtime(),objective='x',object_id='MC-1',owner_cut=cut())
    def test_stale_holds(self):
        p=projection(); p['binding']['local_registry_current']=False
        with self.assertRaises(nav.NavigatorError): nav.compile_route_card(Runtime(p),objective='x',object_id='MCXR-0001',owner_cut=cut())
    def test_authority_escalation_holds(self):
        p=projection(); p['execution_authority']=True
        with self.assertRaises(nav.NavigatorError): nav.compile_route_card(Runtime(p),objective='x',object_id='MCXR-0001',owner_cut=cut())
    def test_binding_truth_escalation_holds(self):
        p=projection(); p['binding']['truth_authority']=True
        with self.assertRaises(nav.NavigatorError): nav.compile_route_card(Runtime(p),objective='x',object_id='MCXR-0001',owner_cut=cut())
    def test_dependency_order_canonical(self):
        a=projection(); a['dependencies']={'b':'2','a':'1'}
        b=projection(); b['dependencies']={'a':'1','b':'2'}
        ca=nav.compile_route_card(Runtime(a),objective='x',object_id='MCXR-0001',owner_cut=cut())
        cb=nav.compile_route_card(Runtime(b),objective='x',object_id='MCXR-0001',owner_cut=cut())
        self.assertEqual(ca.dependency_root,cb.dependency_root)

class SpanTests(unittest.TestCase):
    def setUp(self): self.text='alpha\nbeta\ngamma\ndelta\n'
    def test_exact(self):
        x=nav.capture_source_span(source_id='drive:1',provider_text=self.text,start_line=2,end_line=3,k27_hint=(2,7))
        self.assertEqual(nav.evaluate_source_span_at_use(x,source_id='drive:1',provider_text=self.text)[0],nav.SpanDisposition.REUSE_EXACT)
    def test_parent_change_same_span_rebinds(self):
        x=nav.capture_source_span(source_id='drive:1',provider_text=self.text,start_line=2,end_line=3)
        self.assertEqual(nav.evaluate_source_span_at_use(x,source_id='drive:1',provider_text='ALPHA\nbeta\ngamma\ndelta\n')[0],nav.SpanDisposition.REBIND_PARENT_CURRENTNESS)
    def test_span_change_rehydrates(self):
        x=nav.capture_source_span(source_id='drive:1',provider_text=self.text,start_line=2,end_line=3)
        self.assertEqual(nav.evaluate_source_span_at_use(x,source_id='drive:1',provider_text='alpha\nBETA\ngamma\ndelta\n')[0],nav.SpanDisposition.REHYDRATE_SPAN)
    def test_source_change_holds(self):
        x=nav.capture_source_span(source_id='drive:1',provider_text=self.text,start_line=1,end_line=1)
        self.assertEqual(nav.evaluate_source_span_at_use(x,source_id='drive:2',provider_text=self.text)[0],nav.SpanDisposition.HOLD_SOURCE_IDENTITY)

class UseTimeTests(unittest.TestCase):
    def setUp(self):
        self.card=nav.compile_route_card(Runtime(),objective='x',object_id='MCXR-0001',owner_cut=cut())
        self.limits=nav.RouteUseLimits(1000,10,2,2); self.obs=nav.RouteUseObservation(100,3,1,1)
    def use(self,**kw):
        args=dict(compiled_event_time='e1',use_event_time='e1',current_owner_cut=cut(),current_dependency_root=self.card.dependency_root,compiled_validity_epoch=4,use_validity_epoch=4,limits=self.limits,observation=self.obs)
        args.update(kw); return nav.evaluate_route_at_use(self.card,**args)
    def test_exact(self): self.assertEqual(self.use()[0],nav.RouteUseDisposition.REUSE_EXACT)
    def test_event_time_separate(self): self.assertEqual(self.use(use_event_time='e2')[0],nav.RouteUseDisposition.RECONSTRUCT_EVENT_TIME)
    def test_lifecycle_rebind(self): self.assertEqual(self.use(current_owner_cut=cut(epoch=12))[0],nav.RouteUseDisposition.REBIND_CURRENTNESS)
    def test_owner_reproof(self): self.assertEqual(self.use(current_owner_cut=cut(inc='runtime-2'))[0],nav.RouteUseDisposition.REPROVE_OWNER)
    def test_dependency_reproof(self): self.assertEqual(self.use(current_dependency_root='f'*64)[0],nav.RouteUseDisposition.REPROVE_CONE)
    def test_budget_noncompensatory(self): self.assertEqual(self.use(observation=replace(self.obs,hydration_bytes=1001))[0],nav.RouteUseDisposition.HOLD_BUDGET)

if __name__ == '__main__': unittest.main()
