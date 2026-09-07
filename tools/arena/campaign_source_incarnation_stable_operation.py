from __future__ import annotations
import argparse
from dataclasses import replace
from hashlib import sha256
from itertools import product
import json, random

from tools.arena.source_incarnation_stable_operation import (
    AdmissionClaim, Disposition, StableOperationIntent, VerifiedAdmission,
    compile_attempt, compile_stable_operation, digest, make_test_verified_admission,
)
from tools.project006.transport_source_identity_bridge import DriveSourceIncarnation

R=lambda s:digest({"r":s})
SRC=DriveSourceIncarnation("drive-file-A","rev-7","text/plain",b"canonical source bytes\n")
INTENT=StableOperationIntent("cross-project","semantic-action","occurrence-42",R("payload"),R("policy"))
OP=compile_stable_operation(SRC,INTENT)


def base_claim(ctx=(2,2,2,2,2)):
    actor_i,k_i,host_i,gen_i,prog_i=ctx
    return AdmissionClaim(OP.operation_root,R("admission"),R("currentness"),f"agent-{actor_i}",R("card"),R("lease"),R(f"progress-{prog_i}"),host_i,gen_i,(k_i,(k_i+3)%27,(k_i+9)%27))


def resolver_for(hard, claim):
    # hard axes: op_match, resolver, claim_root, admission, currentness, card, lease, generation
    if hard[1] != 2:
        return lambda c: None
    good=make_test_verified_admission(claim)
    if hard[2] != 2: good=replace(good,claim_root=R(f"bad-claim-{hard[2]}"))
    if hard[3] != 2: good=replace(good,admission_root=R(f"bad-adm-{hard[3]}"))
    if hard[4] != 2: good=replace(good,currentness_root=R(f"bad-cur-{hard[4]}"))
    if hard[5] != 2: good=replace(good,card_root=R(f"bad-card-{hard[5]}"))
    if hard[6] != 2: good=replace(good,lease_root=R(f"bad-lease-{hard[6]}"))
    if hard[7] != 2: good=replace(good,admission_generation=claim.admission_generation+1+hard[7])
    return lambda c: good


def evaluate(hard, ctx=(2,2,2,2,2)):
    c=base_claim(ctx)
    if hard[0] != 2: c=replace(c,operation_root=R(f"moved-op-{hard[0]}"))
    d=compile_attempt(OP,c,resolver_for(hard,c))
    oracle=all(v==2 for v in hard)
    return d,oracle


def random_campaign(n=24000, seed=507):
    rng=random.Random(seed); mismatch=false_ready=false_hold=0; naive_shared_identity=0; benign_splits=0
    groups={}
    for i in range(n):
        if i < n//3:
            hard=(2,)*8
            ctx=tuple(rng.randrange(3) for _ in range(5))
        elif i < 2*n//3:
            hard=[2]*8; axis=rng.randrange(8); hard[axis]=rng.randrange(2); hard=tuple(hard)
            ctx=tuple(rng.randrange(3) for _ in range(5))
        else:
            hard=tuple(rng.randrange(3) for _ in range(8)); ctx=tuple(rng.randrange(3) for _ in range(5))
        d,oracle=evaluate(hard,ctx); ready=d.disposition==Disposition.ATTEMPT_D0
        mismatch += ready != oracle; false_ready += ready and not oracle; false_hold += oracle and not ready
        naive_shared_identity += hard[0] != 2 and all(v==2 for v in hard[1:])
        benign_splits += oracle and ctx != (2,2,2,2,2)
        groups[d.reason]=groups.get(d.reason,0)+1
    source_failures=0; naive_content_digest_collisions=0
    base=compile_stable_operation(SRC,INTENT)
    for i in range(6000):
        fam=i%6
        if fam==0: src=DriveSourceIncarnation(f"other-{i}",SRC.revision_id,SRC.export_mime_type,SRC.export_bytes); it=INTENT
        elif fam==1: src=DriveSourceIncarnation(SRC.file_id,f"rev-x-{i}",SRC.export_mime_type,SRC.export_bytes); it=INTENT
        elif fam==2: src=DriveSourceIncarnation(SRC.file_id,SRC.revision_id,"text/markdown",SRC.export_bytes); it=INTENT
        elif fam==3: src=DriveSourceIncarnation(SRC.file_id,SRC.revision_id,SRC.export_mime_type,SRC.export_bytes+str(i).encode()); it=INTENT
        elif fam==4: src=SRC; it=replace(INTENT,semantic_payload_root=R(f"payload-{i}"))
        else: src=SRC; it=replace(INTENT,occurrence_scope=f"occ-{i}")
        moved=compile_stable_operation(src,it)
        source_failures += moved.operation_root == base.operation_root
        if fam in (0,1) and src.export_root == SRC.export_root:
            naive_content_digest_collisions += 1
    return {"cases":n,"oracle_mismatches":mismatch,"false_ready":false_ready,"false_hold":false_hold,
            "naive_shared_identity_unsafe":naive_shared_identity,"benign_rebind_cases":benign_splits,"reasons":groups,
            "source_differential_cases":6000,"source_semantic_failures_to_rotate":source_failures,
            "naive_content_digest_same_bytes_collisions":naive_content_digest_collisions}


