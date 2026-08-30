"""Deterministic always-on Arena continuation harness (local/single-host reference).

Owns WorkGraph selection, local atomic lease/fencing, stale-claim recovery,
dependency wakeups, explicit successor compilation, handoff persistence, and
artifact indexing. It deliberately performs no LLM/provider calls and cannot
widen authority or promote work past Gate 10.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable
import json
import os
import time
import uuid

STATE_VERSION = "aura.creator.continuation.v1"
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
ACTIVE_STATES = {"CLAIMED", "IN_PROGRESS"}
AUTONOMOUS_EFFECT_CLASSES = {"D0"}


class HarnessError(RuntimeError):
    pass


class ClaimConflict(HarnessError):
    pass


class StaleFence(HarnessError):
    pass


class InvalidTransition(HarnessError):
    pass


@dataclass(frozen=True)
class WorkerIdentity:
    worker_id: str
    visit_id: str
    capabilities: tuple[str, ...] = ()


@dataclass
class WorkCell:
    cell_id: str
    title: str
    priority: str = "P2"
    state: str = "OPEN"
    dependencies: list[str] = field(default_factory=list)
    required_capabilities: list[str] = field(default_factory=list)
    effect_class: str = "D0"
    source_refs: list[str] = field(default_factory=list)
    residual_digest: str | None = None
    created_order: int = 0
    claim: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None


@dataclass(frozen=True)
class ClaimReceipt:
    cell_id: str
    worker_id: str
    visit_id: str
    fence: int
    lease_expires_at: float


@dataclass(frozen=True)
class HarnessTick:
    action: str
    cell_id: str | None = None
    reason: str | None = None
    reclaimed: tuple[str, ...] = ()
    provider_calls: int = 0
    changed: bool = False


def _canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(obj: Any) -> str:
    return sha256(_canonical(obj)).hexdigest()


def _now() -> float:
    return time.time()


class JsonWorkGraphStore:
    """Atomic local JSON store using lockfile serialization and os.replace."""

    def __init__(self, path: str | os.PathLike[str], *, lock_ttl_s: float = 30.0):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.lock_ttl_s = float(lock_ttl_s)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_unlocked({
                "schema": STATE_VERSION,
                "revision": 0,
                "next_created_order": 1,
                "next_fence": 1,
                "cells": {},
                "artifacts": {},
                "events": [],
            })

    def _read_unlocked(self) -> dict[str, Any]:
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema") != STATE_VERSION:
            raise HarnessError("STATE_SCHEMA_MISMATCH")
        return state

    def _write_unlocked(self, state: dict[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def _acquire(self, timeout_s: float = 5.0) -> int:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, f"{os.getpid()} {_now()}".encode())
                return fd
            except FileExistsError:
                try:
                    if _now() - self.lock_path.stat().st_mtime > self.lock_ttl_s:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise HarnessError("STORE_LOCK_TIMEOUT")
                time.sleep(0.01)

    def _release(self, fd: int) -> None:
        try:
            os.close(fd)
        finally:
            self.lock_path.unlink(missing_ok=True)

    def mutate(self, fn):
        fd = self._acquire()
        try:
            state = self._read_unlocked()
            result = fn(state)
            state["revision"] += 1
            self._write_unlocked(state)
            return result
        finally:
            self._release(fd)

    def snapshot(self) -> dict[str, Any]:
        fd = self._acquire()
        try:
            return self._read_unlocked()
        finally:
            self._release(fd)


class ContinuationHarness:
    def __init__(self, store: JsonWorkGraphStore, *, lease_s: float = 120.0):
        if lease_s <= 0:
            raise ValueError("lease_s must be positive")
        self.store = store
        self.lease_s = float(lease_s)

    @staticmethod
    def _event(state: dict[str, Any], event_type: str, **fields: Any) -> None:
        state["events"].append({"type": event_type, "at": _now(), **fields})

    def add_cell(self, cell: WorkCell) -> None:
        if cell.priority not in PRIORITY_ORDER:
            raise ValueError("invalid priority")
        if cell.state not in {"OPEN", "BLOCKED"}:
            raise ValueError("new cells must start OPEN or BLOCKED")
        def op(state):
            if cell.cell_id in state["cells"]:
                raise ClaimConflict("CELL_ALREADY_EXISTS")
            cell.created_order = state["next_created_order"]
            state["next_created_order"] += 1
            state["cells"][cell.cell_id] = asdict(cell)
            self._event(state, "CELL_ADDED", cell_id=cell.cell_id)
        self.store.mutate(op)

    @staticmethod
    def _deps_closed(cell: dict[str, Any], cells: dict[str, Any]) -> bool:
        return all(dep in cells and cells[dep].get("state") == "CLOSED" for dep in cell.get("dependencies", []))

    @staticmethod
    def _compatible(cell: dict[str, Any], worker: WorkerIdentity) -> bool:
        return set(cell.get("required_capabilities", [])).issubset(set(worker.capabilities))

    def _ready(self, state: dict[str, Any], worker: WorkerIdentity) -> list[dict[str, Any]]:
        cells = state["cells"]
        ready = [c for c in cells.values()
                 if c.get("state") == "OPEN"
                 and c.get("effect_class", "D0") in AUTONOMOUS_EFFECT_CLASSES
                 and self._deps_closed(c, cells)
                 and self._compatible(c, worker)]
        return sorted(ready, key=lambda c: (PRIORITY_ORDER[c.get("priority", "P3")], c.get("created_order", 0), c["cell_id"]))

    @staticmethod
    def _assert_fence(cell: dict[str, Any] | None, receipt: ClaimReceipt) -> None:
        if cell is None or not cell.get("claim"):
            raise StaleFence("CLAIM_MISSING")
        claim = cell["claim"]
        if claim.get("worker_id") != receipt.worker_id or claim.get("visit_id") != receipt.visit_id or claim.get("fence") != receipt.fence:
            raise StaleFence("FENCE_MISMATCH")

    def claim_next(self, worker: WorkerIdentity, *, now: float | None = None) -> ClaimReceipt | None:
        now = _now() if now is None else float(now)
        def op(state):
            for cell in state["cells"].values():
                claim = cell.get("claim")
                if cell.get("state") in ACTIVE_STATES and claim and claim["lease_expires_at"] <= now:
                    cell["state"] = "OPEN"
                    cell["claim"] = None
                    self._event(state, "STALE_CLAIM_RECOVERED", cell_id=cell["cell_id"])
            ready = self._ready(state, worker)
            if not ready:
                return None
            cell = ready[0]
            fence = state["next_fence"]
            state["next_fence"] += 1
            expires = now + self.lease_s
            cell["state"] = "CLAIMED"
            cell["claim"] = {"worker_id": worker.worker_id, "visit_id": worker.visit_id,
                             "claimed_at": now, "heartbeat_at": now,
                             "lease_expires_at": expires, "fence": fence}
            self._event(state, "CELL_CLAIMED", cell_id=cell["cell_id"], worker_id=worker.worker_id, fence=fence)
            return ClaimReceipt(cell["cell_id"], worker.worker_id, worker.visit_id, fence, expires)
        return self.store.mutate(op)

    def heartbeat(self, receipt: ClaimReceipt, *, now: float | None = None) -> ClaimReceipt:
        now = _now() if now is None else float(now)
        def op(state):
            cell = state["cells"].get(receipt.cell_id)
            self._assert_fence(cell, receipt)
            claim = cell["claim"]
            if claim["lease_expires_at"] <= now:
                raise StaleFence("LEASE_EXPIRED")
            claim["heartbeat_at"] = now
            claim["lease_expires_at"] = now + self.lease_s
            cell["state"] = "IN_PROGRESS"
            self._event(state, "HEARTBEAT", cell_id=receipt.cell_id, fence=receipt.fence)
            return ClaimReceipt(receipt.cell_id, receipt.worker_id, receipt.visit_id, receipt.fence, claim["lease_expires_at"])
        return self.store.mutate(op)

    @staticmethod
    def _validate_handoff(handoff: dict[str, Any]) -> None:
        required = {"artifact_refs", "tests", "unresolved_residual", "exact_next_action", "invalidators", "source_refs", "effect_status"}
        missing = sorted(required - set(handoff))
        if missing:
            raise InvalidTransition("HANDOFF_MISSING:" + ",".join(missing))

    def complete(self, receipt: ClaimReceipt, *, handoff: dict[str, Any], artifacts: Iterable[dict[str, Any]] = (), now: float | None = None) -> tuple[str, ...]:
        self._validate_handoff(handoff)
        now = _now() if now is None else float(now)
        def op(state):
            cell = state["cells"].get(receipt.cell_id)
            self._assert_fence(cell, receipt)
            if cell["claim"]["lease_expires_at"] <= now:
                raise StaleFence("LEASE_EXPIRED")
            digests = []
            for artifact in artifacts:
                digest = _digest(artifact)
                state["artifacts"].setdefault(digest, {"digest": digest, "cell_id": receipt.cell_id,
                                                       "worker_id": receipt.worker_id, "artifact": artifact})
                digests.append(digest)
            cell["handoff"] = handoff
            cell["state"] = "CLOSED"
            cell["claim"] = None
            self._event(state, "CELL_CLOSED", cell_id=receipt.cell_id, artifact_digests=digests)
            woken = []
            for candidate in state["cells"].values():
                if candidate.get("state") == "OPEN" and receipt.cell_id in candidate.get("dependencies", []) and self._deps_closed(candidate, state["cells"]):
                    woken.append(candidate["cell_id"])
                    self._event(state, "DEPENDENCY_WAKE", cell_id=candidate["cell_id"], predecessor=receipt.cell_id)
            return tuple(sorted(woken))
        return self.store.mutate(op)

    def compile_successor(self, residual: dict[str, Any], *, title: str, priority: str = "P2", effect_class: str = "D0",
                          source_refs: Iterable[str] = (), dependencies: Iterable[str] = (), required_capabilities: Iterable[str] = ()) -> str:
        """Compile an explicit verified residual; never invent residual content."""
        digest = _digest(residual)
        if priority not in PRIORITY_ORDER:
            raise ValueError("invalid priority")
        def op(state):
            for cell in state["cells"].values():
                if cell.get("residual_digest") == digest and cell.get("state") != "STALE":
                    return cell["cell_id"]
            cell_id = f"AUTO-{digest[:12]}"
            order = state["next_created_order"]
            state["next_created_order"] += 1
            state["cells"][cell_id] = asdict(WorkCell(cell_id=cell_id, title=title, priority=priority,
                effect_class=effect_class, source_refs=list(source_refs), dependencies=list(dependencies),
                required_capabilities=list(required_capabilities), residual_digest=digest, created_order=order))
            self._event(state, "SUCCESSOR_COMPILED", cell_id=cell_id, residual_digest=digest)
            return cell_id
        return self.store.mutate(op)

    def tick(self, worker: WorkerIdentity, *, explicit_residual: dict[str, Any] | None = None,
             successor_title: str = "Compiled successor residual", now: float | None = None) -> HarnessTick:
        """One deterministic scan/select tick. No-change ticks make zero model/provider calls."""
        now = _now() if now is None else float(now)
        before = self.store.snapshot()
        stale = tuple(sorted(c["cell_id"] for c in before["cells"].values()
                             if c.get("state") in ACTIVE_STATES and c.get("claim") and c["claim"]["lease_expires_at"] <= now))
        receipt = self.claim_next(worker, now=now)
        if receipt:
            return HarnessTick("CLAIMED", receipt.cell_id, reclaimed=stale, changed=True)
        if explicit_residual is not None:
            successor = self.compile_successor(explicit_residual, title=successor_title)
            receipt = self.claim_next(worker, now=now)
            if receipt:
                return HarnessTick("SUCCESSOR_CLAIMED", receipt.cell_id, reclaimed=stale, changed=True)
            return HarnessTick("BLOCKED_SUCCESSOR", successor, "SUCCESSOR_NOT_LAWFUL_OR_COMPATIBLE", stale, 0, True)
        snapshot = self.store.snapshot()
        reason = "NO_ELIGIBLE_CELL" if any(c.get("state") == "OPEN" for c in snapshot["cells"].values()) else "NO_OPEN_WORK"
        return HarnessTick("IDLE_NO_CHANGE", reason=reason, reclaimed=stale, changed=bool(stale))
