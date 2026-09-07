from __future__ import annotations
import json
from hashlib import sha256
from tools.arena.worker_cells.gpt56sol_astra_realisability_r1 import Effect,InfoEdge,Capability,Program,legal,realisable,repair,full_13d_gate_check

def oracle(p):
    d={e.effect_id:e for e in p.effects}
    if len(d)!=len(p.effects) or not d or sum(e.cost for e in p.effects)>p.budget:return 'HOLD'
    if any(e.witness_epoch!=p.current_epoch for e in p.effects):return 'HOLD'
    state={}
    def visit(k):
        if k not in d or state.get(k)==1:return False
        if state.get(k)==2:return True
        state[k]=1
        if not all(visit(x) for x in d[k].deps):return False
        state[k]=2;return True
    if not all(visit(k) for k in d):return 'HOLD'
    choices={}
    for e in p.effects:
        if e.emits_choice:
            if e.emits_choice in choices:return 'HOLD'
            choices[e.emits_choice]=(e.effect_id,e.actor)
    have={(x.source_effect,x.target_actor,x.fact) for x in p.info_edges}; missing=[]
    for e in p.effects:
        for dep in e.deps:
            if d[dep].actor!=e.actor and (dep,e.actor,f'done:{dep}') not in have:missing.append(1)
        if e.guard_choice:
            src=choices.get(e.guard_choice)
            if not src:return 'UNREALISABLE'
            if src[1]!=e.actor and (src[0],e.actor,f'choice:{e.guard_choice}={e.guard_value}') not in have:missing.append(1)
    return 'UNREALISABLE' if missing else 'READY'

def case(i):
    epoch=7; b=['B','C','D'][i%3]; c=['C','D','E'][(i//3)%3]; stale=i%17==0; cyc=i%29==0; budget=i%31==0; edges=i%2==0
    e1=Effect('choose','A',emits_choice='mode',emits_value='x',witness_epoch=epoch-1 if stale else epoch)
    e2=Effect('middle',b,('tail',) if cyc else ('choose',),'mode','x',witness_epoch=epoch)
    e3=Effect('tail',c,('middle',),witness_epoch=epoch)
    xs=[]
    if edges: xs=[InfoEdge('choose',b,'done:choose'),InfoEdge('choose',b,'choice:mode=x'),InfoEdge('middle',c,'done:middle')]
    if i%11==0 and xs:xs.pop()
    return Program((e1,e2,e3),2 if budget else 9,epoch,tuple(xs),(Capability(b,frozenset({'*'}),5),Capability(c,frozenset({'*'}),5)))

def run():
    mismatch=false_ready=0; statuses={}; roots=[]
    for i in range(1000):
        p=case(i); o=oracle(p); ok,_=legal(p); r,_=realisable(p); got='READY' if ok and r else ('UNREALISABLE' if ok else 'HOLD')
        mismatch+=got!=o; d=repair(p); false_ready+=d.status.startswith('READY') and not ok; statuses[d.status]=statuses.get(d.status,0)+1; roots.append((p.root,d.status))
    g=full_13d_gate_check()
    out={'cases':1000,'oracle_mismatches':mismatch,'repair_false_ready':false_ready,'statuses':dict(sorted(statuses.items())),'states_13d':g['states'],'gate_mismatches':g['mismatches'],'hard_invalid_repairs':g['hard_invalid_repairs'],'authority':'D0_NONPROMOTING','gate10':False,'effect_authority':False}
    out['campaign_root']=sha256(json.dumps({'out':out,'roots':roots},sort_keys=True).encode()).hexdigest()
    if mismatch or false_ready or g['mismatches'] or g['hard_invalid_repairs']:raise SystemExit(json.dumps(out,sort_keys=True))
    return out
if __name__=='__main__':print(json.dumps(run(),sort_keys=True))
