"""Source-first, task-conditioned project-context compilation for Aura PR3.

PR3 wraps the existing PR1 ``ProjectContextProjection``. It does not create a
project database, mutate canonical owners, grant patch/execution authority, or
replace Compass/Continuity/Evidence owners. Outputs are disposable receipts and
bounded projections recompiled when answer-determining identity changes.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import re
from typing import Any

from aura_ephemeral_workspace_contracts import (
    CanonicalReference,
    ProjectContextProjection,
    RepositoryIdentity,
    stable_digest,
)

PROJECT_CONTEXT_COMPILER_VERSION = "AURA_SOURCE_FIRST_PROJECT_CONTEXT_COMPILER_V1"
PROJECTION_SELECTION_RECEIPT_VERSION = "AURA_PROJECTION_SELECTION_RECEIPT_V1"
PROJECT_CONTEXT_COMPILATION_VERSION = "AURA_PROJECT_CONTEXT_COMPILATION_V1"
PROJECT_CONTEXT_PROVENANCE_VERSION = "AURA_PROJECT_CONTEXT_PROVENANCE_TRACE_V1"
PROJECT_CONTEXT_FRESHNESS_VERSION = "AURA_PROJECT_CONTEXT_FRESHNESS_VALIDATION_V1"
PROJECT_CANONICAL_OWNER = "aura_unified_memory_continuity"
MISSING_SELECTED_SOURCE_ID = "source:selected"

MAX_CANDIDATES = 512
MAX_EDGES = 2048
MAX_DEPENDENCIES = 64
MAX_TEMPORAL_BINDINGS = 64
MAX_TEXT_BYTES = 4096
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,191}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")

MEMORY_LIFECYCLE_PHASES = (
    "WRITE_INGEST",
    "STORE",
    "RETRIEVE",
    "EXECUTE_USE",
    "SHARE_PROPAGATE",
    "FORGET_ROLLBACK",
)


class CandidateCategory(str, Enum):
    SOURCE = "SOURCE"
    TEST = "TEST"
    SCHEMA = "SCHEMA"
    DECISION = "DECISION"
    REJECTED_ALTERNATIVE = "REJECTED_ALTERNATIVE"
    FAILED_ATTEMPT = "FAILED_ATTEMPT"
    UNRESOLVED_QUESTION = "UNRESOLVED_QUESTION"
    ASSUMPTION = "ASSUMPTION"
    CAPABILITY = "CAPABILITY"
    RELATIONSHIP = "RELATIONSHIP"
    BLOCKER = "BLOCKER"
    NEXT_ACTION = "NEXT_ACTION"
    AUTHORITY = "AUTHORITY"
    POLICY = "POLICY"
    PROOF_OBLIGATION = "PROOF_OBLIGATION"


class CandidateTruthClass(str, Enum):
    EXACT_CURRENT = "EXACT_CURRENT"
    DERIVED_VERIFIED = "DERIVED_VERIFIED"
    ADVISORY = "ADVISORY"
    HYPOTHESIS = "HYPOTHESIS"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class CandidateAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    SOURCE_ADAPTER_MISSING = "SOURCE_ADAPTER_MISSING"


class EdgeTruthClass(str, Enum):
    EXACT = "EXACT"
    DERIVED_VERIFIED = "DERIVED_VERIFIED"
    ADVISORY = "ADVISORY"
    HYPOTHESIS = "HYPOTHESIS"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"


class SelectionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class TemporalBindingKind(str, Enum):
    REPOSITORY_HEAD = "REPOSITORY_HEAD"
    SOURCE_HASH = "SOURCE_HASH"
    EVIDENCE = "EVIDENCE"
    POLICY = "POLICY"
    LEASE = "LEASE"
    OWNER_RECORD = "OWNER_RECORD"
    DEPENDENCY_VERSION = "DEPENDENCY_VERSION"


class ContextAuthorityClass(str, Enum):
    CANONICAL_READ = "CANONICAL_READ"
    DERIVED_READ = "DERIVED_READ"
    ADVISORY_NONE = "ADVISORY_NONE"


def _text(value: Any, name: str, *, maximum: int = MAX_TEXT_BYTES) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    value = " ".join(value.strip().split())
    if not value or len(value.encode("utf-8")) > maximum:
        raise ValueError(f"{name} must be non-empty and bounded")
    return value


def _id(value: Any, name: str) -> str:
    value = _text(value, name, maximum=192)
    if not _ID.fullmatch(value):
        raise ValueError(f"{name} is not a canonical identifier")
    return value


def _digest(value: Any, name: str) -> str:
    value = _text(value, name, maximum=64).lower()
    if not _DIGEST.fullmatch(value):
        raise ValueError(f"{name} must be a 64-hex digest")
    return value


def _enum(enum_type: type[Enum], value: Any, name: str) -> Any:
    raw = value.value if isinstance(value, Enum) else value
    if type(raw) is not str:
        raise TypeError(f"{name} must be a string enum value")
    try:
        return enum_type(raw)
    except ValueError as exc:
        raise ValueError(f"unsupported {name}: {raw}") from exc


def _ids(values: Sequence[str], name: str, *, maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)) or not isinstance(values, Sequence):
        raise TypeError(f"{name} must be a sequence")
    if len(values) > maximum:
        raise ValueError(f"{name} exceeds its item ceiling")
    result = tuple(_id(item, f"{name} item") for item in values)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    return tuple(sorted(result))


def _int(value: Any, name: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"{name} is outside its allowed range")
    return value


@dataclass(frozen=True)
class TemporalBinding:
    kind: TemporalBindingKind
    binding_id: str
    digest: str
    expires_at_ms: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _enum(TemporalBindingKind, self.kind, "temporal kind"))
        object.__setattr__(self, "binding_id", _id(self.binding_id, "temporal binding_id"))
        object.__setattr__(self, "digest", _digest(self.digest, "temporal digest"))
        object.__setattr__(
            self,
            "expires_at_ms",
            _int(self.expires_at_ms, "expires_at_ms", maximum=2**63 - 1),
        )

    @property
    def key(self) -> str:
        return f"{self.kind.value}:{self.binding_id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "binding_id": self.binding_id,
            "digest": self.digest,
            "expires_at_ms": self.expires_at_ms,
        }


def _normalize_candidate_identity(candidate: Any) -> None:
    object.__setattr__(candidate, "candidate_id", _id(candidate.candidate_id, "candidate_id"))
    object.__setattr__(
        candidate,
        "category",
        _enum(CandidateCategory, candidate.category, "category"),
    )
    object.__setattr__(
        candidate,
        "source_adapter",
        _id(candidate.source_adapter, "source_adapter"),
    )
    object.__setattr__(candidate, "origin_ref", _text(candidate.origin_ref, "origin_ref"))
    object.__setattr__(
        candidate,
        "authority_class",
        _enum(ContextAuthorityClass, candidate.authority_class, "authority_class"),
    )
    object.__setattr__(
        candidate,
        "truth_class",
        _enum(CandidateTruthClass, candidate.truth_class, "truth_class"),
    )
    object.__setattr__(
        candidate,
        "availability",
        _enum(CandidateAvailability, candidate.availability, "availability"),
    )
    object.__setattr__(
        candidate,
        "relevance_score",
        _int(candidate.relevance_score, "relevance_score", maximum=1_000_000),
    )


def _normalize_candidate_relationships(candidate: Any) -> None:
    if type(candidate.required) is not bool or type(candidate.answer_determining) is not bool:
        raise TypeError("required and answer_determining must be booleans")
    object.__setattr__(
        candidate,
        "dependency_ids",
        _ids(candidate.dependency_ids, "dependency_ids", maximum=MAX_DEPENDENCIES),
    )
    if type(candidate.conflict_key) is not str:
        raise TypeError("conflict_key must be a string")
    if candidate.conflict_key:
        object.__setattr__(
            candidate,
            "conflict_key",
            _id(candidate.conflict_key, "conflict_key"),
        )
    bindings = tuple(candidate.temporal_bindings)
    if len(bindings) > MAX_TEMPORAL_BINDINGS or any(
        type(item) is not TemporalBinding for item in bindings
    ):
        raise ValueError(
            "temporal_bindings must contain bounded exact TemporalBinding records"
        )
    if len({item.key for item in bindings}) != len(bindings):
        raise ValueError("temporal_bindings contains duplicate binding keys")
    object.__setattr__(
        candidate,
        "temporal_bindings",
        tuple(sorted(bindings, key=lambda item: item.key)),
    )


def _validate_candidate_reference(candidate: Any) -> None:
    if candidate.availability is CandidateAvailability.AVAILABLE:
        if type(candidate.reference) is not CanonicalReference:
            raise ValueError(
                "available candidate requires an exact CanonicalReference"
            )
        return
    if candidate.reference is not None:
        raise ValueError(
            "unavailable candidate must not carry a canonical reference"
        )


def _validate_candidate_authority(candidate: Any) -> None:
    authoritative = {
        CandidateTruthClass.EXACT_CURRENT,
        CandidateTruthClass.DERIVED_VERIFIED,
    }
    if candidate.truth_class not in authoritative:
        if candidate.authority_class is not ContextAuthorityClass.ADVISORY_NONE:
            raise ValueError(
                "advisory/hypothesis/stale/unavailable candidates cannot carry authority"
            )
        return
    if candidate.reference is None or candidate.reference.truth_class != "EXACT":
        raise ValueError(
            "authoritative read candidate requires an EXACT canonical reference"
        )
    expected = (
        ContextAuthorityClass.CANONICAL_READ
        if candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
        else ContextAuthorityClass.DERIVED_READ
    )
    if candidate.authority_class is not expected:
        raise ValueError(
            "candidate authority class does not match its truth class"
        )
    if candidate.origin_ref != candidate.reference.canonical_ref:
        raise ValueError(
            "authoritative candidate origin_ref must equal its canonical reference origin"
        )


def _canonical_reference_binding_kind(
    category: CandidateCategory,
) -> TemporalBindingKind:
    if category is CandidateCategory.SOURCE:
        return TemporalBindingKind.SOURCE_HASH
    if category is CandidateCategory.POLICY:
        return TemporalBindingKind.POLICY
    if category in {
        CandidateCategory.TEST,
        CandidateCategory.SCHEMA,
        CandidateCategory.FAILED_ATTEMPT,
        CandidateCategory.PROOF_OBLIGATION,
    }:
        return TemporalBindingKind.EVIDENCE
    return TemporalBindingKind.OWNER_RECORD


def _bind_candidate_reference_identity(candidate: Any) -> None:
    if (
        candidate.truth_class
        not in {CandidateTruthClass.EXACT_CURRENT, CandidateTruthClass.DERIVED_VERIFIED}
        or candidate.reference is None
    ):
        return
    reference_binding = TemporalBinding(
        _canonical_reference_binding_kind(candidate.category),
        candidate.reference.reference_id,
        candidate.reference.digest,
    )
    by_key = {item.key: item for item in candidate.temporal_bindings}
    existing = by_key.get(reference_binding.key)
    if existing is not None and existing.digest != reference_binding.digest:
        raise ValueError(
            "authoritative reference binding conflicts with canonical reference digest"
        )
    if existing is None:
        object.__setattr__(
            candidate,
            "temporal_bindings",
            tuple(
                sorted(
                    (*candidate.temporal_bindings, reference_binding),
                    key=lambda item: item.key,
                )
            ),
        )


@dataclass(frozen=True)
class ProjectContextCandidate:
    candidate_id: str
    category: CandidateCategory
    source_adapter: str
    origin_ref: str
    authority_class: ContextAuthorityClass
    truth_class: CandidateTruthClass
    availability: CandidateAvailability = CandidateAvailability.AVAILABLE
    reference: CanonicalReference | None = None
    relevance_score: int = 0
    required: bool = False
    answer_determining: bool = False
    dependency_ids: tuple[str, ...] = ()
    conflict_key: str = ""
    temporal_bindings: tuple[TemporalBinding, ...] = ()

    def __post_init__(self) -> None:
        _normalize_candidate_identity(self)
        _normalize_candidate_relationships(self)
        _validate_candidate_reference(self)
        _validate_candidate_authority(self)
        _bind_candidate_reference_identity(self)

    @property
    def origin_bound(self) -> bool:
        return self.reference is not None and self.origin_ref == self.reference.canonical_ref

    @property
    def authority_non_increasing(self) -> bool:
        if self.truth_class is CandidateTruthClass.EXACT_CURRENT:
            return self.authority_class is ContextAuthorityClass.CANONICAL_READ
        if self.truth_class is CandidateTruthClass.DERIVED_VERIFIED:
            return self.authority_class is ContextAuthorityClass.DERIVED_READ
        return self.authority_class is ContextAuthorityClass.ADVISORY_NONE

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "category": self.category.value,
            "source_adapter": self.source_adapter,
            "origin_ref": self.origin_ref,
            "authority_class": self.authority_class.value,
            "truth_class": self.truth_class.value,
            "availability": self.availability.value,
            "reference": self.reference.to_dict() if self.reference is not None else None,
            "relevance_score": self.relevance_score,
            "required": self.required,
            "answer_determining": self.answer_determining,
            "dependency_ids": list(self.dependency_ids),
            "conflict_key": self.conflict_key,
            "temporal_bindings": [item.to_dict() for item in self.temporal_bindings],
            "memory_lifecycle": list(MEMORY_LIFECYCLE_PHASES),
            "origin_bound": self.origin_bound,
            "authority_non_increasing": self.authority_non_increasing,
        }


@dataclass(frozen=True)
class ProjectContextEdge:
    source_id: str
    target_id: str
    relation: str
    truth_class: EdgeTruthClass

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", _id(self.source_id, "edge source_id"))
        object.__setattr__(self, "target_id", _id(self.target_id, "edge target_id"))
        if self.source_id == self.target_id:
            raise ValueError("project-context self-edge is prohibited")
        object.__setattr__(self, "relation", _id(self.relation, "edge relation"))
        object.__setattr__(
            self,
            "truth_class",
            _enum(EdgeTruthClass, self.truth_class, "edge truth_class"),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "truth_class": self.truth_class.value,
        }


@dataclass(frozen=True)
class ProjectionBudget:
    max_nodes: int = 64
    max_edges: int = 256

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_nodes",
            _int(self.max_nodes, "max_nodes", minimum=1, maximum=256),
        )
        object.__setattr__(
            self,
            "max_edges",
            _int(self.max_edges, "max_edges", minimum=1, maximum=1024),
        )

    def to_dict(self) -> dict[str, int]:
        return {"max_nodes": self.max_nodes, "max_edges": self.max_edges}


def _normalize_selection_receipt(receipt: Any) -> tuple[str, ...]:
    if receipt.version != PROJECTION_SELECTION_RECEIPT_VERSION:
        raise ValueError("unsupported projection selection receipt version")
    object.__setattr__(
        receipt,
        "objective_digest",
        _digest(receipt.objective_digest, "objective_digest"),
    )
    object.__setattr__(
        receipt,
        "repository_identity_digest",
        _digest(receipt.repository_identity_digest, "repository_identity_digest"),
    )
    canonical_owner = _id(receipt.canonical_owner, "canonical_owner")
    if canonical_owner != PROJECT_CANONICAL_OWNER:
        raise ValueError("canonical_owner must remain the unified continuity owner")
    object.__setattr__(receipt, "canonical_owner", canonical_owner)
    omission_fields = (
        "omitted_irrelevant",
        "omitted_by_budget",
        "stale",
        "unavailable",
        "conflicting",
        "source_adapter_missing",
        "mandatory_evidence_missing",
    )
    for name in ("selected", *omission_fields):
        object.__setattr__(
            receipt,
            name,
            _ids(getattr(receipt, name), name, maximum=MAX_CANDIDATES),
        )
    return omission_fields


def _validate_selection_receipt_partition(
    receipt: Any, omission_fields: Sequence[str]
) -> None:
    selected_ids = set(receipt.selected)
    for name in omission_fields:
        overlap = selected_ids.intersection(getattr(receipt, name))
        if overlap:
            raise ValueError(
                f"selection receipt cannot mark selected ids as {name}: {sorted(overlap)}"
            )


def _validate_selection_receipt_status(receipt: Any) -> None:
    object.__setattr__(
        receipt,
        "status",
        _enum(SelectionStatus, receipt.status, "selection status"),
    )
    if type(receipt.budget) is not ProjectionBudget:
        raise ValueError("selection receipt requires exact ProjectionBudget")
    if (
        receipt.status is SelectionStatus.COMPLETE
        and receipt.mandatory_evidence_missing
    ):
        raise ValueError(
            "COMPLETE selection cannot have missing mandatory evidence"
        )
    if (
        receipt.status is SelectionStatus.INCOMPLETE
        and not receipt.mandatory_evidence_missing
    ):
        raise ValueError(
            "INCOMPLETE selection must identify missing mandatory evidence"
        )


def _finalize_selection_receipt(receipt: Any) -> None:
    expected = stable_digest(receipt.to_dict(include_digest=False))
    if receipt.receipt_digest and receipt.receipt_digest != expected:
        raise ValueError("selection receipt digest mismatch")
    object.__setattr__(receipt, "receipt_digest", expected)


@dataclass(frozen=True)
class ProjectionSelectionReceipt:
    objective_digest: str
    repository_identity_digest: str
    canonical_owner: str
    selected: tuple[str, ...]
    omitted_irrelevant: tuple[str, ...]
    omitted_by_budget: tuple[str, ...]
    stale: tuple[str, ...]
    unavailable: tuple[str, ...]
    conflicting: tuple[str, ...]
    source_adapter_missing: tuple[str, ...]
    mandatory_evidence_missing: tuple[str, ...]
    status: SelectionStatus
    budget: ProjectionBudget
    receipt_digest: str = ""
    version: str = PROJECTION_SELECTION_RECEIPT_VERSION

    def __post_init__(self) -> None:
        omission_fields = _normalize_selection_receipt(self)
        _validate_selection_receipt_partition(self, omission_fields)
        _validate_selection_receipt_status(self)
        _finalize_selection_receipt(self)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        body = {
            "version": self.version,
            "objective_digest": self.objective_digest,
            "repository_identity_digest": self.repository_identity_digest,
            "canonical_owner": self.canonical_owner,
            "selected": list(self.selected),
            "omitted_irrelevant": list(self.omitted_irrelevant),
            "omitted_by_budget": list(self.omitted_by_budget),
            "stale": list(self.stale),
            "unavailable": list(self.unavailable),
            "conflicting": list(self.conflicting),
            "source_adapter_missing": list(self.source_adapter_missing),
            "mandatory_evidence_missing": list(self.mandatory_evidence_missing),
            "status": self.status.value,
            "budget": self.budget.to_dict(),
        }
        if include_digest:
            body["receipt_digest"] = self.receipt_digest
        return body


def _validate_compilation_identity(compilation: Any) -> None:
    if compilation.version != PROJECT_CONTEXT_COMPILATION_VERSION:
        raise ValueError("unsupported project-context compilation version")
    object.__setattr__(
        compilation,
        "objective",
        _text(compilation.objective, "objective"),
    )
    object.__setattr__(
        compilation,
        "project_ref",
        _text(compilation.project_ref, "project_ref"),
    )
    object.__setattr__(
        compilation,
        "objective_digest",
        _digest(compilation.objective_digest, "objective_digest"),
    )
    expected_objective_digest = stable_digest({"objective": compilation.objective})
    if compilation.objective_digest != expected_objective_digest:
        raise ValueError("objective_digest is not bound to objective")
    if type(compilation.repository_identity) is not RepositoryIdentity:
        raise ValueError("compilation requires exact RepositoryIdentity")
    if (
        compilation.projection is not None
        and type(compilation.projection) is not ProjectContextProjection
    ):
        raise ValueError("projection must be exact ProjectContextProjection")
    if type(compilation.selection_receipt) is not ProjectionSelectionReceipt:
        raise ValueError(
            "selection_receipt must be exact ProjectionSelectionReceipt"
        )
    if compilation.selection_receipt.objective_digest != compilation.objective_digest:
        raise ValueError(
            "selection receipt objective is not bound to compilation"
        )
    if (
        compilation.selection_receipt.repository_identity_digest
        != compilation.repository_identity.identity_digest
    ):
        raise ValueError(
            "selection receipt repository identity is not bound to compilation"
        )
    if (
        compilation.selection_receipt.status is SelectionStatus.COMPLETE
        and compilation.projection is None
    ):
        raise ValueError(
            "COMPLETE selection must emit the canonical PR1 projection"
        )
    if (
        compilation.selection_receipt.status is SelectionStatus.INCOMPLETE
        and compilation.projection is not None
    ):
        raise ValueError(
            "INCOMPLETE selection must not expose a canonical PR1 projection"
        )


def _canonical_compilation_candidates(
    compilation: Any,
) -> tuple[
    tuple[ProjectContextCandidate, ...],
    tuple[str, ...],
    dict[str, ProjectContextCandidate],
]:
    selected = tuple(compilation.selected_candidates)
    if any(type(item) is not ProjectContextCandidate for item in selected):
        raise ValueError("selected_candidates must be exact records")
    selected = tuple(sorted(selected, key=lambda item: item.candidate_id))
    if len({item.candidate_id for item in selected}) != len(selected):
        raise ValueError(
            "selected_candidates contains duplicate candidate ids"
        )
    if any(item.candidate_id == MISSING_SELECTED_SOURCE_ID for item in selected):
        raise ValueError(
            f"candidate_id {MISSING_SELECTED_SOURCE_ID!r} is reserved for the "
            "missing exact-current answer-determining source receipt marker"
        )
    if any(item.reference is None for item in selected):
        raise ValueError("selected candidate is missing canonical reference")
    reference_ids = {item.reference.reference_id for item in selected}
    if len(reference_ids) != len(selected):
        raise ValueError(
            "selected candidates must have unique canonical references"
        )
    object.__setattr__(compilation, "selected_candidates", selected)
    selected_ids = tuple(item.candidate_id for item in selected)
    if selected_ids != compilation.selection_receipt.selected:
        raise ValueError(
            "selected candidate identities do not match selection receipt"
        )
    if len(selected) > compilation.selection_receipt.budget.max_nodes:
        raise ValueError(
            "selected candidates exceed selection receipt node budget"
        )
    return selected, selected_ids, {
        item.candidate_id: item for item in selected
    }


def _validate_compilation_selection(
    compilation: Any,
    selected: tuple[ProjectContextCandidate, ...],
    selected_map: Mapping[str, ProjectContextCandidate],
) -> None:
    missing_dependencies = sorted(
        (item.candidate_id, dependency_id)
        for item in selected
        for dependency_id in item.dependency_ids
        if dependency_id not in selected_map
    )
    if missing_dependencies:
        raise ValueError(
            "selected candidate dependency closure is incomplete: "
            f"{missing_dependencies}"
        )
    ineligible_selected = {
        item.candidate_id: problem
        for item in selected
        if (problem := _problem(item)) is not None
    }
    if ineligible_selected:
        raise ValueError(
            "selected candidates must remain compiler-eligible: "
            f"{sorted(ineligible_selected.items())}"
        )
    selected_conflicts = _conflicts(selected_map)
    if selected_conflicts:
        raise ValueError(
            "selected candidates must not contain unresolved conflicts: "
            f"{sorted(selected_conflicts)}"
        )
    if compilation.selection_receipt.status is SelectionStatus.COMPLETE:
        if compilation.projection is None:
            raise ValueError("COMPLETE selection requires a projection timestamp")
        expired_ids = _expired_binding_candidate_ids(
            selected, compilation.projection.freshness_timestamp_ms
        )
        if expired_ids:
            raise ValueError(
                "selected temporal binding expired at compilation timestamp: "
                f"{sorted(expired_ids)}"
            )
    authoritative_unbound = sorted(
        item.candidate_id
        for item in selected
        if item.truth_class in _ELIGIBLE_TRUTH
        and item.reference is not None
        and not any(
            binding.kind is _canonical_reference_binding_kind(item.category)
            and binding.binding_id == item.reference.reference_id
            and binding.digest == item.reference.digest
            for binding in item.temporal_bindings
        )
    )
    if (
        compilation.selection_receipt.status is SelectionStatus.COMPLETE
        and authoritative_unbound
    ):
        raise ValueError(
            "COMPLETE selection requires drift-sensitive canonical-reference bindings: "
            f"{authoritative_unbound}"
        )
    has_exact_answer_source = any(
        item.category is CandidateCategory.SOURCE
        and item.truth_class is CandidateTruthClass.EXACT_CURRENT
        and item.answer_determining
        for item in selected
    )
    if (
        compilation.selection_receipt.status is SelectionStatus.COMPLETE
        and not has_exact_answer_source
    ):
        raise ValueError(
            "COMPLETE selection requires an exact-current answer-determining source"
        )


def _canonicalize_compilation_edges(
    compilation: Any,
    selected_ids: tuple[str, ...],
) -> None:
    edges = tuple(compilation.graph_edges)
    if len(edges) > compilation.selection_receipt.budget.max_edges:
        raise ValueError(
            "compiled graph edges exceed selection receipt edge budget"
        )
    if any(type(item) is not ProjectContextEdge for item in edges):
        raise ValueError("graph_edges must be exact records")
    selected_id_set = set(selected_ids)
    if any(
        edge.source_id not in selected_id_set
        or edge.target_id not in selected_id_set
        for edge in edges
    ):
        raise ValueError(
            "compiled graph edge escapes selected candidate set"
        )
    object.__setattr__(
        compilation,
        "graph_edges",
        tuple(
            sorted(
                edges,
                key=lambda item: (
                    item.source_id,
                    item.target_id,
                    item.relation,
                    item.truth_class.value,
                ),
            )
        ),
    )


def _validate_compilation_projection(
    compilation: Any,
    selected: tuple[ProjectContextCandidate, ...],
) -> None:
    projection = compilation.projection
    if projection is None:
        return
    if projection.project_ref != compilation.project_ref:
        raise ValueError("projection project_ref is not bound to compilation")
    if projection.objective_digest != compilation.objective_digest:
        raise ValueError(
            "projection objective is not bound to compilation"
        )
    if projection.canonical_owner != PROJECT_CANONICAL_OWNER:
        raise ValueError(
            "projection canonical owner is not bound to PR3 owner"
        )
    if (
        projection.repository_identity.to_dict()
        != compilation.repository_identity.to_dict()
    ):
        raise ValueError(
            "projection repository identity is not bound to compilation"
        )
    expected_projection_refs: dict[str, list[CanonicalReference]] = {
        name: [] for name in set(_CATEGORY_FIELD.values())
    }
    for item in selected:
        if item.reference is None:
            raise ValueError(
                "selected candidate is missing canonical reference"
            )
        expected_projection_refs[_CATEGORY_FIELD[item.category]].append(
            item.reference
        )
    for field_name, expected_refs in expected_projection_refs.items():
        actual_refs = getattr(projection, field_name)
        canonical_expected = tuple(
            sorted(expected_refs, key=lambda ref: ref.reference_id)
        )
        if tuple(ref.to_dict() for ref in actual_refs) != tuple(
            ref.to_dict() for ref in canonical_expected
        ):
            raise ValueError(
                f"projection {field_name} references do not match selected candidates"
            )
    expected_projection = _projection(
        compilation.objective,
        compilation.project_ref,
        compilation.repository_identity,
        selected,
        projection.freshness_timestamp_ms,
        _selection_warnings(compilation.selection_receipt),
    )
    if projection.to_dict() != expected_projection.to_dict():
        raise ValueError("projection derived fields do not match compiler reconstruction")


def _finalize_compilation(compilation: Any) -> None:
    if type(compilation.admissible) is not bool:
        raise TypeError("admissible must be a boolean")
    expected_admission = (
        compilation.selection_receipt.status is SelectionStatus.COMPLETE
    )
    if compilation.admissible != expected_admission:
        raise ValueError(
            "admissible must equal COMPLETE receipt with emitted projection"
        )
    expected = stable_digest(compilation.to_dict(include_digest=False))
    if (
        compilation.compilation_digest
        and compilation.compilation_digest != expected
    ):
        raise ValueError("project-context compilation digest mismatch")
    object.__setattr__(compilation, "compilation_digest", expected)


@dataclass(frozen=True)
class ProjectContextCompilation:
    objective: str
    project_ref: str
    objective_digest: str
    repository_identity: RepositoryIdentity
    projection: ProjectContextProjection | None
    selection_receipt: ProjectionSelectionReceipt
    selected_candidates: tuple[ProjectContextCandidate, ...]
    graph_edges: tuple[ProjectContextEdge, ...]
    admissible: bool
    compilation_digest: str = ""
    version: str = PROJECT_CONTEXT_COMPILATION_VERSION

    def __post_init__(self) -> None:
        _validate_compilation_identity(self)
        selected, selected_ids, selected_map = _canonical_compilation_candidates(self)
        _validate_compilation_selection(self, selected, selected_map)
        _canonicalize_compilation_edges(self, selected_ids)
        _validate_compilation_projection(self, selected)
        _finalize_compilation(self)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        body = {
            "version": self.version,
            "objective": self.objective,
            "project_ref": self.project_ref,
            "objective_digest": self.objective_digest,
            "repository_identity": self.repository_identity.to_dict(),
            "projection": self.projection.to_dict() if self.projection is not None else None,
            "selection_receipt": self.selection_receipt.to_dict(),
            "selected_candidates": [item.to_dict() for item in self.selected_candidates],
            "graph_edges": [item.to_dict() for item in self.graph_edges],
            "admissible": self.admissible,
            "projection_only": True,
            "source_mutation": False,
            "automatic_persistence": False,
            "automatic_merge": False,
        }
        if include_digest:
            body["compilation_digest"] = self.compilation_digest
        return body

    def headless_projection(self) -> dict[str, Any]:
        return {
            "version": PROJECT_CONTEXT_COMPILATION_VERSION,
            "compilation_digest": self.compilation_digest,
            "project_ref": self.project_ref,
            "objective_digest": self.objective_digest,
            "projection": self.projection.to_dict() if self.projection is not None else None,
            "selection_receipt": self.selection_receipt.to_dict(),
            "nodes": [item.to_dict() for item in self.selected_candidates],
            "edges": [item.to_dict() for item in self.graph_edges],
            "full_project_graph_included": False,
            "source_mutation": False,
        }


_CATEGORY_FIELD = {
    CandidateCategory.SOURCE: "artifact_evidence_refs",
    CandidateCategory.TEST: "artifact_evidence_refs",
    CandidateCategory.SCHEMA: "artifact_evidence_refs",
    CandidateCategory.FAILED_ATTEMPT: "artifact_evidence_refs",
    CandidateCategory.AUTHORITY: "artifact_evidence_refs",
    CandidateCategory.POLICY: "artifact_evidence_refs",
    CandidateCategory.PROOF_OBLIGATION: "artifact_evidence_refs",
    CandidateCategory.DECISION: "decision_refs",
    CandidateCategory.REJECTED_ALTERNATIVE: "rejected_alternative_refs",
    CandidateCategory.UNRESOLVED_QUESTION: "unresolved_question_refs",
    CandidateCategory.ASSUMPTION: "assumption_refs",
    CandidateCategory.CAPABILITY: "capability_refs",
    CandidateCategory.RELATIONSHIP: "relationship_refs",
    CandidateCategory.BLOCKER: "blocker_refs",
    CandidateCategory.NEXT_ACTION: "next_action_refs",
}
_CATEGORY_PRIORITY = {
    category: index for index, category in enumerate(CandidateCategory)
}
_HARD_INCLUDE_CATEGORIES = frozenset(
    {
        CandidateCategory.TEST,
        CandidateCategory.SCHEMA,
        CandidateCategory.AUTHORITY,
        CandidateCategory.POLICY,
        CandidateCategory.BLOCKER,
        CandidateCategory.FAILED_ATTEMPT,
        CandidateCategory.PROOF_OBLIGATION,
    }
)
_ELIGIBLE_TRUTH = frozenset(
    {CandidateTruthClass.EXACT_CURRENT, CandidateTruthClass.DERIVED_VERIFIED}
)
_AUTHORITATIVE_EDGE_TRUTH = frozenset(
    {EdgeTruthClass.EXACT, EdgeTruthClass.DERIVED_VERIFIED}
)


def _problem(candidate: ProjectContextCandidate) -> str | None:
    if candidate.availability is CandidateAvailability.SOURCE_ADAPTER_MISSING:
        return "source_adapter_missing"
    if candidate.availability is CandidateAvailability.UNAVAILABLE:
        return "unavailable"
    if candidate.truth_class is CandidateTruthClass.STALE:
        return "stale"
    if candidate.truth_class is CandidateTruthClass.UNAVAILABLE:
        return "unavailable"
    if candidate.truth_class not in _ELIGIBLE_TRUTH:
        return "omitted_irrelevant"
    if candidate.reference is None:
        raise ValueError("eligible candidate is missing canonical reference")
    if candidate.reference.freshness_class not in {"CURRENT", "BOUNDED"}:
        return "stale"
    return None


def _closure(
    seed: str,
    candidates: Mapping[str, ProjectContextCandidate],
) -> tuple[set[str], set[str]]:
    selected: set[str] = set()
    missing: set[str] = set()
    stack = [seed]
    while stack:
        candidate_id = stack.pop()
        if candidate_id in selected:
            continue
        candidate = candidates.get(candidate_id)
        if candidate is None:
            missing.add(candidate_id)
            continue
        selected.add(candidate_id)
        stack.extend(reversed(candidate.dependency_ids))
    return selected, missing


def _conflicts(candidates: Mapping[str, ProjectContextCandidate]) -> set[str]:
    groups: dict[str, list[ProjectContextCandidate]] = {}
    binding_groups: dict[str, list[tuple[ProjectContextCandidate, TemporalBinding]]] = {}
    for candidate in candidates.values():
        if (
            candidate.conflict_key
            and _problem(candidate) is None
            and candidate.reference is not None
        ):
            groups.setdefault(candidate.conflict_key, []).append(candidate)
        for binding in candidate.temporal_bindings:
            binding_groups.setdefault(binding.key, []).append((candidate, binding))
    result: set[str] = set()
    for items in groups.values():
        if len(
            {item.reference.digest for item in items if item.reference is not None}
        ) > 1:
            result.update(item.candidate_id for item in items)
    for items in binding_groups.values():
        if len({binding.to_dict()["digest"] for _, binding in items}) > 1:
            result.update(candidate.candidate_id for candidate, _ in items)
    return result


def _expired_binding_candidate_ids(
    candidates: Sequence[ProjectContextCandidate],
    freshness_timestamp_ms: int,
) -> set[str]:
    return {
        candidate.candidate_id
        for candidate in candidates
        if any(
            binding.expires_at_ms
            and freshness_timestamp_ms >= binding.expires_at_ms
            for binding in candidate.temporal_bindings
        )
    }


def _projection(
    objective: str,
    project_ref: str,
    repository_identity: RepositoryIdentity,
    selected: Sequence[ProjectContextCandidate],
    freshness_timestamp_ms: int,
    warnings: Sequence[str],
) -> ProjectContextProjection:
    buckets: dict[str, list[CanonicalReference]] = {
        name: [] for name in set(_CATEGORY_FIELD.values())
    }
    selected_freshness: list[str] = []
    for candidate in selected:
        if candidate.reference is None:
            raise ValueError("selected candidate is missing canonical reference")
        buckets[_CATEGORY_FIELD[candidate.category]].append(candidate.reference)
        selected_freshness.append(candidate.reference.freshness_class)
    objective_digest = stable_digest({"objective": objective})
    purpose_digest = stable_digest(
        {
            "objective": objective,
            "compiler": PROJECT_CONTEXT_COMPILER_VERSION,
            "mode": "source_first",
        }
    )
    aggregate_freshness = (
        "BOUNDED" if "BOUNDED" in selected_freshness else "CURRENT"
    )
    return ProjectContextProjection(
        projection_id=f"project-context:{objective_digest[:24]}",
        project_ref=project_ref,
        canonical_owner=PROJECT_CANONICAL_OWNER,
        objective_digest=objective_digest,
        purpose_digest=purpose_digest,
        repository_identity=repository_identity,
        artifact_evidence_refs=tuple(buckets["artifact_evidence_refs"]),
        decision_refs=tuple(buckets["decision_refs"]),
        rejected_alternative_refs=tuple(buckets["rejected_alternative_refs"]),
        unresolved_question_refs=tuple(buckets["unresolved_question_refs"]),
        assumption_refs=tuple(buckets["assumption_refs"]),
        capability_refs=tuple(buckets["capability_refs"]),
        relationship_refs=tuple(buckets["relationship_refs"]),
        blocker_refs=tuple(buckets["blocker_refs"]),
        next_action_refs=tuple(buckets["next_action_refs"]),
        freshness_timestamp_ms=freshness_timestamp_ms,
        freshness_class=aggregate_freshness,
        completeness_warnings=tuple(sorted(set(warnings))),
    )


def _compile_candidate_map(
    candidates: Sequence[ProjectContextCandidate],
) -> dict[str, ProjectContextCandidate]:
    if isinstance(candidates, (str, bytes, bytearray)) or not isinstance(
        candidates, Sequence
    ):
        raise TypeError("candidates must be a sequence")
    if len(candidates) > MAX_CANDIDATES or any(
        type(item) is not ProjectContextCandidate for item in candidates
    ):
        raise ValueError(
            "candidates must be a bounded sequence of exact ProjectContextCandidate records"
        )
    candidate_map = {item.candidate_id: item for item in candidates}
    if len(candidate_map) != len(candidates):
        raise ValueError("duplicate candidate_id")
    if MISSING_SELECTED_SOURCE_ID in candidate_map:
        raise ValueError(
            f"candidate_id {MISSING_SELECTED_SOURCE_ID!r} is reserved for the "
            "missing exact-current answer-determining source receipt marker"
        )
    reference_ids = [
        item.reference.reference_id
        for item in candidates
        if item.reference is not None
    ]
    if len(set(reference_ids)) != len(reference_ids):
        raise ValueError(
            "task-conditioned candidates must not alias one canonical reference into multiple roles"
        )
    return candidate_map


def _compile_edge_items(
    edges: Sequence[ProjectContextEdge],
    candidate_map: Mapping[str, ProjectContextCandidate],
    budget: ProjectionBudget,
) -> tuple[ProjectContextEdge, ...]:
    edge_items = tuple(edges)
    if len(edge_items) > min(MAX_EDGES, budget.max_edges * 4) or any(
        type(item) is not ProjectContextEdge for item in edge_items
    ):
        raise ValueError(
            "edges must be a bounded sequence of exact ProjectContextEdge records"
        )
    unknown = sorted(
        {
            endpoint
            for edge in edge_items
            for endpoint in (edge.source_id, edge.target_id)
            if endpoint not in candidate_map
        }
    )
    if unknown:
        raise ValueError(
            "edge endpoint is outside the task-conditioned candidate set: "
            f"{unknown[:5]}"
        )
    return edge_items


def _validate_compile_context(
    repository_identity: RepositoryIdentity,
    candidates: Sequence[ProjectContextCandidate],
    edges: Sequence[ProjectContextEdge],
    budget: ProjectionBudget,
) -> tuple[dict[str, ProjectContextCandidate], tuple[ProjectContextEdge, ...]]:
    if type(repository_identity) is not RepositoryIdentity:
        raise ValueError("repository_identity must be exact PR1 RepositoryIdentity")
    if type(budget) is not ProjectionBudget:
        raise ValueError("budget must be exact ProjectionBudget")
    candidate_map = _compile_candidate_map(candidates)
    return candidate_map, _compile_edge_items(edges, candidate_map, budget)


def _selection_buckets(
    candidates: Sequence[ProjectContextCandidate],
    candidate_map: Mapping[str, ProjectContextCandidate],
    freshness_timestamp_ms: int,
) -> tuple[set[str], set[str], dict[str, set[str]]]:
    conflict_ids = _conflicts(candidate_map)
    expired_ids = _expired_binding_candidate_ids(candidates, freshness_timestamp_ms)
    buckets = {
        name: set()
        for name in (
            "omitted_irrelevant",
            "omitted_by_budget",
            "stale",
            "unavailable",
            "conflicting",
            "source_adapter_missing",
            "mandatory_evidence_missing",
        )
    }
    buckets["conflicting"].update(conflict_ids)
    buckets["stale"].update(expired_ids)
    for candidate in candidates:
        if problem := _problem(candidate):
            buckets[problem].add(candidate.candidate_id)
    return conflict_ids, expired_ids, buckets


def _mandatory_selection(
    candidates: Sequence[ProjectContextCandidate],
    candidate_map: Mapping[str, ProjectContextCandidate],
    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
) -> tuple[set[str], set[str]]:
    mandatory_seeds = {
        item.candidate_id
        for item in candidates
        if item.required
        or item.answer_determining
        or item.category in _HARD_INCLUDE_CATEGORIES
    }
    mandatory: set[str] = set()
    for seed in sorted(mandatory_seeds):
        closure, missing = _closure(seed, candidate_map)
        mandatory.update(closure)
        buckets["mandatory_evidence_missing"].update(missing)
    invalid = {
        item
        for item in mandatory
        if item in conflict_ids
        or item in expired_ids
        or _problem(candidate_map[item]) is not None
    }
    buckets["mandatory_evidence_missing"].update(invalid)
    eligible = mandatory - invalid
    if len(eligible) > budget.max_nodes:
        buckets["omitted_by_budget"].update(eligible)
        buckets["mandatory_evidence_missing"].update(eligible)
        return mandatory, set()
    return mandatory, set(eligible)


def _optional_candidates(
    candidates: Sequence[ProjectContextCandidate],
    mandatory: set[str],
    conflict_ids: set[str],
    expired_ids: set[str],
) -> list[ProjectContextCandidate]:
    return sorted(
        (
            item
            for item in candidates
            if item.candidate_id not in mandatory
            and item.candidate_id not in conflict_ids
            and item.candidate_id not in expired_ids
            and _problem(item) is None
        ),
        key=lambda item: (
            -item.relevance_score,
            _CATEGORY_PRIORITY[item.category],
            item.candidate_id,
        ),
    )


def _consider_optional_candidate(
    candidate: ProjectContextCandidate,
    candidate_map: Mapping[str, ProjectContextCandidate],
    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
    if candidate.relevance_score == 0:
        buckets["omitted_irrelevant"].add(candidate.candidate_id)
        return
    closure, missing = _closure(candidate.candidate_id, candidate_map)
    invalid = missing or any(
        member in conflict_ids
        or member in expired_ids
        or _problem(candidate_map[member]) is not None
        for member in closure
    )
    if invalid:
        buckets["omitted_irrelevant"].add(candidate.candidate_id)
        return
    needed = closure - selected
    if len(selected) + len(needed) > budget.max_nodes:
        buckets["omitted_by_budget"].add(candidate.candidate_id)
        return
    selected.update(needed)


def _extend_optional_selection(
    candidates: Sequence[ProjectContextCandidate],
    candidate_map: Mapping[str, ProjectContextCandidate],
    mandatory: set[str],
    conflict_ids: set[str],
    expired_ids: set[str],
    buckets: dict[str, set[str]],
    budget: ProjectionBudget,
    selected: set[str],
) -> None:
    for candidate in _optional_candidates(
        candidates, mandatory, conflict_ids, expired_ids
    ):
        _consider_optional_candidate(
            candidate,
            candidate_map,
            conflict_ids,
            expired_ids,
            buckets,
            budget,
            selected,
        )


def _selected_context_edges(
    edge_items: tuple[ProjectContextEdge, ...],
    selected: set[str],
    budget: ProjectionBudget,
) -> tuple[ProjectContextEdge, ...]:
    selected_edges = tuple(
        edge
        for edge in edge_items
        if edge.source_id in selected and edge.target_id in selected
    )
    if len(selected_edges) > budget.max_edges:
        raise ValueError(
            "selected project-context edges exceed the declared edge budget; "
            "silent edge clipping is prohibited"
        )
    return selected_edges


def _build_selection_receipt(
    objective_digest: str,
    repository_identity: RepositoryIdentity,
    selected: set[str],
    buckets: Mapping[str, set[str]],
    budget: ProjectionBudget,
) -> ProjectionSelectionReceipt:
    missing = tuple(sorted(buckets["mandatory_evidence_missing"]))
    status = SelectionStatus.INCOMPLETE if missing else SelectionStatus.COMPLETE
    return ProjectionSelectionReceipt(
        objective_digest=objective_digest,
        repository_identity_digest=repository_identity.identity_digest,
        canonical_owner=PROJECT_CANONICAL_OWNER,
        selected=tuple(sorted(selected)),
        omitted_irrelevant=tuple(sorted(buckets["omitted_irrelevant"] - selected)),
        omitted_by_budget=tuple(sorted(buckets["omitted_by_budget"] - selected)),
        stale=tuple(sorted(buckets["stale"] - selected)),
        unavailable=tuple(sorted(buckets["unavailable"] - selected)),
        conflicting=tuple(sorted(buckets["conflicting"] - selected)),
        source_adapter_missing=tuple(
            sorted(buckets["source_adapter_missing"] - selected)
        ),
        mandatory_evidence_missing=missing,
        status=status,
        budget=budget,
    )


def _selection_warnings(receipt: ProjectionSelectionReceipt) -> tuple[str, ...]:
    warnings: list[str] = []
    if receipt.mandatory_evidence_missing:
        warnings.append(
            "Mandatory project evidence is missing, stale, conflicting, unavailable, "
            "source-less, or budget-blocked."
        )
    if receipt.omitted_by_budget:
        warnings.append(
            "Optional project context was omitted by the declared task-conditioned budget."
        )
    if receipt.stale:
        warnings.append(
            "Stale project context remains receipt-visible but is not projected as current truth."
        )
    if receipt.conflicting:
        warnings.append(
            "Conflicting project context remains explicit and is not collapsed into one truth claim."
        )
    if receipt.unavailable or receipt.source_adapter_missing:
        warnings.append(
            "Unavailable project context or missing source adapters remain receipt-visible."
        )
    return tuple(warnings)


def _materialize_project_context_compilation(
    objective: str,
    project_ref: str,
    repository_identity: RepositoryIdentity,
    candidate_map: Mapping[str, ProjectContextCandidate],
    edge_items: tuple[ProjectContextEdge, ...],
    budget: ProjectionBudget,
    freshness_timestamp_ms: int,
    selected: set[str],
    buckets: dict[str, set[str]],
) -> ProjectContextCompilation:
    selected_candidates = tuple(candidate_map[item] for item in sorted(selected))
    exact_answer_source = any(
        candidate.category is CandidateCategory.SOURCE
        and candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
        and candidate.answer_determining
        for candidate in selected_candidates
    )
    if not exact_answer_source:
        buckets["mandatory_evidence_missing"].add(MISSING_SELECTED_SOURCE_ID)
    selected_edges = _selected_context_edges(edge_items, selected, budget)
    objective_digest = stable_digest({"objective": objective})
    receipt = _build_selection_receipt(
        objective_digest, repository_identity, selected, buckets, budget
    )
    timestamp_ms = _int(
        freshness_timestamp_ms,
        "freshness_timestamp_ms",
        maximum=2**63 - 1,
    )
    projection = None
    if receipt.status is SelectionStatus.COMPLETE:
        projection = _projection(
            objective,
            project_ref,
            repository_identity,
            selected_candidates,
            timestamp_ms,
            _selection_warnings(receipt),
        )
    return ProjectContextCompilation(
        objective=objective,
        project_ref=project_ref,
        objective_digest=objective_digest,
        repository_identity=repository_identity,
        projection=projection,
        selection_receipt=receipt,
        selected_candidates=selected_candidates,
        graph_edges=selected_edges,
        admissible=receipt.status is SelectionStatus.COMPLETE,
    )


def compile_project_context_projection(
    objective: str,
    *,
    project_ref: str,
    repository_identity: RepositoryIdentity,
    candidates: Sequence[ProjectContextCandidate],
    edges: Sequence[ProjectContextEdge] = (),
    budget: ProjectionBudget = ProjectionBudget(),
    freshness_timestamp_ms: int,
) -> ProjectContextCompilation:
    """Compile a deterministic minimum-sufficient read-only project projection."""
    objective = _text(objective, "objective")
    project_ref = _text(project_ref, "project_ref")
    candidate_map, edge_items = _validate_compile_context(
        repository_identity, candidates, edges, budget
    )
    freshness_timestamp_ms = _int(
        freshness_timestamp_ms,
        "freshness_timestamp_ms",
        maximum=2**63 - 1,
    )
    conflict_ids, expired_ids, buckets = _selection_buckets(
        candidates, candidate_map, freshness_timestamp_ms
    )
    mandatory, selected = _mandatory_selection(
        candidates,
        candidate_map,
        conflict_ids,
        expired_ids,
        buckets,
        budget,
    )
    _extend_optional_selection(
        candidates,
        candidate_map,
        mandatory,
        conflict_ids,
        expired_ids,
        buckets,
        budget,
        selected,
    )
    return _materialize_project_context_compilation(
        objective,
        project_ref,
        repository_identity,
        candidate_map,
        edge_items,
        budget,
        freshness_timestamp_ms,
        selected,
        buckets,
    )


def _provenance_inputs(
    compilation: ProjectContextCompilation,
    start_ids: Sequence[str],
    max_hops: int,
    max_nodes: int,
) -> tuple[
    tuple[str, ...],
    int,
    int,
    dict[str, ProjectContextCandidate],
    dict[str, list[ProjectContextEdge]],
]:
    if type(compilation) is not ProjectContextCompilation:
        raise ValueError("compilation must be exact ProjectContextCompilation")
    starts = _ids(start_ids, "start_ids", maximum=64)
    max_hops = _int(max_hops, "max_hops", minimum=1, maximum=16)
    max_nodes = _int(max_nodes, "max_nodes", minimum=1, maximum=256)
    if len(starts) > max_nodes:
        raise ValueError("provenance start_ids exceed max_nodes")
    node_map = {
        item.candidate_id: item for item in compilation.selected_candidates
    }
    missing = sorted(set(starts) - set(node_map))
    if missing:
        raise ValueError(f"provenance start is outside selected context: {missing}")
    incoming: dict[str, list[ProjectContextEdge]] = {
        node_id: [] for node_id in node_map
    }
    for edge in compilation.graph_edges:
        incoming[edge.target_id].append(edge)
    for values in incoming.values():
        values.sort(
            key=lambda edge: (
                edge.source_id,
                edge.relation,
                edge.truth_class.value,
            )
        )
    return starts, max_hops, max_nodes, node_map, incoming


def _walk_provenance(
    starts: tuple[str, ...],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    max_hops: int,
    max_nodes: int,
) -> tuple[set[str], set[ProjectContextEdge], set[str]]:
    seen = set(starts)
    frontier = list(starts)
    traversed: set[ProjectContextEdge] = set()
    truncated: set[str] = set()
    for _ in range(max_hops):
        next_frontier: list[str] = []
        for target in sorted(frontier):
            for edge in incoming.get(target, ()):
                if edge.source_id in seen:
                    traversed.add(edge)
                    continue
                if len(seen) >= max_nodes:
                    truncated.add(edge.source_id)
                    continue
                seen.add(edge.source_id)
                next_frontier.append(edge.source_id)
                traversed.add(edge)
        if not next_frontier:
            break
        frontier = sorted(set(next_frontier))
    else:
        for target in frontier:
            truncated.update(
                edge.source_id
                for edge in incoming.get(target, ())
                if edge.source_id not in seen
            )
    return seen, traversed, truncated


def _provenance_start_is_source_complete(
    start_id: str,
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    traversed: set[ProjectContextEdge],
) -> bool:
    memo: dict[str, bool] = {}
    visiting: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in memo:
            return memo[node_id]
        if node_id in visiting:
            return False
        visiting.add(node_id)
        predecessors = [
            edge for edge in incoming.get(node_id, ()) if edge in traversed
        ]
        candidate = node_map[node_id]
        if not predecessors:
            result = (
                candidate.category is CandidateCategory.SOURCE
                and candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
            )
        else:
            result = all(
                edge.truth_class in _AUTHORITATIVE_EDGE_TRUTH
                and visit(edge.source_id)
                for edge in predecessors
            )
        visiting.remove(node_id)
        memo[node_id] = result
        return result

    return visit(start_id)


def _provenance_summary(
    starts: Sequence[str],
    node_map: Mapping[str, ProjectContextCandidate],
    incoming: Mapping[str, Sequence[ProjectContextEdge]],
    seen: set[str],
    traversed: set[ProjectContextEdge],
) -> tuple[
    list[ProjectContextCandidate], list[str], list[str], list[str], bool, bool
]:
    nodes = [node_map[item] for item in sorted(seen)]
    source_ids = [
        item.candidate_id
        for item in nodes
        if item.category is CandidateCategory.SOURCE
    ]
    exact_source_ids = [
        item.candidate_id
        for item in nodes
        if item.category is CandidateCategory.SOURCE
        and item.truth_class is CandidateTruthClass.EXACT_CURRENT
    ]
    root_ids = sorted(
        node_id
        for node_id in seen
        if not any(
            edge.source_id in seen for edge in incoming.get(node_id, ())
        )
    )
    starts_are_source_complete = bool(starts) and all(
        _provenance_start_is_source_complete(
            start_id, node_map, incoming, traversed
        )
        for start_id in starts
    )
    authoritative_path = all(
        edge.truth_class in _AUTHORITATIVE_EDGE_TRUTH for edge in traversed
    )
    return (
        nodes,
        source_ids,
        exact_source_ids,
        root_ids,
        starts_are_source_complete,
        authoritative_path,
    )


def _provenance_result(
    compilation: ProjectContextCompilation,
    starts: tuple[str, ...],
    nodes: Sequence[ProjectContextCandidate],
    traversed: set[ProjectContextEdge],
    source_ids: Sequence[str],
    exact_source_ids: Sequence[str],
    root_ids: Sequence[str],
    truncated: set[str],
    starts_are_source_complete: bool,
    authoritative_path: bool,
) -> dict[str, Any]:
    result = {
        "version": PROJECT_CONTEXT_PROVENANCE_VERSION,
        "compilation_digest": compilation.compilation_digest,
        "start_ids": list(starts),
        "node_ids": [item.candidate_id for item in nodes],
        "nodes": [item.to_dict() for item in nodes],
        "edges": [
            item.to_dict()
            for item in sorted(
                traversed,
                key=lambda edge: (
                    edge.source_id,
                    edge.target_id,
                    edge.relation,
                    edge.truth_class.value,
                ),
            )
        ],
        "source_ids": list(source_ids),
        "exact_source_ids": list(exact_source_ids),
        "source_reached": bool(source_ids),
        "provenance_root_ids": list(root_ids),
        "truncated_frontier": sorted(truncated),
        "authoritative_path": authoritative_path,
        "source_complete": (
            starts_are_source_complete and authoritative_path and not truncated
        ),
        "bounded": True,
    }
    result["trace_digest"] = stable_digest(result)
    return result


def trace_project_context_provenance(
    compilation: ProjectContextCompilation,
    start_ids: Sequence[str],
    *,
    max_hops: int = 4,
    max_nodes: int = 64,
) -> dict[str, Any]:
    """Trace a bounded authoritative predecessor closure without overclaiming completeness."""
    starts, max_hops, max_nodes, node_map, incoming = _provenance_inputs(
        compilation, start_ids, max_hops, max_nodes
    )
    seen, traversed, truncated = _walk_provenance(
        starts, incoming, max_hops, max_nodes
    )
    summary = _provenance_summary(starts, node_map, incoming, seen, traversed)
    return _provenance_result(
        compilation,
        starts,
        summary[0],
        traversed,
        summary[1],
        summary[2],
        summary[3],
        truncated,
        summary[4],
        summary[5],
    )


def _normalized_current_bindings(
    current_bindings: Mapping[str, str],
) -> dict[str, str]:
    if not isinstance(current_bindings, Mapping):
        raise TypeError("current_bindings must be a mapping")
    normalized: dict[str, str] = {}
    for key, value in current_bindings.items():
        normalized_key = _text(key, "binding key")
        if normalized_key in normalized:
            raise ValueError("current_bindings contains duplicate normalized keys")
        normalized[normalized_key] = _digest(value, "binding digest")
    return normalized


def _freshness_reasons(
    compilation: ProjectContextCompilation,
    current_repository_identity: RepositoryIdentity,
    current_bindings: Mapping[str, str],
    observed_at_ms: int,
) -> list[str]:
    reasons: list[str] = []
    if (
        compilation.repository_identity.to_dict()
        != current_repository_identity.to_dict()
    ):
        reasons.append("repository_identity_changed")
    for candidate in compilation.selected_candidates:
        if candidate.reference is None:
            reasons.append(
                f"selected_reference_missing:{candidate.candidate_id}"
            )
            continue
        if candidate.reference.freshness_class not in {"CURRENT", "BOUNDED"}:
            reasons.append(f"reference_stale:{candidate.candidate_id}")
        for binding in candidate.temporal_bindings:
            current = current_bindings.get(binding.key)
            if current is None:
                reasons.append(f"binding_missing:{binding.key}")
            elif current != binding.digest:
                reasons.append(f"binding_changed:{binding.key}")
            if binding.expires_at_ms and observed_at_ms >= binding.expires_at_ms:
                reasons.append(f"binding_expired:{binding.key}")
    return sorted(set(reasons))


def validate_project_context_freshness(
    compilation: ProjectContextCompilation,
    *,
    current_repository_identity: RepositoryIdentity,
    current_bindings: Mapping[str, str],
    observed_at_ms: int,
) -> dict[str, Any]:
    """Require recompilation after repository or selected temporal identity drift."""
    if type(compilation) is not ProjectContextCompilation:
        raise ValueError("compilation must be exact ProjectContextCompilation")
    if type(current_repository_identity) is not RepositoryIdentity:
        raise ValueError("current_repository_identity must be exact RepositoryIdentity")
    observed_at_ms = _int(
        observed_at_ms,
        "observed_at_ms",
        maximum=2**63 - 1,
    )
    normalized = _normalized_current_bindings(current_bindings)
    reasons = _freshness_reasons(
        compilation,
        current_repository_identity,
        normalized,
        observed_at_ms,
    )
    result = {
        "version": PROJECT_CONTEXT_FRESHNESS_VERSION,
        "compilation_digest": compilation.compilation_digest,
        "valid": not reasons,
        "recompile_required": bool(reasons),
        "reasons": reasons,
        "observed_at_ms": observed_at_ms,
        "mutation_performed": False,
    }
    result["validation_digest"] = stable_digest(result)
    return result


__all__ = [
    "PROJECT_CONTEXT_COMPILER_VERSION",
    "PROJECTION_SELECTION_RECEIPT_VERSION",
    "PROJECT_CONTEXT_COMPILATION_VERSION",
    "PROJECT_CONTEXT_PROVENANCE_VERSION",
    "PROJECT_CONTEXT_FRESHNESS_VERSION",
    "MISSING_SELECTED_SOURCE_ID",
    "MEMORY_LIFECYCLE_PHASES",
    "CandidateCategory",
    "CandidateTruthClass",
    "CandidateAvailability",
    "EdgeTruthClass",
    "SelectionStatus",
    "TemporalBindingKind",
    "ContextAuthorityClass",
    "TemporalBinding",
    "ProjectContextCandidate",
    "ProjectContextEdge",
    "ProjectionBudget",
    "ProjectionSelectionReceipt",
    "ProjectContextCompilation",
    "compile_project_context_projection",
    "trace_project_context_provenance",
    "validate_project_context_freshness",
]
