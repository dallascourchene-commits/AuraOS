"""Creator Studio WorkGraph projection, claim preparation, and continuation state.

This module is a coordination/control-plane reference for CS-HARNESS-001/H-C.
It never grants effect authority, starts a worker, calls a model/provider, or treats
board/document presence as proof of execution. Planning proposes; governance
authorizes; command/effect-bound receipts prove execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Sequence

from aura_event_contracts import canonical_json, stable_digest

VERSION = "AURA_CREATOR_STUDIO_WORKGRAPH_V1"
PROJECTION_SCHEMA = "WorkGraphProjectionV1"
SCHEMA_VERSION = "1.0"
DEFAULT_LEASE_MS = 30 * 60 * 1000


class WorkState(str, Enum):
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    SUPERSEDED = "SUPERSEDED"


class WorkerState(str, Enum):
    ORIENTING = "ORIENTING"
    IDLE = "IDLE"
    CLAIMING = "CLAIMING"
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    RELEASED = "RELEASED"
    DORMANT = "DORMANT"
    STALE = "STALE"


class ExecutionState(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    EFFECT_ADMITTED = "EFFECT_ADMITTED"
    EFFECT_STARTED = "EFFECT_STARTED"
    RESULT_PARTIAL = "RESULT_PARTIAL"
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ProjectionStatus(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    INVALID = "INVALID"


class SelectionDecision(str, Enum):
    REBASE = "REBASE"
    SELECT_WORK = "SELECT_WORK"
    IDLE = "IDLE"
    BLOCKED = "BLOCKED"
    WAKE_LOCAL = "WAKE_LOCAL"
    RECOMMISSION_REQUIRED = "RECOMMISSION_REQUIRED"


class ClaimCASStatus(str, Enum):
    READY = "READY"
    STALE = "STALE"
    REJECTED = "REJECTED"


class RecoveryDecision(str, Enum):
    NOOP = "NOOP"
    RELEASE_TO_OPEN = "RELEASE_TO_OPEN"
    REBASE = "REBASE"
    RECONCILE_EFFECT_STATE_REQUIRED = "RECONCILE_EFFECT_STATE_REQUIRED"
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


_PRIORITY = {value: index for index, value in enumerate(Priority)}
_TERMINAL = frozenset({WorkState.COMPLETE, WorkState.SUPERSEDED})
_ASSIGNABLE_WORKER_STATES = frozenset({WorkerState.IDLE, WorkerState.RELEASED})
_EFFECT_ORDER = {"D0": 0, "D1": 1, "D2": 2, "D3": 3}


class WorkGraphParseError(ValueError):
    pass


def _text(value: Any, field: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _optional(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if type(value) is not str:
        raise ValueError(f"{field} must be text or null")
    return value.strip() or None


def _integer(value: Any, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{field} must be an integer >= {minimum}")
    return value


def _optional_integer(value: Any, field: str, minimum: int = 0) -> int | None:
    if value is None:
        return None
    return _integer(value, field, minimum)


def _strings(values: Sequence[str] | None, field: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field} must be a sequence")
    result = tuple(_text(value, f"{field}[]") for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _enum(value: Any, enum_type: type[Enum], field: str):
    try:
        return value if isinstance(value, enum_type) else enum_type(str(value))
    except ValueError as exc:
        raise ValueError(f"unknown {field}: {value}") from exc


def _effect_covers(worker_ceiling: str, required: str) -> bool:
    worker = _EFFECT_ORDER.get(str(worker_ceiling).upper())
    need = _EFFECT_ORDER.get(str(required).upper())
    return worker is not None and need is not None and worker >= need


@dataclass(frozen=True)
class WorkerSpec:
    worker_id: str
    worker_class: str
    capabilities: tuple[str, ...]
    join_ref: str
    currentness_basis: str
    effect_ceiling: str = "D0"
    state: WorkerState | str = WorkerState.IDLE
    active_claim_id: str | None = None
    heartbeat_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id"))
        object.__setattr__(self, "worker_class", _text(self.worker_class, "worker_class"))
        object.__setattr__(self, "capabilities", _strings(self.capabilities, "capabilities"))
        object.__setattr__(self, "join_ref", _text(self.join_ref, "join_ref"))
        object.__setattr__(self, "currentness_basis", _text(self.currentness_basis, "currentness_basis"))
        ceiling = _text(self.effect_ceiling, "effect_ceiling").upper()
        if ceiling not in _EFFECT_ORDER:
            raise ValueError("effect_ceiling must be D0-D3")
        object.__setattr__(self, "effect_ceiling", ceiling)
        object.__setattr__(self, "state", _enum(self.state, WorkerState, "worker.state"))
        object.__setattr__(self, "active_claim_id", _optional(self.active_claim_id, "active_claim_id"))
        object.__setattr__(self, "heartbeat_ref", _optional(self.heartbeat_ref, "heartbeat_ref"))


@dataclass(frozen=True)
class ClaimLease:
    lease_id: str
    worker_id: str
    acquired_at_ms: int
    expires_at_ms: int
    basis_revision: str
    currentness_basis: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "lease_id", _text(self.lease_id, "lease_id"))
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id"))
        object.__setattr__(self, "acquired_at_ms", _integer(self.acquired_at_ms, "acquired_at_ms"))
        object.__setattr__(self, "expires_at_ms", _integer(self.expires_at_ms, "expires_at_ms"))
        if self.expires_at_ms <= self.acquired_at_ms:
            raise ValueError("lease expiry must follow acquisition")
        object.__setattr__(self, "basis_revision", _text(self.basis_revision, "basis_revision"))
        object.__setattr__(self, "currentness_basis", _text(self.currentness_basis, "currentness_basis"))

    def expired(self, now_ms: int) -> bool:
        return _integer(now_ms, "now_ms") >= self.expires_at_ms


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    state: WorkState | str
    priority: Priority | str
    parent_objective: str
    residual: str
    currentness_basis: str
    dependencies: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    owner_worker_id: str | None = None
    free_first_route: tuple[str, ...] = ("R0_REUSE", "R1_DETERMINISTIC_LOCAL")
    expected_output: str | None = None
    acceptance: tuple[str, ...] = ()
    reopen_conditions: tuple[str, ...] = ()
    cost_ceiling_microusd: int | None = None
    required_effect_ceiling: str = "D0"
    claim_lease: ClaimLease | None = None
    execution_state: ExecutionState | str = ExecutionState.NOT_STARTED
    execution_receipt_refs: tuple[str, ...] = ()
    hydration_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    source_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_id", _text(self.work_id, "work_id"))
        object.__setattr__(self, "state", _enum(self.state, WorkState, "work.state"))
        object.__setattr__(self, "priority", _enum(self.priority, Priority, "priority"))
        object.__setattr__(self, "parent_objective", _text(self.parent_objective, "parent_objective"))
        object.__setattr__(self, "residual", _text(self.residual, "residual"))
        object.__setattr__(self, "currentness_basis", _text(self.currentness_basis, "currentness_basis"))
        object.__setattr__(self, "dependencies", _strings(self.dependencies, "dependencies"))
        object.__setattr__(self, "required_capabilities", _strings(self.required_capabilities, "required_capabilities"))
        object.__setattr__(self, "owner_worker_id", _optional(self.owner_worker_id, "owner_worker_id"))
        object.__setattr__(self, "free_first_route", _strings(self.free_first_route, "free_first_route"))
        object.__setattr__(self, "expected_output", _optional(self.expected_output, "expected_output"))
        object.__setattr__(self, "acceptance", _strings(self.acceptance, "acceptance"))
        object.__setattr__(self, "reopen_conditions", _strings(self.reopen_conditions, "reopen_conditions"))
        object.__setattr__(self, "cost_ceiling_microusd", _optional_integer(self.cost_ceiling_microusd, "cost_ceiling_microusd"))
        required_effect = _text(self.required_effect_ceiling, "required_effect_ceiling").upper()
        if required_effect not in _EFFECT_ORDER:
            raise ValueError("required_effect_ceiling must be D0-D3")
        object.__setattr__(self, "required_effect_ceiling", required_effect)
        if self.claim_lease is not None and not isinstance(self.claim_lease, ClaimLease):
            raise ValueError("claim_lease must be ClaimLease or null")
        object.__setattr__(self, "execution_state", _enum(self.execution_state, ExecutionState, "execution_state"))
        object.__setattr__(self, "execution_receipt_refs", _strings(self.execution_receipt_refs, "execution_receipt_refs"))
        object.__setattr__(self, "hydration_refs", _strings(self.hydration_refs, "hydration_refs"))
        object.__setattr__(self, "evidence_refs", _strings(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "source_order", _integer(self.source_order, "source_order"))
        if self.work_id in self.dependencies:
            raise ValueError("work item cannot depend on itself")
        if self.execution_state is ExecutionState.VERIFIED_COMPLETE and not self.execution_receipt_refs:
            raise ValueError("VERIFIED_COMPLETE requires command/effect-bound receipt refs")


@dataclass(frozen=True)
class Finding:
    code: str
    work_id: str | None
    message: str
    blocking: bool


@dataclass(frozen=True)
class DependencyEdge:
    upstream_work_id: str
    downstream_work_id: str


@dataclass(frozen=True)
class WorkProjection:
    work: WorkItem
    effective_state: WorkState
    dependency_satisfied: bool
    capability_candidates: tuple[str, ...]
    active_lease: ClaimLease | None
    stale_claim_recoverable: bool
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorkGraphSnapshot:
    project_id: str
    canonical_orientation_ref: str
    canonical_orientation_revision: str
    board_ref: str
    board_revision: str
    generated_at_ms: int
    projector_version: str
    source_digests: tuple[str, ...]
    workers: tuple[WorkerSpec, ...]
    work: tuple[WorkProjection, ...]
    dependency_edges: tuple[DependencyEdge, ...]
    currentness_invalidators: tuple[str, ...]
    route_policy_ref: str
    projection_status: ProjectionStatus
    findings: tuple[Finding, ...]
    source_digest: str
    execution_proven: bool = False

    def __post_init__(self) -> None:
        if self.projector_version != VERSION or self.execution_proven is not False:
            raise ValueError("WorkGraph is coordination-only and cannot prove execution")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PROJECTION_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "project_id": self.project_id,
            "canonical_orientation_ref": self.canonical_orientation_ref,
            "canonical_orientation_revision": self.canonical_orientation_revision,
            "board_ref": self.board_ref,
            "board_revision": self.board_revision,
            "generated_at_ms": self.generated_at_ms,
            "projector_version": self.projector_version,
            "source_digests": self.source_digests,
            "workers": self.workers,
            "work_items": self.work,
            "dependency_edges": self.dependency_edges,
            "currentness_invalidators": self.currentness_invalidators,
            "route_policy_ref": self.route_policy_ref,
            "projection_status": self.projection_status,
            "findings": self.findings,
            "source_digest": self.source_digest,
            "coordination_only": True,
            "execution_proven": False,
            "wake_effect_started": False,
        }

    @property
    def revision(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class SelectionProposal:
    decision: SelectionDecision
    worker_id: str
    selected_work_id: str | None
    reason_codes: tuple[str, ...]
    projection_revision: str
    required_hydration_refs: tuple[str, ...]
    effect_allowed: bool = False
    runtime_effect_started: bool = False

    def __post_init__(self) -> None:
        if self.effect_allowed is not False or self.runtime_effect_started is not False:
            raise ValueError("WorkGraph selection cannot grant or start effects")


@dataclass(frozen=True)
class ClaimCASResult:
    status: ClaimCASStatus
    worker_id: str
    work_id: str
    reason_codes: tuple[str, ...]
    expected_projection_revision: str
    observed_projection_revision: str
    proposed_lease: ClaimLease | None = None
    effect_started: bool = False

    def __post_init__(self) -> None:
        if self.effect_started is not False:
            raise ValueError("claim preparation cannot start effects")


@dataclass(frozen=True)
class RecoveryProposal:
    decision: RecoveryDecision
    work_id: str
    reason_codes: tuple[str, ...]
    recovered_state: WorkState | None = None
    effect_started: bool = False

    def __post_init__(self) -> None:
        if self.effect_started is not False:
            raise ValueError("stale recovery proposal cannot start effects")


@dataclass(frozen=True)
class CompletionRecord:
    work_id: str
    worker_id: str
    output_refs: tuple[str, ...]
    residual: str | None = None
    residual_priority: Priority | str = Priority.P1
    residual_required_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_id", _text(self.work_id, "work_id"))
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id"))
        object.__setattr__(self, "output_refs", _strings(self.output_refs, "output_refs"))
        if not self.output_refs:
            raise ValueError("completion requires output receipts")
        object.__setattr__(self, "residual", _optional(self.residual, "residual"))
        object.__setattr__(self, "residual_priority", _enum(self.residual_priority, Priority, "residual_priority"))
        object.__setattr__(self, "residual_required_capabilities", _strings(self.residual_required_capabilities, "residual_required_capabilities"))


def project_workgraph(
    *,
    project_id: str,
    canonical_orientation_ref: str,
    canonical_orientation_revision: str,
    board_ref: str,
    board_revision: str,
    generated_at_ms: int,
    workers: Sequence[WorkerSpec],
    work_items: Sequence[WorkItem],
    route_policy_ref: str,
    source_digests: Sequence[str] = (),
    currentness_invalidators: Sequence[str] = (),
) -> WorkGraphSnapshot:
    """Project shared state without mutating, authorizing, waking, or executing."""
    project_id = _text(project_id, "project_id")
    orientation_ref = _text(canonical_orientation_ref, "canonical_orientation_ref")
    currentness = _text(canonical_orientation_revision, "canonical_orientation_revision")
    board_ref = _text(board_ref, "board_ref")
    board_revision = _text(board_revision, "board_revision")
    route_policy_ref = _text(route_policy_ref, "route_policy_ref")
    now = _integer(generated_at_ms, "generated_at_ms")
    workers = tuple(workers)
    work_items = tuple(work_items)
    source_digests = _strings(tuple(source_digests), "source_digests")
    invalidators = _strings(tuple(currentness_invalidators), "currentness_invalidators")
    worker_map = {worker.worker_id: worker for worker in workers}
    item_map = {item.work_id: item for item in work_items}
    if len(worker_map) != len(workers) or len(item_map) != len(work_items):
        raise ValueError("worker_id and work_id values must be unique")

    findings: list[Finding] = []
    edges: list[DependencyEdge] = []
    complete = {item.work_id for item in work_items if item.state is WorkState.COMPLETE}
    projected: list[WorkProjection] = []

    for item in sorted(work_items, key=lambda value: (value.source_order, value.work_id)):
        reasons: list[str] = []
        for dependency in item.dependencies:
            edges.append(DependencyEdge(dependency, item.work_id))
            if dependency not in item_map:
                findings.append(Finding("UNKNOWN_DEPENDENCY", item.work_id, dependency, True))
        missing = tuple(dependency for dependency in item.dependencies if dependency not in complete)
        if missing:
            reasons.append("DEPENDENCY_BLOCKED:" + ",".join(missing))

        lease = item.claim_lease
        live_lease = bool(lease and not lease.expired(now))
        stale_lease = bool(lease and lease.expired(now))
        safe_stale = bool(
            stale_lease
            and item.execution_state is ExecutionState.NOT_STARTED
            and item.currentness_basis == currentness
            and not invalidators
        )
        if lease and lease.worker_id not in worker_map:
            findings.append(Finding("CLAIM_UNKNOWN_WORKER", item.work_id, lease.worker_id, True))
        if stale_lease:
            reasons.append("STALE_CLAIM")
            if safe_stale:
                reasons.append("STALE_CLAIM_RECOVERABLE")
            else:
                reasons.append("STALE_CLAIM_RECONCILIATION_REQUIRED")

        effective = item.state
        if item.state not in _TERMINAL:
            if live_lease:
                effective = WorkState.CLAIMED
            elif stale_lease and safe_stale:
                effective = WorkState.OPEN
            elif item.state is WorkState.CLAIMED and lease is None:
                findings.append(Finding("CLAIM_STATE_WITHOUT_LEASE", item.work_id, "CLAIMED state has no lease", True))
                reasons.append("CLAIM_STATE_WITHOUT_LEASE")

        candidates = tuple(
            worker.worker_id
            for worker in sorted(workers, key=lambda value: value.worker_id)
            if worker.state in _ASSIGNABLE_WORKER_STATES
            and worker.currentness_basis == currentness
            and set(item.required_capabilities).issubset(worker.capabilities)
            and _effect_covers(worker.effect_ceiling, item.required_effect_ceiling)
        )
        if item.currentness_basis != currentness or invalidators:
            reasons.append("STALE_WORK_CURRENTNESS")
        if not candidates:
            reasons.append("NO_CAPABILITY_OR_EFFECT_FIT")
        if item.cost_ceiling_microusd is None:
            reasons.append("COST_CEILING_UNKNOWN")

        eligible = bool(
            effective is WorkState.OPEN
            and not missing
            and item.currentness_basis == currentness
            and not invalidators
            and candidates
            and (lease is None or safe_stale)
        )
        projected.append(
            WorkProjection(
                item,
                effective,
                not missing,
                candidates,
                lease,
                safe_stale,
                eligible,
                tuple(reasons),
            )
        )

    structural_invalid = any(finding.blocking for finding in findings)
    status = ProjectionStatus.INVALID if structural_invalid else (
        ProjectionStatus.STALE if invalidators else ProjectionStatus.CURRENT
    )
    source_digest = stable_digest(
        {
            "project_id": project_id,
            "canonical_orientation_ref": orientation_ref,
            "canonical_orientation_revision": currentness,
            "board_ref": board_ref,
            "board_revision": board_revision,
            "workers": workers,
            "work_items": work_items,
            "route_policy_ref": route_policy_ref,
            "source_digests": source_digests,
            "currentness_invalidators": invalidators,
        }
    )
    return WorkGraphSnapshot(
        project_id,
        orientation_ref,
        currentness,
        board_ref,
        board_revision,
        now,
        VERSION,
        source_digests,
        workers,
        tuple(projected),
        tuple(edges),
        invalidators,
        route_policy_ref,
        status,
        tuple(findings),
        source_digest,
    )


def select_next_work(snapshot: WorkGraphSnapshot, *, worker_id: str) -> SelectionProposal:
    """Return a deterministic coordination proposal; claim/effect still require separate commits."""
    worker_id = _text(worker_id, "worker_id")
    worker_map = {worker.worker_id: worker for worker in snapshot.workers}
    if worker_id not in worker_map:
        raise ValueError("worker_id is not present in snapshot")
    if snapshot.projection_status is ProjectionStatus.STALE:
        return SelectionProposal(
            SelectionDecision.REBASE, worker_id, None,
            ("PROJECTION_STALE",), snapshot.revision,
            (snapshot.canonical_orientation_ref, snapshot.board_ref),
        )
    if snapshot.projection_status is ProjectionStatus.INVALID:
        return SelectionProposal(
            SelectionDecision.BLOCKED, worker_id, None,
            ("PROJECTION_INVALID",), snapshot.revision,
            (snapshot.canonical_orientation_ref, snapshot.board_ref),
        )
    worker = worker_map[worker_id]
    if worker.currentness_basis != snapshot.canonical_orientation_revision:
        return SelectionProposal(
            SelectionDecision.REBASE, worker_id, None,
            ("WORKER_CURRENTNESS_STALE",), snapshot.revision,
            (snapshot.canonical_orientation_ref, snapshot.board_ref),
        )
    if worker.state not in _ASSIGNABLE_WORKER_STATES:
        return SelectionProposal(
            SelectionDecision.BLOCKED, worker_id, None,
            ("WORKER_NOT_ASSIGNABLE",), snapshot.revision, (),
        )

    candidates = [
        projection
        for projection in snapshot.work
        if projection.eligible and worker_id in projection.capability_candidates
    ]
    candidates.sort(
        key=lambda projection: (
            _PRIORITY[projection.work.priority],
            projection.work.cost_ceiling_microusd is None,
            projection.work.cost_ceiling_microusd or 0,
            projection.work.source_order,
            projection.work.work_id,
        )
    )
    if not candidates:
        return SelectionProposal(
            SelectionDecision.IDLE, worker_id, None,
            ("NO_ELIGIBLE_NON_DUPLICATE_WORK",), snapshot.revision, (),
        )
    selected = candidates[0]
    return SelectionProposal(
        SelectionDecision.SELECT_WORK,
        worker_id,
        selected.work.work_id,
        (
            "HIGHEST_PRIORITY_ELIGIBLE",
            "ATOMIC_CLAIM_COMMIT_REQUIRED",
            "SELECTION_IS_NOT_EXECUTION",
        ),
        snapshot.revision,
        selected.work.hydration_refs,
    )


def prepare_claim_compare_and_set(
    snapshot: WorkGraphSnapshot,
    *,
    expected_projection_revision: str,
    worker_id: str,
    work_id: str,
    lease_id: str,
    acquired_at_ms: int,
    expires_at_ms: int,
) -> ClaimCASResult:
    """Prepare a revision-bound claim. Persistence/atomicity belongs to the host adapter."""
    expected = _text(expected_projection_revision, "expected_projection_revision")
    observed = snapshot.revision
    worker_id = _text(worker_id, "worker_id")
    work_id = _text(work_id, "work_id")
    if expected != observed:
        return ClaimCASResult(
            ClaimCASStatus.STALE, worker_id, work_id,
            ("CLAIM_STALE_REBASE_REQUIRED",), expected, observed,
        )
    projection = next((item for item in snapshot.work if item.work.work_id == work_id), None)
    if projection is None:
        return ClaimCASResult(
            ClaimCASStatus.REJECTED, worker_id, work_id,
            ("WORK_NOT_FOUND",), expected, observed,
        )
    if not projection.eligible or worker_id not in projection.capability_candidates:
        return ClaimCASResult(
            ClaimCASStatus.REJECTED, worker_id, work_id,
            ("WORK_NOT_ELIGIBLE_FOR_WORKER",), expected, observed,
        )
    lease = ClaimLease(
        lease_id,
        worker_id,
        acquired_at_ms,
        expires_at_ms,
        snapshot.board_revision,
        snapshot.canonical_orientation_revision,
    )
    return ClaimCASResult(
        ClaimCASStatus.READY,
        worker_id,
        work_id,
        ("HOST_ATOMIC_COMMIT_REQUIRED", "ZERO_EFFECT_BEFORE_COMMIT"),
        expected,
        observed,
        lease,
    )


def reconcile_stale_claim(
    projection: WorkProjection,
    *,
    now_ms: int,
    currentness_basis: str,
) -> RecoveryProposal:
    """Fail closed when a stale lease has any ambiguous consequence-bearing effect state."""
    now = _integer(now_ms, "now_ms")
    currentness = _text(currentness_basis, "currentness_basis")
    lease = projection.active_lease
    if lease is None or not lease.expired(now):
        return RecoveryProposal(RecoveryDecision.NOOP, projection.work.work_id, ("LEASE_NOT_STALE",))
    if projection.work.currentness_basis != currentness or lease.currentness_basis != currentness:
        return RecoveryProposal(
            RecoveryDecision.REBASE,
            projection.work.work_id,
            ("STALE_CURRENTNESS_REBASE_REQUIRED",),
            WorkState.SUPERSEDED,
        )
    if projection.work.execution_state is ExecutionState.VERIFIED_COMPLETE:
        return RecoveryProposal(
            RecoveryDecision.VERIFIED_COMPLETE,
            projection.work.work_id,
            ("RECEIPT_BOUND_COMPLETION_PRESERVED",),
            WorkState.COMPLETE,
        )
    if projection.work.execution_state is not ExecutionState.NOT_STARTED:
        return RecoveryProposal(
            RecoveryDecision.RECONCILE_EFFECT_STATE_REQUIRED,
            projection.work.work_id,
            ("EFFECT_STATE_NOT_PROVABLY_NOT_STARTED",),
            WorkState.BLOCKED,
        )
    return RecoveryProposal(
        RecoveryDecision.RELEASE_TO_OPEN,
        projection.work.work_id,
        ("STALE_LEASE_EFFECT_NOT_STARTED", "APPEND_ONLY_RELEASE_RECEIPT_REQUIRED"),
        WorkState.OPEN,
    )


def compile_successor_residual(
    *,
    parent: WorkItem,
    completion: CompletionRecord,
    currentness_basis: str,
    source_order: int,
) -> WorkItem | None:
    """Create one deterministic successor only when completion explicitly exposes a residual."""
    if completion.work_id != parent.work_id:
        raise ValueError("completion does not bind to parent")
    if completion.residual is None:
        return None
    payload = {
        "parent": parent.work_id,
        "outputs": completion.output_refs,
        "residual": completion.residual,
        "currentness_basis": currentness_basis,
    }
    return WorkItem(
        work_id=f"{parent.work_id}::RESIDUAL::{stable_digest(payload, digest_size=8)}",
        state=WorkState.OPEN,
        priority=completion.residual_priority,
        parent_objective=parent.parent_objective,
        residual=completion.residual,
        currentness_basis=currentness_basis,
        dependencies=(parent.work_id,),
        required_capabilities=completion.residual_required_capabilities,
        free_first_route=parent.free_first_route,
        expected_output="Successor residual closure receipt",
        acceptance=("Residual acceptance evidence recorded",),
        reopen_conditions=parent.reopen_conditions,
        cost_ceiling_microusd=parent.cost_ceiling_microusd,
        required_effect_ceiling=parent.required_effect_ceiling,
        hydration_refs=completion.output_refs,
        evidence_refs=completion.output_refs,
        source_order=_integer(source_order, "source_order"),
    )


_GROUP = re.compile(r"^GROUP-WO\s*\|\s*([^|]+)\s*\|\s*(.*)$")
_FIELDS = {
    "PARENT OBJECTIVE:": "parent_objective",
    "RESIDUAL:": "residual",
    "DEPENDENCIES:": "dependencies",
    "FREE-FIRST ROUTE:": "free_first_route",
    "EXPECTED OUTPUT:": "expected_output",
    "ACCEPTANCE:": "acceptance",
    "COST CEILING:": "cost_ceiling",
    "REOPEN:": "reopen",
}
_DEP_ID = re.compile(r"\b(?:CS-[A-Z0-9-]+-\d+|COST-\d+|S\d{2}-[A-Z0-9-]+|H-[A-Z])\b")


def _parse_cost(text: str) -> int | None:
    match = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", text)
    return None if match is None else int(round(float(match.group(1)) * 1_000_000))


def parse_group_work_orders(text: str, *, currentness_basis: str) -> tuple[WorkItem, ...]:
    """Parse formal GROUP-WO blocks; malformed formal blocks are typed errors, never silent drops."""
    if type(text) is not str:
        raise ValueError("text must be a string")
    lines = text.splitlines()
    records: list[WorkItem] = []
    index = 0
    source_order = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("GROUP-WO") and not _GROUP.match(stripped):
            raise WorkGraphParseError(f"MALFORMED_GROUP_WO_HEADER:{index + 1}")
        match = _GROUP.match(stripped)
        if not match:
            index += 1
            continue
        header: dict[str, str] = {}
        for part in match.group(2).split("|"):
            if ":" in part:
                key, value = part.split(":", 1)
                header[key.strip().upper()] = value.strip()
        raw_state = header.get("STATE", "OPEN")
        if raw_state.startswith("BLOCKED"):
            raw_state = "BLOCKED"
        if raw_state not in {state.value for state in WorkState}:
            raise WorkGraphParseError(f"INVALID_GROUP_WO_STATE:{match.group(1).strip()}")
        priority = header.get("PRIORITY", "P4")
        if priority not in {value.value for value in Priority}:
            raise WorkGraphParseError(f"INVALID_GROUP_WO_PRIORITY:{match.group(1).strip()}")

        fields: dict[str, str] = {}
        scan = index + 1
        while scan < len(lines):
            line = lines[scan].strip()
            if _GROUP.match(line) or line.startswith(
                ("JOIN |", "CLAIM |", "COMPLETE |", "COMPLETE /", "CHECKPOINT |", "HANDOFF |", "TRIADIC ")
            ):
                break
            for prefix, key in _FIELDS.items():
                if line.startswith(prefix):
                    fields[key] = line[len(prefix):].strip()
                    break
            scan += 1
        missing = [name for name in ("parent_objective", "residual") if not fields.get(name)]
        if missing:
            raise WorkGraphParseError(
                f"GROUP_WO_REQUIRED_FIELD_MISSING:{match.group(1).strip()}:{','.join(missing)}"
            )
        dependency_ids = tuple(dict.fromkeys(_DEP_ID.findall(fields.get("dependencies", ""))))
        route = tuple(
            value.strip()
            for value in re.split(r"\s*->\s*|\s*;\s*", fields.get("free_first_route", ""))
            if value.strip()
        ) or ("R0_REUSE", "R1_DETERMINISTIC_LOCAL")
        records.append(
            WorkItem(
                work_id=match.group(1).strip(),
                state=raw_state,
                priority=priority,
                parent_objective=fields["parent_objective"],
                residual=fields["residual"],
                currentness_basis=currentness_basis,
                dependencies=dependency_ids,
                free_first_route=route,
                expected_output=fields.get("expected_output"),
                acceptance=(fields["acceptance"],) if fields.get("acceptance") else (),
                reopen_conditions=(fields["reopen"],) if fields.get("reopen") else (),
                cost_ceiling_microusd=_parse_cost(fields.get("cost_ceiling", "")),
                source_order=source_order,
            )
        )
        source_order += 1
        index = max(scan, index + 1)
    return tuple(records)


def projection_json(snapshot: WorkGraphSnapshot) -> str:
    return canonical_json(snapshot.to_dict()) + "\n"
