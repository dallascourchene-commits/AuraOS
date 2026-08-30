# Arena Expert Fabric reference

> **Status:** staged, non-production, no provider calls required for the checks.

This bounded reference composes Aura's semantic/currentness routing with an execution-backend selector. It deliberately keeps four layers separate:

1. canonical semantic/source identity;
2. Sub-Arena / domain / Temporal-NOW scope;
3. K27 physical shard/cache routing;
4. concrete model/backend selection.

```text
K27 != semantic identity != model-internal MoE expert
```

Run:

```bash
cd examples/arena_expert_fabric
python checks.py
python paired_rba_systems_benchmark.py
```

`checks.py` currently contains 18 deterministic Python gates. The original local Arena also carried an independent Node K27 parity witness.

The paired benchmark is a deterministic **routing/hydration ablation**, not an LLM-quality benchmark. It assigns equal synthetic hydration cost to each object-domain projection and compares:

```text
R = regular broad orientation
B = rebase-only hard dependency closure
A = full Aura hard closure + selected domain lenses + bounded WorkCapsule + ExpertBundle
```

The fresh nine-task reference result is:

```text
R: 864 projection-equivalents / 3,538,944 equal-cost bytes
B: 342 projection-equivalents / 1,400,832 equal-cost bytes
A: 114 projection-equivalents /   485,376 equal-cost bytes

A vs R: 86.2847% reduction in this equal-cost hydration model
A vs B: 65.3509%
B vs R: 60.4167%
```

This does **not** establish an 86% reduction in provider tokens, wall time, cost, or error rate. It measures only deterministic routing/hydration structure on the checked 16-object × 6-domain reference graph.

No AirLLM, OpenRouter, DeepSeek, or other provider inference is executed by these scripts.
