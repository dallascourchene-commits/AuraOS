from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence, Tuple


ARTIFACT_EVENT_SCHEMA = "ArtifactMutationEventV1"
ARTIFACT_IDENTITY_SCHEMA = "ArtifactIdentityV1"
MIRROR_LINEAGE_SCHEMA = "ArtifactMirrorLineageV1"

ALLOWED_EVENT_TYPES = frozenset(
    {"CREATE", "MODIFY", "RENAME", "DELETE", "TOMBSTONE", "ACCEPT", "SUPERSEDE", "MIRROR_REPAIR"}
)


class ArtifactEventRefusal(ValueError):
    """Typed fail-closed refusal for the pure artifact event core."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _clean_text(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ArtifactEventRefusal(f"INVALID_{name.upper()}")
    text = value.strip()
    if not text and not allow_empty:
        raise ArtifactEventRefusal(f"INVALID_{name.upper()}")
    if any(ord(ch) < 32 and ch not in "\t\n\r" for ch in text):
        raise ArtifactEventRefusal(f"INVALID_{name.upper()}")
    return text


def _canonical_digest(value: Mapping[str, object]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArtifactMutationEvent:
    origin_id: str
    provider: str
    source_surface: str
    event_type: str
    resource_ref: str
    project_id: str
    producer_worker_id: str = ""
    claim_id: str = ""
    work_order_id: str = ""
    source_currentness_ref: str = ""
    observed_at: str = ""
    generation: int = 0
    mirror_fence: str = ""
    prior_artifact_id: str = ""
    event_id: str = ""
    schema: str = ARTIFACT_EVENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ARTIFACT_EVENT_SCHEMA:
            raise ArtifactEventRefusal("UNSUPPORTED_EVENT_SCHEMA")
        object.__setattr__(self, "origin_id", _clean_text("origin_id", self.origin_id))
        object.__setattr__(self, "provider", _clean_text("provider", self.provider))
        object.__setattr__(self, "source_surface", _clean_text("source_surface", self.source_surface))
        object.__setattr__(self, "resource_ref", _clean_text("resource_ref", self.resource_ref))
        object.__setattr__(self, "project_id", _clean_text("project_id", self.project_id))
        event_type = _clean_text("event_type", self.event_type).upper()
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ArtifactEventRefusal("UNSUPPORTED_EVENT_TYPE", event_type)
        object.__setattr__(self, "event_type", event_type)
        if not isinstance(self.generation, int) or isinstance(self.generation, bool) or self.generation < 0:
            raise ArtifactEventRefusal("INVALID_GENERATION")
        for field_name in (
            "producer_worker_id", "claim_id", "work_order_id", "source_currentness_ref",
            "observed_at", "mirror_fence", "prior_artifact_id",
        ):
            object.__setattr__(
                self, field_name,
                _clean_text(field_name, getattr(self, field_name), allow_empty=True),
            )
        expected = self.compute_event_id()
        supplied = _clean_text("event_id", self.event_id, allow_empty=True)
        if supplied and supplied != expected:
            raise ArtifactEventRefusal("EVENT_ID_BINDING_MISMATCH")
        object.__setattr__(self, "event_id", expected)

    def identity_payload(self) -> dict[str, object]:
        # observed_at is deliberately excluded: replaying the same provider/local
        # mutation later must not create a different idempotency identity.
        return {
            "schema": self.schema,
            "origin_id": self.origin_id,
            "provider": self.provider,
            "source_surface": self.source_surface,
            "event_type": self.event_type,
            "resource_ref": self.resource_ref,
            "project_id": self.project_id,
            "producer_worker_id": self.producer_worker_id,
            "claim_id": self.claim_id,
            "work_order_id": self.work_order_id,
            "source_currentness_ref": self.source_currentness_ref,
            "generation": self.generation,
            "mirror_fence": self.mirror_fence,
            "prior_artifact_id": self.prior_artifact_id,
        }

    def compute_event_id(self) -> str:
        return f"evt-{_canonical_digest(self.identity_payload())[:32]}"

    def to_dict(self) -> dict[str, object]:
        return {**self.identity_payload(), "event_id": self.event_id, "observed_at": self.observed_at}


@dataclass(frozen=True)
class ArtifactIdentity:
    sha256: str
    byte_size: int
    mime_type: str
    extension: str
    parent_refs: Tuple[str, ...] = ()
    artifact_sid: str = ""
    schema: str = ARTIFACT_IDENTITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != ARTIFACT_IDENTITY_SCHEMA:
            raise ArtifactEventRefusal("UNSUPPORTED_IDENTITY_SCHEMA")
        digest = _clean_text("sha256", self.sha256).lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ArtifactEventRefusal("INVALID_SHA256")
        object.__setattr__(self, "sha256", digest)
        if not isinstance(self.byte_size, int) or isinstance(self.byte_size, bool) or self.byte_size < 0:
            raise ArtifactEventRefusal("INVALID_BYTE_SIZE")
        object.__setattr__(self, "mime_type", _clean_text("mime_type", self.mime_type, allow_empty=True))
        ext = _clean_text("extension", self.extension, allow_empty=True).lower()
        if ext and not ext.startswith("."):
            ext = "." + ext
        object.__setattr__(self, "extension", ext)
        refs = tuple(sorted({_clean_text("parent_ref", ref) for ref in self.parent_refs}))
        object.__setattr__(self, "parent_refs", refs)
        expected = f"artifact-sha256-{digest}"
        supplied = _clean_text("artifact_sid", self.artifact_sid, allow_empty=True)
        if supplied and supplied != expected:
            raise ArtifactEventRefusal("ARTIFACT_SID_BINDING_MISMATCH")
        object.__setattr__(self, "artifact_sid", expected)

    @classmethod
    def from_bytes(
        cls,
        payload: bytes,
        *,
        mime_type: str = "",
        extension: str = "",
        parent_refs: Sequence[str] = (),
    ) -> "ArtifactIdentity":
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise ArtifactEventRefusal("PAYLOAD_NOT_BYTES")
        body = bytes(payload)
        return cls(
            sha256=hashlib.sha256(body).hexdigest(),
            byte_size=len(body),
            mime_type=mime_type,
            extension=extension,
            parent_refs=tuple(parent_refs),
        )


@dataclass(frozen=True)
class FileObservation:
    byte_size: int
    mtime_ns: int

    def __post_init__(self) -> None:
        if not isinstance(self.byte_size, int) or self.byte_size < 0:
            raise ArtifactEventRefusal("INVALID_OBSERVED_SIZE")
        if not isinstance(self.mtime_ns, int) or self.mtime_ns < 0:
            raise ArtifactEventRefusal("INVALID_MTIME_NS")


@dataclass(frozen=True)
class QuiescenceProof:
    stable_samples: int
    byte_size: int
    mtime_ns: int
    closed_evidence: bool = False


def prove_quiescence(
    observations: Sequence[FileObservation],
    *,
    min_stable_samples: int = 2,
    closed_evidence: bool = False,
) -> QuiescenceProof:
    """Prove caller-sampled stability; the pure core never sleeps or watches."""
    if not isinstance(min_stable_samples, int) or min_stable_samples < 2:
        raise ArtifactEventRefusal("INVALID_STABLE_SAMPLE_REQUIREMENT")
    if closed_evidence:
        if not observations:
            raise ArtifactEventRefusal("QUIESCENCE_OBSERVATION_REQUIRED")
        last = observations[-1]
        return QuiescenceProof(1, last.byte_size, last.mtime_ns, True)
    if len(observations) < min_stable_samples:
        raise ArtifactEventRefusal("ARTIFACT_NOT_QUIESCENT")
    tail = observations[-min_stable_samples:]
    first = tail[0]
    if any((s.byte_size, s.mtime_ns) != (first.byte_size, first.mtime_ns) for s in tail[1:]):
        raise ArtifactEventRefusal("ARTIFACT_NOT_QUIESCENT")
    return QuiescenceProof(min_stable_samples, first.byte_size, first.mtime_ns, False)


@dataclass(frozen=True)
class MirrorLineage:
    origin_id: str
    surfaces: Tuple[str, ...]
    generation: int = 0
    max_hops: int = 8
    schema: str = MIRROR_LINEAGE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != MIRROR_LINEAGE_SCHEMA:
            raise ArtifactEventRefusal("UNSUPPORTED_MIRROR_SCHEMA")
        object.__setattr__(self, "origin_id", _clean_text("origin_id", self.origin_id))
        surfaces = tuple(_clean_text("surface", s) for s in self.surfaces)
        if not surfaces:
            raise ArtifactEventRefusal("MIRROR_SURFACE_REQUIRED")
        if len(set(surfaces)) != len(surfaces):
            raise ArtifactEventRefusal("MIRROR_LINEAGE_LOOP")
        object.__setattr__(self, "surfaces", surfaces)
        if not isinstance(self.generation, int) or self.generation < 0:
            raise ArtifactEventRefusal("INVALID_GENERATION")
        if not isinstance(self.max_hops, int) or self.max_hops < 1:
            raise ArtifactEventRefusal("INVALID_MAX_HOPS")
        if self.generation != len(surfaces) - 1:
            raise ArtifactEventRefusal("MIRROR_GENERATION_MISMATCH")
        if len(surfaces) > self.max_hops + 1:
            raise ArtifactEventRefusal("MIRROR_MAX_HOPS_EXCEEDED")

    @classmethod
    def start(cls, origin_id: str, source_surface: str, *, max_hops: int = 8) -> "MirrorLineage":
        return cls(origin_id=origin_id, surfaces=(source_surface,), generation=0, max_hops=max_hops)

    def next_hop(self, target_surface: str) -> "MirrorLineage":
        target = _clean_text("target_surface", target_surface)
        if target in self.surfaces:
            raise ArtifactEventRefusal("MIRROR_LOOP_SUPPRESSED", target)
        if self.generation >= self.max_hops:
            raise ArtifactEventRefusal("MIRROR_MAX_HOPS_EXCEEDED")
        return MirrorLineage(
            origin_id=self.origin_id,
            surfaces=self.surfaces + (target,),
            generation=self.generation + 1,
            max_hops=self.max_hops,
        )

    @property
    def fence(self) -> str:
        payload = {
            "schema": self.schema,
            "origin_id": self.origin_id,
            "surfaces": self.surfaces,
            "generation": self.generation,
        }
        return f"mf-{_canonical_digest(payload)[:32]}"


def classify_replay(
    event: ArtifactMutationEvent,
    *,
    currentness: str,
    seen_event_ids: Iterable[str] = (),
) -> str:
    """Return deterministic pre-effect disposition."""
    if _clean_text("currentness", currentness).upper() != "CURRENT":
        return "REBASE"
    if event.event_id in set(seen_event_ids):
        return "IDEMPOTENT_REPLAY"
    if event.event_type in {"DELETE", "TOMBSTONE"}:
        return "TOMBSTONE"
    return "INGEST"


def require_rename_parent(event: ArtifactMutationEvent) -> None:
    if event.event_type == "RENAME" and not event.prior_artifact_id:
        raise ArtifactEventRefusal("RENAME_PRIOR_ARTIFACT_REQUIRED")


def validate_event_identity_binding(
    event: ArtifactMutationEvent,
    identity: ArtifactIdentity | None,
) -> None:
    if event.event_type in {"DELETE", "TOMBSTONE"}:
        if identity is not None:
            raise ArtifactEventRefusal("TOMBSTONE_MUST_NOT_REQUIRE_BYTES")
        return
    if identity is None:
        raise ArtifactEventRefusal("ARTIFACT_IDENTITY_REQUIRED")