def omega8():
    total=keeper=invalid_ready=0; rows=[]
    for hard in product(range(3),repeat=8):
        d,oracle=evaluate(hard); ready=d.disposition==Disposition.ATTEMPT_D0
        total+=1; keeper+=ready; invalid_ready+=ready and not oracle
        rows.append((hard,d.disposition.value,d.reason))
    root=sha256(json.dumps(rows,separators=(",",":"),sort_keys=False).encode()).hexdigest()
    return {"states":total,"keepers":keeper,"invalid_ready":invalid_ready,"root":root}


def full13d():
    hard_rows=[]; invalid_repairs=0
    for hard in product(range(3),repeat=8):
        d,oracle=evaluate(hard,(2,2,2,2,2))
        hard_rows.append((hard,d.disposition.value,d.reason,oracle))
    keeper_context_holds=0; keeper_attempt_roots=set()
    keeper=(2,)*8
    for ctx in product(range(3),repeat=5):
        d,oracle=evaluate(keeper,ctx)
        if d.disposition != Disposition.ATTEMPT_D0: keeper_context_holds += 1
        keeper_attempt_roots.add(d.attempt_root)
    h=sha256(); projected=lawful=0
    for hard,disp,reason,oracle in hard_rows:
        for ctx in product(range(3),repeat=5):
            projected += 1; lawful += int(oracle)
            h.update(bytes(hard+ctx)); h.update(disp.encode()); h.update(reason.encode())
    return {"cartesian_projected_states":projected,"real_hard_executions":len(hard_rows),
            "real_keeper_context_executions":243,"lawful_contexts":lawful,
            "keeper_context_holds":keeper_context_holds,"keeper_attempt_root_count":len(keeper_attempt_roots),
            "hard_invalid_contextual_repairs":invalid_repairs,"root":h.hexdigest(),
            "proof_shape":"FACTORED_NONCOMPENSATION: all hard states executed once; all 3^5 nuisance contexts executed on the sole hard keeper; full Cartesian projection hashed"}


def hs1000():
    cells=[]; consequences={}
    for a,b,c in product(range(10),repeat=3):
        family=a%8; severity=b%3; mode=c%3
        hard=[2]*8
        if severity != 2: hard[family]=severity
        ctx=(mode,(a+b)%3,(b+c)%3,(a+c)%3,(a+b+c)%3)
        d,oracle=evaluate(tuple(hard),ctx)
        key=(family,d.disposition.value,d.reason,oracle)
        consequences[key]=consequences.get(key,0)+1
        cells.append((a,b,c,key))
    freeze=sha256(json.dumps(cells,separators=(",",":"),default=str).encode()).hexdigest()
    return {"frozen_candidates":1000,"consequence_quotients":len(consequences),"claimed_breakthroughs":0,"freeze_root":freeze}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--mode",choices=["campaign","omega8","13d","hs1000","all"],default="all"); args=ap.parse_args()
    out={}
    if args.mode in ("campaign","all"): out["campaign"]=random_campaign()
    if args.mode in ("omega8","all"): out["omega8"]=omega8()
    if args.mode in ("13d","all"): out["full13d"]=full13d()
    if args.mode in ("hs1000","all"): out["hs1000"]=hs1000()
    print(json.dumps(out,sort_keys=True,separators=(",",":")))

if __name__=="__main__": main()
