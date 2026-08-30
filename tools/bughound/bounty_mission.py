"""Canonical cash-bounty mission gate for BugHound.

BugHound may operate multiple isolated target profiles over one virtual-Arena
engine. This module owns only the external cash-bounty compiler. AuraOS
self-hardening remains a first-class BugHound target profile, but it is not
cash-mission work and may not inherit payout, scope, credential, submission, or
external-effect authority from this compiler.

This module is deliberately pre-effect. Mission admission proves only that a
work item is a current cash-bounty research candidate. It does not authorize
live-target testing, credentials, provider calls, disclosure, report submission,
claiming, spend, merge, promotion, deployment, or any other external effect.

The receipt deliberately retains the exact payout/scope/source bindings that
were admitted. Downstream effect consumers must compare against these exact
bindings rather than reconstructing or merely asserting currentness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

from tools.bughound.target_profile import CASH_BOUNTY_PROFILE_ID

SCHEMA = "BugHoundCashMissionReceiptV1"
CANONICAL_PROFILE_ID = CASH_BOUNTY_PROFILE_ID
CASH_REWARD_STATE = "VERIFIED_CURRENT_CASH_REWARD"
PROGRAM_STATE = "ACTIVE"
SCOPE_STATE = "CURRENT_SCOPE_BOUND"
SOURCE_STATE = "CURRENT_SOURCE_BOUND"


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


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


@dataclass(frozen=True)
class BugHoundCashMissionInputV1:
    profile_id: str
    program_ref: str
    target_ref: str
    target_generation: str
    program_state: str
    cash_reward_state: str
    reward_currency: str
    reward_floor_minor: int | None
    reward_ceiling_minor: int | None
    payout_rules_digest: str
    scope_state: str
    scope_rules_digest: str
    source_state: str
    source_currentness_ref: str
    testing_ceiling: str
    duplicate_pressure_state: str = "UNKNOWN"


@dataclass(frozen=True)
class BugHoundCashMissionReceiptV1:
    profile_id: str
    program_ref: str
    target_ref: str
    target_generation: str
    cash_bounty_mission_admitted: bool
    payout_current: bool
    scope_current: bool
    source_current: bool
    payout_rules_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    reward_currency: str
    reward_floor_minor: int | None
    reward_ceiling_minor: int | None
    research_effect_ceiling: str
    duplicate_pressure_state: str
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_CASH_MISSION_V1", asdict(self))


def admit_cash_bounty_mission(
    item: BugHoundCashMissionInputV1,
) -> BugHoundCashMissionReceiptV1:
    """Admit only current cash-bounty research into the cash mission lane.

    Other registered BugHound profiles fail this cash compiler by design. That
    rejection is profile isolation, not a statement that those profiles are
    outside BugHound. A successful cash receipt remains pre-effect and cannot be
    used as live-target, credential, submission, claim, or payment authority.
    """
    if item.profile_id != CANONICAL_PROFILE_ID:
        raise ValueError("BUGHOUND_CASH_COMPILER_PROFILE_MISMATCH")
    _require_text("PROGRAM_REF", item.program_ref)
    _require_text("TARGET_REF", item.target_ref)
    _require_text("TARGET_GENERATION", item.target_generation)
    _require_text("PAYOUT_RULES_DIGEST", item.payout_rules_digest)
    _require_text("SCOPE_RULES_DIGEST", item.scope_rules_digest)
    _require_text("SOURCE_CURRENTNESS_REF", item.source_currentness_ref)
    _require_text("TESTING_CEILING", item.testing_ceiling)

    if item.program_state != PROGRAM_STATE:
        raise ValueError("BUGHOUND_PROGRAM_NOT_ACTIVE")
    if item.cash_reward_state != CASH_REWARD_STATE:
        raise ValueError("BUGHOUND_CASH_REWARD_NOT_CURRENT")
    currency = item.reward_currency.upper()
    if currency not in {"USD", "CAD", "EUR", "GBP"}:
        raise ValueError("BUGHOUND_CASH_CURRENCY_REQUIRED")
    if item.reward_floor_minor is not None and item.reward_floor_minor < 0:
        raise ValueError("BUGHOUND_REWARD_FLOOR_INVALID")
    if item.reward_ceiling_minor is not None and item.reward_ceiling_minor < 0:
        raise ValueError("BUGHOUND_REWARD_CEILING_INVALID")
    if (
        item.reward_floor_minor is not None
        and item.reward_ceiling_minor is not None
        and item.reward_floor_minor > item.reward_ceiling_minor
    ):
        raise ValueError("BUGHOUND_REWARD_RANGE_INVALID")
    if item.scope_state != SCOPE_STATE:
        raise ValueError("BUGHOUND_SCOPE_NOT_CURRENT")
    if item.source_state != SOURCE_STATE:
        raise ValueError("BUGHOUND_SOURCE_NOT_CURRENT")

    return BugHoundCashMissionReceiptV1(
        profile_id=item.profile_id,
        program_ref=item.program_ref,
        target_ref=item.target_ref,
        target_generation=item.target_generation,
        cash_bounty_mission_admitted=True,
        payout_current=True,
        scope_current=True,
        source_current=True,
        payout_rules_digest=item.payout_rules_digest,
        scope_rules_digest=item.scope_rules_digest,
        source_currentness_ref=item.source_currentness_ref,
        reward_currency=currency,
        reward_floor_minor=item.reward_floor_minor,
        reward_ceiling_minor=item.reward_ceiling_minor,
        research_effect_ceiling=item.testing_ceiling,
        duplicate_pressure_state=item.duplicate_pressure_state,
    )
