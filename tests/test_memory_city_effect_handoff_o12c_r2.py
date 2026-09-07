from __future__ import annotations
import sys, unittest
from dataclasses import dataclass, replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
import memory_city_effect_handoff_o12c_r2 as seam
from memory_city_effect_handoff_o12c_r2 import *

R=lambda x:digest(x)
SEM='HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1'

@dataclass(frozen=True)
class Hyd:
    status:str='READY_SUPPORT_CLOSED_HYDRATION_D0'; receipt_root:str=R('hydr'); support_root:str=R('support'); support_cut:tuple=('A','B')
@dataclass(frozen=True)
class TC:
    disposition:str='READY_D0'; receipt_root:str=R('tc'); influence_root:str=R('infl'); reproof_item_ids:tuple=('A','B','C'); reproof_semantics:str=SEM; transition_model_root:str=R('trans'); horizon:int=2; future_congruence_root:str|None=R('future')
@dataclass(frozen=True)
class Cert:
    status:str='READY_D0'; receipt_root:str=R('cert'); coverage_receipt_root:str=R('coverage'); binding_roots:tuple=(R('binding'),); member_hydration_receipt_roots:tuple=(R('hydr'),); member_support_roots:tuple=(R('support'),); hydration_cut:tuple=('A','B'); reproof_item_ids:tuple=('A','B','C'); transition_model_root:str=R('trans'); horizon:int=2; future_congruence_root:str|None=R('future'); consequence_root:str=''; mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class Use:
    status:str='READY_D0'; certificate_root:str=R('cert'); mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False

def mk():
    h=Hyd(); t=TC(); c=Cert(consequence_root=seam._canonical_consequence_root(h,t)); u=Use()
    ro=ReadOwnerBindingEvidence(R('binding'),R('use'),R('read-owner'))
    admission={
        'schema':ADMISSION_SCHEMA,'disposition':'HOLD_TECC_REQUIRED_D0','reason':'effect_bound_use_requires_independent_tecc_verification','admission_mode':'EFFECT_BOUND',
        'typed_closure_receipt_root':t.receipt_root,'coverage_receipt_root':c.coverage_receipt_root,'support_root':h.support_root,'influence_root':t.influence_root,
        'transition_model_root':t.transition_model_root,'future_congruence_root':t.future_congruence_root,'horizon':t.horizon,'required_verifier_schema':TECC_SCHEMA,
        'authority_minted':False,'mutation_authority':False,'effect_authority':False,'gate10':False,
    }
    admission['receipt_root']=digest(admission)
    ref=EffectRefinementEvidence(ro.active_read_binding_root,R('intent'),R('escalation'),R('plan'),R('obligation'),R('ref-owner'))
    ev=EffectHandoffEvidence(R('owner'),R('verifier'))
    m=MutationBoundaryProjection('cell',7,R('cfg'),11,19,19,'agent',100,R('transition-auth'),R('resource'))
    v=StrictVerificationContext(ro.active_read_binding_root,ro.current_read_use_root,ro.read_owner_receipt_root,ref.intent_binding_root,ref.effect_escalation_root,ref.refinement_owner_receipt_root,'cell',7,R('cfg'),11,19,19,'agent',R('owner'),R('verifier'),R('transition-auth'),R('resource'),R('nuisance'),10)
    return h,t,c,u,ro,admission,ref,ev,m,v

class Tests(unittest.TestCase):
    def test_valid_routes_to_tecc_never_ready(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        self.assertEqual(d.disposition,HandoffDisposition.HOLD_TECC_REQUIRED_D0); self.assertFalse(d.effect_authority)
    def test_noncanonical_admission_schema_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); a=dict(a); a['schema']='OTHER'; a.pop('receipt_root'); a['receipt_root']=digest(a)
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'ADMISSION_SCHEMA_NOT_CANONICAL')
    def test_missing_authority_field_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); a=dict(a); a.pop('effect_authority'); a.pop('receipt_root'); a['receipt_root']=digest(a)
        self.assertIn('AUTHORITY_FIELDS',compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason)
    def test_read_authority_taint_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); c=replace(c,effect_authority=True)
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'READ_CERTIFICATE_AUTHORITY_ESCALATION')
    def test_use_authority_taint_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); u=replace(u,mutation_authority=True)
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'READ_USE_AUTHORITY_ESCALATION')
    def test_consequence_substitution_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); c=replace(c,consequence_root=R('forged'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'READ_CONSEQUENCE_ROOT_SUBSTITUTED')
    def test_owner_binding_move_rebinds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,active_read_binding_root=R('new-binding'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'READ_OWNER_BINDING_MOVED')
    def test_read_owner_receipt_move_rebinds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,read_owner_receipt_root=R('new-owner'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'READ_OWNER_RECEIPT_STALE')
    def test_effect_escalation_move_rebinds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,effect_escalation_root=R('new-escalation'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'EFFECT_ESCALATION_MOVED')
    def test_refinement_detached_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); r=replace(r,selected_read_binding_root=R('detached'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'EFFECT_REFINEMENT_BINDING_DETACHED')
    def test_refinement_owner_receipt_move_rebinds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,refinement_owner_receipt_root=R('new-ref-owner'))
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'EFFECT_REFINEMENT_OWNER_RECEIPT_STALE')
    def test_holder_mismatch_rebinds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,holder='other')
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'LEASE_HOLDER_MOVED')
    def test_negative_expiry_rejected(self):
        with self.assertRaises(ValueError): MutationBoundaryProjection('c',0,R('c'),0,0,0,'h',-1,R('a'),R('b'))
    def test_negative_now_rejected(self):
        h,t,c,u,ro,a,r,e,m,v=mk()
        with self.assertRaises(ValueError): replace(v,now=-1)
    def test_expired_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); v=replace(v,now=100)
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'LEASE_EXPIRED')
    def test_uninstalled_fence_holds(self):
        h,t,c,u,ro,a,r,e,m,v=mk(); m=replace(m,installed_fence_generation=18)
        self.assertEqual(compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v).reason,'INSTALLED_FENCE_RECEIPT_MISMATCH')

if __name__=='__main__': unittest.main()
