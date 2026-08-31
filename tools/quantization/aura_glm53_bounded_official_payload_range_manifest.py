#!/usr/bin/env python3
"""Compile the smallest bounded live payload-read plan for one official GLM-5.3 expert.

Q10 joins the exact-green live producer-admission frontier (PR649) with the
exact-green concrete-page identity owner (PR641). Historical PR398/PR646 header
observations give exact *relative* safetensors data offsets for layer 3 / expert 0.

This module turns those offsets into a deterministic read manifest only. It does
not claim that payload bytes are currently resident, that block-FP8 dequantization
semantics are owned, that gate/up tensors map to PR628's ``gate_up_proj`` role by
an exact transformation, or that any concrete E8 page was materialized from the
official source tensors.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
import math

from tools.quantization import aura_glm53_historical_official_w2_bridge as historical
from tools.quantization import aura_glm53_live_tensor_concrete_page_producer_admission as live

SCHEMA = "AURA_GLM53_BOUNDED_OFFICIAL_PAYLOAD_RANGE_MANIFEST_V1"
CONVERGENCE_COMMIT = "9534f4782164cd4c29e545b4ce42e8020ef298ba"
PR649_HEAD = "aa004558af8c46bb9bedeedad3cbd2e4e212ab17"
PR649_RUN = 33373165058
PR641_HEAD = "a8d4605a36e04d64cf03f43f457be4bde553e602"
PR641_RUN = 33370700852
PR641_BINDING_BLOB = "157afcb2e457c630d03a8c72aef09f0a6ba04a4d"
PR628_HEAD = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
PR628_PAGE_BLOB = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"
SHARD = "model-00038-of-00141.safetensors"
HISTORICAL_HEADER_SHA256 = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"
EXPECTED_SLICE_COUNT = 6
EXPECTED_TOTAL_PAYLOAD_BYTES = 37_757_952
TARGET_ROLES = ("gate_up_proj", "down_proj")

_DTYPE_BYTES = {"F8_E4M3": 1, "F32": 4}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _target_role(tensor_key: str) -> str:
    if tensor_key.endswith("gate_proj.weight") or tensor_key.endswith("gate_proj.weight_scale_inv"):
        return "gate_up_proj"
    if tensor_key.endswith("up_proj.weight") or tensor_key.endswith("up_proj.weight_scale_inv"):
        return "gate_up_proj"
    if tensor_key.endswith("down_proj.weight") or tensor_key.endswith("down_proj.weight_scale_inv"):
        return "down_proj"
    raise ValueError("Q10_UNEXPECTED_TENSOR_KEY:" + tensor_key)


@dataclass(frozen=True)
class PayloadSliceSpec:
    tensor_key: str
    target_role: str
    shard: str
    header_sha256: str
    dtype: str
    shape: tuple[int, ...]
    relative_begin: int
    relative_end: int
    expected_bytes: int

    def validate(self) -> None:
        if self.target_role not in TARGET_ROLES:
            raise ValueError("Q10_TARGET_ROLE_INVALID")
        if self.shard != SHARD:
            raise ValueError("Q10_SHARD_DRIFT")
        if self.header_sha256 != HISTORICAL_HEADER_SHA256:
            raise ValueError("Q10_HEADER_DIGEST_DRIFT")
        if self.dtype not in _DTYPE_BYTES:
            raise ValueError("Q10_DTYPE_UNSUPPORTED")
        if not self.shape or any(type(v) is not int or v <= 0 for v in self.shape):
            raise ValueError("Q10_SHAPE_INVALID")
        if type(self.relative_begin) is not int or type(self.relative_end) is not int:
            raise ValueError("Q10_OFFSET_TYPE_INVALID")
        if self.relative_begin < 0 or self.relative_end <= self.relative_begin:
            raise ValueError("Q10_OFFSET_RANGE_INVALID")
        calculated = math.prod(self.shape) * _DTYPE_BYTES[self.dtype]
        if self.expected_bytes != calculated:
            raise ValueError("Q10_EXPECTED_BYTE_COUNT_NOT_SHAPE_DTYPE")
        if self.expected_bytes != self.relative_end - self.relative_begin:
            raise ValueError("Q10_OFFSET_BYTE_COUNT_MISMATCH")

    def absolute_range(self, current_header_len: int) -> tuple[int, int]:
        """Return [start,end) in the safetensors file for a revalidated current header.

        SafeTensors data offsets are relative to the data buffer after the 8-byte
        little-endian header-length prefix plus the current JSON header. Historical
        header length is intentionally not persisted here.
        """
        self.validate()
        if type(current_header_len) is not int or current_header_len <= 1:
            raise ValueError("Q10_CURRENT_HEADER_LENGTH_INVALID")
        data_base = 8 + current_header_len
        return data_base + self.relative_begin, data_base + self.relative_end


@dataclass(frozen=True)
class BoundedPayloadRangeManifestReceipt:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    pr641_binding_blob: str
    pr628_page_blob: str
    official_repository: str
    official_revision: str
    layer_id: int
    expert_id: int
    shard: str
    historical_header_sha256: str
    slice_count: int
    total_payload_bytes: int
    target_roles: tuple[str, ...]
    historical_relative_offsets_bound: bool
    absolute_ranges_require_current_header_length: bool
    current_header_revalidation_required: bool
    payload_fetch_plan_complete_for_representative_expert: bool
    target_role_names_bound: bool
    source_to_target_layout_relation_bound: bool
    block_fp8_dequantization_semantics_bound: bool
    live_payload_observation_executed: bool
    live_payload_digests_bound: bool
    exact_live_official_tensor_to_concrete_source_tensor_set_relation: bool
    candidate_page_materialization_owner_bound: bool
    baseline_same_live_official_source_tensor_set_proven: bool
    representative_scope_only: bool
    all_layers_experts_uniformity_proven: bool
    currentness_revalidation_required_at_use: bool
    disposition: str
    real_tensor_quantization_eligible: bool
    model_execution_eligible: bool
    generalized_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def current_payload_slices() -> tuple[PayloadSliceSpec, ...]:
    """Recompile the exact historical six-entry observation into a live read plan."""
    observation = historical.canonical_pr398_observation()
    entries = observation.get("entries")
    if not isinstance(entries, list) or len(entries) != EXPECTED_SLICE_COUNT:
        raise ValueError("Q10_EXACT_SIX_HISTORICAL_ENTRIES_REQUIRED")

    slices: list[PayloadSliceSpec] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Q10_HISTORICAL_ENTRY_INVALID")
        key = str(entry["key"])
        offsets = entry["data_offsets"]
        shape = entry["shape"]
        if not isinstance(offsets, list) or len(offsets) != 2:
            raise ValueError("Q10_OFFSETS_INVALID")
        if not isinstance(shape, list):
            raise ValueError("Q10_SHAPE_INVALID")
        spec = PayloadSliceSpec(
            tensor_key=key,
            target_role=_target_role(key),
            shard=str(entry["shard"]),
            header_sha256=str(entry["header_sha256"]),
            dtype=str(entry["dtype"]),
            shape=tuple(int(v) for v in shape),
            relative_begin=int(offsets[0]),
            relative_end=int(offsets[1]),
            expected_bytes=int(offsets[1]) - int(offsets[0]),
        )
        spec.validate()
        slices.append(spec)

    if len(slices) != EXPECTED_SLICE_COUNT:
        raise ValueError("Q10_SLICE_COUNT_DRIFT")
    if sum(s.expected_bytes for s in slices) != EXPECTED_TOTAL_PAYLOAD_BYTES:
        raise ValueError("Q10_TOTAL_PAYLOAD_BYTE_COUNT_DRIFT")
    if {s.target_role for s in slices} != set(TARGET_ROLES):
        raise ValueError("Q10_TARGET_ROLE_COVERAGE_DRIFT")
    if sum(s.target_role == "gate_up_proj" for s in slices) != 4:
        raise ValueError("Q10_GATE_UP_SOURCE_SLICE_COUNT_DRIFT")
    if sum(s.target_role == "down_proj" for s in slices) != 2:
        raise ValueError("Q10_DOWN_SOURCE_SLICE_COUNT_DRIFT")
    return tuple(slices)


def current_bounded_payload_range_manifest() -> BoundedPayloadRangeManifestReceipt:
    """Return the exact software-derived plan without claiming any live byte effect."""
    admission = live.current_live_producer_admission()
    if admission.disposition != "HOLD_LIVE_OFFICIAL_TENSOR_TO_CONCRETE_PAGE_PRODUCER":
        raise ValueError("Q10_PR649_DISPOSITION_DRIFT")
    if admission.live_official_tensor_payload_observed:
        raise ValueError("Q10_PARENT_ALREADY_HAS_LIVE_PAYLOAD")
    if admission.exact_live_official_tensor_to_concrete_source_tensor_set_relation:
        raise ValueError("Q10_PARENT_ALREADY_HAS_SOURCE_TO_PAGE_RELATION")
    if admission.candidate_page_materialization_owner_bound:
        raise ValueError("Q10_PARENT_ALREADY_HAS_MATERIALIZATION_OWNER")
    if admission.baseline_same_live_official_source_tensor_set_proven:
        raise ValueError("Q10_PARENT_ALREADY_HAS_BASELINE_RELATION")

    slices = current_payload_slices()
    return BoundedPayloadRangeManifestReceipt(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR649_HEAD, PR641_HEAD),
        exact_parent_runs=(PR649_RUN, PR641_RUN),
        pr641_binding_blob=PR641_BINDING_BLOB,
        pr628_page_blob=PR628_PAGE_BLOB,
        official_repository=admission.official_repository,
        official_revision=admission.official_revision,
        layer_id=historical.PR398_LAYER,
        expert_id=historical.PR398_EXPERT,
        shard=SHARD,
        historical_header_sha256=HISTORICAL_HEADER_SHA256,
        slice_count=len(slices),
        total_payload_bytes=sum(s.expected_bytes for s in slices),
        target_roles=TARGET_ROLES,
        historical_relative_offsets_bound=True,
        absolute_ranges_require_current_header_length=True,
        current_header_revalidation_required=True,
        payload_fetch_plan_complete_for_representative_expert=True,
        target_role_names_bound=True,
        source_to_target_layout_relation_bound=False,
        block_fp8_dequantization_semantics_bound=False,
        live_payload_observation_executed=False,
        live_payload_digests_bound=False,
        exact_live_official_tensor_to_concrete_source_tensor_set_relation=False,
        candidate_page_materialization_owner_bound=False,
        baseline_same_live_official_source_tensor_set_proven=False,
        representative_scope_only=True,
        all_layers_experts_uniformity_proven=False,
        currentness_revalidation_required_at_use=True,
        disposition="PLAN_READY_LIVE_EFFECT_NOT_EXECUTED",
        real_tensor_quantization_eligible=False,
        model_execution_eligible=False,
        generalized_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(current_bounded_payload_range_manifest).parameters) != 0


def main() -> None:
    receipt = current_bounded_payload_range_manifest()
    slices = current_payload_slices()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["slices"] = [asdict(s) for s in slices]
    body["absolute_range_formula"] = "[8+CURRENT_HEADER_LEN+BEGIN,8+CURRENT_HEADER_LEN+END)"
    body["law"] = (
        "RangeAddressability != PayloadObservation != DequantizationSemantics != "
        "SourceToPageMaterialization"
    )
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
