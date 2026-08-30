"""AWJ032-GLM53 G1 metadata/source compatibility probe.

This module is D0 only.  It does not import AirLLM, Transformers, GLM model code,
download weights, or grant G2.  It consumes already-materialized text/config
artifacts and emits a fail-closed compatibility receipt.

The current target is the full flagship zai-org/GLM-5.3 checkpoint.  The probe
exists to distinguish four independent questions which must not be collapsed:

1. Does the pinned GLM config match the expected architecture/topology?
2. Can AirLLM discover/stream the ordinary embed/layer/norm/lm_head sequence?
3. Can AirLLM stream *routed experts* without materializing the whole 3-D expert
   bank?
4. Does the exact AirLLM source preserve Aura's hard-false remote-code policy?

A PARTIAL result is expected for stock AirLLM v3.3.0 and is useful evidence: it
identifies the smallest adapter seam without pretending native support exists.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

SCHEMA = "AuraGLM53CompatibilityReceiptV1"
EXPECTED_REPO = "zai-org/GLM-5.3"
EXPECTED_ARCH = "GlmMoeDsaForCausalLM"
EXPECTED_MODEL_TYPE = "glm_moe_dsa"
EXPECTED_TRANSFORMERS = "5.15.0"
EXPECTED_LAYERS = 78
EXPECTED_ROUTED_EXPERTS = 256
EXPECTED_EXPERTS_PER_TOKEN = 8
EXPECTED_FIRST_DENSE = 3
EXPECTED_FP8_FORMAT = "e4m3"
EXPECTED_FP8_BLOCK = (128, 128)


@dataclass(frozen=True)
class Finding:
    code: str
    evidence: str


@dataclass(frozen=True)
class CompatibilityReceipt:
    schema: str
    status: str
    architecture: str | None
    model_type: str | None
    config_digest: str
    source_digests: Mapping[str, str]
    ordinary_layer_streaming: str
    routed_expert_streaming: str
    remote_code_membrane: str
    fp8_path: str
    g2_admitted: bool
    adapter_spec: Mapping[str, Any]
    findings: tuple[Finding, ...]
    claim_ceiling: str = "G1_STATIC_SOURCE_PROBE_ONLY_NO_MODEL_IMPORT_OR_WEIGHT_RUNTIME_PROOF"

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["findings"] = [asdict(item) for item in self.findings]
        return out


def _canonical_digest(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _find_remote_code_widening(*sources: tuple[str, str]) -> list[Finding]:
    findings: list[Finding] = []
    true_pattern = re.compile(r"trust_remote_code\s*=\s*True\b")
    for name, text in sources:
        for match in true_pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(Finding("AIRLLM_REMOTE_CODE_SECURITY_BLOCK", f"{name}:{line}:literal True"))
    return findings


def _config_findings(config: Mapping[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    architectures = config.get("architectures") or []
    arch = architectures[0] if architectures else None
    checks = (
        (arch == EXPECTED_ARCH, "GLM53_ARCH_MISMATCH", f"architecture={arch!r}"),
        (config.get("model_type") == EXPECTED_MODEL_TYPE, "GLM53_MODEL_TYPE_MISMATCH", f"model_type={config.get('model_type')!r}"),
        (config.get("num_hidden_layers") == EXPECTED_LAYERS, "GLM53_LAYER_COUNT_MISMATCH", f"num_hidden_layers={config.get('num_hidden_layers')!r}"),
        (config.get("n_routed_experts") == EXPECTED_ROUTED_EXPERTS, "GLM53_ROUTED_EXPERT_COUNT_MISMATCH", f"n_routed_experts={config.get('n_routed_experts')!r}"),
        (config.get("num_experts_per_tok") == EXPECTED_EXPERTS_PER_TOKEN, "GLM53_TOPK_EXPERT_MISMATCH", f"num_experts_per_tok={config.get('num_experts_per_tok')!r}"),
        (config.get("first_k_dense_replace") == EXPECTED_FIRST_DENSE, "GLM53_DENSE_PREFIX_MISMATCH", f"first_k_dense_replace={config.get('first_k_dense_replace')!r}"),
        (config.get("transformers_version") == EXPECTED_TRANSFORMERS, "GLM53_TRANSFORMERS_VERSION_MISMATCH", f"transformers_version={config.get('transformers_version')!r}"),
    )
    for ok, code, evidence in checks:
        if not ok:
            findings.append(Finding(code, evidence))

    quant = config.get("quantization_config") or {}
    block = tuple(quant.get("weight_block_size") or ())
    if quant.get("quant_method") != "fp8" or quant.get("fmt") != EXPECTED_FP8_FORMAT or block != EXPECTED_FP8_BLOCK:
        findings.append(
            Finding(
                "GLM53_FP8_METADATA_MISMATCH",
                f"quant_method={quant.get('quant_method')!r},fmt={quant.get('fmt')!r},block={block!r}",
            )
        )
    if quant.get("activation_scheme") != "dynamic":
        findings.append(Finding("GLM53_FP8_ACTIVATION_SCHEME_MISMATCH", f"activation_scheme={quant.get('activation_scheme')!r}"))
    return findings


def _ordinary_layer_topology(glm_source: str, airllm_base: str) -> tuple[bool, list[Finding]]:
    # These are structural source checks, not runtime proof.
    glm_markers = (
        "self.embed_tokens = nn.Embedding",
        "self.layers = nn.ModuleList",
        "self.norm = GlmMoeDsaRMSNorm",
        "self.model = GlmMoeDsaModel",
        "self.lm_head = nn.Linear",
    )
    air_markers = (
        "'embed': 'model.embed_tokens'",
        "'layer_prefix': 'model.layers'",
        "'norm': 'model.norm'",
        "'lm_head': 'lm_head'",
    )
    missing = [f"glm:{m}" for m in glm_markers if m not in glm_source]
    missing.extend(f"airllm:{m}" for m in air_markers if m not in airllm_base)
    return (not missing, [Finding("GLM53_ORDINARY_LAYER_TOPOLOGY_UNPROVEN", item) for item in missing])


def _grouped_expert_semantics(glm_source: str) -> tuple[bool, list[Finding]]:
    markers = (
        "@use_experts_implementation",
        "class GlmMoeDsaExperts",
        "self.gate_up_proj = nn.Parameter(torch.empty(self.num_experts",
        "self.down_proj = nn.Parameter(torch.empty(self.num_experts",
        "self.experts = GlmMoeDsaExperts(config)",
        "self.experts(hidden_states, topk_indices, topk_weights)",
    )
    missing = [m for m in markers if m not in glm_source]
    return (not missing, [Finding("GLM53_GROUPED_EXPERT_SOURCE_UNPROVEN", item) for item in missing])


def _airllm_expert_assumptions(airllm_base: str, airllm_utils: str) -> tuple[bool, bool, list[Finding]]:
    # v3.3 per-expert streaming expects an indexable container of expert Modules.
    module_hook_assumption = all(
        marker in airllm_base
        for marker in (
            "expert_module = experts_container[expert_idx]",
            "expert_module.register_forward_pre_hook(self._expert_pre_hook)",
            "load_layer_subset",
        )
    )
    # v3.3 subset loading is key-granular: get_tensor(key), not first-axis slices.
    key_only_loader = "def load_layer_subset" in airllm_utils and "get_tensor(k)" in airllm_utils
    slice_loader = "def load_layer_subset" in airllm_utils and "get_slice(" in airllm_utils[
        airllm_utils.find("def load_layer_subset") : airllm_utils.find("def load_layer", airllm_utils.find("def load_layer_subset") + 1)
    ]
    findings: list[Finding] = []
    if not module_hook_assumption:
        findings.append(Finding("AIRLLM_EXPERT_HOOK_ASSUMPTION_UNRESOLVED", "module-index/hook markers absent"))
    if key_only_loader and not slice_loader:
        findings.append(Finding("AIRLLM_EXPERT_LOADER_WHOLE_TENSOR_ONLY", "load_layer_subset uses safe_open.get_tensor(key)"))
    return module_hook_assumption, slice_loader, findings


def analyze(
    config: Mapping[str, Any],
    *,
    airllm_auto_model_source: str,
    airllm_base_source: str,
    airllm_utils_source: str,
    transformers_glm_source: str,
) -> CompatibilityReceipt:
    findings = _config_findings(config)
    findings.extend(
        _find_remote_code_widening(
            ("airllm/auto_model.py", airllm_auto_model_source),
            ("airllm/airllm_base.py", airllm_base_source),
        )
    )

    ordinary_ok, ordinary_findings = _ordinary_layer_topology(transformers_glm_source, airllm_base_source)
    findings.extend(ordinary_findings)
    grouped_ok, grouped_findings = _grouped_expert_semantics(transformers_glm_source)
    findings.extend(grouped_findings)
    module_hook_assumption, slice_loader, loader_findings = _airllm_expert_assumptions(
        airllm_base_source, airllm_utils_source
    )
    findings.extend(loader_findings)

    architecture_fatal = any(
        f.code.startswith("GLM53_")
        and f.code.endswith(("MISMATCH", "UNPROVEN"))
        and f.code not in {"GLM53_ORDINARY_LAYER_TOPOLOGY_UNPROVEN"}
        for f in findings
    )
    security_block = any(f.code == "AIRLLM_REMOTE_CODE_SECURITY_BLOCK" for f in findings)

    # Stock v3.3 cannot exploit grouped GLM experts: the model exposes 3-D expert
    # tensors while AirLLM hooks individual expert Modules and reads whole tensor keys.
    grouped_stream_gap = grouped_ok and module_hook_assumption and not slice_loader
    if grouped_stream_gap:
        findings.append(
            Finding(
                "GLM53_GROUPED_TENSOR_EXPERT_ADAPTER_REQUIRED",
                "GlmMoeDsaExperts stores 256 experts in 3-D projection tensors; AirLLM v3.3 hooks experts_container[i] modules",
            )
        )

    quant = config.get("quantization_config") or {}
    fp8_metadata_ok = (
        quant.get("quant_method") == "fp8"
        and quant.get("fmt") == EXPECTED_FP8_FORMAT
        and tuple(quant.get("weight_block_size") or ()) == EXPECTED_FP8_BLOCK
        and quant.get("activation_scheme") == "dynamic"
    )

    adapter_spec = {
        "keep_transformers_native_glm_router_attention_dsa": True,
        "airllm_source_gate_pr": 311,
        "transformers_pin": EXPECTED_TRANSFORMERS,
        "expert_storage": "GROUPED_3D_TENSORS",
        "expert_dispatch_extension": "Transformers ExpertsInterface / FP8ExpertsInterface",
        "required_custom_impl_name": "aura_airllm_streaming",
        "required_stream_point": "GlmMoeDsaExperts.forward(hidden_states, top_k_index, top_k_weights)",
        "required_slice_loader": "safetensors safe_open.get_slice first-axis expert slices",
        "required_tensor_families": [
            "mlp.experts.gate_up_proj",
            "mlp.experts.gate_up_proj_scale_inv",
            "mlp.experts.down_proj",
            "mlp.experts.down_proj_scale_inv",
        ],
        "routing_law": "load unique experts selected by top_k_index for this forward; never prune the available 256-expert set",
        "fp8_law": "preserve FP8 e4m3 payload+scale slices; execute through pinned Transformers FP8 expert linear semantics; do not cast packed/FP8 payload to bf16 before kernel",
        "lifecycle": "slice load -> device -> selected expert compute -> accumulate routed weights -> release slice -> next layer",
        "tokenizer_law": "pinned tokenizer/apply_chat_template with trust_remote_code=False; no handwritten GLM prompt grammar",
        "tests_required": [
            "remote-code hard false",
            "grouped expert 3-D source shape",
            "noncontiguous expert slice read",
            "FP8 weight+scale slice alignment",
            "top_k_index selects only routed experts",
            "different routed set changes loaded expert IDs",
            "all 256 experts remain addressable",
            "one sparse layer output matches full-resident reference fixture",
            "release returns expert slice tensors to nonresident state",
            "stale source/config/hash fails closed",
        ],
    }

    if architecture_fatal:
        status = "BLOCKED_ARCHITECTURE"
    elif security_block or grouped_stream_gap or not ordinary_ok:
        status = "PARTIAL"
    else:
        # This static probe still cannot prove runtime equivalence by itself.
        status = "PARTIAL"
        findings.append(Finding("GLM53_RUNTIME_EQUIVALENCE_UNPROVEN", "requires architecture-representative tiny fixture"))

    return CompatibilityReceipt(
        schema=SCHEMA,
        status=status,
        architecture=(config.get("architectures") or [None])[0],
        model_type=config.get("model_type"),
        config_digest=_canonical_digest(config),
        source_digests={
            "airllm_auto_model": _text_digest(airllm_auto_model_source),
            "airllm_base": _text_digest(airllm_base_source),
            "airllm_utils": _text_digest(airllm_utils_source),
            "transformers_glm": _text_digest(transformers_glm_source),
        },
        ordinary_layer_streaming="STATIC_COMPATIBLE" if ordinary_ok else "UNPROVEN",
        routed_expert_streaming="ADAPTER_REQUIRED" if grouped_stream_gap else "UNPROVEN",
        remote_code_membrane="BLOCKED_STOCK_SOURCE" if security_block else "NO_LITERAL_TRUE_FOUND",
        fp8_path="METADATA_MATCH" if fp8_metadata_ok else "MISMATCH",
        g2_admitted=False,
        adapter_spec=adapter_spec,
        findings=tuple(findings),
    )


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="strict")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--airllm-auto-model", required=True)
    parser.add_argument("--airllm-base", required=True)
    parser.add_argument("--airllm-utils", required=True)
    parser.add_argument("--transformers-glm-source", required=True)
    args = parser.parse_args()

    config = json.loads(_read(args.config))
    receipt = analyze(
        config,
        airllm_auto_model_source=_read(args.airllm_auto_model),
        airllm_base_source=_read(args.airllm_base),
        airllm_utils_source=_read(args.airllm_utils),
        transformers_glm_source=_read(args.transformers_glm_source),
    )
    print(json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":")))
    return 0 if receipt.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
