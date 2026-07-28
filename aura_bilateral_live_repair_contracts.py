"""B11 bilateral incident identity, canonicalization, and bounded replay contracts.

This companion module centralizes deterministic, privacy-safe value handling,
exact bilateral runtime identity, rolling incident capture, and replay packet
identity. It is not a memory, truth, verification, policy, routing, persistence,
publication, or authority owner.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import time
from typing import Any

from aura_arena_experience import sanitize_experience_payload

VERSION = "AURA_BILATERAL_LIVE_REPAIR_FOUNDRY_V2"
INCIDENT_VERSION = "AURA_BILATERAL_INCIDENT_REPLAY_V2"
REPAIR_VERSION = "AURA_BILATERAL_REPAIR_ATTEMPT_V2"
PREVIEW_VERSION = "AURA_BILATERAL_LOCAL_PREVIEW_V2"
PROJECTION_VERSION = "AURA_SPATIAL_FOUNDRY_PROJECTION_V2"
MAX_CAPTURE_EVENTS = 256
MAX_REPAIR_ATTEMPTS = 8
MAX_VALUE_DEPTH = 12
MAX_COLLECTION_ITEMS = 512
MAX_TEXT_BYTES = 64 * 1024
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_HEX64 = re.compile(r"[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40,64}")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_LOCAL_FAILURES = frozenset(
    {
        "LOCAL_ASSERTION",
        "LOCAL_TEST",
        "EXACT_SPAN_PATCH",
        "SOURCE_ASSERTION",
        "POSITIVE_ASSERTION",
        "FAULT_ASSERTION",
        "ADJACENT_REGRESSION",
    }
)
_STRUCTURAL_FAILURES = frozenset(
    {
        "INTERFACE",
        "DEPENDENCY",
        "INVARIANT",
        "SCOPE",
        "AUTHORITY",
        "PROHIBITION",
        "SEQUENCE",
        "STALE_IDENTITY",
        "NEGATIVE_ASSERTION",
        "PRESERVATION_ASSERTION",
        "SOURCE_MUTATION",
        "VERIFIER_IDENTITY",
        "CLEANUP",
    }
)

AUTHORITY = {
    "visual_truth": False,
    "patch": False,
    "commit": False,
    "push": False,
    "pull_request": False,
    "merge": False,
    "deployment": False,
    "production_mutation": False,
    "professional": False,
    "physical_work": False,
    "learning_promotion": False,
    "automatic_crystallization": False,
    "human_review_required": True,
}


class BilateralLiveRepairError(RuntimeError):
    """Base deterministic boundary failure."""


class StaleBilateralEvidenceError(BilateralLiveRepairError):
    """A receipt, source identity, or revision no longer matches current truth."""


class RepairBudgetExhausted(BilateralLiveRepairError):
    """The bounded candidate budget is exhausted."""


class RepeatedFailedHypothesis(BilateralLiveRepairError):
    """A failed hypothesis was already attempted for this exact replay."""


def _required_text(value: Any, name: str, *, maximum: int = 4096) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > maximum:
        raise ValueError(f"{name} exceeds {maximum} UTF-8 bytes")
    return text


def _digest64(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=128).lower()
    if not _HEX64.fullmatch(text):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return text


def _git_identity(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=128).lower()
    if not _GIT_SHA.fullmatch(text):
        raise ValueError(f"{name} must be a Git object identity")
    return text


def _identifier(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=256)
    if not _IDENTIFIER.fullmatch(text):
        raise ValueError(f"{name} contains unsupported characters")
    return text


def _repo_path(value: Any, name: str) -> str:
    text = _required_text(value, name, maximum=1024)
    if "\\" in text or "\x00" in text:
        raise ValueError(f"{name} is not a canonical repository path")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{name} escapes the repository boundary")
    return path.as_posix()


def _timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite timestamp")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite timestamp")
    return result


def _canonicalize(value: Any, *, depth: int = 0) -> Any:
    """Normalize unordered input before Aura's canonical privacy sanitizer.

    The previous abandoned branch converted sets with ``list(set)``.  This
    implementation sorts canonical set members by their canonical JSON bytes,
    so hashes are stable across processes and hash seeds.
    """
    if depth > MAX_VALUE_DEPTH:
        return "[MAX_DEPTH]"
    if isinstance(value, Mapping):
        rows: list[tuple[str, Any]] = []
        for index, (raw_key, raw_value) in enumerate(value.items()):
            if index >= MAX_COLLECTION_ITEMS:
                rows.append(("__truncated_items__", len(value) - index))
                break
            key = str(raw_key)[:512]
            rows.append((key, _canonicalize(raw_value, depth=depth + 1)))
        rows.sort(key=lambda item: item[0])
        return {key: item for key, item in rows}
    if isinstance(value, (set, frozenset)):
        normalized = [_canonicalize(item, depth=depth + 1) for item in value]
        normalized.sort(key=canonical_json_bytes)
        return normalized[:MAX_COLLECTION_ITEMS]
    if isinstance(value, (list, tuple)):
        return [
            _canonicalize(item, depth=depth + 1)
            for item in list(value)[:MAX_COLLECTION_ITEMS]
        ]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        if len(encoded) <= MAX_TEXT_BYTES:
            return value
        return encoded[:MAX_TEXT_BYTES].decode("utf-8", errors="ignore")
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are not canonical evidence")
        return value
    return str(value)[:MAX_TEXT_BYTES]


def sanitize_canonical(value: Any) -> tuple[Any, tuple[str, ...]]:
    """Use Aura's canonical experience sanitizer after deterministic ordering."""
    sanitized, redactions = sanitize_experience_payload(_canonicalize(value))
    return sanitized, tuple(sorted({str(item) for item in redactions}))


