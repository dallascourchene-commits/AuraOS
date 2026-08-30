"""Transport-neutral materialization -> consumer-admission currentness membrane.

D0 / evidence-only. This module does not schedule, dispatch, execute, review,
promote, merge, or authorize effects. It only adjudicates whether an exact
materialized target has been independently admitted by a current downstream
consumer, with execution and quality kept orthogonal.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re

SCHEMA = "MaterializationAdmissionCurrentnessBridgeV1"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,511}$")


class BridgeError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


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


class BridgeDisposition(str, Enum):
    MATERIALIZED_NOT_ADMITTED = "MATERIALIZED_NOT_ADMITTED"
    IDEMPOTENCY_MISMATCH = "IDEMPOTENCY_MISMATCH"
    ADMISSION_TARGET_MISMATCH = "ADMISSION_TARGET_MISMATCH"
    ADMISSION_TARGET_DIGEST_MISMATCH = "ADMISSION_TARGET_DIGEST_MISMATCH"
    CURRENTNESS_REOPEN = "CURRENTNESS_REOPEN"
    CONSUMER_REFUSED = "CONSUMER_REFUSED"
    DUPLICATE_NOOP_OBSERVED = "DUPLICATE_NOOP_OBSERVED"
    CONSUMER_ADMITTED_CURRENT = "CONSUMER_ADMITTED_CURRENT"
    EXECUTION_OBSERVED = "EXECUTION_OBSERVED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    RECONCILE_REQUIRED = "RECONCILE_REQUIRED"


def _token(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise BridgeError(code)
    out = value.strip()
    if not out or not _TOKEN.fullmatch(out):
        raise BridgeError(code)
    return out


def _sha(value: object, code: str) -> str:
    if not isinstance(value, str):
        raise BridgeError(code)
    out = value.strip().lower()
    if not _SHA256.fullmatch(out):
        raise BridgeError(code)
    return out


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise BridgeError("NONCANONICAL_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


@dataclass(frozen=True)
class MaterializationReceiptV1:
    transport: TransportClass
    producer_owner_ref: str
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

    def __post_init__(self) -> None:
        if not isinstance(self.transport, TransportClass):
            raise BridgeError("TRANSPORT_INVALID")
        for name in (
            "producer_owner_ref", "producer_generation", "policy_ref", "policy_generation",
            "parent_target_ref", "materialized_target_ref", "currentness_ref", "idempotency_key",
            "effect_receipt_ref",
        ):
            object.__setattr__(self, name, _token(getattr(self, name), f"{name.upper()}_INVALID"))
        for name in ("materialized_target_digest", "artifact_set_digest", "allowed_delta_digest"):
            object.__setattr__(self, name, _sha(getattr(self, name), f"{name.upper()}_INVALID"))
        if self.materialization_observed is not True:
            raise BridgeError("MATERIALIZATION_NOT_OBSERVED")

    @property
    def logical_digest(self) -> str:
        return _digest("AURA_MATERIALIZATION_RECEIPT_V1", {
            "transport": self.transport.value,
            "producer_owner_ref": self.producer_owner_ref,
            "producer_generation": self.producer_generation,
            "policy_ref": self.policy_ref,
            "policy_generation": self.policy_generation,
            "parent_target_ref": self.parent_target_ref,
            "materialized_target_ref": self.materialized_target_ref,
            "materialized_target_digest": self.materialized_target_digest,
            "artifact_set_digest": self.artifact_set_digest,
            "allowed_delta_digest": self.allowed_delta_digest,
            "currentness_ref": self.currentness_ref,
            "idempotency_key": self.idempotency_key,
            "effect_receipt_ref": self.effect_receipt_ref,
            "materialization_observed": True,
            "consumer_admitted": False,
            "execution_observed": False,
            "quality_satisfied": False,
            "authority": False,
        })


@dataclass(frozen=True)
class ConsumerAdmissionObservationV1:
    consumer_owner_ref: str
    consumer_generation: str
    observed_target_ref: str
    observed_target_digest: str
    idempotency_key: str
    consumer_currentness_ref: str
    consumer_current: bool
    admission_state: AdmissionState
    admission_receipt_ref: str | None
    execution_state: ExecutionState = ExecutionState.NOT_OBSERVED
    execution_receipt_ref: str | None = None

    def __post_init__(self) -> None:
        for name in ("consumer_owner_ref", "consumer_generation", "observed_target_ref", "idempotency_key", "consumer_currentness_ref"):
            object.__setattr__(self, name, _token(getattr(self, name), f"{name.upper()}_INVALID"))
        object.__setattr__(self, "observed_target_digest", _sha(self.observed_target_digest, "OBSERVED_TARGET_DIGEST_INVALID"))
        if type(self.consumer_current) is not bool:
            raise BridgeError("CONSUMER_CURRENT_BOOL_REQUIRED")
        if not isinstance(self.admission_state, AdmissionState):
            raise BridgeError("ADMISSION_STATE_INVALID")
        if not isinstance(self.execution_state, ExecutionState):
            raise BridgeError("EXECUTION_STATE_INVALID")
        if self.admission_state in {AdmissionState.ADMITTED, AdmissionState.REFUSED, AdmissionState.DUPLICATE_NOOP, AdmissionState.STALE_REOPEN}:
            if self.admission_receipt_ref is None:
                raise BridgeError("ADMISSION_RECEIPT_REQUIRED")
            object.__setattr__(self, "admission_receipt_ref", _token(self.admission_receipt_ref, "ADMISSION_RECEIPT_INVALID"))
        elif self.admission_receipt_ref is not None:
            object.__setattr__(self, "admission_receipt_ref", _token(self.admission_receipt_ref, "ADMISSION_RECEIPT_INVALID"))
        observed_exec = self.execution_state is not ExecutionState.NOT_OBSERVED
        if observed_exec and self.execution_receipt_ref is None:
            raise BridgeError("EXECUTION_RECEIPT_REQUIRED")
        if self.execution_receipt_ref is not None:
            object.__setattr__(self, "execution_receipt_ref", _token(self.execution_receipt_ref, "EXECUTION_RECEIPT_INVALID"))
        if observed_exec and self.admission_state is not AdmissionState.ADMITTED:
            raise BridgeError("EXECUTION_REQUIRES_ADMITTED_STATE")

    @property
    def logical_digest(self) -> str:
        return _digest("AURA_CONSUMER_ADMISSION_OBSERVATION_V1", {
            "consumer_owner_ref": self.consumer_owner_ref,
            "consumer_generation": self.consumer_generation,
            "observed_target_ref": self.observed_target_ref,
            "observed_target_digest": self.observed_target_digest,
            "idempotency_key": self.idempotency_key,
            "consumer_currentness_ref": self.consumer_currentness_ref,
            "consumer_current": self.consumer_current,
            "admission_state": self.admission_state.value,
            "admission_receipt_ref": self.admission_receipt_ref,
            "execution_state": self.execution_state.value,
            "execution_receipt_ref": self.execution_receipt_ref,
            "quality_claim": False,
            "authority": False,
        })


@dataclass(frozen=True)
class MaterializationAdmissionDecisionV1:
    disposition: BridgeDisposition
    materialization_digest: str
    observation_digest: str | None
    consumer_admitted: bool
    execution_observed: bool
    execution_succeeded: bool
    quality_satisfied: bool = False
    authority: bool = False
    effect_authorized: bool = False
    promotion_authorized: bool = False
    merge_authorized: bool = False
    schema: str = SCHEMA

    @property
    def logical_digest(self) -> str:
        return _digest("AURA_MATERIALIZATION_ADMISSION_DECISION_V1", {
            "schema": self.schema,
            "disposition": self.disposition.value,
            "materialization_digest": self.materialization_digest,
            "observation_digest": self.observation_digest,
            "consumer_admitted": self.consumer_admitted,
            "execution_observed": self.execution_observed,
            "execution_succeeded": self.execution_succeeded,
            "quality_satisfied": False,
            "authority": False,
            "effect_authorized": False,
            "promotion_authorized": False,
            "merge_authorized": False,
        })


def adjudicate_materialization_admission(materialization: MaterializationReceiptV1, observation: ConsumerAdmissionObservationV1 | None) -> MaterializationAdmissionDecisionV1:
    """Adjudicate exact consumer admission without widening downstream authority."""
    if not isinstance(materialization, MaterializationReceiptV1):
        raise BridgeError("MATERIALIZATION_RECEIPT_REQUIRED")
    md = materialization.logical_digest

    def decision(disposition: BridgeDisposition, *, admitted: bool = False, execution_observed: bool = False, execution_succeeded: bool = False) -> MaterializationAdmissionDecisionV1:
        return MaterializationAdmissionDecisionV1(
            disposition=disposition,
            materialization_digest=md,
            observation_digest=None if observation is None else observation.logical_digest,
            consumer_admitted=admitted,
            execution_observed=execution_observed,
            execution_succeeded=execution_succeeded,
        )

    if observation is None:
        return decision(BridgeDisposition.MATERIALIZED_NOT_ADMITTED)
    if not isinstance(observation, ConsumerAdmissionObservationV1):
        raise BridgeError("CONSUMER_OBSERVATION_INVALID")
    if observation.idempotency_key != materialization.idempotency_key:
        return decision(BridgeDisposition.IDEMPOTENCY_MISMATCH)
    if observation.observed_target_ref != materialization.materialized_target_ref:
        return decision(BridgeDisposition.ADMISSION_TARGET_MISMATCH)
    if observation.observed_target_digest != materialization.materialized_target_digest:
        return decision(BridgeDisposition.ADMISSION_TARGET_DIGEST_MISMATCH)
    if not observation.consumer_current or observation.admission_state is AdmissionState.STALE_REOPEN:
        return decision(BridgeDisposition.CURRENTNESS_REOPEN)
    if observation.admission_state is AdmissionState.NOT_OBSERVED:
        return decision(BridgeDisposition.MATERIALIZED_NOT_ADMITTED)
    if observation.admission_state is AdmissionState.REFUSED:
        return decision(BridgeDisposition.CONSUMER_REFUSED)
    if observation.admission_state is AdmissionState.DUPLICATE_NOOP:
        return decision(BridgeDisposition.DUPLICATE_NOOP_OBSERVED)
    if observation.execution_state is ExecutionState.NOT_OBSERVED:
        return decision(BridgeDisposition.CONSUMER_ADMITTED_CURRENT, admitted=True)
    if observation.execution_state is ExecutionState.EXECUTED:
        return decision(BridgeDisposition.EXECUTION_OBSERVED, admitted=True, execution_observed=True, execution_succeeded=True)
    if observation.execution_state is ExecutionState.FAILED:
        return decision(BridgeDisposition.EXECUTION_FAILED, admitted=True, execution_observed=True, execution_succeeded=False)
    return decision(BridgeDisposition.RECONCILE_REQUIRED, admitted=True, execution_observed=True, execution_succeeded=False)


class MaterializationAdmissionCurrentnessBridgeV1:
    """Namespace wrapper for consumers that prefer an explicit ABI object."""
    schema = SCHEMA

    @staticmethod
    def adjudicate(materialization: MaterializationReceiptV1, observation: ConsumerAdmissionObservationV1 | None) -> MaterializationAdmissionDecisionV1:
        return adjudicate_materialization_admission(materialization, observation)
