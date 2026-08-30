"""Fail-closed GLM-5.3 checkpoint-layout -> pager binding bridge.

G1A integration only. No checkpoint download/model import/G2 admission. Consumes
GLM53CheckpointLayoutProbeV1 plus the exact pinned weight map. Packed physical
layouts additionally require exact safetensors-header evidence before first-axis
paging is considered lawful; index-proven per-expert layouts reuse the current
PerExpertIndexBinding ABI from the stabilized pager owner.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from tools.awj032.glm53_packed_expert_pager import ExpertSourceBinding
from tools.awj032.glm53_per_expert_index_pager import (
    PerExpertIndexBinding,
    build_standard_glm_per_expert_binding,
)

PROBE_SCHEMA = "GLM53CheckpointLayoutProbeV1"
PLAN_SCHEMA = "GLM53PagerSourcePlanV2"


class LayoutBindingError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LayoutBindingError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _shape(name: str, value: Any) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise LayoutBindingError("HEADER_SHAPE_REQUIRED", name)
    out = []
    for dim in value:
        if isinstance(dim, bool) or not isinstance(dim, int) or dim <= 0:
            raise LayoutBindingError("INVALID_HEADER_SHAPE", name)
        out.append(dim)
    return tuple(out)


def _scale_map(scale_keys: Sequence[Any]) -> dict[str, str]:
    roles: dict[str, str] = {}
    unresolved: list[str] = []
    for raw in scale_keys:
        key = _text("scale_key", raw)
        low = key.lower()
        role = None
        if any(t in low for t in ("scale", "amax", "quant")):
            if "gate_up_proj" in low:
                role = "gate_up_scale"
            elif "down_proj" in low:
                role = "down_scale"
        if role is None:
            unresolved.append(key)
            continue
        if role in roles and roles[role] != key:
            raise LayoutBindingError("FP8_SCALE_ROLE_AMBIGUOUS", role)
        roles[role] = key
    missing = sorted({"gate_up_scale", "down_scale"} - set(roles))
    if missing:
        raise LayoutBindingError("FP8_SCALE_ROLE_UNRESOLVED", ",".join(missing))
    if unresolved:
        raise LayoutBindingError("FP8_SCALE_EXTRA_KEYS_UNCLASSIFIED", ",".join(sorted(unresolved)))
    return roles


@dataclass(frozen=True)
class PagerSourcePlan:
    binding_kind: str
    binding: ExpertSourceBinding | PerExpertIndexBinding
    probe_logical_id: str
    weight_map_digest: str
    header_evidence_digest: str
    source_plan_digest: str
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False
    schema: str = PLAN_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "binding_kind": self.binding_kind,
            "binding_digest": self.binding.digest,
            "probe_logical_id": self.probe_logical_id,
            "weight_map_digest": self.weight_map_digest,
            "header_evidence_digest": self.header_evidence_digest,
            "source_plan_digest": self.source_plan_digest,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }


def _common(report: Mapping[str, Any], *, expected_model_revision: str, expected_index_digest: str):
    if report.get("schema") != PROBE_SCHEMA:
        raise LayoutBindingError("PROBE_SCHEMA_MISMATCH")
    model_revision = _text("model_revision", report.get("model_revision"))
    index_digest = _text("index_sha256", report.get("index_sha256"))
    if model_revision != _text("expected_model_revision", expected_model_revision):
        raise LayoutBindingError("STALE_MODEL_REVISION")
    if index_digest != _text("expected_index_digest", expected_index_digest):
        raise LayoutBindingError("STALE_INDEX_DIGEST")
    logical_id = _text("probe_logical_id", report.get("logical_id"))
    blockers = report.get("blockers", [])
    if not isinstance(blockers, Sequence) or isinstance(blockers, (str, bytes)):
        raise LayoutBindingError("INVALID_PROBE_BLOCKERS")
    if blockers:
        raise LayoutBindingError("PROBE_BLOCKED", ",".join(sorted(str(x) for x in blockers)))
    if report.get("status") != "READY_FOR_HEADER_AND_TINY_FIXTURE":
        raise LayoutBindingError("PROBE_NOT_READY", str(report.get("status")))
    layer = report.get("layer")
    if not isinstance(layer, Mapping):
        raise LayoutBindingError("LAYER_REPORT_REQUIRED")
    return model_revision, index_digest, logical_id, layer


def _finalize(kind: str, binding, logical_id: str, weight_map: Mapping[str, str], header_digest: str) -> PagerSourcePlan:
    weight_map_digest = _digest(dict(sorted((str(k), str(v)) for k, v in weight_map.items())))
    payload = {
        "schema": PLAN_SCHEMA,
        "binding_kind": kind,
        "binding_digest": binding.digest,
        "probe_logical_id": logical_id,
        "weight_map_digest": weight_map_digest,
        "header_evidence_digest": header_digest,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return PagerSourcePlan(kind, binding, logical_id, weight_map_digest, header_digest, _digest(payload))


def compile_pager_source_plan(
    report: Mapping[str, Any],
    *,
    weight_map: Mapping[str, str],
    headers: Mapping[str, Mapping[str, Any]] | None,
    expected_model_revision: str,
    expected_index_digest: str,
) -> PagerSourcePlan:
    model_revision, index_digest, logical_id, layer = _common(
        report,
        expected_model_revision=expected_model_revision,
        expected_index_digest=expected_index_digest,
    )
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise LayoutBindingError("WEIGHT_MAP_REQUIRED")

    layout = _text("layout", layer.get("layout"))
    geom = layer.get("geometry")
    if not isinstance(geom, Mapping):
        raise LayoutBindingError("GEOMETRY_REQUIRED")
    num_experts = geom.get("num_experts")
    layer_no = layer.get("layer")
    if isinstance(num_experts, bool) or not isinstance(num_experts, int) or num_experts <= 0:
        raise LayoutBindingError("INVALID_EXPERT_COUNT")
    if isinstance(layer_no, bool) or not isinstance(layer_no, int) or layer_no < 0:
        raise LayoutBindingError("INVALID_LAYER_ID")

    if layout == "PER_EXPERT_PHYSICAL_LAYOUT":
        binding = build_standard_glm_per_expert_binding(
            weight_map=weight_map,
            model_revision=model_revision,
            index_digest=index_digest,
            layer_id=f"model.layers.{layer_no}",
            num_experts=num_experts,
            require_fp8_scales=True,
        )
        return _finalize("PER_EXPERT_INDEX", binding, logical_id, weight_map, "INDEX_PROVEN_NO_HEADER_BINDING")

    if layout == "PARTIAL_PER_EXPERT_LAYOUT":
        raise LayoutBindingError("PER_EXPERT_LAYOUT_PARTIAL")
    if layout == "CHUNKED_OR_VENDOR_LAYOUT":
        raise LayoutBindingError("VENDOR_LAYOUT_ADAPTER_REQUIRED")
    if layout == "PHYSICAL_LAYOUT_UNRESOLVED":
        raise LayoutBindingError("EXPERT_PHYSICAL_LAYOUT_UNRESOLVED")
    if layout != "PACKED_PHYSICAL_LAYOUT":
        raise LayoutBindingError("UNSUPPORTED_LAYOUT", layout)

    gate_key = _text("packed_gate_key", layer.get("packed_gate_key"))
    down_key = _text("packed_down_key", layer.get("packed_down_key"))
    scale_keys = layer.get("scale_keys")
    if not isinstance(scale_keys, Sequence) or isinstance(scale_keys, (str, bytes)):
        raise LayoutBindingError("SCALE_KEYS_REQUIRED")
    scale_map = _scale_map(scale_keys)
    block = _shape("block_size", geom.get("block_size"))
    if len(block) != 2:
        raise LayoutBindingError("INVALID_FP8_BLOCK_SIZE")
    if not isinstance(headers, Mapping):
        raise LayoutBindingError("PACKED_HEADER_EVIDENCE_REQUIRED")

    weight_keys = {gate_key, down_key}
    required = [gate_key, down_key, *scale_map.values()]
    evidence: dict[str, Any] = {}
    for key in required:
        assigned = weight_map.get(key)
        if not isinstance(assigned, str) or not assigned:
            raise LayoutBindingError("WEIGHT_MAP_KEY_MISSING", key)
        raw = headers.get(key)
        if not isinstance(raw, Mapping):
            raise LayoutBindingError("HEADER_EVIDENCE_REQUIRED", key)
        shape = _shape(key, raw.get("shape"))
        shard = _text("header_shard", raw.get("shard"))
        dtype = _text("header_dtype", raw.get("dtype"))
        hd = _text("header_digest", raw.get("header_digest"))
        if shape[0] != num_experts:
            raise LayoutBindingError("EXPERT_AXIS_HEADER_MISMATCH", key)
        if shard != assigned:
            raise LayoutBindingError("HEADER_SHARD_BINDING_MISMATCH", key)
        if key in weight_keys and "E4M3" not in dtype.upper():
            raise LayoutBindingError("PACKED_WEIGHT_DTYPE_MISMATCH", f"{key}:{dtype}")
        evidence[key] = {"shape": list(shape), "shard": shard, "dtype": dtype, "header_digest": hd}

    header_digest = _digest(dict(sorted(evidence.items())))
    weight_map_digest = _digest(dict(sorted((str(k), str(v)) for k, v in weight_map.items())))
    binding = ExpertSourceBinding(
        model_revision=model_revision,
        index_digest=index_digest,
        layer_id=f"model.layers.{layer_no}.mlp.experts",
        num_experts=num_experts,
        tensor_map={"gate_up": gate_key, "down": down_key},
        scale_map=scale_map,
        representation=(
            f"GLM53_PACKED_FP8_BLOCK_{block[0]}x{block[1]}:"
            f"probe={logical_id}:headers={header_digest}:weight_map={weight_map_digest}"
        ),
    )
    return _finalize("PACKED_FIRST_AXIS", binding, logical_id, weight_map, header_digest)
