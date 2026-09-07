from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import sys

ARENA = Path(__file__).resolve().parent
REPO = ARENA.parents[1]
sys.path.insert(0, str(ARENA))
sys.path.insert(0, str(REPO / "tests"))

from test_memory_city_ecf_effect_refinement import fixture, hx  # noqa: E402
from memory_city_consequence_refinement import (  # noqa: E402
    EffectIntent,
    EffectObligationProjection,
    compile_effect_refinement,
)
from memory_city_ecf_effect_refinement import compile_ecf_effect_refinement  # noqa: E402


def run(n: int = 20_000) -> dict:
    rows = []
    oracle_mismatches = 0
    unsafe_baseline = 0
    false_hold = 0
    expected = {
        0: "READY_REFINED_D0",
        1: "PARTIAL_HOLD_D0",
        2: "PARTIAL_HOLD_D0",
        3: "PARTIAL_HOLD_D0",
        4: "PARTIAL_HOLD_D0",
        5: "PARTIAL_HOLD_D0",
        6: "PARTIAL_HOLD_D0",
        7: "PARTIAL_HOLD_D0",
        8: "PARTIAL_HOLD_D0",
        9: "PARTIAL_HOLD_D0",
        10: "READY_REFINED_D0",
        11: "HOLD_BINDING_ENVELOPE_D0",
    }
    mode_names = {
        0: "valid",
        1: "owner_not_admitted",
        2: "obligation_moved",
        3: "source_observation_moved",
        4: "intent_moved",
        5: "jurisdiction_generation_moved",
        6: "producer_registry_moved",
        7: "producer_incarnation_moved",
        8: "coherent_cut_moved",
        9: "admitted_witness_not_owner_admitted",
        10: "nuisance_only_moved",
        11: "detached_read_binding",
    }
    counts: dict[str, int] = {}
    per_mode: dict[str, int] = {name: 0 for name in mode_names.values()}

    for i in range(n):
        mode = i % 12
        tag = f"c{i}"
        cert, intent, obs, index, _ = fixture(tag)
        if mode == 1:
            cert, intent, obs, index, _ = fixture(tag, admit=False)
        elif mode == 2:
            obs = replace(obs, effect_obligation_root=hx(f"moved-obl:{i}"))
        elif mode == 3:
            obs = replace(obs, source_observation_root=hx(f"moved-src:{i}"))
        elif mode == 4:
            intent = EffectIntent(hx(f"moved-int:{i}"), intent.effect_domain_root, intent.program_root)
        elif mode == 5:
            cert, intent, obs, index, _ = fixture(tag, cut_mut={"jurisdiction_generation": 5})
        elif mode == 6:
            cert, intent, obs, index, _ = fixture(tag, cut_mut={"producer_registry_root": hx(f"reg2:{i}")})
        elif mode == 7:
            cert, intent, obs, index, _ = fixture(tag, cut_mut={"producer_incarnation": "inc-8"})
        elif mode == 8:
            cert, intent, obs, index, _ = fixture(tag, cut_mut={"coherent_cut_root": hx(f"cut2:{i}")})
        elif mode == 9:
            cert, intent, obs, index, _ = fixture(tag, admit=False)
        elif mode == 10:
            obs = replace(obs, nuisance_configuration_root=hx(f"nuis2:{i}"))
        elif mode == 11:
            obs = replace(obs, read_binding_root=hx(f"detached:{i}"))

        sealed = compile_ecf_effect_refinement((obs,), cert, intent, index)
        got = sealed.plan.status
        exp = expected[mode]
        if got != exp:
            oracle_mismatches += 1
        counts[got] = counts.get(got, 0) + 1
        per_mode[mode_names[mode]] += 1

        if mode != 11:
            baseline = compile_effect_refinement(
                (
                    EffectObligationProjection(
                        obs.read_binding_root,
                        obs.effect_obligation_root,
                        hx(f"caller-evidence:{i}"),
                        True,
                        True,
                        obs.nuisance_configuration_root,
                    ),
                ),
                cert,
                intent,
            )
            if exp != "READY_REFINED_D0" and baseline.status == "READY_REFINED_D0":
                unsafe_baseline += 1
        if exp == "READY_REFINED_D0" and got != "READY_REFINED_D0":
            false_hold += 1
        rows.append((mode, got, sealed.evidence_set_root))

    root = sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema": "AURA-O10R1-ECF-REFINEMENT-CAMPAIGN-v1",
        "cases": n,
        "oracle_mismatches": oracle_mismatches,
        "unsafe_self_attested_baseline_ready": unsafe_baseline,
        "false_hold": false_hold,
        "counts": counts,
        "per_mode": per_mode,
        "campaign_root": root,
        "upstream_ecf_owner_authentication_claimed": False,
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
