import itertools, os, sys, unittest
from dataclasses import replace
HERE=os.path.dirname(__file__);sys.path.insert(0,HERE)
from generation_aware_security_reproof import *

def roots(v=1):return tuple((k,digest({'k':k,'v':v})) for k in SEMANTIC_FIELDS)
def surface(gen='1'*40,**kw):
    d=dict(generation=gen,schema_root=digest({'schema':1}),admission_surface_root=digest({'surface':1}),verifier_generation='2'*40,semantic_roots=roots(),provider_attested=True,current=True,complete=True)
    d.update(kw);return GenerationSurface(**d)
class T(unittest.TestCase):
    def test_exact(self):
        r=classify(surface(),surface());self.assertEqual(r.decision,Decision.REUSE_EXACT);self.assertEqual(r.change_class,ChangeClass.EXACT_UNCHANGED);self.assertTrue(r.verify())
    def test_neutral_generation(self):
        r=classify(surface(),surface('3'*40));self.assertEqual(r.change_class,ChangeClass.PROOF_NEUTRAL);self.assertEqual(r.decision,Decision.REUSE_EXACT)
    def test_model_change_cone(self):
        old=surface(); rr=dict(old.roots());rr['model_root']=digest({'new':1});cur=replace(surface('3'*40),semantic_roots=tuple(rr.items()))
        r=classify(old,cur);self.assertEqual(r.decision,Decision.REPROVE_CONE);self.assertIn('SECURE_ENTRYPOINT',r.recompute_order);self.assertIn('TRACE_PROVENANCE',r.reusable)
    def test_trace_change_narrow(self):
        old=surface();rr=dict(old.roots());rr['trace_root']=digest({'new':1});r=classify(old,replace(surface('3'*40),semantic_roots=tuple(rr.items())))
        self.assertEqual(set(r.recompute_order),{'TRACE_PROVENANCE','TRACE_WORKLOAD_REUSE','FINAL_REUSE_RECEIPT'})
    def test_surface_change_unknown(self):
        r=classify(surface(),replace(surface('3'*40),admission_surface_root=digest({'other':1})));self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_schema_change_unknown(self):
        r=classify(surface(),replace(surface('3'*40),schema_root=digest({'other':1})));self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_verifier_change_unknown(self):
        r=classify(surface(),replace(surface('3'*40),verifier_generation='4'*40));self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_provider_missing_hold(self):self.assertEqual(classify(surface(),replace(surface('3'*40),provider_attested=False)).decision,Decision.HOLD_UNKNOWN)
    def test_stale_hold(self):self.assertEqual(classify(surface(),replace(surface('3'*40),current=False)).decision,Decision.HOLD_UNKNOWN)
    def test_incomplete_hold(self):self.assertEqual(classify(surface(),replace(surface('3'*40),complete=False)).decision,Decision.HOLD_UNKNOWN)
    def test_authority_hold(self):self.assertEqual(classify(surface(),replace(surface('3'*40),gate10=True)).decision,Decision.HOLD_UNKNOWN)
    def test_missing_field_fails(self):self.assertRaises(ReproofError,GenerationSurface('1'*40,digest(1),digest(2),'2'*40,roots()[:-1],True,True,True).normalized)
    def test_bool_identity_fails(self):self.assertRaises(ReproofError,sid,True)
    def test_receipt_tamper(self):
        r=classify(surface(),surface());self.assertFalse(replace(r,receipt_root='0'*64).verify())
    def test_model_and_package_union(self):
        old=surface();rr=dict(old.roots());rr['model_root']=digest('m');rr['package_root']=digest('p');r=classify(old,replace(surface('3'*40),semantic_roots=tuple(rr.items())));self.assertIn('REMOTE_CODE_POLICY',r.recompute_order);self.assertIn('SAFETENSORS_STRUCTURE',r.recompute_order)
    def test_omega8(self):self.assertEqual(sum(crystalline_admission(s) for s in itertools.product(range(3),repeat=8)),1)
    def test_13d_nonrepair(self):
        for t in itertools.product(range(3),repeat=5):self.assertFalse(admission_13d((0,2,2,2,2,2,2,2)+t))
    def test_context_cannot_change_class(self):
        r=classify(surface(),replace(surface('3'*40),provider_attested=False));self.assertEqual(r.decision,Decision.HOLD_UNKNOWN)
    def test_provider_attestation_not_truth_authority(self):
        r=classify(surface(),surface());self.assertFalse(r.truth_authority);self.assertTrue(r.provider_status_separate)
    def test_order_invariant_roots(self):
        s=surface();self.assertEqual(surface_root(s),surface_root(replace(s,semantic_roots=tuple(reversed(s.semantic_roots)))))
if __name__=='__main__':unittest.main()
