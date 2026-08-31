#!/usr/bin/env python3
"""G7 v2: structurally bind GLM-5.3 progress handoff to admission reuse.

D0 / HS1 / NONPROMOTING.

Exactly two terminal-green semantic parents:
- NAV-14 / PR #768: progress-bound hydrated version handoff candidate.
- Generation-bound admission reuse / PR #769: historical bounded admission is
  reusable only when identity-bearing presented use axes remain exact.

W3 repair:
Caller-constructible parent projections and presented-use fields are not
producer authentication or currentness truth. G7 therefore verifies the
positive parent receipt digests for self-consistency, performs only a
structural join, and leaves both parent-producer authentication and use-time
currentness as explicit external debts.

Laws:
    SelfConsistentParentProjection != AuthenticatedParentReceipt
    MatchingPresentedUseContext != AuthenticatedCurrentness
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
NAV14_SCHEMA = "AURA-NAV14-PROGRESS-BOUND-HYDRATED-VERSION-HANDOFF-v1"
NAV14_POSITIVE = "PROGRESS_BOUND_HANDOFF_CANDIDATE"
NAV14_POSITIVE_REASON = (
    "exact handoff material is bound to initial retrieval or an independent "
    "provider/evidence state transition"
)
NAV14_ALLOWED_POSITIVE_RETRIEVAL_DECISIONS = frozenset(
    {"ALLOW_INITIAL", "ALLOW_STATE_TRANSITION"}
)

ADMISSION_REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
ADMISSION_REUSE_RUN = 33437612722
ADMISSION_REUSE_JOB = 99637780915
ADMISSION_REUSE_BLOB = "d171d0938e469a4383490d1a691750c2068f21e7"
ADMISSION_REUSE_SCHEMA = "AURA-GENERATION-BOUND-ADMISSION-REUSE-v1"
ADMISSION_REUSE_POSITIVE = "REUSE_CANDIDATE"
ADMISSION_REUSE_POSITIVE_REASON = (
    "all identity-bearing producer/source/evidence/owner/decision axes remain exact"
)

CONVERGENCE_COMMIT = "afadf96392b2a1fb0f32c488f1b240853b46462c"
SCHEMA = "AURA-GLM53-G7-PROGRESS-ADMISSION-STRUCTURAL-HANDOFF-v2"
REQUIRED_ADMISSION_FAMILY = "GLM53_BOUNDED_C2_PROPOSAL"
HEX = frozenset("0123456789abcdef")


class G7Disposition(str, Enum):
    STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED = (
        "STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED"
    )
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_PROGRESS_HANDOFF_NOT_READY = "HOLD_PROGRESS_HANDOFF_NOT_READY"
    HOLD_ADMISSION_REUSE_NOT_READY = "HOLD_ADMISSION_REUSE_NOT_READY"
    HOLD_ADMISSION_FAMILY = "HOLD_ADMISSION_FAMILY"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"
    HOLD_SUBJECT_IDENTITY_MISMATCH = "HOLD_SUBJECT_IDENTITY_MISMATCH"
    HOLD_EVIDENCE_GENERATION_MISMATCH = "HOLD_EVIDENCE_GENERATION_MISMATCH"
    HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED = "HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED"
    HOLD_PRESENTED_MATERIAL_CHANGED = "HOLD_PRESENTED_MATERIAL_CHANGED"
    HOLD_PRESENTED_SOURCE_VIEW_CHANGED = "HOLD_PRESENTED_SOURCE_VIEW_CHANGED"


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
class ProgressBoundHandoffProjectionV2:
    parent_head: str
    progress_handoff_digest: str
    handoff_digest: str
    retrieval_receipt_digest: str
    retrieval_decision: str
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
        _digest(self.handoff_digest, "NAV14_HANDOFF_DIGEST_REQUIRED")
        _digest(self.retrieval_receipt_digest, "NAV14_RETRIEVAL_RECEIPT_DIGEST_REQUIRED")
        _text(self.retrieval_decision, "NAV14_RETRIEVAL_DECISION_REQUIRED")
        _text(self.disposition, "PROGRESS_DISPOSITION_REQUIRED")
        _digest(self.subject_identity, "PROGRESS_SUBJECT_DIGEST_REQUIRED")
        _digest(self.evidence_generation_key, "PROGRESS_EVIDENCE_GENERATION_DIGEST_REQUIRED")
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
        if self.disposition == NAV14_POSITIVE:
            if self.retrieval_decision not in NAV14_ALLOWED_POSITIVE_RETRIEVAL_DECISIONS:
                raise ValueError("NAV14_POSITIVE_RETRIEVAL_DECISION_INVALID")
            if self.progress_handoff_digest != _expected_nav14_positive_digest(self):
                raise ValueError("NAV14_PROGRESS_RECEIPT_SELF_INTEGRITY_MISMATCH")


@dataclass(frozen=True)
class AdmissionReuseProjectionV2:
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
        if self.disposition == ADMISSION_REUSE_POSITIVE:
            if self.reuse_digest != _expected_admission_reuse_positive_digest(self):
                raise ValueError("ADMISSION_REUSE_RECEIPT_SELF_INTEGRITY_MISMATCH")


@dataclass(frozen=True)
class PresentedHandoffUseContextV2:
    progress_handoff_digest: str
    subject_identity: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str

    def validate_shape(self) -> None:
        _digest(self.progress_handoff_digest, "PRESENTED_PROGRESS_DIGEST_REQUIRED")
        _digest(self.subject_identity, "PRESENTED_SUBJECT_DIGEST_REQUIRED")
        _digest(self.evidence_generation_key, "PRESENTED_EVIDENCE_GENERATION_DIGEST_REQUIRED")
        _digest(self.material_digest, "PRESENTED_MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "PRESENTED_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class G7HandoffReceiptV2:
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
    parent_projection_authentication_required: bool = True
    parent_projection_authenticated_by_this_contract: bool = False
    presented_currentness_authentication_required: bool = True
    presented_currentness_authenticated_by_this_contract: bool = False
    future_read_currentness_required: bool = True
    future_read_currentness_proven: bool = False
    reuse_authorized_by_this_contract: bool = False
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
    def structural_candidate(self) -> bool:
        return (
            self.disposition
            is G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED
        )


def _expected_nav14_positive_digest(progress: ProgressBoundHandoffProjectionV2) -> str:
    body = {
        "schema": NAV14_SCHEMA,
        "disposition": NAV14_POSITIVE,
        "reason": NAV14_POSITIVE_REASON,
        "handoff_digest": progress.handoff_digest,
        "retrieval_receipt_digest": progress.retrieval_receipt_digest,
        "retrieval_decision": progress.retrieval_decision,
        "subject_key": progress.subject_identity,
        "evidence_generation_key": progress.evidence_generation_key,
        "material_digest": progress.material_digest,
        "exact_source_uri": progress.exact_source_uri,
        "claim_ceiling": {
            "candidate_only": True,
            "persistent_write_authorized": False,
            "evidence_admitted": False,
            "source_truth_proven": False,
            "source_currentness_proven": False,
            "read_currentness_proven": False,
            "effect_authorized": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return _sha(body)


def _expected_admission_reuse_positive_digest(reuse: AdmissionReuseProjectionV2) -> str:
    body = {
        "schema": ADMISSION_REUSE_SCHEMA,
        "disposition": ADMISSION_REUSE_POSITIVE,
        "reason": ADMISSION_REUSE_POSITIVE_REASON,
        "family": reuse.family,
        "admission_receipt_digest": reuse.admission_receipt_digest,
        "subject_identity": reuse.subject_identity,
        "source_generation_key": reuse.source_generation_key,
        "evidence_generation_key": reuse.evidence_generation_key,
        "owner_context_key": reuse.owner_context_key,
        "decision_context_key": reuse.decision_context_key,
        "claim_ceiling": {
            "candidate_only": True,
            "admission_reused_as_authority": False,
            "execution_authorized": False,
            "effect_authorized": False,
            "source_currentness_proven": False,
            "semantic_truth_proven": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return _sha(body)


def _ceiling_breached(
    progress: ProgressBoundHandoffProjectionV2,
    reuse: AdmissionReuseProjectionV2,
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
    progress: ProgressBoundHandoffProjectionV2,
    reuse: AdmissionReuseProjectionV2,
    presented: PresentedHandoffUseContextV2,
) -> G7Disposition:
    if progress.parent_head != NAV14_HEAD or reuse.parent_head != ADMISSION_REUSE_HEAD:
        return G7Disposition.HOLD_PARENT_GENERATION
    if progress.disposition != NAV14_POSITIVE:
        return G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY
    if reuse.disposition != ADMISSION_REUSE_POSITIVE:
        return G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY
    if reuse.family != REQUIRED_ADMISSION_FAMILY:
        return G7Disposition.HOLD_ADMISSION_FAMILY
    if _ceiling_breached(progress, reuse):
        return G7Disposition.HOLD_CLAIM_CEILING
    if progress.subject_identity != reuse.subject_identity:
        return G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
    if progress.evidence_generation_key != reuse.evidence_generation_key:
        return G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    if presented.progress_handoff_digest != progress.progress_handoff_digest:
        return G7Disposition.HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED
    if presented.subject_identity != progress.subject_identity:
        return G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH
    if presented.evidence_generation_key != progress.evidence_generation_key:
        return G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    if presented.material_digest != progress.material_digest:
        return G7Disposition.HOLD_PRESENTED_MATERIAL_CHANGED
    if presented.exact_source_uri != progress.exact_source_uri:
        return G7Disposition.HOLD_PRESENTED_SOURCE_VIEW_CHANGED
    return G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED


def _classify_table(
    progress: ProgressBoundHandoffProjectionV2,
    reuse: AdmissionReuseProjectionV2,
    presented: PresentedHandoffUseContextV2,
) -> G7Disposition:
    ordered = (
        (
            progress.parent_head != NAV14_HEAD
            or reuse.parent_head != ADMISSION_REUSE_HEAD,
            G7Disposition.HOLD_PARENT_GENERATION,
        ),
        (
            progress.disposition != NAV14_POSITIVE,
            G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY,
        ),
        (
            reuse.disposition != ADMISSION_REUSE_POSITIVE,
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
            presented.progress_handoff_digest != progress.progress_handoff_digest,
            G7Disposition.HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED,
        ),
        (
            presented.subject_identity != progress.subject_identity,
            G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH,
        ),
        (
            presented.evidence_generation_key != progress.evidence_generation_key,
            G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH,
        ),
        (
            presented.material_digest != progress.material_digest,
            G7Disposition.HOLD_PRESENTED_MATERIAL_CHANGED,
        ),
        (
            presented.exact_source_uri != progress.exact_source_uri,
            G7Disposition.HOLD_PRESENTED_SOURCE_VIEW_CHANGED,
        ),
    )
    for predicate, disposition in ordered:
        if predicate:
            return disposition
    return G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED


def bind_progress_admission_structural_handoff(
    *,
    progress: ProgressBoundHandoffProjectionV2,
    reuse: AdmissionReuseProjectionV2,
    presented: PresentedHandoffUseContextV2,
) -> G7HandoffReceiptV2:
    progress.validate_shape()
    reuse.validate_shape()
    presented.validate_shape()
    a = _classify_tree(progress, reuse, presented)
    b = _classify_table(progress, reuse, presented)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_G7_HANDOFF_CLASSIFIERS_DIVERGED")

    ready = (
        a
        is G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED
    )
    reason = {
        G7Disposition.STRUCTURAL_PROGRESS_ADMISSION_MATCH_EXTERNAL_AUTH_REQUIRED:
            "self-consistent parent projections and presented handoff continuity match structurally; external producer and currentness authentication remain required",
        G7Disposition.HOLD_PARENT_GENERATION:
            "one or both presented parent semantic proof generations changed",
        G7Disposition.HOLD_PROGRESS_HANDOFF_NOT_READY:
            "presented NAV-14 progress-bound handoff is not candidate-ready",
        G7Disposition.HOLD_ADMISSION_REUSE_NOT_READY:
            "presented generation-bound admission is not reuse-candidate shaped",
        G7Disposition.HOLD_ADMISSION_FAMILY:
            "reuse candidate is not the GLM-5.3 bounded C2 proposal family",
        G7Disposition.HOLD_CLAIM_CEILING:
            "upstream projection exceeds the nonpromotion ceiling",
        G7Disposition.HOLD_SUBJECT_IDENTITY_MISMATCH:
            "progress handoff and admission reuse do not bind the same subject",
        G7Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH:
            "progress handoff and admission reuse do not bind the same evidence generation",
        G7Disposition.HOLD_PRESENTED_PROGRESS_RECEIPT_CHANGED:
            "presented use context does not bind the exact progress-handoff receipt",
        G7Disposition.HOLD_PRESENTED_MATERIAL_CHANGED:
            "presented hydrated material differs from the progress-bound handoff",
        G7Disposition.HOLD_PRESENTED_SOURCE_VIEW_CHANGED:
            "presented source view differs from the progress-bound handoff",
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
            "parent_projection_authentication_required": True,
            "parent_projection_authenticated_by_this_contract": False,
            "presented_currentness_authentication_required": True,
            "presented_currentness_authenticated_by_this_contract": False,
            "future_read_currentness_required": True,
            "future_read_currentness_proven": False,
            "reuse_authorized_by_this_contract": False,
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
    return G7HandoffReceiptV2(
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
    ProgressBoundHandoffProjectionV2,
    AdmissionReuseProjectionV2,
    PresentedHandoffUseContextV2,
]:
    d0, d1, d2, d3, d4, d5, d6, d7 = tuple(str(i) * 64 for i in range(8))
    progress = ProgressBoundHandoffProjectionV2(
        parent_head=NAV14_HEAD,
        progress_handoff_digest=d0,
        handoff_digest=d6,
        retrieval_receipt_digest=d7,
        retrieval_decision="ALLOW_INITIAL",
        disposition=NAV14_POSITIVE,
        subject_identity=d4,
        evidence_generation_key=d5,
        material_digest=d1,
        exact_source_uri="https://huggingface.co/zai-org/GLM-5.3",
    )
    progress = replace(
        progress,
        progress_handoff_digest=_expected_nav14_positive_digest(progress),
    )
    reuse = AdmissionReuseProjectionV2(
        parent_head=ADMISSION_REUSE_HEAD,
        reuse_digest=d2,
        disposition=ADMISSION_REUSE_POSITIVE,
        family=REQUIRED_ADMISSION_FAMILY,
        admission_receipt_digest=d3,
        subject_identity=progress.subject_identity,
        source_generation_key="source-generation:glm53:flagship:1",
        evidence_generation_key=progress.evidence_generation_key,
        owner_context_key="owner-context:glm53:c2:1",
        decision_context_key="decision-context:glm53:c2:1",
    )
    reuse = replace(reuse, reuse_digest=_expected_admission_reuse_positive_digest(reuse))
    presented = PresentedHandoffUseContextV2(
        progress_handoff_digest=progress.progress_handoff_digest,
        subject_identity=progress.subject_identity,
        evidence_generation_key=progress.evidence_generation_key,
        material_digest=progress.material_digest,
        exact_source_uri=progress.exact_source_uri,
    )
    return progress, reuse, presented


def prove_different_j() -> int:
    progress, reuse, presented = fixture()
    checked = 0
    for mask in range(512):
        p = replace(
            progress,
            disposition=NAV14_POSITIVE if not (mask & 1) else "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED",
            source_truth_proven=bool(mask & 256),
        )
        r = replace(
            reuse,
            disposition=ADMISSION_REUSE_POSITIVE if not (mask & 2) else "HOLD_SOURCE_GENERATION_CHANGED",
            family=REQUIRED_ADMISSION_FAMILY if not (mask & 4) else "HYDRATION_TRANSACTION",
            subject_identity=reuse.subject_identity if not (mask & 8) else "8" * 64,
            evidence_generation_key=(
                reuse.evidence_generation_key if not (mask & 16) else "9" * 64
            ),
        )
        c = replace(
            presented,
            progress_handoff_digest=(
                presented.progress_handoff_digest if not (mask & 32) else "a" * 64
            ),
            material_digest=presented.material_digest if not (mask & 64) else "b" * 64,
            exact_source_uri=(
                presented.exact_source_uri
                if not (mask & 128)
                else presented.exact_source_uri + "#drift"
            ),
        )
        if _classify_tree(p, r, c) is not _classify_table(p, r, c):
            raise AssertionError("DIFFERENT_J_G7_HANDOFF_MATRIX_MISMATCH")
        checked += 1
    return checked


LAWS = (
    "SelfConsistentParentProjection!=AuthenticatedParentReceipt",
    "MatchingPresentedUseContext!=AuthenticatedCurrentness",
    "ProgressBoundHandoffCandidate!=AdmissionReuseCandidate",
    "AdmissionReuseCandidate!=OwnerHostExecutionAuthority",
    "HandoffMaterialContinuity!=SourceReadCurrentness",
    "FutureReadCurrentnessDebtSurvivesG7",
    "SameSubjectAndEvidenceGeneration!=TensorPayloadBinding",
    "AnyPresentedProgressMaterialSourceViewDrift=>Hold",
    "K27Placement!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
