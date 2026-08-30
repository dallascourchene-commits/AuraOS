import copy
import unittest

from tools.awj032.glm53_layout_binding_bridge import LayoutBindingError, compile_pager_source_plan

MODEL = "glm53-pinned-revision"
INDEX = "index-pinned-digest"
GATE = "model.layers.3.mlp.experts.gate_up_proj.weight"
DOWN = "model.layers.3.mlp.experts.down_proj.weight"
GS = "model.layers.3.mlp.experts.gate_up_proj.weight_scale_inv"
DS = "model.layers.3.mlp.experts.down_proj.weight_scale_inv"


def fixture():
    report = {
        "schema": "GLM53CheckpointLayoutProbeV1",
        "model_revision": MODEL,
        "index_sha256": INDEX,
        "logical_id": "probe-123",
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
    weight_map = {GATE: "s10", GS: "s10", DOWN: "s11", DS: "s11"}
    headers = {
        GATE: {"shape": [256, 4096, 6144], "dtype": "F8_E4M3", "shard": "s10", "header_digest": "hg"},
        GS: {"shape": [256, 32, 48], "dtype": "F32", "shard": "s10", "header_digest": "hgs"},
        DOWN: {"shape": [256, 6144, 2048], "dtype": "F8_E4M3", "shard": "s11", "header_digest": "hd"},
        DS: {"shape": [256, 48, 16], "dtype": "F32", "shard": "s11", "header_digest": "hds"},
    }
    return report, weight_map, headers


def compile_fixture(report=None, weight_map=None, headers=None):
    r, wm, hs = fixture()
    return compile_pager_source_plan(
        r if report is None else report,
        weight_map=wm if weight_map is None else weight_map,
        headers=hs if headers is None else headers,
        expected_model_revision=MODEL,
        expected_index_digest=INDEX,
    )


class BridgeTests(unittest.TestCase):
    def code(self, expected, fn):
        with self.assertRaises(LayoutBindingError) as ctx:
            fn()
        self.assertEqual(ctx.exception.code, expected)

    def test_packed_binding_ready_and_nonpromoting(self):
        plan = compile_fixture()
        self.assertEqual(plan.binding.tensor_map, {"gate_up": GATE, "down": DOWN})
        self.assertEqual(plan.binding.scale_map, {"gate_up_scale": GS, "down_scale": DS})
        self.assertFalse(plan.to_dict()["g2_admitted"])

    def test_stale_currentness_fails_closed(self):
        r, wm, hs = fixture()
        self.code("STALE_MODEL_REVISION", lambda: compile_pager_source_plan(r, weight_map=wm, headers=hs, expected_model_revision="other", expected_index_digest=INDEX))
        self.code("STALE_INDEX_DIGEST", lambda: compile_pager_source_plan(r, weight_map=wm, headers=hs, expected_model_revision=MODEL, expected_index_digest="other"))

    def test_probe_blocker_fails_closed(self):
        r, _, _ = fixture()
        r["blockers"] = ["GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED"]
        self.code("PROBE_BLOCKED", lambda: compile_fixture(report=r))

    def test_nonpacked_layouts_become_typed_residuals(self):
        r, _, _ = fixture()
        r["layer"]["layout"] = "PER_EXPERT_PHYSICAL_LAYOUT"
        self.code("PER_EXPERT_BACKEND_REQUIRED", lambda: compile_fixture(report=r))
        r["layer"]["layout"] = "CHUNKED_OR_VENDOR_LAYOUT"
        self.code("VENDOR_LAYOUT_ADAPTER_REQUIRED", lambda: compile_fixture(report=r))

    def test_header_axis_and_shard_are_exact(self):
        _, _, hs = fixture()
        hs[GATE]["shape"][0] = 255
        self.code("EXPERT_AXIS_HEADER_MISMATCH", lambda: compile_fixture(headers=hs))
        _, _, hs = fixture()
        hs[GATE]["shard"] = "wrong"
        self.code("HEADER_SHARD_BINDING_MISMATCH", lambda: compile_fixture(headers=hs))

    def test_scale_role_ambiguity_fails_closed(self):
        r, _, _ = fixture()
        r["layer"]["scale_keys"].append("model.layers.3.mlp.experts.gate_up_proj.alt_scale")
        self.code("FP8_SCALE_ROLE_AMBIGUOUS", lambda: compile_fixture(report=r))

    def test_clock_metadata_does_not_churn_identity(self):
        a, _, _ = fixture()
        b = copy.deepcopy(a)
        b["observation_time"] = "t2"
        self.assertEqual(compile_fixture(report=a).source_plan_digest, compile_fixture(report=b).source_plan_digest)

    def test_header_digest_change_changes_binding(self):
        a = compile_fixture()
        _, _, hs = fixture()
        hs[GS]["header_digest"] = "changed"
        b = compile_fixture(headers=hs)
        self.assertNotEqual(a.binding.digest, b.binding.digest)


if __name__ == "__main__":
    unittest.main()
