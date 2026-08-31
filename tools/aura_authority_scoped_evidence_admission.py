#!/usr/bin/env python3
"""Authority-scoped, representation-aware evidence admission for AuraOS.

D0 / HS1 / NONPROMOTING.

This membrane does not run a benchmark, model, quantizer, source fetch, or provider.
It binds already-produced evidence to the exact trusted authority, source,
representation, accounting domain, bounded scope, and admission-policy generation
under which that evidence may carry bounded score/proposal mass.

Core laws:
    ReceiptFieldsPresent != HostAuthority
    SameOutcome != SameRepresentation
    SameNominalRate != SameAccountingDomain
    EquivalentRationalRate == OneCanonicalRateIdentity
    AdmissionPolicyGenerationIsPartOfEvidenceIdentity
    PositiveAndNegativeScoreMassShareTheSameHardGates
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from math import gcd
from typing import Any

AUTHORITY_SCHEMA = "AURA-EVIDENCE-AUTHORITY-BINDING-v1"
REPRESENTATION_SCHEMA = "AURA-REPRESENTATION-IDENTITY-v1"
CANDIDATE_SCHEMA = "AURA-EVIDENCE-ADMISSION-CANDIDATE-v1"
POLICY_SCHEMA = "AURA-EVIDENCE-ADMISSION-POLICY-v1"
DECISION_SCHEMA = "AURA-EVIDENCE-ADMISSION-DECISION-v1"
OUTCOMES = frozenset({"SUPPORTS", "NEUTRAL", "OPPOSES"})
AUTHORITY_STATES = frozenset({"VERIFIED_BOUNDED", "HOLD", "REVIEW", "INVALID", "UNKNOWN"})
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


def _reduced_positive_rational(numerator: int, denominator: int) -> tuple[int, int]:
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError("REPRESENTATION_RATE_MUST_BE_INTEGER_RATIONAL")
    if numerator <= 0 or denominator <= 0:
        raise ValueError("REPRESENTATION_RATE_MUST_BE_POSITIVE")
    divisor = gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor


@dataclass(frozen=True)
class AuthorityBindingRef:
    schema_version: str
    owner_ref: str
    policy_generation_ref: str
    binding_receipt_digest: str
    authority_state: str
    authority_scope: str
    execution_required: bool
    expected_route_fingerprint: str
    expected_observer_identity: str
    expected_source_verifier_identity: str

    def validate(self) -> None:
        if self.schema_version != AUTHORITY_SCHEMA:
            raise ValueError("AUTHORITY_BINDING_SCHEMA_MISMATCH")
        for value, name in (
            (self.owner_ref, "AUTHORITY_OWNER_REF"),
            (self.policy_generation_ref, "AUTHORITY_POLICY_GENERATION_REF"),
            (self.authority_scope, "AUTHORITY_SCOPE"),
            (self.expected_source_verifier_identity, "EXPECTED_SOURCE_VERIFIER_IDENTITY"),
        ):
            _required(value, name)
        _sha256(self.binding_receipt_digest, "AUTHORITY_BINDING_RECEIPT_DIGEST")
        if self.authority_state not in AUTHORITY_STATES:
            raise ValueError("UNKNOWN_AUTHORITY_STATE")
        if type(self.execution_required) is not bool:
            raise ValueError("EXECUTION_REQUIRED_MUST_BE_BOOL")
        if self.execution_required:
            _sha256(self.expected_route_fingerprint, "EXPECTED_ROUTE_FINGERPRINT")
            _required(self.expected_observer_identity, "EXPECTED_OBSERVER_IDENTITY")
        else:
            if self.expected_route_fingerprint != "NONE":
                raise ValueError("NONEXECUTION_AUTHORITY_ROUTE_MUST_BE_NONE")
            if self.expected_observer_identity != "NONE":
                raise ValueError("NONEXECUTION_AUTHORITY_OBSERVER_MUST_BE_NONE")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return _sha({"domain": AUTHORITY_SCHEMA, **asdict(self)})


@dataclass(frozen=True)
class RepresentationIdentity:
    schema_version: str
    representation_family: str
    representation_digest: str
    accounting_domain: str
    accounting_contract_digest: str
    rate_numerator: int
    rate_denominator: int
    bounded_scope_digest: str

    def validate(self) -> None:
        if self.schema_version != REPRESENTATION_SCHEMA:
            raise ValueError("REPRESENTATION_SCHEMA_MISMATCH")
        _required(self.representation_family, "REPRESENTATION_FAMILY")
        _sha256(self.representation_digest, "REPRESENTATION_DIGEST")
        _required(self.accounting_domain, "ACCOUNTING_DOMAIN")
        _sha256(self.accounting_contract_digest, "ACCOUNTING_CONTRACT_DIGEST")
        _sha256(self.bounded_scope_digest, "REPRESENTATION_BOUNDED_SCOPE_DIGEST")
        _reduced_positive_rational(self.rate_numerator, self.rate_denominator)

    @property
    def reduced_rate(self) -> tuple[int, int]:
        return _reduced_positive_rational(self.rate_numerator, self.rate_denominator)

    @property
    def fingerprint(self) -> str:
        self.validate()
        rate_numerator, rate_denominator = self.reduced_rate
        return _sha(
            {
                "domain": REPRESENTATION_SCHEMA,
                "representation_family": self.representation_family,
                "representation_digest": self.representation_digest,
                "accounting_domain": self.accounting_domain,
                "accounting_contract_digest": self.accounting_contract_digest,
                "rate_numerator": rate_numerator,
                "rate_denominator": rate_denominator,
                "bounded_scope_digest": self.bounded_scope_digest,
            }
        )


@dataclass(frozen=True)
class EvidenceAdmissionCandidate:
    schema_version: str
    evidence_id: str
    evidence_generation: str
    evidence_receipt_digest: str
    evidence_scope_digest: str
    source_generation: str
    source_receipt_digest: str
    source_scope_digest: str
    route_fingerprint: str
    observer_identity: str
    source_verifier_identity: str
    outcome: str
    representation: RepresentationIdentity
    currentness_roots: tuple[str, ...]

    def validate(self) -> None:
        if self.schema_version != CANDIDATE_SCHEMA:
            raise ValueError("EVIDENCE_CANDIDATE_SCHEMA_MISMATCH")
        for value, name in (
            (self.evidence_id, "EVIDENCE_ID"),
            (self.evidence_generation, "EVIDENCE_GENERATION"),
            (self.source_generation, "SOURCE_GENERATION"),
            (self.source_verifier_identity, "SOURCE_VERIFIER_IDENTITY"),
        ):
            _required(value, name)
        for value, name in (
            (self.evidence_receipt_digest, "EVIDENCE_RECEIPT_DIGEST"),
            (self.evidence_scope_digest, "EVIDENCE_SCOPE_DIGEST"),
            (self.source_receipt_digest, "SOURCE_RECEIPT_DIGEST"),
            (self.source_scope_digest, "SOURCE_SCOPE_DIGEST"),
        ):
            _sha256(value, name)
        if self.route_fingerprint != "NONE":
            _sha256(self.route_fingerprint, "ROUTE_FINGERPRINT")
        _required(self.observer_identity, "OBSERVER_IDENTITY")
        if self.outcome not in OUTCOMES:
            raise ValueError("UNKNOWN_EVIDENCE_OUTCOME")
        self.representation.validate()
        if not self.currentness_roots or any(
            not isinstance(x, str) or not x.strip() for x in self.currentness_roots
        ):
            raise ValueError("EVIDENCE_CURRENTNESS_ROOTS_REQUIRED")
        if len(set(self.currentness_roots)) != len(self.currentness_roots):
            raise ValueError("DUPLICATE_EVIDENCE_CURRENTNESS_ROOT")


@dataclass(frozen=True)
class EvidenceAdmissionPolicy:
    schema_version: str
    policy_owner_ref: str
    policy_generation_ref: str
    expected_authority_owner_ref: str
    expected_authority_policy_generation_ref: str
    expected_authority_scope: str
    require_execution_authority: bool
    allowed_accounting_domains: tuple[str, ...]
    allowed_representation_families: tuple[str, ...]

    def validate(self) -> None:
        if self.schema_version != POLICY_SCHEMA:
            raise ValueError("EVIDENCE_ADMISSION_POLICY_SCHEMA_MISMATCH")
        for value, name in (
            (self.policy_owner_ref, "ADMISSION_POLICY_OWNER_REF"),
            (self.policy_generation_ref, "ADMISSION_POLICY_GENERATION_REF"),
            (self.expected_authority_owner_ref, "EXPECTED_AUTHORITY_OWNER_REF"),
            (self.expected_authority_policy_generation_ref, "EXPECTED_AUTHORITY_POLICY_GENERATION_REF"),
            (self.expected_authority_scope, "EXPECTED_AUTHORITY_SCOPE"),
        ):
            _required(value, name)
        if type(self.require_execution_authority) is not bool:
            raise ValueError("REQUIRE_EXECUTION_AUTHORITY_MUST_BE_BOOL")
        if not self.allowed_accounting_domains or any(
            not isinstance(x, str) or not x.strip() for x in self.allowed_accounting_domains
        ):
            raise ValueError("ALLOWED_ACCOUNTING_DOMAINS_REQUIRED")
        if len(set(self.allowed_accounting_domains)) != len(self.allowed_accounting_domains):
            raise ValueError("DUPLICATE_ALLOWED_ACCOUNTING_DOMAIN")
        if not self.allowed_representation_families or any(
            not isinstance(x, str) or not x.strip() for x in self.allowed_representation_families
        ):
            raise ValueError("ALLOWED_REPRESENTATION_FAMILIES_REQUIRED")
        if len(set(self.allowed_representation_families)) != len(self.allowed_representation_families):
            raise ValueError("DUPLICATE_ALLOWED_REPRESENTATION_FAMILY")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return _sha(
            {
                "domain": POLICY_SCHEMA,
                "policy_owner_ref": self.policy_owner_ref,
                "policy_generation_ref": self.policy_generation_ref,
                "expected_authority_owner_ref": self.expected_authority_owner_ref,
                "expected_authority_policy_generation_ref": self.expected_authority_policy_generation_ref,
                "expected_authority_scope": self.expected_authority_scope,
                "require_execution_authority": self.require_execution_authority,
                "allowed_accounting_domains": sorted(self.allowed_accounting_domains),
                "allowed_representation_families": sorted(self.allowed_representation_families),
            }
        )


@dataclass(frozen=True)
class EvidenceAdmissionDecision:
    schema_version: str
    disposition: str
    reason_code: str
    authority_fingerprint: str | None
    admission_policy_fingerprint: str | None
    representation_fingerprint: str | None
    evidence_admission_fingerprint: str | None
    score_mass_eligible: bool
    proposal_mass_eligible: bool
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    gate10_promoted: bool = False


def _decision(
    *,
    disposition: str,
    reason_code: str,
    authority_fingerprint: str | None = None,
    admission_policy_fingerprint: str | None = None,
    representation_fingerprint: str | None = None,
    evidence_admission_fingerprint: str | None = None,
    eligible: bool = False,
) -> EvidenceAdmissionDecision:
    return EvidenceAdmissionDecision(
        schema_version=DECISION_SCHEMA,
        disposition=disposition,
        reason_code=reason_code,
        authority_fingerprint=authority_fingerprint,
        admission_policy_fingerprint=admission_policy_fingerprint,
        representation_fingerprint=representation_fingerprint,
        evidence_admission_fingerprint=evidence_admission_fingerprint,
        score_mass_eligible=eligible,
        proposal_mass_eligible=eligible,
    )


def admit_evidence(
    *, candidate: EvidenceAdmissionCandidate, authority: AuthorityBindingRef, policy: EvidenceAdmissionPolicy
) -> EvidenceAdmissionDecision:
    """Bind authority/source/representation/policy before evidence mass exists."""
    candidate.validate()
    authority.validate()
    policy.validate()
    af = authority.fingerprint
    pf = policy.fingerprint
    rf = candidate.representation.fingerprint
    base = {
        "authority_fingerprint": af,
        "admission_policy_fingerprint": pf,
        "representation_fingerprint": rf,
    }

    if authority.authority_state != "VERIFIED_BOUNDED":
        return _decision(disposition="HOLD", reason_code="AUTHORITY_BINDING_NOT_VERIFIED", **base)
    if authority.owner_ref != policy.expected_authority_owner_ref:
        return _decision(disposition="REVIEW", reason_code="AUTHORITY_OWNER_MISMATCH", **base)
    if authority.policy_generation_ref != policy.expected_authority_policy_generation_ref:
        return _decision(disposition="HOLD", reason_code="AUTHORITY_POLICY_GENERATION_MISMATCH", **base)
    if authority.authority_scope != policy.expected_authority_scope:
        return _decision(disposition="HOLD", reason_code="AUTHORITY_SCOPE_MISMATCH", **base)
    if authority.execution_required != policy.require_execution_authority:
        return _decision(disposition="HOLD", reason_code="EXECUTION_AUTHORITY_REQUIREMENT_MISMATCH", **base)
    if candidate.source_verifier_identity != authority.expected_source_verifier_identity:
        return _decision(disposition="HOLD", reason_code="SOURCE_VERIFIER_IDENTITY_MISMATCH", **base)
    if authority.execution_required:
        if candidate.route_fingerprint != authority.expected_route_fingerprint:
            return _decision(disposition="HOLD", reason_code="HOST_ROUTE_FINGERPRINT_MISMATCH", **base)
        if candidate.observer_identity != authority.expected_observer_identity:
            return _decision(disposition="HOLD", reason_code="HOST_OBSERVER_IDENTITY_MISMATCH", **base)
    elif candidate.route_fingerprint != "NONE" or candidate.observer_identity != "NONE":
        return _decision(
            disposition="REVIEW",
            reason_code="NONEXECUTION_EVIDENCE_CANNOT_CLAIM_HOST_ROUTE_OR_OBSERVER",
            **base,
        )

    if candidate.representation.bounded_scope_digest != candidate.evidence_scope_digest:
        return _decision(disposition="REVIEW", reason_code="REPRESENTATION_SCOPE_DOES_NOT_MATCH_EVIDENCE_SCOPE", **base)
    if candidate.representation.accounting_domain not in policy.allowed_accounting_domains:
        return _decision(disposition="REVIEW", reason_code="ACCOUNTING_DOMAIN_NOT_ADMITTED", **base)
    if candidate.representation.representation_family not in policy.allowed_representation_families:
        return _decision(disposition="REVIEW", reason_code="REPRESENTATION_FAMILY_NOT_ADMITTED", **base)

    admission = _sha(
        {
            "domain": "AURA-EVIDENCE-ADMISSION-v1",
            "evidence_id": candidate.evidence_id,
            "evidence_generation": candidate.evidence_generation,
            "evidence_receipt_digest": candidate.evidence_receipt_digest,
            "evidence_scope_digest": candidate.evidence_scope_digest,
            "source_generation": candidate.source_generation,
            "source_receipt_digest": candidate.source_receipt_digest,
            "source_scope_digest": candidate.source_scope_digest,
            "outcome": candidate.outcome,
            "authority_fingerprint": af,
            "admission_policy_fingerprint": pf,
            "representation_fingerprint": rf,
            "currentness_roots": sorted(candidate.currentness_roots),
        }
    )
    return _decision(
        disposition="VERIFIED_BOUNDED",
        reason_code="AUTHORITY_SOURCE_REPRESENTATION_ACCOUNTING_AND_POLICY_BOUND",
        evidence_admission_fingerprint=admission,
        eligible=True,
        **base,
    )
