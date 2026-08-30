"""Source-owned trust registry for BugHound authority-bearing proof planes.

This is intentionally a *hold* registry. The canonical source generation exists,
but no live-effect or sanitizer artifact is currently registered. A caller
cannot create trust by supplying an expected digest/ref/generation alongside an
artifact it also created. Promotion requires a repository-owned record for the
exact artifact digest plus producer/currentness (and reviewer, when required),
followed by exact-current verification.

The registry is D0 metadata only and grants no external effect by itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import string

SCHEMA = "BugHoundAuthorityRegistryV2"
REGISTRY_GENERATION = "BUGHOUND_AUTHORITY_REGISTRY_HOLD_V2"
LIVE_EFFECT_PLANE = "LIVE_EFFECT_GRANT"
SANITIZER_PLANE = "SANITIZED_PATTERN"
_RECORD_SCHEMA = "AuthorityProducerRecordV2"
_PROOF_PLANES = frozenset({LIVE_EFFECT_PLANE, SANITIZER_PLANE})


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


def _required_text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityRegistryError(code)
    return value.strip()


def _optional_text(value: object, code: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, code)


def _sha256_hex(value: object) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_ARTIFACT_DIGEST_INVALID")
    if value != value.lower() or any(ch not in string.hexdigits.lower() for ch in value):
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_ARTIFACT_DIGEST_INVALID")
    return value


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
    schema: str = _RECORD_SCHEMA

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_AUTHORITY_PRODUCER_RECORD_V2", asdict(self))


# Backward import compatibility only. Semantics are V2: exact artifact digest is
# mandatory for every source-owned trust record.
AuthorityProducerRecordV1 = AuthorityProducerRecordV2


# Canonical source-owned records. Deliberately empty until an independently
# owned producer/currentness lane explicitly registers one exact artifact.
# Tests may patch this private tuple to exercise the consumer, but production
# APIs never accept a caller-supplied registry or expected producer identity.
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


AuthorityRegistryReceiptV1 = AuthorityRegistryReceiptV2


def _validate_record(record: object) -> AuthorityProducerRecordV2:
    """Fail closed on malformed or authority-widened canonical trust records."""
    if not isinstance(record, AuthorityProducerRecordV2):
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_RECORD_TYPE_INVALID")
    if record.schema != _RECORD_SCHEMA:
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_RECORD_SCHEMA_MISMATCH")
    if record.proof_plane not in _PROOF_PLANES:
        raise AuthorityRegistryError("AUTHORITY_PROOF_PLANE_UNREGISTERED", str(record.proof_plane))

    _sha256_hex(record.artifact_digest)
    _required_text(record.producer_ref, "AUTHORITY_REGISTRY_PRODUCER_REF_REQUIRED")
    _required_text(record.producer_generation, "AUTHORITY_REGISTRY_PRODUCER_GENERATION_REQUIRED")
    _required_text(record.producer_currentness_ref, "AUTHORITY_REGISTRY_PRODUCER_CURRENTNESS_REQUIRED")

    if type(record.enabled) is not bool:
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_ENABLED_FLAG_INVALID")
    if type(record.authority) is not bool or record.authority is not False:
        raise AuthorityRegistryError("AUTHORITY_REGISTRY_AUTHORITY_WIDENING")

    reviewer_values = (
        _optional_text(record.reviewer_ref, "AUTHORITY_REGISTRY_REVIEWER_REF_INVALID"),
        _optional_text(record.reviewer_generation, "AUTHORITY_REGISTRY_REVIEWER_GENERATION_INVALID"),
        _optional_text(
            record.reviewer_currentness_ref,
            "AUTHORITY_REGISTRY_REVIEWER_CURRENTNESS_INVALID",
        ),
    )
    if record.proof_plane == LIVE_EFFECT_PLANE and any(value is not None for value in reviewer_values):
        raise AuthorityRegistryError("LIVE_EFFECT_REVIEWER_FIELDS_FORBIDDEN")
    if record.proof_plane == SANITIZER_PLANE and any(value is None for value in reviewer_values):
        raise AuthorityRegistryError("SANITIZER_REVIEWER_FIELDS_REQUIRED")
    return record


def _validated_records() -> tuple[AuthorityProducerRecordV2, ...]:
    return tuple(_validate_record(record) for record in _CANONICAL_RECORDS)


def authority_registry_receipt() -> AuthorityRegistryReceiptV2:
    records = tuple(sorted(_validated_records(), key=lambda record: record.record_digest))
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
    """Resolve an exact consequence artifact against validated repository-owned state.

    Producer identity by itself is insufficient because those identifiers are
    public and copyable. The source-owned record must bind the exact artifact
    digest consumed at the consequence boundary. Canonical registry records are
    themselves validated before they can become a trust root.
    """
    if proof_plane not in _PROOF_PLANES:
        raise AuthorityRegistryError("AUTHORITY_PROOF_PLANE_UNREGISTERED", proof_plane)
    _sha256_hex(artifact_digest)
    _required_text(producer_ref, "AUTHORITY_REGISTRY_PRODUCER_REF_REQUIRED")
    _required_text(producer_generation, "AUTHORITY_REGISTRY_PRODUCER_GENERATION_REQUIRED")
    _required_text(producer_currentness_ref, "AUTHORITY_REGISTRY_PRODUCER_CURRENTNESS_REQUIRED")

    records = _validated_records()
    for record in records:
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
    raise AuthorityRegistryError("SANITIZER_PRODUCER_TRUST_UNPROVEN")
