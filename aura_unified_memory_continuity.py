"""Unified manufactured-memory and continuity integration contracts for AuraOS.

This module is a deterministic adapter over Aura's existing intent, Architect,
Model Cognome, Relationship Experience, QDKT, Crucible, and continuity owners.
It is not a memory store, truth store, router, verifier, policy engine, or
promotion authority.

The contracts implement the smallest vertical slice shared by:
- minimum-sufficient active-memory compilation;
- model-relative execution packets;
- immutable P0 and independently observed P1;
- proposal-only continuity sensitivity receipts;
- current-reproof eligibility for existing learning owners.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import Enum
import json
import math
from pathlib import PurePosixPath
import time
from types import MappingProxyType
from typing import Any

from aura_event_contracts import (
    PATCH_AUTHORITY,
    VSA_PATCH_AUTHORITY,
    canonical_json,
    stable_digest,
)

UNIFIED_MEMORY_CONTINUITY_VERSION = "AURA_UNIFIED_MEMORY_CONTINUITY_V1"
INTENT_PACKET_VERSION = "AURA_INTENT_PACKET_V1"
SEMANTIC_LEDGER_VERSION = "AURA_SEMANTIC_LEDGER_V1"
ARENA_EVIDENCE_SLICE_VERSION = "AURA_ARENA_EVIDENCE_SLICE_V1"
ACT_CAPSULE_ENVELOPE_VERSION = "AURA_ACT_CAPSULE_ENVELOPE_V2"
MODEL_EXECUTION_PACKET_VERSION = "AURA_MODEL_EXECUTION_PACKET_V1"
PREDICTION_PACKET_VERSION = "AURA_PREDICTION_PACKET_V1"
P1_OBSERVATION_VERSION = "AURA_P1_OBSERVATION_V1"
CONTINUITY_SENSITIVITY_RECEIPT_VERSION = "AURA_CONTINUITY_SENSITIVITY_RECEIPT_V1"
CONTINUITY_DELTA_VERSION = "AURA_CONTINUITY_DELTA_V2"
LEARNING_REPROOF_VERSION = "AURA_LEARNING_TO_REPROOF_V1"
QDKT_ADMISSION_VERSION = "AURA_QDKT_CONSEQUENTIAL_ADMISSION_V1"

UNIVERSAL_AGENT_KERNEL = """# AURA UNIVERSAL AGENT KERNEL

You are a replaceable executor inside AuraOS.

