#!/usr/bin/env python3
"""NAV-13D x EKI-4 hydrated version handoff.

D0 / HS1 / NONPROMOTING.

This module binds two independently proven projections:
- NAV-13D hydration completion: exact hydration obligation structurally satisfied.
- EKI-4 version transition envelope: exact version transition plan prepared while
  future read-currentness debt remains carried.

It does not persist, admit evidence, prove truth/currentness, authorize effects,
derive K27 placement, or access native/private transformer KV.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json

SCHEMA = "AURA-NAV13D-EKI4-HYDRATED-VERSION-HANDOFF-v1"
NAV13D_HEAD = "94e278db77aadce3429fa80d8925c751f44cecf6"
NAV13D_RUN = "33435748257"
NAV13D_BLOB = "1612eac627dbc14d603ebae9c1327170500c76e7"
EKI4_HEAD = "162fdb9c69f288090845453a67d1f41da28e8a53"
EKI4_RUN = "33435683382"
EKI4_BLOB = "7ac33764ee238098a2887af96344ed642565ac48"
CONVERGENCE_COMMIT = "55f15c62eef96951c8af35df098efa865702b48c"
HEX = frozenset("0123456789abcdef")
REQUIRED_GUARD_AXES = ("source",)
REQUIRED_EKI2_AXES = ("SOURCE_GENERATION_CURRENT", "SOURCE_BODY_CURRENT")


class HandoffDisposition(str, Enum):
    HANDOFF_READY_CANDIDATE = "HANDOFF_READY_CANDIDATE"
    HOLD_PARENT_GENERATION = "HOLD_PARENT_GENERATION"
    HOLD_COMPLETION_UNSATISFIED = "HOLD_COMPLETION_UNSATISFIED"
    HOLD_TRANSITION_NOT_READY = "HOLD_TRANSITION_NOT_READY"
    HOLD_SUBJECT_MISMATCH = "HOLD_SUBJECT_MISMATCH"
    HOLD_EVIDENCE_GENERATION_MISMATCH = "HOLD_EVIDENCE_GENERATION_MISMATCH"
    HOLD_SOURCE_URI_MISMATCH = "HOLD_SOURCE_URI_MISMATCH"
    HOLD_MATERIAL_DIGEST_MISMATCH = "HOLD_MATERIAL_DIGEST_MISMATCH"
    HOLD_WRITE_CURRENTNESS_UNRESOLVED = "HOLD_WRITE_CURRENTNESS_UNRESOLVED"
    HOLD_READ_DEBT_NOT_CARRIED = "HOLD_READ_DEBT_NOT_CARRIED"
    HOLD_CLAIM_CEILING = "HOLD_CLAIM_CEILING"


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
class HydrationCompletionProjectionV1:
    parent_head: str
    completion_digest: str
    subject_key: str
    evidence_generation_key: str
    material_digest: str
    exact_source_uri: str
    hydration_obligation_satisfied: bool
    source_truth_proven: bool = False
    evidence_admitted: bool = False
    authorization_issued: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _digest(self.completion_digest, "COMPLETION_DIGEST_REQUIRED")
        _digest(self.subject_key, "HYDRATION_SUBJECT_KEY_REQUIRED")
        _digest(self.evidence_generation_key, "HYDRATION_EVIDENCE_GENERATION_REQUIRED")
        _digest(self.material_digest, "HYDRATION_MATERIAL_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "HYDRATION_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class VersionTransitionProjectionV1:
    parent_head: str
    envelope_receipt_digest: str
    disposition: str
    current_subject_key: str
    current_evidence_generation_key: str
    source_content_digest: str
    exact_source_uri: str
    write_currentness_resolved: bool
    read_currentness_debt_carried: bool
    required_future_read_axes: tuple[str, ...]
    required_eki2_read_axes: tuple[str, ...]
    candidate_only: bool = True
    store_mutated: bool = False
    write_authority: bool = False
    effect_authority: bool = False
    semantic_truth_granted: bool = False
    semantic_k27_authority: bool = False
    persisted_currentness_is_witness: bool = False
    native_private_transformer_kv_accessed: bool = False

    def validate_shape(self) -> None:
        _digest(self.envelope_receipt_digest, "ENVELOPE_RECEIPT_DIGEST_REQUIRED")
        _digest(self.current_subject_key, "TRANSITION_SUBJECT_KEY_REQUIRED")
        _digest(self.current_evidence_generation_key, "TRANSITION_EVIDENCE_GENERATION_REQUIRED")
        _digest(self.source_content_digest, "TRANSITION_CONTENT_DIGEST_REQUIRED")
        _text(self.exact_source_uri, "TRANSITION_SOURCE_URI_REQUIRED")


@dataclass(frozen=True)
class HydratedVersionHandoffReceiptV1:
    disposition: HandoffDisposition
    reason: str
    hydration_completion_digest: str
    transition_receipt_digest: str
    subject_key: str | None
    evidence_generation_key: str | None
    material_digest: str | None
    exact_source_uri: str | None
    future_read_axes: tuple[str, ...]
    eki2_read_axes: tuple[str, ...]
    handoff_digest: str
    candidate_only: bool = True
    persistent_write_authorized: bool = False
    evidence_admitted: bool = False
    source_truth_proven: bool = False
    read_currentness_proven: bool = False
    effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False

    @property
    def ready(self) -> bool:
        return self.disposition is HandoffDisposition.HANDOFF_READY_CANDIDATE


def _ceiling_breached(
    hydration: HydrationCompletionProjectionV1,
    transition: VersionTransitionProjectionV1,
) -> bool:
    return any(
        (
            hydration.source_truth_proven,
            hydration.evidence_admitted,
            hydration.authorization_issued,
            hydration.semantic_k27_authority,
            hydration.native_private_transformer_kv_accessed,
            not transition.candidate_only,
            transition.store_mutated,
            transition.write_authority,
            transition.effect_authority,
            transition.semantic_truth_granted,
            transition.semantic_k27_authority,
            transition.persisted_currentness_is_witness,
            transition.native_private_transformer_kv_accessed,
        )
    )


def _classify_tree(
    hydration: HydrationCompletionProjectionV1,
    transition: VersionTransitionProjectionV1,
) -> HandoffDisposition:
    if hydration.parent_head != NAV13D_HEAD or transition.parent_head != EKI4_HEAD:
        return HandoffDisposition.HOLD_PARENT_GENERATION
    if _ceiling_breached(hydration, transition):
        return HandoffDisposition.HOLD_CLAIM_CEILING
    if hydration.hydration_obligation_satisfied is not True:
        return HandoffDisposition.HOLD_COMPLETION_UNSATISFIED
    if transition.disposition != "VERSION_TRANSITION_PLAN_READY":
        return HandoffDisposition.HOLD_TRANSITION_NOT_READY
    if hydration.subject_key != transition.current_subject_key:
        return HandoffDisposition.HOLD_SUBJECT_MISMATCH
    if hydration.evidence_generation_key != transition.current_evidence_generation_key:
        return HandoffDisposition.HOLD_EVIDENCE_GENERATION_MISMATCH
    if hydration.exact_source_uri != transition.exact_source_uri:
        return HandoffDisposition.HOLD_SOURCE_URI_MISMATCH
    if hydration.material_digest != transition.source_content_digest:
        return HandoffDisposition.HOLD_MATERIAL_DIGEST_MISMATCH
    if transition.write_currentness_resolved is not True:
        return HandoffDisposition.HOLD_WRITE_CURRENTNESS_UNRESOLVED
    if (
        transition.read_currentness_debt_carried is not True
        or transition.required_future_read_axes != REQUIRED_GUARD_AXES
        or transition.required_eki2_read_axes != REQUIRED_EKI2_AXES
    ):
        return HandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED
    return HandoffDisposition.HANDOFF_READY_CANDIDATE


def _classify_rules(
    hydration: HydrationCompletionProjectionV1,
    transition: VersionTransitionProjectionV1,
) -> HandoffDisposition:
    rules = (
        (hydration.parent_head != NAV13D_HEAD or transition.parent_head != EKI4_HEAD, HandoffDisposition.HOLD_PARENT_GENERATION),
        (_ceiling_breached(hydration, transition), HandoffDisposition.HOLD_CLAIM_CEILING),
        (hydration.hydration_obligation_satisfied is not True, HandoffDisposition.HOLD_COMPLETION_UNSATISFIED),
        (transition.disposition != "VERSION_TRANSITION_PLAN_READY", HandoffDisposition.HOLD_TRANSITION_NOT_READY),
        (hydration.subject_key != transition.current_subject_key, HandoffDisposition.HOLD_SUBJECT_MISMATCH),
        (hydration.evidence_generation_key != transition.current_evidence_generation_key, HandoffDisposition.HOLD_EVIDENCE_GENERATION_MISMATCH),
        (hydration.exact_source_uri != transition.exact_source_uri, HandoffDisposition.HOLD_SOURCE_URI_MISMATCH),
        (hydration.material_digest != transition.source_content_digest, HandoffDisposition.HOLD_MATERIAL_DIGEST_MISMATCH),
        (transition.write_currentness_resolved is not True, HandoffDisposition.HOLD_WRITE_CURRENTNESS_UNRESOLVED),
        (
            transition.read_currentness_debt_carried is not True
            or transition.required_future_read_axes != REQUIRED_GUARD_AXES
            or transition.required_eki2_read_axes != REQUIRED_EKI2_AXES,
            HandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED,
        ),
    )
    for predicate, disposition in rules:
        if predicate:
            return disposition
    return HandoffDisposition.HANDOFF_READY_CANDIDATE


def bind_hydrated_version_handoff(
    *,
    hydration: HydrationCompletionProjectionV1,
    transition: VersionTransitionProjectionV1,
) -> HydratedVersionHandoffReceiptV1:
    hydration.validate_shape()
    transition.validate_shape()
    a = _classify_tree(hydration, transition)
    b = _classify_rules(hydration, transition)
    if a is not b:
        raise RuntimeError("DIFFERENT_J_HANDOFF_CLASSIFIERS_DIVERGED")

    ready = a is HandoffDisposition.HANDOFF_READY_CANDIDATE
    reason = {
        HandoffDisposition.HANDOFF_READY_CANDIDATE: "exact hydration and version-transition identities commute; future read debt remains carried",
        HandoffDisposition.HOLD_PARENT_GENERATION: "parent semantic generation mismatch",
        HandoffDisposition.HOLD_COMPLETION_UNSATISFIED: "hydration obligation not structurally satisfied",
        HandoffDisposition.HOLD_TRANSITION_NOT_READY: "version transition plan is not ready",
        HandoffDisposition.HOLD_SUBJECT_MISMATCH: "subject identity mismatch",
        HandoffDisposition.HOLD_EVIDENCE_GENERATION_MISMATCH: "evidence generation mismatch",
        HandoffDisposition.HOLD_SOURCE_URI_MISMATCH: "exact source URI mismatch",
        HandoffDisposition.HOLD_MATERIAL_DIGEST_MISMATCH: "hydrated material does not match transition content digest",
        HandoffDisposition.HOLD_WRITE_CURRENTNESS_UNRESOLVED: "write currentness unresolved",
        HandoffDisposition.HOLD_READ_DEBT_NOT_CARRIED: "future read-currentness obligation not carried exactly",
        HandoffDisposition.HOLD_CLAIM_CEILING: "upstream projection exceeds nonpromotion ceiling",
    }[a]

    body = {
        "schema": SCHEMA,
        "disposition": a.value,
        "reason": reason,
        "hydration_completion_digest": hydration.completion_digest,
        "transition_receipt_digest": transition.envelope_receipt_digest,
        "subject_key": hydration.subject_key if ready else None,
        "evidence_generation_key": hydration.evidence_generation_key if ready else None,
        "material_digest": hydration.material_digest if ready else None,
        "exact_source_uri": hydration.exact_source_uri if ready else None,
        "future_read_axes": transition.required_future_read_axes if ready else (),
        "eki2_read_axes": transition.required_eki2_read_axes if ready else (),
        "claim_ceiling": {
            "candidate_only": True,
            "persistent_write_authorized": False,
            "evidence_admitted": False,
            "source_truth_proven": False,
            "read_currentness_proven": False,
            "effect_authorized": False,
            "semantic_k27_authority": False,
            "native_private_transformer_kv_accessed": False,
        },
    }
    return HydratedVersionHandoffReceiptV1(
        disposition=a,
        reason=reason,
        hydration_completion_digest=hydration.completion_digest,
        transition_receipt_digest=transition.envelope_receipt_digest,
        subject_key=hydration.subject_key if ready else None,
        evidence_generation_key=hydration.evidence_generation_key if ready else None,
        material_digest=hydration.material_digest if ready else None,
        exact_source_uri=hydration.exact_source_uri if ready else None,
        future_read_axes=transition.required_future_read_axes if ready else (),
        eki2_read_axes=transition.required_eki2_read_axes if ready else (),
        handoff_digest=_sha(body),
    )


def prove_different_j() -> int:
    d0, d1 = "0" * 64, "1" * 64
    base_h = HydrationCompletionProjectionV1(NAV13D_HEAD, d0, d0, d1, d0, "https://example.test/source", True)
    base_t = VersionTransitionProjectionV1(
        EKI4_HEAD,
        d1,
        "VERSION_TRANSITION_PLAN_READY",
        d0,
        d1,
        d0,
        "https://example.test/source",
        True,
        True,
        REQUIRED_GUARD_AXES,
        REQUIRED_EKI2_AXES,
    )
    checked = 0
    for completion in (False, True):
        for transition_ready in (False, True):
            for subject_match in (False, True):
                for evidence_match in (False, True):
                    for material_match in (False, True):
                        for write_current in (False, True):
                            for read_debt in (False, True):
                                h = HydrationCompletionProjectionV1(**{**asdict(base_h), "hydration_obligation_satisfied": completion})
                                t = VersionTransitionProjectionV1(
                                    **{
                                        **asdict(base_t),
                                        "disposition": "VERSION_TRANSITION_PLAN_READY" if transition_ready else "WRITE_CURRENTNESS_REQUIRED",
                                        "current_subject_key": d0 if subject_match else d1,
                                        "current_evidence_generation_key": d1 if evidence_match else d0,
                                        "source_content_digest": d0 if material_match else d1,
                                        "write_currentness_resolved": write_current,
                                        "read_currentness_debt_carried": read_debt,
                                    }
                                )
                                if _classify_tree(h, t) is not _classify_rules(h, t):
                                    raise AssertionError("DIFFERENT_J_HANDOFF_MISMATCH")
                                checked += 1
    return checked


LAWS = (
    "HydrationCompletion!=EvidenceAdmission!=PersistentWrite",
    "VersionTransitionPlan!=PersistentWrite",
    "HydratedMaterialDigestMustEqualTransitionSourceContentDigest",
    "HydrationSubjectAndEvidenceGenerationMustCommuteWithVersionTransition",
    "CurrentAtWrite!=CurrentAtRead",
    "FutureReadCurrentnessDebtMustSurviveHandoff",
    "K27Placement!=SemanticIdentity!=VersionOrder!=Currentness!=Authority",
    "CoordinateMemory!=MODEL_PREFIX_KV",
)
