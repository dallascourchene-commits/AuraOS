from __future__ import annotations
import json, hashlib, sys
from dataclasses import dataclass, replace
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
import memory_city_effect_handoff_o12c_r2 as seam
from memory_city_effect_handoff_o12c_r2 import *

R=lambda x:digest(x)
SEM='HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1'
@dataclass(frozen=True)
class H:
    status:str; receipt_root:str; support_root:str; support_cut:tuple
@dataclass(frozen=True)
class T:
    disposition:str; receipt_root:str; influence_root:str; reproof_item_ids:tuple; reproof_semantics:str; transition_model_root:str; horizon:int; future_congruence_root:str|None
@dataclass(frozen=True)
class C:
    status:str; receipt_root:str; coverage_receipt_root:str; binding_roots:tuple; member_hydration_receipt_roots:tuple; member_support_roots:tuple; hydration_cut:tuple; reproof_item_ids:tuple; transition_model_root:str; horizon:int; future_congruence_root:str|None; consequence_root:str; mutation_authority:bool; effect_authority:bool; gate10:bool
@dataclass(frozen=True)
class U:
    status:str; certificate_root:str; mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False

def state(tag):
    h=H('READY_SUPPORT_CLOSED_HYDRATION_D0',R(['h',tag]),R(['s',tag]),('A','B'))
    t=T('READY_D0',R(['tc',tag]),R(['i',tag]),('A','B','C'),SEM,R(['t',tag]),2,R(['f',tag]))
    bind=R(['owner-binding',tag]); certroot=R(['cert',tag])
    c=C('READY_D0',certroot,R(['cov',tag]),(bind,),(h.receipt_root,),(h.support_root,),h.support_cut,t.reproof_item_ids,t.transition_model_root,t.horizon,t.future_congruence_root,seam._canonical_consequence_root(h,t),False,False,False)
    u=U('READY_D0',certroot)
    ro=ReadOwnerBindingEvidence(bind,R(['use',tag]),R(['read-owner',tag]))
    a={'schema':ADMISSION_SCHEMA,'disposition':'HOLD_TECC_REQUIRED_D0','reason':'effect_bound_use_requires_independent_tecc_verification','admission_mode':'EFFECT_BOUND','typed_closure_receipt_root':t.receipt_root,'coverage_receipt_root':c.coverage_receipt_root,'support_root':h.support_root,'influence_root':t.influence_root,'transition_model_root':t.transition_model_root,'future_congruence_root':t.future_congruence_root,'horizon':t.horizon,'required_verifier_schema':TECC_SCHEMA,'authority_minted':False,'mutation_authority':False,'effect_authority':False,'gate10':False}; a['receipt_root']=digest(a)
    r=EffectRefinementEvidence(bind,R(['intent',tag]),R(['esc',tag]),R(['plan',tag]),R(['obl',tag]),R(['ref-owner',tag]))
    e=EffectHandoffEvidence(R(['owner',tag]),R(['ver',tag]))
    m=MutationBoundaryProjection('cell',7,R(['cfg',tag]),11,19,19,'agent',100,R(['ta',tag]),R(['res',tag]))
    v=StrictVerificationContext(bind,ro.current_read_use_root,ro.read_owner_receipt_root,r.intent_binding_root,r.effect_escalation_root,r.refinement_owner_receipt_root,'cell',7,m.configuration_root,11,19,19,'agent',e.owner_evidence_root,e.verifier_receipt_root,m.transition_authority_receipt_root,m.resource_fence_receipt_root,R(['nuisance',tag]),10)
    return h,t,c,u,ro,a,r,e,m,v

def unsafe_o12c_like(c,u,h,t,ro,a,r,e,m,v):
    if c.status!='READY_D0' or u.status!='READY_D0': return False
    if a.get('admission_mode')!='EFFECT_BOUND' or a.get('disposition')!='HOLD_TECC_REQUIRED_D0': return False
    if e.owner_evidence_root!=v.owner_evidence_root or e.verifier_receipt_root!=v.verifier_receipt_root:return False
    if (m.cell_id,m.revision,m.configuration_root,m.support_epoch,m.fence_generation,m.installed_fence_generation)!=(v.cell_id,v.revision,v.configuration_root,v.support_epoch,v.fence_generation,v.installed_fence_generation):return False
    return v.now<m.expires_at and m.fence_generation==m.installed_fence_generation

def main():
    M={k:0 for k in ('cases','oracle_tecc','strict_tecc','strict_false_tecc','strict_false_hold','unsafe_false_tecc','valid','admission_schema','admission_missing_authority','read_authority','consequence_substitution','holder_move','read_owner_move','effect_escalation_move','refinement_owner_move','detached_binding','expired')}
    reasons={}
    for n in range(20000):
        cls=n%10; tag=f'{n%211}'; h,t,c,u,ro,a,r,e,m,v=state(tag)
        expected=True
        if cls==0:
            M['valid']+=1
        elif cls==1:
            M['admission_schema']+=1; expected=False; a=dict(a);a['schema']='OTHER';a.pop('receipt_root');a['receipt_root']=digest(a)
        elif cls==2:
            M['admission_missing_authority']+=1; expected=False; a=dict(a);a.pop('effect_authority');a.pop('receipt_root');a['receipt_root']=digest(a)
        elif cls==3:
            M['read_authority']+=1; expected=False; c=replace(c,effect_authority=True)
        elif cls==4:
            M['consequence_substitution']+=1; expected=False; c=replace(c,consequence_root=R(['forged',tag]))
        elif cls==5:
            M['holder_move']+=1; expected=False; v=replace(v,holder='other')
        elif cls==6:
            M['read_owner_move']+=1; expected=False; v=replace(v,read_owner_receipt_root=R(['new-read-owner',tag]))
        elif cls==7:
            M['effect_escalation_move']+=1; expected=False; v=replace(v,effect_escalation_root=R(['new-esc',tag]))
        elif cls==8:
            M['refinement_owner_move']+=1; expected=False; v=replace(v,refinement_owner_receipt_root=R(['new-ref-owner',tag]))
        elif cls==9:
            M['expired']+=1; expected=False; v=replace(v,now=100)
        d=compile_effect_handoff_r2(c,u,h,t,ro,a,r,e,m,v)
        got=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        unsafe=unsafe_o12c_like(c,u,h,t,ro,a,r,e,m,v)
        M['cases']+=1;M['oracle_tecc']+=expected;M['strict_tecc']+=got;M['strict_false_tecc']+=(got and not expected);M['strict_false_hold']+=((not got) and expected);M['unsafe_false_tecc']+=(unsafe and not expected)
        reasons[d.reason]=reasons.get(d.reason,0)+1
    assert M['strict_false_tecc']==0 and M['strict_false_hold']==0
    out={'schema':'AURA-MEMORY-CITY-O12C-R2-CAMPAIGN-v1','metrics':M,'reasons':dict(sorted(reasons.items()))}
    out['campaign_root']=hashlib.sha256(json.dumps(out,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__':main()
