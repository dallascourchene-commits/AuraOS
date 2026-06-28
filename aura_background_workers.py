"""
[AURA_MASTER_KEY]
ST3GG_BASE: 0xa9f3-[Q-SYS:AURA_BACKGROUND_WORKERS]
DIKWP_TIER: WISDOM
PWFST_ALIGNMENT: GIDINAWENDIMIN (Swarm Synergy / Observe and Propose)
DEPENDENCIES: asyncio, dataclasses, hashlib, json, time, typing
FUNCTIONS: WorkerProposal, BackgroundWorker, StaleDataWorker,
           BoundaryContractWorker, VerifierCoverageWorker, DreamUsefulnessWorker,
           BackgroundWorkerSupervisor
SYNOPSIS: Observe-only background workers. They read system state and propose
          ActionCapsule-shaped dicts into an asyncio proposal queue. They CANNOT
          mutate production directly. Every proposal carries status="proposed"
          and forbidden_actions=["mutate_production"]. Worker outcomes are
          recorded in QDKT.
[/AURA_MASTER_KEY]
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any

AURA_BACKGROUND_WORKERS_VERSION = "AURA_BACKGROUND_WORKERS_V1"


def _hash_payload(payload: Any, *, size: int = 16) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=size).hexdigest()


@dataclass
class WorkerProposal:
    """A proposal emitted by a background worker. Never mutates production."""

    proposal_id: str
    worker_name: str
    domain: str
    capsule: dict[str, Any]
    rationale: str
    status: str = "proposed"
    forbidden_actions: list[str] = field(
        default_factory=lambda: ["mutate_production", "bypass_verifier", "bypass_shadow", "bypass_judge"]
    )
    requires_verifier_gate: bool = True
    requires_human_approval: bool = True
    phase_hash: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": AURA_BACKGROUND_WORKERS_VERSION,
            "proposal_id": self.proposal_id,
            "worker_name": self.worker_name,
            "domain": self.domain,
            "capsule": dict(self.capsule),
            "rationale": self.rationale,
            "status": self.status,
            "forbidden_actions": list(self.forbidden_actions),
            "requires_verifier_gate": self.requires_verifier_gate,
            "requires_human_approval": self.requires_human_approval,
            "phase_hash": self.phase_hash,
            "ts": self.ts,
        }


class BackgroundWorker:
    """Base class for observe-only background workers.

    Subclasses implement ``observe()`` which returns a list of WorkerProposal
    dicts. Workers never hold write handles to production files or sidecars.
    """

    name: str = "base_worker"
    domain: str = "generic"

    def __init__(self, *, qdkt: Any = None, interval: float = 30.0) -> None:
        self.qdkt = qdkt
        self.interval = interval
        self._running = False

    async def observe(self) -> list[WorkerProposal]:
        """Return proposals derived from observed state. Override in subclasses."""
        return []

    def _make_proposal(
        self,
        *,
        capsule: dict[str, Any],
        rationale: str,
    ) -> WorkerProposal:
        payload = {
            "worker_name": self.name,
            "domain": self.domain,
            "capsule": capsule,
            "rationale": rationale,
            "ts": time.time(),
        }
        proposal_id = f"PROP-{_hash_payload(payload)[:12]}"
        phase_hash = _hash_payload({**payload, "proposal_id": proposal_id})
        return WorkerProposal(
            proposal_id=proposal_id,
            worker_name=self.name,
            domain=self.domain,
            capsule=capsule,
            rationale=rationale,
            phase_hash=phase_hash,
        )

    def _record_outcome(self, *, success: bool, proposal_count: int, error: str = "") -> None:
        if self.qdkt is None:
            return
        try:
            self.qdkt.observe(
                "worker_outcome",
                {
                    "worker_name": self.name,
                    "domain": self.domain,
                    "success": bool(success),
                    "proposal_count": int(proposal_count),
                    "error": error[:256],
                },
                rationale=f"worker {self.name} outcome",
                concept=f"worker:{self.name}",
                confidence=0.8 if success else 0.3,
            )
        except Exception:
            pass

    async def run_once(self, queue: asyncio.Queue[WorkerProposal]) -> int:
        """Run one observation cycle and enqueue any proposals."""
        try:
            proposals = await self.observe()
        except Exception as exc:  # noqa: BLE001
            self._record_outcome(success=False, proposal_count=0, error=str(exc))
            return 0
        enqueued = 0
        for proposal in proposals:
            try:
                queue.put_nowait(proposal)
                enqueued += 1
            except asyncio.QueueFull:
                # Queue is full; drop the proposal and record it
                self._record_outcome(success=False, proposal_count=0, error="queue_full")
                break
        self._record_outcome(success=True, proposal_count=enqueued)
        return enqueued

    async def loop(self, queue: asyncio.Queue[WorkerProposal], *, stop_event: asyncio.Event) -> None:
        """Run the worker on its interval until stop_event is set."""
        self._running = True
        while not stop_event.is_set():
            try:
                await self.run_once(queue)
            except Exception:  # noqa: BLE001
                pass
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                continue
        self._running = False


# ---------------------------------------------------------------------------
# Concrete workers
# ---------------------------------------------------------------------------

class StaleDataWorker(BackgroundWorker):
    """Scans sidecar observations for stale or near-stale records."""

    name = "stale_data_worker"
    domain = "travel"

    def __init__(self, *, qdkt: Any = None, interval: float = 60.0, sidecar: Any = None) -> None:
        super().__init__(qdkt=qdkt, interval=interval)
        self.sidecar = sidecar

    async def observe(self) -> list[WorkerProposal]:
        proposals: list[WorkerProposal] = []
        if self.sidecar is None:
            return proposals
        try:
            # Offload blocking SQLite query to executor thread
            def _fetch_rows():
                return self.sidecar.conn.execute(
                    "SELECT price_id, resort_id, observed_at, freshness_status "
                    "FROM price_observations ORDER BY observed_at DESC LIMIT 50"
                ).fetchall()
            
            rows = await asyncio.to_thread(_fetch_rows)
        except Exception:
            return proposals
        now = time.time()
        for row in rows:
            item = dict(row) if hasattr(row, "keys") else {}
            status = str(item.get("freshness_status") or "").lower()
            if status in {"stale", "expired", "unverified"}:
                proposals.append(
                    self._make_proposal(
                        capsule={
                            "objective": f"Re-fetch stale price {item.get('price_id')}",
                            "target": {"price_id": item.get("price_id"), "resort_id": item.get("resort_id")},
                            "action": "request_live_recheck",
                            "domain": "travel",
                        },
                        rationale=f"price {item.get('price_id')} freshness_status={status}",
                    )
                )
        return proposals


class BoundaryContractWorker(BackgroundWorker):
    """Finds unresolved (placeholder) BoundaryContracts and proposes resolution."""

    name = "boundary_contract_worker"
    domain = "arena"

    def __init__(self, *, qdkt: Any = None, interval: float = 45.0, arena_store: Any = None) -> None:
        super().__init__(qdkt=qdkt, interval=interval)
        self.arena_store = arena_store

    async def observe(self) -> list[WorkerProposal]:
        proposals: list[WorkerProposal] = []
        if self.arena_store is None:
            return proposals
        contracts = getattr(self.arena_store, "boundary_contracts", []) or []
        for contract in contracts:
            if isinstance(contract, dict) and contract.get("status") == "placeholder":
                proposals.append(
                    self._make_proposal(
                        capsule={
                            "objective": f"Resolve placeholder BoundaryContract {contract.get('contract_id')}",
                            "target": {"contract_id": contract.get("contract_id")},
                            "action": "materialize_boundary_contract",
                            "domain": contract.get("domain", "arena"),
                        },
                        rationale=f"unresolved BoundaryContract {contract.get('contract_id')}",
                    )
                )
        return proposals


class VerifierCoverageWorker(BackgroundWorker):
    """Checks that staged capsules have verifier gates; proposes coverage gaps."""

    name = "verifier_coverage_worker"
    domain = "arena"

    def __init__(self, *, qdkt: Any = None, interval: float = 50.0, arena_store: Any = None) -> None:
        super().__init__(qdkt=qdkt, interval=interval)
        self.arena_store = arena_store

    async def observe(self) -> list[WorkerProposal]:
        proposals: list[WorkerProposal] = []
        if self.arena_store is None:
            return proposals
        capsules = getattr(self.arena_store, "action_capsules", []) or []
        ledger = getattr(self.arena_store, "verification_ledger", []) or []
        covered_ids = {
            entry.get("capsule_id") for entry in ledger if isinstance(entry, dict)
        }
        for capsule in capsules:
            if isinstance(capsule, dict):
                cid = capsule.get("capsule_id")
                if cid and cid not in covered_ids:
                    proposals.append(
                        self._make_proposal(
                            capsule={
                                "objective": f"Add verifier gate for capsule {cid}",
                                "target": {"capsule_id": cid},
                                "action": "add_verifier_gate",
                                "domain": "arena",
                            },
                            rationale=f"capsule {cid} has no verifier coverage",
                        )
                    )
        return proposals


class DreamUsefulnessWorker(BackgroundWorker):
    """Observes retrieval events and proposes DREAM usefulness scoring rows."""

    name = "dream_usefulness_worker"
    domain = "dream"

    def __init__(self, *, qdkt: Any = None, interval: float = 40.0, retrieval_events: list[dict[str, Any]] | None = None) -> None:
        super().__init__(qdkt=qdkt, interval=interval)
        self.retrieval_events = retrieval_events or []

    async def observe(self) -> list[WorkerProposal]:
        proposals: list[WorkerProposal] = []
        for event in self.retrieval_events:
            if not isinstance(event, dict):
                continue
            proposals.append(
                self._make_proposal(
                    capsule={
                        "objective": "Record DREAM usefulness for retrieval event",
                        "target": {"candidate_id": event.get("candidate_id")},
                        "action": "observe_retrieval_usefulness",
                        "domain": "dream",
                        "score_row": event,
                    },
                    rationale=f"unscored retrieval candidate {event.get('candidate_id')}",
                )
            )
        # Clear the buffer after proposing
        self.retrieval_events.clear()
        return proposals


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

class BackgroundWorkerSupervisor:
    """Manages a fleet of observe-only background workers.

    Workers propose into a shared asyncio queue. The supervisor never
    applies proposals — that is the Arena/Architect Loop's job, gated by
    verifiers and human approval.
    """

    def __init__(self, *, qdkt: Any = None, queue_maxsize: int = 1000) -> None:
        self.qdkt = qdkt
        self.proposal_queue: asyncio.Queue[WorkerProposal] = asyncio.Queue(maxsize=queue_maxsize)
        self._workers: list[BackgroundWorker] = []
        self._stop_event: asyncio.Event | None = None
        self._tasks: list[asyncio.Task] = []
        self._drained: list[WorkerProposal] = []

    def add_worker(self, worker: BackgroundWorker) -> None:
        self._workers.append(worker)

    def list_workers(self) -> list[dict[str, Any]]:
        return [
            {"name": w.name, "domain": w.domain, "interval": w.interval}
            for w in self._workers
        ]

    async def start(self) -> None:
        self._stop_event = asyncio.Event()
        self._tasks = [
            asyncio.create_task(worker.loop(self.proposal_queue, stop_event=self._stop_event))
            for worker in self._workers
        ]

    async def stop(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

    async def run_once_all(self) -> int:
        """Run one observation cycle for all workers synchronously (for tests)."""
        total = 0
        for worker in self._workers:
            total += await worker.run_once(self.proposal_queue)
        return total

    def drain_proposals(self) -> list[WorkerProposal]:
        """Drain all currently-queued proposals without async waiting."""
        proposals: list[WorkerProposal] = []
        while not self.proposal_queue.empty():
            try:
                proposals.append(self.proposal_queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        self._drained.extend(proposals)
        return proposals

    def drained_history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self._drained[-limit:]]


def build_default_supervisor(*, qdkt: Any = None, sidecar: Any = None, arena_store: Any = None) -> BackgroundWorkerSupervisor:
    """Build a supervisor with the default worker fleet."""
    supervisor = BackgroundWorkerSupervisor(qdkt=qdkt)
    supervisor.add_worker(StaleDataWorker(qdkt=qdkt, sidecar=sidecar))
    supervisor.add_worker(BoundaryContractWorker(qdkt=qdkt, arena_store=arena_store))
    supervisor.add_worker(VerifierCoverageWorker(qdkt=qdkt, arena_store=arena_store))
    supervisor.add_worker(DreamUsefulnessWorker(qdkt=qdkt))
    return supervisor


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aura Background Workers — list workers")
    parser.add_argument("--list", action="store_true", help="list registered workers")
    args = parser.parse_args(argv)
    supervisor = build_default_supervisor()
    if args.list:
        print(json.dumps(supervisor.list_workers(), indent=2, sort_keys=True))
    else:
        print(f"Aura Background Workers: {len(supervisor.list_workers())} workers registered")
        for w in supervisor.list_workers():
            print(f"  - {w['name']} (domain={w['domain']}, interval={w['interval']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())