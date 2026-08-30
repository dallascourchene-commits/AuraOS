import copy
import unittest

import glm53_compatibility_probe as p


BASE_CONFIG = {
    "architectures": ["GlmMoeDsaForCausalLM"],
    "model_type": "glm_moe_dsa",
    "num_hidden_layers": 78,
    "n_routed_experts": 256,
    "num_experts_per_tok": 8,
    "first_k_dense_replace": 3,
    "transformers_version": "5.15.0",
    "quantization_config": {
        "quant_method": "fp8",
        "fmt": "e4m3",
        "weight_block_size": [128, 128],
        "activation_scheme": "dynamic",
    },
}

AIR_AUTO_UNSAFE = """
class AutoModel:
    @classmethod
    def get_module_class(cls, path):
        return AutoConfig.from_pretrained(path, trust_remote_code=True)
"""

AIR_AUTO_SAFE = AIR_AUTO_UNSAFE.replace("True", "False")

AIR_BASE = """
class AirLLMBaseModel:
    def set_layer_names_dict(self):
        self.layer_names_dict = {'embed': 'model.embed_tokens', 'layer_prefix': 'model.layers', 'norm': 'model.norm', 'lm_head': 'lm_head'}
    def get_tokenizer(self):
        return AutoTokenizer.from_pretrained(self.model_local_path, trust_remote_code=True)
    def _setup_expert_streaming(self):
        expert_module = experts_container[expert_idx]
        expert_module.register_forward_pre_hook(self._expert_pre_hook)
        state = load_layer_subset(self.checkpoint_path, layer_name, keys)
"""

AIR_BASE_SAFE = AIR_BASE.replace("trust_remote_code=True", "trust_remote_code=False")

AIR_UTILS_KEY_ONLY = """
def load_layer_subset(local_path, layer_name, keys):
    with safe_open(path, framework='pt') as f:
        return {k: f.get_tensor(k) for k in keys}

def load_layer(local_path, layer_name):
    pass
"""

GLM_SOURCE = """
@use_experts_implementation
class GlmMoeDsaExperts(nn.Module):
    def __init__(self, config):
        self.gate_up_proj = nn.Parameter(torch.empty(self.num_experts, 2 * self.intermediate_dim, self.hidden_dim))
        self.down_proj = nn.Parameter(torch.empty(self.num_experts, self.hidden_dim, self.intermediate_dim))
class GlmMoeDsaMoE(nn.Module):
    def __init__(self, config):
        self.experts = GlmMoeDsaExperts(config)
    def forward(self, hidden_states):
        return self.experts(hidden_states, topk_indices, topk_weights)
class GlmMoeDsaModel(nn.Module):
    def __init__(self, config):
        self.embed_tokens = nn.Embedding(config.vocab_size, config.hidden_size)
        self.layers = nn.ModuleList([])
        self.norm = GlmMoeDsaRMSNorm(config.hidden_size)
class GlmMoeDsaForCausalLM(nn.Module):
    def __init__(self, config):
        self.model = GlmMoeDsaModel(config)
        self.lm_head = nn.Linear(config.hidden_size, config.vocab_size)
"""


class GLM53CompatibilityProbeTests(unittest.TestCase):
    def analyze(self, config=None, auto=AIR_AUTO_UNSAFE, base=AIR_BASE, utils=AIR_UTILS_KEY_ONLY, glm=GLM_SOURCE):
        return p.analyze(
            config or BASE_CONFIG,
            airllm_auto_model_source=auto,
            airllm_base_source=base,
            airllm_utils_source=utils,
            transformers_glm_source=glm,
        )

    def codes(self, receipt):
        return {item.code for item in receipt.findings}

    def test_stock_v33_shape_is_partial_not_native_pass(self):
        r = self.analyze()
        self.assertEqual("PARTIAL", r.status)
        self.assertFalse(r.g2_admitted)
        self.assertEqual("STATIC_COMPATIBLE", r.ordinary_layer_streaming)
        self.assertEqual("ADAPTER_REQUIRED", r.routed_expert_streaming)
        self.assertIn("GLM53_GROUPED_TENSOR_EXPERT_ADAPTER_REQUIRED", self.codes(r))

    def test_stock_remote_code_true_is_security_finding(self):
        r = self.analyze()
        self.assertEqual("BLOCKED_STOCK_SOURCE", r.remote_code_membrane)
        self.assertIn("AIRLLM_REMOTE_CODE_SECURITY_BLOCK", self.codes(r))

    def test_safe_remote_code_source_does_not_remove_expert_gap(self):
        r = self.analyze(auto=AIR_AUTO_SAFE, base=AIR_BASE_SAFE)
        self.assertEqual("NO_LITERAL_TRUE_FOUND", r.remote_code_membrane)
        self.assertEqual("ADAPTER_REQUIRED", r.routed_expert_streaming)
        self.assertFalse(r.g2_admitted)

    def test_config_architecture_mismatch_blocks(self):
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["architectures"] = ["ChatGLMForConditionalGeneration"]
        r = self.analyze(cfg)
        self.assertEqual("BLOCKED_ARCHITECTURE", r.status)
        self.assertIn("GLM53_ARCH_MISMATCH", self.codes(r))

    def test_layer_count_mismatch_blocks(self):
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["num_hidden_layers"] = 79
        r = self.analyze(cfg)
        self.assertEqual("BLOCKED_ARCHITECTURE", r.status)
        self.assertIn("GLM53_LAYER_COUNT_MISMATCH", self.codes(r))

    def test_expert_count_mismatch_blocks(self):
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["n_routed_experts"] = 128
        r = self.analyze(cfg)
        self.assertEqual("BLOCKED_ARCHITECTURE", r.status)
        self.assertIn("GLM53_ROUTED_EXPERT_COUNT_MISMATCH", self.codes(r))

    def test_fp8_mismatch_blocks(self):
        cfg = copy.deepcopy(BASE_CONFIG)
        cfg["quantization_config"]["weight_block_size"] = [64, 64]
        r = self.analyze(cfg)
        self.assertEqual("BLOCKED_ARCHITECTURE", r.status)
        self.assertIn("GLM53_FP8_METADATA_MISMATCH", self.codes(r))

    def test_grouped_tensor_source_is_required(self):
        r = self.analyze(glm="class GlmMoeDsaExperts: pass")
        self.assertEqual("BLOCKED_ARCHITECTURE", r.status)
        self.assertIn("GLM53_GROUPED_EXPERT_SOURCE_UNPROVEN", self.codes(r))

    def test_adapter_spec_preserves_native_router_and_all_experts(self):
        r = self.analyze()
        self.assertTrue(r.adapter_spec["keep_transformers_native_glm_router_attention_dsa"])
        self.assertIn("never prune", r.adapter_spec["routing_law"])
        self.assertEqual("safetensors safe_open.get_slice first-axis expert slices", r.adapter_spec["required_slice_loader"])

    def test_receipt_is_deterministic(self):
        a = self.analyze().to_dict()
        b = self.analyze().to_dict()
        self.assertEqual(a, b)
        self.assertEqual(a["config_digest"], b["config_digest"])
        self.assertEqual(a["source_digests"], b["source_digests"])

    def test_probe_never_admits_g2(self):
        r = self.analyze(auto=AIR_AUTO_SAFE, base=AIR_BASE_SAFE)
        self.assertFalse(r.g2_admitted)
        self.assertIn("one sparse layer output matches full-resident reference fixture", r.adapter_spec["tests_required"])


if __name__ == "__main__":
    unittest.main()
