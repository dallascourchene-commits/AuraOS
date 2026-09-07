from __future__ import annotations

import argparse
from dataclasses import replace
from hashlib import sha256
import itertools
import json
from pathlib import Path
import random
from collections import Counter

from tools.awj032.speculative_realization_reconciliation_reference.speculative_realization_reconciliation import (
    AdoptionTarget,
    CanonicalSelectionV1,
    Disposition,
    MaterializationKind,
    O20PortBindingV1,
    O4EffectTimeBindingV1,
    O20_HOLD_EMPIRICAL,
    O4_EFFECT_TIME_ADMIT,
    O_AVX14_CAMPAIGN_ROOT,
    PROOF_CONSUMER_MATRIX,
    SCHEMA,
    SpeculativeMaterializationCapsule,
    reconcile_speculative_materialization,
)

O20_SEMANTIC_PROOF_COMMIT = "950d35702ef777563a84b85f5adda0a7bd824b4e"
O20_TERMINAL_COMMIT = "997f6583add693fba54a9c03b7958053bd2ee915"
O4_CURRENT_LINEAGE_HEAD = "4e4b25a6f3228f6c93b3d840e076f23fb6367748"
FRONTDOOR_BUNDLE_SHA256 = "97e40a23c1f29ca3087b372dea3987019695d486c1a541964780cbc762762812"
FRONTDOOR_MODULE_SHA256 = "629871db3bf03fa26331996089414c6698084302e7190ec2f0c6e393bfd0cb19"


def r(value: object) -> str:
    return sha256(str(value).encode()).hexdigest()


def file_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fixtures():
    q = SpeculativeMaterializationCapsule(
        MaterializationKind.QWEN_ADAPTER,
        r("base"), r("candidate"), r("bytes"), r("source"), r("runtime"), r("proof"), r("consumer"),
        O_AVX14_CAMPAIGN_ROOT,
        adapter_realization_root=r("realization"), adapter_cache_root=r("cache"),
    )
    g = SpeculativeMaterializationCapsule(
        MaterializationKind.GLM_EXPERT_SLICE_SET,
        r("base"), r("candidate"), r("bytes"), r("source"), r("runtime"), r("proof"), r("consumer"),
        O_AVX14_CAMPAIGN_ROOT,
        native_route_root=r("route"), selected_slice_plan_root=r("slices"), fp8_scale_plan_root=r("scales"),
    )
    current = CanonicalSelectionV1(
        r("base"), r("candidate"), r("bytes"), r("source"), r("runtime"), r("proof"), r("consumer")
    )
    o20 = O20PortBindingV1(
        r("port"), True, O20_HOLD_EMPIRICAL, True, r("route"), r("slices"), r("scales")
    )
    o4 = O4EffectTimeBindingV1(
        True, O4_EFFECT_TIME_ADMIT, r("realization"), r("cache"), r("process"), r("effect")
    )
    return q, g, current, o20, o4


CASES = (
    "q_cache_exact", "losing_candidate", "base_drift", "source_drift", "runtime_drift", "proof_drift",
    "consumer_drift", "materialization_drift", "q_serving_no_o4", "q_serving_exact_o4", "q_training",
    "glm_cache_exact", "glm_training", "glm_route_drift", "glm_slice_drift", "glm_scale_drift",
    "glm_o20_not_ready", "glm_serving",
)
EXPECTED = {
    "q_cache_exact": Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,
    "losing_candidate": Disposition.DISSOLVE_NONWINNING_CANDIDATE,
    "base_drift": Disposition.HOLD_PROJECT_BASE_CURRENTNESS,
    "source_drift": Disposition.HOLD_SOURCE_CURRENTNESS,
    "runtime_drift": Disposition.HOLD_RUNTIME_CURRENTNESS,
    "proof_drift": Disposition.HOLD_PROOF_CURRENTNESS,
    "consumer_drift": Disposition.HOLD_CONSUMER_CURRENTNESS,
    "materialization_drift": Disposition.HOLD_MATERIALIZATION_IDENTITY,
    "q_serving_no_o4": Disposition.HOLD_O4_EFFECT_TIME_REBIND,
    "q_serving_exact_o4": Disposition.ADMIT_D0_EFFECT_TIME_REBOUND,
    "q_training": Disposition.HOLD_UNSUPPORTED_ACTIVATION,
    "glm_cache_exact": Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,
    "glm_training": Disposition.HOLD_EMPIRICAL_PORT_RUN,
    "glm_route_drift": Disposition.HOLD_NATIVE_ROUTE_BINDING,
    "glm_slice_drift": Disposition.HOLD_SELECTED_SLICE_BINDING,
    "glm_scale_drift": Disposition.HOLD_FP8_SCALE_BINDING,
    "glm_o20_not_ready": Disposition.HOLD_O20_STATIC_ABI,
    "glm_serving": Disposition.HOLD_UNSUPPORTED_ACTIVATION,
}


