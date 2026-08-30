"""Canonical source-owned independent-reproduction trust root for BugHound.

This convergence successor combines two independently hosted sibling repairs:
- unique matching-record resolution plus full registry generation/content binding;
- source-owned record self-validation plus structural observer/reproducer
  separation.

Callers cannot provide expected producer identities, registry callbacks, records,
prebuilt admissions, trusted booleans, or alternate trust roots. Production
remains an empty source-owned HOLD. Passing this software membrane proves only
the independent-reproduction proof plane and grants no external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    BugHoundCashCandidateAdmissionReceiptV1,
    IndependentBountyReproductionReceiptV1,
    admit_cash_bounty_candidate_for_human_review,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1

SCHEMA = "BugHoundRegisteredIndependentReproductionAdmissionV1"
REGISTRY_SCHEMA = "BugHoundIndependentReproductionRegistryRecordV1"
REGISTRY_GENERATION = "BUGHOUND_INDEPENDENT_REPRODUCTION_REGISTRY_HOLD_V4"


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


_CANONICAL_REPRODUCTION_RECORDS: tuple[
    BugHoundIndependentReproductionRegistryRecordV1, ...
] = ()


@dataclass(frozen=True)
class BugHoundIndependentReproductionRegistryReceiptV4:
    registry_generation: str
    record_digests: tuple[str, ...]
    active_record_count: int
    authority: bool = False
    external_effect: bool = False
    schema: str = "BugHoundIndependentReproductionRegistryReceiptV4"

    @property
    def registry_digest(self) -> str:
        return _digest("AURA_BUGHOUND_INDEPENDENT_REPRO_REGISTRY_RECEIPT_V4", asdict(self))


@dataclass(frozen=True)
class BugHoundRegisteredIndependentReproductionAdmissionV1:
    candidate_admission: BugHoundCashCandidateAdmissionReceiptV1
    registry_record_digest: str
    registry_receipt_ref: str
    registry_observer_ref: str
    registry_observer_generation: str
    registry_generation: str = REGISTRY_GENERATION
    registry_digest: str = ""
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


def _require_text(record: object, field: str, code: str) -> str:
    value = getattr(record, field, None)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value.strip()


def _require_exact_bool(record: object, field: str, code: str) -> bool:
    value = getattr(record, field, None)
    if type(value) is not bool:
        raise ValueError(code)
    return value


def _require_false(record: object, field: str, code: str) -> None:
    if getattr(record, field, None) is not False:
        raise ValueError(code)


def _validate_registry_record_shape(
    record: BugHoundIndependentReproductionRegistryRecordV1,
) -> None:
    """Validate one source-owned record before it can participate in trust."""
    if not isinstance(record, BugHoundIndependentReproductionRegistryRecordV1):
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_RECORD_REQUIRED")
    if record.schema != REGISTRY_SCHEMA:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_SCHEMA_MISMATCH")

    for field, code in (
        ("candidate_id", "INDEPENDENT_REPRODUCTION_REGISTRY_CANDIDATE_REQUIRED"),
        ("target_ref", "INDEPENDENT_REPRODUCTION_REGISTRY_TARGET_REQUIRED"),
        ("target_generation", "INDEPENDENT_REPRODUCTION_REGISTRY_TARGET_GENERATION_REQUIRED"),
        ("reproduction_receipt_digest", "INDEPENDENT_REPRODUCTION_REGISTRY_REPRODUCTION_DIGEST_REQUIRED"),
        ("reproducer_ref", "INDEPENDENT_REPRODUCTION_REGISTRY_REPRODUCER_REQUIRED"),
        ("reproducer_generation", "INDEPENDENT_REPRODUCTION_REGISTRY_REPRODUCER_GENERATION_REQUIRED"),
        ("witness_digest", "INDEPENDENT_REPRODUCTION_REGISTRY_WITNESS_REQUIRED"),
        ("environment_digest", "INDEPENDENT_REPRODUCTION_REGISTRY_ENVIRONMENT_REQUIRED"),
        ("scope_rules_digest", "INDEPENDENT_REPRODUCTION_REGISTRY_SCOPE_REQUIRED"),
        ("source_currentness_ref", "INDEPENDENT_REPRODUCTION_REGISTRY_SOURCE_CURRENTNESS_REQUIRED"),
        ("registry_receipt_ref", "INDEPENDENT_REPRODUCTION_REGISTRY_RECEIPT_REQUIRED"),
        ("registry_observer_ref", "INDEPENDENT_REPRODUCTION_REGISTRY_OBSERVER_REQUIRED"),
        ("registry_observer_generation", "INDEPENDENT_REPRODUCTION_REGISTRY_OBSERVER_REQUIRED"),
    ):
        _require_text(record, field, code)

    _require_exact_bool(
        record,
        "registry_current",
        "INDEPENDENT_REPRODUCTION_REGISTRY_CURRENT_BOOL_REQUIRED",
    )
    _require_exact_bool(
        record,
        "independently_observed",
        "INDEPENDENT_REPRODUCTION_INDEPENDENTLY_OBSERVED_BOOL_REQUIRED",
    )
    _require_exact_bool(
        record,
        "revoked",
        "INDEPENDENT_REPRODUCTION_REVOKED_BOOL_REQUIRED",
    )

    for field, code in (
        ("live_target_testing_authorized", "REPRO_REGISTRY_LIVE_TEST_AUTHORITY_FORBIDDEN"),
        ("credential_use_authorized", "REPRO_REGISTRY_CREDENTIAL_AUTHORITY_FORBIDDEN"),
        ("submission_authorized", "REPRO_REGISTRY_SUBMISSION_AUTHORITY_FORBIDDEN"),
        ("claim_or_payment_authorized", "REPRO_REGISTRY_PAYMENT_AUTHORITY_FORBIDDEN"),
        ("external_effect", "REPRO_REGISTRY_EXTERNAL_EFFECT_FORBIDDEN"),
    ):
        _require_false(record, field, code)

    # A boolean label or different generation label cannot manufacture
    # independence.  The observer must be a distinct logical principal.
    if record.registry_observer_ref.strip() == record.reproducer_ref.strip():
        raise ValueError("INDEPENDENT_REPRODUCTION_OBSERVER_PRODUCER_SEPARATION_REQUIRED")


def _registry_receipt_from_records(
    records: tuple[BugHoundIndependentReproductionRegistryRecordV1, ...],
) -> BugHoundIndependentReproductionRegistryReceiptV4:
    # Full-registry binding is meaningful only if every source-owned record has
    # first passed structural validation.  A malformed neighbor therefore cannot
    # hide behind one valid selected record.
    records = tuple(records)
    for record in records:
        _validate_registry_record_shape(record)
    ordered = tuple(sorted(records, key=lambda record: record.record_digest))
    return BugHoundIndependentReproductionRegistryReceiptV4(
        registry_generation=REGISTRY_GENERATION,
        record_digests=tuple(record.record_digest for record in ordered),
        active_record_count=sum(
            1
            for record in ordered
            if record.registry_current is True
            and record.independently_observed is True
            and record.revoked is False
            and record.external_effect is False
        ),
    )


def independent_reproduction_registry_receipt() -> BugHoundIndependentReproductionRegistryReceiptV4:
    return _registry_receipt_from_records(_CANONICAL_REPRODUCTION_RECORDS)


def _verify_registry_record(
    *,
    reproduction: IndependentBountyReproductionReceiptV1,
    candidate: BountyCandidateEvidenceV1,
    mission_input: BugHoundCashMissionInputV1,
    record: BugHoundIndependentReproductionRegistryRecordV1,
) -> None:
    _validate_registry_record_shape(record)
    if record.registry_current is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_STALE")
    if record.independently_observed is not True:
        raise ValueError("INDEPENDENT_REPRODUCTION_INDEPENDENT_OBSERVER_REQUIRED")
    if record.revoked is not False:
        raise ValueError("INDEPENDENT_REPRODUCTION_REVOKED")

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


def _resolve_from_records(
    *,
    records: tuple[BugHoundIndependentReproductionRegistryRecordV1, ...],
    reproduction: IndependentBountyReproductionReceiptV1,
    candidate: BountyCandidateEvidenceV1,
    mission_input: BugHoundCashMissionInputV1,
) -> BugHoundIndependentReproductionRegistryRecordV1:
    """Resolve exactly one active exact-match record; ambiguity fails closed."""
    valid: list[BugHoundIndependentReproductionRegistryRecordV1] = []
    for record in records:
        try:
            _verify_registry_record(
                reproduction=reproduction,
                candidate=candidate,
                mission_input=mission_input,
                record=record,
            )
        except ValueError:
            continue
        valid.append(record)
    if not valid:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_REQUIRED")
    if len(valid) != 1:
        raise ValueError("INDEPENDENT_REPRODUCTION_REGISTRY_AMBIGUOUS")
    return valid[0]


def _compose_registered_independent_reproduction(
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
    record: BugHoundIndependentReproductionRegistryRecordV1,
    registry_records: tuple[BugHoundIndependentReproductionRegistryRecordV1, ...] | None = None,
) -> BugHoundRegisteredIndependentReproductionAdmissionV1:
    """Private reducer after one source-owned record has been resolved."""
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

    registry = _registry_receipt_from_records(registry_records or (record,))
    return BugHoundRegisteredIndependentReproductionAdmissionV1(
        candidate_admission=admitted,
        registry_record_digest=record.record_digest,
        registry_receipt_ref=record.registry_receipt_ref,
        registry_observer_ref=record.registry_observer_ref,
        registry_observer_generation=record.registry_observer_generation,
        registry_generation=registry.registry_generation,
        registry_digest=registry.registry_digest,
    )


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
) -> BugHoundRegisteredIndependentReproductionAdmissionV1:
    """Resolve reproduction provenance only from the source-owned registry."""
    if independent_reproduction.external_effect:
        raise ValueError("BOUNTY_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN")
    record = _resolve_from_records(
        records=_CANONICAL_REPRODUCTION_RECORDS,
        reproduction=independent_reproduction,
        candidate=candidate,
        mission_input=mission_input,
    )
    return _compose_registered_independent_reproduction(
        mission_input=mission_input,
        candidate=candidate,
        independent_reproduction=independent_reproduction,
        duplicate_pressure_state=duplicate_pressure_state,
        duplicate_check_currentness_ref=duplicate_check_currentness_ref,
        report_lint_state=report_lint_state,
        report_digest=report_digest,
        program_admissibility_state=program_admissibility_state,
        program_admissibility_ref=program_admissibility_ref,
        record=record,
        registry_records=_CANONICAL_REPRODUCTION_RECORDS,
    )


def registered_reproduction_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(admit_with_registered_independent_reproduction).parameters)
