"""Revisioned, digest-bound refactor skeletons for governed AuraOS work.

The skeleton is a planning and continuity object. It never grants patch, commit,
push, merge, deployment, policy, or runtime authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import time
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

REFACTOR_SKELETON_VERSION = "AURA_REFACTOR_SKELETON_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
DEFAULT_STORE_PATH = Path("Aura_Memory/refactor_skeletons")

SKELETON_STATUSES = frozenset(
    {
        "DRAFT", "NEEDS_GROUNDING", "GROUNDED", "PLANNED", "READY_FOR_ACT",
        "STAGED", "VERIFYING", "REPAIR_REQUIRED", "COUNCIL_REPLAN_REQUIRED",
        "READY_FOR_HUMAN_REVIEW", "ACCEPTED", "REJECTED", "ROLLED_BACK",
        "SUPERSEDED",
    }
)
REUSE_DECISIONS = frozenset(
    {
        "REUSE", "EXTEND_CANONICAL_OWNER", "ADD_NARROW_ADAPTER",
        "CONSOLIDATE_DUPLICATE", "TRUE_NEW_CAPABILITY", "DEFER",
    }
)
INTEGRATION_DISPOSITIONS = frozenset(
    {
        "INTEGRATED", "INTENTIONALLY_LOCAL", "ADAPTER_REQUIRED", "DEFERRED",
        "BLOCKED", "NOT_APPLICABLE", "DEPRECATED", "SUPERSEDED",
    }
)
_SKELETON_ID = re.compile(r"^RFS-[0-9a-f]{20}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REVISION_FILE = re.compile(r"^r(?P<revision>[0-9]{8})-(?P<digest>[0-9a-f]{64})\.json$")


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not permitted")
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        frozen = {
            str(key): _freeze(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        items = tuple(_freeze(item) for item in value)
        return tuple(sorted(items, key=lambda item: json.dumps(_thaw(item), sort_keys=True)))
    raise TypeError(f"unsupported skeleton value type: {type(value).__name__}")


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        _thaw(_freeze(value)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    candidate = Path(path)
    digest = hashlib.sha256()
    with candidate.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_strings(values: Iterable[Any] | None) -> tuple[str, ...]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values or ():
        text = str(value).strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return tuple(result)


def _immutable_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    frozen = _freeze(dict(value or {}))
    if not isinstance(frozen, Mapping):
        raise TypeError("mapping value did not freeze to a mapping")
    return frozen


def _normalize_repo_path(value: Any) -> str:
    text = str(value).strip()
    if not text or "\\" in text:
        raise ValueError(f"invalid repository path: {text!r}")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"repository path must be normalized and relative: {text!r}")
    return path.as_posix()


def _resolve_repo_file(repo_root: str | Path, relative_path: str) -> Path:
    root = Path(repo_root).resolve()
    candidate = (root / Path(*PurePosixPath(relative_path).parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"source path escapes repository root: {relative_path}") from exc
    if not candidate.is_file():
        raise ValueError(f"source file does not exist: {relative_path}")
    return candidate


@dataclass(frozen=True)
class SourceSpan:
    path: str
    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        normalized = _normalize_repo_path(self.path)
        if normalized != self.path:
            raise ValueError("source span path is not normalized")
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("source span line range is invalid")

    @classmethod
    def create(cls, path: str, start_line: int, end_line: int) -> "SourceSpan":
        return cls(
            path=_normalize_repo_path(path),
            start_line=int(start_line),
            end_line=int(end_line),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceSpan":
        return cls.create(
            str(value.get("path", "")),
            int(value.get("start_line", 0)),
            int(value.get("end_line", 0)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IntegrationDisposition:
    structure: str
    disposition: str
    reason: str

    def __post_init__(self) -> None:
        if not self.structure.strip():
            raise ValueError("integration structure is required")
        if self.disposition not in INTEGRATION_DISPOSITIONS:
            raise ValueError(f"invalid integration disposition: {self.disposition}")
        if not self.reason.strip():
            raise ValueError("integration reason is required")

    @classmethod
    def create(
        cls, structure: str, disposition: str, reason: str
    ) -> "IntegrationDisposition":
        return cls(
            str(structure).strip(),
            str(disposition).upper(),
            str(reason).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _node_payload(node: "RefactorSkeletonNode") -> dict[str, Any]:
    return {
        "node_id": node.node_id,
        "objective": node.objective,
        "canonical_owner": node.canonical_owner,
        "reuse_decision": node.reuse_decision,
        "target_files": list(node.target_files),
        "target_symbols": list(node.target_symbols),
        "exact_source_hashes": _thaw(node.exact_source_hashes),
        "exact_source_spans": [item.to_dict() for item in node.exact_source_spans],
        "dependencies": list(node.dependencies),
        "invariants": list(node.invariants),
        "acceptance_criteria": list(node.acceptance_criteria),
        "required_tests": list(node.required_tests),
        "risk_lanes": list(node.risk_lanes),
        "authority_boundary": node.authority_boundary,
        "status": node.status,
        "revision": node.revision,
        "prior_revision_digest": node.prior_revision_digest,
        "stage_digest": node.stage_digest,
        "verifier_digest": node.verifier_digest,
        "repair_history": _thaw(node.repair_history),
        "integration_dispositions": [item.to_dict() for item in node.integration_dispositions],
        "metadata": _thaw(node.metadata),
    }


@dataclass(frozen=True)
class RefactorSkeletonNode:
    node_id: str
    objective: str
    canonical_owner: str
    reuse_decision: str
    target_files: tuple[str, ...] = ()
    target_symbols: tuple[str, ...] = ()
    exact_source_hashes: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    exact_source_spans: tuple[SourceSpan, ...] = ()
    dependencies: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    required_tests: tuple[str, ...] = ()
    risk_lanes: tuple[str, ...] = ()
    authority_boundary: str = "planning_only"
    status: str = "DRAFT"
    revision: int = 1
    prior_revision_digest: str = ""
    stage_digest: str = ""
    verifier_digest: str = ""
    repair_history: tuple[Mapping[str, Any], ...] = ()
    integration_dispositions: tuple[IntegrationDisposition, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    node_digest: str = ""

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id is required")
        if not self.objective.strip():
            raise ValueError("node objective is required")
        if not self.canonical_owner.strip():
            raise ValueError("canonical_owner is required")
        if self.reuse_decision not in REUSE_DECISIONS:
            raise ValueError(f"invalid reuse decision: {self.reuse_decision}")
        if self.status not in SKELETON_STATUSES:
            raise ValueError(f"invalid skeleton node status: {self.status}")
        if self.revision < 1:
            raise ValueError("node revision must be positive")
        if self.node_id in self.dependencies:
            raise ValueError("node cannot depend on itself")
        if len(self.target_files) != len(set(self.target_files)):
            raise ValueError("duplicate target file")
        structures = [item.structure for item in self.integration_dispositions]
        if len(structures) != len(set(structures)):
            raise ValueError("duplicate integration disposition structure")
        if not isinstance(self.exact_source_hashes, MappingProxyType):
            raise ValueError("exact_source_hashes must be immutable")
        if not isinstance(self.metadata, MappingProxyType):
            raise ValueError("metadata must be immutable")
        if any(not isinstance(item, MappingProxyType) for item in self.repair_history):
            raise ValueError("repair_history entries must be immutable")
        expected = _digest(_node_payload(self))
        if not self.node_digest or self.node_digest != expected:
            raise ValueError("node_digest does not match canonical node content")
        if self.status == "READY_FOR_ACT":
            self._validate_ready_evidence_shape()

    def _validate_ready_evidence_shape(self) -> None:
        if not self.target_files:
            raise ValueError("READY_FOR_ACT requires target_files")
        if not self.required_tests:
            raise ValueError("READY_FOR_ACT requires required_tests")
        keys = set(self.exact_source_hashes)
        targets = set(self.target_files)
        if keys != targets:
            raise ValueError(
                "READY_FOR_ACT requires exactly one source hash per target file"
            )
        invalid_hashes = [
            path
            for path, value in self.exact_source_hashes.items()
            if not _SHA256.fullmatch(str(value))
        ]
        if invalid_hashes:
            raise ValueError(f"invalid SHA-256 source hashes: {invalid_hashes}")
        span_paths = {item.path for item in self.exact_source_spans}
        missing_spans = sorted(targets - span_paths)
        foreign_spans = sorted(span_paths - targets)
        if missing_spans or foreign_spans:
            raise ValueError(
                f"exact source spans do not match targets; "
                f"missing={missing_spans}, foreign={foreign_spans}"
            )

    @classmethod
    def create(
        cls,
        *,
        node_id: str,
        objective: str,
        canonical_owner: str,
        reuse_decision: str,
        target_files: Sequence[str] = (),
        target_symbols: Sequence[str] = (),
        exact_source_hashes: Mapping[str, str] | None = None,
        exact_source_spans: Sequence[SourceSpan | Mapping[str, Any]] = (),
        dependencies: Sequence[str] = (),
        invariants: Sequence[str] = (),
        acceptance_criteria: Sequence[str] = (),
        required_tests: Sequence[str] = (),
        risk_lanes: Sequence[str] = (),
        authority_boundary: str = "planning_only",
        status: str = "DRAFT",
        revision: int = 1,
        prior_revision_digest: str = "",
        stage_digest: str = "",
        verifier_digest: str = "",
        repair_history: Sequence[Mapping[str, Any]] = (),
        integration_dispositions: Sequence[
            IntegrationDisposition | Mapping[str, Any]
        ] = (),
        metadata: Mapping[str, Any] | None = None,
    ) -> "RefactorSkeletonNode":
        files = tuple(_normalize_repo_path(item) for item in _stable_strings(target_files))
        hashes = MappingProxyType(
            {
                _normalize_repo_path(key): str(value).strip().lower()
                for key, value in sorted(dict(exact_source_hashes or {}).items())
                if str(key).strip() and str(value).strip()
            }
        )
        spans = tuple(
            item if isinstance(item, SourceSpan) else SourceSpan.from_dict(item)
            for item in exact_source_spans
        )
        integrations = tuple(
            item
            if isinstance(item, IntegrationDisposition)
            else IntegrationDisposition.create(
                str(item.get("structure", "")),
                str(item.get("disposition", "")),
                str(item.get("reason", "")),
            )
            for item in integration_dispositions
        )
        fields = {
            "node_id": str(node_id).strip(),
            "objective": str(objective).strip(),
            "canonical_owner": str(canonical_owner).strip(),
            "reuse_decision": str(reuse_decision).upper(),
            "target_files": files,
            "target_symbols": _stable_strings(target_symbols),
            "exact_source_hashes": hashes,
            "exact_source_spans": spans,
            "dependencies": _stable_strings(dependencies),
            "invariants": _stable_strings(invariants),
            "acceptance_criteria": _stable_strings(acceptance_criteria),
            "required_tests": _stable_strings(required_tests),
            "risk_lanes": _stable_strings(risk_lanes),
            "authority_boundary": str(authority_boundary).strip() or "planning_only",
            "status": str(status).upper(),
            "revision": int(revision),
            "prior_revision_digest": str(prior_revision_digest),
            "stage_digest": str(stage_digest),
            "verifier_digest": str(verifier_digest),
            "repair_history": tuple(_immutable_mapping(item) for item in repair_history),
            "integration_dispositions": integrations,
            "metadata": _immutable_mapping(metadata),
        }
        provisional = object.__new__(cls)
        for name, value in fields.items():
            object.__setattr__(provisional, name, value)
        object.__setattr__(provisional, "node_digest", "")
        return cls(node_digest=_digest(_node_payload(provisional)), **fields)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefactorSkeletonNode":
        data = dict(value or {})
        stored_digest = str(data.pop("node_digest", ""))
        created = cls.create(**data)
        if stored_digest != created.node_digest:
            raise ValueError("stored node_digest does not match canonical node content")
        return created

    def to_dict(self) -> dict[str, Any]:
        return {**_node_payload(self), "node_digest": self.node_digest}

    def validate_sources(self, repo_root: str | Path) -> list[str]:
        errors: list[str] = []
        if self.status != "READY_FOR_ACT":
            return errors
        try:
            self._validate_ready_evidence_shape()
        except ValueError as exc:
            return [f"{self.node_id}: {exc}"]
        line_counts: dict[str, int] = {}
        for relative_path in self.target_files:
            try:
                source = _resolve_repo_file(repo_root, relative_path)
                observed = sha256_file(source)
                expected = self.exact_source_hashes[relative_path]
                if observed != expected:
                    errors.append(
                        f"{self.node_id}: source hash mismatch for {relative_path}"
                    )
                with source.open("rb") as handle:
                    line_counts[relative_path] = sum(1 for _ in handle)
            except ValueError as exc:
                errors.append(f"{self.node_id}: {exc}")
        for span in self.exact_source_spans:
            count = line_counts.get(span.path)
            if count is not None and span.end_line > count:
                errors.append(
                    f"{self.node_id}: source span exceeds file length for "
                    f"{span.path}: {span.end_line}>{count}"
                )
        return errors


def _skeleton_identity(
    *,
    objective: str,
    domain: str,
    baseline_commit: str,
    source_plan_digest: str,
    addendum_digest: str,
) -> dict[str, str]:
    return {
        "objective": objective,
        "domain": domain,
        "baseline_commit": baseline_commit,
        "source_plan_digest": source_plan_digest,
        "addendum_digest": addendum_digest,
    }


def _skeleton_payload(skeleton: "RefactorSkeleton") -> dict[str, Any]:
    return {
        "skeleton_version": skeleton.skeleton_version,
        "skeleton_id": skeleton.skeleton_id,
        "objective": skeleton.objective,
        "domain": skeleton.domain,
        "baseline_commit": skeleton.baseline_commit,
        "source_plan_digest": skeleton.source_plan_digest,
        "addendum_digest": skeleton.addendum_digest,
        "emergent_packet_id": skeleton.emergent_packet_id,
        "emergent_packet_digest": skeleton.emergent_packet_digest,
        "nodes": [node.to_dict() for node in skeleton.nodes],
        "status": skeleton.status,
        "revision": skeleton.revision,
        "prior_revision_digest": skeleton.prior_revision_digest,
        "metadata": _thaw(skeleton.metadata),
        "patch_authority": skeleton.patch_authority,
        "vsa_patch_authority": skeleton.vsa_patch_authority,
        "proposal_only": skeleton.proposal_only,
    }


@dataclass(frozen=True)
class RefactorSkeleton:
    skeleton_id: str
    objective: str
    domain: str
    baseline_commit: str
    source_plan_digest: str
    addendum_digest: str
    emergent_packet_id: str
    emergent_packet_digest: str
    nodes: tuple[RefactorSkeletonNode, ...]
    status: str = "DRAFT"
    revision: int = 1
    prior_revision_digest: str = ""
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    skeleton_digest: str = ""
    skeleton_version: str = REFACTOR_SKELETON_VERSION
    patch_authority: str = PATCH_AUTHORITY
    vsa_patch_authority: bool = VSA_PATCH_AUTHORITY
    proposal_only: bool = True

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("skeleton objective is required")
        if not self.domain.strip():
            raise ValueError("skeleton domain is required")
        if not self.baseline_commit.strip():
            raise ValueError("baseline_commit is required")
        if self.status not in SKELETON_STATUSES:
            raise ValueError(f"invalid skeleton status: {self.status}")
        if self.revision < 1:
            raise ValueError("skeleton revision must be positive")
        if (
            not self.proposal_only
            or self.patch_authority != PATCH_AUTHORITY
            or self.vsa_patch_authority
        ):
            raise ValueError("refactor skeleton cannot carry mutation authority")
        if not isinstance(self.metadata, MappingProxyType):
            raise ValueError("metadata must be immutable")
        expected_id = f"RFS-{_digest(_skeleton_identity(
            objective=self.objective,
            domain=self.domain,
            baseline_commit=self.baseline_commit,
            source_plan_digest=self.source_plan_digest,
            addendum_digest=self.addendum_digest,
        ))[:20]}"
        if self.skeleton_id != expected_id or not _SKELETON_ID.fullmatch(self.skeleton_id):
            raise ValueError("skeleton_id does not match canonical identity")
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("duplicate skeleton node_id")
        known = set(node_ids)
        missing = sorted(
            {
                dependency
                for node in self.nodes
                for dependency in node.dependencies
                if dependency not in known
            }
        )
        if missing:
            raise ValueError(f"unknown node dependencies: {missing}")
        if self.revision == 1 and self.prior_revision_digest:
            raise ValueError("revision one cannot declare a prior revision digest")
        expected_digest = _digest(_skeleton_payload(self))
        if not self.skeleton_digest or self.skeleton_digest != expected_digest:
            raise ValueError("skeleton_digest does not match canonical skeleton content")

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        domain: str,
        baseline_commit: str,
        source_plan_digest: str,
        addendum_digest: str,
        nodes: Sequence[RefactorSkeletonNode | Mapping[str, Any]],
        emergent_packet_id: str = "",
        emergent_packet_digest: str = "",
        status: str = "DRAFT",
        revision: int = 1,
        prior_revision_digest: str = "",
        metadata: Mapping[str, Any] | None = None,
    ) -> "RefactorSkeleton":
        node_items = tuple(
            item
            if isinstance(item, RefactorSkeletonNode)
            else RefactorSkeletonNode.from_dict(item)
            for item in nodes
        )
        identity = _skeleton_identity(
            objective=str(objective).strip(),
            domain=str(domain).strip(),
            baseline_commit=str(baseline_commit).strip(),
            source_plan_digest=str(source_plan_digest),
            addendum_digest=str(addendum_digest),
        )
        fields = {
            "skeleton_id": f"RFS-{_digest(identity)[:20]}",
            **identity,
            "emergent_packet_id": str(emergent_packet_id),
            "emergent_packet_digest": str(emergent_packet_digest),
            "nodes": node_items,
            "status": str(status).upper(),
            "revision": int(revision),
            "prior_revision_digest": str(prior_revision_digest),
            "metadata": _immutable_mapping(metadata),
        }
        provisional = object.__new__(cls)
        for name, value in fields.items():
            object.__setattr__(provisional, name, value)
        object.__setattr__(provisional, "skeleton_version", REFACTOR_SKELETON_VERSION)
        object.__setattr__(provisional, "patch_authority", PATCH_AUTHORITY)
        object.__setattr__(provisional, "vsa_patch_authority", False)
        object.__setattr__(provisional, "proposal_only", True)
        object.__setattr__(provisional, "skeleton_digest", "")
        return cls(skeleton_digest=_digest(_skeleton_payload(provisional)), **fields)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefactorSkeleton":
        data = dict(value or {})
        stored_id = str(data.pop("skeleton_id", ""))
        stored_digest = str(data.pop("skeleton_digest", ""))
        authority = {
            "skeleton_version": data.pop("skeleton_version", None),
            "patch_authority": data.pop("patch_authority", None),
            "vsa_patch_authority": data.pop("vsa_patch_authority", None),
            "proposal_only": data.pop("proposal_only", None),
        }
        expected_authority = {
            "skeleton_version": REFACTOR_SKELETON_VERSION,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "proposal_only": True,
        }
        if authority != expected_authority:
            raise ValueError("stored skeleton authority fields are invalid")
        created = cls.create(**data)
        if stored_id != created.skeleton_id:
            raise ValueError("stored skeleton_id does not match canonical identity")
        if stored_digest != created.skeleton_digest:
            raise ValueError("stored skeleton_digest does not match canonical content")
        return created

    def to_dict(self) -> dict[str, Any]:
        return {**_skeleton_payload(self), "skeleton_digest": self.skeleton_digest}

    def node(self, node_id: str) -> RefactorSkeletonNode:
        for item in self.nodes:
            if item.node_id == node_id:
                return item
        raise KeyError(node_id)

    def revise_node(
        self,
        node_id: str,
        *,
        status: str | None = None,
        stage_digest: str | None = None,
        verifier_digest: str | None = None,
        repair_entry: Mapping[str, Any] | None = None,
        metadata_updates: Mapping[str, Any] | None = None,
        exact_source_hashes: Mapping[str, str] | None = None,
        exact_source_spans: Sequence[SourceSpan | Mapping[str, Any]] | None = None,
    ) -> "RefactorSkeleton":
        current = self.node(node_id)
        repairs = list(current.repair_history)
        if repair_entry:
            repairs.append(repair_entry)
        revised = RefactorSkeletonNode.create(
            node_id=current.node_id,
            objective=current.objective,
            canonical_owner=current.canonical_owner,
            reuse_decision=current.reuse_decision,
            target_files=current.target_files,
            target_symbols=current.target_symbols,
            exact_source_hashes=(
                current.exact_source_hashes
                if exact_source_hashes is None
                else exact_source_hashes
            ),
            exact_source_spans=(
                current.exact_source_spans
                if exact_source_spans is None
                else exact_source_spans
            ),
            dependencies=current.dependencies,
            invariants=current.invariants,
            acceptance_criteria=current.acceptance_criteria,
            required_tests=current.required_tests,
            risk_lanes=current.risk_lanes,
            authority_boundary=current.authority_boundary,
            status=status or current.status,
            revision=current.revision + 1,
            prior_revision_digest=current.node_digest,
            stage_digest=current.stage_digest if stage_digest is None else stage_digest,
            verifier_digest=(
                current.verifier_digest
                if verifier_digest is None
                else verifier_digest
            ),
            repair_history=repairs,
            integration_dispositions=current.integration_dispositions,
            metadata={**_thaw(current.metadata), **dict(metadata_updates or {})},
        )
        nodes = tuple(
            revised if item.node_id == node_id else item for item in self.nodes
        )
        return RefactorSkeleton.create(
            objective=self.objective,
            domain=self.domain,
            baseline_commit=self.baseline_commit,
            source_plan_digest=self.source_plan_digest,
            addendum_digest=self.addendum_digest,
            emergent_packet_id=self.emergent_packet_id,
            emergent_packet_digest=self.emergent_packet_digest,
            nodes=nodes,
            status=self.status,
            revision=self.revision + 1,
            prior_revision_digest=self.skeleton_digest,
            metadata=self.metadata,
        )

    def validate(
        self,
        *,
        required_structures: Sequence[str] = (),
        repo_root: str | Path | None = None,
        verify_sources: bool = False,
    ) -> dict[str, Any]:
        errors: list[str] = []
        if self.skeleton_digest != _digest(_skeleton_payload(self)):
            errors.append("skeleton digest no longer matches canonical content")
        required = {
            str(item).strip()
            for item in required_structures
            if str(item).strip()
        }
        for node in self.nodes:
            if node.node_digest != _digest(_node_payload(node)):
                errors.append(f"{node.node_id}: node digest no longer matches content")
            dispositions = {item.structure for item in node.integration_dispositions}
            missing = sorted(required - dispositions)
            if missing:
                errors.append(
                    f"{node.node_id}: missing integration dispositions: {missing}"
                )
            if verify_sources:
                if repo_root is None:
                    errors.append("repo_root is required when verify_sources is true")
                    break
                errors.extend(node.validate_sources(repo_root))
        return {
            "ok": not errors,
            "errors": errors,
            "node_count": len(self.nodes),
            "skeleton_id": self.skeleton_id,
            "skeleton_digest": self.skeleton_digest,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "proposal_only": True,
        }


class RefactorSkeletonStore:
    """Content-addressed revision store with fork and chain rejection."""

    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        store_root: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.store_root = (
            Path(store_root).resolve()
            if store_root is not None
            else (self.repo_root / DEFAULT_STORE_PATH).resolve()
        )
        self.store_root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _envelope_digest(skeleton_dict: Mapping[str, Any]) -> str:
        return _digest(
            {
                "truth_class": "REFACTOR_SKELETON_PLANNING_EVIDENCE",
                "skeleton": skeleton_dict,
            }
        )

    def _read_path(self, path: Path) -> RefactorSkeleton:
        match = _REVISION_FILE.fullmatch(path.name)
        if not match:
            raise ValueError(f"invalid skeleton revision filename: {path.name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("skeleton"), dict):
            raise ValueError("malformed refactor skeleton envelope")
        expected_envelope = self._envelope_digest(payload["skeleton"])
        if payload.get("truth_class") != "REFACTOR_SKELETON_PLANNING_EVIDENCE":
            raise ValueError("stored skeleton truth class is invalid")
        if payload.get("envelope_digest") != expected_envelope:
            raise ValueError("stored skeleton envelope digest is invalid")
        skeleton = RefactorSkeleton.from_dict(payload["skeleton"])
        if int(match.group("revision")) != skeleton.revision:
            raise ValueError("revision filename does not match stored revision")
        if match.group("digest") != skeleton.skeleton_digest:
            raise ValueError("revision filename does not match stored digest")
        return skeleton

    def _load_chain(self, skeleton_id: str) -> list[tuple[Path, RefactorSkeleton]]:
        directory = self.store_root / skeleton_id
        grouped: dict[int, list[Path]] = {}
        for path in directory.glob("r????????-*.json"):
            match = _REVISION_FILE.fullmatch(path.name)
            if match:
                grouped.setdefault(int(match.group("revision")), []).append(path)
        if not grouped:
            return []
        for revision, paths in grouped.items():
            if len(paths) != 1:
                raise ValueError(f"conflicting skeleton revision fork: {revision}")
        revisions = sorted(grouped)
        if revisions != list(range(1, revisions[-1] + 1)):
            raise ValueError("skeleton revision history contains a gap")
        chain: list[tuple[Path, RefactorSkeleton]] = []
        prior = ""
        for revision in revisions:
            path = grouped[revision][0]
            skeleton = self._read_path(path)
            if skeleton.skeleton_id != skeleton_id:
                raise ValueError("stored skeleton path does not match skeleton_id")
            if skeleton.prior_revision_digest != prior:
                raise ValueError("skeleton prior revision digest chain is broken")
            prior = skeleton.skeleton_digest
            chain.append((path, skeleton))
        return chain

    def store(self, skeleton: RefactorSkeleton) -> dict[str, Any]:
        validation = skeleton.validate()
        if not validation["ok"]:
            raise ValueError(
                f"cannot store invalid refactor skeleton: {validation['errors']}"
            )
        directory = self.store_root / skeleton.skeleton_id
        directory.mkdir(parents=True, exist_ok=True)
        chain = self._load_chain(skeleton.skeleton_id)
        if chain:
            latest = chain[-1][1]
            if skeleton.revision == latest.revision:
                if skeleton.skeleton_digest == latest.skeleton_digest:
                    return self._result(skeleton, chain[-1][0], created=False)
                raise ValueError("conflicting skeleton revision fork")
            if skeleton.revision != latest.revision + 1:
                raise ValueError("skeleton revision must extend the latest revision")
            if skeleton.prior_revision_digest != latest.skeleton_digest:
                raise ValueError("skeleton prior revision digest does not match latest")
        elif skeleton.revision != 1 or skeleton.prior_revision_digest:
            raise ValueError("first stored skeleton must be revision one")

        path = directory / f"r{skeleton.revision:08d}-{skeleton.skeleton_digest}.json"
        skeleton_dict = skeleton.to_dict()
        envelope = {
            "stored_at": time.time(),
            "truth_class": "REFACTOR_SKELETON_PLANNING_EVIDENCE",
            "envelope_digest": self._envelope_digest(skeleton_dict),
            "skeleton": skeleton_dict,
        }
        temporary = path.with_name(
            f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(envelope, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            try:
                os.link(temporary, path)
            except FileExistsError:
                existing = self._read_path(path)
                if existing.skeleton_digest != skeleton.skeleton_digest:
                    raise ValueError("conflicting skeleton revision fork")
                return self._result(skeleton, path, created=False)
        finally:
            if temporary.exists():
                temporary.unlink()
        return self._result(skeleton, path, created=True)

    @staticmethod
    def _result(
        skeleton: RefactorSkeleton, path: Path, *, created: bool
    ) -> dict[str, Any]:
        return {
            "ok": True,
            "created": created,
            "skeleton_id": skeleton.skeleton_id,
            "skeleton_digest": skeleton.skeleton_digest,
            "revision": skeleton.revision,
            "path": str(path),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": False,
            "proposal_only": True,
        }

    def load_latest(self, skeleton_id: str) -> RefactorSkeleton:
        safe_id = str(skeleton_id).strip()
        if not _SKELETON_ID.fullmatch(safe_id):
            raise ValueError("invalid skeleton_id")
        chain = self._load_chain(safe_id)
        if not chain:
            raise FileNotFoundError(safe_id)
        return chain[-1][1]
