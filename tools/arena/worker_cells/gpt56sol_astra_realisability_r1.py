from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import itertools, json

D0='D0_NONPROMOTING'
ACTIONS=('EXTEND_W','EXTEND_P','BRIDGE','UNIFY','REPLACE','DELETE','SELECTOR','SHADOW_ORACLE','NEW_CAPABILITY','EMPIRICAL_FALSIFIER')
TARGETS=('effect_legality','projection_realisability','information_edges','branch_knowledge','temporal_currentness','capability_contracts','authority_revocation','irreversible_frontier','counterexample_certificates','repair_minimality')
CONSEQUENCES=('false_global_accept','extra_trace','missing_trace','deadlock','premature_irreversible_effect','branch_confusion','stale_witness_reuse','authority_widening','unbounded_repair_state','nonminimal_coordination')
MECHANISMS=('branching_pomset_projection','local_choice_knowledge','causal_notification','budget_product_monitor','epoch_bound_witness','capability_counterexample','least_privilege_edge','irreversible_cut','shared_monitor_dag','repair_certificate')
LENSES=('topology','temporal','authority','capability','evidence','recovery','resource','portability')

def _canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(x): return sha256(_canon(x)).hexdigest()

@dataclass(frozen=True)
class Effect:
    effect_id:str; actor:str; deps:tuple[str,...]=(); guard_choice:str|None=None; guard_value:str|None=None
    emits_choice:str|None=None; emits_value:str|None=None; cost:int=1; witness_epoch:int=0; irreversible:bool=False
@dataclass(frozen=True)
class InfoEdge: source_effect:str; target_actor:str; fact:str
@dataclass(frozen=True)
class Capability: actor:str; receivable_facts:frozenset[str]=frozenset(); max_new_edges:int=8
@dataclass(frozen=True)
class Program:
    effects:tuple[Effect,...]; budget:int; current_epoch:int; info_edges:tuple[InfoEdge,...]=(); capabilities:tuple[Capability,...]=(); executed_effects:frozenset[str]=frozenset()
    @property
    def root(self):
        return digest({'effects':[e.__dict__ for e in self.effects],'budget':self.budget,'epoch':self.current_epoch,'edges':[e.__dict__ for e in self.info_edges],'caps':[{'actor':c.actor,'facts':sorted(c.receivable_facts),'max':c.max_new_edges} for c in self.capabilities],'executed':sorted(self.executed_effects)})
@dataclass(frozen=True)
class Decision:
    status:str; program_root:str; repair_edges:tuple[InfoEdge,...]=(); certificate:dict|None=None; authority:str=D0; gate10:bool=False; effect_authority:bool=False

def _effects(p):
    d={e.effect_id:e for e in p.effects}
    if len(d)!=len(p.effects): raise ValueError('duplicate effect_id')
    return d

def legal(p):
    try: d=_effects(p)
    except ValueError: return False,'DUPLICATE_EFFECT'
    if not d:return False,'EMPTY_PROGRAM'
    if p.budget<0 or sum(e.cost for e in p.effects)>p.budget:return False,'GLOBAL_BUDGET'
    state={}
    def visit(k):
        if k not in d:return False
        if state.get(k)==1:return False
        if state.get(k)==2:return True
        state[k]=1
        if not all(visit(x) for x in d[k].deps):return False
        state[k]=2; return True
    if not all(visit(k) for k in d):return False,'CAUSALITY'
    if any(e.witness_epoch!=p.current_epoch for e in p.effects):return False,'STALE_WITNESS'
    return True,'LEGAL'

def required_information(p):
    d=_effects(p); choices={}
    for e in p.effects:
        if e.emits_choice:
            if e.emits_choice in choices: raise ValueError('duplicate choice source')
            choices[e.emits_choice]=(e.effect_id,e.actor)
    req=set()
    for e in p.effects:
        for dep in e.deps:
            if d[dep].actor!=e.actor:req.add((dep,e.actor,f'done:{dep}'))
        if e.guard_choice:
            src=choices.get(e.guard_choice)
            if src is None:req.add(('<missing-choice>',e.actor,f'choice:{e.guard_choice}={e.guard_value}'))
            elif src[1]!=e.actor:req.add((src[0],e.actor,f'choice:{e.guard_choice}={e.guard_value}'))
    return tuple(sorted(req))

def realisable(p):
    ok,_=legal(p)
    if not ok:return False,()
    have={(e.source_effect,e.target_actor,e.fact) for e in p.info_edges}
    missing=tuple(x for x in required_information(p) if x not in have)
    return not missing,missing

