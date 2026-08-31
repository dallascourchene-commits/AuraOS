"""Bind a deterministic ThinkPad storage plan into K27 ASTGE benchmark evidence.

PR599 owns a deterministic, non-executing NVMe/RAM residency plan. PR597 owns a
three-phase owner-host benchmark evidence contract whose request contains a
``storage_plan_digest`` but deliberately does not establish where that digest came
from or whether any named plan was executed.

This membrane closes only that identity seam. It derives the benchmark request's
storage-plan digest from an actual PR599 plan and later delegates benchmark admission
to PR597 unchanged. Carrying a plan digest into a request never proves the plan was
executed, that observed counters came from the planned backend, that OS/device caches
were cold, or that physical NVMe I/O / W4 / performance authority was established.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable

from tools.awj032.thinkpad_nvme_residency_plan import (
    HostStorageProfile,
    ResidencyPolicy,
    TensorSlice,
    ThinkPadResidencyPlan,
    build_thinkpad_residency_plan,
)
from tools.k27_astge_thinkpad_owner_host_benchmark import (
    ThinkPadASTGEBenchmarkPhaseSample,
    ThinkPadASTGEBenchmarkReceipt,
    ThinkPadASTGEBenchmarkRequest,
    admit_thinkpad_owner_host_benchmark,
)

SCHEMA = "AuraK27ASTGEPlanBoundThinkPadBenchmarkV1"
PR597_GENERATION = "28867452e25c0fe0159014c8bebc2ee18c925dd7"
PR599_GENERATION = "1a7e3ca521f43836c12cddb3cd5132264dce40da"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


@dataclass(frozen=True)
class PlanBoundBenchmarkRequest:
    plan: ThinkPadResidencyPlan
    request: ThinkPadASTGEBenchmarkRequest
    pr597_generation: str = PR597_GENERATION
    pr599_generation: str = PR599_GENERATION
    storage_plan_digest_derived_from_pr599: bool = True
    storage_plan_execution_observed: bool = False
    planned_backend_observed: bool = False
    host_profile_observed_by_this_membrane: bool = False
    physical_io_attested: bool = False
    producer_authenticated: bool = False
    w4_admitted: bool = False
    real_performance_winner_proven: bool = False
    effect_authority_proven: bool = False
    schema: str = SCHEMA

    def __post_init__(self) -> None:
        if type(self.plan) is not ThinkPadResidencyPlan:
            raise TypeError("EXACT_PR599_PLAN_REQUIRED")
        if type(self.request) is not ThinkPadASTGEBenchmarkRequest:
            raise TypeError("EXACT_PR597_REQUEST_REQUIRED")
        if self.schema != SCHEMA:
            raise ValueError("BINDING_SCHEMA_MISMATCH")
        if self.pr597_generation != PR597_GENERATION:
            raise ValueError("PR597_GENERATION_MISMATCH")
        if self.pr599_generation != PR599_GENERATION:
            raise ValueError("PR599_GENERATION_MISMATCH")
        if self.request.storage_plan_digest != self.plan.storage_plan_digest:
            raise ValueError("STORAGE_PLAN_DIGEST_RELATION_MISMATCH")
        if self.storage_plan_digest_derived_from_pr599 is not True:
            raise ValueError("PLAN_DIGEST_DERIVATION_REQUIRED")
        for name in (
            "storage_plan_execution_observed",
            "planned_backend_observed",
            "host_profile_observed_by_this_membrane",
            "physical_io_attested",
            "producer_authenticated",
            "w4_admitted",
            "real_performance_winner_proven",
            "effect_authority_proven",
        ):
            if getattr(self, name) is not False:
                raise ValueError("AUTHORITY_OR_EXECUTION_WIDENING:" + name)
        for name in (
            "physical_io_observed",
            "model_execution_observed",
            "producer_authenticated",
            "performance_claimed",
            "effect_authority_proven",
            "g2_admitted",
        ):
            if getattr(self.plan, name) is not False:
                raise ValueError("PR599_PLAN_CEILING_WIDENED:" + name)

    @property
    def binding_digest(self) -> str:
        return _digest(
            {
                "schema": self.schema,
                "pr597_generation": self.pr597_generation,
                "pr599_generation": self.pr599_generation,
                "plan": self.plan.to_dict(),
                "request": asdict(self.request),
                "storage_plan_digest_derived_from_pr599": self.storage_plan_digest_derived_from_pr599,
                "storage_plan_execution_observed": self.storage_plan_execution_observed,
                "planned_backend_observed": self.planned_backend_observed,
                "host_profile_observed_by_this_membrane": self.host_profile_observed_by_this_membrane,
                "physical_io_attested": self.physical_io_attested,
                "producer_authenticated": self.producer_authenticated,
                "w4_admitted": self.w4_admitted,
                "real_performance_winner_proven": self.real_performance_winner_proven,
                "effect_authority_proven": self.effect_authority_proven,
            }
        )


def build_plan_bound_benchmark_request(
    *,
    host_profile: HostStorageProfile,
    tensors: Iterable[TensorSlice],
    policy: ResidencyPolicy,
    graph_sha256: str,
    source_fixture_sha256: str,
    root_node_ids: tuple[int, ...],
    max_depth: int,
    iterations: int,
    implementation_generation: str,
    runner_generation: str,
    host_snapshot_digest: str,
    workload_label: str = "k27-astge-same-graph-cone-query",
) -> PlanBoundBenchmarkRequest:
    """Derive PR597's storage-plan field from a concrete PR599 plan.

    There is intentionally no public ``storage_plan_digest`` parameter.
    """
    plan = build_thinkpad_residency_plan(
        host_profile=host_profile,
        tensors=tensors,
        policy=policy,
    )
    request = ThinkPadASTGEBenchmarkRequest(
        graph_sha256=graph_sha256,
        source_fixture_sha256=source_fixture_sha256,
        root_node_ids=root_node_ids,
        max_depth=max_depth,
        iterations=iterations,
        implementation_generation=implementation_generation,
        runner_generation=runner_generation,
        host_snapshot_digest=host_snapshot_digest,
        storage_plan_digest=plan.storage_plan_digest,
        workload_label=workload_label,
    )
    return PlanBoundBenchmarkRequest(plan=plan, request=request)


def admit_plan_bound_benchmark_evidence(
    *,
    binding: PlanBoundBenchmarkRequest,
    samples: Iterable[ThinkPadASTGEBenchmarkPhaseSample],
    host_observation_id: str,
    runner_identity: str,
) -> dict[str, Any]:
    """Admit PR597 benchmark evidence while preserving PR599's nonexecution ceiling."""
    if type(binding) is not PlanBoundBenchmarkRequest:
        raise TypeError("EXACT_PLAN_BOUND_REQUEST_REQUIRED")
    # Reconstruct the closed relation so resealed/widened dataclasses cannot bypass it.
    binding.__post_init__()
    receipt: ThinkPadASTGEBenchmarkReceipt = admit_thinkpad_owner_host_benchmark(
        request=binding.request,
        samples=samples,
        host_observation_id=host_observation_id,
        runner_identity=runner_identity,
    )
    if receipt.physical_io_attested is not False:
        raise ValueError("PR597_PHYSICAL_IO_CEILING_WIDENED")
    if receipt.os_page_cache_cold_proven is not False:
        raise ValueError("PR597_OS_CACHE_COLDNESS_WIDENED")
    if receipt.device_cache_cold_proven is not False:
        raise ValueError("PR597_DEVICE_CACHE_COLDNESS_WIDENED")
    if receipt.producer_authenticated is not False:
        raise ValueError("PR597_PRODUCER_AUTH_WIDENED")
    if receipt.w4_admitted is not False:
        raise ValueError("PR597_W4_WIDENED")
    if receipt.real_performance_winner_proven is not False:
        raise ValueError("PR597_PERFORMANCE_WIDENED")
    if receipt.effect_authority_proven is not False:
        raise ValueError("PR597_EFFECT_WIDENED")

    out = {
        "schema": SCHEMA,
        "pr597_generation": PR597_GENERATION,
        "pr599_generation": PR599_GENERATION,
        "binding_digest": binding.binding_digest,
        "storage_plan_digest": binding.plan.storage_plan_digest,
        "benchmark_request_digest": binding.request.request_digest,
        "benchmark_receipt_digest": receipt.receipt_digest,
        "storage_plan_digest_bound_to_request": True,
        "storage_plan_execution_observed": False,
        "planned_backend_observed": False,
        "host_profile_observed_by_this_membrane": False,
        "benchmark_counters_prove_storage_plan_compliance": False,
        "process_cold_proves_os_page_cache_cold": False,
        "process_cold_proves_device_cache_cold": False,
        "physical_io_attested": False,
        "producer_authenticated": False,
        "w4_admitted": False,
        "real_performance_winner_proven": False,
        "effect_authority_proven": False,
        "authority": {
            "review_authorized": False,
            "mutation_authorized": False,
            "execution_authorized": False,
            "commit_authorized": False,
            "merge_authorized": False,
            "promotion_authorized": False,
            "provider_effect_authorized": False,
            "public_effect_authorized": False,
            "human_authority": False,
        },
    }
    out["receipt_identity"] = {
        "kind": "DIGEST",
        "algorithm_or_provider": "sha256",
        "canonicalization_profile": "JSON_SORT_KEYS_COMPACT_ASCII_V1",
        "scope_profile": SCHEMA,
        "value": _digest(out),
        "schema_version": "DigestOrImmutableIdentityV1-compatible",
    }
    return out
