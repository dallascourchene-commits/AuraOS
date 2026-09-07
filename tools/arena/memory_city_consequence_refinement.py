from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json

D0='D0_NONPROMOTING'
SCHEMA='AURA-MEMORY-CITY-CONSEQUENCE-REFINEMENT-v2'

def digest(v):
    return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def _root(v,n):
    if not isinstance(v,str) or len(v)!=64 or v.lower()!=v or any(c not in '0123456789abcdef' for c in v):
        raise ValueError(f'{n} must be lowercase sha256')
    return v

def _nn(v,n):
    if type(v) is not int or v<0: raise ValueError(f'{n} must be nonnegative int')
    return v

def _state(obj):
    raw=getattr(obj,'status',None)
    if raw is None: raw=getattr(obj,'disposition',None)
    return getattr(raw,'value',raw)

@dataclass(frozen=True)
class EffectObligationProjection:
    read_binding_root:str
    effect_obligation_root:str|None
    obligation_evidence_root:str|None
    obligation_authenticated:bool
    observation_current:bool
    nuisance_configuration_root:str
    def __post_init__(self):
        _root(self.read_binding_root,'read_binding_root'); _root(self.nuisance_configuration_root,'nuisance_configuration_root')
        if self.effect_obligation_root is not None:_root(self.effect_obligation_root,'effect_obligation_root')
        if self.obligation_evidence_root is not None:_root(self.obligation_evidence_root,'obligation_evidence_root')
        if type(self.obligation_authenticated) is not bool or type(self.observation_current) is not bool:
            raise ValueError('currentness flags must be bool')

@dataclass(frozen=True)
class EffectIntent:
    intent_root:str
    effect_domain_root:str
    program_root:str
    def __post_init__(self):
        _root(self.intent_root,'intent_root'); _root(self.effect_domain_root,'effect_domain_root'); _root(self.program_root,'program_root')
    @property
    def binding_root(self):
        return digest({'schema':SCHEMA,'kind':'effect_intent','intent_root':self.intent_root,'effect_domain_root':self.effect_domain_root,'program_root':self.program_root})

@dataclass(frozen=True)
class EffectSubclass:
    obligation_root:str
    member_binding_roots:tuple[str,...]
    evidence_roots:tuple[str,...]
    subclass_root:str
    authority:str=D0
    effect_authority:bool=False
    gate10:bool=False
    def __post_init__(self):
        _root(self.obligation_root,'obligation_root'); _root(self.subclass_root,'subclass_root')
        for x in self.member_binding_roots:_root(x,'member_binding_root')
        for x in self.evidence_roots:_root(x,'evidence_root')
        if self.effect_authority or self.gate10: raise ValueError('D0 effect subclass cannot mint authority')

@dataclass(frozen=True)
class EffectRefinementPlan:
    status:str
    read_certificate_root:str
    parent_read_root:str
    intent_binding_root:str
    subclasses:tuple[EffectSubclass,...]
    unresolved_binding_roots:tuple[str,...]
    plan_root:str
    reason:str=''
    authority:str=D0
    effect_authority:bool=False
    gate10:bool=False
    def __post_init__(self):
        _root(self.read_certificate_root,'read_certificate_root'); _root(self.parent_read_root,'parent_read_root')
        _root(self.intent_binding_root,'intent_binding_root'); _root(self.plan_root,'plan_root')
        for x in self.unresolved_binding_roots:_root(x,'unresolved_binding_root')
        if self.effect_authority or self.gate10: raise ValueError('D0 plan cannot mint authority')

def parent_read_root(cert)->str:
    receipt=_root(getattr(cert,'receipt_root',None),'read_receipt_root')
    coverage=_root(getattr(cert,'coverage_receipt_root',None),'coverage_receipt_root')
    program=_root(getattr(cert,'program_root',None),'program_root')
    domain=_root(getattr(cert,'sealed_domain_root',None),'sealed_domain_root')
    consequence=_root(getattr(cert,'consequence_root',None),'consequence_root')
    transition=_root(getattr(cert,'transition_model_root',None),'transition_model_root')
    generation=_nn(getattr(cert,'coverage_generation',None),'coverage_generation')
    horizon=_nn(getattr(cert,'horizon',None),'horizon')
    future=getattr(cert,'future_congruence_root',None)
    if horizon>0:_root(future,'future_congruence_root')
    elif future is not None:_root(future,'future_congruence_root')
    bindings=tuple(sorted(_root(x,'binding_root') for x in tuple(getattr(cert,'binding_roots',()))))
    if not bindings: raise ValueError('read certificate must bind members')
    return digest({'schema':SCHEMA,'kind':'parent_read','receipt_root':receipt,'coverage_receipt_root':coverage,
                   'program_root':program,'sealed_domain_root':domain,'coverage_generation':generation,
                   'binding_roots':bindings,'consequence_root':consequence,'transition_model_root':transition,
                   'horizon':horizon,'future_congruence_root':future})

