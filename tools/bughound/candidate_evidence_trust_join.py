"""Independent four-leaf trust join for BugHound cash-candidate evidence.

PR428 proved that an aggregate caller bundle is not its own producer trust root.
This additive successor tests the stronger proposition that four consequence-
distinct facts must remain independently current and producer-bound:

1. independent reproduction,
2. duplicate checking,
3. report lint,
4. program admissibility.

All four leaves use the same source-owned registry law.  A caller may describe a
leaf and its claimed producer identity, but only a repository-owned registry
record can authenticate that exact leaf artifact/currentness tuple.  No leaf may
borrow producer proof from another leaf, and staleness/revocation is leaf-local.

The production registry is deliberately empty.  Public admission accepts no
registry, secret, expected identity, trusted boolean, precomputed producer
record, or proof override.  Private composition helpers exist only for
adversarial deterministic tests and do not populate production trust.

D0 only.  Nothing here authorizes live testing, credentials, disclosure,
submission, claiming/payment, spend, deployment, or any external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json
from typing import Union

REPRODUCTION_PLANE = "INDEPENDENT_REPRODUCTION"
DUPLICATE_PLANE = "DUPLICATE_CHECK"
REPORT_LINT_PLANE = "REPORT_LINT"
PROGRAM_PLANE = "PROGRAM_ADMISSIBILITY"
PROOF_PLANES = (
    REPRODUCTION_PLANE,
    DUPLICATE_PLANE,
    REPORT_LINT_PLANE,
    PROGRAM_PLANE,
)
REGISTRY_GENERATION = "BUGHOUND_CANDIDATE_FOUR_LEAF_REGISTRY_HOLD_V1"


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


def _require_exact_bool(name: str, value: object) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name}_BOOL_REQUIRED")
    return value


def _require_no_effect(value: object, prefix: str) -> None:
    if getattr(value, "authority", False) is not False:
        raise ValueError(f"{prefix}_AUTHORITY_WIDENED")
    if getattr(value, "external_effect", False) is not False:
        raise ValueError(f"{prefix}_EXTERNAL_EFFECT_FORBIDDEN")


@dataclass(frozen=True)
class ReproductionEvidenceV1:
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
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = False
    external_effect: bool = False
    schema: str = "ReproductionEvidenceV1"

    @property
    def artifact_digest(self) -> str:
        return _digest("AURA_BUGHOUND_REPRODUCTION_EVIDENCE_V1", asdict(self))


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


LeafEvidence = Union[
    ReproductionEvidenceV1,
    DuplicateEvidenceV1,
    ReportLintEvidenceV1,
    ProgramAdmissibilityEvidenceV1,
]


@dataclass(frozen=True)
class CandidateEvidenceLeafProducerRecordV1:
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
    enabled: bool = True
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceLeafProducerRecordV1"

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_EVIDENCE_LEAF_PRODUCER_RECORD_V1", asdict(self))


# Repository-owned production trust root. Deliberately empty until each proof
# plane has an independently observed current producer record.
_CANONICAL_RECORDS: tuple[CandidateEvidenceLeafProducerRecordV1, ...] = ()


@dataclass(frozen=True)
class CandidateEvidenceLeafRegistryReceiptV1:
    registry_generation: str
    record_digests: tuple[str, ...]
    reproduction_record_count: int
    duplicate_record_count: int
    lint_record_count: int
    program_record_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = "CandidateEvidenceLeafRegistryReceiptV1"

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CANDIDATE_FOUR_LEAF_REGISTRY_V1", asdict(self))


@dataclass(frozen=True)
class CandidateEvidenceTrustJoinReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    reproduction_artifact_digest: str
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


def _active_record(record: CandidateEvidenceLeafProducerRecordV1) -> bool:
    _require_exact_bool("REGISTRY_INDEPENDENTLY_OBSERVED", record.independently_observed)
    _require_exact_bool("REGISTRY_CURRENT", record.current)
    _require_exact_bool("REGISTRY_REVOKED", record.revoked)
    _require_exact_bool("REGISTRY_ENABLED", record.enabled)
    _require_exact_bool("REGISTRY_AUTHORITY", record.authority)
    _require_exact_bool("REGISTRY_EXTERNAL_EFFECT", record.external_effect)
    return (
        record.independently_observed
        and record.current
        and not record.revoked
        and record.enabled
        and not record.authority
        and not record.external_effect
    )


def candidate_evidence_leaf_registry_receipt() -> CandidateEvidenceLeafRegistryReceiptV1:
    records = tuple(sorted(_CANONICAL_RECORDS, key=lambda record: record.record_digest))
    active = tuple(record for record in records if _active_record(record))
    return CandidateEvidenceLeafRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in records),
        reproduction_record_count=sum(record.proof_plane == REPRODUCTION_PLANE for record in active),
        duplicate_record_count=sum(record.proof_plane == DUPLICATE_PLANE for record in active),
        lint_record_count=sum(record.proof_plane == REPORT_LINT_PLANE for record in active),
        program_record_count=sum(record.proof_plane == PROGRAM_PLANE for record in active),
    )


def _proof_plane_for_leaf(leaf: LeafEvidence) -> str:
    if isinstance(leaf, ReproductionEvidenceV1):
        return REPRODUCTION_PLANE
    if isinstance(leaf, DuplicateEvidenceV1):
        return DUPLICATE_PLANE
    if isinstance(leaf, ReportLintEvidenceV1):
        return REPORT_LINT_PLANE
    if isinstance(leaf, ProgramAdmissibilityEvidenceV1):
        return PROGRAM_PLANE
    raise ValueError("CANDIDATE_EVIDENCE_LEAF_TYPE_UNSUPPORTED")


def _verify_leaf_identity(leaf: LeafEvidence, prefix: str) -> None:
    for name, value in (
        (f"{prefix}_CANDIDATE_ID", leaf.candidate_id),
        (f"{prefix}_TARGET_REF", leaf.target_ref),
        (f"{prefix}_TARGET_GENERATION", leaf.target_generation),
        (f"{prefix}_PRODUCER_REF", leaf.producer_ref),
        (f"{prefix}_PRODUCER_GENERATION", leaf.producer_generation),
        (f"{prefix}_PRODUCER_CURRENTNESS_REF", leaf.producer_currentness_ref),
    ):
        _required(name, value)
    _require_no_effect(leaf, prefix)


def _verify_leaf_shapes(
    reproduction: ReproductionEvidenceV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> None:
    _verify_leaf_identity(reproduction, "REPRODUCTION_EVIDENCE")
    _verify_leaf_identity(duplicate, "DUPLICATE_EVIDENCE")
    _verify_leaf_identity(report_lint, "REPORT_LINT_EVIDENCE")
    _verify_leaf_identity(program, "PROGRAM_ADMISSIBILITY_EVIDENCE")

    subject = (
        reproduction.candidate_id,
        reproduction.target_ref,
        reproduction.target_generation,
    )
    for leaf in (duplicate, report_lint, program):
        if (leaf.candidate_id, leaf.target_ref, leaf.target_generation) != subject:
            raise ValueError("CANDIDATE_EVIDENCE_LEAF_SUBJECT_MISMATCH")

    for name, value in (
        ("REPRODUCTION_RECEIPT_DIGEST", reproduction.reproduction_receipt_digest),
        ("REPRODUCER_REF", reproduction.reproducer_ref),
        ("REPRODUCER_GENERATION", reproduction.reproducer_generation),
        ("REPRODUCTION_WITNESS_DIGEST", reproduction.witness_digest),
        ("REPRODUCTION_ENVIRONMENT_DIGEST", reproduction.environment_digest),
        ("REPRODUCTION_SCOPE_RULES_DIGEST", reproduction.scope_rules_digest),
        ("REPRODUCTION_SOURCE_CURRENTNESS_REF", reproduction.source_currentness_ref),
    ):
        _required(name, value)

    _required("DUPLICATE_CHECK_CURRENTNESS_REF", duplicate.duplicate_check_currentness_ref)
    _require_exact_bool("PUBLICLY_KNOWN_ROOT_CAUSE", duplicate.publicly_known_root_cause)
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
    record: CandidateEvidenceLeafProducerRecordV1,
    leaf: LeafEvidence,
) -> bool:
    return (
        record.proof_plane == _proof_plane_for_leaf(leaf)
        and record.artifact_digest == leaf.artifact_digest
        and record.candidate_id == leaf.candidate_id
        and record.target_ref == leaf.target_ref
        and record.target_generation == leaf.target_generation
        and record.producer_ref == leaf.producer_ref
        and record.producer_generation == leaf.producer_generation
        and record.producer_currentness_ref == leaf.producer_currentness_ref
    )


def _resolve_leaf_from_records(
    *,
    records: tuple[CandidateEvidenceLeafProducerRecordV1, ...],
    leaf: LeafEvidence,
) -> CandidateEvidenceLeafProducerRecordV1:
    proof_plane = _proof_plane_for_leaf(leaf)
    for record in records:
        if not _record_matches_leaf(record, leaf):
            continue
        _required("REGISTRY_RECEIPT_REF", record.registry_receipt_ref)
        _required("REGISTRY_OBSERVER_REF", record.registry_observer_ref)
        _required("REGISTRY_OBSERVER_GENERATION", record.registry_observer_generation)
        _required("REGISTRY_CURRENTNESS_REF", record.registry_currentness_ref)
        if not _active_record(record):
            if record.revoked:
                raise ValueError(f"{proof_plane}_REGISTRY_REVOKED")
            if not record.enabled:
                raise ValueError(f"{proof_plane}_REGISTRY_DISABLED")
            if not record.current:
                raise ValueError(f"{proof_plane}_REGISTRY_STALE")
            if not record.independently_observed:
                raise ValueError(f"{proof_plane}_INDEPENDENT_OBSERVER_REQUIRED")
            raise ValueError(f"{proof_plane}_REGISTRY_AUTHORITY_INVALID")
        return record
    raise ValueError(f"{proof_plane}_REGISTRY_REQUIRED")


def _build_registry_receipt(
    records: tuple[CandidateEvidenceLeafProducerRecordV1, ...],
) -> CandidateEvidenceLeafRegistryReceiptV1:
    active = tuple(record for record in records if _active_record(record))
    return CandidateEvidenceLeafRegistryReceiptV1(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(sorted(record.record_digest for record in records)),
        reproduction_record_count=sum(record.proof_plane == REPRODUCTION_PLANE for record in active),
        duplicate_record_count=sum(record.proof_plane == DUPLICATE_PLANE for record in active),
        lint_record_count=sum(record.proof_plane == REPORT_LINT_PLANE for record in active),
        program_record_count=sum(record.proof_plane == PROGRAM_PLANE for record in active),
    )


def _compose_with_records(
    *,
    reproduction: ReproductionEvidenceV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
    records: tuple[CandidateEvidenceLeafProducerRecordV1, ...],
) -> CandidateEvidenceTrustJoinReceiptV1:
    _verify_leaf_shapes(reproduction, duplicate, report_lint, program)
    reproduction_record = _resolve_leaf_from_records(records=records, leaf=reproduction)
    duplicate_record = _resolve_leaf_from_records(records=records, leaf=duplicate)
    lint_record = _resolve_leaf_from_records(records=records, leaf=report_lint)
    program_record = _resolve_leaf_from_records(records=records, leaf=program)
    registry = _build_registry_receipt(records)
    return CandidateEvidenceTrustJoinReceiptV1(
        candidate_id=reproduction.candidate_id,
        target_ref=reproduction.target_ref,
        target_generation=reproduction.target_generation,
        reproduction_artifact_digest=reproduction.artifact_digest,
        reproduction_registry_record_digest=reproduction_record.record_digest,
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
    reproduction: ReproductionEvidenceV1,
    duplicate: DuplicateEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
) -> CandidateEvidenceTrustJoinReceiptV1:
    """Resolve all four proof leaves against the source-owned registry."""
    _verify_leaf_shapes(reproduction, duplicate, report_lint, program)
    if not _CANONICAL_RECORDS:
        raise ValueError("CANDIDATE_EVIDENCE_FOUR_LEAF_REGISTRY_REQUIRED")
    return _compose_with_records(
        reproduction=reproduction,
        duplicate=duplicate,
        report_lint=report_lint,
        program=program,
        records=_CANONICAL_RECORDS,
    )


def candidate_evidence_trust_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(admit_registered_candidate_evidence_trust).parameters)
