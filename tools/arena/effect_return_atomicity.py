from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
import json

SCHEMA = "AURA-EFFECT-RETURN-ATOMICITY-CAPSULE-v2"
D0 = "D0_NONPROMOTING"
EXPECTED_REPROOF_SEMANTICS = "HARD_COMPONENT_SEEDED_DIRECTED_REPROOF-v1"


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
    ACK_WRITE_INFLIGHT = "ACK_WRITE_INFLIGHT"
    ACK_WRITE_AMBIGUOUS = "ACK_WRITE_AMBIGUOUS"
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
    HOLD_ACK_RECONCILIATION = "HOLD_ACK_RECONCILIATION"
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
class ProviderActionCurrentness:
    """Owner-resolved, at-use currentness consumed by the provider-action boundary.

    Construction is not authentication. The EffectAttemptJournal obtains this
    object from its configured currentness resolver at use time. D0 code never
    treats the object itself as effect authority.
    """

    source_root: str
    authorization_root: str
    consumer_admission_root: str
    proof_semantics_id: str
    consumer_generation: int
    source_owner_id: str
    authorization_owner_id: str
    observer_id: str
    effect_authority: bool = False
    gate10: bool = False

    def __post_init__(self):
        for name in ("source_root", "authorization_root", "consumer_admission_root"):
            _root(getattr(self, name), name)
        _id(self.proof_semantics_id, "proof_semantics_id")
        _nn(self.consumer_generation, "consumer_generation")
        for name in ("source_owner_id", "authorization_owner_id", "observer_id"):
            _id(getattr(self, name), name)
        if self.observer_id in {self.source_owner_id, self.authorization_owner_id}:
            raise ValueError("CURRENTNESS_OBSERVER_NOT_INDEPENDENT")
        if self.effect_authority or self.gate10:
            raise ValueError("currentness evidence cannot mint authority")

    @property
    def identity_root(self) -> str:
        return digest({
            "schema": SCHEMA,
            "kind": "provider_action_currentness",
            "source_root": self.source_root,
            "authorization_root": self.authorization_root,
            "consumer_admission_root": self.consumer_admission_root,
            "proof_semantics_id": self.proof_semantics_id,
            "consumer_generation": self.consumer_generation,
            "source_owner_id": self.source_owner_id,
            "authorization_owner_id": self.authorization_owner_id,
            "observer_id": self.observer_id,
            "effect_authority": False,
            "gate10": False,
        })


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
        if not isinstance(self.phase, Phase):
            raise ValueError("phase must be Phase")
        _root(self.intent_root, "intent_root")
        _id(self.idempotency_key, "idempotency_key")
        _root(self.effect_payload_root, "effect_payload_root")
        _root(self.contract_root, "contract_root")
        _nn(self.provider_request_count, "provider_request_count")
        for name in ("ack_receipt_root", "effect_attempt_root", "provider_operation_root", "result_root", "return_receipt_root"):
            value = getattr(self, name)
            if value is not None:
                _root(value, name)
        if self.effect_authority_minted or self.gate10:
            raise ValueError("D0 ERAC cannot mint effect/Gate10 authority")


@dataclass(frozen=True)
class RecoveryContext:
    current_intent_root: str
    current_contract_root: str
    current_capability_receipt_root: str
    observed_idempotency_key: str
    observed_effect_payload_root: str
    provider_operation_observed: bool = False

    def __post_init__(self):
        for name in ("current_intent_root", "current_contract_root", "current_capability_receipt_root", "observed_effect_payload_root"):
            _root(getattr(self, name), name)
        _id(self.observed_idempotency_key, "observed_idempotency_key")
        if type(self.provider_operation_observed) is not bool:
            raise ValueError("provider_operation_observed must be bool")


@dataclass(frozen=True)
class RecoveryDecision:
    action: Action
    reason: str
    intent_root: str
    provider_request_delta: int = 0
    currentness_root: str | None = None
    authority: str = D0
    effect_authority_minted: bool = False
    gate10: bool = False

    def __post_init__(self):
        if not isinstance(self.action, Action):
            raise ValueError("action must be Action")
        _root(self.intent_root, "intent_root")
        _nn(self.provider_request_delta, "provider_request_delta")
        if self.currentness_root is not None:
            _root(self.currentness_root, "currentness_root")
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


def effect_attempt_root(intent: EffectIntent, contract: EffectContract, attempt_seq: int,
                        currentness_root: str | None = None) -> str:
    _nn(attempt_seq, "attempt_seq")
    payload = {"schema": SCHEMA, "kind": "durable_effect_attempt", "intent_root": intent.identity_root,
               "contract_root": contract.contract_root, "idempotency_key": intent.idempotency_key,
               "effect_payload_root": intent.effect_payload_root, "attempt_seq": attempt_seq}
    if currentness_root is not None:
        payload["provider_action_currentness_root"] = _root(currentness_root, "currentness_root")
    return digest(payload)


def _currentness_failure(intent: EffectIntent, currentness: ProviderActionCurrentness | None) -> str | None:
    if currentness is None:
        return "CURRENTNESS_OWNER_UNAVAILABLE"
    if currentness.source_root != intent.source_root:
        return "SOURCE_OWNER_CURRENTNESS_MOVED"
    if currentness.authorization_root != intent.tecc_authorization_root:
        return "TECC_AUTHORIZATION_CURRENTNESS_MOVED"
    if currentness.proof_semantics_id != EXPECTED_REPROOF_SEMANTICS:
        return "PROOF_SEMANTICS_NOT_CURRENT"
    return None


