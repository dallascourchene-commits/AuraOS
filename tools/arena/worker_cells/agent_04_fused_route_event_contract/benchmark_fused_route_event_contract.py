from __future__ import annotations

from dataclasses import replace
import json
import random
import time

from fused_route_event_contract import *


def hs1000(trace: AtomicTrace):
    base = list(flatten_atomic_trace(trace))
    classes = {k: 0 for k in ("missing","boundary","member","group","token","expert_duplicate","expert_range","order")}
    keys = list(classes)
    rejected = 0
    for i in range(1000):
        x = base.copy()
        kind = keys[i % len(keys)]
        try:
            if kind == "missing":
                x.pop()
            elif kind == "boundary":
                x[2] = replace(x[2], event_sequence=1)
            elif kind == "member":
                x[0], x[1] = x[1], x[0]
            elif kind == "group":
                x[0] = replace(x[0], group_size=trace.top_k + 1)
            elif kind == "token":
                x[0] = replace(x[0], token=trace.tokens + 1)
            elif kind == "expert_duplicate":
                x[1] = replace(x[1], expert=x[0].expert)
            elif kind == "expert_range":
                x[0] = replace(x[0], expert=trace.experts_per_layer + 1)
            elif kind == "order":
                x[0], x[trace.top_k] = x[trace.top_k], x[0]
            verify_atomic_roundtrip(trace, x)
        except FusedRouteError:
            rejected += 1
            classes[kind] += 1
    return rejected, classes


def campaign_13d(samples=100000):
    rng = random.Random(13)
    repairs = 0
    for _ in range(samples):
        omega = [rng.randrange(3) for _ in range(8)]
        trailing = [rng.randrange(3) for _ in range(5)]
        admit = crystalline_admission(omega)
        if admit and (0 in omega or omega[7] != 1):
            repairs += 1
        _ = trailing
    return repairs


def main():
    trace = generate_trace(tokens=256, layers=32, experts_per_layer=64, top_k=2, seed=20260905)
    t0 = time.perf_counter()
    flat = flatten_atomic_trace(trace)
    receipt = verify_atomic_roundtrip(trace, flat)
    elapsed = time.perf_counter() - t0
    rejected, classes = hs1000(generate_trace(tokens=8, layers=8, experts_per_layer=32, top_k=2, seed=4))
    repairs = campaign_13d()
    result = {
        "fused_events": len(trace.events),
        "flat_accesses": len(flat),
        "roundtrip_seconds": elapsed,
        "fused_events_per_second": len(trace.events) / elapsed,
        "flat_accesses_per_second": len(flat) / elapsed,
        "event_root": trace.root,
        "flat_root": receipt.flat_access_root,
        "receipt_root": receipt.root,
        "lossy_expert_only_admissible": lossy_stream_is_admissible(naive_expert_only_flatten(trace)),
        "hs1000_rejected": rejected,
        "hs1000_false_admissions": 1000 - rejected,
        "hs1000_classes": classes,
        "sampled_13d_states": 100000,
        "hard_invalid_repairs": repairs,
        "effect_authority": receipt.effect_authority,
        "gate10": receipt.gate10,
    }
    print(json.dumps(result, sort_keys=True))
    if rejected != 1000 or repairs != 0 or result["lossy_expert_only_admissible"] or receipt.effect_authority or receipt.gate10:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
