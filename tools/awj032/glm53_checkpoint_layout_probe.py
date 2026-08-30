"""Metadata-only GLM-5.3 checkpoint layout probe for AWJ032 G1.

This module is deliberately pure: it does not import Transformers, open model
weights, contact Hugging Face, or authorize any checkpoint effect. It turns a
pinned config + safetensors weight map (+ optional shard-size map) into a
fail-closed compatibility report that the packed-expert pager can consume.

The runtime model may expose packed expert Parameters even when the physical
checkpoint is stored differently. This probe keeps those two planes separate.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

SCHEMA = "GLM53CheckpointLayoutProbeV1"
_EXPERT_RE_TEMPLATE = r"^model\.layers\.{layer}\.mlp\.experts\.(\d+)\.(gate_proj|up_proj|down_proj)(?:\.weight)?$"


class ProbeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _int(config: Mapping[str, Any], key: str) -> int:
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProbeError("INVALID_CONFIG_INTEGER", key)
    return value


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class Geometry:
    num_experts: int
    hidden_size: int
    intermediate_size: int
    gate_up_elements: int
    down_elements: int
    gate_up_fp8_bytes: int
    down_fp8_bytes: int
    gate_up_block_scale_elements: int
    down_block_scale_elements: int
    block_size: tuple[int, int]

    @property
    def total_fp8_weight_bytes(self) -> int:
        return self.gate_up_fp8_bytes + self.down_fp8_bytes

    @property
    def candidate_fp32_scale_bank_bytes(self) -> int:
        # Config-derived estimate only. Header/index evidence must establish the
        # actual scale dtype/layout before it can be used as checkpoint truth.
        return 4 * (self.gate_up_block_scale_elements + self.down_block_scale_elements)

    def to_dict(self) -> dict[str, Any]:
        return {
            "num_experts": self.num_experts,
            "hidden_size": self.hidden_size,
            "intermediate_size": self.intermediate_size,
            "gate_up_elements": self.gate_up_elements,
            "down_elements": self.down_elements,
            "gate_up_fp8_bytes": self.gate_up_fp8_bytes,
            "down_fp8_bytes": self.down_fp8_bytes,
            "total_fp8_weight_bytes": self.total_fp8_weight_bytes,
            "block_size": list(self.block_size),
            "gate_up_block_scale_elements": self.gate_up_block_scale_elements,
            "down_block_scale_elements": self.down_block_scale_elements,
            "candidate_fp32_scale_bank_bytes": self.candidate_fp32_scale_bank_bytes,
            "scale_estimate_is_header_proof": False,
        }


def geometry_from_config(config: Mapping[str, Any]) -> Geometry:
    experts = _int(config, "n_routed_experts")
    hidden = _int(config, "hidden_size")
    intermediate = _int(config, "moe_intermediate_size")
    quant = config.get("quantization_config")
    if not isinstance(quant, Mapping):
        raise ProbeError("QUANTIZATION_CONFIG_REQUIRED")
    if str(quant.get("quant_method", "")).lower() != "fp8":
        raise ProbeError("FP8_QUANTIZATION_REQUIRED")
    raw_block = quant.get("weight_block_size")
    if (
        not isinstance(raw_block, Sequence)
        or isinstance(raw_block, (str, bytes))
        or len(raw_block) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in raw_block)
    ):
        raise ProbeError("INVALID_FP8_BLOCK_SIZE")
    bm, bn = int(raw_block[0]), int(raw_block[1])

    gate_rows = 2 * intermediate
    gate_cols = hidden
    down_rows = hidden
    down_cols = intermediate
    gate_elems = experts * gate_rows * gate_cols
    down_elems = experts * down_rows * down_cols
    gate_scale = experts * math.ceil(gate_rows / bm) * math.ceil(gate_cols / bn)
    down_scale = experts * math.ceil(down_rows / bm) * math.ceil(down_cols / bn)
    return Geometry(
        num_experts=experts,
        hidden_size=hidden,
        intermediate_size=intermediate,
        gate_up_elements=gate_elems,
        down_elements=down_elems,
        gate_up_fp8_bytes=gate_elems,  # e4m3 is one byte/element
        down_fp8_bytes=down_elems,
        gate_up_block_scale_elements=gate_scale,
        down_block_scale_elements=down_scale,
        block_size=(bm, bn),
    )


def _layer_prefix(layer: int) -> str:
    return f"model.layers.{layer}.mlp.experts."


def _packed_candidates(layer: int, role: str) -> tuple[str, ...]:
    base = f"model.layers.{layer}.mlp.experts.{role}"
    return (base, f"{base}.weight")


def _scale_keys_for_layer(weight_map: Mapping[str, str], layer: int) -> list[str]:
    prefix = _layer_prefix(layer)
    return sorted(
        key
        for key in weight_map
        if key.startswith(prefix)
        and any(token in key.lower() for token in ("scale", "amax", "quant"))
    )


def _per_expert_projection_coverage(
    weight_map: Mapping[str, str], layer: int
) -> dict[int, set[str]]:
    pattern = re.compile(_EXPERT_RE_TEMPLATE.format(layer=layer))
    coverage: dict[int, set[str]] = {}
    for key in weight_map:
        match = pattern.match(key)
        if match:
            eid = int(match.group(1))
            coverage.setdefault(eid, set()).add(match.group(2))
    return coverage


def _all_layer_indices(weight_map: Mapping[str, str]) -> list[int]:
    pattern = re.compile(r"^model\.layers\.(\d+)\.")
    out: set[int] = set()
    for key in weight_map:
        match = pattern.match(key)
        if match:
            out.add(int(match.group(1)))
    return sorted(out)


def classify_layer_layout(
    config: Mapping[str, Any],
    weight_map: Mapping[str, str],
    *,
    layer: int,
    shard_sizes: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    if isinstance(layer, bool) or not isinstance(layer, int) or layer < 0:
        raise ProbeError("INVALID_LAYER")
    geom = geometry_from_config(config)
    experts = geom.num_experts
    keys = set(weight_map)

    gate_key = next((key for key in _packed_candidates(layer, "gate_up_proj") if key in keys), None)
    down_key = next((key for key in _packed_candidates(layer, "down_proj") if key in keys), None)
    coverage = _per_expert_projection_coverage(weight_map, layer)
    complete_ids = sorted(
        eid for eid, roles in coverage.items()
        if roles == {"gate_proj", "up_proj", "down_proj"}
    )
    expected_ids = list(range(experts))
    scale_keys = _scale_keys_for_layer(weight_map, layer)

    reasons: list[str] = []
    if gate_key and down_key:
        layout = "PACKED_PHYSICAL_LAYOUT"
    elif complete_ids == expected_ids:
        layout = "PER_EXPERT_PHYSICAL_LAYOUT"
    elif coverage:
        layout = "PARTIAL_PER_EXPERT_LAYOUT"
        reasons.append("PER_EXPERT_COVERAGE_INCOMPLETE")
    else:
        prefix = _layer_prefix(layer)
        expert_keys = sorted(k for k in keys if k.startswith(prefix))
        if expert_keys:
            layout = "CHUNKED_OR_VENDOR_LAYOUT"
        else:
            layout = "PHYSICAL_LAYOUT_UNRESOLVED"
            reasons.append("EXPERT_KEYS_NOT_FOUND")

    shard_geometry: dict[str, Any] = {
        "checked": bool(shard_sizes),
        "gate_up_assigned_shard": None,
        "assigned_shard_bytes": None,
        "expected_gate_up_fp8_bytes": geom.gate_up_fp8_bytes,
        "monolithic_gate_up_fits_assigned_shard": None,
    }
    if gate_key and shard_sizes:
        shard = weight_map[gate_key]
        size = shard_sizes.get(shard)
        shard_geometry["gate_up_assigned_shard"] = shard
        shard_geometry["assigned_shard_bytes"] = size
        if size is None:
            reasons.append("PACKED_GATE_SHARD_SIZE_UNKNOWN")
        else:
            fits = int(size) >= geom.gate_up_fp8_bytes
            shard_geometry["monolithic_gate_up_fits_assigned_shard"] = fits
            if not fits:
                reasons.append("PACKED_GATE_TENSOR_EXCEEDS_ASSIGNED_SHARD")

    if not scale_keys:
        reasons.append("FP8_SCALE_KEYS_UNRESOLVED")

    return {
        "layer": layer,
        "layout": layout,
        "packed_gate_key": gate_key,
        "packed_down_key": down_key,
        "complete_per_expert_ids": complete_ids,
        "complete_per_expert_count": len(complete_ids),
        "expected_expert_count": experts,
        "scale_keys": scale_keys,
        "scale_key_count": len(scale_keys),
        "shard_geometry": shard_geometry,
        "reasons": sorted(set(reasons)),
        "geometry": geom.to_dict(),
    }


def probe_checkpoint(
    *,
    config: Mapping[str, Any],
    weight_map: Mapping[str, str],
    model_revision: str,
    config_sha256: str,
    index_sha256: str,
    airllm_revision: str,
    security_hard_false_remote_code: bool,
    representative_sparse_layer: int = 3,
    shard_sizes: Mapping[str, int] | None = None,
    observation_time: str | None = None,
) -> dict[str, Any]:
    """Return a deterministic G1 metadata disposition.

    observation_time is receipt metadata only and is excluded from logical_id.
    """
    for name, value in (
        ("model_revision", model_revision),
        ("config_sha256", config_sha256),
        ("index_sha256", index_sha256),
        ("airllm_revision", airllm_revision),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ProbeError("CURRENTNESS_FIELD_REQUIRED", name)

    layer = classify_layer_layout(
        config, weight_map, layer=representative_sparse_layer, shard_sizes=shard_sizes
    )
    hidden_layers = _int(config, "num_hidden_layers")
    layer_indices = _all_layer_indices(weight_map)
    extra_indices = [idx for idx in layer_indices if idx >= hidden_layers]
    mtp_present = hidden_layers in extra_indices

    blockers: list[str] = []
    if not security_hard_false_remote_code:
        blockers.append("AIRLLM_REMOTE_CODE_SECURITY_BLOCK")
    if layer["layout"] == "PHYSICAL_LAYOUT_UNRESOLVED":
        blockers.append("GLM53_EXPERT_PHYSICAL_LAYOUT_UNRESOLVED")
    if layer["layout"] == "PARTIAL_PER_EXPERT_LAYOUT":
        blockers.append("GLM53_EXPERT_PHYSICAL_LAYOUT_PARTIAL")
    if "FP8_SCALE_KEYS_UNRESOLVED" in layer["reasons"]:
        blockers.append("GLM53_FP8_SCALE_LAYOUT_UNRESOLVED")
    if "PACKED_GATE_TENSOR_EXCEEDS_ASSIGNED_SHARD" in layer["reasons"]:
        blockers.append("GLM53_INDEX_GEOMETRY_CONFLICT")
    if mtp_present:
        # Presence is not itself an error, but it requires an explicit non-decoder
        # classification because native runtime decoder count is num_hidden_layers.
        blockers.append("GLM53_MTP_CHECKPOINT_CLASSIFICATION_REQUIRED")

    if "AIRLLM_REMOTE_CODE_SECURITY_BLOCK" in blockers:
        status = "BLOCKED_SECURITY"
    elif any(code.endswith("UNRESOLVED") or code.endswith("PARTIAL") for code in blockers):
        status = "PARTIAL"
    elif "GLM53_INDEX_GEOMETRY_CONFLICT" in blockers:
        status = "BLOCKED_ARCHITECTURE"
    else:
        # Metadata readiness is intentionally below G1 PASS. Numerical tiny-fixture
        # parity and actual header dtypes/shapes are still separately required.
        status = "READY_FOR_HEADER_AND_TINY_FIXTURE"

    logical = {
        "schema": SCHEMA,
        "model_revision": model_revision.strip(),
        "config_sha256": config_sha256.strip(),
        "index_sha256": index_sha256.strip(),
        "airllm_revision": airllm_revision.strip(),
        "security_hard_false_remote_code": bool(security_hard_false_remote_code),
        "representative_sparse_layer": representative_sparse_layer,
        "layer": layer,
        "num_hidden_layers": hidden_layers,
        "checkpoint_layer_indices": layer_indices,
        "extra_checkpoint_layer_indices": extra_indices,
        "mtp_index_present": mtp_present,
        "status": status,
        "blockers": sorted(set(blockers)),
        "large_checkpoint_admitted": False,
        "g2_admitted": False,
        "runtime_execution_proven": False,
        "provider_calls": 0,
    }
    logical_id = _sha(logical)
    return {
        **logical,
        "logical_id": logical_id,
        "observation_time": observation_time,
        "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
    }
