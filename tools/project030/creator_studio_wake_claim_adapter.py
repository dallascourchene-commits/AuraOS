"""Join H-G durable wake intents to H-C fenced work claims.

A wake intent is only a durable eligibility hint. This adapter revalidates the
current in-memory WorkGraph projection and acquires the authoritative local
claim lease before the worker may treat the wake as actionable. It deliberately
does not authorize provider calls or background execution.
"""
from __future__ import annotations

from dataclasses import dataclass

from creator_studio_claim_lease import ClaimBusy, ClaimLeaseReceipt, ClaimLeaseStore
from creator_studio_continuation_harness import HarnessState, WorkerContext
from creator_studio_wake_adapter import WakeIntent


class WakeClaimRefusal(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AcceptedWakeClaim:
    status: str
    event_id: str
    work_id: str
    worker_id: str
    work_version: str
    claim: ClaimLeaseReceipt


def accept_work_wake(
    intent: WakeIntent,
    *,
    state: HarnessState,
    worker: WorkerContext,
    visit_id: str,
    source_cut: str,
    current_work_version: str,
    lease_store: ClaimLeaseStore,
    lease_s: float = 120.0,
    now: float | None = None,
) -> AcceptedWakeClaim:
    """Revalidate a WORK_ELIGIBLE intent then obtain a fenced claim.

    The file-backed claim is the local concurrency fence. `state.claims` remains
    a scheduler projection and is written only *after* the lease succeeds.
    A crash between lease acquisition and projection update leaves a lease that
    expires/reconciles; it cannot create two valid fenced owners.
    """
    if intent.schema != "CreatorStudioWakeIntentV1":
        raise WakeClaimRefusal("WAKE_SCHEMA_MISMATCH")
    if intent.event_type != "WORK_ELIGIBLE" or not intent.work_id:
        raise WakeClaimRefusal("WAKE_NOT_ACTIONABLE_WORK")
    if intent.execution_authorized or intent.provider_calls_authorized or intent.background_execution_claimed:
        raise WakeClaimRefusal("WAKE_AUTHORITY_WIDENING_REFUSED")
    if intent.worker_id != worker.worker_id:
        raise WakeClaimRefusal("WAKE_WORKER_MISMATCH")
    if intent.mission_id != state.active_mission_id:
        raise WakeClaimRefusal("WAKE_MISSION_STALE")
    if state.currentness != "CURRENT":
        raise WakeClaimRefusal("SUPERSEDED_CURRENTNESS")
    if not source_cut:
        raise WakeClaimRefusal("SOURCE_CUT_REQUIRED")
    if intent.work_version != current_work_version:
        raise WakeClaimRefusal("WAKE_WORK_VERSION_STALE")

    item = state.work.get(intent.work_id)
    if item is None:
        raise WakeClaimRefusal("WAKE_WORK_MISSING")
    if item.state != "OPEN":
        raise WakeClaimRefusal("WAKE_WORK_NOT_OPEN")
    if item.mission_id != state.active_mission_id:
        raise WakeClaimRefusal("WAKE_WORK_MISSION_MISMATCH")
    if intent.work_id in state.claims:
        raise WakeClaimRefusal("WAKE_SCHEDULER_CLAIM_ALREADY_PRESENT")
    if not set(item.dependencies).issubset(state.completed):
        raise WakeClaimRefusal("WAKE_DEPENDENCY_NOT_CLOSED")
    if not item.required_capabilities.issubset(worker.capabilities):
        raise WakeClaimRefusal("WAKE_CAPABILITY_MISMATCH")

    try:
        receipt = lease_store.claim(
            intent.work_id,
            worker_id=worker.worker_id,
            visit_id=visit_id,
            capabilities=worker.capabilities,
            currentness=state.currentness,
            source_cut=source_cut,
            effect_ceiling="D0",
            lease_s=lease_s,
            now=now,
        )
    except ClaimBusy as exc:
        raise WakeClaimRefusal("WAKE_CLAIM_BUSY", str(exc)) from exc

    state.claims[intent.work_id] = worker.worker_id
    item.state = "ACTIVE"
    state.history.append(
        {
            "event": "WAKE_ACCEPTED_FENCED_CLAIM",
            "event_id": intent.event_id,
            "work_id": intent.work_id,
            "worker_id": worker.worker_id,
            "work_version": intent.work_version,
            "fence": receipt.fence,
            "source_cut": source_cut,
        }
    )
    return AcceptedWakeClaim(
        status="CLAIMED_D0",
        event_id=intent.event_id,
        work_id=intent.work_id,
        worker_id=worker.worker_id,
        work_version=intent.work_version,
        claim=receipt,
    )


def revalidate_execution_fence(
    accepted: AcceptedWakeClaim,
    *,
    lease_store: ClaimLeaseStore,
    source_cut: str,
    currentness: str = "CURRENT",
    lease_s: float = 120.0,
    now: float | None = None,
) -> ClaimLeaseReceipt:
    """Heartbeat immediately before a consequence-bearing local work step."""
    return lease_store.heartbeat(
        accepted.claim,
        currentness=currentness,
        source_cut=source_cut,
        lease_s=lease_s,
        now=now,
    )
