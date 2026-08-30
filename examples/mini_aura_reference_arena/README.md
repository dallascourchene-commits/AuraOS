# Mini Aura Reference Arena (staged)

This is a **bounded independent reimplementation/falsification example** derived from the Paper X architecture. It is small enough for an unfamiliar code-capable agent to execute without a live Aura Drive.

It is **not** the canonical AuraOS runtime and does not prove comparative superiority.

```bash
python -m venv .aura-mini
# activate .aura-mini for your shell
python mini_aura_reference.py --out results_local.json
```

The Python entrypoint invokes the independent Node exact-count lane automatically. Expected bounded invariants include:

- depth-10 3-ary world: `88,573` nodes; one-leaf affected cone: `11`;
- incremental state equals full rebuild; unrelated state stays unchanged;
- AMNF `81/81`, zero mismatch;
- HyperScale `40,320` permutations → `108` running-GCD trajectories; `219/255` nonempty subsets reach gcd 1; minimax center `s=4`;
- Python ↔ Node exact-count parity;
- valid-bound Progressive Action Cone: zero true-winner exclusions in 1,000×1,000 bounded trials;
- Decision Capsule: zero winner changes in 25,000 in-radius perturbations.

Timing and pruning magnitude are workload-specific. A separate earlier recorded workload reported `5.36/1000` Action-Cone candidates explored on average; this independently written workload uses about `136/1000`. The safety invariant transferred while the efficiency magnitude did not.

```text
REFERENCE REIMPLEMENTATION != CANONICAL AURAOS
RECONSTRUCTION PASS != COMPARATIVE SUPERIORITY
RECEIPT != TRUTH
NO CODE RUNTIME -> UNEXECUTED_NO_RUNTIME
```

The stronger target remains matched B0-B3/A1-A3 controls plus a blind fresh Agent-A → terminate → fresh Agent-B continuation from a compact SuccessorFrame.
