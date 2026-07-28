"""Canonical B11-B15 bilateral live-repair and Spatial Foundry adapter.

This module composes Aura's existing Attempt Archive, Runtime Profile V2,
Crucible/U7 learning-to-reproof, and Showcase projection owners.  It is not a
truth, archive, verifier, policy, rollback-authority, learning, or publication
plane.  Every consequential result remains exact-identity-bound and proposal
only until the existing human/community gates authorize the next action.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
import math
import re
from typing import Any, cast

from aura_arena_experience import sanitize_experience_payload

VERSION = "AURA_BILATERAL_LIVE_REPAIR_FOUNDRY_V2"
INCIDENT_VERSION = "AURA_BILATERAL_INCIDENT_REPLAY_V2"
PREVIEW_VERSION = "AURA_LOCAL_PREVIEW_ROLLBACK_V1"
PROJECTION_VERSION = "AURA_SPATIAL_FOUNDRY_PROJECTION_V1"
MAX_EVENTS = 256
MAX_ATTEMPTS = 8
MAX_ACTIVE_CAPTURES = 32
MAX_PENDING_PACKET_ARCHIVES = 8
MAX_RETENTION_SECONDS = 300
MAX_TEXT_BYTES = 32 * 1024
MAX_EVENT_BYTES = 64 * 1024
MAX_CAPTURE_BYTES = 4 * 1024 * 1024
MAX_ARCHIVED_PACKET_BYTES = 8 * 1024 * 1024
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False

_FALSE_AUTHORITY = {
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
}
_HEX = re.compile(r"^[0-9a-f]{40,64}$")
_ALLOWED_ROUTE_CLASSES = frozenset({"LOCAL", "STRUCTURAL"})
_STRUCTURAL_FAILURES = frozenset(
    {"INTERFACE", "DEPENDENCY", "INVARIANT", "SCOPE", "AUTHORITY", "PROHIBITION", "SEQUENCE"}
)
_LOCAL_FAILURES = frozenset({"LOCAL_ASSERTION", "LOCAL_TEST", "EXACT_SPAN_PATCH", "SOURCE_ASSERTION"})


class BilateralLiveRepairError(RuntimeError):
    """A live-repair request crossed a deterministic contract boundary."""


def _required_text(value: Any, name: str, *, limit: int = MAX_TEXT_BYTES) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    text = value.strip()
    if len(text.encode("utf-8")) > limit:
        raise ValueError(f"{name} exceeds {limit} UTF-8 bytes")
    return text


def _digest_text(value: Any, name: str) -> str:
    text = _required_text(value, name, limit=256).lower()
    if not _HEX.fullmatch(text):
        raise ValueError(f"{name} must be a 40-64 character lowercase hexadecimal identity")
    return text


def _timestamp(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite timestamp")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite timestamp")
    return result


def _required_int(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")
    return value


def _normalize(value: Any) -> Any:
    """Normalize data before canonical sanitization.

    Sets are sorted by canonical serialized value, closing the nondeterminism
    identified in PR #238. Mapping keys are stringified and sorted. Lists and
    tuples preserve their intentional order.
    """

    if is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, Mapping):
        output: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool)) or (
                isinstance(key, float) and not math.isfinite(key)
            ):
                raise ValueError("mapping keys must have deterministic scalar identities")
            normalized_key = str(key)
            if normalized_key in output:
                raise ValueError(f"mapping keys collide after canonical string conversion: {normalized_key!r}")
            output[normalized_key] = _normalize(item)
        return {key: output[key] for key in sorted(output)}
    if isinstance(value, (set, frozenset)):
        normalized = [_normalize(item) for item in value]
        return sorted(normalized, key=lambda item: canonical_bytes(item))
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite values are not permitted in canonical identity")
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise ValueError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_sanitize(value: Any) -> tuple[Any, tuple[str, ...]]:
    """Use Aura's canonical experience sanitizer after deterministic ordering."""

    normalized = _normalize(value)
    sanitized, redactions = sanitize_experience_payload(normalized)
    return _normalize(sanitized), tuple(sorted({str(item) for item in redactions}))


