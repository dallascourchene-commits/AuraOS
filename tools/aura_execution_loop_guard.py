"""Cross-project loop-safety guard for AuraOS tool execution."""

from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable, Optional, Tuple

VERSION = "AURA_EXECUTION_LOOP_GUARD_V1"

@dataclass(frozen=True)
class RetrievalFingerprint:
    provider_tool: str
    resource_ref: str
    query_pattern: str
    page_range: str
    semantic_purpose: str

@dataclass(frozen=True)
class MutationIntent:
    action_class: str
    target_object: str
    allowed_fields: Tuple[str, ...]
    expected_state_delta: str
    repair_route: str

    @classmethod
    def build(cls, *, action_class: str, target_object: str,
              allowed_fields: Iterable[str] = (),
              expected_state_delta: str, repair_route: str) -> "MutationIntent":
        return cls(action_class, target_object, tuple(sorted(set(allowed_fields))),
                   expected_state_delta, repair_route)

@dataclass(frozen=True)
class GuardDecision:
    allowed: bool
    disposition: str
    reason: str

class ExecutionLoopGuard:
    def __init__(self, *, objective_id: str):
        if not objective_id:
            raise ValueError("objective_id is required")
        self.objective_id = objective_id
        self._last_read: Optional[RetrievalFingerprint] = None
        self._last_read_state_token: Optional[str] = None
        self._last_poll_key: Optional[str] = None
        self._last_poll_state_token: Optional[str] = None
        self._last_poll_terminal = False
        self._frozen_primitives: set[str] = set()
        self._blocked_write_keys: set[tuple[str, str]] = set()
        self._mutation_stop = False
        self._incident_count = 0

    def admit_read(self, fingerprint: RetrievalFingerprint, *,
                   observed_state_token: Optional[str]) -> GuardDecision:
        if self._last_read == fingerprint and self._last_read_state_token == observed_state_token:
            self._incident_count += 1
            return GuardDecision(False, "CHANGE_AXIS_OR_COLLAPSE",
                                 "same retrieval fingerprint observed without a provider state transition")
        self._last_read = fingerprint
        self._last_read_state_token = observed_state_token
        return GuardDecision(True, "READ_ADMITTED", "new retrieval axis or provider state")

    def admit_poll(self, *, poll_key: str, observed_state_token: Optional[str],
                   terminal: bool) -> GuardDecision:
        if (self._last_poll_key == poll_key and
            self._last_poll_state_token == observed_state_token and
            self._last_poll_terminal and terminal):
            self._incident_count += 1
            return GuardDecision(False, "CHANGE_AXIS_OR_COLLAPSE",
                                 "terminal provider state is unchanged; repeated poll would add no evidence")
        self._last_poll_key = poll_key
        self._last_poll_state_token = observed_state_token
        self._last_poll_terminal = terminal
        return GuardDecision(True, "POLL_ADMITTED", "poll has a new state or nonterminal purpose")

    def admit_write(self, intent: MutationIntent, *, selected_action_class: str,
                    selected_target_object: str,
                    selected_fields: Iterable[str] = ()) -> GuardDecision:
        if self._mutation_stop:
            return GuardDecision(False, "MUTATION_STOP",
                                 "writes are frozen after an unintended semantic mutation")
        primitive = selected_action_class
        if primitive in self._frozen_primitives:
            return GuardDecision(False, "STOP_PRIMITIVE",
                                 f"mutation primitive {primitive!r} is frozen for this objective")
        if selected_action_class != intent.action_class:
            self._frozen_primitives.add(selected_action_class)
            self._incident_count += 1
            return GuardDecision(False, "STOP_PRIMITIVE",
                                 "selected action class does not match the bound mutation intent")
        if selected_target_object != intent.target_object:
            self._frozen_primitives.add(selected_action_class)
            self._incident_count += 1
            return GuardDecision(False, "STOP_PRIMITIVE",
                                 "selected target object does not match the bound mutation intent")
        fields = set(selected_fields)
        allowed = set(intent.allowed_fields)
        if not fields.issubset(allowed):
            self._frozen_primitives.add(selected_action_class)
            self._incident_count += 1
            return GuardDecision(False, "STOP_PRIMITIVE",
                                 "selected mutation fields exceed the bound allowed-field set")
        key = (intent.action_class, intent.target_object)
        if key in self._blocked_write_keys:
            return GuardDecision(False, "NO_OP_HISTORY_DRIFT_BLOCKED",
                                 "prior no-op mutation already demonstrated no external state transition")
        return GuardDecision(True, "WRITE_ADMITTED",
                             "selected mutation exactly matches bound intent")

    def record_write_result(self, intent: MutationIntent, *,
                            before_content_identity: Optional[str],
                            after_content_identity: Optional[str],
                            expected_transition_observed: bool,
                            unintended_semantic_mutation: bool = False) -> GuardDecision:
        key = (intent.action_class, intent.target_object)
        if unintended_semantic_mutation:
            self._mutation_stop = True
            self._incident_count += 1
            return GuardDecision(False, "MUTATION_STOP",
                                 "unintended semantic mutation observed; freeze writes and repair via a different primitive")
        if (before_content_identity is not None and
            before_content_identity == after_content_identity and
            not expected_transition_observed):
            self._blocked_write_keys.add(key)
            self._incident_count += 1
            return GuardDecision(False, "NO_OP_HISTORY_DRIFT",
                                 "same content identity plus new history is not proof progress")
        if not expected_transition_observed:
            return GuardDecision(False, "EXPECTED_TRANSITION_NOT_OBSERVED",
                                 "mutation did not produce the bound state delta; change control surface or collapse the cone")
        return GuardDecision(True, "WRITE_CONFIRMED", "expected state transition observed")

    def snapshot(self) -> dict:
        return {
            "version": VERSION,
            "objective_id": self.objective_id,
            "last_read": asdict(self._last_read) if self._last_read else None,
            "last_read_state_token": self._last_read_state_token,
            "last_poll_key": self._last_poll_key,
            "last_poll_state_token": self._last_poll_state_token,
            "last_poll_terminal": self._last_poll_terminal,
            "frozen_primitives": sorted(self._frozen_primitives),
            "blocked_write_keys": [list(x) for x in sorted(self._blocked_write_keys)],
            "mutation_stop": self._mutation_stop,
            "incident_count": self._incident_count,
            "effect_authority": False,
            "semantic_authority": False,
            "provider_authority": False,
            "native_private_transformer_kv": False,
        }
