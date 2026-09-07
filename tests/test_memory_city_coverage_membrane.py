import unittest
from hashlib import sha256
from tools.arena.memory_city_coverage_membrane import *

def r(s): return sha256(s.encode()).hexdigest()

class CoverageMembraneTests(unittest.TestCase):
    def base(self): return r('program'), r('domain'), 3, ('b0','b1','b2')
    def ready_cert(self):
        p,d,g,_=self.base(); return p,d,g,compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',),positive=(PositiveTrace('b0',p,d,g,r('t')),))
    def admission(self,c,**kw):
        return compile_proof_carrying_typed_admission(typed_closure_receipt_root=r('tc'),coverage=c,support_root=r('s'),influence_root=r('i'),transition_model_root=r('m'),future_congruence_root=kw.pop('future',None),horizon=kw.pop('horizon',0),**kw)
    def test_ready_mixed_positive_negative(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=o,
            positive=(PositiveTrace('b0',p,d,g,r('t0')), PositiveTrace('b2',p,d,g,r('t2'))), negative=(NegativeProof('b1',p,d,g,r('n1')),)); self.assertEqual(c.disposition,CoverageDisposition.READY)
    def test_unseen_branch_pending(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=o,positive=(PositiveTrace('b0',p,d,g,r('t0')),), negative=(NegativeProof('b1',p,d,g,r('n1')),)); self.assertEqual(c.pending,('b2',)); self.assertEqual(c.disposition,CoverageDisposition.HOLD_PENDING)
    def test_no_observation_not_completeness(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=o); self.assertEqual(c.disposition,CoverageDisposition.HOLD_PENDING)
    def test_stale_positive_holds(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',),positive=(PositiveTrace('b0',p,d,g,r('t'),current=False),)); self.assertEqual(c.disposition,CoverageDisposition.HOLD_STALE)
    def test_unsound_negative_holds(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',),negative=(NegativeProof('b0',p,d,g,r('n'),sound=False),)); self.assertEqual(c.disposition,CoverageDisposition.HOLD_STALE)
    def test_domain_move_invalidates(self):
        p,d,g,c=self.ready_cert(); u=validate_coverage_at_use(c,program_root=p,sealed_domain_root=r('wider'),generation=g); self.assertEqual(u.disposition,CoverageDisposition.HOLD_IDENTITY)
    def test_program_move_invalidates(self):
        p,d,g,c=self.ready_cert(); u=validate_coverage_at_use(c,program_root=r('p2'),sealed_domain_root=d,generation=g); self.assertEqual(u.disposition,CoverageDisposition.HOLD_IDENTITY)
    def test_generation_move_invalidates(self):
        p,d,g,c=self.ready_cert(); u=validate_coverage_at_use(c,program_root=p,sealed_domain_root=d,generation=g+1); self.assertEqual(u.disposition,CoverageDisposition.HOLD_IDENTITY)
    def test_conflicting_positive_negative_holds(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',),positive=(PositiveTrace('b0',p,d,g,r('t')),),negative=(NegativeProof('b0',p,d,g,r('n')),)); self.assertEqual(c.disposition,CoverageDisposition.HOLD_CONFLICT)
    def test_mutation_never_authorized(self):
        p,d,g,c=self.ready_cert(); u=validate_coverage_at_use(c,program_root=p,sealed_domain_root=d,generation=g,mutation_requested=True); self.assertEqual(u.disposition,CoverageDisposition.HOLD_MUTATION); self.assertFalse(u.mutation_authority)
    def test_read_admission_binds_coverage_receipt(self):
        p,d,g,c=self.ready_cert(); a=self.admission(c); self.assertEqual(a['disposition'],'READY_D0'); self.assertEqual(a['admission_mode'],'READ_ONLY'); self.assertEqual(a['coverage_receipt_root'],c.receipt_root)
    def test_effect_bound_always_routes_to_tecc(self):
        p,d,g,c=self.ready_cert(); a=self.admission(c,mode=AdmissionMode.EFFECT_BOUND); self.assertEqual(a['disposition'],'HOLD_TECC_REQUIRED_D0'); self.assertEqual(a['required_verifier_schema'],'AURA-TECC-v1')
    def test_effect_bound_never_mints_authority(self):
        p,d,g,c=self.ready_cert(); a=self.admission(c,mode=AdmissionMode.EFFECT_BOUND); self.assertFalse(a['authority_minted']); self.assertFalse(a['mutation_authority']); self.assertFalse(a['effect_authority']); self.assertFalse(a['gate10'])
    def test_read_ready_never_implies_effect_ready(self):
        p,d,g,c=self.ready_cert(); read=self.admission(c); effect=self.admission(c,mode=AdmissionMode.EFFECT_BOUND); self.assertEqual(read['disposition'],'READY_D0'); self.assertNotEqual(effect['disposition'],'READY_D0')
    def test_mode_changes_receipt_identity(self):
        p,d,g,c=self.ready_cert(); self.assertNotEqual(self.admission(c)['receipt_root'],self.admission(c,mode=AdmissionMode.EFFECT_BOUND)['receipt_root'])
    def test_raw_mode_string_rejected(self):
        p,d,g,c=self.ready_cert();
        with self.assertRaises(ValueError): self.admission(c,mode='EFFECT_BOUND')
    def test_horizon_requires_future_congruence_for_read(self):
        p,d,g,c=self.ready_cert(); a=self.admission(c,horizon=2); self.assertEqual(a['disposition'],'HOLD_D0')
    def test_horizon_with_future_allows_read_not_effect(self):
        p,d,g,c=self.ready_cert(); read=self.admission(c,horizon=2,future=r('fc')); effect=self.admission(c,horizon=2,future=r('fc'),mode=AdmissionMode.EFFECT_BOUND); self.assertEqual(read['disposition'],'READY_D0'); self.assertEqual(effect['disposition'],'HOLD_TECC_REQUIRED_D0')
    def test_pending_coverage_read_holds(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',)); self.assertEqual(self.admission(c)['disposition'],'HOLD_D0')
    def test_pending_coverage_effect_still_requires_tecc(self):
        p,d,g,o=self.base(); c=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',)); self.assertEqual(self.admission(c,mode=AdmissionMode.EFFECT_BOUND)['disposition'],'HOLD_TECC_REQUIRED_D0')
    def test_receipt_canonical_obligation_order(self):
        p,d,g,o=self.base(); ev=(PositiveTrace('b0',p,d,g,r('t0')), PositiveTrace('b1',p,d,g,r('t1'))); a=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b1','b0'),positive=ev); b=compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0','b1'),positive=ev[::-1]); self.assertEqual(a.receipt_root,b.receipt_root)
    def test_unknown_evidence_branch_rejected(self):
        p,d,g,o=self.base();
        with self.assertRaises(ValueError): compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0',),positive=(PositiveTrace('ghost',p,d,g,r('t')),))
    def test_duplicate_obligation_rejected(self):
        p,d,g,o=self.base();
        with self.assertRaises(ValueError): compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=('b0','b0'))
    def test_no_authority(self):
        p,d,g,c=self.ready_cert(); self.assertFalse(c.mutation_authority); self.assertFalse(c.gate10)

if __name__=='__main__': unittest.main()