def canonical_bytes(value: Any) -> bytes:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _runtime_binding_digest(value: Any) -> str:
    """Match Runtime Profile V2's canonical requirement/candidate identity."""

    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode(), digest_size=32).hexdigest()


@dataclass(frozen=True)
class BilateralIdentity:
    intent_digest: str
    confirmation_digest: str
    semantic_ledger_digest: str
    guardrail_set_digest: str
    intent_revision_id: str
    repository_head: str
    source_tree_digest: str
    runtime_profile_digest: str
    verifier_id: str
    verifier_source_digest: str

    def __post_init__(self) -> None:
        for name in (
            "intent_digest",
            "semantic_ledger_digest",
            "guardrail_set_digest",
            "repository_head",
            "source_tree_digest",
            "runtime_profile_digest",
            "verifier_source_digest",
        ):
            object.__setattr__(self, name, _digest_text(getattr(self, name), name))
        object.__setattr__(
            self,
            "confirmation_digest",
            _required_text(self.confirmation_digest, "confirmation_digest", limit=512),
        )
        object.__setattr__(self, "intent_revision_id", _required_text(self.intent_revision_id, "intent_revision_id", limit=512))
        object.__setattr__(self, "verifier_id", _required_text(self.verifier_id, "verifier_id", limit=512))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "BilateralIdentity":
        if not isinstance(value, Mapping):
            raise ValueError("identity must be an object")
        expected = set(cls.__dataclass_fields__)
        if set(value) != expected:
            missing = sorted(expected - set(value))
            unknown = sorted(set(value) - expected)
            raise ValueError(f"identity schema mismatch; missing={missing}, unknown={unknown}")
        return cls(**{name: value[name] for name in cls.__dataclass_fields__})

    @property
    def identity_digest(self) -> str:
        return digest(asdict(self))

    def assert_current(self, current: "BilateralIdentity") -> None:
        if not isinstance(current, BilateralIdentity) or current != self:
            raise BilateralLiveRepairError("bilateral identity is stale or mismatched")


@dataclass(frozen=True)
class IncidentEvent:
    sequence: int
    event_type: str
    observed_at: float
    payload: Mapping[str, Any]
    payload_digest: str
    redactions: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "IncidentEvent":
        if not isinstance(value, Mapping):
            raise ValueError("incident event must be an object")
        payload, redactions = canonical_sanitize(value.get("payload") or {})
        event = cls(
            sequence=_required_int(value.get("sequence"), "sequence"),
            event_type=_required_text(value.get("event_type"), "event_type", limit=256),
            observed_at=_timestamp(value.get("observed_at"), "observed_at"),
            payload=payload,
            payload_digest=_digest_text(value.get("payload_digest"), "payload_digest"),
            redactions=tuple(sorted({str(item) for item in value.get("redactions") or (*redactions,)})),
        )
        if event.sequence < 0 or digest(event.payload) != event.payload_digest:
            raise ValueError("incident event identity is invalid")
        return event


@dataclass(frozen=True)
class CaptureDissolutionReceipt:
    capture_id: str
    terminal_state: str
    retained_event_count: int
    total_event_count: int
    marker_retained_separately: bool
    closed_at: float
    timers_released: bool = True
    listeners_released: bool = True
    buffers_cleared: bool = True
    unrestricted_recording: bool = False


@dataclass(frozen=True)
class RequiredAssetIdentity:
    path: str
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", _required_text(self.path, "required asset path", limit=2048))
        sha256 = _digest_text(self.sha256, "required asset sha256")
        if len(sha256) != 64:
            raise ValueError("required asset sha256 must be a 64-character digest")
        object.__setattr__(self, "sha256", sha256)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RequiredAssetIdentity":
        if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
            raise ValueError("required asset identity must contain only path and sha256")
        return cls(path=value["path"], sha256=value["sha256"])


