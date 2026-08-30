"""Bind BugHound offline reproduction evidence to exact R0 runtime provenance.

This module closes only an execution-substrate lineage gap.  It proves that a
specific independent-reproduction receipt names the same target generation as a
bounded BugHound R0 capsule, that the receipt's environment digest names that
exact materialization, that the capsule evidence bus recorded the exact witness
digest, and that teardown observed the source intact.

It does NOT execute a reproduction command, authenticate the reproducer, prove a
vulnerability-specific reproduction, establish OS sandboxing, or grant any live
target / credential / submission / payment authority.  PR425's independently
owned registry remains the stronger producer-authentication boundary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

from tools.bughound.arena_runtime import (
    BugHoundArenaEvidenceEventV1,
    BugHoundArenaRuntimeR0ReceiptV1,
    BugHoundArenaTeardownReceiptV1,
    NETWORK_OFF,
)
from tools.bughound.bounty_candidate_admission import IndependentBountyReproductionReceiptV1
from tools.bughound.target_profile import CASH_BOUNTY_PROFILE_ID

SCHEMA = "BugHoundR0OfflineReproductionProvenanceV1"
WITNESS_EVENT_TYPE = "INDEPENDENT_REPRODUCTION_WITNESS"


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


def _text(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")
    return value.strip()


def reproduction_witness_ref(candidate_id: str) -> str:
    return f"bughound://candidate/{_text('CANDIDATE_ID', candidate_id)}/independent-reproduction-witness"


def r0_reproduction_environment_digest(materialization: BugHoundArenaRuntimeR0ReceiptV1) -> str:
    """Return the exact R0 environment identity a reproduction receipt must bind."""
    if not isinstance(materialization, BugHoundArenaRuntimeR0ReceiptV1):
        raise ValueError("BUGHOUND_R0_MATERIALIZATION_RECEIPT_REQUIRED")
    return _digest(
        "AURA_BUGHOUND_R0_REPRO_ENVIRONMENT_V1",
        {
            "materialization_receipt_digest": materialization.receipt_digest,
            "capsule_id": materialization.capsule_id,
            "profile_receipt_digest": materialization.profile_receipt_digest,
            "profile_id": materialization.profile_id,
            "target_ref": materialization.target_ref,
            "target_generation": materialization.target_generation,
            "source_digest": materialization.source_digest,
            "network_policy": materialization.network_policy,
            "logical_network_policy_off": materialization.logical_network_policy_off,
            "os_network_isolation_proven": materialization.os_network_isolation_proven,
            "credential_count": materialization.credential_count,
            "source_write_bits_present": materialization.source_write_bits_present,
        },
    )


def _single_event_log_digest(event: BugHoundArenaEvidenceEventV1) -> str:
    return _digest("AURA_BUGHOUND_R0_EVIDENCE_LOG_V1", [event.event_digest])


@dataclass(frozen=True)
class BugHoundR0OfflineReproductionProvenanceV1:
    candidate_id: str
    target_ref: str
    target_generation: str
    reproducer_ref: str
    reproducer_generation: str
    reproduction_result: str
    reproduction_receipt_digest: str
    witness_digest: str
    environment_digest: str
    scope_rules_digest: str
    source_currentness_ref: str
    r0_materialization_receipt_digest: str
    r0_teardown_receipt_digest: str
    r0_capsule_id: str
    r0_source_digest: str
    r0_evidence_event_digest: str
    r0_evidence_log_digest: str
    witness_artifact_bound: bool = True
    runtime_lineage_bound: bool = True
    source_lineage_bound: bool = True
    teardown_bound: bool = True
    command_execution_proven: bool = False
    reproducer_identity_proven: bool = False
    independent_reproduction_registry_proven: bool = False
    vulnerability_specific_reproduction_proven: bool = False
    os_network_isolation_proven: bool = False
    live_target_testing_authorized: bool = False
    credential_use_authorized: bool = False
    submission_authorized: bool = False
    claim_or_payment_authorized: bool = False
    external_effect: bool = False
    schema: str = SCHEMA

    @property
    def receipt_digest(self) -> str:
        return _digest("AURA_BUGHOUND_R0_OFFLINE_REPRO_PROVENANCE_V1", asdict(self))

    @property
    def registry_binding_coordinates(self) -> dict[str, str]:
        """Coordinates a future independent PR425 registry must bind; not a registry record."""
        return {
            "candidate_id": self.candidate_id,
            "target_ref": self.target_ref,
            "target_generation": self.target_generation,
            "reproduction_receipt_digest": self.reproduction_receipt_digest,
            "reproducer_ref": self.reproducer_ref,
            "reproducer_generation": self.reproducer_generation,
            "witness_digest": self.witness_digest,
            "environment_digest": self.environment_digest,
            "scope_rules_digest": self.scope_rules_digest,
            "source_currentness_ref": self.source_currentness_ref,
        }


def _require_r0_effect_ceiling(materialization: BugHoundArenaRuntimeR0ReceiptV1) -> None:
    if materialization.profile_id != CASH_BOUNTY_PROFILE_ID:
        raise ValueError("R0_REPRODUCTION_CASH_PROFILE_REQUIRED")
    if materialization.network_policy != NETWORK_OFF or materialization.logical_network_policy_off is not True:
        raise ValueError("R0_REPRODUCTION_NETWORK_OFF_REQUIRED")
    if materialization.os_network_isolation_proven is not False:
        raise ValueError("R0_OS_NETWORK_ISOLATION_CANNOT_BE_CLAIMED")
    if materialization.credential_count != 0:
        raise ValueError("R0_REPRODUCTION_CREDENTIALS_FORBIDDEN")
    if materialization.source_write_bits_present is not False:
        raise ValueError("R0_REPRODUCTION_SOURCE_WRITE_BITS_FORBIDDEN")
    for field in (
        "external_effect",
        "live_target_testing_authorized",
        "submission_authorized",
        "payout_authority",
    ):
        if getattr(materialization, field) is not False:
            raise ValueError("R0_REPRODUCTION_MATERIALIZATION_AUTHORITY_WIDENED")


def bind_r0_offline_reproduction_provenance(
    *,
    materialization: BugHoundArenaRuntimeR0ReceiptV1,
    reproduction: IndependentBountyReproductionReceiptV1,
    witness_event: BugHoundArenaEvidenceEventV1,
    teardown: BugHoundArenaTeardownReceiptV1,
) -> BugHoundR0OfflineReproductionProvenanceV1:
    """Bind exact R0 lineage without promoting it to independent producer trust."""
    if not isinstance(materialization, BugHoundArenaRuntimeR0ReceiptV1):
        raise ValueError("BUGHOUND_R0_MATERIALIZATION_RECEIPT_REQUIRED")
    if not isinstance(reproduction, IndependentBountyReproductionReceiptV1):
        raise ValueError("BUGHOUND_INDEPENDENT_REPRODUCTION_RECEIPT_REQUIRED")
    if not isinstance(witness_event, BugHoundArenaEvidenceEventV1):
        raise ValueError("BUGHOUND_R0_REPRODUCTION_WITNESS_EVENT_REQUIRED")
    if not isinstance(teardown, BugHoundArenaTeardownReceiptV1):
        raise ValueError("BUGHOUND_R0_TEARDOWN_RECEIPT_REQUIRED")

    _require_r0_effect_ceiling(materialization)
    if reproduction.external_effect is not False:
        raise ValueError("R0_REPRODUCTION_EXTERNAL_EFFECT_FORBIDDEN")
    for name in (
        "candidate_id",
        "target_ref",
        "target_generation",
        "reproducer_ref",
        "reproducer_generation",
        "result",
        "witness_digest",
        "environment_digest",
        "scope_rules_digest",
        "source_currentness_ref",
    ):
        _text(f"REPRODUCTION_{name.upper()}", getattr(reproduction, name))

    if reproduction.target_ref != materialization.target_ref:
        raise ValueError("R0_REPRODUCTION_TARGET_REF_MISMATCH")
    if reproduction.target_generation != materialization.target_generation:
        raise ValueError("R0_REPRODUCTION_TARGET_GENERATION_MISMATCH")
    expected_environment = r0_reproduction_environment_digest(materialization)
    if reproduction.environment_digest != expected_environment:
        raise ValueError("R0_REPRODUCTION_ENVIRONMENT_DIGEST_MISMATCH")

    if witness_event.sequence != 1:
        raise ValueError("R0_REPRODUCTION_WITNESS_MUST_BE_FIRST_AND_ONLY_EVENT")
    if witness_event.event_type != WITNESS_EVENT_TYPE:
        raise ValueError("R0_REPRODUCTION_WITNESS_EVENT_TYPE_MISMATCH")
    if witness_event.artifact_ref != reproduction_witness_ref(reproduction.candidate_id):
        raise ValueError("R0_REPRODUCTION_WITNESS_REF_MISMATCH")
    if witness_event.artifact_digest != reproduction.witness_digest:
        raise ValueError("R0_REPRODUCTION_WITNESS_DIGEST_MISMATCH")

    if teardown.capsule_id != materialization.capsule_id:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_CAPSULE_MISMATCH")
    if teardown.source_digest_expected != materialization.source_digest:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_SOURCE_EXPECTED_MISMATCH")
    if teardown.source_digest_observed != materialization.source_digest:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_SOURCE_OBSERVED_MISMATCH")
    if teardown.source_intact_before_teardown is not True:
        raise ValueError("R0_REPRODUCTION_SOURCE_INTEGRITY_REQUIRED")
    if teardown.root_removed is not True:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_REQUIRED")
    if teardown.network_policy != NETWORK_OFF or teardown.credential_count != 0:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_EFFECT_CEILING_MISMATCH")
    if teardown.os_network_isolation_proven is not False or teardown.external_effect is not False:
        raise ValueError("R0_REPRODUCTION_TEARDOWN_CLAIM_WIDENED")
    if teardown.evidence_event_count != 1:
        raise ValueError("R0_REPRODUCTION_SINGLE_BOUND_WITNESS_REQUIRED")
    expected_log_digest = _single_event_log_digest(witness_event)
    if teardown.evidence_digest != expected_log_digest:
        raise ValueError("R0_REPRODUCTION_EVIDENCE_LOG_MISMATCH")

    return BugHoundR0OfflineReproductionProvenanceV1(
        candidate_id=reproduction.candidate_id,
        target_ref=reproduction.target_ref,
        target_generation=reproduction.target_generation,
        reproducer_ref=reproduction.reproducer_ref,
        reproducer_generation=reproduction.reproducer_generation,
        reproduction_result=reproduction.result,
        reproduction_receipt_digest=reproduction.receipt_digest,
        witness_digest=reproduction.witness_digest,
        environment_digest=reproduction.environment_digest,
        scope_rules_digest=reproduction.scope_rules_digest,
        source_currentness_ref=reproduction.source_currentness_ref,
        r0_materialization_receipt_digest=materialization.receipt_digest,
        r0_teardown_receipt_digest=teardown.receipt_digest,
        r0_capsule_id=materialization.capsule_id,
        r0_source_digest=materialization.source_digest,
        r0_evidence_event_digest=witness_event.event_digest,
        r0_evidence_log_digest=teardown.evidence_digest,
    )
