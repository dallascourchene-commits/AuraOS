"""Independent four-leaf trust join for BugHound cash-candidate evidence.

PR428 proves that a caller-supplied aggregate bundle is not its own producer
trust root.  This successor preserves that lower-plane evidence while refusing
to let one aggregate producer identity authenticate four consequence-distinct
facts.  Candidate evidence reaches the human-review *evidence* boundary only
when all four leaves are independently producer-bound:

1. registered independent reproduction,
2. duplicate-check evidence,
3. report-lint evidence,
4. program-admissibility evidence.

The production registry for leaves 2-4 is deliberately empty.  Public admission
accepts no registry, secret, expected producer identity, trusted boolean, or
precomputed registry record.  Tests may exercise private composition helpers,
but those helpers are not production trust roots.

D0 only.  Nothing here authorizes live testing, credentials, submission,
disclosure, claiming/payment, spend, deployment, or external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

REPRODUCTION_PLANE = "INDEPENDENT_REPRODUCTION"
DUPLICATE_PLANE = "DUPLICATE_CHECK"
REPORT_LINT_PLANE = "REPORT_LINT"
PROGRAM_PLANE = "PROGRAM_ADMISSIBILITY"
REGISTRY_GENERATION = "BUGHOUND_CANDIDATE_LEAF_REGISTRY_HOLD_V1"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _required(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def _require_no_effect(value: object, prefix: str) -> None:
    if getattr(value, "authority", False) is not False:
        raise ValueError(f"{prefix}_AUTHORITY_WIDENED")
    if getattr(value, "external_effect", False) is not False:
        raise ValueError(f"{prefix}_EXTERNAL_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class RegisteredReproductionAdmissionV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    reproduction_receipt_digest: str
    reproducer_ref: str
    reproducer_generation: str
    witness_digest: str
    environment_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    registry_record_digest: str
    registry_receipt_ref: str
    registry_observer_ref: str
    registry_observer_generation: str
    registry_currentness_ref: str
    independent_reproduction_registry_proven: bool = True
    duplicate_check_producer_proven: bool = False
    report_lint_producer_proven: bool = False
    program_admissibility_producer_proven: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "RegisteredReproductionAdmissionV1"

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_REGISTERED_REPRO_ADAPTER_V1", asdict(self))


@dataclass(frozen=True)
class DuplicateEvidenceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    duplicate_pressure_state: str
    duplicate_check_currentness_ref: str
    publicly_known_root_cause: bool
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = False
    external_effect: bool = False
    schema: str = "DuplicateEvidenceV1"

    @property
    def artifact_digest(self) -> str:
        return _digest("AURA_BUGHOUND_DUPLICATE_EVIDENCE_V1", asdict(self))


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
class CandidateEvidenceProducerRecordV1:
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
    schema: str = "CandidateEvidenceProducerRecordV1"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_LEAF_PRODUCER_RECORD_V1", asdict(self))


# Source-owned production trust root for duplicate/lint/program leaves.
# Deliberately empty until independently observed producer records exist.
_CANONICAL_RECORDS: tuple[CandidateEvidenceProducerRecordV1, ...] = ()


@dataclass(frozen=True)
class CandidateEvidenceLeafRegistryReceiptV1:
    registry_generation: str
    record_digests: tuple[str, ...]
    duplicate_record_count: int
    lint_record_count: int
    program_record_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceLeafRegistryReceiptV1"

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_LEAF_REGISTRY_V1", asdict(self))


@dataclass(frozen=True)
class CandidateEvidenceTrustJoinReceiptV1:
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
    independent_reproduction_registry_proven: bool
    duplicate_check_producer_proven: bool
    report_lint_producer_proven: bool
    program_admissibility_producer_proven: bool
    candidate_evidence_trust_proven: bool
    ready_for_human_review_evidence: bool
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceTrustJoinReceiptV1"

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_TRUST_JOIN_V1", asdict(self))


def candidate_evidence_leaf_registry_receipt() -> CandidateEvidenceLeafRegistryReceiptV1:
    records = tuple(sorted(_CANONICAL_RECORDS, key=lambda record: record.record_digest))
    active = tuple(
        record
        for record in records
        if record.independently_observed
        and record.current
        and not record.revoked
        and not record.authority
        and not record.external_effect
    )
    return CandidateEvidenceLeafRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in records),
        duplicate_record_count=sum(record.proof_plane == DUPLICATE_PLANE for record in active),
        lint_record_count=sum(record.proof_plane == REPORT_LINT_PLANE for record in active),
        program_record_count=sum(record.proof_plane == PROGRAM_PLANE for record in active),
    )


def _verify_reproduction(reproduction: RegisteredReproductionAdmissionV1) -> None:
    for name, value in (
        ("CANDIDATE_ID", reproduction.candidate_id),
        ("TARGET_REF", reproduction.target_ref),
        ("TARGET_GENERATION", reproduction.target_generation),
        ("REPRODUCTION_RECEIPT_DIGEST", reproduction.reproduction_receipt_digest),
        ("REPRODUCER_REF", reproduction.reproducer_ref),
        ("REPRODUCER_GENERATION", reproduction.reproducer_generation),
        ("REPRODUCTION_WITNESS_DIGEST", reproduction.witness_digest),
        ("REPRODUCTION_ENVIRONMENT_DIGEST", reproduction.environment_digest),
        ("REPRODUCTION_SCOPE_RULES_DIGEST", reproduction.scope_rules_digest),
        ("REPRODUCTION_SOURCE_CURRENTNESS_REF", reproduction.source_currentness_ref),
        ("REPRODUCTION_REGISTRY_RECORD_DIGEST", reproduction.registry_record_digest),
        ("REPRODUCTION_REGISTRY_RECEIPT_REF", reproduction.registry_receipt_ref),
        ("REPRODUCTION_REGISTRY_OBSERVER_REF", reproduction.registry_observer_ref),
        ("REPRODUCTION_REGISTRY_OBSERVER_GENERATION", reproduction.registry_observer_generation),
        ("REPRODUCTION_REGISTRY_CURRENTNESS_REF", reproduction.registry_currentness_ref),
    ):
        _required(name, value)
    if reproduction.independent_reproduction_registry_proven is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED")
    if (
        reproduction.duplicate_check_producer_proven
        or reproduction.report_lint_producer_proven
        or reproduction.program_admissibility_producer_proven
    ):
        raise ValueError("REPRODUCTION_CANNOT_PRECLAIM_OTHER_PROOF_LEAVES")
    _require_no_effect(reproduction, "REGISTERED_REPRODUCTION")


def _verify_leaf_shapes(
    reproduction: RegisteredReproductionAdmissionV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> None:
    _verify_reproduction(reproduction)
    for leaf, prefix in (
        (duplicate, "DUPLICATE_EVIDENCE"),
        (report_lint, "REPORT_LINT_EVIDENCE"),
        (program, "PROGRAM_ADMISSIBILITY_EVIDENCE"),
    ):
        for name, value in (
            (f"{prefix}_CANDIDATE_ID", leaf.candidate_id),
            (f"{prefix}_TARGET_REF", leaf.target_ref),
            (f"{prefix}_TARGET_GENERATION", leaf.target_generation),
            (f"{prefix}_PRODUCER_REF", leaf.producer_ref),
            (f"{prefix}_PRODUCER_GENERATION", leaf.producer_generation),
            (f"{prefix}_PRODUCER_CURRENTNESS_REF", leaf.producer_currentness_ref),
        ):
            _required(name, value)
        if (
            leaf.candidate_id != reproduction.candidate_id
            or leaf.target_ref != reproduction.target_ref
            or leaf.target_generation != reproduction.target_generation
        ):
            raise ValueError("CANDIDATE_EVIDENCE_LEAF_SUBJECT_MISMATCH")
        _require_no_effect(leaf, prefix)

    _required("DUPLICATE_CHECK_CURRENTNESS_REF", duplicate.duplicate_check_currentness_ref)
    if duplicate.publicly_known_root_cause:
        raise ValueError("PUBLIC_ROOT_CAUSE_ALREADY_KNOWN")
    if duplicate.duplicate_pressure_state == "HIGH_DUPLICATE_PRESSURE":
        raise ValueError("MANUAL_DUPLICATE_REVIEW_REQUIRED")
    if duplicate.duplicate_pressure_state not in {
        "LOW_OBSERVED_DUPLICATE_PRESSURE",
        "MEDIUM_DUPLICATE_PRESSURE",
    }:
        raise ValueError("DUPLICATE_PRESSURE_UNRESOLVED")

    _required("REPORT_DIGEST", report_lint.report_digest)
    _required("LINT_POLICY_GENERATION", report_lint.lint_policy_generation)
    if report_lint.report_lint_state != "REPORT_LINT_CLEAN":
        raise ValueError("REPORT_LINT_REQUIRED")

    _required("PROGRAM_ADMISSIBILITY_REF", program.program_admissibility_ref)
    _required("PROGRAM_SCOPE_RULES_DIGEST", program.scope_rules_digest)
    _required("PROGRAM_PAYOUT_RULES_DIGEST", program.payout_rules_digest)
    _required("PROGRAM_SOURCE_CURRENTNESS_REF", program.source_currentness_ref)
    if program.program_admissibility_state != "CURRENTLY_ADMISSIBLE":
        raise ValueError("PROGRAM_ADMISSIBILITY_REQUIRED")
    if program.scope_rules_digest != reproduction.scope_rules_digest:
        raise ValueError("PROGRAM_SCOPE_REPRODUCTION_SCOPE_MISMATCH")
    if program.source_currentness_ref != reproduction.source_currentness_ref:
        raise ValueError("PROGRAM_SOURCE_REPRODUCTION_SOURCE_MISMATCH")


def _record_matches_leaf(
    record: CandidateEvidenceProducerRecordV1,
    *,
    proof_plane: str,
    artifact_digest: str,
    candidate_id: str,
    target_ref: str,
    target_generation: str,
    producer_ref: str,
    producer_generation: str,
    producer_currentness_ref: str,
) -> bool:
    return (
        record.proof_plane == proof_plane
        and record.artifact_digest == artifact_digest
        and record.candidate_id == candidate_id
        and record.target_ref == target_ref
        and record.target_generation == target_generation
        and record.producer_ref == producer_ref
        and record.producer_generation == producer_generation
        and record.producer_currentness_ref == producer_currentness_ref
    )


def _resolve_leaf_from_records(
    *,
    records: tuple[CandidateEvidenceProducerRecordV1, ...],
    proof_plane: str,
    leaf: DuplicateEvidenceV1 | ReportLintEvidenceV1 | ProgramAdmissibilityEvidenceV1,
) -> CandidateEvidenceProducerRecordV1:
    for record in records:
        if not _record_matches_leaf(
            record,
            proof_plane=proof_plane,
            artifact_digest=leaf.artifact_digest,
            candidate_id=leaf.candidate_id,
            target_ref=leaf.target_ref,
            target_generation=leaf.target_generation,
            producer_ref=leaf.producer_ref,
            producer_generation=leaf.producer_generation,
            producer_currentness_ref=leaf.producer_currentness_ref,
        ):
            continue
        if not record.registry_receipt_ref.strip():
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_RECEIPT_REQUIRED")
        if not record.registry_observer_ref.strip() or not record.registry_observer_generation.strip():
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_OBSERVER_REQUIRED")
        if not record.registry_currentness_ref.strip() or not record.current:
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_STALE")
        if not record.independently_observed:
            raise ValueError("CANDIDATE_EVIDENCE_INDEPENDENT_OBSERVER_REQUIRED")
        if record.revoked:
            raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_REVOKED")
        _require_no_effect(record, "CANDIDATE_EVIDENCE_REGISTRY_RECORD")
        return record
    raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_REQUIRED")


def _compose_with_records(
    *,
    reproduction: RegisteredReproductionAdmissionV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
    records: tuple[CandidateEvidenceProducerRecordV1, ...],
) -> CandidateEvidenceTrustJoinReceiptV1:
    _verify_leaf_shapes(reproduction, duplicate, report_lint, program)
    duplicate_record = _resolve_leaf_from_records(
        records=records, proof_plane=DUPLICATE_PLANE, leaf=duplicate
    )
    lint_record = _resolve_leaf_from_records(
        records=records, proof_plane=REPORT_LINT_PLANE, leaf=report_lint
    )
    program_record = _resolve_leaf_from_records(
        records=records, proof_plane=PROGRAM_PLANE, leaf=program
    )
    registry = CandidateEvidenceLeafRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(sorted(record.record_digest for record in records)),
        duplicate_record_count=sum(record.proof_plane == DUPLICATE_PLANE for record in records),
        lint_record_count=sum(record.proof_plane == REPORT_LINT_PLANE for record in records),
        program_record_count=sum(record.proof_plane == PROGRAM_PLANE for record in records),
    )
    return CandidateEvidenceTrustJoinReceiptV1(
        candidate_id=reproduction.candidate_id,
        target_ref=reproduction.target_ref,
        target_generation=reproduction.target_generation,
        reproduction_admission_digest=reproduction.receipt_digest,
        reproduction_registry_record_digest=reproduction.registry_record_digest,
        duplicate_artifact_digest=duplicate.artifact_digest,
        duplicate_registry_record_digest=duplicate_record.record_digest,
        report_lint_artifact_digest=report_lint.artifact_digest,
        report_lint_registry_record_digest=lint_record.record_digest,
        program_artifact_digest=program.artifact_digest,
        program_registry_record_digest=program_record.record_digest,
        leaf_registry_generation=registry.registry_generation,
        leaf_registry_digest=registry.registry_digest,
        independent_reproduction_registry_proven=True,
        duplicate_check_producer_proven=True,
        report_lint_producer_proven=True,
        program_admissibility_producer_proven=True,
        candidate_evidence_trust_proven=True,
        ready_for_human_review_evidence=True,
    )


def admit_registered_candidate_evidence_trust(
    *,
    reproduction: RegisteredReproductionAdmissionV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> CandidateEvidenceTrustJoinReceiptV1:
    """Join four independently producer-bound leaves using source-owned records."""
    _verify_leaf_shapes(reproduction, duplicate, report_lint, program)
    if not _CANONICAL_RECORDS:
        raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_REQUIRED")
    return _compose_with_records(
        reproduction=reproduction,
        duplicate=duplicate,
        report_lint=report_lint,
        program=program,
        records=_CANONICAL_RECORDS,
    )


def candidate_evidence_trust_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(admit_registered_candidate_evidence_trust).parameters)
