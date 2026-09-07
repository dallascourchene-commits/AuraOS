from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import hmac
import json

SCHEMA = "AURA-PROJECT006-SINK-EVIDENCE-RECOVERY-v1"
D0 = "D0_NONPROMOTING"


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 2048:
        raise ValueError(f"{field} required")
    return value


def _nn(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be nonnegative exact int")
    return value


class NativeState(str, Enum):
    ACK_WRITTEN_PRE_EFFECT = "ACK_WRITTEN_PRE_EFFECT"
    EXECUTION_STARTED = "EXECUTION_STARTED"
    RESULT_OBSERVED = "RESULT_OBSERVED"
    ERROR_TERMINAL = "ERROR_TERMINAL"
    COMPLETION_AMBIGUOUS = "COMPLETION_AMBIGUOUS"
    RETURN_WRITTEN = "RETURN_WRITTEN"


class RecoveryCapability(str, Enum):
    IDEMPOTENT_RETRY = "IDEMPOTENT_RETRY"
    QUERY_RECONCILE = "QUERY_RECONCILE"
    NON_RETRYABLE = "NON_RETRYABLE"


class SinkDisposition(str, Enum):
    ACCEPTED = "ACCEPTED"
    NOT_ACCEPTED = "NOT_ACCEPTED"
    UNKNOWN = "UNKNOWN"


class RecoveryAction(str, Enum):
    START_PROVIDER_ONCE = "START_PROVIDER_ONCE"
    RETRY_PROVIDER_SAME_OPERATION_ID = "RETRY_PROVIDER_SAME_OPERATION_ID"
    QUERY_RECONCILE = "QUERY_RECONCILE"
    CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY = "CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY"
    RETRY_RETURN_WRITER_ONLY = "RETRY_RETURN_WRITER_ONLY"
    DONE = "DONE"
    HOLD_AMBIGUOUS_NO_REPLAY = "HOLD_AMBIGUOUS_NO_REPLAY"
    HOLD_INVALID_SINK_EVIDENCE = "HOLD_INVALID_SINK_EVIDENCE"
    HOLD_CURRENTNESS_MOVED = "HOLD_CURRENTNESS_MOVED"
    HOLD_IDEMPOTENCY_CONFLICT = "HOLD_IDEMPOTENCY_CONFLICT"
    HOLD_UNSUPPORTED_STATE = "HOLD_UNSUPPORTED_STATE"


@dataclass(frozen=True)
class OperationIdentity:
    command_id: str
    operation_id: str
    idempotency_key: str
    payload_digest: str
    source_file_id: str
    source_revision: str
    source_digest: str
    authorization_root: str
    proof_semantics_root: str
    fence_root: str

    def __post_init__(self):
        for name in ("command_id", "operation_id", "idempotency_key", "source_file_id", "source_revision"):
            _id(getattr(self, name), name)
        for name in ("payload_digest", "source_digest", "authorization_root", "proof_semantics_root", "fence_root"):
            _root(getattr(self, name), name)

    @property
    def root(self) -> str:
        return digest({"schema": SCHEMA, "kind": "operation_identity", **self.__dict__})


@dataclass(frozen=True)
class CurrentOwnerContext:
    operation: OperationIdentity
    authorization_root: str
    proof_semantics_root: str
    fence_root: str

    def __post_init__(self):
        for name in ("authorization_root", "proof_semantics_root", "fence_root"):
            _root(getattr(self, name), name)


@dataclass(frozen=True)
class SinkEvidence:
    operation_id: str
    disposition: SinkDisposition
    sink_result_digest: str
    issuer_root: str
    verifier_root: str
    observed_at: int
    expires_at: int
    mac: str

    def __post_init__(self):
        _id(self.operation_id, "operation_id")
        for name in ("sink_result_digest", "issuer_root", "verifier_root"):
            _root(getattr(self, name), name)
        _nn(self.observed_at, "observed_at")
        _nn(self.expires_at, "expires_at")
        if self.expires_at < self.observed_at:
            raise ValueError("expires_at before observed_at")
        _root(self.mac, "mac")

    def unsigned_payload(self) -> dict:
        return {
            "schema": SCHEMA,
            "kind": "sink_evidence",
            "operation_id": self.operation_id,
            "disposition": self.disposition.value,
            "sink_result_digest": self.sink_result_digest,
            "issuer_root": self.issuer_root,
            "verifier_root": self.verifier_root,
            "observed_at": self.observed_at,
            "expires_at": self.expires_at,
        }


def sign_sink_evidence(*, secret: bytes, operation_id: str, disposition: SinkDisposition,
                       sink_result_digest: str, issuer_root: str, verifier_root: str,
                       observed_at: int, expires_at: int) -> SinkEvidence:
    payload = {
        "schema": SCHEMA,
        "kind": "sink_evidence",
        "operation_id": operation_id,
        "disposition": disposition.value,
        "sink_result_digest": sink_result_digest,
        "issuer_root": issuer_root,
        "verifier_root": verifier_root,
        "observed_at": observed_at,
        "expires_at": expires_at,
    }
    mac = hmac.new(secret, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(), sha256).hexdigest()
    return SinkEvidence(mac=mac, operation_id=operation_id, disposition=disposition,
                        sink_result_digest=sink_result_digest, issuer_root=issuer_root,
                        verifier_root=verifier_root, observed_at=observed_at, expires_at=expires_at)


@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    reason: str
    operation_root: str
    sink_evidence_root: str | None = None
    authority: str = D0
    authority_minted: bool = False
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self):
        _root(self.operation_root, "operation_root")
        if self.sink_evidence_root is not None:
            _root(self.sink_evidence_root, "sink_evidence_root")
        if self.authority_minted or self.effect_authority or self.gate10:
            raise ValueError("D0 recovery cannot mint authority")


