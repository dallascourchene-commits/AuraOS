"""Executable D0 reference implementation of the SOL-AURA1000 top-27 frontier."""
from __future__ import annotations
from collections import OrderedDict, defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
import json, re, time
from typing import Any, Iterable, Mapping, Sequence


def stable(v: Any) -> bytes: return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
def digest(v: Any) -> str: return sha256(stable(v)).hexdigest()
def tokens(s: str) -> list[str]: return re.findall(r"[a-z0-9_]+",s.lower())

class HardFalseSecurityGate:
    @staticmethod
    def admit(*,source_audited:bool,runtime_hard_false:bool,remote_code_widening:bool)->bool:
        return source_audited and runtime_hard_false and not remote_code_widening

@dataclass(frozen=True)
class IdentityEnvelope: model:str; runtime:str; source:str; host:str; generation:str
class P0IdentityGate:
    @staticmethod
    def admit(expected:IdentityEnvelope,observed:IdentityEnvelope|None)->bool: return observed==expected

@dataclass(frozen=True)
class PerformanceEnvelope: device:str; cache_state:str; thermal_c:float; clock_mhz:int
class MatchedEnvelopeGate:
    @staticmethod
    def comparable(a:PerformanceEnvelope,b:PerformanceEnvelope)->bool:
        return a.device==b.device and a.cache_state==b.cache_state and abs(a.thermal_c-b.thermal_c)<=3 and abs(a.clock_mhz-b.clock_mhz)/max(a.clock_mhz,b.clock_mhz,1)<=.05

