from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
from subreaper_containment import fixed_point_contain, group_only_falsifier

SURFACES=['watchdog','worker_tree','session_boundary','pid_identity','reap_state','resource_budget','k27_reopen','hyperdrive','effect_boundary','authority']
MECH=['direct_pid','process_group','subreaper_adoption','pidfd_signal','fixed_point_scan','stable_empty','descendant_budget','typed_hold','semantic_receipt','cgroup_target']
FALS=['setsid_escape','doublefork','fanout','pid_reuse','fork_race','unreaped_zombie','budget_overrun','deadline','external_effect','authority_widen']

def digest(o): return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def classify(s,m,f):
    if f=='authority_widen' or s=='authority': return 'HOLD_AUTHORITY'
    if m in ('direct_pid','process_group') and f in ('setsid_escape','doublefork','fanout'): return 'HOLD_SCOPE_ESCAPE'
    if m=='cgroup_target': return 'HOLD_CGROUP_DIRECT_GAP'
    if f=='external_effect' or s=='effect_boundary': return 'HOLD_EFFECT_ROLLBACK_UNPROVEN'
    if f=='pid_reuse' and m!='pidfd_signal': return 'HOLD_PID_IDENTITY_RACE'
    if f in ('fork_race','unreaped_zombie') and m not in ('subreaper_adoption','fixed_point_scan','stable_empty'): return 'HOLD_REAP_TOTALITY'
    return 'CANDIDATE_SUBREAPER_FIXED_POINT'

def main():
    worker=str(Path(__file__).parent/'tree_worker.py')
    base=group_only_falsifier(worker=worker,mode='escaped')
    physical=[]
    for mode in ['escaped','doublefork','fanout8']:
        for _ in range(3):
            r=fixed_point_contain(worker=worker,mode=mode,max_descendants=32)
            physical.append({'mode':mode,'disposition':r.disposition,'survivors':r.survivors,'pidfd':r.pidfd_supported,'pidfd_signals_positive':r.pidfd_signals>0})
    caps=[]; counts={}
    parent='0'*64
    for i,(s,m,f) in enumerate(( (s,m,f) for s in SURFACES for m in MECH for f in FALS),1):
        disp=classify(s,m,f); counts[disp]=counts.get(disp,0)+1
        cap={'ordinal':i,'surface':s,'mechanism':m,'falsifier':f,'disposition':disp,'parent':parent}
        root=digest(cap); cap['root']=root; parent=root; caps.append(cap)
    # quotient by consequence plus attacked mechanism family; deterministic one winner each bucket
    buckets={}
    for c in caps:
        key=(c['disposition'],c['mechanism'])
        buckets.setdefault(key,c)
    top=sorted(buckets.values(),key=lambda c:(c['disposition']!='CANDIDATE_SUBREAPER_FIXED_POINT',c['ordinal']))[:27]
    out={'schema':'AURA-R10.6-HS1000-v1','cells':len(caps),'consequence_counts':counts,
         'candidate_stream_root':digest([c['root'] for c in caps]),'final_compound_root':parent,
         'quotient_groups':len(buckets),'quotient_root':digest([c['root'] for c in buckets.values()]),
         'top27_root':digest([c['root'] for c in top]),'group_only_falsifier':base,'physical':physical,
         'physical_all_expected':all(x['disposition']=='CONTAINED' and x['survivors']==0 for x in physical),
         'cgroup_direct_gap':True,'authority':'D0_NONOWNER_CANARY'}
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
if __name__=='__main__': main()
