"""Deterministic artifact mutation/identity core for CS-ARENA-SYNC-001 AS-02.

This module is deliberately below semantic ownership, coordinate placement, cloud
write, WorkGraph wake, and project-completion authority. It normalizes one artifact
mutation vocabulary shared by local filesystem, Drive, workspace, and Arena-native
adapters; derives stable identity/idempotency material; evaluates quiescence without
sleeping; and prevents mirror-bounce loops using explicit origin/generation fences.

Presence or a normalized event is never proof that persistence or project work ran.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

EVENT_SCHEMA = "ArtifactMutationEventV1"
IDENTITY_SCHEMA = "ArtifactIdentityV1"
FENCE_SCHEMA = "ArtifactMirrorFenceV1"
QUIESCENCE_SCHEMA = "ArtifactQuiescenceDecisionV1"

EVENT_TYPES = frozenset(
    {"CREATE", "MODIFY", "RENAME", "DELETE", "TOMBSTONE", "ACCEPT", "SUPERSEDE", "MIRROR_REPAIR"}
)
NONCONTENT_EVENTS = frozenset({"DELETE", "TOMBSTONE"})
LINEAGE_REQUIRED_EVENTS = frozenset({"RENAME", "DELETE", "TOMBSTONE", "SUPERSEDE"})


class ArtifactSyncError(ValueError):
    """Typed fail-closed input/lineage error."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _text(value: Any, code: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise ArtifactSyncError(code)
    return result


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ArtifactSyncError("NONCANONICAL_VALUE") from exc


def _digest(domain: str, value: Any) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ArtifactSyncError(code)
    return value


def _sha256(value: str) -> str:
    text = _text(value, "SHA256_REQUIRED").lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ArtifactSyncError("SHA256_INVALID")
    return text


@dataclass(frozen=True)
class ArtifactMutationEventV1:
    event_id: str
    origin_id: str
    provider: str
    source_surface: str
    event_type: str
    source_path_or_resource_id: str
    producer_worker_id: str
    claim_id: str
    work_order_id: str
    project_id: str
    source_currentness_ref: str
    observed_at: str
    generation: int
    mirror_fence: str | None = None
    prior_artifact_id: str | None = None
    prior_source_path_or_resource_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        for value, code in (
            (self.event_id, "EVENT_ID_REQUIRED"),
            (self.origin_id, "ORIGIN_ID_REQUIRED"),
            (self.provider, "PROVIDER_REQUIRED"),
            (self.source_surface, "SOURCE_SURFACE_REQUIRED"),
            (self.source_path_or_resource_id, "SOURCE_REF_REQUIRED"),
            (self.producer_worker_id, "PRODUCER_WORKER_REQUIRED"),
            (self.claim_id, "CLAIM_ID_REQUIRED"),
            (self.work_order_id, "WORK_ORDER_ID_REQUIRED"),
            (self.project_id, "PROJECT_ID_REQUIRED"),
            (self.source_currentness_ref, "SOURCE_CURRENTNESS_REQUIRED"),
            (self.observed_at, "OBSERVED_AT_REQUIRED"),
        ):
            _text(value, code)
        _nonnegative_int(self.generation, "GENERATION_INVALID")
        event_type = self.event_type.strip().upper()
        if event_type not in EVENT_TYPES:
            raise ArtifactSyncError("EVENT_TYPE_INVALID", self.event_type)
        if event_type in LINEAGE_REQUIRED_EVENTS and not (
            (self.prior_artifact_id and self.prior_artifact_id.strip())
            or (self.prior_source_path_or_resource_id and self.prior_source_path_or_resource_id.strip())
        ):
            raise ArtifactSyncError("PRIOR_LINEAGE_REQUIRED", event_type)
        if self.mirror_fence is not None and not self.mirror_fence.strip():
            raise ArtifactSyncError("MIRROR_FENCE_INVALID")
        _canonical(dict(self.metadata))
        expected = self.expected_event_id()
        if self.event_id != expected:
            raise ArtifactSyncError("EVENT_ID_MISMATCH", f"expected={expected}")

    def logical_payload(self) -> dict[str, Any]:
        """Consequence identity intentionally excludes observation clock and metadata."""
        return {
            "schema": EVENT_SCHEMA,
            "origin_id": self.origin_id,
            "provider": self.provider.strip().upper(),
            "source_surface": self.source_surface,
            "event_type": self.event_type.strip().upper(),
            "source_path_or_resource_id": self.source_path_or_resource_id,
            "producer_worker_id": self.producer_worker_id,
            "claim_id": self.claim_id,
            "work_order_id": self.work_order_id,
            "project_id": self.project_id,
            "source_currentness_ref": self.source_currentness_ref,
            "generation": self.generation,
            "mirror_fence": self.mirror_fence,
            "prior_artifact_id": self.prior_artifact_id,
            "prior_source_path_or_resource_id": self.prior_source_path_or_resource_id,
        }

    def expected_event_id(self) -> str:
        return "amev-" + _digest("ARTIFACT_MUTATION_EVENT_V1", self.logical_payload())[:32]

    def idempotency_key(self) -> str:
        self.validate()
        return _digest("ARTIFACT_MUTATION_IDEMPOTENCY_V1", self.logical_payload())

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        result = asdict(self)
        result["schema"] = EVENT_SCHEMA
        result["event_type"] = self.event_type.strip().upper()
        result["idempotency_key"] = self.idempotency_key()
        return result

    @classmethod
    def build(cls, **fields: Any) -> "ArtifactMutationEventV1":
        payload = dict(fields)
        payload["event_type"] = _text(payload.get("event_type"), "EVENT_TYPE_REQUIRED").upper()
        provisional = cls(event_id="__PENDING__", **payload)
        event_id = provisional.expected_event_id()
        event = cls(event_id=event_id, **payload)
        event.validate()
        return event


