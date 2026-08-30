"""Four-leaf BugHound candidate-evidence trust join.

The public consequence path traverses the source-owned independent-reproduction
registry from ``registered_reproduction_gate`` and independently authenticates
duplicate-check, report-lint, and program-admissibility artifacts against a
second source-owned exact-artifact registry.

Production registries are intentionally empty until independently observed
producer records are pinned by source change. Passing this software membrane is
D0 evidence only: it grants no live-target, credential, submission, payment,
deployment, or other external-effect authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
from typing import Any

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.registered_reproduction_gate import (
    BugHoundRegisteredIndependentReproductionAdmissionV1,
    admit_with_registered_independent_reproduction,
)

DUPLICATE_PLANE = "DUPLICATE_CHECK"
REPORT_LINT_PLANE = "REPORT_LINT"
PROGRAM_PLANE = "PROGRAM_ADMISSIBILITY"
REGISTRY_GENERATION = "BUGHOUND_CANDIDATE_LEAF_REGISTRY_HOLD_V2"


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _false(value: object, field: str, code: str) -> None:
    if getattr(value, field, None) is not False:
        raise ValueError(code)


@dataclass(frozen=True)
class DuplicateCheckEvidenceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    duplicate_pressure_state: str
    duplicate_check_currentness_ref: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = False
    external_effect: bool = False
    schema: str = "DuplicateCheckEvidenceV1"

    @property
    def artifact_digest(self) -> str:
        return _digest("AURA_BUGHOUND_DUPLICATE_CHECK_EVIDENCE_V1", asdict(self))


@dataclass(frozen=True)
class ReportLintEvidenceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    report_lint_state: str
    report_digest: str
    lint_policy_generation: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = False
    external_effect: bool = False
    schema: str = "ReportLintEvidenceV1"

    @property
    def artifact_digest(self) -> str:
        return _digest("AURA_BUGHOUND_REPORT_LINT_EVIDENCE_V1", asdict(self))


@dataclass(frozen=True)
class ProgramAdmissibilityEvidenceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    program_admissibility_state: str
    program_admissibility_ref: str
    scope_rules_digest: str
    payout_rules_digest: str
    source_currentness_ref: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = False
    external_effect: bool = False
    schema: str = "ProgramAdmissibilityEvidenceV1"

    @property
    def artifact_digest(self) -> str:
        return _digest("AURA_BUGHOUND_PROGRAM_ADMISSIBILITY_EVIDENCE_V1", asdict(self))


@dataclass(frozen=True)
class CandidateLeafProducerRecordV1:
    proof_plane: str
    artifact_digest: str
    candidate_id: str
    target_ref: str
    target_generation: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    registry_receipt_ref: str
    registry_observer_ref: str
    registry_observer_generation: str
    registry_currentness_ref: str
    independently_observed: bool = True
    current: bool = True
    revoked: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateLeafProducerRecordV1"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_LEAF_PRODUCER_RECORD_V1", asdict(self))


# Production trust root for duplicate/lint/program artifacts. Deliberately empty.
_CANONICAL_LEAF_RECORDS: tuple[CandidateLeafProducerRecordV1, ...] = ()


@dataclass(frozen=True)
class CandidateLeafRegistryReceiptV2:
    registry_generation: str
    record_digests: tuple[str, ...]
    duplicate_record_count: int
    report_lint_record_count: int
    program_record_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateLeafRegistryReceiptV2"

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_LEAF_REGISTRY_RECEIPT_V2", asdict(self))


@dataclass(frozen=True)
class CandidateEvidenceTrustJoinReceiptV2:
    candidate_id: str
    target_ref: str
    target_generation: str
    reproduction_admission_digest: str
    reproduction_registry_record_digest: str
    duplicate_artifact_digest: str
    duplicate_registry_record_digest: str
    report_lint_artifact_digest: str
    report_lint_registry_record_digest: str
    program_artifact_digest: str
    program_registry_record_digest: str
    leaf_registry_generation: str
    leaf_registry_digest: str
    independent_reproduction_registry_proven: bool = True
    duplicate_check_producer_proven: bool = True
    report_lint_producer_proven: bool = True
    program_admissibility_producer_proven: bool = True
    candidate_evidence_trust_proven: bool = True
    ready_for_human_review_evidence: bool = True
    human_authorization_verified: bool = False
    ready_for_human_review: bool = False
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceTrustJoinReceiptV2"

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_TRUST_JOIN_V2", asdict(self))


def candidate_leaf_registry_receipt() -> CandidateLeafRegistryReceiptV2:
    records = tuple(sorted(_CANONICAL_LEAF_RECORDS, key=lambda item: item.record_digest))
    active = tuple(r for r in records if r.independently_observed and r.current and not r.revoked and not r.authority and not r.external_effect)
    return CandidateLeafRegistryReceiptV2(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(r.record_digest for r in records),
        duplicate_record_count=sum(r.proof_plane == DUPLICATE_PLANE for r in active),
        report_lint_record_count=sum(r.proof_plane == REPORT_LINT_PLANE for r in active),
        program_record_count=sum(r.proof_plane == PROGRAM_PLANE for r in active),
    )


def _verify_leaf_subjects(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    duplicate: DuplicateCheckEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> None:
    if candidate.target_ref != mission_input.target_ref or candidate.target_generation != mission_input.target_generation:
        raise ValueError("CANDIDATE_MISSION_SUBJECT_MISMATCH")
    for leaf, prefix in ((duplicate, "DUPLICATE"), (report_lint, "REPORT_LINT"), (program, "PROGRAM")):
        if leaf.candidate_id != candidate.candidate_id or leaf.target_ref != candidate.target_ref or leaf.target_generation != candidate.target_generation:
            raise ValueError("CANDIDATE_EVIDENCE_LEAF_SUBJECT_MISMATCH")
        _required(prefix + "_PRODUCER_REF", leaf.producer_ref)
        _required(prefix + "_PRODUCER_GENERATION", leaf.producer_generation)
        _required(prefix + "_PRODUCER_CURRENTNESS_REF", leaf.producer_currentness_ref)
        _false(leaf, "authority", prefix + "_AUTHORITY_WIDENED")
        _false(leaf, "external_effect", prefix + "_EXTERNAL_EFFECT_FORBIDDEN")

    _required("DUPLICATE_CHECK_CURRENTNESS_REF", duplicate.duplicate_check_currentness_ref)
    if duplicate.duplicate_pressure_state == "PUBLICLY_KNOWN_ROOT_CAUSE":
        raise ValueError("PUBLIC_ROOT_CAUSE_ALREADY_KNOWN")
    if duplicate.duplicate_pressure_state == "HIGH_DUPLICATE_PRESSURE":
        raise ValueError("MANUAL_DUPLICATE_REVIEW_REQUIRED")
    if duplicate.duplicate_pressure_state not in {"LOW_OBSERVED_DUPLICATE_PRESSURE", "MEDIUM_DUPLICATE_PRESSURE"}:
        raise ValueError("DUPLICATE_PRESSURE_UNRESOLVED")

    _required("REPORT_DIGEST", report_lint.report_digest)
    _required("LINT_POLICY_GENERATION", report_lint.lint_policy_generation)
    if report_lint.report_lint_state != "REPORT_LINT_CLEAN":
        raise ValueError("REPORT_LINT_REQUIRED")

    _required("PROGRAM_ADMISSIBILITY_REF", program.program_admissibility_ref)
    if program.program_admissibility_state != "CURRENTLY_ADMISSIBLE":
        raise ValueError("PROGRAM_ADMISSIBILITY_REQUIRED")
    if program.scope_rules_digest != mission_input.scope_rules_digest:
        raise ValueError("PROGRAM_SCOPE_MISSION_SCOPE_MISMATCH")
    if program.payout_rules_digest != mission_input.payout_rules_digest:
        raise ValueError("PROGRAM_PAYOUT_MISSION_PAYOUT_MISMATCH")
    if program.source_currentness_ref != mission_input.source_currentness_ref:
        raise ValueError("PROGRAM_SOURCE_MISSION_SOURCE_MISMATCH")


def _verify_reproduction_admission(
    admission: BugHoundRegisteredIndependentReproductionAdmissionV1,
    candidate: BountyCandidateEvidenceV1,
) -> None:
    if not isinstance(admission, BugHoundRegisteredIndependentReproductionAdmissionV1):
        raise ValueError("REGISTERED_REPRODUCTION_ADMISSION_REQUIRED")
    lower = admission.candidate_admission
    if lower.candidate_id != candidate.candidate_id or lower.target_ref != candidate.target_ref or lower.target_generation != candidate.target_generation:
        raise ValueError("REGISTERED_REPRODUCTION_SUBJECT_MISMATCH")
    if admission.independent_reproduction_registry_proven is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED")
    if admission.duplicate_check_producer_proven or admission.report_lint_producer_proven or admission.program_admissibility_producer_proven:
        raise ValueError("REPRODUCTION_CANNOT_PRECLAIM_OTHER_PROOF_LEAVES")
    if lower.status != "READY_FOR_HUMAN_SUBMISSION_REVIEW" or not lower.ready_for_human_submission_review or lower.blockers:
        raise ValueError("LOWER_CANDIDATE_EVIDENCE_NOT_READY")
    for obj in (admission, lower):
        for field in ("live_target_testing_authorized", "credential_use_authorized", "submission_authorized", "claim_or_payment_authorized", "external_effect"):
            _false(obj, field, "LOWER_REPRODUCTION_AUTHORITY_WIDENED")


def _resolve_leaf(
    *,
    records: tuple[CandidateLeafProducerRecordV1, ...],
    proof_plane: str,
    leaf: DuplicateCheckEvidenceV1 | ReportLintEvidenceV1 | ProgramAdmissibilityEvidenceV1,
) -> CandidateLeafProducerRecordV1:
    for record in records:
        if (
            record.proof_plane != proof_plane
            or record.artifact_digest != leaf.artifact_digest
            or record.candidate_id != leaf.candidate_id
            or record.target_ref != leaf.target_ref
            or record.target_generation != leaf.target_generation
            or record.producer_ref != leaf.producer_ref
            or record.producer_generation != leaf.producer_generation
            or record.producer_currentness_ref != leaf.producer_currentness_ref
        ):
            continue
        _required("LEAF_REGISTRY_RECEIPT_REF", record.registry_receipt_ref)
        _required("LEAF_REGISTRY_OBSERVER_REF", record.registry_observer_ref)
        _required("LEAF_REGISTRY_OBSERVER_GENERATION", record.registry_observer_generation)
        _required("LEAF_REGISTRY_CURRENTNESS_REF", record.registry_currentness_ref)
        if record.current is not True:
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_STALE")
        if record.independently_observed is not True:
            raise ValueError("CANDIDATE_EVIDENCE_INDEPENDENT_OBSERVER_REQUIRED")
        if record.revoked is not False:
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_REVOKED")
        _false(record, "authority", "CANDIDATE_EVIDENCE_REGISTRY_AUTHORITY_WIDENED")
        _false(record, "external_effect", "CANDIDATE_EVIDENCE_REGISTRY_EXTERNAL_EFFECT_FORBIDDEN")
        return record
    raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_REQUIRED")


def _compose_with_records(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    reproduction_admission: BugHoundRegisteredIndependentReproductionAdmissionV1,
    duplicate: DuplicateCheckEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
    records: tuple[CandidateLeafProducerRecordV1, ...],
) -> CandidateEvidenceTrustJoinReceiptV2:
    _verify_leaf_subjects(mission_input=mission_input, candidate=candidate, duplicate=duplicate, report_lint=report_lint, program=program)
    _verify_reproduction_admission(reproduction_admission, candidate)
    duplicate_record = _resolve_leaf(records=records, proof_plane=DUPLICATE_PLANE, leaf=duplicate)
    lint_record = _resolve_leaf(records=records, proof_plane=REPORT_LINT_PLANE, leaf=report_lint)
    program_record = _resolve_leaf(records=records, proof_plane=PROGRAM_PLANE, leaf=program)
    registry = CandidateLeafRegistryReceiptV2(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(sorted(r.record_digest for r in records)),
        duplicate_record_count=1,
        report_lint_record_count=1,
        program_record_count=1,
    )
    return CandidateEvidenceTrustJoinReceiptV2(
        candidate_id=candidate.candidate_id,
        target_ref=candidate.target_ref,
        target_generation=candidate.target_generation,
        reproduction_admission_digest=reproduction_admission.receipt_digest,
        reproduction_registry_record_digest=reproduction_admission.registry_record_digest,
        duplicate_artifact_digest=duplicate.artifact_digest,
        duplicate_registry_record_digest=duplicate_record.record_digest,
        report_lint_artifact_digest=report_lint.artifact_digest,
        report_lint_registry_record_digest=lint_record.record_digest,
        program_artifact_digest=program.artifact_digest,
        program_registry_record_digest=program_record.record_digest,
        leaf_registry_generation=registry.registry_generation,
        leaf_registry_digest=registry.registry_digest,
    )


def admit_registered_candidate_evidence_trust(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    independent_reproduction: IndependentBountyReproductionReceiptV1,
    duplicate: DuplicateCheckEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> CandidateEvidenceTrustJoinReceiptV2:
    """Traverse all four source-owned proof leaves at the public consequence boundary."""
    _verify_leaf_subjects(mission_input=mission_input, candidate=candidate, duplicate=duplicate, report_lint=report_lint, program=program)
    reproduction_admission = admit_with_registered_independent_reproduction(
        mission_input=mission_input,
        candidate=candidate,
        independent_reproduction=independent_reproduction,
        duplicate_pressure_state=duplicate.duplicate_pressure_state,
        duplicate_check_currentness_ref=duplicate.duplicate_check_currentness_ref,
        report_lint_state=report_lint.report_lint_state,
        report_digest=report_lint.report_digest,
        program_admissibility_state=program.program_admissibility_state,
        program_admissibility_ref=program.program_admissibility_ref,
    )
    return _compose_with_records(
        mission_input=mission_input,
        candidate=candidate,
        reproduction_admission=reproduction_admission,
        duplicate=duplicate,
        report_lint=report_lint,
        program=program,
        records=_CANONICAL_LEAF_RECORDS,
    )


def candidate_evidence_trust_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(admit_registered_candidate_evidence_trust).parameters)
