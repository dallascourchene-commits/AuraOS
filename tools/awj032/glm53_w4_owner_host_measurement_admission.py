"""Owner-host measurement admission membrane for AWJ032 GLM-5.3 W4.

This module defines how an owner-host measurement campaign may become trusted input
for the already-existing W4 counter reducer and cache-policy comparator. It does
NOT execute the host, read model weights, or let GitHub CI manufacture ThinkPad
measurements. A structurally valid observation remains waiting until its attestation
reference is present in the code-owned relying-party registry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping

from tools.awj032.glm53_w4_host_preflight import W4CounterSnapshot, W4PreflightReceipt, evaluate_w4_counters

SCHEMA = "GLM53W4OwnerHostMeasurementAdmissionV1"
REQUEST_SCHEMA = "GLM53W4OwnerHostMeasurementRequestV1"
OBSERVATION_SCHEMA = "GLM53W4OwnerHostMeasurementObservationV1"
ATTESTATION_SCHEMA = "GLM53W4OwnerHostAttestationV1"
OWNER_HOST_CLASS = "OWNER_THINKPAD_WSL"
REQUIRED_PHASES = ("COLD", "WARM", "RESTART")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# Relying-party trust root. Intentionally empty until an independently observed
# owner-host execution receipt is pinned by a separate Arena/owner boundary.
TRUSTED_OWNER_HOST_ATTESTATIONS: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


class W4OwnerHostMeasurementError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise W4OwnerHostMeasurementError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _sha(name: str, value: Any) -> str:
    out = _text(name, value).lower()
    if not _SHA256.fullmatch(out):
        raise W4OwnerHostMeasurementError(f"{name.upper()}_INVALID")
    return out


def _exact_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise W4OwnerHostMeasurementError(f"{name.upper()}_INVALID")
    return value


def _nonnegative(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise W4OwnerHostMeasurementError(f"{name.upper()}_INVALID")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise W4OwnerHostMeasurementError(f"{name.upper()}_INVALID")
    return out


def _bytes(name: str, value: Any, *, positive: bool = False) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (positive and value == 0):
        raise W4OwnerHostMeasurementError(f"{name.upper()}_INVALID")
    return value


@dataclass(frozen=True)
class W4OwnerHostMeasurementRequest:
    scope_ref: str
    source_generation: str
    workload_ref: str
    measurement_campaign_ref: str
    policy_id: str
    command_contract_digest: str
    logical_expert_bytes_required: int
    exposed_io_budget_seconds: float
    host_class: str = OWNER_HOST_CLASS
    required_phases: tuple[str, ...] = REQUIRED_PHASES
    allow_provider_effect: bool = False
    allow_checkpoint_download: bool = False
    allow_g2: bool = False
    authority: bool = False
    schema: str = REQUEST_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != REQUEST_SCHEMA:
            raise W4OwnerHostMeasurementError("REQUEST_SCHEMA_MISMATCH")
        if self.host_class != OWNER_HOST_CLASS:
            raise W4OwnerHostMeasurementError("OWNER_HOST_CLASS_REQUIRED")
        if self.required_phases != REQUIRED_PHASES:
            raise W4OwnerHostMeasurementError("REQUIRED_PHASE_SET_MISMATCH")
        for name, value in (
            ("allow_provider_effect", self.allow_provider_effect),
            ("allow_checkpoint_download", self.allow_checkpoint_download),
            ("allow_g2", self.allow_g2),
            ("authority", self.authority),
        ):
            if _exact_bool(name, value):
                raise W4OwnerHostMeasurementError("REQUEST_EFFECT_CEILING_WIDENED", name)
        return {
            "schema": REQUEST_SCHEMA,
            "scope_ref": _text("scope_ref", self.scope_ref),
            "source_generation": _text("source_generation", self.source_generation),
            "workload_ref": _text("workload_ref", self.workload_ref),
            "measurement_campaign_ref": _text("measurement_campaign_ref", self.measurement_campaign_ref),
            "policy_id": _text("policy_id", self.policy_id),
            "command_contract_digest": _sha("command_contract_digest", self.command_contract_digest),
            "logical_expert_bytes_required": _bytes("logical_expert_bytes_required", self.logical_expert_bytes_required, positive=True),
            "exposed_io_budget_seconds": _nonnegative("exposed_io_budget_seconds", self.exposed_io_budget_seconds),
            "host_class": OWNER_HOST_CLASS,
            "required_phases": list(REQUIRED_PHASES),
            "allow_provider_effect": False,
            "allow_checkpoint_download": False,
            "allow_g2": False,
            "authority": False,
        }

    @property
    def request_digest(self) -> str:
        return _digest(self.normalized())


@dataclass(frozen=True)
class W4HostPhaseCounters:
    phase: str
    physical_demand_expert_bytes: int
    prefetch_useful_bytes: int
    prefetch_waste_bytes: int
    aura_cache_avoided_bytes: int
    os_cache_avoided_bytes: int
    other_proven_avoided_bytes: int
    effective_bandwidth_bytes_per_s: float
    overlap_seconds: float
    queue_seconds: float
    energy_joules: float
    peak_resident_bytes: int
    elapsed_seconds: float

    def normalized(self) -> dict[str, Any]:
        phase = _text("phase", self.phase).upper()
        if phase not in REQUIRED_PHASES:
            raise W4OwnerHostMeasurementError("PHASE_UNSUPPORTED", phase)
        return {
            "phase": phase,
            "physical_demand_expert_bytes": _bytes("physical_demand_expert_bytes", self.physical_demand_expert_bytes),
            "prefetch_useful_bytes": _bytes("prefetch_useful_bytes", self.prefetch_useful_bytes),
            "prefetch_waste_bytes": _bytes("prefetch_waste_bytes", self.prefetch_waste_bytes),
            "aura_cache_avoided_bytes": _bytes("aura_cache_avoided_bytes", self.aura_cache_avoided_bytes),
            "os_cache_avoided_bytes": _bytes("os_cache_avoided_bytes", self.os_cache_avoided_bytes),
            "other_proven_avoided_bytes": _bytes("other_proven_avoided_bytes", self.other_proven_avoided_bytes),
            "effective_bandwidth_bytes_per_s": _nonnegative("effective_bandwidth_bytes_per_s", self.effective_bandwidth_bytes_per_s),
            "overlap_seconds": _nonnegative("overlap_seconds", self.overlap_seconds),
            "queue_seconds": _nonnegative("queue_seconds", self.queue_seconds),
            "energy_joules": _nonnegative("energy_joules", self.energy_joules),
            "peak_resident_bytes": _bytes("peak_resident_bytes", self.peak_resident_bytes),
            "elapsed_seconds": _nonnegative("elapsed_seconds", self.elapsed_seconds),
        }


@dataclass(frozen=True)
class W4OwnerHostMeasurementObservation:
    request_digest: str
    scope_ref: str
    source_generation: str
    workload_ref: str
    measurement_campaign_ref: str
    policy_id: str
    command_contract_digest: str
    runner_class: str
    runner_instance_ref: str
    attestation_ref: str
    phases: tuple[W4HostPhaseCounters, ...]
    source_current: bool
    workload_current: bool
    command_observed_exact: bool
    run_completed: bool
    external_benchmark_used_as_measurement: bool = False
    k27_used_as_measurement_authority: bool = False
    cache_hit_ratio_used_as_measurement_authority: bool = False
    schema: str = OBSERVATION_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != OBSERVATION_SCHEMA:
            raise W4OwnerHostMeasurementError("OBSERVATION_SCHEMA_MISMATCH")
        runner = _text("runner_class", self.runner_class)
        if runner.startswith("GITHUB") or runner in {"CI", "GITHUB_ACTIONS", "HOSTED_RUNNER"}:
            raise W4OwnerHostMeasurementError("GITHUB_ACTIONS_RUNNER_FORBIDDEN")
        if runner != OWNER_HOST_CLASS:
            raise W4OwnerHostMeasurementError("OWNER_HOST_RUNNER_REQUIRED")
        for name, value in (
            ("source_current", self.source_current),
            ("workload_current", self.workload_current),
            ("command_observed_exact", self.command_observed_exact),
            ("run_completed", self.run_completed),
        ):
            if not _exact_bool(name, value):
                raise W4OwnerHostMeasurementError(f"{name.upper()}_REQUIRED")
        for name, value in (
            ("external_benchmark_used_as_measurement", self.external_benchmark_used_as_measurement),
            ("k27_used_as_measurement_authority", self.k27_used_as_measurement_authority),
            ("cache_hit_ratio_used_as_measurement_authority", self.cache_hit_ratio_used_as_measurement_authority),
        ):
            if _exact_bool(name, value):
                raise W4OwnerHostMeasurementError("MEASUREMENT_AUTHORITY_SUBSTITUTION_FORBIDDEN", name)
        normalized_phases = tuple(p.normalized() for p in self.phases)
        names = tuple(p["phase"] for p in normalized_phases)
        if names != REQUIRED_PHASES:
            raise W4OwnerHostMeasurementError("COLD_WARM_RESTART_PHASES_REQUIRED")
        return {
            "schema": OBSERVATION_SCHEMA,
            "request_digest": _sha("request_digest", self.request_digest),
            "scope_ref": _text("scope_ref", self.scope_ref),
            "source_generation": _text("source_generation", self.source_generation),
            "workload_ref": _text("workload_ref", self.workload_ref),
            "measurement_campaign_ref": _text("measurement_campaign_ref", self.measurement_campaign_ref),
            "policy_id": _text("policy_id", self.policy_id),
            "command_contract_digest": _sha("command_contract_digest", self.command_contract_digest),
            "runner_class": OWNER_HOST_CLASS,
            "runner_instance_ref": _text("runner_instance_ref", self.runner_instance_ref),
            "attestation_ref": _text("attestation_ref", self.attestation_ref),
            "phases": list(normalized_phases),
            "source_current": True,
            "workload_current": True,
            "command_observed_exact": True,
            "run_completed": True,
            "external_benchmark_used_as_measurement": False,
            "k27_used_as_measurement_authority": False,
            "cache_hit_ratio_used_as_measurement_authority": False,
        }

    @property
    def observation_digest(self) -> str:
        return _digest(self.normalized())


@dataclass(frozen=True)
class W4OwnerHostAttestation:
    attestation_ref: str
    request_digest: str
    observation_digest: str
    runner_class: str
    runner_instance_ref: str
    measurement_campaign_ref: str
    command_contract_digest: str
    current: bool
    independently_observed: bool
    external_effect: bool = False
    authority: bool = False
    schema: str = ATTESTATION_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != ATTESTATION_SCHEMA:
            raise W4OwnerHostMeasurementError("ATTESTATION_SCHEMA_MISMATCH")
        if self.runner_class != OWNER_HOST_CLASS:
            raise W4OwnerHostMeasurementError("ATTESTATION_OWNER_HOST_REQUIRED")
        if not _exact_bool("current", self.current) or not self.current:
            raise W4OwnerHostMeasurementError("ATTESTATION_CURRENT_REQUIRED")
        if not _exact_bool("independently_observed", self.independently_observed) or not self.independently_observed:
            raise W4OwnerHostMeasurementError("INDEPENDENT_ATTESTATION_REQUIRED")
        if _exact_bool("external_effect", self.external_effect) or _exact_bool("authority", self.authority):
            raise W4OwnerHostMeasurementError("ATTESTATION_EFFECT_CEILING_WIDENED")
        return {
            "schema": ATTESTATION_SCHEMA,
            "attestation_ref": _text("attestation_ref", self.attestation_ref),
            "request_digest": _sha("request_digest", self.request_digest),
            "observation_digest": _sha("observation_digest", self.observation_digest),
            "runner_class": OWNER_HOST_CLASS,
            "runner_instance_ref": _text("runner_instance_ref", self.runner_instance_ref),
            "measurement_campaign_ref": _text("measurement_campaign_ref", self.measurement_campaign_ref),
            "command_contract_digest": _sha("command_contract_digest", self.command_contract_digest),
            "current": True,
            "independently_observed": True,
            "external_effect": False,
            "authority": False,
        }


@dataclass(frozen=True)
class W4OwnerHostMeasurementAdmissionReceipt:
    status: str
    request_digest: str
    observation_digest: str
    attestation_ref: str
    trusted_attestation_found: bool
    owner_host_measurement_proven: bool
    phase_preflights: tuple[W4PreflightReceipt, ...]
    measurement_campaign_ref: str
    policy_id: str
    github_ci_is_owner_host: bool = False
    external_benchmark_is_owner_host_measurement: bool = False
    k27_is_measurement_authority: bool = False
    cache_hit_ratio_is_measurement_authority: bool = False
    runtime_mtp_support_proven: bool = False
    end_to_end_usability_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    authority: bool = False
    schema: str = SCHEMA


def _bind_request_observation(request: W4OwnerHostMeasurementRequest, observation: W4OwnerHostMeasurementObservation) -> tuple[dict[str, Any], dict[str, Any]]:
    r = request.normalized()
    o = observation.normalized()
    expected = {
        "request_digest": request.request_digest,
        "scope_ref": r["scope_ref"],
        "source_generation": r["source_generation"],
        "workload_ref": r["workload_ref"],
        "measurement_campaign_ref": r["measurement_campaign_ref"],
        "policy_id": r["policy_id"],
        "command_contract_digest": r["command_contract_digest"],
    }
    mismatches = [k for k, v in expected.items() if o[k] != v]
    if mismatches:
        raise W4OwnerHostMeasurementError("REQUEST_OBSERVATION_BINDING_MISMATCH", ",".join(mismatches))
    return r, o


def _preflights(request: W4OwnerHostMeasurementRequest, observation: W4OwnerHostMeasurementObservation, *, attestation_ref: str) -> tuple[W4PreflightReceipt, ...]:
    out: list[W4PreflightReceipt] = []
    for phase in observation.phases:
        p = phase.normalized()
        snap = W4CounterSnapshot(
            scope_ref=request.scope_ref,
            source_generation=request.source_generation,
            workload_ref=f"{request.workload_ref}:{p['phase']}",
            logical_expert_bytes_required=request.logical_expert_bytes_required,
            physical_demand_expert_bytes=p["physical_demand_expert_bytes"],
            prefetch_useful_bytes=p["prefetch_useful_bytes"],
            prefetch_waste_bytes=p["prefetch_waste_bytes"],
            aura_cache_avoided_bytes=p["aura_cache_avoided_bytes"],
            os_cache_avoided_bytes=p["os_cache_avoided_bytes"],
            other_proven_avoided_bytes=p["other_proven_avoided_bytes"],
            effective_bandwidth_bytes_per_s=p["effective_bandwidth_bytes_per_s"],
            overlap_seconds=p["overlap_seconds"],
            queue_seconds=p["queue_seconds"],
            exposed_io_budget_seconds=request.exposed_io_budget_seconds,
            physical_io_attested=True,
            physical_io_attestation_ref=f"{attestation_ref}:{p['phase']}",
        )
        out.append(evaluate_w4_counters(snap))
    return tuple(out)


def _evaluate_with_registry(
    request: W4OwnerHostMeasurementRequest,
    observation: W4OwnerHostMeasurementObservation,
    registry: Mapping[str, Mapping[str, Any]],
) -> W4OwnerHostMeasurementAdmissionReceipt:
    r, o = _bind_request_observation(request, observation)
    ref = o["attestation_ref"]
    raw = registry.get(ref)
    if raw is None:
        return W4OwnerHostMeasurementAdmissionReceipt(
            status="WAITING_OWNER_HOST_ATTESTATION",
            request_digest=request.request_digest,
            observation_digest=observation.observation_digest,
            attestation_ref=ref,
            trusted_attestation_found=False,
            owner_host_measurement_proven=False,
            phase_preflights=(),
            measurement_campaign_ref=r["measurement_campaign_ref"],
            policy_id=r["policy_id"],
        )
    try:
        att = W4OwnerHostAttestation(**dict(raw))
        a = att.normalized()
    except (TypeError, W4OwnerHostMeasurementError) as exc:
        raise W4OwnerHostMeasurementError("TRUSTED_ATTESTATION_INVALID") from exc
    expected = {
        "attestation_ref": ref,
        "request_digest": request.request_digest,
        "observation_digest": observation.observation_digest,
        "runner_class": OWNER_HOST_CLASS,
        "runner_instance_ref": o["runner_instance_ref"],
        "measurement_campaign_ref": r["measurement_campaign_ref"],
        "command_contract_digest": r["command_contract_digest"],
    }
    mismatches = [k for k, v in expected.items() if a[k] != v]
    if mismatches:
        raise W4OwnerHostMeasurementError("TRUSTED_ATTESTATION_BINDING_MISMATCH", ",".join(mismatches))
    return W4OwnerHostMeasurementAdmissionReceipt(
        status="OWNER_HOST_MEASUREMENT_ADMITTED",
        request_digest=request.request_digest,
        observation_digest=observation.observation_digest,
        attestation_ref=ref,
        trusted_attestation_found=True,
        owner_host_measurement_proven=True,
        phase_preflights=_preflights(request, observation, attestation_ref=ref),
        measurement_campaign_ref=r["measurement_campaign_ref"],
        policy_id=r["policy_id"],
    )


def evaluate_owner_host_measurement(
    request: W4OwnerHostMeasurementRequest,
    observation: W4OwnerHostMeasurementObservation,
) -> W4OwnerHostMeasurementAdmissionReceipt:
    """Canonical relying-party boundary. Callers cannot provide a trust registry."""
    return _evaluate_with_registry(request, observation, TRUSTED_OWNER_HOST_ATTESTATIONS)
