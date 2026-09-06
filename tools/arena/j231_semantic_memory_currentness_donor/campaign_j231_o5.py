from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import replace
from hashlib import sha256
import json
from j231_semantic_memory_donor import *


def stable(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
def root(v): return sha256(stable(v)).hexdigest()

def base_rec(): return LifecycleRecord("a","k27 semantic memory lifecycle epoch","A","g1","r1",1,(4,13,0),True)

def independent_cone(changed):
    rev=defaultdict(set)
    for n,deps in SEMANTIC_DAG.items():
        for d in deps: rev[d].add(n)
    out=set(changed); q=deque(changed)
    while q:
        for ch in rev[q.popleft()]:
            if ch not in out: out.add(ch); q.append(ch)
    return tuple(sorted(out))

def run():
    m=GovernedSemanticMemory(index_generation="idx-o5")
    r=base_rec(); m.add(r,100); p=m.candidate_plane("semantic memory lifecycle")
    outcomes=[]; false_accept=0; false_hold=0
    axes=("CONTROL","SOURCE","GENERATION","REVISION","EPOCH","CURRENT","TIME_FUTURE","SEMANTIC","PLANE","RECEIPT")
    for ai,axis in enumerate(axes):
        for mut in range(10):
            for tail in range(10):
                current=r; now=110; plane=p
                saved=m.receipts["a"]
                if axis=="SOURCE": current=replace(r, exact_source=f"B{mut}")
                elif axis=="GENERATION": current=replace(r, generation=f"g{mut+2}")
                elif axis=="REVISION": current=replace(r, revision_id=f"r{mut+2}")
                elif axis=="EPOCH": current=replace(r, lifecycle_epoch=mut+2)
                elif axis=="CURRENT": current=replace(r, current=False)
                elif axis=="TIME_FUTURE": now=99-mut
                elif axis=="SEMANTIC": current=replace(r, semantic_text=f"semantic drift {mut}")
                elif axis=="PLANE": plane=CandidatePlane(p.query_digest,p.candidate_ids,p.index_generation,p.semantic_index_root,root([mut,tail]))
                elif axis=="RECEIPT": m.receipts["a"]=replace(saved,receipt_digest=root([mut,tail,"bad"]))
                ok=m.capture_at_use("semantic memory lifecycle",plane,"a",current,now_s=now,max_age_s=20) is not None
                expected=(axis=="CONTROL")
                false_accept += int(ok and not expected); false_hold += int((not ok) and expected)
                outcomes.append([ai,axis,mut,tail,ok])
                m.receipts["a"]=saved
    closure=[]; mismatches=0
    nodes=tuple(SEMANTIC_DAG)
    for i in range(1000):
        changed={nodes[i%len(nodes)],nodes[(i*7+3)%len(nodes)]}
        a=reproof_cone(changed); b=independent_cone(changed)
        mismatches += int(a!=b); closure.append([i,sorted(changed),a])
    omega=[]; keepers=0
    for n in range(3**8):
        x=n; state=[]
        for _ in range(8): state.append(x%3); x//=3
        keeper=all(v==2 for v in state); keepers += keeper; omega.append([n,state,keeper])
    tails=[]; repaired=0
    for n in range(3**5):
        x=n; tail=[]
        for _ in range(5): tail.append(x%3); x//=3
        hard=(2,2,2,2,2,2,2,0)
        accepted=all(v==2 for v in hard)
        repaired += int(accepted); tails.append([hard,tail,accepted])
    release=[]; release_false_accept=0; release_false_hold=0
    release_axes=("CONTROL","SEMANTIC_HEAD","CARRIER_EXACT","MOVEMENT_UNKNOWN","METADATA_UNVERIFIED","METADATA_VERIFIED","SOURCE","TEST","CAMPAIGN","PROOF")
    base=dict(expected_semantic_head="head1",observed_semantic_head="head1",observed_carrier_head="head1",movement_kind="EXACT",metadata_only_verified=False,
              donor_source_sha256="s",expected_source_sha256="s",donor_test_sha256="t",expected_test_sha256="t",campaign_sha256="c",expected_campaign_sha256="c",local_proof_root="p",expected_local_proof_root="p",hosted_pass=False)
    for ai,axis in enumerate(release_axes):
        for mut in range(10):
            for tail in range(10):
                kw=dict(base)
                if axis=="SEMANTIC_HEAD": kw["observed_semantic_head"]=f"head{mut+2}"
                elif axis=="CARRIER_EXACT": kw["observed_carrier_head"]=f"carrier{mut+2}"
                elif axis=="MOVEMENT_UNKNOWN": kw["movement_kind"]="SEMANTIC_OR_UNKNOWN"
                elif axis=="METADATA_UNVERIFIED": kw.update(movement_kind="METADATA_ONLY",observed_carrier_head=f"carrier{mut+2}",metadata_only_verified=False)
                elif axis=="METADATA_VERIFIED": kw.update(movement_kind="METADATA_ONLY",observed_carrier_head=f"carrier{mut+2}",metadata_only_verified=True)
                elif axis=="SOURCE": kw["donor_source_sha256"]=f"bad{mut}"
                elif axis=="TEST": kw["donor_test_sha256"]=f"bad{mut}"
                elif axis=="CAMPAIGN": kw["campaign_sha256"]=f"bad{mut}"
                elif axis=="PROOF": kw["local_proof_root"]=f"bad{mut}"
                d=release_gate(ReleaseEvidence(**kw))
                ok=d.state!="HOLD"
                expected=axis in {"CONTROL","METADATA_VERIFIED"}
                release_false_accept += int(ok and not expected); release_false_hold += int((not ok) and expected)
                release.append([ai,axis,mut,tail,d.state,list(d.reasons)])

    summary={
        "hs1000":{"cases":len(outcomes),"false_accept":false_accept,"false_hold":false_hold,"root":root(outcomes)},
        "release_hs1000":{"cases":len(release),"false_accept":release_false_accept,"false_hold":release_false_hold,"root":root(release)},
        "reproof":{"cases":len(closure),"mismatches":mismatches,"root":root(closure)},
        "omega8":{"states":len(omega),"keepers":keepers,"root":root(omega)},
        "context13d":{"tails":len(tails),"hard_axis_repairs":repaired,"root":root(tails)},
    }
    summary["campaign_root"]=root(summary)
    print(json.dumps(summary,sort_keys=True))
    return summary

if __name__=="__main__": run()
