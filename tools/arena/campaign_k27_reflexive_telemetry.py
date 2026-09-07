from __future__ import annotations
import itertools,json,random,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'/'arena'))
from k27_reflexive_telemetry import ProbeTransition,ReflexiveTelemetryGate,hard13d_admission
from k27_dynamic_navigator import digest


def oracle(q,inherited,seen,consumed):
    changed=q.pre_state_root!=q.post_state_root
    if q.declared_effect=='PASSIVE' and changed:return 'HOLD_UNDECLARED_PROBE_EFFECT'
    if q.declared_effect=='CONSUMED_ONCE' and q.probe_id in consumed:return 'HOLD_CONSUMED_ONCE'
    if not q.lawful_ancestry or not q.collision_checked or not q.material_consequence:return 'REJECT'
    if q.consequence_root in inherited or q.consequence_root in seen:return 'SUPPORT_NOT_DISCOVERY'
    if not q.counterexample_root:return 'HOLD_NEEDS_COUNTEREXAMPLE'
    return 'ADMISSION_READY'

def main():
    rng=random.Random(20260907)
    inherited={f'inherited-{i}' for i in range(37)}
    gate=ReflexiveTelemetryGate(inherited)
    expected_seen=set(); expected_consumed=set(); counts=Counter(); mismatches=0; false_novelty=0
    rows=[]
    for i in range(10000):
        effect=rng.choice(['PASSIVE','MAY_MUTATE','CONSUMED_ONCE'])
        pre=f's{rng.randrange(64)}'; changed=rng.random()<0.35; post=f's{rng.randrange(64)}' if changed else pre
        if effect=='CONSUMED_ONCE' and rng.random()<0.08 and expected_consumed:
            pid=rng.choice(sorted(expected_consumed))
        else: pid=f'p{i}'
        if rng.random()<0.2:c=rng.choice(sorted(inherited))
        elif rng.random()<0.15 and expected_seen:c=rng.choice(sorted(expected_seen))
        else:c=f'c{rng.randrange(5000)}'
        q=ProbeTransition(pid,pre,post,effect,c,rng.random()>0.05,rng.random()>0.05,rng.random()>0.05,'' if rng.random()<0.18 else f'cx{i}',rng.choice(['positive','negative']))
        want=oracle(q,inherited,expected_seen,expected_consumed)
        got=gate.admit(q).status
        if got!=want:mismatches+=1
        if got=='ADMISSION_READY' and want!='ADMISSION_READY':false_novelty+=1
        if effect=='CONSUMED_ONCE' and not (effect=='CONSUMED_ONCE' and pid in expected_consumed):expected_consumed.add(pid)
        if want=='ADMISSION_READY':expected_seen.add(c)
        counts[got]+=1; rows.append((pid,got,c,pre,post,effect))
    false_13d=0
    states=0
    for axes in itertools.product(range(3),repeat=13):
        states+=1; got=hard13d_admission(axes); hard=axes[:8]
        want='HOLD_HARD_INVALID' if 0 in hard else ('HOLD_UNRESOLVED' if 1 in hard else 'READY_D0')
        if got!=want:false_13d+=1
    receipt={'schema':'aura.k27.reflexive_telemetry_campaign.v1','cases':10000,'status_counts':dict(sorted(counts.items())),'oracle_mismatches':mismatches,'false_novelty':false_novelty,'13d_states':states,'13d_mismatches':false_13d,'8_crystalline_lenses':['identity','currentness','evidence-polarity','lawful-ancestry','collision','reflexive-effect','reentry','authority'],'authority_minted':False,'gate10':False}
    receipt['campaign_root']=digest({'rows':rows,'receipt_without_root':receipt})
    print(json.dumps(receipt,sort_keys=True,indent=2))
if __name__=='__main__':main()