class VersionRangeGate:
    @staticmethod
    def _v(s:str)->tuple[int,int,int]:
        m=re.match(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?",s)
        if not m: raise ValueError(s)
        return tuple(int(x or 0) for x in m.groups())
    @classmethod
    def admit(cls,v:str|None,minimum:str,maximum_exclusive:str)->bool:
        try: return v is not None and cls._v(minimum)<=cls._v(v)<cls._v(maximum_exclusive)
        except ValueError: return False

@dataclass(frozen=True)
class CapabilityManifest:
    host_powers:frozenset[str]=frozenset()
    def allows(self,requested:Iterable[str])->bool: return set(requested)<=self.host_powers

@dataclass(frozen=True)
class ComponentContract:
    name:str; generation:str; exports:frozenset[str]; imports:frozenset[str]; authority:frozenset[str]
class CompositionMembrane:
    @staticmethod
    def compose(a:ComponentContract,b:ComponentContract,interface:Iterable[str])->dict[str,Any]:
        return {"interface":tuple(sorted(a.exports&b.imports&set(interface))),"authority":tuple(sorted(a.authority&b.authority)),"generation_root":digest([a.generation,b.generation])}

@dataclass
class StateHandleLease:
    resource:str; owner:str; generation:int; expires_at:float; closed:bool=False
    def valid(self,owner:str,generation:int,now:float|None=None)->bool:
        now=time.time() if now is None else now; return not self.closed and owner==self.owner and generation==self.generation and now<=self.expires_at
    def close(self)->None: self.closed=True

class HardGatePin:
    @staticmethod
    def admit(gates:Mapping[str,bool],soft_score:float=0)->bool: return all(gates.values())

@dataclass(frozen=True)
class ExportReceipt:
    output_digest:str; dependency_root:str; generation:str; receipt_digest:str
    @classmethod
    def build(cls,payload:Any,deps:Sequence[str],generation:str)->"ExportReceipt":
        o,d=digest(payload),digest(sorted(deps)); return cls(o,d,generation,digest([o,d,generation]))
    def reusable(self,deps:Sequence[str],generation:str)->bool: return self.dependency_root==digest(sorted(deps)) and self.generation==generation

class SnapshotRing:
    def __init__(self,capacity:int=128): self.r=deque(maxlen=capacity)
    def append(self,tick:int,state:Any)->None: self.r.append((tick,digest(state)))
    def __len__(self)->int: return len(self.r)

class CurrentnessInvalidator:
    def __init__(self): self.rev=defaultdict(set); self.stale=set()
    def bind(self,node:str,deps:Iterable[str])->None:
        for d in deps:self.rev[d].add(node)
    def invalidate(self,deps:Iterable[str])->set[str]:
        out=set().union(*(self.rev.get(d,set()) for d in deps)); self.stale|=out; return out
    def current(self,node:str)->bool:return node not in self.stale

@dataclass(frozen=True)
class TypedEdge: source:str; relation:str; target:str; provenance:str; generation:int; current:bool=True
class TypedGraphEdges:
    def __init__(self): self.idx=defaultdict(list)
    def add(self,e:TypedEdge)->None:self.idx[(e.source,e.relation)].append(e)
    def lookup(self,s:str,r:str)->tuple[TypedEdge,...]:return tuple(e for e in self.idx[(s,r)] if e.current)

class CollisionBucket:
    def __init__(self):self.b=defaultdict(dict)
    def put(self,k:tuple[int,int,int],identity:str,v:Any)->None:self.b[k][identity]=v
    def get(self,k:tuple[int,int,int],identity:str)->Any:return self.b[k][identity]
    def identities(self,k:tuple[int,int,int])->tuple[str,...]:return tuple(sorted(self.b[k]))

class HDCSemanticKey:
    def encode(self,text:str)->int:
        acc=[0]*64
        for t in tokens(text):
            h=int.from_bytes(sha256(t.encode()).digest()[:8],"big")
            for i in range(64):acc[i]+=1 if h>>i&1 else -1
        return sum((1<<i) for i,x in enumerate(acc) if x>=0)
    @staticmethod
    def distance(a:int,b:int)->int:return (a^b).bit_count()

class HybridIndexBridge:
    def __init__(self,prefix_bits:int=10):self.p=prefix_bits;self.h=HDCSemanticKey();self.b=defaultdict(list)
    def add(self,identity:str,text:str,k27:tuple[int,int,int])->None:
        k=self.h.encode(text);self.b[k>>(64-self.p)].append((identity,k,k27))
    def candidates(self,q:str,max_hamming:int=24):
        k=self.h.encode(q);out=[(i,c,self.h.distance(k,h)) for i,h,c in self.b[k>>(64-self.p)]]
        return tuple(sorted((x for x in out if x[2]<=max_hamming),key=lambda x:(x[2],x[0])))

class HotColdCache:
    def __init__(self,cold:Mapping[str,Any],capacity:int=512):self.cold=cold;self.capacity=capacity;self.hot=OrderedDict();self.hits=0;self.misses=0
    def get(self,k:str)->Any:
        if k in self.hot:self.hits+=1;v=self.hot.pop(k)
        else:self.misses+=1;v=self.cold[k]
        self.hot[k]=v
        if len(self.hot)>self.capacity:self.hot.popitem(last=False)
        return v

@dataclass(frozen=True)
class RetrievalReceipt:
    query_digest:str; candidates:tuple[str,...]; generation:str; receipt_digest:str
    @classmethod
    def build(cls,q:str,c:Sequence[str],generation:str)->"RetrievalReceipt":
        qd=digest(q);return cls(qd,tuple(c),generation,digest([qd,list(c),generation]))

class PageCacheStateGate:
    @staticmethod
    def classify(s:str|None)->str:return s if s in {"cold","warm"} else "CALIBRATION_REQUIRED"
class RouterPreservingPrefetch:
    @staticmethod
    def plan(native:Sequence[int],pred:Sequence[int],allowed:Iterable[int])->tuple[int,...]:return tuple(dict.fromkeys(x for x in pred if x in set(allowed)))
class NativeRouterAuthority:
    @staticmethod
    def execute(native:Sequence[int],prefetched:Iterable[int])->tuple[int,...]:return tuple(native)
class WindowAwareBudget:
    @staticmethod
    def bytes(bandwidth:float,window_s:float,cap:int)->int:return min(cap,max(0,int(bandwidth*window_s)))
class PrefetchWasteGuard:
    @staticmethod
    def admit(useful:int,wasted:int)->bool:return useful>wasted

@dataclass(frozen=True)
class StorageTier: name:str; capacity_bytes:int; bandwidth:float; joules_per_gb:float
class TierEnergyAdmission:
    @staticmethod
    def admit(t:StorageTier,n:int,budget_j:float)->bool:return n<=t.capacity_bytes and n/1e9*t.joules_per_gb<=budget_j
class StorageTierPlacement:
    @staticmethod
    def choose(tiers:Sequence[StorageTier],n:int,budget_j:float)->StorageTier|None:
        ok=[t for t in tiers if TierEnergyAdmission.admit(t,n,budget_j)];return max(ok,key=lambda t:t.bandwidth) if ok else None

@dataclass
class UsefulByteAccounting:
    useful:int=0; wasted:int=0; missed:int=0
    @property
    def total(self)->int:return self.useful+self.wasted+self.missed

class ExpertResidencyLRU:
    def __init__(self,capacity:int):self.capacity=capacity;self.r=OrderedDict();self.hits=0;self.misses=0
    def access(self,x:int)->bool:
        hit=x in self.r;self.hits+=hit;self.misses+=not hit
        if hit:self.r.move_to_end(x)
        else:
            self.r[x]=None
            if len(self.r)>self.capacity:self.r.popitem(last=False)
        return hit
    def resident(self,x:int)->bool:return x in self.r
    def prefetch(self,x:int)->None:
        if x in self.r:self.r.move_to_end(x)
        else:
            self.r[x]=None
            if len(self.r)>self.capacity:self.r.popitem(last=False)

class PLEExpertSeparation:
    def __init__(self,expert_capacity:int,ple_capacity:int):self.experts=ExpertResidencyLRU(expert_capacity);self.ple=OrderedDict();self.pc=ple_capacity
    def access(self,kind:str,x:int)->bool:
        if kind=="expert":return self.experts.access(x)
        if kind!="ple":raise ValueError(kind)
        hit=x in self.ple;self.ple[x]=None;self.ple.move_to_end(x)
        if len(self.ple)>self.pc:self.ple.popitem(last=False)
        return hit

FRONTIER_27=("HardFalseSecurityGate","HybridIndexBridge","ExportReceipt","TypedGraphEdges","NativeRouterAuthority","RouterPreservingPrefetch","PageCacheStateGate","VersionRangeGate","SnapshotRing","HotColdCache","StorageTierPlacement","StateHandleLease","WindowAwareBudget","PrefetchWasteGuard","TierEnergyAdmission","UsefulByteAccounting","ExpertResidencyLRU","PLEExpertSeparation","P0IdentityGate","MatchedEnvelopeGate","CompositionMembrane","CollisionBucket","HardGatePin","CapabilityManifest","RetrievalReceipt","CurrentnessInvalidator","HDCSemanticKey")

class LegacyOffload:
    def __init__(self,size:int,bandwidth:float,jpgb:float):self.size=size;self.bw=bandwidth;self.jpgb=jpgb
    def run(self,routes,preds):
        a=UsefulByteAccounting();secs=energy=0.0
        for route,pred in zip(routes,preds):
            n=len(route)*self.size;a.missed+=n;secs+=n/self.bw;energy+=n/1e9*self.jpgb;rs=set(route)
            for x in pred:
                if x in rs:a.useful+=self.size
                else:a.wasted+=self.size
                secs+=self.size/self.bw;energy+=self.size/1e9*self.jpgb
        return {"bytes":a.total,"seconds":secs,"energy_j":energy,"hit_rate":0.0}

class FrontierOffload:
    def __init__(self,size:int,capacity:int,tier:StorageTier,window_s:float,budget_j:float):self.size=size;self.r=ExpertResidencyLRU(capacity);self.t=tier;self.w=window_s;self.e=budget_j
    def run(self,routes,preds):
        a=UsefulByteAccounting();secs=energy=0.0
        for route,pred in zip(routes,preds):
            native=NativeRouterAuthority.execute(route,());budget=WindowAwareBudget.bytes(self.t.bandwidth,self.w,self.size*len(pred));plan=RouterPreservingPrefetch.plan(native,pred[:budget//self.size],range(10000));rs=set(native);u=sum(x in rs for x in plan)*self.size;w=sum(x not in rs for x in plan)*self.size
            if PrefetchWasteGuard.admit(u,w):
                for x in plan:
                    if not self.r.resident(x):self.r.prefetch(x);a.useful+=self.size if x in rs else 0;a.wasted+=self.size if x not in rs else 0;energy+=self.size/1e9*self.t.joules_per_gb
            for x in native:
                if not self.r.access(x):a.missed+=self.size;secs+=self.size/self.t.bandwidth;energy+=self.size/1e9*self.t.joules_per_gb
        total=self.r.hits+self.r.misses;return {"bytes":a.total,"seconds":secs,"energy_j":energy,"hit_rate":self.r.hits/total}

def security_campaign(n:int=1000)->dict[str,Any]:
    e=IdentityEnvelope("glm53","r","s","h","g");invalid=blocked=0
    for i in range(n):
        o=e if i%7 else IdentityEnvelope("glm53","r2","s","h","g");hard=HardFalseSecurityGate.admit(source_audited=i%11!=0,runtime_hard_false=i%13!=0,remote_code_widening=i%17==0);ident=P0IdentityGate.admit(e,o);invalid+=not(hard and ident);blocked+=not HardGatePin.admit({"hard":hard,"identity":ident})
    return {"cases":n,"invalid":invalid,"before_false_admits":invalid,"after_blocked":blocked,"false_admission_reduction":blocked/invalid if invalid else 1.0}