1. Preserve the declared human objective, Purpose, meaning, authority, and acceptance criteria.
2. Treat the supplied IntentPacket, Semantic Ledger, Arena Evidence Slice, Act Capsule, source references, tests, and receipts as the active memory for this task.
3. Do not assume unavailable context is true.
4. Use only explicitly authorized files, symbols, tools, effects, and side effects.
5. Absence of permission is not permission.
6. Make the smallest coherent intervention that satisfies the objective.
7. Reuse existing Aura owners before creating a new mechanism.
8. Distinguish established, inferred, unverified, contradicted, stale, missing, and impossible states.
9. Mechanically decidable requirements must be checked by deterministic tools before another model opinion.
10. Completion requires the declared evidence bundle, not plausibility or a happy path.
11. Escalate when context is missing, instructions conflict, scope must expand, architecture differs, an invariant would be violated, or the repair budget is exhausted.
12. Return a compact evidence-backed Continuity Delta.
"""

_MAX_TEXT_BYTES = 16 * 1024
_MAX_ITEMS = 256
_MAX_PACKET_BYTES = 512 * 1024
_ALLOWED_PRIVACY = {"PUBLIC", "PROJECT", "PRIVATE_REDACTED", "RESTRICTED"}
_ALLOWED_FRESHNESS = {"CURRENT", "STALE", "EXPIRED", "UNKNOWN"}
_ALLOWED_HUMAN_DISPOSITIONS = {"APPROVED", "DENIED", "DEFERRED", "NOT_REVIEWED"}


class IntentMode(str, Enum):
    EXPLORE = "EXPLORE"
    PROPOSE = "PROPOSE"
    DECIDE = "DECIDE"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    ESCALATE = "ESCALATE"


class EvidenceTruthClass(str, Enum):
    EXACT_SOURCE = "EXACT_SOURCE"
    EXACT_SCHEMA = "EXACT_SCHEMA"
    EXACT_TEST = "EXACT_TEST"
    EXACT_RUNTIME = "EXACT_RUNTIME"
    EXACT_RECEIPT = "EXACT_RECEIPT"
    ESTABLISHED = "ESTABLISHED"
    INFERRED = "INFERRED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    STALE = "STALE"
    MISSING = "MISSING"
    IMPOSSIBLE = "IMPOSSIBLE"


class LegalOutcome(str, Enum):
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    REPAIR = "REPAIR"
    ESCALATE = "ESCALATE"
    REFUSE = "REFUSE"
    READY_FOR_HUMAN_REVIEW = "READY_FOR_HUMAN_REVIEW"


class PredictionErrorClass(str, Enum):
    NONE = "NONE"
    EXPECTED_VARIANCE = "EXPECTED_VARIANCE"
    CONTEXT_GAP = "CONTEXT_GAP"
    PROMPT_COMPILATION = "PROMPT_COMPILATION"
    MODEL_SELECTION = "MODEL_SELECTION"
    TOOL = "TOOL"
    RUNTIME = "RUNTIME"
    VERIFIER = "VERIFIER"
    WORLD_MODEL = "WORLD_MODEL"
    ORIGINAL_ASSUMPTION = "ORIGINAL_ASSUMPTION"
    UNRESOLVED = "UNRESOLVED"


def _required(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_BYTES} UTF-8 bytes")
    return text


def _optional(value: Any, name: str) -> str:
    if value is None:
        return ""
    if type(value) is not str:
        raise ValueError(f"{name} must be a string")
    text = value.strip()
    if len(text.encode("utf-8")) > _MAX_TEXT_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_TEXT_BYTES} UTF-8 bytes")
    return text


def _strings(values: Sequence[Any], name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > _MAX_ITEMS:
        raise ValueError(f"{name} exceeds {_MAX_ITEMS} items")
    normalized = tuple(_required(value, name) for value in values)
    if required and not normalized:
        raise ValueError(f"{name} must not be empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name} must not contain duplicates")
    return normalized


def _validate_json_object_keys(value: Any, name: str, *, path: str = "$") -> None:
    if isinstance(value, Mapping):
        seen: set[str] = set()
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError(f"{name} must use string JSON object keys at {path}")
            if key in seen:
                raise ValueError(f"{name} contains a duplicate JSON object key at {path}.{key}")
            seen.add(key)
            _validate_json_object_keys(item, name, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_object_keys(item, name, path=f"{path}[{index}]")


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


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        payload = dict(value)
    elif hasattr(value, "to_dict") and callable(value.to_dict):
        payload = value.to_dict()
    elif is_dataclass(value):
        payload = asdict(value)
    else:
        raise ValueError(f"{name} must be a mapping, dataclass, or to_dict record")
    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must normalize to a mapping")
    _validate_json_object_keys(payload, name)
    try:
        normalized = canonical_json(payload)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be canonical JSON data") from exc
    if len(normalized.encode("utf-8")) > _MAX_PACKET_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_PACKET_BYTES} canonical bytes")
    decoded = json.loads(normalized)
    if not isinstance(decoded, dict):
        raise ValueError(f"{name} must normalize to an object")
    return _freeze_json(decoded)


def _strict_bool(value: Any, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a boolean")
    return value


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    if nonnegative and result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


def _timestamp(value: Any, name: str) -> float:
    result = _finite(value, name)
    if abs(result) > 1_000_000_000_000_000:
        raise ValueError(f"{name} is outside the supported timestamp range")
    return result


def _enum(value: str | Enum, enum_type: type[Enum], name: str) -> str:
    raw = value.value if isinstance(value, Enum) else str(value)
    allowed = {item.value for item in enum_type}
    if raw not in allowed:
        raise ValueError(f"unsupported {name}: {raw}")
    return raw


def _packet_size(value: Mapping[str, Any], name: str) -> None:
    if len(canonical_json(value).encode("utf-8")) > _MAX_PACKET_BYTES:
        raise ValueError(f"{name} exceeds {_MAX_PACKET_BYTES} canonical bytes")


def _canonical_tuple_records(values: Sequence[Any], name: str) -> tuple[Mapping[str, Any], ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise ValueError(f"{name} must be a sequence")
    if len(values) > _MAX_ITEMS:
        raise ValueError(f"{name} exceeds {_MAX_ITEMS} items")
    return tuple(_mapping(value, f"{name}[{index}]") for index, value in enumerate(values))


def _repo_paths(values: Sequence[Any], name: str) -> tuple[str, ...]:
    paths = _strings(values, name)
    for value in paths:
        if "\\" in value:
            raise ValueError(f"{name} must use repository-relative POSIX paths")
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or value in {".", ".."}:
            raise ValueError(f"{name} must contain bounded repository-relative paths")
    return paths


def _canonical_model_endpoint_payload(value: Any) -> Mapping[str, Any]:
    from aura_model_cognome import ModelEndpointIdentity

    normalized = _mapping(value, "endpoint_identity")
    expected_fields = set(ModelEndpointIdentity.__dataclass_fields__)
    if set(normalized) != expected_fields:
        raise ValueError("endpoint_identity must be a complete ModelEndpointIdentity")
    payload = _thaw_json(normalized)
    try:
        canonical = ModelEndpointIdentity.create(
            provider=payload["provider"],
            requested_model=payload["requested_model"],
            returned_model=payload["returned_model"],
            base_url_digest=payload["base_url_digest"],
            access_class=payload["access_class"],
            endpoint_fingerprint=payload["endpoint_fingerprint"],
            fingerprint_version=payload["fingerprint_version"],
            provider_revision=payload["provider_revision"],
            tokenizer_family=payload["tokenizer_family"],
            price_snapshot_digest=payload["price_snapshot_digest"],
            first_seen_at=_timestamp(payload["first_seen_at"], "first_seen_at"),
            last_seen_at=_timestamp(payload["last_seen_at"], "last_seen_at"),
            status=payload["status"],
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise ValueError("endpoint_identity is not a valid ModelEndpointIdentity") from exc
    canonical_payload = _mapping(canonical.to_dict(), "endpoint_identity")
    if _thaw_json(canonical_payload) != payload:
        raise ValueError("endpoint_identity failed canonical Model Cognome validation")
    return canonical_payload


def _canonical_act_capsule_payload(value: Any) -> Mapping[str, Any]:
    from aura_architect_loop import ACT_CAPSULE_VERSION, ActCapsule

    normalized = _mapping(value, "legacy_act_capsule")
    expected_fields = set(ActCapsule.__dataclass_fields__)
    if set(normalized) != expected_fields:
        raise ValueError("legacy_act_capsule must be a complete canonical ActCapsule")
    try:
        capsule = ActCapsule.from_dict(_thaw_json(normalized))
    except (TypeError, ValueError) as exc:
        raise ValueError("legacy_act_capsule is not a valid canonical ActCapsule") from exc
    if capsule.capsule_version != ACT_CAPSULE_VERSION:
        raise ValueError("legacy_act_capsule version differs from the canonical owner")
    canonical = _mapping(capsule.to_dict(), "legacy_act_capsule")
    if _thaw_json(canonical) != _thaw_json(normalized):
        raise ValueError("legacy_act_capsule failed canonical round-trip validation")
    return canonical


@dataclass(frozen=True)
class AuthorityEnvelope:
    inspect: bool = False
    edit: bool = False
    test: bool = False
    commit: bool = False
    publish_pr: bool = False
    merge: bool = False
    production_mutation: bool = False

    def __post_init__(self) -> None:
        for item in fields(self):
            _strict_bool(getattr(self, item.name), f"authority.{item.name}")
        if self.commit and not self.edit:
            raise ValueError("commit authority requires edit authority")
        if self.publish_pr and not self.commit:
            raise ValueError("publish_pr authority requires commit authority")
        if self.merge and not self.publish_pr:
            raise ValueError("merge authority requires publish_pr authority")
        if self.production_mutation and not self.edit:
            raise ValueError("production mutation authority requires edit authority")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntentPacket:
    packet_id: str
    objective: str
    purpose: str
    user_meaning: str
    mode: IntentMode | str
    arena: str
    constraints: tuple[str, ...]
    prohibitions: tuple[str, ...]
    authority: AuthorityEnvelope
    acceptance_criteria: tuple[str, ...]
    required_evidence: tuple[str, ...]
    risk_class: str
    cost_budget: str
    context_budget: str
    privacy_class: str
    freshness_requirement: str
    output_contract: str
    intent_digest: str
    version: str = INTENT_PACKET_VERSION

    def __post_init__(self) -> None:
        for name in ("packet_id", "objective", "purpose", "user_meaning", "arena",
                     "risk_class", "cost_budget", "context_budget", "output_contract",
                     "intent_digest"):
            _required(getattr(self, name), name)
        object.__setattr__(self, "mode", IntentMode(_enum(self.mode, IntentMode, "intent mode")))
        object.__setattr__(self, "constraints", _strings(self.constraints, "constraints"))
        object.__setattr__(self, "prohibitions", _strings(self.prohibitions, "prohibitions"))
        object.__setattr__(
            self, "acceptance_criteria",
            _strings(self.acceptance_criteria, "acceptance_criteria", required=True),
        )
        object.__setattr__(
            self, "required_evidence",
            _strings(self.required_evidence, "required_evidence", required=True),
        )
        if not isinstance(self.authority, AuthorityEnvelope):
            raise ValueError("authority must be an AuthorityEnvelope")
        privacy = _required(self.privacy_class, "privacy_class").upper()
        if privacy not in _ALLOWED_PRIVACY:
            raise ValueError("unsupported privacy_class")
        object.__setattr__(self, "privacy_class", privacy)
        freshness = _required(self.freshness_requirement, "freshness_requirement").upper()
        if freshness not in {"CURRENT", "CURRENT_HEAD", "CURRENT_SOURCE", "TIME_BOUNDED"}:
            raise ValueError("unsupported freshness_requirement")
        object.__setattr__(self, "freshness_requirement", freshness)
        if self.version != INTENT_PACKET_VERSION:
            raise ValueError("unsupported IntentPacket version")
        expected = stable_digest(self.identity_payload())
        if self.intent_digest != expected or self.packet_id != f"intent_{expected}":
            raise ValueError("IntentPacket identity mismatch")
        _packet_size(self.to_dict(), "IntentPacket")

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        purpose: str,
        user_meaning: str,
        mode: IntentMode | str,
        arena: str,
        constraints: Sequence[str],
        prohibitions: Sequence[str],
        authority: AuthorityEnvelope,
        acceptance_criteria: Sequence[str],
        required_evidence: Sequence[str],
        risk_class: str,
        cost_budget: str,
        context_budget: str,
        privacy_class: str,
        freshness_requirement: str,
        output_contract: str,
    ) -> IntentPacket:
        identity = {
            "objective": _required(objective, "objective"),
            "purpose": _required(purpose, "purpose"),
            "user_meaning": _required(user_meaning, "user_meaning"),
            "mode": _enum(mode, IntentMode, "intent mode"),
            "arena": _required(arena, "arena"),
            "constraints": list(_strings(constraints, "constraints")),
            "prohibitions": list(_strings(prohibitions, "prohibitions")),
            "authority": authority.to_dict(),
            "acceptance_criteria": list(
                _strings(acceptance_criteria, "acceptance_criteria", required=True)
            ),
            "required_evidence": list(
                _strings(required_evidence, "required_evidence", required=True)
            ),
            "risk_class": _required(risk_class, "risk_class"),
            "cost_budget": _required(cost_budget, "cost_budget"),
            "context_budget": _required(context_budget, "context_budget"),
            "privacy_class": _required(privacy_class, "privacy_class").upper(),
            "freshness_requirement": _required(
                freshness_requirement, "freshness_requirement"
            ).upper(),
            "output_contract": _required(output_contract, "output_contract"),
        }
        digest = stable_digest(identity)
        constructor = dict(identity)
        constructor["authority"] = authority
        return cls(
            packet_id=f"intent_{digest}",
            intent_digest=digest,
            **constructor,
        )

    def identity_payload(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "purpose": self.purpose,
            "user_meaning": self.user_meaning,
            "mode": self.mode.value,
            "arena": self.arena,
            "constraints": list(self.constraints),
            "prohibitions": list(self.prohibitions),
            "authority": self.authority.to_dict(),
            "acceptance_criteria": list(self.acceptance_criteria),
            "required_evidence": list(self.required_evidence),
            "risk_class": self.risk_class,
            "cost_budget": self.cost_budget,
            "context_budget": self.context_budget,
            "privacy_class": self.privacy_class,
            "freshness_requirement": self.freshness_requirement,
            "output_contract": self.output_contract,
        }

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["mode"] = self.mode.value
        return result


@dataclass(frozen=True)
class SemanticDefinition:
    term: str
    means: tuple[str, ...]
    does_not_mean: tuple[str, ...]
    source_refs: tuple[str, ...]
    freshness: str = "CURRENT"

    def __post_init__(self) -> None:
        _required(self.term, "term")
        object.__setattr__(self, "means", _strings(self.means, "means", required=True))
        object.__setattr__(
            self, "does_not_mean", _strings(self.does_not_mean, "does_not_mean")
        )
        object.__setattr__(
            self, "source_refs", _strings(self.source_refs, "source_refs", required=True)
        )
        freshness = _required(self.freshness, "freshness").upper()
        if freshness not in _ALLOWED_FRESHNESS:
            raise ValueError("unsupported semantic freshness")
        object.__setattr__(self, "freshness", freshness)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SemanticLedger:
    ledger_id: str
    intent_digest: str
    definitions: tuple[SemanticDefinition, ...]
    ledger_digest: str
    version: str = SEMANTIC_LEDGER_VERSION

    def __post_init__(self) -> None:
        _required(self.ledger_id, "ledger_id")
        _required(self.intent_digest, "intent_digest")
        if not isinstance(self.definitions, tuple) or not self.definitions:
            raise ValueError("definitions must be a non-empty tuple")
        if any(not isinstance(item, SemanticDefinition) for item in self.definitions):
            raise ValueError("definitions must contain SemanticDefinition records")
        terms = [item.term.casefold() for item in self.definitions]
        if len(terms) != len(set(terms)):
            raise ValueError("Semantic Ledger terms must be unique")
        if any(item.freshness != "CURRENT" for item in self.definitions):
            raise ValueError("Semantic Ledger cannot dispatch with stale definitions")
        if self.version != SEMANTIC_LEDGER_VERSION:
            raise ValueError("unsupported Semantic Ledger version")
        expected = stable_digest(self.identity_payload())
        if self.ledger_digest != expected or self.ledger_id != f"sem_{expected}":
            raise ValueError("Semantic Ledger identity mismatch")
        _packet_size(self.to_dict(), "SemanticLedger")

    @classmethod
    def create(
        cls, *, intent_digest: str, definitions: Sequence[SemanticDefinition]
    ) -> SemanticLedger:
        definitions_tuple = tuple(definitions)
        identity = {
            "intent_digest": _required(intent_digest, "intent_digest"),
            "definitions": [item.to_dict() for item in definitions_tuple],
        }
        digest = stable_digest(identity)
        return cls(
            ledger_id=f"sem_{digest}",
            intent_digest=identity["intent_digest"],
            definitions=definitions_tuple,
            ledger_digest=digest,
        )

    def require_terms(self, terms: Sequence[str]) -> None:
        available = {item.term.casefold() for item in self.definitions}
        missing = [term for term in _strings(terms, "required_terms") if term.casefold() not in available]
        if missing:
            raise ValueError(f"Semantic Ledger is missing required terms: {missing}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "intent_digest": self.intent_digest,
            "definitions": [item.to_dict() for item in self.definitions],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "ledger_id": self.ledger_id,
            "intent_digest": self.intent_digest,
            "definitions": [item.to_dict() for item in self.definitions],
            "ledger_digest": self.ledger_digest,
            "version": self.version,
        }


@dataclass(frozen=True)
class ArenaEvidenceItem:
    evidence_ref: str
    causal_reason: str
    truth_class: EvidenceTruthClass | str
    canonical_owner: str
    source_digest: str
    freshness: str
    required: bool = True

    def __post_init__(self) -> None:
        for name in ("evidence_ref", "causal_reason", "canonical_owner", "source_digest"):
            _required(getattr(self, name), name)
        object.__setattr__(
            self,
            "truth_class",
            EvidenceTruthClass(_enum(self.truth_class, EvidenceTruthClass, "truth class")),
        )
        freshness = _required(self.freshness, "freshness").upper()
        if freshness not in _ALLOWED_FRESHNESS:
            raise ValueError("unsupported evidence freshness")
        object.__setattr__(self, "freshness", freshness)
        _strict_bool(self.required, "required")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["truth_class"] = self.truth_class.value
        return result


@dataclass(frozen=True)
class ArenaEvidenceSlice:
    slice_id: str
    repository_head: str
    working_tree_digest: str
    codemap_digest: str
    objective_digest: str
    items: tuple[ArenaEvidenceItem, ...]
    prohibitions: tuple[str, ...]
    required_verifiers: tuple[str, ...]
    excluded_refs: tuple[str, ...]
    slice_digest: str
    version: str = ARENA_EVIDENCE_SLICE_VERSION

    def __post_init__(self) -> None:
        for name in (
            "slice_id", "repository_head", "working_tree_digest", "codemap_digest",
            "objective_digest", "slice_digest",
        ):
            _required(getattr(self, name), name)
        if not isinstance(self.items, tuple) or not self.items:
            raise ValueError("Arena Evidence Slice must contain evidence items")
        if any(not isinstance(item, ArenaEvidenceItem) for item in self.items):
            raise ValueError("items must contain ArenaEvidenceItem records")
        refs = [item.evidence_ref for item in self.items]
        if len(refs) != len(set(refs)):
            raise ValueError("Arena Evidence Slice contains duplicate evidence refs")
        if any(
            item.required
            and (
                item.freshness != "CURRENT"
                or item.truth_class in {
                    EvidenceTruthClass.UNVERIFIED,
                    EvidenceTruthClass.CONTRADICTED,
                    EvidenceTruthClass.STALE,
                    EvidenceTruthClass.MISSING,
                    EvidenceTruthClass.IMPOSSIBLE,
                }
            )
            for item in self.items
        ):
            raise ValueError("required evidence must be current and dispatch-compatible")
        object.__setattr__(self, "prohibitions", _strings(self.prohibitions, "prohibitions"))
        object.__setattr__(
            self,
            "required_verifiers",
            _strings(self.required_verifiers, "required_verifiers", required=True),
        )
        object.__setattr__(
            self, "excluded_refs", _strings(self.excluded_refs, "excluded_refs")
        )
        if set(refs) & set(self.excluded_refs):
            raise ValueError("included and excluded evidence refs overlap")
        if self.version != ARENA_EVIDENCE_SLICE_VERSION:
            raise ValueError("unsupported Arena Evidence Slice version")
        expected = stable_digest(self.identity_payload())
        if self.slice_digest != expected or self.slice_id != f"slice_{expected}":
            raise ValueError("Arena Evidence Slice identity mismatch")
        _packet_size(self.to_dict(), "ArenaEvidenceSlice")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "repository_head": self.repository_head,
            "working_tree_digest": self.working_tree_digest,
            "codemap_digest": self.codemap_digest,
            "objective_digest": self.objective_digest,
            "items": [item.to_dict() for item in self.items],
            "prohibitions": list(self.prohibitions),
            "required_verifiers": list(self.required_verifiers),
            "excluded_refs": list(self.excluded_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "slice_id": self.slice_id,
            **self.identity_payload(),
            "slice_digest": self.slice_digest,
            "version": self.version,
        }


@dataclass(frozen=True)
class ActCapsuleEnvelope:
    envelope_id: str
    legacy_act_capsule: Mapping[str, Any]
    legacy_act_capsule_digest: str
    intent_digest: str
    semantic_ledger_digest: str
    arena_slice_digest: str
    repository_head: str
    allowed_files: tuple[str, ...]
    allowed_symbols: tuple[str, ...]
    prohibited_effects: tuple[str, ...]
    invariants: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    p0_required: bool
    acceptance_bundle: tuple[str, ...]
    repair_budget: int
    legal_outcomes: tuple[LegalOutcome, ...]
    continuity_requirements: tuple[str, ...]
    envelope_digest: str
    version: str = ACT_CAPSULE_ENVELOPE_VERSION
    canonical_act_owner: str = "aura_architect_loop.ActCapsule"
    compatibility_adapter: bool = True
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY

    def __post_init__(self) -> None:
        for name in (
            "envelope_id", "legacy_act_capsule_digest", "intent_digest",
            "semantic_ledger_digest", "arena_slice_digest", "repository_head",
            "envelope_digest", "canonical_act_owner",
        ):
            _required(getattr(self, name), name)
        normalized = _mapping(self.legacy_act_capsule, "legacy_act_capsule")
        object.__setattr__(self, "legacy_act_capsule", normalized)
        if stable_digest(normalized) != self.legacy_act_capsule_digest:
            raise ValueError("legacy Act Capsule digest mismatch")
        object.__setattr__(
            self, "allowed_files", _repo_paths(self.allowed_files, "allowed_files")
        )
        object.__setattr__(
            self, "allowed_symbols", _strings(self.allowed_symbols, "allowed_symbols")
        )
        object.__setattr__(
            self,
            "prohibited_effects",
            _strings(self.prohibited_effects, "prohibited_effects", required=True),
        )
        object.__setattr__(
            self, "invariants", _strings(self.invariants, "invariants", required=True)
        )
        object.__setattr__(
            self, "allowed_tools", _strings(self.allowed_tools, "allowed_tools")
        )
        _strict_bool(self.p0_required, "p0_required")
        if self.p0_required is not True:
            raise ValueError("unified Act Capsule dispatch requires P0")
        object.__setattr__(
            self,
            "acceptance_bundle",
            _strings(self.acceptance_bundle, "acceptance_bundle", required=True),
        )
        if type(self.repair_budget) is not int or self.repair_budget < 0:
            raise ValueError("repair_budget must be a non-negative integer")
        outcomes = tuple(LegalOutcome(_enum(item, LegalOutcome, "legal outcome")) for item in self.legal_outcomes)
        if not outcomes or len(outcomes) != len(set(outcomes)):
            raise ValueError("legal_outcomes must be non-empty and unique")
        object.__setattr__(self, "legal_outcomes", outcomes)
        object.__setattr__(
            self,
            "continuity_requirements",
            _strings(
                self.continuity_requirements,
                "continuity_requirements",
                required=True,
            ),
        )
        if (
            self.version != ACT_CAPSULE_ENVELOPE_VERSION
            or self.compatibility_adapter is not True
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
        ):
            raise ValueError("Act Capsule envelope authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.envelope_digest != expected or self.envelope_id != f"actenv_{expected}":
            raise ValueError("Act Capsule envelope identity mismatch")
        _packet_size(self.to_dict(), "ActCapsuleEnvelope")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "legacy_act_capsule": _thaw_json(self.legacy_act_capsule),
            "legacy_act_capsule_digest": self.legacy_act_capsule_digest,
            "intent_digest": self.intent_digest,
            "semantic_ledger_digest": self.semantic_ledger_digest,
            "arena_slice_digest": self.arena_slice_digest,
            "repository_head": self.repository_head,
            "allowed_files": list(self.allowed_files),
            "allowed_symbols": list(self.allowed_symbols),
            "prohibited_effects": list(self.prohibited_effects),
            "invariants": list(self.invariants),
            "allowed_tools": list(self.allowed_tools),
            "p0_required": self.p0_required,
            "acceptance_bundle": list(self.acceptance_bundle),
            "repair_budget": self.repair_budget,
            "legal_outcomes": [item.value for item in self.legal_outcomes],
            "continuity_requirements": list(self.continuity_requirements),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            **self.identity_payload(),
            "envelope_digest": self.envelope_digest,
            "version": self.version,
            "canonical_act_owner": self.canonical_act_owner,
            "compatibility_adapter": self.compatibility_adapter,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
        }


@dataclass(frozen=True)
class ModelProfileRef:
    profile_id: str
    provider: str
    requested_model: str
    returned_model: str
    endpoint_fingerprint: str
    provider_revision: str
    endpoint_identity: Mapping[str, Any]
    endpoint_identity_digest: str
    profile_digest: str
    status: str
    calibrated_at: float
    expires_at: float
    evidence_refs: tuple[str, ...]
    uncertainty: float

    def __post_init__(self) -> None:
        for name in (
            "profile_id", "provider", "requested_model", "returned_model",
            "endpoint_fingerprint", "endpoint_identity_digest", "profile_digest", "status",
        ):
            _required(getattr(self, name), name)
        object.__setattr__(self, "provider_revision", _optional(self.provider_revision, "provider_revision"))
        endpoint_identity = _canonical_model_endpoint_payload(self.endpoint_identity)
        object.__setattr__(self, "endpoint_identity", endpoint_identity)
        if stable_digest(endpoint_identity) != self.endpoint_identity_digest:
            raise ValueError("ModelProfileRef endpoint identity digest mismatch")
        endpoint_payload = _thaw_json(endpoint_identity)
        for name in (
            "profile_id",
            "provider",
            "requested_model",
            "returned_model",
            "endpoint_fingerprint",
            "provider_revision",
            "status",
        ):
            if getattr(self, name) != endpoint_payload[name]:
                raise ValueError(f"ModelProfileRef {name} differs from Model Cognome identity")
        calibrated = _timestamp(self.calibrated_at, "calibrated_at")
        expires = _timestamp(self.expires_at, "expires_at")
        if expires <= calibrated:
            raise ValueError("expires_at must be after calibrated_at")
        object.__setattr__(self, "calibrated_at", calibrated)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(
            self, "evidence_refs", _strings(self.evidence_refs, "evidence_refs", required=True)
        )
        uncertainty = _finite(self.uncertainty, "uncertainty", nonnegative=True)
        if uncertainty > 1:
            raise ValueError("uncertainty must be between 0 and 1")
        object.__setattr__(self, "uncertainty", uncertainty)
        if self.status != "ACTIVE":
            raise ValueError("only ACTIVE model profiles may compile consequential packets")
        expected = stable_digest(self.identity_payload())
        if self.profile_digest != expected:
            raise ValueError("ModelProfileRef digest mismatch")
        _packet_size(self.to_dict(), "ModelProfileRef")

    @classmethod
    def create(
        cls,
        *,
        endpoint_identity: Any,
        calibrated_at: float,
        expires_at: float,
        evidence_refs: Sequence[str],
        uncertainty: float,
    ) -> ModelProfileRef:
        from aura_model_cognome import ModelEndpointIdentity

        if not isinstance(endpoint_identity, ModelEndpointIdentity):
            raise ValueError("endpoint_identity must use canonical ModelEndpointIdentity")
        canonical_endpoint = ModelEndpointIdentity.create(
            provider=endpoint_identity.provider,
            requested_model=endpoint_identity.requested_model,
            returned_model=endpoint_identity.returned_model,
            base_url_digest=endpoint_identity.base_url_digest,
            access_class=endpoint_identity.access_class,
            endpoint_fingerprint=endpoint_identity.endpoint_fingerprint,
            fingerprint_version=endpoint_identity.fingerprint_version,
            provider_revision=endpoint_identity.provider_revision,
            tokenizer_family=endpoint_identity.tokenizer_family,
            price_snapshot_digest=endpoint_identity.price_snapshot_digest,
            first_seen_at=_timestamp(endpoint_identity.first_seen_at, "first_seen_at"),
            last_seen_at=_timestamp(endpoint_identity.last_seen_at, "last_seen_at"),
            status=endpoint_identity.status,
        )
        endpoint_payload = canonical_endpoint.to_dict()
        if endpoint_payload != endpoint_identity.to_dict():
            raise ValueError("endpoint_identity failed canonical Model Cognome validation")
        payload = {
            "profile_id": canonical_endpoint.profile_id,
            "provider": canonical_endpoint.provider,
            "requested_model": canonical_endpoint.requested_model,
            "returned_model": canonical_endpoint.returned_model,
            "endpoint_fingerprint": canonical_endpoint.endpoint_fingerprint,
            "provider_revision": canonical_endpoint.provider_revision,
            "endpoint_identity": endpoint_payload,
            "endpoint_identity_digest": stable_digest(endpoint_payload),
            "status": canonical_endpoint.status,
            "calibrated_at": _timestamp(calibrated_at, "calibrated_at"),
            "expires_at": _timestamp(expires_at, "expires_at"),
            "evidence_refs": list(_strings(evidence_refs, "evidence_refs", required=True)),
            "uncertainty": _finite(uncertainty, "uncertainty", nonnegative=True),
        }
        digest = stable_digest(payload)
        return cls(profile_digest=digest, **payload)

    def assert_fresh(self, *, observed_at: float | None = None) -> None:
        now = time.time() if observed_at is None else _timestamp(observed_at, "observed_at")
        if now < self.calibrated_at or now >= self.expires_at:
            raise ValueError("Model Cognome profile is not current")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "returned_model": self.returned_model,
            "endpoint_fingerprint": self.endpoint_fingerprint,
            "provider_revision": self.provider_revision,
            "endpoint_identity": _thaw_json(self.endpoint_identity),
            "endpoint_identity_digest": self.endpoint_identity_digest,
            "status": self.status,
            "calibrated_at": self.calibrated_at,
            "expires_at": self.expires_at,
            "evidence_refs": list(self.evidence_refs),
            "uncertainty": self.uncertainty,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "profile_digest": self.profile_digest}


@dataclass(frozen=True)
class ModelExecutionPacket:
    packet_id: str
    intent_digest: str
    act_capsule_digest: str
    repository_head: str
    working_tree_digest: str
    source_digest: str
    model_profile_digest: str
    provider_config_digest: str
    selected_role: str
    task_slice: str
    prompt_structure: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    context_order: tuple[str, ...]
    examples: tuple[Mapping[str, Any], ...]
    tools_available: tuple[str, ...]
    reasoning_budget: str
    output_schema: str
    uncertainty_requirements: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    retry_policy: str
    escalation_policy: str
    disagreement_refs: tuple[str, ...]
    required_verification_depth: int
    packet_digest: str
    version: str = MODEL_EXECUTION_PACKET_VERSION
    disposable: bool = True
    action_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "packet_id", "intent_digest", "act_capsule_digest", "repository_head",
            "working_tree_digest", "source_digest", "model_profile_digest",
            "provider_config_digest", "selected_role", "task_slice",
            "reasoning_budget", "output_schema", "retry_policy", "escalation_policy",
            "packet_digest",
        ):
            _required(getattr(self, name), name)
        for name, required in (
            ("prompt_structure", True), ("evidence_refs", True), ("context_order", True),
            ("tools_available", False), ("uncertainty_requirements", True),
            ("stop_conditions", True), ("disagreement_refs", False),
        ):
            object.__setattr__(self, name, _strings(getattr(self, name), name, required=required))
        object.__setattr__(
            self, "examples", _canonical_tuple_records(self.examples, "examples")
        )
        if type(self.required_verification_depth) is not int or self.required_verification_depth < 1:
            raise ValueError("required_verification_depth must be a positive integer")
        if self.disagreement_refs and self.required_verification_depth < 2:
            raise ValueError("cross-model disagreement must increase verification depth")
        if (
            self.version != MODEL_EXECUTION_PACKET_VERSION
            or self.disposable is not True
            or self.action_authority is not False
        ):
            raise ValueError("ModelExecutionPacket authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.packet_digest != expected or self.packet_id != f"modelexec_{expected}":
            raise ValueError("ModelExecutionPacket identity mismatch")
        _packet_size(self.to_dict(), "ModelExecutionPacket")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "intent_digest": self.intent_digest,
            "act_capsule_digest": self.act_capsule_digest,
            "repository_head": self.repository_head,
            "working_tree_digest": self.working_tree_digest,
            "source_digest": self.source_digest,
            "model_profile_digest": self.model_profile_digest,
            "provider_config_digest": self.provider_config_digest,
            "selected_role": self.selected_role,
            "task_slice": self.task_slice,
            "prompt_structure": list(self.prompt_structure),
            "evidence_refs": list(self.evidence_refs),
            "context_order": list(self.context_order),
            "examples": [_thaw_json(item) for item in self.examples],
            "tools_available": list(self.tools_available),
            "reasoning_budget": self.reasoning_budget,
            "output_schema": self.output_schema,
            "uncertainty_requirements": list(self.uncertainty_requirements),
            "stop_conditions": list(self.stop_conditions),
            "retry_policy": self.retry_policy,
            "escalation_policy": self.escalation_policy,
            "disagreement_refs": list(self.disagreement_refs),
            "required_verification_depth": self.required_verification_depth,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "packet_id": self.packet_id,
            **self.identity_payload(),
            "packet_digest": self.packet_digest,
            "version": self.version,
            "disposable": self.disposable,
            "action_authority": self.action_authority,
        }


@dataclass(frozen=True)
class PredictionPacket:
    prediction_id: str
    objective_digest: str
    purpose_digest: str
    act_capsule_digest: str
    model_execution_packet_digest: str
    model_profile_digest: str
    repository_head: str
    source_digest: str
    prompt_runtime_digest: str
    current_state_digest: str
    proposed_transition: str
    expected_state_delta: tuple[str, ...]
    expected_evidence: tuple[str, ...]
    expected_cost: Mapping[str, Any]
    expected_risk: tuple[str, ...]
    committed_at: float
    producer_id: str
    p0_digest: str
    version: str = PREDICTION_PACKET_VERSION
    committed_before_observation: bool = True

    def __post_init__(self) -> None:
        for name in (
            "prediction_id", "objective_digest", "purpose_digest", "act_capsule_digest",
            "model_execution_packet_digest", "model_profile_digest", "repository_head",
            "source_digest", "prompt_runtime_digest", "current_state_digest",
            "proposed_transition", "producer_id", "p0_digest",
        ):
            _required(getattr(self, name), name)
        object.__setattr__(
            self,
            "expected_state_delta",
            _strings(self.expected_state_delta, "expected_state_delta", required=True),
        )
        object.__setattr__(
            self,
            "expected_evidence",
            _strings(self.expected_evidence, "expected_evidence", required=True),
        )
        object.__setattr__(self, "expected_cost", _mapping(self.expected_cost, "expected_cost"))
        for key, value in self.expected_cost.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                _finite(value, f"expected_cost.{key}", nonnegative=True)
        object.__setattr__(
            self, "expected_risk", _strings(self.expected_risk, "expected_risk", required=True)
        )
        object.__setattr__(self, "committed_at", _timestamp(self.committed_at, "committed_at"))
        if self.version != PREDICTION_PACKET_VERSION or self.committed_before_observation is not True:
            raise ValueError("PredictionPacket must be a committed P0")
        expected = stable_digest(self.identity_payload())
        if self.p0_digest != expected or self.prediction_id != f"prediction_{expected}":
            raise ValueError("PredictionPacket P0 identity mismatch")
        _packet_size(self.to_dict(), "PredictionPacket")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "objective_digest": self.objective_digest,
            "purpose_digest": self.purpose_digest,
            "act_capsule_digest": self.act_capsule_digest,
            "model_execution_packet_digest": self.model_execution_packet_digest,
            "model_profile_digest": self.model_profile_digest,
            "repository_head": self.repository_head,
            "source_digest": self.source_digest,
            "prompt_runtime_digest": self.prompt_runtime_digest,
            "current_state_digest": self.current_state_digest,
            "proposed_transition": self.proposed_transition,
            "expected_state_delta": list(self.expected_state_delta),
            "expected_evidence": list(self.expected_evidence),
            "expected_cost": _thaw_json(self.expected_cost),
            "expected_risk": list(self.expected_risk),
            "committed_at": self.committed_at,
            "producer_id": self.producer_id,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            **self.identity_payload(),
            "p0_digest": self.p0_digest,
            "version": self.version,
            "committed_before_observation": self.committed_before_observation,
        }


@dataclass(frozen=True)
class P1Observation:
    observation_id: str
    prediction_id: str
    p0_digest: str
    objective_digest: str
    purpose_digest: str
    repository_head: str
    source_digest: str
    observed_state_delta: tuple[str, ...]
    observed_evidence_refs: tuple[str, ...]
    observed_cost: Mapping[str, Any]
    missing_measurements: tuple[str, ...]
    observer_id: str
    observed_at: float
    observation_digest: str
    version: str = P1_OBSERVATION_VERSION

    def __post_init__(self) -> None:
        for name in (
            "observation_id", "prediction_id", "p0_digest", "objective_digest",
            "purpose_digest", "repository_head", "source_digest", "observer_id",
            "observation_digest",
        ):
            _required(getattr(self, name), name)
        object.__setattr__(
            self,
            "observed_state_delta",
            _strings(self.observed_state_delta, "observed_state_delta"),
        )
        object.__setattr__(
            self,
            "observed_evidence_refs",
            _strings(self.observed_evidence_refs, "observed_evidence_refs", required=True),
        )
        object.__setattr__(self, "observed_cost", _mapping(self.observed_cost, "observed_cost"))
        for key, value in self.observed_cost.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                _finite(value, f"observed_cost.{key}", nonnegative=True)
        object.__setattr__(
            self,
            "missing_measurements",
            _strings(self.missing_measurements, "missing_measurements"),
        )
        object.__setattr__(self, "observed_at", _timestamp(self.observed_at, "observed_at"))
        if self.version != P1_OBSERVATION_VERSION:
            raise ValueError("unsupported P1 observation version")
        expected = stable_digest(self.identity_payload())
        if self.observation_digest != expected or self.observation_id != f"p1_{expected}":
            raise ValueError("P1 observation identity mismatch")
        _packet_size(self.to_dict(), "P1Observation")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "p0_digest": self.p0_digest,
            "objective_digest": self.objective_digest,
            "purpose_digest": self.purpose_digest,
            "repository_head": self.repository_head,
            "source_digest": self.source_digest,
            "observed_state_delta": list(self.observed_state_delta),
            "observed_evidence_refs": list(self.observed_evidence_refs),
            "observed_cost": _thaw_json(self.observed_cost),
            "missing_measurements": list(self.missing_measurements),
            "observer_id": self.observer_id,
            "observed_at": self.observed_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            **self.identity_payload(),
            "observation_digest": self.observation_digest,
            "version": self.version,
        }


@dataclass(frozen=True)
class ContinuitySensitivityReceipt:
    receipt_id: str
    prediction_id: str
    p0_digest: str
    p1_observation_digest: str
    objective_digest: str
    purpose_digest: str
    repository_head: str
    source_digest: str
    model_profile_digest: str
    model_execution_packet_digest: str
    prompt_runtime_digest: str
    error_class: PredictionErrorClass | str
    prediction_error: tuple[str, ...]
    consequence_dimensions: tuple[str, ...]
    protected_pathways: tuple[str, ...]
    mutation_budget: tuple[str, ...]
    replay_burden: tuple[str, ...]
    raw_evidence_refs: tuple[str, ...]
    missing_measurements: tuple[str, ...]
    replacement_candidate_refs: tuple[str, ...]
    uncertainty: float
    freshness: str
    producer_id: str
    independent_verifier_id: str
    verifier_evidence_refs: tuple[str, ...]
    human_disposition_ref: str
    receipt_digest: str
    version: str = CONTINUITY_SENSITIVITY_RECEIPT_VERSION
    proposal_only: bool = True
    canonical_truth_owner: bool = False
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "receipt_id", "prediction_id", "p0_digest", "p1_observation_digest",
            "objective_digest", "purpose_digest", "repository_head", "source_digest",
            "model_profile_digest", "model_execution_packet_digest",
            "prompt_runtime_digest", "producer_id", "independent_verifier_id",
            "human_disposition_ref", "receipt_digest",
        ):
            _required(getattr(self, name), name)
        if self.producer_id == self.independent_verifier_id:
            raise ValueError("producer cannot independently verify its own continuity receipt")
        object.__setattr__(
            self, "error_class",
            PredictionErrorClass(_enum(self.error_class, PredictionErrorClass, "prediction error class")),
        )
        for name, required in (
            ("prediction_error", False), ("consequence_dimensions", True),
            ("protected_pathways", True), ("mutation_budget", True),
            ("replay_burden", True), ("raw_evidence_refs", True),
            ("missing_measurements", False), ("replacement_candidate_refs", False),
            ("verifier_evidence_refs", True),
        ):
            object.__setattr__(self, name, _strings(getattr(self, name), name, required=required))
        uncertainty = _finite(self.uncertainty, "uncertainty", nonnegative=True)
        if uncertainty > 1:
            raise ValueError("uncertainty must be between 0 and 1")
        object.__setattr__(self, "uncertainty", uncertainty)
        freshness = _required(self.freshness, "freshness").upper()
        if freshness != "CURRENT":
            raise ValueError("continuity receipt must be current")
        object.__setattr__(self, "freshness", freshness)
        if (
            self.version != CONTINUITY_SENSITIVITY_RECEIPT_VERSION
            or self.proposal_only is not True
            or self.canonical_truth_owner is not False
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("continuity receipt authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.receipt_digest != expected or self.receipt_id != f"continuity_{expected}":
            raise ValueError("ContinuitySensitivityReceipt identity mismatch")
        _packet_size(self.to_dict(), "ContinuitySensitivityReceipt")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "p0_digest": self.p0_digest,
            "p1_observation_digest": self.p1_observation_digest,
            "objective_digest": self.objective_digest,
            "purpose_digest": self.purpose_digest,
            "repository_head": self.repository_head,
            "source_digest": self.source_digest,
            "model_profile_digest": self.model_profile_digest,
            "model_execution_packet_digest": self.model_execution_packet_digest,
            "prompt_runtime_digest": self.prompt_runtime_digest,
            "error_class": self.error_class.value,
            "prediction_error": list(self.prediction_error),
            "consequence_dimensions": list(self.consequence_dimensions),
            "protected_pathways": list(self.protected_pathways),
            "mutation_budget": list(self.mutation_budget),
            "replay_burden": list(self.replay_burden),
            "raw_evidence_refs": list(self.raw_evidence_refs),
            "missing_measurements": list(self.missing_measurements),
            "replacement_candidate_refs": list(self.replacement_candidate_refs),
            "uncertainty": self.uncertainty,
            "freshness": self.freshness,
            "producer_id": self.producer_id,
            "independent_verifier_id": self.independent_verifier_id,
            "verifier_evidence_refs": list(self.verifier_evidence_refs),
            "human_disposition_ref": self.human_disposition_ref,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            **self.identity_payload(),
            "receipt_digest": self.receipt_digest,
            "version": self.version,
            "proposal_only": self.proposal_only,
            "canonical_truth_owner": self.canonical_truth_owner,
            "patch_authority": self.patch_authority,
            "vsa_patch_authority": self.vsa_patch_authority,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class ContinuityDelta:
    delta_id: str
    objective_digest: str
    purpose_digest: str
    act_capsule_digest: str
    repository_head: str
    continuity_receipt_ref: str
    decisions: tuple[str, ...]
    changed_refs: tuple[str, ...]
    unchanged_protected_pathways: tuple[str, ...]
    unresolved_refs: tuple[str, ...]
    next_required_actions: tuple[str, ...]
    delta_digest: str
    version: str = CONTINUITY_DELTA_VERSION
    durable_lesson: bool = False
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "delta_id", "objective_digest", "purpose_digest", "act_capsule_digest",
            "repository_head", "continuity_receipt_ref", "delta_digest",
        ):
            _required(getattr(self, name), name)
        for name, required in (
            ("decisions", True), ("changed_refs", False),
            ("unchanged_protected_pathways", True), ("unresolved_refs", False),
            ("next_required_actions", True),
        ):
            object.__setattr__(self, name, _strings(getattr(self, name), name, required=required))
        if (
            self.version != CONTINUITY_DELTA_VERSION
            or self.durable_lesson is not False
            or self.promotion_authority is not False
        ):
            raise ValueError("Continuity Delta authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.delta_digest != expected or self.delta_id != f"delta_{expected}":
            raise ValueError("Continuity Delta identity mismatch")
        _packet_size(self.to_dict(), "ContinuityDelta")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "objective_digest": self.objective_digest,
            "purpose_digest": self.purpose_digest,
            "act_capsule_digest": self.act_capsule_digest,
            "repository_head": self.repository_head,
            "continuity_receipt_ref": self.continuity_receipt_ref,
            "decisions": list(self.decisions),
            "changed_refs": list(self.changed_refs),
            "unchanged_protected_pathways": list(self.unchanged_protected_pathways),
            "unresolved_refs": list(self.unresolved_refs),
            "next_required_actions": list(self.next_required_actions),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            **self.identity_payload(),
            "delta_digest": self.delta_digest,
            "version": self.version,
            "durable_lesson": self.durable_lesson,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class LearningToReproofDecision:
    decision_id: str
    relationship_id: str
    relationship_digest: str
    objective_digest: str
    purpose_digest: str
    repository_head: str
    current_source_digest: str
    continuity_receipt_ref: str
    crucible_proposal_ref: str
    current_reproof_ref: str
    independent_verifier_ref: str
    human_disposition: str
    human_disposition_ref: str
    eligible_for_relationship_experience: bool
    blockers: tuple[str, ...]
    decision_digest: str
    version: str = LEARNING_REPROOF_VERSION
    proposal_only: bool = True
    promotion_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_id", "relationship_id", "relationship_digest",
            "objective_digest", "purpose_digest", "repository_head",
            "current_source_digest", "continuity_receipt_ref", "decision_digest",
        ):
            _required(getattr(self, name), name)
        for name in (
            "crucible_proposal_ref", "current_reproof_ref",
            "independent_verifier_ref", "human_disposition_ref",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name), name))
        disposition = _required(self.human_disposition, "human_disposition").upper()
        if disposition not in _ALLOWED_HUMAN_DISPOSITIONS:
            raise ValueError("unsupported human disposition")
        object.__setattr__(self, "human_disposition", disposition)
        _strict_bool(
            self.eligible_for_relationship_experience,
            "eligible_for_relationship_experience",
        )
        object.__setattr__(self, "blockers", _strings(self.blockers, "blockers"))
        required_refs_present = all(
            (
                self.crucible_proposal_ref,
                self.current_reproof_ref,
                self.independent_verifier_ref,
                self.human_disposition_ref,
            )
        )
        expected_eligible = required_refs_present and disposition == "APPROVED" and not self.blockers
        if self.eligible_for_relationship_experience != expected_eligible:
            raise ValueError("learning-to-reproof eligibility does not match blockers")
        if (
            self.version != LEARNING_REPROOF_VERSION
            or self.proposal_only is not True
            or self.promotion_authority is not False
        ):
            raise ValueError("learning-to-reproof authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.decision_digest != expected or self.decision_id != f"reproof_{expected}":
            raise ValueError("LearningToReproofDecision identity mismatch")
        _packet_size(self.to_dict(), "LearningToReproofDecision")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "relationship_id": self.relationship_id,
            "relationship_digest": self.relationship_digest,
            "objective_digest": self.objective_digest,
            "purpose_digest": self.purpose_digest,
            "repository_head": self.repository_head,
            "current_source_digest": self.current_source_digest,
            "continuity_receipt_ref": self.continuity_receipt_ref,
            "crucible_proposal_ref": self.crucible_proposal_ref,
            "current_reproof_ref": self.current_reproof_ref,
            "independent_verifier_ref": self.independent_verifier_ref,
            "human_disposition": self.human_disposition,
            "human_disposition_ref": self.human_disposition_ref,
            "eligible_for_relationship_experience": self.eligible_for_relationship_experience,
            "blockers": list(self.blockers),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            **self.identity_payload(),
            "decision_digest": self.decision_digest,
            "version": self.version,
            "proposal_only": self.proposal_only,
            "promotion_authority": self.promotion_authority,
        }


@dataclass(frozen=True)
class QDKTConsequentialAdmission:
    decision_id: str
    continuity_receipt_ref: str
    relationship_experience_ref: str
    crucible_proposal_ref: str
    current_reproof_ref: str
    independent_verifier_ref: str
    human_disposition_ref: str
    raw_evidence_refs: tuple[str, ...]
    current_repository_head: str
    current_source_digest: str
    purpose_compatible: bool
    privacy_compatible: bool
    consent_compatible: bool
    sovereignty_compatible: bool
    admitted: bool
    blockers: tuple[str, ...]
    decision_digest: str
    version: str = QDKT_ADMISSION_VERSION
    proposal_only: bool = True
    crystallization_authority: bool = False

    def __post_init__(self) -> None:
        for name in (
            "decision_id", "continuity_receipt_ref", "current_repository_head",
            "current_source_digest", "decision_digest",
        ):
            _required(getattr(self, name), name)
        for name in (
            "relationship_experience_ref", "crucible_proposal_ref",
            "current_reproof_ref", "independent_verifier_ref",
            "human_disposition_ref",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name), name))
        object.__setattr__(
            self, "raw_evidence_refs",
            _strings(self.raw_evidence_refs, "raw_evidence_refs", required=True),
        )
        for name in (
            "purpose_compatible", "privacy_compatible", "consent_compatible",
            "sovereignty_compatible", "admitted",
        ):
            _strict_bool(getattr(self, name), name)
        object.__setattr__(self, "blockers", _strings(self.blockers, "blockers"))
        refs_ok = all(
            (
                self.relationship_experience_ref,
                self.crucible_proposal_ref,
                self.current_reproof_ref,
                self.independent_verifier_ref,
                self.human_disposition_ref,
            )
        )
        compatible = all(
            (
                self.purpose_compatible,
                self.privacy_compatible,
                self.consent_compatible,
                self.sovereignty_compatible,
            )
        )
        if self.admitted != (refs_ok and compatible and not self.blockers):
            raise ValueError("QDKT admission does not match blockers and compatibility")
        if (
            self.version != QDKT_ADMISSION_VERSION
            or self.proposal_only is not True
            or self.crystallization_authority is not False
        ):
            raise ValueError("QDKT admission authority or version changed")
        expected = stable_digest(self.identity_payload())
        if self.decision_digest != expected or self.decision_id != f"qdkt_admission_{expected}":
            raise ValueError("QDKT admission identity mismatch")
        _packet_size(self.to_dict(), "QDKTConsequentialAdmission")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "continuity_receipt_ref": self.continuity_receipt_ref,
            "relationship_experience_ref": self.relationship_experience_ref,
            "crucible_proposal_ref": self.crucible_proposal_ref,
            "current_reproof_ref": self.current_reproof_ref,
            "independent_verifier_ref": self.independent_verifier_ref,
            "human_disposition_ref": self.human_disposition_ref,
            "raw_evidence_refs": list(self.raw_evidence_refs),
            "current_repository_head": self.current_repository_head,
            "current_source_digest": self.current_source_digest,
            "purpose_compatible": self.purpose_compatible,
            "privacy_compatible": self.privacy_compatible,
            "consent_compatible": self.consent_compatible,
            "sovereignty_compatible": self.sovereignty_compatible,
            "admitted": self.admitted,
            "blockers": list(self.blockers),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            **self.identity_payload(),
            "decision_digest": self.decision_digest,
            "version": self.version,
            "proposal_only": self.proposal_only,
            "crystallization_authority": self.crystallization_authority,
        }


def compile_arena_evidence_slice(
    *,
    repository_head: str,
    working_tree_digest: str,
    codemap_digest: str,
    objective_digest: str,
    candidate_items: Sequence[ArenaEvidenceItem],
    required_refs: Sequence[str],
    prohibitions: Sequence[str],
    required_verifiers: Sequence[str],
) -> ArenaEvidenceSlice:
    """Compile minimum-sufficient active memory with deterministic saturation/noise tests."""
    required = set(_strings(required_refs, "required_refs", required=True))
    items: list[ArenaEvidenceItem] = []
    excluded: list[str] = []
    seen: set[str] = set()
    for item in candidate_items:
        if not isinstance(item, ArenaEvidenceItem):
            raise ValueError("candidate_items must contain ArenaEvidenceItem records")
        if item.evidence_ref in seen:
            raise ValueError(f"candidate_items contains duplicate evidence_ref: {item.evidence_ref}")
        seen.add(item.evidence_ref)
        if item.required or item.evidence_ref in required:
            selected_item = item
            if item.evidence_ref in required and not item.required:
                selected_item = ArenaEvidenceItem(
                    evidence_ref=item.evidence_ref,
                    causal_reason=item.causal_reason,
                    truth_class=item.truth_class,
                    canonical_owner=item.canonical_owner,
                    source_digest=item.source_digest,
                    freshness=item.freshness,
                    required=True,
                )
            items.append(selected_item)
        else:
            excluded.append(item.evidence_ref)
    present = {item.evidence_ref for item in items}
    missing = sorted(required - present)
    if missing:
        raise ValueError(f"minimum sufficient saturation is missing required refs: {missing}")
    identity = {
        "repository_head": _required(repository_head, "repository_head"),
        "working_tree_digest": _required(working_tree_digest, "working_tree_digest"),
        "codemap_digest": _required(codemap_digest, "codemap_digest"),
        "objective_digest": _required(objective_digest, "objective_digest"),
        "items": [item.to_dict() for item in items],
        "prohibitions": list(_strings(prohibitions, "prohibitions")),
        "required_verifiers": list(
            _strings(required_verifiers, "required_verifiers", required=True)
        ),
        "excluded_refs": list(dict.fromkeys(excluded)),
    }
    digest = stable_digest(identity)
    return ArenaEvidenceSlice(
        slice_id=f"slice_{digest}",
        items=tuple(items),
        slice_digest=digest,
        **{key: value for key, value in identity.items() if key != "items"},
    )


def compile_act_capsule_envelope(
    *,
    legacy_act_capsule: Any,
    intent: IntentPacket,
    semantic_ledger: SemanticLedger,
    arena_slice: ArenaEvidenceSlice,
    allowed_files: Sequence[str],
    allowed_symbols: Sequence[str],
    prohibited_effects: Sequence[str],
    invariants: Sequence[str],
    allowed_tools: Sequence[str],
    acceptance_bundle: Sequence[str],
    repair_budget: int,
    legal_outcomes: Sequence[LegalOutcome | str],
    continuity_requirements: Sequence[str],
    required_semantic_terms: Sequence[str],
) -> ActCapsuleEnvelope:
    """Attach V2 boundaries without replacing Aura's canonical ActCapsule owner."""
    if semantic_ledger.intent_digest != intent.intent_digest:
        raise ValueError("Semantic Ledger and IntentPacket disagree")
    if arena_slice.objective_digest != intent.intent_digest:
        raise ValueError("Arena Evidence Slice and IntentPacket disagree")
    semantic_ledger.require_terms(required_semantic_terms)
    legacy = _canonical_act_capsule_payload(legacy_act_capsule)
    if legacy["objective"] != intent.objective:
        raise ValueError("canonical ActCapsule objective differs from IntentPacket")
    normalized_allowed_files = _repo_paths(allowed_files, "allowed_files")
    normalized_allowed_symbols = _strings(allowed_symbols, "allowed_symbols")
    target_file = str(legacy.get("target_file") or "")
    target_symbol = str(legacy.get("target_symbol") or "")
    if target_file and target_file not in normalized_allowed_files:
        raise ValueError("canonical ActCapsule target_file is outside allowed_files")
    if target_symbol and target_symbol not in normalized_allowed_symbols:
        raise ValueError("canonical ActCapsule target_symbol is outside allowed_symbols")
    legacy_digest = stable_digest(legacy)
    identity = {
        "legacy_act_capsule": legacy,
        "legacy_act_capsule_digest": legacy_digest,
        "intent_digest": intent.intent_digest,
        "semantic_ledger_digest": semantic_ledger.ledger_digest,
        "arena_slice_digest": arena_slice.slice_digest,
        "repository_head": arena_slice.repository_head,
        "allowed_files": list(normalized_allowed_files),
        "allowed_symbols": list(normalized_allowed_symbols),
        "prohibited_effects": list(
            _strings(prohibited_effects, "prohibited_effects", required=True)
        ),
        "invariants": list(_strings(invariants, "invariants", required=True)),
        "allowed_tools": list(_strings(allowed_tools, "allowed_tools")),
        "p0_required": True,
        "acceptance_bundle": list(
            _strings(acceptance_bundle, "acceptance_bundle", required=True)
        ),
        "repair_budget": repair_budget,
        "legal_outcomes": [
            LegalOutcome(_enum(item, LegalOutcome, "legal outcome")).value
            for item in legal_outcomes
        ],
        "continuity_requirements": list(
            _strings(
                continuity_requirements, "continuity_requirements", required=True
            )
        ),
    }
    digest = stable_digest(identity)
    return ActCapsuleEnvelope(
        envelope_id=f"actenv_{digest}",
        legal_outcomes=tuple(LegalOutcome(item) for item in identity["legal_outcomes"]),
        envelope_digest=digest,
        **{
            key: value
            for key, value in identity.items()
            if key not in {"legal_outcomes"}
        },
    )


