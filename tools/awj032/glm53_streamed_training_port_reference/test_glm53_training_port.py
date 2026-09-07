from __future__ import annotations

from dataclasses import replace
import itertools
import random
import re
import unittest

from glm53_training_port import (
    EXPECTED,
    PortDecision,
    StaticObservation,
    TrainingSkeleton,
    assess_port,
    selected_expert_slice_plan,
)


def observation(**changes):
    base = StaticObservation(
        architecture=EXPECTED["architecture"],
        model_type=EXPECTED["model_type"],
        layer_count=EXPECTED["layer_count"],
        num_experts=EXPECTED["num_experts"],
        top_k=EXPECTED["top_k"],
        first_dense_layers=EXPECTED["first_dense_layers"],
        gate_up_rank=3,
        down_rank=3,
        experts_interface=True,
        native_router_owns_selection=True,
        fp8_format=EXPECTED["fp8_format"],
        fp8_block_shape=EXPECTED["fp8_block_shape"],
        remote_code_false=True,
        layer_topology=EXPECTED["layer_topology"],
        transformers_version="5.15.0",
        airllm_revision=EXPECTED["airllm_revision"],
    )
    return replace(base, **changes)


def skeleton(**changes):
    base = TrainingSkeleton(True, True, True, True, False, False, 0.0)
    return replace(base, **changes)


class GLM53TrainingPortTests(unittest.TestCase):
    def test_exact_static_contract_closes_to_empirical_hold_not_training_admit(self):
        r = assess_port(observation(), skeleton())
        self.assertEqual(r.decision, PortDecision.HOLD_EMPIRICAL_PORT_RUN)
        self.assertTrue(r.static_abi_ready)
        self.assertIn("owner-host", r.empirical_obligation)

    def test_remote_code_fails_closed(self):
        self.assertEqual(assess_port(observation(remote_code_false=False), skeleton()).decision, PortDecision.BLOCK_SECURITY)

    def test_grouped_expert_bank_contract_is_mandatory(self):
        self.assertEqual(assess_port(observation(gate_up_rank=2), skeleton()).decision, PortDecision.BLOCK_EXPERT_BANK)
        self.assertEqual(assess_port(observation(experts_interface=False), skeleton()).decision, PortDecision.BLOCK_EXPERT_BANK)

    def test_native_router_contract_is_mandatory(self):
        self.assertEqual(assess_port(observation(top_k=4), skeleton()).decision, PortDecision.BLOCK_ROUTER)
        self.assertEqual(assess_port(observation(native_router_owns_selection=False), skeleton()).decision, PortDecision.BLOCK_ROUTER)

    def test_fp8_scale_contract_is_mandatory(self):
        self.assertEqual(assess_port(observation(fp8_block_shape=(64, 64)), skeleton()).decision, PortDecision.BLOCK_FP8)

    def test_backward_recompute_contract_is_mandatory(self):
        self.assertEqual(assess_port(observation(), skeleton(use_cache=True)).decision, PortDecision.BLOCK_TRAINING_SKELETON)
        self.assertEqual(assess_port(observation(), skeleton(lora_dropout=0.1)).decision, PortDecision.BLOCK_TRAINING_SKELETON)
        self.assertEqual(assess_port(observation(), skeleton(adapter_only_gradients=False)).decision, PortDecision.BLOCK_TRAINING_SKELETON)

    def test_slice_plan_is_unique_selected_first_axis_only(self):
        plan = selected_expert_slice_plan([[7, 2, 7, 9], [9, 10, 2, 3]], num_experts=256)
        self.assertEqual(len(plan), 5 * 4)
        for key in plan:
            self.assertRegex(key, r"^(gate_up_proj|down_proj|gate_up_proj_scale|down_proj_scale)\[\d+\]$")
        self.assertNotIn("gate_up_proj", plan)
        self.assertNotIn("down_proj", plan)

    def test_slice_plan_rejects_out_of_range_experts(self):
        with self.assertRaises(ValueError):
            selected_expert_slice_plan([[0, 255, 256]], num_experts=256)

    def test_eight_corner_crystalline_lattice(self):
        ready = 0
        for source_ok, expert_ok, skeleton_ok in itertools.product([False, True], repeat=3):
            obs = observation(
                airllm_revision=EXPECTED["airllm_revision"] if source_ok else "stale",
                experts_interface=expert_ok,
            )
            sk = skeleton(backward_recompute=skeleton_ok)
            ready += assess_port(obs, sk).static_abi_ready
        self.assertEqual(ready, 1)

    def test_hyperscale_1000_routes_preserve_native_selected_set_and_address_all_experts(self):
        rng = random.Random(333908)
        seen = set()
        for _ in range(1000):
            rows = []
            for _token in range(rng.randint(1, 16)):
                row = rng.sample(range(256), 8)
                rows.append(row)
                seen.update(row)
            plan = selected_expert_slice_plan(rows)
            planned_ids = {int(re.search(r"\[(\d+)\]", key).group(1)) for key in plan}
            selected = {i for row in rows for i in row}
            self.assertEqual(planned_ids, selected)
            self.assertEqual(len(plan), 4 * len(selected))
            self.assertTrue(all("[" in key and "]" in key for key in plan))
        self.assertEqual(seen, set(range(256)))

    def test_y13_witness_is_stable_and_derived(self):
        a = assess_port(observation(), skeleton())
        b = assess_port(observation(), skeleton())
        self.assertEqual(len(a.y13), 13)
        self.assertEqual(a.y13, b.y13)
        self.assertEqual(len(a.y13[-1]), 64)


if __name__ == "__main__":
    unittest.main()