def decide_recovery(state: DurableEffectState, intent: EffectIntent, contract: EffectContract,
                    context: RecoveryContext, currentness: ProviderActionCurrentness | None) -> RecoveryDecision:
    # Once a terminal local outcome exists, the system owes its outbound return.
    # Later action currentness cannot retroactively erase an already-observed result.
    if state.phase in (Phase.RESULT_OBSERVED, Phase.ERROR_TERMINAL):
        return RecoveryDecision(Action.RETRY_RETURN_WRITER_ONLY,
                                "TERMINAL_LOCAL_RESULT_EXISTS_DO_NOT_REEXECUTE_PROVIDER", state.intent_root)
    if state.phase is Phase.RETURN_WRITTEN:
        return RecoveryDecision(Action.NOOP_TERMINAL,
                                "COMMAND_ALREADY_HAS_DURABLE_BOUND_RETURN", state.intent_root)

    if state.intent_root != intent.identity_root or context.current_intent_root != intent.identity_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "INTENT_IDENTITY_MOVED", intent.identity_root)
    if state.contract_root != contract.contract_root or context.current_contract_root != contract.contract_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "EFFECT_CONTRACT_MOVED", intent.identity_root)
    if context.current_capability_receipt_root != contract.capability_receipt_root:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, "CAPABILITY_RECEIPT_MOVED", intent.identity_root)
    currentness_failure = _currentness_failure(intent, currentness)
    if currentness_failure is not None:
        return RecoveryDecision(Action.HOLD_REBIND_REQUIRED, currentness_failure, intent.identity_root)
    assert currentness is not None
    currentness_root = currentness.identity_root
    if context.observed_idempotency_key != intent.idempotency_key:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "IDEMPOTENCY_KEY_MOVED", intent.identity_root,
                                currentness_root=currentness_root)
    if context.observed_effect_payload_root != intent.effect_payload_root or state.effect_payload_root != intent.effect_payload_root:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "SAME_KEY_OR_STATE_WITH_DIFFERENT_PAYLOAD", intent.identity_root,
                                currentness_root=currentness_root)
    if state.idempotency_key != intent.idempotency_key:
        return RecoveryDecision(Action.HOLD_IDEMPOTENCY_CONFLICT, "STATE_IDEMPOTENCY_KEY_MOVED", intent.identity_root,
                                currentness_root=currentness_root)
    if state.phase is Phase.DECIDED_NEGATIVE:
        return RecoveryDecision(Action.WRITE_TERMINAL_RETURN, "NEGATIVE_DECISION_IS_STILL_A_RETURN", intent.identity_root,
                                currentness_root=currentness_root)
    if state.phase is Phase.DECIDED_ADMITTED:
        return RecoveryDecision(Action.WRITE_ACK_PRE_EFFECT, "ACK_MUST_BE_DURABLE_BEFORE_PROVIDER_EFFECT", intent.identity_root,
                                currentness_root=currentness_root)
    if state.phase in (Phase.ACK_WRITE_INFLIGHT, Phase.ACK_WRITE_AMBIGUOUS):
        return RecoveryDecision(Action.HOLD_ACK_RECONCILIATION, "ACK_DELIVERY_OUTCOME_AMBIGUOUS", intent.identity_root,
                                currentness_root=currentness_root)
    if state.phase is Phase.ACK_WRITTEN_PRE_EFFECT:
        return RecoveryDecision(Action.CALL_PROVIDER_FIRST_TIME, "NO_PRIOR_EFFECT_ATTEMPT_EXISTS", intent.identity_root, 1,
                                currentness_root=currentness_root)
    if state.phase in (Phase.EFFECT_ATTEMPT_DURABLE, Phase.COMPLETION_AMBIGUOUS):
        if contract.recovery_mode is RecoveryMode.IDEMPOTENT_RETRY:
            return RecoveryDecision(Action.RETRY_EXACT_SAME_EFFECT, "SAME_KEY_SAME_PAYLOAD_RETRY_IS_PROVIDER_DEDUPED", intent.identity_root, 1,
                                    currentness_root=currentness_root)
        if contract.recovery_mode is RecoveryMode.QUERY_RECONCILE:
            return RecoveryDecision(Action.QUERY_PROVIDER_STATUS, "RECONCILE_EXTERNAL_OPERATION_BEFORE_ANY_RESEND", intent.identity_root,
                                    currentness_root=currentness_root)
        return RecoveryDecision(Action.HOLD_COMPLETION_AMBIGUOUS, "NON_IDEMPOTENT_NONQUERYABLE_EFFECT_MAY_HAVE_ESCAPED", intent.identity_root,
                                currentness_root=currentness_root)
    raise AssertionError("unhandled phase")


def hard13d_erac(axes) -> str:
    if len(axes) != 13 or any(type(x) is not int or x not in (0, 1, 2) for x in axes):
        return "HOLD_MALFORMED"
    hard = axes[:8]
    if 0 in hard:
        return "HOLD_HARD_INVALID"
    if 1 in hard:
        return "HOLD_UNRESOLVED"
    return "READY_RECOVERY_ACTION_D0"
