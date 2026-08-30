"""Producer-bound independent-reproduction gate for BugHound cash candidates.

This layer removes caller control over the three PR420 expectation fields. A
registry lookup owned outside the discoverer/candidate boundary must return a
current, independently observed record for the exact reproduction receipt.

The default path fails closed because no canonical production registry is yet
wired. Passing the software contract does not prove that a real bounty
reproduction registry exists, does not authorize live testing or submission,
and does not clear PR425's remaining duplicate/lint/program producer-trust debt.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Callable

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    BugHoundCashCandidateAdmissionReceiptV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1

SCHEMA = "BugHoundRegisteredIndependentReproductionAdmissionV1"
REGISTRY_SCHEMA = "BugHoundIndependentReproductionRegistryRecordV1"


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


@dataclass(frozen=True)
class BugHoundIndependentReproductionRegistryRecordV1:
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
    registry_receipt_ref: str
    registry_observer_ref: str
    registry_observer_generation: str
    registry_current: bool
    independently_observed: bool
    revoked: bool = False
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = REGISTRY_SCHEMA

    @property
    def record_digest(self) -> str:
        return _digest("AURA_BUGHOUND_INDEPENDENT_REPRO_REGISTRY_V1", asdict(self))


@dataclass(frozen=True)
class BugHoundRegisteredIndependentReproductionAdmissionV1:
    candidate_admission: BugHoundCashCandidateAdmissionReceiptV1
    registry_record_digest: str
    registry_receipt_ref: str
    registry_observer_ref: str
    registry_observer_generation: str
    independent_reproduction_registry_proven: bool = True
    duplicate_check_producer_proven: bool = False
    report_lint_producer_proven: bool = False
    program_admissibility_producer_proven: bool = False
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest(
            "AURA_BUGHOUND_REGISTERED_INDEPENDENT_REPRO_ADMISSION_V1",
            asdict(self),
        )


RegistryLookup = Callable[
    [IndependentBountyReproductionReceiptV1],
    BugHoundIndependentReproductionRegistryRecordV1,
]


def _production_registry_unavailable(
    _reproduction: IndependentBountyReproductionReceiptV1,
) -> BugHoundIndependentReproductionRegistryRecordV1:
    raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED")


def _require_false(record: object, field: str, code: str) -> None:
    if getattr(record, field, None) is not False:
        raise ValueError(code)


def _verify_registry_record(
    *,
    reproduction: IndependentBountyReproductionReceiptV1,
    candidate: BountyCandidateEvidenceV1,
    mission_input: BugHoundCashMissionInputV1,
    record: BugHoundIndependentReproductionRegistryRecordV1,
) -> None:
    if record.schema != REGISTRY_SCHEMA:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_SCHEMA_MISMATCH")
    if not record.registry_receipt_ref.strip():
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_RECEIPT_REQUIRED")
    if not record.registry_observer_ref.strip() or not record.registry_observer_generation.strip():
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_OBSERVER_REQUIRED")
    if record.registry_current is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_STALE")
    if record.independently_observed is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_INDEPENDENT_OBSERVER_REQUIRED")
    if record.revoked is not False:
        raise ValueError("INDEPENDENT_REPRODUCTION_REVOKED")

    for field, code in (
        ("live_target_testing_authorized", "REPRO_REGISTRY_LIVE_TEST_AUTHORITY_FORBIDDEN"),
        ("credential_use_authorized", "REPRO_REGISTRY_CREDENTIAL_AUTHORITY_FORBIDDEN"),
        ("submission_authorized", "REPRO_REGISTRY_SUBMISSION_AUTHORITY_FORBIDDEN"),
        ("claim_or_payment_authorized", "REPRO_REGISTRY_PAYMENT_AUTHORITY_FORBIDDEN"),
        ("external_effect", "REPRO_REGISTRY_EXTERNAL_EFFECT_FORBIDDEN"),
    ):
        _require_false(record, field, code)

    exact = {
        "candidate_id": (record.candidate_id, candidate.candidate_id),
        "target_ref": (record.target_ref, candidate.target_ref),
        "target_generation": (record.target_generation, candidate.target_generation),
        "reproduction_receipt_digest": (
            record.reproduction_receipt_digest,
            reproduction.receipt_digest,
        ),
        "reproducer_ref": (record.reproducer_ref, reproduction.reproducer_ref),
        "reproducer_generation": (
            record.reproducer_generation,
            reproduction.reproducer_generation,
        ),
        "witness_digest": (record.witness_digest, reproduction.witness_digest),
        "environment_digest": (record.environment_digest, reproduction.environment_digest),
        "scope_rules_digest": (record.scope_rules_digest, mission_input.scope_rules_digest),
        "source_currentness_ref": (
            record.source_currentness_ref,
            mission_input.source_currentness_ref,
        ),
    }
    for field, (observed, expected) in exact.items():
        if observed != expected:
            raise ValueError(f"INDEPENDENT_REPRODUCTION_REGISTRY_{field.upper()}_MISMATCH")


def admit_with_registered_independent_reproduction(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    independent_reproduction: IndependentBountyReproductionReceiptV1,
    duplicate_pressure_state: str,
    duplicate_check_currentness_ref: str,
    report_lint_state: str,
    report_digest: str,
    program_admissibility_state: str,
    program_admissibility_ref: str,
    registry_lookup: RegistryLookup = _production_registry_unavailable,
    **forbidden_expectation_fields: object,
) -> BugHoundRegisteredIndependentReproductionAdmissionV1:
    """Admit PR420 through an independently owned reproduction-registry boundary.

    Callers cannot provide the three `expected_*` reproduction fields. A trusted
    registry lookup is the only source for them. The default production path
    fails closed until a canonical registry is wired.
    """
    if forbidden_expectation_fields:
        forbidden = {
            "expected_independent_reproduction_digest",
            "expected_reproducer_ref",
            "expected_reproducer_generation",
        }
        if forbidden.intersection(forbidden_expectation_fields):
            raise ValueError("CALLER_REPRODUCTION_EXPECTATION_FORBIDDEN")
        raise TypeError(
            "UNEXPECTED_REGISTERED_REPRODUCTION_ARGUMENTS: "
            + ",".join(sorted(forbidden_expectation_fields))
        )

    if independent_reproduction.external_effect:
        raise ValueError("BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN")

    record = registry_lookup(independent_reproduction)
    if not isinstance(record, BugHoundIndependentReproductionRegistryRecordV1):
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_RECORD_REQUIRED")
    _verify_registry_record(
        reproduction=independent_reproduction,
        candidate=candidate,
        mission_input=mission_input,
        record=record,
    )

    admitted = admit_cash_bounty_candidate_for_human_review(
        mission_input=mission_input,
        candidate=candidate,
        independent_reproduction=independent_reproduction,
        expected_independent_reproduction_digest=record.reproduction_receipt_digest,
        expected_reproducer_ref=record.reproducer_ref,
        expected_reproducer_generation=record.reproducer_generation,
        duplicate_pressure_state=duplicate_pressure_state,
        duplicate_check_currentness_ref=duplicate_check_currentness_ref,
        report_lint_state=report_lint_state,
        report_digest=report_digest,
        program_admissibility_state=program_admissibility_state,
        program_admissibility_ref=program_admissibility_ref,
    )

    for field in (
        "live_target_testing_authorized",
        "credential_use_authorized",
        "submission_authorized",
        "claim_or_payment_authorized",
        "external_effect",
    ):
        if getattr(admitted, field) is not False:
            raise ValueError("REGISTERED_REPRODUCTION_ADMISSION_AUTHORITY_WIDENED")

    return BugHoundRegisteredIndependentReproductionAdmissionV1(
        candidate_admission=admitted,
        registry_record_digest=record.record_digest,
        registry_receipt_ref=record.registry_receipt_ref,
        registry_observer_ref=record.registry_observer_ref,
        registry_observer_generation=record.registry_observer_generation,
    )