def compile_model_execution_packet(
    *,
    intent: IntentPacket,
    act_envelope: ActCapsuleEnvelope,
    arena_slice: ArenaEvidenceSlice,
    model_profile: ModelProfileRef,
    current_source_digest: str,
    provider_config_digest: str,
    selected_role: str,
    task_slice: str,
    prompt_structure: Sequence[str],
    evidence_refs: Sequence[str],
    context_order: Sequence[str],
    examples: Sequence[Mapping[str, Any]],
    tools_available: Sequence[str],
    reasoning_budget: str,
    output_schema: str,
    uncertainty_requirements: Sequence[str],
    stop_conditions: Sequence[str],
    retry_policy: str,
    escalation_policy: str,
    disagreement_refs: Sequence[str] = (),
    observed_at: float | None = None,
) -> ModelExecutionPacket:
    """Compile a disposable model-relative packet from a canonical Act Capsule."""
    if act_envelope.intent_digest != intent.intent_digest:
        raise ValueError("Act Capsule envelope and IntentPacket disagree")
    if act_envelope.arena_slice_digest != arena_slice.slice_digest:
        raise ValueError("Act Capsule envelope and Arena Evidence Slice disagree")
    if act_envelope.repository_head != arena_slice.repository_head:
        raise ValueError("Act Capsule envelope repository head is stale")
    role = _required(selected_role, "selected_role")
    if role != str(act_envelope.legacy_act_capsule["role"]):
        raise ValueError("selected_role differs from the canonical ActCapsule role")
    available_tools = _strings(tools_available, "tools_available")
    if not set(available_tools).issubset(act_envelope.allowed_tools):
        raise ValueError("ModelExecutionPacket requests tools outside the Act Capsule")
    selected_evidence = _strings(evidence_refs, "evidence_refs", required=True)
    arena_refs = {item.evidence_ref for item in arena_slice.items}
    if not set(selected_evidence).issubset(arena_refs):
        raise ValueError("ModelExecutionPacket references evidence outside the active slice")
    required_arena_refs = {item.evidence_ref for item in arena_slice.items if item.required}
    missing_required_evidence = sorted(required_arena_refs - set(selected_evidence))
    if missing_required_evidence:
        raise ValueError(
            "ModelExecutionPacket omitted required active evidence: "
            f"{missing_required_evidence}"
        )
    model_profile.assert_fresh(observed_at=observed_at)
    disagreements = _strings(disagreement_refs, "disagreement_refs")
    verification_depth = 2 if disagreements else 1
    identity = {
        "intent_digest": intent.intent_digest,
        "act_capsule_digest": act_envelope.envelope_digest,
        "repository_head": arena_slice.repository_head,
        "working_tree_digest": arena_slice.working_tree_digest,
        "source_digest": _required(current_source_digest, "current_source_digest"),
        "model_profile_digest": model_profile.profile_digest,
        "provider_config_digest": _required(
            provider_config_digest, "provider_config_digest"
        ),
        "selected_role": role,
        "task_slice": _required(task_slice, "task_slice"),
        "prompt_structure": list(
            _strings(prompt_structure, "prompt_structure", required=True)
        ),
        "evidence_refs": list(selected_evidence),
        "context_order": list(_strings(context_order, "context_order", required=True)),
        "examples": [_mapping(item, "example") for item in examples],
        "tools_available": list(available_tools),
        "reasoning_budget": _required(reasoning_budget, "reasoning_budget"),
        "output_schema": _required(output_schema, "output_schema"),
        "uncertainty_requirements": list(
            _strings(
                uncertainty_requirements,
                "uncertainty_requirements",
                required=True,
            )
        ),
        "stop_conditions": list(
            _strings(stop_conditions, "stop_conditions", required=True)
        ),
        "retry_policy": _required(retry_policy, "retry_policy"),
        "escalation_policy": _required(escalation_policy, "escalation_policy"),
        "disagreement_refs": list(disagreements),
        "required_verification_depth": verification_depth,
    }
    digest = stable_digest(identity)
    return ModelExecutionPacket(
        packet_id=f"modelexec_{digest}",
        examples=tuple(identity["examples"]),
        packet_digest=digest,
        **{key: value for key, value in identity.items() if key != "examples"},
    )


