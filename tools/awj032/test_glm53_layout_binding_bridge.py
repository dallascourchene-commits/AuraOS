import copy
import unittest

from tools.awj032.glm53_layout_binding_bridge import LayoutBindingError, compile_pager_source_plan

MODEL = "glm53-pinned-revision"
INDEX = "index-pinned-digest"
GATE = "model.layers.3.mlp.experts.gate_up_proj.weight"
DOWN = "model.layers.3.mlp.experts.down_proj.weight"
GS = "model.layers.3.mlp.experts.gate_up_proj.weight_scale_inv"
DS = "model.layers.3.mlp.experts.down_proj.weight_scale_inv"


def packed_fixture():
    report = {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-packed",
        "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
        "blockers": [],
        "layer": {
            "layer": 3,
            "layout": "PACKED_PHYSICAL_LAYOUT",
            "packed_gate_key": GATE,
            "packed_down_key": DOWN,
            "scale_keys": [GS, DS],
            "geometry": {"num_experts": 256, "block_size": [128, 128]},
        },
        "observation_time": "t1",
    }
    wm = {GATE: "s10", GS: "s10", DOWN: "s11", DS: "s11"}
    hs = {
        GATE: {"shape": [256, 4096, 6144], "dtype": "F8_E4M3", "shard": "s10", "header_digest": "hg"},
        GS: {"shape": [256, 32, 48], "dtype": "F32", "shard": "s10", "header_digest": "hgs"},
        DOWN: {"shape": [256, 6144, 2048], "dtype": "F8_E4M3", "shard": "s11", "header_digest": "hd"},
        DS: {"shape": [256, 48, 16], "dtype": "F32", "shard": "s11", "header_digest": "hds"},
    }
    return report, wm, hs


def per_expert_fixture():
    report = {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-per-expert",
        "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
        "blockers": [],
        "layer": {
            "layer": 3,
            "layout": "PER_EXPERT_PHYSICAL_LAYOUT",
            "geometry": {"num_experts": 256, "block_size": [128, 128]},
        },
    }
    wm = {}
    for eid in range(256):
        for proj in ("gate_proj", "up_proj", "down_proj"):
            key = f"model.layers.3.mlp.experts.{eid}.{proj}.weight"
            scale = f"model.layers.3.mlp.experts.{eid}.{proj}.weight_scale_inv"
            wm[key] = f"shard-{eid // 16:02d}"
            wm[scale] = f"shard-{eid // 16:02d}"
    return report, wm


def compile_packed(report=None, wm=None, hs=None):
    r, w, h = packed_fixture()
    return compile_pager_source_plan(
        r if report is None else report,
        weight_map=w if wm is None else wm,
        headers=h if hs is None else hs,
        expected_model_revision=MODEL,
        expected_index_digest=INDEX,
    )


class BridgeTests(unittest.TestCase):
    def code(self, expected, fn):
        with self.assertRaises(LayoutBindingError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_packed_layout_binds_current_pager_abi(self):
        plan = compile_packed()
        self.assertEqual(plan.binding_kind, "PACKED_FIRST_AXIS")
        self.assertEqual(plan.binding.tensor_map, {"gate_up": GATE, "down": DOWN})
        self.assertEqual(plan.binding.scale_map, {"gate_up_scale": GS, "down_scale": DS})
        self.assertFalse(plan.g2_admitted)

    def test_per_expert_layout_binds_current_per_expert_abi(self):
        report, wm = per_expert_fixture()
        plan = compile_pager_source_plan(
            report, weight_map=wm, headers=None,
            expected_model_revision=MODEL, expected_index_digest=INDEX,
        )
        self.assertEqual(plan.binding_kind, "PER_EXPERT_INDEX")
        self.assertEqual(len(plan.binding.experts), 256)
        self.assertTrue(plan.binding.require_fp8_scales)
        self.assertFalse(plan.to_dict()["g2_admitted"])

    def test_per_expert_missing_scale_fails_in_sibling_abi(self):
        report, wm = per_expert_fixture()
        del wm["model.layers.3.mlp.experts.7.down_proj.weight_scale_inv"]
        with self.assertRaises(Exception) as ctx:
            compile_pager_source_plan(report, weight_map=wm, headers=None, expected_model_revision=MODEL, expected_index_digest=INDEX)
        self.assertIn("FP8_SCALE_KEYS_UNRESOLVED", str(ctx.exception))

    def test_stale_currentness_and_probe_blockers_fail_closed(self):
        r, wm, hs = packed_fixture()
        self.code("STALE_MODEL_REVISION", lambda: compile_pager_source_plan(r, weight_map=wm, headers=hs, expected_model_revision="other", expected_index_digest=INDEX))
        r["blockers"] = ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]
        self.code("PROBE_BLOCKED", lambda: compile_packed(report=r))

    def test_packed_requires_header_axis_shard_and_fp8_dtype(self):
        _, _, hs = packed_fixture()
        hs[GATE]["shape"][0] = 255
        self.code("EXPERT_AXIS_HEADER_MISMATCH", lambda: compile_packed(hs=hs))
        _, _, hs = packed_fixture()
        hs[GATE]["shard"] = "wrong"
        self.code("HEADER_SHARD_BINDING_MISMATCH", lambda: compile_packed(hs=hs))
        _, _, hs = packed_fixture()
        hs[GATE]["dtype"] = "BF16"
        self.code("PACKED_WEIGHT_DTYPE_MISMATCH", lambda: compile_packed(hs=hs))

    def test_vendor_and_partial_layouts_are_typed_residuals(self):
        r, _, _ = packed_fixture()
        r["layer"]["layout"] = "CHUNKED_OR_VENDOR_LAYOUT"
        self.code("VENDOR_LAYOUT_ADAPTER_REQUIRED", lambda: compile_packed(report=r))
        r["layer"]["layout"] = "PARTIAL_PER_EXPERT_LAYOUT"
        self.code("PER_EXPERT_LAYOUT_PARTIAL", lambda: compile_packed(report=r))

    def test_scale_ambiguity_is_not_guessed(self):
        r, _, _ = packed_fixture()
        r["layer"]["scale_keys"].append("model.layers.3.mlp.experts.gate_up_proj.alt_scale")
        self.code("FP8_SCALE_ROLE_AMBIGUOUS", lambda: compile_packed(report=r))

    def test_clock_metadata_does_not_churn_source_plan(self):
        a, _, _ = packed_fixture()
        b = copy.deepcopy(a)
        b["observation_time"] = "later"
        self.assertEqual(compile_packed(report=a).source_plan_digest, compile_packed(report=b).source_plan_digest)


if __name__ == "__main__":
    unittest.main()
