from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
import json

D0='D0_NONPROMOTING'; UNKNOWN=-1

def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x): return sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class DurationInterval:
    lo:int; hi:int
    def __post_init__(self):
        if self.lo < 0 or self.lo > self.hi: raise ValueError('bad duration interval')
    @property
    def midpoint(self): return (self.lo+self.hi)//2
    def add(self,other:'DurationInterval')->'DurationInterval':return DurationInterval(self.lo+other.lo,self.hi+other.hi)

@dataclass(frozen=True)
class EvidenceQuery:
    name:str; bit:int; cost:int; duration:DurationInterval; private:bool=False; premise_bit:int|None=0; clock_current:bool=True
    def __post_init__(self):
        if self.bit<0:raise ValueError('bit must be >=0')
        if self.cost<0:raise ValueError('negative query cost')
        if self.private and self.premise_bit is None:raise ValueError('private query requires premise bit')

@dataclass(frozen=True)
class RefreshAction:
    name:str; cost:int; duration:DurationInterval; clock_current:bool=True
    def __post_init__(self):
        if self.cost<0:raise ValueError('negative refresh cost')

@dataclass(frozen=True)
class TreeNode:
    kind:str; action:str|None; decision:bool|None; zero:'TreeNode|None'=None; one:'TreeNode|None'=None; next:'TreeNode|None'=None

@dataclass(frozen=True)
class ChoreographyPlan:
    status:str; worst_cost:int; worst_duration:DurationInterval; tree:TreeNode|None; reason:str=''; authority:str=D0; gate10:bool=False; effect_authority:bool=False; k27_coordinate:str|None=None; plan_root:str=''

@dataclass(frozen=True)
class _Candidate:
    worst_cost:int; worst_duration:DurationInterval; tree:TreeNode; key:str

def _assignments(known):
    for mask in range(1<<len(known)):
        bits=[];ok=True
        for i,k in enumerate(known):
            b=(mask>>i)&1
            if k!=UNKNOWN and k!=b:ok=False;break
            bits.append(b)
        if ok:yield tuple(bits)

def _truth(table,bits):return bool(table[sum((b<<i) for i,b in enumerate(bits))])
def uniform_decision(table,known):
    vals={_truth(table,b) for b in _assignments(known)}
    return next(iter(vals)) if len(vals)==1 else None

def _legal_query(q,known):
    if not q.clock_current or known[q.bit]!=UNKNOWN:return False
    if q.private and (q.premise_bit is None or known[q.premise_bit]!=1):return False
    return True

def _tree_obj(t):
    if t is None:return None
    return {'kind':t.kind,'action':t.action,'decision':t.decision,'zero':_tree_obj(t.zero),'one':_tree_obj(t.one),'next':_tree_obj(t.next)}

def _pick(cands):return min(cands,key=lambda c:(c.worst_cost,c.worst_duration.hi,c.worst_duration.lo,c.key)) if cands else None

