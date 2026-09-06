from __future__ import annotations
from dataclasses import replace
import hashlib, json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.arena.frontier27_runtime import CollisionBucket, CurrentnessInvalidator
from tools.arena.consequence_admission_kernel import ConsequenceAdmissionKernel
from tools.arena.research_testspec_proof_reuse_adapter import ProofUnit, ResearchProofContract, ResearchTestSpecProofReuseAdapter

def fixture(**kw):
    c=ResearchProofContract(
        principal="P1",claim_id="C1",claim_digest="cd1",k27=(6,6,14),semantic_key="planfence",
        testspec_root="ts1",semantic_admission_root="sa1",source_id="src1",source_owner_ref="arxiv",
        source_generation="g1",currentness_root="cur1",currentness_verified=True,
        evidence_roots=frozenset({"e1","e2"}),min_independent_roots=2,evidence_ancestry_admitted=True,
        proof_units=(ProofUnit("SOURCE",frozenset({"source.py"}),"p1"),ProofUnit("ORACLE",frozenset({"source.py","oracle.py"}),"p2"),ProofUnit("DOC",frozenset({"README.md"}),"p3")),
        proof_surface={"source.py":"b1","oracle.py":"b2","README.md":"b3"},resolution=2)
    return replace(c,**kw)

def adapter():
    return ResearchTestSpecProofReuseAdapter(secret=b"campaign-secret",bucket=CollisionBucket(),currentness=CurrentnessInvalidator(),kernel=ConsequenceAdmissionKernel())

def run(n=1000):
    false_reuse=0; counts={}; reason_escapes=0
    for i in range(n):
        a=adapter(); a.store(fixture()); p=fixture(); mode=i%12
        if mode==0: p=replace(p,currentness_root=f"mut-cur:{i}",currentness_verified=True)
        elif mode==1: p=replace(p,currentness_root=f"mut-cur:{i}",currentness_verified=False)
        elif mode==2: p=replace(p,claim_digest=f"mut-cd:{i}")
        elif mode==3: p=replace(p,source_generation=f"mut-g:{i}")
        elif mode==4: p=replace(p,semantic_admission_root=f"mut-sa:{i}")
        elif mode==5: p=replace(p,evidence_roots=frozenset({"e1",f"mut-e:{i}"}))
        elif mode==6: p=replace(p,evidence_ancestry_admitted=False)
        elif mode==7: p=replace(p,proof_surface={**p.proof_surface,"source.py":f"mut-b:{i}"})
        elif mode==8: p=replace(p,proof_surface={**p.proof_surface,f"new:{i}.py":"x"})
        elif mode==9: p=replace(p,resolution=1)
        elif mode==10: p=replace(p,currentness_root=f"mut-cur:{i}",currentness_verified=False,proof_surface={**p.proof_surface,"README.md":f"mut-d:{i}"})
        elif mode==11: pass
        try:
            d=a.assess(p); disposition=d.disposition
            if mode==10 and not {"CURRENTNESS_UNVERIFIED","PROOF_SURFACE_DRIFT"}.issubset(d.reasons): reason_escapes+=1
        except ValueError: disposition="REJECT"
        counts[disposition]=counts.get(disposition,0)+1
        if (mode==11 and disposition!="REUSE_EXACT") or (mode!=11 and disposition=="REUSE_EXACT"):
            false_reuse+=1
    all_verified=sum(2*(3**i) for i in range(8))
    omega_keep=sum(1 for x in range(3**8) if x==all_verified)
    tail_repairs=0
    for _ in range(243):
        a=adapter(); a.store(fixture())
        if a.assess(fixture(principal="P2")).disposition=="REUSE_EXACT": tail_repairs+=1
    body={"n":n,"counts":counts,"false_reuse":false_reuse,"reason_escapes":reason_escapes,"omega_keep":omega_keep,"tail_repairs":tail_repairs}
    body["root"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return body

if __name__=="__main__": print(json.dumps(run(),sort_keys=True,indent=2))
