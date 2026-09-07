import itertools,unittest,sys
from pathlib import Path
HERE=Path(__file__).resolve(); ROOT=HERE.parents[1]; ARENA=ROOT/'tools'/'arena'
sys.path.insert(0,str(ARENA if ARENA.exists() else HERE.parent))
from dataclasses import dataclass
from memory_city_consequence_refinement import *
R=lambda x:digest(x)
@dataclass(frozen=True)
class ReadCert:
    status:str='READY_D0';coverage_receipt_root:str=R('coverage');program_root:str=R('program');sealed_domain_root:str=R('domain');coverage_generation:int=7;binding_roots:tuple=(R('b1'),R('b2'));transition_model_root:str=R('transition');horizon:int=2;future_congruence_root:str|None=R('future');consequence_root:str=R('consequence');receipt_root:str=R('receipt')
I=EffectIntent(R('intent'),R('effect-domain'),R('program'))
def p(binding,obl='o',auth=True,current=True,cfg=None,evidence='e'):
    return EffectObligationProjection(binding,None if obl is None else R(obl),None if obl is None else R([evidence,binding]),auth,current,R(cfg or ['cfg',binding]))
class T(unittest.TestCase):
    def test_uniform_effect_obligation_refines_one_child(self):
        c=ReadCert();ps=(p(c.binding_roots[0],cfg='a'),p(c.binding_roots[1],cfg='b'));plan=compile_effect_refinement(ps,c,I)
        self.assertEqual((plan.status,len(plan.subclasses),plan.unresolved_binding_roots),('READY_REFINED_D0',1,()));self.assertTrue(refinement_invariants(c,plan))
    def test_obligation_divergence_splits(self):
        c=ReadCert();plan=compile_effect_refinement((p(c.binding_roots[0],'a'),p(c.binding_roots[1],'b')),c,I);self.assertEqual(len(plan.subclasses),2)
    def test_forged_evidence_quarantined(self):
        c=ReadCert();plan=compile_effect_refinement((p(c.binding_roots[0],auth=False),p(c.binding_roots[1])),c,I);self.assertIn(c.binding_roots[0],plan.unresolved_binding_roots)
    def test_stale_evidence_quarantined(self):
        c=ReadCert();plan=compile_effect_refinement((p(c.binding_roots[0],current=False),p(c.binding_roots[1])),c,I);self.assertIn(c.binding_roots[0],plan.unresolved_binding_roots)
    def test_detached_binding_envelope_holds(self):
        c=ReadCert();bad=R('detached');plan=compile_effect_refinement((p(bad),p(c.binding_roots[1])),c,I);self.assertEqual(plan.status,'HOLD_BINDING_ENVELOPE_D0')
    def test_duplicate_binding_envelope_holds(self):
        c=ReadCert();plan=compile_effect_refinement((p(c.binding_roots[0]),p(c.binding_roots[0])),c,I);self.assertEqual(plan.status,'HOLD_BINDING_ENVELOPE_D0')
    def test_read_certificate_move_invalidates(self):
        c=ReadCert();plan=compile_effect_refinement(tuple(p(x) for x in c.binding_roots),c,I);c2=ReadCert(coverage_generation=8,receipt_root=R('receipt2'));self.assertEqual(validate_effect_binding(plan,cert=c2,intent=I,read_binding_root=c.binding_roots[0],obligation_root=R('o')),'HOLD_READ_CERTIFICATE_MOVED')
    def test_intent_move_invalidates(self):
        c=ReadCert();plan=compile_effect_refinement(tuple(p(x) for x in c.binding_roots),c,I);i2=EffectIntent(I.intent_root,R('other-domain'),I.program_root);self.assertEqual(validate_effect_binding(plan,cert=c,intent=i2,read_binding_root=c.binding_roots[0],obligation_root=R('o')),'HOLD_EFFECT_INTENT_MOVED')
    def test_no_authority_minted(self):
        c=ReadCert();plan=compile_effect_refinement(tuple(p(x) for x in c.binding_roots),c,I);self.assertFalse(plan.effect_authority);self.assertFalse(plan.subclasses[0].effect_authority);self.assertEqual(len(effect_escalation_root(plan,plan.subclasses[0])),64)
    def test_13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5):self.assertEqual(hard13d_refinement((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')
if __name__=='__main__':unittest.main()
