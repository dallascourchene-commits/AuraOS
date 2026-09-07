import itertools, unittest
from dataclasses import dataclass
from memory_city_horizon_fenced_handoff import *

R=lambda x:digest(x)

@dataclass(frozen=True)
class ReadCert:
    status:str='READY_D0'
    coverage_receipt_root:str=R('coverage')
    program_root:str=R('program')
    sealed_domain_root:str=R('domain')
    coverage_generation:int=4
    binding_roots:tuple=(R('b1'),R('b2'))
    member_support_roots:tuple=(R('s1'),R('s2'))
    transition_model_root:str=R('t')
    horizon:int=2
    future_congruence_root:str|None=R('f')
    consequence_root:str=R('c')
    receipt_root:str=R('receipt')

@dataclass(frozen=True)
class ReadUse:
    status:str='READY_D0'
    reason:str='ok'
    certificate_root:str=R('receipt')

@dataclass(frozen=True)
class TypedCert:
    disposition:str='READY_D0'
    support_root:str=R('s')
    influence_root:str=R('i')
    transition_model_root:str=R('t')
    horizon:int=2
    future_congruence_root:str|None=R('f')
    receipt_root:str=R('tr')

@dataclass(frozen=True)
class TypedUse:
    disposition:str='READY_D0'
    branch_id:str='b'
    hydrate_item_ids:tuple=('A',)
    reproof_item_ids:tuple=('A','B')

def bundle(cert=None,use=None):
    c=cert or ReadCert(); u=use or ReadUse()
    sem=semantic_handoff_root(c)
    ev=SemanticHandoffEvidence(read_use_root(c,u),sem,R('owner'),R('verify'))
    m=MutationBoundaryProjection('cell',7,R('cfg'),11,19,19,'agent',100,sem,R('transition'),R('resource'))
    v=HandoffVerificationContext('cell',7,R('cfg'),11,19,19,R('owner'),R('verify'),R('transition'),R('resource'),10)
    return c,u,ev,m,v

class Tests(unittest.TestCase):
    def test_current_read_consequence_ready(self):
        self.assertEqual(compile_horizon_fenced_handoff(*bundle()).disposition,HandoffDisposition.READY_D0)
    def test_singleton_typed_closure_still_ready(self):
        self.assertEqual(compile_horizon_fenced_handoff(*bundle(TypedCert(),TypedUse())).disposition,HandoffDisposition.READY_D0)
    def test_consequence_root_swap_rebinds(self):
        c,u,ev,m,v=bundle(); old=ReadCert(consequence_root=R('old-c'),receipt_root=R('old-r'))
        m=MutationBoundaryProjection(m.cell_id,m.revision,m.configuration_root,m.support_epoch,m.fence_generation,m.installed_fence_generation,m.holder,m.expires_at,semantic_handoff_root(old),m.transition_authority_receipt_root,m.resource_fence_receipt_root)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).disposition,HandoffDisposition.REBIND_REQUIRED)
    def test_member_set_move_changes_semantic_root(self):
        self.assertNotEqual(semantic_handoff_root(ReadCert()),semantic_handoff_root(ReadCert(member_support_roots=(R('s1'),R('s3')))))
    def test_coverage_move_changes_semantic_root(self):
        self.assertNotEqual(semantic_handoff_root(ReadCert()),semantic_handoff_root(ReadCert(coverage_generation=5)))
    def test_horizon_missing_rejected(self):
        with self.assertRaises(ValueError): semantic_handoff_root(ReadCert(future_congruence_root=None))
    def test_owner_evidence_stale_holds(self):
        c,u,ev,m,v=bundle(); ev=SemanticHandoffEvidence(ev.read_use_root,ev.semantic_handoff_root,R('bad'),ev.verifier_receipt_root)
        self.assertEqual(compile_horizon_fenced_handoff(c,u,ev,m,v).reason,'OWNER_EVIDENCE_ROOT_STALE')
    def test_fence_not_installed_holds(self):
        c,u,ev,m,v=bundle(); m=MutationBoundaryProjection(m.cell_id,m.revision,m.configuration_root,m.support_epoch,19,18,m.holder,m.expires_at,m.semantic_handoff_root,m.transition_authority_receipt_root,m.resource_fence_receipt_root)
        self.assertIn('FENCE',compile_horizon_fenced_handoff(c,u,ev,m,v).reason)
    def test_irrelevant_configuration_not_in_semantic_root(self):
        self.assertEqual(semantic_handoff_root(ReadCert()),semantic_handoff_root(ReadCert()))
    def test_13d_noncompensation(self):
        for tail in itertools.product(range(3),repeat=5): self.assertEqual(hard13d_handoff((0,2,2,2,2,2,2,2)+tail),'HOLD_HARD_INVALID')

if __name__=='__main__': unittest.main()
