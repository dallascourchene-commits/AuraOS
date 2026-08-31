#!/usr/bin/env python3
"""Bind an exact packed-expert quantization plan into a quantized trial identity.

Q4 consumes two exact-green non-self parents:
- Q2 packed-expert mixed-precision planning;
- Q3 frozen-corpus quantized-representation trial admission.

It closes an identity seam only.  The candidate representation digest becomes a
function of the exact Q2 plan, expert assignment, layout projection, representation
revision, and implementation digests for every representation used by that plan.
Q3 then binds the exact trial sample and independent verification to that digest.

This does not prove that the planned layout was executed, that selected experts were
actually served, that companion metadata was physically loaded, or that physical I/O
or model execution occurred.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Mapping

from tools.quantization.aura_glm53_packed_expert_quantization_plan import (
    PACKED_EXPERT_ARTIFACT_ID,
    LIFECYCLE_POLICY_ARTIFACT_ID,
    IndexedQuantizedRepresentation,
    PackedExpertQuantizationPlan,
    PackedExpertQuantizationRequest,
    build_packed_expert_quantization_plan,
)
from tools.quantization.aura_glm53_quantized_representation_trial import (
    BENCHMARK_WORK_ORDER_ID,
    PLACEMENT_DERBY_WORK_ORDER_ID,
    IndependentVerification,
    QuantizedRepresentationComparison,
    QuantizedTrialRequest,
    RepresentationIdentity,
    TrialSample,
    compare_quantized_representation,
)

VERSION = "AURA_GLM53_PLAN_CONFORMING_QUANTIZED_TRIAL_V1"
MANIFEST_VERSION = "AURA_GLM53_PLAN_BOUND_CANDIDATE_REPRESENTATION_V1"
Q2_EXACT_HEAD = "cb9f50fc2fd05006f4f5af0a2f143f2c74aee62f"
Q2_EXACT_RUN = 33367433407
Q3_EXACT_HEAD = "c4f526714e89fc36c55230c55ab2f704695212dc"
Q3_EXACT_RUN = 33367951206
Q4_CONVERGENCE_COMMIT = "79c0d416c04874b1fb0a75b714cb39259d572fc2"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hex64(name: str, value: str) -> None:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("INVALID_SHA256:" + name)


def _layout_projection(plan: PackedExpertQuantizationPlan) -> dict[str, object]:
    if plan.version != "AURA_GLM53_PACKED_EXPERT_QUANTIZATION_PLAN_V1":
        raise ValueError("Q2_PLAN_VERSION_MISMATCH")
    if plan.parent_artifact_ids != (PACKED_EXPERT_ARTIFACT_ID, LIFECYCLE_POLICY_ARTIFACT_ID):
        raise ValueError("Q2_PARENT_IDENTITY_MISMATCH")
    if plan.packed_weight_first_axis_sliceability_required is not True:
        raise ValueError("Q2_SLICEABILITY_INVARIANT_WIDENED")
    if plan.quantization_companion_identity_bound is not True:
        raise ValueError("Q2_COMPANION_IDENTITY_INVARIANT_WIDENED")
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
    return {
        "plan_digest": plan.plan_digest,
        "num_experts": plan.num_experts,
        "parameters_per_expert": plan.parameters_per_expert,
        "selected_expert_ids": plan.selected_expert_ids,
        "selected_contiguous_runs": plan.selected_contiguous_runs,
        "representation_bpw_by_id": plan.representation_bpw_by_id,
        "expert_representation_ids": plan.expert_representation_ids,
        "full_routed_expert_static_bytes": plan.full_routed_expert_static_bytes,
        "selected_expert_working_set_bytes": plan.selected_expert_working_set_bytes,
        "working_set_fits_cache_budget": plan.working_set_fits_cache_budget,
        "lifecycle_mode": plan.lifecycle_mode,
        "bank_companion_loaded_as_bounded_exception": plan.bank_companion_loaded_as_bounded_exception,
    }


def _assignment_digest(plan: PackedExpertQuantizationPlan) -> str:
    return _sha({"expert_representation_ids": plan.expert_representation_ids})


def _weighted_routed_expert_bpw(plan: PackedExpertQuantizationPlan) -> float:
    bpw = dict(plan.representation_bpw_by_id)
    return sum(bpw[rid] for rid in plan.expert_representation_ids) / plan.num_experts


@dataclass(frozen=True)
class PlanBoundCandidateRepresentation:
    version: str
    q2_plan_digest: str
    q2_layout_projection_digest: str
    q2_expert_assignment_digest: str
    representation_revision: str
    implementation_digests_by_representation_id: tuple[tuple[str, str], ...]

    def validate_against(self, plan: PackedExpertQuantizationPlan) -> None:
        if self.version != MANIFEST_VERSION:
            raise ValueError("MANIFEST_VERSION_MISMATCH")
        if not self.representation_revision.strip():
            raise ValueError("REPRESENTATION_REVISION_REQUIRED")
        projection = _layout_projection(plan)
        if self.q2_plan_digest != plan.plan_digest:
            raise ValueError("MANIFEST_PLAN_DIGEST_MISMATCH")
        if self.q2_layout_projection_digest != _sha(projection):
            raise ValueError("MANIFEST_LAYOUT_PROJECTION_MISMATCH")
        if self.q2_expert_assignment_digest != _assignment_digest(plan):
            raise ValueError("MANIFEST_ASSIGNMENT_DIGEST_MISMATCH")
        bindings = dict(self.implementation_digests_by_representation_id)
        if len(bindings) != len(self.implementation_digests_by_representation_id):
            raise ValueError("DUPLICATE_REPRESENTATION_BINDING")
        used = set(plan.expert_representation_ids)
        if set(bindings) != used:
            raise ValueError("REPRESENTATION_BINDING_SET_MISMATCH")
        for rep_id, digest in self.implementation_digests_by_representation_id:
            if not rep_id.strip():
                raise ValueError("REPRESENTATION_BINDING_ID_REQUIRED")
            _hex64("implementation_digest:" + rep_id, digest)

    @property
    def representation_digest(self) -> str:
        return _sha(asdict(self))


def build_plan_bound_candidate_representation(
    *,
    plan: PackedExpertQuantizationPlan,
    representation_revision: str,
    implementation_digests_by_representation_id: Mapping[str, str],
) -> PlanBoundCandidateRepresentation:
    projection = _layout_projection(plan)
    used = set(plan.expert_representation_ids)
    if set(implementation_digests_by_representation_id) != used:
        raise ValueError("REPRESENTATION_BINDING_SET_MISMATCH")
    ordered: list[tuple[str, str]] = []
    for rep_id in sorted(used):
        digest = implementation_digests_by_representation_id[rep_id]
        _hex64("implementation_digest:" + rep_id, digest)
        ordered.append((rep_id, digest))
    manifest = PlanBoundCandidateRepresentation(
        version=MANIFEST_VERSION,
        q2_plan_digest=plan.plan_digest,
        q2_layout_projection_digest=_sha(projection),
        q2_expert_assignment_digest=_assignment_digest(plan),
        representation_revision=representation_revision,
        implementation_digests_by_representation_id=tuple(ordered),
    )
    manifest.validate_against(plan)
    return manifest


def plan_bound_candidate_identity(
    *,
    plan: PackedExpertQuantizationPlan,
    model_revision: str,
    topology_digest: str,
    representation_revision: str,
    implementation_digests_by_representation_id: Mapping[str, str],
    nominal_bits_per_weight: float,
    static_weight_bytes: int,
) -> tuple[PlanBoundCandidateRepresentation, RepresentationIdentity]:
    manifest = build_plan_bound_candidate_representation(
        plan=plan,
        representation_revision=representation_revision,
        implementation_digests_by_representation_id=implementation_digests_by_representation_id,
    )
    identity = RepresentationIdentity(
        model_revision=model_revision,
        topology_digest=topology_digest,
        representation_revision=representation_revision,
        representation_digest=manifest.representation_digest,
        nominal_bits_per_weight=nominal_bits_per_weight,
        static_weight_bytes=static_weight_bytes,
        quantized=True,
    )
    identity.validate()
    return manifest, identity


@dataclass(frozen=True)
class PlanConformingQuantizedTrialReceipt:
    version: str
    exact_parent_heads: tuple[str, str]
    exact_parent_runs: tuple[int, int]
    q2_plan_digest: str
    q2_layout_projection_digest: str
    q2_expert_assignment_digest: str
    plan_bound_candidate_representation_digest: str
    candidate_representation_revision: str
    candidate_implementation_binding_digest: str
    trial_request_digest: str
    candidate_sample_digest: str
    q3_comparison_digest: str
    selected_expert_ids: tuple[int, ...]
    selected_contiguous_runs: tuple[tuple[int, int], ...]
    selected_expert_working_set_bytes: int
    full_routed_expert_static_bytes: int
    planned_routed_expert_effective_bpw: float
    q3_candidate_nominal_bpw: float
    q3_candidate_static_weight_bytes: int
    lifecycle_mode: str
    candidate_tradeoff_class: str
    candidate_quality_retained_on_frozen_corpus: bool
    independent_acceptance_reproduced: bool
    plan_bound_candidate_identity_admitted: bool
    exact_trial_sample_bound_to_plan_identity: bool
    whole_model_static_bytes_derived_from_routed_expert_plan: bool
    planned_layout_executed_proven: bool
    selected_experts_actually_served_proven: bool
    companion_layout_actually_loaded_proven: bool
    implementation_bytes_authenticated: bool
    physical_io_attributed_exclusively: bool
    exact_causal_timing_comparison_claimed: bool
    general_performance_winner_proven: bool
    coding_quality_generalized_beyond_frozen_corpus: bool
    owner_host_identity_authenticated: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    gate10_ready_for_owner_promotion: bool
    deployment_authorized: bool

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def _verify_q3_ceiling(comparison: QuantizedRepresentationComparison) -> None:
    if comparison.parent_artifact_ids != (BENCHMARK_WORK_ORDER_ID, PLACEMENT_DERBY_WORK_ORDER_ID):
        raise ValueError("Q3_PARENT_IDENTITY_MISMATCH")
    for name in (
        "exact_causal_timing_comparison_claimed",
        "general_performance_winner_proven",
        "coding_quality_generalized_beyond_frozen_corpus",
        "owner_host_identity_authenticated",
        "physical_io_attributed_exclusively",
        "gate10_ready_for_owner_promotion",
        "native_private_transformer_kv_accessed",
        "semantic_k27_authority_minted",
        "deployment_authorized",
    ):
        if getattr(comparison, name) is not False:
            raise ValueError("Q3_CLAIM_CEILING_WIDENED:" + name)


def bind_plan_conforming_quantized_trial(
    *,
    plan_request: PackedExpertQuantizationRequest,
    representations: Mapping[str, IndexedQuantizedRepresentation],
    candidate_manifest: PlanBoundCandidateRepresentation,
    trial_request: QuantizedTrialRequest,
    baseline_sample: TrialSample,
    candidate_sample: TrialSample,
    independent_verification: IndependentVerification,
) -> PlanConformingQuantizedTrialReceipt:
    plan = build_packed_expert_quantization_plan(request=plan_request, representations=representations)
    candidate_manifest.validate_against(plan)
    trial_request.validate()
    if trial_request.lifecycle_mode != plan.lifecycle_mode:
        raise ValueError("PLAN_TRIAL_LIFECYCLE_MISMATCH")
    if trial_request.candidate.representation_revision != candidate_manifest.representation_revision:
        raise ValueError("CANDIDATE_REVISION_NOT_PLAN_BOUND")
    if trial_request.candidate.representation_digest != candidate_manifest.representation_digest:
        raise ValueError("CANDIDATE_DIGEST_NOT_PLAN_BOUND")

    comparison = compare_quantized_representation(
        request=trial_request,
        baseline_sample=baseline_sample,
        candidate_sample=candidate_sample,
        independent_verification=independent_verification,
    )
    _verify_q3_ceiling(comparison)

    projection = _layout_projection(plan)
    implementation_binding_digest = _sha(
        {"implementation_digests_by_representation_id": candidate_manifest.implementation_digests_by_representation_id}
    )
    return PlanConformingQuantizedTrialReceipt(
        version=VERSION,
        exact_parent_heads=(Q2_EXACT_HEAD, Q3_EXACT_HEAD),
        exact_parent_runs=(Q2_EXACT_RUN, Q3_EXACT_RUN),
        q2_plan_digest=plan.plan_digest,
        q2_layout_projection_digest=_sha(projection),
        q2_expert_assignment_digest=_assignment_digest(plan),
        plan_bound_candidate_representation_digest=candidate_manifest.representation_digest,
        candidate_representation_revision=candidate_manifest.representation_revision,
        candidate_implementation_binding_digest=implementation_binding_digest,
        trial_request_digest=trial_request.request_digest,
        candidate_sample_digest=candidate_sample.sample_digest,
        q3_comparison_digest=comparison.comparison_digest,
        selected_expert_ids=plan.selected_expert_ids,
        selected_contiguous_runs=plan.selected_contiguous_runs,
        selected_expert_working_set_bytes=plan.selected_expert_working_set_bytes,
        full_routed_expert_static_bytes=plan.full_routed_expert_static_bytes,
        planned_routed_expert_effective_bpw=_weighted_routed_expert_bpw(plan),
        q3_candidate_nominal_bpw=trial_request.candidate.nominal_bits_per_weight,
        q3_candidate_static_weight_bytes=trial_request.candidate.static_weight_bytes,
        lifecycle_mode=plan.lifecycle_mode,
        candidate_tradeoff_class=comparison.candidate_tradeoff_class,
        candidate_quality_retained_on_frozen_corpus=comparison.candidate_quality_retained_on_frozen_corpus,
        independent_acceptance_reproduced=comparison.independent_acceptance_reproduced,
        plan_bound_candidate_identity_admitted=True,
        exact_trial_sample_bound_to_plan_identity=True,
        whole_model_static_bytes_derived_from_routed_expert_plan=False,
        planned_layout_executed_proven=False,
        selected_experts_actually_served_proven=False,
        companion_layout_actually_loaded_proven=False,
        implementation_bytes_authenticated=False,
        physical_io_attributed_exclusively=False,
        exact_causal_timing_comparison_claimed=False,
        general_performance_winner_proven=False,
        coding_quality_generalized_beyond_frozen_corpus=False,
        owner_host_identity_authenticated=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        gate10_ready_for_owner_promotion=False,
        deployment_authorized=False,
    )


def portable_plan_conforming_receipt(**kwargs: object) -> dict[str, object]:
    receipt = bind_plan_conforming_quantized_trial(**kwargs)
    payload = asdict(receipt)
    return {**payload, "receipt_digest": receipt.receipt_digest}
