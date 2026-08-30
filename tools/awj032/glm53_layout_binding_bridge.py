"""Fail-closed GLM-5.3 checkpoint-layout -> pager binding bridge.

G1A integration only. No checkpoint download/model import/G2 admission. Consumes
GLM53CheckpointLayoutProbeV1 plus the exact pinned weight map. Packed physical
layouts require exact safetensors-header evidence before first-axis paging is
considered lawful. Per-expert layouts additionally require one exact bounded
GLM53SafetensorsHeaderEvidenceV1 canary plus an independently supplied expected
W2 observation identity before a W3 source plan can be emitted; that
representative canary is never generalized to all experts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from tools.awj032.glm53_packed_expert_pager import ExpertSourceBinding
from tools.awj032.glm53_per_expert_index_pager import (
    PerExpertIndexBinding,
    build_standard_glm_per_expert_binding,
)

PROBE_SCHEMA = "GLM53CheckpointLayoutProbeV1"
PLAN_SCHEMA = "GLM53PagerSourcePlanV2"
PER_EXPERT_HEADER_SCHEMA = "GLM53SafetensorsHeaderEvidenceV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_RECEIPT_RE = re.compile(r"^[0-9a-f]{40}$")


class LayoutBindingError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _transport_receipt_digest(value: Any) -> str:
    body = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.blake2b(body, digest_size=20).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LayoutBindingError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _sha256(name: str, value: Any) -> str:
    out = _text(name, value).lower()
    if not _SHA256_RE.fullmatch(out):
        raise LayoutBindingError("HEADER_SHA256_INVALID", name)
    return out


def _receipt(name: str, value: Any, invalid_code: str) -> str:
    out = _text(name, value).lower()
    if not _RECEIPT_RE.fullmatch(out):
        raise LayoutBindingError(invalid_code)
    return out


def _shape(name: str, value: Any) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise LayoutBindingError("HEADER_SHAPE_REQUIRED", name)
    out = []
    for dim in value:
        if isinstance(dim, bool) or not isinstance(dim, int) or dim <= 0:
            raise LayoutBindingError("INVALID_HEADER_SHAPE", name)
        out.append(dim)
    return tuple(out)


def _offsets(name: str, value: Any) -> tuple[int, int]:
    if (
        not isinstance(value, Sequence)
        or isinstance(value, (str, bytes))
        or len(value) != 2
        or any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in value)
        or value[1] <= value[0]
    ):
        raise LayoutBindingError("INVALID_HEADER_OFFSETS", name)
    return int(value[0]), int(value[1])


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
    header_receipt_digest: str | None = None
    header_observation_repo_id: str | None = None
    official_w2_observation_bound: bool = False
    representative_header_bound: bool = False
    representative_layer: int | None = None
    representative_expert: int | None = None
    all_experts_header_uniformity_proven: bool = False
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
            "header_receipt_digest": self.header_receipt_digest,
            "header_observation_repo_id": self.header_observation_repo_id,
            "official_w2_observation_bound": self.official_w2_observation_bound,
            "source_plan_digest": self.source_plan_digest,
            "representative_header_bound": self.representative_header_bound,
            "representative_layer": self.representative_layer,
            "representative_expert": self.representative_expert,
            "all_experts_header_uniformity_proven": False,
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


def _finalize(
    kind: str,
    binding: Any,
    logical_id: str,
    weight_map: Mapping[str, str],
    header_digest: str,
    *,
    header_receipt_digest: str | None = None,
    header_observation_repo_id: str | None = None,
    official_w2_observation_bound: bool = False,
    representative_header_bound: bool = False,
    representative_layer: int | None = None,
    representative_expert: int | None = None,
) -> PagerSourcePlan:
    weight_map_digest = _digest(dict(sorted((str(k), str(v)) for k, v in weight_map.items())))
    payload = {
        "schema": PLAN_SCHEMA,
        "binding_kind": kind,
        "binding_digest": binding.digest,
        "probe_logical_id": logical_id,
        "weight_map_digest": weight_map_digest,
        "header_evidence_digest": header_digest,
        "header_receipt_digest": header_receipt_digest,
        "header_observation_repo_id": header_observation_repo_id,
        "official_w2_observation_bound": official_w2_observation_bound,
        "representative_header_bound": representative_header_bound,
        "representative_layer": representative_layer,
        "representative_expert": representative_expert,
        "all_experts_header_uniformity_proven": False,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
    }
    return PagerSourcePlan(
        binding_kind=kind,
        binding=binding,
        probe_logical_id=logical_id,
        weight_map_digest=weight_map_digest,
        header_evidence_digest=header_digest,
        source_plan_digest=_digest(payload),
        header_receipt_digest=header_receipt_digest,
        header_observation_repo_id=header_observation_repo_id,
        official_w2_observation_bound=official_w2_observation_bound,
        representative_header_bound=representative_header_bound,
        representative_layer=representative_layer,
        representative_expert=representative_expert,
    )


def _per_expert_header_digest(
    evidence: Mapping[str, Any] | None,
    *,
    weight_map: Mapping[str, str],
    model_revision: str,
    index_digest: str,
    layer_no: int,
    num_experts: int,
    block_size: tuple[int, int],
    expected_repo_id: str | None,
    expected_receipt_digest: str | None,
) -> tuple[str, int, str, str]:
    expected_repo = _text("expected_per_expert_header_repo_id", expected_repo_id)
    expected_receipt = _receipt(
        "expected_per_expert_header_receipt_digest",
        expected_receipt_digest,
        "PER_EXPERT_HEADER_EXPECTED_RECEIPT_INVALID",
    )
    if not isinstance(evidence, Mapping):
        raise LayoutBindingError("PER_EXPERT_HEADER_EVIDENCE_REQUIRED")
    if evidence.get("schema") != PER_EXPERT_HEADER_SCHEMA:
        raise LayoutBindingError("PER_EXPERT_HEADER_SCHEMA_MISMATCH")
    if _text("header_model_revision", evidence.get("model_revision")) != model_revision:
        raise LayoutBindingError("PER_EXPERT_HEADER_MODEL_REVISION_MISMATCH")
    if _text("header_index_sha256", evidence.get("index_sha256")) != index_digest:
        raise LayoutBindingError("PER_EXPERT_HEADER_INDEX_MISMATCH")
    repo_id = _text("header_repo_id", evidence.get("repo_id"))
    if repo_id != expected_repo:
        raise LayoutBindingError(
            "PER_EXPERT_HEADER_OFFICIAL_REPO_MISMATCH",
            f"expected={expected_repo},observed={repo_id}",
        )
    index_size = evidence.get("index_size_bytes")
    if isinstance(index_size, bool) or not isinstance(index_size, int) or index_size <= 0:
        raise LayoutBindingError("PER_EXPERT_HEADER_INDEX_SIZE_INVALID")
    selected_layer = evidence.get("selected_layer")
    selected_expert = evidence.get("selected_expert")
    if isinstance(selected_layer, bool) or not isinstance(selected_layer, int) or selected_layer != layer_no:
        raise LayoutBindingError("PER_EXPERT_HEADER_LAYER_MISMATCH")
    if (
        isinstance(selected_expert, bool)
        or not isinstance(selected_expert, int)
        or selected_expert < 0
        or selected_expert >= num_experts
    ):
        raise LayoutBindingError("PER_EXPERT_HEADER_EXPERT_INVALID")
    if type(evidence.get("payload_bytes_read")) is not int or evidence.get("payload_bytes_read") != 0:
        raise LayoutBindingError("PER_EXPERT_HEADER_PAYLOAD_EFFECT_FORBIDDEN")
    if evidence.get("g2_admitted") is not False or evidence.get("runtime_executed") is not False or evidence.get("authority") is not False:
        raise LayoutBindingError("PER_EXPERT_HEADER_AUTHORITY_WIDENING_FORBIDDEN")

    entries = evidence.get("entries")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)) or len(entries) != 6:
        raise LayoutBindingError("PER_EXPERT_HEADER_SIX_ENTRIES_REQUIRED")
    prefix = f"model.layers.{layer_no}.mlp.experts.{selected_expert}."
    suffixes = (
        "gate_proj.weight",
        "gate_proj.weight_scale_inv",
        "up_proj.weight",
        "up_proj.weight_scale_inv",
        "down_proj.weight",
        "down_proj.weight_scale_inv",
    )
    required_keys = tuple(prefix + suffix for suffix in suffixes)
    normalized_entries: list[dict[str, Any]] = []
    shapes: dict[str, tuple[int, ...]] = {}
    dtypes: dict[str, str] = {}
    for expected_key, raw in zip(required_keys, entries):
        if not isinstance(raw, Mapping):
            raise LayoutBindingError("PER_EXPERT_HEADER_ENTRY_INVALID", expected_key)
        key = _text("tensor_key", raw.get("tensor_key"))
        if key != expected_key:
            raise LayoutBindingError("PER_EXPERT_HEADER_KEY_MISMATCH", f"expected={expected_key},observed={key}")
        shard = _text("shard_name", raw.get("shard_name"))
        if weight_map.get(key) != shard:
            raise LayoutBindingError("PER_EXPERT_HEADER_SHARD_MISMATCH", key)
        dtype = _text("dtype", raw.get("dtype"))
        shape = _shape(key, raw.get("shape"))
        offsets = _offsets(key, raw.get("data_offsets"))
        header_sha = _sha256(key, raw.get("header_sha256"))
        normalized_entries.append(
            {
                "tensor_key": key,
                "shard_name": shard,
                "dtype": dtype,
                "shape": list(shape),
                "data_offsets": list(offsets),
                "header_sha256": header_sha,
            }
        )
        shapes[key] = shape
        dtypes[key] = dtype.upper()

    gate = required_keys[0]
    gate_scale = required_keys[1]
    up = required_keys[2]
    up_scale = required_keys[3]
    down = required_keys[4]
    down_scale = required_keys[5]
    if "E4M3" not in dtypes[gate] or "E4M3" not in dtypes[up] or "E4M3" not in dtypes[down]:
        raise LayoutBindingError("PER_EXPERT_HEADER_WEIGHT_DTYPE_MISMATCH")
    if dtypes[gate_scale] != "F32" or dtypes[up_scale] != "F32" or dtypes[down_scale] != "F32":
        raise LayoutBindingError("PER_EXPERT_HEADER_SCALE_DTYPE_MISMATCH")
    if len(shapes[gate]) != 2 or shapes[up] != shapes[gate] or shapes[down] != tuple(reversed(shapes[gate])):
        raise LayoutBindingError("PER_EXPERT_HEADER_WEIGHT_SHAPE_MISMATCH")
    rows, cols = shapes[gate]
    br, bc = block_size
    expected_forward_scale = ((rows + br - 1) // br, (cols + bc - 1) // bc)
    expected_down_scale = ((cols + br - 1) // br, (rows + bc - 1) // bc)
    if shapes[gate_scale] != expected_forward_scale or shapes[up_scale] != expected_forward_scale:
        raise LayoutBindingError("PER_EXPERT_HEADER_FORWARD_SCALE_SHAPE_MISMATCH")
    if shapes[down_scale] != expected_down_scale:
        raise LayoutBindingError("PER_EXPERT_HEADER_DOWN_SCALE_SHAPE_MISMATCH")

    normalized_body = {
        "repo_id": repo_id,
        "model_revision": model_revision,
        "index_sha256": index_digest,
        "index_size_bytes": index_size,
        "selected_layer": selected_layer,
        "selected_expert": selected_expert,
        "entries": normalized_entries,
        "payload_bytes_read": 0,
        "g2_admitted": False,
        "runtime_executed": False,
        "authority": False,
        "schema": PER_EXPERT_HEADER_SCHEMA,
    }
    receipt = _receipt(
        "receipt_digest",
        evidence.get("receipt_digest"),
        "PER_EXPERT_HEADER_RECEIPT_INVALID",
    )
    observed_receipt = _transport_receipt_digest(normalized_body)
    if receipt != observed_receipt:
        raise LayoutBindingError(
            "PER_EXPERT_HEADER_RECEIPT_MISMATCH",
            f"claimed={receipt},observed={observed_receipt}",
        )
    if observed_receipt != expected_receipt:
        raise LayoutBindingError(
            "PER_EXPERT_HEADER_OFFICIAL_OBSERVATION_MISMATCH",
            f"expected_official={expected_receipt},observed_candidate={observed_receipt}",
        )
    return (
        _digest(
            {
                "official_observation_repo_id": expected_repo,
                "official_transport_receipt_digest": expected_receipt,
                "evidence": normalized_body,
            }
        ),
        selected_expert,
        expected_receipt,
        expected_repo,
    )


def compile_pager_source_plan(
    report: Mapping[str, Any],
    *,
    weight_map: Mapping[str, str],
    headers: Mapping[str, Mapping[str, Any]] | None,
    expected_model_revision: str,
    expected_index_digest: str,
    per_expert_header_evidence: Mapping[str, Any] | None = None,
    expected_per_expert_header_repo_id: str | None = None,
    expected_per_expert_header_receipt_digest: str | None = None,
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
        block = _shape("block_size", geom.get("block_size"))
        if len(block) != 2:
            raise LayoutBindingError("INVALID_FP8_BLOCK_SIZE")
        header_digest, selected_expert, receipt_digest, observation_repo = _per_expert_header_digest(
            per_expert_header_evidence,
            weight_map=weight_map,
            model_revision=model_revision,
            index_digest=index_digest,
            layer_no=layer_no,
            num_experts=num_experts,
            block_size=(block[0], block[1]),
            expected_repo_id=expected_per_expert_header_repo_id,
            expected_receipt_digest=expected_per_expert_header_receipt_digest,
        )
        return _finalize(
            "PER_EXPERT_INDEX",
            binding,
            logical_id,
            weight_map,
            header_digest,
            header_receipt_digest=receipt_digest,
            header_observation_repo_id=observation_repo,
            official_w2_observation_bound=True,
            representative_header_bound=True,
            representative_layer=layer_no,
            representative_expert=selected_expert,
        )

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