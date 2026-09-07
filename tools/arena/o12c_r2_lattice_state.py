from __future__ import annotations
from dataclasses import replace
from campaign_memory_city_effect_handoff_o12c_r2 import state, R
from memory_city_effect_handoff_o12c_r2 import digest

# Eight hard ternary axes: 0 invalid, 1 stale/unresolved, 2 exact-current.
def mutate(hard, tag="lattice"):
    h,t,c,u,ro,a,r,e,m,v=state(tag)
    x=list(hard)
    if x[0]==0: v=replace(v,active_read_binding_root=R(["bad-binding",tag]))
    elif x[0]==1: v=replace(v,read_owner_receipt_root=R(["stale-read-owner",tag]))
    if x[1]==0:
        a=dict(a);a["schema"]="OTHER";a.pop("receipt_root");a["receipt_root"]=digest(a)
    elif x[1]==1:
        a=dict(a);a.pop("effect_authority");a.pop("receipt_root");a["receipt_root"]=digest(a)
    if x[2]==0: c=replace(c,consequence_root=R(["forged-consequence",tag]))
    elif x[2]==1: t=replace(t,transition_model_root=R(["moved-transition",tag]))
    if x[3]==0: r=replace(r,selected_read_binding_root=R(["detached",tag]))
    elif x[3]==1: v=replace(v,effect_escalation_root=R(["moved-escalation",tag]))
    if x[4]==0: v=replace(v,holder="other")
    elif x[4]==1: v=replace(v,revision=8)
    if x[5]==0: m=replace(m,installed_fence_generation=18)
    elif x[5]==1: v=replace(v,fence_generation=20,installed_fence_generation=20)
    if x[6]==0: v=replace(v,owner_evidence_root=R(["stale-owner",tag]))
    elif x[6]==1: v=replace(v,verifier_receipt_root=R(["stale-verifier",tag]))
    if x[7]==0: v=replace(v,now=101)
    elif x[7]==1: v=replace(v,now=100)
    return h,t,c,u,ro,a,r,e,m,v
