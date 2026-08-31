#!/usr/bin/env python3
"""Bind the exact GLM-5.3 six-slice source manifest to the earned canonical FP8 transform.

Q13 is planning/evidence structure only. It does not perform the unowned up/down
range reads and it does not infer a fused ``gate_up`` tensor layout. The exact gate
canonical source identity is carried from PR657's hosted-green result; up/down stay
HOLD until their raw payloads are independently observed and transformed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

SCHEMA = "AURA_GLM53_CANONICAL_EXPERT_SOURCE_SET_TRANSFORM_MANIFEST_V1"
CONVERGENCE_COMMIT = "ad6b8f7541d6556ff724f6ced24896a5fa1b0868"
PR657_HEAD = "7922fbfadb3adab4e5f9b935d1e997693cd7c7a6"
PR657_RUN = 33395690612
PR652_HEAD = "73491807ab2f1f977e2f2b491607893de0ccec23"
PR652_RUN = 33374060046
OFFICIAL_REPOSITORY = "zai-org/GLM-5.3"
OFFICIAL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
SHARD = "model-00038-of-00141.safetensors"
LAYER_ID = 3
EXPERT_ID = 0
HEADER_SHA256 = "8607b1b281f5ca8c7b166376e8f6d7eb9ca07f79200f6095f0f55ca35149ba56"

FP8_FORMAT = "S1E4M3_BIAS7_FINITE_OUTER_NAN"
BLOCK_SHAPE = (128, 128)
CANONICAL_DTYPE = "float32_le"
CANONICAL_ORDER = "C"
CANONICAL_DOMAIN = "IEEE754_BINARY32_LITTLE_ENDIAN_C_ORDER"
PROJECTION_ELEMENT_COUNT = 12_582_912
CANONICAL_PROJECTION_BYTES = 50_331_648
GATE_UP_SOURCE_SET_BYTES = 100_663_296
FULL_PROJECTION_SOURCE_SET_BYTES = 150_994_944
EARNED_GATE_CANONICAL_SHA256 = "0db00dc5a76ce5b91273dd7be7e12b5d47121154b5c1f440131c399ce245a43e"
EARNED_GATE_RAW_WEIGHT_SHA256 = "2d4e5f36478b598043431b3691ce6a48639e01b6f804b1db62ca4af4d14063e8"
EARNED_GATE_RAW_SCALE_SHA256 = "671dd3b32b3f4cc651b93f3420ae47957ae09c1f745d278c0795d56e5d511c55"

# Exact PR652 hosted six-slice manifest. Offsets are SafeTensors data-buffer relative.
_SOURCE_SLICES = (
    ("gate", "weight", "model.layers.3.mlp.experts.0.gate_proj.weight", "F8_E4M3", (2048, 6144), 4_070_207_936, 4_082_790_848, 12_582_912),
    ("gate", "scale", "model.layers.3.mlp.experts.0.gate_proj.weight_scale_inv", "F32", (16, 48), 993_728, 996_800, 3_072),
    ("up", "weight", "model.layers.3.mlp.experts.0.up_proj.weight", "F8_E4M3", (2048, 6144), 4_082_790_848, 4_095_373_760, 12_582_912),
    ("up", "scale", "model.layers.3.mlp.experts.0.up_proj.weight_scale_inv", "F32", (16, 48), 996_800, 999_872, 3_072),
    ("down", "weight", "model.layers.3.mlp.experts.0.down_proj.weight", "F8_E4M3", (6144, 2048), 4_057_625_024, 4_070_207_936, 12_582_912),
    ("down", "scale", "model.layers.3.mlp.experts.0.down_proj.weight_scale_inv", "F32", (48, 16), 990_656, 993_728, 3_072),
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class SourceSlice:
    projection: str
    role: str
    tensor_key: str
    dtype: str
    shape: tuple[int, ...]
    relative_begin: int
    relative_end: int
    expected_bytes: int

    def validate(self) -> None:
        if self.projection not in {"gate", "up", "down"}:
            raise ValueError("Q13_PROJECTION_INVALID")
        if self.role not in {"weight", "scale"}:
            raise ValueError("Q13_ROLE_INVALID")
        if self.relative_end - self.relative_begin != self.expected_bytes:
            raise ValueError("Q13_RANGE_BYTE_COUNT_MISMATCH")
        if self.role == "weight":
            if self.dtype != "F8_E4M3" or self.expected_bytes != PROJECTION_ELEMENT_COUNT:
                raise ValueError("Q13_WEIGHT_CONTRACT_DRIFT")
            if self.shape not in {(2048, 6144), (6144, 2048)}:
                raise ValueError("Q13_WEIGHT_SHAPE_DRIFT")
        else:
            if self.dtype != "F32" or self.expected_bytes != 3_072:
                raise ValueError("Q13_SCALE_CONTRACT_DRIFT")
            if self.shape not in {(16, 48), (48, 16)}:
                raise ValueError("Q13_SCALE_SHAPE_DRIFT")


@dataclass(frozen=True)
class ProjectionTransformState:
    projection: str
    weight_key: str
    scale_key: str
    weight_shape: tuple[int, ...]
    scale_shape: tuple[int, ...]
    block_shape: tuple[int, int]
    fp8_format: str
    canonical_dtype: str
    canonical_order: str
    canonical_bytes: int
    raw_payload_observed: bool
    canonical_identity_earned: bool
    canonical_sha256: str | None
    status: str


@dataclass(frozen=True)
class CanonicalExpertSourceSetTransformManifest:
    schema: str
    convergence_commit: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    official_repository: str
    official_revision: str
    layer_id: int
    expert_id: int
    shard: str
    historical_header_sha256: str
    source_slice_count: int
    source_manifest_total_bytes: int
    transform_profile: str
    transform_profile_bound: bool
    gate_canonical_sha256: str
    gate_canonical_bytes: int
    gate_up_independent_source_set_bytes: int
    full_independent_projection_source_set_bytes: int
    gate_up_concatenation_order_bound: bool
    gate_up_concatenation_axis_bound: bool
    gate_up_tensor_layout_bound: bool
    up_payload_observed: bool
    down_payload_observed: bool
    up_canonical_identity_earned: bool
    down_canonical_identity_earned: bool
    full_expert_canonical_source_set_materialized: bool
    source_to_e8_page_materialization_bound: bool
    real_e8_page_materialized: bool
    model_quality_proven: bool
    runtime_performance_proven: bool
    semantic_k27_authority: bool
    native_private_transformer_kv_accessed: bool
    gate10_promoted: bool
    deployment_authorized: bool
    disposition: str

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def source_slices() -> tuple[SourceSlice, ...]:
    rows = tuple(SourceSlice(*row) for row in _SOURCE_SLICES)
    for row in rows:
        row.validate()
    if len(rows) != 6 or {r.projection for r in rows} != {"gate", "up", "down"}:
        raise ValueError("Q13_EXACT_SIX_SOURCE_SLICES_REQUIRED")
    for projection in ("gate", "up", "down"):
        group = [r for r in rows if r.projection == projection]
        if len(group) != 2 or {r.role for r in group} != {"weight", "scale"}:
            raise ValueError("Q13_WEIGHT_SCALE_PAIR_REQUIRED:" + projection)
    if sum(r.expected_bytes for r in rows) != 37_757_952:
        raise ValueError("Q13_SOURCE_MANIFEST_TOTAL_DRIFT")
    return rows


def _projection_state(projection: str) -> ProjectionTransformState:
    rows = [r for r in source_slices() if r.projection == projection]
    weight = next(r for r in rows if r.role == "weight")
    scale = next(r for r in rows if r.role == "scale")
    observed = projection == "gate"
    return ProjectionTransformState(
        projection=projection,
        weight_key=weight.tensor_key,
        scale_key=scale.tensor_key,
        weight_shape=weight.shape,
        scale_shape=scale.shape,
        block_shape=BLOCK_SHAPE,
        fp8_format=FP8_FORMAT,
        canonical_dtype=CANONICAL_DTYPE,
        canonical_order=CANONICAL_ORDER,
        canonical_bytes=CANONICAL_PROJECTION_BYTES,
        raw_payload_observed=observed,
        canonical_identity_earned=observed,
        canonical_sha256=EARNED_GATE_CANONICAL_SHA256 if projection == "gate" else None,
        status="CANONICAL_IDENTITY_EARNED" if observed else "RAW_PAYLOAD_UNOBSERVED_CANONICAL_IDENTITY_HOLD",
    )


def build_manifest() -> tuple[CanonicalExpertSourceSetTransformManifest, tuple[ProjectionTransformState, ...]]:
    slices = source_slices()
    projections = tuple(_projection_state(name) for name in ("gate", "up", "down"))
    gate = projections[0]
    if gate.canonical_sha256 != EARNED_GATE_CANONICAL_SHA256:
        raise ValueError("Q13_GATE_EARNED_IDENTITY_DRIFT")
    if projections[1].canonical_sha256 is not None or projections[2].canonical_sha256 is not None:
        raise ValueError("Q13_UNOBSERVED_PROJECTION_HASH_MINTED")
    receipt = CanonicalExpertSourceSetTransformManifest(
        schema=SCHEMA,
        convergence_commit=CONVERGENCE_COMMIT,
        exact_parent_heads=(PR657_HEAD, PR652_HEAD),
        exact_parent_runs=(PR657_RUN, PR652_RUN),
        official_repository=OFFICIAL_REPOSITORY,
        official_revision=OFFICIAL_REVISION,
        layer_id=LAYER_ID,
        expert_id=EXPERT_ID,
        shard=SHARD,
        historical_header_sha256=HEADER_SHA256,
        source_slice_count=len(slices),
        source_manifest_total_bytes=sum(s.expected_bytes for s in slices),
        transform_profile=f"{FP8_FORMAT}__BLOCK128x128__{CANONICAL_DOMAIN}",
        transform_profile_bound=True,
        gate_canonical_sha256=EARNED_GATE_CANONICAL_SHA256,
        gate_canonical_bytes=CANONICAL_PROJECTION_BYTES,
        gate_up_independent_source_set_bytes=GATE_UP_SOURCE_SET_BYTES,
        full_independent_projection_source_set_bytes=FULL_PROJECTION_SOURCE_SET_BYTES,
        gate_up_concatenation_order_bound=False,
        gate_up_concatenation_axis_bound=False,
        gate_up_tensor_layout_bound=False,
        up_payload_observed=False,
        down_payload_observed=False,
        up_canonical_identity_earned=False,
        down_canonical_identity_earned=False,
        full_expert_canonical_source_set_materialized=False,
        source_to_e8_page_materialization_bound=False,
        real_e8_page_materialized=False,
        model_quality_proven=False,
        runtime_performance_proven=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        deployment_authorized=False,
        disposition="GATE_CANONICALIZED__UP_DOWN_RAW_UNOBSERVED__GATE_UP_LAYOUT_UNBOUND",
    )
    return receipt, projections


def public_api_has_promotion_inputs() -> bool:
    return len(inspect.signature(build_manifest).parameters) != 0


def main() -> None:
    receipt, projections = build_manifest()
    body = asdict(receipt)
    body["receipt_digest"] = receipt.receipt_digest
    body["projections"] = [asdict(p) for p in projections]
    body["source_slices"] = [asdict(s) for s in source_slices()]
    body["laws"] = [
        "TransformProfileApplicable != PayloadObserved",
        "HeaderShapeCompatible != CanonicalBytesMaterialized",
        "GateCanonicalized != GateUpComposed",
        "GateUpSourceSetByteSum != GateUpTensorLayout",
        "SameDecoderFamily != SameSourceIdentity",
        "CanonicalF32SourceIdentity != E8PageMaterialization",
    ]
    print(json.dumps(body, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
