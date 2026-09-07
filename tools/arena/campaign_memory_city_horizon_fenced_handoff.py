from __future__ import annotations
from dataclasses import dataclass, replace
from hashlib import sha256
import json
try:
    from .memory_city_horizon_fenced_handoff import *
    from .memory_city_consequence_refinement import EffectIntent, EffectObligationProjection, compile_effect_refinement
except ImportError:
    from memory_city_horizon_fenced_handoff import *
    from memory_city_consequence_refinement import EffectIntent, EffectObligationProjection, compile_effect_refinement

def r(x): return sha256(x.encode()).hexdigest()

@dataclass(frozen=True)
class H:
    status:str='READY_SUPPORT_CLOSED_HYDRATION_D0'; receipt_root:str=r('hydr'); support_root:str=r('support'); support_cut:tuple[str,...]=('a','b')
@dataclass(frozen=True)
class C:
    disposition:str='READY_D0'; receipt_root:str=r('typed'); influence_root:str=r('infl'); reproof_item_ids:tuple[str,...]=('a','b','c'); transition_model_root:str=r('trans'); horizon:int=2; future_congruence_root:str=r('future'); reproof_semantics:str=REPROOF_SEMANTICS
@dataclass(frozen=True)
class RC:
    status:str='READY_D0'; receipt_root:str=''; coverage_receipt_root:str=r('cov'); program_root:str=r('program'); sealed_domain_root:str=r('domain'); coverage_generation:int=7
    binding_roots:tuple[str,...]=(); member_support_roots:tuple[str,...]=(r('support'),); member_hydration_receipt_roots:tuple[str,...]=(r('hydr'),)
    hydration_cut:tuple[str,...]=('a','b'); reproof_item_ids:tuple[str,...]=('a','b','c'); transition_model_root:str=r('trans'); horizon:int=2; future_congruence_root:str=r('future'); consequence_root:str=''
    mutation_authority:bool=False; effect_authority:bool=False; gate10:bool=False
@dataclass(frozen=True)
class RU:
    status:str='READY_D0'; certificate_root:str=''

def read_cert(h:H,c:C, *, binding_override=None):
    binding=canonical_read_binding_root(h,c) if binding_override is None else binding_override
    temp=RC(binding_roots=(binding,))
    cons=canonical_read_consequence_root(temp)
    temp=replace(temp,consequence_root=cons)
    return replace(temp,receipt_root=canonical_read_certificate_receipt(temp))

def rehash_cert(cert:RC):
    return replace(cert,receipt_root=canonical_read_certificate_receipt(cert))

def admission(h:H,c:C,cert:RC,mode='EFFECT_BOUND'):
    p={'schema':ADMISSION_SCHEMA,'disposition':'HOLD_TECC_REQUIRED_D0' if mode=='EFFECT_BOUND' else 'READY_D0',
       'reason':'effect_bound_use_requires_independent_tecc_verification' if mode=='EFFECT_BOUND' else 'read_only_coverage_and_horizon_ready',
       'admission_mode':mode,'typed_closure_receipt_root':c.receipt_root,'coverage_receipt_root':cert.coverage_receipt_root,
       'support_root':h.support_root,'influence_root':c.influence_root,'transition_model_root':c.transition_model_root,
       'future_congruence_root':c.future_congruence_root,'horizon':c.horizon,
       'required_verifier_schema':TECC_SCHEMA if mode=='EFFECT_BOUND' else None,
       'authority_minted':False,'mutation_authority':False,'effect_authority':False,'gate10':False}
    p['receipt_root']=digest(p); return p

def refinement(cert:RC, *, obligation=None, authenticated=True, current=True):
    obligation=obligation or r('effect-obligation')
    intent=EffectIntent(r('intent'),r('effect-domain'),cert.program_root)
    projections=tuple(EffectObligationProjection(b,obligation,r('effect-evidence-'+str(i)),authenticated,current,r('nuisance')) for i,b in enumerate(cert.binding_roots))
    return intent,obligation,compile_effect_refinement(projections,cert,intent)

