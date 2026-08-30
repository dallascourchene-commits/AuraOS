"""Transport-neutral materialization -> consumer admission/currentness evidence membrane.

This module is intentionally non-authoritative. It separates:
materialization -> consumer observation/claim -> independently resolved admission/currentness
-> execution observation -> quality/effect authority.

Raw caller observations cannot mint CONSUMER_ADMITTED_CURRENT. That disposition requires
resolver-bound evidence plus an independently supplied resolver expectation whose exact
consumer/resolver/currentness generation tuple matches.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping

SCHEMA_VERSION = "AURA_MATERIALIZATION_ADMISSION_CURRENTNESS_BRIDGE_V1"


class TransportClass(str, Enum):
    GITHUB = "GITHUB"
    DRIVE_BUS = "DRIVE_BUS"
    QUEUE = "QUEUE"
    LOCAL_ARTIFACT = "LOCAL_ARTIFACT"


class AdmissionState(str, Enum):
    NOT_OBSERVED = "NOT_OBSERVED"
    ADMITTED = "ADMITTED"
    REFUSED = "REFUSED"
    DUPLICATE_NOOP = "DUPLICATE_NOOP"
    STALE_REOPEN = "STALE_REOPEN"


class ExecutionState(str, Enum):
    NOT_OBSERVED = "NOT_OBSERVED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"


class AdjudicationDisposition(str, Enum):
    MATERIALIZED_NOT_ADMITTED = "MATERIALIZED_NOT_ADMITTED"
    IDEMPOTENCY_MISMATCH = "IDEMPOTENCY_MISMATCH"
    ADMISSION_TARGET_MISMATCH = "ADMISSION_TARGET_MISMATCH"
    ADMISSION_TARGET_DIGEST_MISMATCH = "ADMISSION_TARGET_DIGEST_MISMATCH"
    CURRENTNESS_REOPEN = "CURRENTNESS_REOPEN"
    CONSUMER_REFUSED = "CONSUMER_REFUSED"
    DUPLICATE_NOOP_OBSERVED = "DUPLICATE_NOOP_OBSERVED"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    EVIDENCE_MISMATCH = "EVIDENCE_MISMATCH"
    CONSUMER_ADMITTED_CURRENT = "CONSUMER_ADMITTED_CURRENT"
    EXECUTION_OBSERVED = "EXECUTION_OBSERVED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"


def _require_text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _require_bool(name: str, value: Any) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _enum_value(enum_type: type[Enum], value: Any, name: str) -> Enum:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string or {enum_type.__name__}")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"unsupported {name}: {value}") from exc


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def logical_digest(value: Any) -> str:
    body = json.dumps(
        _canonical(asdict(value) if hasattr(value, "__dataclass_fields__") else value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.blake2b(body.encode("utf-8"), digest_size=20).hexdigest()


@dataclass(frozen=True)
class MaterializationReceiptV1:
    transport: TransportClass
    producer_owner: str
    producer_generation: str
    policy_ref: str
    policy_generation: str
    parent_target_ref: str
    materialized_target_ref: str
    materialized_target_digest: str
    artifact_set_digest: str
    allowed_delta_digest: str
    currentness_ref: str
    idempotency_key: str
    effect_receipt_ref: str
    materialization_observed: bool = True
    consumer_admitted: bool = False
    execution_observed: bool = False
    quality_satisfied: bool = False
    effect_authorized: bool = False
    promotion_authorized: bool = False
    merge_authorized: bool = False
    authority: bool = False
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "transport", _enum_value(TransportClass, self.transport, "transport"))
        for field in (
            "producer_owner", "producer_generation", "policy_ref", "policy_generation",
            "parent_target_ref", "materialized_target_ref", "materialized_target_digest",
            "artifact_set_digest", "allowed_delta_digest", "currentness_ref",
            "idempotency_key", "effect_receipt_ref", "schema",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.schema != SCHEMA_VERSION:
            raise ValueError("schema mismatch")
        if _require_bool("materialization_observed", self.materialization_observed) is not True:
            raise ValueError("materialization_observed must be true")
        for field in (
            "consumer_admitted", "execution_observed", "quality_satisfied", "effect_authorized",
            "promotion_authorized", "merge_authorized", "authority",
        ):
            if _require_bool(field, getattr(self, field)) is not False:
                raise ValueError(f"{field} must remain false")

    @property
    def receipt_digest(self) -> str:
        return logical_digest(self)


@dataclass(frozen=True)
class ConsumerAdmissionObservationV1:
    """Untrusted/typed observation. It is a claim, not resolved currentness proof."""
    consumer_owner: str
    consumer_generation: str
    observed_target_ref: str
    observed_target_digest: str
    idempotency_key: str
    consumer_currentness_ref: str
    consumer_current: bool
    admission_state: AdmissionState
    admission_receipt_ref: str = ""
    execution_state: ExecutionState = ExecutionState.NOT_OBSERVED
    execution_receipt_ref: str = ""
    quality_claim: bool = False
    effect_authorized: bool = False
    promotion_authorized: bool = False
    merge_authorized: bool = False
    authority: bool = False
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "admission_state", _enum_value(AdmissionState, self.admission_state, "admission_state"))
        object.__setattr__(self, "execution_state", _enum_value(ExecutionState, self.execution_state, "execution_state"))
        for field in (
            "consumer_owner", "consumer_generation", "observed_target_ref",
            "observed_target_digest", "idempotency_key", "consumer_currentness_ref", "schema",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.schema != SCHEMA_VERSION:
            raise ValueError("schema mismatch")
        _require_bool("consumer_current", self.consumer_current)
        for field in ("quality_claim", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"):
            if _require_bool(field, getattr(self, field)) is not False:
                raise ValueError(f"{field} must remain false")
        if self.admission_state in {AdmissionState.ADMITTED, AdmissionState.REFUSED, AdmissionState.DUPLICATE_NOOP}:
            _require_text("admission_receipt_ref", self.admission_receipt_ref)
        if self.execution_state is not ExecutionState.NOT_OBSERVED:
            _require_text("execution_receipt_ref", self.execution_receipt_ref)
        if self.execution_state is not ExecutionState.NOT_OBSERVED and self.admission_state is not AdmissionState.ADMITTED:
            raise ValueError("execution cannot be observed without ADMITTED state")

    @property
    def receipt_digest(self) -> str:
        return logical_digest(self)


@dataclass(frozen=True)
class ConsumerAdmissionResolverExpectationV1:
    """Independently resolved expectation for the admission/currentness resolver boundary."""
    resolver_ref: str
    resolver_generation: str
    consumer_owner: str
    consumer_generation: str
    consumer_currentness_ref: str
    consumer_currentness_generation: str
    authority: bool = False
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "resolver_ref", "resolver_generation", "consumer_owner", "consumer_generation",
            "consumer_currentness_ref", "consumer_currentness_generation", "schema",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.schema != SCHEMA_VERSION:
            raise ValueError("schema mismatch")
        if _require_bool("authority", self.authority) is not False:
            raise ValueError("authority must remain false")

    @property
    def receipt_digest(self) -> str:
        return logical_digest(self)


@dataclass(frozen=True)
class ResolvedConsumerAdmissionEvidenceV1:
    """Resolver-produced evidence. The bridge checks it against a separate expectation."""
    resolver_ref: str
    resolver_generation: str
    consumer_owner: str
    consumer_generation: str
    consumer_currentness_ref: str
    consumer_currentness_generation: str
    observed_target_ref: str
    observed_target_digest: str
    idempotency_key: str
    admission_receipt_ref: str
    admission_receipt_digest: str
    evidence_ref: str
    resolved_current: bool
    resolved_admitted: bool
    quality_claim: bool = False
    effect_authorized: bool = False
    promotion_authorized: bool = False
    merge_authorized: bool = False
    authority: bool = False
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "resolver_ref", "resolver_generation", "consumer_owner", "consumer_generation",
            "consumer_currentness_ref", "consumer_currentness_generation", "observed_target_ref",
            "observed_target_digest", "idempotency_key", "admission_receipt_ref",
            "admission_receipt_digest", "evidence_ref", "schema",
        ):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.schema != SCHEMA_VERSION:
            raise ValueError("schema mismatch")
        _require_bool("resolved_current", self.resolved_current)
        _require_bool("resolved_admitted", self.resolved_admitted)
        for field in ("quality_claim", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"):
            if _require_bool(field, getattr(self, field)) is not False:
                raise ValueError(f"{field} must remain false")

    @property
    def receipt_digest(self) -> str:
        return logical_digest(self)


@dataclass(frozen=True)
class AdjudicationResultV1:
    disposition: AdjudicationDisposition
    materialized_target_ref: str
    materialized_target_digest: str
    idempotency_key: str
    consumer_admitted_current: bool
    execution_observed: bool
    observation_digest: str | None = None
    resolution_evidence_digest: str | None = None
    resolver_expectation_digest: str | None = None
    quality_satisfied: bool = False
    effect_authorized: bool = False
    promotion_authorized: bool = False
    merge_authorized: bool = False
    authority: bool = False
    schema: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "disposition", _enum_value(AdjudicationDisposition, self.disposition, "disposition"))
        for field in ("materialized_target_ref", "materialized_target_digest", "idempotency_key", "schema"):
            object.__setattr__(self, field, _require_text(field, getattr(self, field)))
        if self.schema != SCHEMA_VERSION:
            raise ValueError("schema mismatch")
        _require_bool("consumer_admitted_current", self.consumer_admitted_current)
        _require_bool("execution_observed", self.execution_observed)
        for field in ("quality_satisfied", "effect_authorized", "promotion_authorized", "merge_authorized", "authority"):
            if _require_bool(field, getattr(self, field)) is not False:
                raise ValueError(f"{field} must remain false")

    @property
    def receipt_digest(self) -> str:
        return logical_digest(self)


def compile_materialization_receipt(payload: Mapping[str, Any]) -> MaterializationReceiptV1:
    if not isinstance(payload, Mapping):
        raise ValueError("materialization payload must be a mapping")
    return MaterializationReceiptV1(**dict(payload))


def compile_consumer_observation(payload: Mapping[str, Any]) -> ConsumerAdmissionObservationV1:
    """Compile raw caller input only into an untrusted observation/claim."""
    if not isinstance(payload, Mapping):
        raise ValueError("consumer payload must be a mapping")
    return ConsumerAdmissionObservationV1(**dict(payload))


def _resolution_matches(
    materialization: MaterializationReceiptV1,
    observation: ConsumerAdmissionObservationV1,
    evidence: ResolvedConsumerAdmissionEvidenceV1,
    expectation: ConsumerAdmissionResolverExpectationV1,
) -> bool:
    return all((
        evidence.resolver_ref == expectation.resolver_ref,
        evidence.resolver_generation == expectation.resolver_generation,
        evidence.consumer_owner == expectation.consumer_owner == observation.consumer_owner,
        evidence.consumer_generation == expectation.consumer_generation == observation.consumer_generation,
        evidence.consumer_currentness_ref == expectation.consumer_currentness_ref == observation.consumer_currentness_ref,
        evidence.consumer_currentness_generation == expectation.consumer_currentness_generation,
        evidence.observed_target_ref == observation.observed_target_ref == materialization.materialized_target_ref,
        evidence.observed_target_digest == observation.observed_target_digest == materialization.materialized_target_digest,
        evidence.idempotency_key == observation.idempotency_key == materialization.idempotency_key,
        evidence.admission_receipt_ref == observation.admission_receipt_ref,
    ))


def adjudicate(
    materialization: MaterializationReceiptV1,
    observation: ConsumerAdmissionObservationV1 | None = None,
    *,
    resolution_evidence: ResolvedConsumerAdmissionEvidenceV1 | None = None,
    resolver_expectation: ConsumerAdmissionResolverExpectationV1 | None = None,
) -> AdjudicationResultV1:
    """Adjudicate without allowing raw booleans/non-empty refs to self-certify current admission."""
    if not isinstance(materialization, MaterializationReceiptV1):
        raise ValueError("materialization must be MaterializationReceiptV1")

    disposition = AdjudicationDisposition.MATERIALIZED_NOT_ADMITTED
    admitted = False
    executed = False

    if observation is not None:
        if not isinstance(observation, ConsumerAdmissionObservationV1):
            raise ValueError("observation must be ConsumerAdmissionObservationV1")
        if observation.idempotency_key != materialization.idempotency_key:
            disposition = AdjudicationDisposition.IDEMPOTENCY_MISMATCH
        elif observation.observed_target_ref != materialization.materialized_target_ref:
            disposition = AdjudicationDisposition.ADMISSION_TARGET_MISMATCH
        elif observation.observed_target_digest != materialization.materialized_target_digest:
            disposition = AdjudicationDisposition.ADMISSION_TARGET_DIGEST_MISMATCH
        elif not observation.consumer_current or observation.admission_state is AdmissionState.STALE_REOPEN:
            disposition = AdjudicationDisposition.CURRENTNESS_REOPEN
        elif observation.admission_state is AdmissionState.REFUSED:
            disposition = AdjudicationDisposition.CONSUMER_REFUSED
        elif observation.admission_state is AdmissionState.DUPLICATE_NOOP:
            disposition = AdjudicationDisposition.DUPLICATE_NOOP_OBSERVED
        elif observation.admission_state is AdmissionState.ADMITTED:
            if resolution_evidence is None or resolver_expectation is None:
                disposition = AdjudicationDisposition.EVIDENCE_REQUIRED
            elif not isinstance(resolution_evidence, ResolvedConsumerAdmissionEvidenceV1):
                raise ValueError("resolution_evidence must be ResolvedConsumerAdmissionEvidenceV1")
            elif not isinstance(resolver_expectation, ConsumerAdmissionResolverExpectationV1):
                raise ValueError("resolver_expectation must be ConsumerAdmissionResolverExpectationV1")
            elif not _resolution_matches(materialization, observation, resolution_evidence, resolver_expectation):
                disposition = AdjudicationDisposition.EVIDENCE_MISMATCH
            elif not resolution_evidence.resolved_current:
                disposition = AdjudicationDisposition.CURRENTNESS_REOPEN
            elif not resolution_evidence.resolved_admitted:
                disposition = AdjudicationDisposition.EVIDENCE_REQUIRED
            else:
                admitted = True
                if observation.execution_state is ExecutionState.EXECUTED:
                    executed = True
                    disposition = AdjudicationDisposition.EXECUTION_OBSERVED
                elif observation.execution_state is ExecutionState.FAILED:
                    disposition = AdjudicationDisposition.EXECUTION_FAILED
                elif observation.execution_state is ExecutionState.RECONCILE_REQUIRED:
                    disposition = AdjudicationDisposition.RECONCILE_REQUIRED
                else:
                    disposition = AdjudicationDisposition.CONSUMER_ADMITTED_CURRENT

    return AdjudicationResultV1(
        disposition=disposition,
        materialized_target_ref=materialization.materialized_target_ref,
        materialized_target_digest=materialization.materialized_target_digest,
        idempotency_key=materialization.idempotency_key,
        consumer_admitted_current=admitted,
        execution_observed=executed,
        observation_digest=None if observation is None else observation.receipt_digest,
        resolution_evidence_digest=None if resolution_evidence is None else resolution_evidence.receipt_digest,
        resolver_expectation_digest=None if resolver_expectation is None else resolver_expectation.receipt_digest,
    )
