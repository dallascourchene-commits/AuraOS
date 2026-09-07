import sys, unittest
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_dynamic_navigator import K27DynamicNavigator, NegativeRouteScar
from k27_reflexive_telemetry import ProbeTransition, ReflexiveTelemetryGate
from k27_invariant_route_cut import SupportHyperedge,SupportBeliefState,compile_invariant_route_cut
from memory_city_navigator import SourceSpanLocator
from memory_city_support_hydration import compile_support_closed_hydration
@dataclass(frozen=True)
class B: object_id:str; revision_id:str; epoch:int; payload_sha256:str
class RT:
    def route_projection(self,o):return {'binding':{'revision_id':'r','epoch':1},'dependencies':{'B':'b'}}
    def invalidation_cone(self,o):return {'affected':[{'object_id':'B'}],'mutation_performed':False}
    def read(self,o):return B(o,'r',1,'p'),{'payload':{'x':1},'source_url':'u','source_version':'v'}
def loc(x,b=10):return SourceSpanLocator(x,sha256(('p'+x).encode()).hexdigest(),1,1,sha256(('s'+x).encode()).hexdigest(),b,())
class ConvergenceTests(unittest.TestCase):
    def test_dynamic_invalidation_remains_read_only(self):
        n=K27DynamicNavigator(RT()); n.register_route('r','A'); p=n.plan_invalidation('A'); self.assertEqual(p.affected_routes,('r',)); self.assertFalse(p.authority_minted)
    def test_reflexive_passive_state_change_holds(self):
        q=ProbeTransition('p','a','b','PASSIVE','c',True,True,True,'cx'); self.assertEqual(ReflexiveTelemetryGate().admit(q).status,'HOLD_UNDECLARED_PROBE_EFFECT')
    def test_support_closure_expands_direct_route(self):
        s=SupportBeliefState('x',(SupportHyperedge('i',frozenset({'A','B'})),),True,True); self.assertEqual(compile_invariant_route_cut(['A'],[s]).safe_support_cut,('A','B'))
    def test_support_closed_hydration_uses_pr874_spans(self):
        s=SupportBeliefState('x',(SupportHyperedge('i',frozenset({'A','B'})),),True,True); out=compile_support_closed_hydration(['A'],[s],{'A':loc('A'),'B':loc('B'),'Z':loc('Z')},max_hydration_bytes=100); self.assertEqual(out.status,'READY_SUPPORT_CLOSED_HYDRATION_D0'); self.assertEqual(out.selected_bytes,20)
    def test_support_ambiguity_blocks_span_hydration(self):
        a=SupportBeliefState('a',(SupportHyperedge('i',frozenset({'A','B'})),),True,True); b=SupportBeliefState('b',(SupportHyperedge('i',frozenset({'A','C'})),),True,True); out=compile_support_closed_hydration(['A'],[a,b],{'A':loc('A'),'B':loc('B'),'C':loc('C')},max_hydration_bytes=100); self.assertEqual(out.status,'HOLD_ROUTE_SUPPORT')
    def test_negative_scar_narrowing_reuses_nonauthoritatively(self):
        scar=NegativeRouteScar('s','r',{'budget':10},'h','e'); self.assertEqual(K27DynamicNavigator.classify_negative_scar(scar,{'budget':9},'h'),'REUSE_NEGATIVE')
if __name__=='__main__': unittest.main()
