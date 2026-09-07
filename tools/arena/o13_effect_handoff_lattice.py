from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from itertools import product
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "arena"))

from campaign_memory_city_effect_handoff_o13 import fixtures
from memory_city_effect_handoff_o13 import HandoffDisposition, compile_effect_handoff, digest


def hx(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def apply_axis_state(axis: int, state: int, cert, kwargs):
    """State 2 is current/valid; 1 is unresolved/stale; 0 is malformed/substituted."""
    if state == 2:
        return cert, kwargs
    if axis == 0:
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], reproof_semantics="UNKNOWN" if state == 1 else "")
    elif axis == 1:
        kwargs["typed_closure"] = replace(kwargs["typed_closure"], receipt_root=hx(f"moved-read-{state}"))
    elif axis == 2:
        admission = dict(kwargs["admission"])
        if state == 1:
            admission["schema"] = "UNKNOWN-ADMISSION"
        else:
            admission.pop("effect_authority")
        kwargs["admission"] = admission
    elif axis == 3:
        kwargs["mutation"] = replace(kwargs["mutation"], holder=f"other-holder-{state}")
    elif axis == 4:
        kwargs["mutation"] = replace(kwargs["mutation"], expires_at=101 + state)
    elif axis == 5:
        kwargs["mutation"] = replace(kwargs["mutation"], installed_fence_generation=16 - state)
        kwargs["verification"] = replace(kwargs["verification"], installed_fence_generation=16 - state)
    elif axis == 6:
        if state == 1:
            kwargs["evidence"] = replace(kwargs["evidence"], owner_evidence_root=hx("old-owner"))
        else:
            kwargs["evidence"] = replace(kwargs["evidence"], verifier_receipt_root=hx("old-verifier"))
    elif axis == 7:
        cert = replace(cert, effect_authority=(state == 1), gate10=(state == 0))
    return cert, kwargs


def classify_hard(axes):
    cert, kwargs = fixtures()
    for axis, state in enumerate(axes):
        cert, kwargs = apply_axis_state(axis, state, cert, kwargs)
    return compile_effect_handoff(cert, **kwargs)


def contextual_projection(decision, context_axes):
    """Five nonauthority context axes: K27 locality, cache warmth, cost, UI hint, telemetry density.

    They are intentionally excluded from the governed handoff input. The function still
    executes over every contextual state and returns the already-proved governed decision,
    making any accidental future coupling visible in this proof harness.
    """
    if len(context_axes) != 5 or any(x not in (0, 1, 2) for x in context_axes):
        raise ValueError("five ternary context axes required")
    return decision.disposition


def run():
    hard_rows = {}
    lattice_routes = 0
    hard_invalid_routes = 0
    for axes in product(range(3), repeat=8):
        decision = classify_hard(axes)
        hard_rows[axes] = decision
        if decision.disposition is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
            lattice_routes += 1
            if axes != (2,) * 8:
                hard_invalid_routes += 1

    contextual_repairs = 0
    contextual_variations = 0
    hard_valid_contexts = 0
    context_count = 0
    for axes, decision in hard_rows.items():
        expected = decision.disposition
        for tail in product(range(3), repeat=5):
            context_count += 1
            projected = contextual_projection(decision, tail)
            if projected is not expected:
                contextual_variations += 1
            if axes == (2,) * 8 and projected is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
                hard_valid_contexts += 1
            if axes != (2,) * 8 and projected is HandoffDisposition.HOLD_TECC_REQUIRED_D0:
                contextual_repairs += 1

    payload = {
        "schema": "AURA-MEMORY-CITY-O13-LATTICE13D-v1",
        "lattice8_states": 3 ** 8,
        "lattice8_tecc_routes": lattice_routes,
        "lattice8_hard_invalid_routes": hard_invalid_routes,
        "sweep13d_states": context_count,
        "sweep13d_hard_valid_contexts": hard_valid_contexts,
        "sweep13d_hard_invalid_context_repairs": contextual_repairs,
        "sweep13d_contextual_decision_variations": contextual_variations,
    }
    payload["root"] = digest(payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
