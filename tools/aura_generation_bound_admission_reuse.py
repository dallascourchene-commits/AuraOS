#!/usr/bin/env python3
"""Generation-bound bounded-admission reuse membrane.

D0 / HS1 / NONPROMOTING.

Exactly two semantic parents:
- PR #758 scheme-serializable hydration transaction.
- Q18 current-generation bounded C2 proposal.

A positive admission receipt is a historical decision, not a timeless lease.
This module can only revalidate a typed admission projection against a current
identity/generation vector. It does not execute the admitted operation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json

SCHEMA = "AURA-GENERATION-BOUND-ADMISSION-REUSE-v1"
PR758_HEAD = "8c30df774ad55507aa57bbfd49444991c1a2b379"
PR758_RUN = 33436051562
PR758_JOB = 99632632584
PR758_BLOB = "97211589682a7ed67c8c63530dac744b9c186e57"
Q18_HEAD = "aed81432db8b84d2f43b8a85d06d4b72e16f6a50"
Q18_RUN = 33436580962
Q18_JOB = 99634379758
Q18_BLOB = "4cee26edaf0759fc80d31889ab9e4e268f9a4fbe"
CONVERGENCE_COMMIT = "ea3a61a20b410fd02ed0520d0e4488fcd6987329"
HEX = frozenset("0123456789abcdef")


class AdmissionFamily(str, Enum):
    HYDRATION_TRANSACTION = "HYDRATION_TRANSACTION"
    GLM53_BOUNDED_C2_PROPOSAL = "GLM53_BOUNDED_C2_PROPOSAL"


EXPECTED_HEAD = {
    AdmissionFamily.HYDRATION_TRANSACTION: PR758_HEAD,
    AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL: Q18_HEAD,
}
EXPECTED_POSITIVE_DISPOSITION = {
    AdmissionFamily.HYDRATION_TRANSACTION: "ADMIT_BOUNDED_TRANSACTION",
    AdmissionFamily.GLM53_BOUNDED_C2_PROPOSAL: "BOUNDED_REPRESENTATIVE_E8_C2_REQUEST_PROPOSAL_ELIGIBLE",
}


class ReuseDisposition(str, Enum):
    REUSE_CANDIDATE = "REUSE_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_ADMISSION_NOT_POSITIVE = "HOLD_ADMISSION_NOT_POSITIVE"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"
    HOLD_PRODUCER_GENERATION_CHANGED = "HOLD_PRODUCER_GENERATION_CHANGED"
    HOLD_SUBJECT_CHANGED = "HOLD_SUBJECT_CHANGED"
    HOLD_SOURCE_GENERATION_CHANGED = "HOLD_SOURCE_GENERATION_CHANGED"
    HOLD_EVIDENCE_GENERATION_CHANGED = "HOLD_EVIDENCE_GENERATION_CHANGED"
    HOLD_OWNER_CONTEXT_CHANGED = "HOLD_OWNER_CONTEXT_CHANGED"
    HOLD_DECISION_CONTEXT_CHANGED = "HOLD_DECISION_CONTEXT_CHANGED"


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
class AdmissionReceiptProjectionV1:
    family: AdmissionFamily
    producer_head: str
    receipt_digest: str
    admission_disposition: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str
    bounded_admission_positive: bool
    candidate_only: bool = True
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    evidence_admitted: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        if not isinstance(self.family, AdmissionFamily):
            raise ValueError("ADMISSION_FAMILY_INVALID")
        _text(self.producer_head, "PRODUCER_HEAD_REQUIRED")
        _digest(self.receipt_digest, "RECEIPT_DIGEST_REQUIRED")
        for value, code in (
            (self.admission_disposition, "ADMISSION_DISPOSITION_REQUIRED"),
            (self.subject_identity, "SUBJECT_IDENTITY_REQUIRED"),
            (self.source_generation_key, "SOURCE_GENERATION_KEY_REQUIRED"),
            (self.evidence_generation_key, "EVIDENCE_GENERATION_KEY_REQUIRED"),
            (self.owner_context_key, "OWNER_CONTEXT_KEY_REQUIRED"),
            (self.decision_context_key, "DECISION_CONTEXT_KEY_REQUIRED"),
        ):
            _text(value, code)
        if not isinstance(self.bounded_admission_positive, bool):
            raise ValueError("BOUNDED_ADMISSION_POSITIVE_MUST_BE_BOOL")
        if not isinstance(self.candidate_only, bool):
            raise ValueError("CANDIDATE_ONLY_MUST_BE_BOOL")


@dataclass(frozen=True)
class CurrentAdmissionUseContextV1:
    producer_head: str
    subject_identity: str
    source_generation_key: str
    evidence_generation_key: str
    owner_context_key: str
    decision_context_key: str

    def validate_shape(self) -> None:
        for value, code in (
            (self.producer_head, "CURRENT_PRODUCER_HEAD_REQUIRED"),
            (self.subject_identity, "CURRENT_SUBJECT_IDENTITY_REQUIRED"),
            (self.source_generation_key, "CURRENT_SOURCE_GENERATION_REQUIRED"),
            (self.evidence_generation_key, "CURRENT_EVIDENCE_GENERATION_REQUIRED"),
            (self.owner_context_key, "CURRENT_OWNER_CONTEXT_REQUIRED"),
            (self.decision_context_key, "CURRENT_DECISION_CONTEXT_REQUIRED"),
        ):
            _text(value, code)


@dataclass(frozen=True)
class AdmissionReuseReceiptV1:
    disposition: ReuseDisposition
    reason: str
    family: AdmissionFamily
    admission_receipt_digest: str
    subject_identity: str | None
    source_generation_key: str | None
    evidence_generation_key: str | None
    owner_context_key: str | None
    decision_context_key: str | None
    reuse_digest: str
    candidate_only: bool = True
    admission_reused_as_authority: bool = False
    execution_authorized: bool = False
    effect_authorized: bool = False
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def reusable_candidate(self) -> bool:
        return self.disposition is ReuseDisposition.REUSE_CANDIDATE


def _claim_ceiling_breached(admission: AdmissionReceiptProjectionV1) -> bool:
    return any(
        (
            not admission.candidate_only,
            admission.source_currentness_proven,
            admission.semantic_truth_proven,
            admission.evidence_admitted,
            admission.execution_authorized,
            admission.effect_authorized,
            admission.semantic_k27_authority,
            admission.native_private_transformer_kv_accessed,
        )
    )


def _classify_tree(
    admission: AdmissionReceiptProjectionV1,
    current: CurrentAdmissionUseContextV1,
) -> ReuseDisposition:
    if admission.producer_head != EXPECTED_HEAD[admission.family]:
        return ReuseDisposition.HOLD_PARENT_GENERATION
    if (
        admission.admission_disposition != EXPECTED_POSITIVE_DISPOSITION[admission.family]
        or admission.bounded_admission_positive is not True
    ):
        return ReuseDisposition.HOLD_ADMISSION_NOT_POSITIVE
    if _claim_ceiling_breached(admission):
        return ReuseDisposition.HOLD_CLAIM_CEILING
    if current.producer_head != admission.producer_head:
        return ReuseDisposition.HOLD_PRODUCER_GENERATION_CHANGED
    if current.subject_identity != admission.subject_identity:
        return ReuseDisposition.HOLD_SUBJECT_CHANGED
    if current.source_generation_key != admission.source_generation_key:
        return ReuseDisposition.HOLD_SOURCE_GENERATION_CHANGED
    if current.evidence_generation_key != admission.evidence_generation_key:
        return ReuseDisposition.HOLD_EVIDENCE_GENERATION_CHANGED
    if current.owner_context_key != admission.owner_context_key:
        return ReuseDisposition.HOLD_OWNER_CONTEXT_CHANGED
    if current.decision_context_key != admission.decision_context_key:
        return ReuseDisposition.HOLD_DECISION_CONTEXT_CHANGED
    return ReuseDisposition.REUSE_CANDIDATE


def _classify_table(
    admission: AdmissionReceiptProjectionV1,
    current: CurrentAdmissionUseContextV1,
) -> ReuseDisposition:
    ordered = (
        (admission.producer_head != EXPECTED_HEAD[admission.family], ReuseDisposition.HOLD_PARENT_GENERATION),
        (
            admission.admission_disposition != EXPECTED_POSITIVE_DISPOSITION[admission.family]
            or admission.bounded_admission_positive is not True,
            ReuseDisposition.HOLD_ADMISSION_NOT_POSITIVE,
        ),
        (_claim_ceiling_breached(admission), ReuseDisposition.HOLD_CLAIM_CEILING),
        (current.producer_head != admission.producer_head, ReuseDisposition.HOLD_PRODUCER_GENERATION_CHANGED),
        (current.subject_identity != admission.subject_identity, ReuseDisposition.HOLD_SUBJECT_CHANGED),
        (current.source_generation_key != admission.source_generation_key, ReuseDisposition.HOLD_SOURCE_GENERATION_CHANGED),
        (current.evidence_generation_key != admission.evidence_generation_key, ReuseDisposition.HOLD_EVIDENCE_GENERATION_CHANGED),
        (current.owner_context_key != admission.owner_context_key, ReuseDisposition.HOLD_OWNER_CONTEXT_CHANGED),
        (current.decision_context_key != admission.decision_context_key, ReuseDisposition.HOLD_DECISION_CONTEXT_CHANGED),
    )
    for predicate, disposition in ordered:
        if predicate:
            return disposition
    return ReuseDisposition.REUSE_CANDIDATE


def revalidate_admission_reuse(
    *,
    admission: AdmissionReceiptProjectionV1,
    current: CurrentAdmissionUseContextV1,
) -> AdmissionReuseReceiptV1:
    admission.validate_shape()
    current.validate_shape()
    a = _classify_tree(admission, current)
    b = _classify_table(admission, current)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_ADMISSION_REUSE_DIVERGED")

    ready = a is ReuseDisposition.REUSE_CANDIDATE
    reason = {
        ReuseDisposition.REUSE_CANDIDATE: "all identity-bearing producer/source/evidence/owner/decision axes remain exact",
        ReuseDisposition.HOLD_PARENT_GENERATION: "admission projection is not from the pinned terminal-green semantic parent generation",
        ReuseDisposition.HOLD_ADMISSION_NOT_POSITIVE: "historical receipt did not carry the exact bounded positive disposition",
        ReuseDisposition.HOLD_CLAIM_CEILING: "admission projection exceeds the nonpromotion ceiling",
        ReuseDisposition.HOLD_PRODUCER_GENERATION_CHANGED: "producer semantic generation changed",
        ReuseDisposition.HOLD_SUBJECT_CHANGED: "subject identity changed",
        ReuseDisposition.HOLD_SOURCE_GENERATION_CHANGED: "source generation changed",
        ReuseDisposition.HOLD_EVIDENCE_GENERATION_CHANGED: "evidence generation changed",
        ReuseDisposition.HOLD_OWNER_CONTEXT_CHANGED: "owner epoch/context changed",
        ReuseDisposition.HOLD_DECISION_CONTEXT_CHANGED: "route/policy/decision context changed",
    }[a]
    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "reason": reason,
        "family": admission.family.value,
        "admission_receipt_digest": admission.receipt_digest,
        "subject_identity": admission.subject_identity if ready else None,
        "source_generation_key": admission.source_generation_key if ready else None,
        "evidence_generation_key": admission.evidence_generation_key if ready else None,
        "owner_context_key": admission.owner_context_key if ready else None,
        "decision_context_key": admission.decision_context_key if ready else None,
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
    return AdmissionReuseReceiptV1(
        disposition=a,
        reason=reason,
        family=admission.family,
        admission_receipt_digest=admission.receipt_digest,
        subject_identity=admission.subject_identity if ready else None,
        source_generation_key=admission.source_generation_key if ready else None,
        evidence_generation_key=admission.evidence_generation_key if ready else None,
        owner_context_key=admission.owner_context_key if ready else None,
        decision_context_key=admission.decision_context_key if ready else None,
        reuse_digest=_sha(body),
    )


def fixture(family: AdmissionFamily) -> tuple[AdmissionReceiptProjectionV1, CurrentAdmissionUseContextV1]:
    head = EXPECTED_HEAD[family]
    suffix = "hydration" if family is AdmissionFamily.HYDRATION_TRANSACTION else "q18"
    admission = AdmissionReceiptProjectionV1(
        family=family,
        producer_head=head,
        receipt_digest=("1" if family is AdmissionFamily.HYDRATION_TRANSACTION else "2") * 64,
        admission_disposition=EXPECTED_POSITIVE_DISPOSITION[family],
        subject_identity=f"subject:{suffix}",
        source_generation_key=f"source-generation:{suffix}:1",
        evidence_generation_key=f"evidence-generation:{suffix}:1",
        owner_context_key=f"owner-context:{suffix}:1",
        decision_context_key=f"decision-context:{suffix}:1",
        bounded_admission_positive=True,
    )
    current = CurrentAdmissionUseContextV1(
        producer_head=admission.producer_head,
        subject_identity=admission.subject_identity,
        source_generation_key=admission.source_generation_key,
        evidence_generation_key=admission.evidence_generation_key,
        owner_context_key=admission.owner_context_key,
        decision_context_key=admission.decision_context_key,
    )
    return admission, current


def prove_different_j() -> int:
    checked = 0
    for family in AdmissionFamily:
        admission, base = fixture(family)
        for mask in range(64):
            current = CurrentAdmissionUseContextV1(
                producer_head=("f" * 40 if mask & 1 else base.producer_head),
                subject_identity=(base.subject_identity + ":drift" if mask & 2 else base.subject_identity),
                source_generation_key=(base.source_generation_key + ":drift" if mask & 4 else base.source_generation_key),
                evidence_generation_key=(base.evidence_generation_key + ":drift" if mask & 8 else base.evidence_generation_key),
                owner_context_key=(base.owner_context_key + ":drift" if mask & 16 else base.owner_context_key),
                decision_context_key=(base.decision_context_key + ":drift" if mask & 32 else base.decision_context_key),
            )
            if _classify_tree(admission, current) is not _classify_table(admission, current):
                raise AssertionError("DIFFERENT_J_ADMISSION_REUSE_MISMATCH")
            checked += 1
    return checked


LAWS = (
    "AdmissionValidAtProduce!=AdmissionReusableAtUse",
    "CurrentGenerationIdentityBeforeAdmissionReuse",
    "AnyIdentityBearingAdmissionAxisDrift=>HoldRecompute",
    "HistoricalPositiveDisposition!=TimelessLease",
    "ExactReuseCandidate!=ExecutionAuthority",
    "RouteOrPolicyContextChangeRequiresRevalidation",
    "K27Placement!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
