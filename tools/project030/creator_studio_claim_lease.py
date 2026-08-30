"""Creator Studio H-C claim/lease/fencing primitive.

This is a D0 local/single-host reference for shared WorkGraph claim integrity.
It does not choose objectives, route models/providers, or widen authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping
import json
import os
import time
import uuid

SCHEMA = "CreatorStudioClaimLeaseV1"


class LeaseError(RuntimeError):
    pass


class ClaimBusy(LeaseError):
    pass


class StaleFence(LeaseError):
    pass


class CurrentnessRequired(LeaseError):
    pass


@dataclass(frozen=True)
class ClaimLeaseReceipt:
    work_id: str
    worker_id: str
    visit_id: str
    fence: int
    claimed_at: float
    heartbeat_at: float
    lease_expires_at: float
    currentness: str
    source_cut: str
    effect_ceiling: str
    capabilities_digest: str


def _digest_capabilities(capabilities: Iterable[str]) -> str:
    payload = json.dumps(sorted(set(capabilities)), separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


class ClaimLeaseStore:
    """File-backed atomic claim registry with monotonic fencing tokens.

    `O_EXCL` lockfile serialization plus `os.replace` closes local-process
    scan/claim write races. The fence closes stale-worker completion races after
    lease recovery. This is not a multi-host consensus protocol.
    """

    def __init__(self, path: str | os.PathLike[str], *, lock_ttl_s: float = 30.0):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.lock_ttl_s = float(lock_ttl_s)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write_unlocked({"schema": SCHEMA, "revision": 0, "next_fence": 1, "claims": {}, "events": []})

    def _read_unlocked(self) -> dict[str, Any]:
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("schema") != SCHEMA:
            raise LeaseError("CLAIM_STORE_SCHEMA_MISMATCH")
        return state

    def _write_unlocked(self, state: Mapping[str, Any]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + f".{uuid.uuid4().hex}.tmp")
        tmp.write_text(json.dumps(state, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)

    def _acquire_lock(self, timeout_s: float = 5.0) -> int:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.write(fd, f"pid={os.getpid()} at={time.time()}".encode("ascii"))
                return fd
            except FileExistsError:
                try:
                    if time.time() - self.lock_path.stat().st_mtime > self.lock_ttl_s:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise LeaseError("CLAIM_STORE_LOCK_TIMEOUT")
                time.sleep(0.005)

    def _release_lock(self, fd: int) -> None:
        try:
            os.close(fd)
        finally:
            self.lock_path.unlink(missing_ok=True)

    def _mutate(self, fn):
        fd = self._acquire_lock()
        try:
            state = self._read_unlocked()
            result = fn(state)
            state["revision"] += 1
            self._write_unlocked(state)
            return result
        finally:
            self._release_lock(fd)

    @staticmethod
    def _event(state: dict[str, Any], kind: str, now: float, **fields: Any) -> None:
        state["events"].append({"type": kind, "at": now, **fields})

    @staticmethod
    def _as_receipt(claim: Mapping[str, Any]) -> ClaimLeaseReceipt:
        return ClaimLeaseReceipt(**claim)

    @staticmethod
    def _assert_fence(claim: Mapping[str, Any] | None, receipt: ClaimLeaseReceipt) -> None:
        if claim is None:
            raise StaleFence("CLAIM_MISSING")
        if (
            claim.get("work_id") != receipt.work_id
            or claim.get("worker_id") != receipt.worker_id
            or claim.get("visit_id") != receipt.visit_id
            or int(claim.get("fence", -1)) != receipt.fence
        ):
            raise StaleFence("CLAIM_FENCE_MISMATCH")

    def claim(
        self,
        work_id: str,
        *,
        worker_id: str,
        visit_id: str,
        capabilities: Iterable[str] = (),
        currentness: str,
        source_cut: str,
        effect_ceiling: str = "D0",
        lease_s: float = 120.0,
        now: float | None = None,
    ) -> ClaimLeaseReceipt:
        if currentness != "CURRENT":
            raise CurrentnessRequired("SUPERSEDED_CURRENTNESS")
        if not work_id or not worker_id or not visit_id or not source_cut:
            raise ValueError("work_id/worker_id/visit_id/source_cut required")
        if lease_s <= 0:
            raise ValueError("lease_s must be positive")
        now = time.time() if now is None else float(now)

        def op(state):
            existing = state["claims"].get(work_id)
            if existing is not None:
                if float(existing["lease_expires_at"]) > now:
                    raise ClaimBusy(f"WORK_ALREADY_CLAIMED:{work_id}")
                self._event(
                    state,
                    "STALE_CLAIM_RECOVERED",
                    now,
                    work_id=work_id,
                    stale_worker_id=existing["worker_id"],
                    stale_fence=existing["fence"],
                )
            fence = int(state["next_fence"])
            state["next_fence"] += 1
            claim = asdict(
                ClaimLeaseReceipt(
                    work_id=work_id,
                    worker_id=worker_id,
                    visit_id=visit_id,
                    fence=fence,
                    claimed_at=now,
                    heartbeat_at=now,
                    lease_expires_at=now + float(lease_s),
                    currentness=currentness,
                    source_cut=source_cut,
                    effect_ceiling=effect_ceiling,
                    capabilities_digest=_digest_capabilities(capabilities),
                )
            )
            state["claims"][work_id] = claim
            self._event(state, "CLAIM_ACQUIRED", now, work_id=work_id, worker_id=worker_id, fence=fence)
            return self._as_receipt(claim)

        return self._mutate(op)

    def heartbeat(
        self,
        receipt: ClaimLeaseReceipt,
        *,
        currentness: str = "CURRENT",
        source_cut: str | None = None,
        lease_s: float = 120.0,
        now: float | None = None,
    ) -> ClaimLeaseReceipt:
        if currentness != "CURRENT":
            raise CurrentnessRequired("SUPERSEDED_CURRENTNESS")
        if lease_s <= 0:
            raise ValueError("lease_s must be positive")
        now = time.time() if now is None else float(now)

        def op(state):
            claim = state["claims"].get(receipt.work_id)
            self._assert_fence(claim, receipt)
            if float(claim["lease_expires_at"]) <= now:
                raise StaleFence("LEASE_EXPIRED")
            if source_cut is not None and source_cut != claim["source_cut"]:
                raise StaleFence("SOURCE_CUT_CHANGED")
            claim["heartbeat_at"] = now
            claim["lease_expires_at"] = now + float(lease_s)
            self._event(state, "CLAIM_HEARTBEAT", now, work_id=receipt.work_id, fence=receipt.fence)
            return self._as_receipt(claim)

        return self._mutate(op)

    def release(self, receipt: ClaimLeaseReceipt, *, now: float | None = None) -> None:
        now = time.time() if now is None else float(now)

        def op(state):
            claim = state["claims"].get(receipt.work_id)
            self._assert_fence(claim, receipt)
            state["claims"].pop(receipt.work_id, None)
            self._event(state, "CLAIM_RELEASED", now, work_id=receipt.work_id, fence=receipt.fence)

        self._mutate(op)

    def recover_stale(self, *, now: float | None = None) -> tuple[str, ...]:
        now = time.time() if now is None else float(now)

        def op(state):
            stale = sorted(
                work_id
                for work_id, claim in state["claims"].items()
                if float(claim["lease_expires_at"]) <= now
            )
            for work_id in stale:
                claim = state["claims"].pop(work_id)
                self._event(
                    state,
                    "STALE_CLAIM_RECOVERED",
                    now,
                    work_id=work_id,
                    stale_worker_id=claim["worker_id"],
                    stale_fence=claim["fence"],
                )
            return tuple(stale)

        return self._mutate(op)

    def snapshot(self) -> dict[str, Any]:
        fd = self._acquire_lock()
        try:
            return self._read_unlocked()
        finally:
            self._release_lock(fd)


def dependency_wake_candidates(
    work: Mapping[str, Mapping[str, Any]],
    completed_ids: Iterable[str],
) -> tuple[str, ...]:
    """Return OPEN cells whose dependency sets are now fully closed."""
    complete = set(completed_ids)
    ready = []
    for work_id, cell in work.items():
        if cell.get("state") != "OPEN":
            continue
        deps = set(cell.get("dependencies", ()))
        if deps and deps.issubset(complete):
            ready.append(work_id)
    return tuple(sorted(ready))
