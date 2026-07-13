"""Unified telemetry contracts for Aura's Model Cognome.

This module composes the existing usage normalizer, versioned pricing registry,
ModelObservation, and empirical cost ledger. It does not select models, call
providers, or mutate route policy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import time
from typing import Any, Callable, Mapping, Protocol

from aura_model_cognome import (
    BEHAVIORAL_SURROGATE,
    ModelObservation,
    stable_digest,
    stable_id,
)
from aura_pricing_registry import (
    COST_LOCAL_ZERO,
    COST_MEASURED,
    COST_UNKNOWN,
    PricingRegistry,
)
from aura_usage_normalizer import (
    DERIVED,
    MEASURED,
    UNAVAILABLE,
    normalize_usage,
)

TELEMETRY_VERSION = "AURA_MODEL_COGNOME_TELEMETRY_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False


class CognomeObservationStore(Protocol):
    def get_endpoint(self, profile_id: str) -> dict[str, Any] | None: ...
    def record_observation(self, observation: ModelObservation) -> str: ...
    def record_price_snapshot(self, snapshot: Mapping[str, Any]) -> str: ...


class EmpiricalLedger(Protocol):
    def record_run(self, run: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class TelemetryLinkage:
    correlation_id: str
    profile_id: str
    call_id: str
    cost_run_id: str
    route_decision_id: str = ""
    task_context_id: str = ""
    experience_id: str = ""
    comparison_id: str = ""
    attempt_index: int = 0
    fallback_index: int = 0

    @classmethod
    def create(
        cls,
        *,
        correlation_id: str,
        profile_id: str,
        route_decision_id: str = "",
        task_context_id: str = "",
        experience_id: str = "",
        comparison_id: str = "",
        attempt_index: int = 0,
        fallback_index: int = 0,
        event_nonce: str = "",
    ) -> "TelemetryLinkage":
        correlation = str(correlation_id).strip()
        profile = str(profile_id).strip()
        if not correlation:
            raise ValueError("correlation_id must not be empty")
        if not profile:
            raise ValueError("profile_id must not be empty")
        if attempt_index < 0 or fallback_index < 0:
            raise ValueError("attempt and fallback indexes must be non-negative")
        basis = {
            "correlation_id": correlation,
            "profile_id": profile,
            "route_decision_id": str(route_decision_id),
            "task_context_id": str(task_context_id),
            "attempt_index": int(attempt_index),
            "fallback_index": int(fallback_index),
            "event_nonce": str(event_nonce),
        }
        call_id = stable_id("call", basis)
        return cls(
            correlation_id=correlation,
            profile_id=profile,
            call_id=call_id,
            cost_run_id=stable_id("cost-run", {"call_id": call_id}),
            route_decision_id=str(route_decision_id),
            task_context_id=str(task_context_id),
            experience_id=str(experience_id),
            comparison_id=str(comparison_id or correlation),
            attempt_index=int(attempt_index),
            fallback_index=int(fallback_index),
        )


@dataclass(frozen=True)
class StageTimings:
    intent_compilation_ms: float | None = None
    capability_resolution_ms: float | None = None
    router_decision_ms: float | None = None
    queue_ms: float | None = None
    connect_ms: float | None = None
    time_to_first_token_ms: float | None = None
    generation_ms: float | None = None
    tool_execution_ms: float | None = None
    verifier_ms: float | None = None
    retry_ms: float | None = None
    fallback_ms: float | None = None
    machine_completion_ms: float | None = None
    human_wait_ms: float | None = None

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if value is None:
                continue
            numeric = float(value)
            if not math.isfinite(numeric) or numeric < 0:
                raise ValueError(f"{name} must be a finite non-negative number")

    def stage_sum_ms(self) -> float | None:
        values = (
            self.intent_compilation_ms,
            self.capability_resolution_ms,
            self.router_decision_ms,
            self.queue_ms,
            self.connect_ms,
            self.time_to_first_token_ms,
            self.generation_ms,
            self.tool_execution_ms,
            self.verifier_ms,
            self.retry_ms,
            self.fallback_ms,
        )
        present = [float(value) for value in values if value is not None]
        return round(sum(present), 6) if present else None

    def machine_total_ms(self) -> float | None:
        if self.machine_completion_ms is not None:
            return float(self.machine_completion_ms)
        return self.stage_sum_ms()

    def time_to_verified_outcome_ms(self, verifier_pass: bool | None) -> float | None:
        return self.machine_total_ms() if verifier_pass is True else None

    def workflow_wall_ms(self) -> float | None:
        machine = self.machine_total_ms()
        if machine is None and self.human_wait_ms is None:
            return None
        return round(float(machine or 0.0) + float(self.human_wait_ms or 0.0), 6)

    def to_dict(self) -> dict[str, float | None]:
        return {
            "intent_compilation_ms": self.intent_compilation_ms,
            "capability_resolution_ms": self.capability_resolution_ms,
            "router_decision_ms": self.router_decision_ms,
            "queue_ms": self.queue_ms,
            "connect_ms": self.connect_ms,
            "time_to_first_token_ms": self.time_to_first_token_ms,
            "generation_ms": self.generation_ms,
            "tool_execution_ms": self.tool_execution_ms,
            "verifier_ms": self.verifier_ms,
            "retry_ms": self.retry_ms,
            "fallback_ms": self.fallback_ms,
            "machine_completion_ms": self.machine_completion_ms,
            "human_wait_ms": self.human_wait_ms,
        }


@dataclass(frozen=True)
class TelemetryPacket:
    linkage: TelemetryLinkage
    observation: ModelObservation
    normalized_usage: dict[str, Any]
    cost_result: dict[str, Any]
    cost_run: dict[str, Any]
    logger_record: dict[str, Any]
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": TELEMETRY_VERSION,
            "linkage": self.linkage.__dict__,
            "observation": self.observation.to_dict(),
            "normalized_usage": dict(self.normalized_usage),
            "cost_result": dict(self.cost_result),
            "cost_run": dict(self.cost_run),
            "logger_record": dict(self.logger_record),
            "created_at": self.created_at,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }


def _field_measurement_classes(normalized: Mapping[str, Any]) -> dict[str, str]:
    present = set(str(item) for item in normalized.get("raw_usage_fields_present", []) or [])
    warnings = " ".join(str(item).lower() for item in normalized.get("usage_parse_warnings", []) or [])
    classes: dict[str, str] = {}
    for name in (
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_creation_tokens",
        "reasoning_tokens",
        "tool_input_tokens",
        "tool_output_tokens",
        "energy_joules",
        "runtime_ms",
    ):
        value = normalized.get(name)
        classes[name] = MEASURED if value is not None and name in present else (
            MEASURED if value is not None and name in {"energy_joules", "runtime_ms"} else UNAVAILABLE
        )
    if normalized.get("total_tokens") is None:
        classes["total_tokens"] = UNAVAILABLE
    elif "derived" in warnings:
        classes["total_tokens"] = DERIVED
    else:
        classes["total_tokens"] = MEASURED
    if normalized.get("provider_reported_cost_usd") is None:
        classes["provider_reported_cost_usd"] = UNAVAILABLE
    else:
        classes["provider_reported_cost_usd"] = MEASURED
    return classes


def normalize_usage_with_provenance(
    raw_usage: Mapping[str, Any] | None,
    *,
    provider: str,
    model: str,
) -> dict[str, Any]:
    normalized = normalize_usage(dict(raw_usage or {}), provider=provider, model=model)
    normalized["field_measurement_classes"] = _field_measurement_classes(normalized)
    normalized["normalizer_version"] = "AURA_USAGE_NORMALIZER_V1"
    return normalized


def calculate_normalized_cost(
    normalized_usage: Mapping[str, Any],
    *,
    pricing_registry: PricingRegistry,
) -> dict[str, Any]:
    provider = str(normalized_usage.get("provider", ""))
    model = str(normalized_usage.get("model", ""))
    provider_cost = normalized_usage.get("provider_reported_cost_usd")
    if provider == "local":
        return {
            "cost_usd": 0.0,
            "cost_status": COST_LOCAL_ZERO,
            "price_snapshot": None,
            "price_snapshot_digest": "",
            "calculation_detail": "local_zero_api_cost",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    if provider_cost is not None:
        result = pricing_registry.calculate_cost(
            model=model,
            input_tokens=normalized_usage.get("input_tokens"),
            output_tokens=normalized_usage.get("output_tokens"),
            cached_input_tokens=normalized_usage.get("cached_input_tokens"),
            cache_creation_tokens=normalized_usage.get("cache_creation_tokens"),
            provider_billed_cost=float(provider_cost),
        )
    elif normalized_usage.get("input_tokens") is None or normalized_usage.get("output_tokens") is None:
        result = {
            "cost_usd": None,
            "cost_status": COST_UNKNOWN,
            "price_snapshot": None,
            "calculation_detail": "incomplete_token_measurement",
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
    else:
        result = pricing_registry.calculate_cost(
            model=model,
            input_tokens=normalized_usage.get("input_tokens"),
            output_tokens=normalized_usage.get("output_tokens"),
            cached_input_tokens=normalized_usage.get("cached_input_tokens"),
            cache_creation_tokens=normalized_usage.get("cache_creation_tokens"),
        )
    result = dict(result)
    snapshot = result.get("price_snapshot")
    result["price_snapshot_digest"] = stable_digest(snapshot) if snapshot else ""
    return result


def build_telemetry_packet(
    *,
    linkage: TelemetryLinkage,
    provider: str,
    model: str,
    raw_usage: Mapping[str, Any] | None,
    timings: StageTimings,
    pricing_registry: PricingRegistry,
    policy_mode: str = "",
    verifier_pass: bool | None = None,
    tests_passed: int | None = None,
    tests_failed: int | None = None,
    format_valid: bool | None = None,
    scope_violation_count: int = 0,
    repair_attempt_count: int = 0,
    human_review_status: str = "",
    failure_class: str = "",
    evidence_class: str = BEHAVIORAL_SURROGATE,
    shadow_only: bool = False,
    started_at: float | None = None,
    completed_at: float | None = None,
    extra_evidence: Mapping[str, Any] | None = None,
) -> TelemetryPacket:
    normalized = normalize_usage_with_provenance(
        raw_usage,
        provider=provider,
        model=model,
    )
    cost_result = calculate_normalized_cost(normalized, pricing_registry=pricing_registry)
    generation_ms = timings.generation_ms
    output_tokens = normalized.get("output_tokens")
    output_tps = None
    if output_tokens is not None and generation_ms is not None and generation_ms > 0:
        output_tps = round(float(output_tokens) / (float(generation_ms) / 1000.0), 6)
    created = time.time() if completed_at is None else float(completed_at)
    machine_total = timings.machine_total_ms()
    observation = ModelObservation.create(
        profile_id=linkage.profile_id,
        call_id=linkage.call_id,
        created_at=created,
        route_decision_id=linkage.route_decision_id,
        task_context_id=linkage.task_context_id,
        cost_run_id=linkage.cost_run_id,
        experience_id=linkage.experience_id,
        policy_mode=policy_mode,
        attempt_index=linkage.attempt_index,
        fallback_index=linkage.fallback_index,
        shadow_only=shadow_only,
        input_tokens=normalized.get("input_tokens"),
        cached_input_tokens=normalized.get("cached_input_tokens"),
        output_tokens=normalized.get("output_tokens"),
        reasoning_tokens=normalized.get("reasoning_tokens"),
        cost_usd=cost_result.get("cost_usd"),
        cost_status=str(cost_result.get("cost_status", COST_UNKNOWN)),
        price_snapshot_digest=str(cost_result.get("price_snapshot_digest", "")),
        usage_measurement_class=str(normalized.get("measurement_class", UNAVAILABLE)),
        field_measurement_classes=dict(normalized.get("field_measurement_classes", {})),
        energy_joules=normalized.get("energy_joules"),
        queue_ms=timings.queue_ms,
        connect_ms=timings.connect_ms,
        time_to_first_token_ms=timings.time_to_first_token_ms,
        generation_ms=timings.generation_ms,
        tool_execution_ms=timings.tool_execution_ms,
        verifier_ms=timings.verifier_ms,
        retry_ms=timings.retry_ms,
        fallback_ms=timings.fallback_ms,
        end_to_end_ms=machine_total,
        time_to_verified_outcome_ms=timings.time_to_verified_outcome_ms(verifier_pass),
        output_tokens_per_second=output_tps,
        verifier_pass=verifier_pass,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        format_valid=format_valid,
        scope_violation_count=scope_violation_count,
        repair_attempt_count=repair_attempt_count,
        human_review_status=human_review_status,
        failure_class=failure_class,
        measurement_class=str(normalized.get("measurement_class", UNAVAILABLE)),
        evidence_class=evidence_class,
        extra_evidence={
            "correlation_id": linkage.correlation_id,
            "comparison_id": linkage.comparison_id,
            "timings": timings.to_dict(),
            "workflow_wall_ms": timings.workflow_wall_ms(),
            "usage_parse_warnings": normalized.get("usage_parse_warnings", []),
            **dict(extra_evidence or {}),
        },
    )
    began = float(started_at) if started_at is not None else (
        created - (float(machine_total) / 1000.0) if machine_total is not None else created
    )
    cost_run = {
        "run_id": linkage.cost_run_id,
        "comparison_id": linkage.comparison_id,
        "parent_run_id": "",
        "task_id": linkage.task_context_id,
        "arena_id": "model_cognome",
        "plan_phase_hash": linkage.route_decision_id,
        "objective_hash": "",
        "mode": policy_mode,
        "provider": provider,
        "model": model,
        "measurement_class": normalized.get("measurement_class", UNAVAILABLE),
        "started_at": began,
        "completed_at": created,
        "input_tokens": normalized.get("input_tokens"),
        "output_tokens": normalized.get("output_tokens"),
        "cached_input_tokens": normalized.get("cached_input_tokens"),
        "cache_creation_tokens": normalized.get("cache_creation_tokens"),
        "reasoning_tokens": normalized.get("reasoning_tokens"),
        "provider_cost_usd": (
            cost_result.get("cost_usd") if cost_result.get("cost_status") == COST_MEASURED else None
        ),
        "calculated_cost_usd": (
            cost_result.get("cost_usd") if cost_result.get("cost_status") != COST_MEASURED else None
        ),
        "latency_ms": machine_total,
        "time_to_first_token_ms": timings.time_to_first_token_ms,
        "model_call_count": 1,
        "tool_call_count": 1 if timings.tool_execution_ms is not None else 0,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "verification_status": (
            "PASSED" if verifier_pass is True else "FAILED" if verifier_pass is False else "UNVERIFIED"
        ),
        "scope_violation_count": scope_violation_count,
        "repair_attempt_count": repair_attempt_count,
        "human_review_status": human_review_status,
        "telemetry_warnings": normalized.get("usage_parse_warnings", []),
        "price_snapshot": cost_result.get("price_snapshot"),
        "correlation_id": linkage.correlation_id,
        "route_decision_id": linkage.route_decision_id,
        "task_context_id": linkage.task_context_id,
        "profile_id": linkage.profile_id,
        "call_id": linkage.call_id,
        "observation_id": observation.observation_id,
        "experience_id": linkage.experience_id,
        "time_to_verified_outcome_ms": observation.time_to_verified_outcome_ms,
        "queue_ms": timings.queue_ms,
        "connect_ms": timings.connect_ms,
        "generation_ms": timings.generation_ms,
        "tool_execution_ms": timings.tool_execution_ms,
        "verifier_ms": timings.verifier_ms,
        "retry_ms": timings.retry_ms,
        "fallback_ms": timings.fallback_ms,
        "human_wait_ms": timings.human_wait_ms,
        "cost_status": cost_result.get("cost_status", COST_UNKNOWN),
        "price_snapshot_digest": cost_result.get("price_snapshot_digest", ""),
        "field_measurement_classes": normalized.get("field_measurement_classes", {}),
    }
    logger_record = {
        "call_id": linkage.call_id,
        "correlation_id": linkage.correlation_id,
        "route_decision_id": linkage.route_decision_id,
        "task_context_id": linkage.task_context_id,
        "profile_id": linkage.profile_id,
        "cost_run_id": linkage.cost_run_id,
        "experience_id": linkage.experience_id,
        "provider": provider,
        "model": model,
        "input_tokens": normalized.get("input_tokens"),
        "output_tokens": normalized.get("output_tokens"),
        "cost_usd": cost_result.get("cost_usd"),
        "cost_status": cost_result.get("cost_status", COST_UNKNOWN),
        "latency_ms": machine_total,
        "time_to_verified_outcome_ms": observation.time_to_verified_outcome_ms,
        "measurement_class": normalized.get("measurement_class", UNAVAILABLE),
        "field_measurement_classes": normalized.get("field_measurement_classes", {}),
    }
    return TelemetryPacket(
        linkage=linkage,
        observation=observation,
        normalized_usage=normalized,
        cost_result=cost_result,
        cost_run=cost_run,
        logger_record=logger_record,
        created_at=created,
    )


def persist_telemetry_packet(
    packet: TelemetryPacket,
    *,
    cognome_store: CognomeObservationStore,
    empirical_ledger: EmpiricalLedger | None = None,
    logger_sink: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    if cognome_store.get_endpoint(packet.linkage.profile_id) is None:
        raise ValueError(f"Unknown Cognome profile: {packet.linkage.profile_id}")
    snapshot = packet.cost_result.get("price_snapshot")
    if snapshot:
        stored_digest = cognome_store.record_price_snapshot(snapshot)
        if stored_digest != packet.cost_result.get("price_snapshot_digest"):
            raise ValueError("Stored price snapshot digest does not match telemetry packet")
    observation_id = cognome_store.record_observation(packet.observation)
    cost_run_id = None
    if empirical_ledger is not None:
        result = empirical_ledger.record_run(dict(packet.cost_run))
        cost_run_id = result.get("run_id")
        if cost_run_id != packet.linkage.cost_run_id:
            raise ValueError("Empirical ledger returned an unexpected cost run ID")
    if logger_sink is not None:
        logger_sink(dict(packet.logger_record))
    return {
        "ok": True,
        "observation_id": observation_id,
        "cost_run_id": cost_run_id,
        "call_id": packet.linkage.call_id,
        "correlation_id": packet.linkage.correlation_id,
        "version": TELEMETRY_VERSION,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
