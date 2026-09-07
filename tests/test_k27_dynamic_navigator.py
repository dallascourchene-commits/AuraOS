import sys, unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'arena'))

from k27_dynamic_navigator import (
    EffectIntent, K27DynamicNavigator, LawField, NegativeRouteScar,
    TrafficEvent, summarize_traffic,
)


@dataclass(frozen=True)
class Binding:
    object_id: str
    revision_id: str
    epoch: int
    payload_sha256: str


class FakeRuntime:
    def __init__(self):
        self.records = {
            'MCXR-A': (Binding('MCXR-A','rev-a',2,'pa'), {'payload': {'route':['A','B','C']}, 'source_url':'drive://route-a', 'source_version':'v2'}),
            'SRC-B': (Binding('SRC-B','rev-b',3,'pb'), {'payload': {'fact':'b'}, 'source_url':'drive://b', 'source_version':'v3'}),
            'SRC-C': (Binding('SRC-C','rev-c',4,'pc'), {'payload': {'fact':'c'}, 'source_url':'github://c', 'source_version':'sha-c'}),
            'MCXR-D': (Binding('MCXR-D','rev-d',1,'pd'), {'payload': {'route':['D','E']}, 'source_url':'drive://route-d', 'source_version':'v1'}),
            'SRC-E': (Binding('SRC-E','rev-e',1,'pe'), {'payload': {'fact':'e'}, 'source_url':'drive://e', 'source_version':'v1'}),
        }
    def read(self, object_id):
        return self.records[object_id]
    def route_projection(self, object_id):
        binding, record = self.records[object_id]
        deps = {'SRC-B':'rev-b','SRC-C':'rev-c'} if object_id == 'MCXR-A' else {'SRC-E':'rev-e'}
        return {
            'binding': {'object_id':binding.object_id,'revision_id':binding.revision_id,'epoch':binding.epoch},
            'payload': record['payload'], 'dependencies': deps,
            'execution_authority': False, 'gate10': False,
        }
    def invalidation_cone(self, object_id):
        affected = {'SRC-B':['SRC-C'], 'SRC-E':[], 'MCXR-A':['SRC-B','SRC-C']}.get(object_id, [])
        return {'root_object_id':object_id,'affected':[{'object_id':x} for x in affected],
                'mutation_performed':False,'authority_minted':False}


class DynamicNavigatorTests(unittest.TestCase):
    def test_route_delta_consumes_owned_projection_and_cone(self):
        nav=K27DynamicNavigator(FakeRuntime())
        a=nav.register_route('route-a','MCXR-A'); d=nav.register_route('route-d','MCXR-D')
        self.assertEqual(a.dependencies,('MCXR-A','SRC-B','SRC-C'))
        self.assertEqual(d.dependencies,('MCXR-D','SRC-E'))
        plan=nav.plan_invalidation('SRC-B')
        self.assertEqual(plan.affected_routes,('route-a',)); self.assertEqual(plan.reusable_routes,('route-d',))
        self.assertFalse(plan.mutation_performed); self.assertFalse(plan.authority_minted); self.assertFalse(plan.gate10)

    def test_cone_descendants_also_invalidate_route(self):
        nav=K27DynamicNavigator(FakeRuntime()); nav.register_route('route-a','MCXR-A')
        plan=nav.plan_invalidation('MCXR-A')
        self.assertEqual(plan.affected_routes,('route-a',)); self.assertIn('SRC-C',plan.cone)

    def test_effect_compiler_holds_on_first_local_information_gap(self):
        laws={
            'A':LawField('root',frozenset({'execute'}),frozenset({'source_current'}),True,100),
            'B':LawField('child',frozenset({'execute'}),frozenset({'owner_current'}),True,100),
        }
        out=K27DynamicNavigator.compile_effect(('A','B'),laws,{'A':{'source_current'},'B':set()},EffectIntent('fx','execute',False,1))
        self.assertEqual(out.status,'HOLD_INFORMATION_EDGE'); self.assertEqual(out.blocking_node,'B')
        self.assertEqual(out.missing_information,('owner_current',)); self.assertFalse(out.effect_authority)

    def test_effect_compiler_ready_still_nonauthorizing(self):
        laws={'A':LawField('root',frozenset({'execute'}),frozenset(),True,10)}
        out=K27DynamicNavigator.compile_effect(('A',),laws,{},EffectIntent('fx','execute',False,1))
        self.assertEqual(out.status,'READY_DISTRIBUTED_REALISABILITY_D0')
        self.assertFalse(out.effect_authority); self.assertFalse(out.gate10)

    def test_at_use_capsule_is_deep_copied_and_stable(self):
        rt=FakeRuntime(); nav=K27DynamicNavigator(rt)
        cap=nav.capture_at_use('SRC-B'); before=cap.capture_root
        rt.records['SRC-B'][1]['payload']['fact']='mutated'
        self.assertEqual(cap.exact_payload,{'fact':'b'}); self.assertEqual(cap.capture_root,before)

    def test_negative_scar_reuse_only_under_narrower_equal_envelope(self):
        scar=NegativeRouteScar('s','deadline',{'budget':10,'deadline_slack':5},'hard','e')
        self.assertEqual(K27DynamicNavigator.classify_negative_scar(scar,{'budget':8,'deadline_slack':4},'hard'),'REUSE_NEGATIVE')
        self.assertEqual(K27DynamicNavigator.classify_negative_scar(scar,{'budget':11,'deadline_slack':4},'hard'),'REPROVE_NEGATIVE')
        self.assertEqual(K27DynamicNavigator.classify_negative_scar(scar,{'budget':8,'deadline_slack':4},'other'),'REPROVE_NEGATIVE')

    def test_negative_scar_currentness_rebind_is_not_exact_reuse(self):
        scar=NegativeRouteScar('s','capability',{'capability_rank':3},'hard','e')
        out=K27DynamicNavigator.classify_negative_scar(scar,{'capability_rank':2},'hard',currentness_only_movement=True)
        self.assertEqual(out,'REBIND_NEGATIVE_CURRENTNESS')

    def test_positive_scar_never_gets_negative_reuse_privilege(self):
        scar=NegativeRouteScar('s','ready',{'budget':10},'hard','e',polarity='positive')
        self.assertEqual(K27DynamicNavigator.classify_negative_scar(scar,{'budget':1},'hard'),'RECHECK_POSITIVE_AT_USE')

    def test_traffic_summary_measures_hydration_levels(self):
        rows=[TrafficEvent('1','drive','search','d1','metadata','cut',100),TrafficEvent('2','drive','open','d1','exact','rev1',200),TrafficEvent('3','github','fetch','g1','exact','sha1',300)]
        s=summarize_traffic(rows)
        self.assertEqual((s.events,s.unique_locators,s.repeated_locator_hits),(3,2,1))
        self.assertEqual((s.metadata_events,s.exact_events,s.bytes_observed),(1,2,600))

    def test_duplicate_telemetry_ids_fail_closed(self):
        row=TrafficEvent('1','drive','search','d1','metadata','cut')
        with self.assertRaises(ValueError): summarize_traffic([row,row])

    def test_invalid_hydration_level_fails_closed(self):
        with self.assertRaises(ValueError): summarize_traffic([TrafficEvent('1','drive','x','d','deep','cut')])

    def test_route_registration_projection_root_is_deterministic(self):
        self.assertEqual(K27DynamicNavigator(FakeRuntime()).register_route('r','MCXR-A').projection_root,K27DynamicNavigator(FakeRuntime()).register_route('r','MCXR-A').projection_root)


if __name__ == '__main__': unittest.main()
