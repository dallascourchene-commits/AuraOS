#!/usr/bin/env python3
"""O65: authority-scoped materialization proposal conformance for AuraOS.

D0 / HS1 / NONPROMOTING.

This membrane consumes two consequence-distinct exact-hosted parent proof surfaces:
- Q20 / PR #701: an exact representation proposal bound to execution-qualified
  materialization lineage, while proposal execution authority remains false.
- O64 evidence admission / PR #702: bounded evidence mass exists only after trusted
  authority, representation, accounting, scope, policy, and currentness are bound.

O65 proves only that the *same representation consequence* is named by both planes.
It does not replace either parent, does not resolve live proposal currentness (PR #696
owns that), and does not authorize model/provider execution or external effects.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from math import gcd
from typing import Any

SCHEMA = "AURA-AUTHORITY-MATERIALIZATION-PROPOSAL-CONFORMANCE-v1"
DECISION_SCHEMA = "AURA-AUTHORITY-MATERIALIZATION-PROPOSAL-CONFORMANCE-DECISION-v1"
HEX = frozenset("0123456789abcdef")

Q20_PROOF_HEAD = "8122131047477c65030af8a3dce97a7881a42c28"
Q20_RUN = 33408333739
Q20_JOB = 99541395341
Q20_PARENT_WORKFLOW = "GLM53 Q20 Materialization Bound Proposal"
Q20_Q19_REPRESENTATION_IDENTITY = "61048a6f227942b514a94a2e5ec46aacee32d9422f4fda7722adcd789213fb0c"
Q20_Q19_PROPOSAL_BASIS = "8b3f0d4ed5f92f2d41745b0f4136b64ff245525c4b533c6e2700b0b4335042cd"
Q20_Q19_SOURCE_GATE_GENERATION = "9dab15c3a0bb0b9ad2408fdd54b09cfcfa1373d8"
Q20_Q6_RECEIPT = "5173b6c1df5f6f889a7912574c51beac546b09a92457cc32ba5918a8f6bd28a4"
Q20_Q15_HEAD = "b4791c47f7e1b1a8078688b2721957fc4c863a90"
Q20_Q15_ARTIFACT_DIGEST = "sha256:812aee1771143c2c598c2610c8387f9540af7341ed778377181c8e036db5116e"
Q20_Q15_PAGE_SET = "4811719dd71a1c8b3258000286955a7ae31895c46a0a34bbfcf5fec3717bdf41"
Q20_REPRESENTATION_FAMILY = "AURA_E8_BALL10_16BIT_REF_V1"
Q20_ACCOUNTING_DOMAIN = "CODEC_PAYLOAD_ONLY"
Q20_SCOPE_LABEL = "GLM53_Q6_2P25_CODEC_RATE_TWO_OFFICIAL_TILES"
Q20_RATE_NUMERATOR = 9
Q20_RATE_DENOMINATOR = 4

O64_PROOF_HEAD = "860b6cb41774e31c1f1ba1942d2f5c91914af0c3"
O64_RUN = 33408498622
O64_JOB = 99541935417
O64_PARENT_WORKFLOW = "Aura O64 Authority Representation Evidence Proof"
O64_SEMANTIC_HEAD = "6f3401b65628df022cd18af86df111fcb59157b4"


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


def _reduced_rate(numerator: int, denominator: int) -> tuple[int, int]:
    if type(numerator) is not int or type(denominator) is not int:
        raise ValueError("RATE_MUST_BE_INTEGER_RATIONAL")
    if numerator <= 0 or denominator <= 0:
        raise ValueError("RATE_MUST_BE_POSITIVE")
    divisor = gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor


def q20_scope_digest() -> str:
    return _sha({"domain": "AURA-O65-Q20-BOUNDED-SCOPE-v1", "scope": Q20_SCOPE_LABEL})


def q20_materialization_relation_digest() -> str:
    return _sha(
        {
            "domain": "AURA-Q20-MATERIALIZATION-RELATION-v1",
            "q19_representation_identity_digest": Q20_Q19_REPRESENTATION_IDENTITY,
            "q6_receipt_digest": Q20_Q6_RECEIPT,
            "q6_page_set_digest": Q20_Q15_PAGE_SET,
            "q15_proof_head": Q20_Q15_HEAD,
            "q15_artifact_digest": Q20_Q15_ARTIFACT_DIGEST,
            "q15_page_set_digest": Q20_Q15_PAGE_SET,
            "accounting_domain": Q20_ACCOUNTING_DOMAIN,
            "exact_codec_rate_bpw": 2.25,
        }
    )


def q20_materialization_bound_basis_digest() -> str:
    return _sha(
        {
            "domain": "AURA-Q20-MATERIALIZATION-BOUND-PROPOSAL-BASIS-v1",
            "q19_proposal_basis_digest": Q20_Q19_PROPOSAL_BASIS,
            "materialization_relation_digest": q20_materialization_relation_digest(),
            "q19_source_gate_generation": Q20_Q19_SOURCE_GATE_GENERATION,
            "authority_ceiling": "NONEXECUTABLE_D0",
        }
    )


def representation_fingerprint(
    *,
    family: str,
    representation_digest: str,
    accounting_domain: str,
    accounting_contract_digest: str,
    rate_numerator: int,
    rate_denominator: int,
    bounded_scope_digest: str,
) -> str:
    _required(family, "REPRESENTATION_FAMILY")
    _sha256(representation_digest, "REPRESENTATION_DIGEST")
    _required(accounting_domain, "ACCOUNTING_DOMAIN")
    _sha256(accounting_contract_digest, "ACCOUNTING_CONTRACT_DIGEST")
    _sha256(bounded_scope_digest, "BOUNDED_SCOPE_DIGEST")
    numerator, denominator = _reduced_rate(rate_numerator, rate_denominator)
    return _sha(
        {
            "domain": "AURA-REPRESENTATION-IDENTITY-v1",
            "representation_family": family,
            "representation_digest": representation_digest,
            "accounting_domain": accounting_domain,
            "accounting_contract_digest": accounting_contract_digest,
            "rate_numerator": numerator,
            "rate_denominator": denominator,
            "bounded_scope_digest": bounded_scope_digest,
        }
    )


@dataclass(frozen=True)
class Q20ProposalProjection:
    proof_head: str
    run_id: int
    job_id: int
    workflow_name: str
    materialization_bound_proposal_basis_digest: str
    materialization_relation_digest: str
    representation_family: str
    representation_digest: str
    accounting_domain: str
    accounting_contract_digest: str
    rate_numerator: int
    rate_denominator: int
    bounded_scope_digest: str
    provider_materialization_execution_qualified: bool
    proposal_execution_authorized: bool
    provider_effect_authorized: bool

    def validate(self) -> None:
        if (self.proof_head, self.run_id, self.job_id, self.workflow_name) != (
            Q20_PROOF_HEAD, Q20_RUN, Q20_JOB, Q20_PARENT_WORKFLOW
        ):
            raise ValueError("Q20_EXACT_HOSTED_PROOF_REQUIRED")
        if self.materialization_bound_proposal_basis_digest != q20_materialization_bound_basis_digest():
            raise ValueError("Q20_MATERIALIZATION_BOUND_BASIS_MISMATCH")
        if self.materialization_relation_digest != q20_materialization_relation_digest():
            raise ValueError("Q20_MATERIALIZATION_RELATION_MISMATCH")
        if self.representation_family != Q20_REPRESENTATION_FAMILY:
            raise ValueError("Q20_REPRESENTATION_FAMILY_MISMATCH")
        if self.representation_digest != Q20_Q19_REPRESENTATION_IDENTITY:
            raise ValueError("Q20_REPRESENTATION_DIGEST_MISMATCH")
        if self.accounting_domain != Q20_ACCOUNTING_DOMAIN:
            raise ValueError("Q20_ACCOUNTING_DOMAIN_MISMATCH")
        _sha256(self.accounting_contract_digest, "Q20_ACCOUNTING_CONTRACT_DIGEST")
        if _reduced_rate(self.rate_numerator, self.rate_denominator) != (
            Q20_RATE_NUMERATOR, Q20_RATE_DENOMINATOR
        ):
            raise ValueError("Q20_RATE_MISMATCH")
        if self.bounded_scope_digest != q20_scope_digest():
            raise ValueError("Q20_SCOPE_MISMATCH")
        if self.provider_materialization_execution_qualified is not True:
            raise ValueError("Q20_MATERIALIZATION_EXECUTION_QUALIFICATION_REQUIRED")
        if self.proposal_execution_authorized is not False or self.provider_effect_authorized is not False:
            raise ValueError("Q20_PROPOSAL_MUST_REMAIN_NONEXECUTABLE")

    @property
    def representation_fingerprint(self) -> str:
        self.validate()
        return representation_fingerprint(
            family=self.representation_family,
            representation_digest=self.representation_digest,
            accounting_domain=self.accounting_domain,
            accounting_contract_digest=self.accounting_contract_digest,
            rate_numerator=self.rate_numerator,
            rate_denominator=self.rate_denominator,
            bounded_scope_digest=self.bounded_scope_digest,
        )


@dataclass(frozen=True)
class AuthorityScopedEvidenceProjection:
    proof_head: str
    run_id: int
    job_id: int
    workflow_name: str
    semantic_head: str
    authority_fingerprint: str
    admission_policy_fingerprint: str
    evidence_admission_fingerprint: str
    representation_fingerprint: str
    representation_family: str
    representation_digest: str
    accounting_domain: str
    accounting_contract_digest: str
    rate_numerator: int
    rate_denominator: int
    bounded_scope_digest: str
    evidence_scope_digest: str
    currentness_roots: tuple[str, ...]
    disposition: str
    score_mass_eligible: bool
    proposal_mass_eligible: bool
    execution_authorized: bool
    provider_effect_authorized: bool
    gate10_promoted: bool

    def validate(self) -> None:
        if (self.proof_head, self.run_id, self.job_id, self.workflow_name, self.semantic_head) != (
            O64_PROOF_HEAD, O64_RUN, O64_JOB, O64_PARENT_WORKFLOW, O64_SEMANTIC_HEAD
        ):
            raise ValueError("O64_EXACT_HOSTED_PROOF_REQUIRED")
        for value, name in (
            (self.authority_fingerprint, "AUTHORITY_FINGERPRINT"),
            (self.admission_policy_fingerprint, "ADMISSION_POLICY_FINGERPRINT"),
            (self.evidence_admission_fingerprint, "EVIDENCE_ADMISSION_FINGERPRINT"),
            (self.representation_fingerprint, "O64_REPRESENTATION_FINGERPRINT"),
            (self.representation_digest, "O64_REPRESENTATION_DIGEST"),
            (self.accounting_contract_digest, "O64_ACCOUNTING_CONTRACT_DIGEST"),
            (self.bounded_scope_digest, "O64_BOUNDED_SCOPE_DIGEST"),
            (self.evidence_scope_digest, "O64_EVIDENCE_SCOPE_DIGEST"),
        ):
            _sha256(value, name)
        _required(self.representation_family, "O64_REPRESENTATION_FAMILY")
        _required(self.accounting_domain, "O64_ACCOUNTING_DOMAIN")
        if self.bounded_scope_digest != self.evidence_scope_digest:
            raise ValueError("O64_REPRESENTATION_SCOPE_NOT_EVIDENCE_SCOPE")
        expected_rf = representation_fingerprint(
            family=self.representation_family,
            representation_digest=self.representation_digest,
            accounting_domain=self.accounting_domain,
            accounting_contract_digest=self.accounting_contract_digest,
            rate_numerator=self.rate_numerator,
            rate_denominator=self.rate_denominator,
            bounded_scope_digest=self.bounded_scope_digest,
        )
        if self.representation_fingerprint != expected_rf:
            raise ValueError("O64_REPRESENTATION_FINGERPRINT_NOT_REPRODUCIBLE")
        if not self.currentness_roots or any(not x.strip() for x in self.currentness_roots):
            raise ValueError("O64_CURRENTNESS_ROOTS_REQUIRED")
        if len(set(self.currentness_roots)) != len(self.currentness_roots):
            raise ValueError("O64_DUPLICATE_CURRENTNESS_ROOT")
        if self.disposition != "VERIFIED_BOUNDED":
            raise ValueError("O64_EVIDENCE_NOT_VERIFIED_BOUNDED")
        if self.score_mass_eligible is not True or self.proposal_mass_eligible is not True:
            raise ValueError("O64_EVIDENCE_MASS_NOT_ELIGIBLE")
        if any((self.execution_authorized, self.provider_effect_authorized, self.gate10_promoted)):
            raise ValueError("O64_EVIDENCE_ADMISSION_CANNOT_AUTHORIZE_EFFECTS")


@dataclass(frozen=True)
class ConformanceDecision:
    schema_version: str
    disposition: str
    reason_code: str
    proposal_basis_digest: str
    materialization_relation_digest: str
    proposal_representation_fingerprint: str
    evidence_representation_fingerprint: str
    authority_fingerprint: str
    admission_policy_fingerprint: str
    evidence_admission_fingerprint: str
    proposal_evidence_support_digest: str | None
    bounded_evidence_supports_exact_proposal: bool
    live_proposal_currentness_resolved: bool = False
    execution_authorized: bool = False
    provider_effect_authorized: bool = False
    semantic_k27_authority: bool = False
    native_private_transformer_kv_accessed: bool = False
    gate10_promoted: bool = False
    merge_or_deployment_authorized: bool = False

    @property
    def receipt_digest(self) -> str:
        return _sha(asdict(self))


def prove_proposal_evidence_conformance(
    *, proposal: Q20ProposalProjection, evidence: AuthorityScopedEvidenceProjection
) -> ConformanceDecision:
    proposal.validate()
    evidence.validate()
    prf = proposal.representation_fingerprint
    erf = evidence.representation_fingerprint
    base = {
        "schema_version": DECISION_SCHEMA,
        "proposal_basis_digest": proposal.materialization_bound_proposal_basis_digest,
        "materialization_relation_digest": proposal.materialization_relation_digest,
        "proposal_representation_fingerprint": prf,
        "evidence_representation_fingerprint": erf,
        "authority_fingerprint": evidence.authority_fingerprint,
        "admission_policy_fingerprint": evidence.admission_policy_fingerprint,
        "evidence_admission_fingerprint": evidence.evidence_admission_fingerprint,
    }

    if proposal.representation_family != evidence.representation_family:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="REPRESENTATION_FAMILY_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if proposal.representation_digest != evidence.representation_digest:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="REPRESENTATION_DIGEST_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if proposal.accounting_domain != evidence.accounting_domain:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="ACCOUNTING_DOMAIN_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if proposal.accounting_contract_digest != evidence.accounting_contract_digest:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="ACCOUNTING_CONTRACT_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if _reduced_rate(proposal.rate_numerator, proposal.rate_denominator) != _reduced_rate(
        evidence.rate_numerator, evidence.rate_denominator
    ):
        return ConformanceDecision(
            disposition="REVIEW", reason_code="EXACT_RATE_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if proposal.bounded_scope_digest != evidence.bounded_scope_digest:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="BOUNDED_SCOPE_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )
    if prf != erf:
        return ConformanceDecision(
            disposition="REVIEW", reason_code="REPRESENTATION_FINGERPRINT_DIVERGENCE",
            proposal_evidence_support_digest=None,
            bounded_evidence_supports_exact_proposal=False, **base
        )

    support = _sha(
        {
            "domain": SCHEMA,
            "proposal_basis_digest": proposal.materialization_bound_proposal_basis_digest,
            "materialization_relation_digest": proposal.materialization_relation_digest,
            "representation_fingerprint": prf,
            "authority_fingerprint": evidence.authority_fingerprint,
            "admission_policy_fingerprint": evidence.admission_policy_fingerprint,
            "evidence_admission_fingerprint": evidence.evidence_admission_fingerprint,
            "currentness_roots": sorted(evidence.currentness_roots),
            "authority_ceiling": "BOUNDED_SUPPORT_NONEXECUTABLE",
        }
    )
    return ConformanceDecision(
        disposition="CONFORMANT_BOUNDED_SUPPORT",
        reason_code="MATERIALIZATION_PROPOSAL_AND_AUTHORITY_SCOPED_EVIDENCE_COMMUTE",
        proposal_evidence_support_digest=support,
        bounded_evidence_supports_exact_proposal=True,
        **base,
    )


def main() -> None:
    print(
        json.dumps(
            {
                "schema": SCHEMA,
                "parents": {
                    "q20": {"head": Q20_PROOF_HEAD, "run": Q20_RUN, "job": Q20_JOB},
                    "o64_evidence": {"head": O64_PROOF_HEAD, "run": O64_RUN, "job": O64_JOB},
                },
                "laws": [
                    "MaterializationBoundProposal!=AuthorityScopedEvidenceAdmissionUntilRepresentationConformance",
                    "SameNominalRate!=SameAccountingDomain",
                    "EquivalentRationalRate==OneCanonicalRateIdentity",
                    "MaterializationExecution!=ProposalExecutionAuthority",
                    "EvidenceAdmission!=LiveProposalCurrentness",
                    "K27Coordinate!=ProposalEvidenceAuthority",
                ],
                "claim_ceiling": {
                    "live_proposal_currentness_resolved": False,
                    "execution_authorized": False,
                    "provider_effect_authorized": False,
                    "semantic_k27_authority": False,
                    "native_private_transformer_kv_accessed": False,
                    "gate10_promoted": False,
                    "merge_or_deployment_authorized": False,
                },
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
