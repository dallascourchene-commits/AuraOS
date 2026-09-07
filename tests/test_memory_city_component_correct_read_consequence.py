import sys,unittest
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_navigator import SourceSpanLocator
from memory_city_contingent_hydration import HydrationItem,DemandBranch,InvariantSupport
from memory_city_typed_closure import InfluenceGraph,compile_typed_closure,directed_descendants
from memory_city_support_hydration import SupportClosedHydration
from memory_city_coverage_membrane import PositiveTrace,compile_coverage_certificate
from memory_city_read_consequence import ReadWorldBinding,compile_read_consequence_certificate

def hx(s): return sha256(s.encode()).hexdigest()
def loc(n): return SourceSpanLocator(n,hx('p'+n),1,1,hx('s'+n),5,())
def item(n): return HydrationItem(n,loc(n),1)
def support_hydration(root,receipt,cut=('A','B')): return SupportClosedHydration('READY_SUPPORT_CLOSED_HYDRATION_D0',cut,(),10,30,1/3,'plan-'+receipt,receipt,False,False,root)
def cert_for(worlds):
    p,d,g=hx('program'),hx('domain'),7
    bindings=tuple(w.binding_root for w in worlds)
    pos=tuple(PositiveTrace(b,p,d,g,hx('trace-'+b),True,True) for b in bindings)
    cov=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=bindings,positive=pos)
    return compile_read_consequence_certificate(tuple(worlds),cov)

class ComponentCorrectReadTests(unittest.TestCase):
    def compile_world(self,support,receipt):
        items=tuple(item(x) for x in 'ABCDEF'); branches=(DemandBranch('r',('A',)),); influence=InfluenceGraph(1,(('A','C'),))
        typed=compile_typed_closure(items,branches,support,influence,changed_evidence_item_ids=('A',),max_resident_bytes=30,reveal_tick=0,deadline_tick=6,transition_model_root='T')
        h=support_hydration(support.support_root,receipt)
        return ReadWorldBinding(h,typed)
    def test_legacy_same_reproof_but_component_different_holds(self):
        s1=InvariantSupport(1,(('A','B'),)); s2=InvariantSupport(1,(('A','B'),('C','D')))
        w1=self.compile_world(s1,'h1'); w2=self.compile_world(s2,'h2')
        self.assertEqual(directed_descendants(('A',),InfluenceGraph(1,(('A','C'),)),tuple('ABCDEF')),('A','C'))
        self.assertEqual(w1.typed_closure.reproof_item_ids,('A','B','C'))
        self.assertEqual(w2.typed_closure.reproof_item_ids,('A','B','C','D'))
        c=cert_for((w1,w2)); self.assertEqual(c.status,'HOLD_D0'); self.assertEqual(c.reason,'reproof_consequence_diverged')
    def test_irrelevant_hidden_support_can_still_quotient(self):
        s1=InvariantSupport(1,(('A','B'),)); s2=InvariantSupport(1,(('A','B'),('E','F')))
        w1=self.compile_world(s1,'h1'); w2=self.compile_world(s2,'h2')
        self.assertNotEqual(w1.hydration.support_root,w2.hydration.support_root)
        self.assertEqual(w1.typed_closure.reproof_item_ids,w2.typed_closure.reproof_item_ids)
        self.assertEqual(cert_for((w1,w2)).status,'READY_D0')
    def test_no_authority_widening(self):
        s=InvariantSupport(1,(('A','B'),)); w=self.compile_world(s,'h1'); c=cert_for((w,))
        self.assertFalse(c.mutation_authority); self.assertFalse(c.effect_authority); self.assertFalse(c.gate10)
if __name__=='__main__': unittest.main()