def commit_prediction(
    *,
    intent: IntentPacket,
    act_envelope: ActCapsuleEnvelope,
    model_execution_packet: ModelExecutionPacket,
    current_state_digest: str,
    prompt_runtime_digest: str,
    proposed_transition: str,
    expected_state_delta: Sequence[str],
    expected_evidence: Sequence[str],
    expected_cost: Mapping[str, Any],
    expected_risk: Sequence[str],
    producer_id: str,
    committed_at: float | None = None,
) -> PredictionPacket:
    if act_envelope.intent_digest != intent.intent_digest:
        raise ValueError("Act Capsule envelope and IntentPacket disagree at P0")
    if model_execution_packet.intent_digest != intent.intent_digest:
        raise ValueError("ModelExecutionPacket and IntentPacket disagree at P0")
    if model_execution_packet.act_capsule_digest != act_envelope.envelope_digest:
        raise ValueError("ModelExecutionPacket and Act Capsule envelope disagree at P0")
    if model_execution_packet.repository_head != act_envelope.repository_head:
        raise ValueError("ModelExecutionPacket repository head differs from Act Capsule")
    timestamp = time.time() if committed_at is None else committed_at
    identity = {
        "objective_digest": intent.intent_digest,
        "purpose_digest": stable_digest(intent.purpose),
        "act_capsule_digest": act_envelope.envelope_digest,
        "model_execution_packet_digest": model_execution_packet.packet_digest,
        "model_profile_digest": model_execution_packet.model_profile_digest,
        "repository_head": model_execution_packet.repository_head,
        "source_digest": model_execution_packet.source_digest,
        "prompt_runtime_digest": _required(
            prompt_runtime_digest, "prompt_runtime_digest"
        ),
        "current_state_digest": _required(current_state_digest, "current_state_digest"),
        "proposed_transition": _required(proposed_transition, "proposed_transition"),
        "expected_state_delta": list(
            _strings(expected_state_delta, "expected_state_delta", required=True)
        ),
        "expected_evidence": list(
            _strings(expected_evidence, "expected_evidence", required=True)
        ),
        "expected_cost": _mapping(expected_cost, "expected_cost"),
        "expected_risk": list(_strings(expected_risk, "expected_risk", required=True)),
        "committed_at": _timestamp(timestamp, "committed_at"),
        "producer_id": _required(producer_id, "producer_id"),
    }
    digest = stable_digest(identity)
    return PredictionPacket(
        prediction_id=f"prediction_{digest}",
        p0_digest=digest,
        **identity,
    )


