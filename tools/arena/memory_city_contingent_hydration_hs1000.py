from __future__ import annotations
import hashlib,json

BOUNDARIES=("source_span","parent_currentness","branch_reveal","support_generation","invariant_component","hydration_capacity","deadline","lease_scope","k27_route","effect_cut")
FAILURES=("clairvoyant_future","fixed_union_overhydrate","hidden_invariant_bridge","stale_lease","source_identity_drift","span_content_drift","capacity_exhaustion","deadline_miss","dense_support","authority_crosscast")
MECHANISMS=("exact_component_quotient","nonanticipatory_prefetch","branch_remaining_plan","support_rebind","span_rehydrate","currentness_rebind","capacity_hold","deadline_hold","global_collapse","counterexample_receipt")

def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"))
def root(x): return hashlib.sha256(canon(x).encode()).hexdigest()

def generate():
    raw=[]; i=0
    for b in BOUNDARIES:
        for f in FAILURES:
            for m in MECHANISMS:
                raw.append({"candidate_id":f"MC-HS1000-{i:04d}","boundary":b,"failure":f,"mechanism":m,"expected_gain":"UNSCORED_AT_FREEZE","status":"CANDIDATE_NOT_BREAKTHROUGH","authority":"D0_NONPROMOTING"}); i+=1
    assert len(raw)==1000
    freeze_root=root(raw)
    groups={}
    for x in raw: groups.setdefault((x["boundary"],x["failure"]),[]).append(x["candidate_id"])
    quot=[{"boundary":k[0],"failure":k[1],"members":v} for k,v in sorted(groups.items())]
    assert len(quot)==100
    score_mech={"exact_component_quotient":9,"nonanticipatory_prefetch":10,"branch_remaining_plan":9,"support_rebind":8,"span_rehydrate":7,"currentness_rebind":8,"capacity_hold":5,"deadline_hold":5,"global_collapse":6,"counterexample_receipt":7}
    scored=[]
    for x in raw:
        score=score_mech[x["mechanism"]]
        if x["failure"] in {"clairvoyant_future","hidden_invariant_bridge","stale_lease","authority_crosscast"}: score+=3
        if x["boundary"] in {"branch_reveal","support_generation","invariant_component","effect_cut"}: score+=2
        scored.append((score,x["candidate_id"],x))
    top27=[dict(x,post_freeze_score=s) for s,_,x in sorted(scored,key=lambda z:(-z[0],z[1]))[:27]]
    return {"schema":"AURA-MC-HS1000-v1","raw_count":1000,"freeze_root":freeze_root,"quotient_count":100,"quotients":quot,"top27":top27,"raw":raw}

if __name__=="__main__": print(canon(generate()))
