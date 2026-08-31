#!/usr/bin/env python3
"""NAV-14 progress-bound hydrated version handoff.

D0 / HS1 / NONPROMOTING.

This relation consumes two independently earned surfaces:
- PR #760: exact hydrated-version HANDOFF_READY_CANDIDATE;
- PR #754: exact retrieval-progress receipt.

It prevents an identical no-progress retrieval, a collapsed retrieval cone, or a
mere fingerprint-axis change from being used as the progress basis for a new
hydrated-version handoff candidate. It does not retrieve, persist, admit
evidence, prove truth/currentness, authorize effects, derive K27 semantics, or
access native/private transformer KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json

SCHEMA = "AURA-NAV14-PROGRESS-BOUND-HYDRATED-VERSION-HANDOFF-v1"
HANDOFF_HEAD = "1a7ab9d884acc917ea28bea2b28bc747222f1aed"
HANDOFF_RUN = "33436321891"
HANDOFF_BLOB = "edac88e89e0659cd6bbf99c7a138e2ae3f516ae8"
RETRIEVAL_HEAD = "412e683b8a3d28bd57e4dc39059283cc823e2fb3"
RETRIEVAL_RUN = "33435590114"
RETRIEVAL_JOB = "99631099474"
RETRIEVAL_BLOB = "5e20a51af1bbafa17c56b3a80125bcf003cc6b62"
REQUIRED_PURPOSE = "hydrate-version-handoff"
REQUIRED_FUTURE_READ_AXES = ("source",)
REQUIRED_EKI2_AXES = ("SOURCE_GENERATION_CURRENT", "SOURCE_BODY_CURRENT")
HEX = frozenset("0123456789abcdef")


class RetrievalDecision(str, Enum):
    ALLOW_INITIAL = "ALLOW_INITIAL"
    ALLOW_CHANGED_AXIS = "ALLOW_CHANGED_AXIS"
    ALLOW_STATE_TRANSITION = "ALLOW_STATE_TRANSITION"
    CHANGE_AXIS_REQUIRED = "CHANGE_AXIS_REQUIRED"
    COLLAPSE_CONE = "COLLAPSE_CONE"


class ProgressHandoffDisposition(str, Enum):
    PROGRESS_BOUND_HANDOFF_CANDIDATE = "PROGRESS_BOUND_HANDOFF_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_HANDOFF_NOT_READY = "HOLD_HANDOFF_NOT_READY"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"
    HOLD_READ_DEBT_NOT_CARRIED = "HOLD_READ_DEBT_NOT_CARRIED"
    HOLD_EVIDENCE_DIGEST_MISMATCH = "HOLD_EVIDENCE_DIGEST_MISMATCH"
    HOLD_PURPOSE_MISMATCH = "HOLD_PURPOSE_MISMATCH"
    HOLD_RETRIEVAL_AXIS_ONLY = "HOLD_RETRIEVAL_AXIS_ONLY"
    HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED = "HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED"
    HOLD_RETRIEVAL_CONE_COLLAPSED = "HOLD_RETRIEVAL_CONE_COLLAPSED"


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
class HydratedVersionHandoffProjectionV1:
    parent_head: str
    handoff_digest: str
    disposition: str
    subject_key: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    future_read_axes: tuple[str, ...]
    eki2_read_axes: tuple[str, ...]
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _digest(self.handoff_digest, "HANDOFF_DIGEST_REQUIRED")
        _digest(self.subject_key, "SUBJECT_KEY_REQUIRED")
        _digest(self.evidence_generation_key, "EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class RetrievalProgressProjectionV1:
    parent_head: str
    decision: RetrievalDecision
    provider: str
    tool: str
    resource: str
    query_or_pattern: str
    page_or_range: str
    semantic_purpose: str
    provider_state_generation: str
    evidence_digest: str
    fingerprint_digest: str
    prior_no_progress_count: int
    next_no_progress_count: int
    fingerprint_changed: bool
    provider_state_changed: bool
    evidence_changed: bool
    receipt_digest: str
    source_currentness_proven: bool = False
    semantic_truth_proven: bool = False
    authority_granted: bool = False
    effect_authority_granted: bool = False
    native_private_transformer_kv_accessed: bool = False

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "provider": _text(self.provider, "PROVIDER_REQUIRED"),
            "tool": _text(self.tool, "TOOL_REQUIRED"),
            "resource": _text(self.resource, "RESOURCE_REQUIRED"),
            "query_or_pattern": _text(self.query_or_pattern, "QUERY_REQUIRED"),
            "page_or_range": _text(self.page_or_range, "PAGE_OR_RANGE_REQUIRED"),
            "semantic_purpose": _text(self.semantic_purpose, "PURPOSE_REQUIRED"),
        }

    def validate_shape(self) -> None:
        _text(self.provider_state_generation, "PROVIDER_STATE_GENERATION_REQUIRED")
        _digest(self.evidence_digest, "RETRIEVAL_EVIDENCE_DIGEST_REQUIRED")
        _digest(self.fingerprint_digest, "FINGERPRINT_DIGEST_REQUIRED")
        _digest(self.receipt_digest, "RETRIEVAL_RECEIPT_DIGEST_REQUIRED")
        if not isinstance(self.prior_no_progress_count, int) or isinstance(
            self.prior_no_progress_count, bool
        ):
            raise ValueError("PRIOR_NO_PROGRESS_COUNT_INVALID")
        if not isinstance(self.next_no_progress_count, int) or isinstance(
            self.next_no_progress_count, bool
        ):
            raise ValueError("NEXT_NO_PROGRESS_COUNT_INVALID")
        if self.prior_no_progress_count < 0 or self.next_no_progress_count < 0:
            raise ValueError("NO_PROGRESS_COUNT_NEGATIVE")
        if self.fingerprint_digest != _sha(self.fingerprint_payload()):
            raise ValueError("FINGERPRINT_DIGEST_MISMATCH")
        if self.receipt_digest != _parent_receipt_digest(self):
            raise ValueError("RETRIEVAL_RECEIPT_DIGEST_MISMATCH")
        _validate_decision_shape(self)


@dataclass(frozen=True)
class ProgressBoundHandoffReceiptV1:
    disposition: ProgressHandoffDisposition
    reason: str
    handoff_digest: str
    retrieval_receipt_digest: str
    retrieval_decision: RetrievalDecision
    subject_key: str | None
    evidence_generation_key: str | None
    material_digest: str | None
    exact_source_uri: str | None
    progress_handoff_digest: str
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    source_currentness_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def ready(self) -> bool:
        return self.disposition is ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE


def _parent_receipt_digest(retrieval: RetrievalProgressProjectionV1) -> str:
    payload = {
        "decision": retrieval.decision.value,
        "fingerprint_digest": retrieval.fingerprint_digest,
        "prior_no_progress_count": retrieval.prior_no_progress_count,
        "next_no_progress_count": retrieval.next_no_progress_count,
        "fingerprint_changed": retrieval.fingerprint_changed,
        "provider_state_changed": retrieval.provider_state_changed,
        "evidence_changed": retrieval.evidence_changed,
        "claim_ceiling": {
            "source_currentness_proven": False,
            "semantic_truth_proven": False,
            "authority_granted": False,
            "effect_authority_granted": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return _sha(payload)


def _validate_decision_shape(retrieval: RetrievalProgressProjectionV1) -> None:
    d = retrieval.decision
    fp = retrieval.fingerprint_changed
    state = retrieval.provider_state_changed
    evidence = retrieval.evidence_changed
    prior = retrieval.prior_no_progress_count
    nxt = retrieval.next_no_progress_count
    valid = False
    if d is RetrievalDecision.ALLOW_INITIAL:
        valid = prior == 0 and nxt == 0 and not fp and not state and not evidence
    elif d is RetrievalDecision.ALLOW_CHANGED_AXIS:
        valid = fp and nxt == 0
    elif d is RetrievalDecision.ALLOW_STATE_TRANSITION:
        valid = not fp and (state or evidence) and nxt == 0
    elif d is RetrievalDecision.CHANGE_AXIS_REQUIRED:
        valid = not fp and not state and not evidence and prior == 0 and nxt == 1
    elif d is RetrievalDecision.COLLAPSE_CONE:
        valid = not fp and not state and not evidence and prior >= 1 and nxt == prior + 1
    if not valid:
        raise ValueError("RETRIEVAL_DECISION_SHAPE_INVALID")


def _ceiling_breached(
    handoff: HydratedVersionHandoffProjectionV1,
    retrieval: RetrievalProgressProjectionV1,
) -> bool:
    return any(
        (
            not handoff.candidate_only,
            handoff.persistent_write_authorized,
            handoff.evidence_admitted,
            handoff.source_truth_proven,
            handoff.read_currentness_proven,
            handoff.effect_authorized,
            handoff.semantic_k27_authority,
            handoff.native_private_transformer_kv_accessed,
            retrieval.source_currentness_proven,
            retrieval.semantic_truth_proven,
            retrieval.authority_granted,
            retrieval.effect_authority_granted,
            retrieval.native_private_transformer_kv_accessed,
        )
    )


def _classify_tree(
    handoff: HydratedVersionHandoffProjectionV1,
    retrieval: RetrievalProgressProjectionV1,
) -> ProgressHandoffDisposition:
    if handoff.parent_head != HANDOFF_HEAD or retrieval.parent_head != RETRIEVAL_HEAD:
        return ProgressHandoffDisposition.HOLD_PARENT_GENERATION
    if _ceiling_breached(handoff, retrieval):
        return ProgressHandoffDisposition.HOLD_CLAIM_CEILING
    if handoff.disposition != "HANDOFF_READY_CANDIDATE":
        return ProgressHandoffDisposition.HOLD_HANDOFF_NOT_READY
    if (
        handoff.future_read_axes != REQUIRED_FUTURE_READ_AXES
        or handoff.eki2_read_axes != REQUIRED_EKI2_AXES
    ):
        return ProgressHandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED
    if retrieval.evidence_digest != handoff.material_digest:
        return ProgressHandoffDisposition.HOLD_EVIDENCE_DIGEST_MISMATCH
    if retrieval.semantic_purpose != REQUIRED_PURPOSE:
        return ProgressHandoffDisposition.HOLD_PURPOSE_MISMATCH
    if retrieval.decision is RetrievalDecision.CHANGE_AXIS_REQUIRED:
        return ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED
    if retrieval.decision is RetrievalDecision.COLLAPSE_CONE:
        return ProgressHandoffDisposition.HOLD_RETRIEVAL_CONE_COLLAPSED
    if retrieval.decision is RetrievalDecision.ALLOW_CHANGED_AXIS:
        return ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_ONLY
    return ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE


def _classify_rules(
    handoff: HydratedVersionHandoffProjectionV1,
    retrieval: RetrievalProgressProjectionV1,
) -> ProgressHandoffDisposition:
    rules = (
        (
            handoff.parent_head != HANDOFF_HEAD or retrieval.parent_head != RETRIEVAL_HEAD,
            ProgressHandoffDisposition.HOLD_PARENT_GENERATION,
        ),
        (_ceiling_breached(handoff, retrieval), ProgressHandoffDisposition.HOLD_CLAIM_CEILING),
        (
            handoff.disposition != "HANDOFF_READY_CANDIDATE",
            ProgressHandoffDisposition.HOLD_HANDOFF_NOT_READY,
        ),
        (
            handoff.future_read_axes != REQUIRED_FUTURE_READ_AXES
            or handoff.eki2_read_axes != REQUIRED_EKI2_AXES,
            ProgressHandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED,
        ),
        (
            retrieval.evidence_digest != handoff.material_digest,
            ProgressHandoffDisposition.HOLD_EVIDENCE_DIGEST_MISMATCH,
        ),
        (
            retrieval.semantic_purpose != REQUIRED_PURPOSE,
            ProgressHandoffDisposition.HOLD_PURPOSE_MISMATCH,
        ),
        (
            retrieval.decision is RetrievalDecision.CHANGE_AXIS_REQUIRED,
            ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED,
        ),
        (
            retrieval.decision is RetrievalDecision.COLLAPSE_CONE,
            ProgressHandoffDisposition.HOLD_RETRIEVAL_CONE_COLLAPSED,
        ),
        (
            retrieval.decision is RetrievalDecision.ALLOW_CHANGED_AXIS,
            ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_ONLY,
        ),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE


def bind_progress_bound_handoff(
    *,
    handoff: HydratedVersionHandoffProjectionV1,
    retrieval: RetrievalProgressProjectionV1,
) -> ProgressBoundHandoffReceiptV1:
    handoff.validate_shape()
    retrieval.validate_shape()
    a = _classify_tree(handoff, retrieval)
    b = _classify_rules(handoff, retrieval)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_PROGRESS_HANDOFF_CLASSIFIERS_DIVERGED")

    ready = a is ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE
    reason = {
        ProgressHandoffDisposition.PROGRESS_BOUND_HANDOFF_CANDIDATE: "exact handoff material is bound to initial retrieval or an independent provider/evidence state transition",
        ProgressHandoffDisposition.HOLD_PARENT_GENERATION: "parent semantic generation mismatch",
        ProgressHandoffDisposition.HOLD_HANDOFF_NOT_READY: "hydrated version handoff is not candidate-ready",
        ProgressHandoffDisposition.HOLD_CLAIM_CEILING: "upstream projection exceeds nonpromotion ceiling",
        ProgressHandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED: "future read-currentness debt is not preserved exactly",
        ProgressHandoffDisposition.HOLD_EVIDENCE_DIGEST_MISMATCH: "retrieval evidence does not bind the exact hydrated material",
        ProgressHandoffDisposition.HOLD_PURPOSE_MISMATCH: "retrieval semantic purpose is not this handoff",
        ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_ONLY: "fingerprint-axis change alone cannot mint a new hydrated-version handoff consequence",
        ProgressHandoffDisposition.HOLD_RETRIEVAL_AXIS_CHANGE_REQUIRED: "identical no-progress retrieval must change axis before further work",
        ProgressHandoffDisposition.HOLD_RETRIEVAL_CONE_COLLAPSED: "repeated no-progress retrieval cone is collapsed",
    }[a]

    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "reason": reason,
        "handoff_digest": handoff.handoff_digest,
        "retrieval_receipt_digest": retrieval.receipt_digest,
        "retrieval_decision": retrieval.decision.value,
        "subject_key": handoff.subject_key if ready else None,
        "evidence_generation_key": handoff.evidence_generation_key if ready else None,
        "material_digest": handoff.material_digest if ready else None,
        "exact_source_uri": handoff.exact_source_uri if ready else None,
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
    return ProgressBoundHandoffReceiptV1(
        disposition=a,
        reason=reason,
        handoff_digest=handoff.handoff_digest,
        retrieval_receipt_digest=retrieval.receipt_digest,
        retrieval_decision=retrieval.decision,
        subject_key=handoff.subject_key if ready else None,
        evidence_generation_key=handoff.evidence_generation_key if ready else None,
        material_digest=handoff.material_digest if ready else None,
        exact_source_uri=handoff.exact_source_uri if ready else None,
        progress_handoff_digest=_sha(body),
    )


def _retrieval_fixture(
    decision: RetrievalDecision,
    *,
    evidence_digest: str,
    purpose: str = REQUIRED_PURPOSE,
    ceiling: bool = False,
) -> RetrievalProgressProjectionV1:
    fp_changed = decision is RetrievalDecision.ALLOW_CHANGED_AXIS
    state_changed = decision is RetrievalDecision.ALLOW_STATE_TRANSITION
    evidence_changed = False
    prior = 1 if decision is RetrievalDecision.COLLAPSE_CONE else 0
    nxt = prior + 1 if decision in {RetrievalDecision.CHANGE_AXIS_REQUIRED, RetrievalDecision.COLLAPSE_CONE} else 0
    payload = {
        "provider": "drive",
        "tool": "fetch",
        "resource": "external-source",
        "query_or_pattern": "exact",
        "page_or_range": "0:1",
        "semantic_purpose": purpose,
    }
    projection = RetrievalProgressProjectionV1(
        parent_head=RETRIEVAL_HEAD,
        decision=decision,
        provider=payload["provider"],
        tool=payload["tool"],
        resource=payload["resource"],
        query_or_pattern=payload["query_or_pattern"],
        page_or_range=payload["page_or_range"],
        semantic_purpose=payload["semantic_purpose"],
        provider_state_generation="g1" if state_changed else "g0",
        evidence_digest=evidence_digest,
        fingerprint_digest=_sha(payload),
        prior_no_progress_count=prior,
        next_no_progress_count=nxt,
        fingerprint_changed=fp_changed,
        provider_state_changed=state_changed,
        evidence_changed=evidence_changed,
        receipt_digest="0" * 64,
        source_currentness_proven=ceiling,
    )
    return RetrievalProgressProjectionV1(**{**asdict(projection), "receipt_digest": _parent_receipt_digest(projection)})


def prove_different_j() -> int:
    d0, d1, d2 = "0" * 64, "1" * 64, "2" * 64
    base_handoff = HydratedVersionHandoffProjectionV1(
        HANDOFF_HEAD,
        d0,
        "HANDOFF_READY_CANDIDATE",
        d1,
        d2,
        d0,
        "https://example.test/source",
        REQUIRED_FUTURE_READ_AXES,
        REQUIRED_EKI2_AXES,
    )
    checked = 0
    for handoff_ready in (False, True):
        for decision in RetrievalDecision:
            for evidence_match in (False, True):
                for purpose_match in (False, True):
                    for ceiling in (False, True):
                        handoff = HydratedVersionHandoffProjectionV1(
                            **{
                                **asdict(base_handoff),
                                "disposition": "HANDOFF_READY_CANDIDATE" if handoff_ready else "HOLD_TRANSITION_NOT_READY",
                            }
                        )
                        retrieval = _retrieval_fixture(
                            decision,
                            evidence_digest=d0 if evidence_match else d1,
                            purpose=REQUIRED_PURPOSE if purpose_match else "other-purpose",
                            ceiling=ceiling,
                        )
                        retrieval.validate_shape()
                        if _classify_tree(handoff, retrieval) is not _classify_rules(handoff, retrieval):
                            raise AssertionError("DIFFERENT_J_PROGRESS_HANDOFF_MISMATCH")
                        checked += 1
    return checked


LAWS = (
    "HandoffReadyCandidate!=PersistentUseReady",
    "RetrievalActivity!=RetrievalProgress",
    "IdenticalNoProgressRetrievalCannotMintHandoffConsequence",
    "CollapsedRetrievalConeCannotMintHandoffConsequence",
    "FingerprintAxisChangeAloneCannotMintHandoffConsequence",
    "InitialOrIndependentProviderEvidenceTransitionMaySupportCandidateOnly",
    "RetrievalEvidenceDigestMustEqualHydratedMaterialDigest",
    "CurrentAtWrite!=CurrentAtRead",
    "FutureReadCurrentnessDebtMustSurviveHandoff",
    "K27Path!=SemanticIdentity!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