def observe_prediction(
    *,
    prediction: PredictionPacket,
    p0_digest: str,
    objective_digest: str,
    purpose_digest: str,
    repository_head: str,
    source_digest: str,
    observed_state_delta: Sequence[str],
    observed_evidence_refs: Sequence[str],
    observed_cost: Mapping[str, Any],
    missing_measurements: Sequence[str],
    observer_id: str,
    observed_at: float | None = None,
) -> P1Observation:
    """Record P1 only when the caller supplies the unchanged committed P0 digest."""
    if stable_digest(prediction.identity_payload()) != prediction.p0_digest:
        raise ValueError("P0 contents changed after commitment")
    if p0_digest != prediction.p0_digest:
        raise ValueError("P0 was modified or does not match the committed prediction")
    if objective_digest != prediction.objective_digest:
        raise ValueError("P1 objective differs from P0")
    if purpose_digest != prediction.purpose_digest:
        raise ValueError("P1 Purpose differs from P0")
    if repository_head != prediction.repository_head:
        raise ValueError("P1 repository head differs from committed P0")
    if source_digest != prediction.source_digest:
        raise ValueError("P1 source digest differs from committed P0")
    observer = _required(observer_id, "observer_id")
    if observer == prediction.producer_id:
        raise ValueError("P0 producer cannot independently observe its own prediction")
    timestamp = time.time() if observed_at is None else observed_at
    if _timestamp(timestamp, "observed_at") <= prediction.committed_at:
        raise ValueError("P1 must occur strictly after P0")
    identity = {
        "prediction_id": prediction.prediction_id,
        "p0_digest": prediction.p0_digest,
        "objective_digest": prediction.objective_digest,
        "purpose_digest": prediction.purpose_digest,
        "repository_head": _required(repository_head, "repository_head"),
        "source_digest": _required(source_digest, "source_digest"),
        "observed_state_delta": list(
            _strings(observed_state_delta, "observed_state_delta")
        ),
        "observed_evidence_refs": list(
            _strings(
                observed_evidence_refs, "observed_evidence_refs", required=True
            )
        ),
        "observed_cost": _mapping(observed_cost, "observed_cost"),
        "missing_measurements": list(
            _strings(missing_measurements, "missing_measurements")
        ),
        "observer_id": observer,
        "observed_at": _timestamp(timestamp, "observed_at"),
    }
    digest = stable_digest(identity)
    return P1Observation(
        observation_id=f"p1_{digest}",
        observation_digest=digest,
        **identity,
    )


