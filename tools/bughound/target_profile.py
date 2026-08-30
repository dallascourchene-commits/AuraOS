"""BugHound cash-bounty target-profile boundary.

Owner invariant: BugHound is the Arena capability for cash bug bounties.
AuraOS self-hardening may reuse authority-free generic discovery, reproduction,
benchmark, and evidence tools, but it is not a BugHound mission/profile and may
not enter BugHound payout, portfolio, scheduler, scope, credential, submission,
or effect state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json

SCHEMA = "BugHoundTargetProfileReceiptV1"
ENGINE_ID = "BUGHOUND_VIRTUAL_ARENA_ENGINE_V1"
CASH_BOUNTY_PROFILE_ID = "BUGHOUND_CASH_BOUNTY_V1"
# Historical compatibility marker only. It is deliberately NOT registered.
AURAOS_HARDENING_PROFILE_ID = "BUGHOUND_AURAOS_HARDENING_V1"

_PROFILE_KINDS = {
    CASH_BOUNTY_PROFILE_ID: "EXTERNAL_CASH_BOUNTY",
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


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


@dataclass(frozen=True)
class BugHoundTargetProfileV1:
    profile_id: str
    profile_kind: str
    target_ref: str
    target_generation: str


@dataclass(frozen=True)
class BugHoundTargetProfileReceiptV1:
    profile_id: str
    profile_kind: str
    target_ref: str
    target_generation: str
    engine_id: str
    cash_mission_eligible: bool
    # Retained for wire compatibility with the short-lived dual-profile draft.
    # It is always false under the owner cash-only invariant.
    auraos_hardening: bool = False
    cross_profile_authority_credit: bool = False
    payout_authority: bool = False
    live_target_testing_authority: bool = False
    submission_authority: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_TARGET_PROFILE_V1", asdict(self))


def bind_target_profile(
    profile: BugHoundTargetProfileV1,
) -> BugHoundTargetProfileReceiptV1:
    """Bind one exact cash-bounty BugHound profile without granting authority."""
    _require_text("PROFILE_ID", profile.profile_id)
    _require_text("PROFILE_KIND", profile.profile_kind)
    _require_text("TARGET_REF", profile.target_ref)
    _require_text("TARGET_GENERATION", profile.target_generation)

    expected_kind = _PROFILE_KINDS.get(profile.profile_id)
    if expected_kind is None:
        raise ValueError("BUGHOUND_PROFILE_NOT_REGISTERED")
    if profile.profile_kind != expected_kind:
        raise ValueError("BUGHOUND_PROFILE_KIND_MISMATCH")

    return BugHoundTargetProfileReceiptV1(
        profile_id=profile.profile_id,
        profile_kind=profile.profile_kind,
        target_ref=profile.target_ref,
        target_generation=profile.target_generation,
        engine_id=ENGINE_ID,
        cash_mission_eligible=True,
        auraos_hardening=False,
    )
