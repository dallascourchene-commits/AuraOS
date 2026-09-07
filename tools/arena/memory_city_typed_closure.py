from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from memory_city_navigator import NavigatorError, digest
from memory_city_contingent_hydration import (
    ContingentHydrationStrategy, DemandBranch, HydrationItem, InvariantSupport,
    StrategyDisposition, compile_contingent_hydration, invariant_components, validate_strategy_at_use,
)

D0='D0_NONPROMOTING'
SCHEMA='AURA-MEMORY-CITY-TYPED-CLOSURE-v1'

class TypedClosureDisposition(str, Enum):
    READY='READY_D0'
    HOLD_BASE_HYDRATION='HOLD_BASE_HYDRATION'
    HOLD_INCOMPLETE_RELATION='HOLD_INCOMPLETE_RELATION'
    HOLD_INFLUENCE_IDENTITY='HOLD_INFLUENCE_IDENTITY'
    HOLD_FUTURE_CONGRUENCE='HOLD_FUTURE_CONGRUENCE'
    HOLD_SUPPORT_IDENTITY='HOLD_SUPPORT_IDENTITY'

@dataclass(frozen=True)
class InfluenceGraph:
    generation:int
    edges:tuple[tuple[str,str],...]
    complete:bool=True
    def __post_init__(self):
        if type(self.generation) is not int or self.generation<0: raise NavigatorError('influence generation must be nonnegative')
        norm=[]
        for edge in self.edges:
            if len(edge)!=2 or not all(isinstance(x,str) and x for x in edge): raise NavigatorError('directed influence edge must have two ids')
            if edge[0]==edge[1]: raise NavigatorError('self influence edge not allowed')
            norm.append(tuple(edge))
        if len(set(norm))!=len(norm): raise NavigatorError('duplicate directed influence edge')
        if type(self.complete) is not bool: raise NavigatorError('complete must be bool')
    @property
    def normalized_edges(self): return tuple(sorted(self.edges))
    @property
    def influence_root(self):
        return digest({'schema':'AURA-MEMORY-CITY-INFLUENCE-v1','generation':self.generation,'complete':self.complete,'edges':[list(e) for e in self.normalized_edges]})

@dataclass(frozen=True)
class TypedClosureCertificate:
    disposition:TypedClosureDisposition
    hydration:ContingentHydrationStrategy
    support_root:str
    influence_root:str
    reproof_item_ids:tuple[str,...]
    horizon:int
    transition_model_root:str
    future_congruence_root:str|None
    receipt_root:str
    reason:str=''
    authority:str=D0
    effect_authority:bool=False
    gate10:bool=False

@dataclass(frozen=True)
class TypedClosureUseDecision:
    disposition:TypedClosureDisposition
    branch_id:str
    hydrate_item_ids:tuple[str,...]
    reproof_item_ids:tuple[str,...]
    reason:str
    authority:str=D0
    effect_authority:bool=False
    gate10:bool=False


def directed_descendants(item_ids:Iterable[str], graph:InfluenceGraph, universe:Iterable[str])->tuple[str,...]:
    """Raw item-level reachability retained only as a falsifier baseline."""
    universe=set(universe); starts=set(item_ids)
    if not starts.issubset(universe): raise NavigatorError('changed evidence references unknown item')
    adj={x:set() for x in universe}
    for a,b in graph.edges:
        if a not in universe or b not in universe: raise NavigatorError('influence references unknown item')
        adj[a].add(b)
    seen=set(starts); stack=sorted(starts, reverse=True)
    while stack:
        x=stack.pop()
        for y in sorted(adj[x]):
            if y not in seen: seen.add(y); stack.append(y)
    return tuple(sorted(seen))


def typed_reproof_descendants(item_ids:Iterable[str], graph:InfluenceGraph, support:InvariantSupport, universe:Iterable[str])->tuple[str,...]:
    """Hard-component-seeded directed reproof closure.

    Hard support components are indivisible reproof units. Directed influence is
    lifted between those components and retains direction.
    """
    universe=tuple(sorted(set(universe))); starts=set(item_ids)
    if not starts.issubset(set(universe)): raise NavigatorError('changed evidence references unknown item')
    components=invariant_components(universe,support)
    item_to_component={item:component for component in components for item in component}
    adjacency={component:set() for component in components}
    for a,b in graph.edges:
        if a not in item_to_component or b not in item_to_component: raise NavigatorError('influence references unknown item')
        source,target=item_to_component[a],item_to_component[b]
        if source!=target: adjacency[source].add(target)
    seen={item_to_component[x] for x in starts}; stack=sorted(seen,reverse=True)
    while stack:
        component=stack.pop()
        for target in sorted(adjacency[component]):
            if target not in seen: seen.add(target); stack.append(target)
    return tuple(sorted(item for component in seen for item in component))


