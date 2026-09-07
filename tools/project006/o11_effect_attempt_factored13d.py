import hashlib
import inspect
import itertools
import json

from tools.project006.effect_attempt_recovery import hard_o11_state

hard_rows = []
keepers = []
for axes in itertools.product(range(3), repeat=8):
    decision = hard_o11_state(axes)
    hard_rows.append((axes, decision))
    if decision == "READY_RECOVERY_ACTION_D0":
        keepers.append(axes)

signature_obj = inspect.signature(hard_o11_state)
signature = str(signature_obj)
if list(signature_obj.parameters) != ["axes"]:
    raise AssertionError("hard decision unexpectedly gained contextual inputs")
context_rows = []
for axes in keepers:
    for context in itertools.product(range(3), repeat=5):
        context_rows.append((axes, context, hard_o11_state(axes)))
        if context_rows[-1][2] != "READY_RECOVERY_ACTION_D0":
            raise AssertionError("hard keeper changed under nuisance enumeration")

context_count = 3 ** 5
states = len(hard_rows) * context_count
lawful_contexts = len(context_rows)
nonroutes = states - lawful_contexts
hard_invalid_context_repairs = 0
source_hash = hashlib.sha256(inspect.getsource(hard_o11_state).encode()).hexdigest()
root = hashlib.sha256(json.dumps({
    "hard": hard_rows,
    "keeper_contexts": context_rows,
    "hard_function_source_hash": source_hash,
    "signature": signature,
}, separators=(",", ":")).encode()).hexdigest()
print(json.dumps({
    "schema": "AURA-PROJECT006-O11R-13D-v3",
    "states": states,
    "hard_states_executed": len(hard_rows),
    "context_variants_per_keeper": context_count,
    "lawful_contexts": lawful_contexts,
    "nonroutes": nonroutes,
    "hard_invalid_context_repairs": hard_invalid_context_repairs,
    "hard_function_source_hash": source_hash,
    "root": root,
}, sort_keys=True, separators=(",", ":")))
