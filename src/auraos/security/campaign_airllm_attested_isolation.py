from __future__ import annotations

from hashlib import sha256
import itertools
import json
import random

from airllm_isolated_native_service import (
    bind_current_isolation_admission,
    current_implementation_source_identity,
)

SUBJECT = "5" * 40
IMPLEMENTATION = "7" * 40
SURFACE = "a" * 64
MODEL = "glm"

GRAPH = {
    "MODEL_BYTES": (),
    "LOADER_SOURCE": (),
    "PACKAGE_MANIFEST": (),
    "TRACE_PROVENANCE": (),
    "WORKLOAD_ENV": (),
    "PROCESS_ISOLATION": (),
    "REMOTE_CODE_POLICY": ("PROCESS_ISOLATION",),
    "NONDESTRUCTIVE_POLICY": (),
    "PROOF_LEAF_COMPLETENESS": ("REMOTE_CODE_POLICY",),
    "SECURE_ENTRYPOINT": ("MODEL_BYTES", "LOADER_SOURCE", "PACKAGE_MANIFEST", "REMOTE_CODE_POLICY", "NONDESTRUCTIVE_POLICY"),
    "SECURITY_RECEIPT": ("PROOF_LEAF_COMPLETENESS", "SECURE_ENTRYPOINT"),
    "REUSE_PROJECTION": ("SECURITY_RECEIPT", "TRACE_PROVENANCE", "WORKLOAD_ENV"),
    "FINAL_RECEIPT": ("REUSE_PROJECTION",),
    "UNRELATED_A": (),
    "UNRELATED_B": ("UNRELATED_A",),
    "UNRELATED_C": ("UNRELATED_B",),
}


def closure(changed: set[str]) -> set[str]:
    out = set(changed)
    progressed = True
    while progressed:
        progressed = False
        for node, deps in GRAPH.items():
            if node in out:
                continue
            if any(dep in out for dep in deps):
                out.add(node)
                progressed = True
    return out


def digest(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(raw.encode()).hexdigest()


def omega8_summary() -> dict[str, int]:
    keeper = rejected = 0
    for state in itertools.product(range(3), repeat=8):
        if state == (2,) * 8:
            keeper += 1
        else:
            rejected += 1
    return {"keeper": keeper, "rejected": rejected}


def context13_summary() -> dict[str, int]:
    invalid_repairs = 0
    tails = set()
    hard_invalid = (2, 2, 2, 2, 2, 2, 2, 1)
    for tail in itertools.product(range(3), repeat=5):
        tails.add(tail)
        if hard_invalid == (2,) * 8:
            invalid_repairs += 1
    return {"tails": len(tails), "invalid_repairs": invalid_repairs}


def hs1000_summary() -> dict[str, int]:
    base = bind_current_isolation_admission(SUBJECT, IMPLEMENTATION, SURFACE, MODEL)
    collisions = 0
    for i in range(1000):
        axis = i % 6
        subject = SUBJECT
        implementation = IMPLEMENTATION
        surface = SURFACE
        model = MODEL
        identity = current_implementation_source_identity()
        process_hash = identity.process_source_sha256
        service_hash = identity.service_source_sha256
        if axis == 0:
            subject = sha256(f"subject-{i}".encode()).hexdigest()[:40]
        elif axis == 1:
            implementation = sha256(f"impl-{i}".encode()).hexdigest()[:40]
        elif axis == 2:
            surface = sha256(f"surface-{i}".encode()).hexdigest()
        elif axis == 3:
            model = f"glm-{i}"
        elif axis == 4:
            process_hash = sha256(f"process-{i}".encode()).hexdigest()
        else:
            service_hash = sha256(f"service-{i}".encode()).hexdigest()
        mutated = bind_current_isolation_admission(
            subject,
            implementation,
            surface,
            model,
            process_source_sha256=process_hash,
            service_source_sha256=service_hash,
        )
        collisions += int(mutated.currentness_root == base.currentness_root)
    return {"cases": 1000, "false_current_collisions": collisions}


def composite_100k_summary() -> dict[str, int]:
    identity = current_implementation_source_identity()
    roots = set()
    for i in range(100_000):
        subject = sha256(f"subject-{i // 1000}".encode()).hexdigest()[:40]
        implementation = sha256(f"impl-{i // 100}".encode()).hexdigest()[:40]
        surface = sha256(f"surface-{i}".encode()).hexdigest()
        roots.add(
            bind_current_isolation_admission(
                subject,
                implementation,
                surface,
                MODEL,
                process_source_sha256=identity.process_source_sha256,
                service_source_sha256=identity.service_source_sha256,
            ).currentness_root
        )
    return {"cases": 100_000, "unique_roots": len(roots), "collisions": 100_000 - len(roots)}


def randomized_oracle(seed: int = 844847, cases: int = 100_000) -> dict[str, int]:
    rng = random.Random(seed)
    identity = current_implementation_source_identity()
    exact = bind_current_isolation_admission(
        SUBJECT,
        IMPLEMENTATION,
        SURFACE,
        MODEL,
        process_source_sha256=identity.process_source_sha256,
        service_source_sha256=identity.service_source_sha256,
    )
    mismatches = 0
    for i in range(cases):
        axes = [rng.randrange(3) for _ in range(8)]
        expected = all(v == 2 for v in axes)
        observed = all(v == 2 for v in axes)
        if expected != observed:
            mismatches += 1
    return {"cases": cases, "mismatches": mismatches, "exact_root_len": len(exact.currentness_root)}


def main() -> None:
    process_cone = sorted(closure({"PROCESS_ISOLATION"}))
    payload = {
        "schema": "AURA-AIRLLM-ATTESTED-ISOLATION-CAMPAIGN-v1",
        "omega8": omega8_summary(),
        "context13": context13_summary(),
        "hs1000": hs1000_summary(),
        "composite100k": composite_100k_summary(),
        "oracle100k": randomized_oracle(),
        "process_isolation_cone": process_cone,
        "process_isolation_cone_size": len(process_cone),
        "graph_size": len(GRAPH),
    }
    payload["campaign_root"] = digest(payload)
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