def derive_continuity_sensitivity_receipt(
    *,
    prediction: PredictionPacket,
    observation: P1Observation,
    current_repository_head: str,
    current_source_digest: str,
    model_profile_digest: str,
    model_execution_packet_digest: str,
    prompt_runtime_digest: str,
    error_class: PredictionErrorClass | str,
    prediction_error: Sequence[str],
    consequence_dimensions: Sequence[str],
    protected_pathways: Sequence[str],
    mutation_budget: Sequence[str],
    replay_burden: Sequence[str],
    raw_evidence_refs: Sequence[str],
    replacement_candidate_refs: Sequence[str],
    uncertainty: float,
    producer_id: str,
    independent_verifier_id: str,
    verifier_evidence_refs: Sequence[str],
    human_disposition_ref: str,
) -> ContinuitySensitivityReceipt:
    if observation.prediction_id != prediction.prediction_id:
        raise ValueError("P1 does not reference the supplied PredictionPacket")
    if observation.p0_digest != prediction.p0_digest:
        raise ValueError("P1 does not preserve the committed P0 digest")
    if (
        observation.objective_digest != prediction.objective_digest
        or observation.purpose_digest != prediction.purpose_digest
    ):
        raise ValueError("P0 and P1 identity disagree")
    if observation.repository_head != current_repository_head:
        raise ValueError("continuity receipt cannot be copied across repository heads")
    if observation.source_digest != current_source_digest:
        raise ValueError("continuity receipt cannot be copied across source digests")
    if prediction.model_execution_packet_digest != model_execution_packet_digest:
        raise ValueError("continuity receipt model-execution packet differs from P0")
    if prediction.model_profile_digest != model_profile_digest:
        raise ValueError("continuity receipt model profile differs from P0")
    if prediction.prompt_runtime_digest != prompt_runtime_digest:
        raise ValueError("continuity receipt prompt runtime differs from committed P0")
    verifier = _required(independent_verifier_id, "independent_verifier_id")
    if verifier != observation.observer_id:
        raise ValueError("continuity receipt verifier differs from the independent P1 observer")
    verifier_refs = _strings(
        verifier_evidence_refs, "verifier_evidence_refs", required=True
    )
    if not set(verifier_refs).issubset(observation.observed_evidence_refs):
        raise ValueError("verifier evidence is not bound to the P1 observation")
    raw_refs = _strings(raw_evidence_refs, "raw_evidence_refs", required=True)
    if not set(observation.observed_evidence_refs).issubset(raw_refs):
        raise ValueError("continuity receipt omitted raw P1 evidence")
    identity = {
        "prediction_id": prediction.prediction_id,
        "p0_digest": prediction.p0_digest,
        "p1_observation_digest": observation.observation_digest,
        "objective_digest": prediction.objective_digest,
        "purpose_digest": prediction.purpose_digest,
        "repository_head": observation.repository_head,
        "source_digest": observation.source_digest,
        "model_profile_digest": _required(model_profile_digest, "model_profile_digest"),
        "model_execution_packet_digest": model_execution_packet_digest,
        "prompt_runtime_digest": _required(
            prompt_runtime_digest, "prompt_runtime_digest"
        ),
        "error_class": _enum(error_class, PredictionErrorClass, "prediction error class"),
        "prediction_error": list(_strings(prediction_error, "prediction_error")),
        "consequence_dimensions": list(
            _strings(
                consequence_dimensions, "consequence_dimensions", required=True
            )
        ),
        "protected_pathways": list(
            _strings(protected_pathways, "protected_pathways", required=True)
        ),
        "mutation_budget": list(
            _strings(mutation_budget, "mutation_budget", required=True)
        ),
        "replay_burden": list(
            _strings(replay_burden, "replay_burden", required=True)
        ),
        "raw_evidence_refs": list(raw_refs),
        "missing_measurements": list(observation.missing_measurements),
        "replacement_candidate_refs": list(
            _strings(replacement_candidate_refs, "replacement_candidate_refs")
        ),
        "uncertainty": uncertainty,
        "freshness": "CURRENT",
        "producer_id": _required(producer_id, "producer_id"),
        "independent_verifier_id": verifier,
        "verifier_evidence_refs": list(verifier_refs),
        "human_disposition_ref": _required(
            human_disposition_ref, "human_disposition_ref"
        ),
    }
    digest = stable_digest(identity)
    return ContinuitySensitivityReceipt(
        receipt_id=f"continuity_{digest}",
        error_class=PredictionErrorClass(identity["error_class"]),
        receipt_digest=digest,
        **{key: value for key, value in identity.items() if key != "error_class"},
    )


