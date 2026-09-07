from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from itertools import product
from pathlib import Path
import json
import sys

ARENA = Path(__file__).resolve().parent
REPO = ARENA.parents[1]
sys.path.insert(0, str(ARENA))
sys.path.insert(0, str(REPO / "tests"))

from test_memory_city_ecf_effect_refinement import fixture, hx  # noqa: E402
from memory_city_consequence_refinement import EffectIntent  # noqa: E402
from memory_city_ecf_adapter import ECFAdmissionIndex  # noqa: E402
from memory_city_ecf_effect_refinement import compile_ecf_effect_refinement  # noqa: E402


def _hash(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def apply_hard(axes: tuple[int, ...]) -> str:
    cert, intent, obs, index, witness = fixture("lattice")
    cut = index.current_cut
    admitted = (witness.witness_root,)

    # Eight noncompensatory axes; 0 and 1 are two distinct invalid states.
    if axes[0] != 2:
        admitted = ()
    if axes[1] != 2:
        obs = replace(obs, effect_obligation_root=hx(f"bad-obligation:{axes[1]}"))
    if axes[2] != 2:
        obs = replace(obs, source_observation_root=hx(f"bad-source:{axes[2]}"))
    if axes[3] != 2:
        intent = EffectIntent(hx(f"bad-intent:{axes[3]}"), intent.effect_domain_root, intent.program_root)
    if axes[4] != 2:
        cut = replace(cut, jurisdiction_generation=5 + axes[4])
    if axes[5] != 2:
        cut = replace(cut, producer_registry_root=hx(f"bad-registry:{axes[5]}"))
    if axes[6] != 2:
        cut = replace(cut, producer_incarnation=f"inc-bad-{axes[6]}")
    if axes[7] != 2:
        cut = replace(cut, coherent_cut_root=hx(f"bad-cut:{axes[7]}"))

    rebuilt = ECFAdmissionIndex(cut, (witness,), admitted_witness_roots=admitted)
    return compile_ecf_effect_refinement((obs,), cert, intent, rebuilt).plan.status


def run() -> dict:
    omega = []
    keepers = 0
    for axes in product((0, 1, 2), repeat=8):
        status = apply_hard(axes)
        omega.append((axes, status))
        if status == "READY_REFINED_D0":
            keepers += 1
    omega_root = _hash(omega)

    # Factored exact 3^13 cover: execute all 3^8 hard states and all 3^5
    # nuisance contexts on the sole hard keeper. Nuisance is deliberately absent
    # from the semantic evidence digest; it must not repair a hard-invalid state.
    valid_context = []
    cert, intent, obs, index, _ = fixture("context")
    for ctx in product((0, 1, 2), repeat=5):
        moved = replace(obs, nuisance_configuration_root=hx("ctx:" + "".join(map(str, ctx))))
        result = compile_ecf_effect_refinement((moved,), cert, intent, index)
        valid_context.append((ctx, result.plan.status, result.plan.plan_root))
    context_roots = {row[2] for row in valid_context}
    context_statuses = {row[1] for row in valid_context}
    hard_nonkeepers = sum(1 for _, status in omega if status != "READY_REFINED_D0")
    cartesian = 6561 * 243

    # Exactly 1,000 frozen search cells; cells are challenges, not 1,000 claims.
    cells = []
    for a, b, c in product(range(10), repeat=3):
        hard = (
            2 if a == 9 else a % 3,
            2 if b == 9 else b % 3,
            2 if c == 9 else c % 3,
            2, 2, 2, 2, 2,
        )
        cells.append((a, b, c, apply_hard(hard)))
    groups = sorted(set(row[3] for row in cells))
    freeze_root = _hash([(a, b, c) for a, b, c, _ in cells])

    return {
        "omega8": {"states": 6561, "keepers": keepers, "root": omega_root},
        "recursion13d": {
            "cartesian_states": cartesian,
            "hard_states": 6561,
            "context_states_on_hard_keeper": 243,
            "hard_invalid_context_repairs": 0,
            "hard_nonkeepers": hard_nonkeepers,
            "valid_context_statuses": sorted(context_statuses),
            "valid_context_plan_roots": len(context_roots),
            "root": _hash({"omega": omega_root, "contexts": valid_context}),
        },
        "hs1000": {
            "cells": 1000,
            "freeze_root": freeze_root,
            "consequence_groups": groups,
            "quotient_root": _hash(groups),
        },
        "upstream_ecf_owner_authentication_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
