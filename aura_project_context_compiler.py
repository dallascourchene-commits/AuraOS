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
        object.__setattr__(self, "candidate_id", _id(self.candidate_id, "candidate_id"))
        object.__setattr__(self, "category", _enum(CandidateCategory, self.category, "category"))
        object.__setattr__(self, "source_adapter", _id(self.source_adapter, "source_adapter"))
        object.__setattr__(self, "origin_ref", _text(self.origin_ref, "origin_ref"))
        object.__setattr__(
            self,
            "authority_class",
            _enum(ContextAuthorityClass, self.authority_class, "authority_class"),
        )
        object.__setattr__(
            self,
            "truth_class",
            _enum(CandidateTruthClass, self.truth_class, "truth_class"),
        )
        object.__setattr__(
            self,
            "availability",
            _enum(CandidateAvailability, self.availability, "availability"),
        )
        object.__setattr__(
            self,
            "relevance_score",
            _int(self.relevance_score, "relevance_score", maximum=1_000_000),
        )
        if type(self.required) is not bool or type(self.answer_determining) is not bool:
            raise TypeError("required and answer_determining must be booleans")
        object.__setattr__(
            self,
            "dependency_ids",
            _ids(self.dependency_ids, "dependency_ids", maximum=MAX_DEPENDENCIES),
        )
        if type(self.conflict_key) is not str:
            raise TypeError("conflict_key must be a string")
        if self.conflict_key:
            object.__setattr__(self, "conflict_key", _id(self.conflict_key, "conflict_key"))
        bindings = tuple(self.temporal_bindings)
        if len(bindings) > MAX_TEMPORAL_BINDINGS or any(
            type(item) is not TemporalBinding for item in bindings
        ):
            raise ValueError(
                "temporal_bindings must contain bounded exact TemporalBinding records"
            )
        if len({item.key for item in bindings}) != len(bindings):
            raise ValueError("temporal_bindings contains duplicate binding keys")
        object.__setattr__(
            self,
            "temporal_bindings",
            tuple(sorted(bindings, key=lambda item: item.key)),
        )

        if self.availability is CandidateAvailability.AVAILABLE:
            if type(self.reference) is not CanonicalReference:
                raise ValueError("available candidate requires an exact CanonicalReference")
        elif self.reference is not None:
            raise ValueError("unavailable candidate must not carry a canonical reference")

        authoritative = {
            CandidateTruthClass.EXACT_CURRENT,
            CandidateTruthClass.DERIVED_VERIFIED,
        }
        if self.truth_class in authoritative:
            if self.reference is None or self.reference.truth_class != "EXACT":
                raise ValueError(
                    "authoritative read candidate requires an EXACT canonical reference"
                )
            expected = (
                ContextAuthorityClass.CANONICAL_READ
                if self.truth_class is CandidateTruthClass.EXACT_CURRENT
                else ContextAuthorityClass.DERIVED_READ
            )
            if self.authority_class is not expected:
                raise ValueError("candidate authority class does not match its truth class")
            if self.origin_ref != self.reference.canonical_ref:
                raise ValueError(
                    "authoritative candidate origin_ref must equal its canonical reference origin"
                )
        elif self.authority_class is not ContextAuthorityClass.ADVISORY_NONE:
            raise ValueError(
                "advisory/hypothesis/stale/unavailable candidates cannot carry authority"
            )

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
        if self.version != PROJECTION_SELECTION_RECEIPT_VERSION:
            raise ValueError("unsupported projection selection receipt version")
        object.__setattr__(
            self,
            "objective_digest",
            _digest(self.objective_digest, "objective_digest"),
        )
        object.__setattr__(
            self,
            "repository_identity_digest",
            _digest(self.repository_identity_digest, "repository_identity_digest"),
        )
        if _id(self.canonical_owner, "canonical_owner") != PROJECT_CANONICAL_OWNER:
            raise ValueError("canonical_owner must remain the unified continuity owner")
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
                self,
                name,
                _ids(getattr(self, name), name, maximum=MAX_CANDIDATES),
            )
        selected_ids = set(self.selected)
        for name in omission_fields:
            overlap = selected_ids.intersection(getattr(self, name))
            if overlap:
                raise ValueError(
                    f"selection receipt cannot mark selected ids as {name}: {sorted(overlap)}"
                )
        object.__setattr__(
            self,
            "status",
            _enum(SelectionStatus, self.status, "selection status"),
        )
        if type(self.budget) is not ProjectionBudget:
            raise ValueError("selection receipt requires exact ProjectionBudget")
        if self.status is SelectionStatus.COMPLETE and self.mandatory_evidence_missing:
            raise ValueError("COMPLETE selection cannot have missing mandatory evidence")
        if self.status is SelectionStatus.INCOMPLETE and not self.mandatory_evidence_missing:
            raise ValueError("INCOMPLETE selection must identify missing mandatory evidence")
        expected = stable_digest(self.to_dict(include_digest=False))
        if self.receipt_digest and self.receipt_digest != expected:
            raise ValueError("selection receipt digest mismatch")
        object.__setattr__(self, "receipt_digest", expected)

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


