from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
D0='D0_NONPROMOTING'
def _canon(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def digest(x):return sha256(_canon(x)).hexdigest()
@dataclass(frozen=True)
class Interval:
 lo:int;hi:int
 def __post_init__(self):
  if self.lo<0 or self.lo>self.hi:raise ValueError('bad interval')
@dataclass(frozen=True)
class Sensor:
 name:str;duration:Interval;current:bool=True
@dataclass(frozen=True)
class Task:
 name:str;condition:int;duration:Interval;resource:str;invariant_support:frozenset[str];current:bool=True
 def __post_init__(self):
  if self.condition not in (0,1):raise ValueError('condition must be 0/1')
  if not self.invariant_support:raise ValueError('empty invariant support')
@dataclass(frozen=True)
class BranchPlan:
 outcome:int;active_tasks:tuple[str,...];components:tuple[tuple[str,...],...];worst_finish:int;root:str
@dataclass(frozen=True)
class Strategy:
 status:str;branches:tuple[BranchPlan,...];worst_finish:int;reason:str;strategy_root:str='';authority:str=D0;gate10:bool=False;effect_authority:bool=False;k27_coordinate:str|None=None

def _components(tasks,mode='invariant'):
 ts=tuple(sorted(tasks,key=lambda t:t.name));adj={t.name:set() for t in ts};by={t.name:t for t in ts}
 for i,a in enumerate(ts):
  for b in ts[i+1:]:
   conflict=(bool(a.invariant_support & b.invariant_support) if mode=='invariant' else a.resource==b.resource)
   if conflict:adj[a.name].add(b.name);adj[b.name].add(a.name)
 out=[];seen=set()
 for n in sorted(adj):
  if n in seen:continue
  stack=[n];c=set()
  while stack:
   x=stack.pop()
   if x in seen:continue
   seen.add(x);c.add(x);stack.extend(adj[x]-seen)
  out.append(tuple(sorted(c)))
 return tuple(out),by

def _branch_finish(sensor,tasks,outcome,mode='invariant'):
 active=tuple(t for t in tasks if t.condition==outcome)
 if any(not t.current for t in active):return None,None
 comps,by=_components(active,mode)
 serial=[sum(by[n].duration.hi for n in c) for c in comps]
 finish=sensor.duration.hi+(max(serial) if serial else 0)
 return comps,finish

def compile_strategy(sensor,tasks,deadline,*,k27_coordinate=None):
 tasks=tuple(tasks)
 if not sensor.current:return Strategy('HOLD_SENSOR_CURRENTNESS',(),0,'sensor stale',k27_coordinate=k27_coordinate)
 branches=[]
 for o in (0,1):
  comps,finish=_branch_finish(sensor,tasks,o,'invariant')
  if comps is None:return Strategy('HOLD_TASK_CURRENTNESS',(),0,f'active branch {o} contains stale evidence task',k27_coordinate=k27_coordinate)
  active=tuple(sorted(t.name for t in tasks if t.condition==o));root=digest({'outcome':o,'active':active,'components':comps,'finish':finish});branches.append(BranchPlan(o,active,comps,finish,root))
 worst=max(b.worst_finish for b in branches)
 status='READY_D0' if worst<=deadline else 'HOLD_NOT_DYNAMICALLY_CONTROLLABLE'
 reason='branch-contingent invariant-support policy meets all duration envelopes' if status=='READY_D0' else 'at least one observation branch misses deadline under worst-case duration'
 sr=digest({'sensor':sensor.name,'sensor_hi':sensor.duration.hi,'branches':[(b.outcome,b.root) for b in branches],'deadline':deadline,'status':status})
 return Strategy(status,tuple(branches),worst,reason,sr,k27_coordinate=k27_coordinate)

def static_union_finish(sensor,tasks):
 comps,by=_components(tuple(tasks),'invariant');serial=[sum(by[n].duration.hi for n in c) for c in comps];return sensor.duration.hi+(max(serial) if serial else 0)
def resource_only_branch_finish(sensor,tasks,outcome):
 comps,finish=_branch_finish(sensor,tasks,outcome,'resource');return finish
def oracle_dynamic_ready(sensor,tasks,deadline):
 if not sensor.current:return False
 for o in (0,1):
  comps,finish=_branch_finish(sensor,tasks,o,'invariant')
  if comps is None or finish>deadline:return False
 return True
