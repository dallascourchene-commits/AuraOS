"""Fail-closed AWJ032 GLM-5.3 owner-host C2 canary handoff contract.

This module closes only the transport boundary between the current native-synthetic
W3 proof and an eventual owner-host canary runner.  It does not execute a model,
authorize an effect, authenticate the host producer, or admit G2.

The request is a bounded effect *proposal* bound to exact upstream generations.
The returned receipt is integrity/currentness evidence only until an independent
owner-host producer registry (the W4 lifecycle lane) authenticates it.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any

REQUEST_SCHEMA = "AWJ032GLM53OwnerHostC2CanaryRequestV1"
RECEIPT_SCHEMA = "AWJ032GLM53OwnerHostC2CanaryReceiptV1"
CURRENT_W3_HEAD = "218992d7abafdd54c516b84baa778fcd960b2b5b"
CURRENT_PREFLIGHT_HEAD = "7038c24ef7972415fe10bea2261cc69c695bb9d8"
OFFICIAL_MODEL_REPO = "zai-org/GLM-5.3"
OFFICIAL_MODEL_REVISION = "7cda81930d6e4cef42f48555de830aa32ecdde28"
C2_STAGE = "C2_BOUNDED_OWNER_HOST_CANARY"


class OwnerHostC2HandoffError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}:{detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise OwnerHostC2HandoffError("NONCANONICAL_HANDOFF_STATE") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OwnerHostC2HandoffError(code)
    return value.strip()


def _sha256(value: Any, code: str) -> str:
    value = _text(value, code)
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise OwnerHostC2HandoffError(code)
    return value


def _positive_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise OwnerHostC2HandoffError(code)
    return value


def _nonneg_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise OwnerHostC2HandoffError(code)
    return value


def _positive_float(value: Any, code: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OwnerHostC2HandoffError(code)
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise OwnerHostC2HandoffError(code)
    return value


def _exact_bool(value: Any, expected: bool, code: str) -> None:
    if type(value) is not bool or value is not expected:
        raise OwnerHostC2HandoffError(code)


def _utc(value: Any, code: str) -> datetime:
    text = _text(value, code)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OwnerHostC2HandoffError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise OwnerHostC2HandoffError(code)
    return parsed


@dataclass(frozen=True)
class OwnerHostC2CanaryRequest:
    w3_proof_logical_id: str
    preflight_receipt_digest: str
    airllm_source_revision: str
    airllm_security_evidence_digest: str
    host_snapshot_digest: str
    storage_plan_digest: str
    workspace_root: str
    max_payload_bytes: int
    max_wall_seconds: int
    effect_admission_ref: str
    w3_head_sha: str = CURRENT_W3_HEAD
    preflight_head_sha: str = CURRENT_PREFLIGHT_HEAD
    model_repo: str = OFFICIAL_MODEL_REPO
    model_revision: str = OFFICIAL_MODEL_REVISION
    canary_stage: str = C2_STAGE
    trust_remote_code: bool = False
    allow_remote_fallback: bool = False
    allow_model_substitution: bool = False
    require_safetensors: bool = True
    source_recoverable: bool = True
    execution_authorized_by_this_contract: bool = False
    g2_admitted: bool = False
    schema: str = REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != REQUEST_SCHEMA:
            raise OwnerHostC2HandoffError("REQUEST_SCHEMA_MISMATCH")
        if self.w3_head_sha != CURRENT_W3_HEAD:
            raise OwnerHostC2HandoffError("W3_HEAD_NOT_CURRENT_CONTRACT_GENERATION")
        if self.preflight_head_sha != CURRENT_PREFLIGHT_HEAD:
            raise OwnerHostC2HandoffError("PREFLIGHT_HEAD_NOT_CURRENT_CONTRACT_GENERATION")
        if self.model_repo != OFFICIAL_MODEL_REPO or self.model_revision != OFFICIAL_MODEL_REVISION:
            raise OwnerHostC2HandoffError("MODEL_SOURCE_SUBSTITUTION")
        if self.canary_stage != C2_STAGE:
            raise OwnerHostC2HandoffError("CANARY_STAGE_MISMATCH")
        for value, code in (
            (self.w3_proof_logical_id, "W3_PROOF_LOGICAL_ID_INVALID"),
            (self.preflight_receipt_digest, "PREFLIGHT_RECEIPT_DIGEST_INVALID"),
            (self.airllm_security_evidence_digest, "AIRLLM_SECURITY_DIGEST_INVALID"),
            (self.host_snapshot_digest, "HOST_SNAPSHOT_DIGEST_INVALID"),
            (self.storage_plan_digest, "STORAGE_PLAN_DIGEST_INVALID"),
        ):
            _sha256(value, code)
        _text(self.airllm_source_revision, "AIRLLM_SOURCE_REVISION_REQUIRED")
        workspace = _text(self.workspace_root, "WORKSPACE_ROOT_REQUIRED")
        if not workspace.startswith("/") or workspace in {"/", "/home", "/mnt"}:
            raise OwnerHostC2HandoffError("WORKSPACE_ROOT_MUST_BE_BOUNDED_ABSOLUTE_PATH")
        _positive_int(self.max_payload_bytes, "MAX_PAYLOAD_BYTES_INVALID")
        _positive_int(self.max_wall_seconds, "MAX_WALL_SECONDS_INVALID")
        _text(self.effect_admission_ref, "EFFECT_ADMISSION_REF_REQUIRED")
        _exact_bool(self.trust_remote_code, False, "REMOTE_CODE_FORBIDDEN")
        _exact_bool(self.allow_remote_fallback, False, "REMOTE_FALLBACK_FORBIDDEN")
        _exact_bool(self.allow_model_substitution, False, "MODEL_SUBSTITUTION_FORBIDDEN")
        _exact_bool(self.require_safetensors, True, "SAFETENSORS_REQUIRED")
        _exact_bool(self.source_recoverable, True, "SOURCE_RECOVERABILITY_REQUIRED")
        _exact_bool(self.execution_authorized_by_this_contract, False, "HANDOFF_CANNOT_AUTHORIZE_EXECUTION")
        _exact_bool(self.g2_admitted, False, "HANDOFF_CANNOT_ADMIT_G2")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def request_digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class OwnerHostC2CanaryReceipt:
    request_digest: str
    owner_host_observation_id: str
    runner_identity: str
    runner_generation: str
    started_at_utc: str
    ended_at_utc: str
    command_digest: str
    environment_digest: str
    source_snapshot_digest: str
    airllm_source_revision: str
    model_repo: str
    model_revision: str
    actual_payload_bytes: int
    tensor_read_operations: int
    physical_read_bytes: int
    elapsed_seconds: float
    process_exit_code: int
    generated_token_count: int
    generated_output_sha256: str | None
    lifecycle_measurement_ref: str
    host_measurement_ref: str
    trust_remote_code: bool = False
    remote_model_execution_observed: bool = False
    smaller_model_substitution_observed: bool = False
    synthetic_fixture_substitution_observed: bool = False
    full_model_complete_architecture_proven: bool = False
    producer_authenticated_by_this_contract: bool = False
    effect_authority_proven: bool = False
    g2_admitted: bool = False
    schema: str = RECEIPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RECEIPT_SCHEMA:
            raise OwnerHostC2HandoffError("RECEIPT_SCHEMA_MISMATCH")
        for value, code in (
            (self.request_digest, "REQUEST_DIGEST_INVALID"),
            (self.command_digest, "COMMAND_DIGEST_INVALID"),
            (self.environment_digest, "ENVIRONMENT_DIGEST_INVALID"),
            (self.source_snapshot_digest, "SOURCE_SNAPSHOT_DIGEST_INVALID"),
        ):
            _sha256(value, code)
        for value, code in (
            (self.owner_host_observation_id, "OWNER_HOST_OBSERVATION_ID_REQUIRED"),
            (self.runner_identity, "RUNNER_IDENTITY_REQUIRED"),
            (self.runner_generation, "RUNNER_GENERATION_REQUIRED"),
            (self.airllm_source_revision, "AIRLLM_SOURCE_REVISION_REQUIRED"),
            (self.lifecycle_measurement_ref, "LIFECYCLE_MEASUREMENT_REF_REQUIRED"),
            (self.host_measurement_ref, "HOST_MEASUREMENT_REF_REQUIRED"),
        ):
            _text(value, code)
        if self.model_repo != OFFICIAL_MODEL_REPO or self.model_revision != OFFICIAL_MODEL_REVISION:
            raise OwnerHostC2HandoffError("RECEIPT_MODEL_SOURCE_SUBSTITUTION")
        start = _utc(self.started_at_utc, "STARTED_AT_UTC_INVALID")
        end = _utc(self.ended_at_utc, "ENDED_AT_UTC_INVALID")
        if end < start:
            raise OwnerHostC2HandoffError("RECEIPT_TIME_REVERSED")
        _nonneg_int(self.actual_payload_bytes, "ACTUAL_PAYLOAD_BYTES_INVALID")
        _nonneg_int(self.tensor_read_operations, "TENSOR_READ_OPERATIONS_INVALID")
        _nonneg_int(self.physical_read_bytes, "PHYSICAL_READ_BYTES_INVALID")
        elapsed = _positive_float(self.elapsed_seconds, "ELAPSED_SECONDS_INVALID")
        observed_elapsed = (end - start).total_seconds()
        if abs(observed_elapsed - elapsed) > max(1.0, observed_elapsed * 0.05):
            raise OwnerHostC2HandoffError("ELAPSED_TIME_NOT_BOUND_TO_TIMESTAMPS")
        if isinstance(self.process_exit_code, bool) or not isinstance(self.process_exit_code, int):
            raise OwnerHostC2HandoffError("PROCESS_EXIT_CODE_INVALID")
        tokens = _nonneg_int(self.generated_token_count, "GENERATED_TOKEN_COUNT_INVALID")
        if tokens:
            _sha256(self.generated_output_sha256, "GENERATED_OUTPUT_DIGEST_REQUIRED")
        elif self.generated_output_sha256 is not None:
            raise OwnerHostC2HandoffError("OUTPUT_DIGEST_WITHOUT_GENERATED_TOKENS")
        _exact_bool(self.trust_remote_code, False, "RECEIPT_REMOTE_CODE_FORBIDDEN")
        _exact_bool(self.remote_model_execution_observed, False, "REMOTE_MODEL_EXECUTION_FORBIDDEN")
        _exact_bool(self.smaller_model_substitution_observed, False, "SMALLER_MODEL_SUBSTITUTION_FORBIDDEN")
        _exact_bool(self.synthetic_fixture_substitution_observed, False, "SYNTHETIC_FIXTURE_SUBSTITUTION_FORBIDDEN")
        _exact_bool(self.full_model_complete_architecture_proven, False, "C2_RECEIPT_CANNOT_PROVE_FULL_MODEL_COMPLETENESS")
        _exact_bool(self.producer_authenticated_by_this_contract, False, "HANDOFF_CANNOT_AUTHENTICATE_PRODUCER")
        _exact_bool(self.effect_authority_proven, False, "HANDOFF_CANNOT_PROVE_EFFECT_AUTHORITY")
        _exact_bool(self.g2_admitted, False, "HANDOFF_CANNOT_ADMIT_G2")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def receipt_digest(self) -> str:
        return _digest(self.to_dict())


@dataclass(frozen=True)
class OwnerHostC2JoinReceipt:
    request_digest: str
    attempt_receipt_digest: str
    w3_proof_logical_id: str
    preflight_receipt_digest: str
    host_attempt_integrity_checked: bool
    bounded_payload_respected: bool
    local_only_constraints_respected: bool
    generated_output_observed: bool
    canary_process_succeeded: bool
    lifecycle_measurement_ref: str
    producer_authentication_required: bool = True
    lifecycle_registry_required: bool = True
    real_w4_policy_winner_proven: bool = False
    full_model_runtime_proven: bool = False
    g2_admitted: bool = False
    effect_authority_proven: bool = False
    claim_ceiling: str = "D0_OWNER_HOST_C2_HANDOFF_INTEGRITY_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def logical_id(self) -> str:
        return _digest(self.to_dict())


def join_owner_host_c2_attempt(
    *,
    request: OwnerHostC2CanaryRequest,
    receipt: OwnerHostC2CanaryReceipt,
) -> OwnerHostC2JoinReceipt:
    """Bind one owner-host attempt to the exact request without minting producer trust."""
    if not isinstance(request, OwnerHostC2CanaryRequest):
        raise OwnerHostC2HandoffError("OWNER_HOST_C2_REQUEST_REQUIRED")
    if not isinstance(receipt, OwnerHostC2CanaryReceipt):
        raise OwnerHostC2HandoffError("OWNER_HOST_C2_RECEIPT_REQUIRED")
    if receipt.request_digest != request.request_digest:
        raise OwnerHostC2HandoffError("RECEIPT_NOT_FOR_REQUEST")
    if receipt.airllm_source_revision != request.airllm_source_revision:
        raise OwnerHostC2HandoffError("AIRLLM_GENERATION_DRIFT")
    if receipt.actual_payload_bytes > request.max_payload_bytes:
        raise OwnerHostC2HandoffError("C2_PAYLOAD_BUDGET_EXCEEDED")
    observed_elapsed = (_utc(receipt.ended_at_utc, "ENDED_AT_UTC_INVALID") - _utc(receipt.started_at_utc, "STARTED_AT_UTC_INVALID")).total_seconds()
    if observed_elapsed > request.max_wall_seconds:
        raise OwnerHostC2HandoffError("C2_WALL_TIME_BUDGET_EXCEEDED")

    succeeded = receipt.process_exit_code == 0
    generated = succeeded and receipt.generated_token_count > 0
    return OwnerHostC2JoinReceipt(
        request_digest=request.request_digest,
        attempt_receipt_digest=receipt.receipt_digest,
        w3_proof_logical_id=request.w3_proof_logical_id,
        preflight_receipt_digest=request.preflight_receipt_digest,
        host_attempt_integrity_checked=True,
        bounded_payload_respected=True,
        local_only_constraints_respected=True,
        generated_output_observed=generated,
        canary_process_succeeded=succeeded,
        lifecycle_measurement_ref=receipt.lifecycle_measurement_ref,
    )
