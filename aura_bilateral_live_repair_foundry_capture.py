"""Bounded explicit incident capture for the bilateral live-repair adapter."""
from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping
from dataclasses import asdict
import secrets
import time
from typing import Any

from aura_bilateral_live_repair_foundry_contracts import (
    INCIDENT_VERSION,
    MAX_CAPTURE_BYTES,
    MAX_EVENT_BYTES,
    MAX_EVENTS,
    MAX_ARCHIVED_PACKET_BYTES,
    MAX_RETENTION_SECONDS,
    _FALSE_AUTHORITY,
    BilateralIdentity,
    BilateralLiveRepairError,
    CaptureDissolutionReceipt,
    IncidentEvent,
    IncidentReplayPacket,
    RequiredAssetIdentity,
    _required_text,
    _timestamp,
    canonical_sanitize,
    canonical_bytes,
    digest,
)

class BoundedIncidentCapture:
    """Explicitly authorized, rolling, privacy-minimized field capture."""

    def __init__(
        self,
        *,
        identity: BilateralIdentity,
        release_id: str,
        environment_id: str,
        capture_authorized: bool,
        max_events: int = MAX_EVENTS,
        retention_seconds: int = 120,
        started_at: float | None = None,
    ) -> None:
        if capture_authorized is not True:
            raise BilateralLiveRepairError("explicit human capture authorization is required")
        if not 1 <= int(max_events) <= MAX_EVENTS:
            raise ValueError("max_events exceeds the bounded capture policy")
        if not 1 <= int(retention_seconds) <= MAX_RETENTION_SECONDS:
            raise ValueError("retention_seconds exceeds the bounded capture policy")
        self.identity = identity
        self.release_id = _required_text(release_id, "release_id", limit=512)
        self.environment_id = _required_text(environment_id, "environment_id", limit=512)
        self.capture_id = f"CAP-{secrets.token_hex(12)}"
        self.max_events = int(max_events)
        self.retention_seconds = int(retention_seconds)
        self.started_at = time.time() if started_at is None else _timestamp(started_at, "started_at")
        self._events: deque[IncidentEvent] = deque(maxlen=self.max_events)
        self._marker_event: IncidentEvent | None = None
        self._event_sizes: dict[int, int] = {}
        self._retained_bytes = 0
        self._total_event_count = 0
        self._closed = False

    def _assert_open(self) -> None:
        if self._closed:
            raise BilateralLiveRepairError("capture is closed and dissolved")
        if time.time() - self.started_at > self.retention_seconds:
            self._closed = True
            self._events.clear()
            self._marker_event = None
            self._event_sizes.clear()
            self._retained_bytes = 0
            raise BilateralLiveRepairError("capture retention window expired and dissolved")

    def observe(
        self,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        *,
        observed_at: float | None = None,
    ) -> IncidentEvent:
        self._assert_open()
        clean, redactions = canonical_sanitize(dict(payload or {}))
        timestamp = time.time() if observed_at is None else _timestamp(observed_at, "observed_at")
        event = IncidentEvent(
            sequence=self._total_event_count,
            event_type=_required_text(event_type, "event_type", limit=256),
            observed_at=timestamp,
            payload=clean,
            payload_digest=digest(clean),
            redactions=redactions,
        )
        event_bytes = len(canonical_bytes(asdict(event)))
        if event_bytes > MAX_EVENT_BYTES:
            raise BilateralLiveRepairError("incident event exceeds the bounded capture byte ceiling")
        evicted = self._events[0] if len(self._events) == self.max_events else None
        retained_bytes = self._retained_bytes + event_bytes
        if (
            evicted is not None
            and (
                self._marker_event is None
                or evicted.sequence != self._marker_event.sequence
            )
        ):
            retained_bytes -= self._event_sizes.get(evicted.sequence, 0)
        if retained_bytes > MAX_CAPTURE_BYTES:
            raise BilateralLiveRepairError("incident capture exceeds the aggregate byte ceiling")
        self._events.append(event)
        if evicted is not None and (
            self._marker_event is None
            or evicted.sequence != self._marker_event.sequence
        ):
            self._event_sizes.pop(evicted.sequence, None)
        self._event_sizes[event.sequence] = event_bytes
        self._retained_bytes = retained_bytes
        self._total_event_count += 1
        return event

    def mark_incident(
        self,
        marker: str,
        payload: Mapping[str, Any] | None = None,
        *,
        observed_at: float | None = None,
    ) -> IncidentEvent:
        self._assert_open()
        if self._marker_event is not None:
            raise BilateralLiveRepairError("incident is already marked")
        marker_text = _required_text(marker, "marker", limit=4096)
        event = self.observe(
            "INCIDENT_MARKER",
            {**dict(payload or {}), "marker": marker_text},
            observed_at=observed_at,
        )
        # The canonical marker is retained separately from the rolling deque so
        # later events can never evict replay identity.
        self._marker_event = event
        return event

    def finalize(
        self,
        *,
        expected_positive: Iterable[str],
        expected_negative: Iterable[str],
        preservation_claims: Iterable[str],
        required_assets: Iterable[Mapping[str, Any]] = (),
        current_identity: BilateralIdentity | None = None,
        created_at: float | None = None,
    ) -> IncidentReplayPacket:
        self._assert_open()
        if self._marker_event is None:
            raise ValueError("incident marker is required")
        if current_identity is not None:
            self.identity.assert_current(current_identity)

        obligation_redactions: set[str] = set()

        def _obligations(values: Iterable[str], name: str, limit: int) -> tuple[str, ...]:
            normalized: set[str] = set()
            for raw in values:
                text = _required_text(raw, name, limit=limit)
                clean, redactions = canonical_sanitize(text)
                normalized.add(_required_text(clean, name, limit=limit))
                obligation_redactions.update(redactions)
            return tuple(sorted(normalized))

        positive = _obligations(expected_positive, "positive requirement", 4096)
        negative = _obligations(expected_negative, "negative requirement", 4096)
        preservation = _obligations(preservation_claims, "preservation claim", 4096)
        asset_rows: dict[tuple[str, str], RequiredAssetIdentity] = {}
        for raw in required_assets:
            clean_asset, redactions = canonical_sanitize(raw)
            if not isinstance(clean_asset, Mapping):
                raise ValueError("required asset identity must be an object")
            asset = RequiredAssetIdentity.from_mapping(clean_asset)
            asset_rows[(asset.path, asset.sha256)] = asset
            obligation_redactions.update(redactions)
        assets = tuple(asset_rows[key] for key in sorted(asset_rows))
        if not positive or not negative or not preservation:
            raise ValueError("positive, negative, and preservation obligations are required")

        retained = tuple(self._events)
        window_start = retained[0].sequence if retained else self._total_event_count
        closed_at = time.time() if created_at is None else _timestamp(created_at, "created_at")
        dissolution = CaptureDissolutionReceipt(
            capture_id=self.capture_id,
            terminal_state="DISSOLVED",
            retained_event_count=len(retained),
            total_event_count=self._total_event_count,
            marker_retained_separately=True,
            closed_at=closed_at,
        )
        privacy = {
            "sanitizer_owner": "aura_arena_experience.sanitize_experience_payload",
            "redaction_refs": sorted(
                {
                    redaction
                    for event in (self._marker_event, *retained)
                    for redaction in event.redactions
                } | obligation_redactions
            ),
            "raw_secret_retained": False,
            "unrestricted_recording": False,
            "retention_seconds": self.retention_seconds,
            "max_events": self.max_events,
        }
        payload = {
            "version": INCIDENT_VERSION,
            "identity": asdict(self.identity),
            "release_id": self.release_id,
            "environment_id": self.environment_id,
            "capture_id": self.capture_id,
            "marker_event": asdict(self._marker_event),
            "events": [asdict(item) for item in retained],
            "window_start_sequence": window_start,
            "total_event_count": self._total_event_count,
            "expected_positive": list(positive),
            "expected_negative": list(negative),
            "preservation_claims": list(preservation),
            "required_assets": [asdict(item) for item in assets],
            "retention_class": "BOUNDED_SESSION_ONLY",
            "created_at": closed_at,
            "privacy_receipt": privacy,
            "dissolution_receipt": asdict(dissolution),
            "authority": {**_FALSE_AUTHORITY, "human_review_required": True},
        }
        packet_digest = digest(payload)
        packet = IncidentReplayPacket(
            packet_id=f"IRP-{packet_digest[:24]}",
            identity=self.identity,
            release_id=self.release_id,
            environment_id=self.environment_id,
            capture_id=self.capture_id,
            marker_event=self._marker_event,
            events=retained,
            window_start_sequence=window_start,
            total_event_count=self._total_event_count,
            expected_positive=positive,
            expected_negative=negative,
            preservation_claims=preservation,
            required_assets=assets,
            retention_class="BOUNDED_SESSION_ONLY",
            created_at=closed_at,
            packet_digest=packet_digest,
            privacy_receipt=privacy,
            dissolution_receipt=dissolution,
            authority={**_FALSE_AUTHORITY, "human_review_required": True},
        )
        if len(canonical_bytes(packet.to_dict())) > MAX_ARCHIVED_PACKET_BYTES:
            raise BilateralLiveRepairError("incident replay packet exceeds the durable archive byte ceiling")
        self._closed = True
        self._events.clear()
        self._marker_event = None
        self._event_sizes.clear()
        self._retained_bytes = 0
        return packet



__all__ = ["BoundedIncidentCapture"]
