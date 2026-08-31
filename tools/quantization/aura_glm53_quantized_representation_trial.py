#!/usr/bin/env python3
"""Evidence-only benchmark admission contract for quantized GLM-5.3 representations.

Derived from two non-self AWJ032 GLM work orders:
- coding benchmark / independent verification / Gate-10;
- adaptive backend / placement derby.

The contract prevents a smaller or faster quantized representation from becoming a
"winner" unless it is evaluated on the same frozen task corpus and acceptance criteria
and an independent verifier reproduces the declared quality consequence.

V2 additionally binds the exact static-weight byte domain so whole-model bytes cannot
be compared to routed-expert-only or other partial-component bytes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

VERSION = "AURA_GLM53_QUANTIZED_REPRESENTATION_TRIAL_V2"
BENCHMARK_WORK_ORDER_ID = "1rPU_cIF-AOVigT3Liu7k67GD3_UAtrlKxzxTtlb1QS8"
PLACEMENT_DERBY_WORK_ORDER_ID = "1lqFmTIV1WdgTU7KjHiTN7bNDY9CN7qIJPZdvEUw_kJw"

FULL_MODEL_STATIC = "FULL_MODEL_STATIC"
ROUTED_EXPERT_BANK_STATIC = "ROUTED_EXPERT_BANK_STATIC"
COMPONENT_MANIFEST_STATIC = "COMPONENT_MANIFEST_STATIC"
_ALLOWED_STATIC_WEIGHT_BYTE_DOMAINS = {
    FULL_MODEL_STATIC,
    ROUTED_EXPERT_BANK_STATIC,
    COMPONENT_MANIFEST_STATIC,
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _hex64(name: str, value: str) -> None:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError("INVALID_SHA256:" + name)


def _finite_nonnegative(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) or value < 0:
        raise ValueError("INVALID_NONNEGATIVE:" + name)


@dataclass(frozen=True)
class RepresentationIdentity:
    model_revision: str
    topology_digest: str
    representation_revision: str
    representation_digest: str
    nominal_bits_per_weight: float
    static_weight_bytes: int
    static_weight_byte_domain: str
    static_weight_byte_domain_digest: str
    quantized: bool

    def validate(self) -> None:
        if not self.model_revision.strip() or not self.representation_revision.strip():
            raise ValueError("REPRESENTATION_REVISION_REQUIRED")
        _hex64("topology_digest", self.topology_digest)
        _hex64("representation_digest", self.representation_digest)
        if not math.isfinite(self.nominal_bits_per_weight) or self.nominal_bits_per_weight <= 0:
            raise ValueError("INVALID_BPW")
        if type(self.static_weight_bytes) is not int or self.static_weight_bytes <= 0:
            raise ValueError("INVALID_STATIC_WEIGHT_BYTES")
        if self.static_weight_byte_domain not in _ALLOWED_STATIC_WEIGHT_BYTE_DOMAINS:
            raise ValueError("INVALID_STATIC_WEIGHT_BYTE_DOMAIN")
        _hex64("static_weight_byte_domain_digest", self.static_weight_byte_domain_digest)
        if type(self.quantized) is not bool:
            raise ValueError("QUANTIZED_BOOLEAN_REQUIRED")


@dataclass(frozen=True)
class QuantizedTrialRequest:
    task_corpus_digest: str
    acceptance_criteria_digest: str
    host_profile_digest: str
    context_tier: str
    batch_tier: str
    lifecycle_mode: str
    baseline: RepresentationIdentity
    candidate: RepresentationIdentity

    def validate(self) -> None:
        for name in ("task_corpus_digest", "acceptance_criteria_digest", "host_profile_digest"):
            _hex64(name, getattr(self, name))
        if self.context_tier not in {"SHORT", "MEDIUM", "LONG", "VERY_LONG"}:
            raise ValueError("INVALID_CONTEXT_TIER")
        if self.batch_tier not in {"SINGLE", "BATCH", "HYPERBATCH"}:
            raise ValueError("INVALID_BATCH_TIER")
        if self.lifecycle_mode not in {"INTERACTIVE", "BACKGROUND", "OVERNIGHT_AC"}:
            raise ValueError("INVALID_LIFECYCLE_MODE")
        self.baseline.validate()
        self.candidate.validate()
        if self.baseline.model_revision != self.candidate.model_revision:
            raise ValueError("MODEL_REVISION_MISMATCH")
        if self.baseline.topology_digest != self.candidate.topology_digest:
            raise ValueError("TOPOLOGY_MISMATCH")
        if self.baseline.static_weight_byte_domain != self.candidate.static_weight_byte_domain:
            raise ValueError("STATIC_WEIGHT_BYTE_DOMAIN_MISMATCH")
        if self.baseline.static_weight_byte_domain_digest != self.candidate.static_weight_byte_domain_digest:
            raise ValueError("STATIC_WEIGHT_BYTE_DOMAIN_MANIFEST_MISMATCH")
        if self.baseline.representation_digest == self.candidate.representation_digest:
            raise ValueError("DISTINCT_REPRESENTATIONS_REQUIRED")
        if self.candidate.quantized is not True:
            raise ValueError("CANDIDATE_MUST_BE_QUANTIZED")

    @property
    def request_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class TrialSample:
    request_digest: str
    representation_digest: str
    route_id: str
    task_count: int
    tasks_passed: int
    tasks_failed: int
    incorrect_edits: int
    hallucinated_apis: int
    source_currentness_violations: int
    repair_loops: int
    wall_seconds: float
    ttft_seconds: float
    generation_tokens_per_second: float
    bytes_read: int
    peak_ram_bytes: int
    peak_vram_bytes: int
    output_set_digest: str

    def validate(self) -> None:
        _hex64("request_digest", self.request_digest)
        _hex64("representation_digest", self.representation_digest)
        _hex64("output_set_digest", self.output_set_digest)
        if not self.route_id.strip():
            raise ValueError("ROUTE_ID_REQUIRED")
        for name in ("task_count", "tasks_passed", "tasks_failed", "incorrect_edits", "hallucinated_apis", "source_currentness_violations", "repair_loops", "bytes_read", "peak_ram_bytes", "peak_vram_bytes"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError("INVALID_INTEGER_METRIC:" + name)
        if self.task_count <= 0 or self.tasks_passed + self.tasks_failed != self.task_count:
            raise ValueError("TASK_ACCOUNTING_MISMATCH")
        for name in ("wall_seconds", "ttft_seconds", "generation_tokens_per_second"):
            _finite_nonnegative(name, getattr(self, name))
        if self.wall_seconds <= 0:
            raise ValueError("WALL_TIME_REQUIRED")

    @property
    def sample_digest(self) -> str:
        self.validate()
        return _sha(asdict(self))


@dataclass(frozen=True)
class IndependentVerification:
    request_digest: str
    candidate_sample_digest: str
    producer_identity: str
    verifier_identity: str
    reproduced_task_count: int
    reproduced_tasks_passed: int
    acceptance_criteria_reproduced: bool

    def validate(self) -> None:
        _hex64("request_digest", self.request_digest)
        _hex64("candidate_sample_digest", self.candidate_sample_digest)
        if not self.producer_identity.strip() or not self.verifier_identity.strip():
            raise ValueError("IDENTITY_REQUIRED")
        if self.producer_identity == self.verifier_identity:
            raise ValueError("SELF_REVIEW_IS_NOT_INDEPENDENT")
        if type(self.reproduced_task_count) is not int or self.reproduced_task_count <= 0:
            raise ValueError("INVALID_REPRO_TASK_COUNT")
        if type(self.reproduced_tasks_passed) is not int or not 0 <= self.reproduced_tasks_passed <= self.reproduced_task_count:
            raise ValueError("INVALID_REPRO_PASS_COUNT")
        if type(self.acceptance_criteria_reproduced) is not bool:
            raise ValueError("REPRO_BOOLEAN_REQUIRED")


@dataclass(frozen=True)
class QuantizedRepresentationComparison:
    version: str
    parent_artifact_ids: tuple[str, str]
    request_digest: str
    baseline_sample_digest: str
    candidate_sample_digest: str
    independent_verifier_identity: str
    static_weight_byte_domain: str
    static_weight_byte_domain_digest: str
    quality_pass_delta: int
    candidate_quality_retained_on_frozen_corpus: bool
    independent_acceptance_reproduced: bool
    candidate_smaller_static_weights: bool
    candidate_faster_wall_time: bool
    candidate_lower_peak_memory: bool
    candidate_tradeoff_class: str
    exact_causal_timing_comparison_claimed: bool
    general_performance_winner_proven: bool
    coding_quality_generalized_beyond_frozen_corpus: bool
    owner_host_identity_authenticated: bool
    physical_io_attributed_exclusively: bool
    gate10_ready_for_owner_promotion: bool
    native_private_transformer_kv_accessed: bool
    semantic_k27_authority_minted: bool
    deployment_authorized: bool

    @property
    def comparison_digest(self) -> str:
        return _sha(asdict(self))


def compare_quantized_representation(
    *,
    request: QuantizedTrialRequest,
    baseline_sample: TrialSample,
    candidate_sample: TrialSample,
    independent_verification: IndependentVerification,
) -> QuantizedRepresentationComparison:
    request.validate()
    baseline_sample.validate()
    candidate_sample.validate()
    independent_verification.validate()
    req = request.request_digest
    if baseline_sample.request_digest != req or candidate_sample.request_digest != req or independent_verification.request_digest != req:
        raise ValueError("REQUEST_BINDING_MISMATCH")
    if baseline_sample.representation_digest != request.baseline.representation_digest:
        raise ValueError("BASELINE_REPRESENTATION_MISMATCH")
    if candidate_sample.representation_digest != request.candidate.representation_digest:
        raise ValueError("CANDIDATE_REPRESENTATION_MISMATCH")
    if baseline_sample.task_count != candidate_sample.task_count:
        raise ValueError("TASK_CORPUS_CARDINALITY_MISMATCH")
    if independent_verification.candidate_sample_digest != candidate_sample.sample_digest:
        raise ValueError("VERIFIER_SAMPLE_BINDING_MISMATCH")
    if independent_verification.reproduced_task_count != candidate_sample.task_count:
        raise ValueError("INDEPENDENT_REPRO_CORPUS_MISMATCH")

    quality_delta = candidate_sample.tasks_passed - baseline_sample.tasks_passed
    independent_reproduced = (
        independent_verification.acceptance_criteria_reproduced
        and independent_verification.reproduced_tasks_passed == candidate_sample.tasks_passed
    )
    quality_retained = (
        quality_delta >= 0
        and candidate_sample.incorrect_edits <= baseline_sample.incorrect_edits
        and candidate_sample.hallucinated_apis <= baseline_sample.hallucinated_apis
        and candidate_sample.source_currentness_violations <= baseline_sample.source_currentness_violations
        and independent_reproduced
    )
    smaller = request.candidate.static_weight_bytes < request.baseline.static_weight_bytes
    faster = candidate_sample.wall_seconds < baseline_sample.wall_seconds
    lower_memory = (
        candidate_sample.peak_ram_bytes + candidate_sample.peak_vram_bytes
        < baseline_sample.peak_ram_bytes + baseline_sample.peak_vram_bytes
    )

    if quality_retained and smaller and (faster or lower_memory):
        tradeoff = "FROZEN_CORPUS_CANDIDATE_DOMINATES_MEASURED_AXES"
    elif quality_retained and smaller:
        tradeoff = "QUALITY_RETAINED_MEMORY_TRADEOFF"
    elif quality_retained:
        tradeoff = "QUALITY_RETAINED_NO_RESOURCE_WIN"
    elif smaller or faster or lower_memory:
        tradeoff = "RESOURCE_GAIN_WITH_QUALITY_REGRESSION"
    else:
        tradeoff = "NO_MEASURED_ADVANTAGE"

    return QuantizedRepresentationComparison(
        version=VERSION,
        parent_artifact_ids=(BENCHMARK_WORK_ORDER_ID, PLACEMENT_DERBY_WORK_ORDER_ID),
        request_digest=req,
        baseline_sample_digest=baseline_sample.sample_digest,
        candidate_sample_digest=candidate_sample.sample_digest,
        independent_verifier_identity=independent_verification.verifier_identity,
        static_weight_byte_domain=request.baseline.static_weight_byte_domain,
        static_weight_byte_domain_digest=request.baseline.static_weight_byte_domain_digest,
        quality_pass_delta=quality_delta,
        candidate_quality_retained_on_frozen_corpus=quality_retained,
        independent_acceptance_reproduced=independent_reproduced,
        candidate_smaller_static_weights=smaller,
        candidate_faster_wall_time=faster,
        candidate_lower_peak_memory=lower_memory,
        candidate_tradeoff_class=tradeoff,
        exact_causal_timing_comparison_claimed=False,
        general_performance_winner_proven=False,
        coding_quality_generalized_beyond_frozen_corpus=False,
        owner_host_identity_authenticated=False,
        physical_io_attributed_exclusively=False,
        gate10_ready_for_owner_promotion=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        deployment_authorized=False,
    )