def repair(p):
    ok,why=legal(p)
    if not ok:
        return Decision('HOLD_'+why,p.root,certificate={'reason':why,'stale':[e.effect_id for e in p.effects if e.witness_epoch!=p.current_epoch]})
    yes,missing=realisable(p)
    if yes:return Decision('READY_LOCALLY_REALISABLE',p.root)
    caps={c.actor:c for c in p.capabilities}; blocked=[]; out=[]; counts={}; irrev=[]
    for src,actor,fact in missing:
        if src=='<missing-choice>':blocked.append((src,actor,fact));continue
        cap=caps.get(actor); allowed=cap is None or fact in cap.receivable_facts or '*' in cap.receivable_facts
        if cap and counts.get(actor,0)>=cap.max_new_edges:allowed=False
        targets=[e for e in p.effects if e.actor==actor and (src in e.deps or fact.startswith('choice:'))]
        if any(e.effect_id in p.executed_effects and e.irreversible for e in targets):
            allowed=False; irrev.extend(e.effect_id for e in targets if e.effect_id in p.executed_effects and e.irreversible)
        if not allowed:blocked.append((src,actor,fact));continue
        out.append(InfoEdge(src,actor,fact));counts[actor]=counts.get(actor,0)+1
    out=tuple(sorted(set(out),key=lambda x:(x.source_effect,x.target_actor,x.fact)))
    if blocked or irrev:
        return Decision('HOLD_UNREALISABLE',p.root,out,{'missing':missing,'blocked':tuple(sorted(set(blocked))),'irreversible':tuple(sorted(set(irrev)))})
    p2=Program(p.effects,p.budget,p.current_epoch,tuple(sorted(set(p.info_edges+out),key=lambda x:(x.source_effect,x.target_actor,x.fact))),p.capabilities,p.executed_effects)
    yes,left=realisable(p2)
    if not yes:return Decision('HOLD_REPAIR_INCOMPLETE',p.root,certificate={'missing':left})
    return Decision('READY_WITH_MINIMAL_INFO_REPAIR',p.root,out)

def revalidate_at_use(p,d,current_caps):
    if d.status!='READY_WITH_MINIMAL_INFO_REPAIR':return d
    caps={c.actor:c for c in current_caps}; blocked=[]
    for e in d.repair_edges:
        c=caps.get(e.target_actor)
        if c and e.fact not in c.receivable_facts and '*' not in c.receivable_facts:blocked.append((e.source_effect,e.target_actor,e.fact))
    return Decision('HOLD_CAPABILITY_REVOKED_AT_USE',p.root,certificate={'blocked':tuple(blocked)}) if blocked else d

def crystalline_gate(hard8,tail5):
    if len(hard8)!=8 or len(tail5)!=5 or any(x not in (0,1,2) for x in tuple(hard8)+tuple(tail5)):raise ValueError('8+5 ternary axes required')
    if any(x!=2 for x in hard8):return 'HOLD_HARD_AXIS'
    if 0 in tail5:return 'HOLD_CONTEXT'
    if 1 in tail5:return 'REPROVE_CONTEXT'
    return 'READY_D0'

def candidate_k27(p):
    return (min(len({e.actor for e in p.effects}),2),min(len({e.emits_choice for e in p.effects if e.emits_choice}),2),min(len(required_information(p)),2))

def hs1000_candidates():
    rows=[]; i=0
    for ti,t in enumerate(TARGETS):
      for ci,c in enumerate(CONSEQUENCES):
       for mi,m in enumerate(MECHANISMS):
        i+=1
        rows.append({'candidate_id':f'ASTRA-RZ-{i:04d}','title':f'{m}:{t}:{c}','action':ACTIONS[(ti+ci+mi)%10],'target_roots':[t,'ASTRA_V6_POST_DUAL','EFFECT_PROGRAM_REALISABILITY'],'consequence_key':f'{t}|{c}','mechanism':m,'consequence_change':f'Change {c} at {t} without treating global legality as local implementability.','novelty_statement':f'Frontier-relative candidate testing {m} against {c} in {t}.','cheapest_falsifier':f'Smallest globally legal asynchronous program exposing {c}; mutate {m} and compare global/local traces.','evidence_required':['independent_oracle','exact_source_bytes','counterexample_or_pass_receipt'],'expected_gain':'UNSCORED_AT_FREEZE','claim_ceiling':'D0_REFERENCE_ONLY','tags':[LENSES[(ti+mi)%8],LENSES[(ci+mi+3)%8],'K27_LOCALITY_ONLY']})
    assert len(rows)==1000;return rows

def hs1000_freeze_root(rows=None):
    rows=rows or hs1000_candidates(); raw=''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in rows).encode();return sha256(raw).hexdigest()

def hs1000_quotient(rows=None):
    rows=rows or hs1000_candidates(); g={}
    for r in rows:g.setdefault(r['consequence_key'],[]).append(r)
    assert len(g)==100
    return tuple(sorted((k,len(v)) for k,v in g.items()))

def full_13d_gate_check():
    mismatches=repairs=states=0
    for a in itertools.product(range(3),repeat=13):
        h,t=a[:8],a[8:]; got=crystalline_gate(h,t)
        exp='HOLD_HARD_AXIS' if any(x!=2 for x in h) else ('HOLD_CONTEXT' if 0 in t else ('REPROVE_CONTEXT' if 1 in t else 'READY_D0'))
        mismatches+=got!=exp; repairs+=any(x!=2 for x in h) and got!='HOLD_HARD_AXIS';states+=1
    return {'states':states,'mismatches':mismatches,'hard_invalid_repairs':repairs}
