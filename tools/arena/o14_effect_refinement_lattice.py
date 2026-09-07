from __future__ import annotations
from dataclasses import replace
from hashlib import sha256
import itertools,json
from campaign_memory_city_effect_refinement_handoff_o14 import fixture,hx
from memory_city_effect_handoff_o13 import HandoffDisposition
from memory_city_effect_refinement_handoff_o14 import compile_effect_refined_handoff

def run():
    counts={"states":0,"candidate_tecc":0,"oracle_tecc":0,"false_tecc":0,"false_hold":0,"effect_ready":0}
    for axes in itertools.product(range(3),repeat=8):
        cert,kw,ref,current=fixture("omega8"); counts["states"]+=1
        if axes[0]==0: kw["verification"]=replace(kw["verification"],now=100)
        elif axes[0]==1: kw["mutation"]=replace(kw["mutation"],revision=5)
        cur=current; fields=("plan_root","intent_binding_root","obligation_root","escalation_root","owner_receipt_root","verifier_receipt_root","read_binding_root")
        for idx,field in enumerate(fields,1):
            if axes[idx]!=2: cur=replace(cur,**{field:hx(f"{field}:{axes[idx]}")})
        d=compile_effect_refined_handoff(cert,**kw,refinement=ref,refinement_verification=cur)
        got=d.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0; exp=all(x==2 for x in axes)
        counts["candidate_tecc"]+=got;counts["oracle_tecc"]+=exp;counts["false_tecc"]+=got and not exp;counts["false_hold"]+=(not got) and exp;counts["effect_ready"]+=d.effect_authority
    payload={"schema":"AURA-O14-OMEGA8-v2-INTEGRATED","counts":counts};payload["root"]=sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest();return payload
if __name__=="__main__":print(json.dumps(run(),sort_keys=True,separators=(",",":")))
