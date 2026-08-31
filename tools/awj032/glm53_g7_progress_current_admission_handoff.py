#!/usr/bin/env python3
"""G7: progress-bound current-generation GLM-5.3 admission handoff.

D0 / HS1 / NONPROMOTING.

Exactly two terminal-green semantic parents:
- NAV-14 / PR #768: progress-bound hydrated version handoff candidate.
- Generation-bound admission reuse / PR #769: historical bounded admission is
  reusable only when identity-bearing current-use axes remain exact.

This membrane joins those consequences without cross-casting either into
source truth, read currentness, execution authority, or Gate-10 evidence.

Laws:
    ProgressBoundHandoffCandidate != AdmissionReuseCandidate
    HandoffMaterialContinuity != SourceReadCurrentness
    HistoricalAdmissionReuseCandidate != OwnerHostExecutionAuthority
    SameSubjectAndEvidenceGeneration != TensorPayloadBinding
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
import json

NAV14_HEAD = "6cdd1be40428250bffba20e924f664c7be585469"
NAV14_RUN = 33437542974
NAV14_JOB = 99637538062
NAV14_BLOB = "b1bdfb4c65281c314e658a6fb6fc8727a4b54245"

ADMISSION_REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
ADMISSION_REUSE_RUN = 33437612722
ADMISSION_REUSE_JOB = 99637780915
ADMISSION_REUSE_BLOB = "d171d0938e469a4383490d1a691750c2068f21e7"

CONVERGENCE_COMMIT = "afadf96392b2a1fb0f32c488f1b240853b46462c"
SCHEMA = "AURA-GLM53-G7-PROGRESS-CURRENT-ADMISSION-HANDOFF-v1"
REQUIRED_ADMISSION_FAMILY = "GLM53_BOUNDED_C2_PROPOSAL"
HEX = frozenset("0123456789abcdef")


class G7Disposition(str, Enum):
    CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE = (
        "CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE"
    )
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_PROGRESS_HANDOFF_NOT_READY = "HOLD_PROGRESS_HANDOFF_NOT_READY"
    HOLD_ADMISSION_REUSE_NOT_READY = "HOLD_ADMISSION_REUSE_NOT_READY"
    HOLD_ADMISSION_FAMILY = "HOLD_ADMISSION_FAMILY"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"
    HOLD_SUBJECT_IDENTITY_MISMATCH = "HOLD_SUBJECT_IDENTITY_MISMATCH"
    HOLD_EVIDENCE_GENERATION_MISMATCH = "HOLD_EVIDENCE_GENERATION_MISMATCH"
    HOLD_PROGRESS_RECEIPT_CHANGED = "HOLD_PROGRESS_RECEIPT_CHANGED"
    HOLD_MATERIAL_CHANGED = "HOLD_MATERIAL_CHANGED"
    HOLD_SOURCE_VIEW_CHANGED = "HOLD_SOURCE_VIEW_CHANGED"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=lambda obj: obj.value if isinstance(obj, Enum) else str(obj),
    ).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _digest(value: str, code: str) -> str:
    value = _text(value, code).lower()
    if len(value) != 64 or any(ch not in HEX for ch in value):
        raise ValueError(code)
    return value


@dataclass(frozen=True)
class ProgressBoundHandoffProjectionV1:
    parent_head: str
    progress_handoff_digest: str
    disposition: str
    subject_identity: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _text(self.parent_head, "PROGRESS_PARENT_HEAD_REQUIRED")
        _digest(self.progress_handoff_digest, "PROGRESS_HANDOFF_DIGEST_REQUIRED")
        _text(self.disposition, "PROGRESS_DISPOSITION_REQUIRED")
        _text(self.subject_identity, "PROGRESS_SUBJECT_REQUIRED")
        _text(self.evidence_generation_key, "PROGRESS_EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "PROGRESS_MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "PROGRESS_SOURCE_URI_REQUIRED")
        for value, code in (
            (self.candidate_only, "PROGRESS_CANDIDATE_ONLY_BOOL"),
            (self.persistent_write_authorized, "PROGRESS_WRITE_BOOL"),
            (self.evidence_admitted, "PROGRESS_EVIDENCE_ADMITTED_BOOL"),
            (self.source_truth_proven, "PROGRESS_SOURCE_TRUTH_BOOL"),
            (self.source_currentness_proven, "PROGRESS_SOURCE_CURRENTNESS_BOOL"),
            (self.read_currentness_proven, "PROGRESS_READ_CURRENTNESS_BOOL"),
            (self.effect_authorized, "PROGRESS_EFFECT_BOOL"),
            (self.semantic_k27_authority, "PROGRESS_K27_BOOL"),
            (self.native_private_transformer_kv_accessed, "PROGRESS_NATIVE_KV_BOOL"),
        ):
            if not isinstance(value, bool):
                raise ValueError(code)


@dataclass(frozen=True)
class AdmissionReuseProjectionV1:
    parent_head: str
    reuse_digest: str
    disposition: str
    family: str
    admission_receipt_digest: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    candidate_only: bool = True
    admission_reused_as_authority: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _text(self.parent_head, "REUSE_PARENT_HEAD_REQUIRED")
        _digest(self.reuse_digest, "REUSE_DIGEST_REQUIRED")
        _text(self.disposition, "REUSE_DISPOSITION_REQUIRED")
        _text(self.family, "REUSE_FAMILY_REQUIRED")
        _digest(self.admission_receipt_digest, "ADMISSION_RECEIPT_DIGEST_REQUIRED")
        for value, code in (
            (self.subject_identity, "REUSE_SUBJECT_REQUIRED"),
            (self.source_generation_key, "REUSE_SOURCE_GENERATION_REQUIRED"),
            (self.evidence_generation_key, "REUSE_EVIDENCE_GENERATION_REQUIRED"),
            (self.owner_context_key, "REUSE_OWNER_CONTEXT_REQUIRED"),
            (self.decision_context_key, "REUSE_DECISION_CONTEXT_REQUIRED"),
        ):
            _text(value, code)
        for value, code in (
            (self.candidate_only, "REUSE_CANDIDATE_ONLY_BOOL"),
            (self.admission_reused_as_authority, "REUSE_AS_AUTHORITY_BOOL"),
            (self.execution_authorized, "REUSE_EXECUTION_BOOL"),
            (self.effect_authorized, "REUSE_EFFECT_BOOL"),
            (self.source_currentness_proven, "REUSE_SOURCE_CURRENTNESS_BOOL"),
            (self.semantic_truth_proven, "REUSE_SEMANTIC_TRUTH_BOOL"),
            (self.semantic_k27_authority, "REUSE_K27_BOOL"),
            (self.native_private_transformer_kv_accessed, "REUSE_NATIVE_KV_BOOL"),
        ):
            if not isinstance(value, bool):
                raise ValueError(code)


@dataclass(frozen=True)
class CurrentHandoffUseContextV1:
    progress_handoff_digest: str
    subject_identity: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str

    def validate_shape(self) -> None:
        _digest(self.progress_handoff_digest, "CURRENT_PROGRESS_DIGEST_REQUIRED")
        _text(self.subject_identity, "CURRENT_SUBJECT_REQUIRED")
        _text(self.evidence_generation_key, "CURRENT_EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "CURRENT_MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "CURRENT_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class G7HandoffReceiptV1:
    disposition: G7Disposition
    reason: str
    progress_handoff_digest: str
    admission_reuse_digest: str
    admission_receipt_digest: str
    subject_identity: str | None
    source_generation_key: str | None
    evidence_generation_key: str | None
    material_digest: str | None
    exact_source_uri: str | None
    owner_context_key: str | None
    decision_context_key: str | None
    handoff_receipt_digest: str
    candidate_only: bool = True
    future_read_currentness_required: bool = True
    future_read_currentness_proven: bool = False
    tensor_payload_bound: bool = False
    source_truth_proven: bool = False
    evidence_admitted: bool = False
    persistent_write_authorized: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    owner_host_execution_observed: bool = False
    gate10_promoted: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.disposition
            is G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE
        )


def _ceiling_breached(
    progress: ProgressBoundHandoffProjectionV1,
    reuse: AdmissionReuseProjectionV1,
) -> bool:
    return any(
        (
            not progress.candidate_only,
            progress.persistent_write_authorized,
            progress.evidence_admitted,
            progress.source_truth_proven,
            progress.source_currentness_proven,
            progress.read_currentness_proven,
            progress.effect_authorized,
            progress.semantic_k27_authority,
            progress.native_private_transformer_kv_accessed,
            not reuse.candidate_only,
            reuse.admission_reused_as_authority,
            reuse.execution_authorized,
            reuse.effect_authorized,
            reuse.source_currentness_proven,
            reuse.semantic_truth_proven,
            reuse.semantic_k27_authority,
            reuse.native_private_transformer_kv_accessed,
        )
    )


def _classify_tree(
    progress: ProgressBoundHandoffProjectionV1,
    reuse: AdmissionReuseProjectionV1,
    current: CurrentHandoffUseContextV1,
) -> G7Disposition:
    if progress.parent_head != NAV14_HEAD or reuse.parent_head != ADMISSION_REUSE_HEAD:
        return G7Disposition.HOLD_PARENT_GENERATION
    if progress.disposition != "PROGRESS_BOUND_HANDOFF_CANDIDATE":
        return G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY
    if reuse.disposition != "REUSE_CANDIDATE":
        return G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY
    if reuse.family != REQUIRED_ADMISSION_FAMILY:
        return G7Disposition.HOLD_ADMISSION_FAMILY
    if _ceiling_breached(progress, reuse):
        return G7Disposition.HOLD_CLAIM_CEILING
    if progress.subject_identity != reuse.subject_identity:
        return G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
    if progress.evidence_generation_key != reuse.evidence_generation_key:
        return G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    if current.progress_handoff_digest != progress.progress_handoff_digest:
        return G7Disposition.HOLD_PROGRESS_RECEIPT_CHANGED
    if current.subject_identity != progress.subject_identity:
        return G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
    if current.evidence_generation_key != progress.evidence_generation_key:
        return G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    if current.material_digest != progress.material_digest:
        return G7Disposition.HOLD_MATERIAL_CHANGED
    if current.exact_source_uri != progress.exact_source_uri:
        return G7Disposition.HOLD_SOURCE_VIEW_CHANGED
    return G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE


def _classify_table(
    progress: ProgressBoundHandoffProjectionV1,
    reuse: AdmissionReuseProjectionV1,
    current: CurrentHandoffUseContextV1,
) -> G7Disposition:
    ordered = (
        (
            progress.parent_head != NAV14_HEAD
            or reuse.parent_head != ADMISSION_REUSE_HEAD,
            G7Disposition.HOLD_PARENT_GENERATION,
        ),
        (
            progress.disposition != "PROGRESS_BOUND_HANDOFF_CANDIDATE",
            G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY,
        ),
        (
            reuse.disposition != "REUSE_CANDIDATE",
            G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY,
        ),
        (reuse.family != REQUIRED_ADMISSION_FAMILY, G7Disposition.HOLD_ADMISSION_FAMILY),
        (_ceiling_breached(progress, reuse), G7Disposition.HOLD_CLAIM_CEILING),
        (
            progress.subject_identity != reuse.subject_identity,
            G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH,
        ),
        (
            progress.evidence_generation_key != reuse.evidence_generation_key,
            G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH,
        ),
        (
            current.progress_handoff_digest != progress.progress_handoff_digest,
            G7Disposition.HOLD_PROGRESS_RECEIPT_CHANGED,
        ),
        (
            current.subject_identity != progress.subject_identity,
            G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH,
        ),
        (
            current.evidence_generation_key != progress.evidence_generation_key,
            G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH,
        ),
        (current.material_digest != progress.material_digest, G7Disposition.HOLD_MATERIAL_CHANGED),
        (current.exact_source_uri != progress.exact_source_uri, G7Disposition.HOLD_SOURCE_VIEW_CHANGED),
    )
    for predicate, disposition in ordered:
        if predicate:
            return disposition
    return G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE


def bind_progress_current_admission_handoff(
    *,
    progress: ProgressBoundHandoffProjectionV1,
    reuse: AdmissionReuseProjectionV1,
    current: CurrentHandoffUseContextV1,
) -> G7HandoffReceiptV1:
    progress.validate_shape()
    reuse.validate_shape()
    current.validate_shape()
    a = _classify_tree(progress, reuse, current)
    b = _classify_table(progress, reuse, current)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_G7_HANDOFF_CLASSIFIERS_DIVERGED")

    ready = a is G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE
    reason = {
        G7Disposition.CURRENT_PROGRESS_BOUND_ADMISSION_HANDOFF_CANDIDATE:
            "progress-bound material and generation-bound admission reuse commute at the current handoff identity while future read-currentness remains unpaid",
        G7Disposition.HOLD_PARENT_GENERATION:
            "one or both parent semantic proof generations changed",
        G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY:
            "NAV-14 progress-bound handoff is not candidate-ready",
        G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY:
            "generation-bound admission is not reusable at this use cut",
        G7Disposition.HOLD_ADMISSION_FAMILY:
            "reuse candidate is not the GLM-5.3 bounded C2 proposal family",
        G7Disposition.HOLD_CLAIM_CEILING:
            "upstream projection widened beyond the nonpromotion ceiling",
        G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH:
            "progress handoff and admission reuse do not bind the same subject",
        G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH:
            "progress handoff and admission reuse do not bind the same evidence generation",
        G7Disposition.HOLD_PROGRESS_RECEIPT_CHANGED:
            "current use does not bind the exact progress-handoff receipt",
        G7Disposition.HOLD_MATERIAL_CHANGED:
            "hydrated material changed after progress-bound handoff",
        G7Disposition.HOLD_SOURCE_VIEW_CHANGED:
            "exact source view changed after progress-bound handoff",
    }[a]

    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "reason": reason,
        "parents": {
            "nav14_head": progress.parent_head,
            "admission_reuse_head": reuse.parent_head,
            "convergence_commit": CONVERGENCE_COMMIT,
        },
        "progress_handoff_digest": progress.progress_handoff_digest,
        "admission_reuse_digest": reuse.reuse_digest,
        "admission_receipt_digest": reuse.admission_receipt_digest,
        "subject_identity": progress.subject_identity if ready else None,
        "source_generation_key": reuse.source_generation_key if ready else None,
        "evidence_generation_key": progress.evidence_generation_key if ready else None,
        "material_digest": progress.material_digest if ready else None,
        "exact_source_uri": progress.exact_source_uri if ready else None,
        "owner_context_key": reuse.owner_context_key if ready else None,
        "decision_context_key": reuse.decision_context_key if ready else None,
        "claim_ceiling": {
            "candidate_only": True,
            "future_read_currentness_required": True,
            "future_read_currentness_proven": False,
            "tensor_payload_bound": False,
            "source_truth_proven": False,
            "evidence_admitted": False,
            "persistent_write_authorized": False,
            "execution_authorized": False,
            "provider_effect_authorized": False,
            "owner_host_execution_observed": False,
            "gate10_promoted": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return G7HandoffReceiptV1(
        disposition=a,
        reason=reason,
        progress_handoff_digest=progress.progress_handoff_digest,
        admission_reuse_digest=reuse.reuse_digest,
        admission_receipt_digest=reuse.admission_receipt_digest,
        subject_identity=progress.subject_identity if ready else None,
        source_generation_key=reuse.source_generation_key if ready else None,
        evidence_generation_key=progress.evidence_generation_key if ready else None,
        material_digest=progress.material_digest if ready else None,
        exact_source_uri=progress.exact_source_uri if ready else None,
        owner_context_key=reuse.owner_context_key if ready else None,
        decision_context_key=reuse.decision_context_key if ready else None,
        handoff_receipt_digest=_sha(body),
    )


def fixture() -> tuple[
    ProgressBoundHandoffProjectionV1,
    AdmissionReuseProjectionV1,
    CurrentHandoffUseContextV1,
]:
    d0, d1, d2, d3 = ("0" * 64, "1" * 64, "2" * 64, "3" * 64)
    progress = ProgressBoundHandoffProjectionV1(
        parent_head=NAV14_HEAD,
        progress_handoff_digest=d0,
        disposition="PROGRESS_BOUND_HANDOFF_CANDIDATE",
        subject_identity="glm53:flagship:c2",
        evidence_generation_key="evidence-generation:glm53:c2:1",
        material_digest=d1,
        exact_source_uri="https://huggingface.co/zai-org/GLM-5.3",
    )
    reuse = AdmissionReuseProjectionV1(
        parent_head=ADMISSION_REUSE_HEAD,
        reuse_digest=d2,
        disposition="REUSE_CANDIDATE",
        family=REQUIRED_ADMISSION_FAMILY,
        admission_receipt_digest=d3,
        subject_identity=progress.subject_identity,
        source_generation_key="source-generation:glm53:flagship:1",
        evidence_generation_key=progress.evidence_generation_key,
        owner_context_key="owner-context:glm53:c2:1",
        decision_context_key="decision-context:glm53:c2:1",
    )
    current = CurrentHandoffUseContextV1(
        progress_handoff_digest=progress.progress_handoff_digest,
        subject_identity=progress.subject_identity,
        evidence_generation_key=progress.evidence_generation_key,
        material_digest=progress.material_digest,
        exact_source_uri=progress.exact_source_uri,
    )
    return progress, reuse, current


def prove_different_j() -> int:
    progress, reuse, current = fixture()
    checked = 0
    for mask in range(512):
        p = replace(
            progress,
            disposition=(
                "PROGRESS_BOUND_HANDOFF_CANDIDATE"
                if not (mask & 1)
                else "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
            ),
            source_truth_proven=bool(mask & 256),
        )
        r = replace(
            reuse,
            disposition="REUSE_CANDIDATE" if not (mask & 2) else "HOLD_SOURCE_GENERATION_CHANGED",
            family=REQUIRED_ADMISSION_FAMILY if not (mask & 4) else "HYDRATION_TRANSACTION",
            subject_identity=reuse.subject_identity if not (mask & 8) else reuse.subject_identity + ":drift",
            evidence_generation_key=(
                reuse.evidence_generation_key
                if not (mask & 16)
                else reuse.evidence_generation_key + ":drift"
            ),
        )
        c = replace(
            current,
            progress_handoff_digest=(
                current.progress_handoff_digest if not (mask & 32) else "4" * 64
            ),
            material_digest=current.material_digest if not (mask & 64) else "5" * 64,
            exact_source_uri=(
                current.exact_source_uri
                if not (mask & 128)
                else current.exact_source_uri + "#drift"
            ),
        )
        if _classify_tree(p, r, c) is not _classify_table(p, r, c):
            raise AssertionError("DIFFERENT_J_G7_HANDOFF_MATRIX_MISMATCH")
        checked += 1
    return checked


LAWS = (
    "ProgressBoundHandoffCandidate!=AdmissionReuseCandidate",
    "AdmissionReuseCandidate!=OwnerHostExecutionAuthority",
    "HandoffMaterialContinuity!=SourceReadCurrentness",
    "FutureReadCurrentnessDebtSurvivesG7",
    "SameSubjectAndEvidenceGeneration!=TensorPayloadBinding",
    "AnyProgressMaterialSourceViewDrift=>Hold",
    "CurrentGenerationAdmissionReuseMustCommuteWithCurrentProgressHandoff",
    "K27Placement!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
