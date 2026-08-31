#!/usr/bin/env python3
"""Progress-bound generation reuse preflight.

D0 / HS1 / NONPROMOTING.

Exactly two earned semantic parents:
- PR #768 / NAV-14 progress-bound hydrated-version handoff.
- PR #769 / generation-bound admission reuse.

This relation refuses to cross-cast NAV-14's exact source URI/material domain into
PR769's source-generation/owner/decision domain.  A positive result proves only
that the two parent candidates refer to the same subject and evidence generation
and that the exact parent generations/proofs are the expected ones.  It carries
source-relation and future-read-currentness debt forward.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json

SCHEMA = "AURA-PROGRESS-BOUND-GENERATION-REUSE-PREFLIGHT-v1"
NAV14_HEAD = "6cdd1be40428250bffba20e924f664c7be585469"
NAV14_RUN = 33437542974
NAV14_JOB = 99637538062
REUSE_HEAD = "d1a0f94255527835a59a70a0af7dc417ba1d023d"
REUSE_RUN = 33437612722
REUSE_JOB = 99637780915
REQUIRED_NAV14_DISPOSITION = "PROGRESS_BOUND_HANDOFF_CANDIDATE"
REQUIRED_REUSE_DISPOSITION = "REUSE_CANDIDATE"
REQUIRED_REUSE_FAMILY = "HYDRATION_TRANSACTION"
REQUIRED_DEBTS = (
    "SOURCE_URI_TO_SOURCE_GENERATION_RELATION",
    "FUTURE_READ_CURRENTNESS",
)
HEX = frozenset("0123456789abcdef")


class Disposition(str, Enum):
    PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE = "PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_PARENT_PROOF = "HOLD_PARENT_PROOF"
    HOLD_PARENT_NOT_READY = "HOLD_PARENT_NOT_READY"
    HOLD_REUSE_FAMILY = "HOLD_REUSE_FAMILY"
    HOLD_SUBJECT_MISMATCH = "HOLD_SUBJECT_MISMATCH"
    HOLD_EVIDENCE_GENERATION_MISMATCH = "HOLD_EVIDENCE_GENERATION_MISMATCH"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
                      default=lambda o: o.value if isinstance(o, Enum) else str(o)).encode("ascii")


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
    parent_run: int
    parent_job: int
    disposition: str
    progress_handoff_digest: str
    retrieval_receipt_digest: str
    subject_key: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    candidate_only: bool = True
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _text(self.parent_head, "NAV14_HEAD_REQUIRED")
        _digest(self.progress_handoff_digest, "NAV14_HANDOFF_DIGEST_REQUIRED")
        _digest(self.retrieval_receipt_digest, "NAV14_RETRIEVAL_RECEIPT_REQUIRED")
        _text(self.subject_key, "NAV14_SUBJECT_REQUIRED")
        _text(self.evidence_generation_key, "NAV14_EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "NAV14_MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "NAV14_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class AdmissionReuseProjectionV1:
    parent_head: str
    parent_run: int
    parent_job: int
    disposition: str
    family: str
    reuse_digest: str
    admission_receipt_digest: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    candidate_only: bool = True
    admission_reused_as_authority: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _text(self.parent_head, "REUSE_HEAD_REQUIRED")
        _digest(self.reuse_digest, "REUSE_DIGEST_REQUIRED")
        _digest(self.admission_receipt_digest, "ADMISSION_RECEIPT_DIGEST_REQUIRED")
        for value, code in (
            (self.subject_identity, "REUSE_SUBJECT_REQUIRED"),
            (self.source_generation_key, "REUSE_SOURCE_GENERATION_REQUIRED"),
            (self.evidence_generation_key, "REUSE_EVIDENCE_GENERATION_REQUIRED"),
            (self.owner_context_key, "REUSE_OWNER_CONTEXT_REQUIRED"),
            (self.decision_context_key, "REUSE_DECISION_CONTEXT_REQUIRED"),
        ):
            _text(value, code)


@dataclass(frozen=True)
class ProgressBoundReusePreflightReceiptV1:
    disposition: Disposition
    reason: str
    progress_handoff_digest: str
    reuse_digest: str
    subject_identity: str | None
    evidence_generation_key: str | None
    material_digest: str | None
    exact_source_uri: str | None
    source_generation_key: str | None
    owner_context_key: str | None
    decision_context_key: str | None
    unresolved_debts: tuple[str, ...]
    receipt_digest: str
    candidate_only: bool = True
    source_relation_proven: bool = False
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    persistent_use_authorized: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def ready(self) -> bool:
        return self.disposition is Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE


def _ceiling_breached(h: ProgressBoundHandoffProjectionV1, r: AdmissionReuseProjectionV1) -> bool:
    return any((
        not h.candidate_only, h.source_currentness_proven, h.read_currentness_proven,
        h.persistent_write_authorized, h.evidence_admitted, h.effect_authorized,
        h.semantic_k27_authority, h.native_private_transformer_kv_accessed,
        not r.candidate_only, r.admission_reused_as_authority, r.source_currentness_proven,
        r.semantic_truth_proven, r.execution_authorized, r.effect_authorized,
        r.semantic_k27_authority, r.native_private_transformer_kv_accessed,
    ))


def _classify_tree(h: ProgressBoundHandoffProjectionV1, r: AdmissionReuseProjectionV1) -> Disposition:
    if h.parent_head != NAV14_HEAD or r.parent_head != REUSE_HEAD:
        return Disposition.HOLD_PARENT_GENERATION
    if (h.parent_run, h.parent_job) != (NAV14_RUN, NAV14_JOB) or (r.parent_run, r.parent_job) != (REUSE_RUN, REUSE_JOB):
        return Disposition.HOLD_PARENT_PROOF
    if h.disposition != REQUIRED_NAV14_DISPOSITION or r.disposition != REQUIRED_REUSE_DISPOSITION:
        return Disposition.HOLD_PARENT_NOT_READY
    if r.family != REQUIRED_REUSE_FAMILY:
        return Disposition.HOLD_REUSE_FAMILY
    if _ceiling_breached(h, r):
        return Disposition.HOLD_CLAIM_CEILING
    if h.subject_key != r.subject_identity:
        return Disposition.HOLD_SUBJECT_MISMATCH
    if h.evidence_generation_key != r.evidence_generation_key:
        return Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    return Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE


def _classify_rules(h: ProgressBoundHandoffProjectionV1, r: AdmissionReuseProjectionV1) -> Disposition:
    rules = (
        (h.parent_head != NAV14_HEAD or r.parent_head != REUSE_HEAD, Disposition.HOLD_PARENT_GENERATION),
        ((h.parent_run, h.parent_job) != (NAV14_RUN, NAV14_JOB) or (r.parent_run, r.parent_job) != (REUSE_RUN, REUSE_JOB), Disposition.HOLD_PARENT_PROOF),
        (h.disposition != REQUIRED_NAV14_DISPOSITION or r.disposition != REQUIRED_REUSE_DISPOSITION, Disposition.HOLD_PARENT_NOT_READY),
        (r.family != REQUIRED_REUSE_FAMILY, Disposition.HOLD_REUSE_FAMILY),
        (_ceiling_breached(h, r), Disposition.HOLD_CLAIM_CEILING),
        (h.subject_key != r.subject_identity, Disposition.HOLD_SUBJECT_MISMATCH),
        (h.evidence_generation_key != r.evidence_generation_key, Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE


def assess_progress_bound_reuse_preflight(*, handoff: ProgressBoundHandoffProjectionV1, reuse: AdmissionReuseProjectionV1) -> ProgressBoundReusePreflightReceiptV1:
    handoff.validate_shape()
    reuse.validate_shape()
    a = _classify_tree(handoff, reuse)
    b = _classify_rules(handoff, reuse)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_PROGRESS_REUSE_DIVERGED")
    ready = a is Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE
    reasons = {
        Disposition.PROGRESS_BOUND_REUSE_PREFLIGHT_CANDIDATE: "exact terminal parent proofs plus subject/evidence generation commute; source relation and future read currentness remain unresolved",
        Disposition.HOLD_PARENT_GENERATION: "parent semantic generation mismatch",
        Disposition.HOLD_PARENT_PROOF: "parent hosted proof coordinate mismatch",
        Disposition.HOLD_PARENT_NOT_READY: "one or both parent dispositions are not candidate-ready",
        Disposition.HOLD_REUSE_FAMILY: "reuse family is not the hydration transaction family",
        Disposition.HOLD_SUBJECT_MISMATCH: "progress handoff and reuse candidate identify different subjects",
        Disposition.HOLD_EVIDENCE_GENERATION_MISMATCH: "progress handoff and reuse candidate identify different evidence generations",
        Disposition.HOLD_CLAIM_CEILING: "parent projection exceeds nonpromotion ceiling",
    }
    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "progress_handoff_digest": handoff.progress_handoff_digest,
        "reuse_digest": reuse.reuse_digest,
        "subject_identity": handoff.subject_key if ready else None,
        "evidence_generation_key": handoff.evidence_generation_key if ready else None,
        "material_digest": handoff.material_digest if ready else None,
        "exact_source_uri": handoff.exact_source_uri if ready else None,
        "source_generation_key": reuse.source_generation_key if ready else None,
        "owner_context_key": reuse.owner_context_key if ready else None,
        "decision_context_key": reuse.decision_context_key if ready else None,
        "unresolved_debts": REQUIRED_DEBTS,
        "claim_ceiling": {
            "candidate_only": True,
            "source_relation_proven": False,
            "source_currentness_proven": False,
            "read_currentness_proven": False,
            "persistent_use_authorized": False,
            "execution_authorized": False,
            "effect_authorized": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return ProgressBoundReusePreflightReceiptV1(
        disposition=a,
        reason=reasons[a],
        progress_handoff_digest=handoff.progress_handoff_digest,
        reuse_digest=reuse.reuse_digest,
        subject_identity=handoff.subject_key if ready else None,
        evidence_generation_key=handoff.evidence_generation_key if ready else None,
        material_digest=handoff.material_digest if ready else None,
        exact_source_uri=handoff.exact_source_uri if ready else None,
        source_generation_key=reuse.source_generation_key if ready else None,
        owner_context_key=reuse.owner_context_key if ready else None,
        decision_context_key=reuse.decision_context_key if ready else None,
        unresolved_debts=REQUIRED_DEBTS,
        receipt_digest=_sha(body),
    )


LAWS = (
    "ProgressBoundHandoff!=ReusableCurrentAdmission",
    "SameSubjectAndEvidenceGeneration!=SourceRelation",
    "ProgressCannotRefreshHistoricalAdmission",
    "CurrentAdmissionCannotBorrowUnrelatedProgress",
    "SourceURI!=SourceGenerationKeyUntilOwnerRelation",
    "PreflightCandidate!=PersistentUseReady",
    "FutureReadCurrentnessDebtSurvivesReusePreflight",
    "K27Placement!=SemanticIdentity!=Progress!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