@dataclass(frozen=True)
class IncidentReplayPacket:
    packet_id: str
    identity: BilateralIdentity
    release_id: str
    environment_id: str
    capture_id: str
    marker_event: IncidentEvent
    events: tuple[IncidentEvent, ...]
    window_start_sequence: int
    total_event_count: int
    expected_positive: tuple[str, ...]
    expected_negative: tuple[str, ...]
    preservation_claims: tuple[str, ...]
    required_assets: tuple[RequiredAssetIdentity, ...]
    retention_class: str
    created_at: float
    packet_digest: str
    privacy_receipt: Mapping[str, Any]
    dissolution_receipt: CaptureDissolutionReceipt
    authority: Mapping[str, bool]
    version: str = INCIDENT_VERSION

    def canonical_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload.pop("packet_id", None)
        payload.pop("packet_digest", None)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "IncidentReplayPacket":
        if not isinstance(value, Mapping):
            raise ValueError("incident replay packet must be an object")
        identity = BilateralIdentity.from_mapping(value.get("identity") or {})
        marker = IncidentEvent.from_mapping(value.get("marker_event") or {})
        events = tuple(IncidentEvent.from_mapping(item) for item in value.get("events") or ())
        dissolution_raw = value.get("dissolution_receipt") or {}
        if not isinstance(dissolution_raw, Mapping):
            raise ValueError("dissolution receipt must be an object")
        try:
            dissolution = CaptureDissolutionReceipt(**dict(dissolution_raw))
        except TypeError as exc:
            raise ValueError(f"dissolution receipt construction failed: {exc}") from exc
        authority = dict(value.get("authority") or {})
        if any(authority.get(name) is not False for name in _FALSE_AUTHORITY):
            raise ValueError("incident replay packet grants forbidden authority")
        packet = cls(
            packet_id=_required_text(value.get("packet_id"), "packet_id", limit=128),
            identity=identity,
            release_id=_required_text(value.get("release_id"), "release_id", limit=512),
            environment_id=_required_text(value.get("environment_id"), "environment_id", limit=512),
            capture_id=_required_text(value.get("capture_id"), "capture_id", limit=128),
            marker_event=marker,
            events=events,
            window_start_sequence=_required_int(
                value.get("window_start_sequence"),
                "window_start_sequence",
            ),
            total_event_count=_required_int(
                value.get("total_event_count"),
                "total_event_count",
            ),
            expected_positive=tuple(_required_text(item, "positive requirement", limit=4096) for item in value.get("expected_positive") or ()),
            expected_negative=tuple(_required_text(item, "negative requirement", limit=4096) for item in value.get("expected_negative") or ()),
            preservation_claims=tuple(_required_text(item, "preservation claim", limit=4096) for item in value.get("preservation_claims") or ()),
            required_assets=tuple(
                RequiredAssetIdentity.from_mapping(item)
                for item in value.get("required_assets") or ()
            ),
            retention_class=_required_text(value.get("retention_class"), "retention_class", limit=128),
            created_at=_timestamp(value.get("created_at"), "created_at"),
            packet_digest=_digest_text(value.get("packet_digest"), "packet_digest"),
            privacy_receipt=dict(value.get("privacy_receipt") or {}),
            dissolution_receipt=dissolution,
            authority=authority,
            version=_required_text(value.get("version"), "version", limit=128),
        )
        if (
            packet.version != INCIDENT_VERSION
            or not packet.expected_positive
            or not packet.expected_negative
            or not packet.preservation_claims
            or packet.total_event_count < len(packet.events)
            or packet.marker_event.event_type != "INCIDENT_MARKER"
            or packet.dissolution_receipt.capture_id != packet.capture_id
            or packet.dissolution_receipt.terminal_state != "DISSOLVED"
            or packet.dissolution_receipt.buffers_cleared is not True
            or packet.dissolution_receipt.unrestricted_recording is not False
            or packet.dissolution_receipt.closed_at != packet.created_at
            or tuple(item.sequence for item in packet.events) != tuple(
                range(packet.window_start_sequence, packet.total_event_count)
            )
            or packet.marker_event.sequence >= packet.total_event_count
            or digest(packet.canonical_payload()) != packet.packet_digest
            or packet.packet_id != f"IRP-{packet.packet_digest[:24]}"
        ):
            raise ValueError("incident replay packet identity is invalid")
        return packet



