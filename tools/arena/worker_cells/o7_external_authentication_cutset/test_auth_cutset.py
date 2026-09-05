import unittest
from dataclasses import replace
from auth_cutset import *
from campaign import run,oracle_cover

class T(unittest.TestCase):
  def test_exact_parents(self): self.assertTrue(all(p.exact() for p in default_parents()))
  def test_all_observed_holds(self):
    p=compile_plan(default_parents(),make_auth()); self.assertEqual(p.decision,Decision.HOLD_AUTHENTICATION_CUTSET); self.assertEqual(set(p.missing_subjects),set(SUBJECTS))
  def test_minimum_cover_all_is_two(self): self.assertEqual(len(minimum_cover(SUBJECTS,bundle_catalog())),2)
  def test_cover_matches_independent_oracle(self):
    for r in range(5):
      for need in itertools.combinations(SUBJECTS,r): self.assertEqual(minimum_cover(need,bundle_catalog()),oracle_cover(need,bundle_catalog()))
  def test_full_attested_is_only_readjudication_eligible(self):
    p=compile_plan(default_parents(),make_auth({s:ProviderState.ATTESTED for s in SUBJECTS})); self.assertEqual(p.decision,Decision.ELIGIBLE_FOR_FRESH_READJUDICATION); self.assertTrue(p.verify())
  def test_stale_local_precedes_auth(self):
    ps=list(default_parents()); ps[0]=replace(ps[0],generation='0'*40); p=compile_plan(ps,make_auth({s:ProviderState.ATTESTED for s in SUBJECTS})); self.assertEqual(p.decision,Decision.REPROVE_LOCAL_FIRST)
  def test_projection_drift_precedes_auth(self):
    ps=list(default_parents()); ps[1]=replace(ps[1],projection_root='0'*64); self.assertEqual(compile_plan(ps,make_auth()).decision,Decision.REPROVE_LOCAL_FIRST)
  def test_graph_drift_precedes_auth(self):
    ps=list(default_parents()); ps[1]=replace(ps[1],graph_root='0'*64); self.assertEqual(compile_plan(ps,make_auth()).decision,Decision.REPROVE_LOCAL_FIRST)
  def test_source_unbound_precedes_auth(self):
    ps=list(default_parents()); ps[0]=replace(ps[0],source_bound=False); self.assertEqual(compile_plan(ps,make_auth()).decision,Decision.REPROVE_LOCAL_FIRST)
  def test_effect_authority_fails_exact(self):
    ps=list(default_parents()); ps[0]=replace(ps[0],effect_authority=True); self.assertEqual(compile_plan(ps,make_auth()).decision,Decision.REPROVE_LOCAL_FIRST)
  def test_attested_requires_receipt(self):
    a=SubjectAuth(SUBJECTS[0],ProviderState.ATTESTED,'a'*64,'OBS_GEN_0',None)
    with self.assertRaises(CutsetError): a.validate()
  def test_bool_ambiguity_fails(self):
    p=replace(default_parents()[0],source_bound=1)
    with self.assertRaises(CutsetError): p.validate()
  def test_auth_surface_complete(self):
    a=make_auth(); a.pop(SUBJECTS[0])
    with self.assertRaises(CutsetError): compile_plan(default_parents(),a)
  def test_wrong_parent_pair(self):
    ps=list(default_parents()); ps[0]=replace(ps[0],owner='OTHER')
    with self.assertRaises(CutsetError): compile_plan(ps,make_auth())
  def test_duplicate_parent_owner(self):
    ps=[default_parents()[0],default_parents()[0]]
    with self.assertRaises(CutsetError): compile_plan(ps,make_auth())
  def test_plan_receipt_tamper(self):
    p=compile_plan(default_parents(),make_auth()); self.assertTrue(p.verify()); self.assertFalse(replace(p,receipt_root='0'*64).verify())
  def test_bundle_duplicate_rejected(self):
    with self.assertRaises(CutsetError): AttestationBundle('X',(SUBJECTS[0],SUBJECTS[0]),'P').normalized()
  def test_bundle_unknown_subject_rejected(self):
    with self.assertRaises(CutsetError): AttestationBundle('X',('UNKNOWN',),'P').normalized()
  def test_observed_not_attested(self): self.assertIsNot(ProviderState.OBSERVED,ProviderState.ATTESTED)
  def test_campaign(self):
    r=run(1000); self.assertEqual(r['oracle_mismatches'],0); self.assertEqual(r['false_auth_admissions'],0); self.assertEqual(r['hs1000_false_admissions'],0); self.assertEqual(r['omega8_keepers'],1); self.assertEqual(r['tail13d_hard_invalid_repairs'],0)

if __name__=='__main__': unittest.main()