@dataclass(frozen=True)
class ProjectContextCompilation:
    objective: str
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
        if self.version != PROJECT_CONTEXT_COMPILATION_VERSION:
            raise ValueError("unsupported project-context compilation version")
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(
            self,
            "objective_digest",
            _digest(self.objective_digest, "objective_digest"),
        )
        expected_objective_digest = stable_digest({"objective": self.objective})
        if self.objective_digest != expected_objective_digest:
            raise ValueError("objective_digest is not bound to objective")
        if type(self.repository_identity) is not RepositoryIdentity:
            raise ValueError("compilation requires exact RepositoryIdentity")
        if self.projection is not None and type(self.projection) is not ProjectContextProjection:
            raise ValueError("projection must be exact ProjectContextProjection")
        if type(self.selection_receipt) is not ProjectionSelectionReceipt:
            raise ValueError("selection_receipt must be exact ProjectionSelectionReceipt")
        if self.selection_receipt.objective_digest != self.objective_digest:
            raise ValueError("selection receipt objective is not bound to compilation")
        if (
            self.selection_receipt.repository_identity_digest
            != self.repository_identity.identity_digest
        ):
            raise ValueError("selection receipt repository identity is not bound to compilation")
        if self.selection_receipt.status is SelectionStatus.COMPLETE and self.projection is None:
            raise ValueError("COMPLETE selection must emit the canonical PR1 projection")
        if self.selection_receipt.status is SelectionStatus.INCOMPLETE and self.projection is not None:
            raise ValueError("INCOMPLETE selection must not expose a canonical PR1 projection")

        selected = tuple(self.selected_candidates)
        if any(type(item) is not ProjectContextCandidate for item in selected):
            raise ValueError("selected_candidates must be exact records")
        selected = tuple(sorted(selected, key=lambda item: item.candidate_id))
        if len({item.candidate_id for item in selected}) != len(selected):
            raise ValueError("selected_candidates contains duplicate candidate ids")
        if len(
            {
                item.reference.reference_id
                for item in selected
                if item.reference is not None
            }
        ) != len(selected):
            raise ValueError("selected candidates must have unique canonical references")
        object.__setattr__(self, "selected_candidates", selected)
        selected_ids = tuple(item.candidate_id for item in selected)
        if selected_ids != self.selection_receipt.selected:
            raise ValueError("selected candidate identities do not match selection receipt")
        selected_map = {item.candidate_id: item for item in selected}
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
        exact_answer_sources = tuple(
            item
            for item in selected
            if item.category is CandidateCategory.SOURCE
            and item.truth_class is CandidateTruthClass.EXACT_CURRENT
            and item.answer_determining
        )
        if (
            self.selection_receipt.status is SelectionStatus.COMPLETE
            and not exact_answer_sources
        ):
            raise ValueError(
                "COMPLETE selection requires an exact-current answer-determining source"
            )

        edges = tuple(self.graph_edges)
        if any(type(item) is not ProjectContextEdge for item in edges):
            raise ValueError("graph_edges must be exact records")
        selected_id_set = set(selected_ids)
        if any(
            edge.source_id not in selected_id_set or edge.target_id not in selected_id_set
            for edge in edges
        ):
            raise ValueError("compiled graph edge escapes selected candidate set")
        object.__setattr__(
            self,
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

        if self.projection is not None:
            if self.projection.objective_digest != self.objective_digest:
                raise ValueError("projection objective is not bound to compilation")
            if self.projection.canonical_owner != PROJECT_CANONICAL_OWNER:
                raise ValueError("projection canonical owner is not bound to PR3 owner")
            if (
                self.projection.repository_identity.to_dict()
                != self.repository_identity.to_dict()
            ):
                raise ValueError("projection repository identity is not bound to compilation")
            projection_refs = (
                self.projection.artifact_evidence_refs
                + self.projection.decision_refs
                + self.projection.rejected_alternative_refs
                + self.projection.unresolved_question_refs
                + self.projection.assumption_refs
                + self.projection.capability_refs
                + self.projection.relationship_refs
                + self.projection.blocker_refs
                + self.projection.next_action_refs
            )
            projection_ref_ids = {item.reference_id for item in projection_refs}
            selected_ref_ids = {
                item.reference.reference_id
                for item in selected
                if item.reference is not None
            }
            if projection_ref_ids != selected_ref_ids:
                raise ValueError("projection references do not match selected candidates")

        if type(self.admissible) is not bool:
            raise TypeError("admissible must be a boolean")
        expected_admission = self.selection_receipt.status is SelectionStatus.COMPLETE
        if self.admissible != expected_admission:
            raise ValueError("admissible must equal COMPLETE receipt with emitted projection")
        expected = stable_digest(self.to_dict(include_digest=False))
        if self.compilation_digest and self.compilation_digest != expected:
            raise ValueError("project-context compilation digest mismatch")
        object.__setattr__(self, "compilation_digest", expected)

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        body = {
            "version": self.version,
            "objective": self.objective,
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
    assert candidate.reference is not None
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
    for candidate in candidates.values():
        if (
            candidate.conflict_key
            and _problem(candidate) is None
            and candidate.reference is not None
        ):
            groups.setdefault(candidate.conflict_key, []).append(candidate)
    result: set[str] = set()
    for items in groups.values():
        if len(
            {item.reference.digest for item in items if item.reference is not None}
        ) > 1:
            result.update(item.candidate_id for item in items)
    return result


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
        assert candidate.reference is not None
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
    if type(repository_identity) is not RepositoryIdentity:
        raise ValueError("repository_identity must be exact PR1 RepositoryIdentity")
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
            f"edge endpoint is outside the task-conditioned candidate set: {unknown[:5]}"
        )

    conflict_ids = _conflicts(candidate_map)
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
    for candidate in candidates:
        if problem := _problem(candidate):
            buckets[problem].add(candidate.candidate_id)

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
    invalid_mandatory = {
        item
        for item in mandatory
        if item in conflict_ids or _problem(candidate_map[item]) is not None
    }
    buckets["mandatory_evidence_missing"].update(invalid_mandatory)
    eligible_mandatory = mandatory - invalid_mandatory

    selected: set[str] = set()
    if len(eligible_mandatory) > budget.max_nodes:
        buckets["omitted_by_budget"].update(eligible_mandatory)
        buckets["mandatory_evidence_missing"].update(eligible_mandatory)
    else:
        selected.update(eligible_mandatory)

    optional = sorted(
        (
            item
            for item in candidates
            if item.candidate_id not in mandatory
            and item.candidate_id not in conflict_ids
            and _problem(item) is None
        ),
        key=lambda item: (
            -item.relevance_score,
            _CATEGORY_PRIORITY[item.category],
            item.candidate_id,
        ),
    )
    for candidate in optional:
        if candidate.relevance_score == 0:
            buckets["omitted_irrelevant"].add(candidate.candidate_id)
            continue
        closure, missing = _closure(candidate.candidate_id, candidate_map)
        if missing or any(
            member in conflict_ids or _problem(candidate_map[member]) is not None
            for member in closure
        ):
            buckets["omitted_irrelevant"].add(candidate.candidate_id)
            continue
        needed = closure - selected
        if len(selected) + len(needed) > budget.max_nodes:
            buckets["omitted_by_budget"].add(candidate.candidate_id)
            continue
        selected.update(needed)

    selected_candidates = tuple(candidate_map[item] for item in sorted(selected))
    exact_answer_sources = tuple(
        candidate
        for candidate in selected_candidates
        if candidate.category is CandidateCategory.SOURCE
        and candidate.truth_class is CandidateTruthClass.EXACT_CURRENT
        and candidate.answer_determining
    )
    if not exact_answer_sources:
        buckets["mandatory_evidence_missing"].add(MISSING_SELECTED_SOURCE_ID)

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

    missing = tuple(sorted(buckets["mandatory_evidence_missing"]))
    status = SelectionStatus.INCOMPLETE if missing else SelectionStatus.COMPLETE
    objective_digest = stable_digest({"objective": objective})
    receipt = ProjectionSelectionReceipt(
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
    warnings: list[str] = []
    if missing:
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
    timestamp_ms = _int(
        freshness_timestamp_ms,
        "freshness_timestamp_ms",
        maximum=2**63 - 1,
    )
    projection = None
    if status is SelectionStatus.COMPLETE:
        projection = _projection(
            objective,
            project_ref,
            repository_identity,
            selected_candidates,
            timestamp_ms,
            warnings,
        )
    return ProjectContextCompilation(
        objective=objective,
        objective_digest=objective_digest,
        repository_identity=repository_identity,
        projection=projection,
        selection_receipt=receipt,
        selected_candidates=selected_candidates,
        graph_edges=selected_edges,
        admissible=status is SelectionStatus.COMPLETE,
    )


def trace_project_context_provenance(
    compilation: ProjectContextCompilation,
    start_ids: Sequence[str],
    *,
    max_hops: int = 4,
    max_nodes: int = 64,
) -> dict[str, Any]:
    """Trace a bounded authoritative predecessor closure without overclaiming completeness."""
    if type(compilation) is not ProjectContextCompilation:
        raise ValueError("compilation must be exact ProjectContextCompilation")
    starts = _ids(start_ids, "start_ids", maximum=64)
    max_hops = _int(max_hops, "max_hops", minimum=1, maximum=16)
    max_nodes = _int(max_nodes, "max_nodes", minimum=1, maximum=256)
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
    provenance_root_ids = sorted(
        node_id
        for node_id in seen
        if not any(edge.source_id in seen for edge in incoming.get(node_id, ()))
    )
    roots_are_exact_sources = bool(provenance_root_ids) and all(
        node_map[node_id].category is CandidateCategory.SOURCE
        and node_map[node_id].truth_class is CandidateTruthClass.EXACT_CURRENT
        for node_id in provenance_root_ids
    )
    authoritative_path = all(
        edge.truth_class in _AUTHORITATIVE_EDGE_TRUTH for edge in traversed
    )
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
        "source_ids": source_ids,
        "exact_source_ids": exact_source_ids,
        "source_reached": bool(source_ids),
        "provenance_root_ids": provenance_root_ids,
        "truncated_frontier": sorted(truncated),
        "authoritative_path": authoritative_path,
        "source_complete": roots_are_exact_sources and authoritative_path and not truncated,
        "bounded": True,
    }
    result["trace_digest"] = stable_digest(result)
    return result


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
    if not isinstance(current_bindings, Mapping):
        raise TypeError("current_bindings must be a mapping")
    observed_at_ms = _int(
        observed_at_ms,
        "observed_at_ms",
        maximum=2**63 - 1,
    )
    normalized = {
        _text(key, "binding key"): _digest(value, "binding digest")
        for key, value in current_bindings.items()
    }
    reasons: list[str] = []
    if compilation.repository_identity.to_dict() != current_repository_identity.to_dict():
        reasons.append("repository_identity_changed")
    for candidate in compilation.selected_candidates:
        if candidate.reference is None:
            reasons.append(f"selected_reference_missing:{candidate.candidate_id}")
            continue
        if candidate.reference.freshness_class not in {"CURRENT", "BOUNDED"}:
            reasons.append(f"reference_stale:{candidate.candidate_id}")
        for binding in candidate.temporal_bindings:
            current = normalized.get(binding.key)
            if current is None:
                reasons.append(f"binding_missing:{binding.key}")
            elif current != binding.digest:
                reasons.append(f"binding_changed:{binding.key}")
            if binding.expires_at_ms and observed_at_ms >= binding.expires_at_ms:
                reasons.append(f"binding_expired:{binding.key}")
    reasons = sorted(set(reasons))
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
