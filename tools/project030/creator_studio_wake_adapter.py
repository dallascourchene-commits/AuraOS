from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence

from creator_studio_continuation_harness import (
    PRIORITY_STAGE_ORDER,
    HarnessState,
    WorkerContext,
    eligible_work,
)


class WakeRefusal(RuntimeError):
    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class WakeIntent:
    schema: str
    event_id: str
    event_type: str
    mission_id: str
    worker_id: str
    work_id: str | None
    work_version: str
    reason: str
    requires_worker_admission: bool = True
    execution_authorized: bool = False
    provider_calls_authorized: bool = False
    background_execution_claimed: bool = False

    def canonical_bytes(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")


class FileWakeLedger:
    """Append-only wake-intent ledger using fully-written temp + exclusive publish."""

    def __init__(self, root: os.PathLike[str] | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, event_id: str) -> Path:
        return self.root / f"{event_id}.json"

    def _read_landed(self, path: Path, attempts: int = 8) -> bytes:
        last_error = None
        for _ in range(attempts):
            try:
                return path.read_bytes()
            except OSError as exc:
                last_error = exc
                time.sleep(0.002)
        raise WakeRefusal("WAKE_EVENT_UNREADABLE", repr(last_error))

    def append(self, intent: WakeIntent) -> str:
        path = self.path_for(intent.event_id)
        payload = intent.canonical_bytes()
        fd, tmp_name = tempfile.mkstemp(dir=str(self.root), suffix=".tmp")
        published = False
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                if os.name == "nt":
                    os.rename(tmp_name, str(path))
                else:
                    os.link(tmp_name, str(path))
                    os.unlink(tmp_name)
                published = True
            except FileExistsError:
                published = False
            except OSError:
                if path.exists():
                    published = False
                else:
                    raise
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

        if published:
            landed = self._read_landed(path)
            if landed != payload:
                raise WakeRefusal("WAKE_POST_PUBLISH_MISMATCH", intent.event_id)
            return "APPENDED"

        existing = self._read_landed(path)
        if existing == payload:
            return "IDEMPOTENT_REPLAY"
        raise WakeRefusal("WAKE_EVENT_ID_COLLISION", intent.event_id)

    def events(self) -> List[WakeIntent]:
        out: List[WakeIntent] = []
        for path in sorted(self.root.glob("*.json")):
            out.append(WakeIntent(**json.loads(path.read_text(encoding="utf-8"))))
        return out


class ArenaWakeScheduler:
    """Project deterministic eligibility into durable wake intents, never execution claims."""

    def __init__(self, ledger: FileWakeLedger) -> None:
        self.ledger = ledger

    @staticmethod
    def _event_id(
        *, mission_id: str, event_type: str, worker_id: str, work_id: str | None, work_version: str
    ) -> str:
        raw = "|".join((mission_id, event_type, worker_id, work_id or "-", work_version))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    @staticmethod
    def _best_worker(candidates: Sequence[WorkerContext], required: frozenset[str]) -> WorkerContext:
        if not candidates:
            raise WakeRefusal("NO_WAKE_CANDIDATE")
        return sorted(
            candidates,
            key=lambda worker: (
                -len(required.intersection(worker.capabilities)),
                -len(worker.capabilities),
                worker.worker_id,
            ),
        )[0]

    def emit_recommission_required(
        self,
        state: HarnessState,
        *,
        work_id: str,
        work_version: str,
        reason: str = "eligible work requires a ChatGPT-class worker but no lawful wake/input adapter is active",
    ) -> WakeIntent:
        event_id = self._event_id(
            mission_id=state.active_mission_id,
            event_type="RECOMMISSION_REQUIRED",
            worker_id="__RECOMMISSION__",
            work_id=work_id,
            work_version=work_version,
        )
        intent = WakeIntent(
            schema="CreatorStudioWakeIntentV1",
            event_id=event_id,
            event_type="RECOMMISSION_REQUIRED",
            mission_id=state.active_mission_id,
            worker_id="__RECOMMISSION__",
            work_id=work_id,
            work_version=work_version,
            reason=reason,
        )
        self.ledger.append(intent)
        return intent

    def scan_and_emit(
        self,
        state: HarnessState,
        workers: Iterable[WorkerContext],
        *,
        work_versions: Mapping[str, str] | None = None,
    ) -> List[WakeIntent]:
        worker_list = sorted(list(workers), key=lambda worker: worker.worker_id)
        if not worker_list:
            return []
        versions = dict(work_versions or {})
        emitted: List[WakeIntent] = []

        if state.currentness != "CURRENT":
            for worker in worker_list:
                version = versions.get("__currentness__", state.currentness)
                event_id = self._event_id(
                    mission_id=state.active_mission_id,
                    event_type="CURRENTNESS_REBASE_REQUIRED",
                    worker_id=worker.worker_id,
                    work_id=None,
                    work_version=version,
                )
                intent = WakeIntent(
                    schema="CreatorStudioWakeIntentV1",
                    event_id=event_id,
                    event_type="CURRENTNESS_REBASE_REQUIRED",
                    mission_id=state.active_mission_id,
                    worker_id=worker.worker_id,
                    work_id=None,
                    work_version=version,
                    reason="shared Arena currentness is not CURRENT",
                )
                self.ledger.append(intent)
                emitted.append(intent)
            return emitted

        candidates_by_work: Dict[str, List[WorkerContext]] = {}
        items: Dict[str, object] = {}
        ordered_work_ids: List[str] = []
        seen_work_ids = set()
        for stage in PRIORITY_STAGE_ORDER:
            for worker in worker_list:
                for item in eligible_work(state, worker, stage=stage):
                    candidates_by_work.setdefault(item.work_id, []).append(worker)
                    items[item.work_id] = item
            for worker in worker_list:
                for item in eligible_work(state, worker, stage=stage):
                    if item.work_id not in seen_work_ids:
                        ordered_work_ids.append(item.work_id)
                        seen_work_ids.add(item.work_id)

        assigned_workers = set()
        for work_id in ordered_work_ids:
            available = [
                worker
                for worker in candidates_by_work.get(work_id, [])
                if worker.worker_id not in assigned_workers
            ]
            if not available:
                continue
            item = items[work_id]
            worker = self._best_worker(available, item.required_capabilities)
            assigned_workers.add(worker.worker_id)
            version = versions.get(work_id, "v1")
            event_id = self._event_id(
                mission_id=state.active_mission_id,
                event_type="WORK_ELIGIBLE",
                worker_id=worker.worker_id,
                work_id=work_id,
                work_version=version,
            )
            intent = WakeIntent(
                schema="CreatorStudioWakeIntentV1",
                event_id=event_id,
                event_type="WORK_ELIGIBLE",
                mission_id=state.active_mission_id,
                worker_id=worker.worker_id,
                work_id=work_id,
                work_version=version,
                reason="mission-aligned dependency-ready unclaimed work became eligible",
            )
            self.ledger.append(intent)
            emitted.append(intent)
        return emitted
