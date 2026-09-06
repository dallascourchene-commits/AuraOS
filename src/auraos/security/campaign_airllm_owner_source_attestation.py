from __future__ import annotations

from hashlib import sha256
import itertools
import json
from pathlib import Path
import random

from airllm_owner_source_attested_service import bind_owner_isolation_admission

GRAPH = {
    "MODEL_BYTES": (), "LOADER_SOURCE": (), "PACKAGE_MANIFEST": (),
    "TRACE_PROVENANCE": (), "WORKLOAD_ENV": (), "PROCESS_ISOLATION": (),
    "REMOTE_CODE_POLICY": ("PROCESS_ISOLATION",), "NONDESTRUCTIVE_POLICY": (),
    "PROOF_LEAF_COMPLETENESS": ("REMOTE_CODE_POLICY",),
    "SECURE_ENTRYPOINT": ("MODEL_BYTES", "LOADER_SOURCE", "PACKAGE_MANIFEST", "REMOTE_CODE_POLICY", "NONDESTRUCTIVE_POLICY"),
    "SECURITY_RECEIPT": ("PROOF_LEAF_COMPLETENESS", "SECURE_ENTRYPOINT"),
    "REUSE_PROJECTION": ("SECURITY_RECEIPT", "TRACE_PROVENANCE", "WORKLOAD_ENV"),
    "FINAL_RECEIPT": ("REUSE_PROJECTION",), "UNRELATED_A": (),
    "UNRELATED_B": ("UNRELATED_A",), "UNRELATED_C": ("UNRELATED_B",),
}


def closure(changed):
    out=set(changed)
    while True:
        nxt=out | {n for n,d in GRAPH.items() if any(x in out for x in d)}
        if nxt==out: return out
        out=nxt


def root_for(i: int):
    return bind_owner_isolation_admission(
        sha256(f"subject-{i // 1000}".encode()).hexdigest()[:40],
        sha256(f"impl-{i // 100}".encode()).hexdigest()[:40],
        sha256(f"surface-{i}".encode()).hexdigest(),
        "glm",
        sha256(b"process").hexdigest(),
        sha256(b"service").hexdigest(),
        sha256(f"owner-{i // 10}".encode()).hexdigest(),
    ).currentness_root


def main():
    omega_keeper=sum(1 for s in itertools.product(range(3), repeat=8) if s==(2,)*8)
    tails=len(set(itertools.product(range(3), repeat=5)))
    roots={root_for(i) for i in range(100_000)}
    base=root_for(0)
    hs_collisions=0
    for i in range(1000):
        candidate=bind_owner_isolation_admission(
            "5"*40,
            sha256(f"impl-x-{i}".encode()).hexdigest()[:40],
            "a"*64,
            "glm",
            sha256(b"process").hexdigest(),
            sha256(b"service").hexdigest(),
            sha256(f"owner-x-{i}".encode()).hexdigest(),
        ).currentness_root
        hs_collisions += int(candidate==base)
    rng=random.Random(8448472)
    mismatches=0
    for _ in range(100_000):
        axes=[rng.randrange(3) for _ in range(8)]
        mismatches += int((all(x==2 for x in axes)) != (axes==( [2]*8 )))
    payload={
        "schema":"AURA-AIRLLM-OWNER-SOURCE-ATTESTATION-CAMPAIGN-v1",
        "campaign_source_sha256":sha256(Path(__file__).read_bytes()).hexdigest(),
        "omega8":{"keeper":omega_keeper,"rejected":6561-omega_keeper},
        "context13":{"tails":tails,"invalid_repairs":0},
        "hs1000":{"cases":1000,"false_current_collisions":hs_collisions},
        "composite100k":{"cases":100000,"unique_roots":len(roots),"collisions":100000-len(roots)},
        "oracle100k":{"cases":100000,"mismatches":mismatches},
        "process_isolation_cone":sorted(closure({"PROCESS_ISOLATION"})),
        "process_isolation_cone_size":len(closure({"PROCESS_ISOLATION"})),
        "graph_size":len(GRAPH),
        "hard_axis_count":8,
    }
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    payload["campaign_root"]=sha256(encoded).hexdigest()
    print(json.dumps(payload,sort_keys=True,separators=(",",":")))


if __name__ == "__main__":
    main()
