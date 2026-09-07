from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-EFFECT-RETURN-ATOMICITY-CAPSULE-v1"
D0 = "D0_NONPROMOTING"


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _root(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or value.lower() != value or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def _id(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} required")
    return value


def _nn(value: int, field: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field} must be nonnegative exact int")
    return value


class RecoveryMode(str, Enum):
    IDEMPOTENT_RETRY = "IDEMPOTENT_RETRY"
    QUERY_RECONCILE = "QUERY_RECONCILE"
    NON_RETRYABLE = "NON_RETRYABLE"


class Phase(str, Enum):
    DECIDED_NEGATIVE = "DECIDED_NEGATIVE"
    DECIDED_ADMITTED = "DECIDED_ADMITTED"
    ACK_WRITTEN_PRE_EFFECT = "ACK_WRITTEN_PRE_EFFECT"
    EFFECT_ATTEMPT_DURABLE = "EFFECT_ATTEMPT_DURABLE"
    COMPLETION_AMBIGUOUS = "COMPLETION_AMBIGUOUS"
    RESULT_OBSERVED = "RESULT_OBSERVED"
    ERROR_TERMINAL = "ERROR_TERMINAL"
    RETURN_WRITTEN = "RETURN_WRITTEN"


class Action(str, Enum):
    WRITE_TERMINAL_RETURN = "WRITE_TERMINAL_RETURN"
    WRITE_ACK_PRE_EFFECT = "WRITE_ACK_PRE_EFFECT"
    CALL_PROVIDER_FIRST_TIME = "CALL_PROVIDER_FIRST_TIME"
    RETRY_EXACT_SAME_EFFECT = "RETRY_EXACT_SAME_EFFECT"
    QUERY_PROVIDER_STATUS = "QUERY_PROVIDER_STATUS"
    RETRY_RETURN_WRITER_ONLY = "RETRY_RETURN_WRITER_ONLY"
    HOLD_COMPLETION_AMBIGUOUS = "HOLD_COMPLETION_AMBIGUOUS"
    HOLD_REBIND_REQUIRED = "HOLD_REBIND_REQUIRED"
    HOLD_IDEMPOTENCY_CONFLICT = "HOLD_IDEMPOTENCY_CONFLICT"
    NOOP_TERMINAL = "NOOP_TERMINAL"


@dataclass(frozen=True)
class EffectContract:
    recovery_mode: RecoveryMode
    capability_receipt_root: str
    effect_type: str

    def __post_init__(self):
        if not isinstance(self.recovery_mode, RecoveryMode):
            raise ValueError("recovery_mode must be RecoveryMode")
        _root(self.capability_receipt_root, "capability_receipt_root")
        _id(self.effect_type, "effect_type")

    @property
    def contract_root(self) -> str:
        return digest({"schema": SCHEMA, "kind": "effect_contract", "recovery_mode": self.recovery_mode.value,
                       "capability_receipt_root": self.capability_receipt_root, "effect_type": self.effect_type})


@dataclass(frozen=True)
class EffectIntent:
    command_id: str
    idempotency_key: str
    source_root: str
    tecc_authorization_root: str
    effect_payload_root: str
    effect_type: str

    def __post_init__(self):
        _id(self.command_id, "command_id")
        _id(self.idempotency_key, "idempotency_key")
        for name in ("source_root", "tecc_authorization_root", "effect_payload_root"):
            _root(getattr(self, name), name)
        _id(self.effect_type, "effect_type")

    @property
    def identity_root(self) -> str:
        return digest({"schema": SCHEMA, "kind": "effect_intent", "command_id": self.command_id,
                       "idempotency_key": self.idempotency_key, "source_root": self.source_root,
                       "tecc_authorization_root": self.tecc_authorization_root,
                       "effect_payload_root": self.effect_payload_root, "effect_type": self.effect_type})


@dataclass(frozen=True)
class DurableEffectState:
    phase: Phase
    intent_root: str
    idempotency_key: str
    effect_payload_root: str
    contract_root: str
    provider_request_count: int = 0
    ack_receipt_root: str | None = None
    effect_attempt_root: str | None = None
    provider_operation_root: str | None = None
    result_root: str | None = None
    return_receipt_root: str | None = None
    terminal_class: str | None = None
    authority: str = D0
    effect_authority_minted: bool = False
    gate10: bool = False

    def __post_init__(self):
        if not isinstance(self.phase, Phase): raise ValueError("phase must be Phase")
        _root(self.intent_root, "intent_root")
        _id(self.idempotency_key, "idempotency_key")
        _root(self.effect_payload_root, "effect_payload_root")
        _root(self.contract_root, "contract_root")
        _nn(self.provider_request_count, "provider_request_count")
        for name in ("ack_receipt_root", "effect_attempt_root", "provider_operation_root", "result_root", "return_receipt_root"):
            value = getattr(self, name)
            if value is not None: _root(value, name)
        if self.effect_authority_minted or self.gate10:
            raise ValueError("D0 ERAC cannot mint effect/Gate10 authority")


@dataclass(frozen=True)
class RecoveryContext:
    current_intent_root: str
    current_contract_root: str
    current_capability_receipt_root: str
    observed_idempotency_key: str
    observed_effect_payload_root: str
    source_current: bool
    authorization_current: bool
    provider_operation_observed: bool = False

    def __post_init__(self):
        for name in ("current_intent_root", "current_contract_root", "current_capability_receipt_root", "observed_effect_payload_root"):
            _root(getattr(self, name), name)
        _id(self.observed_idempotency_key, "observed_idempotency_key")
        for name in ("source_current", "authorization_current", "provider_operation_observed"):
            if type(getattr(self, name)) is not bool: raise ValueError(f"{name} must be bool")


@dataclass(frozen=True)
class RecoveryDecision:
    action: Action
    reason: str
    intent_root: str
    provider_request_delta: int = 0
    authority: str = D0
    effect_authority_minted: bool = False
    gate10: bool = False

    def __post_init__(self):
        if not isinstance(self.action, Action): raise ValueError("action must be Action")
        _root(self.intent_root, "intent_root")
        _nn(self.provider_request_delta, "provider_request_delta")
        if self.effect_authority_minted or self.gate10:
            raise ValueError("D0 ERAC decision cannot mint authority")


def compile_initial_state(intent: EffectIntent, contract: EffectContract, *, admitted: bool, terminal_class: str | None = None) -> DurableEffectState:
    if intent.effect_type != contract.effect_type:
        raise ValueError("effect type/contract mismatch")
    if type(admitted) is not bool:
        raise ValueError("admitted must be bool")
    if admitted:
        phase = Phase.DECIDED_ADMITTED
        terminal_class = None
    else:
        phase = Phase.DECIDED_NEGATIVE
        terminal_class = terminal_class or "ADMISSION_BLOCKED"
    return DurableEffectState(phase, intent.identity_root, intent.idempotency_key, intent.effect_payload_root,
                              contract.contract_root, terminal_class=terminal_class)


def effect_attempt_root(intent: EffectIntent, contract: EffectContract, attempt_seq: int) -> str:
    _nn(attempt_seq, "attempt_seq")
    return digest({"schema": SCHEMA, "kind": "durable_effect_attempt", "intent_root": intent.identity_root,
                   "contract_root": contract.contract_root, "idempotency_key": intent.idempotency_key,
                   "effect_payload_root": intent.effect_payload_root, "attempt_seq": attempt_seq})


def decide_recovery(state: DurableEffectState, intent: EffectIntent, contract: EffectContract,
                    context: RecoveryContext) -> RecoveryDecision:
    if state.intent_root != intent.identity_root or context.current_intent_root != intent.identity_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "INTENT_IDENTITY_MOVED", intent.identity_root)
    if state.contract_root != contract.contract_root or context.current_contract_root != contract.contract_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "EFFECT_CONTRACT_MOVED", intent.identity_root)
    if context.current_capability_receipt_root != contract.capability_receipt_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "CAPABILITY_RECEIPT_MOVED", intent.identity_root)
    if not context.source_current or not context.authorization_current:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "SOURCE_OR_AUTHORIZATION_STALE", intent.identity_root)
    if context.observed_idempotency_key != intent.idempotency_key:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "IDEMPOTENCY_KEY_MOVED", intent.identity_root)
    if context.observed_effect_payload_root != intent.effect_payload_root or state.effect_payload_root != intent.effect_payload_root:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "SAME_KEY_OR_STATE_WITH_DIFFERENT_PAYLOAD", intent.identity_root)
    if state.idempotency_key != intent.idempotency_key:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "STATE_IDEMPOTENCY_KEY_MOVED", intent.identity_root)
    if state.phase is Phase.DECIDED_NEGATIVE:
        return RecoveryDecision(Action.WRITE_TERMINAL_RETURN, "NEGATIVE_DECISION_IS_STILL_A_RETURN", intent.identity_root)
    if state.phase is Phase.DECIDED_ADMITTED:
        return RecoveryDecision(Action.WRITE_ACK_PRE_EFFECT, "ACK_MUST_BE_DURABLE_BEFORE_PROVIDER_EFFECT", intent.identity_root)
    if state.phase is Phase.ACK_WRITTEN_PRE_EFFECT:
        return RecoveryDecision(Action.CALL_PROVIDER_FIRST_TIME, "NO_PRIOR_EFFECT_ATTEMPT_EXISTS", intent.identity_root, 1)
    if state.phase in (Phase.EFFECT_ATTEMPT_DURABLE, Phase.COMPLETION_AMBIGUOUS):
        if contract.recovery_mode is RecoveryMode.IDEMPOTENT_RETRY:
            return RecoveryDecision(Action.RETRY_EXACT_SAME_EFFECT, "SAME_KEY_SAME_PAYLOAD_RETRY_IS_PROVIDER_DEDUPED", intent.identity_root, 1)
        if contract.recovery_mode is RecoveryMode.QUERY_RECONCILE:
            return RecoveryDecision(Action.QUERY_PROVIDER_STATUS, "RECONCILE_EXTERNAL_OPERATION_BEFORE_ANY_RESEND", intent.identity_root)
        return RecoveryDecision(Action.HOLD_COMPLETION_AMBIGUOUS, "NON_IDEMPOTENT_NONQUERYABLE_EFFECT_MAY_HAVE_ESCAPED", intent.identity_root)
    if state.phase in (Phase.RESULT_OBSERVED, Phase.ERROR_TERMINAL):
        return RecoveryDecision(Action.RETRY_RETURN_WRITER_ONLY, "TERMINAL_LOCAL_RESULT_EXISTS_DO_NOT_REEXECUTE_PROVIDER", intent.identity_root)
    if state.phase is Phase.RETURN_WRITTEN:
        return RecoveryDecision(Action.NOOP_TERMINAL, "COMMAND_ALREADY_HAS_DURABLE_BOUND_RETURN", intent.identity_root)
    raise AssertionError("unhandled phase")


def hard13d_erac(axes) -> str:
    if len(axes) != 13 or any(type(x) is not int or x not in (0,1,2) for x in axes):
        return "HOLD_MALFORMED"
    hard = axes[:8]
    if 0 in hard: return "HOLD_HARD_INVALID"
    if 1 in hard: return "HOLD_UNRESOLVED"
    return "READY_RECOVERY_ACTION_D0"
