"""Source-owned trust registry for BugHound authority-bearing proof planes.

This is intentionally a *hold* registry. The canonical source generation exists,
but no live-effect or sanitizer artifact is currently registered. A caller
cannot create trust by supplying an expected digest/ref/generation alongside an
artifact it also created. Promotion requires an exact artifact digest plus its
producer/currentness (and reviewer, where applicable) to be registered in this
repository-owned plane, followed by exact-current verification.

The registry is D0 metadata only and grants no external effect by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "BugHoundAuthorityRegistryV2"
REGISTRY_GENERATION = "BUGHOUND_AUTHORITY_REGISTRY_HOLD_V2"
LIVE_EFFECT_PLANE = "LIVE_EFFECT_GRANT"
SANITIZER_PLANE = "SANITIZED_PATTERN"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


class AuthorityRegistryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class AuthorityProducerRecordV2:
    proof_plane: str
    artifact_digest: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    reviewer_ref: str | None = None
    reviewer_generation: str | None = None
    reviewer_currentness_ref: str | None = None
    enabled: bool = True
    authority: bool = False
    schema: str = "AuthorityProducerRecordV2"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_AUTHORITY_PRODUCER_RECORD_V2", asdict(self))


# Canonical source-owned records. Deliberately empty until an independently
# owned producer/currentness lane registers one exact consequence artifact.
# Tests may verify the hold, but production admission never accepts a caller-
# supplied registry object or caller-supplied expected producer identity.
_CANONICAL_RECORDS: tuple[AuthorityProducerRecordV2, ...] = ()


@dataclass(frozen=True)
class AuthorityRegistryReceiptV2:
    registry_generation: str
    record_digests: tuple[str, ...]
    live_effect_producer_count: int
    sanitizer_producer_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_AUTHORITY_REGISTRY_V2", asdict(self))


def authority_registry_receipt() -> AuthorityRegistryReceiptV2:
    records = tuple(sorted(_CANONICAL_RECORDS, key=lambda record: record.record_digest))
    return AuthorityRegistryReceiptV2(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in records),
        live_effect_producer_count=sum(
            1 for record in records if record.enabled and record.proof_plane == LIVE_EFFECT_PLANE
        ),
        sanitizer_producer_count=sum(
            1 for record in records if record.enabled and record.proof_plane == SANITIZER_PLANE
        ),
    )


def resolve_authority_producer(
    *,
    proof_plane: str,
    artifact_digest: str,
    producer_ref: str,
    producer_generation: str,
    producer_currentness_ref: str,
    reviewer_ref: str | None = None,
    reviewer_generation: str | None = None,
    reviewer_currentness_ref: str | None = None,
) -> AuthorityProducerRecordV2:
    """Resolve an exact artifact only against the repository-owned registry.

    Binding only a producer name/generation is insufficient: a caller could copy
    those public identifiers onto a self-created artifact. The exact artifact
    digest is therefore part of the source-owned trust record.
    """
    for record in _CANONICAL_RECORDS:
        if not record.enabled or record.proof_plane != proof_plane:
            continue
        if (
            record.artifact_digest == artifact_digest
            and record.producer_ref == producer_ref
            and record.producer_generation == producer_generation
            and record.producer_currentness_ref == producer_currentness_ref
            and record.reviewer_ref == reviewer_ref
            and record.reviewer_generation == reviewer_generation
            and record.reviewer_currentness_ref == reviewer_currentness_ref
        ):
            return record
    if proof_plane == LIVE_EFFECT_PLANE:
        raise AuthorityRegistryError("LIVE_EFFECT_PRODUCER_TRUST_UNPROVEN")
    if proof_plane == SANITIZER_PLANE:
        raise AuthorityRegistryError("SANITIZER_PRODUCER_TRUST_UNPROVEN")
    raise AuthorityRegistryError("AUTHORITY_PROOF_PLANE_UNREGISTERED", proof_plane)
