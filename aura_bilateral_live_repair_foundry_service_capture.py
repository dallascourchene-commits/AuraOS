"""Capture, packet retention, and lifecycle mixin for B11-B15."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from aura_arena_attempt_archive import ArenaAttemptArchive
from aura_bilateral_live_repair_foundry_capture import BoundedIncidentCapture
from aura_bilateral_live_repair_foundry_contracts import (
    MAX_EVENTS,
    MAX_ACTIVE_CAPTURES,
    VERSION,
    _FALSE_AUTHORITY,
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
        self._captures: dict[str, BoundedIncidentCapture] = {}
        self._packets: dict[str, IncidentReplayPacket] = {}
        self._runtime_proofs: dict[str, tuple[str, dict[str, Any]]] = {}
        self._previews: dict[str, PreviewRollbackReceipt] = {}

    def close(self) -> None:
        for capture in self._captures.values():
            capture._closed = True
            capture._events.clear()
            capture._marker_event = None
        self._captures.clear()
        self._packets.clear()
        self._runtime_proofs.clear()
        self._previews.clear()
        if self._owns_archive:
            self.attempt_archive.close()

    def status(self) -> dict[str, Any]:
        return {
            "ok": True,
            "version": VERSION,
            "active_capture_count": sum(not item._closed for item in self._captures.values()),
            "retained_packet_count": len(self._packets),
            "retained_runtime_proof_count": len(self._runtime_proofs),
            "preview_receipt_count": len(self._previews),
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
        self._sweep_expired_captures()
        if len(self._captures) >= MAX_ACTIVE_CAPTURES:
            raise BilateralLiveRepairError("active capture budget exhausted")
        identity = BilateralIdentity.from_mapping(contract.get("identity") or {})
        capture = BoundedIncidentCapture(
            identity=identity,
            release_id=contract.get("release_id"),
            environment_id=contract.get("environment_id"),
            capture_authorized=contract.get("capture_authorized") is True,
            max_events=int(contract.get("max_events", MAX_EVENTS)),
            retention_seconds=int(contract.get("retention_seconds", 120)),
        )
        self._captures[capture.capture_id] = capture
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
        capture = self._capture(capture_id)
        event = capture.observe(event_type, payload)
        return {"ok": True, "capture_id": capture.capture_id, "event": asdict(event)}

    def mark(self, capture_id: str, marker: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
        capture = self._capture(capture_id)
        event = capture.mark_incident(marker, payload)
        return {"ok": True, "capture_id": capture.capture_id, "marker_event": asdict(event)}

    def finalize_capture(self, capture_id: str, contract: Mapping[str, Any]) -> dict[str, Any]:
        capture = self._capture(capture_id)
        current_identity = BilateralIdentity.from_mapping(contract.get("current_identity") or {})
        packet = capture.finalize(
            expected_positive=contract.get("expected_positive") or (),
            expected_negative=contract.get("expected_negative") or (),
            preservation_claims=contract.get("preservation_claims") or (),
            required_assets=contract.get("required_assets") or (),
            current_identity=current_identity,
        )
        self._packets[packet.packet_id] = packet
        # The packet is already privacy-sanitized and digest-bound. Preserve its
        # exact canonical bytes as a string so Attempt Archive's key-based secret
        # scrubber does not rewrite safe boolean fields such as
        # ``raw_secret_retained`` and invalidate durable replay identity.
        packet_json = canonical_bytes(packet.to_dict()).decode("ascii")
        archive = self.attempt_archive.record(
            arena_id=str(contract.get("arena_id") or "construction"),
            route="bilateral-live-repair/incident-capture",
            request={
                "action_id": "compile_incident_replay_packet",
                "capture_id": capture_id,
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
                "objective": str(contract.get("objective") or "Compile an exact field incident replay"),
            },
            archive_context={
                "stage_hint": "B11",
                "incident_packet_digest": packet.packet_digest,
                "identity_digest": packet.identity.identity_digest,
            },
        )
        if archive.get("ok") is not True:
            self._packets.pop(packet.packet_id, None)
            raise BilateralLiveRepairError("canonical Attempt Archive did not retain the incident replay")
        return {"ok": True, "packet": packet.to_dict(), "attempt_artifact": archive}

    def _capture(self, capture_id: str) -> BoundedIncidentCapture:
        item = self._captures.get(_required_text(capture_id, "capture_id", limit=128))
        if item is None:
            raise BilateralLiveRepairError("capture not found")
        return item

    def _packet(self, packet_id: str) -> IncidentReplayPacket:
        resolved = _required_text(packet_id, "packet_id", limit=128)
        item = self._packets.get(resolved)
        if item is not None:
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
                # Read-only compatibility for artifacts created before exact-byte
                # packet retention. Identity validation still fails closed if an
                # older archive scrubbed a digest-bearing nested field.
                raw_packet = result["incident_replay_packet"]
            if isinstance(raw_packet, Mapping):
                item = IncidentReplayPacket.from_mapping(raw_packet)
                if item.packet_id != resolved:
                    raise BilateralLiveRepairError("archived incident packet identity differs from its workflow key")
                self._packets[resolved] = item
                return item
        raise BilateralLiveRepairError("incident replay packet was not retained by the canonical Attempt Archive")


__all__ = ["_CapturePersistenceMixin"]
