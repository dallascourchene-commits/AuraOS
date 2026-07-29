"""Capture, packet retention, and lifecycle mixin for B11-B15."""
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import asdict
import json
from pathlib import Path
import threading
import time
from typing import Any

from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_bilateral_live_repair_foundry_capture import BoundedIncidentCapture
from aura_bilateral_live_repair_foundry_contracts import (
    _FALSE_AUTHORITY,
    MAX_ACTIVE_CAPTURES,
    MAX_EVENTS,
    MAX_PENDING_PACKET_ARCHIVES,
    VERSION,
    BilateralIdentity,
    BilateralLiveRepairError,
    IncidentReplayPacket,
    PreviewRollbackReceipt,
    _required_text,
    canonical_bytes,
)


class _CapturePersistenceMixin:
    def __init__(
        self,
        repo_root: str | Path = ".",
        *,
        attempt_archive: ArenaAttemptArchive | None = None,
        attempt_archive_db_path: str | Path | None = None,
        runtime_runner: Callable[..., Mapping[str, Any]] | None = None,
        current_identity_resolver: Callable[[BilateralIdentity], BilateralIdentity] | None = None,
        allow_reduced_runtime_fixture: bool = False,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self._owns_archive = attempt_archive is None
        self.attempt_archive = attempt_archive or ArenaAttemptArchive(
            self.repo_root,
            db_path=attempt_archive_db_path,
        )
        if runtime_runner is None:
            from scripts.aura_runtime_profile_v2_adapter import run_runtime_profile_v2

            runtime_runner = run_runtime_profile_v2
        self.runtime_runner = runtime_runner
        self._current_identity_resolver = current_identity_resolver
        self._allow_reduced_runtime_fixture = allow_reduced_runtime_fixture is True
        self._capture_lock = threading.RLock()
        self._capture_timers: dict[str, threading.Timer] = {}
        self._captures: dict[str, BoundedIncidentCapture] = {}
        self._packets: OrderedDict[str, IncidentReplayPacket] = OrderedDict()
        self._pending_packet_archives: dict[str, tuple[IncidentReplayPacket, dict[str, str]]] = {}
        self._runtime_proofs: OrderedDict[str, tuple[str, dict[str, Any]]] = OrderedDict()
        self._previews: OrderedDict[str, PreviewRollbackReceipt] = OrderedDict()

    def close(self) -> None:
        with self._capture_lock:
            for timer in self._capture_timers.values():
                timer.cancel()
            self._capture_timers.clear()
            for capture in self._captures.values():
                self._scrub_capture(capture)
            self._captures.clear()
            self._packets.clear()
            self._pending_packet_archives.clear()
            self._runtime_proofs.clear()
            self._previews.clear()
        if self._owns_archive:
            self.attempt_archive.close()

    def status(self) -> dict[str, Any]:
        with self._capture_lock:
            active_capture_count = sum(not item._closed for item in self._captures.values())
            retained_packet_count = len(self._packets)
            pending_packet_archive_count = len(self._pending_packet_archives)
            retained_runtime_proof_count = len(self._runtime_proofs)
            preview_receipt_count = len(self._previews)
        return {
            "ok": True,
            "version": VERSION,
            "active_capture_count": active_capture_count,
            "retained_packet_count": retained_packet_count,
            "pending_packet_archive_count": pending_packet_archive_count,
            "retained_runtime_proof_count": retained_runtime_proof_count,
            "preview_receipt_count": preview_receipt_count,
            "attempt_archive": self.attempt_archive.status(),
            "canonical_owners": {
                "sanitization": "aura_arena_experience.sanitize_experience_payload",
                "attempt_archive": "aura_arena_attempt_archive.ArenaAttemptArchive",
                "runtime": "scripts.aura_runtime_profile_v2_adapter.run_runtime_profile_v2",
                "u7": "aura_unified_memory_continuity_learning",
                "projection": "aura_showcase_live_repair_server",
            },
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }

    def start_capture(self, contract: Mapping[str, Any]) -> dict[str, Any]:
        with self._capture_lock:
            self._sweep_expired_captures()
            if len(self._captures) >= MAX_ACTIVE_CAPTURES:
                raise BilateralLiveRepairError("active capture budget exhausted")
            identity = BilateralIdentity.from_mapping(contract.get("identity") or {})
            release_id = _required_text(contract.get("release_id"), "release_id", limit=512)
            environment_id = _required_text(
                contract.get("environment_id"),
                "environment_id",
                limit=512,
            )
            capture = BoundedIncidentCapture(
                identity=identity,
                release_id=release_id,
                environment_id=environment_id,
                capture_authorized=contract.get("capture_authorized") is True,
                max_events=int(contract.get("max_events", MAX_EVENTS)),
                retention_seconds=int(contract.get("retention_seconds", 120)),
            )
            self._captures[capture.capture_id] = capture
            timer = threading.Timer(
                capture.retention_seconds,
                self._expire_capture,
                args=(capture.capture_id,),
            )
            timer.daemon = True
            self._capture_timers[capture.capture_id] = timer
            timer.start()
        return {
            "ok": True,
            "capture_id": capture.capture_id,
            "started_at": capture.started_at,
            "max_events": capture.max_events,
            "retention_seconds": capture.retention_seconds,
            "recording_scope": "EXPLICIT_BOUNDED_SESSION",
            "unrestricted_recording": False,
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }

    def observe(self, capture_id: str, event_type: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._capture_lock:
            capture = self._capture(capture_id)
            event = capture.observe(event_type, payload)
        return {"ok": True, "capture_id": capture.capture_id, "event": asdict(event)}

    def mark(self, capture_id: str, marker: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        with self._capture_lock:
            capture = self._capture(capture_id)
            event = capture.mark_incident(marker, payload)
        return {"ok": True, "capture_id": capture.capture_id, "marker_event": asdict(event)}

    def finalize_capture(self, capture_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
        with self._capture_lock:
            capture = self._capture(capture_id)
            if len(self._pending_packet_archives) >= MAX_PENDING_PACKET_ARCHIVES:
                raise BilateralLiveRepairError("pending incident archive retry budget exhausted")
            current_identity = self._resolve_current_identity(capture.identity)
            packet = capture.finalize(
                expected_positive=contract.get("expected_positive") or (),
                expected_negative=contract.get("expected_negative") or (),
                preservation_claims=contract.get("preservation_claims") or (),
                required_assets=contract.get("required_assets") or (),
                current_identity=current_identity,
            )
            timer = self._capture_timers.pop(capture.capture_id, None)
            if timer is not None:
                timer.cancel()
            self._packets[packet.packet_id] = packet
            archive_contract = {
                "arena_id": str(contract.get("arena_id") or "construction"),
                "objective": str(
                    contract.get("objective")
                    or "Compile an exact field incident replay"
                ),
            }
            self._pending_packet_archives[packet.packet_id] = (packet, archive_contract)
        return self._archive_pending_packet(packet.packet_id)

    def retry_packet_archive(self, packet_id: str) -> dict[str, Any]:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        with self._capture_lock:
            if resolved not in self._pending_packet_archives:
                raise BilateralLiveRepairError("pending incident replay archive not found")
        return self._archive_pending_packet(resolved)

    def _archive_pending_packet(self, packet_id: str) -> dict[str, Any]:
        with self._capture_lock:
            entry = self._pending_packet_archives.get(packet_id)
        if entry is None:
            raise BilateralLiveRepairError(f"pending packet archive not found: {packet_id}")
        packet, contract = entry
        packet_json = canonical_bytes(packet.to_dict()).decode("ascii")
        try:
            archive = self.attempt_archive.record(
                arena_id=contract["arena_id"],
                route="bilateral-live-repair/incident-capture",
                request={
                    "action_id": "compile_incident_replay_packet",
                    "capture_id": packet.capture_id,
                    "identity_digest": packet.identity.identity_digest,
                    "confirmation_digest": packet.identity.confirmation_digest,
                },
                result={
                    "ok": True,
                    "status": "INCIDENT_REPLAY_COMPILED",
                    "packet_id": packet.packet_id,
                    "packet_digest": packet.packet_digest,
                    "privacy_receipt": packet.privacy_receipt,
                    "dissolution_receipt": asdict(packet.dissolution_receipt),
                    "incident_replay_packet_json": packet_json,
                },
                workflow_state={
                    "workflow_id": packet.packet_id,
                    "current_phase": "B11_INCIDENT_CAPTURE",
                    "objective": contract["objective"],
                },
                archive_context={
                    "stage_hint": "B11",
                    "incident_packet_digest": packet.packet_digest,
                    "identity_digest": packet.identity.identity_digest,
                },
            )
        except Exception as exc:
            raise BilateralLiveRepairError(
                f"incident replay {packet.packet_id} retained in memory for archive retry"
            ) from exc
        if archive.get("ok") is not True:
            raise BilateralLiveRepairError(
                f"incident replay {packet.packet_id} retained in memory for archive retry"
            )
        with self._capture_lock:
            retained = self._pending_packet_archives.get(packet.packet_id)
            if retained is None or retained[0].packet_digest != packet.packet_digest:
                raise BilateralLiveRepairError(
                    "pending incident replay identity changed before durable completion"
                )
            self._pending_packet_archives.pop(packet.packet_id, None)
            self._packets[packet.packet_id] = packet
            self._packets.move_to_end(packet.packet_id)
            while len(self._packets) > 32:
                self._packets.popitem(last=False)
        return {"ok": True, "packet": packet.to_dict(), "attempt_artifact": archive}

    def _capture(self, capture_id: str) -> BoundedIncidentCapture:
        with self._capture_lock:
            item = self._captures.get(_required_text(capture_id, "capture_id", limit=128))
        if item is None:
            raise BilateralLiveRepairError("capture not found")
        return item

    def _expire_capture(self, capture_id: str) -> None:
        with self._capture_lock:
            capture = self._captures.pop(capture_id, None)
            self._capture_timers.pop(capture_id, None)
            if capture is not None:
                self._scrub_capture(capture)

    @staticmethod
    def _scrub_capture(capture: Any) -> None:
        capture._closed = True
        capture._events.clear()
        capture._marker_event = None
        capture._event_sizes.clear()
        capture._retained_bytes = 0

    def _sweep_expired_captures(self) -> None:
        with self._capture_lock:
            now = time.time()
            for capture_id, capture in list(self._captures.items()):
                if not capture._closed and now - capture.started_at > capture.retention_seconds:
                    self._scrub_capture(capture)
                if capture._closed:
                    self._captures.pop(capture_id, None)
                    timer = self._capture_timers.pop(capture_id, None)
                    if timer is not None:
                        timer.cancel()

    def _resolve_current_identity(self, expected: BilateralIdentity) -> BilateralIdentity:
        if self._current_identity_resolver is None:
            raise BilateralLiveRepairError(
                "operation requires a trusted current-identity resolver"
            )
        current = self._current_identity_resolver(expected)
        if not isinstance(current, BilateralIdentity):
            raise BilateralLiveRepairError(
                "trusted current-identity resolver returned an invalid identity"
            )
        expected.assert_current(current)
        return current

    def _packet(self, packet_id: str) -> IncidentReplayPacket:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        with self._capture_lock:
            if resolved in self._pending_packet_archives:
                raise BilateralLiveRepairError(
                    "incident replay packet is pending durable archival"
                )
            item = self._packets.get(resolved)
            if item is not None:
                self._packets.move_to_end(resolved)
                return item
        for summary in self.attempt_archive.list(
            workflow_id=resolved,
            route="bilateral-live-repair/incident-capture",
            limit=10,
        ):
            artifact = self.attempt_archive.get(str(summary.get("artifact_id") or ""))
            result = dict((artifact or {}).get("result") or {})
            packet_json = result.get("incident_replay_packet_json")
            raw_packet: Any = None
            if isinstance(packet_json, str) and packet_json:
                try:
                    raw_packet = json.loads(packet_json)
                except json.JSONDecodeError as exc:
                    raise BilateralLiveRepairError("archived incident packet JSON is invalid") from exc
            elif isinstance(result.get("incident_replay_packet"), Mapping):
                raw_packet = result["incident_replay_packet"]
            if isinstance(raw_packet, Mapping):
                item = IncidentReplayPacket.from_mapping(raw_packet)
                if item.packet_id != resolved:
                    raise BilateralLiveRepairError("archived incident packet identity differs from its workflow key")
                with self._capture_lock:
                    self._packets[resolved] = item
                    self._packets.move_to_end(resolved)
                    while len(self._packets) > 32:
                        self._packets.popitem(last=False)
                return item
        raise BilateralLiveRepairError("incident replay packet was not retained by the canonical Attempt Archive")


__all__ = ["_CapturePersistenceMixin"]
