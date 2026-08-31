#!/usr/bin/env python3
"""Exact legacy-EKI -> current-EKI external-subject identity bridge.

This relation exists because the two proven EKI generations use different identity
schemas:

* legacy EKI / EKI-2: semantic_id = H(domain, legacy SourceKind, canonical_id)
* current EKI: subject_key = H(domain, provider, current source_kind, canonical_id)

The bridge does not choose a current version, compare source/evidence generations,
prove source currentness, or grant write/read/effect authority.  It only proves that
two independently formed identity projections name the same canonical external
subject under one explicit versioned vocabulary mapping.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any

SCHEMA = "AURA-EKI-LEGACY-CURRENT-SUBJECT-IDENTITY-BRIDGE-v1"
LEGACY_ID_DOMAIN = "AURA-EKI-EXTERNAL-SEMANTIC-ID-v1"
CURRENT_ID_DOMAIN = "AURA-EXTERNAL-SUBJECT-v1"
MAPPING_SCHEMA = "AURA-EKI-LEGACY-CURRENT-VOCABULARY-MAP-v1"
HEX = frozenset("0123456789abcdef")

# Exact mapping between the source-kind vocabulary owned by the EKI-2/legacy
# parent and the provider + source-kind split owned by the current EKI parent.
# Classification fields that were never identity-bearing in the parent remain
# outside this table.
VOCABULARY_MAP: dict[str, tuple[str, str]] = {
    "ARXIV": ("ARXIV", "PAPER"),
    "GITHUB": ("GITHUB", "REPOSITORY"),
    "HUGGINGFACE_MODEL": ("HUGGING_FACE", "MODEL"),
    "HUGGINGFACE_DATASET": ("HUGGING_FACE", "DATASET"),
    "HUGGINGFACE_SPACE": ("HUGGING_FACE", "SPACE"),
    "GOOGLE_SCHOLAR_DISCOVERY": ("GOOGLE_SCHOLAR", "PAPER"),
    "REDDIT": ("REDDIT", "DISCUSSION"),
    "WEB": ("WEB", "WEB_PAGE"),
}


class IdentityBridgeDisposition(str, Enum):
    MATCHED_SUBJECT = "MATCHED_SUBJECT"
    HOLD_UNSUPPORTED_LEGACY_KIND = "HOLD_UNSUPPORTED_LEGACY_KIND"
    HOLD_VOCABULARY_MAPPING_MISMATCH = "HOLD_VOCABULARY_MAPPING_MISMATCH"
    HOLD_CANONICAL_ID_MISMATCH = "HOLD_CANONICAL_ID_MISMATCH"
    HOLD_CANONICAL_URI_MISMATCH = "HOLD_CANONICAL_URI_MISMATCH"
    HOLD_LEGACY_IDENTITY_DIGEST_MISMATCH = "HOLD_LEGACY_IDENTITY_DIGEST_MISMATCH"
    HOLD_CURRENT_IDENTITY_DIGEST_MISMATCH = "HOLD_CURRENT_IDENTITY_DIGEST_MISMATCH"


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _text(value, name).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def legacy_semantic_id(*, source_kind: str, canonical_id: str) -> str:
    return _sha(
        {
            "domain": LEGACY_ID_DOMAIN,
            "source_kind": _text(source_kind, "LEGACY_SOURCE_KIND"),
            "canonical_id": _text(canonical_id, "CANONICAL_ID"),
        }
    )


def current_subject_key(*, provider: str, source_kind: str, canonical_id: str) -> str:
    return _sha(
        {
            "domain": CURRENT_ID_DOMAIN,
            "provider": _text(provider, "CURRENT_PROVIDER"),
            "source_kind": _text(source_kind, "CURRENT_SOURCE_KIND"),
            "canonical_id": _text(canonical_id, "CANONICAL_ID"),
        }
    )


@dataclass(frozen=True)
class LegacyExternalIdentityProjectionV1:
    source_kind: str
    canonical_id: str
    canonical_uri: str
    semantic_id: str
    artifact_class: str | None = None
    source_generation_id: str | None = None

    def validate(self) -> None:
        _text(self.source_kind, "LEGACY_SOURCE_KIND")
        _text(self.canonical_id, "LEGACY_CANONICAL_ID")
        _text(self.canonical_uri, "LEGACY_CANONICAL_URI")
        _sha256(self.semantic_id, "LEGACY_SEMANTIC_ID")
        if self.artifact_class is not None:
            _text(self.artifact_class, "LEGACY_ARTIFACT_CLASS")
        if self.source_generation_id is not None:
            _sha256(self.source_generation_id, "LEGACY_SOURCE_GENERATION_ID")


@dataclass(frozen=True)
class CurrentExternalSubjectProjectionV1:
    provider: str
    source_kind: str
    canonical_id: str
    canonical_uri: str
    subject_key: str
    sector: str | None = None
    evidence_generation_key: str | None = None

    def validate(self) -> None:
        _text(self.provider, "CURRENT_PROVIDER")
        _text(self.source_kind, "CURRENT_SOURCE_KIND")
        _text(self.canonical_id, "CURRENT_CANONICAL_ID")
        _text(self.canonical_uri, "CURRENT_CANONICAL_URI")
        _sha256(self.subject_key, "CURRENT_SUBJECT_KEY")
        if self.sector is not None:
            _text(self.sector, "CURRENT_SECTOR")
        if self.evidence_generation_key is not None:
            _sha256(self.evidence_generation_key, "CURRENT_EVIDENCE_GENERATION_KEY")


@dataclass(frozen=True)
class ExternalSubjectIdentityBridgeReceiptV1:
    disposition: IdentityBridgeDisposition
    reason_code: str
    mapping_schema: str
    mapping_rule: str | None
    canonical_id: str | None
    canonical_uri: str | None
    legacy_source_kind: str
    legacy_semantic_id: str
    current_provider: str
    current_source_kind: str
    current_subject_key: str
    legacy_source_generation_id: str | None
    current_evidence_generation_key: str | None
    same_external_subject: bool
    version_equivalence_proven: bool = False
    generation_equivalence_proven: bool = False
    current_version_selected: bool = False
    source_currentness_proven: bool = False
    record_currentness_proven: bool = False
    semantic_truth_granted: bool = False
    write_authority: bool = False
    read_authority: bool = False
    effect_authority: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    schema: str = SCHEMA

    def validate(self) -> None:
        if not isinstance(self.disposition, IdentityBridgeDisposition):
            raise ValueError("IDENTITY_BRIDGE_DISPOSITION_MUST_BE_TYPED")
        _text(self.reason_code, "REASON_CODE")
        if self.mapping_schema != MAPPING_SCHEMA:
            raise ValueError("MAPPING_SCHEMA_MISMATCH")
        if self.mapping_rule is not None:
            _text(self.mapping_rule, "MAPPING_RULE")
        _text(self.legacy_source_kind, "LEGACY_SOURCE_KIND")
        _sha256(self.legacy_semantic_id, "LEGACY_SEMANTIC_ID")
        _text(self.current_provider, "CURRENT_PROVIDER")
        _text(self.current_source_kind, "CURRENT_SOURCE_KIND")
        _sha256(self.current_subject_key, "CURRENT_SUBJECT_KEY")
        if self.canonical_id is not None:
            _text(self.canonical_id, "CANONICAL_ID")
        if self.canonical_uri is not None:
            _text(self.canonical_uri, "CANONICAL_URI")
        if self.legacy_source_generation_id is not None:
            _sha256(self.legacy_source_generation_id, "LEGACY_SOURCE_GENERATION_ID")
        if self.current_evidence_generation_key is not None:
            _sha256(self.current_evidence_generation_key, "CURRENT_EVIDENCE_GENERATION_KEY")
        if type(self.same_external_subject) is not bool:
            raise ValueError("SAME_EXTERNAL_SUBJECT_MUST_BE_BOOL")
        for field in (
            "version_equivalence_proven",
            "generation_equivalence_proven",
            "current_version_selected",
            "source_currentness_proven",
            "record_currentness_proven",
            "semantic_truth_granted",
            "write_authority",
            "read_authority",
            "effect_authority",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
        ):
            if getattr(self, field) is not False:
                raise ValueError(f"{field.upper()}_MUST_REMAIN_FALSE")
        if self.disposition is IdentityBridgeDisposition.MATCHED_SUBJECT:
            if self.same_external_subject is not True:
                raise ValueError("MATCHED_SUBJECT_REQUIRES_SUBJECT_RELATION")
            if self.mapping_rule is None or self.canonical_id is None or self.canonical_uri is None:
                raise ValueError("MATCHED_SUBJECT_REQUIRES_EXACT_MAPPING_AND_CANONICAL_COORDINATES")
        elif self.same_external_subject is not False:
            raise ValueError("HOLD_CANNOT_ASSERT_SUBJECT_EQUIVALENCE")
        if self.schema != SCHEMA:
            raise ValueError("IDENTITY_BRIDGE_SCHEMA_MISMATCH")

    @property
    def receipt_digest(self) -> str:
        self.validate()
        return _sha({"domain": SCHEMA, "receipt": asdict(self)})


def bridge_external_subject_identity(
    *,
    legacy: LegacyExternalIdentityProjectionV1,
    current: CurrentExternalSubjectProjectionV1,
) -> ExternalSubjectIdentityBridgeReceiptV1:
    legacy.validate()
    current.validate()

    base = dict(
        mapping_schema=MAPPING_SCHEMA,
        legacy_source_kind=legacy.source_kind,
        legacy_semantic_id=legacy.semantic_id,
        current_provider=current.provider,
        current_source_kind=current.source_kind,
        current_subject_key=current.subject_key,
        legacy_source_generation_id=legacy.source_generation_id,
        current_evidence_generation_key=current.evidence_generation_key,
    )

    def hold(disposition: IdentityBridgeDisposition, reason: str) -> ExternalSubjectIdentityBridgeReceiptV1:
        receipt = ExternalSubjectIdentityBridgeReceiptV1(
            disposition=disposition,
            reason_code=reason,
            mapping_rule=None,
            canonical_id=None,
            canonical_uri=None,
            same_external_subject=False,
            **base,
        )
        receipt.validate()
        return receipt

    expected_legacy = legacy_semantic_id(
        source_kind=legacy.source_kind,
        canonical_id=legacy.canonical_id,
    )
    if legacy.semantic_id != expected_legacy:
        return hold(
            IdentityBridgeDisposition.HOLD_LEGACY_IDENTITY_DIGEST_MISMATCH,
            "LEGACY_SEMANTIC_ID_DOES_NOT_MATCH_EXACT_PARENT_RECIPE",
        )

    expected_current = current_subject_key(
        provider=current.provider,
        source_kind=current.source_kind,
        canonical_id=current.canonical_id,
    )
    if current.subject_key != expected_current:
        return hold(
            IdentityBridgeDisposition.HOLD_CURRENT_IDENTITY_DIGEST_MISMATCH,
            "CURRENT_SUBJECT_KEY_DOES_NOT_MATCH_EXACT_PARENT_RECIPE",
        )

    mapped = VOCABULARY_MAP.get(legacy.source_kind)
    if mapped is None:
        return hold(
            IdentityBridgeDisposition.HOLD_UNSUPPORTED_LEGACY_KIND,
            "NO_VERSIONED_VOCABULARY_MAPPING_FOR_LEGACY_SOURCE_KIND",
        )
    if mapped != (current.provider, current.source_kind):
        return hold(
            IdentityBridgeDisposition.HOLD_VOCABULARY_MAPPING_MISMATCH,
            "LEGACY_SOURCE_KIND_DOES_NOT_MAP_TO_CURRENT_PROVIDER_AND_KIND",
        )
    if legacy.canonical_id != current.canonical_id:
        return hold(
            IdentityBridgeDisposition.HOLD_CANONICAL_ID_MISMATCH,
            "CANONICAL_ID_MUST_MATCH_EXACTLY_ACROSS_IDENTITY_GENERATIONS",
        )
    if legacy.canonical_uri != current.canonical_uri:
        return hold(
            IdentityBridgeDisposition.HOLD_CANONICAL_URI_MISMATCH,
            "CANONICAL_URI_MUST_MATCH_EXACTLY_ACROSS_IDENTITY_GENERATIONS",
        )

    mapping_rule = f"{legacy.source_kind}->{current.provider}+{current.source_kind}"
    receipt = ExternalSubjectIdentityBridgeReceiptV1(
        disposition=IdentityBridgeDisposition.MATCHED_SUBJECT,
        reason_code="EXACT_PARENT_IDENTITY_RECIPES_AND_VERSIONED_VOCABULARY_COMMUTE",
        mapping_schema=MAPPING_SCHEMA,
        mapping_rule=mapping_rule,
        canonical_id=legacy.canonical_id,
        canonical_uri=legacy.canonical_uri,
        legacy_source_kind=legacy.source_kind,
        legacy_semantic_id=legacy.semantic_id,
        current_provider=current.provider,
        current_source_kind=current.source_kind,
        current_subject_key=current.subject_key,
        legacy_source_generation_id=legacy.source_generation_id,
        current_evidence_generation_key=current.evidence_generation_key,
        same_external_subject=True,
    )
    receipt.validate()
    return receipt


LAWS = (
    "LegacySemanticID!=CurrentSubjectKey",
    "LegacyVocabulary!=CurrentProviderKindVocabulary",
    "VocabularyMapping+CanonicalCoordinates+ExactParentDigests=>SubjectRelationOnly",
    "SameExternalSubject!=SameGeneration!=SameVersion",
    "SubjectIdentityBridge!=CurrentVersionSelection",
    "SubjectIdentityBridge!=SourceCurrentness",
    "K27Coordinate!=CrossSchemaIdentityProof",
    "IdentityRelation!=WriteAuthority!=ReadAuthority!=EffectAuthority",
)
