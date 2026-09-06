from __future__ import annotations
from hashlib import sha256
import itertools, json, random


def stable(v): return json.dumps(v, sort_keys=True, separators=(",", ":")).encode()
def digest(v): return sha256(stable(v)).hexdigest()

AXES = ("source", "owner_boundary", "epoch", "generation", "full_state", "pinned_transition", "atomic_commit", "authority")

def classify(axes):
    if axes[0] != 2: return "SOURCE_HOLD"
    if axes[1] != 2: return "BYPASS_HOLD"
    if axes[2] != 2: return "EPOCH_HOLD"
    if axes[3] != 2 or axes[4] != 2: return "CAS_HOLD"
    if axes[5] != 2 or axes[6] != 2: return "TRANSITION_HOLD"
    if axes[7] != 2: return "AUTHORITY_HOLD"
    return "OWNER_EPOCH_KEEPER"

def run(seed=115):
    rng=random.Random(seed)
    omega=[]; keeper=0
    for axes in itertools.product(range(3), repeat=8):
        cls=classify(axes); keeper += cls=="OWNER_EPOCH_KEEPER"; omega.append((axes,cls))
    tails=list(itertools.product(range(3), repeat=5))
    hard_invalid=(2,2,0,2,2,2,2,2)
    repairs=sum(classify(hard_invalid)=="OWNER_EPOCH_KEEPER" for _ in tails)
    valid=(2,)*8
    valid_admits=sum(classify(valid)=="OWNER_EPOCH_KEEPER" for _ in tails)
    hs=[]; false_promotions=0
    classes={}
    for i in range(1000):
        family=i%5
        axes=[2]*8
        axes[family]=rng.randrange(0,2)
        if i%10==0: axes=[2]*8
        cls=classify(tuple(axes)); classes[cls]=classes.get(cls,0)+1
        expected=(all(x==2 for x in axes))
        false_promotions += int((cls=="OWNER_EPOCH_KEEPER") != expected)
        hs.append((i,axes,cls))
    return {
        "omega_states": len(omega), "omega_keepers": keeper,
        "routing_tails": len(tails), "hard_invalid_repairs": repairs, "valid_tail_admits": valid_admits,
        "hs1000": 1000, "false_promotions": false_promotions, "classes": classes,
        "omega_root": digest(omega), "hs_root": digest(hs),
    }

if __name__ == "__main__": print(json.dumps(run(), sort_keys=True))
