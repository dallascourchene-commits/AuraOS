"""D0 reference: vision-rate kinetic intent -> audio-owned sample clock."""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json, math, statistics, time
from typing import Any, Literal, Sequence


def stable(v: Any) -> bytes: return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()
def digest(v: Any) -> str: return sha256(stable(v)).hexdigest()
def _sha(v): return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdef" for c in v)
def _ceil(v: Fraction) -> int: return -(-v.numerator//v.denominator)
def _bounded(v,lo,hi,name):
    if type(v) is not int or not lo<=v<=hi: raise ValueError(f"{name} must be int in [{lo}, {hi}]")
    return v

def _align(n,q): return ((n+q-1)//q)*q

@dataclass(frozen=True,order=True)
class K27Coordinate:
    x:int; y:int; z:int
    def __post_init__(self):
        for n,v in (("x",self.x),("y",self.y),("z",self.z)): _bounded(v,0,2,n)
    @property
    def code(self): return self.x*9+self.y*3+self.z
    @property
    def centered(self): return self.x-1,self.y-1,self.z-1

@dataclass(frozen=True)
class GestureObservation:
    frame_index:int; gesture:str; confidence_milli:int; magnitude_milli:int; k27:K27Coordinate
    def __post_init__(self):
        _bounded(self.frame_index,0,2**63-1,"frame_index"); _bounded(self.confidence_milli,0,1000,"confidence"); _bounded(self.magnitude_milli,0,1000,"magnitude")
        if not self.gesture or not isinstance(self.k27,K27Coordinate): raise ValueError("gesture/k27 required")

@dataclass(frozen=True)
class RawGestureIntent:
    gesture:str; magnitude_milli:int; k27:K27Coordinate; frame_index:int; raw_digest:str
    @classmethod
    def build(cls,o): return cls(o.gesture,o.magnitude_milli,o.k27,o.frame_index,digest([o.gesture,o.magnitude_milli,o.k27.code,o.frame_index]))

class GestureIntentCompiler:
    def __init__(self,activation_milli=750,release_milli=550,hold_frames=2):
        self.a=_bounded(activation_milli,1,1000,"activation"); self.r=_bounded(release_milli,0,999,"release"); self.h=_bounded(hold_frames,1,120,"hold")
        if self.r>=self.a: raise ValueError("release must be below activation")
        self.c=None; self.n=0; self.active=None; self.last=-1
    def observe(self,o):
        if o.frame_index<=self.last: raise ValueError("frames must increase")
        self.last=o.frame_index
        if o.confidence_milli<=self.r: self.c=None; self.n=0; self.active=None; return None
        if o.confidence_milli<self.a: return None
        if o.gesture!=self.c: self.c=o.gesture; self.n=1
        else: self.n+=1
        if self.n>=self.h and self.active!=o.gesture: self.active=o.gesture; return RawGestureIntent.build(o)
        return None

ControlKind=Literal["soft","hard"]
@dataclass(frozen=True)
class ProjectedMusicalIntent:
    kind:ControlKind; controls:tuple[tuple[str,int],...]; k27:K27Coordinate; source_gesture:str; source_digest:str
    basis_graph_generation:int; basis_mutation_epoch:int; basis_timeline_epoch:int; basis_projection_root:str; authority:str="CONTROL_ONLY"
    def __post_init__(self):
        if self.kind not in ("soft","hard") or self.authority!="CONTROL_ONLY" or not self.controls or tuple(sorted(self.controls))!=self.controls: raise ValueError("invalid intent")
        if len({k for k,_ in self.controls})!=len(self.controls) or not _sha(self.source_digest) or not _sha(self.basis_projection_root): raise ValueError("invalid identity")
    @property
    def intent_digest(self): return digest([self.kind,list(self.controls),self.k27.code,self.source_gesture,self.source_digest,self.basis_graph_generation,self.basis_mutation_epoch,self.basis_timeline_epoch,self.basis_projection_root,self.authority])

@dataclass(frozen=True)
class OwnerSnapshot:
    graph_generation:int; mutation_epoch:int; timeline_epoch:int; graph_root:str; projection_root:str; sample_cursor:int; performance_revision:int
    bpm_milli:int; scale_index:int; drop_state:int; soft_controls:tuple[tuple[str,int],...]; state_root:str

class K27ConstraintProjector:
    SOFT={"open","pinch","spread"}; HARD={"fist","swipe_up","swipe_down","rotate"}
    @staticmethod
    def clamp(v,a,b): return a if v<a else b if v>b else v
    def project(self,r,s):
        if r.gesture in self.SOFT:
            c=r.k27.centered; idx={"open":0,"pinch":1,"spread":2}[r.gesture]; name={"open":"brightness_milli","pinch":"density_milli","spread":"width_milli"}[r.gesture]
            controls=((name,self.clamp(500+170*c[idx]+(r.magnitude_milli-500)//3,0,1000)),); kind="soft"
        elif r.gesture in self.HARD:
            kind="hard"
            if r.gesture=="fist": controls=(("drop_state",int(r.magnitude_milli>=500)),)
            elif r.gesture=="rotate": controls=(("scale_index",r.k27.code%12),)
            else:
                d=1 if r.gesture=="swipe_up" else -1; c=r.k27.centered; step=4000+1000*abs(c[0])+500*abs(c[1])
                controls=(("bpm_milli",self.clamp(s.bpm_milli+d*step,60000,180000)),)
        else: raise ValueError("unsupported gesture")
        return ProjectedMusicalIntent(kind,controls,r.k27,r.gesture,r.raw_digest,s.graph_generation,s.mutation_epoch,s.timeline_epoch,s.projection_root)

@dataclass(frozen=True)
class EpochBoundPermit:
    graph_generation:int; mutation_epoch:int; timeline_epoch:int; graph_root:str; intent_digest:str; issued_sample:int; target_sample:int; permit_digest:str
    @classmethod
    def build(cls,s,i,t):
        b=[s.graph_generation,s.mutation_epoch,s.timeline_epoch,s.graph_root,i.intent_digest,s.sample_cursor,t]
        return cls(*b,digest(b))
    def verify(self): return self.permit_digest==digest([self.graph_generation,self.mutation_epoch,self.timeline_epoch,self.graph_root,self.intent_digest,self.issued_sample,self.target_sample])

@dataclass(frozen=True)
class ScheduledEvent: event_id:str; intent:ProjectedMusicalIntent; permit:EpochBoundPermit; ramp_frames:int
@dataclass(frozen=True)
class ScheduleReceipt: admitted:bool; reason:str; event_id:str|None; target_sample:int|None; queue_depth:int
@dataclass(frozen=True)
class GraphWriteReceipt: changed:bool; invalidated_events:tuple[str,...]; snapshot:OwnerSnapshot; receipt_digest:str
@dataclass(frozen=True)
class AppliedEvent: event_id:str; sample_offset:int; kind:ControlKind; controls:tuple[tuple[str,int],...]; ramp_frames:int
@dataclass(frozen=True)
class BlockReceipt: block_start:int; frames:int; applied:tuple[AppliedEvent,...]; held_stale:tuple[str,...]; held_late:tuple[str,...]; queue_depth:int; state_root:str

class FixedEventQueue:
    def __init__(self,cap): self.cap=_bounded(cap,1,65536,"queue"); self.s=[None]*self.cap; self.n=0
    def __len__(self): return self.n
    def push(self,e):
        if self.n>=self.cap:return False
        p=self.n; k=(e.permit.target_sample,e.event_id)
        while p and (self.s[p-1].permit.target_sample,self.s[p-1].event_id)>k: self.s[p]=self.s[p-1]; p-=1
        self.s[p]=e; self.n+=1; return True
    def peek(self): return self.s[0] if self.n else None
    def pop(self):
        if not self.n: raise IndexError
        e=self.s[0]
        for i in range(1,self.n): self.s[i-1]=self.s[i]
        self.n-=1; self.s[self.n]=None; return e
    def ids(self): return tuple(self.s[i].event_id for i in range(self.n))
    def drop_if(self,pred):
        w=0; dropped=[]
        for i in range(self.n):
            e=self.s[i]
            if pred(e): dropped.append(e.event_id)
            else: self.s[w]=e; w+=1
        for i in range(w,self.n): self.s[i]=None
        self.n=w; return tuple(dropped)

class KineticAudioOwner:
    SOFT={"brightness_milli","density_milli","width_milli"}; HARD={"bpm_milli","scale_index","drop_state"}
    def __init__(self,*,recipe_root,engine_root,sample_rate=48000,block_size=128,bpm_milli=128000,beats_per_bar=4,bars_per_phrase=4,queue_capacity=128,lookahead_blocks=2,smoothing_ms=20):
        if not _sha(recipe_root) or not _sha(engine_root): raise ValueError("sha roots required")
        self.sample_rate=_bounded(sample_rate,8000,384000,"sample_rate"); self.block_size=_bounded(block_size,16,8192,"block_size")
        self.beats_per_bar=_bounded(beats_per_bar,1,32,"beats_per_bar"); self.bars_per_phrase=_bounded(bars_per_phrase,1,128,"bars_per_phrase")
        self.lookahead_blocks=_bounded(lookahead_blocks,0,1024,"lookahead"); self.smoothing_ms=_bounded(smoothing_ms,0,10000,"smoothing"); _bounded(bpm_milli,20000,400000,"bpm")
        self.rr=recipe_root; self.er=engine_root; self.g=1; self.m=1; self.t=1; self.pr=0; self.cur=0; self.bpm=bpm_milli; self.scale=0; self.drop=0
        self.soft={"brightness_milli":500,"density_milli":500,"width_milli":500}; self.q=FixedEventQueue(queue_capacity)
    @property
    def queue_depth(self): return len(self.q)
    @property
    def graph_root(self): return digest(["aura.kinetic_audio_multirate.v1",self.rr,self.er,self.sample_rate,self.block_size])
    def _proj(self): return digest([self.g,self.m,self.t,self.graph_root,self.pr,self.bpm,self.scale,self.drop,sorted(self.soft.items())])
    def _state(self): return digest([self._proj(),self.cur,self.q.ids()])
    def snapshot(self): return OwnerSnapshot(self.g,self.m,self.t,self.graph_root,self._proj(),self.cur,self.pr,self.bpm,self.scale,self.drop,tuple(sorted(self.soft.items())),self._state())
    def _current(self,p): return p.verify() and (p.graph_generation,p.mutation_epoch,p.timeline_epoch,p.graph_root)==(self.g,self.m,self.t,self.graph_root)
    def governed_graph_write(self,*,recipe_root=None,engine_root=None):
        nr=self.rr if recipe_root is None else recipe_root; ne=self.er if engine_root is None else engine_root
        if not _sha(nr) or not _sha(ne): raise ValueError("sha roots required")
        changed=(nr,ne)!=(self.rr,self.er); self.rr,self.er=nr,ne; self.g+=int(changed); self.m+=1
        inv=self.q.drop_if(lambda e:not self._current(e.permit)); s=self.snapshot(); return GraphWriteReceipt(changed,inv,s,digest([changed,list(inv),s.state_root]))
    def _validate(self,i,s):
        if not isinstance(i,ProjectedMusicalIntent): return "HOLD_INVALID_INTENT"
        if (i.basis_graph_generation,i.basis_mutation_epoch,i.basis_timeline_epoch,i.basis_projection_root)!=(s.graph_generation,s.mutation_epoch,s.timeline_epoch,s.projection_root): return "HOLD_STALE_PROJECTION"
        valid=self.SOFT if i.kind=="soft" else self.HARD
        if any(k not in valid for k,_ in i.controls): return "HOLD_CONTROL_SCHEMA"
        for k,v in i.controls:
            if k in self.SOFT and not 0<=v<=1000:return "HOLD_CONTROL_BOUNDS"
            if k=="bpm_milli" and not 60000<=v<=180000:return "HOLD_CONTROL_BOUNDS"
            if k=="scale_index" and not 0<=v<12:return "HOLD_CONTROL_BOUNDS"
            if k=="drop_state" and v not in (0,1):return "HOLD_CONTROL_BOUNDS"
        return None
    def _phrase_target(self,minsample):
        ph=Fraction(self.sample_rate*60*1000*self.beats_per_bar*self.bars_per_phrase,self.bpm); n=_ceil(Fraction(minsample,1)/ph); return max(minsample,_ceil(ph*n))
    def schedule(self,i):
        s=self.snapshot(); reason=self._validate(i,s)
        if reason:return ScheduleReceipt(False,reason,None,None,len(self.q))
        minimum=s.sample_cursor+self.lookahead_blocks*self.block_size
        if i.kind=="soft": target=_align(minimum,self.block_size); ramp=max(self.block_size,_ceil(Fraction(self.sample_rate*self.smoothing_ms,1000)))
        else: target=self._phrase_target(minimum); ramp=0
        p=EpochBoundPermit.build(s,i,target); eid=digest([p.permit_digest,list(i.controls),i.k27.code,ramp]); e=ScheduledEvent(eid,i,p,ramp)
        if not self.q.push(e): return ScheduleReceipt(False,"HOLD_QUEUE_FULL",None,None,len(self.q))
        return ScheduleReceipt(True,"ADMIT_SCHEDULED",eid,target,len(self.q))
    def _apply(self,e):
        if e.intent.kind=="soft": self.soft.update(dict(e.intent.controls))
        else:
            for k,v in e.intent.controls:
                if k=="bpm_milli":self.bpm=v
                elif k=="scale_index":self.scale=v
                elif k=="drop_state":self.drop=v
            self.t+=1
        self.pr+=1; return AppliedEvent(e.event_id,e.permit.target_sample-self.cur,e.intent.kind,e.intent.controls,e.ramp_frames)
    def process_block(self,frames=None):
        frames=self.block_size if frames is None else _bounded(frames,1,self.block_size,"frames"); start=self.cur; end=start+frames; app=[]; stale=[]; late=[]
        while self.q.peek() and self.q.peek().permit.target_sample<end:
            e=self.q.pop()
            if e.permit.target_sample<start: late.append(e.event_id); continue
            if not self._current(e.permit): stale.append(e.event_id); continue
            a=self._apply(e); app.append(a)
            if a.kind=="hard": stale.extend(self.q.drop_if(lambda x:not self._current(x.permit)))
        self.cur=end; return BlockReceipt(start,frames,tuple(app),tuple(stale),tuple(late),len(self.q),self._state())
    def process_until(self,sample_exclusive):
        _bounded(sample_exclusive,self.cur,2**63-1,"sample_exclusive"); out=[]
        while self.cur<sample_exclusive: out.append(self.process_block(min(self.block_size,sample_exclusive-self.cur)))
        return tuple(out)

class KineticAudioMembrane:
    def __init__(self,owner,compiler=None,projector=None): self.owner=owner; self.compiler=compiler or GestureIntentCompiler(); self.projector=projector or K27ConstraintProjector()
    def ingest(self,o):
        r=self.compiler.observe(o)
        return None if r is None else self.owner.schedule(self.projector.project(r,self.owner.snapshot()))

@dataclass(frozen=True)
class SyntheticBenchmark:
    blocks:int;p50_ns:int;p95_ns:int;p99_ns:int;max_ns:int;callback_budget_ns:int;overruns:int;claim_ceiling:str="PROCESS_LEVEL_SYNTHETIC_ONLY"

def synthetic_callback_benchmark(owner,blocks=20000):
    _bounded(blocks,100,1000000,"blocks"); xs=[]
    for _ in range(blocks): t=time.perf_counter_ns(); owner.process_block(); xs.append(time.perf_counter_ns()-t)
    xs.sort(); pct=lambda p:xs[min(len(xs)-1,max(0,math.ceil(p*len(xs))-1))]; budget=int(owner.block_size/owner.sample_rate*1e9)
    return SyntheticBenchmark(blocks,int(statistics.median(xs)),pct(.95),pct(.99),xs[-1],budget,sum(x>budget for x in xs))

def replay_root(sequence:Sequence[GestureObservation],*,recipe_root,engine_root):
    o=KineticAudioOwner(recipe_root=recipe_root,engine_root=engine_root,sample_rate=8000,block_size=64,beats_per_bar=1,bars_per_phrase=1); m=KineticAudioMembrane(o); tr=[]
    for obs in sequence:
        r=m.ingest(obs); tr.append(None if r is None else r.__dict__)
        for b in range(4):
            br=o.process_block(); tr.append([b,[a.event_id for a in br.applied],list(br.held_stale),br.state_root])
    return digest(tr)
