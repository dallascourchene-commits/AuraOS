from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class SyncState(str, Enum):
    SYNCED = "SYNCED"
    LOCAL_ONLY = "LOCAL_ONLY"
    CLOUD_ONLY = "CLOUD_ONLY"
    LOCAL_AHEAD = "LOCAL_AHEAD"
    CLOUD_AHEAD = "CLOUD_AHEAD"
    CONFLICT = "CONFLICT"
    STALE_GENERATION = "STALE_GENERATION"
    INVALID = "INVALID"


@dataclass(frozen=True)
class Replica:
    exists: bool
    digest: Optional[str] = None
    revision: Optional[str] = None
    generation: Optional[int] = None


@dataclass(frozen=True)
class ArtifactReplicaRecord:
    sid: str
    source_owner: str
    generation: int
    base_digest: Optional[str]
    local: Replica
    cloud: Replica
    cloud_native: bool = False


@dataclass(frozen=True)
class ReconcilePlan:
    state: SyncState
    actions: Tuple[str, ...]
    may_overwrite: bool
    requires_review: bool
    reason: str


def reconcile(record: ArtifactReplicaRecord) -> ReconcilePlan:
    """Classify one semantic artifact's local/cloud replica state.

    The record has one semantic identity and authority owner even though it may
    have two durable physical realizations. The function never performs I/O; it
    emits a fail-closed plan for an owning adapter/resident to execute.
    """
    if not record.sid or not record.source_owner or record.generation < 1:
        return ReconcilePlan(
            SyncState.INVALID, (), False, True, "missing identity/owner/generation"
        )

    local, cloud = record.local, record.cloud
    for replica in (local, cloud):
        if replica.exists and (not replica.digest or replica.generation is None):
            return ReconcilePlan(
                SyncState.INVALID,
                (),
                False,
                True,
                "existing replica lacks digest/generation",
            )
        if replica.exists and replica.generation != record.generation:
            return ReconcilePlan(
                SyncState.STALE_GENERATION,
                (),
                False,
                True,
                "replica generation mismatch",
            )

    if not local.exists and not cloud.exists:
        return ReconcilePlan(
            SyncState.INVALID, (), False, True, "no durable replica exists"
        )
    if local.exists and not cloud.exists:
        return ReconcilePlan(
            SyncState.LOCAL_ONLY,
            ("CREATE_CLOUD_REPLICA",),
            False,
            False,
            "materialize missing cloud replica",
        )
    if cloud.exists and not local.exists:
        return ReconcilePlan(
            SyncState.CLOUD_ONLY,
            ("CREATE_LOCAL_REPLICA",),
            False,
            False,
            "materialize missing local replica",
        )

    if local.digest == cloud.digest:
        return ReconcilePlan(
            SyncState.SYNCED, (), False, False, "replicas agree"
        )

    base = record.base_digest
    if not base:
        return ReconcilePlan(
            SyncState.CONFLICT,
            ("PRESERVE_BOTH", "OPEN_REVIEW"),
            False,
            True,
            "divergent replicas without common base",
        )

    local_changed = local.digest != base
    cloud_changed = cloud.digest != base

    if local_changed and not cloud_changed:
        return ReconcilePlan(
            SyncState.LOCAL_AHEAD,
            ("UPDATE_CLOUD_FROM_LOCAL", "VERIFY_DIGEST"),
            True,
            False,
            "only local changed from common base",
        )
    if cloud_changed and not local_changed:
        return ReconcilePlan(
            SyncState.CLOUD_AHEAD,
            ("UPDATE_LOCAL_FROM_CLOUD", "VERIFY_DIGEST"),
            True,
            False,
            "only cloud changed from common base",
        )

    return ReconcilePlan(
        SyncState.CONFLICT,
        ("PRESERVE_BOTH", "COMPILE_AFFECTED_CONE", "OPEN_REVIEW"),
        False,
        True,
        "both replicas changed from common base",
    )


def can_dispatch_work(record: ArtifactReplicaRecord) -> bool:
    """Workers may act only from an agreed current replica pair."""
    return reconcile(record).state == SyncState.SYNCED


def currentness_token(record: ArtifactReplicaRecord) -> str:
    """Return the compact token bound into a WorkCapsule."""
    plan = reconcile(record)
    if plan.state != SyncState.SYNCED:
        raise ValueError(f"artifact not dispatchable: {plan.state}")
    return f"{record.sid}:g{record.generation}:{record.local.digest}"


def native_cloud_digest(export_digest: str) -> str:
    """Native Google objects use a canonical-export digest, not fake byte identity."""
    if not export_digest:
        raise ValueError("canonical export digest required")
    return export_digest