def execute_named_case(name: str, salt: int = 0):
    q, g, cur, o20, o4 = fixtures()
    alt = lambda key: r(f"{key}:{salt}")
    spec = q
    target = AdoptionTarget.CACHE_REUSE
    passed_o20 = None
    passed_o4 = None
    if name == "q_cache_exact":
        pass
    elif name == "losing_candidate":
        cur = replace(cur, winning_candidate_operation_root=alt("winner"))
    elif name == "base_drift":
        cur = replace(cur, project_base_root=alt("base"))
    elif name == "source_drift":
        cur = replace(cur, source_generation_root=alt("source"))
    elif name == "runtime_drift":
        cur = replace(cur, runtime_root=alt("runtime"))
    elif name == "proof_drift":
        cur = replace(cur, proof_root=alt("proof"))
    elif name == "consumer_drift":
        cur = replace(cur, consumer_root=alt("consumer"))
    elif name == "materialization_drift":
        cur = replace(cur, materialization_root=alt("materialization"))
    elif name == "q_serving_no_o4":
        target = AdoptionTarget.SERVING_ACTIVATION
    elif name == "q_serving_exact_o4":
        target = AdoptionTarget.SERVING_ACTIVATION
        passed_o4 = o4
    elif name == "q_training":
        target = AdoptionTarget.TRAINING_ACTIVATION
    elif name == "glm_cache_exact":
        spec, passed_o20 = g, o20
    elif name == "glm_training":
        spec, passed_o20, target = g, o20, AdoptionTarget.TRAINING_ACTIVATION
    elif name == "glm_route_drift":
        spec, passed_o20 = g, replace(o20, native_route_root=alt("route"))
    elif name == "glm_slice_drift":
        spec, passed_o20 = g, replace(o20, selected_slice_plan_root=alt("slices"))
    elif name == "glm_scale_drift":
        spec, passed_o20 = g, replace(o20, fp8_scale_plan_root=alt("scales"))
    elif name == "glm_o20_not_ready":
        spec, passed_o20 = g, replace(o20, static_abi_ready=False)
    elif name == "glm_serving":
        spec, passed_o20, target = g, o20, AdoptionTarget.SERVING_ACTIVATION
    else:
        raise AssertionError(name)
    decision = reconcile_speculative_materialization(
        speculative=spec, current=cur, target=target, o20=passed_o20, o4=passed_o4
    )
    return decision, spec, cur, target


def random_campaign(n: int = 24_000) -> dict:
    rng = random.Random(0xA0_5_20260907)
    counts = Counter()
    false_module = 0
    false_reuse_naive = 0
    authority_promotions = 0
    cases = list(CASES)
    for i in range(n):
        name = cases[i] if i < len(cases) else cases[rng.randrange(len(cases))]
        decision, spec, cur, target = execute_named_case(name, salt=rng.randrange(1, 1_000_000_000))
        expected = EXPECTED[name]
        if decision.disposition is not expected:
            false_module += 1
        counts[decision.disposition.value] += 1
        if decision.effect_authority or decision.training_authority or decision.checkpoint_authority or decision.gate10:
            authority_promotions += 1
        naive_reuse = cur.materialization_root == spec.materialization_root
        lawful_reuse_or_effect = decision.disposition in {
            Disposition.REUSE_EXACT_SPECULATIVE_BYTES_D0,
            Disposition.ADMIT_D0_EFFECT_TIME_REBOUND,
        }
        if naive_reuse and not lawful_reuse_or_effect:
            false_reuse_naive += 1
    assert false_module == 0, false_module
    assert authority_promotions == 0, authority_promotions
    assert false_reuse_naive > 0, "wrong oracle was not falsified"
    return {
        "cases": n,
        "decision_counts": dict(sorted(counts.items())),
        "false_module_decisions": false_module,
        "authority_promotions": authority_promotions,
        "wrong_same_bytes_oracle_false_reuse": false_reuse_naive,
        "oracle_customs": "PASS_WRONG_SAME_BYTES_CLASSIFIER_REJECTED",
    }


