from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import itertools
import json
import random
import sys

sys.path.insert(0, "src")
from contamination_bound_cost_adjudicator import *


def rebuilt(parent: ParentAttestation, **changes) -> ParentAttestation:
    values = parent.canonical_without_root()
    values.update(changes)
    return make_attestation(**values)


def independent_oracle(c: ParentAttestation, k: ParentAttestation) -> Decision:
    if c.role != "WORKLOAD_CONTAMINATION" or k.role != "FUSED_ROUTE_COST" or c.schema != CONTAMINATION_SCHEMA or k.schema != COST_SCHEMA:
        return Decision.HOLD_PARENT_SCHEMA
    if c.semantic_commit != CONTAMINATION_PARENT_COMMIT or k.semantic_commit != COST_PARENT_COMMIT:
        return Decision.HOLD_PARENT_GENERATION
    if c.semantic_commit == k.semantic_commit:
        return Decision.HOLD_PARENT_LINEAGE_COLLISION
    if not c.internally_valid() or not k.internally_valid():
        return Decision.HOLD_PARENT_ATTESTATION
    if not c.verified or not k.verified:
        return Decision.HOLD_PARENT_UNVERIFIED
    if not c.current or not k.current:
        return Decision.HOLD_PARENT_STALE
    if not c.ready_non_authorizing or not k.ready_non_authorizing:
        return Decision.HOLD_PARENT_NOT_READY
    if c.truth_authority or c.effect_authority or c.gate10 or k.truth_authority or k.effect_authority or k.gate10:
        return Decision.HOLD_AUTHORITY_CEILING
    if c.source_identity != k.source_identity:
        return Decision.HOLD_SOURCE_IDENTITY_MISMATCH
    if c.benchmark_generation != k.benchmark_generation:
        return Decision.HOLD_BENCHMARK_GENERATION_MISMATCH
    if c.envelope_identity != k.envelope_identity:
        return Decision.HOLD_ENVELOPE_BINDING_MISMATCH
    return Decision.READY_NONAUTHORIZING


def randomized_oracle(n=100_000):
    rng = random.Random(2026090504)
    base_c, base_k = valid_pair()
    a = ContaminationBoundCostAdjudicator()
    mismatches = 0
    counts = {d.value: 0 for d in Decision}
    modes = [
        "valid", "c_unverified", "k_unverified", "c_stale", "k_stale", "c_not_ready", "k_not_ready",
        "source", "benchmark", "envelope", "authority", "schema", "generation", "tamper",
    ]
    for i in range(n):
        mode = modes[rng.randrange(len(modes))]
        c, k = base_c, base_k
        if mode == "c_unverified": c = rebuilt(c, verified=False)
        elif mode == "k_unverified": k = rebuilt(k, verified=False)
        elif mode == "c_stale": c = rebuilt(c, current=False)
        elif mode == "k_stale": k = rebuilt(k, current=False)
        elif mode == "c_not_ready": c = rebuilt(c, ready_non_authorizing=False)
        elif mode == "k_not_ready": k = rebuilt(k, ready_non_authorizing=False)
        elif mode == "source": k = rebuilt(k, source_identity="b" * 40)
        elif mode == "benchmark": k = rebuilt(k, benchmark_generation="bench-g2")
        elif mode == "envelope": k = rebuilt(k, envelope_identity="f" * 64)
        elif mode == "authority": k = rebuilt(k, gate10=True)
        elif mode == "schema": c = rebuilt(c, schema="FORGED")
        elif mode == "generation": c = rebuilt(c, semantic_commit="1" * 40)
        elif mode == "tamper": c = replace(c, attestation_root="0" * 64)
        got = a.adjudicate(c, k).decision
        want = independent_oracle(c, k)
        counts[got.value] += 1
        mismatches += int(got != want)
    root = sha256(json.dumps(counts, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"cases": n, "mismatches": mismatches, "decision_counts": counts, "root": root}


def omega8_campaign():
    admit = hold = hard_invalid_escape = unknown_escape = 0
    for state in itertools.product(range(3), repeat=8):
        ok = crystalline_admission(state)
        admit += int(ok); hold += int(not ok)
        hard_invalid_escape += int(0 in state and ok)
        unknown_escape += int(1 in state[:7] and ok)
    return {"states": 3**8, "admit": admit, "hold": hold, "hard_invalid_escape": hard_invalid_escape, "unknown_escape": unknown_escape}


def context13d_campaign():
    invalid_omega = (2,2,2,2,2,2,1,1)
    repairs = 0
    for routing in itertools.product(range(3), repeat=5):
        repairs += int(admission_13d(invalid_omega, routing))
    return {"contexts": 3**5, "invalid_repairs": repairs}


def hs1000_campaign():
    c, k = valid_pair(); a = ContaminationBoundCostAdjudicator(); false_admits = 0
    families = []
    for i in range(1000):
        mode = i % 10; cc, kk = c, k
        if mode == 0: cc = rebuilt(cc, current=False); family="stale"
        elif mode == 1: kk = rebuilt(kk, verified=False); family="unverified"
        elif mode == 2: cc = rebuilt(cc, ready_non_authorizing=False); family="contamination"
        elif mode == 3: kk = rebuilt(kk, ready_non_authorizing=False); family="cost"
        elif mode == 4: kk = rebuilt(kk, source_identity="b"*40); family="source"
        elif mode == 5: kk = rebuilt(kk, benchmark_generation="other"); family="benchmark"
        elif mode == 6: kk = rebuilt(kk, envelope_identity="f"*64); family="envelope"
        elif mode == 7: kk = rebuilt(kk, effect_authority=True); family="authority"
        elif mode == 8: cc = rebuilt(cc, semantic_commit="1"*40); family="generation"
        else: cc = replace(cc, attestation_root="0"*64); family="attestation"
        false_admits += int(a.adjudicate(cc, kk).decision == Decision.READY_NONAUTHORIZING)
        families.append(family)
    root = sha256(json.dumps(families, separators=(",", ":")).encode()).hexdigest()
    return {"cases": 1000, "false_admits": false_admits, "families": len(set(families)), "root": root}


def main():
    c, k = valid_pair(); receipt = ContaminationBoundCostAdjudicator().adjudicate(c, k)
    out = {
        "schema": SCHEMA,
        "valid_receipt_root": receipt.result_root,
        "randomized_oracle": randomized_oracle(),
        "omega8": omega8_campaign(),
        "context13d": context13d_campaign(),
        "hs1000": hs1000_campaign(),
    }
    stable = json.dumps(out, sort_keys=True, separators=(",", ":"))
    out["campaign_root"] = sha256(stable.encode()).hexdigest()
    print(json.dumps(out, indent=2, sort_keys=True))
    if out["randomized_oracle"]["mismatches"] or out["omega8"]["hard_invalid_escape"] or out["omega8"]["unknown_escape"] or out["context13d"]["invalid_repairs"] or out["hs1000"]["false_admits"]:
        raise SystemExit(1)

if __name__ == "__main__": main()