def compile_typed_closure(
    items:tuple[HydrationItem,...], branches:tuple[DemandBranch,...], support:InvariantSupport,
    influence:InfluenceGraph, *, changed_evidence_item_ids:tuple[str,...], max_resident_bytes:int,
    reveal_tick:int, deadline_tick:int, transition_model_root:str, horizon:int=0,
    future_congruence_root:str|None=None, support_complete:bool=True,
)->TypedClosureCertificate:
    if type(horizon) is not int or horizon<0: raise NavigatorError('horizon must be nonnegative')
    if not isinstance(transition_model_root,str) or not transition_model_root: raise NavigatorError('transition_model_root required')
    base=compile_contingent_hydration(items,branches,support,max_resident_bytes=max_resident_bytes,reveal_tick=reveal_tick,deadline_tick=deadline_tick)
    universe=tuple(x.item_id for x in items)
    reproof=typed_reproof_descendants(changed_evidence_item_ids,influence,support,universe)
    disp=TypedClosureDisposition.READY; reason=''
    if base.disposition is not StrategyDisposition.READY:
        disp=TypedClosureDisposition.HOLD_BASE_HYDRATION; reason='base_hydration_not_ready'
    elif not support_complete or not influence.complete:
        disp=TypedClosureDisposition.HOLD_INCOMPLETE_RELATION; reason='support_or_influence_completeness_unknown'
    elif horizon>0 and not future_congruence_root:
        disp=TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE; reason='persistent_reuse_requires_future_congruence'
    payload={'schema':SCHEMA,'disposition':disp.value,'base_receipt':base.receipt_root,'support_root':support.support_root,'influence_root':influence.influence_root,'reproof':list(reproof),'horizon':horizon,'transition_model_root':transition_model_root,'future_congruence_root':future_congruence_root,'support_complete':support_complete}
    return TypedClosureCertificate(disp,base,support.support_root,influence.influence_root,reproof,horizon,transition_model_root,future_congruence_root,digest(payload),reason)


def validate_typed_closure_at_use(cert:TypedClosureCertificate, *, branch_id:str, support:InvariantSupport,
    influence:InfluenceGraph, transition_model_root:str, future_congruence_root:str|None=None)->TypedClosureUseDecision:
    base=validate_strategy_at_use(cert.hydration,branch_id=branch_id,support=support)
    if base.disposition is not StrategyDisposition.READY:
        return TypedClosureUseDecision(TypedClosureDisposition.HOLD_SUPPORT_IDENTITY,branch_id,(),(),base.reason)
    if influence.influence_root!=cert.influence_root:
        return TypedClosureUseDecision(TypedClosureDisposition.HOLD_INFLUENCE_IDENTITY,branch_id,(),(), 'influence_identity_changed')
    if cert.horizon>0:
        if transition_model_root!=cert.transition_model_root or future_congruence_root!=cert.future_congruence_root:
            return TypedClosureUseDecision(TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE,branch_id,(),(), 'future_transition_congruence_changed')
    elif transition_model_root!=cert.transition_model_root:
        return TypedClosureUseDecision(TypedClosureDisposition.HOLD_FUTURE_CONGRUENCE,branch_id,(),(), 'h0_requires_exact_transition_rebind')
    if cert.disposition is not TypedClosureDisposition.READY:
        return TypedClosureUseDecision(cert.disposition,branch_id,(),(),cert.reason)
    return TypedClosureUseDecision(TypedClosureDisposition.READY,branch_id,base.hydrate_item_ids,cert.reproof_item_ids,'typed_support_component_seeded_directed_reproof')


def symmetrized_union_closure(starts:Iterable[str], support:InvariantSupport, influence:InfluenceGraph, universe:Iterable[str])->tuple[str,...]:
    universe=set(universe); adj={x:set() for x in universe}
    for edge in support.hyperedges:
        for a in edge:
            for b in edge:
                if a!=b: adj[a].add(b)
    for a,b in influence.edges:
        adj[a].add(b); adj[b].add(a)
    seen=set(starts); stack=list(starts)
    while stack:
        x=stack.pop()
        for y in adj[x]:
            if y not in seen: seen.add(y); stack.append(y)
    return tuple(sorted(seen))
