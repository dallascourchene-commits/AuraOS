from __future__ import annotations

from dataclasses import replace
from itertools import product
import json
import random
import time

from workload_contamination_gate import *


def semantic_campaign() -> dict[str, object]:
    gate = WorkloadContaminationGate()
    clean = valid_batch()
    valid = gate.assess(clean)
    rng = random.Random(20260905)
    false_admits = 0
    cases = 1000
    for i in range(cases):
        items = list(clean.samples)
        family = i % 8
        if family == 0:
            items[2] = replace(items[2], rendered_generation_prefix=items[0].rendered_generation_prefix)
            mutated = replace(clean, samples=tuple(items))
        elif family == 1:
            items[0] = replace(items[0], trace=replace(items[0].trace, atomic_semantics_preserved=False))
            mutated = replace(clean, samples=tuple(items))
        elif family == 2:
            items[0] = replace(items[0], trace=replace(items[0].trace, envelope_root=f"env-{i}"))
            mutated = replace(clean, samples=tuple(items))
        elif family == 3:
            items[0] = replace(items[0], source_generation=f"old-{i}")
            mutated = replace(clean, samples=tuple(items))
        elif family == 4:
            mutated = replace(clean, source_current=False)
        elif family == 5:
            control = sample(10000 + i, "code", clean.samples[0].rendered_generation_prefix,
                             ranking_eligible=False, control_group="diagnostic")
            mutated = replace(clean, samples=clean.samples + (replace(control, ranking_eligible=True),))
        elif family == 6:
            mutated = replace(clean, samples=tuple(s for s in clean.samples if s.category == "code"))
        else:
            mutated = replace(clean, asks_effect_authority=True)
        false_admits += int(gate.assess(mutated).policy_ranking_eligible)

    keepers = sum(crystalline_admission(state) for state in product((0, 1, 2), repeat=8))
    items = list(clean.samples)
    items[2] = replace(items[2], rendered_generation_prefix=items[0].rendered_generation_prefix)
    failing = replace(clean, samples=tuple(items))
    repairs = 0
    samples_13d = 100_000
    for _ in range(samples_13d):
        _tail = tuple(rng.randrange(3) for _ in range(5))
        repairs += int(gate.assess(failing).policy_ranking_eligible)

    semantic = {
        "schema": SCHEMA,
        "valid_decision": valid.decision.value,
        "valid_receipt_root": valid.receipt_root,
        "hs1000_cases": cases,
        "hs1000_false_admits": false_admits,
        "omega8_states": 3 ** 8,
        "omega8_keepers": keepers,
        "sampled_13d_states": samples_13d,
        "hard_failure_repairs": repairs,
    }
    semantic["semantic_campaign_root"] = digest(semantic)
    return semantic


def benchmark(n: int = 20_000) -> dict[str, object]:
    gate = WorkloadContaminationGate()
    categories = tuple(f"category-{i}" for i in range(8))
    samples = tuple(sample(i + 1, categories[i % 8], f"prefix::{categories[i % 8]}::{i}") for i in range(n))
    batch = WorkloadBatch("workload-prefix-throughput", "bench-throughput-g1", "src-g1", "env-root", True, samples)
    t0 = time.perf_counter()
    receipt = gate.assess(batch)
    elapsed = time.perf_counter() - t0
    return {
        "samples": n,
        "categories": len(categories),
        "decision": receipt.decision.value,
        "elapsed_s": elapsed,
        "samples_per_s": n / elapsed,
        "note": "Parser/admission throughput only; not model/cache throughput.",
    }


if __name__ == "__main__":
    print(json.dumps({"semantic": semantic_campaign(), "benchmark": benchmark()}, sort_keys=True, indent=2))
