"""Cash-bounty candidate admission for BugHound.

This boundary deliberately does not accept benchmark score/adjudication objects.
SeedLab/blind benchmark evidence can validate BugHound tooling, but a real cash
bounty candidate must independently satisfy mission currentness, causal/repro
evidence, duplicate/public-known checks, program admissibility, and report lint.

The output is READY_FOR_HUMAN_SUBMISSION_REVIEW at most. It never grants live
target testing, credentials, disclosure, submission, claiming, payment, spend,
or any external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.bughound.bounty_mission import (
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)

SCHEMA = "BugHoundCashCandidateAdmissionReceiptV1"
REPRO_SCHEMA = "IndependentBountyReproductionReceiptV1"


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
class BountyCandidateEvidenceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    security_invariant_digest: str
    causal_cone_digest: str
    discovery_receipt_digest: str
    discovery_reproduction_state: str
    claimed_consequence_band: str


@dataclass(frozen=True)
class IndependentBountyReproductionReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    reproducer_ref: str
    reproducer_generation: str
    result: str
    witness_digest: str
    environment_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    external_effect: bool = False
    schema: str = REPRO_SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_INDEPENDENT_REPRO_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundCashCandidateAdmissionReceiptV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    status: str
    blockers: tuple[str, ...]
    mission_receipt_digest: str
    independent_reproduction_digest: str
    duplicate_pressure_state: str
    report_digest: str
    ready_for_human_submission_review: bool
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_CANDIDATE_ADMISSION_V1", asdict(self))


def admit_cash_bounty_candidate_for_human_review(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    independent_reproduction: IndependentBountyReproductionReceiptV1,
    expected_independent_reproduction_digest: str,
    expected_reproducer_ref: str,
    expected_reproducer_generation: str,
    duplicate_pressure_state: str,
    duplicate_check_currentness_ref: str,
    report_lint_state: str,
    report_digest: str,
    program_admissibility_state: str,
    program_admissibility_ref: str,
) -> BugHoundCashCandidateAdmissionReceiptV1:
    """Admit a real cash-bounty candidate only to human submission review.

    The function intentionally has no benchmark score, seeded-TP, blind
    adjudication, or oracle-credit input. Those objects are capability evidence,
    not bounty-candidate evidence.
    """
    mission = admit_cash_bounty_mission(mission_input)

    for name, value in (
        ("CANDIDATE_ID", candidate.candidate_id),
        ("SECURITY_INVARIANT_DIGEST", candidate.security_invariant_digest),
        ("CAUSAL_CONE_DIGEST", candidate.causal_cone_digest),
        ("DISCOVERY_RECEIPT_DIGEST", candidate.discovery_receipt_digest),
        ("CLAIMED_CONSEQUENCE_BAND", candidate.claimed_consequence_band),
        ("EXPECTED_REPRODUCTION_DIGEST", expected_independent_reproduction_digest),
        ("EXPECTED_REPRODUCER_REF", expected_reproducer_ref),
        ("EXPECTED_REPRODUCER_GENERATION", expected_reproducer_generation),
        ("DUPLICATE_CHECK_CURRENTNESS_REF", duplicate_check_currentness_ref),
        ("REPORT_DIGEST", report_digest),
        ("PROGRAM_ADMISSIBILITY_REF", program_admissibility_ref),
    ):
        _required(name, value)

    if candidate.target_ref != mission_input.target_ref:
        raise ValueError("BOUNTY_CANDIDATE_TARGET_MISMATCH")
    if candidate.target_generation != mission_input.target_generation:
        raise ValueError("BOUNTY_CANDIDATE_GENERATION_MISMATCH")
    if candidate.discovery_reproduction_state != "REPRODUCED_CURRENT":
        raise ValueError("BOUNTY_DISCOVERY_REPRODUCTION_REQUIRED")

    repro = independent_reproduction
    if repro.external_effect:
        raise ValueError("BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN")
    if repro.candidate_id != candidate.candidate_id:
        raise ValueError("BOUNTY_REPRODUCTION_CANDIDATE_MISMATCH")
    if repro.target_ref != candidate.target_ref:
        raise ValueError("BOUNTY_REPRODUCTION_TARGET_MISMATCH")
    if repro.target_generation != candidate.target_generation:
        raise ValueError("BOUNTY_REPRODUCTION_GENERATION_MISMATCH")
    if repro.reproducer_ref != expected_reproducer_ref:
        raise ValueError("BOUNTY_REPRODUCER_REF_MISMATCH")
    if repro.reproducer_generation != expected_reproducer_generation:
        raise ValueError("BOUNTY_REPRODUCER_GENERATION_MISMATCH")
    if repro.result != "REPRODUCED_CURRENT":
        raise ValueError("BOUNTY_INDEPENDENT_REPRODUCTION_REQUIRED")
    _required("REPRODUCTION_WITNESS_DIGEST", repro.witness_digest)
    _required("REPRODUCTION_ENVIRONMENT_DIGEST", repro.environment_digest)
    if repro.scope_rules_digest != mission_input.scope_rules_digest:
        raise ValueError("BOUNTY_REPRODUCTION_SCOPE_MISMATCH")
    if repro.source_currentness_ref != mission_input.source_currentness_ref:
        raise ValueError("BOUNTY_REPRODUCTION_CURRENTNESS_MISMATCH")
    if repro.receipt_digest != expected_independent_reproduction_digest:
        raise ValueError("BOUNTY_REPRODUCTION_EXPECTATION_MISMATCH")

    blockers: list[str] = []
    if duplicate_pressure_state == "PUBLICLY_KNOWN_ROOT_CAUSE":
        blockers.append("PUBLIC_ROOT_CAUSE_ALREADY_KNOWN")
    elif duplicate_pressure_state == "HIGH_DUPLICATE_PRESSURE":
        blockers.append("MANUAL_DUPLICATE_REVIEW_REQUIRED")
    elif duplicate_pressure_state not in {
        "LOW_OBSERVED_DUPLICATE_PRESSURE",
        "MEDIUM_DUPLICATE_PRESSURE",
    }:
        blockers.append("DUPLICATE_PRESSURE_UNRESOLVED")

    if report_lint_state != "REPORT_LINT_CLEAN":
        blockers.append("REPORT_LINT_REQUIRED")
    if program_admissibility_state != "CURRENTLY_ADMISSIBLE":
        blockers.append("PROGRAM_ADMISSIBILITY_REQUIRED")

    ready = not blockers
    status = "READY_FOR_HUMAN_SUBMISSION_REVIEW" if ready else "BOUNTY_CANDIDATE_BLOCKED"
    return BugHoundCashCandidateAdmissionReceiptV1(
        candidate_id=candidate.candidate_id,
        target_ref=candidate.target_ref,
        target_generation=candidate.target_generation,
        status=status,
        blockers=tuple(blockers),
        mission_receipt_digest=mission.receipt_digest,
        independent_reproduction_digest=repro.receipt_digest,
        duplicate_pressure_state=duplicate_pressure_state,
        report_digest=report_digest,
        ready_for_human_submission_review=ready,
    )
