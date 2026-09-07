from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA='AURA-O18-ATTENUATED-STABLE-OPERATION-DELEGATION-v1'
def digest(x): return sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class Disposition(str,Enum):
    ADMIT_D0='ADMIT_DELEGATED_ATTEMPT_D0'; HOLD='HOLD'
@dataclass(frozen=True)
class StableOperation:
    domain:str; semantic_root:str; action_class:str; source_incarnation_root:str; policy_root:str
    def root(self): return digest({'domain':self.domain,'semantic_root':self.semantic_root,'action_class':self.action_class,'source_incarnation_root':self.source_incarnation_root,'policy_root':self.policy_root})
@dataclass(frozen=True)
class DelegationHop:
    principal:str; scope:frozenset[str]; budget:int; generation:int; current:bool=True
@dataclass(frozen=True)
class DomainAdmission:
    domain:str; operation_root:str; admission_root:str; allowed_scope:frozenset[str]; max_budget:int; generation:int; current:bool; proof_bound:bool
@dataclass(frozen=True)
class AttemptContext:
    actor:str; workcell_root:str; workcell_generation:int; workcell_current:bool; lease_root:str; lease_current:bool; source_incarnation_root:str; requested_scope:frozenset[str]; requested_budget:int
@dataclass(frozen=True)
class Decision:
    disposition:Disposition; reason:str; operation_root:str; delegation_chain_root:str; effective_scope:tuple[str,...]; effective_budget:int; attempt_root:str|None; effect_authority:bool=False; training_authority:bool=False; checkpoint_authority:bool=False; gate10:bool=False
def chain_root(hops): return digest([{'principal':h.principal,'scope':sorted(h.scope),'budget':h.budget,'generation':h.generation} for h in hops])
def effective_authority(hops):
    if not hops:return frozenset(),0
    scope=set(hops[0].scope);budget=hops[0].budget
    for h in hops[1:]: scope.intersection_update(h.scope);budget=min(budget,h.budget)
    return frozenset(scope),budget
def decide(operation,hops,admission,ctx):
    op=operation.root();cr=chain_root(hops);scope,budget=effective_authority(hops)
    def hold(reason): return Decision(Disposition.HOLD,reason,op,cr,tuple(sorted(scope)),budget,None)
    if not hops:return hold('NO_DELEGATION_CHAIN')
    if any(not h.current for h in hops):return hold('DELEGATION_ANCESTOR_STALE')
    if any(h.budget<0 for h in hops) or ctx.requested_budget<0:return hold('MALFORMED_BUDGET')
    for parent,child in zip(hops,hops[1:]):
        if not child.scope.issubset(parent.scope) or child.budget>parent.budget:return hold('NON_ATTENUATING_DELEGATION')
    if admission.domain!=operation.domain or admission.operation_root!=op:return hold('DOMAIN_ADMISSION_OPERATION_MISMATCH')
    if not admission.current:return hold('DOMAIN_ADMISSION_STALE')
    if not admission.proof_bound:return hold('DOMAIN_ADMISSION_NOT_PROOF_BOUND')
    if not ctx.workcell_current or not ctx.lease_current:return hold('ATTEMPT_CURRENTNESS_FAILED')
    if ctx.source_incarnation_root!=operation.source_incarnation_root:return hold('SOURCE_INCARNATION_MOVED')
    allowed=scope.intersection(admission.allowed_scope);ceiling=min(budget,admission.max_budget)
    if not ctx.requested_scope.issubset(allowed):return hold('REQUESTED_SCOPE_EXCEEDS_EFFECTIVE_AUTHORITY')
    if ctx.requested_budget>ceiling:return hold('REQUESTED_BUDGET_EXCEEDS_EFFECTIVE_AUTHORITY')
    ar=digest({'schema':SCHEMA,'operation_root':op,'delegation_chain_root':cr,'admission_root':admission.admission_root,'actor':ctx.actor,'workcell_root':ctx.workcell_root,'workcell_generation':ctx.workcell_generation,'lease_root':ctx.lease_root,'source_incarnation_root':ctx.source_incarnation_root,'requested_scope':sorted(ctx.requested_scope),'requested_budget':ctx.requested_budget})
    return Decision(Disposition.ADMIT_D0,'OK_D0',op,cr,tuple(sorted(allowed)),ceiling,ar)