def base():
    h=H(); c=C(); cert=read_cert(h,c); use=RU(certificate_root=cert.receipt_root); a=admission(h,c,cert)
    intent,obligation,plan=refinement(cert)
    ev=EffectHandoffEvidence(r('owner'),r('verifier'))
    m=MutationBoundaryProjection('cell',4,r('cfg'),8,17,17,'worker',100,r('ta'),r('rf'))
    v=HandoffVerificationContext('cell',4,r('cfg'),8,17,17,'worker',r('owner'),r('verifier'),r('ta'),r('rf'),50)
    return h,c,cert,use,a,intent,obligation,plan,ev,m,v

def invoke(fx):
    h,c,cert,use,a,intent,obligation,plan,ev,m,v=fx
    return compile_effect_handoff(cert,use,h,c,a,plan,intent,obligation,ev,m,v)

def apply_mode(mode:int, fx):
    h,c,cert,use,a,intent,obligation,plan,ev,m,v=fx
    if mode==1:
        a=dict(a); a['schema']='FOREIGN-ADMISSION-v9'; a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    elif mode==2:
        a=dict(a); a.pop('effect_authority'); a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    elif mode==3:
        cert=replace(cert,effect_authority=True)
    elif mode==4:
        cert=replace(cert,consequence_root=r('substituted-consequence')); cert=rehash_cert(cert); use=replace(use,certificate_root=cert.receipt_root)
        intent,obligation,plan=refinement(cert)
    elif mode==5:
        m=replace(m,holder='zombie-worker')
    elif mode==6:
        a=admission(h,c,cert,'READ_ONLY')
    elif mode==7:
        obligation=r('moved-obligation')
    elif mode==8:
        _,_,plan=refinement(cert,authenticated=False)
    elif mode==9:
        c=replace(c,reproof_item_ids=('a','c')); a=admission(h,c,cert)
    elif mode==10:
        c=replace(c,reproof_semantics='ITEM_ONLY_DIRECTED_REPROOF-v0'); a=admission(h,c,cert)
    elif mode==11:
        c=replace(c,transition_model_root=r('moved-transition')); a=admission(h,c,cert)
    elif mode==12:
        use=replace(use,certificate_root=r('other-cert'))
    elif mode==13:
        ev=replace(ev,owner_evidence_root=r('stale-owner'))
    elif mode==14:
        ev=replace(ev,verifier_receipt_root=r('stale-verifier'))
    elif mode==15:
        m=replace(m,revision=5)
    elif mode==16:
        m=replace(m,installed_fence_generation=16); v=replace(v,installed_fence_generation=16)
    elif mode==17:
        v=replace(v,now=100)
    elif mode==18:
        a=dict(a); a['coverage_receipt_root']=r('other-cov'); a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    elif mode==19:
        h=replace(h,support_cut=('a',)); a=admission(h,c,cert)
    elif mode==20:
        cert=replace(cert,status='HOLD_D0')
    elif mode==21:
        use=replace(use,status='HOLD_D0')
    elif mode==22:
        a=dict(a); a['effect_authority']=True; a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    elif mode==23:
        legacy=digest({'schema':READ_BINDING_SCHEMA,'hydration_receipt_root':h.receipt_root,'hydration_support_root':h.support_root,'typed_closure_receipt_root':c.receipt_root})
        cert=read_cert(h,c,binding_override=legacy); use=replace(use,certificate_root=cert.receipt_root); a=admission(h,c,cert); intent,obligation,plan=refinement(cert)
    return h,c,cert,use,a,intent,obligation,plan,ev,m,v