def _hold(cert,intent,status,reason,unresolved):
    rr=_root(getattr(cert,'receipt_root',None),'read_receipt_root'); parent=parent_read_root(cert); ib=intent.binding_root
    unresolved=tuple(sorted(set(unresolved)))
    pr=digest({'schema':SCHEMA,'kind':'effect_refinement_hold','status':status,'reason':reason,
               'read_certificate_root':rr,'parent_read_root':parent,'intent_binding_root':ib,'unresolved':unresolved})
    return EffectRefinementPlan(status,rr,parent,ib,(),unresolved,pr,reason)

def compile_effect_refinement(projections:tuple[EffectObligationProjection,...], cert, intent:EffectIntent)->EffectRefinementPlan:
    if not isinstance(intent,EffectIntent): raise ValueError('intent must be EffectIntent')
    rr=_root(getattr(cert,'receipt_root',None),'read_receipt_root'); parent=parent_read_root(cert); ib=intent.binding_root
    members=tuple(sorted(_root(x,'binding_root') for x in tuple(getattr(cert,'binding_roots',()))))
    if _state(cert)!='READY_D0': return _hold(cert,intent,'HOLD_PARENT_D0','read_certificate_not_ready',members)
    if any(not isinstance(p,EffectObligationProjection) for p in projections): raise ValueError('projections must be EffectObligationProjection')
    keys=tuple(p.read_binding_root for p in projections)
    if len(set(keys))!=len(keys) or set(keys)!=set(members):
        return _hold(cert,intent,'HOLD_BINDING_ENVELOPE_D0','effect_projection_binding_envelope_mismatch',members)
    unresolved=[]; groups={}
    for p in projections:
        if p.effect_obligation_root is None or p.obligation_evidence_root is None or not p.obligation_authenticated or not p.observation_current:
            unresolved.append(p.read_binding_root); continue
        groups.setdefault(p.effect_obligation_root,[]).append(p)
    subclasses=[]
    for obligation,ps in sorted(groups.items()):
        mb=tuple(sorted(p.read_binding_root for p in ps)); ev=tuple(sorted(p.obligation_evidence_root for p in ps))
        sr=digest({'schema':SCHEMA,'kind':'effect_subclass','parent_read_root':parent,'read_certificate_root':rr,
                   'intent_binding_root':ib,'obligation_root':obligation,'member_binding_roots':mb,'evidence_roots':ev})
        subclasses.append(EffectSubclass(obligation,mb,ev,sr))
    unresolved=tuple(sorted(unresolved)); status='READY_REFINED_D0' if not unresolved else 'PARTIAL_HOLD_D0'
    pr=digest({'schema':SCHEMA,'kind':'effect_refinement','status':status,'read_certificate_root':rr,
               'parent_read_root':parent,'intent_binding_root':ib,'children':[x.subclass_root for x in subclasses],
               'unresolved':unresolved})
    return EffectRefinementPlan(status,rr,parent,ib,tuple(subclasses),unresolved,pr)

def validate_effect_binding(plan:EffectRefinementPlan, *, cert, intent:EffectIntent, read_binding_root:str, obligation_root:str)->str:
    _root(read_binding_root,'read_binding_root'); _root(obligation_root,'obligation_root')
    if parent_read_root(cert)!=plan.parent_read_root or getattr(cert,'receipt_root',None)!=plan.read_certificate_root:
        return 'HOLD_READ_CERTIFICATE_MOVED'
    if intent.binding_root!=plan.intent_binding_root:return 'HOLD_EFFECT_INTENT_MOVED'
    for child in plan.subclasses:
        if read_binding_root in child.member_binding_roots:
            if child.obligation_root!=obligation_root:return 'HOLD_EFFECT_OBLIGATION_MOVED'
            return 'READY_EFFECT_SUBCLASS_D0'
    return 'HOLD_BINDING_UNRESOLVED'

def effect_escalation_root(plan:EffectRefinementPlan, child:EffectSubclass)->str:
    if child not in plan.subclasses: raise ValueError('child not in refinement plan')
    return digest({'schema':SCHEMA,'kind':'effect_escalation','read_certificate_root':plan.read_certificate_root,
                   'parent_read_root':plan.parent_read_root,'intent_binding_root':plan.intent_binding_root,
                   'plan_root':plan.plan_root,'subclass_root':child.subclass_root,'obligation_root':child.obligation_root,
                   'authority':D0})

def refinement_invariants(cert,plan:EffectRefinementPlan)->bool:
    parent=set(getattr(cert,'binding_roots',())); seen=set()
    for c in plan.subclasses:
        s=set(c.member_binding_roots)
        if not s or not s<=parent or seen&s:return False
        seen|=s
    return seen|set(plan.unresolved_binding_roots)==parent
