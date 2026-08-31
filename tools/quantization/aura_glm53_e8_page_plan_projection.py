#!/usr/bin/env python3
"""Project the exact PR628 indexed-E8 expert page codec into the exact Q2 planner.

Q5 closes a representation-identity/accounting seam between two exact-green
other-agent artifacts:
- Q2's abstract packed-expert quantization planner; and
- PR628's concrete source-bound indexed-E8 expert-page format.

The projection proves codec/layout compatibility and selected-page coverage only.
Serialized page headers remain outside Q2's codec-byte budget, and no model execution,
physical I/O, source-tensor authentication, quality preservation, or deployment is
promoted by this module.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Mapping, Sequence

from tools.quantization.aura_glm53_packed_expert_quantization_plan import (
    BANK_RESIDENT_BOUNDED,
    IndexedQuantizedRepresentation,
    PackedExpertQuantizationPlan,
    PackedExpertQuantizationRequest,
    build_packed_expert_quantization_plan,
)
from tools.quantization.aura_glm53_e8_indexed_expert_page_reference import (
    DEFAULT_BLOCK_SIZE,
    INDEX_BITS,
    SCHEME,
    TENSOR_ROLES,
    VECTOR_DIM,
    ExpertPage,
    codebook,
    codebook_digest,
    unpack_expert_page,
)

VERSION = "AURA_GLM53_E8_PAGE_PLAN_PROJECTION_V1"
Q2_EXACT_HEAD = "cb9f50fc2fd05006f4f5af0a2f143f2c74aee62f"
Q2_EXACT_RUN = 33367433407
E8_EXACT_HEAD = "b8fd399ee0ca6b45a4ec7db58750e6d4105ae3ae"
E8_EXACT_RUN = 33367948262
Q5_CONVERGENCE_COMMIT = "86d0f573076a4da56ff661bcd9cef971c3c5058c"
E8_SOURCE_BLOB_SHA = "5df2cd69a1519b2626cb52c1d8f23a25504425d9"
SCALE_GROUP_WEIGHTS = 64
SCALE_BITS_PER_GROUP = 16


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def e8_plan_representation_id() -> str:
    return f"{SCHEME}:codebook-sha256:{codebook_digest()}"


def e8_codebook_bytes() -> int:
    grid = codebook()[0]
    if str(grid.dtype) != "float32" or tuple(grid.shape) != (58112, 8):
        raise ValueError("E8_CODEBOOK_LAYOUT_DRIFT")
    return int(grid.nbytes)


def e8_q2_representation() -> IndexedQuantizedRepresentation:
    rep = IndexedQuantizedRepresentation(
        representation_id=e8_plan_representation_id(),
        vector_dim=VECTOR_DIM,
        index_bits_per_vector=INDEX_BITS,
        scale_group_weights=SCALE_GROUP_WEIGHTS,
        scale_bits_per_group=SCALE_BITS_PER_GROUP,
        companion_layout=BANK_RESIDENT_BOUNDED,
        bank_resident_companion_bytes=e8_codebook_bytes(),
        indexed_bitstring_mapping_proven=True,
    )
    rep.validate()
    if not math.isclose(rep.effective_bits_per_weight, 2.25, abs_tol=1e-12):
        raise ValueError("E8_Q2_RATE_PROJECTION_DRIFT")
    return rep


def implementation_binding_digest() -> str:
    return _sha({
        "exact_parent_head": E8_EXACT_HEAD,
        "source_blob_sha": E8_SOURCE_BLOB_SHA,
        "scheme": SCHEME,
        "vector_dim": VECTOR_DIM,
        "index_bits": INDEX_BITS,
        "scale_group_weights": SCALE_GROUP_WEIGHTS,
        "scale_bits_per_group": SCALE_BITS_PER_GROUP,
        "default_block_size": DEFAULT_BLOCK_SIZE,
        "codebook_digest": codebook_digest(),
        "codebook_bytes": e8_codebook_bytes(),
        "tensor_roles": sorted(TENSOR_ROLES),
    })


@dataclass(frozen=True)
class SelectedE8PagePlanReceipt:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    q2_plan_digest: str
    e8_representation_id: str
    e8_implementation_binding_digest: str
    codebook_digest: str
    codebook_bank_resident_bytes: int
    model_revision: str
    representation_revision: str
    layer_id: int
    selected_expert_ids: tuple[int, ...]
    page_identity_digests: tuple[str, ...]
    page_payload_digests: tuple[str, ...]
    selected_source_weight_count: int
    selected_codec_payload_bytes: int
    selected_serialized_page_bytes: int
    q2_selected_working_set_bytes: int
    q2_codec_working_set_matches_concrete_pages: bool
    serialized_page_overhead_bytes: int
    serialized_working_set_matches_q2_plan: bool
    selected_page_roles_complete: bool
    selected_parameter_count_matches_plan: bool
    shared_codebook_matches_q2_bounded_companion: bool
    page_headers_accounted_in_q2_cache_budget: bool
    source_tensor_bytes_authenticated: bool
    planned_layout_executed_proven: bool
    selected_experts_actually_served_proven: bool
    physical_io_observed: bool
    model_execution_performed: bool
    glm53_quality_preserved_proven: bool
    general_performance_winner_proven: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    gate10_promoted: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _validate_plan_ceiling(plan: PackedExpertQuantizationPlan) -> None:
    for name in (
        "expert_quality_preserved_proven",
        "selected_expert_router_frequency_measured",
        "kv_cache_compression_proven",
        "physical_io_observed",
        "planned_backend_executed",
        "model_execution_performed",
        "lifecycle_mode_performance_safe_proven",
        "native_private_transformer_kv_accessed",
        "semantic_k27_authority_minted",
        "deployment_authorized",
    ):
        if getattr(plan, name) is not False:
            raise ValueError("Q2_CLAIM_CEILING_WIDENED:" + name)


def bind_selected_e8_pages_to_q2_plan(
    *,
    plan_request: PackedExpertQuantizationRequest,
    representations: Mapping[str, IndexedQuantizedRepresentation],
    pages: Sequence[ExpertPage],
    model_revision: str,
    representation_revision: str,
    layer_id: int,
) -> SelectedE8PagePlanReceipt:
    if type(layer_id) is not int or layer_id < 0:
        raise ValueError("INVALID_LAYER_ID")
    exact_rep = e8_q2_representation()
    supplied = representations.get(exact_rep.representation_id)
    if supplied != exact_rep:
        raise ValueError("EXACT_E8_Q2_REPRESENTATION_REQUIRED")

    plan = build_packed_expert_quantization_plan(request=plan_request, representations=representations)
    _validate_plan_ceiling(plan)
    selected = plan.selected_expert_ids
    if any(plan.expert_representation_ids[e] != exact_rep.representation_id for e in selected):
        raise ValueError("SELECTED_EXPERT_NOT_ASSIGNED_EXACT_E8_REPRESENTATION")

    expected_pairs = {(expert_id, role) for expert_id in selected for role in TENSOR_ROLES}
    seen: dict[tuple[int, str], ExpertPage] = {}
    source_weights_by_expert = {expert_id: 0 for expert_id in selected}
    codec_payload_bytes = 0
    serialized_page_bytes = 0
    identity_digests: list[str] = []
    payload_digests: list[str] = []

    if not pages:
        raise ValueError("SELECTED_E8_PAGES_REQUIRED")
    for page in pages:
        page.validate()
        ident = page.identity
        key = (ident.expert_id, ident.tensor_role)
        if key not in expected_pairs:
            raise ValueError("FOREIGN_OR_UNSELECTED_E8_PAGE")
        if key in seen:
            raise ValueError("DUPLICATE_EXPERT_TENSOR_ROLE_PAGE")
        if ident.model_revision != model_revision:
            raise ValueError("PAGE_MODEL_REVISION_MISMATCH")
        if ident.representation_revision != representation_revision:
            raise ValueError("PAGE_REPRESENTATION_REVISION_MISMATCH")
        if ident.layer_id != layer_id:
            raise ValueError("PAGE_LAYER_MISMATCH")
        if ident.scheme != SCHEME or ident.block_size != DEFAULT_BLOCK_SIZE:
            raise ValueError("PAGE_CODEC_LAYOUT_MISMATCH")

        # This validates the serialized header, codebook digest, dtypes, payload length,
        # and deterministic decode path. It does not authenticate the original source bytes.
        unpack_expert_page(page)
        count = math.prod(ident.source_shape)
        if count % DEFAULT_BLOCK_SIZE:
            raise ValueError("PAGE_ROLE_WEIGHT_COUNT_MUST_BE_BLOCK_ALIGNED_FOR_Q2_EXACT_ACCOUNTING")
        source_weights_by_expert[ident.expert_id] += count
        codec_payload_bytes += int(round(count * page.codec_bits_per_weight / 8.0))
        serialized_page_bytes += len(page.payload)
        identity_digests.append(ident.digest())
        payload_digests.append(page.payload_sha256)
        seen[key] = page

    if set(seen) != expected_pairs:
        missing = sorted(expected_pairs - set(seen))
        raise ValueError("SELECTED_PAGE_ROLE_COVERAGE_INCOMPLETE:" + repr(missing))
    if any(count != plan.parameters_per_expert for count in source_weights_by_expert.values()):
        raise ValueError("SELECTED_EXPERT_PARAMETER_COUNT_MISMATCH")

    concrete_codec_working_set = codec_payload_bytes + e8_codebook_bytes()
    codec_matches = concrete_codec_working_set == plan.selected_expert_working_set_bytes
    if not codec_matches:
        raise ValueError("Q2_CODEC_WORKING_SET_DOES_NOT_MATCH_CONCRETE_E8_PAGES")
    serialized_overhead = serialized_page_bytes - codec_payload_bytes
    if serialized_overhead <= 0:
        raise ValueError("EXPECTED_SERIALIZED_PAGE_OVERHEAD_MISSING")

    return SelectedE8PagePlanReceipt(
        version=VERSION,
        exact_parent_heads=(Q2_EXACT_HEAD, E8_EXACT_HEAD),
        exact_parent_runs=(Q2_EXACT_RUN, E8_EXACT_RUN),
        q2_plan_digest=plan.plan_digest,
        e8_representation_id=exact_rep.representation_id,
        e8_implementation_binding_digest=implementation_binding_digest(),
        codebook_digest=codebook_digest(),
        codebook_bank_resident_bytes=e8_codebook_bytes(),
        model_revision=model_revision,
        representation_revision=representation_revision,
        layer_id=layer_id,
        selected_expert_ids=selected,
        page_identity_digests=tuple(sorted(identity_digests)),
        page_payload_digests=tuple(sorted(payload_digests)),
        selected_source_weight_count=sum(source_weights_by_expert.values()),
        selected_codec_payload_bytes=codec_payload_bytes,
        selected_serialized_page_bytes=serialized_page_bytes,
        q2_selected_working_set_bytes=plan.selected_expert_working_set_bytes,
        q2_codec_working_set_matches_concrete_pages=True,
        serialized_page_overhead_bytes=serialized_overhead,
        serialized_working_set_matches_q2_plan=False,
        selected_page_roles_complete=True,
        selected_parameter_count_matches_plan=True,
        shared_codebook_matches_q2_bounded_companion=True,
        page_headers_accounted_in_q2_cache_budget=False,
        source_tensor_bytes_authenticated=False,
        planned_layout_executed_proven=False,
        selected_experts_actually_served_proven=False,
        physical_io_observed=False,
        model_execution_performed=False,
        glm53_quality_preserved_proven=False,
        general_performance_winner_proven=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        gate10_promoted=False,
        deployment_authorized=False,
    )


def portable_selected_e8_page_plan_receipt(**kwargs: object) -> dict[str, object]:
    receipt = bind_selected_e8_pages_to_q2_plan(**kwargs)
    payload = asdict(receipt)
    return {**payload, "receipt_digest": receipt.receipt_digest}
