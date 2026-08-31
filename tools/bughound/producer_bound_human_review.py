"""Canonical producer-bound human-review gate for BugHound cash bounties.

The consequence-bearing public API accepts raw current mission/evidence/scheduler
inputs and traverses the source-owned candidate-producer admission internally.
A caller cannot substitute a serialized candidate receipt, producer record,
registry, trusted boolean, expected producer identity, or secret.

A successful packet is permission for a human to inspect evidence only. It never
authorizes target interaction, credentials, disclosure, submission, claiming,
payment, spend, deployment, or any external effect.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import inspect
import json

from tools.bughound.bounty_mission import (
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)
from tools.bughound.cash_scheduler import BugHoundCashSchedulerDecisionV1
from tools.bughound.producer_bound_candidate_admission import (
    BugHoundCashCandidateEvidenceBundleV1,
    ProducerBoundBugHoundCashCandidateReceiptV1,
    admit_producer_bound_cash_bounty_candidate_for_human_review,
)

SCHEMA = "ProducerBoundBugHoundCashHumanReviewPacketV1"
STATUS = "READY_FOR_HUMAN_REVIEW_DECISION"
REVIEW_CHECKS = (
    "CONFIRM_CURRENT_PROGRAM_PAYOUT_AND_SCOPE",
    "CONFIRM_PRODUCER_REGISTRY_RECORD_CURRENTNESS",
    "CONFIRM_INDEPENDENT_REPRODUCTION_WITNESS",
    "CONFIRM_PUBLIC_DUPLICATE_STATE_AND_NOVEL_ROOT_CAUSE",
    "CONFIRM_REPORT_ACCURACY_AND_CONSERVATIVE_IMPACT",
    "HUMAN_DECIDES_IF_ANY_SUBMISSION_EFFECT_IS_SEPARATELY_AUTHORIZED",
)


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


def _require_no_effect_authority(obj: object, prefix: str) -> None:
    for field in (
        "live_target_testing_authorized",
        "credential_use_authorized",
        "submission_authorized",
        "claim_or_payment_authorized",
        "external_effect",
    ):
        if getattr(obj, field, None) is not False:
            raise ValueError(f"{prefix}_{field.upper()}_MUST_BE_FALSE")


@dataclass(frozen=True)
class ProducerBoundBugHoundCashHumanReviewPacketV1:
    work_item_id: str
    candidate_id: str
    program_ref: str
    target_ref: str
    target_generation: str
    mission_receipt_digest: str
    producer_bound_candidate_receipt_digest: str
    evidence_bundle_digest: str
    producer_registry_record_digest: str
    scheduler_decision_digest: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    independent_reproduction_digest: str
    duplicate_pressure_state: str
    report_digest: str
    reward_currency: str
    reward_floor_minor: int
    reward_ceiling_minor: int
    payout_rules_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    candidate_producer_trust_proven: bool = True
    human_authorization_verified: bool = False
    ready_for_human_review: bool = True
    reviewer_required_checks: tuple[str, ...] = REVIEW_CHECKS
    status: str = STATUS
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def packet_digest(self) -> str:
        return _digest("AURA_BUGHOUND_PRODUCER_BOUND_HUMAN_REVIEW_PACKET_V1", asdict(self))


def _compose_from_producer_bound_candidate(
    *,
    mission_input: BugHoundCashMissionInputV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
    producer_bound_candidate: ProducerBoundBugHoundCashCandidateReceiptV1,
    scheduler_decision: BugHoundCashSchedulerDecisionV1,
) -> ProducerBoundBugHoundCashHumanReviewPacketV1:
    """Private reducer for an already traversed producer-bound candidate path."""
    mission = admit_cash_bounty_mission(mission_input)
    candidate = producer_bound_candidate

    if candidate.candidate_producer_trust_proven is not True:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_PRODUCER_TRUST_REQUIRED")
    if candidate.status != "READY_FOR_HUMAN_SUBMISSION_REVIEW":
        raise ValueError("BUGHOUND_HUMAN_REVIEW_CANDIDATE_NOT_READY")
    if candidate.ready_for_human_submission_review is not True:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_CANDIDATE_READY_FLAG_REQUIRED")
    _require_no_effect_authority(candidate, "BUGHOUND_PRODUCER_BOUND_CANDIDATE")

    if candidate.candidate_id != evidence_bundle.candidate.candidate_id:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_CANDIDATE_ID_MISMATCH")
    if candidate.target_ref != mission_input.target_ref:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_TARGET_MISMATCH")
    if candidate.target_generation != mission_input.target_generation:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_TARGET_GENERATION_MISMATCH")
    if candidate.evidence_bundle_digest != evidence_bundle.bundle_digest:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_EVIDENCE_BUNDLE_MISMATCH")
    if candidate.producer_ref != evidence_bundle.producer_ref:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_PRODUCER_REF_MISMATCH")
    if candidate.producer_generation != evidence_bundle.producer_generation:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_PRODUCER_GENERATION_MISMATCH")
    if candidate.producer_currentness_ref != evidence_bundle.producer_currentness_ref:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_PRODUCER_CURRENTNESS_MISMATCH")

    if scheduler_decision.mission_receipt_digest != mission.receipt_digest:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_SCHEDULER_MISSION_MISMATCH")
    if not isinstance(scheduler_decision.work_item_id, str) or not scheduler_decision.work_item_id.strip():
        raise ValueError("BUGHOUND_HUMAN_REVIEW_WORK_ITEM_ID_REQUIRED")
    _require_no_effect_authority(scheduler_decision, "BUGHOUND_HUMAN_REVIEW_SCHEDULER")

    at_human_gate = (
        scheduler_decision.next_action == "PREPARE_HUMAN_SUBMISSION_REVIEW"
        and scheduler_decision.selected_gap == "G_EXTERNAL_ACCEPTANCE"
    ) or (
        scheduler_decision.next_action == "NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY"
        and scheduler_decision.selected_gap is None
        and scheduler_decision.stop_reason == "EVIDENCE_GAPS_CLOSED"
    )
    if not at_human_gate:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE")

    if evidence_bundle.duplicate_pressure_state not in {
        "LOW_OBSERVED_DUPLICATE_PRESSURE",
        "MEDIUM_DUPLICATE_PRESSURE",
    }:
        raise ValueError("BUGHOUND_HUMAN_REVIEW_DUPLICATE_STATE_NOT_ADMISSIBLE")
    if evidence_bundle.report_lint_state != "REPORT_LINT_CLEAN":
        raise ValueError("BUGHOUND_HUMAN_REVIEW_REPORT_LINT_REQUIRED")
    if evidence_bundle.program_admissibility_state != "CURRENTLY_ADMISSIBLE":
        raise ValueError("BUGHOUND_HUMAN_REVIEW_PROGRAM_ADMISSIBILITY_REQUIRED")

    return ProducerBoundBugHoundCashHumanReviewPacketV1(
        work_item_id=scheduler_decision.work_item_id,
        candidate_id=candidate.candidate_id,
        program_ref=mission_input.program_ref,
        target_ref=candidate.target_ref,
        target_generation=candidate.target_generation,
        mission_receipt_digest=mission.receipt_digest,
        producer_bound_candidate_receipt_digest=candidate.receipt_digest,
        evidence_bundle_digest=evidence_bundle.bundle_digest,
        producer_registry_record_digest=candidate.producer_registry_record_digest,
        scheduler_decision_digest=scheduler_decision.decision_digest,
        producer_ref=candidate.producer_ref,
        producer_generation=candidate.producer_generation,
        producer_currentness_ref=candidate.producer_currentness_ref,
        independent_reproduction_digest=evidence_bundle.independent_reproduction.receipt_digest,
        duplicate_pressure_state=evidence_bundle.duplicate_pressure_state,
        report_digest=evidence_bundle.report_digest,
        reward_currency=mission_input.reward_currency,
        reward_floor_minor=mission_input.reward_floor_minor,
        reward_ceiling_minor=mission_input.reward_ceiling_minor,
        payout_rules_digest=mission_input.payout_rules_digest,
        scope_rules_digest=mission_input.scope_rules_digest,
        source_currentness_ref=mission_input.source_currentness_ref,
    )


def compile_producer_bound_cash_human_review_packet(
    *,
    mission_input: BugHoundCashMissionInputV1,
    evidence_bundle: BugHoundCashCandidateEvidenceBundleV1,
    scheduler_decision: BugHoundCashSchedulerDecisionV1,
) -> ProducerBoundBugHoundCashHumanReviewPacketV1:
    """Force canonical producer resolution at the public human-review boundary."""
    candidate = admit_producer_bound_cash_bounty_candidate_for_human_review(
        mission_input=mission_input,
        evidence_bundle=evidence_bundle,
    )
    return _compose_from_producer_bound_candidate(
        mission_input=mission_input,
        evidence_bundle=evidence_bundle,
        producer_bound_candidate=candidate,
        scheduler_decision=scheduler_decision,
    )


def producer_bound_human_review_parameter_names() -> tuple[str, ...]:
    return tuple(
        inspect.signature(compile_producer_bound_cash_human_review_packet).parameters
    )