def _owner_current(op: OperationIdentity, current: CurrentOwnerContext) -> tuple[bool, str]:
    if current.operation.command_id != op.command_id or current.operation.operation_id != op.operation_id:
        return False, "OPERATION_IDENTITY_MOVED"
    if current.operation.idempotency_key != op.idempotency_key or current.operation.payload_digest != op.payload_digest:
        return False, "IDEMPOTENCY_OR_PAYLOAD_MOVED"
    if (current.operation.source_file_id, current.operation.source_revision, current.operation.source_digest) != (op.source_file_id, op.source_revision, op.source_digest):
        return False, "SOURCE_CURRENTNESS_MOVED"
    if current.authorization_root != op.authorization_root or current.operation.authorization_root != op.authorization_root:
        return False, "AUTHORIZATION_MOVED"
    if current.proof_semantics_root != op.proof_semantics_root or current.operation.proof_semantics_root != op.proof_semantics_root:
        return False, "PROOF_SEMANTICS_MOVED"
    if current.fence_root != op.fence_root or current.operation.fence_root != op.fence_root:
        return False, "FENCE_MOVED"
    return True, "CURRENT"


def _verify_sink(evidence: SinkEvidence, *, secret: bytes, expected_operation_id: str,
                 expected_issuer_root: str, expected_verifier_root: str, now: int) -> tuple[bool, str, str]:
    _nn(now, "now")
    root = digest(evidence.unsigned_payload())
    if evidence.operation_id != expected_operation_id:
        return False, "SINK_OPERATION_MISMATCH", root
    if evidence.issuer_root != expected_issuer_root or evidence.verifier_root != expected_verifier_root:
        return False, "SINK_TRUST_ROOT_MISMATCH", root
    if now > evidence.expires_at:
        return False, "SINK_EVIDENCE_EXPIRED", root
    expected = hmac.new(secret, json.dumps(evidence.unsigned_payload(), sort_keys=True, separators=(",", ":")).encode(), sha256).hexdigest()
    if not hmac.compare_digest(expected, evidence.mac):
        return False, "SINK_EVIDENCE_MAC_INVALID", root
    return True, "SINK_EVIDENCE_VERIFIED", root


