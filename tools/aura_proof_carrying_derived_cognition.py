#!/usr/bin/env python3
"""Proof-carrying derived cognition for AuraOS.

D0 / HS1 / NONPROMOTING.

This module is intentionally orthogonal to the closed-world result lifecycle reducer.
The lifecycle reducer decides whether a typed result may become terminal. This module
answers a narrower question: when a result is *derived* from admitted parents, what
exact derivation and evidence-production lineage must be bound before semantic reuse
or consequence collapse can call that derived cognition verified?

Core separation:
    ValidParentState != ReproducibleDerivation
    SameOutput != SameDerivation
    ContentReuse != EvidenceIndependence
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any

DERIVATION_SCHEMA = "AURA-DERIVATION-v1"
EVIDENCE_IDENTITY_SCHEMA = "AURA-EVIDENCE-IDENTITY-v1"
DERIVED_POLICY_SCHEMA = "AURA-DERIVED-POLICY-v1"
DERIVED_CANDIDATE_SCHEMA = "AURA-DERIVED-CANDIDATE-v1"
DERIVED_DECISION_SCHEMA = "AURA-DERIVED-DECISION-v1"

HEX = frozenset("0123456789abcdef")
DIGEST_OR_NONE_FIELDS = (
    "transformation_code_digest",
    "transformation_config_digest",
    "inclusion_predicate_digest",
    "exclusion_predicate_digest",
    "ordering_grouping_digest",
    "aggregation_digest",
    "rounding_threshold_digest",
    "label_reclassification_digest",
    "source_set_selection_digest",
)
INDEPENDENCE_CLASSES = frozenset(
    {
        "CLEAN_INDEPENDENT",
        "SEARCH_MEDIATED",
        "USER_CONDITIONED",
        "MEMORY_CONDITIONED",
        "MIXED_CONDITIONED",
        "UNKNOWN",
    }
)
VERIFICATION_STATES = frozenset({"VERIFIED_BOUNDED", "HOLD", "REVIEW", "INVALID", "UNKNOWN"})


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


def _digest_or_none(value: str, name: str) -> None:
    if value == "NONE":
        return
    _sha256(value, name)


@dataclass(frozen=True)
class ParentValidationRef:
    parent_ref: str
    parent_content_digest: str
    validation_fingerprint: str
    validator_generation_ref: str
    valid_current: bool

    def validate(self) -> None:
        _required(self.parent_ref, "PARENT_REF")
        _sha256(self.parent_content_digest, "PARENT_CONTENT_DIGEST")
        _sha256(self.validation_fingerprint, "VALIDATION_FINGERPRINT")
        _required(self.validator_generation_ref, "VALIDATOR_GENERATION_REF")
        if type(self.valid_current) is not bool:
            raise ValueError("PARENT_VALID_CURRENT_MUST_BE_BOOL")


@dataclass(frozen=True)
class EvidenceIdentity:
    schema_version: str
    evidence_id: str
    producer_identity: str
    generation_ref: str
    content_digest: str
    source_refs: tuple[str, ...]
    independence_class: str
    search_used: bool
    memory_used: bool
    user_conditioned: bool
    condition_ref: str

    def validate(self) -> None:
        if self.schema_version != EVIDENCE_IDENTITY_SCHEMA:
            raise ValueError("EVIDENCE_IDENTITY_SCHEMA_MISMATCH")
        for value, name in (
            (self.evidence_id, "EVIDENCE_ID"),
            (self.producer_identity, "EVIDENCE_PRODUCER_IDENTITY"),
            (self.generation_ref, "EVIDENCE_GENERATION_REF"),
            (self.condition_ref, "EVIDENCE_CONDITION_REF"),
        ):
            _required(value, name)
        _sha256(self.content_digest, "EVIDENCE_CONTENT_DIGEST")
        if not self.source_refs or any(not isinstance(x, str) or not x.strip() for x in self.source_refs):
            raise ValueError("EVIDENCE_SOURCE_REFS_REQUIRED")
        if self.independence_class not in INDEPENDENCE_CLASSES:
            raise ValueError("UNKNOWN_EVIDENCE_INDEPENDENCE_CLASS")
        for value, name in (
            (self.search_used, "SEARCH_USED"),
            (self.memory_used, "MEMORY_USED"),
            (self.user_conditioned, "USER_CONDITIONED"),
        ):
            if type(value) is not bool:
                raise ValueError(f"{name}_MUST_BE_BOOL")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return _sha({"domain": "AURA-EVIDENCE-IDENTITY-v1", **asdict(self)})


@dataclass(frozen=True)
class DerivationDescriptor:
    schema_version: str
    transformation_code_digest: str
    transformation_config_digest: str
    inclusion_predicate_digest: str
    exclusion_predicate_digest: str
    ordering_grouping_digest: str
    aggregation_digest: str
    rounding_threshold_digest: str
    label_reclassification_digest: str
    source_set_selection_digest: str
    randomness_seed_or_deterministic: str
    environment_generation: str
    policy_generation_ref: str

    def validate(self) -> None:
        if self.schema_version != DERIVATION_SCHEMA:
            raise ValueError("DERIVATION_SCHEMA_MISMATCH")
        for name in DIGEST_OR_NONE_FIELDS:
            _digest_or_none(getattr(self, name), name.upper())
        _required(self.randomness_seed_or_deterministic, "RANDOMNESS_SEED_OR_DETERMINISTIC")
        _required(self.environment_generation, "ENVIRONMENT_GENERATION")
        _required(self.policy_generation_ref, "DERIVATION_POLICY_GENERATION_REF")

    @property
    def fingerprint(self) -> str:
        self.validate()
        return _sha({"domain": "AURA-DERIVATION-v1", **asdict(self)})


@dataclass(frozen=True)
class DerivedPolicy:
    schema_version: str
    currentness_cut: str
    authority_scope: str
    claim_scope: str
    require_clean_independent_evidence: bool

    def validate(self) -> None:
        if self.schema_version != DERIVED_POLICY_SCHEMA:
            raise ValueError("DERIVED_POLICY_SCHEMA_MISMATCH")
        for value, name in (
            (self.currentness_cut, "CURRENTNESS_CUT"),
            (self.authority_scope, "POLICY_AUTHORITY_SCOPE"),
            (self.claim_scope, "POLICY_CLAIM_SCOPE"),
        ):
            _required(value, name)
        if type(self.require_clean_independent_evidence) is not bool:
            raise ValueError("REQUIRE_CLEAN_INDEPENDENT_EVIDENCE_MUST_BE_BOOL")


@dataclass(frozen=True)
class DerivedCandidate:
    schema_version: str
    derived_artifact_id: str
    objective_id: str
    producer_identity: str
    output_digest: str
    output_schema_generation: str
    claim_scope: str
    currentness_cut: str
    authority_scope: str

    def validate(self) -> None:
        if self.schema_version != DERIVED_CANDIDATE_SCHEMA:
            raise ValueError("DERIVED_CANDIDATE_SCHEMA_MISMATCH")
        for value, name in (
            (self.derived_artifact_id, "DERIVED_ARTIFACT_ID"),
            (self.objective_id, "OBJECTIVE_ID"),
            (self.producer_identity, "PRODUCER_IDENTITY"),
            (self.output_schema_generation, "OUTPUT_SCHEMA_GENERATION"),
            (self.claim_scope, "CLAIM_SCOPE"),
            (self.currentness_cut, "CURRENTNESS_CUT"),
            (self.authority_scope, "AUTHORITY_SCOPE"),
        ):
            _required(value, name)
        _sha256(self.output_digest, "OUTPUT_DIGEST")


@dataclass(frozen=True)
class DerivedDecision:
    schema_version: str
    verification_state: str
    reason_code: str
    derivation_fingerprint: str | None
    verified_derived_identity: str | None
    receipt_digest: str
    semantic_reuse_eligible: bool
    independent_evidence_credit_eligible: bool


def _decision(
    *,
    candidate: DerivedCandidate,
    parents: tuple[ParentValidationRef, ...],
    evidence: tuple[EvidenceIdentity, ...],
    policy: DerivedPolicy,
    verification_state: str,
    reason_code: str,
    derivation_fingerprint: str | None,
    verified_derived_identity: str | None,
    semantic_reuse_eligible: bool = False,
    independent_evidence_credit_eligible: bool = False,
) -> DerivedDecision:
    if verification_state not in VERIFICATION_STATES:
        raise ValueError("UNKNOWN_VERIFICATION_STATE")
    receipt_payload = {
        "domain": "AURA-DERIVED-RECEIPT-v1",
        "candidate": asdict(candidate),
        "parent_refs": [asdict(p) for p in sorted(parents, key=lambda p: p.parent_ref)],
        "evidence_fingerprints": sorted(e.fingerprint for e in evidence),
        "policy": asdict(policy),
        "verification_state": verification_state,
        "reason_code": reason_code,
        "derivation_fingerprint": derivation_fingerprint,
        "verified_derived_identity": verified_derived_identity,
    }
    return DerivedDecision(
        schema_version=DERIVED_DECISION_SCHEMA,
        verification_state=verification_state,
        reason_code=reason_code,
        derivation_fingerprint=derivation_fingerprint,
        verified_derived_identity=verified_derived_identity,
        receipt_digest=_sha(receipt_payload),
        semantic_reuse_eligible=semantic_reuse_eligible,
        independent_evidence_credit_eligible=independent_evidence_credit_eligible,
    )


def verify_derived_cognition(
    *,
    candidate: DerivedCandidate,
    parents: tuple[ParentValidationRef, ...],
    evidence: tuple[EvidenceIdentity, ...],
    derivation: DerivationDescriptor | None,
    policy: DerivedPolicy,
) -> DerivedDecision:
    """Verify a derived artifact without conflating bytes, derivation, or evidence rank."""
    candidate.validate()
    policy.validate()
    if not parents:
        raise ValueError("PARENT_VALIDATION_REFS_REQUIRED")
    if len({p.parent_ref for p in parents}) != len(parents):
        raise ValueError("DUPLICATE_PARENT_REF")
    for parent in parents:
        parent.validate()
    if len({e.evidence_id for e in evidence}) != len(evidence):
        raise ValueError("DUPLICATE_EVIDENCE_ID")
    for item in evidence:
        item.validate()

    if derivation is None:
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="HOLD",
            reason_code="DERIVATION_DESCRIPTOR_REQUIRED",
            derivation_fingerprint=None,
            verified_derived_identity=None,
        )
    derivation.validate()
    df = derivation.fingerprint

    if any(not p.valid_current for p in parents):
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="HOLD",
            reason_code="PARENT_VALIDATION_NOT_CURRENT_OR_LOSSLESS",
            derivation_fingerprint=df,
            verified_derived_identity=None,
        )
    if candidate.currentness_cut != policy.currentness_cut:
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="HOLD",
            reason_code="DERIVED_CURRENTNESS_CUT_MISMATCH",
            derivation_fingerprint=df,
            verified_derived_identity=None,
        )
    if candidate.authority_scope != policy.authority_scope:
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="HOLD",
            reason_code="DERIVED_AUTHORITY_SCOPE_MISMATCH",
            derivation_fingerprint=df,
            verified_derived_identity=None,
        )
    if candidate.claim_scope != policy.claim_scope:
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="HOLD",
            reason_code="DERIVED_CLAIM_SCOPE_MISMATCH",
            derivation_fingerprint=df,
            verified_derived_identity=None,
        )

    incompatible = tuple(
        sorted(e.evidence_id for e in evidence if e.independence_class != "CLEAN_INDEPENDENT")
    )
    if policy.require_clean_independent_evidence and incompatible:
        return _decision(
            candidate=candidate,
            parents=parents,
            evidence=evidence,
            policy=policy,
            verification_state="REVIEW",
            reason_code="EVIDENCE_INDEPENDENCE_INCOMPATIBLE",
            derivation_fingerprint=df,
            verified_derived_identity=None,
            independent_evidence_credit_eligible=False,
        )

    vdi = _sha(
        {
            "domain": "AURA-VERIFIED-DERIVED-v1",
            "output_digest": candidate.output_digest,
            "validation_fingerprints": sorted(p.validation_fingerprint for p in parents),
            "derivation_fingerprint": df,
            "evidence_identities": sorted(e.fingerprint for e in evidence),
            "claim_scope": candidate.claim_scope,
            "currentness_cut": candidate.currentness_cut,
            "authority_scope": candidate.authority_scope,
        }
    )
    return _decision(
        candidate=candidate,
        parents=parents,
        evidence=evidence,
        policy=policy,
        verification_state="VERIFIED_BOUNDED",
        reason_code="VERIFIED_DERIVATION_LINEAGE_BOUND",
        derivation_fingerprint=df,
        verified_derived_identity=vdi,
        semantic_reuse_eligible=True,
        independent_evidence_credit_eligible=(
            bool(evidence) and all(e.independence_class == "CLEAN_INDEPENDENT" for e in evidence)
        ),
    )


def verified_semantic_equivalent(a: DerivedDecision, b: DerivedDecision) -> bool:
    """Return semantic equivalence only for verified decisions with identical VDI."""
    return (
        a.verification_state == "VERIFIED_BOUNDED"
        and b.verification_state == "VERIFIED_BOUNDED"
        and a.verified_derived_identity is not None
        and a.verified_derived_identity == b.verified_derived_identity
    )
