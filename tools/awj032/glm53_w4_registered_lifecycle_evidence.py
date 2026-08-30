"""Registry-bound lifecycle evidence adapter for AWJ032 GLM-5.3 W4.

This membrane joins two proof planes without collapsing them:
1) PR423 owner-host origin/command/three-phase admission; and
2) a producer-owned lifecycle measurement receipt retrieved from a relying-party registry.

Only after both are independently admitted may this module construct the caller-shaped
``W4CachePolicyObservation`` consumed by PR417. The public path has no caller metric
vector, no caller lifecycle-attested/current/correct booleans, and no caller registry
parameter. Production registry lookup is intentionally unavailable until an independently
observed owner-host lifecycle producer receipt is pinned.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Any, Mapping

from tools.awj032.glm53_w4_cache_policy_decision import ROLE, W4CachePolicyObservation
from tools.awj032.glm53_w4_host_preflight import W4PreflightReceipt
from tools.awj032.glm53_w4_owner_host_measurement_admission import (
    OWNER_HOST_CLASS,
    W4OwnerHostMeasurementAdmissionReceipt,
)

RECEIPT_SCHEMA = "W4LifecycleMeasurementReceiptV1"
REGISTRY_SCHEMA = "W4LifecycleMeasurementRegistryRecordV1"
EVIDENCE_SCHEMA = "W4RegisteredLifecycleEvidenceV1"
CLAIM_CEILING = "D0_REGISTERED_OWNER_HOST_LIFECYCLE_EVIDENCE_ONLY_NO_RUNTIME_QUALITY_G2_OR_AUTHORITY"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

# Code-owned relying-party trust root. Intentionally empty until an independent
# Arena/owner process observes a real owner-host lifecycle producer and pins it.
TRUSTED_LIFECYCLE_MEASUREMENT_REGISTRY: Mapping[str, Mapping[str, Any]] = MappingProxyType({})


class W4RegisteredLifecycleEvidenceError(ValueError):
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
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_REQUIRED")
    return value.strip()


def _sha(name: str, value: Any) -> str:
    out = _text(name, value).lower()
    if not _SHA256.fullmatch(out):
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_INVALID")
    return out


def _exact_true(name: str, value: Any) -> bool:
    if type(value) is not bool or value is not True:
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_REQUIRED")
    return True


def _exact_false(name: str, value: Any) -> bool:
    if type(value) is not bool or value is not False:
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_FORBIDDEN")
    return False


def _nonnegative(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_INVALID")
    out = float(value)
    if not math.isfinite(out) or out < 0:
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_INVALID")
    return out


def _bytes(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_INVALID")
    return value


def _ratio(name: str, value: Any) -> float:
    out = _nonnegative(name, value)
    if out > 1:
        raise W4RegisteredLifecycleEvidenceError(f"{name.upper()}_INVALID")
    return out


def preflight_digest(receipt: W4PreflightReceipt) -> str:
    if not isinstance(receipt, W4PreflightReceipt):
        raise W4RegisteredLifecycleEvidenceError("W4_PREFLIGHT_REQUIRED")
    return _digest(asdict(receipt))


@dataclass(frozen=True)
class W4LifecycleMeasurementReceipt:
    receipt_ref: str
    owner_host_request_digest: str
    owner_host_observation_digest: str
    owner_host_attestation_ref: str
    scope_ref: str
    source_generation: str
    workload_ref: str
    measurement_campaign_ref: str
    policy_id: str
    preflight_receipt_digest: str
    observer_ref: str
    observer_generation: str
    producer_run_ref: str
    runner_class: str
    runner_instance_ref: str
    cache_hit_ratio: float
    energy_joules: float
    peak_resident_bytes: int
    warmup_seconds: float
    restart_seconds: float
    revalidation_seconds: float
    control_overhead_seconds: float
    physical_io_attested: bool
    correctness_reference_equivalent: bool
    source_current: bool
    measurement_current: bool
    independently_observed: bool
    revoked: bool = False
    external_effect: bool = False
    runtime_execution_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    authority: bool = False
    schema: str = RECEIPT_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != RECEIPT_SCHEMA:
            raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_RECEIPT_SCHEMA_MISMATCH")
        if self.runner_class != OWNER_HOST_CLASS:
            raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_OWNER_HOST_RUNNER_REQUIRED")
        for name, value in (
            ("physical_io_attested", self.physical_io_attested),
            ("correctness_reference_equivalent", self.correctness_reference_equivalent),
            ("source_current", self.source_current),
            ("measurement_current", self.measurement_current),
            ("independently_observed", self.independently_observed),
        ):
            _exact_true(name, value)
        for name, value in (
            ("revoked", self.revoked),
            ("external_effect", self.external_effect),
            ("runtime_execution_proven", self.runtime_execution_proven),
            ("quality_proven", self.quality_proven),
            ("g2_admitted", self.g2_admitted),
            ("authority", self.authority),
        ):
            _exact_false(name, value)
        return {
            "schema": RECEIPT_SCHEMA,
            "receipt_ref": _text("receipt_ref", self.receipt_ref),
            "owner_host_request_digest": _sha("owner_host_request_digest", self.owner_host_request_digest),
            "owner_host_observation_digest": _sha("owner_host_observation_digest", self.owner_host_observation_digest),
            "owner_host_attestation_ref": _text("owner_host_attestation_ref", self.owner_host_attestation_ref),
            "scope_ref": _text("scope_ref", self.scope_ref),
            "source_generation": _text("source_generation", self.source_generation),
            "workload_ref": _text("workload_ref", self.workload_ref),
            "measurement_campaign_ref": _text("measurement_campaign_ref", self.measurement_campaign_ref),
            "policy_id": _text("policy_id", self.policy_id),
            "preflight_receipt_digest": _sha("preflight_receipt_digest", self.preflight_receipt_digest),
            "observer_ref": _text("observer_ref", self.observer_ref),
            "observer_generation": _text("observer_generation", self.observer_generation),
            "producer_run_ref": _text("producer_run_ref", self.producer_run_ref),
            "runner_class": OWNER_HOST_CLASS,
            "runner_instance_ref": _text("runner_instance_ref", self.runner_instance_ref),
            "cache_hit_ratio": _ratio("cache_hit_ratio", self.cache_hit_ratio),
            "energy_joules": _nonnegative("energy_joules", self.energy_joules),
            "peak_resident_bytes": _bytes("peak_resident_bytes", self.peak_resident_bytes),
            "warmup_seconds": _nonnegative("warmup_seconds", self.warmup_seconds),
            "restart_seconds": _nonnegative("restart_seconds", self.restart_seconds),
            "revalidation_seconds": _nonnegative("revalidation_seconds", self.revalidation_seconds),
            "control_overhead_seconds": _nonnegative("control_overhead_seconds", self.control_overhead_seconds),
            "physical_io_attested": True,
            "correctness_reference_equivalent": True,
            "source_current": True,
            "measurement_current": True,
            "independently_observed": True,
            "revoked": False,
            "external_effect": False,
            "runtime_execution_proven": False,
            "quality_proven": False,
            "g2_admitted": False,
            "authority": False,
        }

    @property
    def receipt_digest(self) -> str:
        return _digest(self.normalized())


@dataclass(frozen=True)
class W4LifecycleMeasurementRegistryRecord:
    receipt_ref: str
    receipt_digest: str
    owner_host_request_digest: str
    owner_host_observation_digest: str
    owner_host_attestation_ref: str
    observer_ref: str
    observer_generation: str
    producer_run_ref: str
    current: bool
    independently_verified: bool
    revoked: bool = False
    authority: bool = False
    schema: str = REGISTRY_SCHEMA

    def normalized(self) -> dict[str, Any]:
        if self.schema != REGISTRY_SCHEMA:
            raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_REGISTRY_SCHEMA_MISMATCH")
        _exact_true("registry_current", self.current)
        _exact_true("registry_independently_verified", self.independently_verified)
        _exact_false("registry_revoked", self.revoked)
        _exact_false("registry_authority", self.authority)
        return {
            "schema": REGISTRY_SCHEMA,
            "receipt_ref": _text("receipt_ref", self.receipt_ref),
            "receipt_digest": _sha("receipt_digest", self.receipt_digest),
            "owner_host_request_digest": _sha("owner_host_request_digest", self.owner_host_request_digest),
            "owner_host_observation_digest": _sha("owner_host_observation_digest", self.owner_host_observation_digest),
            "owner_host_attestation_ref": _text("owner_host_attestation_ref", self.owner_host_attestation_ref),
            "observer_ref": _text("observer_ref", self.observer_ref),
            "observer_generation": _text("observer_generation", self.observer_generation),
            "producer_run_ref": _text("producer_run_ref", self.producer_run_ref),
            "current": True,
            "independently_verified": True,
            "revoked": False,
            "authority": False,
        }


@dataclass(frozen=True)
class W4RegisteredLifecycleEvidence:
    receipt_ref: str
    receipt_digest: str
    registry_record_digest: str
    owner_host_request_digest: str
    owner_host_observation_digest: str
    owner_host_attestation_ref: str
    scope_ref: str
    source_generation: str
    workload_ref: str
    measurement_campaign_ref: str
    policy_id: str
    preflight_receipt_digest: str
    observer_ref: str
    observer_generation: str
    producer_run_ref: str
    cache_hit_ratio: float
    energy_joules: float
    peak_resident_bytes: int
    warmup_seconds: float
    restart_seconds: float
    revalidation_seconds: float
    control_overhead_seconds: float
    lifecycle_metrics_attested: bool = True
    correctness_reference_equivalent: bool = True
    source_current: bool = True
    measurement_current: bool = True
    physical_io_attested: bool = True
    producer_registry_verified: bool = True
    runtime_execution_proven: bool = False
    quality_proven: bool = False
    g2_admitted: bool = False
    authority: bool = False
    schema: str = EVIDENCE_SCHEMA
    claim_ceiling: str = CLAIM_CEILING

    @property
    def evidence_digest(self) -> str:
        return _digest(asdict(self))


def _validate_host_admission(
    host_admission: W4OwnerHostMeasurementAdmissionReceipt,
    *,
    preflight: W4PreflightReceipt,
    expected_policy_id: str,
) -> tuple[str, str, str]:
    if not isinstance(host_admission, W4OwnerHostMeasurementAdmissionReceipt):
        raise W4RegisteredLifecycleEvidenceError("OWNER_HOST_ADMISSION_REQUIRED")
    if host_admission.status != "OWNER_HOST_MEASUREMENT_ADMITTED":
        raise W4RegisteredLifecycleEvidenceError("OWNER_HOST_MEASUREMENT_NOT_ADMITTED")
    _exact_true("trusted_attestation_found", host_admission.trusted_attestation_found)
    _exact_true("owner_host_measurement_proven", host_admission.owner_host_measurement_proven)
    for name, value in (
        ("github_ci_is_owner_host", host_admission.github_ci_is_owner_host),
        ("external_benchmark_is_owner_host_measurement", host_admission.external_benchmark_is_owner_host_measurement),
        ("k27_is_measurement_authority", host_admission.k27_is_measurement_authority),
        ("cache_hit_ratio_is_measurement_authority", host_admission.cache_hit_ratio_is_measurement_authority),
        ("runtime_mtp_support_proven", host_admission.runtime_mtp_support_proven),
        ("end_to_end_usability_proven", host_admission.end_to_end_usability_proven),
        ("quality_proven", host_admission.quality_proven),
        ("g2_admitted", host_admission.g2_admitted),
        ("authority", host_admission.authority),
    ):
        _exact_false(name, value)
    if host_admission.policy_id != expected_policy_id:
        raise W4RegisteredLifecycleEvidenceError("OWNER_HOST_POLICY_MISMATCH")
    target_digest = preflight_digest(preflight)
    admitted_digests = tuple(preflight_digest(p) for p in host_admission.phase_preflights)
    if target_digest not in admitted_digests:
        raise W4RegisteredLifecycleEvidenceError("PREFLIGHT_NOT_ADMITTED_BY_OWNER_HOST_RECEIPT")
    return host_admission.request_digest, host_admission.observation_digest, host_admission.attestation_ref


def _decode_registry_entry(raw: Mapping[str, Any]) -> tuple[W4LifecycleMeasurementReceipt, W4LifecycleMeasurementRegistryRecord]:
    if not isinstance(raw, Mapping):
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_REGISTRY_ENTRY_INVALID")
    try:
        receipt = W4LifecycleMeasurementReceipt(**dict(raw["receipt"]))
        record = W4LifecycleMeasurementRegistryRecord(**dict(raw["registry_record"]))
    except (KeyError, TypeError) as exc:
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_REGISTRY_ENTRY_INVALID") from exc
    receipt.normalized()
    record.normalized()
    return receipt, record


def _admit_with_registry(
    *,
    lifecycle_receipt_ref: str,
    expected_policy_id: str,
    preflight: W4PreflightReceipt,
    host_admission: W4OwnerHostMeasurementAdmissionReceipt,
    registry: Mapping[str, Mapping[str, Any]],
) -> W4RegisteredLifecycleEvidence:
    ref = _text("lifecycle_receipt_ref", lifecycle_receipt_ref)
    policy_id = _text("expected_policy_id", expected_policy_id)
    request_digest, observation_digest, attestation_ref = _validate_host_admission(
        host_admission, preflight=preflight, expected_policy_id=policy_id
    )
    raw = registry.get(ref)
    if raw is None:
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_MEASUREMENT_PRODUCER_REQUIRED")
    receipt, record = _decode_registry_entry(raw)
    rn = receipt.normalized()
    rr = record.normalized()
    if rn["receipt_ref"] != ref or rr["receipt_ref"] != ref:
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_RECEIPT_REF_MISMATCH")
    if rr["receipt_digest"] != receipt.receipt_digest:
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_RECEIPT_DIGEST_MISMATCH")
    for field in (
        "owner_host_request_digest",
        "owner_host_observation_digest",
        "owner_host_attestation_ref",
        "observer_ref",
        "observer_generation",
        "producer_run_ref",
    ):
        if rr[field] != rn[field]:
            raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_REGISTRY_BINDING_MISMATCH", field)
    expected = {
        "owner_host_request_digest": request_digest,
        "owner_host_observation_digest": observation_digest,
        "owner_host_attestation_ref": attestation_ref,
        "policy_id": policy_id,
        "preflight_receipt_digest": preflight_digest(preflight),
        "scope_ref": preflight.scope_ref,
        "source_generation": preflight.source_generation,
        "workload_ref": preflight.workload_ref,
        "measurement_campaign_ref": host_admission.measurement_campaign_ref,
    }
    mismatches = [field for field, value in expected.items() if rn[field] != value]
    if mismatches:
        raise W4RegisteredLifecycleEvidenceError("LIFECYCLE_OWNER_HOST_BINDING_MISMATCH", ",".join(mismatches))
    registry_digest = _digest(rr)
    return W4RegisteredLifecycleEvidence(
        receipt_ref=ref,
        receipt_digest=receipt.receipt_digest,
        registry_record_digest=registry_digest,
        owner_host_request_digest=request_digest,
        owner_host_observation_digest=observation_digest,
        owner_host_attestation_ref=attestation_ref,
        scope_ref=rn["scope_ref"],
        source_generation=rn["source_generation"],
        workload_ref=rn["workload_ref"],
        measurement_campaign_ref=rn["measurement_campaign_ref"],
        policy_id=rn["policy_id"],
        preflight_receipt_digest=rn["preflight_receipt_digest"],
        observer_ref=rn["observer_ref"],
        observer_generation=rn["observer_generation"],
        producer_run_ref=rn["producer_run_ref"],
        cache_hit_ratio=rn["cache_hit_ratio"],
        energy_joules=rn["energy_joules"],
        peak_resident_bytes=rn["peak_resident_bytes"],
        warmup_seconds=rn["warmup_seconds"],
        restart_seconds=rn["restart_seconds"],
        revalidation_seconds=rn["revalidation_seconds"],
        control_overhead_seconds=rn["control_overhead_seconds"],
    )


def admit_registered_lifecycle_measurement(
    *,
    lifecycle_receipt_ref: str,
    expected_policy_id: str,
    preflight: W4PreflightReceipt,
    host_admission: W4OwnerHostMeasurementAdmissionReceipt,
) -> W4RegisteredLifecycleEvidence:
    """Canonical relying-party path; callers cannot provide metrics or a registry."""
    return _admit_with_registry(
        lifecycle_receipt_ref=lifecycle_receipt_ref,
        expected_policy_id=expected_policy_id,
        preflight=preflight,
        host_admission=host_admission,
        registry=TRUSTED_LIFECYCLE_MEASUREMENT_REGISTRY,
    )


def build_registered_cache_policy_observation(
    *,
    lifecycle_receipt_ref: str,
    expected_policy_id: str,
    policy_class: str,
    preflight: W4PreflightReceipt,
    host_admission: W4OwnerHostMeasurementAdmissionReceipt,
) -> W4CachePolicyObservation:
    evidence = admit_registered_lifecycle_measurement(
        lifecycle_receipt_ref=lifecycle_receipt_ref,
        expected_policy_id=expected_policy_id,
        preflight=preflight,
        host_admission=host_admission,
    )
    return _observation_from_evidence(evidence=evidence, policy_class=policy_class, preflight=preflight)


def _observation_from_evidence(
    *,
    evidence: W4RegisteredLifecycleEvidence,
    policy_class: str,
    preflight: W4PreflightReceipt,
) -> W4CachePolicyObservation:
    if not isinstance(evidence, W4RegisteredLifecycleEvidence) or evidence.producer_registry_verified is not True:
        raise W4RegisteredLifecycleEvidenceError("REGISTERED_LIFECYCLE_EVIDENCE_REQUIRED")
    if evidence.preflight_receipt_digest != preflight_digest(preflight):
        raise W4RegisteredLifecycleEvidenceError("REGISTERED_LIFECYCLE_PREFLIGHT_MISMATCH")
    return W4CachePolicyObservation(
        policy_id=evidence.policy_id,
        policy_class=_text("policy_class", policy_class),
        preflight=preflight,
        measurement_campaign_ref=evidence.measurement_campaign_ref,
        lifecycle_measurement_attestation_ref=evidence.receipt_ref,
        lifecycle_metrics_attested=True,
        correctness_reference_equivalent=True,
        source_current=True,
        measurement_current=True,
        cache_hit_ratio=evidence.cache_hit_ratio,
        energy_joules=evidence.energy_joules,
        peak_resident_bytes=evidence.peak_resident_bytes,
        warmup_seconds=evidence.warmup_seconds,
        restart_seconds=evidence.restart_seconds,
        revalidation_seconds=evidence.revalidation_seconds,
        control_overhead_seconds=evidence.control_overhead_seconds,
        role=ROLE,
    )
