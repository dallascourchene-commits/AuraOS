from __future__ import annotations
import json, sys
p=sys.argv[1] if len(sys.argv)>1 else 'benchmark_result.json'
r=json.load(open(p,encoding='utf-8'))
g=r['gains']
thresholds={
    'offload_transfer_bytes_reduction':0.85,
    'offload_estimated_transfer_time_reduction':0.85,
    'offload_estimated_energy_reduction':0.85,
    'retrieval_candidate_reduction':0.99,
    'selective_reproof_reduction':0.95,
    'snapshot_retention_reduction':0.95,
    'security_false_admission_reduction':1.0,
}
fail=[]
for k,v in thresholds.items():
    got=g[k]
    if got+1e-12 < v: fail.append((k,got,v))
if fail:
    for k,got,want in fail: print(f'FAIL {k}: {got:.6f} < {want:.6f}')
    raise SystemExit(1)
print('Frontier-27 deterministic thresholds PASS')
for k,v in thresholds.items(): print(f'{k}={g[k]:.6f} threshold={v:.6f}')
