"""Creator Studio WorkGraph projection and continual-work selection.

Coordination only: claims and wake proposals never grant authority or prove execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Sequence

from aura_event_contracts import canonical_json, stable_digest

VERSION = "AURA_CREATOR_STUDIO_WORKGRAPH_V1"
SCHEMA_VERSION = "1.0"
DEFAULT_STALE_AFTER_MS = 30 * 60 * 1000


class WorkState(str, Enum):
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    BLOCKED = "BLOCKED"
    COMPLETE = "COMPLETE"
    SUPERSEDED = "SUPERSEDED"


class Priority(str, Enum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


_PRIORITY = {value: index for index, value in enumerate(Priority)}
_TERMINAL = frozenset({WorkState.COMPLETE, WorkState.SUPERSEDED})


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


def _strings(values: Sequence[str] | None, field: str) -> tuple[str, ...]:
    if values is None:
        return ()
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{field} must be a sequence")
    result = tuple(_text(value, f"{field}[]") for value in values)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} must not contain duplicates")
    return result


def _state(value: WorkState | str) -> WorkState:
    try:
        return value if isinstance(value, WorkState) else WorkState(str(value))
    except ValueError as exc:
        raise ValueError(f"unknown work state: {value}") from exc


def _priority(value: Priority | str) -> Priority:
    try:
        return value if isinstance(value, Priority) else Priority(str(value))
    except ValueError as exc:
        raise ValueError(f"unknown priority: {value}") from exc


@dataclass(frozen=True)
class WorkerSpec:
    worker_id: str
    capabilities: tuple[str, ...]
    currentness_ref: str
    joined_at_ms: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_id", _text(self.worker_id, "worker_id"))
        object.__setattr__(self, "capabilities", _strings(self.capabilities, "capabilities"))
        object.__setattr__(self, "currentness_ref", _text(self.currentness_ref, "currentness_ref"))
        object.__setattr__(self, "joined_at_ms", _integer(self.joined_at_ms, "joined_at_ms"))


@dataclass(frozen=True)
class WorkItem:
    work_id: str
    state: WorkState | str
    priority: Priority | str
    parent_objective: str
    residual: str
    currentness_ref: str
    dependencies: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    expected_output: str | None = None
    cost_ceiling_microusd: int = 0
    reopen: str | None = None
    evidence_refs: tuple[str, ...] = ()
    source_order: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "work_id", _text(self.work_id, "work_id"))
        object.__setattr__(self, "state", _state(self.state))
        object.__setattr__(self, "priority", _priority(self.priority))
        object.__setattr__(self, "parent_objective", _text(self.parent_objective, "parent_objective"))
        object.__setattr__(self, "residual", _text(self.residual, "residual"))
        object.__setattr__(self, "currentness_ref", _text(self.currentness_ref, "currentness_ref"))
        object.__setattr__(self, "dependencies", _strings(self.dependencies, "dependencies"))
        object.__setattr__(self, "required_capabilities", _strings(self.required_capabilities, "required_capabilities"))
        object.__setattr__(self, "expected_output", _optional(self.expected_output, "expected_output"))
        object.__setattr__(self, "cost_ceiling_microusd", _integer(self.cost_ceiling_microusd, "cost_ceiling_microusd"))
        object.__setattr__(self, "reopen", _optional(self.reopen, "reopen"))
        object.__setattr__(self, "evidence_refs", _strings(self.evidence_refs, "evidence_refs"))
        object.__setattr__(self, "source_order", _integer(self.source_order, "source_order"))
        if self.work_id in self.dependencies:
            raise ValueError("work item cannot depend on itself")


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    work_id: str
    worker_id: str
    claimed_at_ms: int
    last_checkpoint_ms: int
    released: bool = False

    def __post_init__(self) -> None:
        for field in ("claim_id", "work_id", "worker_id"):
            object.__setattr__(self, field, _text(getattr(self, field), field))
        object.__setattr__(self, "claimed_at_ms", _integer(self.claimed_at_ms, "claimed_at_ms"))
        object.__setattr__(self, "last_checkpoint_ms", _integer(self.last_checkpoint_ms, "last_checkpoint_ms"))
        if self.last_checkpoint_ms < self.claimed_at_ms:
            raise ValueError("checkpoint cannot precede claim")
        if type(self.released) is not bool:
            raise ValueError("released must be boolean")


@dataclass(frozen=True)
class Finding:
    code: str
    work_id: str | None
    message: str
    blocking: bool


@dataclass(frozen=True)
class WorkProjection:
    work: WorkItem
    effective_state: WorkState
    dependency_satisfied: bool
    capability_candidates: tuple[str, ...]
    active_claim: ClaimRecord | None
    stale_claim_recoverable: bool
    eligible: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class WorkGraphSnapshot:
    arena_id: str
    currentness_ref: str
    observed_at_ms: int
    workers: tuple[WorkerSpec, ...]
    work: tuple[WorkProjection, ...]
    findings: tuple[Finding, ...]
    source_digest: str
    version: str = VERSION
    execution_proven: bool = False

    def __post_init__(self) -> None:
        if self.version != VERSION or self.execution_proven is not False:
            raise ValueError("WorkGraph is coordination-only and cannot prove execution")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "version": self.version,
            "arena_id": self.arena_id,
            "currentness_ref": self.currentness_ref,
            "observed_at_ms": self.observed_at_ms,
            "workers": self.workers,
            "work": self.work,
            "findings": self.findings,
            "source_digest": self.source_digest,
            "coordination_only": True,
            "execution_proven": False,
            "wake_effect_started": False,
        }

    @property
    def digest(self) -> str:
        return stable_digest(self.to_dict())


@dataclass(frozen=True)
class SelectionProposal:
    worker_id: str
    work_id: str | None
    claim_required: bool
    stale_recovery_required: bool
    wake_needed: bool
    reasons: tuple[str, ...]
    runtime_effect_started: bool = False

    def __post_init__(self) -> None:
        if self.runtime_effect_started is not False:
            raise ValueError("selection proposal cannot start runtime effects")


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
        object.__setattr__(self, "residual_priority", _priority(self.residual_priority))
        object.__setattr__(self, "residual_required_capabilities", _strings(self.residual_required_capabilities, "residual_required_capabilities"))


def project_workgraph(*, arena_id: str, currentness_ref: str, observed_at_ms: int,
                      workers: Sequence[WorkerSpec], work_items: Sequence[WorkItem],
                      claims: Sequence[ClaimRecord] = (),
                      stale_after_ms: int = DEFAULT_STALE_AFTER_MS) -> WorkGraphSnapshot:
    """Project state; never mutate source state, authorize work, or start a wake."""
    now = _integer(observed_at_ms, "observed_at_ms")
    ttl = _integer(stale_after_ms, "stale_after_ms", 1)
    workers, work_items, claims = tuple(workers), tuple(work_items), tuple(claims)
    worker_map = {worker.worker_id: worker for worker in workers}
    item_map = {item.work_id: item for item in work_items}
    if len(worker_map) != len(workers) or len(item_map) != len(work_items):
        raise ValueError("worker_id and work_id values must be unique")

    findings: list[Finding] = []
    claims_by_work: dict[str, list[ClaimRecord]] = {}
    for claim in claims:
        if claim.work_id not in item_map:
            findings.append(Finding("CLAIM_UNKNOWN_WORK", claim.work_id, "claim targets unknown work", True))
        elif claim.worker_id not in worker_map:
            findings.append(Finding("CLAIM_UNKNOWN_WORKER", claim.work_id, "claim names unknown worker", True))
        elif not claim.released:
            claims_by_work.setdefault(claim.work_id, []).append(claim)

    complete = {item.work_id for item in work_items if item.state is WorkState.COMPLETE}
    projected: list[WorkProjection] = []
    for item in sorted(work_items, key=lambda value: (value.source_order, value.work_id)):
        reasons: list[str] = []
        missing = tuple(dep for dep in item.dependencies if dep not in complete)
        if missing:
            reasons.append("DEPENDENCY_BLOCKED:" + ",".join(missing))
        if any(dep not in item_map for dep in item.dependencies):
            findings.append(Finding("UNKNOWN_DEPENDENCY", item.work_id, "dependency absent from projection", True))

        active = sorted(claims_by_work.get(item.work_id, ()), key=lambda value: (value.last_checkpoint_ms, value.claim_id), reverse=True)
        claim = active[0] if active else None
        if len(active) > 1:
            findings.append(Finding("CLAIM_COLLISION", item.work_id, "multiple active claims", True))
            reasons.append("CLAIM_COLLISION")
        stale = bool(claim and now - claim.last_checkpoint_ms > ttl)
        if stale:
            reasons.append("STALE_CLAIM_RECOVERABLE")

        effective = item.state
        if item.state not in _TERMINAL:
            if claim and not stale:
                effective = WorkState.CLAIMED
            elif item.state is WorkState.CLAIMED and (claim is None or stale):
                effective = WorkState.OPEN
                reasons.append("SOURCE_CLAIM_STATE_REQUIRES_RECOVERY")
            elif item.state is WorkState.BLOCKED and not missing:
                reasons.append("EXPLICIT_BLOCK_REMAINS")

        candidates = tuple(
            worker.worker_id for worker in sorted(workers, key=lambda value: value.worker_id)
            if set(item.required_capabilities).issubset(worker.capabilities)
            and worker.currentness_ref == currentness_ref
        )
        if item.currentness_ref != currentness_ref:
            reasons.append("STALE_WORK_CURRENTNESS")
        if not candidates:
            reasons.append("NO_CAPABILITY_FIT")
        eligible = (
            effective is WorkState.OPEN and not missing and item.currentness_ref == currentness_ref
            and bool(candidates) and len(active) <= 1
        )
        projected.append(WorkProjection(item, effective, not missing, candidates, claim, stale, eligible, tuple(reasons)))

    source = stable_digest({
        "arena_id": arena_id, "currentness_ref": currentness_ref,
        "workers": workers, "work_items": work_items, "claims": claims,
        "stale_after_ms": ttl,
    })
    return WorkGraphSnapshot(arena_id, currentness_ref, now, workers, tuple(projected), tuple(findings), source)


def select_next_work(snapshot: WorkGraphSnapshot, *, worker_id: str) -> SelectionProposal:
    """Propose the cheapest highest-priority eligible cell for one worker."""
    worker_id = _text(worker_id, "worker_id")
    if worker_id not in {worker.worker_id for worker in snapshot.workers}:
        raise ValueError("worker_id is not present in snapshot")
    candidates = [item for item in snapshot.work if item.eligible and worker_id in item.capability_candidates]
    candidates.sort(key=lambda value: (
        _PRIORITY[value.work.priority], value.work.cost_ceiling_microusd,
        value.work.source_order, value.work.work_id,
    ))
    if not candidates:
        return SelectionProposal(worker_id, None, False, False, False, ("NO_ELIGIBLE_NON_DUPLICATE_WORK",))
    selected = candidates[0]
    return SelectionProposal(
        worker_id, selected.work.work_id, True, selected.stale_claim_recoverable, True,
        ("HIGHEST_PRIORITY_ELIGIBLE", "CLAIM_WRITE_REQUIRED_BEFORE_WORK", "WAKE_IS_PROPOSAL_NOT_EXECUTION"),
    )


def compile_successor_residual(*, parent: WorkItem, completion: CompletionRecord,
                               currentness_ref: str, source_order: int) -> WorkItem | None:
    """Create successor work only from an explicit completion residual."""
    if completion.work_id != parent.work_id:
        raise ValueError("completion does not bind to parent")
    if completion.residual is None:
        return None
    payload = {"parent": parent.work_id, "outputs": completion.output_refs,
               "residual": completion.residual, "currentness_ref": currentness_ref}
    return WorkItem(
        f"{parent.work_id}::RESIDUAL::{stable_digest(payload, digest_size=8)}",
        WorkState.OPEN, completion.residual_priority, parent.parent_objective,
        completion.residual, currentness_ref, (parent.work_id,),
        completion.residual_required_capabilities, "Successor residual closure receipt",
        parent.cost_ceiling_microusd, parent.reopen, completion.output_refs, source_order,
    )


_GROUP = re.compile(r"^GROUP-WO\s*\|\s*([^|]+)\s*\|\s*(.*)$")
_FIELDS = {
    "PARENT OBJECTIVE:": "parent_objective", "RESIDUAL:": "residual",
    "DEPENDENCIES:": "dependencies", "EXPECTED OUTPUT:": "expected_output",
    "COST CEILING:": "cost_ceiling", "REOPEN:": "reopen",
}


def parse_group_work_orders(text: str, *, currentness_ref: str) -> tuple[WorkItem, ...]:
    """Conservatively parse formal GROUP-WO blocks; prose never proves completion."""
    if type(text) is not str:
        raise ValueError("text must be a string")
    lines, records, index, order = text.splitlines(), [], 0, 0
    while index < len(lines):
        match = _GROUP.match(lines[index].strip())
        if not match:
            index += 1
            continue
        header = {}
        for part in match.group(2).split("|"):
            if ":" in part:
                key, value = part.split(":", 1)
                header[key.strip().upper()] = value.strip()
        raw_state = header.get("STATE", "OPEN")
        raw_state = "BLOCKED" if raw_state.startswith("BLOCKED") else raw_state
        if raw_state not in {value.value for value in WorkState}:
            index += 1
            continue
        fields, scan = {}, index + 1
        while scan < len(lines):
            line = lines[scan].strip()
            if _GROUP.match(line) or line.startswith(("JOIN |", "CLAIM |", "COMPLETE |", "COMPLETE /", "CHECKPOINT |", "HANDOFF |", "TRIADIC ")):
                break
            for prefix, key in _FIELDS.items():
                if line.startswith(prefix):
                    fields[key] = line[len(prefix):].strip()
                    break
            scan += 1
        if "parent_objective" in fields and "residual" in fields:
            dep_text = fields.get("dependencies", "")
            deps = () if dep_text.upper() in {"", "NONE"} else tuple(
                value.strip() for value in re.split(r"[,;]", dep_text) if value.strip()
            )
            cost = 0
            cost_match = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", fields.get("cost_ceiling", ""))
            if cost_match:
                cost = int(round(float(cost_match.group(1)) * 1_000_000))
            records.append(WorkItem(
                match.group(1).strip(), raw_state, header.get("PRIORITY", "P4"),
                fields["parent_objective"], fields["residual"], currentness_ref,
                deps, (), fields.get("expected_output"), cost, fields.get("reopen"), (), order,
            ))
            order += 1
        index = max(scan, index + 1)
    return tuple(records)


def projection_json(snapshot: WorkGraphSnapshot) -> str:
    return canonical_json(snapshot.to_dict()) + "\n"
