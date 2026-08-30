"""Pre-effect human review packet for BugHound cash-bounty candidates.

This module closes only the internal handoff from a current cash candidate and
cash scheduler decision to a compact evidence packet. It deliberately does not
contain exploit payloads, live-target actions, credentials, submission calls,
payment claims, or any external-effect authority.

Current upstream PR420 candidate evidence is self-consistency checked but its
independent-reproduction / duplicate / lint / program-admissibility producer
trust boundary is not yet independently authenticated. Therefore this adapter
MUST preserve the lower-plane evidence while marking the packet producer-trust
blocked. It may not invent a caller-set `trusted=True` escape hatch.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.bughound.bounty_candidate_admission import (
    BugHoundCashCandidateAdmissionReceiptV1,
)
from tools.bughound.bounty_mission import (
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)
from tools.bughound.cash_scheduler import BugHoundCashSchedulerDecisionV1

SCHEMA = "BugHoundCashHumanReviewPacketV1"
STATUS = "HUMAN_REVIEW_PACKET_EVIDENCE_TRUST_REQUIRED"
UPSTREAM_TRUST_BLOCKER = "UPSTREAM_CANDIDATE_PRODUCER_TRUST_UNPROVEN"
REVIEW_CHECKS = (
    "CONFIRM_CURRENT_PROGRAM_AND_PAYOUT_RULES",
    "CONFIRM_CURRENT_SCOPE_AND_DISCLOSURE_RULES",
    "CONFIRM_INDEPENDENT_REPRODUCTION_PRODUCER_AUTHENTICITY",
    "CONFIRM_DUPLICATE_CHECK_PRODUCER_AND_PUBLIC_KNOWN_STATE",
    "CONFIRM_REPORT_LINT_PRODUCER_AND_CONSERVATIVE_IMPACT",
    "CONFIRM_PROGRAM_ADMISSIBILITY_PRODUCER_CURRENTNESS",
    "HUMAN_DECIDES_WHETHER_TO_SUBMIT_ONLY_AFTER_TRUST_GAPS_CLOSE",
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
class BugHoundCashHumanReviewPacketV1:
    work_item_id: str
    candidate_id: str
    program_ref: str
    target_ref: str
    target_generation: str
    mission_receipt_digest: str
    candidate_admission_digest: str
    scheduler_decision_digest: str
    independent_reproduction_digest: str
    duplicate_pressure_state: str
    report_digest: str
    reward_currency: str
    reward_floor_minor: int
    reward_ceiling_minor: int
    payout_rules_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    blockers: tuple[str, ...] = (UPSTREAM_TRUST_BLOCKER,)
    candidate_producer_trust_proven: bool = False
    human_authorization_verified: bool = False
    ready_for_human_review: bool = False
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
        return _digest("AURA_BUGHOUND_CASH_HUMAN_REVIEW_PACKET_V1", asdict(self))


def compile_cash_bounty_human_review_packet(
    *,
    mission_input: BugHoundCashMissionInputV1,
    candidate_admission: BugHoundCashCandidateAdmissionReceiptV1,
    scheduler_decision: BugHoundCashSchedulerDecisionV1,
) -> BugHoundCashHumanReviewPacketV1:
    """Compile a digest-only evidence packet while preserving upstream trust debt.

    `READY_FOR_HUMAN_SUBMISSION_REVIEW` from the current PR420 contract is
    accepted only as lower-plane shape/currentness evidence. The packet is
    deliberately NOT promoted to human-review-ready because PR420 presently lets
    the same caller supply both candidate evidence and its expected reproduction
    identity/digest, and its duplicate/lint/program gates are assertion-shaped.
    A future producer/registry-bound upstream generation must reopen this module.
    """
    mission = admit_cash_bounty_mission(mission_input)

    if candidate_admission.status != "READY_FOR_HUMAN_SUBMISSION_REVIEW":
        raise ValueError("BUGHOUND_CANDIDATE_NOT_READY_FOR_LOWER_PLANE_PACKET")
    if candidate_admission.ready_for_human_submission_review is not True:
        raise ValueError("BUGHOUND_CANDIDATE_READY_FLAG_REQUIRED")
    if candidate_admission.blockers:
        raise ValueError("BUGHOUND_CANDIDATE_BLOCKERS_PRESENT")
    _require_no_effect_authority(candidate_admission, "BUGHOUND_CANDIDATE")

    if candidate_admission.target_ref != mission_input.target_ref:
        raise ValueError("BUGHOUND_REVIEW_TARGET_MISMATCH")
    if candidate_admission.target_generation != mission_input.target_generation:
        raise ValueError("BUGHOUND_REVIEW_TARGET_GENERATION_MISMATCH")
    if candidate_admission.mission_receipt_digest != mission.receipt_digest:
        raise ValueError("BUGHOUND_REVIEW_MISSION_RECEIPT_MISMATCH")
    if candidate_admission.duplicate_pressure_state not in {
        "LOW_OBSERVED_DUPLICATE_PRESSURE",
        "MEDIUM_DUPLICATE_PRESSURE",
    }:
        raise ValueError("BUGHOUND_REVIEW_DUPLICATE_STATE_NOT_ADMISSIBLE")

    if not isinstance(scheduler_decision.work_item_id, str) or not scheduler_decision.work_item_id.strip():
        raise ValueError("BUGHOUND_REVIEW_WORK_ITEM_ID_REQUIRED")
    if scheduler_decision.mission_receipt_digest != mission.receipt_digest:
        raise ValueError("BUGHOUND_REVIEW_SCHEDULER_MISSION_MISMATCH")
    _require_no_effect_authority(scheduler_decision, "BUGHOUND_SCHEDULER")

    at_human_gate = (
        scheduler_decision.next_action == "PREPARE_HUMAN_SUBMISSION_REVIEW"
        and scheduler_decision.selected_gap == "G_EXTERNAL_ACCEPTANCE"
    ) or (
        scheduler_decision.next_action == "NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY"
        and scheduler_decision.selected_gap is None
        and scheduler_decision.stop_reason == "EVIDENCE_GAPS_CLOSED"
    )
    if not at_human_gate:
        raise ValueError("BUGHOUND_REVIEW_SCHEDULER_NOT_AT_HUMAN_GATE")

    if not candidate_admission.independent_reproduction_digest.strip():
        raise ValueError("BUGHOUND_REVIEW_INDEPENDENT_REPRODUCTION_REQUIRED")
    if not candidate_admission.report_digest.strip():
        raise ValueError("BUGHOUND_REVIEW_REPORT_DIGEST_REQUIRED")

    return BugHoundCashHumanReviewPacketV1(
        work_item_id=scheduler_decision.work_item_id,
        candidate_id=candidate_admission.candidate_id,
        program_ref=mission_input.program_ref,
        target_ref=candidate_admission.target_ref,
        target_generation=candidate_admission.target_generation,
        mission_receipt_digest=mission.receipt_digest,
        candidate_admission_digest=candidate_admission.receipt_digest,
        scheduler_decision_digest=scheduler_decision.decision_digest,
        independent_reproduction_digest=candidate_admission.independent_reproduction_digest,
        duplicate_pressure_state=candidate_admission.duplicate_pressure_state,
        report_digest=candidate_admission.report_digest,
        reward_currency=mission_input.reward_currency,
        reward_floor_minor=mission_input.reward_floor_minor,
        reward_ceiling_minor=mission_input.reward_ceiling_minor,
        payout_rules_digest=mission_input.payout_rules_digest,
        scope_rules_digest=mission_input.scope_rules_digest,
        source_currentness_ref=mission_input.source_currentness_ref,
    )
