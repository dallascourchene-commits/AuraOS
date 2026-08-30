"""W2 official-header binding layer for the GLM-5.3 per-expert pager plan.

D0 integration only. This module consumes the existing PR350 pager source plan and
the exact zero-payload GLM53SafetensorsHeaderEvidenceV1 receipt produced by W2.
It does not read weights, import a model, execute the pager, or admit G2.

The W2-bound plan is deliberately representative: exact layer/expert header
evidence is part of plan identity, while all-expert/header uniformity remains
explicitly false.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any, Callable, Mapping, Sequence

HEADER_SCHEMA = "GLM53SafetensorsHeaderEvidenceV1"
PLAN_SCHEMA = "GLM53W2HeaderBoundPagerSourcePlanV1"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BLAKE20_RE = re.compile(r"^[0-9a-f]{40}$")


class W2HeaderBindingError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise W2HeaderBindingError("NONCANONICAL_EVIDENCE") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W2HeaderBindingError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _sha_field(name: str, value: Any) -> str:
    value = _text(name, value).lower()
    if not _SHA256_RE.fullmatch(value):
        raise W2HeaderBindingError(f"{name.upper()}_INVALID")
    return value


def _blake20_field(name: str, value: Any) -> str:
    value = _text(name, value).lower()
    if not _BLAKE20_RE.fullmatch(value):
        raise W2HeaderBindingError(f"{name.upper()}_INVALID")
    return value


def _int(name: str, value: Any, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise W2HeaderBindingError(f"{name.upper()}_INVALID")
    return value


def _bool_exact(name: str, value: Any, expected: bool) -> None:
    if type(value) is not bool or value is not expected:
        raise W2HeaderBindingError(f"{name.upper()}_INVALID")


def _producer_receipt_payload(evidence: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "repo_id", "model_revision", "index_sha256", "index_size_bytes",
        "selected_layer", "selected_expert", "entries", "payload_bytes_read",
        "g2_admitted", "runtime_executed", "authority", "schema",
    )
    missing = [name for name in required if name not in evidence]
    if missing:
        raise W2HeaderBindingError("HEADER_EVIDENCE_FIELD_REQUIRED", ",".join(missing))
    return {name: evidence[name] for name in required}


def _producer_receipt_digest(evidence: Mapping[str, Any]) -> str:
    return hashlib.blake2b(_canonical(_producer_receipt_payload(evidence)), digest_size=20).hexdigest()


def _expected_geometry(layer: Mapping[str, Any]) -> tuple[int, int, tuple[int, int]]:
    geom = layer.get("geometry")
    if not isinstance(geom, Mapping):
        raise W2HeaderBindingError("HEADER_GEOMETRY_REQUIRED")
    hidden = _int("hidden_size", geom.get("hidden_size"), minimum=1)
    intermediate = _int("intermediate_size", geom.get("intermediate_size"), minimum=1)
    block = geom.get("block_size")
    if not isinstance(block, Sequence) or isinstance(block, (str, bytes)) or len(block) != 2:
        raise W2HeaderBindingError("HEADER_BLOCK_SIZE_REQUIRED")
    bm = _int("block_rows", block[0], minimum=1)
    bn = _int("block_cols", block[1], minimum=1)
    return hidden, intermediate, (bm, bn)


def _entry_map(evidence: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    raw = evidence.get("entries")
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise W2HeaderBindingError("HEADER_ENTRIES_REQUIRED")
    out: dict[str, Mapping[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping):
            raise W2HeaderBindingError("HEADER_ENTRY_INVALID")
        key = _text("tensor_key", item.get("tensor_key"))
        if key in out:
            raise W2HeaderBindingError("HEADER_ENTRY_DUPLICATE", key)
        out[key] = item
    return out


def _validate_entry(*, item: Mapping[str, Any], key: str, expected_shard: str, expected_dtype: str, expected_shape: tuple[int, ...]) -> dict[str, Any]:
    shard = _text("shard_name", item.get("shard_name"))
    if shard != expected_shard:
        raise W2HeaderBindingError("HEADER_SHARD_BINDING_MISMATCH", key)
    dtype = _text("dtype", item.get("dtype"))
    if dtype != expected_dtype:
        raise W2HeaderBindingError("HEADER_DTYPE_MISMATCH", f"{key}:{dtype}")
    shape_raw = item.get("shape")
    if not isinstance(shape_raw, Sequence) or isinstance(shape_raw, (str, bytes)):
        raise W2HeaderBindingError("HEADER_SHAPE_REQUIRED", key)
    shape = tuple(_int("shape_dim", dim, minimum=1) for dim in shape_raw)
    if shape != expected_shape:
        raise W2HeaderBindingError("HEADER_SHAPE_MISMATCH", f"{key}:expected={expected_shape},observed={shape}")
    offsets_raw = item.get("data_offsets")
    if not isinstance(offsets_raw, Sequence) or isinstance(offsets_raw, (str, bytes)) or len(offsets_raw) != 2:
        raise W2HeaderBindingError("HEADER_OFFSETS_REQUIRED", key)
    start = _int("offset_start", offsets_raw[0])
    end = _int("offset_end", offsets_raw[1])
    if end <= start:
        raise W2HeaderBindingError("HEADER_OFFSETS_INVALID", key)
    bytes_per_element = 1 if expected_dtype == "F8_E4M3" else 4
    expected_bytes = math.prod(shape) * bytes_per_element
    if end - start != expected_bytes:
        raise W2HeaderBindingError("HEADER_BYTE_GEOMETRY_MISMATCH", f"{key}:expected={expected_bytes},observed={end-start}")
    header_sha = _sha_field("header_sha256", item.get("header_sha256"))
    return {"tensor_key": key, "shard_name": shard, "dtype": dtype, "shape": list(shape), "data_offsets": [start, end], "header_sha256": header_sha}


@dataclass(frozen=True)
class W2HeaderBoundPagerSourcePlan:
    inner_plan: Any
    repo_id: str
    model_revision: str
    index_sha256: str
    selected_layer: int
    selected_expert: int
    header_evidence_digest: str
    producer_receipt_digest: str
    source_plan_digest: str
    representative_header_bound: bool = True
    all_experts_header_uniformity_proven: bool = False
    g2_admitted: bool = False
    large_checkpoint_admitted: bool = False
    runtime_execution_proven: bool = False
    authority: bool = False
    schema: str = PLAN_SCHEMA

    @property
    def binding(self) -> Any:
        return self.inner_plan.binding

    def to_dict(self) -> dict[str, Any]:
        inner = self.inner_plan.to_dict() if hasattr(self.inner_plan, "to_dict") else {"binding_kind": getattr(self.inner_plan, "binding_kind", None), "source_plan_digest": getattr(self.inner_plan, "source_plan_digest", None)}
        return {"schema": self.schema, "repo_id": self.repo_id, "model_revision": self.model_revision, "index_sha256": self.index_sha256, "selected_layer": self.selected_layer, "selected_expert": self.selected_expert, "header_evidence_digest": self.header_evidence_digest, "producer_receipt_digest": self.producer_receipt_digest, "inner_plan": inner, "source_plan_digest": self.source_plan_digest, "representative_header_bound": True, "all_experts_header_uniformity_proven": False, "g2_admitted": False, "large_checkpoint_admitted": False, "runtime_execution_proven": False, "authority": False}


def compile_w2_header_bound_pager_source_plan(report: Mapping[str, Any], *, weight_map: Mapping[str, str], header_evidence: Mapping[str, Any], expected_model_revision: str, expected_index_digest: str, compile_fn: Callable[..., Any] | None = None) -> W2HeaderBoundPagerSourcePlan:
    """Bind exact W2 canary evidence into the source-plan identity consumed by W3."""
    if not isinstance(report, Mapping):
        raise W2HeaderBindingError("PROBE_REPORT_REQUIRED")
    if not isinstance(weight_map, Mapping) or not weight_map:
        raise W2HeaderBindingError("WEIGHT_MAP_REQUIRED")
    if not isinstance(header_evidence, Mapping):
        raise W2HeaderBindingError("W2_HEADER_EVIDENCE_REQUIRED")
    if header_evidence.get("schema") != HEADER_SCHEMA:
        raise W2HeaderBindingError("W2_HEADER_SCHEMA_MISMATCH")

    model_revision = _text("model_revision", header_evidence.get("model_revision"))
    index_sha256 = _sha_field("index_sha256", header_evidence.get("index_sha256"))
    if model_revision != _text("expected_model_revision", expected_model_revision):
        raise W2HeaderBindingError("W2_MODEL_REVISION_MISMATCH")
    if index_sha256 != _text("expected_index_digest", expected_index_digest).lower():
        raise W2HeaderBindingError("W2_INDEX_DIGEST_MISMATCH")
    if report.get("model_revision") != model_revision or report.get("index_sha256") != index_sha256:
        raise W2HeaderBindingError("W2_PROBE_SOURCE_MISMATCH")

    _int("index_size_bytes", header_evidence.get("index_size_bytes"), minimum=1)
    selected_layer = _int("selected_layer", header_evidence.get("selected_layer"))
    selected_expert = _int("selected_expert", header_evidence.get("selected_expert"))
    if header_evidence.get("payload_bytes_read") != 0:
        raise W2HeaderBindingError("W2_PAYLOAD_READ_FORBIDDEN")
    _bool_exact("g2_admitted", header_evidence.get("g2_admitted"), False)
    _bool_exact("runtime_executed", header_evidence.get("runtime_executed"), False)
    _bool_exact("authority", header_evidence.get("authority"), False)

    layer = report.get("layer")
    if not isinstance(layer, Mapping):
        raise W2HeaderBindingError("LAYER_REPORT_REQUIRED")
    if layer.get("layout") != "PER_EXPERT_PHYSICAL_LAYOUT":
        raise W2HeaderBindingError("W2_PER_EXPERT_LAYOUT_REQUIRED")
    layer_no = _int("layer", layer.get("layer"))
    if selected_layer != layer_no:
        raise W2HeaderBindingError("W2_SELECTED_LAYER_MISMATCH")
    geom = layer.get("geometry")
    if not isinstance(geom, Mapping):
        raise W2HeaderBindingError("HEADER_GEOMETRY_REQUIRED")
    num_experts = _int("num_experts", geom.get("num_experts"), minimum=1)
    if selected_expert >= num_experts:
        raise W2HeaderBindingError("W2_SELECTED_EXPERT_OUT_OF_RANGE")
    hidden, intermediate, (bm, bn) = _expected_geometry(layer)

    prefix = f"model.layers.{selected_layer}.mlp.experts.{selected_expert}."
    expected = {
        prefix + "gate_proj.weight": ("F8_E4M3", (intermediate, hidden)),
        prefix + "gate_proj.weight_scale_inv": ("F32", (math.ceil(intermediate / bm), math.ceil(hidden / bn))),
        prefix + "up_proj.weight": ("F8_E4M3", (intermediate, hidden)),
        prefix + "up_proj.weight_scale_inv": ("F32", (math.ceil(intermediate / bm), math.ceil(hidden / bn))),
        prefix + "down_proj.weight": ("F8_E4M3", (hidden, intermediate)),
        prefix + "down_proj.weight_scale_inv": ("F32", (math.ceil(hidden / bm), math.ceil(intermediate / bn))),
    }
    entries = _entry_map(header_evidence)
    if set(entries) != set(expected):
        missing = sorted(set(expected) - set(entries)); extra = sorted(set(entries) - set(expected))
        raise W2HeaderBindingError("W2_HEADER_KEY_SET_MISMATCH", f"missing={missing},extra={extra}")

    normalized_entries = []
    for key in sorted(expected):
        assigned = weight_map.get(key)
        if not isinstance(assigned, str) or not assigned:
            raise W2HeaderBindingError("W2_WEIGHT_MAP_KEY_MISSING", key)
        dtype, shape = expected[key]
        normalized_entries.append(_validate_entry(item=entries[key], key=key, expected_shard=assigned, expected_dtype=dtype, expected_shape=shape))

    producer_receipt = _blake20_field("receipt_digest", header_evidence.get("receipt_digest"))
    observed_receipt = _producer_receipt_digest(header_evidence)
    if producer_receipt != observed_receipt:
        raise W2HeaderBindingError("W2_RECEIPT_DIGEST_MISMATCH", f"expected={producer_receipt},observed={observed_receipt}")

    normalized_evidence = {"schema": HEADER_SCHEMA, "repo_id": _text("repo_id", header_evidence.get("repo_id")), "model_revision": model_revision, "index_sha256": index_sha256, "index_size_bytes": header_evidence["index_size_bytes"], "selected_layer": selected_layer, "selected_expert": selected_expert, "entries": normalized_entries, "payload_bytes_read": 0, "g2_admitted": False, "runtime_executed": False, "authority": False, "producer_receipt_digest": producer_receipt}
    header_digest = _sha256(normalized_evidence)

    if compile_fn is None:
        try:
            from .glm53_layout_binding_bridge import compile_pager_source_plan as compile_fn  # type: ignore
        except ImportError:
            from glm53_layout_binding_bridge import compile_pager_source_plan as compile_fn  # type: ignore
    inner = compile_fn(report, weight_map=weight_map, headers=None, expected_model_revision=expected_model_revision, expected_index_digest=expected_index_digest)
    if getattr(inner, "binding_kind", None) != "PER_EXPERT_INDEX":
        raise W2HeaderBindingError("W2_INNER_PER_EXPERT_PLAN_REQUIRED")
    inner_digest = _sha_field("inner_source_plan_digest", getattr(inner, "source_plan_digest", None))
    payload = {"schema": PLAN_SCHEMA, "inner_source_plan_digest": inner_digest, "header_evidence_digest": header_digest, "producer_receipt_digest": producer_receipt, "repo_id": normalized_evidence["repo_id"], "model_revision": model_revision, "index_sha256": index_sha256, "selected_layer": selected_layer, "selected_expert": selected_expert, "representative_header_bound": True, "all_experts_header_uniformity_proven": False, "g2_admitted": False, "large_checkpoint_admitted": False, "runtime_execution_proven": False, "authority": False}
    return W2HeaderBoundPagerSourcePlan(inner_plan=inner, repo_id=normalized_evidence["repo_id"], model_revision=model_revision, index_sha256=index_sha256, selected_layer=selected_layer, selected_expert=selected_expert, header_evidence_digest=header_digest, producer_receipt_digest=producer_receipt, source_plan_digest=_sha256(payload))