@dataclass(frozen=True)
class RepairCandidateResult:
    attempt_id: str
    replay_packet_digest: str
    hypothesis_digest: str
    candidate_digest: str
    runtime_proof_digest: str
    runtime_proof_passed: bool
    positive_passed: bool
    negative_passed: bool
    preservation_passed: bool
    fault_injections_passed: bool
    adjacent_regressions_passed: bool
    repository_unchanged: bool
    independent_verifier_exact: bool
    minimized_counterexample: Mapping[str, Any] | None
    failure_class: str
    route_class: str
    promotion_ready: bool
    archive_artifact_ref: str
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, archive_artifact_ref: str = "") -> "RepairCandidateResult":
        if not isinstance(value, Mapping):
            raise ValueError("repair attempt must be an object")
        payload = {name: value.get(name) for name in cls.__dataclass_fields__}
        payload["archive_artifact_ref"] = archive_artifact_ref or str(payload.get("archive_artifact_ref") or "")
        if "runtime_proof_passed" not in value:
            # Compatibility for receipts written before the proof-level result
            # was persisted. Promotion could only be true when the proof passed.
            payload["runtime_proof_passed"] = value.get("promotion_ready") is True
        counterexample = payload.get("minimized_counterexample")
        payload["minimized_counterexample"] = dict(counterexample) if isinstance(counterexample, Mapping) else None
        item = cast(Any, cls)(**payload)
        if (
            item.route_class not in _ALLOWED_ROUTE_CLASSES
            or item.route_class != classify_repair_route(item.failure_class)
            or item.promotion_ready != all((
                item.runtime_proof_passed,
                item.positive_passed, item.negative_passed, item.preservation_passed,
                item.fault_injections_passed, item.adjacent_regressions_passed,
                item.repository_unchanged, item.independent_verifier_exact,
            ))
        ):
            raise ValueError("repair attempt identity or proof classification is invalid")
        return item


@dataclass(frozen=True)
class PreviewRollbackReceipt:
    preview_id: str
    replay_packet_digest: str
    bilateral_identity_digest: str
    candidate_digest: str
    last_verified_digest: str
    health_before_digest: str
    health_after_digest: str
    environment_class: str
    preview_isolated: bool
    degraded: bool
    rollback_preauthorized: bool
    technical_rollback_executed: bool
    rollback_succeeded: bool
    restored_digest: str
    rollback_reason: str
    rollback_failure: str
    human_promotion_required: bool
    production_mutation: bool
    created_at: float
    version: str = PREVIEW_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreviewRollbackReceipt":
        if not isinstance(value, Mapping):
            raise ValueError("preview receipt must be an object")
        payload = {name: value.get(name) for name in cls.__dataclass_fields__}
        if "rollback_succeeded" not in value:
            payload["rollback_succeeded"] = (
                value.get("technical_rollback_executed") is True
                and value.get("restored_digest") == value.get("last_verified_digest")
            )
        if "rollback_failure" not in value:
            payload["rollback_failure"] = ""
        item = cast(Any, cls)(**payload)
        for name in (
            "replay_packet_digest",
            "bilateral_identity_digest",
            "candidate_digest",
            "last_verified_digest",
            "health_before_digest",
            "health_after_digest",
        ):
            _digest_text(getattr(item, name), name)
        if item.restored_digest:
            _digest_text(item.restored_digest, "restored_digest")
        for name in (
            "preview_isolated",
            "degraded",
            "rollback_preauthorized",
            "technical_rollback_executed",
            "rollback_succeeded",
            "human_promotion_required",
            "production_mutation",
        ):
            if type(getattr(item, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        _timestamp(item.created_at, "created_at")
        _required_text(item.preview_id, "preview_id", limit=128)
        if type(item.rollback_reason) is not str or type(item.rollback_failure) is not str:
            raise ValueError("rollback_reason and rollback_failure must be strings")
        identity = {
            "replay_packet_digest": item.replay_packet_digest,
            "bilateral_identity_digest": item.bilateral_identity_digest,
            "candidate_digest": item.candidate_digest,
            "last_verified_digest": item.last_verified_digest,
            "health_before_digest": item.health_before_digest,
            "health_after_digest": item.health_after_digest,
            "environment_class": item.environment_class,
            "degraded": item.degraded,
            "rollback_preauthorized": item.rollback_preauthorized,
            "technical_rollback_executed": item.technical_rollback_executed,
            "rollback_succeeded": item.rollback_succeeded,
            "restored_digest": item.restored_digest,
            "rollback_failure": item.rollback_failure,
        }
        if "rollback_succeeded" not in value and "rollback_failure" not in value:
            identity.pop("rollback_succeeded")
            identity.pop("rollback_failure")
        if (
            item.version != PREVIEW_VERSION
            or item.preview_id != f"PREVIEW-{digest(identity)[:24]}"
            or item.preview_isolated is not True
            or item.production_mutation is not False
            or item.human_promotion_required is not True
            or item.environment_class not in {"LOCAL_EPHEMERAL", "CANARY_ISOLATED"}
            or (item.degraded and not item.rollback_reason.strip())
            or (item.technical_rollback_executed and item.rollback_preauthorized is not True)
            or (
                item.rollback_succeeded
                and (
                    item.technical_rollback_executed is not True
                    or item.restored_digest != item.last_verified_digest
                    or bool(item.rollback_failure)
                )
            )
            or (
                item.technical_rollback_executed
                and not item.rollback_succeeded
                and not item.rollback_failure.strip()
            )
            or (not item.technical_rollback_executed and bool(item.restored_digest))
            or (not item.technical_rollback_executed and bool(item.rollback_failure))
        ):
            raise ValueError("preview receipt authority or rollback identity is invalid")
        return item


def _group_passed(runtime_proof: Mapping[str, Any], group: str) -> bool:
    rows = runtime_proof.get(group)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)) or not rows:
        return False
    return all(isinstance(item, Mapping) and item.get("passed") is True for item in rows)


