from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


class HarnessRefusal(RuntimeError):
    """Typed fail-closed refusal emitted by the continuation harness."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


PRIORITY_STAGE_ORDER: Mapping[str, int] = {
    "PRIORITY": 0,
    "REVIEW": 1,
    "BACKBURNER": 2,
}

LAWFUL_TERMINALS = {
    "GATE10_COMPLETE",
    "BLOCKED_EXTERNAL_BOUNDARY",
    "NO_ELIGIBLE_WORK_AFTER_REVIEW",
    "SUPERSEDED_CURRENTNESS",
    "OWNER_STOP",
}


@dataclass(frozen=True)
class GateEvidence:
    evidence_class: str
    ref: str

    def __post_init__(self) -> None:
        if not self.evidence_class.strip():
            raise ValueError("evidence_class required")
        if not self.ref.strip():
            raise ValueError("evidence ref required")


GATE_EVIDENCE_REQUIREMENTS: Mapping[int, frozenset[str]] = {
    1: frozenset({"ARENA_ADMISSION_RECEIPT"}),
    2: frozenset({"WORKGRAPH_PROJECTION_RECEIPT"}),
    3: frozenset({"CONTINUATION_REPLAY_RECEIPT"}),
    4: frozenset({"SUCCESSOR_GROUP_WO_RECEIPT"}),
    5: frozenset({"COLLAB_WAKE_RECEIPT"}),
    6: frozenset({"COST_ROUTE_RECEIPT"}),
    7: frozenset({"ADVERSARIAL_REPLAY_RECEIPT"}),
    8: frozenset({"FRESH_WORKER_PROBE_RECEIPT"}),
    9: frozenset({"LIVE_CREATOR_STUDIO_INTEGRATION_RECEIPT"}),
    10: frozenset({
        "DIFFERENT_J_REVIEW_RECEIPT",
        "RESTART_REPLAY_RECEIPT",
        "CURRENTNESS_REPLAY_RECEIPT",
        "MISSION_RETURN_RECEIPT",
    }),
}


@dataclass(frozen=True)
class WorkerContext:
    worker_id: str
    capabilities: frozenset[str] = frozenset()


@dataclass
class WorkItem:
    work_id: str
    mission_id: str
    objective: str
    stage: str = "PRIORITY"
    priority: int = 100
    dependencies: Tuple[str, ...] = ()
    required_capabilities: frozenset[str] = frozenset()
    future_cost_avoided: float = 0.0
    dependency_unlock: float = 0.0
    information_gain: float = 0.0
    estimated_total_cost: float = 0.0
    state: str = "OPEN"
    parent_work_id: Optional[str] = None
    residual_fingerprint: Optional[str] = None

    def __post_init__(self) -> None:
        if self.stage not in PRIORITY_STAGE_ORDER:
            raise ValueError(f"unknown work stage: {self.stage}")
        if not self.work_id:
            raise ValueError("work_id required")
        if not self.mission_id:
            raise ValueError("mission_id required")


@dataclass(frozen=True)
class Residual:
    summary: str
    mission_id: str
    consequence: float
    material: bool = True
    stage: str = "PRIORITY"
    priority: int = 100
    dependencies: Tuple[str, ...] = ()
    required_capabilities: frozenset[str] = frozenset()
    future_cost_avoided: float = 0.0
    dependency_unlock: float = 0.0
    information_gain: float = 0.0
    estimated_total_cost: float = 0.0

    def fingerprint(self) -> str:
        payload = {
            "summary": " ".join(self.summary.lower().split()),
            "mission_id": self.mission_id,
            "dependencies": sorted(self.dependencies),
            "required_capabilities": sorted(self.required_capabilities),
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HarnessAction:
    action: str
    reason: str
    work_id: Optional[str] = None
    mission_id: Optional[str] = None
    requires_inference: bool = False
    recheck_trigger: Optional[str] = None


@dataclass
class HarnessState:
    active_mission_id: str
    canonical_mission_id: str
    temporary_mission: bool = False
    gate: int = 0
    work: Dict[str, WorkItem] = field(default_factory=dict)
    claims: Dict[str, str] = field(default_factory=dict)
    completed: Set[str] = field(default_factory=set)
    residual_fingerprints: Set[str] = field(default_factory=set)
    currentness: str = "CURRENT"
    owner_stop: bool = False
    external_boundary_ref: Optional[str] = None
    history: List[dict] = field(default_factory=list)
    _sequence: int = 0

    def add_work(self, item: WorkItem) -> None:
        if item.work_id in self.work:
            raise HarnessRefusal("DUPLICATE_WORK_ID", item.work_id)
        self.work[item.work_id] = item
        self.history.append({"event": "WORK_ADDED", "work_id": item.work_id})

    def _next_sequence(self) -> int:
        self._sequence += 1
        return self._sequence


def _score(item: WorkItem) -> Tuple[float, float, float, float, int, str]:
    """Deterministic ranking. Higher mission value first; lower cost/priority next."""
    return (
        -item.dependency_unlock,
        -item.future_cost_avoided,
        -item.information_gain,
        item.estimated_total_cost,
        item.priority,
        item.work_id,
    )


def eligible_work(
    state: HarnessState,
    worker: WorkerContext,
    *,
    stage: Optional[str] = None,
) -> List[WorkItem]:
    """Return mission-aligned, dependency-ready, unclaimed work without inference."""
    if state.currentness != "CURRENT":
        raise HarnessRefusal("SUPERSEDED_CURRENTNESS", "rebase before work selection")

    result: List[WorkItem] = []
    for item in state.work.values():
        if item.state != "OPEN":
            continue
        if item.mission_id != state.active_mission_id:
            continue
        if stage is not None and item.stage != stage:
            continue
        if item.work_id in state.claims:
            continue
        if not set(item.dependencies).issubset(state.completed):
            continue
        if not item.required_capabilities.issubset(worker.capabilities):
            continue
        result.append(item)
    return sorted(result, key=_score)


def claim_best_available(state: HarnessState, worker: WorkerContext) -> HarnessAction:
    """Priority -> Review -> Backburner, matching Aura replenishment law."""
    if state.owner_stop:
        return HarnessAction("STOP", "OWNER_STOP", mission_id=state.active_mission_id)
    if state.currentness != "CURRENT":
        return HarnessAction(
            "REBASE",
            "SUPERSEDED_CURRENTNESS",
            mission_id=state.active_mission_id,
            recheck_trigger="currentness becomes CURRENT",
        )
    if state.gate >= 10:
        return restore_canonical_mission(state)

    for stage in ("PRIORITY", "REVIEW", "BACKBURNER"):
        candidates = eligible_work(state, worker, stage=stage)
        if not candidates:
            continue
        item = candidates[0]
        state.claims[item.work_id] = worker.worker_id
        item.state = "ACTIVE"
        state.history.append(
            {"event": "CLAIM", "work_id": item.work_id, "worker_id": worker.worker_id}
        )
        return HarnessAction(
            "CLAIM_AND_CONTINUE",
            f"CLAIM_{stage}",
            work_id=item.work_id,
            mission_id=state.active_mission_id,
            requires_inference=False,
        )

    return HarnessAction(
        "STOP",
        "NO_ELIGIBLE_WORK_AFTER_REVIEW",
        mission_id=state.active_mission_id,
        requires_inference=False,
        recheck_trigger="dependency/currentness/new-work event",
    )


def compile_successor_work(
    state: HarnessState,
    parent_work_id: str,
    residuals: Sequence[Residual],
) -> List[WorkItem]:
    """Turn material consequence-changing residuals into deduplicated GROUP-WOs."""
    created: List[WorkItem] = []
    for residual in residuals:
        if residual.mission_id != state.active_mission_id:
            continue
        if not residual.material or residual.consequence <= 0 or not residual.summary.strip():
            continue
        if residual.stage not in PRIORITY_STAGE_ORDER:
            raise HarnessRefusal("INVALID_RESIDUAL_STAGE", residual.stage)
        fingerprint = residual.fingerprint()
        if fingerprint in state.residual_fingerprints:
            continue
        if any(w.residual_fingerprint == fingerprint for w in state.work.values()):
            state.residual_fingerprints.add(fingerprint)
            continue
        seq = state._next_sequence()
        work_id = f"GROUP-WO-{seq:04d}-{fingerprint[:8]}"
        item = WorkItem(
            work_id=work_id,
            mission_id=residual.mission_id,
            objective=residual.summary.strip(),
            stage=residual.stage,
            priority=residual.priority,
            dependencies=tuple(residual.dependencies),
            required_capabilities=residual.required_capabilities,
            future_cost_avoided=residual.future_cost_avoided,
            dependency_unlock=residual.dependency_unlock,
            information_gain=residual.information_gain,
            estimated_total_cost=residual.estimated_total_cost,
            parent_work_id=parent_work_id,
            residual_fingerprint=fingerprint,
        )
        state.residual_fingerprints.add(fingerprint)
        state.add_work(item)
        state.history.append(
            {
                "event": "SUCCESSOR_COMPILED",
                "parent_work_id": parent_work_id,
                "work_id": work_id,
                "fingerprint": fingerprint,
            }
        )
        created.append(item)
    return created


def complete_and_continue(
    state: HarnessState,
    worker: WorkerContext,
    work_id: str,
    *,
    residuals: Sequence[Residual] = (),
) -> HarnessAction:
    """Finish -> release -> compile residuals -> scan -> claim next work."""
    if state.currentness != "CURRENT":
        return HarnessAction("REBASE", "SUPERSEDED_CURRENTNESS", mission_id=state.active_mission_id)
    item = state.work.get(work_id)
    if item is None:
        raise HarnessRefusal("UNKNOWN_WORK_ID", work_id)
    if state.claims.get(work_id) != worker.worker_id:
        raise HarnessRefusal("CLAIM_OWNERSHIP_MISMATCH", work_id)

    item.state = "COMPLETE"
    state.completed.add(work_id)
    state.claims.pop(work_id, None)
    state.history.append(
        {"event": "FINISH_RELEASE", "work_id": work_id, "worker_id": worker.worker_id}
    )
    compile_successor_work(state, work_id, residuals)
    return claim_best_available(state, worker)


def advance_gate(
    state: HarnessState,
    target_gate: int,
    evidence: Iterable[GateEvidence],
) -> int:
    """Advance exactly one gate only when that gate's typed evidence classes are present."""
    if target_gate != state.gate + 1:
        raise HarnessRefusal("GATE_SEQUENCE_VIOLATION", f"{state.gate}->{target_gate}")
    if target_gate < 1 or target_gate > 10:
        raise HarnessRefusal("INVALID_GATE", str(target_gate))

    items = tuple(evidence)
    if not items:
        raise HarnessRefusal("GATE_EVIDENCE_REQUIRED", str(target_gate))
    if any(not isinstance(item, GateEvidence) for item in items):
        raise HarnessRefusal("GATE_EVIDENCE_SHAPE_INVALID", str(target_gate))

    present = {item.evidence_class for item in items}
    required = GATE_EVIDENCE_REQUIREMENTS[target_gate]
    missing = sorted(required - present)
    if missing:
        raise HarnessRefusal(
            "GATE_EVIDENCE_CLASS_MISSING",
            f"gate={target_gate} missing={','.join(missing)}",
        )

    state.gate = target_gate
    state.history.append(
        {
            "event": "GATE_ADVANCE",
            "gate": target_gate,
            "evidence": [
                {"evidence_class": item.evidence_class, "ref": item.ref}
                for item in items
            ],
        }
    )
    return state.gate


