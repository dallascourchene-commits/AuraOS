"""Source-owned trust registry for BugHound authority-bearing proof planes.

This is intentionally a *hold* registry. The canonical source generation exists,
but no live-effect or sanitizer producer is currently registered. A caller
cannot create trust by passing an expected digest/ref/generation alongside the
artifact it also created. Promotion requires a repository-owned registry update
on this proof plane followed by exact-current verification.

The registry is D0 metadata only and grants no external effect by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "BugHoundAuthorityRegistryV1"
REGISTRY_GENERATION = "BUGHOUND_AUTHORITY_REGISTRY_HOLD_V1"
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
class AuthorityProducerRecordV1:
    proof_plane: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    reviewer_ref: str | None = None
    reviewer_generation: str | None = None
    reviewer_currentness_ref: str | None = None
    enabled: bool = True
    authority: bool = False
    schema: str = "AuthorityProducerRecordV1"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_AUTHORITY_PRODUCER_RECORD_V1", asdict(self))


# Canonical source-owned records. Deliberately empty until an independently
# owned producer/currentness lane is explicitly registered in repository source.
# Tests may verify the hold, but canonical admission never accepts a caller-
# supplied registry object or caller-supplied expected producer identity.
_CANONICAL_RECORDS: tuple[AuthorityProducerRecordV1, ...] = ()


@dataclass(frozen=True)
class AuthorityRegistryReceiptV1:
    registry_generation: str
    record_digests: tuple[str, ...]
    live_effect_producer_count: int
    sanitizer_producer_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_AUTHORITY_REGISTRY_V1", asdict(self))


def authority_registry_receipt() -> AuthorityRegistryReceiptV1:
    records = tuple(sorted(_CANONICAL_RECORDS, key=lambda record: record.record_digest))
    return AuthorityRegistryReceiptV1(
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
    producer_ref: str,
    producer_generation: str,
    producer_currentness_ref: str,
    reviewer_ref: str | None = None,
    reviewer_generation: str | None = None,
    reviewer_currentness_ref: str | None = None,
) -> AuthorityProducerRecordV1:
    """Resolve only against the repository-owned canonical registry.

    No registry, expected digest, producer ref, or reviewer identity is accepted
    from a caller as an alternate trust root.
    """
    for record in _CANONICAL_RECORDS:
        if not record.enabled or record.proof_plane != proof_plane:
            continue
        if (
            record.producer_ref == producer_ref
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
