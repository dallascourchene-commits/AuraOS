from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
import unicodedata
from typing import Any, Iterable, Mapping, Sequence

TRIAD_OBJECTIVE_BINDING_SCHEMA = "AURAOS_V9_TRIAD_OBJECTIVE_BINDING_V1"
TRIAD_OUTPUT_REF_SCHEMA = "AURAOS_V9_TRIAD_OUTPUT_REF_V1"
TRIAD_ROUND_COMMIT_SCHEMA = "AURAOS_V9_TRIAD_ROUND_COMMIT_RECEIPT_V1"
TRIAD_CANONICAL_PROFILE = "AURAOS_V9_TRIAD_CANONICAL_JSON_V1"
OBJECTIVE_BINDING_DOMAIN = "AURA::V9::TRIAD::OBJECTIVE-BINDING::V1"
ROUND_COMMIT_DOMAIN = "AURA::V9::TRIAD::ROUND-COMMIT::V1"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_MAX_JCS_SAFE_INTEGER = (1 << 53) - 1


class ContractViolation(ValueError):
    """Fail-closed structural validation error for the V9 triad model."""


def _nfc(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise ContractViolation(f"{field} must be a string")
    normalized = unicodedata.normalize("NFC", value)
    if not normalized:
        raise ContractViolation(f"{field} must be non-empty")
    return normalized


def _digest(value: str, field: str) -> str:
    normalized = _nfc(value, field)
    if not _HEX64.fullmatch(normalized):
        raise ContractViolation(f"{field} must be lowercase 64-hex SHA-256 syntax")
    return normalized


def _generation(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > _MAX_JCS_SAFE_INTEGER:
        raise ContractViolation(f"{field} must be a non-negative JCS-safe integer <= {_MAX_JCS_SAFE_INTEGER}")
    return value


def _normalize_json(value: Any, field: str = "value") -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if value is None or isinstance(value, float):
        raise ContractViolation(f"{field} contains unsupported JSON value")
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return _generation(value, field)
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item, f"{field}[]") for item in value]
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = _nfc(key, f"{field}.key")
            if normalized_key in normalized:
                raise ContractViolation(f"{field} has duplicate canonical key")
            normalized[normalized_key] = _normalize_json(item, f"{field}.{normalized_key}")
        return normalized
    raise ContractViolation(f"{field} contains unsupported type {type(value).__name__}")


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    normalized = _normalize_json(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _hash_domain(domain: str, body: Mapping[str, Any]) -> str:
    if "domain_separator" in body:
        raise ContractViolation("body may not supply domain_separator")
    return hashlib.sha256(
        canonical_json_bytes({"domain_separator": domain, **dict(body)})
    ).hexdigest()


def _canonical_string_set(values: Iterable[str], field: str) -> tuple[str, ...]:
    normalized = [_nfc(value, field) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ContractViolation(f"{field} contains duplicate canonical members")
    return tuple(sorted(normalized, key=lambda item: item.encode("utf-8")))


class TriadPosition(str, Enum):
    X = "X"
    Y = "Y"
    Z = "Z"


class RoundCommitStatus(str, Enum):
    COMMITTED = "COMMITTED"
    WAIT = "WAIT"
    REPAIR = "REPAIR"
    REOPEN = "REOPEN"


@dataclass(frozen=True)
class Epoch:
    value: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _generation(self.value, "epoch"))

    def protected_value(self) -> int:
        return self.value


@dataclass(frozen=True)
class ObjectiveBinding:
    objective_id: str
    objective_digest: str
    semantic_environment: str
    source_generation: int
    currentness_digest: str
    authority_ceiling_digest: str

    def protected_body(self) -> dict[str, Any]:
        return {
            "schema": TRIAD_OBJECTIVE_BINDING_SCHEMA,
            "canonical_profile_id": TRIAD_CANONICAL_PROFILE,
            "objective_id": _nfc(self.objective_id, "objective_id"),
            "objective_digest": _digest(self.objective_digest, "objective_digest"),
            "semantic_environment": _nfc(self.semantic_environment, "semantic_environment"),
            "source_generation": _generation(self.source_generation, "source_generation"),
            "currentness_digest": _digest(self.currentness_digest, "currentness_digest"),
            "authority_ceiling_digest": _digest(self.authority_ceiling_digest, "authority_ceiling_digest"),
        }

    def identity(self) -> str:
        return _hash_domain(OBJECTIVE_BINDING_DOMAIN, self.protected_body())


@dataclass(frozen=True)
class OutputRef:
    position: TriadPosition
    epoch: Epoch
    output_digest: str
    objective_binding_identity: str
    source_generation: int
    currentness_digest: str
    authority_ceiling_digest: str
    round_receipt_identity: str
    committed: bool = True

    def protected_body(self) -> dict[str, Any]:
        if not isinstance(self.position, TriadPosition):
            raise ContractViolation("position must be a TriadPosition")
        if not isinstance(self.epoch, Epoch):
            raise ContractViolation("epoch must be an Epoch")
        if not isinstance(self.committed, bool):
            raise ContractViolation("committed must be boolean")
        return {
            "schema": TRIAD_OUTPUT_REF_SCHEMA,
            "position": self.position.value,
            "epoch": self.epoch.protected_value(),
            "output_digest": _digest(self.output_digest, "output_digest"),
            "objective_binding_identity": _digest(
                self.objective_binding_identity, "objective_binding_identity"
            ),
            "source_generation": _generation(self.source_generation, "source_generation"),
            "currentness_digest": _digest(self.currentness_digest, "currentness_digest"),
            "authority_ceiling_digest": _digest(self.authority_ceiling_digest, "authority_ceiling_digest"),
            "round_receipt_identity": _digest(self.round_receipt_identity, "round_receipt_identity"),
            "committed": self.committed,
        }


@dataclass(frozen=True)
class PositionExecutionIdentity:
    position: TriadPosition
    worker_id: str
    model_id: str
    provider_id: str
    evidence_independence_group: str
    physical_assignment_ref: str
    authority_ceiling_digest: str

    def protected_body(self) -> dict[str, Any]:
        if not isinstance(self.position, TriadPosition):
            raise ContractViolation("execution position must be a TriadPosition")
        return {
            "position": self.position.value,
            "worker_id": _nfc(self.worker_id, "worker_id"),
            "model_id": _nfc(self.model_id, "model_id"),
            "provider_id": _nfc(self.provider_id, "provider_id"),
            "evidence_independence_group": _nfc(
                self.evidence_independence_group, "evidence_independence_group"
            ),
            "physical_assignment_ref": _nfc(self.physical_assignment_ref, "physical_assignment_ref"),
            "authority_ceiling_digest": _digest(self.authority_ceiling_digest, "authority_ceiling_digest"),
        }


def _canonical_output_refs(values: Sequence[OutputRef], field: str) -> tuple[dict[str, Any], ...]:
    bodies = [value.protected_body() for value in values]
    encoded = [canonical_json_bytes(body) for body in bodies]
    if len(set(encoded)) != len(encoded):
        raise ContractViolation(f"{field} contains duplicate canonical members")
    return tuple(body for _, body in sorted(zip(encoded, bodies), key=lambda pair: pair[0]))


@dataclass(frozen=True)
class TriadRoundCommitReceipt:
    workflow_id: str
    objective: ObjectiveBinding
    epoch: Epoch
    bootstrap_flag: bool
    x_peer_inputs: Sequence[OutputRef]
    y_peer_inputs: Sequence[OutputRef]
    z_peer_inputs: Sequence[OutputRef]
    external_evidence_refs: Sequence[str]
    x_output: OutputRef
    y_output: OutputRef
    z_output: OutputRef
    x_execution: PositionExecutionIdentity
    y_execution: PositionExecutionIdentity
    z_execution: PositionExecutionIdentity
    handoff_plan_ref: str
    committed_at: str
    commit_status: RoundCommitStatus

    def _slot_shape(self) -> None:
        if not isinstance(self.objective, ObjectiveBinding):
            raise ContractViolation("objective must be an ObjectiveBinding")
        if not isinstance(self.epoch, Epoch):
            raise ContractViolation("epoch must be an Epoch")
        if not isinstance(self.bootstrap_flag, bool):
            raise ContractViolation("bootstrap_flag must be boolean")
        if not isinstance(self.commit_status, RoundCommitStatus):
            raise ContractViolation("commit_status must be a RoundCommitStatus")
        for field, output, expected in (
            ("x_output", self.x_output, TriadPosition.X),
            ("y_output", self.y_output, TriadPosition.Y),
            ("z_output", self.z_output, TriadPosition.Z),
        ):
            if output.position is not expected:
                raise ContractViolation(f"{field} must carry position {expected.value}")
            if output.epoch != self.epoch:
                raise ContractViolation(f"{field} epoch must equal receipt epoch")
        for field, execution, expected in (
            ("x_execution", self.x_execution, TriadPosition.X),
            ("y_execution", self.y_execution, TriadPosition.Y),
            ("z_execution", self.z_execution, TriadPosition.Z),
        ):
            if execution.position is not expected:
                raise ContractViolation(f"{field} must carry position {expected.value}")

    def protected_body(self) -> dict[str, Any]:
        self._slot_shape()
        return {
            "schema": TRIAD_ROUND_COMMIT_SCHEMA,
            "canonical_profile_id": TRIAD_CANONICAL_PROFILE,
            "workflow_id": _nfc(self.workflow_id, "workflow_id"),
            "objective": self.objective.protected_body(),
            "objective_binding_identity": self.objective.identity(),
            "epoch": self.epoch.protected_value(),
            "bootstrap_flag": self.bootstrap_flag,
            "peer_inputs": {
                "X": list(_canonical_output_refs(self.x_peer_inputs, "x_peer_inputs")),
                "Y": list(_canonical_output_refs(self.y_peer_inputs, "y_peer_inputs")),
                "Z": list(_canonical_output_refs(self.z_peer_inputs, "z_peer_inputs")),
            },
            "external_evidence_refs": list(
                _canonical_string_set(self.external_evidence_refs, "external_evidence_refs")
            ),
            "outputs": {
                "X": self.x_output.protected_body(),
                "Y": self.y_output.protected_body(),
                "Z": self.z_output.protected_body(),
            },
            "execution_identities": {
                "X": self.x_execution.protected_body(),
                "Y": self.y_execution.protected_body(),
                "Z": self.z_execution.protected_body(),
            },
            "handoff_plan_ref": _nfc(self.handoff_plan_ref, "handoff_plan_ref"),
            "committed_at": _nfc(self.committed_at, "committed_at"),
            "commit_status": self.commit_status.value,
        }

    def receipt_digest(self) -> str:
        return _hash_domain(ROUND_COMMIT_DOMAIN, self.protected_body())

    def to_record(self) -> dict[str, Any]:
        body = self.protected_body()
        return {**body, "receipt_digest": self.receipt_digest()}