def canonical_json_bytes(value: Any) -> bytes:
    normalized = _canonicalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def stable_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _string_tuple(value: Iterable[Any], name: str, *, required: bool = False) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{name} must be a sequence of strings")
    result = tuple(dict.fromkeys(_identifier(item, name) for item in value))
    if required and not result:
        raise ValueError(f"{name} must not be empty")
    if len(result) > MAX_COLLECTION_ITEMS:
        raise ValueError(f"{name} exceeds {MAX_COLLECTION_ITEMS} items")
    return result


@dataclass(frozen=True)
class BilateralRuntimeIdentity:
    """Exact identity binding for B11-B15 evidence."""

    intent_digest: str
    confirmation_digest: str
    semantic_ledger_digest: str
    guardrail_set_digest: str
    intent_revision_id: str
    repository_head: str
    source_tree_digest: str
    release_id: str
    environment_id: str
    runtime_profile_path: str
    runtime_profile_digest: str
    verifier_id: str
    verifier_source_digest: str
    allowed_path_set_digest: str

    def __post_init__(self) -> None:
        for name in (
            "intent_digest",
            "confirmation_digest",
            "semantic_ledger_digest",
            "guardrail_set_digest",
            "runtime_profile_digest",
            "verifier_source_digest",
            "allowed_path_set_digest",
        ):
            object.__setattr__(self, name, _digest64(getattr(self, name), name))
        object.__setattr__(self, "repository_head", _git_identity(self.repository_head, "repository_head"))
        object.__setattr__(self, "source_tree_digest", _git_identity(self.source_tree_digest, "source_tree_digest"))
        for name in ("intent_revision_id", "release_id", "environment_id", "verifier_id"):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        object.__setattr__(
            self,
            "runtime_profile_path",
            _repo_path(self.runtime_profile_path, "runtime_profile_path"),
        )

    def identity_payload(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def identity_digest(self) -> str:
        return stable_sha256(self.identity_payload())

    def assert_current(self, current: "BilateralRuntimeIdentity") -> None:
        if not isinstance(current, BilateralRuntimeIdentity):
            raise TypeError("current identity must be BilateralRuntimeIdentity")
        if self.identity_digest != current.identity_digest:
            changed = [
                name
                for name in self.__dataclass_fields__
                if getattr(self, name) != getattr(current, name)
            ]
            raise StaleBilateralEvidenceError(
                "bilateral evidence is stale or mismatched: " + ", ".join(changed)
            )


@dataclass(frozen=True)
class IncidentEvent:
    sequence: int
    event_type: str
    observed_at: float
    payload: Any
    payload_digest: str
    redactions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["redactions"] = list(self.redactions)
        return data


@dataclass(frozen=True)
class IncidentMarker:
    sequence: int
    marker: str
    observed_at: float
    payload: Any
    payload_digest: str
    redactions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["redactions"] = list(self.redactions)
        return data


@dataclass(frozen=True)
class IncidentReplayPacket:
    packet_id: str
    identity: BilateralRuntimeIdentity
    marker: IncidentMarker
    retained_events: tuple[IncidentEvent, ...]
    positive_assertion_ids: tuple[str, ...]
    negative_assertion_ids: tuple[str, ...]
    preservation_assertion_ids: tuple[str, ...]
    fault_assertion_ids: tuple[str, ...]
    adjacent_scenario_ids: tuple[str, ...]
    started_at: float
    finalized_at: float
    retention_expires_at: float
    packet_digest: str
    version: str = INCIDENT_VERSION

    def identity_payload(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "identity": self.identity.identity_payload(),
            "marker": self.marker.to_dict(),
            "retained_events": [item.to_dict() for item in self.retained_events],
            "positive_assertion_ids": list(self.positive_assertion_ids),
            "negative_assertion_ids": list(self.negative_assertion_ids),
            "preservation_assertion_ids": list(self.preservation_assertion_ids),
            "fault_assertion_ids": list(self.fault_assertion_ids),
            "adjacent_scenario_ids": list(self.adjacent_scenario_ids),
            "started_at": self.started_at,
            "finalized_at": self.finalized_at,
            "retention_expires_at": self.retention_expires_at,
            "authority": AUTHORITY,
        }

    def __post_init__(self) -> None:
        expected = stable_sha256(self.identity_payload())
        if self.packet_digest != expected or self.packet_id != f"IRP-{expected[:24]}":
            raise ValueError("incident replay packet identity mismatch")

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.identity_payload(),
            "packet_id": self.packet_id,
            "packet_digest": self.packet_digest,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    def assert_current(self, current: BilateralRuntimeIdentity, *, now: float | None = None) -> None:
        self.identity.assert_current(current)
        timestamp = time.time() if now is None else _timestamp(now, "now")
        if timestamp > self.retention_expires_at:
            raise StaleBilateralEvidenceError("incident replay packet retention expired")


class BoundedIncidentCapture:
    """Explicit, bounded, privacy-safe incident capture with terminal cleanup."""

    def __init__(
        self,
        *,
        identity: BilateralRuntimeIdentity,
        max_events: int = MAX_CAPTURE_EVENTS,
        retention_seconds: float = 24 * 60 * 60,
        started_at: float | None = None,
    ) -> None:
        if not isinstance(identity, BilateralRuntimeIdentity):
            raise TypeError("identity must be BilateralRuntimeIdentity")
        if isinstance(max_events, bool) or not 1 <= int(max_events) <= MAX_CAPTURE_EVENTS:
            raise ValueError(f"max_events must be in [1, {MAX_CAPTURE_EVENTS}]")
        if retention_seconds <= 0 or retention_seconds > 7 * 24 * 60 * 60:
            raise ValueError("retention_seconds must be positive and no more than seven days")
        self.identity = identity
        self.max_events = int(max_events)
        self.retention_seconds = float(retention_seconds)
        self.started_at = time.time() if started_at is None else _timestamp(started_at, "started_at")
        self._events: list[IncidentEvent] = []
        self._marker: IncidentMarker | None = None
        self._next_sequence = 0
        self._state = "CAPTURING"
        self._finalized_packet_digest = ""

    @property
    def state(self) -> str:
        return self._state

    def _require_capturing(self) -> None:
        if self._state != "CAPTURING":
            raise BilateralLiveRepairError(f"capture is terminal: {self._state}")

    def _new_event(
        self,
        event_type: str,
        payload: Mapping[str, Any] | None,
        observed_at: float | None,
    ) -> IncidentEvent:
        clean, redactions = sanitize_canonical(dict(payload or {}))
        event = IncidentEvent(
            sequence=self._next_sequence,
            event_type=_identifier(event_type, "event_type"),
            observed_at=time.time() if observed_at is None else _timestamp(observed_at, "observed_at"),
            payload=clean,
            payload_digest=stable_sha256(clean),
            redactions=redactions,
        )
        self._next_sequence += 1
        self._events.append(event)
        if len(self._events) > self.max_events:
            del self._events[: len(self._events) - self.max_events]
        return event

    def observe(
        self,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        *,
        observed_at: float | None = None,
    ) -> IncidentEvent:
        self._require_capturing()
        return self._new_event(event_type, payload, observed_at)

    def mark_incident(
        self,
        marker: str,
        payload: Mapping[str, Any] | None = None,
        *,
        observed_at: float | None = None,
    ) -> IncidentMarker:
        self._require_capturing()
        if self._marker is not None:
            raise BilateralLiveRepairError("incident marker is already retained")
        timestamp = time.time() if observed_at is None else _timestamp(observed_at, "observed_at")
        event = self._new_event(
            "INCIDENT_MARKER",
            {**dict(payload or {}), "marker": _required_text(marker, "marker", maximum=2048)},
            timestamp,
        )
        marker_value = str(event.payload.get("marker") or "") if isinstance(event.payload, Mapping) else ""
        if not marker_value:
            raise BilateralLiveRepairError("canonical sanitizer removed the incident marker")
        self._marker = IncidentMarker(
            sequence=event.sequence,
            marker=marker_value,
            observed_at=event.observed_at,
            payload=event.payload,
            payload_digest=event.payload_digest,
            redactions=event.redactions,
        )
        return self._marker

    def finalize(
        self,
        *,
        current_identity: BilateralRuntimeIdentity,
        positive_assertion_ids: Iterable[str],
        negative_assertion_ids: Iterable[str],
        preservation_assertion_ids: Iterable[str],
        fault_assertion_ids: Iterable[str],
        adjacent_scenario_ids: Iterable[str],
        finalized_at: float | None = None,
    ) -> IncidentReplayPacket:
        self._require_capturing()
        self.identity.assert_current(current_identity)
        if self._marker is None:
            raise BilateralLiveRepairError("an explicit incident marker is required")
        positive = _string_tuple(positive_assertion_ids, "positive_assertion_ids", required=True)
        negative = _string_tuple(negative_assertion_ids, "negative_assertion_ids", required=True)
        preservation = _string_tuple(
            preservation_assertion_ids, "preservation_assertion_ids", required=True
        )
        faults = _string_tuple(fault_assertion_ids, "fault_assertion_ids", required=True)
        adjacent = _string_tuple(adjacent_scenario_ids, "adjacent_scenario_ids", required=True)
        completed = time.time() if finalized_at is None else _timestamp(finalized_at, "finalized_at")
        if completed < self.started_at or completed < self._marker.observed_at:
            raise ValueError("finalized_at predates capture evidence")
        expires = completed + self.retention_seconds
        body = {
            "version": INCIDENT_VERSION,
            "identity": self.identity.identity_payload(),
            "marker": self._marker.to_dict(),
            "retained_events": [item.to_dict() for item in self._events],
            "positive_assertion_ids": list(positive),
            "negative_assertion_ids": list(negative),
            "preservation_assertion_ids": list(preservation),
            "fault_assertion_ids": list(faults),
            "adjacent_scenario_ids": list(adjacent),
            "started_at": self.started_at,
            "finalized_at": completed,
            "retention_expires_at": expires,
            "authority": AUTHORITY,
        }
        packet_digest = stable_sha256(body)
        packet = IncidentReplayPacket(
            packet_id=f"IRP-{packet_digest[:24]}",
            identity=self.identity,
            marker=self._marker,
            retained_events=tuple(self._events),
            positive_assertion_ids=positive,
            negative_assertion_ids=negative,
            preservation_assertion_ids=preservation,
            fault_assertion_ids=faults,
            adjacent_scenario_ids=adjacent,
            started_at=self.started_at,
            finalized_at=completed,
            retention_expires_at=expires,
            packet_digest=packet_digest,
        )
        self._events.clear()
        self._marker = None
        self._state = "FINALIZED"
        self._finalized_packet_digest = packet.packet_digest
        return packet

    def dissolve(self) -> dict[str, Any]:
        if self._state == "DISSOLVED":
            return self.status()
        self._events.clear()
        self._marker = None
        self._state = "DISSOLVED"
        return self.status()

    def status(self) -> dict[str, Any]:
        return {
            "version": VERSION,
            "state": self._state,
            "identity_digest": self.identity.identity_digest,
            "retained_event_count": len(self._events),
            "maximum_event_count": self.max_events,
            "incident_marked": self._marker is not None,
            "next_sequence": self._next_sequence,
            "finalized_packet_digest": self._finalized_packet_digest,
            "unrestricted_recording": False,
            "authority": dict(AUTHORITY),
        }

