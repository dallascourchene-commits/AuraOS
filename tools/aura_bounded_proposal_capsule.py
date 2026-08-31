#!/usr/bin/env python3
"""Content-addressed, non-executable proposal capsules for AuraOS.

D0 / HS1 / NONPROMOTING.

A proposal basis is not allowed to self-certify either eligibility or currentness.
Creation requires an owner-controlled resolver to reproduce the exact eligibility
record. Revalidation resolves every consequence-changing operand from its current
owner state; unavailable, unknown, stale, or mismatched state invalidates rather than
renewing the proposal.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Protocol

BASIS_SCHEMA = "AURA-BOUNDED-PROPOSAL-BASIS-v1"
CAPSULE_SCHEMA = "AURA-BOUNDED-PROPOSAL-CAPSULE-v1"
ELIGIBILITY_DISPOSITION = "ELIGIBLE_BOUNDED_PROPOSAL"
HEX = frozenset("0123456789abcdef")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


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
    owner_ref: str
    transition_id: str
    domain_id: str
    gate_scope_digest: str
    source_currentness_root: str
    disposition: str
    receipt_digest: str
    receipt_generation: str
    policy_generation_ref: str
    proposal_eligible: bool
    execution_authorized: bool
    provider_effect_authorized: bool

    def validate(self) -> None:
        for value, name in (
            (self.owner_ref, "ELIGIBILITY_OWNER_REF"),
            (self.transition_id, "ELIGIBILITY_TRANSITION_ID"),
            (self.domain_id, "ELIGIBILITY_DOMAIN_ID"),
            (self.source_currentness_root, "ELIGIBILITY_SOURCE_CURRENTNESS_ROOT"),
            (self.receipt_generation, "ELIGIBILITY_RECEIPT_GENERATION"),
            (self.policy_generation_ref, "ELIGIBILITY_POLICY_GENERATION_REF"),
        ):
            _required(value, name)
        _sha256(self.gate_scope_digest, "ELIGIBILITY_GATE_SCOPE_DIGEST")
        _sha256(self.receipt_digest, "ELIGIBILITY_RECEIPT_DIGEST")
        if self.disposition != ELIGIBILITY_DISPOSITION:
            raise ValueError("ELIGIBILITY_RECEIPT_NOT_PROPOSAL_ELIGIBLE")
        if self.proposal_eligible is not True:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_ASSERT_PROPOSAL_ELIGIBLE")
        if self.execution_authorized is not False:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_EXECUTION")
        if self.provider_effect_authorized is not False:
            raise ValueError("ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_PROVIDER_EFFECT")


@dataclass(frozen=True)
class ScientificEvidenceState:
    scope_digest: str
    generation: str
    receipt_digest: str

    def validate(self) -> None:
        _sha256(self.scope_digest, "SCIENTIFIC_SCOPE_DIGEST")
        _required(self.generation, "SCIENTIFIC_EVIDENCE_GENERATION")
        _sha256(self.receipt_digest, "SCIENTIFIC_EVIDENCE_RECEIPT_DIGEST")


@dataclass(frozen=True)
class SourceAdmissionState:
    scope_digest: str
    generation: str
    receipt_digest: str

    def validate(self) -> None:
        _sha256(self.scope_digest, "SOURCE_SCOPE_DIGEST")
        _required(self.generation, "SOURCE_ADMISSION_GENERATION")
        _sha256(self.receipt_digest, "SOURCE_ADMISSION_RECEIPT_DIGEST")


@dataclass(frozen=True)
class RequestOwnerState:
    request_id: str
    request_digest: str
    action_parameters_digest: str
    resource_envelope_digest: str

    def validate(self) -> None:
        _required(self.request_id, "REQUEST_ID")
        _sha256(self.request_digest, "REQUEST_DIGEST")
        _sha256(self.action_parameters_digest, "ACTION_PARAMETERS_DIGEST")
        _sha256(self.resource_envelope_digest, "RESOURCE_ENVELOPE_DIGEST")


class ProposalOwnerResolver(Protocol):
    """Host-owned current-state resolvers. Callers do not supply raw current truth."""

    def resolve_eligibility(
        self, *, owner_ref: str, transition_id: str
    ) -> EligibilityReceiptRef | None: ...

    def resolve_scientific_evidence(
        self, *, scope_digest: str
    ) -> ScientificEvidenceState | None: ...

    def resolve_source_admission(
        self, *, scope_digest: str
    ) -> SourceAdmissionState | None: ...

    def resolve_request(self, *, request_id: str) -> RequestOwnerState | None: ...

    def currentness_root_is_current(self, *, root: str) -> bool | None: ...

    def invalidator_is_triggered(self, *, invalidator: str) -> bool | None: ...


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
        if self.eligibility.domain_id != self.domain_id:
            raise ValueError("ELIGIBILITY_DOMAIN_MISMATCH")
        if not self.currentness_roots or any(
            not isinstance(x, str) or not x.strip() for x in self.currentness_roots
        ):
            raise ValueError("CURRENTNESS_ROOTS_REQUIRED")
        if len(set(self.currentness_roots)) != len(self.currentness_roots):
            raise ValueError("DUPLICATE_CURRENTNESS_ROOT")
        if self.eligibility.source_currentness_root not in self.currentness_roots:
            raise ValueError("ELIGIBILITY_CURRENTNESS_ROOT_NOT_BOUND")
        if not self.invalidators or any(
            not isinstance(x, str) or not x.strip() for x in self.invalidators
        ):
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

    @property
    def basis_digest(self) -> str:
        return _sha(
            {"domain": "AURA-BOUNDED-PROPOSAL-BASIS-v1", "basis": self.canonical_identity_payload}
        )

    @property
    def proposal_id(self) -> str:
        return _sha({"domain": "AURA-BOUNDED-PROPOSAL-ID-v1", "basis_digest": self.basis_digest})


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

    def validate_integrity(self) -> None:
        if self.schema_version != CAPSULE_SCHEMA:
            raise ValueError("PROPOSAL_CAPSULE_SCHEMA_MISMATCH")
        _sha256(self.proposal_basis_digest, "PROPOSAL_BASIS_DIGEST")
        _sha256(self.proposal_id, "PROPOSAL_ID")
        if self.proposal_basis_digest != self.basis.basis_digest:
            raise ValueError("PROPOSAL_CAPSULE_BASIS_INTEGRITY_MISMATCH")
        if self.proposal_id != self.basis.proposal_id:
            raise ValueError("PROPOSAL_CAPSULE_ID_INTEGRITY_MISMATCH")
        self.validate_claim_ceiling()


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


def _resolve_eligibility_or_raise(
    *, basis: ProposalBasis, owner_resolver: ProposalOwnerResolver | None
) -> None:
    if owner_resolver is None:
        raise ValueError("ELIGIBILITY_OWNER_RESOLVER_REQUIRED")
    resolved = owner_resolver.resolve_eligibility(
        owner_ref=basis.eligibility.owner_ref,
        transition_id=basis.eligibility.transition_id,
    )
    if resolved is None:
        raise ValueError("ELIGIBILITY_OWNER_RECEIPT_UNRESOLVED")
    resolved.validate()
    if resolved != basis.eligibility:
        raise ValueError("ELIGIBILITY_OWNER_RECEIPT_MISMATCH")


def create_bounded_proposal_capsule(
    *,
    basis: ProposalBasis,
    producer_identity: str,
    owner_resolver: ProposalOwnerResolver | None,
) -> ProposalGeneration:
    """Freeze only an owner-resolved eligible basis; producer identity does not alter ID."""
    _required(producer_identity, "PRODUCER_IDENTITY")
    basis.validate()
    _resolve_eligibility_or_raise(basis=basis, owner_resolver=owner_resolver)
    capsule = ProposalCapsule(
        schema_version=CAPSULE_SCHEMA,
        proposal_id=basis.proposal_id,
        proposal_basis_digest=basis.basis_digest,
        basis=basis,
    )
    capsule.validate_integrity()
    generation_receipt_digest = _sha(
        {
            "domain": "AURA-BOUNDED-PROPOSAL-GENERATION-v1",
            "proposal_id": capsule.proposal_id,
            "producer_identity": producer_identity,
            "eligibility_owner_ref": basis.eligibility.owner_ref,
            "eligibility_receipt_digest": basis.eligibility.receipt_digest,
        }
    )
    return ProposalGeneration(
        capsule=capsule,
        producer_identity=producer_identity,
        generation_receipt_digest=generation_receipt_digest,
    )


def _invalidated(capsule: ProposalCapsule, reason_code: str) -> ProposalCurrentnessDecision:
    return ProposalCurrentnessDecision(
        state="INVALIDATED",
        reason_code=reason_code,
        proposal_id=capsule.proposal_id,
    )


def revalidate_proposal_capsule(
    *, capsule: ProposalCapsule, owner_resolver: ProposalOwnerResolver | None
) -> ProposalCurrentnessDecision:
    """Resolve current owner state; caller replay of the stored basis cannot assert currentness."""
    capsule.validate_integrity()
    if owner_resolver is None:
        return _invalidated(capsule, "OWNER_RESOLVER_UNAVAILABLE")
    b = capsule.basis
    try:
        eligibility = owner_resolver.resolve_eligibility(
            owner_ref=b.eligibility.owner_ref,
            transition_id=b.eligibility.transition_id,
        )
        science = owner_resolver.resolve_scientific_evidence(
            scope_digest=b.scientific_scope_digest
        )
        source = owner_resolver.resolve_source_admission(scope_digest=b.source_scope_digest)
        request = owner_resolver.resolve_request(request_id=b.request_id)
    except Exception:
        return _invalidated(capsule, "OWNER_RESOLVER_ERROR")

    if eligibility is None or science is None or source is None or request is None:
        return _invalidated(capsule, "OWNER_STATE_UNAVAILABLE_OR_UNKNOWN")
    try:
        eligibility.validate()
        science.validate()
        source.validate()
        request.validate()
    except ValueError:
        return _invalidated(capsule, "OWNER_STATE_INVALID")

    if eligibility != b.eligibility:
        return _invalidated(capsule, "ELIGIBILITY_OWNER_STATE_DRIFT")
    expected_science = ScientificEvidenceState(
        scope_digest=b.scientific_scope_digest,
        generation=b.scientific_evidence_generation,
        receipt_digest=b.scientific_evidence_receipt_digest,
    )
    if science != expected_science:
        return _invalidated(capsule, "SCIENTIFIC_EVIDENCE_OWNER_STATE_DRIFT")
    expected_source = SourceAdmissionState(
        scope_digest=b.source_scope_digest,
        generation=b.source_admission_generation,
        receipt_digest=b.source_admission_receipt_digest,
    )
    if source != expected_source:
        return _invalidated(capsule, "SOURCE_ADMISSION_OWNER_STATE_DRIFT")
    expected_request = RequestOwnerState(
        request_id=b.request_id,
        request_digest=b.request_digest,
        action_parameters_digest=b.action_parameters_digest,
        resource_envelope_digest=b.resource_envelope_digest,
    )
    if request != expected_request:
        return _invalidated(capsule, "REQUEST_OR_RESOURCE_OWNER_STATE_DRIFT")

    for root in b.currentness_roots:
        try:
            state = owner_resolver.currentness_root_is_current(root=root)
        except Exception:
            return _invalidated(capsule, "CURRENTNESS_RESOLVER_ERROR")
        if state is not True:
            return _invalidated(capsule, "CURRENTNESS_ROOT_NOT_ATTESTED_CURRENT")

    for invalidator in b.invalidators:
        try:
            triggered = owner_resolver.invalidator_is_triggered(invalidator=invalidator)
        except Exception:
            return _invalidated(capsule, "INVALIDATOR_RESOLVER_ERROR")
        if triggered is not False:
            return _invalidated(capsule, "INVALIDATOR_UNKNOWN_OR_TRIGGERED")

    return ProposalCurrentnessDecision(
        state="CURRENT_NONEXECUTABLE",
        reason_code="ALL_OWNER_RESOLVED_OPERANDS_STILL_CURRENT",
        proposal_id=capsule.proposal_id,
    )
