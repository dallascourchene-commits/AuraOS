from __future__ import annotations
import json
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "benchmark_result.json"
r = json.load(open(p, encoding="utf-8"))
g = r["gains"]
thresholds = {
    "offload_transfer_bytes_reduction": 0.85,
    "offload_estimated_transfer_time_reduction": 0.85,
    "offload_estimated_energy_reduction": 0.85,
    "retrieval_candidate_reduction": 0.99,
    "selective_reproof_reduction": 0.95,
    "snapshot_retention_reduction": 0.95,
    "security_false_admission_reduction": 1.0,
}
fail = []
for k, v in thresholds.items():
    got = g[k]
    if got + 1e-12 < v: fail.append((k, got, v))
recall = r["retrieval"]["quality"]["recall"]
if recall + 1e-12 < 1.0: fail.append(("retrieval_recall", recall, 1.0))
if r["retrieval"]["quality"]["false_negatives"] != 0: fail.append(("retrieval_false_negatives", r["retrieval"]["quality"]["false_negatives"], 0))
prefetch_transfers = r["offload"]["after"].get("prefetch_transfers", 0)
if prefetch_transfers <= 0: fail.append(("prefetch_transfers", prefetch_transfers, ">0"))
audit = r["audit"]
if audit.get("after_false_admits", 0) != 0: fail.append(("security_after_false_admits", audit.get("after_false_admits"), 0))
if audit.get("valid_rejected", 0) != 0: fail.append(("security_valid_rejected", audit.get("valid_rejected"), 0))
if fail:
    for k, got, want in fail: print(f"FAIL {k}: {got} does not satisfy {want}")
    raise SystemExit(1)
print("Frontier-27 deterministic thresholds PASS")
for k, v in thresholds.items(): print(f"{k}={g[k]:.6f} threshold={v:.6f}")
print(f"retrieval_recall={recall:.6f} threshold=1.000000")
print(f"prefetch_transfers={prefetch_transfers} threshold=>0")
print(f"security_after_false_admits={audit.get('after_false_admits', 0)} threshold=0")
print(f"security_valid_rejected={audit.get('valid_rejected', 0)} threshold=0")
