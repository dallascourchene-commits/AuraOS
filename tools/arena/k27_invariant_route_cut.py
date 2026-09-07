from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from k27_dynamic_navigator import digest
@dataclass(frozen=True)
class SupportHyperedge:
    invariant_id:str; members:frozenset[str]; hard:bool=True
    def validate(self):
        if not isinstance(self.invariant_id,str) or not self.invariant_id:raise ValueError('invariant_id required')
        if not isinstance(self.members,frozenset) or not self.members or any(not isinstance(x,str) or not x for x in self.members):raise ValueError('members must be a nonempty frozenset of IDs')
        if type(self.hard) is not bool:raise ValueError('hard must be bool')
@dataclass(frozen=True)
class SupportBeliefState:
    state_root:str; edges:tuple[SupportHyperedge,...]; complete:bool; current:bool
    def validate(self):
        if not isinstance(self.state_root,str) or not self.state_root:raise ValueError('state_root required')
        if type(self.complete) is not bool or type(self.current) is not bool:raise ValueError('complete/current must be bool')
        ids=set()
        for e in self.edges:
            e.validate()
            if e.invariant_id in ids:raise ValueError('duplicate invariant_id')
            ids.add(e.invariant_id)
@dataclass(frozen=True)
class InvariantRouteCut:
    status:str; direct_dependencies:tuple[str,...]; safe_support_cut:tuple[str,...]; crossing_invariants:tuple[str,...]; belief_state_roots:tuple[str,...]; cut_root:str; local_reuse_allowed:bool; authority_minted:bool=False; gate10:bool=False
def _hard_map(s):s.validate(); return {e.invariant_id:e.members for e in s.edges if e.hard}
def _hold(status,direct,states,crossing,cut):
    roots=tuple(s.state_root for s in states); payload={'status':status,'direct':direct,'cut':tuple(sorted(set(cut))),'crossing':tuple(sorted(crossing)),'belief_state_roots':roots}
    return InvariantRouteCut(status,direct,tuple(sorted(set(cut))),tuple(sorted(crossing)),roots,digest(payload),False)
def compile_invariant_route_cut(direct_dependencies:Iterable[str],belief_states:Iterable[SupportBeliefState])->InvariantRouteCut:
    direct=tuple(sorted(set(direct_dependencies)))
    if not direct or any(not isinstance(x,str) or not x for x in direct):raise ValueError('nonempty direct dependencies required')
    states=tuple(belief_states)
    if not states:return _hold('HOLD_SUPPORT_UNKNOWN',direct,states,(),direct)
    for s in states:s.validate()
    if any(not s.current for s in states):return _hold('HOLD_SUPPORT_STALE',direct,states,(),direct)
    if any(not s.complete for s in states):return _hold('HOLD_SUPPORT_INCOMPLETE',direct,states,(),direct)
    maps=[_hard_map(s) for s in states]; all_ids=set().union(*(m.keys() for m in maps)); invariant={}; unstable=[]
    for iid in sorted(all_ids):
        supports=[m.get(iid) for m in maps]
        if any(x is None for x in supports) or len(set(supports))!=1:unstable.append(iid)
        else:invariant[iid]=supports[0]
    if unstable:
        conservative=set(direct)
        for m in maps:
            for support in m.values():conservative.update(support)
        return _hold('HOLD_REFLEXIVE_SUPPORT_AMBIGUITY',direct,states,tuple(unstable),tuple(sorted(conservative)))
    closure=set(direct); crossing=set(); changed=True
    while changed:
        changed=False
        for iid,members in invariant.items():
            if closure.intersection(members) and not members.issubset(closure):crossing.add(iid); closure.update(members); changed=True
    roots=tuple(s.state_root for s in states); payload={'status':'READY_INVARIANT_ROUTE_CUT_D0','direct':direct,'cut':tuple(sorted(closure)),'crossing':tuple(sorted(crossing)),'belief_state_roots':roots}
    return InvariantRouteCut('READY_INVARIANT_ROUTE_CUT_D0',direct,tuple(sorted(closure)),tuple(sorted(crossing)),roots,digest(payload),True)
def affected_by_change(cut,changed_object_id):
    if not isinstance(changed_object_id,str) or not changed_object_id:raise ValueError('changed_object_id required')
    return cut.status!='READY_INVARIANT_ROUTE_CUT_D0' or changed_object_id in cut.safe_support_cut
def hard13d_route_cut(axes):
    if len(axes)!=13 or any(type(x) is not int or x not in (0,1,2) for x in axes):return 'HOLD_MALFORMED'
    hard=axes[:8]
    if 0 in hard:return 'HOLD_HARD_INVALID'
    if 1 in hard:return 'HOLD_UNRESOLVED'
    return 'READY_D0'
