#!/usr/bin/env python3
"""Content-addressed, non-executable proposal capsules for AuraOS.

D0 / HS1 / NONPROMOTING.

This module does not decide whether evidence is favorable or whether a hard-gate
product is feasible. It consumes an exact typed eligibility receipt from those owners
and freezes the exact bounded proposal basis for later revalidation. A proposal is
never an execution lease or effect credential.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

BASIS_SCHEMA = "AURA-BOUNDED-PROPOSAL-BASIS-v1"
CAPSULE_SCHEMA = "AURA-BOUNDED-PROPOSAL-CAPSULE-v1"
ELIGIBILITY_DISPOSITION = "ELIGIBLE_BOUNDED_PROPOSAL"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_REQUIRED")


def _sha256(value: str, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64 or any(c not in HEX for c in value):
        raise ValueError(f"{name}_MUST_BE_SHA256_HEX")


@dataclass(frozen=True)
class EligibilityReceiptRef:
    disposition: str
    receipt_digest: str
    receipt_generation: str
    policy_generation_ref: str
    proposal_eligible: bool
    execution_authorized: bool
    provider_effect_authorized: bool

    def validate(self) -> None:
        if self.disposition != ELIGIBILITY_DISPOSITION:
            raise ValueError("ELIGIBILITY_RECEIPT_NOT_PROPOSAL_ELIGIBLE")
        _sha256(self.receipt_digest, "ELIGIBILITY_RECEIPT_DIGEST")
        _required(self.receipt_generation, "ELIGIBILITY_RECEIPT_GENERATION")
        _required(self.policy_generation_ref, "ELIGIBILITY_POLICY_GENERATION_REF")
        if self.proposal_eligible is not True:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_ASSERT_PROPOSAL_ELIGIBLE")
        if self.execution_authorized is not False:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_EXECUTION")
        if self.provider_effect_authorized is not False:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_PROVIDER_EFFECT")


@dataclass(frozen=True)
class ProposalBasis:
    schema_version: str
    domain_id: str
    action_kind: str
    action_parameters_digest: str
    scientific_scope_digest: str
    scientific_evidence_generation: str
    scientific_evidence_receipt_digest: str
    source_scope_digest: str
    source_admission_generation: str
    source_admission_receipt_digest: str
    request_id: str
    request_digest: str
    resource_envelope_digest: str
    eligibility: EligibilityReceiptRef
    currentness_roots: tuple[str, ...]
    invalidators: tuple[str, ...]
    authority_scope: str

    def validate(self) -> None:
        if self.schema_version != BASIS_SCHEMA:
            raise ValueError("PROPOSAL_BASIS_SCHEMA_MISMATCH")
        for value, name in (
            (self.domain_id, "DOMAIN_ID"),
            (self.action_kind, "ACTION_KIND"),
            (self.scientific_evidence_generation, "SCIENTIFIC_EVIDENCE_GENERATION"),
            (self.source_admission_generation, "SOURCE_ADMISSION_GENERATION"),
            (self.request_id, "REQUEST_ID"),
            (self.authority_scope, "AUTHORITY_SCOPE"),
        ):
            _required(value, name)
        for value, name in (
            (self.action_parameters_digest, "ACTION_PARAMETERS_DIGEST"),
            (self.scientific_scope_digest, "SCIENTIFIC_SCOPE_DIGEST"),
            (self.scientific_evidence_receipt_digest, "SCIENTIFIC_EVIDENCE_RECEIPT_DIGEST"),
            (self.source_scope_digest, "SOURCE_SCOPE_DIGEST"),
            (self.source_admission_receipt_digest, "SOURCE_ADMISSION_RECEIPT_DIGEST"),
            (self.request_digest, "REQUEST_DIGEST"),
            (self.resource_envelope_digest, "RESOURCE_ENVELOPE_DIGEST"),
        ):
            _sha256(value, name)
        self.eligibility.validate()
        if not self.currentness_roots or any(not isinstance(x, str) or not x.strip() for x in self.currentness_roots):
            raise ValueError("CURRENTNESS_ROOTS_REQUIRED")
        if len(set(self.currentness_roots)) != len(self.currentness_roots):
            raise ValueError("DUPLICATE_CURRENTNESS_ROOT")
        if not self.invalidators or any(not isinstance(x, str) or not x.strip() for x in self.invalidators):
            raise ValueError("INVALIDATORS_REQUIRED")
        if len(set(self.invalidators)) != len(self.invalidators):
            raise ValueError("DUPLICATE_INVALIDATOR")

    @property
    def canonical_identity_payload(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["currentness_roots"] = sorted(self.currentness_roots)
        payload["invalidators"] = sorted(self.invalidators)
        return payload


@dataclass(frozen=True)
class ProposalCapsule:
    schema_version: str
    proposal_id: str
    proposal_basis_digest: str
    basis: ProposalBasis
    revalidation_required_before_execution: bool = True
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    owner_host_execution_observed: bool = False
    native_private_transformer_kv_accessed: bool = False
    semantic_k27_authority: bool = False
    gate10_promoted: bool = False
    merge_deploy_spend_public_human_effect: bool = False

    def validate_claim_ceiling(self) -> None:
        if self.revalidation_required_before_execution is not True:
            raise ValueError("PROPOSAL_MUST_REQUIRE_REVALIDATION_BEFORE_EXECUTION")
        forbidden = (
            self.execution_authorized,
            self.provider_effect_authorized,
            self.owner_host_execution_observed,
            self.native_private_transformer_kv_accessed,
            self.semantic_k27_authority,
            self.gate10_promoted,
            self.merge_deploy_spend_public_human_effect,
        )
        if any(value is not False for value in forbidden):
            raise ValueError("PROPOSAL_CAPSULE_CANNOT_CARRY_EFFECT_AUTHORITY")


@dataclass(frozen=True)
class ProposalGeneration:
    capsule: ProposalCapsule
    producer_identity: str
    generation_receipt_digest: str


@dataclass(frozen=True)
class ProposalCurrentnessDecision:
    state: str
    reason_code: str
    proposal_id: str
    execution_authorized: bool = False
    provider_effect_authorized: bool = False


def create_bounded_proposal_capsule(*, basis: ProposalBasis, producer_identity: str) -> ProposalGeneration:
    """Freeze exact eligible basis; producer identity does not alter proposal_id."""
    _required(producer_identity, "PRODUCER_IDENTITY")
    payload = basis.canonical_identity_payload
    basis_digest = _sha({"domain": "AURA-BOUNDED-PROPOSAL-BASIS-v1", "basis": payload})
    proposal_id = _sha({"domain": "AURA-BOUNDED-PROPOSAL-ID-v1", "basis_digest": basis_digest})
    capsule = ProposalCapsule(
        schema_version=CAPSULE_SCHEMA,
        proposal_id=proposal_id,
        proposal_basis_digest=basis_digest,
        basis=basis,
    )
    capsule.validate_claim_ceiling()
    generation_receipt_digest = _sha(
        {
            "domain": "AURA-BOUNDED-PROPOSAL-GENERATION-v1",
            "proposal_id": proposal_id,
            "producer_identity": producer_identity,
        }
    )
    return ProposalGeneration(
        capsule=capsule,
        producer_identity=producer_identity,
        generation_receipt_digest=generation_receipt_digest,
    )


def revalidate_proposal_capsule(
    *, capsule: ProposalCapsule, current_basis: ProposalBasis
) -> ProposalCurrentnessDecision:
    """Revalidate exact operands without renewing or authorizing the proposal."""
    capsule.validate_claim_ceiling()
    current = create_bounded_proposal_capsule(basis=current_basis, producer_identity="REVALIDATOR")
    if current.capsule.proposal_id != capsule.proposal_id:
        return ProposalCurrentnessDecision(
            state="INVALIDATED",
            reason_code="PROPOSAL_OPERAND_OR_CURRENTNESS_DRIFT",
            proposal_id=capsule.proposal_id,
        )
    if current.capsule.proposal_basis_digest != capsule.proposal_basis_digest:
        return ProposalCurrentnessDecision(
            state="INVALIDATED",
            reason_code="PROPOSAL_BASIS_DIGEST_MISMATCH",
            proposal_id=capsule.proposal_id,
        )
    return ProposalCurrentnessDecision(
        state="CURRENT_NONEXECUTABLE",
        reason_code="EXACT_PROPOSAL_BASIS_STILL_CURRENT",
        proposal_id=capsule.proposal_id,
    )
