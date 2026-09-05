from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
import random

from efficiency_proof_reuse_gate import Decision, admission_13d, crystalline_admission, decide, make_receipt, valid_evidence


def semantic_campaign(seed=827, hs=1000, destructive=50000, tails=100000):
    rng = random.Random(seed)
    base = valid_evidence()
    mutations = [
        lambda e: replace(e, authority_requested=True),
        lambda e: replace(e, proof=replace(e.proof, receipt_valid=False)),
        lambda e: replace(e, proof=replace(e.proof, expected_receipt_root="drift-proof")),
        lambda e: replace(e, cost=replace(e.cost, receipt_valid=False)),
        lambda e: replace(e, cost=replace(e.cost, policy_ranking_eligible=False)),
        lambda e: replace(e, cost=replace(e.cost, exact_cumulative_cost_verified=False)),
        lambda e: replace(e, cost=replace(e.cost, source_current=False)),
        lambda e: replace(e, cost=replace(e.cost, expected_source_head="drift-source")),
        lambda e: replace(e, cost=replace(e.cost, expected_workload_root="drift-workload")),
        lambda e: replace(e, cost=replace(e.cost, expected_transfer_root="drift-transfer")),
        lambda e: replace(e, cost=replace(e.cost, expected_envelope_id="drift-envelope")),
        lambda e: replace(e, cost=replace(e.cost, expected_result_root="drift-result")),
        lambda e: replace(e, cost=replace(e.cost, expected_benchmark_generation="bench-g2")),
        lambda e: replace(e, cost=replace(e.cost, expected_receipt_root="drift-cost")),
    ]
    false_admits = 0
    for i in range(hs):
        e = mutations[i % len(mutations)](base)
        false_admits += int(decide(e) != Decision.REPROVE)

    destructive_false_admits = 0
    for _ in range(destructive):
        e = mutations[rng.randrange(len(mutations))](base)
        destructive_false_admits += int(decide(e) != Decision.REPROVE)

    omega_keepers = sum(crystalline_admission(x) for x in product(range(3), repeat=8))
    failed = (0,2,2,2,2,2,2,1)
    repaired = 0
    for _ in range(tails):
        tail = tuple(rng.randrange(3) for _ in range(5))
        repaired += int(admission_13d(failed, tail))

    exact = make_receipt(base)
    neutral = make_receipt(valid_evidence(Decision.ELIGIBLE_BY_PROOF_NEUTRAL_REBIND))
    semantic = {
        "schema": "AURA-WQ-EFFICIENCY-PROOF-REUSE-CAMPAIGN-v1",
        "hs_cases": hs,
        "hs_false_admits": false_admits,
        "destructive_handoffs": destructive,
        "destructive_false_admits": destructive_false_admits,
        "omega8_states": 3**8,
        "omega8_keepers": omega_keepers,
        "tails_13d": tails,
        "tails_13d_repairs": repaired,
        "exact_receipt_root": exact.receipt_root,
        "neutral_rebind_receipt_root": neutral.receipt_root,
    }
    root = sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return semantic, root


if __name__ == "__main__":
    s, r = semantic_campaign()
    print(json.dumps({"semantic": s, "campaign_root": r}, sort_keys=True))
