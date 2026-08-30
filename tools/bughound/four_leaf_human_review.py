"""Canonical four-leaf human-review consequence boundary for BugHound.

This successor is layered directly on the PR446 four-leaf owner.  The public
boundary accepts only raw mission/candidate/evidence/scheduler inputs.  It first
traverses the source-owned independent-reproduction registry so production HOLD
ordering is explicit, then invokes PR446's canonical four-leaf join, which
traverses the same reproduction owner plus independently source-owned duplicate,
report-lint, and program-admissibility artifacts.

The repeated reproduction check is a prerequisite verification, not a second
trust owner.  No registry, record, lookup, expected producer, prebuilt admission,
secret, trusted boolean, or authority bit is accepted by this public API.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.bughound.bounty_candidate_admission import (
    BountyCandidateEvidenceV1,
    IndependentBountyReproductionReceiptV1,
)
from tools.bughound.bounty_mission import BugHoundCashMissionInputV1, admit_cash_bounty_mission
from tools.bughound.candidate_evidence_trust_join import (
    CandidateEvidenceTrustJoinReceiptV2,
    DuplicateCheckEvidenceV1,
    ProgramAdmissibilityEvidenceV1,
    ReportLintEvidenceV1,
    admit_registered_candidate_evidence_trust,
)
from tools.bughound.cash_scheduler import BugHoundCashSchedulerDecisionV1
from tools.bughound.registered_reproduction_gate import admit_with_registered_independent_reproduction

SCHEMA = "FourLeafBugHoundCashHumanReviewPacketV2"
STATUS = "READY_FOR_HUMAN_REVIEW_DECISION"
REVIEW_CHECKS = (
    "CONFIRM_CURRENT_PROGRAM_PAYOUT_AND_SCOPE",
    "CONFIRM_INDEPENDENT_REPRODUCTION_REGISTRY_CURRENTNESS",
    "CONFIRM_DUPLICATE_PRODUCER_CURRENTNESS",
    "CONFIRM_REPORT_LINT_PRODUCER_CURRENTNESS",
    "CONFIRM_PROGRAM_ADMISSIBILITY_PRODUCER_CURRENTNESS",
    "CONFIRM_NO_PROOF_LEAF_INVALIDATED_SINCE_JOIN",
    "HUMAN_DECIDES_IF_ANY_SEPARATE_EFFECT_AUTHORIZATION_EXISTS",
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _require_no_effect(obj: object, prefix: str) -> None:
    for field in (
        "live_target_testing_authorized",
        "credential_use_authorized",
        "submission_authorized",
        "claim_or_payment_authorized",
        "external_effect",
    ):
        if getattr(obj, field, False) is not False:
            raise ValueError(f"{prefix}_{field.upper()}_MUST_BE_FALSE")
    if getattr(obj, "authority", False) is not False:
        raise ValueError(f"{prefix}_AUTHORITY_MUST_BE_FALSE")


@dataclass(frozen=True)
class FourLeafBugHoundCashHumanReviewPacketV2:
    work_item_id: str
    candidate_id: str
    program_ref: str
    target_ref: str
    target_generation: str
    mission_receipt_digest: str
    four_leaf_join_receipt_digest: str
    scheduler_decision_digest: str
    reproduction_registry_record_digest: str
    duplicate_registry_record_digest: str
    report_lint_registry_record_digest: str
    program_registry_record_digest: str
    duplicate_artifact_digest: str
    report_lint_artifact_digest: str
    program_artifact_digest: str
    reward_currency: str
    reward_floor_minor: int | None
    reward_ceiling_minor: int | None
    payout_rules_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    candidate_evidence_trust_proven: bool = True
    independent_reproduction_registry_proven: bool = True
    duplicate_check_producer_proven: bool = True
    report_lint_producer_proven: bool = True
    program_admissibility_producer_proven: bool = True
    human_authorization_verified: bool = False
    ready_for_human_review: bool = True
    reviewer_required_checks: tuple[str, ...] = REVIEW_CHECKS
    status: str = STATUS
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def packet_digest(self) -> str:
        return _digest("AURA_BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_PACKET_V2", asdict(self))


def _verify_scheduler(*, mission_receipt_digest: str, scheduler: BugHoundCashSchedulerDecisionV1) -> None:
    if scheduler.mission_receipt_digest != mission_receipt_digest:
        raise ValueError("BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_MISSION_MISMATCH")
    if not isinstance(scheduler.work_item_id, str) or not scheduler.work_item_id.strip():
        raise ValueError("BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_WORK_ITEM_ID_REQUIRED")
    _require_no_effect(scheduler, "BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER")
    at_human_gate = (
        scheduler.next_action == "PREPARE_HUMAN_SUBMISSION_REVIEW"
        and scheduler.selected_gap == "G_EXTERNAL_ACCEPTANCE"
    ) or (
        scheduler.next_action == "NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY"
        and scheduler.selected_gap is None
        and scheduler.stop_reason == "EVIDENCE_GAPS_CLOSED"
    )
    if not at_human_gate:
        raise ValueError("BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE")


def _compose_packet(
    *,
    mission_input: BugHoundCashMissionInputV1,
    join: CandidateEvidenceTrustJoinReceiptV2,
    scheduler_decision: BugHoundCashSchedulerDecisionV1,
) -> FourLeafBugHoundCashHumanReviewPacketV2:
    mission = admit_cash_bounty_mission(mission_input)
    _verify_scheduler(mission_receipt_digest=mission.receipt_digest, scheduler=scheduler_decision)
    _require_no_effect(join, "BUGHOUND_FOUR_LEAF_JOIN")
    if not (
        join.candidate_evidence_trust_proven
        and join.ready_for_human_review_evidence
        and join.independent_reproduction_registry_proven
        and join.duplicate_check_producer_proven
        and join.report_lint_producer_proven
        and join.program_admissibility_producer_proven
    ):
        raise ValueError("BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_TRUST_JOIN_REQUIRED")
    if join.target_ref != mission_input.target_ref or join.target_generation != mission_input.target_generation:
        raise ValueError("BUGHOUND_FOUR_LEAF_HUMAN_REVIEW_TARGET_MISMATCH")
    return FourLeafBugHoundCashHumanReviewPacketV2(
        work_item_id=scheduler_decision.work_item_id,
        candidate_id=join.candidate_id,
        program_ref=mission_input.program_ref,
        target_ref=join.target_ref,
        target_generation=join.target_generation,
        mission_receipt_digest=mission.receipt_digest,
        four_leaf_join_receipt_digest=join.receipt_digest,
        scheduler_decision_digest=scheduler_decision.decision_digest,
        reproduction_registry_record_digest=join.reproduction_registry_record_digest,
        duplicate_registry_record_digest=join.duplicate_registry_record_digest,
        report_lint_registry_record_digest=join.report_lint_registry_record_digest,
        program_registry_record_digest=join.program_registry_record_digest,
        duplicate_artifact_digest=join.duplicate_artifact_digest,
        report_lint_artifact_digest=join.report_lint_artifact_digest,
        program_artifact_digest=join.program_artifact_digest,
        reward_currency=mission_input.reward_currency,
        reward_floor_minor=mission_input.reward_floor_minor,
        reward_ceiling_minor=mission_input.reward_ceiling_minor,
        payout_rules_digest=mission_input.payout_rules_digest,
        scope_rules_digest=mission_input.scope_rules_digest,
        source_currentness_ref=mission_input.source_currentness_ref,
    )


def compile_four_leaf_cash_human_review_packet(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate: BountyCandidateEvidenceV1,
    independent_reproduction: IndependentBountyReproductionReceiptV1,
    duplicate: DuplicateCheckEvidenceV1,
    report_lint: ReportLintEvidenceV1,
    program: ProgramAdmissibilityEvidenceV1,
    scheduler_decision: BugHoundCashSchedulerDecisionV1,
) -> FourLeafBugHoundCashHumanReviewPacketV2:
    """Force reproduction prerequisite, then canonical four-leaf traversal."""
    # Deliberately first: a missing source-owned reproduction record is the
    # production HOLD and must stop before downstream leaf diagnosis.
    prerequisite = admit_with_registered_independent_reproduction(
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
    _require_no_effect(prerequisite, "BUGHOUND_REGISTERED_REPRODUCTION")
    if prerequisite.independent_reproduction_registry_proven is not True:
        raise ValueError("BUGHOUND_REPRODUCTION_TRUST_REQUIRED")

    # PR446 remains the sole owner of the four-leaf join. It traverses the same
    # canonical reproduction registry and the separate leaf registry internally.
    join = admit_registered_candidate_evidence_trust(
        mission_input=mission_input,
        candidate=candidate,
        independent_reproduction=independent_reproduction,
        duplicate=duplicate,
        report_lint=report_lint,
        program=program,
    )
    return _compose_packet(
        mission_input=mission_input,
        join=join,
        scheduler_decision=scheduler_decision,
    )


def four_leaf_human_review_parameter_names() -> tuple[str, ...]:
    return tuple(inspect.signature(compile_four_leaf_cash_human_review_packet).parameters)
