"""Producer-bound cash-candidate admission for BugHound.

The lower cash-candidate gate is useful evidence about candidate/reproduction,
duplicate, lint, and program state. It is not producer authentication. This
module preserves that lower plane while requiring a repository-owned producer
registry before the consequence can advance to human-review readiness.

A caller may still create an HMAC envelope as an integrity diagnostic, but the
canonical consequence API accepts no caller secret, expected producer identity,
registry override, or precomputed trusted receipt. Integrity under a supplied
key is not a trust root.

D0 by default. Nothing here authorizes target testing, credentials, disclosure,
submission, claiming, payment, spend, deployment, or any external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import inspect
import json

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1
from tools.bughound.candidate_evidence_registry import (
    CandidateEvidenceProducerRecordV1,
    CandidateEvidenceRegistryError,
    resolve_candidate_evidence_producer,
)

BUNDLE_SCHEMA = "BugHoundCashCandidateEvidenceBundleV1"
ENVELOPE_SCHEMA = "BugHoundCashCandidateEvidenceProducerEnvelopeV1"
VALIDATION_SCHEMA = "BugHoundCashCandidateEvidenceValidationReceiptV1"
RECEIPT_SCHEMA = "ProducerBoundBugHoundCashCandidateReceiptV1"


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


@dataclass(frozen=True)
class BugHoundCashCandidateEvidenceBundleV1:
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    candidate: BountyCandidateEvidenceV1
    independent_reproduction: IndependentBountyReproductionReceiptV1
    duplicate_pressure_state: str
    duplicate_check_currentness_ref: str
    report_lint_state: str
    report_digest: str
    program_admissibility_state: str
    program_admissibility_ref: str
    schema: str = BUNDLE_SCHEMA

    @property
    def bundle_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_CANDIDATE_EVIDENCE_BUNDLE_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundCashCandidateEvidenceProducerEnvelopeV1:
    """Integrity-only envelope under a caller-supplied key.

    This object deliberately carries no producer-trust or authority bit and is
    not consumed by the canonical consequence-bearing admission function.
    """

    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    bundle_digest: str
    mac_hex: str
    producer_authentication_proven: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = ENVELOPE_SCHEMA

    @property
    def envelope_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_CANDIDATE_PRODUCER_ENVELOPE_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundCashCandidateEvidenceValidationReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    lower_candidate_receipt_digest: str
    evidence_bundle_digest: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    lower_status: str
    lower_ready_for_human_submission_review: bool
    candidate_producer_trust_proven: bool = False
    ready_for_human_submission_review: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = VALIDATION_SCHEMA

    @property
    def validation_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_CANDIDATE_VALIDATION_V1", asdict(self))


@dataclass(frozen=True)
class ProducerBoundBugHoundCashCandidateReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    lower_candidate_receipt_digest: str
    evidence_bundle_digest: str
    producer_registry_record_digest: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    candidate_producer_trust_proven: bool
    status: str
    ready_for_human_submission_review: bool
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = RECEIPT_SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_PRODUCER_BOUND_CASH_CANDIDATE_V1", asdict(self))


def _mac_message(bundle: BugHoundCashCandidateEvidenceBundleV1) -> bytes:
    return (
        b"AURA_BUGHOUND_CASH_CANDIDATE_EVIDENCE_INTEGRITY_V1\0"
        + bundle.producer_ref.encode("utf-8")
        + b"\0"
        + bundle.producer_generation.encode("utf-8")
        + b"\0"
        + bundle.producer_currentness_ref.encode("utf-8")
        + b"\0"
        + bundle.bundle_digest.encode("ascii")
    )


def seal_candidate_evidence_bundle(
    bundle: BugHoundCashCandidateEvidenceBundleV1,
    *,
    producer_secret: bytes,
) -> BugHoundCashCandidateEvidenceProducerEnvelopeV1:
    """Create an integrity envelope; this does not authenticate the producer."""
    if not producer_secret:
        raise ValueError("BUGHOUND_CANDIDATE_INTEGRITY_SECRET_REQUIRED")
    _required("PRODUCER_REF", bundle.producer_ref)
    _required("PRODUCER_GENERATION", bundle.producer_generation)
    _required("PRODUCER_CURRENTNESS_REF", bundle.producer_currentness_ref)
    mac_hex = hmac.new(producer_secret, _mac_message(bundle), hashlib.sha256).hexdigest()
    return BugHoundCashCandidateEvidenceProducerEnvelopeV1(
        producer_ref=bundle.producer_ref,
        producer_generation=bundle.producer_generation,
        producer_currentness_ref=bundle.producer_currentness_ref,
        bundle_digest=bundle.bundle_digest,
        mac_hex=mac_hex,
    )


def validate_candidate_evidence_bundle(
    *,
    mission_input: BugHoundCashMissionInputV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
) -> BugHoundCashCandidateEvidenceValidationReceiptV1:
    """Validate the lower candidate plane without promoting producer trust."""
    _required("PRODUCER_REF", evidence_bundle.producer_ref)
    _required("PRODUCER_GENERATION", evidence_bundle.producer_generation)
    _required("PRODUCER_CURRENTNESS_REF", evidence_bundle.producer_currentness_ref)

    repro = evidence_bundle.independent_reproduction
    lower = admit_cash_bounty_candidate_for_human_review(
        mission_input=mission_input,
        candidate=evidence_bundle.candidate,
        independent_reproduction=repro,
        expected_independent_reproduction_digest=repro.receipt_digest,
        expected_reproducer_ref=repro.reproducer_ref,
        expected_reproducer_generation=repro.reproducer_generation,
        duplicate_pressure_state=evidence_bundle.duplicate_pressure_state,
        duplicate_check_currentness_ref=evidence_bundle.duplicate_check_currentness_ref,
        report_lint_state=evidence_bundle.report_lint_state,
        report_digest=evidence_bundle.report_digest,
        program_admissibility_state=evidence_bundle.program_admissibility_state,
        program_admissibility_ref=evidence_bundle.program_admissibility_ref,
    )

    return BugHoundCashCandidateEvidenceValidationReceiptV1(
        candidate_id=lower.candidate_id,
        target_ref=lower.target_ref,
        target_generation=lower.target_generation,
        lower_candidate_receipt_digest=lower.receipt_digest,
        evidence_bundle_digest=evidence_bundle.bundle_digest,
        producer_ref=evidence_bundle.producer_ref,
        producer_generation=evidence_bundle.producer_generation,
        producer_currentness_ref=evidence_bundle.producer_currentness_ref,
        lower_status=lower.status,
        lower_ready_for_human_submission_review=lower.ready_for_human_submission_review,
    )


def _record_matches_bundle(
    record: CandidateEvidenceProducerRecordV1,
    bundle: BugHoundCashCandidateEvidenceBundleV1,
) -> None:
    repro = bundle.independent_reproduction
    exact = (
        record.producer_ref == bundle.producer_ref
        and record.producer_generation == bundle.producer_generation
        and record.producer_currentness_ref == bundle.producer_currentness_ref
        and record.evidence_bundle_digest == bundle.bundle_digest
        and record.target_ref == bundle.candidate.target_ref
        and record.target_generation == bundle.candidate.target_generation
        and record.scope_rules_digest == repro.scope_rules_digest
        and record.source_currentness_ref == repro.source_currentness_ref
        and record.independent_reproduction_digest == repro.receipt_digest
        and record.duplicate_check_currentness_ref == bundle.duplicate_check_currentness_ref
        and record.report_digest == bundle.report_digest
        and record.program_admissibility_ref == bundle.program_admissibility_ref
    )
    if not exact:
        raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_BINDING_MISMATCH")
    if not record.independently_observed or not record.current or record.revoked:
        raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_NOT_CURRENT")
    if record.authority or record.external_effect:
        raise ValueError("CANDIDATE_EVIDENCE_REGISTRY_AUTHORITY_WIDENED")


def _compose_registered_candidate_receipt(
    *,
    validation: BugHoundCashCandidateEvidenceValidationReceiptV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
    record: CandidateEvidenceProducerRecordV1,
) -> ProducerBoundBugHoundCashCandidateReceiptV1:
    _record_matches_bundle(record, evidence_bundle)
    ready = validation.lower_ready_for_human_submission_review
    return ProducerBoundBugHoundCashCandidateReceiptV1(
        candidate_id=validation.candidate_id,
        target_ref=validation.target_ref,
        target_generation=validation.target_generation,
        lower_candidate_receipt_digest=validation.lower_candidate_receipt_digest,
        evidence_bundle_digest=validation.evidence_bundle_digest,
        producer_registry_record_digest=record.record_digest,
        producer_ref=record.producer_ref,
        producer_generation=record.producer_generation,
        producer_currentness_ref=record.producer_currentness_ref,
        candidate_producer_trust_proven=True,
        status=(
            "READY_FOR_HUMAN_SUBMISSION_REVIEW"
            if ready
            else validation.lower_status
        ),
        ready_for_human_submission_review=ready,
    )


def admit_producer_bound_cash_bounty_candidate_for_human_review(
    *,
    mission_input: BugHoundCashMissionInputV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
) -> ProducerBoundBugHoundCashCandidateReceiptV1:
    """Resolve producer trust internally, then admit the exact lower evidence.

    Production has no caller-selected secret, expected producer identity,
    registry parameter, precomputed producer receipt, or trust boolean. The
    repository-owned registry is currently empty, so a structurally valid bundle
    remains a useful lower-plane validation while this call fails closed at the
    producer-trust boundary.
    """
    validation = validate_candidate_evidence_bundle(
        mission_input=mission_input,
        evidence_bundle=evidence_bundle,
    )
    repro = evidence_bundle.independent_reproduction
    try:
        record = resolve_candidate_evidence_producer(
            producer_ref=evidence_bundle.producer_ref,
            producer_generation=evidence_bundle.producer_generation,
            producer_currentness_ref=evidence_bundle.producer_currentness_ref,
            evidence_bundle_digest=evidence_bundle.bundle_digest,
            target_ref=evidence_bundle.candidate.target_ref,
            target_generation=evidence_bundle.candidate.target_generation,
            scope_rules_digest=repro.scope_rules_digest,
            source_currentness_ref=repro.source_currentness_ref,
            independent_reproduction_digest=repro.receipt_digest,
            duplicate_check_currentness_ref=evidence_bundle.duplicate_check_currentness_ref,
            report_digest=evidence_bundle.report_digest,
            program_admissibility_ref=evidence_bundle.program_admissibility_ref,
        )
    except CandidateEvidenceRegistryError as exc:
        raise ValueError(exc.code) from exc
    return _compose_registered_candidate_receipt(
        validation=validation,
        evidence_bundle=evidence_bundle,
        record=record,
    )


def producer_bound_admission_parameter_names() -> tuple[str, ...]:
    """Expose the public consequence ABI for deterministic anti-bypass tests."""
    return tuple(
        inspect.signature(
            admit_producer_bound_cash_bounty_candidate_for_human_review
        ).parameters
    )
