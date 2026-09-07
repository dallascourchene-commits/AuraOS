from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
from hashlib import sha256
import json

DOMAINS=('causal','validity','media','simulation','commitment','externalization')
HARD=frozenset({'causal','validity','commitment','externalization'})
D0='D0_NONPROMOTING'

def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x): return sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class TemporalPoint:
    causal:int
    validity:int
    media:int
    simulation:int
    commitment:int
    externalization:int
    def as_dict(self): return {d:getattr(self,d) for d in DOMAINS}

@dataclass(frozen=True)
class TemporalRule:
    domain:str
    relation:str
    value:int
    tolerance:int=0
    def __post_init__(self):
        if self.domain not in DOMAINS: raise ValueError('unknown domain')
        if self.relation not in ('eq','ge','le','within'): raise ValueError('bad relation')
        if self.tolerance<0: raise ValueError('negative tolerance')

@dataclass(frozen=True)
class Sensitivity:
    domain:str
    error_if_coarse:int
    exact_cost:int
    def __post_init__(self):
        if self.domain not in DOMAINS: raise ValueError('unknown domain')
        if self.error_if_coarse<0 or self.exact_cost<0: raise ValueError('negative budget term')

@dataclass(frozen=True)
class ConsequenceBudget:
    max_error:int
    max_cost:int
    hard_domains:frozenset[str]=HARD
    def __post_init__(self):
        if self.max_error<0 or self.max_cost<0: raise ValueError('negative contract budget')
        if not self.hard_domains.issubset(DOMAINS): raise ValueError('unknown hard domain')

@dataclass(frozen=True)
class ExactnessPlan:
    status:str
    exact_domains:frozenset[str]
    bounded_error:int
    exact_cost:int
    reason:str=''
    authority:str=D0
    gate10:bool=False
    effect_authority:bool=False

@dataclass(frozen=True)
class TemporalRepairLease:
    edge_key:str
    planned_at:TemporalPoint
    rules:tuple[TemporalRule,...]
    exact_domains:frozenset[str]
    plan_root:str
    authority:str=D0
    gate10:bool=False
    effect_authority:bool=False

@dataclass(frozen=True)
class UseDecision:
    status:str
    violations:tuple[str,...]
    edge_key:str
    authority:str=D0
    gate10:bool=False
    effect_authority:bool=False

def _sensitivity_map(sensitivities):
    out={}
    for s in sensitivities:
        if s.domain in out: raise ValueError('duplicate sensitivity domain')
        out[s.domain]=s
    for d in DOMAINS:
        out.setdefault(d,Sensitivity(d,0,0))
    return out

def compile_exactness(sensitivities, budget:ConsequenceBudget):
    """Backward consequence budget -> minimum-cost typed exactness plan.

    Hard domains are noncompensatory. Soft-domain coarsening contributes a
    conservative error bound. The compiler exhaustively checks the tiny
    six-domain lattice, so discrete/nonconvex cost choices are handled without
    pretending a differentiable adjoint is already proven.
    """
    sm=_sensitivity_map(sensitivities)
    hard=frozenset(budget.hard_domains)
    if any(sm[d].exact_cost>budget.max_cost for d in hard):
        return ExactnessPlan('HOLD_COST',hard,0,sum(sm[d].exact_cost for d in hard),'hard exactness exceeds cost budget')
    soft=[d for d in DOMAINS if d not in hard]
    feasible=[]
    for r in range(len(soft)+1):
        for chosen in combinations(soft,r):
            exact=hard|frozenset(chosen)
            cost=sum(sm[d].exact_cost for d in exact)
            err=sum(sm[d].error_if_coarse for d in DOMAINS if d not in exact)
            if cost<=budget.max_cost and err<=budget.max_error:
                feasible.append((cost,err,tuple(sorted(exact))))
    if not feasible:
        min_hard=sum(sm[d].exact_cost for d in hard)
        return ExactnessPlan('HOLD_NO_FEASIBLE_PLAN',hard,sum(sm[d].error_if_coarse for d in soft),min_hard,'no exactness subset meets consequence+cost budgets')
    cost,err,exact=sorted(feasible,key=lambda x:(x[0],x[1],x[2]))[0]
    return ExactnessPlan('READY_D0',frozenset(exact),err,cost)

def _rule_ok(rule:TemporalRule, point:TemporalPoint):
    v=getattr(point,rule.domain)
    if rule.relation=='eq': return v==rule.value
    if rule.relation=='ge': return v>=rule.value
    if rule.relation=='le': return v<=rule.value
    return abs(v-rule.value)<=rule.tolerance

def issue_lease(edge_key, planned_at, rules, plan:ExactnessPlan):
    if plan.status!='READY_D0': raise ValueError('cannot lease from HOLD plan')
    rules=tuple(rules)
    violations=[r.domain for r in rules if r.domain in plan.exact_domains and not _rule_ok(r,planned_at)]
    if violations: raise ValueError('invalid plan-time temporal witness:'+','.join(sorted(violations)))
    root=digest({'edge':edge_key,'planned_at':planned_at.as_dict(),'rules':[r.__dict__ for r in rules],'exact':sorted(plan.exact_domains),'error':plan.bounded_error,'cost':plan.exact_cost})
    return TemporalRepairLease(edge_key,planned_at,rules,plan.exact_domains,root)

def validate_at_use(lease:TemporalRepairLease, now:TemporalPoint):
    violations=[]
    for r in lease.rules:
        if r.domain in lease.exact_domains and not _rule_ok(r,now):
            violations.append(f'{r.domain}:{r.relation}:{r.value}')
    return UseDecision('READY_D0' if not violations else 'HOLD_TEMPORAL_REPROOF',tuple(sorted(violations)),lease.edge_key)

def scalar_collision(a:TemporalPoint,b:TemporalPoint,scalar_domains=('causal',)):
    return all(getattr(a,d)==getattr(b,d) for d in scalar_domains) and a.as_dict()!=b.as_dict()

def plan_root(sensitivities,budget):
    p=compile_exactness(sensitivities,budget)
    return digest({'sens':[s.__dict__ for s in sensitivities],'budget':{'max_error':budget.max_error,'max_cost':budget.max_cost,'hard':sorted(budget.hard_domains)},'result':{'status':p.status,'exact':sorted(p.exact_domains),'err':p.bounded_error,'cost':p.exact_cost}})
