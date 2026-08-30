"""Fail-closed bridge from GLM-5.3 checkpoint-layout evidence to pager bindings.

G1A integration only. This module does not open checkpoints, import the model,
or admit G2. It consumes a GLM53CheckpointLayoutProbeV1 report plus the exact
pinned index weight-map and safetensors-header evidence, and constructs an
ExpertSourceBinding only when the physical representation is proven compatible
with the packed first-axis pager.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence

from tools.awj032.glm53_packed_expert_pager import ExpertSourceBinding


PROBE_SCHEMA = "GLM53CheckpointLayoutProbeV1"
PLAN_SCHEMA = "GLM53PagerSourcePlanV1"


class LayoutBindingError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LayoutBindingError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _shape(name: str, value: Any) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise LayoutBindingError("HEADER_SHAPE_REQUIRED", name)
    out: list[int] = []
    for dim in value:
        if isinstance(dim, bool) or not isinstance(dim, int) or dim <= 0:
            raise LayoutBindingError("INVALID_HEADER_SHAPE", name)
        out.append(dim)
    return tuple(out)


@dataclass(frozen=True)
class HeaderTensorEvidence:
    key: str
    shape: tuple[int, ...]
    dtype: str
    shard: str
    header_digest: str

    @classmethod
    def from_mapping(cls, key: str, raw: Mapping[str, Any]) -> "HeaderTensorEvidence":
        return cls(
            key=_text("header_key", key),
            shape=_shape(key, raw.get("shape")),
            dtype=_text("header_dtype", raw.get("dtype")),
            shard=_text("header_shard", raw.get("shard")),
            header_digest=_text("header_digest", raw.get("header_digest")),
        )


@dataclass(frozen=True)
class PagerSourcePlan:
    binding: ExpertSourceBinding
    probe_logical_id: str
    header_evidence_digest: str
    weight_map_digest: str
    source_plan_digest: str
    disposition: str = "PACKED_PAGER_BINDING_READY"
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False
    schema: str = PLAN_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "disposition": self.disposition,
            "binding_digest": self.binding.digest,
            "probe_logical_id": self.probe_logical_id,
            "header_evidence_digest": self.header_evidence_digest,
            "weight_map_digest": self.weight_map_digest,
            "source_plan_digest": self.source_plan_digest,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }


def _role_for_scale_key(key: str) -> str | None:
    lower = key.lower()
    if not any(token in lower for token in ("scale", "amax", "quant")):
        return None
    if "gate_up_proj" in lower:
        return "gate_up_scale"
    if "down_proj" in lower:
        return "down_scale"
    return None


def _scale_map(scale_keys: Sequence[Any]) -> dict[str, str]:
    roles: dict[str, str] = {}
    unresolved: list[str] = []
    for raw in scale_keys:
        key = _text("scale_key", raw)
        role = _role_for_scale_key(key)
        if role is None:
            unresolved.append(key)
            continue
        if role in roles and roles[role] != key:
            raise LayoutBindingError("FP8_SCALE_ROLE_AMBIGUOUS", role)
        roles[role] = key
    required = {"gate_up_scale", "down_scale"}
    missing = sorted(required - set(roles))
    if missing:
        detail = ",".join(missing)
        if unresolved:
            detail += f";unresolved={','.join(sorted(unresolved))}"
        raise LayoutBindingError("FP8_SCALE_ROLE_UNRESOLVED", detail)
    if unresolved:
        raise LayoutBindingError("FP8_SCALE_EXTRA_KEYS_UNCLASSIFIED", ",".join(sorted(unresolved)))
    return roles


def _layout_residual(layout: str) -> None:
    if layout == "PER_EXPERT_PHYSICAL_LAYOUT":
        raise LayoutBindingError("PER_EXPERT_BACKEND_REQUIRED")
    if layout == "PARTIAL_PER_EXPERT_LAYOUT":
        raise LayoutBindingError("PER_EXPERT_LAYOUT_PARTIAL")
    if layout == "CHUNKED_OR_VENDOR_LAYOUT":
        raise LayoutBindingError("VENDOR_LAYOUT_ADAPTER_REQUIRED")
    if layout == "PHYSICAL_LAYOUT_UNRESOLVED":
        raise LayoutBindingError("EXPERT_PHYSICAL_LAYOUT_UNRESOLVED")
    if layout != "PACKED_PHYSICAL_LAYOUT":
        raise LayoutBindingError("UNSUPPORTED_LAYOUT", layout)


def compile_pager_source_plan(
    report: Mapping[str, Any],
    *,
    weight_map: Mapping[str, str],
    headers: Mapping[str, Mapping[str, Any]],
    expected_model_revision: str,
    expected_index_digest: str,
) -> PagerSourcePlan:
    """Compile verified metadata/header evidence into the PR #338 pager ABI.

    An index key alone cannot prove that expert-axis row slicing is lawful. Each
    required weight/scale tensor must have exact header evidence whose first
    dimension is the routed-expert count and whose shard matches the pinned
    weight-map assignment.
    """
    if report.get("schema") != PROBE_SCHEMA:
        raise LayoutBindingError("PROBE_SCHEMA_MISMATCH")
    model_revision = _text("model_revision", report.get("model_revision"))
    index_digest = _text("index_sha256", report.get("index_sha256"))
    if model_revision != _text("expected_model_revision", expected_model_revision):
        raise LayoutBindingError("STALE_MODEL_REVISION")
    if index_digest != _text("expected_index_digest", expected_index_digest):
        raise LayoutBindingError("STALE_INDEX_DIGEST")
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise LayoutBindingError("WEIGHT_MAP_REQUIRED")

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
    layout = _text("layout", layer.get("layout"))
    _layout_residual(layout)

    gate_key = _text("packed_gate_key", layer.get("packed_gate_key"))
    down_key = _text("packed_down_key", layer.get("packed_down_key"))
    if gate_key == down_key:
        raise LayoutBindingError("PACKED_WEIGHT_KEYS_COLLIDE")
    scale_keys = layer.get("scale_keys")
    if not isinstance(scale_keys, Sequence) or isinstance(scale_keys, (str, bytes)):
        raise LayoutBindingError("SCALE_KEYS_REQUIRED")
    scale_map = _scale_map(scale_keys)

    geom = layer.get("geometry")
    if not isinstance(geom, Mapping):
        raise LayoutBindingError("GEOMETRY_REQUIRED")
    num_experts = geom.get("num_experts")
    if isinstance(num_experts, bool) or not isinstance(num_experts, int) or num_experts <= 0:
        raise LayoutBindingError("INVALID_EXPERT_COUNT")
    block = _shape("block_size", geom.get("block_size"))
    if len(block) != 2:
        raise LayoutBindingError("INVALID_FP8_BLOCK_SIZE")

    required_keys = [gate_key, down_key, *scale_map.values()]
    evidence: dict[str, HeaderTensorEvidence] = {}
    for key in required_keys:
        assigned = weight_map.get(key)
        if not isinstance(assigned, str) or not assigned:
            raise LayoutBindingError("WEIGHT_MAP_KEY_MISSING", key)
        raw = headers.get(key)
        if not isinstance(raw, Mapping):
            raise LayoutBindingError("HEADER_EVIDENCE_REQUIRED", key)
        item = HeaderTensorEvidence.from_mapping(key, raw)
        if item.shape[0] != num_experts:
            raise LayoutBindingError("EXPERT_AXIS_HEADER_MISMATCH", key)
        if assigned != item.shard:
            raise LayoutBindingError("HEADER_SHARD_BINDING_MISMATCH", key)
        evidence[key] = item

    evidence_payload = {
        key: {
            "shape": list(item.shape),
            "dtype": item.dtype,
            "shard": item.shard,
            "header_digest": item.header_digest,
        }
        for key, item in sorted(evidence.items())
    }
    header_digest = _digest(evidence_payload)
    weight_map_digest = _digest(dict(sorted((str(k), str(v)) for k, v in weight_map.items())))
    layer_no = layer.get("layer")
    if isinstance(layer_no, bool) or not isinstance(layer_no, int) or layer_no < 0:
        raise LayoutBindingError("INVALID_LAYER_ID")
    representation = (
        f"GLM53_PACKED_FP8_BLOCK_{block[0]}x{block[1]}:"
        f"probe={logical_id}:headers={header_digest}:weight_map={weight_map_digest}"
    )
    binding = ExpertSourceBinding(
        model_revision=model_revision,
        index_digest=index_digest,
        layer_id=f"model.layers.{layer_no}.mlp.experts",
        num_experts=num_experts,
        tensor_map={"gate_up": gate_key, "down": down_key},
        scale_map=scale_map,
        representation=representation,
    )
    plan_payload = {
        "schema": PLAN_SCHEMA,
        "binding_digest": binding.digest,
        "probe_logical_id": logical_id,
        "header_evidence_digest": header_digest,
        "weight_map_digest": weight_map_digest,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return PagerSourcePlan(
        binding=binding,
        probe_logical_id=logical_id,
        header_evidence_digest=header_digest,
        weight_map_digest=weight_map_digest,
        source_plan_digest=_digest(plan_payload),
    )
