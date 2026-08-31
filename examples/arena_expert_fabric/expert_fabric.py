from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from typing import Dict

TRITS=27
MOD=3**TRITS

def h16(s:str)->str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def k27(sid:str, domain:str)->str:
    n=int.from_bytes(hashlib.sha256(f"{sid}|{domain}".encode()).digest(), 'big') % MOD
    ds=[]
    for _ in range(TRITS):
        ds.append(str(n%3)); n//=3
    return ''.join(reversed(ds))

@dataclass(frozen=True)
class Task:
    sid:str; generation:int; domain:str; task_class:str
    privacy:str='standard'
    latency:str='interactive'
    tool_required:bool=False
    risk:str='normal'
    benchmark_mode:bool=False
    diversity_needed:bool=False
    deterministic_sufficient:bool=False

@dataclass(frozen=True)
class Backend:
    name:str; local:bool; tools:bool; latency_rank:int; cost_rank:int
    kind:str; family:str

BACKENDS=[
    Backend('NO_MODEL',True,True,0,0,'deterministic','deterministic'),
    Backend('LOCAL_FAST',True,True,1,0,'local_model','local-fast'),
    Backend('AIRLLM_LARGE_LOCAL',True,False,5,0,'airllm','local-large'),
    Backend('OPENROUTER_PINNED',False,True,2,2,'openrouter','remote-pinned'),
    Backend('OPENROUTER_TRIAD',False,True,4,4,'openrouter_moa','remote-diverse'),
]

DOMAIN_PREFS={
 'source_currentness':['NO_MODEL','LOCAL_FAST','OPENROUTER_PINNED'],
 'runtime_code':['LOCAL_FAST','OPENROUTER_PINNED','OPENROUTER_TRIAD'],
 'deep_private_reasoning':['AIRLLM_LARGE_LOCAL','LOCAL_FAST'],
 'cross_domain_research':['OPENROUTER_TRIAD','OPENROUTER_PINNED','AIRLLM_LARGE_LOCAL'],
 'batch_falsification':['AIRLLM_LARGE_LOCAL','OPENROUTER_TRIAD','OPENROUTER_PINNED'],
}

def cache_key(task:Task, model_identity:str, preset_generation:str, workcapsule_digest:str)->str:
    material='|'.join(map(str,[task.sid,task.generation,task.domain,task.task_class,
                                model_identity,preset_generation,workcapsule_digest]))
    return hashlib.sha256(material.encode()).hexdigest()

def choose(task:Task, local_airllm_available=True)->Dict:
    if task.deterministic_sufficient:
        selected=['NO_MODEL']
    else:
        candidates=list(DOMAIN_PREFS.get(task.domain,['LOCAL_FAST','OPENROUTER_PINNED']))
        if task.privacy=='strict_local':
            candidates=[c for c in candidates if next(b for b in BACKENDS if b.name==c).local]
        if task.tool_required:
            candidates=[c for c in candidates if next(b for b in BACKENDS if b.name==c).tools]
        if task.latency=='interactive':
            candidates=[c for c in candidates if next(b for b in BACKENDS if b.name==c).latency_rank<=2]
        if not local_airllm_available:
            candidates=[c for c in candidates if c!='AIRLLM_LARGE_LOCAL']
        if task.benchmark_mode:
            candidates=[c for c in candidates if c in ('OPENROUTER_PINNED','LOCAL_FAST')]
        if not candidates:
            return {'status':'BLOCK','reason':'NO_POLICY_COMPLIANT_BACKEND'}
        selected=[candidates[0]]
        if task.diversity_needed and not task.benchmark_mode and task.privacy!='strict_local':
            if 'OPENROUTER_TRIAD' in candidates:
                selected=['OPENROUTER_TRIAD']
    shard=k27(task.sid,task.domain)
    bundle_material=json.dumps({'sid':task.sid,'g':task.generation,'d':task.domain,
                                'class':task.task_class,'selected':selected},sort_keys=True)
    return {
      'status':'ROUTED',
      'stable_sid':task.sid,
      'generation':task.generation,
      'domain_lens':task.domain,
      'k27':shard,
      'k27_prefix_6':shard[:6],
      'expert_bundle_ref':'EXPERTBUNDLE:'+h16(bundle_material),
      'selected':selected,
      'laws':[
        'DOMAIN_LENS_SELECTS_COGNITIVE_NEIGHBORHOOD_NOT_TRUTH',
        'K27_ROUTES_PHYSICAL_SHARD_NOT_EXPERT_SEMANTICS',
        'CACHE_KEY_BINDS_MODEL_AND_SOURCE_GENERATION',
        'PRIVACY_AND_AUTHORITY_GATE_BEFORE_COST_OR_SPEED'
      ]
    }
