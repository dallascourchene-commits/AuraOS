from hashlib import sha256
from pathlib import Path
import json
import subprocess
import sys
import unittest
from tools.arena.k27_memory_navigator.demand_lease_handoff import DemandCellLease,DemandCellState
from tools.arena.k27_memory_navigator.envelope_bound_horizon import ConsequenceWorld,PossibilityEnvelope,EnvelopeCompletenessReceipt,EnvelopeVerificationContext,HorizonDisposition,issue_horizon_certificate,admit_horizon_certificate

def r(x): return sha256(x.encode()).hexdigest()
def lease(revision=4): return DemandCellLease('cell-11',revision,r('cfg'),8,17,'worker',100)
def cell(revision=4): return DemandCellState('cell-11',revision,r('cfg'),8,17,17)
def w(tag='a',**kw):
 v=dict(support_closure_root=r('support-closure'),reproof_closure_root=r('reproof-closure'),authority_projection_root=r('authority'),support_identity_root=r('support-id'),transition_signature_root=r('transition-h3'),irrelevant_config_root=r('irrelevant-'+tag)); v.update(kw); return ConsequenceWorld(**v)
def env(*ws,generation=5): return PossibilityEnvelope(tuple(ws),generation)
def ev(e,valid=True,verifier=None):
 a=r('envelope-authority'); vr=verifier or r('envelope-verifier'); return EnvelopeCompletenessReceipt(e.consequence_envelope_root() if valid else r('wrong'),e.completeness_generation,a,vr),EnvelopeVerificationContext(a,r('envelope-verifier'))
class T(unittest.TestCase):
 def setUp(self): self.e=env(w('a'),w('b')); rec,ctx=ev(self.e); d,self.c=issue_horizon_certificate(lease(),cell(),self.e,rec,ctx,current_support_identity_root=r('support-id'),observation_epoch=9,horizon=3,now=50); self.assertIs(d.disposition,HorizonDisposition.READY_D0)
 def admit(self,e=None,*,rec=None,ctx=None,l=None,c=None,support=None,obs=9,horizon=3,now=50):
  e=e or self.e; default_rec,default_ctx=ev(e); return admit_horizon_certificate(self.c,l or lease(),c or cell(),e,rec or default_rec,ctx or default_ctx,current_support_identity_root=support or r('support-id'),observation_epoch=obs,horizon=horizon,now=now)
 def test_exact_reuse_ready(self): self.assertIs(self.admit().disposition,HorizonDisposition.READY_D0)
 def test_same_epoch_support_but_new_possible_consequence_rebinds(self): self.assertIs(self.admit(env(w('a'),w('x',support_closure_root=r('different')))).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_transition_divergence_rebinds(self): self.assertIs(self.admit(env(w('a'),w('x',transition_signature_root=r('different-transition')))).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_authority_divergence_rebinds(self): self.assertIs(self.admit(env(w('a'),w('x',authority_projection_root=r('different-authority')))).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_same_generation_support_identity_swap_cannot_reuse(self): self.assertIs(self.admit(env(w('a'),w('x',support_identity_root=r('other-support')))).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_completeness_generation_move_rebinds(self): self.assertIs(self.admit(env(w('a'),w('b'),generation=6)).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_forged_completeness_receipt_holds(self): rec,ctx=ev(self.e,valid=False); self.assertIs(self.admit(rec=rec,ctx=ctx).disposition,HorizonDisposition.HOLD)
 def test_stale_completeness_verifier_holds(self): rec,ctx=ev(self.e,verifier=r('stale')); self.assertIs(self.admit(rec=rec,ctx=ctx).disposition,HorizonDisposition.HOLD)
 def test_observation_move_rebinds(self): self.assertIs(self.admit(obs=10).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_lease_move_rebinds(self): self.assertIs(self.admit(l=lease(5)).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_expired_lease_cannot_be_rescued_by_envelope_certificate(self): self.assertIs(self.admit(now=100).disposition,HorizonDisposition.HOLD)
 def test_cell_revision_move_cannot_be_rescued_by_envelope_certificate(self): self.assertIs(self.admit(c=cell(5)).disposition,HorizonDisposition.REBIND_REQUIRED)
 def test_uninstalled_fence_cannot_be_rescued_by_envelope_certificate(self):
  stale=DemandCellState('cell-11',4,r('cfg'),8,17,16); self.assertIs(self.admit(c=stale).disposition,HorizonDisposition.HOLD)
 def test_irrelevant_hidden_config_is_quotiented(self): self.assertIs(self.admit(env(w('c',irrelevant_config_root=r('fresh1')),w('d',irrelevant_config_root=r('fresh2')))).disposition,HorizonDisposition.READY_D0)
 def test_extra_equivalent_world_does_not_force_full_reconstruction(self): self.assertIs(self.admit(env(w('a'),w('b'),w('c'))).disposition,HorizonDisposition.READY_D0)
 def test_issue_divergent_envelope_holds(self): e=env(w('a'),w('x',reproof_closure_root=r('different'))); rec,ctx=ev(e); d,c=issue_horizon_certificate(lease(),cell(),e,rec,ctx,current_support_identity_root=r('support-id'),observation_epoch=9,horizon=3,now=50); self.assertIs(d.disposition,HorizonDisposition.HOLD); self.assertIsNone(c)
 def test_issue_requires_completeness_evidence(self): rec,ctx=ev(self.e,valid=False); d,c=issue_horizon_certificate(lease(),cell(),self.e,rec,ctx,current_support_identity_root=r('support-id'),observation_epoch=9,horizon=3,now=50); self.assertIs(d.disposition,HorizonDisposition.HOLD); self.assertIsNone(c)
 def test_authority_ceiling_stays_false(self): d=self.admit(); self.assertFalse(d.authority_minted); self.assertFalse(d.effect_authority); self.assertFalse(d.gate10)
 def test_campaign_direct_script_entrypoint_runs(self):
  repo=Path(__file__).resolve().parents[1]; script=repo/'tools'/'arena'/'k27_memory_navigator'/'campaign_envelope_bound_horizon.py'; completed=subprocess.run([sys.executable,str(script)],cwd=repo,capture_output=True,text=True,check=True); payload=json.loads(completed.stdout); self.assertEqual(payload['compiler_false_ready'],0); self.assertEqual(payload['compiler_false_hold'],0); self.assertEqual(payload['unsupported_completeness_false_ready'],0)
if __name__=='__main__': unittest.main()
