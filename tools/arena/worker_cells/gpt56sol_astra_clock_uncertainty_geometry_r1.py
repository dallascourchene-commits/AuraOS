from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from itertools import permutations, product
import json

DOMAINS = ('causal','validity','media','simulation','commitment','externalization')
D0 = 'D0_NONPROMOTING'

def _canon(x): return json.dumps(x, sort_keys=True, separators=(',', ':')).encode()
def digest(x): return sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class TimeInterval:
    lo: int
    hi: int
    def __post_init__(self):
        if self.lo > self.hi: raise ValueError('interval lo>hi')
    @property
    def width(self): return self.hi - self.lo
    @property
    def midpoint(self): return (self.lo + self.hi) // 2

@dataclass(frozen=True)
class ClockRelation:
    src: str
    dst: str
    offset_lo_us: int
    offset_hi_us: int
    skew_ppm: int
    calibrated_at_us: int
    valid_for_us: int
    evidence_current: bool = True
    relation_id: str = ''
    def __post_init__(self):
        if self.src not in DOMAINS or self.dst not in DOMAINS or self.src == self.dst: raise ValueError('invalid domains')
        if self.offset_lo_us > self.offset_hi_us: raise ValueError('offset lo>hi')
        if not 0 <= self.skew_ppm < 1_000_000: raise ValueError('bad skew')
        if self.valid_for_us < 0: raise ValueError('bad validity')
    def is_current_for(self, interval: TimeInterval) -> bool:
        if not self.evidence_current: return False
        return max(abs(interval.lo-self.calibrated_at_us), abs(interval.hi-self.calibrated_at_us)) <= self.valid_for_us
    def map_point(self, t_us: int, offset_us: int, signed_skew_ppm: int) -> int:
        age = t_us - self.calibrated_at_us
        return t_us + offset_us + (age * signed_skew_ppm) // 1_000_000
    def map_interval(self, x: TimeInterval) -> TimeInterval:
        vals = [self.map_point(t,o,s) for t,o,s in product((x.lo,x.hi),(self.offset_lo_us,self.offset_hi_us),(-self.skew_ppm,self.skew_ppm))]
        return TimeInterval(min(vals),max(vals))

@dataclass(frozen=True)
class Route:
    source_domain: str
    target_domain: str
    relations: tuple[ClockRelation, ...]
    route_root: str

@dataclass(frozen=True)
class DeadlineRequirement:
    deadline_us: int

@dataclass(frozen=True)
class WindowRequirement:
    start_us: int
    end_us: int
    def __post_init__(self):
        if self.start_us > self.end_us: raise ValueError('window start>end')

@dataclass(frozen=True)
class RouteDecision:
    status: str
    mapped: TimeInterval | None
    reason: str
    route_root: str
    k27_coordinate: str | None = None
    authority: str = D0
    gate10: bool = False
    effect_authority: bool = False

def compile_route(source_domain: str, target_domain: str, relations) -> Route:
    if source_domain not in DOMAINS or target_domain not in DOMAINS: raise ValueError('bad route endpoint')
    rels=tuple(relations); by_src={}
    for r in rels: by_src.setdefault(r.src,[]).append(r)
    chain=[]; cur=source_domain; seen=set()
    while cur != target_domain:
        if cur in seen: raise ValueError('route cycle')
        seen.add(cur); choices=by_src.get(cur,[])
        if len(choices)!=1: raise ValueError('route missing or ambiguous')
        r=choices[0]; chain.append(r); cur=r.dst
        if len(chain)>len(rels): raise ValueError('route cycle')
    if len(chain)!=len(rels): raise ValueError('unused relation declarations')
    root=digest({'source':source_domain,'target':target_domain,'relations':[{'src':r.src,'dst':r.dst,'olo':r.offset_lo_us,'ohi':r.offset_hi_us,'skew':r.skew_ppm,'cal':r.calibrated_at_us,'valid':r.valid_for_us,'current':r.evidence_current,'id':r.relation_id} for r in chain]})
    return Route(source_domain,target_domain,tuple(chain),root)

def propagate(route: Route, source: TimeInterval):
    x=source
    for r in route.relations:
        if not r.is_current_for(x): return None, f'stale_relation:{r.relation_id or r.src+"->"+r.dst}'
        x=r.map_interval(x)
    return x,''

def decide(route: Route, source: TimeInterval, requirement, *, k27_coordinate=None) -> RouteDecision:
    mapped,reason=propagate(route,source)
    if mapped is None: return RouteDecision('HOLD_CURRENTNESS',None,reason,route.route_root,k27_coordinate)
    if isinstance(requirement,DeadlineRequirement):
        d=requirement.deadline_us
        if mapped.hi<=d: status,reason='READY_D0','all admissible clock realizations meet deadline'
        elif mapped.lo>d: status,reason='HOLD_DEADLINE_MISS','all admissible clock realizations miss deadline'
        else: status,reason='HOLD_TEMPORAL_UNCERTAINTY','admissible clock realizations straddle deadline'
    elif isinstance(requirement,WindowRequirement):
        a,b=requirement.start_us,requirement.end_us
        if mapped.lo>=a and mapped.hi<=b: status,reason='READY_D0','all admissible realizations inside window'
        elif mapped.hi<a or mapped.lo>b: status,reason='HOLD_WINDOW_MISS','all admissible realizations outside window'
        else: status,reason='HOLD_TEMPORAL_UNCERTAINTY','admissible realizations cross window boundary'
    else: raise TypeError('unsupported requirement')
    return RouteDecision(status,mapped,reason,route.route_root,k27_coordinate)

def naive_midpoint_deadline_accept(route: Route, source: TimeInterval, deadline_us: int) -> bool:
    x=source.midpoint
    for r in route.relations:
        x=r.map_point(x,(r.offset_lo_us+r.offset_hi_us)//2,0)
    return x<=deadline_us

def brute_extrema(route: Route, source: TimeInterval) -> TimeInterval:
    vals={source.lo,source.hi}
    for r in route.relations:
        nxt=set()
        for t in vals:
            for off in (r.offset_lo_us,r.offset_hi_us):
                for skew in (-r.skew_ppm,r.skew_ppm): nxt.add(r.map_point(t,off,skew))
        vals=nxt
    return TimeInterval(min(vals),max(vals))

def permutation_roots(source_domain,target_domain,relations):
    return {compile_route(source_domain,target_domain,p).route_root for p in permutations(tuple(relations))}
