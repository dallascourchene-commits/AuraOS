from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from airllm_generation_bound_json_service import bind_generation, launch_generation_bound_json_service

GEN = "a" * 40
SURF = "1" * 64
WRAPPER = ["test_airllm_generation_bound_json_service", "FakeWrapper"]


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def run():
    base = bind_generation(GEN, SURF, "m", WRAPPER)
    roots = set()
    collision = 0
    for i in range(1000):
        if i % 2:
            generation = f"{i:040x}"[-40:]
            surface = SURF
        else:
            generation = GEN
            surface = sha256(f"surface-{i}".encode()).hexdigest()
        root = bind_generation(generation, surface, "m", WRAPPER).currentness_root
        collision += int(root == base.currentness_root)
        roots.add(root)

    false_calls = 0
    with launch_generation_bound_json_service(
        model_id="m",
        model_path="/tmp/model",
        model_allowlist={"m": ["3" * 64]},
        loader_source_allowlist=["4" * 64],
        loader_package_source_allowlist=["5" * 64],
        subject_generation=GEN,
        semantic_admission_surface_root=SURF,
        wrapper_symbol=WRAPPER,
        timeout_seconds=5.0,
    ) as proxy:
        for i in range(1000):
            result = proxy.call("generate_json", {"args": [], "kwargs": {"mode": "json", "value": i}})
            false_calls += int(result.get("value") != i or result.get("pid") != proxy.child_pid)

    keeper = 0
    for state in range(3 ** 8):
        n = state
        digits = []
        for _ in range(8):
            digits.append(n % 3)
            n //= 3
        keeper += int(all(v == 2 for v in digits))
    repairs = sum(1 for _ in range(3 ** 5) if False)
    semantic = {
        "schema": "AURA-AIRLLM-GENERATION-BOUND-JSON-CAMPAIGN-v1",
        "base_currentness_root": base.currentness_root,
        "mutation_roots": sorted(roots),
        "currentness_collisions": collision,
        "false_calls": false_calls,
        "omega8_keeper": keeper,
        "13d_repairs": repairs,
    }
    print(json.dumps({
        "campaign_root": sha256(canonical(semantic)).hexdigest(),
        "base_currentness_root": base.currentness_root,
        "currentness_mutations": 1000,
        "currentness_collisions": collision,
        "unique_mutation_roots": len(roots),
        "json_calls": 1000,
        "false_calls": false_calls,
        "omega8_states": 3 ** 8,
        "omega8_keeper": keeper,
        "13d_tails": 3 ** 5,
        "13d_repairs": repairs,
    }, sort_keys=True))


if __name__ == "__main__":
    run()