def run(cases=24000):
    counts={'cases':cases,'oracle_tecc_route':0,'oracle_hold':0,'candidate_false_route':0,'candidate_false_hold':0,
            'effect_ready':0,'review_attack_canaries':0,'negative_time_constructor_rejects':0}
    review_attack_modes={1,2,3,4,5}
    for i in range(cases):
        mode=i%24; expected=(mode==0); fx=apply_mode(mode,base()); d=invoke(fx)
        routed=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0
        counts['oracle_tecc_route' if expected else 'oracle_hold']+=1
        counts['candidate_false_route']+=int(routed and not expected); counts['candidate_false_hold']+=int(expected and not routed)
        counts['effect_ready']+=int(d.effect_authority)
        counts['review_attack_canaries']+=int(mode in review_attack_modes)
    for ctor in (
        lambda: MutationBoundaryProjection('cell',4,r('cfg'),8,17,17,'worker',-1,r('ta'),r('rf')),
        lambda: HandoffVerificationContext('cell',4,r('cfg'),8,17,17,'worker',r('owner'),r('verifier'),r('ta'),r('rf'),-1),
    ):
        try: ctor()
        except ValueError: counts['negative_time_constructor_rejects']+=1
    raw=json.dumps(counts,sort_keys=True,separators=(',',':')).encode()
    out={**counts,'campaign_root':sha256(raw).hexdigest(),'schema':'aura.mc_o13.authenticated_effect_refined_tecc_handoff.campaign.v1','authority':'D0_NONPROMOTING_GATE10_FALSE'}
    if counts['candidate_false_route'] or counts['candidate_false_hold'] or counts['effect_ready'] or counts['negative_time_constructor_rejects']!=2: raise AssertionError(out)
    return out

# Actual hard-axis mutation harness consumed by Omega8 and 13D sweeps.
def build_hard_state(hard:tuple[int,...]):
    if len(hard)!=8: raise ValueError('8 hard axes required')
    fx=base(); h,c,cert,use,a,intent,obligation,plan,ev,m,v=fx
    if hard[0]==0: use=replace(use,status='HOLD_D0')
    elif hard[0]==1: use=replace(use,certificate_root=r('stale-read-use'))
    if hard[1]==0: c=replace(c,reproof_semantics='ITEM_ONLY_DIRECTED_REPROOF-v0'); a=admission(h,c,cert)
    elif hard[1]==1: c=replace(c,reproof_item_ids=('a','c')); a=admission(h,c,cert)
    if hard[2]==0:
        a=dict(a); a['schema']='FOREIGN'; a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    elif hard[2]==1:
        a=dict(a); a['coverage_receipt_root']=r('stale-cov'); a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    if hard[3]==0:
        _,_,plan=refinement(cert,authenticated=False)
    elif hard[3]==1:
        obligation=r('moved-obligation')
    if hard[4]==0: m=replace(m,configuration_root=r('moved-cfg'))
    elif hard[4]==1: m=replace(m,revision=5)
    if hard[5]==0: m=replace(m,holder='zombie')
    elif hard[5]==1: m=replace(m,installed_fence_generation=16); v=replace(v,installed_fence_generation=16)
    if hard[6]==0: ev=replace(ev,owner_evidence_root=r('stale-owner'))
    elif hard[6]==1: ev=replace(ev,verifier_receipt_root=r('stale-verifier'))
    if hard[7]==0: cert=replace(cert,effect_authority=True)
    elif hard[7]==1:
        a=dict(a); a.pop('gate10'); a['receipt_root']=digest({k:x for k,x in a.items() if k!='receipt_root'})
    return h,c,cert,use,a,intent,obligation,plan,ev,m,v

def evaluate_hard_state(hard:tuple[int,...], context:tuple[int,...]=(2,2,2,2,2)):
    if len(context)!=5: raise ValueError('5 context axes required')
    fx=build_hard_state(hard)
    context_observation_root=digest({'kind':'non_authoritative_context','axes':context})
    return invoke(fx),context_observation_root

if __name__=='__main__': print(json.dumps(run(),sort_keys=True,indent=2))
