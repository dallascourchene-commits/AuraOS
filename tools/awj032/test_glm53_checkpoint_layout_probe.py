import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).with_name("glm53_checkpoint_layout_probe.py")
SPEC = importlib.util.spec_from_file_location("glm53_checkpoint_layout_probe", PATH)
m = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = m
assert SPEC.loader is not None
SPEC.loader.exec_module(m)


def config():
    return {
        "n_routed_experts": 256,
        "hidden_size": 6144,
        "moe_intermediate_size": 2048,
        "num_hidden_layers": 78,
        "quantization_config": {
            "quant_method": "fp8",
            "fmt": "e4m3",
            "weight_block_size": [128, 128],
        },
    }


def complete_per_expert_weight_map():
    wm = {}
    for e in range(256):
        for p in ("gate_proj", "up_proj", "down_proj"):
            wm[f"model.layers.3.mlp.experts.{e}.{p}.weight"] = "s1"
    wm["model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv"] = "s1"
    return wm


class GLM53CheckpointLayoutProbeTests(unittest.TestCase):
    def test_geometry_matches_flagship_shape_law(self):
        g = m.geometry_from_config(config())
        self.assertEqual(g.gate_up_fp8_bytes, 6_442_450_944)
        self.assertEqual(g.down_fp8_bytes, 3_221_225_472)
        self.assertEqual(g.gate_up_block_scale_elements, 393_216)
        self.assertEqual(g.down_block_scale_elements, 196_608)
        self.assertEqual(g.candidate_fp32_scale_bank_bytes, 2_359_296)

    def test_packed_physical_layout_detected(self):
        wm = {
            "model.layers.3.mlp.experts.gate_up_proj": "s1",
            "model.layers.3.mlp.experts.down_proj": "s2",
            "model.layers.3.mlp.experts.gate_up_proj_scale_inv": "s3",
        }
        r = m.classify_layer_layout(config(), wm, layer=3)
        self.assertEqual(r["layout"], "PACKED_PHYSICAL_LAYOUT")
        self.assertGreater(r["scale_key_count"], 0)

    def test_monolithic_gate_cannot_fit_smaller_assigned_shard(self):
        wm = {
            "model.layers.3.mlp.experts.gate_up_proj": "s1",
            "model.layers.3.mlp.experts.down_proj": "s2",
            "model.layers.3.mlp.experts.gate_up_proj_scale_inv": "s3",
        }
        r = m.classify_layer_layout(
            config(), wm, layer=3, shard_sizes={"s1": 5_370_000_000, "s2": 5_370_000_000}
        )
        self.assertIn("PACKED_GATE_TENSOR_EXCEEDS_ASSIGNED_SHARD", r["reasons"])

    def test_complete_per_expert_layout_detected(self):
        r = m.classify_layer_layout(config(), complete_per_expert_weight_map(), layer=3)
        self.assertEqual(r["layout"], "PER_EXPERT_PHYSICAL_LAYOUT")
        self.assertEqual(r["complete_per_expert_count"], 256)

    def test_partial_per_expert_layout_fails_closed(self):
        wm = {
            "model.layers.3.mlp.experts.0.gate_proj.weight": "s1",
            "model.layers.3.mlp.experts.0.up_proj.weight": "s1",
            "model.layers.3.mlp.experts.0.down_proj.weight": "s1",
        }
        r = m.classify_layer_layout(config(), wm, layer=3)
        self.assertEqual(r["layout"], "PARTIAL_PER_EXPERT_LAYOUT")
        self.assertIn("PER_EXPERT_COVERAGE_INCOMPLETE", r["reasons"])

    def test_fp8_without_scale_keys_is_unresolved(self):
        wm = {
            "model.layers.3.mlp.experts.gate_up_proj": "s1",
            "model.layers.3.mlp.experts.down_proj": "s2",
        }
        r = m.classify_layer_layout(config(), wm, layer=3)
        self.assertIn("FP8_SCALE_KEYS_UNRESOLVED", r["reasons"])

    def test_mtp_extra_layer_is_explicit_blocker_and_not_ready(self):
        wm = complete_per_expert_weight_map()
        wm["model.layers.78.self_attn.q_a_proj.weight"] = "mtp"
        r = m.probe_checkpoint(
            config=config(),
            weight_map=wm,
            model_revision="modelrev",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        self.assertTrue(r["mtp_index_present"])
        self.assertIn("GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED", r["blockers"])
        self.assertEqual(r["status"], "PARTIAL")
        self.assertFalse(r["g2_admitted"])

    def test_chunked_vendor_layout_requires_mapping_before_ready(self):
        wm = {
            "model.layers.3.mlp.experts.vendor_chunk_0": "s1",
            "model.layers.3.mlp.experts.vendor_chunk_0_scale": "s1",
        }
        r = m.probe_checkpoint(
            config=config(),
            weight_map=wm,
            model_revision="modelrev",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        self.assertEqual(r["layer"]["layout"], "CHUNKED_OR_VENDOR_LAYOUT")
        self.assertIn("GLM53_CHUNK_MAPPING_REQUIRED", r["blockers"])
        self.assertEqual(r["status"], "PARTIAL")

    def test_unexpected_extra_layer_requires_classification(self):
        wm = complete_per_expert_weight_map()
        wm["model.layers.79.self_attn.q_a_proj.weight"] = "unexpected"
        r = m.probe_checkpoint(
            config=config(),
            weight_map=wm,
            model_revision="modelrev",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        self.assertFalse(r["mtp_index_present"])
        self.assertEqual(r["unexpected_extra_checkpoint_layer_indices"], [79])
        self.assertIn("GLM53_UNEXPECTED_CHECKPOINT_LAYER_CLASSIFICATION_REQUIRED", r["blockers"])
        self.assertEqual(r["status"], "PARTIAL")

    def test_security_input_requires_actual_bool(self):
        with self.assertRaises(m.ProbeError) as ctx:
            m.probe_checkpoint(
                config=config(),
                weight_map={},
                model_revision="m",
                config_sha256="c",
                index_sha256="i",
                airllm_revision="a",
                security_hard_false_remote_code="false",
            )
        self.assertEqual(ctx.exception.code, "SECURITY_HARD_FALSE_REMOTE_CODE_BOOL_REQUIRED")

    def test_metadata_ready_has_no_required_blockers(self):
        r = m.probe_checkpoint(
            config=config(),
            weight_map=complete_per_expert_weight_map(),
            model_revision="modelrev",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        self.assertEqual(r["status"], "READY_FOR_HEADER_AND_TINY_FIXTURE")
        self.assertEqual(r["blockers"], [])

    def test_security_block_has_priority(self):
        r = m.probe_checkpoint(
            config=config(),
            weight_map={},
            model_revision="m",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=False,
        )
        self.assertEqual(r["status"], "BLOCKED_SECURITY")
        self.assertIn("AIRLLM_REMOTE_CODE_SECURITY_BLOCK", r["blockers"])

    def test_observation_time_does_not_churn_logical_id(self):
        kwargs = dict(
            config=config(),
            weight_map={},
            model_revision="m",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        a = m.probe_checkpoint(**kwargs, observation_time="t1")
        b = m.probe_checkpoint(**kwargs, observation_time="t2")
        self.assertEqual(a["logical_id"], b["logical_id"])

    def test_missing_currentness_fails_closed(self):
        with self.assertRaises(m.ProbeError) as ctx:
            m.probe_checkpoint(
                config=config(),
                weight_map={},
                model_revision="",
                config_sha256="c",
                index_sha256="i",
                airllm_revision="a",
                security_hard_false_remote_code=True,
            )
        self.assertEqual(ctx.exception.code, "CURRENTNESS_FIELD_REQUIRED")

    def test_report_never_admits_large_checkpoint_or_g2(self):
        r = m.probe_checkpoint(
            config=config(),
            weight_map={},
            model_revision="m",
            config_sha256="c",
            index_sha256="i",
            airllm_revision="a",
            security_hard_false_remote_code=True,
        )
        self.assertFalse(r["large_checkpoint_admitted"])
        self.assertFalse(r["g2_admitted"])
        self.assertFalse(r["runtime_execution_proven"])
        self.assertEqual(r["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
