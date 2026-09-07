import hashlib
import itertools
import json

cells = []
for boundary, mechanism, recovery in itertools.product(range(10), repeat=3):
    cell = {
        "boundary": boundary,
        "mechanism": mechanism,
        "recovery": recovery,
        "expected_gain": "UNSCORED_AT_FREEZE",
    }
    cell["cell_root"] = hashlib.sha256(
        json.dumps(cell, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    cells.append(cell)
freeze_root = hashlib.sha256(
    json.dumps(cells, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
classes = (
    "ACK_REQUIRED",
    "ATTEMPT_REQUIRED",
    "IDEMPOTENT_RETRY",
    "QUERY_RECONCILE",
    "NONRETRYABLE_HOLD",
    "RETURN_ONLY",
    "IDENTITY_REBIND",
    "TERMINAL_CLASS_SPLIT",
)
groups = {}
for cell in cells:
    label = classes[(cell["boundary"] + 2 * cell["mechanism"] + 3 * cell["recovery"]) % len(classes)]
    groups[label] = groups.get(label, 0) + 1
quotient_root = hashlib.sha256(
    json.dumps(groups, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
print(json.dumps({
    "schema": "AURA-PROJECT006-O11-HS1000-v1",
    "raw_cells": len(cells),
    "freeze_root": freeze_root,
    "consequence_groups": len(groups),
    "groups": groups,
    "quotient_root": quotient_root,
    "claimed_breakthroughs": 0,
}, sort_keys=True, separators=(",", ":")))
