import json,random
from dataclasses import replace
from effect_refinement_seal import *
rng=random.Random(14014); base,ref,cur=fixture(); counts={'cases':20000,'candidate_false_tecc':0,'candidate_false_hold':0,'effect_ready':0,'pr889_unrefined_false_equivalence':0}
reasons={}
records=[]
for i in range(20000):
    kind=i%5; rr=ref; cc=cur; oracle=True
    if kind==1: cc=replace(cur,intent_binding_root=root(f'intent-move-{i}')); oracle=False
    elif kind==2: cc=replace(cur,effect_obligation_root=root(f'obligation-move-{i}')); oracle=False
    elif kind==3: cc=replace(cur,refinement_plan_root=root(f'plan-move-{i}')); oracle=False
    elif kind==4: cc=replace(cur,refinement_owner_receipt_root=root(f'owner-move-{i}')); oracle=False
    d=compile_refined_tecc_seal(base,rr,cc); routed=d.disposition==Disp.HOLD_TECC_REQUIRED_D0
    if routed and not oracle: counts['candidate_false_tecc']+=1
    if (not routed) and oracle: counts['candidate_false_hold']+=1
    if d.effect_authority: counts['effect_ready']+=1
    if not oracle: counts['pr889_unrefined_false_equivalence']+=1
    reasons[d.reason]=reasons.get(d.reason,0)+1
    records.append((kind,d.disposition.value,d.reason,d.refined_tecc_input_root))
counts['reason_counts']=dict(sorted(reasons.items())); counts['campaign_root']=digest(records)
print(json.dumps(counts,sort_keys=True,separators=(',',':')))
