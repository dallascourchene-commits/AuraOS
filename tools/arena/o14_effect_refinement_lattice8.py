import itertools,json
from dataclasses import replace
from effect_refinement_seal import *
base0,ref0,cur0=fixture(); cand=legacy=false=0; rows=[]
for axes in itertools.product(range(3), repeat=8):
    b,r,c=base0,ref0,cur0
    if axes[0]!=2: b=replace(b,disposition='HOLD')
    if axes[1]!=2: c=replace(c,active_read_binding_root=root('bind-'+str(axes[1])))
    if axes[2]!=2: c=replace(c,intent_binding_root=root('intent-'+str(axes[2])))
    if axes[3]!=2: c=replace(c,effect_escalation_root=root('esc-'+str(axes[3])))
    if axes[4]!=2: c=replace(c,refinement_plan_root=root('plan-'+str(axes[4])))
    if axes[5]!=2: c=replace(c,effect_obligation_root=root('obl-'+str(axes[5])))
    if axes[6]!=2: c=replace(c,refinement_owner_receipt_root=root('own-'+str(axes[6])))
    if axes[7]!=2: r=replace(r,effect_authority=True)
    d=compile_refined_tecc_seal(b,r,c); oracle=all(x==2 for x in axes); route=d.disposition==Disp.HOLD_TECC_REQUIRED_D0
    cand+=route; legacy_route=(axes[0]==2); legacy+=legacy_route; false+=bool(legacy_route and not oracle)
    rows.append((axes,d.disposition.value,d.reason))
out={'lattice8_states':6561,'candidate_tecc_routes':cand,'candidate_false_tecc':cand-1,'pr889_unrefined_routes':legacy,'pr889_unrefined_false_routes':false,'root':digest(rows)}
print(json.dumps(out,sort_keys=True,separators=(',',':')))