def decide_recovery(*, state: NativeState, operation: OperationIdentity,
                    current: CurrentOwnerContext, capability: RecoveryCapability,
                    sink_evidence: SinkEvidence | None, secret: bytes,
                    expected_issuer_root: str, expected_verifier_root: str, now: int) -> RecoveryDecision:
    """Project006-native recovery with sink evidence as observation, never authority.

    Outcome terminality is monotone: once a result/error/return exists, later pre-effect
    currentness drift cannot authorize provider replay or erase the owed return.
    """
    op_root = operation.root
    if state is NativeState.RETURN_WRITTEN:
        return RecoveryDecision(RecoveryAction.DONE, "RETURN_ALREADY_DURABLE", op_root)
    if state in (NativeState.RESULT_OBSERVED, NativeState.ERROR_TERMINAL):
        return RecoveryDecision(RecoveryAction.RETRY_RETURN_WRITER_ONLY, "TERMINAL_OUTCOME_ALREADY_OBSERVED", op_root)

    current_ok, current_reason = _owner_current(operation, current)

    if state is NativeState.ACK_WRITTEN_PRE_EFFECT:
        if not current_ok:
            return RecoveryDecision(RecoveryAction.HOLD_CURRENTNESS_MOVED, current_reason, op_root)
        return RecoveryDecision(RecoveryAction.START_PROVIDER_ONCE, "CURRENT_ACK_ALLOWS_FIRST_PROVIDER_ATTEMPT", op_root)

    if state is not NativeState.COMPLETION_AMBIGUOUS:
        return RecoveryDecision(RecoveryAction.HOLD_UNSUPPORTED_STATE, "UNSUPPORTED_NATIVE_RECOVERY_STATE", op_root)

    evidence_root = None
    if sink_evidence is not None:
        ok, evidence_reason, evidence_root = _verify_sink(
            sink_evidence, secret=secret, expected_operation_id=operation.operation_id,
            expected_issuer_root=expected_issuer_root, expected_verifier_root=expected_verifier_root, now=now)
        if not ok:
            return RecoveryDecision(RecoveryAction.HOLD_INVALID_SINK_EVIDENCE, evidence_reason, op_root, evidence_root)
        if sink_evidence.disposition is SinkDisposition.ACCEPTED:
            return RecoveryDecision(RecoveryAction.CONSUME_SINK_RESULT_NO_PROVIDER_REPLAY,
                                    "SINK_ACCEPTED_SAME_OPERATION", op_root, evidence_root)
        if sink_evidence.disposition is SinkDisposition.NOT_ACCEPTED:
            if not current_ok:
                return RecoveryDecision(RecoveryAction.HOLD_CURRENTNESS_MOVED, current_reason, op_root, evidence_root)
            if capability is RecoveryCapability.IDEMPOTENT_RETRY:
                return RecoveryDecision(RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID,
                                        "SINK_NOT_ACCEPTED_AND_CURRENT_IDEMPOTENT_CONTRACT", op_root, evidence_root)
            return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,
                                    "SINK_NOT_ACCEPTED_WITHOUT_IDEMPOTENT_RETRY_CONTRACT", op_root, evidence_root)
        # Verified UNKNOWN is still observational uncertainty; continue through capability split.

    if not current_ok:
        return RecoveryDecision(RecoveryAction.HOLD_CURRENTNESS_MOVED, current_reason, op_root, evidence_root)
    if capability is RecoveryCapability.IDEMPOTENT_RETRY:
        return RecoveryDecision(RecoveryAction.RETRY_PROVIDER_SAME_OPERATION_ID,
                                "AMBIGUOUS_BUT_EXACT_IDEMPOTENT_RETRY", op_root, evidence_root)
    if capability is RecoveryCapability.QUERY_RECONCILE:
        return RecoveryDecision(RecoveryAction.QUERY_RECONCILE,
                                "AMBIGUOUS_REQUIRES_PROVIDER_RECONCILIATION", op_root, evidence_root)
    return RecoveryDecision(RecoveryAction.HOLD_AMBIGUOUS_NO_REPLAY,
                            "AMBIGUOUS_NONRETRYABLE_EFFECT", op_root, evidence_root)
