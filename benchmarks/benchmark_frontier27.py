import json
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools", "arena"))
from frontier27_runtime import *

SEED = 2701000


def routes(steps=3000, experts=96, k=4):
    r = random.Random(SEED); out = []; pred = []; hot = list(range(16))
    for _ in range(steps):
        x = r.sample(hot, k) if r.random() < 0.82 else r.sample(range(experts), k)
        out.append(x); pred.append([e if r.random() < 0.70 else r.randrange(experts) for e in x])
    return out, pred


def retrieval(n=10000, q=500):
    records = {f"R{i:05d}": f"family_{i%100} mechanism_{i%27} currentness cache expert route evidence record_{i}" for i in range(n)}
    record_terms = {identity: set(tokens(text)) for identity, text in records.items()}
    rng = random.Random(SEED + 1); qs = [f"family_{rng.randrange(100)} mechanism_{rng.randrange(27)}" for _ in range(q)]

    t = time.perf_counter(); before_exam = 0; expected_by_query = []
    for term in qs:
        wanted_terms = set(tokens(term)); expected = {identity for identity, ts in record_terms.items() if wanted_terms <= ts}
        expected_by_query.append(expected); before_exam += len(records)
    before_s = time.perf_counter() - t

    t = time.perf_counter(); idx = HybridIndexBridge(10); cache = HotColdCache(records)
    for identity, text in records.items():
        h = sha256(identity.encode()).digest(); idx.add(identity, text, (h[0] % 27, h[1] % 27, h[2] % 27))
    build = time.perf_counter() - t

    t = time.perf_counter(); after_exam = 0; expected_total = covered_total = 0
    for term, expected in zip(qs, expected_by_query):
        c = idx.candidates(term, 24); after_exam += len(c); ids = [x[0] for x in c]; got = set(ids)
        expected_total += len(expected); covered_total += len(expected & got)
        for identity in ids: cache.get(identity)
        receipt = RetrievalReceipt.build(term, ids, "g1")
        if not receipt.valid_for(term, ids, "g1"): raise AssertionError("retrieval receipt failed self/context verification")
    after_s = time.perf_counter() - t
    recall = 1.0 if expected_total == 0 else covered_total / expected_total
    return {
        "before": {"wall_s": before_s, "examined": before_exam},
        "after": {"query_wall_s": after_s, "index_build_s": build, "amortized_wall_s": after_s + build, "examined": after_exam, "hot_hits": cache.hits, "hot_misses": cache.misses},
        "quality": {"expected_relevant": expected_total, "covered_relevant": covered_total, "false_negatives": expected_total - covered_total, "recall": recall},
    }


def main():
    rs, ps = routes(); size = 8 * 1024 * 1024; tier = StorageTier("ssd", 10_000 * size, 1.2e9, 2.4)
    b = LegacyOffload(size, 1.2e9, 2.4).run(rs, ps); a = FrontierOffload(size, 24, tier, 0.0025, 0.1).run(rs, ps)
    inv = CurrentnessInvalidator(); nodes = 20000
    for i in range(nodes): inv.bind(f"N{i}", [f"D{i%200}", f"D{(i*7)%200}"])
    affected = inv.invalidate(["D17"]); ring = SnapshotRing(128)
    for i in range(10000): ring.append(i, {"i": i})
    ret = retrieval(); audit = security_campaign(1000); red = lambda x, y: (x - y) / x
    out = {"seed": SEED, "manifest": FRONTIER_27, "offload": {"before": b, "after": a, "after_time_model": "serialized_all_transfers"}, "retrieval": ret, "currentness": {"before": nodes, "after": len(affected)}, "snapshots": {"before": 10000, "after": len(ring)}, "audit": audit}
    out["gains"] = {
        "offload_transfer_bytes_reduction": red(b["bytes"], a["bytes"]),
        "offload_estimated_transfer_time_reduction": red(b["seconds"], a["seconds"]),
        "offload_estimated_energy_reduction": red(b["energy_j"], a["energy_j"]),
        "retrieval_candidate_reduction": red(ret["before"]["examined"], ret["after"]["examined"]),
        "retrieval_query_wall_time_reduction": red(ret["before"]["wall_s"], ret["after"]["query_wall_s"]),
        "retrieval_amortized_wall_time_reduction": red(ret["before"]["wall_s"], ret["after"]["amortized_wall_s"]),
        "selective_reproof_reduction": red(nodes, len(affected)),
        "snapshot_retention_reduction": red(10000, len(ring)),
        "security_false_admission_reduction": audit["false_admission_reduction"],
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__": main()
