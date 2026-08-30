"""Deterministic pre-effect cash-bounty scheduler for BugHound.

The scheduler consumes a current BugHound cash mission and a typed evidence-gap
state, then selects exactly one next local/preflight action. It does not invent
probabilities, exploitability, payout likelihood, or expected value. It never
executes target interaction, credentials, disclosure, submission, claiming, or
payment effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.bughound.bounty_mission import (
    BugHoundCashMissionInputV1,
    admit_cash_bounty_mission,
)

SCHEMA = "BugHoundCashSchedulerDecisionV1"

GAP_ORDER = (
    "G_CAUSAL_MODEL",
    "G_REACHABILITY",
    "G_CONTROL",
    "G_SINK",
    "G_REPRO",
    "G_INDEPENDENT_REPRO",
    "G_DUPLICATE",
    "G_REPORT_QUALITY",
    "G_EXTERNAL_ACCEPTANCE",
)

ACTION_FOR_GAP = {
    "G_CAUSAL_MODEL": "BUILD_CAUSAL_MODEL",
    "G_REACHABILITY": "PROVE_REACHABILITY_LOCALLY",
    "G_CONTROL": "BUILD_NEGATIVE_CONTROL",
    "G_SINK": "PROVE_CONSEQUENCE_SINK_LOCALLY",
    "G_REPRO": "REPRODUCE_IN_CURRENT_AUTHORIZED_LOCAL_ENVIRONMENT",
    "G_INDEPENDENT_REPRO": "REQUEST_INDEPENDENT_REPRODUCTION_ARTIFACT",
    "G_DUPLICATE": "CHECK_PUBLIC_DUPLICATE_PRESSURE",
    "G_REPORT_QUALITY": "LINT_DISCLOSURE_SAFE_REPORT",
    "G_EXTERNAL_ACCEPTANCE": "PREPARE_HUMAN_SUBMISSION_REVIEW",
}


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
class CashBountyWorkStateV1:
    work_item_id: str
    unresolved_gaps: tuple[str, ...]
    duplicate_pressure_state: str
    probe_budget_minutes: int
    active_probe_minutes: int
    survivor_state: str
    source_generation: str
    currentness_ref: str


@dataclass(frozen=True)
class BugHoundCashSchedulerDecisionV1:
    work_item_id: str
    next_action: str
    selected_gap: str | None
    stop_reason: str | None
    unresolved_gaps: tuple[str, ...]
    mission_receipt_digest: str
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def decision_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_SCHEDULER_V1", asdict(self))


def schedule_next_cash_bounty_step(
    *,
    mission_input: BugHoundCashMissionInputV1,
    work_state: CashBountyWorkStateV1,
) -> BugHoundCashSchedulerDecisionV1:
    """Choose one next pre-effect action from typed unresolved evidence gaps."""
    mission = admit_cash_bounty_mission(mission_input)

    if not work_state.work_item_id.strip():
        raise ValueError("BUGHOUND_WORK_ITEM_ID_REQUIRED")
    if work_state.probe_budget_minutes <= 0:
        raise ValueError("BUGHOUND_PROBE_BUDGET_REQUIRED")
    if work_state.active_probe_minutes < 0:
        raise ValueError("BUGHOUND_ACTIVE_PROBE_MINUTES_INVALID")
    if work_state.source_generation != mission_input.target_generation:
        raise ValueError("BUGHOUND_WORK_SOURCE_GENERATION_MISMATCH")
    if work_state.currentness_ref != mission_input.source_currentness_ref:
        raise ValueError("BUGHOUND_WORK_CURRENTNESS_MISMATCH")

    unknown_gaps = tuple(g for g in work_state.unresolved_gaps if g not in GAP_ORDER)
    if unknown_gaps:
        raise ValueError("BUGHOUND_UNKNOWN_EVIDENCE_GAP:" + ",".join(sorted(unknown_gaps)))
    if len(set(work_state.unresolved_gaps)) != len(work_state.unresolved_gaps):
        raise ValueError("BUGHOUND_DUPLICATE_EVIDENCE_GAP")

    if work_state.active_probe_minutes >= work_state.probe_budget_minutes:
        return BugHoundCashSchedulerDecisionV1(
            work_item_id=work_state.work_item_id,
            next_action="STOP_AND_COLLAPSE",
            selected_gap=None,
            stop_reason="PROBE_BUDGET_EXHAUSTED",
            unresolved_gaps=work_state.unresolved_gaps,
            mission_receipt_digest=mission.receipt_digest,
        )

    if work_state.duplicate_pressure_state == "PUBLICLY_KNOWN_ROOT_CAUSE":
        return BugHoundCashSchedulerDecisionV1(
            work_item_id=work_state.work_item_id,
            next_action="PARK_AND_COLLAPSE_NEGATIVE_KNOWLEDGE",
            selected_gap="G_DUPLICATE" if "G_DUPLICATE" in work_state.unresolved_gaps else None,
            stop_reason="PUBLIC_ROOT_CAUSE_ALREADY_KNOWN",
            unresolved_gaps=work_state.unresolved_gaps,
            mission_receipt_digest=mission.receipt_digest,
        )

    if (
        work_state.duplicate_pressure_state == "HIGH_DUPLICATE_PRESSURE"
        and work_state.survivor_state not in {"TWO_EDGE_SURVIVOR", "REPRODUCED_SURVIVOR"}
    ):
        return BugHoundCashSchedulerDecisionV1(
            work_item_id=work_state.work_item_id,
            next_action="PARK_PENDING_DIFFERENTIATING_EVIDENCE",
            selected_gap="G_DUPLICATE" if "G_DUPLICATE" in work_state.unresolved_gaps else None,
            stop_reason="HIGH_DUPLICATE_PRESSURE_WITHOUT_STRONG_SURVIVOR",
            unresolved_gaps=work_state.unresolved_gaps,
            mission_receipt_digest=mission.receipt_digest,
        )

    for gap in GAP_ORDER:
        if gap in work_state.unresolved_gaps:
            return BugHoundCashSchedulerDecisionV1(
                work_item_id=work_state.work_item_id,
                next_action=ACTION_FOR_GAP[gap],
                selected_gap=gap,
                stop_reason=None,
                unresolved_gaps=work_state.unresolved_gaps,
                mission_receipt_digest=mission.receipt_digest,
            )

    return BugHoundCashSchedulerDecisionV1(
        work_item_id=work_state.work_item_id,
        next_action="NO_LOCAL_RESIDUAL_HUMAN_GATE_ONLY",
        selected_gap=None,
        stop_reason="EVIDENCE_GAPS_CLOSED",
        unresolved_gaps=(),
        mission_receipt_digest=mission.receipt_digest,
    )
