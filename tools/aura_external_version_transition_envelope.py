#!/usr/bin/env python3
"""EKI-4: versioned admission/read obligation envelope.

D0 / HS1 / NONPROMOTING.

This module closes one narrow relation between two independently authored Arena
artifacts:

* PR #738 proves that a changed evidence generation under one stable subject K
  cannot be losslessly superseded by aura-coordinate-memory-kv-v1's unique-K
  representation.  It must HOLD rather than overwrite history.
* PR #737 proves that persisted CURRENT_REFERENCE/current-at-write cannot pay a
  future read-time source-currentness debt.

EKI-4 does not mutate a store.  It translates an independently admitted stable-
subject transition into the already-existing EKI-2 versioned record-key model,
binds an explicit predecessor -> successor edge, and carries the independent
future read-currentness obligation alongside it.

Identity/generation domains remain separate:
CurrentSubjectKey != CurrentEvidenceGenerationKey != LegacySemanticId
                  != EKI2RecordGeneration.

K27 / 13D coordinates are routing/reopen memory only.  Native/private/provider
transformer KV is neither accessed nor represented here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Mapping


SCHEMA = "AURA-EKI4-VERSION-TRANSITION-ENVELOPE-v1"
CURRENT_SUBJECT_DOMAIN = "AURA-EXTERNAL-SUBJECT-v1"
CURRENT_OBSERVATION_DOMAIN = "AURA-EXTERNAL-OBSERVATION-v1"
LEGACY_SEMANTIC_DOMAIN = "AURA-EKI-EXTERNAL-SEMANTIC-ID-v1"
VERSIONED_KEY_PREFIX = "external-cognition://"

PR738_HEAD = "906653a807f54b343d644b1764c7ef37bbbf7191"
PR738_BLOB = "367f29e04e33641d319a3daa1efd7a60b7860d07"
PR737_HEAD = "55ae020ae1c06501935a45f3ade45eeff532d905"
PR737_BLOB = "7dfaaf755a802e0a20a23ce06ba520fe47028f56"
EKI3_SEMANTIC_HEAD = "923edcf63187e14d771528cb08083d6a0467c87d"
EKI2_SEMANTIC_HEAD = "b13ba81aa671693828e4fd97bd5b222db5d49d94"

PR738_REQUIRED_HOLD = "HOLD_SUPERSESSION_REPRESENTATION_REQUIRED"
PR737_REQUIRED_AXES = ("source",)
EKI2_REQUIRED_AXES = ("SOURCE_GENERATION_CURRENT", "SOURCE_BODY_CURRENT")
HEX = frozenset("0123456789abcdef")

LEGACY_TO_CURRENT_SUBJECT_TYPE: Mapping[str, tuple[str, str]] = {
    "ARXIV": ("ARXIV", "PAPER"),
    "GITHUB": ("GITHUB", "REPOSITORY"),
    "HUGGINGFACE_MODEL": ("HUGGING_FACE", "MODEL"),
    "HUGGINGFACE_DATASET": ("HUGGING_FACE", "DATASET"),
    "HUGGINGFACE_SPACE": ("HUGGING_FACE", "SPACE"),
    "GOOGLE_SCHOLAR_DISCOVERY": ("GOOGLE_SCHOLAR", "PAPER"),
    "REDDIT": ("REDDIT", "DISCUSSION"),
    "WEB": ("WEB", "WEB_PAGE"),
}


class EnvelopeDisposition(str, Enum):
    VERSION_TRANSITION_PLAN_READY = "VERSION_TRANSITION_PLAN_READY"
    WRITE_CURRENTNESS_REQUIRED = "WRITE_CURRENTNESS_REQUIRED"
    READ_OBLIGATION_REQUIRED = "READ_OBLIGATION_REQUIRED"
    IDENTITY_BRIDGE_HOLD = "IDENTITY_BRIDGE_HOLD"
    GENERATION_BINDING_HOLD = "GENERATION_BINDING_HOLD"
    SUPERSESSION_EDGE_REQUIRED = "SUPERSESSION_EDGE_REQUIRED"
    REPRESENTATION_OWNER_HOLD = "REPRESENTATION_OWNER_HOLD"
    STORE_INTEGRITY_HOLD = "STORE_INTEGRITY_HOLD"
    WRONG_RESPONSIBILITY_OWNER = "WRONG_RESPONSIBILITY_OWNER"


class EnvelopeError(ValueError):
    pass


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


def _required(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeError(f"{name}_REQUIRED")
    return value.strip()


def _sha256(value: Any, name: str) -> str:
    value = _required(value, name).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise EnvelopeError(f"{name}_MUST_BE_SHA256_HEX")
    return value


def current_subject_key(*, provider: str, source_kind: str, canonical_id: str) -> str:
    return _sha(
        {
            "domain": CURRENT_SUBJECT_DOMAIN,
            "provider": _required(provider, "PROVIDER"),
            "source_kind": _required(source_kind, "SOURCE_KIND"),
            "canonical_id": _required(canonical_id, "CANONICAL_ID"),
        }
    )


def current_evidence_generation_key(
    *,
    subject_key: str,
    provider_revision: str,
    content_digest: str,
    source_generated_at: str,
    exact_source_uri: str,
    verifier_generation: str,
    verified_fields: tuple[str, ...],
    etag: str | None = None,
    last_modified: str | None = None,
    license_id: str | None = None,
    security_flags: tuple[str, ...] = (),
    provider_metadata_digest: str | None = None,
) -> str:
    subject_key = _sha256(subject_key, "SUBJECT_KEY")
    content_digest = _sha256(content_digest, "CONTENT_DIGEST")
    if provider_metadata_digest is not None:
        provider_metadata_digest = _sha256(provider_metadata_digest, "PROVIDER_METADATA_DIGEST")
    if not verified_fields or tuple(sorted(set(verified_fields))) != verified_fields:
        raise EnvelopeError("VERIFIED_FIELDS_MUST_BE_NONEMPTY_CANONICAL")
    if tuple(sorted(set(security_flags))) != security_flags:
        raise EnvelopeError("SECURITY_FLAGS_MUST_BE_CANONICAL")
    return _sha(
        {
            "domain": CURRENT_OBSERVATION_DOMAIN,
            "subject_key": subject_key,
            "provider_revision": _required(provider_revision, "PROVIDER_REVISION"),
            "content_digest": content_digest,
            "source_generated_at": _required(source_generated_at, "SOURCE_GENERATED_AT"),
            "exact_source_uri": _required(exact_source_uri, "EXACT_SOURCE_URI"),
            "etag": etag,
            "last_modified": last_modified,
            "license_id": license_id,
            "security_flags": security_flags,
            "provider_metadata_digest": provider_metadata_digest,
            "verifier_generation": _required(verifier_generation, "VERIFIER_GENERATION"),
            "verified_fields": verified_fields,
        }
    )


def legacy_semantic_id(*, legacy_source_kind: str, canonical_id: str) -> str:
    return _sha(
        {
            "domain": LEGACY_SEMANTIC_DOMAIN,
            "source_kind": _required(legacy_source_kind, "LEGACY_SOURCE_KIND"),
            "canonical_id": _required(canonical_id, "CANONICAL_ID"),
        }
    )


def versioned_record_key(*, legacy_id: str, record_generation: str) -> str:
    return (
        VERSIONED_KEY_PREFIX
        + _sha256(legacy_id, "LEGACY_SEMANTIC_ID")
        + "/record/"
        + _sha256(record_generation, "RECORD_GENERATION")
    )


@dataclass(frozen=True)
class CurrentEvidenceDescriptorV1:
    provider: str
    source_kind: str
    canonical_id: str
    canonical_uri: str
    provider_revision: str
    content_digest: str
    source_generated_at: str
    exact_source_uri: str
    verifier_generation: str
    verified_fields: tuple[str, ...]
    claimed_subject_key: str
    claimed_evidence_generation_key: str
    etag: str | None = None
    last_modified: str | None = None
    license_id: str | None = None
    security_flags: tuple[str, ...] = ()
    provider_metadata_digest: str | None = None

    def validate(self) -> None:
        _required(self.canonical_uri, "CANONICAL_URI")
        expected_subject = current_subject_key(
            provider=self.provider,
            source_kind=self.source_kind,
            canonical_id=self.canonical_id,
        )
        if _sha256(self.claimed_subject_key, "CLAIMED_SUBJECT_KEY") != expected_subject:
            raise EnvelopeError("CURRENT_SUBJECT_KEY_MISMATCH")
        expected_evidence = current_evidence_generation_key(
            subject_key=expected_subject,
            provider_revision=self.provider_revision,
            content_digest=self.content_digest,
            source_generated_at=self.source_generated_at,
            exact_source_uri=self.exact_source_uri,
            verifier_generation=self.verifier_generation,
            verified_fields=self.verified_fields,
            etag=self.etag,
            last_modified=self.last_modified,
            license_id=self.license_id,
            security_flags=self.security_flags,
            provider_metadata_digest=self.provider_metadata_digest,
        )
        if _sha256(self.claimed_evidence_generation_key, "CLAIMED_EVIDENCE_GENERATION_KEY") != expected_evidence:
            raise EnvelopeError("CURRENT_EVIDENCE_GENERATION_KEY_MISMATCH")


@dataclass(frozen=True)
class VersionedRowBindingV1:
    key: str
    record_generation: str
    legacy_semantic_id: str
    canonical_id: str
    canonical_uri: str
    successor: str | None

    def validate(self, *, legacy_source_kind: str) -> None:
        expected_legacy = legacy_semantic_id(
            legacy_source_kind=legacy_source_kind,
            canonical_id=self.canonical_id,
        )
        if _sha256(self.legacy_semantic_id, "ROW_LEGACY_SEMANTIC_ID") != expected_legacy:
            raise EnvelopeError("ROW_LEGACY_SEMANTIC_ID_MISMATCH")
        expected_key = versioned_record_key(
            legacy_id=expected_legacy,
            record_generation=self.record_generation,
        )
        if self.key != expected_key:
            raise EnvelopeError("VERSIONED_RECORD_KEY_MISMATCH")
        _required(self.canonical_uri, "ROW_CANONICAL_URI")
        if self.successor is not None:
            _required(self.successor, "ROW_SUCCESSOR")


@dataclass(frozen=True)
class WriteAdmissionWitnessV1:
    pr738_head: str
    pr738_blob: str
    stable_subject_disposition: str
    subject_key: str
    proposed_evidence_generation_key: str
    store_ref: str
    store_generation: str
    store_sha256: str
    proposed_source_current: bool
    observed_store_current: bool
    independently_resolved: bool
    authority: bool = False
    write_effect_authorized: bool = False

    def validate(self) -> None:
        if self.pr738_head != PR738_HEAD or self.pr738_blob != PR738_BLOB:
            raise EnvelopeError("PR738_PARENT_GENERATION_MISMATCH")
        if self.stable_subject_disposition != PR738_REQUIRED_HOLD:
            raise EnvelopeError("PR738_STABLE_KEY_REPRESENTATION_HOLD_REQUIRED")
        _sha256(self.subject_key, "WRITE_SUBJECT_KEY")
        _sha256(self.proposed_evidence_generation_key, "WRITE_EVIDENCE_GENERATION_KEY")
        _required(self.store_ref, "STORE_REF")
        _required(self.store_generation, "STORE_GENERATION")
        _sha256(self.store_sha256, "STORE_SHA256")
        if self.proposed_source_current is not True or self.observed_store_current is not True:
            raise EnvelopeError("WRITE_CURRENTNESS_REQUIRED")
        if self.independently_resolved is not True:
            raise EnvelopeError("WRITE_CURRENTNESS_MUST_BE_INDEPENDENTLY_RESOLVED")
        if self.authority is not False or self.write_effect_authorized is not False:
            raise EnvelopeError("WRITE_WITNESS_CANNOT_MINT_AUTHORITY")


@dataclass(frozen=True)
class FutureReadObligationV1:
    pr737_head: str
    pr737_blob: str
    required_guard_axes: tuple[str, ...]
    required_eki2_axes: tuple[str, ...]
    persisted_currentness_is_witness: bool
    resolve_at_read_required: bool

    def validate(self) -> None:
        if self.pr737_head != PR737_HEAD or self.pr737_blob != PR737_BLOB:
            raise EnvelopeError("PR737_PARENT_GENERATION_MISMATCH")
        if self.required_guard_axes != PR737_REQUIRED_AXES:
            raise EnvelopeError("PR737_SOURCE_READ_AXIS_REQUIRED")
        if self.required_eki2_axes != EKI2_REQUIRED_AXES:
            raise EnvelopeError("EKI2_READ_CURRENTNESS_AXES_REQUIRED")
        if self.persisted_currentness_is_witness is not False:
            raise EnvelopeError("PERSISTED_CURRENTNESS_CANNOT_BE_READ_WITNESS")
        if self.resolve_at_read_required is not True:
            raise EnvelopeError("READ_CURRENTNESS_REVALIDATION_REQUIRED")


@dataclass(frozen=True)
class VersionTransitionRequestV1:
    legacy_source_kind: str
    evidence: CurrentEvidenceDescriptorV1
    predecessor: VersionedRowBindingV1
    successor: VersionedRowBindingV1
    write_witness: WriteAdmissionWitnessV1
    future_read: FutureReadObligationV1
    expected_store_ref: str
    expected_store_generation: str
    expected_store_sha256: str
    responsibility: str = "SOURCE_BOUND_COORDINATE_MEMORY"


@dataclass(frozen=True)
class VersionTransitionEnvelopeV1:
    disposition: EnvelopeDisposition
    request_digest: str
    receipt_digest: str
    current_subject_key: str | None
    current_evidence_generation_key: str | None
    legacy_semantic_id: str | None
    predecessor_record_key: str | None
    successor_record_key: str | None
    predecessor_record_generation: str | None
    successor_record_generation: str | None
    explicit_supersession_edge: tuple[str, str] | None
    write_currentness_resolved: bool
    read_currentness_debt_carried: bool
    required_future_read_axes: tuple[str, ...]
    required_eki2_read_axes: tuple[str, ...]
    refusal_reason: str | None = None
    candidate_only: bool = True
    store_mutated: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_truth_granted: bool = False
    semantic_k27_authority: bool = False
    chronological_order_inferred: bool = False
    persisted_currentness_is_witness: bool = False
    native_private_transformer_kv_accessed: bool = False


def _receipt(
    request: VersionTransitionRequestV1,
    disposition: EnvelopeDisposition,
    *,
    subject_key: str | None = None,
    evidence_key: str | None = None,
    legacy_id: str | None = None,
    refusal_reason: str | None = None,
    ready: bool = False,
) -> VersionTransitionEnvelopeV1:
    request_digest = _sha({"domain": SCHEMA, "request": asdict(request)})
    edge = (request.predecessor.key, request.successor.key) if ready else None
    payload = {
        "disposition": disposition.value,
        "request_digest": request_digest,
        "current_subject_key": subject_key,
        "current_evidence_generation_key": evidence_key,
        "legacy_semantic_id": legacy_id,
        "predecessor_record_key": request.predecessor.key if ready else None,
        "successor_record_key": request.successor.key if ready else None,
        "predecessor_record_generation": request.predecessor.record_generation if ready else None,
        "successor_record_generation": request.successor.record_generation if ready else None,
        "explicit_supersession_edge": edge,
        "write_currentness_resolved": ready,
        "read_currentness_debt_carried": ready,
        "required_future_read_axes": request.future_read.required_guard_axes if ready else (),
        "required_eki2_read_axes": request.future_read.required_eki2_axes if ready else (),
        "refusal_reason": refusal_reason,
        "claim_ceiling": {
            "candidate_only": True,
            "store_mutated": False,
            "write_authority": False,
            "effect_authority": False,
            "semantic_truth_granted": False,
            "semantic_k27_authority": False,
            "chronological_order_inferred": False,
            "persisted_currentness_is_witness": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return VersionTransitionEnvelopeV1(
        disposition=disposition,
        request_digest=request_digest,
        receipt_digest=_sha({"domain": SCHEMA, "receipt": payload}),
        current_subject_key=subject_key,
        current_evidence_generation_key=evidence_key,
        legacy_semantic_id=legacy_id,
        predecessor_record_key=request.predecessor.key if ready else None,
        successor_record_key=request.successor.key if ready else None,
        predecessor_record_generation=request.predecessor.record_generation if ready else None,
        successor_record_generation=request.successor.record_generation if ready else None,
        explicit_supersession_edge=edge,
        write_currentness_resolved=ready,
        read_currentness_debt_carried=ready,
        required_future_read_axes=request.future_read.required_guard_axes if ready else (),
        required_eki2_read_axes=request.future_read.required_eki2_axes if ready else (),
        refusal_reason=refusal_reason,
    )


def build_version_transition_envelope(request: VersionTransitionRequestV1) -> VersionTransitionEnvelopeV1:
    """Build a non-writing version-transition plan or a typed fail-closed HOLD."""
    if request.responsibility == "MODEL_PREFIX_KV":
        return _receipt(
            request,
            EnvelopeDisposition.WRONG_RESPONSIBILITY_OWNER,
            refusal_reason="source-bound coordinate memory is not transformer MODEL_PREFIX_KV",
        )

    try:
        request.evidence.validate()
        subject_key = _sha256(request.evidence.claimed_subject_key, "SUBJECT_KEY")
        evidence_key = _sha256(request.evidence.claimed_evidence_generation_key, "EVIDENCE_GENERATION_KEY")
        expected_type = LEGACY_TO_CURRENT_SUBJECT_TYPE.get(request.legacy_source_kind)
        if expected_type != (request.evidence.provider, request.evidence.source_kind):
            raise EnvelopeError("LEGACY_CURRENT_SUBJECT_TYPE_BRIDGE_MISMATCH")
        legacy_id = legacy_semantic_id(
            legacy_source_kind=request.legacy_source_kind,
            canonical_id=request.evidence.canonical_id,
        )
        request.predecessor.validate(legacy_source_kind=request.legacy_source_kind)
        request.successor.validate(legacy_source_kind=request.legacy_source_kind)
        if request.predecessor.legacy_semantic_id != legacy_id or request.successor.legacy_semantic_id != legacy_id:
            raise EnvelopeError("VERSION_ROWS_NOT_IN_EXACT_BRIDGED_SUBJECT")
        if request.predecessor.canonical_id != request.evidence.canonical_id or request.successor.canonical_id != request.evidence.canonical_id:
            raise EnvelopeError("VERSION_ROW_CANONICAL_ID_MISMATCH")
        if request.predecessor.canonical_uri != request.evidence.canonical_uri or request.successor.canonical_uri != request.evidence.canonical_uri:
            raise EnvelopeError("VERSION_ROW_CANONICAL_URI_MISMATCH")
    except EnvelopeError as exc:
        return _receipt(
            request,
            EnvelopeDisposition.IDENTITY_BRIDGE_HOLD,
            subject_key=locals().get("subject_key"),
            evidence_key=locals().get("evidence_key"),
            legacy_id=locals().get("legacy_id"),
            refusal_reason=str(exc),
        )

    if request.predecessor.key == request.successor.key or request.predecessor.record_generation == request.successor.record_generation:
        return _receipt(
            request,
            EnvelopeDisposition.GENERATION_BINDING_HOLD,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason="version transition requires distinct record generations and keys",
        )
    if request.predecessor.successor != request.successor.key:
        return _receipt(
            request,
            EnvelopeDisposition.SUPERSESSION_EDGE_REQUIRED,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason="explicit predecessor successor edge required; chronology is never inferred",
        )
    if request.successor.successor not in (None, ""):
        return _receipt(
            request,
            EnvelopeDisposition.GENERATION_BINDING_HOLD,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason="proposed successor must be the explicit terminal of this transition",
        )

    try:
        request.write_witness.validate()
    except EnvelopeError as exc:
        disposition = (
            EnvelopeDisposition.WRITE_CURRENTNESS_REQUIRED
            if "CURRENTNESS" in str(exc)
            else EnvelopeDisposition.REPRESENTATION_OWNER_HOLD
        )
        return _receipt(
            request,
            disposition,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason=str(exc),
        )
    if request.write_witness.subject_key != subject_key or request.write_witness.proposed_evidence_generation_key != evidence_key:
        return _receipt(
            request,
            EnvelopeDisposition.GENERATION_BINDING_HOLD,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason="write-currentness witness is bound to a different subject/evidence generation",
        )

    expected_sha = _sha256(request.expected_store_sha256, "EXPECTED_STORE_SHA256")
    if (
        request.write_witness.store_ref != request.expected_store_ref
        or request.write_witness.store_generation != request.expected_store_generation
        or request.write_witness.store_sha256 != expected_sha
    ):
        return _receipt(
            request,
            EnvelopeDisposition.STORE_INTEGRITY_HOLD,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason="write witness and exact immutable store expectation do not commute",
        )

    try:
        request.future_read.validate()
    except EnvelopeError as exc:
        return _receipt(
            request,
            EnvelopeDisposition.READ_OBLIGATION_REQUIRED,
            subject_key=subject_key,
            evidence_key=evidence_key,
            legacy_id=legacy_id,
            refusal_reason=str(exc),
        )

    return _receipt(
        request,
        EnvelopeDisposition.VERSION_TRANSITION_PLAN_READY,
        subject_key=subject_key,
        evidence_key=evidence_key,
        legacy_id=legacy_id,
        ready=True,
    )


LAWS = (
    "CurrentSubjectKey!=CurrentEvidenceGenerationKey!=LegacySemanticId!=EKI2RecordGeneration",
    "StableSubjectOverwriteHold=>TranslateToDistinctVersionedRecordKeys",
    "DistinctVersionedKeysSolveRepresentationOnly",
    "CurrentAtProjection!=CurrentAtWrite!=CurrentAtRead",
    "ExplicitSuccessorEdge!=Chronology!=LexicalOrder!=K27Order",
    "PersistedCurrentness!=ReadCurrentnessWitness",
    "K27Placement!=SemanticIdentity!=VersionOrder!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
