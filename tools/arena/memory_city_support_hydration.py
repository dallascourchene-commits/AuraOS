from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable,Mapping
from k27_dynamic_navigator import digest
from k27_invariant_route_cut import SupportBeliefState,compile_invariant_route_cut
from memory_city_navigator import SourceSpanLocator
from memory_city_hydration_plan import HydrationPlanDisposition,compile_hydration_plan
@dataclass(frozen=True)
class SupportClosedHydration:
    status:str; support_cut:tuple[str,...]; missing_objects:tuple[str,...]; selected_bytes:int; universe_bytes:int; hydration_fraction:float; plan_root:str; receipt_root:str; authority_minted:bool=False; gate10:bool=False; support_root:str=''
def compile_support_closed_hydration(direct_objects:Iterable[str],belief_states:Iterable[SupportBeliefState],locator_by_object:Mapping[str,SourceSpanLocator],*,max_hydration_bytes:int)->SupportClosedHydration:
    cut=compile_invariant_route_cut(direct_objects,belief_states); universe=sum(x.span_bytes for x in locator_by_object.values())
    if cut.status!='READY_INVARIANT_ROUTE_CUT_D0':return _out('HOLD_ROUTE_SUPPORT',cut.safe_support_cut,(),0,universe,cut.cut_root,cut.cut_root)
    missing=tuple(sorted(set(cut.safe_support_cut)-set(locator_by_object)))
    if missing:return _out('HOLD_SPAN_MAP_GAP',cut.safe_support_cut,missing,0,universe,cut.cut_root,cut.cut_root)
    plan=compile_hydration_plan(tuple(locator_by_object[x] for x in cut.safe_support_cut),max_hydration_bytes=max_hydration_bytes)
    if plan.disposition is HydrationPlanDisposition.HOLD_COLLISION:status='HOLD_SPAN_COLLISION'
    elif plan.disposition is HydrationPlanDisposition.HOLD_BUDGET:status='HOLD_HYDRATION_BUDGET'
    else:status='READY_SUPPORT_CLOSED_HYDRATION_D0'
    return _out(status,cut.safe_support_cut,(),plan.selected_bytes,universe,plan.receipt_root,cut.cut_root)
def _out(status,cut,missing,selected,universe,plan_root,support_root):
    fraction=selected/universe if universe else 0.0; payload={'status':status,'support_cut':tuple(cut),'missing':tuple(missing),'selected':selected,'universe':universe,'plan_root':plan_root,'support_root':support_root}
    return SupportClosedHydration(status,tuple(cut),tuple(missing),selected,universe,fraction,plan_root,digest(payload),False,False,support_root)
