"""Aura Relational Synthesis Phase 1 contracts and shadow compiler.

This module compiles a supplied, exact Emergent Evidence Spine packet into a
read-only objective-specific relational view. It does not discover repository
truth, mutate Waboose or Agent Bridge state, or grant patch authority.

The six-slot intent packet, exact source identities, canonical digests, and
authority boundaries remain owned by their existing Aura modules.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aura_event_contracts import canonical_json, stable_digest, stable_id
from aura_polysynthetic_intent import PolysyntheticIntentPacket
from aura_topological_context_anchor import PATCH_AUTHORITY_POLICY


RELATIONAL_SYNTHESIS_VERSION = "AURA_RELATIONAL_SYNTHESIS_PHASE1_V1"
RELATIONAL_PARTICIPANT_VERSION = "AURA_RELATIONAL_PARTICIPANT_V1"
RELATIONAL_RELATION_VERSION = "AURA_TYPED_RELATION_V1"
RELATIONAL_GROUP_VERSION = "AURA_RELATIONAL_GROUP_V1"
RELATIONAL_CAPSULE_VERSION = "AURA_RELATIONAL_SYNTHESIS_CAPSULE_V1"
RELATIONAL_BOUNDARY_VERSION = "AURA_RELATIONAL_BOUNDARY_V1"
PROOF_OBLIGATION_VERSION = "AURA_RELATIONAL_PROOF_OBLIGATION_V1"
PATCH_AUTHORITY = PATCH_AUTHORITY_POLICY
VSA_PATCH_AUTHORITY = False


class TruthClass(str, Enum):
    EXACT_SOURCE = "EXACT_SOURCE"
    EXACT_SCHEMA = "EXACT_SCHEMA"
    EXACT_TEST = "EXACT_TEST"
    EXACT_MANIFEST = "EXACT_MANIFEST"
    EXACT_RUNTIME = "EXACT_RUNTIME"
    ADVISORY_CONNECTOME = "ADVISORY_CONNECTOME"
    ADVISORY_AFFINITY = "ADVISORY_AFFINITY"
    INFERRED_MOTIF = "INFERRED_MOTIF"
    UNRESOLVED = "UNRESOLVED"


class Freshness(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    UNRESOLVED = "UNRESOLVED"


class ParticipantType(str, Enum):
    ATOMIC_SYMBOL = "atomic_symbol"
    CAPABILITY = "capability"
    TEST = "test"
    SCHEMA = "schema"
    STATE = "state"
    VERIFIER = "verifier"
    AUTHORITY = "authority"
    ARENA = "arena"
    DOCUMENT = "document"
    EXTERNAL_EFFECT = "external_effect"
    PACKET = "packet"


class RelationType(str, Enum):
    CALLS = "CALLS"
    CALLED_BY = "CALLED_BY"
    IMPORTS = "IMPORTS"
    IMPORTED_BY = "IMPORTED_BY"
    TESTS = "TESTS"
    TESTED_BY = "TESTED_BY"
    DECLARES = "DECLARES"
    DEFINED_IN = "DEFINED_IN"
    IMPLEMENTS_CAPABILITY = "IMPLEMENTS_CAPABILITY"
    DOCUMENTED_BY = "DOCUMENTED_BY"
    ACCEPTS_SCHEMA = "ACCEPTS_SCHEMA"
    EMITS_SCHEMA = "EMITS_SCHEMA"
    SERIALIZES = "SERIALIZES"
    DESERIALIZES = "DESERIALIZES"
    VALIDATES = "VALIDATES"
    NORMALIZES = "NORMALIZES"
    READS_STATE = "READS_STATE"
    WRITES_STATE = "WRITES_STATE"
    CLEARS_STATE = "CLEARS_STATE"
    PERSISTS_TO = "PERSISTS_TO"
    RESTORES_FROM = "RESTORES_FROM"
    REQUIRES_CAPABILITY = "REQUIRES_CAPABILITY"
    REQUIRES_LEASE = "REQUIRES_LEASE"
    REQUIRES_AUTHORITY = "REQUIRES_AUTHORITY"
    REQUIRES_CONSENT = "REQUIRES_CONSENT"
    REQUIRES_QUORUM = "REQUIRES_QUORUM"
    REQUIRES_VERIFIER = "REQUIRES_VERIFIER"
    PRODUCES_EVIDENCE = "PRODUCES_EVIDENCE"
    PROJECTS_TO_ARENA = "PROJECTS_TO_ARENA"
    DELEGATES_TO_AGENT = "DELEGATES_TO_AGENT"
    DISSOLVES_AFTER = "DISSOLVES_AFTER"
    OBSERVED_IN_REVIEW = "OBSERVED_IN_REVIEW"
    CORROBORATED_BY = "CORROBORATED_BY"
    REPAIRED_BY = "REPAIRED_BY"
    VERIFIED_BY = "VERIFIED_BY"
    LEARNED_FROM = "LEARNED_FROM"
    REQUIRES_CURRENT_REPROOF = "REQUIRES_CURRENT_REPROOF"


class GroupKind(str, Enum):
    MACRO_DOMAIN = "macro_domain"
    CROSS_DOMAIN_BUNDLE = "cross_domain_bundle"
    OBJECTIVE_GROUP = "objective_group"
    CAUSAL_MOTIF = "causal_motif"


class ProofStatus(str, Enum):
    OPEN = "OPEN"
    SATISFIED = "SATISFIED"
    CONTRADICTED = "CONTRADICTED"
    DEFERRED = "DEFERRED"


_EXACT_TRUTH_CLASSES = frozenset(
    {
        TruthClass.EXACT_SOURCE,
        TruthClass.EXACT_SCHEMA,
        TruthClass.EXACT_TEST,
        TruthClass.EXACT_MANIFEST,
        TruthClass.EXACT_RUNTIME,
    }
)
_EDGE_RELATIONS = {
    "call": RelationType.CALLS,
    "calls": RelationType.CALLS,
    "import": RelationType.IMPORTS,
    "imports": RelationType.IMPORTS,
    "test": RelationType.TESTS,
    "tests": RelationType.TESTS,
}
_INPUT_ROLE_PATTERNS = {
    "input_parser": ("from_value", "parse", "request"),
    "scope_normalizer": ("normalize", "_repo_paths", "target"),
    "authority_guard": ("authority", "human_review", "safe_to_patch", "patch_authority"),
    "packet_assembler": ("assemble_packet", "to_dict", "canonical_dict"),
}


def _required_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string or null")
    return value.strip() or None


def _strict_bool(value: Any, field_name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _strict_nonnegative_int(value: Any, field_name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _string_tuple(
    value: Any,
    field_name: str,
    *,
    allow_empty: bool = True,
    sort_values: bool = True,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"{field_name} must be a list or tuple")
    items = tuple(_required_text(item, f"{field_name}[]") for item in value)
    if not allow_empty and not items:
        raise ValueError(f"{field_name} must not be empty")
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} must not contain duplicates")
    return tuple(sorted(items)) if sort_values else items


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    result = {str(key): item for key, item in value.items()}
    canonical_json(result)
    return result


def _enum(value: Any, enum_type: type[Enum], field_name: str) -> Any:
    if isinstance(value, enum_type):
        return value
    if type(value) is not str:
        raise ValueError(f"{field_name} must be a string")
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"unknown {field_name}: {value}") from exc


def _is_test_path(path: str) -> bool:
    parts = str(path).replace("\\", "/").lower().split("/")
    return any(
        part == "tests" or part.startswith("test_") or part.endswith("_test.py")
        for part in parts
    )


def _identity_ref(file_path: str, qualified_symbol: str) -> str:
    return f"{file_path}#{qualified_symbol}"


@dataclass(frozen=True)
class RelationalParticipant:
    participant_id: str
    participant_type: ParticipantType
    role: str
    truth_class: TruthClass
    canonical_owner: str
    canonical_ref: str
    digest: str | None
    evidence_refs: tuple[str, ...]
    freshness: Freshness
    qualified_symbol: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "participant_type",
            _enum(self.participant_type, ParticipantType, "participant_type"),
        )
        object.__setattr__(self, "role", _required_text(self.role, "role"))
        object.__setattr__(
            self, "truth_class", _enum(self.truth_class, TruthClass, "truth_class")
        )
        object.__setattr__(
            self, "canonical_owner", _required_text(self.canonical_owner, "canonical_owner")
        )
        object.__setattr__(
            self, "canonical_ref", _required_text(self.canonical_ref, "canonical_ref")
        )
        object.__setattr__(self, "digest", _optional_text(self.digest, "digest"))
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self, "freshness", _enum(self.freshness, Freshness, "freshness")
        )
        object.__setattr__(
            self,
            "qualified_symbol",
            _optional_text(self.qualified_symbol, "qualified_symbol"),
        )
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        expected = self.expected_id()
        if self.participant_id != expected:
            raise ValueError("participant_id does not match canonical participant identity")
        if self.truth_class in _EXACT_TRUTH_CLASSES:
            if not self.digest or not self.evidence_refs:
                raise ValueError("exact participants require digest and evidence_refs")
            if self.freshness is not Freshness.CURRENT:
                raise ValueError("exact participants must be current")
        if self.truth_class is TruthClass.UNRESOLVED and self.freshness is not Freshness.UNRESOLVED:
            raise ValueError("unresolved participants must have unresolved freshness")

    @classmethod
    def create(
        cls,
        *,
        participant_type: ParticipantType | str,
        role: str,
        truth_class: TruthClass | str,
        canonical_owner: str,
        canonical_ref: str,
        digest: str | None,
        evidence_refs: Sequence[str] = (),
        freshness: Freshness | str = Freshness.CURRENT,
        qualified_symbol: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> "RelationalParticipant":
        participant_type_value = _enum(
            participant_type, ParticipantType, "participant_type"
        )
        canonical_owner_value = _required_text(canonical_owner, "canonical_owner")
        canonical_ref_value = _required_text(canonical_ref, "canonical_ref")
        digest_value = _optional_text(digest, "digest")
        qualified_value = _optional_text(qualified_symbol, "qualified_symbol")
        identity = {
            "participant_type": participant_type_value.value,
            "canonical_owner": canonical_owner_value,
            "canonical_ref": canonical_ref_value,
            "qualified_symbol": qualified_value,
            "digest": digest_value,
        }
        return cls(
            participant_id=stable_id("relp", identity),
            participant_type=participant_type_value,
            role=role,
            truth_class=truth_class,
            canonical_owner=canonical_owner_value,
            canonical_ref=canonical_ref_value,
            digest=digest_value,
            evidence_refs=tuple(evidence_refs),
            freshness=freshness,
            qualified_symbol=qualified_value,
            metadata=dict(metadata or {}),
        )

    def expected_id(self) -> str:
        return stable_id(
            "relp",
            {
                "participant_type": self.participant_type.value,
                "canonical_owner": self.canonical_owner,
                "canonical_ref": self.canonical_ref,
                "qualified_symbol": self.qualified_symbol,
                "digest": self.digest,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONAL_PARTICIPANT_VERSION,
            "participant_id": self.participant_id,
            "participant_type": self.participant_type.value,
            "role": self.role,
            "truth_class": self.truth_class.value,
            "canonical_owner": self.canonical_owner,
            "canonical_ref": self.canonical_ref,
            "digest": self.digest,
            "evidence_refs": list(self.evidence_refs),
            "freshness": self.freshness.value,
            "qualified_symbol": self.qualified_symbol,
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationalParticipant":
        data = _mapping(value, "participant")
        allowed = {
            "schema_version",
            "participant_id",
            "participant_type",
            "role",
            "truth_class",
            "canonical_owner",
            "canonical_ref",
            "digest",
            "evidence_refs",
            "freshness",
            "qualified_symbol",
            "metadata",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown participant fields: {', '.join(unknown)}")
        if data.get("schema_version") != RELATIONAL_PARTICIPANT_VERSION:
            raise ValueError("unsupported participant schema_version")
        return cls(
            participant_id=_required_text(data.get("participant_id"), "participant_id"),
            participant_type=data.get("participant_type"),
            role=data.get("role"),
            truth_class=data.get("truth_class"),
            canonical_owner=data.get("canonical_owner"),
            canonical_ref=data.get("canonical_ref"),
            digest=data.get("digest"),
            evidence_refs=_string_tuple(data.get("evidence_refs", []), "evidence_refs"),
            freshness=data.get("freshness"),
            qualified_symbol=data.get("qualified_symbol"),
            metadata=_mapping(data.get("metadata", {}), "metadata"),
        )


@dataclass(frozen=True)
class TypedRelation:
    relation_id: str
    relation_type: RelationType
    source_participant_id: str
    target_participant_id: str
    truth_class: TruthClass
    evidence_refs: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "relation_type", _enum(self.relation_type, RelationType, "relation_type")
        )
        object.__setattr__(
            self,
            "source_participant_id",
            _required_text(self.source_participant_id, "source_participant_id"),
        )
        object.__setattr__(
            self,
            "target_participant_id",
            _required_text(self.target_participant_id, "target_participant_id"),
        )
        object.__setattr__(
            self, "truth_class", _enum(self.truth_class, TruthClass, "truth_class")
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(self, "metadata", _mapping(self.metadata, "metadata"))
        if self.relation_id != self.expected_id():
            raise ValueError("relation_id does not match canonical relation identity")
        if self.truth_class in _EXACT_TRUTH_CLASSES and not self.evidence_refs:
            raise ValueError("exact relations require evidence_refs")

    @classmethod
    def create(
        cls,
        *,
        relation_type: RelationType | str,
        source_participant_id: str,
        target_participant_id: str,
        truth_class: TruthClass | str,
        evidence_refs: Sequence[str] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "TypedRelation":
        relation_type_value = _enum(relation_type, RelationType, "relation_type")
        truth_value = _enum(truth_class, TruthClass, "truth_class")
        source_value = _required_text(source_participant_id, "source_participant_id")
        target_value = _required_text(target_participant_id, "target_participant_id")
        refs = tuple(sorted(set(evidence_refs)))
        identity = {
            "relation_type": relation_type_value.value,
            "source_participant_id": source_value,
            "target_participant_id": target_value,
            "truth_class": truth_value.value,
            "evidence_refs": refs,
        }
        return cls(
            relation_id=stable_id("rel", identity),
            relation_type=relation_type_value,
            source_participant_id=source_value,
            target_participant_id=target_value,
            truth_class=truth_value,
            evidence_refs=refs,
            metadata=dict(metadata or {}),
        )

    def expected_id(self) -> str:
        return stable_id(
            "rel",
            {
                "relation_type": self.relation_type.value,
                "source_participant_id": self.source_participant_id,
                "target_participant_id": self.target_participant_id,
                "truth_class": self.truth_class.value,
                "evidence_refs": self.evidence_refs,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONAL_RELATION_VERSION,
            "relation_id": self.relation_id,
            "relation_type": self.relation_type.value,
            "source_participant_id": self.source_participant_id,
            "target_participant_id": self.target_participant_id,
            "truth_class": self.truth_class.value,
            "evidence_refs": list(self.evidence_refs),
            "metadata": dict(sorted(self.metadata.items())),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TypedRelation":
        data = _mapping(value, "relation")
        allowed = {
            "schema_version",
            "relation_id",
            "relation_type",
            "source_participant_id",
            "target_participant_id",
            "truth_class",
            "evidence_refs",
            "metadata",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown relation fields: {', '.join(unknown)}")
        if data.get("schema_version") != RELATIONAL_RELATION_VERSION:
            raise ValueError("unsupported relation schema_version")
        return cls(
            relation_id=_required_text(data.get("relation_id"), "relation_id"),
            relation_type=data.get("relation_type"),
            source_participant_id=data.get("source_participant_id"),
            target_participant_id=data.get("target_participant_id"),
            truth_class=data.get("truth_class"),
            evidence_refs=_string_tuple(data.get("evidence_refs", []), "evidence_refs"),
            metadata=_mapping(data.get("metadata", {}), "metadata"),
        )


@dataclass(frozen=True)
class RoleBinding:
    participant_id: str
    role: str
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "participant_id", _required_text(self.participant_id, "participant_id")
        )
        object.__setattr__(self, "role", _required_text(self.role, "role"))
        object.__setattr__(self, "required", _strict_bool(self.required, "required"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "participant_id": self.participant_id,
            "role": self.role,
            "required": self.required,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RoleBinding":
        data = _mapping(value, "role_binding")
        if set(data) - {"participant_id", "role", "required"}:
            raise ValueError("unknown role binding fields")
        return cls(
            participant_id=data.get("participant_id"),
            role=data.get("role"),
            required=data.get("required", True),
        )


@dataclass(frozen=True)
class ProofObligation:
    obligation_id: str
    claim: str
    status: ProofStatus
    required_evidence: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    verifier_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", _required_text(self.claim, "claim"))
        object.__setattr__(
            self, "status", _enum(self.status, ProofStatus, "proof status")
        )
        object.__setattr__(
            self,
            "required_evidence",
            _string_tuple(
                self.required_evidence, "required_evidence", allow_empty=False
            ),
        )
        object.__setattr__(
            self,
            "evidence_refs",
            _string_tuple(self.evidence_refs, "evidence_refs"),
        )
        object.__setattr__(
            self,
            "verifier_ids",
            _string_tuple(self.verifier_ids, "verifier_ids"),
        )
        if self.obligation_id != self.expected_id():
            raise ValueError("obligation_id does not match canonical proof identity")
        if self.status is ProofStatus.SATISFIED and not self.evidence_refs:
            raise ValueError("satisfied proof obligations require evidence_refs")

    @classmethod
    def create(
        cls,
        *,
        claim: str,
        status: ProofStatus | str,
        required_evidence: Sequence[str],
        evidence_refs: Sequence[str] = (),
        verifier_ids: Sequence[str] = (),
    ) -> "ProofObligation":
        claim_value = _required_text(claim, "claim")
        requirements = tuple(sorted(set(required_evidence)))
        identity = {"claim": claim_value, "required_evidence": requirements}
        return cls(
            obligation_id=stable_id("proof", identity),
            claim=claim_value,
            status=status,
            required_evidence=requirements,
            evidence_refs=tuple(evidence_refs),
            verifier_ids=tuple(verifier_ids),
        )

    def expected_id(self) -> str:
        return stable_id(
            "proof",
            {"claim": self.claim, "required_evidence": self.required_evidence},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": PROOF_OBLIGATION_VERSION,
            "obligation_id": self.obligation_id,
            "claim": self.claim,
            "status": self.status.value,
            "required_evidence": list(self.required_evidence),
            "evidence_refs": list(self.evidence_refs),
            "verifier_ids": list(self.verifier_ids),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProofObligation":
        data = _mapping(value, "proof_obligation")
        allowed = {
            "schema_version",
            "obligation_id",
            "claim",
            "status",
            "required_evidence",
            "evidence_refs",
            "verifier_ids",
        }
        if set(data) - allowed:
            raise ValueError("unknown proof obligation fields")
        if data.get("schema_version") != PROOF_OBLIGATION_VERSION:
            raise ValueError("unsupported proof obligation schema_version")
        return cls(
            obligation_id=data.get("obligation_id"),
            claim=data.get("claim"),
            status=data.get("status"),
            required_evidence=_string_tuple(
                data.get("required_evidence", []),
                "required_evidence",
                allow_empty=False,
            ),
            evidence_refs=_string_tuple(data.get("evidence_refs", []), "evidence_refs"),
            verifier_ids=_string_tuple(data.get("verifier_ids", []), "verifier_ids"),
        )


@dataclass(frozen=True)
class RelationalBoundary:
    included_participant_ids: tuple[str, ...]
    omitted_relation_count: int
    omitted_reasons: dict[str, int]
    unresolved_relations: tuple[str, ...]
    budget_truncated: bool
    all_relation_endpoints_present: bool

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "included_participant_ids",
            _string_tuple(
                self.included_participant_ids,
                "included_participant_ids",
            ),
        )
        object.__setattr__(
            self,
            "omitted_relation_count",
            _strict_nonnegative_int(
                self.omitted_relation_count, "omitted_relation_count"
            ),
        )
        if not isinstance(self.omitted_reasons, Mapping):
            raise ValueError("omitted_reasons must be an object")
        normalized_reasons: dict[str, int] = {}
        for key, count in self.omitted_reasons.items():
            name = _required_text(key, "omitted_reasons key")
            normalized_reasons[name] = _strict_nonnegative_int(
                count, f"omitted_reasons.{name}"
            )
        if sum(normalized_reasons.values()) != self.omitted_relation_count:
            raise ValueError("omitted reason counts must equal omitted_relation_count")
        object.__setattr__(
            self, "omitted_reasons", dict(sorted(normalized_reasons.items()))
        )
        object.__setattr__(
            self,
            "unresolved_relations",
            _string_tuple(self.unresolved_relations, "unresolved_relations"),
        )
        object.__setattr__(
            self,
            "budget_truncated",
            _strict_bool(self.budget_truncated, "budget_truncated"),
        )
        object.__setattr__(
            self,
            "all_relation_endpoints_present",
            _strict_bool(
                self.all_relation_endpoints_present,
                "all_relation_endpoints_present",
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RELATIONAL_BOUNDARY_VERSION,
            "included_participant_ids": list(self.included_participant_ids),
            "omitted_relation_count": self.omitted_relation_count,
            "omitted_reasons": dict(self.omitted_reasons),
            "unresolved_relations": list(self.unresolved_relations),
            "budget_truncated": self.budget_truncated,
            "all_relation_endpoints_present": self.all_relation_endpoints_present,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationalBoundary":
        data = _mapping(value, "boundary")
        allowed = {
            "schema_version",
            "included_participant_ids",
            "omitted_relation_count",
            "omitted_reasons",
            "unresolved_relations",
            "budget_truncated",
            "all_relation_endpoints_present",
        }
        if set(data) - allowed:
            raise ValueError("unknown relational boundary fields")
        if data.get("schema_version") != RELATIONAL_BOUNDARY_VERSION:
            raise ValueError("unsupported relational boundary schema_version")
        return cls(
            included_participant_ids=_string_tuple(
                data.get("included_participant_ids", []),
                "included_participant_ids",
            ),
            omitted_relation_count=data.get("omitted_relation_count"),
            omitted_reasons=_mapping(data.get("omitted_reasons", {}), "omitted_reasons"),
            unresolved_relations=_string_tuple(
                data.get("unresolved_relations", []),
                "unresolved_relations",
            ),
            budget_truncated=data.get("budget_truncated"),
            all_relation_endpoints_present=data.get(
                "all_relation_endpoints_present"
            ),
        )


@dataclass(frozen=True)
class RelationalGroup:
    group_id: str
    group_kind: GroupKind
    purpose: str
    role_bindings: tuple[RoleBinding, ...]
    relations: tuple[TypedRelation, ...]
    predicates: tuple[str, ...]
    temporal_conditions: tuple[str, ...]
    authority_constraints: tuple[str, ...]
    proof_obligations: tuple[ProofObligation, ...]
    boundary: RelationalBoundary
    canonical_owner_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "group_kind", _enum(self.group_kind, GroupKind, "group_kind")
        )
        object.__setattr__(self, "purpose", _required_text(self.purpose, "purpose"))
        if type(self.role_bindings) is not tuple or not all(
            isinstance(item, RoleBinding) for item in self.role_bindings
        ):
            raise ValueError("role_bindings must be a tuple of RoleBinding")
        object.__setattr__(
            self,
            "role_bindings",
            tuple(sorted(self.role_bindings, key=lambda item: (item.role, item.participant_id))),
        )
        if type(self.relations) is not tuple or not all(
            isinstance(item, TypedRelation) for item in self.relations
        ):
            raise ValueError("relations must be a tuple of TypedRelation")
        object.__setattr__(
            self,
            "relations",
            tuple(sorted(self.relations, key=lambda item: item.relation_id)),
        )
        if len({item.relation_id for item in self.relations}) != len(self.relations):
            raise ValueError("relations must not contain duplicate IDs")
        for name in ("predicates", "temporal_conditions", "authority_constraints"):
            object.__setattr__(
                self,
                name,
                _string_tuple(getattr(self, name), name),
            )
        if type(self.proof_obligations) is not tuple or not all(
            isinstance(item, ProofObligation) for item in self.proof_obligations
        ):
            raise ValueError("proof_obligations must be a tuple of ProofObligation")
        object.__setattr__(
            self,
            "proof_obligations",
            tuple(sorted(self.proof_obligations, key=lambda item: item.obligation_id)),
        )
        if len({item.obligation_id for item in self.proof_obligations}) != len(
            self.proof_obligations
        ):
            raise ValueError("proof obligations must not contain duplicate IDs")
        if not isinstance(self.boundary, RelationalBoundary):
            raise ValueError("boundary must be a RelationalBoundary")
        object.__setattr__(
            self,
            "canonical_owner_refs",
            _string_tuple(
                self.canonical_owner_refs,
                "canonical_owner_refs",
                allow_empty=False,
            ),
        )
        if self.group_id != self.expected_id():
            raise ValueError("group_id does not match canonical group identity")

    @classmethod
    def create(
        cls,
        *,
        group_kind: GroupKind | str,
        purpose: str,
        role_bindings: Sequence[RoleBinding],
        relations: Sequence[TypedRelation],
        predicates: Sequence[str] = (),
        temporal_conditions: Sequence[str] = (),
        authority_constraints: Sequence[str] = (),
        proof_obligations: Sequence[ProofObligation] = (),
        boundary: RelationalBoundary,
        canonical_owner_refs: Sequence[str],
    ) -> "RelationalGroup":
        group_kind_value = _enum(group_kind, GroupKind, "group_kind")
        purpose_value = _required_text(purpose, "purpose")
        role_tuple = tuple(
            sorted(role_bindings, key=lambda item: (item.role, item.participant_id))
        )
        relation_tuple = tuple(
            sorted(relations, key=lambda item: item.relation_id)
        )
        proof_tuple = tuple(
            sorted(proof_obligations, key=lambda item: item.obligation_id)
        )
        identity = {
            "group_kind": group_kind_value.value,
            "purpose": purpose_value,
            "role_bindings": [item.to_dict() for item in role_tuple],
            "relation_ids": [item.relation_id for item in relation_tuple],
            "proof_obligation_ids": [item.obligation_id for item in proof_tuple],
            "boundary": boundary.to_dict(),
        }
        return cls(
            group_id=stable_id("relgroup", identity),
            group_kind=group_kind_value,
            purpose=purpose_value,
            role_bindings=role_tuple,
            relations=relation_tuple,
            predicates=tuple(predicates),
            temporal_conditions=tuple(temporal_conditions),
            authority_constraints=tuple(authority_constraints),
            proof_obligations=proof_tuple,
            boundary=boundary,
            canonical_owner_refs=tuple(canonical_owner_refs),
        )

    def expected_id(self) -> str:
        return stable_id(
            "relgroup",
            {
                "group_kind": self.group_kind.value,
                "purpose": self.purpose,
                "role_bindings": [item.to_dict() for item in self.role_bindings],
                "relation_ids": [item.relation_id for item in self.relations],
                "proof_obligation_ids": [
                    item.obligation_id for item in self.proof_obligations
                ],
                "boundary": self.boundary.to_dict(),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": RELATIONAL_GROUP_VERSION,
            "group_id": self.group_id,
            "group_kind": self.group_kind.value,
            "purpose": self.purpose,
            "role_bindings": [item.to_dict() for item in self.role_bindings],
            "relations": [item.to_dict() for item in self.relations],
            "predicates": list(self.predicates),
            "temporal_conditions": list(self.temporal_conditions),
            "authority_constraints": list(self.authority_constraints),
            "proof_obligations": [
                item.to_dict() for item in self.proof_obligations
            ],
            "boundary": self.boundary.to_dict(),
            "canonical_owner_refs": list(self.canonical_owner_refs),
        }
        return {**body, "group_digest": stable_digest(body, digest_size=20)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationalGroup":
        data = _mapping(value, "group")
        allowed = {
            "schema_version",
            "group_id",
            "group_kind",
            "purpose",
            "role_bindings",
            "relations",
            "predicates",
            "temporal_conditions",
            "authority_constraints",
            "proof_obligations",
            "boundary",
            "canonical_owner_refs",
            "group_digest",
        }
        if set(data) - allowed:
            raise ValueError("unknown relational group fields")
        if data.get("schema_version") != RELATIONAL_GROUP_VERSION:
            raise ValueError("unsupported relational group schema_version")
        group = cls(
            group_id=data.get("group_id"),
            group_kind=data.get("group_kind"),
            purpose=data.get("purpose"),
            role_bindings=tuple(
                RoleBinding.from_dict(item)
                for item in data.get("role_bindings", [])
            ),
            relations=tuple(
                TypedRelation.from_dict(item) for item in data.get("relations", [])
            ),
            predicates=_string_tuple(data.get("predicates", []), "predicates"),
            temporal_conditions=_string_tuple(
                data.get("temporal_conditions", []), "temporal_conditions"
            ),
            authority_constraints=_string_tuple(
                data.get("authority_constraints", []), "authority_constraints"
            ),
            proof_obligations=tuple(
                ProofObligation.from_dict(item)
                for item in data.get("proof_obligations", [])
            ),
            boundary=RelationalBoundary.from_dict(data.get("boundary", {})),
            canonical_owner_refs=_string_tuple(
                data.get("canonical_owner_refs", []),
                "canonical_owner_refs",
                allow_empty=False,
            ),
        )
        expected_digest = group.to_dict()["group_digest"]
        if data.get("group_digest") != expected_digest:
            raise ValueError("group_digest does not match canonical group")
        return group


@dataclass(frozen=True)
class RelationalSynthesisCapsule:
    capsule_id: str
    objective: str
    objective_digest: str
    intent_packet: PolysyntheticIntentPacket
    repository_identity: dict[str, Any]
    source_packet_id: str
    source_packet_digest: str
    participants: tuple[RelationalParticipant, ...]
    groups: tuple[RelationalGroup, ...]
    source_slices: tuple[dict[str, Any], ...]
    tests: tuple[str, ...]
    active_arena: str
    boundary: RelationalBoundary
    shadow_mode: bool = True
    safe_to_patch: bool = False
    production_mutation: bool = False
    human_review_required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "objective", _required_text(self.objective, "objective")
        )
        object.__setattr__(
            self,
            "objective_digest",
            _required_text(self.objective_digest, "objective_digest"),
        )
        if not isinstance(self.intent_packet, PolysyntheticIntentPacket):
            raise ValueError("intent_packet must be a PolysyntheticIntentPacket")
        if self.intent_packet.objective_digest != self.objective_digest:
            raise ValueError("intent packet objective digest does not match capsule")
        object.__setattr__(
            self,
            "repository_identity",
            _mapping(self.repository_identity, "repository_identity"),
        )
        for key in (
            "repo_head",
            "atomic_inventory_digest",
            "capability_graph_digest",
            "capability_path_digest",
            "evidence_packet_version",
        ):
            _required_text(self.repository_identity.get(key), f"repository_identity.{key}")
        object.__setattr__(
            self,
            "source_packet_id",
            _required_text(self.source_packet_id, "source_packet_id"),
        )
        object.__setattr__(
            self,
            "source_packet_digest",
            _required_text(self.source_packet_digest, "source_packet_digest"),
        )
        if type(self.participants) is not tuple or not all(
            isinstance(item, RelationalParticipant) for item in self.participants
        ):
            raise ValueError("participants must be a tuple of RelationalParticipant")
        object.__setattr__(
            self,
            "participants",
            tuple(sorted(self.participants, key=lambda item: item.participant_id)),
        )
        participant_ids = [item.participant_id for item in self.participants]
        if not participant_ids or len(participant_ids) != len(set(participant_ids)):
            raise ValueError("participants must be nonempty and contain unique IDs")
        if type(self.groups) is not tuple or not all(
            isinstance(item, RelationalGroup) for item in self.groups
        ):
            raise ValueError("groups must be a tuple of RelationalGroup")
        object.__setattr__(
            self,
            "groups",
            tuple(sorted(self.groups, key=lambda item: item.group_id)),
        )
        group_ids = [item.group_id for item in self.groups]
        if not group_ids or len(group_ids) != len(set(group_ids)):
            raise ValueError("groups must be nonempty and contain unique IDs")
        participant_id_set = set(participant_ids)
        for group in self.groups:
            for binding in group.role_bindings:
                if binding.participant_id not in participant_id_set:
                    raise ValueError("role binding references unknown participant")
            group_boundary_ids = set(group.boundary.included_participant_ids)
            for relation in group.relations:
                if (
                    relation.source_participant_id not in participant_id_set
                    or relation.target_participant_id not in participant_id_set
                ):
                    raise ValueError("relation endpoint references unknown participant")
                if (
                    relation.source_participant_id not in group_boundary_ids
                    or relation.target_participant_id not in group_boundary_ids
                ):
                    raise ValueError("relation endpoint not in group boundary")
            if not group_boundary_ids.issubset(participant_id_set):
                raise ValueError("group boundary references unknown participant")
            if group.boundary.all_relation_endpoints_present is not True:
                raise ValueError("group boundary must declare all_relation_endpoints_present as True")
        if not set(self.boundary.included_participant_ids).issubset(
            participant_id_set
        ):
            raise ValueError("capsule boundary references unknown participant")
        if self.boundary.all_relation_endpoints_present is not True:
            raise ValueError("capsule boundary must declare all_relation_endpoints_present as True")
        normalized_slices: list[dict[str, Any]] = []
        seen_slice_ids: set[str] = set()
        for item in self.source_slices:
            data = _mapping(item, "source_slices[]")
            node_id = _required_text(data.get("node_id"), "source_slices[].node_id")
            if node_id in seen_slice_ids:
                raise ValueError("source_slices must not contain duplicate node IDs")
            seen_slice_ids.add(node_id)
            for field_name in (
                "file_path",
                "qualified_symbol",
                "source_hash",
                "file_source_hash",
            ):
                _required_text(data.get(field_name), f"source_slices[].{field_name}")
            line_start = data.get("line_start")
            line_end = data.get("line_end")
            if (
                type(line_start) is not int
                or type(line_end) is not int
                or line_start < 1
                or line_end < line_start
            ):
                raise ValueError("source_slices[] line range is invalid")
            normalized_slices.append(data)
        object.__setattr__(
            self,
            "source_slices",
            tuple(
                sorted(
                    normalized_slices,
                    key=lambda item: (
                        str(item.get("file_path") or ""),
                        int(item.get("line_start") or 0),
                        str(item.get("qualified_symbol") or ""),
                    ),
                )
            ),
        )
        object.__setattr__(self, "tests", _string_tuple(self.tests, "tests"))
        object.__setattr__(
            self, "active_arena", _required_text(self.active_arena, "active_arena")
        )
        if not isinstance(self.boundary, RelationalBoundary):
            raise ValueError("boundary must be a RelationalBoundary")
        for field_name, expected in (
            ("shadow_mode", True),
            ("safe_to_patch", False),
            ("production_mutation", False),
            ("human_review_required", True),
        ):
            value = _strict_bool(getattr(self, field_name), field_name)
            if value is not expected:
                raise ValueError(f"{field_name} crossed the Phase 1 authority boundary")
        if self.capsule_id != self.expected_id():
            raise ValueError("capsule_id does not match canonical capsule identity")

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        intent_packet: PolysyntheticIntentPacket,
        repository_identity: Mapping[str, Any],
        source_packet_id: str,
        source_packet_digest: str,
        participants: Sequence[RelationalParticipant],
        groups: Sequence[RelationalGroup],
        source_slices: Sequence[Mapping[str, Any]],
        tests: Sequence[str],
        active_arena: str,
        boundary: RelationalBoundary,
    ) -> "RelationalSynthesisCapsule":
        participant_tuple = tuple(
            sorted(participants, key=lambda item: item.participant_id)
        )
        group_tuple = tuple(sorted(groups, key=lambda item: item.group_id))
        identity = {
            "objective_digest": intent_packet.objective_digest,
            "intent_packet_digest": intent_packet.digest(),
            "repository_identity": dict(repository_identity),
            "source_packet_id": source_packet_id,
            "source_packet_digest": source_packet_digest,
            "participant_ids": [item.participant_id for item in participant_tuple],
            "group_ids": [item.group_id for item in group_tuple],
        }
        return cls(
            capsule_id=stable_id("relcapsule", identity),
            objective=objective,
            objective_digest=intent_packet.objective_digest,
            intent_packet=intent_packet,
            repository_identity=dict(repository_identity),
            source_packet_id=source_packet_id,
            source_packet_digest=source_packet_digest,
            participants=participant_tuple,
            groups=group_tuple,
            source_slices=tuple(dict(item) for item in source_slices),
            tests=tuple(tests),
            active_arena=active_arena,
            boundary=boundary,
        )

    def expected_id(self) -> str:
        return stable_id(
            "relcapsule",
            {
                "objective_digest": self.objective_digest,
                "intent_packet_digest": self.intent_packet.digest(),
                "repository_identity": self.repository_identity,
                "source_packet_id": self.source_packet_id,
                "source_packet_digest": self.source_packet_digest,
                "participant_ids": [
                    item.participant_id for item in self.participants
                ],
                "group_ids": [item.group_id for item in self.groups],
            },
        )

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema_version": RELATIONAL_CAPSULE_VERSION,
            "capsule_id": self.capsule_id,
            "objective": self.objective,
            "objective_digest": self.objective_digest,
            "intent_packet": self.intent_packet.canonical_dict(),
            "intent_packet_digest": self.intent_packet.digest(),
            "repository_identity": dict(sorted(self.repository_identity.items())),
            "source_packet_id": self.source_packet_id,
            "source_packet_digest": self.source_packet_digest,
            "participants": [item.to_dict() for item in self.participants],
            "groups": [item.to_dict() for item in self.groups],
            "source_slices": [dict(item) for item in self.source_slices],
            "tests": list(self.tests),
            "active_arena": self.active_arena,
            "boundary": self.boundary.to_dict(),
            "shadow_mode": self.shadow_mode,
            "safe_to_patch": self.safe_to_patch,
            "production_mutation": self.production_mutation,
            "automatic_fix": False,
            "automatic_commit": False,
            "automatic_push": False,
            "automatic_pull_request": False,
            "automatic_merge": False,
            "human_review_required": self.human_review_required,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        return {**body, "capsule_digest": stable_digest(body, digest_size=20)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelationalSynthesisCapsule":
        data = _mapping(value, "capsule")
        allowed = {
            "schema_version",
            "capsule_id",
            "objective",
            "objective_digest",
            "intent_packet",
            "intent_packet_digest",
            "repository_identity",
            "source_packet_id",
            "source_packet_digest",
            "participants",
            "groups",
            "source_slices",
            "tests",
            "active_arena",
            "boundary",
            "shadow_mode",
            "safe_to_patch",
            "production_mutation",
            "automatic_fix",
            "automatic_commit",
            "automatic_push",
            "automatic_pull_request",
            "automatic_merge",
            "human_review_required",
            "patch_authority",
            "vsa_patch_authority",
            "capsule_digest",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise ValueError(f"unknown capsule fields: {', '.join(unknown)}")
        if data.get("schema_version") != RELATIONAL_CAPSULE_VERSION:
            raise ValueError("unsupported capsule schema_version")
        for field_name, expected in (
            ("automatic_fix", False),
            ("automatic_commit", False),
            ("automatic_push", False),
            ("automatic_pull_request", False),
            ("automatic_merge", False),
            ("vsa_patch_authority", False),
        ):
            if data.get(field_name) is not expected:
                raise ValueError(f"{field_name} crossed the authority boundary")
        if data.get("patch_authority") != PATCH_AUTHORITY:
            raise ValueError("unsupported patch_authority")
        intent_data = _mapping(data.get("intent_packet", {}), "intent_packet")
        if intent_data.get("schema_version") is None:
            raise ValueError("intent packet schema_version is required")
        intent = PolysyntheticIntentPacket.from_slots(
            _mapping(intent_data.get("slots", {}), "intent_packet.slots"),
            adjuncts=_mapping(intent_data.get("adjuncts", {}), "intent_packet.adjuncts"),
            objective=data.get("objective"),
        )
        if intent_data.get("objective_digest") != intent.objective_digest:
            raise ValueError("intent packet objective digest mismatch")
        if data.get("intent_packet_digest") != intent.digest():
            raise ValueError("intent_packet_digest mismatch")
        if intent_data != intent.canonical_dict():
            raise ValueError("intent_packet representation must match canonical_dict()")
        capsule = cls(
            capsule_id=data.get("capsule_id"),
            objective=data.get("objective"),
            objective_digest=data.get("objective_digest"),
            intent_packet=intent,
            repository_identity=_mapping(
                data.get("repository_identity", {}), "repository_identity"
            ),
            source_packet_id=data.get("source_packet_id"),
            source_packet_digest=data.get("source_packet_digest"),
            participants=tuple(
                RelationalParticipant.from_dict(item)
                for item in data.get("participants", [])
            ),
            groups=tuple(
                RelationalGroup.from_dict(item) for item in data.get("groups", [])
            ),
            source_slices=tuple(
                _mapping(item, "source_slices[]")
                for item in data.get("source_slices", [])
            ),
            tests=_string_tuple(data.get("tests", []), "tests"),
            active_arena=data.get("active_arena"),
            boundary=RelationalBoundary.from_dict(data.get("boundary", {})),
            shadow_mode=data.get("shadow_mode"),
            safe_to_patch=data.get("safe_to_patch"),
            production_mutation=data.get("production_mutation"),
            human_review_required=data.get("human_review_required"),
        )
        if data.get("capsule_digest") != capsule.to_dict()["capsule_digest"]:
            raise ValueError("capsule_digest does not match canonical capsule")
        return capsule


class RelationalSynthesisShadowCompiler:
    """Compile exact Evidence Spine packets into non-authoritative relational views."""

    def compile(
        self,
        evidence_packet: Mapping[str, Any],
        *,
        intent_packet: PolysyntheticIntentPacket,
        expected_repo_head: str,
        expected_packet_digest: str,
        expected_inventory_digest: str,
        active_arena: str | None = None,
    ) -> RelationalSynthesisCapsule:
        packet = _validate_evidence_packet(
            evidence_packet,
            intent_packet=intent_packet,
            expected_repo_head=expected_repo_head,
            expected_packet_digest=expected_packet_digest,
            expected_inventory_digest=expected_inventory_digest,
        )
        source_packet_id = packet["packet_id"]
        source_packet_digest = packet["packet_digest"]
        packet_ref = f"evidence_packet:{source_packet_id}:{source_packet_digest}"
        source_slices = _source_slices(packet)
        selected = _selected_atomic_functions(packet)
        slice_by_node = {item["node_id"]: item for item in source_slices}
        selected_node_ids = {
            _required_text(item.get("node_id"), "selected node_id")
            for item in selected
        }
        if set(slice_by_node) != selected_node_ids:
            raise ValueError(
                "source_slices must match selected atomic functions exactly"
            )

        participants: dict[str, RelationalParticipant] = {}
        node_to_participant: dict[str, str] = {}

        packet_participant = RelationalParticipant.create(
            participant_type=ParticipantType.PACKET,
            role="evidence_source",
            truth_class=TruthClass.EXACT_MANIFEST,
            canonical_owner="AuraEmergentEvidenceSpine",
            canonical_ref=source_packet_id,
            digest=source_packet_digest,
            evidence_refs=(packet_ref,),
            freshness=Freshness.CURRENT,
            metadata={"packet_version": packet["version"]},
        )
        participants[packet_participant.participant_id] = packet_participant

        for record in sorted(
            selected,
            key=lambda item: (
                str(item.get("file_path") or ""),
                int(item.get("line_start") or 0),
                str(item.get("node_id") or ""),
            ),
        ):
            node_id = _required_text(record.get("node_id"), "selected node_id")
            span = slice_by_node.get(node_id)
            if span is None:
                raise ValueError(f"selected atomic function lacks exact source slice: {node_id}")
            for field_name in (
                "file_path",
                "symbol",
                "kind",
                "line_start",
                "line_end",
                "source_hash",
            ):
                if record.get(field_name) != span.get(field_name):
                    raise ValueError(
                        f"selected atomic identity disagrees with source slice: {node_id}"
                    )
            qualified_symbol = _required_text(
                span.get("qualified_symbol"), "source slice qualified_symbol"
            )
            participant = RelationalParticipant.create(
                participant_type=ParticipantType.ATOMIC_SYMBOL,
                role="focal_operation",
                truth_class=(
                    TruthClass.EXACT_TEST
                    if _is_test_path(span["file_path"])
                    else TruthClass.EXACT_SOURCE
                ),
                canonical_owner="CodeTopoAnchor",
                canonical_ref=_identity_ref(span["file_path"], qualified_symbol),
                digest=span["source_hash"],
                evidence_refs=(
                    packet_ref,
                    f"source:{span['file_path']}:{span['line_start']}-{span['line_end']}:{span['source_hash']}",
                ),
                freshness=Freshness.CURRENT,
                qualified_symbol=qualified_symbol,
                metadata={
                    "node_id": node_id,
                    "file_path": span["file_path"],
                    "line_start": span["line_start"],
                    "line_end": span["line_end"],
                    "file_source_hash": span.get("file_source_hash", ""),
                    "kind": span.get("kind", record.get("kind", "")),
                },
            )
            if participant.participant_id in participants:
                raise ValueError("duplicate participant identity in exact source packet")
            participants[participant.participant_id] = participant
            node_to_participant[node_id] = participant.participant_id

        authority_participants = _authority_participants(packet, packet_ref)
        for participant in authority_participants:
            participants[participant.participant_id] = participant

        exact_relations = _relations_from_packet(
            packet, node_to_participant=node_to_participant, packet_ref=packet_ref
        )
        closure_group = _closure_group(
            tuple(participants.values()),
            exact_relations,
            node_to_participant=node_to_participant,
            packet_ref=packet_ref,
        )

        test_group, test_participants = _test_group(
            packet,
            tuple(participants.values()),
            exact_relations,
            node_to_participant=node_to_participant,
            packet_ref=packet_ref,
        )
        for participant in test_participants:
            if participant.participant_id not in participants:
                participants[participant.participant_id] = participant

        scope_group, scope_participants = _input_scope_authority_group(
            tuple(participants.values()),
            exact_relations,
            authority_participants=authority_participants,
            packet_ref=packet_ref,
        )
        for participant in scope_participants:
            if participant.participant_id not in participants:
                participants[participant.participant_id] = participant

        groups = (closure_group, test_group, scope_group)
        participant_ids = tuple(sorted(participants))
        unresolved = tuple(
            sorted(
                {
                    item
                    for group in groups
                    for item in group.boundary.unresolved_relations
                }
            )
        )
        omitted_reasons: dict[str, int] = {}
        for group in groups:
            for reason, count in group.boundary.omitted_reasons.items():
                omitted_reasons[reason] = omitted_reasons.get(reason, 0) + count
        boundary = RelationalBoundary(
            included_participant_ids=participant_ids,
            omitted_relation_count=sum(omitted_reasons.values()),
            omitted_reasons=omitted_reasons,
            unresolved_relations=unresolved,
            budget_truncated=any(
                group.boundary.budget_truncated for group in groups
            ),
            all_relation_endpoints_present=True,
        )
        repository_identity = {
            "repo_head": packet["repo_head"],
            "atomic_inventory_digest": packet["atomic_inventory"]["inventory_digest"],
            "capability_graph_digest": packet["capability_connectome"]["graph_digest"],
            "capability_path_digest": str(
                packet["capability_connectome"].get("path", {}).get(
                    "capability_path_digest"
                )
                or packet["capability_connectome"].get("path", {}).get("path_digest")
                or ""
            ),
            "evidence_packet_version": packet["version"],
        }
        if not repository_identity["capability_path_digest"]:
            repository_identity["capability_path_digest"] = stable_digest(
                packet["capability_connectome"].get("path", {}), digest_size=20
            )
        return RelationalSynthesisCapsule.create(
            objective=packet["objective"],
            intent_packet=intent_packet,
            repository_identity=repository_identity,
            source_packet_id=source_packet_id,
            source_packet_digest=source_packet_digest,
            participants=tuple(participants.values()),
            groups=groups,
            source_slices=source_slices,
            tests=tuple(packet.get("tests", [])),
            active_arena=active_arena or packet["target_arena"],
            boundary=boundary,
        )


def compile_relational_shadow_capsule(
    evidence_packet: Mapping[str, Any],
    *,
    intent_packet: PolysyntheticIntentPacket,
    expected_repo_head: str,
    expected_packet_digest: str,
    expected_inventory_digest: str,
    active_arena: str | None = None,
) -> dict[str, Any]:
    """Public JSON surface for the Phase 1 read-only shadow compiler."""

    return RelationalSynthesisShadowCompiler().compile(
        evidence_packet,
        intent_packet=intent_packet,
        expected_repo_head=expected_repo_head,
        expected_packet_digest=expected_packet_digest,
        expected_inventory_digest=expected_inventory_digest,
        active_arena=active_arena,
    ).to_dict()


def _validate_evidence_packet(
    value: Mapping[str, Any],
    *,
    intent_packet: PolysyntheticIntentPacket,
    expected_repo_head: str | None,
    expected_packet_digest: str | None,
    expected_inventory_digest: str | None,
) -> dict[str, Any]:
    packet = _mapping(value, "evidence_packet")
    if packet.get("ok") is not True:
        raise ValueError("evidence packet is not successful")
    if packet.get("grounding_ok") is not True:
        raise ValueError("evidence packet is not exactly grounded")
    if packet.get("approximate_only") is not False:
        raise ValueError("evidence packet must not be approximate_only")
    if packet.get("status") != "GROUNDED_ATOMIC_CLOSURE":
        raise ValueError("evidence packet must contain a grounded atomic closure")
    objective = _required_text(packet.get("objective"), "objective")
    expected_intent = PolysyntheticIntentPacket.from_slots(
        {name: filler for name, filler in intent_packet.slot_items()},
        adjuncts=intent_packet.adjuncts,
        objective=objective,
    )
    if expected_intent.objective_digest != intent_packet.objective_digest:
        raise ValueError("intent packet does not bind the evidence objective")
    for field_name in ("packet_id", "packet_digest", "repo_head", "version", "target_arena"):
        _required_text(packet.get(field_name), field_name)
    atomic_inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")
    _required_text(
        atomic_inventory.get("inventory_digest"), "atomic_inventory.inventory_digest"
    )
    capability = _mapping(
        packet.get("capability_connectome"), "capability_connectome"
    )
    _required_text(capability.get("graph_digest"), "capability_connectome.graph_digest")
    expected_repo_head = _required_text(expected_repo_head, "expected_repo_head")
    expected_packet_digest = _required_text(
        expected_packet_digest, "expected_packet_digest"
    )
    expected_inventory_digest = _required_text(
        expected_inventory_digest, "expected_inventory_digest"
    )
    if packet["repo_head"] != expected_repo_head:
        raise ValueError("stale evidence packet repository HEAD")
    if packet["packet_digest"] != expected_packet_digest:
        raise ValueError("evidence packet digest mismatch")
    if atomic_inventory["inventory_digest"] != expected_inventory_digest:
        raise ValueError("atomic inventory digest mismatch")
    authority = {
        "safe_to_patch": False,
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "vsa_patch_authority": False,
    }
    for field_name, expected in authority.items():
        if packet.get(field_name) is not expected:
            raise ValueError(
                f"evidence packet crossed authority boundary: {field_name}"
            )
    if packet.get("patch_authority") != PATCH_AUTHORITY:
        raise ValueError("evidence packet patch authority is unsupported")
    _selected_atomic_functions(packet)
    _source_slices(packet)
    tests = packet.get("tests", [])
    if not isinstance(tests, list) or any(type(item) is not str for item in tests):
        raise ValueError("evidence packet tests must be a list of paths")
    return packet


def _selected_atomic_functions(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    inventory = _mapping(packet.get("atomic_inventory"), "atomic_inventory")
    selected = inventory.get("selected_atomic_functions")
    if not isinstance(selected, list) or not selected:
        raise ValueError("evidence packet must select atomic functions")
    result: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for item in selected:
        record = _mapping(item, "selected_atomic_functions[]")
        node_id = _required_text(record.get("node_id"), "selected node_id")
        if node_id in node_ids:
            raise ValueError("selected atomic functions contain duplicate node IDs")
        node_ids.add(node_id)
        for field_name in ("file_path", "symbol", "source_hash"):
            _required_text(record.get(field_name), f"selected.{field_name}")
        result.append(record)
    return result


def _source_slices(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    slices = packet.get("source_slices")
    if not isinstance(slices, list) or not slices:
        raise ValueError("evidence packet must contain source_slices")
    result: list[dict[str, Any]] = []
    node_ids: set[str] = set()
    for item in slices:
        span = _mapping(item, "source_slices[]")
        node_id = _required_text(span.get("node_id"), "source slice node_id")
        if node_id in node_ids:
            raise ValueError("source_slices contain duplicate node IDs")
        node_ids.add(node_id)
        for field_name in (
            "file_path",
            "qualified_symbol",
            "source_hash",
            "file_source_hash",
        ):
            _required_text(span.get(field_name), f"source slice {field_name}")
        line_start = span.get("line_start")
        line_end = span.get("line_end")
        if (
            type(line_start) is not int
            or type(line_end) is not int
            or line_start < 1
            or line_end < line_start
        ):
            raise ValueError("source slice line range is invalid")
        result.append(span)
    return result


def _authority_participants(
    packet: Mapping[str, Any], packet_ref: str
) -> tuple[RelationalParticipant, ...]:
    fields = (
        ("patch_authority", "authority_guard"),
        ("human_review_required", "human_authorizer"),
        ("production_mutation", "mutation_boundary"),
        ("automatic_merge", "merge_boundary"),
    )
    participants: list[RelationalParticipant] = []
    for field_name, role in fields:
        participants.append(
            RelationalParticipant.create(
                participant_type=ParticipantType.AUTHORITY,
                role=role,
                truth_class=TruthClass.EXACT_MANIFEST,
                canonical_owner="AuraEmergentEvidenceSpine",
                canonical_ref=f"packet.authority.{field_name}",
                digest=stable_digest(
                    {"field": field_name, "value": packet.get(field_name)},
                    digest_size=20,
                ),
                evidence_refs=(packet_ref,),
                freshness=Freshness.CURRENT,
                metadata={"value": packet.get(field_name)},
            )
        )
    return tuple(participants)


def _relations_from_packet(
    packet: Mapping[str, Any],
    *,
    node_to_participant: Mapping[str, str],
    packet_ref: str,
) -> tuple[TypedRelation, ...]:
    edges = packet.get("dependency_edges")
    if not isinstance(edges, list):
        raise ValueError("dependency_edges must be a list")
    relations: list[TypedRelation] = []
    seen_edges: set[tuple[str, str, str]] = set()
    for item in sorted(
        edges,
        key=lambda edge: (
            str(edge.get("edge_type") or ""),
            str(edge.get("src_id") or ""),
            str(edge.get("dst_id") or ""),
            str(edge.get("evidence") or ""),
        ),
    ):
        edge = _mapping(item, "dependency_edges[]")
        src_id = _required_text(edge.get("src_id"), "dependency edge src_id")
        dst_id = _required_text(edge.get("dst_id"), "dependency edge dst_id")
        edge_type = _required_text(edge.get("edge_type"), "dependency edge edge_type").lower()
        if src_id not in node_to_participant or dst_id not in node_to_participant:
            raise ValueError(
                "dependency edge endpoint is absent from selected atomic functions"
            )
        key = (src_id, dst_id, edge_type)
        if key in seen_edges:
            raise ValueError("dependency_edges contain duplicate exact relations")
        seen_edges.add(key)
        relation_type = _EDGE_RELATIONS.get(edge_type)
        if relation_type is None:
            raise ValueError(f"unsupported exact dependency edge type: {edge_type}")
        evidence = _required_text(edge.get("evidence"), "dependency edge evidence")
        relations.append(
            TypedRelation.create(
                relation_type=relation_type,
                source_participant_id=node_to_participant[src_id],
                target_participant_id=node_to_participant[dst_id],
                truth_class=(
                    TruthClass.EXACT_TEST
                    if relation_type is RelationType.TESTS
                    else TruthClass.EXACT_SOURCE
                ),
                evidence_refs=(packet_ref, f"topology:{evidence}"),
                metadata={
                    "edge_type": edge_type,
                    "confidence": edge.get("confidence", 1.0),
                },
            )
        )
    return tuple(relations)


def _group_boundary(
    participant_ids: Sequence[str],
    *,
    unresolved: Sequence[str] = (),
    omitted_reasons: Mapping[str, int] | None = None,
    budget_truncated: bool = False,
) -> RelationalBoundary:
    reasons = dict(omitted_reasons or {})
    return RelationalBoundary(
        included_participant_ids=tuple(participant_ids),
        omitted_relation_count=sum(reasons.values()),
        omitted_reasons=reasons,
        unresolved_relations=tuple(unresolved),
        budget_truncated=budget_truncated,
        all_relation_endpoints_present=True,
    )


def _closure_group(
    participants: Sequence[RelationalParticipant],
    relations: Sequence[TypedRelation],
    *,
    node_to_participant: Mapping[str, str],
    packet_ref: str,
) -> RelationalGroup:
    del participants
    atomic_ids = tuple(sorted(node_to_participant.values()))
    role_bindings = tuple(
        RoleBinding(participant_id=item, role="inspectable_closure_endpoint")
        for item in atomic_ids
    )
    proof = ProofObligation.create(
        claim="Every emitted dependency relation has both exact endpoints and source evidence in the bounded packet.",
        status=ProofStatus.SATISFIED,
        required_evidence=("exact_source_slice", "topology_edge", "endpoint_membership"),
        evidence_refs=(packet_ref,),
        verifier_ids=("relational_endpoint_integrity",),
    )
    return RelationalGroup.create(
        group_kind=GroupKind.OBJECTIVE_GROUP,
        purpose="closure_packet_integrity",
        role_bindings=role_bindings,
        relations=relations,
        predicates=("all_relation_endpoints_present", "source_hashes_current"),
        authority_constraints=("relation_evidence_is_not_patch_authority",),
        proof_obligations=(proof,),
        boundary=_group_boundary(atomic_ids),
        canonical_owner_refs=(
            "AuraEmergentEvidenceSpine",
            "CodeTopoAnchor",
        ),
    )


def _test_group(
    packet: Mapping[str, Any],
    participants: Sequence[RelationalParticipant],
    relations: Sequence[TypedRelation],
    *,
    node_to_participant: Mapping[str, str],
    packet_ref: str,
) -> tuple[RelationalGroup, tuple[RelationalParticipant, ...]]:
    del node_to_participant
    exact_tests = tuple(
        participant
        for participant in participants
        if participant.participant_type is ParticipantType.ATOMIC_SYMBOL
        and participant.truth_class is TruthClass.EXACT_TEST
    )
    exact_test_paths = {
        str(item.metadata.get("file_path") or "") for item in exact_tests
    }
    unresolved_participants: list[RelationalParticipant] = []
    unresolved: list[str] = []
    proof_obligations: list[ProofObligation] = []

    for participant in exact_tests:
        unresolved.append(f"proved_invariant:{participant.participant_id}")
        proof_obligations.append(
            ProofObligation.create(
                claim=(
                    "Bind exact test callable "
                    f"{participant.qualified_symbol or participant.canonical_ref} "
                    "to the specific invariant it proves."
                ),
                status=ProofStatus.OPEN,
                required_evidence=(
                    "exact_test_callable",
                    "test_edge",
                    "proved_invariant",
                ),
                evidence_refs=participant.evidence_refs,
                verifier_ids=("relational_test_proof_integrity",),
            )
        )

    for path in sorted(set(packet.get("tests", []))):
        if path in exact_test_paths:
            continue
        participant = RelationalParticipant.create(
            participant_type=ParticipantType.TEST,
            role="unresolved_test_callable_owner",
            truth_class=TruthClass.UNRESOLVED,
            canonical_owner="AuraEmergentEvidenceSpine",
            canonical_ref=path,
            digest=None,
            evidence_refs=(packet_ref,),
            freshness=Freshness.UNRESOLVED,
            metadata={
                "known_test_file": True,
                "callable_owner_grounded": False,
            },
        )
        unresolved_participants.append(participant)
        unresolved.append(f"test_callable_owner:{path}")
        proof_obligations.append(
            ProofObligation.create(
                claim=f"Resolve the exact test callable and invariant owned by {path}.",
                status=ProofStatus.OPEN,
                required_evidence=(
                    "exact_test_callable",
                    "test_edge",
                    "proved_invariant",
                ),
                verifier_ids=("relational_test_proof_integrity",),
            )
        )

    test_relations = tuple(
        relation
        for relation in relations
        if relation.relation_type is RelationType.TESTS
    )
    group_participants = tuple(
        sorted(
            [
                *(item.participant_id for item in exact_tests),
                *(item.participant_id for item in unresolved_participants),
            ]
        )
    )
    if not proof_obligations:
        unresolved.append("exact_test_callable:missing")
        proof_obligations.append(
            ProofObligation.create(
                claim=(
                    "Resolve an exact test callable, exact test edge, and the "
                    "specific invariant proved for this objective."
                ),
                status=ProofStatus.OPEN,
                required_evidence=(
                    "exact_test_callable",
                    "test_edge",
                    "proved_invariant",
                ),
                verifier_ids=("relational_test_proof_integrity",),
            )
        )

    role_bindings = tuple(
        [
            *(
                RoleBinding(item.participant_id, "exact_test_callable")
                for item in exact_tests
            ),
            *(
                RoleBinding(item.participant_id, "test_file_without_callable_proof")
                for item in unresolved_participants
            ),
        ]
    )
    omitted: dict[str, int] = {}
    filename_gaps = sum(item.startswith("test_callable_owner:") for item in unresolved)
    invariant_gaps = sum(item.startswith("proved_invariant:") for item in unresolved)
    missing_test_gaps = sum(item == "exact_test_callable:missing" for item in unresolved)
    if filename_gaps:
        omitted["unresolved_test_callable_owner"] = filename_gaps
    if invariant_gaps:
        omitted["unresolved_test_invariant"] = invariant_gaps
    if missing_test_gaps:
        omitted["missing_exact_test_evidence"] = missing_test_gaps

    return (
        RelationalGroup.create(
            group_kind=GroupKind.OBJECTIVE_GROUP,
            purpose="test_proof_ownership",
            role_bindings=role_bindings,
            relations=test_relations,
            predicates=("test_filename_alone_is_not_callable_proof",),
            authority_constraints=("verification_proves",),
            proof_obligations=tuple(proof_obligations),
            boundary=_group_boundary(
                group_participants,
                unresolved=unresolved,
                omitted_reasons=omitted,
            ),
            canonical_owner_refs=(
                "AuraEmergentEvidenceSpine",
                "CodeTopoAnchor",
                "CodingWaboose",
            ),
        ),
        tuple(unresolved_participants),
    )


def _input_scope_authority_group(
    participants: Sequence[RelationalParticipant],
    relations: Sequence[TypedRelation],
    *,
    authority_participants: Sequence[RelationalParticipant],
    packet_ref: str,
) -> tuple[RelationalGroup, tuple[RelationalParticipant, ...]]:
    atomic = tuple(
        item
        for item in participants
        if item.participant_type is ParticipantType.ATOMIC_SYMBOL
    )
    assignments: dict[str, RelationalParticipant] = {}
    name_derived_roles: set[str] = set()
    for role, patterns in _INPUT_ROLE_PATTERNS.items():
        if role == "authority_guard":
            continue
        matches = [
            item
            for item in atomic
            if any(
                pattern in (item.qualified_symbol or "").lower()
                for pattern in patterns
            )
        ]
        if matches:
            assignments[role] = sorted(matches, key=lambda item: item.participant_id)[0]
            name_derived_roles.add(role)
    if authority_participants:
        authority_guard = next(
            (item for item in authority_participants if item.role == "authority_guard"),
            None
        )
        if authority_guard is None:
            authority_guard = sorted(
                authority_participants, key=lambda item: item.participant_id
            )[0]
        assignments["authority_guard"] = authority_guard

    unresolved_participants: list[RelationalParticipant] = []
    unresolved: list[str] = []
    proof_obligations: list[ProofObligation] = []
    for role in ("input_parser", "scope_normalizer", "authority_guard", "packet_assembler"):
        if role in assignments:
            continue
        participant = RelationalParticipant.create(
            participant_type=(
                ParticipantType.AUTHORITY
                if role == "authority_guard"
                else ParticipantType.ATOMIC_SYMBOL
            ),
            role=f"unresolved_{role}",
            truth_class=TruthClass.UNRESOLVED,
            canonical_owner="RelationalSynthesisShadowCompiler",
            canonical_ref=f"required_role:{role}",
            digest=None,
            evidence_refs=(packet_ref,),
            freshness=Freshness.UNRESOLVED,
            qualified_symbol=None,
            metadata={"required_role": role},
        )
        assignments[role] = participant
        unresolved_participants.append(participant)
        unresolved.append(f"required_role:{role}")
        proof_obligations.append(
            ProofObligation.create(
                claim=f"Resolve exact current evidence for required role {role}.",
                status=ProofStatus.OPEN,
                required_evidence=("exact_source_or_manifest", "current_digest"),
                verifier_ids=("relational_authority_path_integrity",),
            )
        )

    for role in sorted(name_derived_roles):
        participant = assignments[role]
        unresolved.append(f"candidate_role:{role}:{participant.participant_id}")
        proof_obligations.append(
            ProofObligation.create(
                claim=(
                    f"Prove role {role} for exact participant "
                    f"{participant.qualified_symbol or participant.canonical_ref} "
                    "through structural, schema, manifest, or verifier evidence; "
                    "the function name is ranking evidence only."
                ),
                status=ProofStatus.OPEN,
                required_evidence=("nonlexical_role_evidence", "current_digest"),
                evidence_refs=participant.evidence_refs,
                verifier_ids=("relational_identity_consistency",),
            )
        )

    assignment_ids = {item.participant_id for item in assignments.values()}
    group_relations = tuple(
        relation
        for relation in relations
        if relation.source_participant_id in assignment_ids
        and relation.target_participant_id in assignment_ids
    )
    role_bindings = tuple(
        RoleBinding(
            item.participant_id,
            f"candidate_{role}" if role in name_derived_roles else role,
        )
        for role, item in sorted(assignments.items())
    )
    if not proof_obligations:
        unresolved.append("input_scope_authority_path:unproved")
        proof_obligations.append(
            ProofObligation.create(
                claim=(
                    "Reprove the complete input-to-scope-to-authority path from "
                    "nonlexical current evidence."
                ),
                status=ProofStatus.OPEN,
                required_evidence=(
                    "exact_source",
                    "authority_manifest",
                    "nonlexical_role_evidence",
                ),
                verifier_ids=("relational_authority_path_integrity",),
            )
        )

    omitted: dict[str, int] = {}
    missing_roles = sum(item.startswith("required_role:") for item in unresolved)
    candidate_roles = sum(item.startswith("candidate_role:") for item in unresolved)
    unproved_paths = sum(item == "input_scope_authority_path:unproved" for item in unresolved)
    if missing_roles:
        omitted["unresolved_input_scope_authority_role"] = missing_roles
    if candidate_roles:
        omitted["name_derived_role_requires_proof"] = candidate_roles
    if unproved_paths:
        omitted["unproved_input_scope_authority_path"] = unproved_paths

    return (
        RelationalGroup.create(
            group_kind=GroupKind.OBJECTIVE_GROUP,
            purpose="input_scope_authority",
            role_bindings=role_bindings,
            relations=group_relations,
            predicates=(
                "invalid_explicit_targets_fail_closed",
                "advisory_affinity_cannot_expand_exact_scope",
                "name_derived_roles_are_candidates_only",
            ),
            authority_constraints=(
                "human_review_required",
                "production_mutation_false",
                "automatic_merge_false",
            ),
            proof_obligations=tuple(proof_obligations),
            boundary=_group_boundary(
                tuple(item.participant_id for item in assignments.values()),
                unresolved=unresolved,
                omitted_reasons=omitted,
            ),
            canonical_owner_refs=(
                "AuraEmergentEvidenceSpine",
                "PolysyntheticIntentPacket",
                "RelationalSynthesisShadowCompiler",
            ),
        ),
        tuple(unresolved_participants),
    )


__all__ = [
    "RELATIONAL_SYNTHESIS_VERSION",
    "RELATIONAL_PARTICIPANT_VERSION",
    "RELATIONAL_GROUP_VERSION",
    "RELATIONAL_CAPSULE_VERSION",
    "TruthClass",
    "Freshness",
    "ParticipantType",
    "RelationType",
    "GroupKind",
    "ProofStatus",
    "RelationalParticipant",
    "TypedRelation",
    "RoleBinding",
    "ProofObligation",
    "RelationalBoundary",
    "RelationalGroup",
    "RelationalSynthesisCapsule",
    "RelationalSynthesisShadowCompiler",
    "compile_relational_shadow_capsule",
]
