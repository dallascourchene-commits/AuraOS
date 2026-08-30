"""Cash-bounty effect and sanitized-memory boundary for BugHound.

BugHound is one virtual-Arena engine with separately admitted target profiles.
Canonical cash-mission admission lives in :mod:`tools.bughound.bounty_mission`.
This module starts strictly *after* a valid cash-mission receipt and preserves
three separate planes:

1. cash-mission/research admission,
2. exact live-effect authority for the cash-bounty profile,
3. authority-free sanitized reusable memory that may cross into another
   registered profile such as AuraOS hardening.

The cash and AuraOS-hardening profiles may reuse generic tools, but shared engine
or tool capability never transfers payout, scope, credential, submission, live-
testing, or disclosure authority between profiles.

The live-effect grant and sanitizer receipt are producer-bound proof planes.
Their own internal consistency is necessary but insufficient: the consumer must
also receive independently supplied expected producer/receipt identities.

D0 by default. Nothing here performs network access, credential use, submission,
claiming/payment, provider calls, repository mutation, deployment, or spend.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Iterable

from tools.bughound.bounty_mission import (
    CANONICAL_PROFILE_ID,
    BugHoundCashMissionReceiptV1,
)
from tools.bughound.target_profile import AURAOS_HARDENING_PROFILE_ID

LIVE_EFFECT_CLASS = "BOUNTY_LIVE_NETWORK_TEST"
GENERIC_SECURITY_TOOL_FOUNDRY = "GENERIC_SECURITY_TOOL_FOUNDRY"
GENERIC_REUSE_CONTEXTS = frozenset(
    {
        GENERIC_SECURITY_TOOL_FOUNDRY,
        AURAOS_HARDENING_PROFILE_ID,
    }
)
_REQUIRED_SANITIZED_CLASSES = frozenset(
    {
        "target_specific_material",
        "credentials_or_tokens",
        "private_endpoint",
        "undisclosed_exploit_material",
        "pii_or_third_party_data",
        "private_report_identifier",
    }
)


class CashEffectBoundaryError(ValueError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CashEffectBoundaryError("NONCANONICAL_BOUNDARY_STATE") from exc


def _digest(domain: str, value: object) -> str:
    return hashlib.sha256(domain.encode("utf-8") + b"\0" + _canonical(value)).hexdigest()


def _text(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CashEffectBoundaryError(code)
    return value.strip()


def _strings(values: Iterable[str], code: str) -> frozenset[str]:
    try:
        out = frozenset(values)
    except TypeError as exc:
        raise CashEffectBoundaryError(code) from exc
    if any(not isinstance(value, str) or not value for value in out):
        raise CashEffectBoundaryError(code)
    return out


def _verify_mission_receipt(receipt: BugHoundCashMissionReceiptV1) -> None:
    if not isinstance(receipt, BugHoundCashMissionReceiptV1):
        raise CashEffectBoundaryError("CASH_MISSION_RECEIPT_REQUIRED")
    if receipt.profile_id != CANONICAL_PROFILE_ID:
        raise CashEffectBoundaryError("NONCANONICAL_CASH_MISSION_REJECTED")
    if not receipt.cash_bounty_mission_admitted:
        raise CashEffectBoundaryError("CASH_MISSION_NOT_ADMITTED")
    if not (receipt.payout_current and receipt.scope_current and receipt.source_current):
        raise CashEffectBoundaryError("CASH_MISSION_CURRENTNESS_REQUIRED")
    if (
        receipt.live_target_testing_authorized
        or receipt.credential_use_authorized
        or receipt.submission_authorized
        or receipt.claim_or_payment_authorized
        or receipt.external_effect
    ):
        raise CashEffectBoundaryError("CASH_MISSION_RECEIPT_AUTHORITY_WIDENED")


@dataclass(frozen=True)
class SharedSecurityToolCapabilityV1:
    capability_id: str
    contexts: tuple[str, ...]
    local_only: bool = True
    network_required: bool = False
    credential_required: bool = False
    authority: bool = False
    schema: str = "SharedSecurityToolCapabilityV1"

    @property
    def capability_digest(self) -> str:
        return _digest("AURA_SHARED_SECURITY_TOOL_CAPABILITY_V1", asdict(self))


@dataclass(frozen=True)
class BountyLiveEffectGrantV1:
    profile_id: str
    mission_receipt_digest: str
    program_ref: str
    target_ref: str
    target_generation: str
    program_policy_snapshot_digest: str
    program_policy_generation: str
    program_policy_current: bool
    scope_rules_digest: str
    scope_currentness_ref: str
    target_currentness_ref: str
    effect_class: str
    network_origin: str
    network_allowlist: tuple[str, ...]
    credential_aliases: tuple[str, ...]
    human_authorization_ref: str | None
    revocation_currentness_ref: str
    disclosure_policy_ref: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    authority: bool = True
    schema: str = "BountyLiveEffectGrantV1"

    @property
    def grant_digest(self) -> str:
        return _digest("AURA_BUGHOUND_LIVE_EFFECT_GRANT_V1", asdict(self))


@dataclass(frozen=True)
class LiveEffectAdmissionReceiptV1:
    mission_receipt_digest: str
    effect_grant_digest: str
    producer_ref: str
    producer_generation: str
    program_ref: str
    target_ref: str
    target_generation: str
    effect_class: str
    network_origin: str
    live_effect_authorized: bool
    authority_scope: str
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    authority: bool = True
    external_effect_executed: bool = False
    schema: str = "LiveEffectAdmissionReceiptV1"

    @property
    def admission_digest(self) -> str:
        return _digest("AURA_BUGHOUND_LIVE_EFFECT_ADMISSION_V1", asdict(self))


@dataclass(frozen=True)
class SanitizedPatternReceiptV1:
    mission_receipt_digest: str
    disclosure_state_ref: str
    reusable_memory_policy_ref: str
    sanitizer_generation: str
    reviewer_ref: str
    producer_ref: str
    producer_generation: str
    producer_currentness_ref: str
    removed_classes: tuple[str, ...]
    retained_abstract_pattern_ref: str
    target_specific_material_present: bool
    credentials_or_tokens_present: bool
    private_endpoint_present: bool
    undisclosed_exploit_material_present: bool
    pii_or_third_party_data_present: bool
    private_report_identifier_present: bool
    authority: bool = False
    schema: str = "SanitizedPatternReceiptV1"

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_SANITIZED_PATTERN_V1", asdict(self))


@dataclass(frozen=True)
class ReusablePatternExportV1:
    source_cash_profile_id: str
    source_mission_receipt_digest: str
    sanitized_pattern_receipt_digest: str
    producer_ref: str
    producer_generation: str
    retained_abstract_pattern_ref: str
    destination_context: str
    cross_profile_reuse: bool
    bughound_mission_state_exported: bool = False
    payout_state_exported: bool = False
    scope_authority_exported: bool = False
    live_effect_authority_exported: bool = False
    disclosure_authority_exported: bool = False
    credential_state_exported: bool = False
    authority: bool = False
    external_effect: bool = False
    schema: str = "ReusablePatternExportV1"

    @property
    def export_digest(self) -> str:
        return _digest("AURA_BUGHOUND_REUSABLE_PATTERN_EXPORT_V1", asdict(self))


def admit_shared_tool_for_cash_research(
    receipt: BugHoundCashMissionReceiptV1,
    capability: SharedSecurityToolCapabilityV1,
) -> str:
    """Admit an authority-free local capability into the cash-bounty profile.

    The same generic capability may list the AuraOS-hardening profile as another
    compatible context, but this admission transfers no cash/profile authority.
    """
    _verify_mission_receipt(receipt)
    _text(capability.capability_id, "TOOL_CAPABILITY_ID_REQUIRED")
    contexts = _strings(capability.contexts, "TOOL_CONTEXTS_INVALID")
    if CANONICAL_PROFILE_ID not in contexts:
        raise CashEffectBoundaryError("TOOL_NOT_ADMITTED_FOR_CASH_BOUNTY")
    if capability.authority:
        raise CashEffectBoundaryError("TOOL_CAPABILITY_CANNOT_SELF_GRANT_AUTHORITY")
    if capability.network_required or capability.credential_required or not capability.local_only:
        raise CashEffectBoundaryError("EFFECTFUL_TOOL_REQUIRES_SEPARATE_LIVE_GRANT")
    return _digest(
        "AURA_BUGHOUND_CASH_RESEARCH_TOOL_ADMISSION_V1",
        {
            "mission_receipt_digest": receipt.receipt_digest,
            "capability_digest": capability.capability_digest,
        },
    )


def admit_live_effect(
    receipt: BugHoundCashMissionReceiptV1,
    grant: BountyLiveEffectGrantV1,
    *,
    expected_grant_digest: str,
    expected_producer_ref: str,
    expected_producer_generation: str,
) -> LiveEffectAdmissionReceiptV1:
    """Admit exactly one independently expected cash-profile live-test grant.

    This returns an admission receipt only. It does not execute the network
    effect and grants no submission, payout, or payment authority. A caller may
    not self-certify a grant merely by constructing a self-consistent dataclass.
    """
    _verify_mission_receipt(receipt)
    if grant.profile_id != CANONICAL_PROFILE_ID:
        raise CashEffectBoundaryError("LIVE_GRANT_NON_CASH_PROFILE")
    if grant.mission_receipt_digest != receipt.receipt_digest:
        raise CashEffectBoundaryError("LIVE_GRANT_MISSION_RECEIPT_MISMATCH")
    if grant.program_ref != receipt.program_ref:
        raise CashEffectBoundaryError("LIVE_GRANT_PROGRAM_MISMATCH")
    if grant.target_ref != receipt.target_ref or grant.target_generation != receipt.target_generation:
        raise CashEffectBoundaryError("LIVE_GRANT_TARGET_MISMATCH")
    if not grant.authority:
        raise CashEffectBoundaryError("LIVE_GRANT_AUTHORITY_REQUIRED")
    if not grant.program_policy_current:
        raise CashEffectBoundaryError("LIVE_GRANT_PROGRAM_POLICY_STALE")

    expected_digest = _text(expected_grant_digest, "EXPECTED_LIVE_GRANT_DIGEST_REQUIRED")
    expected_ref = _text(expected_producer_ref, "EXPECTED_LIVE_GRANT_PRODUCER_REQUIRED")
    expected_generation = _text(
        expected_producer_generation,
        "EXPECTED_LIVE_GRANT_PRODUCER_GENERATION_REQUIRED",
    )
    if grant.grant_digest != expected_digest:
        raise CashEffectBoundaryError("LIVE_GRANT_EXPECTATION_MISMATCH")
    if grant.producer_ref != expected_ref or grant.producer_generation != expected_generation:
        raise CashEffectBoundaryError("LIVE_GRANT_PRODUCER_MISMATCH")
    _text(grant.producer_currentness_ref, "LIVE_GRANT_PRODUCER_CURRENTNESS_REQUIRED")

    _text(grant.program_policy_snapshot_digest, "LIVE_GRANT_POLICY_DIGEST_REQUIRED")
    _text(grant.program_policy_generation, "LIVE_GRANT_POLICY_GENERATION_REQUIRED")
    _text(grant.scope_rules_digest, "LIVE_GRANT_SCOPE_DIGEST_REQUIRED")
    _text(grant.scope_currentness_ref, "LIVE_GRANT_SCOPE_CURRENTNESS_REQUIRED")
    _text(grant.target_currentness_ref, "LIVE_GRANT_TARGET_CURRENTNESS_REQUIRED")
    _text(grant.revocation_currentness_ref, "LIVE_GRANT_REVOCATION_CURRENTNESS_REQUIRED")
    _text(grant.disclosure_policy_ref, "LIVE_GRANT_DISCLOSURE_POLICY_REQUIRED")
    if grant.effect_class != LIVE_EFFECT_CLASS:
        raise CashEffectBoundaryError("LIVE_GRANT_EFFECT_CLASS_UNSUPPORTED")
    origin = _text(grant.network_origin, "LIVE_GRANT_NETWORK_ORIGIN_REQUIRED")
    allowlist = _strings(grant.network_allowlist, "LIVE_GRANT_ALLOWLIST_INVALID")
    if origin not in allowlist:
        raise CashEffectBoundaryError("LIVE_GRANT_ORIGIN_NOT_ALLOWLISTED")
    _strings(grant.credential_aliases, "LIVE_GRANT_CREDENTIAL_ALIASES_INVALID")

    return LiveEffectAdmissionReceiptV1(
        mission_receipt_digest=receipt.receipt_digest,
        effect_grant_digest=grant.grant_digest,
        producer_ref=grant.producer_ref,
        producer_generation=grant.producer_generation,
        program_ref=receipt.program_ref,
        target_ref=receipt.target_ref,
        target_generation=receipt.target_generation,
        effect_class=grant.effect_class,
        network_origin=origin,
        live_effect_authorized=True,
        authority_scope="EXACT_NAMED_CASH_PROFILE_LIVE_TEST_ONLY",
    )


def export_sanitized_pattern(
    receipt: BugHoundCashMissionReceiptV1,
    sanitized: SanitizedPatternReceiptV1,
    *,
    destination_context: str,
    expected_sanitized_receipt_digest: str,
    expected_producer_ref: str,
    expected_producer_generation: str,
    expected_reviewer_ref: str,
) -> ReusablePatternExportV1:
    """Export only independently expected, authority-free abstract knowledge.

    A sanitized abstraction may cross from the cash-bounty profile to the
    AuraOS-hardening profile, but no cash mission or authority state accompanies
    it. K27/locality is not an authorization mechanism for this crossing.
    """
    _verify_mission_receipt(receipt)
    if sanitized.mission_receipt_digest != receipt.receipt_digest:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_MISSION_MISMATCH")
    destination = _text(destination_context, "REUSE_DESTINATION_CONTEXT_REQUIRED")
    if destination not in GENERIC_REUSE_CONTEXTS:
        raise CashEffectBoundaryError("REUSE_DESTINATION_CONTEXT_NOT_ADMITTED")
    if sanitized.authority:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_CANNOT_CARRY_AUTHORITY")

    expected_digest = _text(
        expected_sanitized_receipt_digest,
        "EXPECTED_SANITIZED_RECEIPT_DIGEST_REQUIRED",
    )
    expected_ref = _text(expected_producer_ref, "EXPECTED_SANITIZER_PRODUCER_REQUIRED")
    expected_generation = _text(
        expected_producer_generation,
        "EXPECTED_SANITIZER_PRODUCER_GENERATION_REQUIRED",
    )
    expected_reviewer = _text(expected_reviewer_ref, "EXPECTED_SANITIZER_REVIEWER_REQUIRED")
    if sanitized.receipt_digest != expected_digest:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_EXPECTATION_MISMATCH")
    if sanitized.producer_ref != expected_ref or sanitized.producer_generation != expected_generation:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_PRODUCER_MISMATCH")
    if sanitized.reviewer_ref != expected_reviewer:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_REVIEWER_MISMATCH")
    _text(sanitized.producer_currentness_ref, "SANITIZER_PRODUCER_CURRENTNESS_REQUIRED")

    _text(sanitized.disclosure_state_ref, "SANITIZED_DISCLOSURE_STATE_REQUIRED")
    _text(sanitized.reusable_memory_policy_ref, "SANITIZED_MEMORY_POLICY_REQUIRED")
    _text(sanitized.sanitizer_generation, "SANITIZER_GENERATION_REQUIRED")
    pattern_ref = _text(sanitized.retained_abstract_pattern_ref, "SANITIZED_PATTERN_REF_REQUIRED")

    sensitive = {
        "target_specific_material": sanitized.target_specific_material_present,
        "credentials_or_tokens": sanitized.credentials_or_tokens_present,
        "private_endpoint": sanitized.private_endpoint_present,
        "undisclosed_exploit_material": sanitized.undisclosed_exploit_material_present,
        "pii_or_third_party_data": sanitized.pii_or_third_party_data_present,
        "private_report_identifier": sanitized.private_report_identifier_present,
    }
    leaking = sorted(name for name, present in sensitive.items() if present)
    if leaking:
        raise CashEffectBoundaryError("SANITIZED_PATTERN_PRIVATE_STATE_REMAINS", ",".join(leaking))
    removed = _strings(sanitized.removed_classes, "SANITIZED_REMOVED_CLASSES_INVALID")
    if not _REQUIRED_SANITIZED_CLASSES <= removed:
        raise CashEffectBoundaryError("SANITIZED_REMOVAL_COVERAGE_INCOMPLETE")

    return ReusablePatternExportV1(
        source_cash_profile_id=CANONICAL_PROFILE_ID,
        source_mission_receipt_digest=receipt.receipt_digest,
        sanitized_pattern_receipt_digest=sanitized.receipt_digest,
        producer_ref=sanitized.producer_ref,
        producer_generation=sanitized.producer_generation,
        retained_abstract_pattern_ref=pattern_ref,
        destination_context=destination,
        cross_profile_reuse=destination == AURAOS_HARDENING_PROFILE_ID,
    )
