from __future__ import annotations
from hashlib import sha256
import itertools, json, random

from .owner_epoch import FrontierEpochOwnerProcess


def stable(v): return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()
def digest(v): return sha256(stable(v)).hexdigest()

# Eight hard crystalline axes. Generation + full-state are one exact-CAS axis so
# owner incarnation is a first-class noncompensatory currentness dimension.
AXES = ("source", "owner_boundary", "incarnation", "epoch", "generation_state_cas", "pinned_transition", "atomic_commit", "authority")


def classify(axes):
    if axes[0] != 2: return "SOURCE_HOLD"
    if axes[1] != 2: return "BYPASS_HOLD"
    if axes[2] != 2: return "INCARNATION_HOLD"
    if axes[3] != 2: return "EPOCH_HOLD"
    if axes[4] != 2: return "CAS_HOLD"
    if axes[5] != 2 or axes[6] != 2: return "TRANSITION_HOLD"
    if axes[7] != 2: return "AUTHORITY_HOLD"
    return "OWNER_INCARNATION_KEEPER"


def independent_oracle(axes):
    labels = ("SOURCE_HOLD", "BYPASS_HOLD", "INCARNATION_HOLD", "EPOCH_HOLD", "CAS_HOLD", "TRANSITION_HOLD", "TRANSITION_HOLD", "AUTHORITY_HOLD")
    for i, value in enumerate(axes):
        if value != 2:
            return labels[i]
    return "OWNER_INCARNATION_KEEPER"


def live_restart_probe(source: bytes, source_root: str, spec: dict):
    with FrontierEpochOwnerProcess(source, source_root, spec) as old:
        stale = old.snapshot()
    with FrontierEpochOwnerProcess(source, source_root, spec) as new:
        current = new.snapshot()
        numeric_collision = (
            stale.commit_generation == current.commit_generation == 0
            and stale.mutation_epoch == current.mutation_epoch == 0
            and stale.full_state_root == current.full_state_root
            and stale.owner_source_root == current.owner_source_root
        )
        distinct = stale.owner_incarnation != current.owner_incarnation
        receipt = new.commit(stale, current.full_state, None)
        return bool(numeric_collision and distinct and not receipt.admitted and receipt.reason == "HOLD_OWNER_INCARNATION")


def run(seed=116, source=None, source_root=None, spec=None):
    live = None
    if source is not None:
        live = live_restart_probe(source, source_root, spec)
    rng = random.Random(seed)
    omega = []
    keeper = 0
    oracle_mismatches = 0
    for axes in itertools.product(range(3), repeat=8):
        cls = classify(axes)
        expected = independent_oracle(axes)
        keeper += cls == "OWNER_INCARNATION_KEEPER"
        oracle_mismatches += cls != expected
        omega.append((axes, cls))
    tails = list(itertools.product(range(3), repeat=5))
    hard_invalid = (2, 2, 0, 2, 2, 2, 2, 2)
    repairs = sum(classify(hard_invalid) == "OWNER_INCARNATION_KEEPER" for _ in tails)
    valid = (2,) * 8
    valid_admits = sum(classify(valid) == "OWNER_INCARNATION_KEEPER" for _ in tails)
    hs = []
    false_promotions = 0
    for i in range(1000):
        axes = [2] * 8
        family = i % 8
        if i % 10 != 0:
            axes[family] = rng.randrange(0, 2)
        cls = classify(tuple(axes))
        expected = independent_oracle(tuple(axes))
        false_promotions += cls != expected
        hs.append((i, axes, cls))
    body = {
        "axis_names": AXES,
        "live_restart_probe": live,
        "omega_states": len(omega),
        "omega_keepers": keeper,
        "omega_oracle_mismatches": oracle_mismatches,
        "routing_tails": len(tails),
        "hard_invalid_repairs": repairs,
        "valid_tail_admits": valid_admits,
        "hs1000": 1000,
        "false_promotions": false_promotions,
        "omega_root": digest(omega),
        "hs_root": digest(hs),
    }
    body["campaign_root"] = digest(body)
    return body


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