@dataclass(frozen=True)
class ArtifactIdentityV1:
    artifact_sid: str
    sha256: str
    byte_size: int
    mime: str
    extension: str
    source_surface: str
    source_path_or_resource_id: str
    origin_id: str
    generation: int
    semantic_type: str = "UNKNOWN"
    parent_source_refs: tuple[str, ...] = ()

    def validate(self) -> None:
        _text(self.artifact_sid, "ARTIFACT_SID_REQUIRED")
        _sha256(self.sha256)
        _nonnegative_int(self.byte_size, "BYTE_SIZE_INVALID")
        for value, code in (
            (self.mime, "MIME_REQUIRED"),
            (self.extension, "EXTENSION_REQUIRED"),
            (self.source_surface, "SOURCE_SURFACE_REQUIRED"),
            (self.source_path_or_resource_id, "SOURCE_REF_REQUIRED"),
            (self.origin_id, "ORIGIN_ID_REQUIRED"),
            (self.semantic_type, "SEMANTIC_TYPE_REQUIRED"),
        ):
            _text(value, code)
        _nonnegative_int(self.generation, "GENERATION_INVALID")
        if any(not str(item).strip() for item in self.parent_source_refs):
            raise ArtifactSyncError("PARENT_SOURCE_REF_INVALID")
        if self.artifact_sid != self.expected_artifact_sid():
            raise ArtifactSyncError("ARTIFACT_SID_MISMATCH")

    def expected_artifact_sid(self) -> str:
        """SID preserves observed provenance; byte equality alone is not dedup authority."""
        lineage = {
            "sha256": _sha256(self.sha256),
            "source_surface": self.source_surface,
            "source_path_or_resource_id": self.source_path_or_resource_id,
            "origin_id": self.origin_id,
            "generation": self.generation,
            "parent_source_refs": sorted(self.parent_source_refs),
        }
        return "artifact-" + _digest("ARTIFACT_IDENTITY_V1", lineage)[:32]

    def content_key(self) -> str:
        self.validate()
        return "sha256:" + self.sha256.lower()

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        result = asdict(self)
        result["schema"] = IDENTITY_SCHEMA
        result["parent_source_refs"] = list(self.parent_source_refs)
        result["content_key"] = self.content_key()
        return result

    @classmethod
    def from_bytes(
        cls,
        content: bytes,
        *,
        mime: str,
        extension: str,
        source_surface: str,
        source_path_or_resource_id: str,
        origin_id: str,
        generation: int,
        semantic_type: str = "UNKNOWN",
        parent_source_refs: Iterable[str] = (),
    ) -> "ArtifactIdentityV1":
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise ArtifactSyncError("CONTENT_BYTES_REQUIRED")
        raw = bytes(content)
        sha = hashlib.sha256(raw).hexdigest()
        provisional = cls(
            artifact_sid="__PENDING__",
            sha256=sha,
            byte_size=len(raw),
            mime=mime,
            extension=extension,
            source_surface=source_surface,
            source_path_or_resource_id=source_path_or_resource_id,
            origin_id=origin_id,
            generation=generation,
            semantic_type=semantic_type,
            parent_source_refs=tuple(sorted(set(parent_source_refs))),
        )
        sid = provisional.expected_artifact_sid()
        identity = cls(**{**asdict(provisional), "artifact_sid": sid})
        identity.validate()
        return identity


