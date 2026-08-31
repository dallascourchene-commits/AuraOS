#!/usr/bin/env python3
"""Planning-only packed-expert quantization layout for the GLM-5.3/AirLLM lane.

Derived from two non-self Aura artifacts:
- packed expert first-axis sliceability source verification;
- Point0/KV/energy/thermal lifecycle policy.

The planner computes exact representation and working-set bytes for a selected set of
experts while failing closed when weight and companion quantization metadata cannot be
selected under the same expert identity. It performs no tensor I/O or model execution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

VERSION = "AURA_GLM53_PACKED_EXPERT_QUANTIZATION_PLAN_V1"
PACKED_EXPERT_ARTIFACT_ID = "1xC6iwBv1EMxSLJW67otQFRUvF1PvhWVS04YRZG_4ZAk"
LIFECYCLE_POLICY_ARTIFACT_ID = "1iN1n8pIfcRoOaXkVTuMcQJelY69MxXuirOPUJF_wcGQ"

PER_EXPERT_SLICEABLE = "PER_EXPERT_SLICEABLE"
BANK_RESIDENT_BOUNDED = "BANK_RESIDENT_BOUNDED"
BANK_ONLY_UNBOUNDED = "BANK_ONLY_UNBOUNDED"
_ALLOWED_COMPANION_LAYOUTS = {
    PER_EXPERT_SLICEABLE,
    BANK_RESIDENT_BOUNDED,
    BANK_ONLY_UNBOUNDED,
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _positive_int(name: str, value: int) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError("INVALID_POSITIVE_INT:" + name)


@dataclass(frozen=True)
class IndexedQuantizedRepresentation:
    representation_id: str
    vector_dim: int
    index_bits_per_vector: int
    scale_group_weights: int
    scale_bits_per_group: int
    companion_layout: str
    companion_bytes_per_expert: int = 0
    bank_resident_companion_bytes: int = 0
    indexed_bitstring_mapping_proven: bool = True

    def validate(self) -> None:
        if not self.representation_id.strip():
            raise ValueError("REPRESENTATION_ID_REQUIRED")
        for name in ("vector_dim", "index_bits_per_vector", "scale_group_weights"):
            _positive_int(name, getattr(self, name))
        if type(self.scale_bits_per_group) is not int or self.scale_bits_per_group < 0:
            raise ValueError("INVALID_SCALE_BITS")
        if self.companion_layout not in _ALLOWED_COMPANION_LAYOUTS:
            raise ValueError("INVALID_COMPANION_LAYOUT")
        for name in ("companion_bytes_per_expert", "bank_resident_companion_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError("INVALID_COMPANION_BYTES:" + name)
        if self.indexed_bitstring_mapping_proven is not True:
            raise ValueError("INDEXED_BITSTRING_MAPPING_REQUIRED")
        if self.companion_layout == PER_EXPERT_SLICEABLE and self.bank_resident_companion_bytes:
            raise ValueError("PER_EXPERT_LAYOUT_CANNOT_REQUIRE_BANK_COMPANION")
        if self.companion_layout == BANK_RESIDENT_BOUNDED and self.companion_bytes_per_expert:
            raise ValueError("BANK_LAYOUT_CANNOT_REQUIRE_PER_EXPERT_COMPANION")

    @property
    def effective_bits_per_weight(self) -> float:
        self.validate()
        return self.index_bits_per_vector / self.vector_dim + self.scale_bits_per_group / self.scale_group_weights


@dataclass(frozen=True)
class PackedExpertQuantizationRequest:
    num_experts: int
    parameters_per_expert: int
    expert_representation_ids: tuple[str, ...]
    selected_expert_ids: tuple[int, ...]
    cache_budget_bytes: int
    bank_resident_companion_cap_bytes: int
    lifecycle_mode: str

    def validate(self) -> None:
        _positive_int("num_experts", self.num_experts)
        _positive_int("parameters_per_expert", self.parameters_per_expert)
        _positive_int("cache_budget_bytes", self.cache_budget_bytes)
        if type(self.bank_resident_companion_cap_bytes) is not int or self.bank_resident_companion_cap_bytes < 0:
            raise ValueError("INVALID_BANK_COMPANION_CAP")
        if len(self.expert_representation_ids) != self.num_experts:
            raise ValueError("EXPERT_ASSIGNMENT_CARDINALITY_MISMATCH")
        if not self.selected_expert_ids:
            raise ValueError("SELECTED_EXPERTS_REQUIRED")
        if any(type(e) is not int or e < 0 or e >= self.num_experts for e in self.selected_expert_ids):
            raise ValueError("EXPERT_ID_OUT_OF_RANGE")
        if self.lifecycle_mode not in {"INTERACTIVE", "BACKGROUND", "OVERNIGHT_AC", "DEFER"}:
            raise ValueError("INVALID_LIFECYCLE_MODE")


@dataclass(frozen=True)
class PackedExpertQuantizationPlan:
    version: str
    parent_artifact_ids: tuple[str, str]
    num_experts: int
    parameters_per_expert: int
    selected_expert_ids: tuple[int, ...]
    selected_contiguous_runs: tuple[tuple[int, int], ...]
    representation_bpw_by_id: tuple[tuple[str, float], ...]
    expert_representation_ids: tuple[str, ...]
    full_routed_expert_static_bytes: int
    selected_expert_working_set_bytes: int
    fp8_reference_static_bytes: int
    static_compression_ratio_vs_fp8: float
    working_set_fits_cache_budget: bool
    lifecycle_mode: str
    packed_weight_first_axis_sliceability_required: bool
    quantization_companion_identity_bound: bool
    bank_companion_loaded_as_bounded_exception: bool
    expert_quality_preserved_proven: bool
    selected_expert_router_frequency_measured: bool
    kv_cache_compression_proven: bool
    physical_io_observed: bool
    planned_backend_executed: bool
    model_execution_performed: bool
    lifecycle_mode_performance_safe_proven: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    deployment_authorized: bool

    @property
    def plan_digest(self) -> str:
        return _sha(asdict(self))


def _runs(ids: Sequence[int]) -> tuple[tuple[int, int], ...]:
    ordered = sorted(set(ids))
    runs: list[tuple[int, int]] = []
    start = prev = ordered[0]
    for value in ordered[1:]:
        if value == prev + 1:
            prev = value
            continue
        runs.append((start, prev + 1))
        start = prev = value
    runs.append((start, prev + 1))
    return tuple(runs)


def _payload_bytes(parameters: int, rep: IndexedQuantizedRepresentation) -> int:
    return math.ceil(parameters * rep.effective_bits_per_weight / 8.0)


def build_packed_expert_quantization_plan(
    *,
    request: PackedExpertQuantizationRequest,
    representations: Mapping[str, IndexedQuantizedRepresentation],
) -> PackedExpertQuantizationPlan:
    request.validate()
    if not representations:
        raise ValueError("REPRESENTATIONS_REQUIRED")
    for key, rep in representations.items():
        rep.validate()
        if key != rep.representation_id:
            raise ValueError("REPRESENTATION_KEY_ID_MISMATCH")

    used_ids = set(request.expert_representation_ids)
    missing = sorted(used_ids - set(representations))
    if missing:
        raise ValueError("UNKNOWN_REPRESENTATION:" + ",".join(missing))

    bank_requirements: dict[str, int] = {}
    expert_bytes: list[int] = []
    for rep_id in request.expert_representation_ids:
        rep = representations[rep_id]
        if rep.companion_layout == BANK_ONLY_UNBOUNDED:
            raise ValueError("UNSLICEABLE_COMPANION_LAYOUT:" + rep_id)
        if rep.companion_layout == BANK_RESIDENT_BOUNDED:
            bank_requirements[rep_id] = rep.bank_resident_companion_bytes
        expert_bytes.append(
            _payload_bytes(request.parameters_per_expert, rep)
            + (rep.companion_bytes_per_expert if rep.companion_layout == PER_EXPERT_SLICEABLE else 0)
        )

    bank_companion_bytes = sum(bank_requirements.values())
    if bank_companion_bytes > request.bank_resident_companion_cap_bytes:
        raise ValueError("BANK_COMPANION_CAP_EXCEEDED")

    selected = tuple(sorted(set(request.selected_expert_ids)))
    selected_bytes = sum(expert_bytes[e] for e in selected) + bank_companion_bytes
    static_bytes = sum(expert_bytes) + bank_companion_bytes
    fp8_reference = request.num_experts * request.parameters_per_expert
    ratio = fp8_reference / static_bytes

    return PackedExpertQuantizationPlan(
        version=VERSION,
        parent_artifact_ids=(PACKED_EXPERT_ARTIFACT_ID, LIFECYCLE_POLICY_ARTIFACT_ID),
        num_experts=request.num_experts,
        parameters_per_expert=request.parameters_per_expert,
        selected_expert_ids=selected,
        selected_contiguous_runs=_runs(selected),
        representation_bpw_by_id=tuple(sorted((rid, representations[rid].effective_bits_per_weight) for rid in used_ids)),
        expert_representation_ids=request.expert_representation_ids,
        full_routed_expert_static_bytes=static_bytes,
        selected_expert_working_set_bytes=selected_bytes,
        fp8_reference_static_bytes=fp8_reference,
        static_compression_ratio_vs_fp8=ratio,
        working_set_fits_cache_budget=selected_bytes <= request.cache_budget_bytes,
        lifecycle_mode=request.lifecycle_mode,
        packed_weight_first_axis_sliceability_required=True,
        quantization_companion_identity_bound=True,
        bank_companion_loaded_as_bounded_exception=bank_companion_bytes > 0,
        expert_quality_preserved_proven=False,
        selected_expert_router_frequency_measured=False,
        kv_cache_compression_proven=False,
        physical_io_observed=False,
        planned_backend_executed=False,
        model_execution_performed=False,
        lifecycle_mode_performance_safe_proven=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        deployment_authorized=False,
    )


def main() -> None:
    # A deterministic planning fixture, not GLM-5.3 model evidence.
    e8_2p5 = IndexedQuantizedRepresentation(
        representation_id="E8_INDEXED_EXAMPLE_2P5",
        vector_dim=8,
        index_bits_per_vector=18,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=PER_EXPERT_SLICEABLE,
        companion_bytes_per_expert=4096,
    )
    e8_3 = IndexedQuantizedRepresentation(
        representation_id="E8_INDEXED_EXAMPLE_3P0",
        vector_dim=8,
        index_bits_per_vector=22,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=PER_EXPERT_SLICEABLE,
        companion_bytes_per_expert=4096,
    )
    assignments = tuple("E8_INDEXED_EXAMPLE_3P0" if i % 31 == 0 else "E8_INDEXED_EXAMPLE_2P5" for i in range(256))
    request = PackedExpertQuantizationRequest(
        num_experts=256,
        parameters_per_expert=1_000_000,
        expert_representation_ids=assignments,
        selected_expert_ids=(3, 4, 9, 17, 18, 19, 31, 200),
        cache_budget_bytes=8_000_000,
        bank_resident_companion_cap_bytes=1_000_000,
        lifecycle_mode="BACKGROUND",
    )
    plan = build_packed_expert_quantization_plan(request=request, representations={e8_2p5.representation_id: e8_2p5, e8_3.representation_id: e8_3})
    print(json.dumps({**asdict(plan), "plan_digest": plan.plan_digest}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
