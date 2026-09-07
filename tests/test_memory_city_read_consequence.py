import sys,unittest
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_support_hydration import SupportClosedHydration
from memory_city_adaptive_hydration import SupportFixedPoint,compile_adaptive_hydration_strategy
from memory_city_typed_closure import TypedClosureCertificate,TypedClosureDisposition,REPROOF_SEMANTICS
from memory_city_coverage_membrane import PositiveTrace,compile_coverage_certificate
from memory_city_read_consequence import ReadWorldBinding,compile_read_consequence_certificate,validate_read_consequence_at_use

def hx(s):return sha256(s.encode()).hexdigest()
def h(root,receipt,cut=('A','B')):return SupportClosedHydration('READY_SUPPORT_CLOSED_HYDRATION_D0',cut,(),20,100,.2,'p',receipt,False,False,root)
def t(receipt,reproof=('C',),transition='T',horizon=0,future=None,semantics=REPROOF_SEMANTICS):return TypedClosureCertificate(TypedClosureDisposition.READY,None,hx('typed-'+receipt),hx('infl-'+receipt),reproof,horizon,transition,future,receipt,reproof_semantics=semantics)
def ready_cert(world_pairs,program=hx('program'),domain=hx('domain'),generation=7):
    worlds=tuple(ReadWorldBinding(*pair) for pair in world_pairs);obligations=tuple(w.binding_root for w in worlds)
    positive=tuple(PositiveTrace(root,program,domain,generation,hx('trace-'+root),True,True) for root in obligations)
    coverage=compile_coverage_certificate(program_root=program,sealed_domain_root=domain,generation=generation,obligations=obligations,positive=positive)
    return worlds,coverage,compile_read_consequence_certificate(worlds,coverage)
class ReadConsequenceTests(unittest.TestCase):
    def test_distinct_roots_same_read_consequence_ready(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));self.assertEqual(cert.status,'READY_D0');self.assertEqual(set(cert.member_support_roots),{'rA','rB'})
    def test_adaptive_read_accepts_certified_cross_root(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));x=compile_adaptive_hydration_strategy(worlds[0].hydration,SupportFixedPoint('rB',True,True,1),expected_uses=2,shared_global_available=False,read_certificate=cert,read_coverage=cov,read_typed_closure=worlds[0].typed_closure,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(x.status,'READY_ADAPTIVE_D0')
    def test_cross_root_requires_active_typed_closure(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));x=compile_adaptive_hydration_strategy(worlds[0].hydration,SupportFixedPoint('rB',True,True,1),expected_uses=2,shared_global_available=False,read_certificate=cert,read_coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(x.status,'HOLD_READ_TYPED_CLOSURE_REQUIRED')
    def test_without_certificate_cross_root_holds(self):
        x=compile_adaptive_hydration_strategy(h('rA','hA'),SupportFixedPoint('rB',True,True,1),expected_uses=2,shared_global_available=False);self.assertEqual(x.status,'HOLD_SUPPORT_IDENTITY_MISMATCH')
    def test_legacy_reproof_semantics_hold_at_compile(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA',semantics='')),(h('rB','hB'),t('tB'))));self.assertEqual(cert.status,'HOLD_D0');self.assertEqual(cert.reason,'typed_reproof_semantics_not_current')
    def test_legacy_reproof_semantics_hold_at_use(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));legacy=t('tA',semantics='');d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=legacy,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(d.status,'HOLD_REPROOF_SEMANTICS')
    def test_reproof_divergence_holds(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA',('C',))),(h('rB','hB'),t('tB',('D',)))));self.assertEqual(cert.status,'HOLD_D0')
    def test_hydration_divergence_holds(self):
        worlds,cov,cert=ready_cert(((h('rA','hA',('A','B')),t('tA')),(h('rB','hB',('A','C')),t('tB'))));self.assertEqual(cert.status,'HOLD_D0')
    def test_transition_divergence_holds(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA',transition='T1')),(h('rB','hB'),t('tB',transition='T2'))));self.assertEqual(cert.status,'HOLD_D0')
    def test_incomplete_binding_coverage_holds(self):
        worlds=tuple(ReadWorldBinding(*p) for p in ((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));ob=(worlds[0].binding_root,);pos=(PositiveTrace(ob[0],hx('program'),hx('domain'),7,hx('trace'),True,True),);cov=compile_coverage_certificate(program_root=hx('program'),sealed_domain_root=hx('domain'),generation=7,obligations=ob,positive=pos);self.assertEqual(compile_read_consequence_certificate(worlds,cov).status,'HOLD_D0')
    def test_currentness_move_holds_at_use(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=worlds[0].typed_closure,fixed_support_root='rB',coverage=cov,current_program_root=hx('moved'),current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertNotEqual(d.status,'READY_D0')
    def test_unknown_active_world_holds(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));d=validate_read_consequence_at_use(cert,hydration=h('rC','hC'),typed_closure=worlds[0].typed_closure,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(d.status,'HOLD_ACTIVE_WORLD_MEMBERSHIP')
    def test_same_receipt_reproof_move_holds_at_use(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));m=t('tA',reproof=('Z',));d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=m,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(d.status,'HOLD_ACTIVE_WORLD_MEMBERSHIP')
    def test_same_receipt_transition_move_holds_at_use(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));m=t('tA',transition='MOVED');d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=m,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(d.status,'HOLD_ACTIVE_WORLD_MEMBERSHIP')
    def test_same_receipt_future_move_holds_at_use(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA',transition='T',horizon=1,future='F')),(h('rB','hB'),t('tB',transition='T',horizon=1,future='F'))));m=t('tA',transition='T',horizon=1,future='MOVED');d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=m,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation);self.assertEqual(d.status,'HOLD_ACTIVE_WORLD_MEMBERSHIP')
    def test_mutation_never_authorized(self):
        worlds,cov,cert=ready_cert(((h('rA','hA'),t('tA')),(h('rB','hB'),t('tB'))));d=validate_read_consequence_at_use(cert,hydration=worlds[0].hydration,typed_closure=worlds[0].typed_closure,fixed_support_root='rB',coverage=cov,current_program_root=cov.program_root,current_sealed_domain_root=cov.sealed_domain_root,current_coverage_generation=cov.generation,mutation_requested=True);self.assertEqual(d.status,'HOLD_MUTATION_AUTHORITY');self.assertFalse(d.mutation_authority);self.assertFalse(d.effect_authority);self.assertFalse(d.gate10)
if __name__=='__main__':unittest.main()
