"""Cooperative control plane for Aura's interruptible Crystallization Crucible.

The controller owns local runtime state only. It cannot edit production source,
promote grammars, install plugins, commit, push, or merge. Interactive Aura activity
is authoritative; operating-system idleness is never guessed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import json
import os
from pathlib import Path
import secrets
import tempfile
import time
from typing import Any

CRUCIBLE_CONTROL_VERSION = "AURA_CRUCIBLE_CONTROL_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
AUTOMATIC_GRAMMAR_PROMOTION = False


class CrucibleState(str, Enum):
    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    MINING = "MINING"
    VALIDATING = "VALIDATING"
    PAUSE_REQUESTED = "PAUSE_REQUESTED"
    PAUSING = "PAUSING"
    PAUSED = "PAUSED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CrucibleBudget:
    max_jobs_per_cycle: int = 4
    max_wall_time_seconds: float = 30.0
    max_experiences_per_cycle: int = 500
    queue_maxsize: int = 100
    idle_after_seconds: float = 30.0
    poll_interval_seconds: float = 5.0

    def normalized(self) -> "CrucibleBudget":
        return CrucibleBudget(
            max_jobs_per_cycle=max(1, min(int(self.max_jobs_per_cycle), 100)),
            max_wall_time_seconds=max(1.0, min(float(self.max_wall_time_seconds), 3600.0)),
            max_experiences_per_cycle=max(1, min(int(self.max_experiences_per_cycle), 10000)),
            queue_maxsize=max(1, min(int(self.queue_maxsize), 10000)),
            idle_after_seconds=max(1.0, min(float(self.idle_after_seconds), 86400.0)),
            poll_interval_seconds=max(0.25, min(float(self.poll_interval_seconds), 3600.0)),
        )


@dataclass(frozen=True)
class CrucibleCheckpoint:
    checkpoint_id: str
    state: str
    phase: str
    last_experience_completed_at: float
    current_job_id: str
    processed_experience_ids: tuple[str, ...]
    pending_proposal_ids: tuple[str, ...]
    repository_commit: str
    grammar_digests: dict[str, str]
    created_at: float
    version: str = CRUCIBLE_CONTROL_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["processed_experience_ids"] = list(self.processed_experience_ids)
        payload["pending_proposal_ids"] = list(self.pending_proposal_ids)
        return payload


_ALLOWED_STATE_TRANSITIONS: dict[CrucibleState, frozenset[CrucibleState]] = {
    CrucibleState.IDLE: frozenset({CrucibleState.OBSERVING, CrucibleState.PAUSE_REQUESTED, CrucibleState.STOP_REQUESTED, CrucibleState.BLOCKED, CrucibleState.FAILED}),
    CrucibleState.OBSERVING: frozenset({CrucibleState.MINING, CrucibleState.IDLE, CrucibleState.PAUSE_REQUESTED, CrucibleState.STOP_REQUESTED, CrucibleState.BLOCKED, CrucibleState.FAILED}),
    CrucibleState.MINING: frozenset({CrucibleState.VALIDATING, CrucibleState.IDLE, CrucibleState.PAUSE_REQUESTED, CrucibleState.STOP_REQUESTED, CrucibleState.BLOCKED, CrucibleState.FAILED}),
    CrucibleState.VALIDATING: frozenset({CrucibleState.IDLE, CrucibleState.PAUSE_REQUESTED, CrucibleState.STOP_REQUESTED, CrucibleState.BLOCKED, CrucibleState.FAILED}),
    CrucibleState.PAUSE_REQUESTED: frozenset({CrucibleState.PAUSING, CrucibleState.PAUSED, CrucibleState.STOP_REQUESTED}),
    CrucibleState.PAUSING: frozenset({CrucibleState.PAUSED, CrucibleState.STOP_REQUESTED, CrucibleState.FAILED}),
    CrucibleState.PAUSED: frozenset({CrucibleState.IDLE, CrucibleState.STOP_REQUESTED}),
    CrucibleState.STOP_REQUESTED: frozenset({CrucibleState.STOPPING, CrucibleState.STOPPED}),
    CrucibleState.STOPPING: frozenset({CrucibleState.STOPPED, CrucibleState.FAILED}),
    CrucibleState.STOPPED: frozenset({CrucibleState.IDLE}),
    CrucibleState.BLOCKED: frozenset({CrucibleState.IDLE, CrucibleState.PAUSE_REQUESTED, CrucibleState.STOP_REQUESTED}),
    CrucibleState.FAILED: frozenset({CrucibleState.IDLE, CrucibleState.STOP_REQUESTED}),
}


class CrucibleController:
    def __init__(self, repo_root: str | Path = ".", *, state_root: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.state_root = Path(state_root).resolve() if state_root is not None else self.repo_root / "Aura_Memory" / "crucible"
        self.state_root.mkdir(parents=True, exist_ok=True)
        self.control_path = self.state_root / "control.json"
        self.heartbeat_path = self.state_root / "interactive_heartbeat.json"
        self.checkpoint_path = self.state_root / "checkpoint.json"
        self.lock_path = self.state_root / "service.lock"
        self.events_path = self.state_root / "events.jsonl"
        if not self.control_path.exists():
            self._write_control(CrucibleState.STOPPED, request="none", reason="initialized")

    def acquire_service_lock(self, *, stale_after_seconds: float = 300.0) -> dict[str, Any]:
        existing = self._read_json(self.lock_path)
        if self.lock_path.exists():
            if self._lock_is_stale(existing, stale_after_seconds=stale_after_seconds):
                try:
                    self.lock_path.unlink()
                except OSError as exc:
                    return self._denial(f"stale_lock_removal_failed:{type(exc).__name__}")
            else:
                return self._denial("service_already_running", details=existing)
        payload = {
            "version": CRUCIBLE_CONTROL_VERSION,
            "owner_pid": os.getpid(),
            "owner_token": secrets.token_hex(16),
            "created_at": time.time(),
            "heartbeat_at": time.time(),
            "repo_root": str(self.repo_root),
        }
        try:
            descriptor = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"))
        except FileExistsError:
            return self._denial("service_already_running", details=self._read_json(self.lock_path))
        except OSError as exc:
            return self._denial(f"service_lock_failed:{type(exc).__name__}")
        self._write_control(CrucibleState.IDLE, request="none", reason="service_lock_acquired")
        self.emit_event("crucible_started", {"owner_pid": os.getpid()})
        return self._allowed({"lock": payload})

    def refresh_service_lock(self, owner_token: str) -> bool:
        payload = self._read_json(self.lock_path)
        if not payload or payload.get("owner_token") != owner_token or int(payload.get("owner_pid") or -1) != os.getpid():
            return False
        payload["heartbeat_at"] = time.time()
        self._atomic_write_json(self.lock_path, payload)
        return True

    def release_service_lock(self, owner_token: str = "") -> dict[str, Any]:
        payload = self._read_json(self.lock_path)
        if not payload:
            self._write_control(CrucibleState.STOPPED, request="none", reason="lock_already_absent")
            return self._allowed({"released": False})
        if owner_token and payload.get("owner_token") != owner_token:
            return self._denial("service_lock_owner_mismatch")
        if int(payload.get("owner_pid") or -1) not in {-1, os.getpid()} and not self._lock_is_stale(payload, stale_after_seconds=0):
            return self._denial("cannot_release_live_foreign_lock")
        try:
            self.lock_path.unlink(missing_ok=True)
        except OSError as exc:
            return self._denial(f"service_lock_release_failed:{type(exc).__name__}")
        self._write_control(CrucibleState.STOPPED, request="none", reason="service_stopped")
        self.emit_event("crucible_stopped", {})
        return self._allowed({"released": True})

    def request_pause(self, *, reason: str = "interactive_priority") -> dict[str, Any]:
        current = self.current_state()
        if current in {CrucibleState.PAUSED, CrucibleState.PAUSE_REQUESTED, CrucibleState.PAUSING}:
            return self._allowed({"state": current.value, "idempotent": True})
        self._write_control(CrucibleState.PAUSE_REQUESTED, request="pause", reason=reason)
        self.emit_event("crucible_pause_requested", {"reason": reason})
        return self._allowed({"state": CrucibleState.PAUSE_REQUESTED.value})

    def acknowledge_paused(self, *, reason: str = "safe_checkpoint") -> dict[str, Any]:
        current = self.current_state()
        if current not in {CrucibleState.PAUSE_REQUESTED, CrucibleState.PAUSING, CrucibleState.PAUSED}:
            return self._denial("pause_not_requested", details={"state": current.value})
        self._write_control(CrucibleState.PAUSED, request="pause", reason=reason)
        self.emit_event("crucible_paused", {"reason": reason})
        return self._allowed({"state": CrucibleState.PAUSED.value})

    def request_resume(self, *, reason: str = "human_resume") -> dict[str, Any]:
        current = self.current_state()
        if current not in {CrucibleState.PAUSED, CrucibleState.PAUSE_REQUESTED, CrucibleState.PAUSING, CrucibleState.STOPPED}:
            return self._denial("resume_not_allowed", details={"state": current.value})
        self._write_control(CrucibleState.IDLE, request="none", reason=reason)
        self.emit_event("crucible_resumed", {"reason": reason})
        return self._allowed({"state": CrucibleState.IDLE.value})

    def request_stop(self, *, reason: str = "human_stop") -> dict[str, Any]:
        current = self.current_state()
        if current == CrucibleState.STOPPED:
            return self._allowed({"state": current.value, "idempotent": True})
        self._write_control(CrucibleState.STOP_REQUESTED, request="stop", reason=reason)
        self.emit_event("crucible_stop_requested", {"reason": reason})
        return self._allowed({"state": CrucibleState.STOP_REQUESTED.value})

    def transition(self, to_state: CrucibleState, *, phase: str = "", reason: str = "") -> dict[str, Any]:
        current = self.current_state()
        if to_state == current:
            return self._allowed({"from": current.value, "to": to_state.value, "idempotent": True})
        if to_state not in _ALLOWED_STATE_TRANSITIONS.get(current, frozenset()):
            return self._denial("illegal_crucible_state_transition", details={"from": current.value, "to": to_state.value})
        control = self._write_control(to_state, request=self.current_request(), reason=reason, phase=phase)
        return self._allowed({"from": current.value, "to": to_state.value, "control": control})

    def touch_interactive_heartbeat(self, *, source: str = "aura_terminal", session_id: str = "") -> dict[str, Any]:
        payload = {
            "version": CRUCIBLE_CONTROL_VERSION,
            "timestamp": time.time(),
            "source": str(source or "aura_terminal")[:160],
            "session_id": str(session_id or "")[:200],
            "pid": os.getpid(),
        }
        self._atomic_write_json(self.heartbeat_path, payload)
        return self._allowed({"heartbeat": payload})

    def interactive_is_active(self, *, idle_after_seconds: float = 30.0, now: float | None = None) -> bool:
        heartbeat = self._read_json(self.heartbeat_path)
        timestamp = float(heartbeat.get("timestamp") or 0.0) if heartbeat else 0.0
        current = time.time() if now is None else float(now)
        return timestamp > 0 and current - timestamp < max(1.0, float(idle_after_seconds))

    def should_yield(self, *, idle_after_seconds: float = 30.0) -> tuple[bool, str]:
        state = self.current_state()
        if state in {CrucibleState.PAUSE_REQUESTED, CrucibleState.PAUSING, CrucibleState.PAUSED}:
            return True, "pause_requested"
        if state in {CrucibleState.STOP_REQUESTED, CrucibleState.STOPPING, CrucibleState.STOPPED}:
            return True, "stop_requested"
        if self.interactive_is_active(idle_after_seconds=idle_after_seconds):
            return True, "interactive_activity"
        return False, ""

    def write_checkpoint(self, checkpoint: CrucibleCheckpoint) -> dict[str, Any]:
        self._atomic_write_json(self.checkpoint_path, checkpoint.to_dict())
        self.emit_event("crucible_checkpointed", {"checkpoint_id": checkpoint.checkpoint_id, "phase": checkpoint.phase})
        return self._allowed({"checkpoint": checkpoint.to_dict()})

    def read_checkpoint(self) -> dict[str, Any] | None:
        payload = self._read_json(self.checkpoint_path)
        return payload or None

    def status(self, *, idle_after_seconds: float = 30.0) -> dict[str, Any]:
        control = self._read_json(self.control_path)
        lock = self._read_json(self.lock_path)
        checkpoint = self.read_checkpoint()
        heartbeat = self._read_json(self.heartbeat_path)
        return {
            "ok": True,
            "version": CRUCIBLE_CONTROL_VERSION,
            "state": self.current_state().value,
            "request": self.current_request(),
            "control": control,
            "service_lock": lock,
            "service_running": bool(lock and not self._lock_is_stale(lock, stale_after_seconds=300.0)),
            "interactive_heartbeat": heartbeat,
            "interactive_active": self.interactive_is_active(idle_after_seconds=idle_after_seconds),
            "checkpoint": checkpoint,
            "state_root": str(self.state_root),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_grammar_promotion": AUTOMATIC_GRAMMAR_PROMOTION,
        }

    def current_state(self) -> CrucibleState:
        value = str(self._read_json(self.control_path).get("state") or CrucibleState.STOPPED.value)
        try:
            return CrucibleState(value)
        except ValueError:
            return CrucibleState.FAILED

    def current_request(self) -> str:
        return str(self._read_json(self.control_path).get("request") or "none")

    def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "version": CRUCIBLE_CONTROL_VERSION,
            "event": str(event_type),
            "timestamp": time.time(),
            "data": dict(data),
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        }
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str) + "\n")

    def _write_control(self, state: CrucibleState, *, request: str, reason: str, phase: str = "") -> dict[str, Any]:
        payload = {
            "version": CRUCIBLE_CONTROL_VERSION,
            "state": state.value,
            "request": str(request or "none"),
            "reason": str(reason or "")[:500],
            "phase": str(phase or "")[:200],
            "updated_at": time.time(),
            "owner_pid": os.getpid(),
        }
        self._atomic_write_json(self.control_path, payload)
        return payload

    def _lock_is_stale(self, payload: dict[str, Any], *, stale_after_seconds: float) -> bool:
        if not payload:
            return True
        pid = int(payload.get("owner_pid") or -1)
        heartbeat_at = float(payload.get("heartbeat_at") or payload.get("created_at") or 0.0)
        if pid > 0 and _pid_alive(pid):
            return False
        return time.time() - heartbeat_at >= max(0.0, stale_after_seconds)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            except OSError:
                pass

    @staticmethod
    def _allowed(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            **payload,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_grammar_promotion": False,
        }

    @staticmethod
    def _denial(reason: str, *, details: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": False,
            "reason": reason,
            "details": dict(details or {}),
            "fail_closed": True,
            "patch_authority": PATCH_AUTHORITY,
            "vsa_patch_authority": VSA_PATCH_AUTHORITY,
            "automatic_grammar_promotion": False,
        }


def build_checkpoint(
    *,
    state: CrucibleState,
    phase: str,
    last_experience_completed_at: float = 0.0,
    current_job_id: str = "",
    processed_experience_ids: tuple[str, ...] | list[str] = (),
    pending_proposal_ids: tuple[str, ...] | list[str] = (),
    repository_commit: str = "",
    grammar_digests: dict[str, str] | None = None,
) -> CrucibleCheckpoint:
    payload = f"{state.value}:{phase}:{last_experience_completed_at}:{current_job_id}:{time.time()}"
    return CrucibleCheckpoint(
        checkpoint_id=f"CP-{secrets.token_hex(10)}",
        state=state.value,
        phase=str(phase or ""),
        last_experience_completed_at=float(last_experience_completed_at),
        current_job_id=str(current_job_id or ""),
        processed_experience_ids=tuple(str(item) for item in processed_experience_ids),
        pending_proposal_ids=tuple(str(item) for item in pending_proposal_ids),
        repository_commit=str(repository_commit or ""),
        grammar_digests=dict(grammar_digests or {}),
        created_at=time.time(),
    )


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True
