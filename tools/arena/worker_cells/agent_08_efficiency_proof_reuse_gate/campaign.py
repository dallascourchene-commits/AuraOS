from dataclasses import replace
from hashlib import sha256
from itertools import product
import json, random
from efficiency_proof_reuse_gate import *

def semantic_campaign(seed=808, hs=1000, destructive=50000, tails=100000):
    rng=random.Random(seed); base=valid_evidence()
    def mutate(e,i):
        m=i%12
        if m==0: return replace(e,proof=replace(e.proof,semantic_commit="1"*40))
        if m==1: return replace(e,proof=replace(e.proof,verifier_blob="1"*40))
        if m==2: return replace(e,proof=replace(e.proof,expected_event_root=digest({"drift":"event"})))
        if m==3: return replace(e,proof=replace(e.proof,expected_execution_provenance_root=digest({"drift":"exec"})))
        if m==4: return replace(e,cost=replace(e.cost,semantic_commit="1"*40))
        if m==5: return replace(e,cost=replace(e.cost,verifier_blob="1"*40))
        if m==6:
            ss=list(e.cost.samples); ss[1]=replace(ss[1],rendered_prefix=ss[0].rendered_prefix); return replace(e,cost=replace(e.cost,samples=tuple(ss)))
        if m==7: return replace(e,cost=replace(e.cost,envelope=replace(e.cost.envelope,source_head="1"*40)))
        if m==8: return replace(e,cost=replace(e.cost,envelope=replace(e.cost.envelope,speculative_energy_budget_j="0.0000001")))
        if m==9: return replace(e,proved_proof_projection_root="e"*64)
        if m==10: return replace(e,proved_cost_projection_root="f"*64)
        return replace(e,authority_requested=True)
    false=sum(assess(mutate(base,i)).decision!=Decision.REPROVE for i in range(hs))
    destructive_false=0
    for _ in range(destructive): destructive_false += assess(mutate(base,rng.randrange(12))).decision!=Decision.REPROVE
    omega=sum(crystalline_admission(x) for x in product(range(3),repeat=8))
    invalid=replace(base,proved_cost_projection_root="f"*64); invalid_receipt=assess(invalid); repairs=0; context_roots=set()
    if invalid_receipt.decision != Decision.REPROVE: raise RuntimeError("invalid base unexpectedly reusable")
    for _ in range(tails):
        tail=tuple(rng.randrange(3) for _ in range(5)); r=recontextualize(invalid_receipt,tail); context_roots.add(r.context_root); repairs += r.decision!=Decision.REPROVE
    semantic={"schema":"AURA-WQ-EFFICIENCY-PROOF-REUSE-CAMPAIGN-v2","hs_cases":hs,"hs_false_admits":false,"destructive_handoffs":destructive,"destructive_false_reuses":destructive_false,"omega8_states":3**8,"omega8_keepers":omega,"tails_13d":tails,"distinct_context_roots":len(context_roots),"tails_13d_repairs":repairs,"valid_receipt_root":assess(base).receipt_root}
    root=sha256(json.dumps(semantic,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return semantic,root
if __name__=="__main__":
    s,r=semantic_campaign(); print(json.dumps({"semantic":s,"campaign_root":r},sort_keys=True))
