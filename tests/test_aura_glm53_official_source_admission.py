import hashlib
import importlib.util
import inspect
import json
import pathlib
import struct
import sys
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / "tools" / "quantization" / "aura_glm53_official_source_admission.py"
spec = importlib.util.spec_from_file_location("glm53_source_admission", MODULE_PATH)
q = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = q
assert spec.loader is not None
spec.loader.exec_module(q)


def official_config_fixture():
    return {
        "architectures": ["GlmMoeDsaForCausalLM"],
        "model_type": "glm_moe_dsa",
        "hidden_size": 6144,
        "moe_intermediate_size": 2048,
        "n_routed_experts": 256,
        "num_experts_per_tok": 8,
        "num_hidden_layers": 78,
        "num_nextn_predict_layers": 1,
        "max_position_embeddings": 1048576,
        "quantization_config": {
            "quant_method": "fp8",
            "fmt": "e4m3",
            "weight_block_size": [128, 128],
        },
    }


def synthetic_index_bytes(prefix="model.layers.3.mlp.experts.7"):
    shard = "model-00009-of-00141.safetensors"
    weight_map = {f"{prefix}.{role}": shard for role in q.REQUIRED_ROLES}
    raw = json.dumps({"metadata": {"total_size": 1}, "weight_map": weight_map}, sort_keys=True, separators=(",", ":")).encode()
    return raw, weight_map, shard


def synthetic_header(prefix="model.layers.3.mlp.experts.7", bad_scale=False):
    offset = 0
    header = {}
    shapes = {
        "gate_proj.weight": (2048, 6144),
        "gate_proj.weight_scale_inv": (16, 48),
        "up_proj.weight": (2048, 6144),
        "up_proj.weight_scale_inv": (16, 48),
        "down_proj.weight": (6144, 2048),
        "down_proj.weight_scale_inv": (48, 16),
    }
    if bad_scale:
        shapes["down_proj.weight_scale_inv"] = (47, 16)
    for role in q.REQUIRED_ROLES:
        shape = shapes[role]
        dtype = "F32" if role.endswith("weight_scale_inv") else "F8_E4M3"
        nbytes = 4096 if dtype == "F32" else 8192
        header[f"{prefix}.{role}"] = {
            "dtype": dtype,
            "shape": list(shape),
            "data_offsets": [offset, offset + nbytes],
        }
        offset += nbytes
    body = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    return struct.pack("<Q", len(body)) + body


class OfficialGLM53SourceAdmissionTests(unittest.TestCase):
    def test_current_official_config_profile_is_typed(self):
        obs = q.observe_official_config(official_config_fixture())
        self.assertEqual(obs.revision, "7cda81930d6e4cef42f48555de830aa32ecdde28")
        self.assertEqual(obs.weight_block_size, (128, 128))
        self.assertEqual(obs.n_routed_experts, 256)
        self.assertEqual(obs.num_hidden_layers, 78)
        self.assertEqual(obs.num_nextn_predict_layers, 1)

    def test_config_substitution_fails_closed(self):
        config = official_config_fixture()
        config["quantization_config"]["weight_block_size"] = [64, 128]
        with self.assertRaises(ValueError):
            q.observe_official_config(config)
        config = official_config_fixture()
        config["n_routed_experts"] = 255
        with self.assertRaises(ValueError):
            q.observe_official_config(config)

    def test_index_object_identity_does_not_claim_bytes(self):
        ident = q.official_index_object_identity()
        self.assertEqual(ident.sha256, q.OFFICIAL_INDEX_SHA256)
        self.assertEqual(ident.size_bytes, 11_359_251)
        self.assertFalse(ident.bytes_materialized)
        self.assertFalse(ident.weight_map_observed)

    def test_generic_index_bytes_are_recomputed_and_tamper_sensitive(self):
        raw, weight_map, _ = synthetic_index_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        obs = q.verify_index_bytes(raw, expected_sha256=digest, expected_size=len(raw))
        self.assertEqual(obs.tensor_count, 6)
        self.assertEqual(obs.weight_map, weight_map)
        tampered = raw + b" "
        with self.assertRaises(ValueError):
            q.verify_index_bytes(tampered, expected_sha256=digest, expected_size=len(raw))

    def test_synthetic_bytes_cannot_impersonate_official_index(self):
        raw, _, _ = synthetic_index_bytes()
        with self.assertRaises(ValueError):
            q.verify_official_index_bytes(raw)

    def test_header_parser_and_fp8_companion_binding(self):
        raw, weight_map, shard = synthetic_index_bytes()
        obs = q.verify_index_bytes(raw, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_size=len(raw))
        prefix = "model.layers.3.mlp.experts.7"
        mapping = q.extract_expert_bundle(obs, prefix)
        self.assertEqual(mapping, weight_map)
        parsed = q.parse_safetensors_header(synthetic_header(prefix), shard)
        bundle = q.bind_expert_headers(prefix, mapping, {shard: parsed})
        self.assertEqual(len(bundle.entries), 6)
        self.assertEqual(bundle.entries[0].dtype, "F8_E4M3")
        self.assertEqual(bundle.entries[1].dtype, "F32")

    def test_bad_fp8_companion_shape_fails_closed(self):
        raw, _, shard = synthetic_index_bytes()
        obs = q.verify_index_bytes(raw, expected_sha256=hashlib.sha256(raw).hexdigest(), expected_size=len(raw))
        prefix = "model.layers.3.mlp.experts.7"
        mapping = q.extract_expert_bundle(obs, prefix)
        parsed = q.parse_safetensors_header(synthetic_header(prefix, bad_scale=True), shard)
        with self.assertRaises(ValueError):
            q.bind_expert_headers(prefix, mapping, {shard: parsed})

    def test_current_public_state_is_hold_not_header_trial(self):
        state = q.current_public_state()
        self.assertTrue(state.config_profile_bound)
        self.assertTrue(state.index_object_identity_bound)
        self.assertTrue(state.candidate_representation_bound)
        self.assertFalse(state.index_bytes_verified)
        self.assertFalse(state.representative_key_to_shard_bound)
        self.assertFalse(state.representative_headers_observed)
        self.assertFalse(state.fp8_companions_bound)
        self.assertFalse(state.header_trial_eligible)
        self.assertFalse(state.source_tensor_payload_bound)
        self.assertFalse(state.real_tensor_quantization_eligible)
        self.assertFalse(state.semantic_k27_authority)
        self.assertFalse(state.native_transformer_kv_accessed)
        self.assertFalse(state.gate10_promoted)

    def test_public_official_admission_has_no_boolean_escape_hatch(self):
        params = tuple(inspect.signature(q.admit_official_header_state).parameters)
        self.assertEqual(
            params,
            ("config", "index_bytes", "expert_prefix", "shard_header_prefixes", "candidate_parent_sha"),
        )
        self.assertFalse(any(name.endswith("verified") or name.endswith("bound") for name in params))

    def test_official_admission_stops_before_headers_without_exact_index_bytes(self):
        raw, _, shard = synthetic_index_bytes()
        with self.assertRaises(ValueError):
            q.admit_official_header_state(
                official_config_fixture(),
                raw,
                "model.layers.3.mlp.experts.7",
                {shard: synthetic_header()},
                candidate_parent_sha=q.PR628_E8_PAGE_ARTIFACT_SHA,
            )


if __name__ == "__main__":
    unittest.main()
