from __future__ import annotations
from dataclasses import dataclass
from k27_dynamic_navigator import digest
from memory_city_support_hydration import SupportClosedHydration
@dataclass(frozen=True)
class SupportFixedPoint:
    support_root:str; current:bool; converged:bool; terminal_states:int
    def validate(self):
        if not isinstance(self.support_root,str) or not self.support_root:raise ValueError('support_root required')
        if type(self.current) is not bool or type(self.converged) is not bool:raise ValueError('current/converged must be bool')
        if type(self.terminal_states) is not int or self.terminal_states<1:raise ValueError('terminal_states must be positive')
@dataclass(frozen=True)
class AdaptiveHydrationStrategy:
    status:str; strategy:str; certified_support_cut:tuple[str,...]; selected_bytes:int; universe_bytes:int; expected_uses:int; modeled_total_bytes:int; strategy_root:str; authority_minted:bool=False; gate10:bool=False
def compile_adaptive_hydration_strategy(hydration:SupportClosedHydration,fixed:SupportFixedPoint,*,expected_uses:int,shared_global_available:bool)->AdaptiveHydrationStrategy:
    fixed.validate()
    if type(expected_uses) is not int or expected_uses<1:raise ValueError('expected_uses must be positive')
    if type(shared_global_available) is not bool:raise ValueError('shared_global_available must be bool')
    if hydration.status!='READY_SUPPORT_CLOSED_HYDRATION_D0':return _out('HOLD_HYDRATION_NOT_READY','NONE',hydration,expected_uses,0,fixed.support_root)
    if not fixed.current:return _out('HOLD_SUPPORT_FIXED_POINT_STALE','NONE',hydration,expected_uses,0,fixed.support_root)
    if not fixed.converged or fixed.terminal_states!=1:return _out('HOLD_SUPPORT_NOT_CONVERGED','NONE',hydration,expected_uses,0,fixed.support_root)
    local_cost=hydration.selected_bytes*expected_uses; global_cost=hydration.universe_bytes
    if shared_global_available and global_cost<local_cost:return _out('READY_ADAPTIVE_D0','GLOBAL_SHARED',hydration,expected_uses,global_cost,fixed.support_root)
    return _out('READY_ADAPTIVE_D0','LOCAL_SUPPORT_CLOSED',hydration,expected_uses,local_cost,fixed.support_root)
def _out(status,strategy,h,e,cost,support_root):
    payload={'status':status,'strategy':strategy,'cut':h.support_cut,'selected':h.selected_bytes,'universe':h.universe_bytes,'expected_uses':e,'cost':cost,'support_root':support_root}
    return AdaptiveHydrationStrategy(status,strategy,h.support_cut,h.selected_bytes,h.universe_bytes,e,cost,digest(payload))
def hard13d_strategy(axes):
    if len(axes)!=13 or any(type(x) is not int or x not in (0,1,2) for x in axes):return 'HOLD_MALFORMED'
    hard=axes[:8]
    if 0 in hard:return 'HOLD_HARD_INVALID'
    if 1 in hard:return 'HOLD_UNRESOLVED'
    return 'READY_D0'
