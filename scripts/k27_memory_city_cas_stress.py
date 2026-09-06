#!/usr/bin/env python3
"""Bounded five-worker ABA/CAS adversarial replay for K27 Memory City.

The target coordinate (4,13,0) is an explicit synthetic fixture. Every database
is temporary. The repository-owned canonical registry is never mutated.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from aura_k27_memory_city import FrameAddress, MemoryConflict, MemoryStore

FRAME = "aura-memory-city-lane-c-stress"
GEN = "fixture-v1"
OBJECT_ID = "LANE-C/CAS-HOTSPOT"
ADDRESS = FrameAddress(FRAME, GEN, (4,13,0), OBJECT_ID)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def one_round(index: int) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"k27-cas-{index:04d}-") as td:
        dbpath=Path(td)/"stress.sqlite"
        with MemoryStore(dbpath) as seed:
            seed.register_frame(FRAME,GEN)
            first=seed.publish(OBJECT_ID, {"value":"A"}, ADDRESS, source_url="fixture:lane-c", source_version="1")
            observed=seed.get(OBJECT_ID)
        barrier=threading.Barrier(5)
        results=[]
        lock=threading.Lock()
        def worker(worker_id: int):
            with MemoryStore(dbpath) as store:
                barrier.wait(timeout=5)
                try:
                    commit=store.publish(OBJECT_ID, {"value":f"B{worker_id}"}, ADDRESS,
                        source_url="fixture:lane-c", source_version=f"worker-{worker_id}",
                        expected_revision=observed["revision_id"], expected_epoch=observed["epoch"])
                    item={"worker":worker_id,"disposition":"COMMIT","revision_id":commit["revision_id"],"epoch":commit["epoch"]}
                except MemoryConflict:
                    item={"worker":worker_id,"disposition":"HOLD_STALE_DEPENDENCY"}
            with lock: results.append(item)
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures=[pool.submit(worker,i) for i in range(5)]
            for f in futures: f.result(timeout=10)
        commits=[r for r in results if r["disposition"]=="COMMIT"]
        holds=[r for r in results if r["disposition"]=="HOLD_STALE_DEPENDENCY"]
        if len(commits)!=1 or len(holds)!=4:
            raise AssertionError(f"non-deterministic CAS outcome: {results}")
        # ABA: retire the winning revision, then restore exact original A payload/revision.
        with MemoryStore(dbpath) as store:
            current=store.get(OBJECT_ID)
            store.retract(OBJECT_ID, expected_revision=current["revision_id"], expected_epoch=current["epoch"])
            retired=store.get(OBJECT_ID,allow_stale=True)
            restored=store.publish(OBJECT_ID, {"value":"A"}, ADDRESS, source_url="fixture:lane-c", source_version="1",
                expected_revision=current["revision_id"], expected_epoch=retired["epoch"])
            if restored["revision_id"] != first["revision_id"]:
                raise AssertionError("ABA fixture did not recreate original content-addressed revision")
            if restored["epoch"] <= observed["epoch"]:
                raise AssertionError("lifecycle epoch did not advance across ABA")
            try:
                store.publish(OBJECT_ID, {"value":"STALE"}, ADDRESS, source_url="fixture:lane-c", source_version="stale",
                    expected_revision=observed["revision_id"], expected_epoch=observed["epoch"])
            except MemoryConflict:
                aba_blocked=True
            else:
                aba_blocked=False
            if not aba_blocked:
                raise AssertionError("ABA stale token was accepted")
        return {
            "round":index,"attempts":5,"commits":1,"holds":4,"aba_blocked":1,"aba_violations":0,
            "false_readiness":0,"original_revision":observed["revision_id"],"restored_epoch":restored["epoch"]
        }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--rounds",type=int,default=750); args=ap.parse_args()
    if args.rounds < 1 or args.rounds > 10000: raise SystemExit("rounds must be 1..10000")
    campaign=hashlib.sha256(); totals={"rounds":0,"attempts":0,"commits":0,"holds":0,"aba_blocked":0,"aba_violations":0,"false_readiness":0}
    for i in range(args.rounds):
        r=one_round(i); campaign.update(canonical(r).encode())
        totals["rounds"]+=1
        for key in ("attempts","commits","holds","aba_blocked","aba_violations","false_readiness"): totals[key]+=r[key]
    receipt={
        "schema":"aura-k27-memory-city-cas-aba-candidate-v1",
        "synthetic_fixture":True,"target_coordinate":[4,13,0],"canonical_store_mutated":False,
        **totals,"campaign_root":campaign.hexdigest(),
        "keeper_law":"RevisionEqualityAfterABA != EpochEquality",
        "authority_minted":False,"gate10":False,"canonical_promotion":False,
    }
    expected={"attempts":args.rounds*5,"commits":args.rounds,"holds":args.rounds*4,"aba_blocked":args.rounds,"aba_violations":0,"false_readiness":0}
    if any(receipt[k]!=v for k,v in expected.items()): raise SystemExit("campaign totals violated invariant")
    print(json.dumps(receipt,sort_keys=True))

if __name__=='__main__': main()