def restore_canonical_mission(state: HarnessState) -> HarnessAction:
    """At Gate 10, infrastructure remains but temporary mission automatically releases."""
    if state.gate < 10:
        raise HarnessRefusal("GATE10_REQUIRED_FOR_MISSION_RETURN", str(state.gate))
    previous = state.active_mission_id
    state.active_mission_id = state.canonical_mission_id
    state.temporary_mission = False
    state.history.append(
        {
            "event": "MISSION_RETURN",
            "from": previous,
            "to": state.canonical_mission_id,
        }
    )
    return HarnessAction(
        "REBASE_AND_CONTINUE",
        "GATE10_COMPLETE_CANONICAL_MISSION_RESTORED",
        mission_id=state.canonical_mission_id,
        requires_inference=False,
    )


def assert_terminal_allowed(
    state: HarnessState,
    worker: WorkerContext,
    requested_reason: str,
) -> None:
    """Reject untyped or predicate-unbound terminal behavior."""

    if requested_reason not in LAWFUL_TERMINALS:
        if state.currentness == "CURRENT":
            if any(eligible_work(state, worker, stage=s) for s in PRIORITY_STAGE_ORDER):
                raise HarnessRefusal("PREMATURE_TERMINAL_REFUSED", requested_reason)
        raise HarnessRefusal("UNTYPED_TERMINAL_REFUSED", requested_reason)

    if requested_reason == "GATE10_COMPLETE":
        if state.gate < 10:
            raise HarnessRefusal("GATE10_NOT_REACHED", str(state.gate))
        return

    if requested_reason == "OWNER_STOP":
        if not state.owner_stop:
            raise HarnessRefusal("OWNER_STOP_NOT_BOUND")
        return

    if requested_reason == "BLOCKED_EXTERNAL_BOUNDARY":
        if not (state.external_boundary_ref and state.external_boundary_ref.strip()):
            raise HarnessRefusal("EXTERNAL_BOUNDARY_NOT_BOUND")
        return

    if requested_reason == "SUPERSEDED_CURRENTNESS":
        if state.currentness == "CURRENT":
            raise HarnessRefusal("CURRENTNESS_NOT_SUPERSEDED")
        return

    if requested_reason == "NO_ELIGIBLE_WORK_AFTER_REVIEW":
        if state.currentness != "CURRENT":
            raise HarnessRefusal("CURRENTNESS_REBASE_REQUIRED")
        if any(eligible_work(state, worker, stage=s) for s in PRIORITY_STAGE_ORDER):
            raise HarnessRefusal("ELIGIBLE_WORK_REMAINS", requested_reason)
        return

    raise HarnessRefusal("UNTYPED_TERMINAL_REFUSED", requested_reason)


def continuation_snapshot(state: HarnessState, worker: WorkerContext) -> dict:
    """Machine-readable zero-inference scheduler snapshot."""
    counts = {}
    for stage in PRIORITY_STAGE_ORDER:
        counts[stage] = len(eligible_work(state, worker, stage=stage)) if state.currentness == "CURRENT" else 0
    return {
        "schema": "CreatorStudioContinuationHarnessV1",
        "active_mission_id": state.active_mission_id,
        "canonical_mission_id": state.canonical_mission_id,
        "temporary_mission": state.temporary_mission,
        "gate": state.gate,
        "currentness": state.currentness,
        "eligible_counts": counts,
        "active_claim_count": len(state.claims),
        "completed_count": len(state.completed),
        "scheduler_requires_inference": False,
    }
