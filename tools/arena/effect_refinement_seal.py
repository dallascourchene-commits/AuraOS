from __future__ import annotations
from dataclasses import dataclass, replace
from enum import Enum
from hashlib import sha256
import json

D0='D0_NONPROMOTING'
TECC='AURA-TECC-v1'
SCHEMA='AURA-MEMORY-CITY-CURRENT-OWNER-EFFECT-REFINEMENT-SEAL-v1'

def digest(v):
    return sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def root(tag): return sha256(tag.encode()).hexdigest()

def _root(v,n):
    if not isinstance(v,str) or len(v)!=64 or v.lower()!=v or any(c not in '0123456789abcdef' for c in v):
        raise ValueError(f'{n} must be lowercase sha256')
    return v

class Disp(str,Enum):
    HOLD='HOLD'
    REBIND_REQUIRED='REBIND_REQUIRED'
    HOLD_TECC_REQUIRED_D0='HOLD_TECC_REQUIRED_D0'

@dataclass(frozen=True)
class CurrentOwnerHandoff:
    disposition: str
    semantic_handoff_root: str
    tecc_input_root: str
    required_verifier_schema: str=TECC
    authority: str=D0
    authority_minted: bool=False
    mutation_authority: bool=False
    effect_authority: bool=False
    gate10: bool=False
    def __post_init__(self):
        _root(self.semantic_handoff_root,'semantic_handoff_root'); _root(self.tecc_input_root,'tecc_input_root')

@dataclass(frozen=True)
class EffectRefinementSeal:
    selected_read_binding_root: str
    intent_binding_root: str
    effect_escalation_root: str
    refinement_plan_root: str
    effect_obligation_root: str
    refinement_owner_receipt_root: str
    plan_status: str='READY_REFINED_D0'
    binding_status: str='READY_EFFECT_SUBCLASS_D0'
    authority: str=D0
    authority_minted: bool=False
    mutation_authority: bool=False
    effect_authority: bool=False
    gate10: bool=False
    def __post_init__(self):
        for n in ('selected_read_binding_root','intent_binding_root','effect_escalation_root','refinement_plan_root','effect_obligation_root','refinement_owner_receipt_root'):
            _root(getattr(self,n),n)

@dataclass(frozen=True)
class RefinementVerification:
    active_read_binding_root: str
    intent_binding_root: str
    effect_escalation_root: str
    refinement_plan_root: str
    effect_obligation_root: str
    refinement_owner_receipt_root: str
    def __post_init__(self):
        for n in self.__dataclass_fields__: _root(getattr(self,n),n)

@dataclass(frozen=True)
class Decision:
    disposition: Disp
    reason: str
    refined_tecc_input_root: str|None=None
    required_verifier_schema: str|None=None
    authority: str=D0
    authority_minted: bool=False
    mutation_authority: bool=False
    effect_authority: bool=False
    gate10: bool=False
    def __post_init__(self):
        if self.refined_tecc_input_root is not None: _root(self.refined_tecc_input_root,'refined_tecc_input_root')
        if self.authority!=D0 or self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError('seal cannot mint authority')

def _authority_clean(obj):
    return getattr(obj,'authority',None)==D0 and all(getattr(obj,n,None) is False for n in ('authority_minted','mutation_authority','effect_authority','gate10'))

def compile_refined_tecc_seal(base:CurrentOwnerHandoff, refinement:EffectRefinementSeal, current:RefinementVerification)->Decision:
    if not isinstance(refinement,EffectRefinementSeal) or not isinstance(current,RefinementVerification):
        raise ValueError('typed refinement/current evidence required')
    disposition=getattr(getattr(base,'disposition',None),'value',getattr(base,'disposition',None))
    semantic=_root(getattr(base,'semantic_handoff_root',None),'semantic_handoff_root')
    base_tecc=_root(getattr(base,'tecc_input_root',None),'tecc_input_root')
    if disposition!='HOLD_TECC_REQUIRED_D0' or getattr(base,'required_verifier_schema',None)!=TECC:
        return Decision(Disp.HOLD,'CURRENT_OWNER_HANDOFF_NOT_TECC_ROUTABLE')
    if not _authority_clean(base): return Decision(Disp.HOLD,'CURRENT_OWNER_HANDOFF_AUTHORITY_ESCALATION')
    if refinement.plan_status!='READY_REFINED_D0' or refinement.binding_status!='READY_EFFECT_SUBCLASS_D0':
        return Decision(Disp.HOLD,'EFFECT_REFINEMENT_NOT_READY')
    if not _authority_clean(refinement): return Decision(Disp.HOLD,'EFFECT_REFINEMENT_AUTHORITY_ESCALATION')
    if refinement.selected_read_binding_root!=current.active_read_binding_root:
        return Decision(Disp.REBIND_REQUIRED,'EFFECT_REFINEMENT_BINDING_MOVED')
    for field,reason in (
        ('intent_binding_root','EFFECT_INTENT_MOVED'),
        ('effect_escalation_root','EFFECT_ESCALATION_MOVED'),
        ('refinement_plan_root','EFFECT_REFINEMENT_PLAN_MOVED'),
        ('effect_obligation_root','EFFECT_OBLIGATION_MOVED'),
        ('refinement_owner_receipt_root','EFFECT_REFINEMENT_OWNER_RECEIPT_STALE'),
    ):
        if getattr(refinement,field)!=getattr(current,field):
            return Decision(Disp.REBIND_REQUIRED,reason)
    out=digest({
        'schema':SCHEMA,'kind':'effect_refined_tecc_input',
        'base_current_owner_tecc_input_root':base_tecc,
        'semantic_handoff_root':semantic,
        'selected_read_binding_root':refinement.selected_read_binding_root,
        'intent_binding_root':refinement.intent_binding_root,
        'effect_escalation_root':refinement.effect_escalation_root,
        'refinement_plan_root':refinement.refinement_plan_root,
        'effect_obligation_root':refinement.effect_obligation_root,
        'refinement_owner_receipt_root':refinement.refinement_owner_receipt_root,
        'required_verifier_schema':TECC,
        'authority_minted':False,'mutation_authority':False,'effect_authority':False,'gate10':False,
    })
    return Decision(Disp.HOLD_TECC_REQUIRED_D0,'CURRENT_OWNER_EFFECT_REFINEMENT_REQUIRES_INDEPENDENT_TECC',out,TECC)

def fixture():
    base=CurrentOwnerHandoff('HOLD_TECC_REQUIRED_D0',root('semantic'),root('pr889-tecc'))
    ref=EffectRefinementSeal(root('binding'),root('intent'),root('escalation'),root('plan'),root('obligation'),root('ref-owner'))
    cur=RefinementVerification(root('binding'),root('intent'),root('escalation'),root('plan'),root('obligation'),root('ref-owner'))
    return base,ref,cur
