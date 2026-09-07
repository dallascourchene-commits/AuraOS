from __future__ import annotations

"""Authenticated D0 effect-refined semantic-to-TECC handoff.

Memory City may certify and refine current read semantics, then bind the selected
refinement to an exact current mutation boundary. It never mints effect authority.
The strongest success state here is HOLD_TECC_REQUIRED_D0 with an exact input root
for an independent AURA-TECC-v1 verifier.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping
from memory_city_consequence_refinement import (
    EffectIntent, EffectRefinementPlan, effect_escalation_root, validate_effect_binding,
)

SCHEMA = "AURA-MEMORY-CITY-HORIZON-FENCED-HANDOFF-v3"
READ_BINDING_SCHEMA = "AURA-MEMORY-CITY-READ-WORLD-BINDING-v1"
READ_CONSEQUENCE_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-v1"
READ_CERT_SCHEMA = "AURA-MEMORY-CITY-READ-CONSEQUENCE-CERT-v1"
ADMISSION_SCHEMA = "AURA-MEMORY-CITY-PROOF-CARRYING-TYPED-ADMISSION-v2"
REPROOF_SEMANTICS = "HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1"
TECC_SCHEMA = "AURA-TECC-v1"
D0 = "D0_NONPROMOTING"
ADMISSION_KEYS = frozenset({
    'schema','disposition','reason','admission_mode','typed_closure_receipt_root','coverage_receipt_root',
    'support_root','influence_root','transition_model_root','future_congruence_root','horizon',
    'required_verifier_schema','authority_minted','mutation_authority','effect_authority','gate10','receipt_root'
})


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()

def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value

def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value: raise ValueError(f"{field} required")
    return value

def _nn(value: int, field: str) -> int:
    if type(value) is not int or value < 0: raise ValueError(f"{field} must be nonnegative exact int")
    return value

def _status(obj) -> str | None:
    raw = getattr(obj, "status", None)
    if raw is None: raw = getattr(obj, "disposition", None)
    return getattr(raw, "value", raw)

class HandoffDisposition(str, Enum):
    HOLD = "HOLD"
    REBIND_REQUIRED = "REBIND_REQUIRED"
    HOLD_TECC_REQUIRED_D0 = "HOLD_TECC_REQUIRED_D0"

@dataclass(frozen=True)
class MutationBoundaryProjection:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    installed_fence_generation: int
    holder: str
    expires_at: int
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str
    def __post_init__(self):
        _id(self.cell_id, "cell_id"); _id(self.holder, "holder")
        _nn(self.revision, "revision"); _nn(self.support_epoch, "support_epoch")
        _nn(self.fence_generation, "fence_generation"); _nn(self.installed_fence_generation, "installed_fence_generation")
        _nn(self.expires_at, "expires_at")
        for name in ("configuration_root", "transition_authority_receipt_root", "resource_fence_receipt_root"):
            _root(getattr(self, name), name)
    @property
    def boundary_root(self) -> str:
        return digest({"schema":SCHEMA,"kind":"mutation_boundary","cell_id":self.cell_id,"revision":self.revision,
            "configuration_root":self.configuration_root,"support_epoch":self.support_epoch,
            "fence_generation":self.fence_generation,"installed_fence_generation":self.installed_fence_generation,
            "holder":self.holder,"expires_at":self.expires_at,
            "transition_authority_receipt_root":self.transition_authority_receipt_root,
            "resource_fence_receipt_root":self.resource_fence_receipt_root})

@dataclass(frozen=True)
class HandoffVerificationContext:
    cell_id: str
    revision: int
    configuration_root: str
    support_epoch: int
    fence_generation: int
    installed_fence_generation: int
    holder: str
    owner_evidence_root: str
    verifier_receipt_root: str
    transition_authority_receipt_root: str
    resource_fence_receipt_root: str
    now: int
    def __post_init__(self):
        _id(self.cell_id,"cell_id"); _id(self.holder,"holder")
        _nn(self.revision,"revision"); _nn(self.support_epoch,"support_epoch")
        _nn(self.fence_generation,"fence_generation"); _nn(self.installed_fence_generation,"installed_fence_generation")
        _nn(self.now,"now")
        for name in ("configuration_root","owner_evidence_root","verifier_receipt_root","transition_authority_receipt_root","resource_fence_receipt_root"):
            _root(getattr(self,name),name)

@dataclass(frozen=True)
class EffectHandoffEvidence:
    owner_evidence_root: str
    verifier_receipt_root: str
    def __post_init__(self):
        _root(self.owner_evidence_root,"owner_evidence_root"); _root(self.verifier_receipt_root,"verifier_receipt_root")

@dataclass(frozen=True)
class HandoffDecision:
    disposition: HandoffDisposition
    reason: str
    semantic_handoff_root: str | None = None
    effect_escalation_root: str | None = None
    tecc_input_root: str | None = None
    required_verifier_schema: str | None = None
    authority: str = D0
    authority_minted: bool = False
    mutation_authority: bool = False
    effect_authority: bool = False
    gate10: bool = False
    def __post_init__(self):
        for name in ('semantic_handoff_root','effect_escalation_root','tecc_input_root'):
            value=getattr(self,name)
            if value is not None:_root(value,name)
        if self.authority_minted or self.mutation_authority or self.effect_authority or self.gate10:
            raise ValueError("D0 handoff cannot mint authority")


def canonical_read_binding_root(hydration, typed_closure) -> str:
    semantics=getattr(typed_closure,'reproof_semantics',None)
    if semantics != REPROOF_SEMANTICS: raise ValueError('typed reproof semantics not current')
    return digest({'schema':READ_BINDING_SCHEMA,'hydration_receipt_root':getattr(hydration,'receipt_root',None),
        'hydration_support_root':getattr(hydration,'support_root',None),
        'typed_closure_receipt_root':getattr(typed_closure,'receipt_root',None),
        'typed_reproof_semantics':semantics})


def canonical_read_consequence_root(read_cert) -> str:
    transition=_root(getattr(read_cert,'transition_model_root',None),'transition_model_root')
    horizon=_nn(getattr(read_cert,'horizon',None),'horizon')
    future=getattr(read_cert,'future_congruence_root',None)
    if horizon>0:_root(future,'future_congruence_root')
    elif future is not None:_root(future,'future_congruence_root')
    return digest({'schema':READ_CONSEQUENCE_SCHEMA,'hydration_cut':tuple(getattr(read_cert,'hydration_cut',())),
        'reproof':tuple(getattr(read_cert,'reproof_item_ids',())),'reproof_semantics':REPROOF_SEMANTICS,
        'transition_model_root':transition,'horizon':horizon,'future_congruence_root':future})


def canonical_read_certificate_receipt(read_cert) -> str:
    bindings=tuple(sorted(_root(x,'binding_root') for x in tuple(getattr(read_cert,'binding_roots',()))))
    supports=tuple(sorted(_root(x,'support_root') for x in tuple(getattr(read_cert,'member_support_roots',()))))
    hydr=tuple(sorted(_root(x,'hydration_receipt_root') for x in tuple(getattr(read_cert,'member_hydration_receipt_roots',()))))
    if not bindings or not supports or not hydr: raise ValueError('read certificate membership envelope required')
    payload={'schema':READ_CERT_SCHEMA,'status':'READY_D0','coverage_receipt_root':_root(getattr(read_cert,'coverage_receipt_root',None),'coverage_receipt_root'),
        'program_root':_root(getattr(read_cert,'program_root',None),'program_root'),
        'sealed_domain_root':_root(getattr(read_cert,'sealed_domain_root',None),'sealed_domain_root'),
        'coverage_generation':_nn(getattr(read_cert,'coverage_generation',None),'coverage_generation'),
        'bindings':list(bindings),'member_support_roots':list(supports),'member_hydration_receipts':list(hydr),
        'reproof_semantics':REPROOF_SEMANTICS,'consequence_root':_root(getattr(read_cert,'consequence_root',None),'consequence_root'),
        'mutation_authority':False,'effect_authority':False,'gate10':False}
    return digest(payload)


def _admission_receipt_current(admission: Mapping[str, object], read_cert, hydration, typed_closure) -> tuple[bool,str]:
    if not isinstance(admission,Mapping): return False,'ADMISSION_RECEIPT_REQUIRED'
    if frozenset(admission.keys()) != ADMISSION_KEYS: return False,'ADMISSION_SHAPE_NOT_CANONICAL'
    if admission.get('schema') != ADMISSION_SCHEMA: return False,'ADMISSION_SCHEMA_NOT_CANONICAL'
    if admission.get('admission_mode') != 'EFFECT_BOUND': return False,'READ_ONLY_CANNOT_ENTER_EFFECT_HANDOFF'
    if admission.get('disposition') != 'HOLD_TECC_REQUIRED_D0' or admission.get('required_verifier_schema') != TECC_SCHEMA:
        return False,'EFFECT_MODE_NOT_TECC_SEALED'
    if admission.get('reason') != 'effect_bound_use_requires_independent_tecc_verification': return False,'ADMISSION_REASON_NOT_CANONICAL'
    for k in ('authority_minted','mutation_authority','effect_authority','gate10'):
        if admission.get(k) is not False: return False,'ADMISSION_AUTHORITY_DECLARATION_INVALID'
    checks=(('typed_closure_receipt_root',getattr(typed_closure,'receipt_root',None),'ADMISSION_TYPED_CLOSURE_MOVED'),
        ('coverage_receipt_root',getattr(read_cert,'coverage_receipt_root',None),'ADMISSION_COVERAGE_MOVED'),
        ('support_root',getattr(hydration,'support_root',None),'ADMISSION_SUPPORT_MOVED'),
        ('influence_root',getattr(typed_closure,'influence_root',None),'ADMISSION_INFLUENCE_MOVED'),
        ('transition_model_root',getattr(typed_closure,'transition_model_root',None),'ADMISSION_TRANSITION_MOVED'))
    for key,expected,reason in checks:
        if admission.get(key)!=expected:return False,reason
    if admission.get('horizon')!=getattr(typed_closure,'horizon',None) or admission.get('future_congruence_root')!=getattr(typed_closure,'future_congruence_root',None):
        return False,'ADMISSION_HORIZON_MOVED'
    try:_root(admission.get('receipt_root'),'admission_receipt_root')
    except ValueError:return False,'ADMISSION_RECEIPT_ROOT_MALFORMED'
    payload=dict(admission); receipt=payload.pop('receipt_root')
    if digest(payload)!=receipt:return False,'ADMISSION_RECEIPT_ROOT_FORGED'
    return True,'EFFECT_MODE_TECC_SEALED'


def _read_consequence_current(read_cert, read_use, hydration, typed_closure):
    if _status(read_cert)!='READY_D0' or _status(read_use)!='READY_D0': return False,'READ_CONSEQUENCE_NOT_READY',None,None
    if any(getattr(read_cert,k,None) is not False for k in ('mutation_authority','effect_authority','gate10')):
        return False,'READ_CERTIFICATE_AUTHORITY_ESCALATION',None,None
    if getattr(read_use,'certificate_root',None)!=getattr(read_cert,'receipt_root',None): return False,'READ_USE_CERTIFICATE_MOVED',None,None
    if getattr(hydration,'status',None)!='READY_SUPPORT_CLOSED_HYDRATION_D0': return False,'ACTIVE_HYDRATION_NOT_READY',None,None
    if _status(typed_closure)!='READY_D0': return False,'ACTIVE_TYPED_CLOSURE_NOT_READY',None,None
    if getattr(typed_closure,'reproof_semantics',None)!=REPROOF_SEMANTICS: return False,'ACTIVE_REPROOF_SEMANTICS_MOVED',None,None
    try:
        binding=canonical_read_binding_root(hydration,typed_closure)
        expected_consequence=canonical_read_consequence_root(read_cert)
        _root(getattr(read_cert,'receipt_root',None),'read_certificate_root')
        _root(getattr(read_cert,'consequence_root',None),'consequence_root')
        expected_receipt=canonical_read_certificate_receipt(read_cert)
    except ValueError:
        return False,'READ_CERTIFICATE_MALFORMED',None,None
    if expected_consequence!=getattr(read_cert,'consequence_root',None): return False,'READ_CONSEQUENCE_ROOT_UNAUTHENTICATED',None,None
    if expected_receipt!=getattr(read_cert,'receipt_root',None): return False,'READ_CERTIFICATE_RECEIPT_UNAUTHENTICATED',None,None
    if binding not in tuple(getattr(read_cert,'binding_roots',())): return False,'ACTIVE_READ_WORLD_NOT_CERTIFIED',None,None
    if getattr(hydration,'receipt_root',None) not in tuple(getattr(read_cert,'member_hydration_receipt_roots',())): return False,'ACTIVE_HYDRATION_RECEIPT_NOT_CERTIFIED',None,None
    if getattr(hydration,'support_root',None) not in tuple(getattr(read_cert,'member_support_roots',())): return False,'ACTIVE_SUPPORT_ROOT_NOT_CERTIFIED',None,None
    if tuple(getattr(hydration,'support_cut',()))!=tuple(getattr(read_cert,'hydration_cut',())): return False,'ACTIVE_HYDRATION_CONSEQUENCE_MOVED',None,None
    if tuple(getattr(typed_closure,'reproof_item_ids',()))!=tuple(getattr(read_cert,'reproof_item_ids',())): return False,'ACTIVE_COMPONENT_REPROOF_MOVED',None,None
    if (getattr(typed_closure,'transition_model_root',None),getattr(typed_closure,'horizon',None),getattr(typed_closure,'future_congruence_root',None)) != (getattr(read_cert,'transition_model_root',None),getattr(read_cert,'horizon',None),getattr(read_cert,'future_congruence_root',None)):
        return False,'ACTIVE_TRANSITION_CONSEQUENCE_MOVED',None,None
    read_semantic=digest({'schema':SCHEMA,'kind':'authenticated_current_read_semantic','read_certificate_root':read_cert.receipt_root,
        'active_binding_root':binding,'typed_closure_receipt_root':typed_closure.receipt_root,
        'coverage_receipt_root':read_cert.coverage_receipt_root,'consequence_root':read_cert.consequence_root,
        'reproof_semantics':REPROOF_SEMANTICS})
    return True,'CURRENT_READ_CONSEQUENCE_AUTHENTICATED',read_semantic,binding


def _effect_refinement_current(plan:EffectRefinementPlan,intent:EffectIntent,read_cert,binding:str,obligation_root:str):
    if not isinstance(plan,EffectRefinementPlan) or not isinstance(intent,EffectIntent): return False,'EFFECT_REFINEMENT_REQUIRED',None
    if plan.status!='READY_REFINED_D0' or plan.unresolved_binding_roots: return False,'EFFECT_REFINEMENT_NOT_COMPLETE',None
    result=validate_effect_binding(plan,cert=read_cert,intent=intent,read_binding_root=binding,obligation_root=obligation_root)
    if result!='READY_EFFECT_SUBCLASS_D0': return False,result,None
    children=[c for c in plan.subclasses if binding in c.member_binding_roots and c.obligation_root==obligation_root]
    if len(children)!=1:return False,'EFFECT_SUBCLASS_NOT_UNIQUE',None
    return True,'CURRENT_EFFECT_SUBCLASS_AUTHENTICATED',effect_escalation_root(plan,children[0])


def compile_effect_handoff(read_cert, read_use, hydration, typed_closure, admission:Mapping[str,object],
                           refinement_plan:EffectRefinementPlan, effect_intent:EffectIntent, effect_obligation_root:str,
                           evidence:EffectHandoffEvidence, mutation:MutationBoundaryProjection,
                           verification:HandoffVerificationContext) -> HandoffDecision:
    try:_root(effect_obligation_root,'effect_obligation_root')
    except ValueError:return HandoffDecision(HandoffDisposition.HOLD,'EFFECT_OBLIGATION_ROOT_MALFORMED')
    read_ok,reason,read_semantic,binding=_read_consequence_current(read_cert,read_use,hydration,typed_closure)
    if not read_ok:return HandoffDecision(HandoffDisposition.HOLD,reason)
    refine_ok,reason,escalation=_effect_refinement_current(refinement_plan,effect_intent,read_cert,binding,effect_obligation_root)
    if not refine_ok:return HandoffDecision(HandoffDisposition.HOLD,reason,read_semantic)
    semantic=digest({'schema':SCHEMA,'kind':'effect_refined_current_read_semantic','current_read_semantic_root':read_semantic,
        'effect_escalation_root':escalation,'effect_obligation_root':effect_obligation_root,
        'effect_refinement_plan_root':refinement_plan.plan_root,'effect_intent_root':effect_intent.binding_root})
    admission_ok,reason=_admission_receipt_current(admission,read_cert,hydration,typed_closure)
    if not admission_ok:return HandoffDecision(HandoffDisposition.HOLD,reason,semantic,escalation)
    if evidence.owner_evidence_root!=verification.owner_evidence_root:return HandoffDecision(HandoffDisposition.HOLD,'OWNER_EVIDENCE_ROOT_STALE',semantic,escalation)
    if evidence.verifier_receipt_root!=verification.verifier_receipt_root:return HandoffDecision(HandoffDisposition.HOLD,'VERIFIER_RECEIPT_ROOT_STALE',semantic,escalation)
    if mutation.cell_id!=verification.cell_id:return HandoffDecision(HandoffDisposition.HOLD,'CELL_MISMATCH',semantic,escalation)
    if mutation.holder!=verification.holder:return HandoffDecision(HandoffDisposition.HOLD,'LEASE_HOLDER_MOVED',semantic,escalation)
    if mutation.revision!=verification.revision:return HandoffDecision(HandoffDisposition.REBIND_REQUIRED,'REVISION_MOVED',semantic,escalation)
    if mutation.configuration_root!=verification.configuration_root:return HandoffDecision(HandoffDisposition.REBIND_REQUIRED,'CONFIGURATION_MOVED',semantic,escalation)
    if mutation.support_epoch!=verification.support_epoch:return HandoffDecision(HandoffDisposition.REBIND_REQUIRED,'SUPPORT_EPOCH_MOVED',semantic,escalation)
    if mutation.transition_authority_receipt_root!=verification.transition_authority_receipt_root:return HandoffDecision(HandoffDisposition.HOLD,'TRANSITION_AUTHORITY_RECEIPT_STALE',semantic,escalation)
    if mutation.resource_fence_receipt_root!=verification.resource_fence_receipt_root:return HandoffDecision(HandoffDisposition.HOLD,'RESOURCE_FENCE_RECEIPT_STALE',semantic,escalation)
    if mutation.fence_generation!=verification.fence_generation:return HandoffDecision(HandoffDisposition.REBIND_REQUIRED,'FENCE_GENERATION_MOVED',semantic,escalation)
    if mutation.installed_fence_generation!=verification.installed_fence_generation:return HandoffDecision(HandoffDisposition.HOLD,'INSTALLED_FENCE_RECEIPT_MISMATCH',semantic,escalation)
    if mutation.fence_generation!=mutation.installed_fence_generation or verification.fence_generation!=verification.installed_fence_generation:
        return HandoffDecision(HandoffDisposition.HOLD,'FENCE_NOT_INSTALLED_CURRENT',semantic,escalation)
    if verification.now>=mutation.expires_at:return HandoffDecision(HandoffDisposition.HOLD,'LEASE_EXPIRED',semantic,escalation)
    tecc_input=digest({'schema':SCHEMA,'kind':'authenticated_effect_refined_tecc_input','semantic_handoff_root':semantic,
        'effect_escalation_root':escalation,'admission_receipt_root':admission['receipt_root'],
        'mutation_boundary_root':mutation.boundary_root,'lease_holder':mutation.holder,
        'owner_evidence_root':evidence.owner_evidence_root,'verifier_receipt_root':evidence.verifier_receipt_root,
        'required_verifier_schema':TECC_SCHEMA,'authority_minted':False,'mutation_authority':False,'effect_authority':False,'gate10':False})
    return HandoffDecision(HandoffDisposition.HOLD_TECC_REQUIRED_D0,'AUTHENTICATED_EFFECT_REFINED_CROSS_BINDING_REQUIRES_INDEPENDENT_TECC',semantic,escalation,tecc_input,TECC_SCHEMA)