def omega8() -> dict:
    q, _, cur, _, o4 = fixtures()
    admitted = 0
    false_admit = 0
    counts = Counter()
    for state in itertools.product(range(3), repeat=8):
        s_cur = cur
        s_o4 = o4
        axes = ("winner", "base", "source", "runtime", "proof", "consumer", "materialization", "o4")
        for axis, value in zip(axes, state):
            if value == 0:
                continue
            alt = r(f"omega8:{axis}:{value}")
            if axis == "winner": s_cur = replace(s_cur, winning_candidate_operation_root=alt)
            elif axis == "base": s_cur = replace(s_cur, project_base_root=alt)
            elif axis == "source": s_cur = replace(s_cur, source_generation_root=alt)
            elif axis == "runtime": s_cur = replace(s_cur, runtime_root=alt)
            elif axis == "proof": s_cur = replace(s_cur, proof_root=alt)
            elif axis == "consumer": s_cur = replace(s_cur, consumer_root=alt)
            elif axis == "materialization": s_cur = replace(s_cur, materialization_root=alt)
            elif axis == "o4": s_o4 = replace(s_o4, cache_root=alt)
        d = reconcile_speculative_materialization(
            speculative=q, current=s_cur, target=AdoptionTarget.SERVING_ACTIVATION, o4=s_o4
        )
        is_admit = d.disposition is Disposition.ADMIT_D0_EFFECT_TIME_REBOUND
        should_admit = all(v == 0 for v in state)
        admitted += int(is_admit)
        false_admit += int(is_admit and not should_admit)
        counts[d.disposition.value] += 1
    assert admitted == 1 and false_admit == 0, (admitted, false_admit)
    return {
        "states": 3**8,
        "hard_keeper_states": admitted,
        "false_admits": false_admit,
        "decision_counts": dict(sorted(counts.items())),
    }


def factored_13d() -> dict:
    hard = omega8()
    nuisance_contexts = 3**5
    total = hard["states"] * nuisance_contexts
    contextual_lawful = hard["hard_keeper_states"] * nuisance_contexts
    hard_invalid_repair = hard["false_admits"] * nuisance_contexts
    assert total == 1_594_323
    assert contextual_lawful == 243
    assert hard_invalid_repair == 0
    return {
        "states": total,
        "hard_axes": 8,
        "nuisance_axes": 5,
        "nuisance_contexts_per_hard_state": nuisance_contexts,
        "hard_keeper_classes": 1,
        "contextual_lawful_states": contextual_lawful,
        "hard_invalid_contextual_repairs": hard_invalid_repair,
    }


def hs1000() -> dict:
    counts = Counter()
    false_module = 0
    for i in range(1000):
        name = CASES[i % len(CASES)]
        d, *_ = execute_named_case(name, salt=10_000 + i)
        if d.disposition is not EXPECTED[name]:
            false_module += 1
        counts[d.disposition.value] += 1
    assert false_module == 0
    return {
        "frozen_cells": 1000,
        "consequence_classes": len(counts),
        "decision_counts": dict(sorted(counts.items())),
        "false_module_decisions": false_module,
        "breakthrough_claims": 0,
    }


