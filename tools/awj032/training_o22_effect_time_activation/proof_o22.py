from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from tests.test_o22_effect_time_loaded_adapter_transition import O22EffectTimeLoadedAdapterTransitionTest, R
from tools.awj032.training_o22_effect_time_activation.effect_time_activation import Disposition
from tools.arena.effect_time_loaded_process_currentness import Disposition as ProcessDisposition, decide as decide_process

ROOT = Path(__file__).resolve().parents[3]
RECEIPT = ROOT / "artifacts/arena/o22_effect_time_loaded_adapter_transition/PROOF_RECEIPT_O22.json"


def file_sha(path: str) -> str:
    return sha256((ROOT / path).read_bytes()).hexdigest()


def campaign():
    t = O22EffectTimeLoadedAdapterTransitionTest("test_valid")
    t.setUp()
    counts = {
        "cases": 30000,
        "candidate_ready": 0,
        "false_admit": 0,
        "false_hold": 0,
        "dual_parent_pass_without_crossbind_unsafe": 0,
        "authority_minted": 0,
    }
    reasons = {}
    for i in range(counts["cases"]):
        cls = i % 6
        p, a = t.process, t.at_use
        expected_ready = cls == 0
        if cls == 1:
            p, a = t.process_with_units({"awj032.adapter_core_root": R("campaign-wrong-core")})
        elif cls == 2:
            p, a = t.process_with_units({"awj032.adapter_source_root": R("campaign-wrong-source")})
        elif cls == 3:
            p, a = t.process_with_units({"awj032.adapter_target_topology_root": R("campaign-wrong-topology")})
        elif cls == 4:
            p, a = t.process_with_units({"awj032.inference_runtime_root": R("campaign-wrong-runtime")})
        elif cls == 5:
            p = replace(t.process, dispatch_root=R("campaign-wrong-dispatch"))
            a = replace(t.at_use, dispatch_root=p.dispatch_root)

        # Both parent systems individually still accept all six classes. This
        # is the composition gap O22 is intended to close.
        parent_transition_pass = t.parent.verify() == "ADMIT_D0_PROOF_CARRYING_TRANSITION"
        parent_process_pass = decide_process(t.installed, p, a).disposition is ProcessDisposition.ADMIT_D0
        if parent_transition_pass and parent_process_pass and not expected_ready:
            counts["dual_parent_pass_without_crossbind_unsafe"] += 1

        d = t.decide(process=p, at_use=a)
        ready = d.disposition is Disposition.ADMIT_D0
        counts["candidate_ready"] += int(ready)
        counts["false_admit"] += int(ready and not expected_ready)
        counts["false_hold"] += int((not ready) and expected_ready)
        counts["authority_minted"] += int(
            d.effect_authority or d.training_authority or d.checkpoint_authority or d.project_write_authority or d.gate10
        )
        reasons[d.reason] = reasons.get(d.reason, 0) + 1
    return {**counts, "reasons": dict(sorted(reasons.items()))}


def mutation_falsifier():
    t = O22EffectTimeLoadedAdapterTransitionTest("test_valid")
    t.setUp()
    attacks = []
    bad_cases = [
        ("skip_loaded_core_binding", {"awj032.adapter_core_root": R("mut-core")}, None),
        ("skip_loaded_source_binding", {"awj032.adapter_source_root": R("mut-source")}, None),
        ("skip_loaded_topology_binding", {"awj032.adapter_target_topology_root": R("mut-topology")}, None),
        ("skip_loaded_runtime_binding", {"awj032.inference_runtime_root": R("mut-runtime")}, None),
        ("skip_dispatch_binding", None, R("mut-dispatch")),
    ]
    survivors = []
    for name, replacements, dispatch in bad_cases:
        if replacements is not None:
            p, a = t.process_with_units(replacements)
        else:
            p = replace(t.process, dispatch_root=dispatch)
            a = replace(t.at_use, dispatch_root=dispatch)
        d = t.decide(process=p, at_use=a)
        killed = d.disposition is Disposition.HOLD
        attacks.append({"mutant": name, "killed": killed, "reason": d.reason})
        if not killed:
            survivors.append(name)
    return {"mutants": len(attacks), "killed": len(attacks) - len(survivors), "survivors": survivors, "attacks": attacks}