@dataclass(frozen=True)
class ArtifactMirrorFenceV1:
    origin_id: str
    generation: int
    source_surface: str
    target_surface: str
    fence_token: str

    @classmethod
    def mint(cls, *, origin_id: str, generation: int, source_surface: str, target_surface: str) -> "ArtifactMirrorFenceV1":
        _text(origin_id, "ORIGIN_ID_REQUIRED")
        _nonnegative_int(generation, "GENERATION_INVALID")
        source = _text(source_surface, "SOURCE_SURFACE_REQUIRED")
        target = _text(target_surface, "TARGET_SURFACE_REQUIRED")
        if source == target:
            raise ArtifactSyncError("MIRROR_SAME_SURFACE_FORBIDDEN")
        payload = {
            "origin_id": origin_id,
            "generation": generation,
            "source_surface": source,
            "target_surface": target,
        }
        token = "mf-" + _digest("ARTIFACT_MIRROR_FENCE_V1", payload)[:32]
        return cls(origin_id, generation, source, target, token)

    def validate(self) -> None:
        expected = self.mint(
            origin_id=self.origin_id,
            generation=self.generation,
            source_surface=self.source_surface,
            target_surface=self.target_surface,
        ).fence_token
        if self.fence_token != expected:
            raise ArtifactSyncError("MIRROR_FENCE_TOKEN_MISMATCH")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": FENCE_SCHEMA, **asdict(self)}


def mirror_route_decision(
    *,
    event: ArtifactMutationEventV1,
    target_surface: str,
    inbound_fence: ArtifactMirrorFenceV1 | None = None,
) -> dict[str, Any]:
    """Allow one forward mirror; suppress reflected reverse/self routes deterministically."""
    event.validate()
    target = _text(target_surface, "TARGET_SURFACE_REQUIRED")
    if target == event.source_surface:
        return {"decision": "REFUSED", "code": "MIRROR_SAME_SURFACE_FORBIDDEN", "target_surface": target}
    if inbound_fence is not None:
        inbound_fence.validate()
        if inbound_fence.origin_id != event.origin_id or inbound_fence.generation != event.generation:
            return {"decision": "REFUSED", "code": "MIRROR_FENCE_LINEAGE_MISMATCH", "target_surface": target}
        # Observing on the prior target and attempting to route back to the prior source is a bounce.
        if event.source_surface == inbound_fence.target_surface and target == inbound_fence.source_surface:
            return {"decision": "SUPPRESSED", "code": "MIRROR_BOUNCE_SUPPRESSED", "target_surface": target}
    fence = ArtifactMirrorFenceV1.mint(
        origin_id=event.origin_id,
        generation=event.generation,
        source_surface=event.source_surface,
        target_surface=target,
    )
    return {
        "decision": "ALLOW_MIRROR_PLAN",
        "code": "MIRROR_FENCE_MINTED",
        "target_surface": target,
        "fence": fence.to_dict(),
        "execution_authorized": False,
    }


@dataclass(frozen=True)
class QuiescenceSampleV1:
    byte_size: int
    mtime_ns: int
    observed_monotonic_ns: int
    close_evidence: bool = False
    atomic_publish_evidence: bool = False

    def validate(self) -> None:
        _nonnegative_int(self.byte_size, "QUIESCENCE_SIZE_INVALID")
        _nonnegative_int(self.mtime_ns, "QUIESCENCE_MTIME_INVALID")
        _nonnegative_int(self.observed_monotonic_ns, "QUIESCENCE_OBSERVATION_INVALID")


