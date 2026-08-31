"""Aura external knowledge ingress admission.

D0 / HS1 / NONPROMOTING.

This module normalizes heterogeneous external knowledge into source-resolvable,
versioned hydration cards while keeping retrieval coordinates, currentness,
semantic identity, and effect authority on separate planes.

It intentionally does not fetch network resources. Provider adapters acquire
evidence; this membrane validates and stamps it.

Core laws:
- ExternalSubjectIdentity != ExternalEvidenceGeneration.
- ArtifactObservedAt != SourceSemanticGeneration.
- HydrationLevel != VerificationLevel != ToolUseAuthority.
- CoordinateProjection != SemanticIdentity != EvidenceTruth.
- CacheHit != Currentness != Authority.
- ReadOnlyReference != CodeExecution != ModelDownload != ProviderEffect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


SCHEMA = "AURA-EXTERNAL-KNOWLEDGE-NODE-v1"
SUBJECT_SCHEMA = "AURA-EXTERNAL-SUBJECT-v1"
OBSERVATION_SCHEMA = "AURA-EXTERNAL-OBSERVATION-v1"
VALIDATION_SCHEMA = "AURA-EXTERNAL-VALIDATION-FINGERPRINT-v1"
COORDINATE_SCHEMA = "AURA-EXTERNAL-COORDINATE-PROJECTION-v1"
HYDRATION_SCHEMA = "AURA-EXTERNAL-HYDRATION-v1"

ALLOWED_PROVIDERS = frozenset(
    {
        "ARXIV",
        "CROSSREF",
        "OPENALEX",
        "SEMANTIC_SCHOLAR",
        "GOOGLE_SCHOLAR",
        "GITHUB",
        "HUGGING_FACE",
        "REDDIT",
        "WEB",
        "DATASET",
        "PACKAGE_REGISTRY",
    }
)

ALLOWED_KINDS = frozenset(
    {
        "PAPER",
        "REPOSITORY",
        "MODEL",
        "DATASET",
        "SPACE",
        "TOOLKIT",
        "BENCHMARK",
        "DOCUMENTATION",
        "DISCUSSION",
        "PACKAGE",
        "WEB_PAGE",
    }
)

SECTORS = frozenset({"02_SRC", "04_TRU", "06_RUN", "07_SEC", "08_RSH"})

PROVIDER_INVALIDATORS: dict[str, tuple[str, ...]] = {
    "ARXIV": ("NEW_VERSION", "WITHDRAWAL", "LICENSE_CHANGE"),
    "CROSSREF": ("UPDATED_METADATA", "INDEXED_METADATA_CHANGE", "RETRACTION_UPDATE"),
    "OPENALEX": ("UPDATED_RECORD", "MERGE", "DELETE"),
    "SEMANTIC_SCHOLAR": ("UPDATED_RECORD", "CORPUS_REVISION"),
    "GOOGLE_SCHOLAR": ("DISCOVERY_RESULT_DRIFT", "SOURCE_LINK_CHANGE"),
    "GITHUB": ("NEW_COMMIT", "NEW_RELEASE", "LICENSE_CHANGE", "SECURITY_ADVISORY", "ARCHIVE_STATE_CHANGE"),
    "HUGGING_FACE": ("NEW_COMMIT", "NEW_REVISION", "LICENSE_CHANGE", "GATED_STATE_CHANGE", "SECURITY_SCAN_CHANGE"),
    "REDDIT": ("EDIT", "DELETE", "MODERATION_CHANGE"),
    "WEB": ("ETAG_CHANGE", "LAST_MODIFIED_CHANGE", "CONTENT_DIGEST_CHANGE", "HTTP_GONE"),
    "DATASET": ("REVISION_CHANGE", "LICENSE_CHANGE", "SCHEMA_CHANGE"),
    "PACKAGE_REGISTRY": ("NEW_RELEASE", "YANK", "DEPENDENCY_CHANGE", "SECURITY_ADVISORY"),
}

HEX = frozenset("0123456789abcdef")


class KnowledgeState(str, Enum):
    DISCOVERED_UNVERIFIED = "DISCOVERED_UNVERIFIED"
    SOURCE_RESOLVED = "SOURCE_RESOLVED"
    METADATA_VERIFIED = "METADATA_VERIFIED"
    CONTENT_VERIFIED = "CONTENT_VERIFIED"
    CURRENT_REFERENCE = "CURRENT_REFERENCE"
    STALE_REVERIFY_REQUIRED = "STALE_REVERIFY_REQUIRED"
    INVALIDATED = "INVALIDATED"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _required(value, name)
    if len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def _iso(value: Any, name: str) -> str:
    value = _required(value, name)
    normalized = value.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{name}_MUST_BE_ISO8601") from exc
    if dt.tzinfo is None:
        raise ValueError(f"{name}_MUST_BE_TIMEZONE_AWARE")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _uri(value: Any, name: str) -> str:
    value = _required(value, name)
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https", "git", "doi", "arxiv", "hf"}:
        raise ValueError(f"{name}_UNSUPPORTED_SCHEME")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ValueError(f"{name}_HOST_REQUIRED")
    return value


def _base3_digits(hex_digest: str, count: int) -> tuple[int, ...]:
    n = int(_sha256(hex_digest, "COORDINATE_DIGEST"), 16)
    n %= 3 ** count
    out = [0] * count
    for i in range(count - 1, -1, -1):
        out[i] = n % 3
        n //= 3
    return tuple(out)


def _k27_xyz(hex_digest: str) -> tuple[int, int, int]:
    _sha256(hex_digest, "K27_DIGEST")
    raw = bytes.fromhex(hex_digest[:6])
    return tuple(b % 27 for b in raw)  # type: ignore[return-value]


@dataclass(frozen=True)
class ExternalSubject:
    provider: str
    source_kind: str
    canonical_id: str
    canonical_uri: str
    sector: str

    def validate(self) -> None:
        if self.provider not in ALLOWED_PROVIDERS:
            raise ValueError("EXTERNAL_PROVIDER_UNSUPPORTED")
        if self.source_kind not in ALLOWED_KINDS:
            raise ValueError("EXTERNAL_SOURCE_KIND_UNSUPPORTED")
        _required(self.canonical_id, "CANONICAL_ID")
        _uri(self.canonical_uri, "CANONICAL_URI")
        if self.sector not in SECTORS:
            raise ValueError("EXTERNAL_SECTOR_UNSUPPORTED")

    @property
    def subject_key(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": SUBJECT_SCHEMA,
                "provider": self.provider,
                "source_kind": self.source_kind,
                "canonical_id": self.canonical_id,
            }
        )


@dataclass(frozen=True)
class ExternalObservation:
    provider_revision: str
    content_digest: str
    observed_at: str
    source_generated_at: str
    exact_source_uri: str
    verifier_generation: str
    verified_fields: tuple[str, ...]
    etag: str | None = None
    last_modified: str | None = None
    license_id: str | None = None
    security_flags: tuple[str, ...] = ()
    provider_metadata_digest: str | None = None

    def validate(self) -> None:
        _required(self.provider_revision, "PROVIDER_REVISION")
        _sha256(self.content_digest, "CONTENT_DIGEST")
        observed = _iso(self.observed_at, "OBSERVED_AT")
        generated = _iso(self.source_generated_at, "SOURCE_GENERATED_AT")
        if datetime.fromisoformat(generated.replace("Z", "+00:00")) > datetime.fromisoformat(
            observed.replace("Z", "+00:00")
        ):
            raise ValueError("SOURCE_GENERATION_CANNOT_FOLLOW_OBSERVATION")
        _uri(self.exact_source_uri, "EXACT_SOURCE_URI")
        _required(self.verifier_generation, "VERIFIER_GENERATION")
        if not self.verified_fields:
            raise ValueError("VERIFIED_FIELDS_REQUIRED")
        if tuple(sorted(set(self.verified_fields))) != self.verified_fields:
            raise ValueError("VERIFIED_FIELDS_MUST_BE_CANONICAL")
        if self.provider_metadata_digest is not None:
            _sha256(self.provider_metadata_digest, "PROVIDER_METADATA_DIGEST")
        if tuple(sorted(set(self.security_flags))) != self.security_flags:
            raise ValueError("SECURITY_FLAGS_MUST_BE_CANONICAL")

    def evidence_generation_key(self, *, subject_key: str) -> str:
        self.validate()
        _sha256(subject_key, "SUBJECT_KEY")
        return _sha(
            {
                "domain": OBSERVATION_SCHEMA,
                "subject_key": subject_key,
                "provider_revision": self.provider_revision,
                "content_digest": self.content_digest,
                "source_generated_at": _iso(self.source_generated_at, "SOURCE_GENERATED_AT"),
                "exact_source_uri": self.exact_source_uri,
                "etag": self.etag,
                "last_modified": self.last_modified,
                "license_id": self.license_id,
                "security_flags": self.security_flags,
                "provider_metadata_digest": self.provider_metadata_digest,
                "verifier_generation": self.verifier_generation,
                "verified_fields": self.verified_fields,
            }
        )


@dataclass(frozen=True)
class HydrationPayload:
    level: str
    data: Mapping[str, Any]
    derivation_method: str
    source_excerpt_digest: str | None = None

    def validate(self) -> None:
        if self.level not in {"L0", "L1", "L2", "L3", "L4"}:
            raise ValueError("HYDRATION_LEVEL_INVALID")
        if not isinstance(self.data, Mapping) or not self.data:
            raise ValueError("HYDRATION_DATA_REQUIRED")
        _required(self.derivation_method, "DERIVATION_METHOD")
        if self.source_excerpt_digest is not None:
            _sha256(self.source_excerpt_digest, "SOURCE_EXCERPT_DIGEST")

    @property
    def digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": HYDRATION_SCHEMA,
                "level": self.level,
                "data": self.data,
                "derivation_method": self.derivation_method,
                "source_excerpt_digest": self.source_excerpt_digest,
            }
        )


@dataclass(frozen=True)
class CoordinateProjection:
    scheme: str
    subject_trits_13d: tuple[int, ...]
    evidence_trits_13d: tuple[int, ...]
    k27_xyz: tuple[int, int, int]
    toroidal_xyz_mod27: tuple[int, int, int]
    tesseract_vertex: tuple[int, int, int, int]

    def validate(self) -> None:
        if self.scheme != COORDINATE_SCHEMA:
            raise ValueError("COORDINATE_SCHEME_MISMATCH")
        if len(self.subject_trits_13d) != 13 or any(v not in {0, 1, 2} for v in self.subject_trits_13d):
            raise ValueError("SUBJECT_13D_TRITS_INVALID")
        if len(self.evidence_trits_13d) != 13 or any(v not in {0, 1, 2} for v in self.evidence_trits_13d):
            raise ValueError("EVIDENCE_13D_TRITS_INVALID")
        for xyz in (self.k27_xyz, self.toroidal_xyz_mod27):
            if len(xyz) != 3 or any(v < 0 or v >= 27 for v in xyz):
                raise ValueError("MOD27_COORDINATE_INVALID")
        if len(self.tesseract_vertex) != 4 or any(v not in {0, 1} for v in self.tesseract_vertex):
            raise ValueError("TESSERACT_VERTEX_INVALID")


@dataclass(frozen=True)
class ExternalKnowledgeNode:
    schema: str
    subject: ExternalSubject
    observation: ExternalObservation
    knowledge_state: KnowledgeState
    hydration: tuple[HydrationPayload, ...]
    validation_fingerprint: str
    coordinate: CoordinateProjection
    invalidation_triggers: tuple[str, ...]
    read_only_reference_admissible: bool
    tool_use_requires_separate_admission: bool = True
    code_execution_authorized: bool = False
    model_download_authorized: bool = False
    remote_code_authorized: bool = False
    network_write_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError("EXTERNAL_KNOWLEDGE_SCHEMA_MISMATCH")
        self.subject.validate()
        self.observation.validate()
        if not isinstance(self.knowledge_state, KnowledgeState):
            raise ValueError("KNOWLEDGE_STATE_INVALID")
        if not self.hydration:
            raise ValueError("HYDRATION_REQUIRED")
        levels = tuple(item.level for item in self.hydration)
        expected = tuple(f"L{i}" for i in range(len(levels)))
        if levels != expected:
            raise ValueError("HYDRATION_MUST_BE_CONTIGUOUS_FROM_L0")
        for item in self.hydration:
            item.validate()
        _sha256(self.validation_fingerprint, "VALIDATION_FINGERPRINT")
        self.coordinate.validate()
        if tuple(sorted(set(self.invalidation_triggers))) != self.invalidation_triggers:
            raise ValueError("INVALIDATION_TRIGGERS_MUST_BE_CANONICAL")
        if self.knowledge_state == KnowledgeState.CURRENT_REFERENCE:
            if not self.read_only_reference_admissible:
                raise ValueError("CURRENT_REFERENCE_REQUIRES_READ_ONLY_ADMISSION")
            if "exact_source_uri" not in self.observation.verified_fields:
                raise ValueError("CURRENT_REFERENCE_REQUIRES_VERIFIED_EXACT_SOURCE")
        elif self.read_only_reference_admissible:
            raise ValueError("READ_ONLY_REFERENCE_REQUIRES_CURRENT_REFERENCE")
        forbidden = (
            self.code_execution_authorized,
            self.model_download_authorized,
            self.remote_code_authorized,
            self.network_write_authorized,
            self.provider_effect_authorized,
            self.semantic_k27_authority,
            self.native_private_transformer_kv_accessed,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("INGRESS_CANNOT_MINT_TOOL_OR_EFFECT_AUTHORITY")
        if self.tool_use_requires_separate_admission is not True:
            raise ValueError("TOOL_USE_MUST_REQUIRE_SEPARATE_ADMISSION")

    @property
    def subject_key(self) -> str:
        return self.subject.subject_key

    @property
    def evidence_generation_key(self) -> str:
        return self.observation.evidence_generation_key(subject_key=self.subject_key)

    @property
    def node_digest(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": SCHEMA,
                "subject_key": self.subject_key,
                "evidence_generation_key": self.evidence_generation_key,
                "knowledge_state": self.knowledge_state.value,
                "hydration": [item.digest for item in self.hydration],
                "validation_fingerprint": self.validation_fingerprint,
                "coordinate": asdict(self.coordinate),
                "invalidation_triggers": self.invalidation_triggers,
                "claim_ceiling": {
                    "read_only_reference_admissible": self.read_only_reference_admissible,
                    "tool_use_requires_separate_admission": self.tool_use_requires_separate_admission,
                    "code_execution_authorized": self.code_execution_authorized,
                    "model_download_authorized": self.model_download_authorized,
                    "remote_code_authorized": self.remote_code_authorized,
                    "network_write_authorized": self.network_write_authorized,
                    "provider_effect_authorized": self.provider_effect_authorized,
                    "semantic_k27_authority": self.semantic_k27_authority,
                    "native_private_transformer_kv_accessed": self.native_private_transformer_kv_accessed,
                },
            }
        )


def derive_validation_fingerprint(
    *,
    subject: ExternalSubject,
    observation: ExternalObservation,
    knowledge_state: KnowledgeState,
    hydration: Sequence[HydrationPayload],
    validator_generation: str,
) -> str:
    subject.validate()
    observation.validate()
    _required(validator_generation, "VALIDATOR_GENERATION")
    if not hydration:
        raise ValueError("HYDRATION_REQUIRED")
    for item in hydration:
        item.validate()
    return _sha(
        {
            "domain": VALIDATION_SCHEMA,
            "subject_key": subject.subject_key,
            "evidence_generation_key": observation.evidence_generation_key(subject_key=subject.subject_key),
            "knowledge_state": knowledge_state.value,
            "hydration_digests": [item.digest for item in hydration],
            "validator_generation": validator_generation,
            "verified_fields": observation.verified_fields,
            "authority_ceiling": "READ_ONLY_REFERENCE_ONLY",
        }
    )


def derive_coordinate_projection(
    *,
    subject_key: str,
    evidence_generation_key: str,
    source_verified: bool,
    source_current: bool,
    exact_source_resolvable: bool,
) -> CoordinateProjection:
    _sha256(subject_key, "SUBJECT_KEY")
    _sha256(evidence_generation_key, "EVIDENCE_GENERATION_KEY")
    if any(type(v) is not bool for v in (source_verified, source_current, exact_source_resolvable)):
        raise ValueError("TESSERACT_STATE_BITS_MUST_BE_BOOL")
    k27 = _k27_xyz(subject_key)
    evidence_xyz = _k27_xyz(evidence_generation_key)
    projection = CoordinateProjection(
        scheme=COORDINATE_SCHEMA,
        subject_trits_13d=_base3_digits(subject_key, 13),
        evidence_trits_13d=_base3_digits(evidence_generation_key, 13),
        k27_xyz=k27,
        toroidal_xyz_mod27=(
            (k27[0] + evidence_xyz[0]) % 27,
            (k27[1] + evidence_xyz[1]) % 27,
            (k27[2] + evidence_xyz[2]) % 27,
        ),
        tesseract_vertex=(
            int(source_verified),
            int(source_current),
            int(exact_source_resolvable),
            0,
        ),
    )
    projection.validate()
    return projection


def build_external_knowledge_node(
    *,
    subject: ExternalSubject,
    observation: ExternalObservation,
    knowledge_state: KnowledgeState,
    hydration: Sequence[HydrationPayload],
    validator_generation: str,
) -> ExternalKnowledgeNode:
    subject.validate()
    observation.validate()
    hydration_tuple = tuple(hydration)
    fingerprint = derive_validation_fingerprint(
        subject=subject,
        observation=observation,
        knowledge_state=knowledge_state,
        hydration=hydration_tuple,
        validator_generation=validator_generation,
    )
    is_verified = knowledge_state in {
        KnowledgeState.METADATA_VERIFIED,
        KnowledgeState.CONTENT_VERIFIED,
        KnowledgeState.CURRENT_REFERENCE,
    }
    is_current = knowledge_state == KnowledgeState.CURRENT_REFERENCE
    coordinate = derive_coordinate_projection(
        subject_key=subject.subject_key,
        evidence_generation_key=observation.evidence_generation_key(subject_key=subject.subject_key),
        source_verified=is_verified,
        source_current=is_current,
        exact_source_resolvable="exact_source_uri" in observation.verified_fields,
    )
    node = ExternalKnowledgeNode(
        schema=SCHEMA,
        subject=subject,
        observation=observation,
        knowledge_state=knowledge_state,
        hydration=hydration_tuple,
        validation_fingerprint=fingerprint,
        coordinate=coordinate,
        invalidation_triggers=tuple(sorted(PROVIDER_INVALIDATORS[subject.provider])),
        read_only_reference_admissible=is_current,
    )
    node.validate()
    return node


def classify_refresh(
    *,
    previous: ExternalKnowledgeNode,
    current: ExternalKnowledgeNode,
) -> str:
    previous.validate()
    current.validate()
    if previous.subject_key != current.subject_key:
        return "DIFFERENT_SUBJECT"
    if previous.evidence_generation_key == current.evidence_generation_key:
        return "UNCHANGED_EVIDENCE_GENERATION"
    if previous.observation.content_digest == current.observation.content_digest:
        return "METADATA_OR_VERIFIER_REFRESH"
    return "CONTENT_GENERATION_CHANGED"


LAWS = (
    "ExternalSubjectIdentity!=ExternalEvidenceGeneration",
    "ArtifactObservedAt!=SourceSemanticGeneration",
    "HydrationLevel!=VerificationLevel!=ToolUseAuthority",
    "CoordinateProjection!=SemanticIdentity!=EvidenceTruth",
    "CacheHit!=Currentness!=Authority",
    "ReadOnlyReference!=CodeExecution!=ModelDownload!=ProviderEffect",
    "CoordinateCollisionMustResolveThroughFullSubjectAndEvidenceKeys",
    "StaleSourceRemainsHistoricalButIsNotCurrentUseAdmissible",
    "ToolUseRequiresSeparateOwnerAdmission",
    "NativePrivateTransformerKVAccessed=false",
)
