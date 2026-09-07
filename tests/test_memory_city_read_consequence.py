import sys, unittest
from pathlib import Path
from hashlib import sha256
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_coverage_membrane import *
from memory_city_read_consequence import *

def r(s): return sha256(s.encode()).hexdigest()

def cov(pos=('w0','w1'), neg=()):
    p,d,g=r('program'),r('domain'),7
    obligations=tuple(pos)+tuple(neg)
    return compile_coverage_certificate(program_root=p,sealed_domain_root=d,generation=g,obligations=obligations,
        positive=tuple(PositiveTrace(x,p,d,g,r('trace-'+x)) for x in pos),
        negative=tuple(NegativeProof(x,p,d,g,r('neg-'+x)) for x in neg))

def wp(w, hyd=('a','b'), rep=('a','c'), trust='trust', current=True, k=()):
    return ReadWorldProjection(w,r('root-'+w),hyd,rep,r(trust),current,k)

class Tests(unittest.TestCase):
    def test_distinct_world_roots_same_consequence_ready(self):
        c=compile_read_consequence_certificate(coverage=cov(), projections=(wp('w0'),wp('w1')))
        self.assertEqual(c.disposition,ReadConsequenceDisposition.READY); self.assertNotEqual(c.member_world_roots[0],c.member_world_roots[1])
    def test_negative_unreachable_needs_no_projection(self):
        c=compile_read_consequence_certificate(coverage=cov(('w0',),('w1',)),projections=(wp('w0'),)); self.assertEqual(c.disposition,ReadConsequenceDisposition.READY)
    def test_missing_positive_projection_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0'),)); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_ENVELOPE)
    def test_extra_projection_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(('w0',)),projections=(wp('w0'),wp('w1'))); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_ENVELOPE)
    def test_hydration_divergence_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0'),wp('w1',hyd=('a',)))); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_CONSEQUENCE_DIVERGENCE)
    def test_reproof_divergence_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0'),wp('w1',rep=('a','d')))); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_CONSEQUENCE_DIVERGENCE)
    def test_trust_divergence_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0'),wp('w1',trust='other'))); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_TRUST_DIVERGENCE)
    def test_stale_world_holds(self):
        c=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0'),wp('w1',current=False))); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_STALE_WORLD)
    def test_k27_does_not_change_semantic_root(self):
        a=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0',k=(1,2)),wp('w1',k=(3,4))))
        b=compile_read_consequence_certificate(coverage=cov(),projections=(wp('w0',k=(9,9)),wp('w1',k=(8,8))))
        self.assertEqual(a.receipt_root,b.receipt_root)
    def test_active_member_ready(self):
        cv=cov(); c=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1')))
        u=validate_read_consequence_at_use(c,coverage=cv,active_world_id='w1',active_world_root=r('root-w1'),read_obligation_root=r('trust')); self.assertEqual(u.disposition,ReadConsequenceDisposition.READY)
    def test_unknown_member_holds(self):
        cv=cov(); c=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1')))
        u=validate_read_consequence_at_use(c,coverage=cv,active_world_id='w2',active_world_root=r('root-w2'),read_obligation_root=r('trust')); self.assertEqual(u.disposition,ReadConsequenceDisposition.HOLD_MEMBER)
    def test_trust_move_at_use_holds(self):
        cv=cov(); c=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1')))
        u=validate_read_consequence_at_use(c,coverage=cv,active_world_id='w0',active_world_root=r('root-w0'),read_obligation_root=r('moved')); self.assertEqual(u.disposition,ReadConsequenceDisposition.HOLD_TRUST_IDENTITY)
    def test_coverage_move_at_use_holds(self):
        cv=cov(); c=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1'))); moved=cov(('w0',),('w1',))
        u=validate_read_consequence_at_use(c,coverage=moved,active_world_id='w0',active_world_root=r('root-w0'),read_obligation_root=r('trust')); self.assertEqual(u.disposition,ReadConsequenceDisposition.HOLD_COVERAGE_IDENTITY)
    def test_mutation_always_holds(self):
        cv=cov(); c=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1')))
        u=validate_read_consequence_at_use(c,coverage=cv,active_world_id='w0',active_world_root=r('root-w0'),read_obligation_root=r('trust'),mutation_requested=True); self.assertEqual(u.disposition,ReadConsequenceDisposition.HOLD_MUTATION); self.assertFalse(u.mutation_authority)
    def test_projection_order_canonical(self):
        cv=cov(); a=compile_read_consequence_certificate(coverage=cv,projections=(wp('w0'),wp('w1'))); b=compile_read_consequence_certificate(coverage=cv,projections=(wp('w1'),wp('w0'))); self.assertEqual(a.receipt_root,b.receipt_root)
    def test_no_positive_world_holds(self):
        c=compile_read_consequence_certificate(coverage=cov((),('w0','w1')),projections=()); self.assertEqual(c.disposition,ReadConsequenceDisposition.HOLD_ENVELOPE)
if __name__=='__main__': unittest.main()
