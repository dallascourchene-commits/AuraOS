import itertools, sys, unittest
from dataclasses import dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools'/'arena'))
from memory_city_horizon_fenced_handoff import *

R=lambda x:digest(x)
@dataclass(frozen=True)
class Cert:
    disposition:str='READY_D0'; support_root:str=R('s'); influence_root:str=R('i'); transition_model_root:str=R('t'); horizon:int=2; future_congruence_root:str|None=R('f'); receipt_root:str=R('receipt')
@dataclass(frozen=True)
class Use:
    disposition:str='READY_D0'; branch_id:str='b'; hydrate_item_ids:tuple=('A',); reproof_item_ids:tuple=('A','B')
def bundle(cert=None):
    c=cert or Cert(); u=Use(); sem=semantic_handoff_root(c); ev=SemanticHandoffEvidence(read_use_root(c,u),sem,R('owner'),R('verify'))
    m=MutationBoundaryProjection('cell',7,R('cfg'),11,19,19,'agent',100,sem,R('transition'),R('resource'))
    v=HandoffVerificationContext('cell',7,R('cfg'),11,19,19,R('owner'),R('verify'),R('transition'),R('resource'),10)
    return c,u,ev,m,v
class Tests(unittest.TestCase):
    def test_ready(self):
        self.assertEqual(compile_horizon_fenced_handoff(*bundle()).disposition,HandoffDisposition.READY_D0)
    def test_semantic_swap_rebinds(self):
        c,u,ev,m,v=bundle(); stale=Cert(support_root=R('old-s')); stale_sem=semantic_handoff_root(stale)
        m=MutationBoundaryProjection(m.cell_id,m.revision,m.configuration_root,m.support_epoch,m.fence_generation,m.installed_fence_generation,m.holder,m.expires_at,stale_sem,m.transition_authority_receipt_root,m.resource_fence_receipt_root)
        d=compile_horizon_fenced_handoff(c,u,ev,m,v); self.assertEqual((d.disposition,d.reason),(HandoffDisposition.REBIND_REQUIRED,'SEMANTIC_HANDOFF_MOVED'))
    def test_horizon_missing_cannot_form_semantic_root(self):
        c=Cert(future_congruence_root=None)
        with self.assertRaises(ValueError): semantic_handoff_root(c)
    def test_forged_semantic_evidence_holds(self):
        c,u,ev,m,v=bundle(); ev=SemanticHandoffEvidence(ev.read_use_root,R('forged'),ev.owner_evidence_root,ev.verifier_receipt_root)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).reason,'SEMANTIC_EVIDENCE_BINDING_MISMATCH')
    def test_owner_evidence_stale_holds(self):
        c,u,ev,m,v=bundle(); ev=SemanticHandoffEvidence(ev.read_use_root,ev.semantic_handoff_root,R('old-owner'),ev.verifier_receipt_root)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).reason,'OWNER_EVIDENCE_ROOT_STALE')
    def test_revision_move_rebinds(self):
        c,u,ev,m,v=bundle(); v=HandoffVerificationContext(v.cell_id,8,v.configuration_root,v.support_epoch,v.fence_generation,v.installed_fence_generation,v.owner_evidence_root,v.verifier_receipt_root,v.transition_authority_receipt_root,v.resource_fence_receipt_root,v.now)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).disposition,HandoffDisposition.REBIND_REQUIRED)
    def test_installed_fence_mismatch_holds(self):
        c,u,ev,m,v=bundle(); m=MutationBoundaryProjection(m.cell_id,m.revision,m.configuration_root,m.support_epoch,19,18,m.holder,m.expires_at,m.semantic_handoff_root,m.transition_authority_receipt_root,m.resource_fence_receipt_root)
        self.assertIn('FENCE',compile_horizon_fenced_handoff(c,u,ev,m,v).reason)
    def test_expired_holds(self):
        c,u,ev,m,v=bundle(); m=MutationBoundaryProjection(m.cell_id,m.revision,m.configuration_root,m.support_epoch,m.fence_generation,m.installed_fence_generation,m.holder,10,m.semantic_handoff_root,m.transition_authority_receipt_root,m.resource_fence_receipt_root)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).reason,'LEASE_EXPIRED')
    def test_context_noise_not_part_of_handoff(self):
        self.assertEqual(compile_horizon_fenced_handoff(*bundle()).disposition,HandoffDisposition.READY_D0)
    def test_13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5):
            self.assertEqual(hard13d_handoff((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')
if __name__=='__main__': unittest.main()
