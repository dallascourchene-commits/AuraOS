"""Proposal-only bilateral intent refinement contracts for AuraOS.

The module compiles positive and negative requirements, guardrail proposals,
paired teach-back, confirmation receipts, and evidence-bound plan revisions.
It is not a memory, truth, policy, routing, verification, patch, publication,
production, or learning-promotion authority.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, fields, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from aura_event_contracts import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_json,
    stable_digest,
    stable_id,
)

VERSION = "AURA_INTENT_REFINEMENT_V1"
MEMORY_OWNER = TRUTH_OWNER = POLICY_OWNER = ROUTING_OWNER = False
VERIFICATION_OWNER = PATCH_AUTHORITY_GRANTED = PRODUCTION_MUTATION = False
HUMAN_CONFIRMATION_REQUIRED = True
CANONICAL_OUTPUTS = (
    "aura_unified_memory_continuity.IntentPacket",
    "aura_unified_memory_continuity.SemanticLedger",
)
MAX_ITEMS = 256
MAX_TEXT_BYTES = 16 * 1024
MAX_PACKET_BYTES = 512 * 1024


class RefinementStage(str, Enum):
    DRAFT = "DRAFT"
    ANALYZED = "ANALYZED"
    CLARIFICATION_REQUIRED = "CLARIFICATION_REQUIRED"
    TEACH_BACK_PENDING = "TEACH_BACK_PENDING"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    COMPILED = "COMPILED"
    STALE = "STALE"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class AmbiguityClass(str, Enum):
    TERM_MEANING = "TERM_MEANING"
    DESIRED_OUTCOME = "DESIRED_OUTCOME"
    PROHIBITED_OUTCOME = "PROHIBITED_OUTCOME"
    SCOPE = "SCOPE"
    AUTHORITY = "AUTHORITY"
    FAILURE_BEHAVIOR = "FAILURE_BEHAVIOR"
    FALLBACK_BEHAVIOR = "FALLBACK_BEHAVIOR"
    DATA_PRIVACY = "DATA_PRIVACY"
    EXTERNAL_EFFECT = "EXTERNAL_EFFECT"
    EVIDENCE_REQUIRED = "EVIDENCE_REQUIRED"
    CONTRADICTION = "CONTRADICTION"
    PRIORITY = "PRIORITY"
    REVERSIBILITY = "REVERSIBILITY"


class GuardrailSourceClass(str, Enum):
    ATLAS_PROHIBITION = "ATLAS_PROHIBITION"
    AUTHORITY_OWNER = "AUTHORITY_OWNER"
    AURA_AXIOM = "AURA_AXIOM"
    DOMAIN_CONTRACT = "DOMAIN_CONTRACT"
    REPOSITORY_EVIDENCE = "REPOSITORY_EVIDENCE"
    SYSTEM_BASELINE = "SYSTEM_BASELINE"
    AI_INFERRED = "AI_INFERRED"
    HUMAN_ADDED = "HUMAN_ADDED"


class GuardrailHardness(str, Enum):
    HARD_ARCHITECTURAL = "HARD_ARCHITECTURAL"
    HARD_AUTHORITY = "HARD_AUTHORITY"
    DOMAIN_REQUIRED = "DOMAIN_REQUIRED"
    PROPOSED_DEFAULT = "PROPOSED_DEFAULT"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"


class GuardrailEnforcementClass(str, Enum):
    STATIC_SOURCE = "STATIC_SOURCE"
    SCHEMA = "SCHEMA"
    AUTHORITY = "AUTHORITY"
    TEST = "TEST"
    RUNTIME = "RUNTIME"
    LIFECYCLE = "LIFECYCLE"
    PRIVACY = "PRIVACY"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class HumanGuardrailDisposition(str, Enum):
    CONFIRMED = "CONFIRMED"
    STRENGTHENED = "STRENGTHENED"
    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    REJECTED_SOFT = "REJECTED_SOFT"
    ACKNOWLEDGED_HARD = "ACKNOWLEDGED_HARD"
    DEFERRED = "DEFERRED"


class ConfirmationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class NegativeRequirementClass(str, Enum):
    PROHIBITION = "PROHIBITION"
    EXCLUSION_NON_GOAL = "EXCLUSION_NON_GOAL"
    PRESERVATION_INVARIANT = "PRESERVATION_INVARIANT"
    AUTHORITY_DENIAL = "AUTHORITY_DENIAL"
    FAILURE_BEHAVIOR = "FAILURE_BEHAVIOR"
    PRIVACY_RESTRICTION = "PRIVACY_RESTRICTION"
    RESOURCE_RESTRICTION = "RESOURCE_RESTRICTION"
    QUALITY_PROHIBITION = "QUALITY_PROHIBITION"
    SCOPE_BOUNDARY = "SCOPE_BOUNDARY"
    TEMPORAL_RESTRICTION = "TEMPORAL_RESTRICTION"
    SOFT_PREFERENCE = "SOFT_PREFERENCE"


class PlanRevisionClass(str, Enum):
    LOCAL_EVIDENCE_REFINEMENT = "LOCAL_EVIDENCE_REFINEMENT"
    BOUNDED_PLAN_RESTRUCTURING = "BOUNDED_PLAN_RESTRUCTURING"
    INTENT_AUTHORITY_SCOPE_CHANGE = "INTENT_AUTHORITY_SCOPE_CHANGE"


TRANSITIONS = {
    "DRAFT": {"ANALYZED", "REJECTED", "EXPIRED"},
    "ANALYZED": {"CLARIFICATION_REQUIRED", "TEACH_BACK_PENDING", "REJECTED", "EXPIRED"},
    "CLARIFICATION_REQUIRED": {"CLARIFICATION_REQUIRED", "TEACH_BACK_PENDING", "REJECTED", "EXPIRED"},
    "TEACH_BACK_PENDING": {"CLARIFICATION_REQUIRED", "HUMAN_CONFIRMED", "REJECTED", "EXPIRED"},
    "HUMAN_CONFIRMED": {"COMPILED", "STALE", "REJECTED"},
    "COMPILED": {"STALE"},
    "STALE": set(),
    "REJECTED": set(),
    "EXPIRED": set(),
}


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value.encode()) > MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    return value


def _optional(value: Any, name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    value = value.strip()
    if len(value.encode()) > MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {MAX_TEXT_BYTES} UTF-8 bytes")
    return value


def _enum(value: str | Enum, enum_type: type[Enum], name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    if raw not in {item.value for item in enum_type}:
        raise ValueError(f"unsupported {name}: {raw}")
    return raw


def _strings(values: Sequence[Any], name: str, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > MAX_ITEMS:
        raise ValueError(f"{name} exceeds {MAX_ITEMS} items")
    result = tuple(_required(value, name) for value in values)
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{name} must not contain duplicates")
    return result


def _paths(values: Sequence[Any], name: str) -> tuple[str, ...]:
    result = _strings(values, name)
    for value in result:
        if value.startswith("/") or "\\" in value or ".." in value.split("/") or value in {".", ".."}:
            raise ValueError(f"{name} must contain bounded repository-relative POSIX paths")
    return result


def _timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite timestamp")
    value = float(value)
    if value != value or value in {float("inf"), float("-inf")}:
        raise ValueError(f"{name} must be a finite timestamp")
    return value


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value


def _validate_json_keys(value: Any, name: str, path: str = "$") -> None:
    if isinstance(value, Mapping):
        seen: set[str] = set()
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{name} must use string keys at {path}")
            if key in seen:
                raise ValueError(f"{name} contains a duplicate key at {path}.{key}")
            seen.add(key)
            _validate_json_keys(item, name, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_keys(item, name, f"{path}[{index}]")


def _freeze_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    return value


def _packet(payload: Any, name: str) -> None:
    encoded = canonical_json(payload).encode("utf-8")
    if len(encoded) > MAX_PACKET_BYTES:
        raise ValueError(f"{name} exceeds {MAX_PACKET_BYTES} canonical bytes")


def _record(value: Any, name: str) -> Mapping[str, Any]:
    payload = value.to_dict() if hasattr(value, "to_dict") else dict(value) if isinstance(value, Mapping) else None
    if payload is None:
        raise ValueError(f"{name} must be a mapping or to_dict record")
    _validate_json_keys(payload, name)
    normalized = json.loads(canonical_json(payload))
    if not isinstance(normalized, dict):
        raise ValueError(f"{name} must normalize to an object")
    _packet(normalized, name)
    return _freeze_json(normalized)


def _records(values: Sequence[Any], name: str) -> tuple[Mapping[str, Any], ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > MAX_ITEMS:
        raise ValueError(f"{name} exceeds {MAX_ITEMS} items")
    return tuple(_record(value, f"{name}[{index}]") for index, value in enumerate(values))


def _dataclass_dict(value: Any) -> dict[str, Any]:
    payload = {field.name: _thaw_json(getattr(value, field.name)) for field in fields(value)}
    _packet(payload, type(value).__name__)
    return payload


@dataclass(frozen=True)
class NegativeRequirement:
    requirement_id: str
    statement: str
    classification: str
    source_span: str
    source_start: int
    source_end: int
    operator: str
    target: str
    scope: str
    ambiguous: bool = False
    version: str = VERSION

    @classmethod
    def create(cls, *, statement: str, classification: str | NegativeRequirementClass,
               source_span: str, source_start: int, source_end: int, operator: str,
               target: str, scope: str = "", ambiguous: bool = False) -> "NegativeRequirement":
        statement, span = _required(statement, "statement"), _required(source_span, "source_span")
        if not isinstance(source_start, int) or not isinstance(source_end, int):
            raise ValueError("source offsets must be integers")
        if source_start < 0 or source_end <= source_start or source_end - source_start != len(span):
            raise ValueError("source offsets must exactly bind source_span")
        payload = {
            "statement": statement,
            "classification": _enum(classification, NegativeRequirementClass, "classification"),
            "source_span": span,
            "source_start": source_start,
            "source_end": source_end,
            "operator": _required(operator, "operator").lower(),
            "target": _optional(target, "target"),
            "scope": _optional(scope, "scope"),
            "ambiguous": _strict_bool(ambiguous, "ambiguous"),
        }
        return cls(stable_id("neg", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        return _dataclass_dict(self)


@dataclass(frozen=True)
class ClarificationQuestion:
    question_id: str
    ambiguity_class: str
    question: str
    why_it_changes_execution: str
    candidate_answers: tuple[str, ...] = ()
    affected_requirements: tuple[str, ...] = ()
    affected_guardrails: tuple[str, ...] = ()
    required_human_answer: bool = True
    version: str = VERSION

    @classmethod
    def create(cls, *, ambiguity_class: str | AmbiguityClass, question: str,
               why_it_changes_execution: str, candidate_answers: Sequence[str] = (),
               affected_requirements: Sequence[str] = (), affected_guardrails: Sequence[str] = (),
               required_human_answer: bool = True) -> "ClarificationQuestion":
        payload = {
            "ambiguity_class": _enum(ambiguity_class, AmbiguityClass, "ambiguity_class"),
            "question": _required(question, "question"),
            "why_it_changes_execution": _required(why_it_changes_execution, "why_it_changes_execution"),
            "candidate_answers": _strings(candidate_answers, "candidate_answers"),
            "affected_requirements": _strings(affected_requirements, "affected_requirements"),
            "affected_guardrails": _strings(affected_guardrails, "affected_guardrails"),
            "required_human_answer": _strict_bool(required_human_answer, "required_human_answer"),
        }
        return cls(stable_id("clarify", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        for key in ("candidate_answers", "affected_requirements", "affected_guardrails"):
            payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True)
class GuardrailProposal:
    guardrail_id: str
    statement: str
    source_class: str
    source_refs: tuple[str, ...]
    hardness: str
    enforcement_class: str
    affected_arenas: tuple[str, ...]
    affected_files: tuple[str, ...]
    affected_symbols: tuple[str, ...]
    rationale: str
    human_disposition: str
    human_note: str = ""
    version: str = VERSION

    @classmethod
    def create(cls, *, statement: str, source_class: str | GuardrailSourceClass,
               source_refs: Sequence[str], hardness: str | GuardrailHardness,
               enforcement_class: str | GuardrailEnforcementClass,
               affected_arenas: Sequence[str] = (), affected_files: Sequence[str] = (),
               affected_symbols: Sequence[str] = (), rationale: str,
               human_disposition: str | HumanGuardrailDisposition = HumanGuardrailDisposition.DEFERRED,
               human_note: str = "") -> "GuardrailProposal":
        hardness_value = _enum(hardness, GuardrailHardness, "hardness")
        disposition = _enum(human_disposition, HumanGuardrailDisposition, "human_disposition")
        if hardness_value in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY"} and disposition not in {"ACKNOWLEDGED_HARD", "DEFERRED"}:
            raise ValueError("hard architectural or authority guardrails are acknowledgement-only")
        if hardness_value == "DOMAIN_REQUIRED" and disposition in {"REJECTED_SOFT", "MODIFIED"}:
            raise ValueError("domain-required guardrails need separate authority to change")
        payload = {
            "statement": _required(statement, "statement"),
            "source_class": _enum(source_class, GuardrailSourceClass, "source_class"),
            "source_refs": _strings(source_refs, "source_refs", True),
            "hardness": hardness_value,
            "enforcement_class": _enum(enforcement_class, GuardrailEnforcementClass, "enforcement_class"),
            "affected_arenas": _strings(affected_arenas, "affected_arenas"),
            "affected_files": _paths(affected_files, "affected_files"),
            "affected_symbols": _strings(affected_symbols, "affected_symbols"),
            "rationale": _required(rationale, "rationale"),
            "human_disposition": disposition,
            "human_note": _optional(human_note, "human_note"),
        }
        return cls(stable_id("guardrail", payload), **payload)

    @property
    def is_hard(self) -> bool:
        return self.hardness in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY", "DOMAIN_REQUIRED"}

    def with_human_disposition(self, disposition: str | HumanGuardrailDisposition,
                               note: str = "") -> "GuardrailProposal":
        disposition = _enum(disposition, HumanGuardrailDisposition, "human_disposition")
        if self.hardness in {"HARD_ARCHITECTURAL", "HARD_AUTHORITY"} and disposition not in {"ACKNOWLEDGED_HARD", "DEFERRED"}:
            raise ValueError("hard architectural or authority guardrails are acknowledgement-only")
        if self.hardness == "DOMAIN_REQUIRED" and disposition in {"REJECTED_SOFT", "MODIFIED"}:
            raise ValueError("domain-required guardrails need separate authority to change")
        return replace(self, human_disposition=disposition, human_note=_optional(note, "human_note"))

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        for key in ("source_refs", "affected_arenas", "affected_files", "affected_symbols"):
            payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True)
class PairedTeachBack:
    will_do: tuple[str, ...]
    will_not_do: tuple[str, ...]
    will_preserve: tuple[str, ...]
    will_stop_or_escalate_if: tuple[str, ...]
    positive_examples: tuple[str, ...]
    negative_examples: tuple[str, ...]
    unresolved_assumptions: tuple[str, ...]
    required_human_decisions: tuple[str, ...]
    teach_back_digest: str
    version: str = VERSION

    @classmethod
    def create(cls, *, will_do: Sequence[str], will_not_do: Sequence[str],
               will_preserve: Sequence[str] = (), will_stop_or_escalate_if: Sequence[str] = (),
               positive_examples: Sequence[str] = (), negative_examples: Sequence[str] = (),
               unresolved_assumptions: Sequence[str] = (),
               required_human_decisions: Sequence[str] = ()) -> "PairedTeachBack":
        payload = {
            "will_do": _strings(will_do, "will_do", True),
            "will_not_do": _strings(will_not_do, "will_not_do", True),
            "will_preserve": _strings(will_preserve, "will_preserve"),
            "will_stop_or_escalate_if": _strings(will_stop_or_escalate_if, "will_stop_or_escalate_if"),
            "positive_examples": _strings(positive_examples, "positive_examples"),
            "negative_examples": _strings(negative_examples, "negative_examples"),
            "unresolved_assumptions": _strings(unresolved_assumptions, "unresolved_assumptions"),
            "required_human_decisions": _strings(required_human_decisions, "required_human_decisions"),
        }
        return cls(**payload, teach_back_digest=stable_digest(payload))

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        for key in payload:
            if isinstance(payload[key], tuple):
                payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True)
class IntentRefinementSession:
    session_id: str
    repository_head: str
    working_tree_digest: str
    arena: str
    source_request: str
    source_request_digest: str
    current_stage: str
    candidate_positive_requirements: tuple[str, ...]
    candidate_negative_requirements: tuple[str, ...]
    candidate_definitions: tuple[Mapping[str, Any], ...]
    candidate_guardrails: tuple[Mapping[str, Any], ...]
    unresolved_ambiguities: tuple[Mapping[str, Any], ...]
    questions_asked: tuple[Mapping[str, Any], ...]
    answers_received: tuple[Mapping[str, Any], ...]
    teach_back: Mapping[str, Any]
    confirmation_status: str
    confirmation_receipt_id: str
    created_at: float
    expires_at: float
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    version: str = VERSION

    @classmethod
    def create(cls, *, repository_head: str, working_tree_digest: str, arena: str,
               source_request: str, expires_at: float, created_at: float | None = None) -> "IntentRefinementSession":
        created = time.time() if created_at is None else _timestamp(created_at, "created_at")
        expires = _timestamp(expires_at, "expires_at")
        if expires <= created:
            raise ValueError("expires_at must be later than created_at")
        request = _required(source_request, "source_request")
        base = {
            "repository_head": _required(repository_head, "repository_head"),
            "working_tree_digest": _required(working_tree_digest, "working_tree_digest"),
            "arena": _required(arena, "arena"),
            "source_request_digest": stable_digest(request),
            "created_at": created,
            "expires_at": expires,
        }
        return cls(
            stable_id("intent-session", base), base["repository_head"], base["working_tree_digest"],
            base["arena"], request, base["source_request_digest"], "DRAFT", (), (), (), (), (), (),
            (), {}, "PENDING", "", created, expires,
        )

    def transition(self, next_stage: str | RefinementStage, *,
                   positive_requirements: Sequence[str] | None = None,
                   negative_requirements: Sequence[str] | None = None,
                   definitions: Sequence[Any] | None = None,
                   guardrails: Sequence[Any] | None = None,
                   unresolved_ambiguities: Sequence[Any] | None = None,
                   questions_asked: Sequence[Any] | None = None,
                   answers_received: Sequence[Any] | None = None,
                   teach_back: PairedTeachBack | Mapping[str, Any] | None = None,
                   confirmation_status: str | ConfirmationStatus | None = None,
                   confirmation_receipt_id: str | None = None,
                   now: float | None = None) -> "IntentRefinementSession":
        observed = time.time() if now is None else _timestamp(now, "now")
        target = _enum(next_stage, RefinementStage, "next_stage")
        if observed >= self.expires_at and target != "EXPIRED":
            raise ValueError("expired session may only transition to EXPIRED")
        if target not in TRANSITIONS[self.current_stage]:
            raise ValueError(f"illegal refinement transition: {self.current_stage} -> {target}")
        positive = self.candidate_positive_requirements if positive_requirements is None else _strings(positive_requirements, "positive_requirements")
        negative = self.candidate_negative_requirements if negative_requirements is None else _strings(negative_requirements, "negative_requirements")
        ambiguities = self.unresolved_ambiguities if unresolved_ambiguities is None else _records(unresolved_ambiguities, "unresolved_ambiguities")
        teach_payload = self.teach_back if teach_back is None else _record(teach_back, "teach_back")
        status = self.confirmation_status if confirmation_status is None else _enum(confirmation_status, ConfirmationStatus, "confirmation_status")
        receipt_id = self.confirmation_receipt_id if confirmation_receipt_id is None else _optional(confirmation_receipt_id, "confirmation_receipt_id")
        if target == "TEACH_BACK_PENDING" and (not positive or not negative or not teach_payload):
            raise ValueError("teach-back requires explicit positive and negative requirements")
        if target == "HUMAN_CONFIRMED":
            required_decisions = teach_payload.get("required_human_decisions", ()) if teach_payload else ()
            if status != "CONFIRMED" or not positive or not negative or ambiguities or not teach_payload or required_decisions:
                raise ValueError("human confirmation requires teach-back, confirmed status, both polarities, and ambiguities resolved")
        if target == "COMPILED" and not receipt_id:
            raise ValueError("COMPILED requires a confirmation receipt")
        if target == "STALE":
            status = "STALE"
        elif target == "REJECTED":
            status = "REJECTED"
        elif target == "EXPIRED":
            status = "EXPIRED"
        return replace(
            self, current_stage=target, candidate_positive_requirements=positive,
            candidate_negative_requirements=negative,
            candidate_definitions=self.candidate_definitions if definitions is None else _records(definitions, "definitions"),
            candidate_guardrails=self.candidate_guardrails if guardrails is None else _records(guardrails, "guardrails"),
            unresolved_ambiguities=ambiguities,
            questions_asked=self.questions_asked if questions_asked is None else _records(questions_asked, "questions_asked"),
            answers_received=self.answers_received if answers_received is None else _records(answers_received, "answers_received"),
            teach_back=teach_payload,
            confirmation_status=status, confirmation_receipt_id=receipt_id,
        )

    def is_current(self, *, repository_head: str, working_tree_digest: str,
                   now: float | None = None) -> bool:
        observed = time.time() if now is None else _timestamp(now, "now")
        return (
            self.current_stage not in {"STALE", "REJECTED", "EXPIRED"}
            and observed < self.expires_at
            and _required(repository_head, "repository_head") == self.repository_head
            and _required(working_tree_digest, "working_tree_digest") == self.working_tree_digest
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        for key in ("candidate_positive_requirements", "candidate_negative_requirements",
                    "candidate_definitions", "candidate_guardrails", "unresolved_ambiguities",
                    "questions_asked", "answers_received"):
            payload[key] = list(payload[key])
        return payload


@dataclass(frozen=True)
class IntentConfirmationReceipt:
    confirmation_id: str
    session_id: str
    repository_head: str
    source_tree_digest: str
    working_tree_clean_receipt: str
    source_request_digest: str
    positive_requirements_digest: str
    negative_requirements_digest: str
    semantic_ledger_digest: str
    guardrail_set_digest: str
    authority_digest: str
    teach_back_digest: str
    allowed_path_set_digest: str
    runtime_profile_digest: str
    unified_execution_binding_ref: str
    human_reviewer: str
    human_disposition: str
    confirmed_at: float
    expires_at: float
    expires_or_stales_on: tuple[str, ...]
    confirmation_status: str = "CONFIRMED"
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    version: str = VERSION

    @classmethod
    def create(cls, *, session_id: str, repository_head: str, source_tree_digest: str,
               working_tree_clean_receipt: str, source_request_digest: str,
               positive_requirements: Sequence[str], negative_requirements: Sequence[str],
               semantic_ledger_digest: str, guardrails: Sequence[Any], authority: Mapping[str, Any],
               teach_back: PairedTeachBack, allowed_paths: Sequence[str], runtime_profile_digest: str,
               human_reviewer: str, human_disposition: str, expires_at: float,
               expires_or_stales_on: Sequence[str], confirmed_at: float | None = None,
               unified_execution_binding_ref: str = "") -> "IntentConfirmationReceipt":
        confirmed = time.time() if confirmed_at is None else _timestamp(confirmed_at, "confirmed_at")
        expires = _timestamp(expires_at, "expires_at")
        if expires <= confirmed:
            raise ValueError("expires_at must be later than confirmed_at")
        positive, negative = _strings(positive_requirements, "positive_requirements", True), _strings(negative_requirements, "negative_requirements", True)
        guardrail_payloads, authority_payload, paths = _records(guardrails, "guardrails"), _record(authority, "authority"), _paths(allowed_paths, "allowed_paths")
        if not paths:
            raise ValueError("allowed_paths must not be empty")
        if any(item.get("human_disposition") == "DEFERRED" for item in guardrail_payloads):
            raise ValueError("confirmation receipt cannot contain deferred guardrails")
        payload = {
            "session_id": _required(session_id, "session_id"),
            "repository_head": _required(repository_head, "repository_head"),
            "source_tree_digest": _required(source_tree_digest, "source_tree_digest"),
            "working_tree_clean_receipt": _required(working_tree_clean_receipt, "working_tree_clean_receipt"),
            "source_request_digest": _required(source_request_digest, "source_request_digest"),
            "positive_requirements_digest": stable_digest(list(positive)),
            "negative_requirements_digest": stable_digest(list(negative)),
            "semantic_ledger_digest": _required(semantic_ledger_digest, "semantic_ledger_digest"),
            "guardrail_set_digest": stable_digest(guardrail_payloads),
            "authority_digest": stable_digest(authority_payload),
            "teach_back_digest": _required(teach_back.teach_back_digest, "teach_back_digest"),
            "allowed_path_set_digest": stable_digest(list(paths)),
            "runtime_profile_digest": _required(runtime_profile_digest, "runtime_profile_digest"),
            "unified_execution_binding_ref": _optional(unified_execution_binding_ref, "unified_execution_binding_ref"),
            "human_reviewer": _required(human_reviewer, "human_reviewer"),
            "human_disposition": _required(human_disposition, "human_disposition"),
            "confirmed_at": confirmed,
            "expires_at": expires,
            "expires_or_stales_on": _strings(expires_or_stales_on, "expires_or_stales_on", True),
        }
        return cls(stable_id("intent-confirmation", payload), **payload)

    def is_current(self, *, repository_head: str, source_tree_digest: str,
                   source_request_digest: str, positive_requirements: Sequence[str],
                   negative_requirements: Sequence[str], semantic_ledger_digest: str,
                   guardrail_set_digest: str, authority_digest: str,
                   teach_back_digest: str, allowed_paths: Sequence[str],
                   runtime_profile_digest: str, now: float | None = None) -> bool:
        observed = time.time() if now is None else _timestamp(now, "now")
        return (
            observed < self.expires_at
            and _required(repository_head, "repository_head") == self.repository_head
            and _required(source_tree_digest, "source_tree_digest") == self.source_tree_digest
            and _required(source_request_digest, "source_request_digest") == self.source_request_digest
            and stable_digest(list(_strings(positive_requirements, "positive_requirements", True))) == self.positive_requirements_digest
            and stable_digest(list(_strings(negative_requirements, "negative_requirements", True))) == self.negative_requirements_digest
            and _required(semantic_ledger_digest, "semantic_ledger_digest") == self.semantic_ledger_digest
            and _required(guardrail_set_digest, "guardrail_set_digest") == self.guardrail_set_digest
            and _required(authority_digest, "authority_digest") == self.authority_digest
            and _required(teach_back_digest, "teach_back_digest") == self.teach_back_digest
            and stable_digest(list(_paths(allowed_paths, "allowed_paths"))) == self.allowed_path_set_digest
            and _required(runtime_profile_digest, "runtime_profile_digest") == self.runtime_profile_digest
        )

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        payload["expires_or_stales_on"] = list(payload["expires_or_stales_on"])
        return payload


@dataclass(frozen=True)
class IntentRevisionDelta:
    revision_id: str
    parent_confirmation_id: str
    trigger_evidence: tuple[str, ...]
    base_repository_head: str
    base_source_tree_digest: str
    candidate_tree_digest: str
    allowed_path_set_digest: str
    publication_bundle_digest: str
    generated_artifact_disposition: str
    changed_assumptions: tuple[str, ...]
    positive_requirements_added: tuple[str, ...]
    positive_requirements_removed: tuple[str, ...]
    negative_requirements_added: tuple[str, ...]
    negative_requirements_removed: tuple[str, ...]
    definitions_changed: tuple[str, ...]
    guardrails_changed: tuple[str, ...]
    scope_changed: bool
    authority_changed: bool
    affected_plan_tasks: tuple[str, ...]
    required_new_verifiers: tuple[str, ...]
    current_reproof_required: bool
    prior_confirmation_staled: bool
    requires_human_reconfirmation: bool
    requires_council_replan: bool
    revision_class: str
    status: str
    version: str = VERSION

    @classmethod
    def create(cls, *, parent_confirmation_id: str, trigger_evidence: Sequence[str],
               base_repository_head: str, base_source_tree_digest: str, candidate_tree_digest: str,
               allowed_paths: Sequence[str], generated_artifact_disposition: str,
               revision_class: str | PlanRevisionClass, publication_bundle_digest: str = "",
               changed_assumptions: Sequence[str] = (), positive_requirements_added: Sequence[str] = (),
               positive_requirements_removed: Sequence[str] = (), negative_requirements_added: Sequence[str] = (),
               negative_requirements_removed: Sequence[str] = (), definitions_changed: Sequence[str] = (),
               guardrails_changed: Sequence[str] = (), scope_changed: bool = False,
               authority_changed: bool = False, affected_plan_tasks: Sequence[str] = (),
               required_new_verifiers: Sequence[str] = (), current_reproof_required: bool = False,
               prior_confirmation_staled: bool = False, requires_human_reconfirmation: bool = False,
               requires_council_replan: bool = False, status: str = "PROPOSED") -> "IntentRevisionDelta":
        revision = _enum(revision_class, PlanRevisionClass, "revision_class")
        if revision == "INTENT_AUTHORITY_SCOPE_CHANGE" and not (prior_confirmation_staled and requires_human_reconfirmation):
            raise ValueError("intent/authority/scope changes must stale prior confirmation and require human reconfirmation")
        if revision == "BOUNDED_PLAN_RESTRUCTURING" and not requires_council_replan:
            raise ValueError("bounded plan restructuring must require Council re-evaluation")
        intent_changes = any((positive_requirements_added, positive_requirements_removed,
                              negative_requirements_added, negative_requirements_removed,
                              definitions_changed, guardrails_changed))
        if revision == "LOCAL_EVIDENCE_REFINEMENT" and (scope_changed or authority_changed or intent_changes or requires_human_reconfirmation or requires_council_replan):
            raise ValueError("local evidence refinement cannot change intent, guardrails, scope, authority, or plan structure")
        if revision == "BOUNDED_PLAN_RESTRUCTURING" and (scope_changed or authority_changed or intent_changes):
            raise ValueError("bounded plan restructuring cannot change intent, guardrails, scope, or authority")
        if revision == "INTENT_AUTHORITY_SCOPE_CHANGE" and not requires_council_replan:
            raise ValueError("intent/authority/scope changes must require Council re-evaluation")
        payload = {
            "parent_confirmation_id": _required(parent_confirmation_id, "parent_confirmation_id"),
            "trigger_evidence": _strings(trigger_evidence, "trigger_evidence", True),
            "base_repository_head": _required(base_repository_head, "base_repository_head"),
            "base_source_tree_digest": _required(base_source_tree_digest, "base_source_tree_digest"),
            "candidate_tree_digest": _required(candidate_tree_digest, "candidate_tree_digest"),
            "allowed_path_set_digest": stable_digest(list(_paths(allowed_paths, "allowed_paths"))),
            "publication_bundle_digest": _optional(publication_bundle_digest, "publication_bundle_digest"),
            "generated_artifact_disposition": _required(generated_artifact_disposition, "generated_artifact_disposition"),
            "changed_assumptions": _strings(changed_assumptions, "changed_assumptions"),
            "positive_requirements_added": _strings(positive_requirements_added, "positive_requirements_added"),
            "positive_requirements_removed": _strings(positive_requirements_removed, "positive_requirements_removed"),
            "negative_requirements_added": _strings(negative_requirements_added, "negative_requirements_added"),
            "negative_requirements_removed": _strings(negative_requirements_removed, "negative_requirements_removed"),
            "definitions_changed": _strings(definitions_changed, "definitions_changed"),
            "guardrails_changed": _strings(guardrails_changed, "guardrails_changed"),
            "scope_changed": _strict_bool(scope_changed, "scope_changed"), "authority_changed": _strict_bool(authority_changed, "authority_changed"),
            "affected_plan_tasks": _strings(affected_plan_tasks, "affected_plan_tasks"),
            "required_new_verifiers": _strings(required_new_verifiers, "required_new_verifiers"),
            "current_reproof_required": _strict_bool(current_reproof_required, "current_reproof_required"),
            "prior_confirmation_staled": _strict_bool(prior_confirmation_staled, "prior_confirmation_staled"),
            "requires_human_reconfirmation": _strict_bool(requires_human_reconfirmation, "requires_human_reconfirmation"),
            "requires_council_replan": _strict_bool(requires_council_replan, "requires_council_replan"),
            "revision_class": revision, "status": _required(status, "status"),
        }
        return cls(stable_id("intent-revision", payload), **payload)

    def to_dict(self) -> dict[str, Any]:
        payload = _dataclass_dict(self)
        for key, value in tuple(payload.items()):
            if isinstance(value, tuple):
                payload[key] = list(value)
        return payload


NEGATION = re.compile(
    r"(?ix)\b(leave(?=[^.!?\n]{0,120}\bunchanged\b)|must\s+not|do\s+not|does\s+not|did\s+not|should\s+not|"
    r"would\s+not|could\s+not|cannot|can['’]t|don['’]t|doesn['’]t|didn['’]t|"
    r"mustn['’]t|shouldn['’]t|wouldn['’]t|couldn['’]t|never|without|avoid|"
    r"exclude|except|only|no|not)\b"
)
SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)")


def _negative_class(statement: str, operator: str, target: str) -> str:
    text = f" {operator} {target} {statement} ".lower()
    checks = (
        ("SOFT_PREFERENCE", operator == "avoid" or " prefer not " in text),
        ("EXCLUSION_NON_GOAL", any(x in text for x in (" not yet ", " out of scope ", " non-goal ", " later phase "))),
        ("AUTHORITY_DENIAL", any(x in text for x in (" approve", " authorize", " certify", " professional release", " inspection", " payment release", " grant access"))),
        ("PRESERVATION_INVARIANT", any(x in text for x in (" unchanged", " preserve", " canonical geometry", " source truth", " mutate canonical", " modify canonical"))),
        ("FAILURE_BEHAVIOR", any(x in text for x in (" silently", " hide failure", " suppress", " fallback", " digest fails", " error", " fail closed"))),
        ("PRIVACY_RESTRICTION", any(x in text for x in (" private", " secret", " personal data", " project data", " credentials", " logs"))),
        ("RESOURCE_RESTRICTION", any(x in text for x in (" paid provider", " external network", " network access", " dependency", " provider", " service"))),
        ("QUALITY_PROHIBITION", any(x in text for x in (" weaken tests", " delete tests", " bypass tests", " rewrite tests", " self-verify", " only verifier"))),
        ("SCOPE_BOUNDARY", any(x in text for x in (" outside", " unrelated files", " scope", " other subsystem", " only these files", " except"))),
        ("TEMPORAL_RESTRICTION", any(x in text for x in (" until ", " before ", " after ", " unless canary"))),
    )
    return next((name for name, matched in checks if matched), "PROHIBITION")


def extract_negative_requirements(text: str) -> tuple[NegativeRequirement, ...]:
    source = _required(text, "text")
    results: list[NegativeRequirement] = []
    for sentence_match in SENTENCE.finditer(source):
        sentence, base = sentence_match.group(0), sentence_match.start()
        matches = list(NEGATION.finditer(sentence))
        for index, match in enumerate(matches):
            end_local = matches[index + 1].start() if index + 1 < len(matches) else len(sentence)
            raw = sentence[match.start():end_local]
            span = raw.strip()
            start = base + match.start() + len(raw) - len(raw.lstrip())
            end = start + len(span)
            target = sentence[match.end():end_local].strip(" \t,:;-.!?")
            operator = match.group(1).lower().replace("’", "'")
            results.append(NegativeRequirement.create(
                statement=span, classification=_negative_class(span, operator, target),
                source_span=span, source_start=start, source_end=end, operator=operator,
                target=target, scope=target, ambiguous=not target or target.lower() in {"it", "that", "this", "so"},
            ))
    return tuple(results)


def detect_requirement_contradictions(positive_requirements: Sequence[str],
                                      negative_requirements: Sequence[str | NegativeRequirement]) -> tuple[dict[str, str], ...]:
    positives = _strings(positive_requirements, "positive_requirements")
    negatives = [item.target or item.statement if isinstance(item, NegativeRequirement) else _required(item, "negative_requirements") for item in negative_requirements]
    stop = {"the", "a", "an", "to", "and", "or", "of", "in", "on", "for", "with",
            "do", "does", "did", "not", "never", "no", "must", "should", "would",
            "could", "can", "without", "avoid", "only", "except"}
    conflicts = []
    for positive in positives:
        p = {x for x in re.findall(r"[a-z0-9_]+", positive.lower()) if x not in stop and len(x) > 2}
        for negative in negatives:
            n = {x for x in re.findall(r"[a-z0-9_]+", negative.lower()) if x not in stop and len(x) > 2}
            overlap = p & n
            if len(overlap) >= 2 or (overlap and min(len(p), len(n)) <= 2):
                conflicts.append({"positive_requirement": positive, "negative_requirement": negative,
                                  "shared_terms": ",".join(sorted(overlap))})
    return tuple(conflicts)


ATLAS = (
    ("Fuzzy similarity, VSA affinity, or semantic closeness must never authorize code mutation or patch approval.", "ATLAS_AFFINITY_MUTATION_BLOCK", "AUTHORITY"),
    ("A component or agent that produces a result must not be its only verifier.", "ATLAS_SELF_VERIFICATION_BLOCK", "AUTHORITY"),
    ("An agent must not upgrade its own candidate relationship into exact architectural truth.", "ATLAS_AGENT_SELF_UPGRADE_BLOCK", "AUTHORITY"),
    ("Circular authorization chains are prohibited.", "ATLAS_CIRCULAR_AUTHORIZATION_BLOCK", "AUTHORITY"),
    ("Temporary worktrees, leases, environments, diagnostics, and child processes must expire and dissolve.", "ATLAS_EPHEMERAL_LEASE_LEAK_BLOCK", "LIFECYCLE"),
    ("Unverified research, generated hypotheses, provisional learning, or model consensus must not directly mutate production.", "ATLAS_RESEARCH_PRODUCTION_COUPLING_BLOCK", "AUTHORITY"),
    ("Arenas must not write each other's state without an explicit adapter and export/import contract.", "ATLAS_CROSS_ARENA_COUPLING_BLOCK", "STATIC_SOURCE"),
)
CODING = (
    ("Do not mutate production during exploration or testing.", "RUNTIME"),
    ("Do not commit, push, open a pull request, merge, or deploy without declared human authority.", "AUTHORITY"),
    ("Do not touch files or symbols outside the explicit lease.", "STATIC_SOURCE"),
    ("Do not invent files, symbols, tests, APIs, runtime evidence, or authority.", "HUMAN_REVIEW"),
    ("Do not expose secrets or private data.", "PRIVACY"),
    ("Do not use unapproved external network access.", "RUNTIME"),
    ("Do not add dependencies without explicit review.", "HUMAN_REVIEW"),
    ("Do not weaken, delete, bypass, or rewrite tests merely to make a patch pass.", "TEST"),
    ("Do not silently suppress an error or replace failure with misleading success.", "RUNTIME"),
    ("Preserve rollback and the last verified version.", "LIFECYCLE"),
    ("Stop and replan when scope, architecture, authority, or meaning changes.", "LIFECYCLE"),
)
CONSTRUCTION = (
    ("Do not authorize physical work.", "HARD_AUTHORITY", "AUTHORITY"),
    ("Do not authorize access control or equipment operation.", "HARD_AUTHORITY", "AUTHORITY"),
    ("Do not release payment.", "HARD_AUTHORITY", "AUTHORITY"),
    ("Do not infer professional, legal, regulatory, engineering, inspection, or environmental certification.", "DOMAIN_REQUIRED", "AUTHORITY"),
    ("Do not infer completion from visual state alone.", "DOMAIN_REQUIRED", "TEST"),
    ("Do not mutate canonical Construction records from spatial presentation.", "DOMAIN_REQUIRED", "SCHEMA"),
    ("Do not place private real-project data in fictional fixtures.", "DOMAIN_REQUIRED", "PRIVACY"),
    ("Do not present synthetic or fallback evidence without a visible label.", "DOMAIN_REQUIRED", "RUNTIME"),
    ("Do not mutate cross-trade state without the canonical Construction adapter.", "DOMAIN_REQUIRED", "STATIC_SOURCE"),
)


def compile_default_guardrails(*, arena: str = "CODING", affected_files: Sequence[str] = (),
                               affected_symbols: Sequence[str] = ()) -> tuple[GuardrailProposal, ...]:
    arena, files, symbols = _required(arena, "arena").upper(), _paths(affected_files, "affected_files"), _strings(affected_symbols, "affected_symbols")
    result = [
        GuardrailProposal.create(statement=statement, source_class="ATLAS_PROHIBITION",
            source_refs=(source,), hardness="HARD_ARCHITECTURAL", enforcement_class=enforcement,
            affected_arenas=(arena,), affected_files=files, affected_symbols=symbols,
            rationale="Mandatory Atlas architectural prohibition.", human_disposition="ACKNOWLEDGED_HARD")
        for statement, source, enforcement in ATLAS
    ]
    result.extend(
        GuardrailProposal.create(statement=statement, source_class="SYSTEM_BASELINE",
            source_refs=(f"UNIVERSAL_CODING_BASELINE_{index:02d}",), hardness="PROPOSED_DEFAULT",
            enforcement_class=enforcement, affected_arenas=(arena,), affected_files=files,
            affected_symbols=symbols, rationale="Editable default for bounded coding work.")
        for index, (statement, enforcement) in enumerate(CODING, 1)
    )
    if arena == "CONSTRUCTION":
        result.extend(
            GuardrailProposal.create(statement=statement, source_class="DOMAIN_CONTRACT",
                source_refs=(f"CONSTRUCTION_DOMAIN_GUARDRAIL_{index:02d}",), hardness=hardness,
                enforcement_class=enforcement, affected_arenas=(arena,), affected_files=files,
                affected_symbols=symbols, rationale="Construction authority and truth-boundary default.",
                human_disposition="ACKNOWLEDGED_HARD" if hardness == "HARD_AUTHORITY" else "DEFERRED")
            for index, (statement, hardness, enforcement) in enumerate(CONSTRUCTION, 1)
        )
    return tuple(result)


def guardrail_set_digest(guardrails: Sequence[Any]) -> str:
    return stable_digest(_records(guardrails, "guardrails"))


def authority_digest(authority: Mapping[str, Any]) -> str:
    return stable_digest(_record(authority, "authority"))


def refinement_capabilities() -> dict[str, Any]:
    return {
        "version": VERSION,
        "memory_owner": MEMORY_OWNER,
        "truth_owner": TRUTH_OWNER,
        "policy_owner": POLICY_OWNER,
        "routing_owner": ROUTING_OWNER,
        "verification_owner": VERIFICATION_OWNER,
        "patch_authority": PATCH_AUTHORITY_GRANTED,
        "production_mutation": PRODUCTION_MUTATION,
        "human_confirmation_required": HUMAN_CONFIRMATION_REQUIRED,
        "canonical_outputs": list(CANONICAL_OUTPUTS),
        "exact_patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
    }