def compile_continuity_delta(
    *,
    objective_digest: str,
    purpose_digest: str,
    act_capsule_digest: str,
    repository_head: str,
    continuity_receipt_ref: str,
    decisions: Sequence[str],
    changed_refs: Sequence[str],
    unchanged_protected_pathways: Sequence[str],
    unresolved_refs: Sequence[str],
    next_required_actions: Sequence[str],
) -> ContinuityDelta:
    identity = {
        "objective_digest": _required(objective_digest, "objective_digest"),
        "purpose_digest": _required(purpose_digest, "purpose_digest"),
        "act_capsule_digest": _required(act_capsule_digest, "act_capsule_digest"),
        "repository_head": _required(repository_head, "repository_head"),
        "continuity_receipt_ref": _required(
            continuity_receipt_ref, "continuity_receipt_ref"
        ),
        "decisions": list(_strings(decisions, "decisions", required=True)),
        "changed_refs": list(_strings(changed_refs, "changed_refs")),
        "unchanged_protected_pathways": list(
            _strings(
                unchanged_protected_pathways,
                "unchanged_protected_pathways",
                required=True,
            )
        ),
        "unresolved_refs": list(_strings(unresolved_refs, "unresolved_refs")),
        "next_required_actions": list(
            _strings(next_required_actions, "next_required_actions", required=True)
        ),
    }
    digest = stable_digest(identity)
    return ContinuityDelta(
        delta_id=f"delta_{digest}", delta_digest=digest, **identity
    )


def evaluate_learning_to_reproof(
    *,
    relationship_id: str,
    relationship_digest: str,
    repository_head: str,
    current_source_digest: str,
    continuity_receipt: ContinuitySensitivityReceipt,
    crucible_proposal_ref: str = "",
    current_reproof_ref: str = "",
    independent_verifier_ref: str = "",
    human_disposition: str = "NOT_REVIEWED",
    human_disposition_ref: str = "",
    extra_blockers: Sequence[str] = (),
) -> LearningToReproofDecision:
    if repository_head != continuity_receipt.repository_head:
        raise ValueError("learning reproof repository head differs from continuity evidence")
    if current_source_digest != continuity_receipt.source_digest:
        raise ValueError("learning reproof source digest differs from continuity evidence")
    if (
        independent_verifier_ref
        and independent_verifier_ref != continuity_receipt.independent_verifier_id
    ):
        raise ValueError("learning reproof verifier differs from continuity evidence")
    blockers = list(_strings(extra_blockers, "extra_blockers"))
    if not crucible_proposal_ref:
        blockers.append("MISSING_CRUCIBLE_PROPOSAL")
    if not current_reproof_ref:
        blockers.append("MISSING_CURRENT_REPROOF")
    if not independent_verifier_ref:
        blockers.append("MISSING_INDEPENDENT_VERIFIER")
    disposition = _required(human_disposition, "human_disposition").upper()
    if disposition != "APPROVED":
        blockers.append(f"HUMAN_DISPOSITION_{disposition}")
    if disposition == "APPROVED" and not human_disposition_ref:
        blockers.append("MISSING_HUMAN_DISPOSITION_REF")
    blockers = list(dict.fromkeys(blockers))
    eligible = not blockers
    identity = {
        "relationship_id": _required(relationship_id, "relationship_id"),
        "relationship_digest": _required(
            relationship_digest, "relationship_digest"
        ),
        "objective_digest": continuity_receipt.objective_digest,
        "purpose_digest": continuity_receipt.purpose_digest,
        "repository_head": _required(repository_head, "repository_head"),
        "current_source_digest": _required(
            current_source_digest, "current_source_digest"
        ),
        "continuity_receipt_ref": continuity_receipt.receipt_id,
        "crucible_proposal_ref": _optional(
            crucible_proposal_ref, "crucible_proposal_ref"
        ),
        "current_reproof_ref": _optional(current_reproof_ref, "current_reproof_ref"),
        "independent_verifier_ref": _optional(
            independent_verifier_ref, "independent_verifier_ref"
        ),
        "human_disposition": disposition,
        "human_disposition_ref": _optional(
            human_disposition_ref, "human_disposition_ref"
        ),
        "eligible_for_relationship_experience": eligible,
        "blockers": blockers,
    }
    digest = stable_digest(identity)
    return LearningToReproofDecision(
        decision_id=f"reproof_{digest}", decision_digest=digest, **identity
    )


