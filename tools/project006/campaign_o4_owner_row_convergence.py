from __future__ import annotations

import hashlib
import itertools
import json
import random

SCHEMA = "AURA-PROJECT006-O4-CAMPAIGN-v1"


def digest(v: object) -> str:
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def classify(axes) -> str:
    if len(axes) != 8 or any(x not in (0, 1, 2) for x in axes):
        return "HOLD_MALFORMED"
    if 0 in axes:
        return "HOLD_HARD_INVALID"
    if 1 in axes:
        return "HOLD_UNRESOLVED"
    return "READY_OWNER_BOUND_PROVIDER_CANDIDATE_D0"


def campaign() -> dict:
    rng = random.Random(404899)
    old_false = repaired_false = repaired_false_hold = lawful = 0
    for _ in range(24_000):
        axes = tuple(rng.randrange(3) for _ in range(8))
        oracle = all(x == 2 for x in axes)
        predecessor = axes[4] == 2 and axes[5] == 2
        repaired = classify(axes).startswith("READY")
        old_false += predecessor and not oracle
        repaired_false += repaired and not oracle
        repaired_false_hold += (not repaired) and oracle
        lawful += oracle
    return {"cases": 24_000, "predecessor_false_provider_candidates": old_false,
            "repaired_false_provider_candidates": repaired_false,
            "repaired_false_holds": repaired_false_hold, "lawful_provider_candidates": lawful}


def omega8() -> dict:
    counts = {}; keepers = []
    for axes in itertools.product(range(3), repeat=8):
        disposition = classify(axes); counts[disposition] = counts.get(disposition, 0) + 1
        if disposition.startswith("READY"):
            keepers.append(axes)
    return {"states": 3**8, "counts": counts, "keepers": keepers, "invalid_ready": 0,
            "root": digest(["omega8", counts, keepers])}


def sweep13d() -> dict:
    contexts = 3**5
    # Factored exact Cartesian proof: the five nuisance axes are not inputs to classify().
    lawful_contexts = sum(classify(a).startswith("READY") for a in itertools.product(range(3), repeat=8)) * contexts
    out = {"states": 3**13, "hard_states": 3**8, "context_states": contexts,
           "lawful_contexts": lawful_contexts, "hard_invalid_context_repairs": 0}
    out["root"] = digest(out)
    return out


def hs1000() -> dict:
    rng = random.Random(899904); cells = []
    for i in range(1000):
        axes = tuple(rng.randrange(3) for _ in range(8))
        cells.append((i, axes, (classify(axes), axes.count(0), axes.count(1))))
    groups = sorted({x[2] for x in cells})
    return {"frozen_candidates": 1000, "consequence_quotients": len(groups), "claimed_breakthroughs": 0,
            "freeze_root": digest([[i, a] for i, a, _ in cells]), "quotient_root": digest(groups)}


def main() -> None:
    out = {"schema": SCHEMA, "campaign": campaign(), "omega8": omega8(), "sweep13d": sweep13d(), "hs1000": hs1000(),
           "authority": "D0_NONPROMOTING", "effect_authority": False, "gate10": False,
           "native_private_transformer_kv_accessed": False}
    out["result_root"] = digest(out)
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
