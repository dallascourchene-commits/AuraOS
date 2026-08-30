"""Producer-bound cash-candidate admission for BugHound.

The lower cash-candidate gate correctly separates benchmark score from real
bounty evidence, but its reproduction/duplicate/lint/program leaves can still be
caller-shaped. This wrapper authenticates those leaves as one producer-owned
bundle before reusing the lower gate.

HMAC here is an Arena-local producer-authentication mechanism, not general
external authority. A successful receipt can prove only that the expected
producer generation emitted the exact evidence bundle consumed by this gate.
It never grants target testing, credentials, disclosure, submission, claiming,
payment, spend, deployment, or any other external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import hmac
import inspect
import json

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    BugHoundCashCandidateAdmissionReceiptV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1

BUNDLE_SCHEMA = "BugHoundCashCandidateEvidenceBundleV1"
ENVELOPE_SCHEMA = "BugHoundCashCandidateEvidenceProducerEnvelopeV1"
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


def _required(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


@dataclass(frozen=True)
class BugHoundCashCandidateEvidenceBundleV1:
    producer_ref: str
    producer_generation: str
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
    producer_ref: str
    producer_generation: str
    bundle_digest: str
    mac_hex: str
    schema: str = ENVELOPE_SCHEMA

    @property
    def envelope_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_CANDIDATE_PRODUCER_ENVELOPE_V1", asdict(self))


@dataclass(frozen=True)
class ProducerBoundBugHoundCashCandidateReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    lower_candidate_receipt_digest: str
    evidence_bundle_digest: str
    producer_envelope_digest: str
    producer_ref: str
    producer_generation: str
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
        b"AURA_BUGHOUND_CASH_CANDIDATE_EVIDENCE_PRODUCER_V1\0"
        + bundle.producer_ref.encode("utf-8")
        + b"\0"
        + bundle.producer_generation.encode("utf-8")
        + b"\0"
        + bundle.bundle_digest.encode("ascii")
    )


def seal_candidate_evidence_bundle(
    bundle: BugHoundCashCandidateEvidenceBundleV1,
    *,
    producer_secret: bytes,
) -> BugHoundCashCandidateEvidenceProducerEnvelopeV1:
    """Seal one exact producer-owned candidate-evidence bundle."""
    if not producer_secret:
        raise ValueError("BUGHOUND_CANDIDATE_PRODUCER_SECRET_REQUIRED")
    _required("PRODUCER_REF", bundle.producer_ref)
    _required("PRODUCER_GENERATION", bundle.producer_generation)
    mac_hex = hmac.new(producer_secret, _mac_message(bundle), hashlib.sha256).hexdigest()
    return BugHoundCashCandidateEvidenceProducerEnvelopeV1(
        producer_ref=bundle.producer_ref,
        producer_generation=bundle.producer_generation,
        bundle_digest=bundle.bundle_digest,
        mac_hex=mac_hex,
    )


def admit_producer_bound_cash_bounty_candidate_for_human_review(
    *,
    mission_input: BugHoundCashMissionInputV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
    producer_envelope: BugHoundCashCandidateEvidenceProducerEnvelopeV1,
    verifier_held_producer_secret: bytes,
    expected_producer_ref: str,
    expected_producer_generation: str,
) -> ProducerBoundBugHoundCashCandidateReceiptV1:
    """Authenticate producer evidence, then invoke the lower cash gate.

    The public boundary deliberately has no standalone duplicate-pressure,
    report-lint, program-admissibility, reproduction-digest, benchmark-score,
    seeded-TP, adjudication, oracle, or caller trust override. Those leaves are
    consumed only from the authenticated bundle.
    """
    if not verifier_held_producer_secret:
        raise ValueError("BUGHOUND_CANDIDATE_VERIFIER_SECRET_REQUIRED")
    _required("EXPECTED_PRODUCER_REF", expected_producer_ref)
    _required("EXPECTED_PRODUCER_GENERATION", expected_producer_generation)

    if evidence_bundle.producer_ref != expected_producer_ref:
        raise ValueError("BUGHOUND_CANDIDATE_PRODUCER_REF_MISMATCH")
    if evidence_bundle.producer_generation != expected_producer_generation:
        raise ValueError("BUGHOUND_CANDIDATE_PRODUCER_GENERATION_MISMATCH")
    if producer_envelope.producer_ref != evidence_bundle.producer_ref:
        raise ValueError("BUGHOUND_CANDIDATE_ENVELOPE_PRODUCER_REF_MISMATCH")
    if producer_envelope.producer_generation != evidence_bundle.producer_generation:
        raise ValueError("BUGHOUND_CANDIDATE_ENVELOPE_PRODUCER_GENERATION_MISMATCH")
    if producer_envelope.bundle_digest != evidence_bundle.bundle_digest:
        raise ValueError("BUGHOUND_CANDIDATE_EVIDENCE_BUNDLE_DIGEST_MISMATCH")

    expected_mac = hmac.new(
        verifier_held_producer_secret,
        _mac_message(evidence_bundle),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(producer_envelope.mac_hex, expected_mac):
        raise ValueError("BUGHOUND_CANDIDATE_PRODUCER_AUTHENTICATION_FAILED")

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

    return ProducerBoundBugHoundCashCandidateReceiptV1(
        candidate_id=lower.candidate_id,
        target_ref=lower.target_ref,
        target_generation=lower.target_generation,
        lower_candidate_receipt_digest=lower.receipt_digest,
        evidence_bundle_digest=evidence_bundle.bundle_digest,
        producer_envelope_digest=producer_envelope.envelope_digest,
        producer_ref=evidence_bundle.producer_ref,
        producer_generation=evidence_bundle.producer_generation,
        candidate_producer_trust_proven=True,
        status=lower.status,
        ready_for_human_submission_review=lower.ready_for_human_submission_review,
    )


def producer_bound_admission_parameter_names() -> tuple[str, ...]:
    """Expose the public ABI for deterministic no-bypass regression tests."""
    return tuple(
        inspect.signature(
            admit_producer_bound_cash_bounty_candidate_for_human_review
        ).parameters
    )