def evaluate_quiescence(
    samples: Sequence[QuiescenceSampleV1],
    *,
    min_stable_ns: int,
    min_stable_samples: int = 2,
) -> dict[str, Any]:
    """Pure close/stability gate. The caller schedules samples; this function never sleeps."""
    _nonnegative_int(min_stable_ns, "MIN_STABLE_NS_INVALID")
    if isinstance(min_stable_samples, bool) or not isinstance(min_stable_samples, int) or min_stable_samples < 2:
        raise ArtifactSyncError("MIN_STABLE_SAMPLES_INVALID")
    rows = list(samples)
    for row in rows:
        if not isinstance(row, QuiescenceSampleV1):
            raise ArtifactSyncError("QUIESCENCE_SAMPLE_INVALID")
        row.validate()
    if not rows:
        return {"schema": QUIESCENCE_SCHEMA, "decision": "WAIT", "code": "NO_OBSERVATIONS"}
    if any(row.atomic_publish_evidence for row in rows):
        return {"schema": QUIESCENCE_SCHEMA, "decision": "QUIESCENT", "code": "ATOMIC_PUBLISH_EVIDENCE"}
    if rows[-1].close_evidence:
        return {"schema": QUIESCENCE_SCHEMA, "decision": "QUIESCENT", "code": "CLOSE_EVIDENCE"}
    if len(rows) < min_stable_samples:
        return {"schema": QUIESCENCE_SCHEMA, "decision": "WAIT", "code": "INSUFFICIENT_STABLE_SAMPLES"}

    tail = rows[-min_stable_samples:]
    if any(tail[i].observed_monotonic_ns >= tail[i + 1].observed_monotonic_ns for i in range(len(tail) - 1)):
        raise ArtifactSyncError("QUIESCENCE_OBSERVATION_ORDER_INVALID")
    signature = {(row.byte_size, row.mtime_ns) for row in tail}
    elapsed = tail[-1].observed_monotonic_ns - tail[0].observed_monotonic_ns
    if len(signature) == 1 and elapsed >= min_stable_ns:
        return {
            "schema": QUIESCENCE_SCHEMA,
            "decision": "QUIESCENT",
            "code": "STABLE_WINDOW_OBSERVED",
            "stable_ns": elapsed,
            "sample_count": len(tail),
        }
    return {
        "schema": QUIESCENCE_SCHEMA,
        "decision": "WAIT",
        "code": "MUTATION_STILL_ACTIVE",
        "stable_ns": elapsed,
        "sample_count": len(tail),
    }


def event_for_mirrored_observation(
    source_event: ArtifactMutationEventV1,
    *,
    observed_surface: str,
    observed_source_ref: str,
    fence: ArtifactMirrorFenceV1,
    observed_at: str,
    provider: str,
) -> ArtifactMutationEventV1:
    """Normalize the observation generated by our own mirror without losing origin lineage."""
    source_event.validate()
    fence.validate()
    if fence.origin_id != source_event.origin_id or fence.generation != source_event.generation:
        raise ArtifactSyncError("MIRROR_FENCE_LINEAGE_MISMATCH")
    if observed_surface != fence.target_surface:
        raise ArtifactSyncError("MIRROR_OBSERVED_SURFACE_MISMATCH")
    return ArtifactMutationEventV1.build(
        origin_id=source_event.origin_id,
        provider=provider,
        source_surface=observed_surface,
        event_type="MODIFY" if source_event.event_type == "MODIFY" else "CREATE",
        source_path_or_resource_id=observed_source_ref,
        producer_worker_id=source_event.producer_worker_id,
        claim_id=source_event.claim_id,
        work_order_id=source_event.work_order_id,
        project_id=source_event.project_id,
        source_currentness_ref=source_event.source_currentness_ref,
        observed_at=observed_at,
        generation=source_event.generation,
        mirror_fence=fence.fence_token,
        prior_artifact_id=source_event.prior_artifact_id,
        metadata={"mirror_source_event_id": source_event.event_id},
    )