def classify_repair_route(failure_class: str) -> str:
    failure = _required_text(failure_class, "failure_class", limit=160).upper()
    if failure in _LOCAL_FAILURES:
        return "LOCAL"
    if failure in _STRUCTURAL_FAILURES:
        return "STRUCTURAL"
    raise ValueError("failure_class is not a canonical Surgeon/Council routing class")


def derive_repair_failure_class(runtime_proof: Mapping[str, Any]) -> str:
    """Derive Surgeon/Council routing from retained proof, never caller preference."""

    if runtime_proof.get("repository_identity_unchanged") is not True:
        return "INVARIANT"
    verifier = runtime_proof.get("independent_verifier")
    if not isinstance(verifier, Mapping):
        return "AUTHORITY"
    if not _group_passed(runtime_proof, "negative_assertions"):
        return "PROHIBITION"
    if not _group_passed(runtime_proof, "preservation_assertions"):
        return "INVARIANT"
    if not _group_passed(runtime_proof, "positive_assertions"):
        return _failed_group_class(runtime_proof, "positive_assertions", "DEPENDENCY")
    if not _group_passed(runtime_proof, "fault_injections"):
        return _failed_group_class(runtime_proof, "fault_injections", "INVARIANT")
    base = runtime_proof.get("base_runtime_receipt")
    if not isinstance(base, Mapping) or base.get("ok") is not True:
        failure = str(base.get("failure_class") or "").upper() if isinstance(base, Mapping) else ""
        return failure if failure in _STRUCTURAL_FAILURES | _LOCAL_FAILURES else "DEPENDENCY"
    return "SOURCE_ASSERTION"


def _failed_group_class(
    runtime_proof: Mapping[str, Any],
    group: str,
    structural_default: str,
) -> str:
    rows = runtime_proof.get(group)
    if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
        for row in rows:
            if isinstance(row, Mapping) and row.get("passed") is not True:
                failure = str(row.get("failure_class") or "").upper()
                if failure in _STRUCTURAL_FAILURES | _LOCAL_FAILURES:
                    return failure
    return structural_default




__all__ = [
    "BilateralIdentity",
    "BilateralLiveRepairError",
    "CaptureDissolutionReceipt",
    "IncidentEvent",
    "IncidentReplayPacket",
    "RequiredAssetIdentity",
    "PreviewRollbackReceipt",
    "RepairCandidateResult",
    "canonical_bytes",
    "canonical_sanitize",
    "classify_repair_route",
    "derive_repair_failure_class",
    "digest",
]