def relationship_experience_kwargs(
    *,
    decision: LearningToReproofDecision,
    outcome: str,
    verifier_evidence_refs: Sequence[str],
    receipt_refs: Sequence[str],
    source_refs: Sequence[str],
    working_tree_digest: str,
    privacy_class: str,
    objective_digest: str,
    reason: str,
) -> dict[str, Any]:
    """Return exact kwargs for RelationshipExperienceObservation.create.

    This adapter does not create or persist the canonical observation. The existing
    Relationship Experience owner remains responsible for validation and storage.
    """
    if not decision.eligible_for_relationship_experience:
        raise ValueError("learning-to-reproof decision is not eligible")
    verifier_refs = _strings(
        verifier_evidence_refs, "verifier_evidence_refs", required=True
    )
    if decision.independent_verifier_ref not in verifier_refs:
        raise ValueError("Relationship Experience evidence omits the independent verifier")
    normalized_receipt_refs = _strings(receipt_refs, "receipt_refs", required=True)
    required_governance_refs = {
        decision.continuity_receipt_ref,
        decision.crucible_proposal_ref,
        decision.current_reproof_ref,
        decision.human_disposition_ref,
    }
    missing_governance_refs = sorted(required_governance_refs - set(normalized_receipt_refs))
    if missing_governance_refs:
        raise ValueError(
            "Relationship Experience evidence omits governed receipt refs: "
            f"{missing_governance_refs}"
        )
    normalized_privacy = _required(privacy_class, "privacy_class").upper()
    if normalized_privacy not in {"PUBLIC", "PROJECT", "PRIVATE_REDACTED"}:
        raise ValueError("privacy class is unsupported by Relationship Experience")
    if objective_digest != decision.objective_digest:
        raise ValueError("Relationship Experience objective differs from reproof evidence")
    return {
        "relationship_id": decision.relationship_id,
        "relationship_digest": decision.relationship_digest,
        "repository_head": decision.repository_head,
        "working_tree_digest": _required(
            working_tree_digest, "working_tree_digest"
        ),
        "valid_from_head": decision.repository_head,
        "outcome": _required(outcome, "outcome"),
        "verifier_evidence_refs": list(verifier_refs),
        "receipt_refs": list(normalized_receipt_refs),
        "source_refs": list(_strings(source_refs, "source_refs", required=True)),
        "current_source_digest": decision.current_source_digest,
        "human_disposition": decision.human_disposition,
        "privacy_class": normalized_privacy,
        "objective_digest": _required(objective_digest, "objective_digest"),
        "reason": _optional(reason, "reason"),
    }


def evaluate_qdkt_consequential_admission(
    *,
    continuity_receipt: ContinuitySensitivityReceipt,
    learning_decision: LearningToReproofDecision,
    relationship_experience: Any | None,
    raw_evidence_refs: Sequence[str],
    current_repository_head: str,
    current_source_digest: str,
    purpose_compatible: bool,
    privacy_compatible: bool,
    consent_compatible: bool,
    sovereignty_compatible: bool,
    extra_blockers: Sequence[str] = (),
) -> QDKTConsequentialAdmission:
    from aura_relationship_experience import RelationshipExperienceObservation

    if learning_decision.continuity_receipt_ref != continuity_receipt.receipt_id:
        raise ValueError("QDKT learning decision differs from continuity evidence")
    if current_repository_head != continuity_receipt.repository_head:
        raise ValueError("QDKT repository head differs from continuity evidence")
    if current_source_digest != continuity_receipt.source_digest:
        raise ValueError("QDKT source digest differs from continuity evidence")
    if (
        learning_decision.repository_head != current_repository_head
        or learning_decision.current_source_digest != current_source_digest
    ):
        raise ValueError("QDKT learning decision is stale")

    blockers = list(_strings(extra_blockers, "extra_blockers"))
    if not learning_decision.eligible_for_relationship_experience:
        blockers.append("LEARNING_REPROOF_NOT_ELIGIBLE")

    relationship_ref = ""
    if relationship_experience is None:
        blockers.append("MISSING_RELATIONSHIP_EXPERIENCE")
    elif not isinstance(relationship_experience, RelationshipExperienceObservation):
        raise ValueError("relationship_experience must use the canonical owner")
    else:
        relationship_ref = relationship_experience.observation_id
        if continuity_receipt.receipt_id not in relationship_experience.receipt_refs:
            raise ValueError("Relationship Experience omits the continuity receipt")
        if (
            relationship_experience.repository_head != current_repository_head
            or relationship_experience.current_source_digest != current_source_digest
        ):
            raise ValueError("Relationship Experience is stale for QDKT admission")
        if relationship_experience.relationship_id != learning_decision.relationship_id:
            raise ValueError("Relationship Experience relationship differs from reproof")
        if relationship_experience.relationship_digest != learning_decision.relationship_digest:
            raise ValueError("Relationship Experience digest differs from reproof")
        if relationship_experience.objective_digest != learning_decision.objective_digest:
            raise ValueError("Relationship Experience objective differs from reproof")
        required_relationship_receipts = {
            ref
            for ref in (
                learning_decision.continuity_receipt_ref,
                learning_decision.crucible_proposal_ref,
                learning_decision.current_reproof_ref,
                learning_decision.human_disposition_ref,
            )
            if ref
        }
        if not required_relationship_receipts.issubset(relationship_experience.receipt_refs):
            raise ValueError("Relationship Experience omits governed reproof receipts")
        if (
            learning_decision.independent_verifier_ref
            and learning_decision.independent_verifier_ref
            not in relationship_experience.verifier_evidence_refs
        ):
            raise ValueError("Relationship Experience omits the independent verifier")
        if (
            relationship_experience.human_disposition.value
            != learning_decision.human_disposition
        ):
            raise ValueError("Relationship Experience disposition differs from reproof")
        if relationship_experience.human_disposition.value != "APPROVED":
            blockers.append("HUMAN_DISPOSITION_NOT_APPROVED")

    if not learning_decision.crucible_proposal_ref:
        blockers.append("MISSING_CRUCIBLE_PROPOSAL")
    if not learning_decision.current_reproof_ref:
        blockers.append("MISSING_CURRENT_REPROOF")
    if not learning_decision.independent_verifier_ref:
        blockers.append("MISSING_INDEPENDENT_VERIFIER")
    if not learning_decision.human_disposition_ref:
        blockers.append("MISSING_HUMAN_DISPOSITION")

    raw_refs = _strings(raw_evidence_refs, "raw_evidence_refs", required=True)
    if not set(continuity_receipt.raw_evidence_refs).issubset(raw_refs):
        raise ValueError("QDKT admission omitted continuity raw evidence")

    for name, value in (
        ("PURPOSE_INCOMPATIBLE", purpose_compatible),
        ("PRIVACY_INCOMPATIBLE", privacy_compatible),
        ("CONSENT_INCOMPATIBLE", consent_compatible),
        ("SOVEREIGNTY_INCOMPATIBLE", sovereignty_compatible),
    ):
        _strict_bool(value, name.casefold())
        if not value:
            blockers.append(name)
    blockers = list(dict.fromkeys(blockers))
    admitted = not blockers
    identity = {
        "continuity_receipt_ref": continuity_receipt.receipt_id,
        "relationship_experience_ref": relationship_ref,
        "crucible_proposal_ref": learning_decision.crucible_proposal_ref,
        "current_reproof_ref": learning_decision.current_reproof_ref,
        "independent_verifier_ref": learning_decision.independent_verifier_ref,
        "human_disposition_ref": learning_decision.human_disposition_ref,
        "raw_evidence_refs": list(raw_refs),
        "current_repository_head": _required(
            current_repository_head, "current_repository_head"
        ),
        "current_source_digest": _required(
            current_source_digest, "current_source_digest"
        ),
        "purpose_compatible": purpose_compatible,
        "privacy_compatible": privacy_compatible,
        "consent_compatible": consent_compatible,
        "sovereignty_compatible": sovereignty_compatible,
        "admitted": admitted,
        "blockers": blockers,
    }
    digest = stable_digest(identity)
    return QDKTConsequentialAdmission(
        decision_id=f"qdkt_admission_{digest}",
        decision_digest=digest,
        **identity,
    )


__all__ = [
    "ACT_CAPSULE_ENVELOPE_VERSION",
    "ARENA_EVIDENCE_SLICE_VERSION",
    "CONTINUITY_DELTA_VERSION",
    "CONTINUITY_SENSITIVITY_RECEIPT_VERSION",
    "INTENT_PACKET_VERSION",
    "LEARNING_REPROOF_VERSION",
    "MODEL_EXECUTION_PACKET_VERSION",
    "P1_OBSERVATION_VERSION",
    "PREDICTION_PACKET_VERSION",
    "QDKT_ADMISSION_VERSION",
    "SEMANTIC_LEDGER_VERSION",
    "UNIFIED_MEMORY_CONTINUITY_VERSION",
    "UNIVERSAL_AGENT_KERNEL",
    "ActCapsuleEnvelope",
    "ArenaEvidenceItem",
    "ArenaEvidenceSlice",
    "AuthorityEnvelope",
    "ContinuityDelta",
    "ContinuitySensitivityReceipt",
    "EvidenceTruthClass",
    "IntentMode",
    "IntentPacket",
    "LearningToReproofDecision",
    "LegalOutcome",
    "ModelExecutionPacket",
    "ModelProfileRef",
    "P1Observation",
    "PredictionErrorClass",
    "PredictionPacket",
    "QDKTConsequentialAdmission",
    "SemanticDefinition",
    "SemanticLedger",
    "commit_prediction",
    "compile_act_capsule_envelope",
    "compile_arena_evidence_slice",
    "compile_continuity_delta",
    "compile_model_execution_packet",
    "derive_continuity_sensitivity_receipt",
    "evaluate_learning_to_reproof",
    "evaluate_qdkt_consequential_admission",
    "observe_prediction",
    "relationship_experience_kwargs",
]
