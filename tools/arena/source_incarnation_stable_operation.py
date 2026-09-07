from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json
from typing import Callable, Protocol, runtime_checkable

D0 = "D0_NONPROMOTING"
SCHEMA = "AURA-SOURCE-INCARNATION-STABLE-OPERATION-v1"


def canon(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(canon(value)).hexdigest()


def root_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


@runtime_checkable
class SourceIncarnationLike(Protocol):
    file_id: str
    revision_id: str
    export_mime_type: str
    export_bytes: bytes
    @property
    def incarnation_root(self) -> str: ...


@dataclass(frozen=True)
class SourceIncarnationProjection:
    file_id: str
    revision_id: str
    export_mime_type: str
    export_root: str
    incarnation_root: str

    def __post_init__(self) -> None:
        for n in ("file_id", "revision_id", "export_mime_type"):
            _id(getattr(self, n), n)
        _root(self.export_root, "export_root")
        _root(self.incarnation_root, "incarnation_root")


def project_source_incarnation(source: SourceIncarnationLike) -> SourceIncarnationProjection:
    if not isinstance(source, SourceIncarnationLike):
        raise ValueError("SOURCE_INCARNATION_OBJECT_REQUIRED")
    if not isinstance(source.export_bytes, bytes):
        raise ValueError("SOURCE_EXPORT_BYTES_REQUIRED")
    export_root = root_bytes(source.export_bytes)
    expected = digest({
        "schema": "AURA-PROJECT006-TRANSPORT-SOURCE-IDENTITY-BRIDGE-v1",
        "kind": "drive_source_incarnation",
        "file_id": source.file_id,
        "revision_id": source.revision_id,
        "export_mime_type": source.export_mime_type,
        "export_root": export_root,
    })
    if source.incarnation_root != expected:
        raise ValueError("SOURCE_INCARNATION_ROOT_NOT_INDEPENDENTLY_REPRODUCIBLE")
    return SourceIncarnationProjection(source.file_id, source.revision_id, source.export_mime_type, export_root, expected)


@dataclass(frozen=True)
class StableOperationIntent:
    domain: str
    operation_kind: str
    occurrence_scope: str
    semantic_payload_root: str
    policy_root: str

    def __post_init__(self) -> None:
        for n in ("domain", "operation_kind", "occurrence_scope"):
            _id(getattr(self, n), n)
        _root(self.semantic_payload_root, "semantic_payload_root")
        _root(self.policy_root, "policy_root")


@dataclass(frozen=True)
class StableSourceOperation:
    source: SourceIncarnationProjection
    intent: StableOperationIntent
    operation_root: str

    def __post_init__(self) -> None:
        _root(self.operation_root, "operation_root")


def compile_stable_operation(source: SourceIncarnationLike, intent: StableOperationIntent) -> StableSourceOperation:
    src = project_source_incarnation(source)
    operation_root = digest({
        "schema": SCHEMA,
        "kind": "stable_source_operation",
        "source_incarnation_root": src.incarnation_root,
        "domain": intent.domain,
        "operation_kind": intent.operation_kind,
        "occurrence_scope": intent.occurrence_scope,
        "semantic_payload_root": intent.semantic_payload_root,
        "policy_root": intent.policy_root,
    })
    return StableSourceOperation(src, intent, operation_root)


@dataclass(frozen=True)
class AdmissionClaim:
    operation_root: str
    admission_root: str
    currentness_root: str
    actor_id: str
    card_root: str
    lease_root: str
    progress_root: str
    host_generation: int
    admission_generation: int
    k27: tuple[int, int, int]

    def __post_init__(self) -> None:
        for n in ("operation_root", "admission_root", "currentness_root", "card_root", "lease_root", "progress_root"):
            _root(getattr(self, n), n)
        _id(self.actor_id, "actor_id")
        if self.host_generation < 0 or self.admission_generation < 0:
            raise ValueError("generations must be nonnegative")
        if len(self.k27) != 3 or any(type(v) is not int or v < 0 or v > 26 for v in self.k27):
            raise ValueError("k27 must be three integers in [0,26]")


@dataclass(frozen=True)
class VerifiedAdmission:
    claim_root: str
    operation_root: str
    admission_root: str
    currentness_root: str
    actor_id: str
    card_root: str
    lease_root: str
    progress_root: str
    host_generation: int
    admission_generation: int
    k27: tuple[int, int, int]
    authority: str = D0
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        for n in ("claim_root", "operation_root", "admission_root", "currentness_root", "card_root", "lease_root", "progress_root"):
            _root(getattr(self, n), n)
        if self.authority != D0 or self.effect_authority or self.gate10:
            raise ValueError("verified admission cannot widen authority")


AdmissionResolver = Callable[[AdmissionClaim], VerifiedAdmission | None]


class Disposition(str, Enum):
    ATTEMPT_D0 = "ATTEMPT_D0"
    HOLD = "HOLD"
    REBIND = "REBIND"
    REPROVE = "REPROVE"


@dataclass(frozen=True)
class AttemptDecision:
    disposition: Disposition
    reason: str
    operation_root: str
    attempt_root: str | None = None
    authority: str = D0
    effect_authority: bool = False
    transport_digest_authority: bool = False
    gate10: bool = False

    def __post_init__(self) -> None:
        _root(self.operation_root, "operation_root")
        if self.attempt_root is not None:
            _root(self.attempt_root, "attempt_root")
        if self.authority != D0 or self.effect_authority or self.transport_digest_authority or self.gate10:
            raise ValueError("attempt decision cannot widen authority")


def _verified_claim_root(claim: AdmissionClaim) -> str:
    return digest({
        "schema": SCHEMA,
        "kind": "admission_claim",
        "operation_root": claim.operation_root,
        "admission_root": claim.admission_root,
        "currentness_root": claim.currentness_root,
        "actor_id": claim.actor_id,
        "card_root": claim.card_root,
        "lease_root": claim.lease_root,
        "progress_root": claim.progress_root,
        "host_generation": claim.host_generation,
        "admission_generation": claim.admission_generation,
        "k27": list(claim.k27),
    })


def compile_attempt(operation: StableSourceOperation, claim: AdmissionClaim, resolver: AdmissionResolver,
                    *, transport_observation_root: str | None = None, transport_required: bool = False) -> AttemptDecision:
    if claim.operation_root != operation.operation_root:
        return AttemptDecision(Disposition.REBIND, "ADMISSION_OPERATION_MOVED", operation.operation_root)
    if transport_required and transport_observation_root is None:
        return AttemptDecision(Disposition.HOLD, "TRANSPORT_SOURCE_OBSERVATION_REQUIRED", operation.operation_root)
    if transport_observation_root is not None:
        try:
            _root(transport_observation_root, "transport_observation_root")
        except ValueError:
            return AttemptDecision(Disposition.REPROVE, "TRANSPORT_SOURCE_OBSERVATION_INVALID", operation.operation_root)
    verified = resolver(claim)
    if verified is None:
        return AttemptDecision(Disposition.HOLD, "CANONICAL_ADMISSION_NOT_VERIFIED", operation.operation_root)
    if verified.claim_root != _verified_claim_root(claim):
        return AttemptDecision(Disposition.REPROVE, "VERIFIED_ADMISSION_CLAIM_ROOT_DIVERGED", operation.operation_root)
    for name in ("operation_root", "admission_root", "currentness_root", "actor_id", "card_root", "lease_root", "progress_root", "host_generation", "admission_generation", "k27"):
        if getattr(verified, name) != getattr(claim, name):
            return AttemptDecision(Disposition.REBIND, f"VERIFIED_ADMISSION_{name.upper()}_DIVERGED", operation.operation_root)
    attempt_root = digest({
        "schema": SCHEMA,
        "kind": "source_incarnation_attempt",
        "operation_root": operation.operation_root,
        "source_incarnation_root": operation.source.incarnation_root,
        "verified_admission_claim_root": verified.claim_root,
        "admission_root": verified.admission_root,
        "currentness_root": verified.currentness_root,
        "actor_id": verified.actor_id,
        "card_root": verified.card_root,
        "lease_root": verified.lease_root,
        "progress_root": verified.progress_root,
        "host_generation": verified.host_generation,
        "admission_generation": verified.admission_generation,
        "k27": list(verified.k27),
        "transport_observation_root": transport_observation_root,
        "authority": D0,
        "effect_authority": False,
        "transport_digest_authority": False,
        "gate10": False,
    })
    return AttemptDecision(Disposition.ATTEMPT_D0, "SOURCE_OPERATION_AND_CURRENT_ADMISSION_BOUND", operation.operation_root, attempt_root)


def make_test_verified_admission(claim: AdmissionClaim) -> VerifiedAdmission:
    return VerifiedAdmission(
        claim_root=_verified_claim_root(claim), operation_root=claim.operation_root,
        admission_root=claim.admission_root, currentness_root=claim.currentness_root,
        actor_id=claim.actor_id, card_root=claim.card_root, lease_root=claim.lease_root,
        progress_root=claim.progress_root, host_generation=claim.host_generation,
        admission_generation=claim.admission_generation, k27=claim.k27,
    )