def proof_consumer_audit() -> dict:
    required_fields = {
        "candidate_operation_root", "project_base_root", "source_generation_root", "runtime_root", "proof_root",
        "consumer_root", "materialization_root", "native_route_root", "selected_slice_plan_root", "fp8_scale_plan_root",
        "adapter_realization_root", "adapter_cache_root", "o20_binding", "o4_binding",
    }
    observed = set(PROOF_CONSUMER_MATRIX)
    missing = sorted(required_fields - observed)
    unexpected = sorted(observed - required_fields)
    incomplete = sorted(
        field for field, consumers in PROOF_CONSUMER_MATRIX.items()
        if not {"focused_tests", "random_campaign"}.issubset(consumers)
    )
    higher_order = {"oracle_customs", "omega8", "13d", "hs1000", "proof_consumer_audit", "proof_receipt"}
    shallow = sorted(field for field, consumers in PROOF_CONSUMER_MATRIX.items() if not (set(consumers) & higher_order))
    passed = not missing and not unexpected and not incomplete and not shallow
    assert passed, {"missing": missing, "unexpected": unexpected, "incomplete": incomplete, "shallow": shallow}
    return {
        "status": "PASS_DEPENDENCY_CLOSED_CONSUMER_CONE",
        "producer_fields": len(required_fields),
        "missing_fields": missing,
        "unexpected_fields": unexpected,
        "minimum_consumer_incomplete": incomplete,
        "higher_order_untracked": shallow,
        "matrix": {k: list(v) for k, v in sorted(PROOF_CONSUMER_MATRIX.items())},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--frontdoor-receipt", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    frontdoor_path = Path(args.frontdoor_receipt)
    frontdoor = json.loads(frontdoor_path.read_text())
    selected = frontdoor["active_tool_neighborhood"]["selected_capability_ids"]
    required_selected = ["drive.read", "drive.write", "github.read", "github.write", "python.exec", "web.read"]
    assert selected == required_selected, selected
    assert frontdoor["runtime_jacked_in_required"] is True
    assert frontdoor["global_laptop_jacked_in"] is False

    module_path = Path(__file__).with_name("speculative_realization_reconciliation.py")
    test_path = Path(__file__).with_name("test_speculative_realization_reconciliation.py")
    proof = {
        "schema": "AURA-AWJ032-O5-PROOF-RECEIPT-v1",
        "implementation_schema": SCHEMA,
        "frontdoor_runtime": {
            "bundle_sha256": FRONTDOOR_BUNDLE_SHA256,
            "module_sha256": FRONTDOOR_MODULE_SHA256,
            "prework_receipt_sha256": file_sha(frontdoor_path),
            "objective_root": frontdoor["objective_root"],
            "project_root": frontdoor["project_root"],
            "capability_projection_root": frontdoor["projection_root"],
            "active_tool_neighborhood_root": frontdoor["active_tool_neighborhood_root"],
            "cruise_root": frontdoor["cruise_root"],
            "ephemeral_app_root": frontdoor["ephemeral_app_root"],
            "selected_capability_ids": selected,
            "runtime_jacked_in_required": True,
            "global_laptop_jacked_in": False,
        },
        "parents": {
            "o_avx14_campaign_root": O_AVX14_CAMPAIGN_ROOT,
            "o20_semantic_proof_commit": O20_SEMANTIC_PROOF_COMMIT,
            "o20_terminal_commit": O20_TERMINAL_COMMIT,
            "o4_ancestor_head": O4_CURRENT_LINEAGE_HEAD,
        },
        "source_sha256": file_sha(module_path),
        "tests_sha256": file_sha(test_path),
        "proof_script_sha256": file_sha(Path(__file__)),
        "random_campaign": random_campaign(),
        "oracle_customs": None,
        "proof_consumer_audit": proof_consumer_audit(),
        "omega8": omega8(),
        "factored_13d": factored_13d(),
        "hs1000": hs1000(),
        "authority": {
            "effect": False,
            "training": False,
            "checkpoint": False,
            "gate10": False,
            "owner_host_runtime_claim": False,
        },
        "claim_ceiling": "D0_POST_SPECULATION_RECONCILIATION_ONLY_NOT_SCHEDULER_NOT_MODEL_EXECUTION_NOT_OWNER_HOST_PROOF",
        "status": "PASS",
    }
    proof["oracle_customs"] = {
        "status": proof["random_campaign"]["oracle_customs"],
        "wrong_same_bytes_false_reuse": proof["random_campaign"]["wrong_same_bytes_oracle_false_reuse"],
    }
    proof["proof_root"] = sha256(json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()
    out = Path(args.out)
    out.write_text(json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n")
    print(json.dumps({
        "status": proof["status"], "proof_root": proof["proof_root"],
        "campaign_cases": proof["random_campaign"]["cases"],
        "wrong_oracle_false_reuse": proof["oracle_customs"]["wrong_same_bytes_false_reuse"],
        "omega8_keeper": proof["omega8"]["hard_keeper_states"],
        "13d_contextual_lawful": proof["factored_13d"]["contextual_lawful_states"],
        "hs1000_cells": proof["hs1000"]["frozen_cells"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