def compile_choreography(truth_table,queries,refresh,deadline_us,*,duration_mode='robust',k27_coordinate=None):
    """Exact finite evidence tree; robust mode admits only all-realization deadline-safe paths."""
    table=tuple(bool(x) for x in truth_table); queries=tuple(sorted(tuple(queries),key=lambda q:(q.bit,q.name)))
    n=(max(q.bit for q in queries)+1) if queries else 1
    if len(table)!=(1<<n):raise ValueError('truth table length mismatch')
    if deadline_us<0:raise ValueError('negative deadline')
    if duration_mode not in ('robust','midpoint'):raise ValueError('bad duration mode')
    if len({q.name for q in queries})!=len(queries) or len({q.bit for q in queries})!=len(queries):raise ValueError('duplicate query')
    def fits(e,d):return (e.hi+d.hi<=deadline_us) if duration_mode=='robust' else (e.midpoint+d.midpoint<=deadline_us)
    @lru_cache(maxsize=None)
    def solve(known,refreshed,elo,ehi):
        elapsed=DurationInterval(elo,ehi);u=uniform_decision(table,known)
        if u is False:
            t=TreeNode('terminal',None,False);return _Candidate(0,elapsed,t,digest(_tree_obj(t)))
        if u is True and refreshed:
            t=TreeNode('terminal',None,True);return _Candidate(0,elapsed,t,digest(_tree_obj(t)))
        c=[]
        if u is True and not refreshed and refresh.clock_current and fits(elapsed,refresh.duration):
            e2=elapsed.add(refresh.duration);sub=solve(known,True,e2.lo,e2.hi)
            if sub:
                t=TreeNode('refresh',refresh.name,None,next=sub.tree);c.append(_Candidate(refresh.cost+sub.worst_cost,sub.worst_duration,t,digest(_tree_obj(t))))
        if u is None:
            for q in queries:
                if not _legal_query(q,known) or not fits(elapsed,q.duration):continue
                e2=elapsed.add(q.duration);bs=[]
                for b in (0,1):
                    kk=list(known);kk[q.bit]=b;bs.append(solve(tuple(kk),refreshed,e2.lo,e2.hi))
                if None in bs:continue
                z,o=bs;cost=q.cost+max(z.worst_cost,o.worst_cost);wd=DurationInterval(max(z.worst_duration.lo,o.worst_duration.lo),max(z.worst_duration.hi,o.worst_duration.hi));t=TreeNode('query',q.name,None,zero=z.tree,one=o.tree);c.append(_Candidate(cost,wd,t,digest(_tree_obj(t))))
        return _pick(c)
    best=solve(tuple([UNKNOWN]*n),False,0,0)
    if not best:return ChoreographyPlan('HOLD_NO_CHOREOGRAPHY',0,DurationInterval(0,0),None,'no deadline-feasible exact evidence choreography',k27_coordinate=k27_coordinate)
    root=digest({'mode':duration_mode,'deadline':deadline_us,'truth':list(table),'queries':[{'name':q.name,'bit':q.bit,'cost':q.cost,'duration':[q.duration.lo,q.duration.hi],'private':q.private,'premise':q.premise_bit,'current':q.clock_current} for q in queries],'refresh':{'name':refresh.name,'cost':refresh.cost,'duration':[refresh.duration.lo,refresh.duration.hi],'current':refresh.clock_current},'tree':_tree_obj(best.tree),'worst_cost':best.worst_cost,'worst_duration':[best.worst_duration.lo,best.worst_duration.hi]})
    return ChoreographyPlan('READY_D0',best.worst_cost,best.worst_duration,best.tree,k27_coordinate=k27_coordinate,plan_root=root)

def validate_tree(truth_table,queries,refresh,tree,deadline_us,*,robust=True):
    qmap={q.name:q for q in queries};table=tuple(bool(x) for x in truth_table);n=len(queries);fail=[];max_cost=max_hi=0
    for mask in range(1<<n):
        bits=tuple((mask>>i)&1 for i in range(n));known=[UNKNOWN]*n;e=DurationInterval(0,0);cost=0;refreshed=False;node=tree
        while node and node.kind!='terminal':
            if node.kind=='query':
                q=qmap[node.action]
                if q.private and (q.premise_bit is None or known[q.premise_bit]!=1):fail.append(('private_before_premise',mask,node.action))
                if not q.clock_current:fail.append(('stale_query',mask,node.action));break
                e=e.add(q.duration);cost+=q.cost;known[q.bit]=bits[q.bit];node=node.one if bits[q.bit] else node.zero
            elif node.kind=='refresh':
                if not refresh.clock_current:fail.append(('stale_refresh',mask,node.action));break
                e=e.add(refresh.duration);cost+=refresh.cost;refreshed=True;node=node.next
            else:fail.append(('bad_node',mask,node.kind));break
        if node is None:fail.append(('missing_terminal',mask,''));continue
        if node.kind=='terminal':
            expect=_truth(table,bits)
            if node.decision!=expect:fail.append(('decision_mismatch',mask,''))
            if node.decision and not refreshed:fail.append(('positive_without_refresh',mask,''))
            if (e.hi if robust else e.midpoint)>deadline_us:fail.append(('deadline',mask,''))
        max_cost=max(max_cost,cost);max_hi=max(max_hi,e.hi)
    return {'failures':tuple(fail),'worst_cost':max_cost,'worst_duration_hi':max_hi}

def robustly_safe(plan,truth_table,queries,refresh,deadline_us):return plan.status=='READY_D0' and plan.tree is not None and not validate_tree(truth_table,queries,refresh,plan.tree,deadline_us,robust=True)['failures']
