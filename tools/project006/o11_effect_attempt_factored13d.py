import hashlib
import itertools
import json

from tools.project006.effect_attempt_recovery import hard_o11_state

hard_states = list(itertools.product(range(3), repeat=8))
context_count = 3 ** 5
rows = []
lawful_contexts = 0
nonroutes = 0
hard_invalid_context_repairs = 0
for axes in hard_states:
    decision = hard_o11_state(axes)
    rows.append((axes, decision))
    if decision == "READY_RECOVERY_ACTION_D0":
        lawful_contexts += context_count
    else:
        nonroutes += context_count
        # The five contextual axes are deliberately absent from hard_o11_state;
        # they cannot compensate for a hard invalid or unresolved state.
        if hard_o11_state(axes) == "READY_RECOVERY_ACTION_D0":
            hard_invalid_context_repairs += context_count
root = hashlib.sha256(json.dumps({
    "hard": rows,
    "context_count": context_count,
}, separators=(",", ":")).encode()).hexdigest()
print(json.dumps({
    "schema": "AURA-PROJECT006-O11-13D-v1",
    "states": len(hard_states) * context_count,
    "lawful_contexts": lawful_contexts,
    "nonroutes": nonroutes,
    "hard_invalid_context_repairs": hard_invalid_context_repairs,
    "root": root,
}, sort_keys=True, separators=(",", ":")))