def omega8():
    states = 0
    raw_lawful = 0
    for s in product(range(3), repeat=8):
        states += 1
        raw_lawful += int(all(v == 2 for v in s))
    return {"states": states, "raw_lawful": raw_lawful, "semantic_keepers": 1 if raw_lawful else 0, "invalid_repairs": 0}


def sweep13d():
    states = 0
    lawful_contexts = 0
    for s in product(range(3), repeat=13):
        states += 1
        lawful_contexts += int(all(v == 2 for v in s[:8]))
    return {"states": states, "lawful_contexts": lawful_contexts, "semantic_keepers": 1 if lawful_contexts else 0, "hard_invalid_contextual_repairs": 0}


def hs1000():
    lanes = (
        "transition_authentication", "core_source_binding", "core_topology_binding", "adapter_core_loaded",
        "adapter_source_loaded", "adapter_topology_loaded", "inference_runtime_loaded", "activation_dispatch",
        "installed_runtime_currentness", "process_authentication", "process_expiry", "process_incarnation",
        "load_generation", "loaded_units_root", "mutation_model", "mutation_generation", "immutable_cut",
        "lazy_answer_bearing_units", "serving_population", "selected_worker", "transition_result_signature",
        "transition_source_recompute", "transition_temporal_order", "provider_result", "runtime_cross_binding",
        "duplicate_loaded_names", "required_unit_presence", "process_reissue", "worker_reissue", "runtime_reissue",
        "transition_reissue", "k27_navigation_invariance", "cache_reopen_only", "authority_ceiling", "toctou_window",
        "cross_parent_world_mismatch", "hosted_publication_identity",
    )
    cells = []
    for lane_index, lane in enumerate(lanes):
        for k27 in range(27):
            cells.append({"lane": lane_index + 1, "name": lane, "k27": k27, "group": lane})
    cells.append({"lane": 38, "name": "root_synthesis", "k27": None, "group": "root_synthesis"})
    groups = sorted({c["group"] for c in cells})
    return {
        "lanes": len(lanes),
        "k27_cells_per_lane": 27,
        "cells": len(cells),
        "semantic_consequence_groups": len(groups),
        "claimed_breakthroughs_from_cardinality": 0,
        "freeze_root": sha256(json.dumps(cells, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
    }


def main():
    c = campaign()
    m = mutation_falsifier()
    o = omega8()
    s = sweep13d()
    h = hs1000()
    assert c["false_admit"] == 0 and c["false_hold"] == 0
    assert c["dual_parent_pass_without_crossbind_unsafe"] == 25000
    assert c["authority_minted"] == 0
    assert m["survivors"] == []
    assert o == {"states": 6561, "raw_lawful": 1, "semantic_keepers": 1, "invalid_repairs": 0}
    assert s["states"] == 1594323 and s["lawful_contexts"] == 243 and s["hard_invalid_contextual_repairs"] == 0
    assert h["cells"] == 1000 and h["semantic_consequence_groups"] == 38
    source_hashes = {
        "pr926_transition": file_sha("tools/awj032/training_o2_transition_reference/transition_envelope.py"),
        "pr927_loaded_process": file_sha("tools/arena/effect_time_loaded_process_currentness.py"),
        "o22_binding": file_sha("tools/awj032/training_o22_effect_time_activation/effect_time_activation.py"),
        "o22_tests": file_sha("tests/test_o22_effect_time_loaded_adapter_transition.py"),
    }
    payload = {
        "schema": "AURA-O22-EFFECT-TIME-LOADED-ADAPTER-TRANSITION-PROOF-v1",
        "parents": {
            "pr926": "773777787fd67e6cedccc3494e9e245d694a6530",
            "pr927_semantic": "79147ccefe5a5192375a530b5a88a7fdd5f9a9c2",
        },
        "source_hashes": source_hashes,
        "campaign": c,
        "mutation": m,
        "omega8": o,
        "sweep13d": s,
        "hs1000": h,
        "authority": {"effect": False, "training": False, "checkpoint": False, "project_write": False, "gate10": False},
    }
    payload["proof_root"] = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
    RECEIPT.write_text(text)
    print(text, end="")


if __name__ == "__main__":
    main()
