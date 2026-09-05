from dataclasses import replace
import hashlib
import json
import random
import time

from fused_route_cost_receipt import *

HEAD = "7a2c7a16f845752ffb7c16c68636d8d542ecd72e"
BYTES = 2 * 1024 * 1024
BANDWIDTH = 1_200_000_000.0
ENERGY_PER_GB = 2.4
EVENT_N = 8192
EXPERTS = 64
BUDGET = 2.0

def charge_metrics(bytes_moved: int):
    return bytes_moved / BANDWIDTH, (bytes_moved / 1_000_000_000.0) * ENERGY_PER_GB

def build():
    rng = random.Random(20260905)
    events = []
    for seq in range(1, EVENT_N + 1):
        a = (seq * 7 + rng.randrange(5)) % EXPERTS
        b = (seq * 13 + rng.randrange(7)) % EXPERTS
        if b == a: b = (b + 1) % EXPERTS
        events.append(RouteEvent(seq, (seq - 1) // 32, (seq - 1) % 32, (a, b)))
    transfers = []
    resident = set(); spec_spent = 0.0; seqno = 1
    for idx, event in enumerate(events):
        for expert in event.experts:
            if expert not in resident:
                t, e = charge_metrics(BYTES)
                transfers.append(TransferCharge(f"d-{seqno}", seqno, "DEMAND", event.sequence, event.sequence, expert, BYTES, t, e))
                seqno += 1; resident.add(expert)
                if len(resident) > 16: resident.remove(min(resident))
        if idx + 1 < len(events) and idx % 128 == 0:
            target = events[idx + 1]; expert = target.experts[0]
            if expert not in resident:
                t, e = charge_metrics(BYTES)
                if spec_spent + e <= BUDGET + 1e-12:
                    transfers.append(TransferCharge(f"p-{seqno}", seqno, "SPECULATIVE", event.sequence, target.sequence, expert, BYTES, t, e))
                    seqno += 1; spec_spent += e; resident.add(expert)
                    if len(resident) > 16: resident.remove(min(resident))
    env = CostEnvelope(HEAD, "synthetic-runtime-v1", "synthetic-hw-v1", "fused-cost-bench-v1", "ssd1.2GBps-energy2.4JperGB", BUDGET)
    return tuple(events), tuple(transfers), env

def mutation_campaign(events, transfers, env, receipt):
    rng = random.Random(55); false_admits = 0; cases = 1000
    for i in range(cases):
        mode = i % 8; es, ts, ev, rr = events, transfers, env, receipt
        try:
            if mode == 0: ts = (replace(ts[0], transfer_id=ts[1].transfer_id),) + ts[1:]
            elif mode == 1: ts = (replace(ts[0], modeled_energy_j=True),) + ts[1:]
            elif mode == 2: rr = replace(rr, result_root="f" * 64)
            elif mode == 3: ev = replace(ev, source_head="1" * 40)
            elif mode == 4: rr = replace(rr, schema="FORGED")
            elif mode == 5: ts = (replace(ts[0], expert_id=999),) + ts[1:]
            elif mode == 6: rr = replace(rr, total_bytes=rr.total_bytes + rng.randrange(1, 100))
            else:
                j = next((j for j in range(len(ts)-1, -1, -1) if ts[j].kind == "SPECULATIVE"), None)
                if j is not None:
                    arr = list(ts); arr[j] = replace(arr[j], modeled_energy_j=env.speculative_energy_budget_j + 0.5); ts = tuple(arr)
            if verify_receipt(es, ts, ev, rr): false_admits += 1
        except CostReceiptError:
            pass
    return cases, false_admits

def main():
    events, transfers, env = build()
    start = time.perf_counter(); receipt = compile_receipt(events, transfers, env); compile_s = time.perf_counter() - start
    start = time.perf_counter(); ok = verify_receipt(events, transfers, env, receipt); verify_s = time.perf_counter() - start
    attack_events = events[:256]
    attack_transfers = tuple(t for t in transfers if t.target_event_sequence <= 256)
    attack_receipt = compile_receipt(attack_events, attack_transfers, env)
    cases, false_admits = mutation_campaign(attack_events, attack_transfers, env, attack_receipt)
    rng = random.Random(1305); repairs = 0
    for _ in range(100_000):
        o = [rng.randrange(3) for _ in range(8)]; r = [rng.randrange(3) for _ in range(5)]
        if 0 in o and admission_13d(o, r): repairs += 1
    out = {
        "schema": SCHEMA, "events": len(events), "transfers": len(transfers),
        "demand_transfers": receipt.demand_transfer_count, "speculative_transfers": receipt.speculative_transfer_count,
        "total_bytes": receipt.total_bytes, "total_modeled_time_s": receipt.total_modeled_time_s,
        "total_modeled_energy_j": receipt.total_modeled_energy_j, "speculative_energy_j": receipt.speculative_modeled_energy_j,
        "speculative_budget_j": receipt.speculative_energy_budget_j, "speculative_remaining_j": receipt.speculative_energy_remaining_j,
        "compile_s": compile_s, "verify_s": verify_s, "events_per_s_compile": len(events) / compile_s,
        "events_per_s_verify": len(events) / verify_s, "verify_ok": ok, "mutation_cases": cases,
        "false_admissions": false_admits, "sampled_13d": 100000, "hard_invalid_repairs": repairs,
        "event_root": receipt.event_root, "transfer_root": receipt.transfer_root, "result_root": receipt.result_root,
        "effect_authority": receipt.effect_authority, "gate10": receipt.gate10,
    }
    stable = {k:v for k,v in out.items() if k not in {"compile_s","verify_s","events_per_s_compile","events_per_s_verify"}}
    out["stable_campaign_root"] = hashlib.sha256(json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    print(json.dumps(out, sort_keys=True))
    if not ok or false_admits or repairs: raise SystemExit(1)

if __name__ == "__main__": main()
