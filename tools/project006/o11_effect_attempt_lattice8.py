import hashlib
import itertools
import json

from tools.project006.effect_attempt_recovery import hard_o11_state

rows = []
keeper = hard_invalid = unresolved = 0
for axes in itertools.product(range(3), repeat=8):
    decision = hard_o11_state(axes)
    rows.append((axes, decision))
    if decision == "READY_RECOVERY_ACTION_D0":
        keeper += 1
    elif decision == "HOLD_HARD_INVALID":
        hard_invalid += 1
    else:
        unresolved += 1
root = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
print(json.dumps({
    "schema": "AURA-PROJECT006-O11-OMEGA8-v1",
    "states": len(rows),
    "keeper": keeper,
    "hard_invalid": hard_invalid,
    "unresolved": unresolved,
    "root": root,
}, sort_keys=True, separators=(",", ":")))
