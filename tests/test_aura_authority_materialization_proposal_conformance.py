from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_authority_materialization_proposal_conformance import (
    O64_JOB,
    O64_PARENT_WORKFLOW,
    O64_PROOF_HEAD,
    O64_RUN,
    O64_SEMANTIC_HEAD,
    Q20_ACCOUNTING_DOMAIN,
    Q20_JOB,
    Q20_PARENT_WORKFLOW,
    Q20_PROOF_HEAD,
    Q20_Q19_REPRESENTATION_IDENTITY,
    Q20_RATE_DENOMINATOR,
    Q20_RATE_NUMERATOR,
    Q20_REPRESENTATION_FAMILY,
    Q20_RUN,
    AuthorityScopedEvidenceProjection,
    Q20ProposalProjection,
    prove_proposal_evidence_conformance,
    q20_materialization_bound_basis_digest,
    q20_materialization_relation_digest,
    q20_scope_digest,
    representation_fingerprint,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def proposal(**overrides):
    base = Q20ProposalProjection(
        proof_head=Q20_PROOF_HEAD,
        run_id=Q20_RUN,
        job_id=Q20_JOB,
        workflow_name=Q20_PARENT_WORKFLOW,
        materialization_bound_proposal_basis_digest=q20_materialization_bound_basis_digest(),
        materialization_relation_digest=q20_materialization_relation_digest(),
        representation_family=Q20_REPRESENTATION_FAMILY,
        representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
        accounting_domain=Q20_ACCOUNTING_DOMAIN,
        accounting_contract_digest=A,
        rate_numerator=Q20_RATE_NUMERATOR,
        rate_denominator=Q20_RATE_DENOMINATOR,
        bounded_scope_digest=q20_scope_digest(),
        provider_materialization_execution_qualified=True,
        proposal_execution_authorized=False,
        provider_effect_authorized=False,
    )
    return replace(base, **overrides)


def evidence(**overrides):
    rf = representation_fingerprint(
        family=Q20_REPRESENTATION_FAMILY,
        representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
        accounting_domain=Q20_ACCOUNTING_DOMAIN,
        accounting_contract_digest=A,
        rate_numerator=Q20_RATE_NUMERATOR,
        rate_denominator=Q20_RATE_DENOMINATOR,
        bounded_scope_digest=q20_scope_digest(),
    )
    base = AuthorityScopedEvidenceProjection(
        proof_head=O64_PROOF_HEAD,
        run_id=O64_RUN,
        job_id=O64_JOB,
        workflow_name=O64_PARENT_WORKFLOW,
        semantic_head=O64_SEMANTIC_HEAD,
        authority_fingerprint=B,
        admission_policy_fingerprint=C,
        evidence_admission_fingerprint=D,
        representation_fingerprint=rf,
        representation_family=Q20_REPRESENTATION_FAMILY,
        representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
        accounting_domain=Q20_ACCOUNTING_DOMAIN,
        accounting_contract_digest=A,
        rate_numerator=Q20_RATE_NUMERATOR,
        rate_denominator=Q20_RATE_DENOMINATOR,
        bounded_scope_digest=q20_scope_digest(),
        evidence_scope_digest=q20_scope_digest(),
        currentness_roots=("q20:proof-current", "q19:source-current", "o64:policy-current"),
        disposition="VERIFIED_BOUNDED",
        score_mass_eligible=True,
        proposal_mass_eligible=True,
        execution_authorized=False,
        provider_effect_authorized=False,
        gate10_promoted=False,
    )
    return replace(base, **overrides)


class AuthorityMaterializationProposalConformanceTests(unittest.TestCase):
    def test_exact_conformance_yields_bounded_support_only(self):
        first = prove_proposal_evidence_conformance(proposal=proposal(), evidence=evidence())
        second = prove_proposal_evidence_conformance(proposal=proposal(), evidence=evidence())
        self.assertEqual(first.disposition, "CONFORMANT_BOUNDED_SUPPORT")
        self.assertTrue(first.bounded_evidence_supports_exact_proposal)
        self.assertEqual(first.proposal_evidence_support_digest, second.proposal_evidence_support_digest)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertFalse(first.live_proposal_currentness_resolved)
        self.assertFalse(first.execution_authorized)
        self.assertFalse(first.provider_effect_authorized)
        self.assertFalse(first.semantic_k27_authority)
        self.assertFalse(first.native_private_transformer_kv_accessed)
        self.assertFalse(first.gate10_promoted)
        self.assertFalse(first.merge_or_deployment_authorized)

    def test_q20_parent_identity_is_exact(self):
        for changed in (
            proposal(proof_head="1" * 40),
            proposal(run_id=1),
            proposal(job_id=2),
            proposal(workflow_name="other"),
        ):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, "Q20_EXACT_HOSTED_PROOF_REQUIRED"):
                    prove_proposal_evidence_conformance(proposal=changed, evidence=evidence())

    def test_o64_parent_identity_is_exact(self):
        for changed in (
            evidence(proof_head="2" * 40),
            evidence(run_id=1),
            evidence(job_id=2),
            evidence(workflow_name="other"),
            evidence(semantic_head="3" * 40),
        ):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, "O64_EXACT_HOSTED_PROOF_REQUIRED"):
                    prove_proposal_evidence_conformance(proposal=proposal(), evidence=changed)

    def test_materialization_lineage_cannot_be_substituted(self):
        with self.assertRaisesRegex(ValueError, "Q20_MATERIALIZATION_RELATION_MISMATCH"):
            prove_proposal_evidence_conformance(
                proposal=proposal(materialization_relation_digest="4" * 64), evidence=evidence()
            )
        with self.assertRaisesRegex(ValueError, "Q20_MATERIALIZATION_BOUND_BASIS_MISMATCH"):
            prove_proposal_evidence_conformance(
                proposal=proposal(materialization_bound_proposal_basis_digest="5" * 64), evidence=evidence()
            )

    def test_same_outcome_cannot_crosscast_representation(self):
        changed_digest = "6" * 64
        changed_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=changed_digest,
            accounting_domain=Q20_ACCOUNTING_DOMAIN,
            accounting_contract_digest=A,
            rate_numerator=9,
            rate_denominator=4,
            bounded_scope_digest=q20_scope_digest(),
        )
        result = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(representation_digest=changed_digest, representation_fingerprint=changed_rf),
        )
        self.assertEqual(result.reason_code, "REPRESENTATION_DIGEST_DIVERGENCE")
        self.assertFalse(result.bounded_evidence_supports_exact_proposal)

    def test_accounting_domain_and_contract_are_independent(self):
        domain_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
            accounting_domain="SERIALIZED_CONTAINER_ONLY",
            accounting_contract_digest=A,
            rate_numerator=9,
            rate_denominator=4,
            bounded_scope_digest=q20_scope_digest(),
        )
        domain = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(accounting_domain="SERIALIZED_CONTAINER_ONLY", representation_fingerprint=domain_rf),
        )
        self.assertEqual(domain.reason_code, "ACCOUNTING_DOMAIN_DIVERGENCE")

        contract_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
            accounting_domain=Q20_ACCOUNTING_DOMAIN,
            accounting_contract_digest="7" * 64,
            rate_numerator=9,
            rate_denominator=4,
            bounded_scope_digest=q20_scope_digest(),
        )
        contract = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(accounting_contract_digest="7" * 64, representation_fingerprint=contract_rf),
        )
        self.assertEqual(contract.reason_code, "ACCOUNTING_CONTRACT_DIVERGENCE")

    def test_equivalent_rational_rate_conforms_but_different_rate_does_not(self):
        equivalent_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
            accounting_domain=Q20_ACCOUNTING_DOMAIN,
            accounting_contract_digest=A,
            rate_numerator=225,
            rate_denominator=100,
            bounded_scope_digest=q20_scope_digest(),
        )
        equivalent = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(rate_numerator=225, rate_denominator=100, representation_fingerprint=equivalent_rf),
        )
        self.assertEqual(equivalent.disposition, "CONFORMANT_BOUNDED_SUPPORT")

        different_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
            accounting_domain=Q20_ACCOUNTING_DOMAIN,
            accounting_contract_digest=A,
            rate_numerator=5,
            rate_denominator=2,
            bounded_scope_digest=q20_scope_digest(),
        )
        different = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(rate_numerator=5, rate_denominator=2, representation_fingerprint=different_rf),
        )
        self.assertEqual(different.reason_code, "EXACT_RATE_DIVERGENCE")

    def test_scope_crosscast_is_rejected(self):
        other_scope = "8" * 64
        other_rf = representation_fingerprint(
            family=Q20_REPRESENTATION_FAMILY,
            representation_digest=Q20_Q19_REPRESENTATION_IDENTITY,
            accounting_domain=Q20_ACCOUNTING_DOMAIN,
            accounting_contract_digest=A,
            rate_numerator=9,
            rate_denominator=4,
            bounded_scope_digest=other_scope,
        )
        result = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(
                bounded_scope_digest=other_scope,
                evidence_scope_digest=other_scope,
                representation_fingerprint=other_rf,
            ),
        )
        self.assertEqual(result.reason_code, "BOUNDED_SCOPE_DIVERGENCE")

    def test_unverified_or_noneligible_evidence_cannot_support_proposal(self):
        for changes in (
            {"disposition": "HOLD"},
            {"score_mass_eligible": False},
            {"proposal_mass_eligible": False},
        ):
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    prove_proposal_evidence_conformance(
                        proposal=proposal(), evidence=evidence(**changes)
                    )

    def test_effect_authority_cannot_cross_from_either_parent(self):
        for p in (
            proposal(proposal_execution_authorized=True),
            proposal(provider_effect_authorized=True),
        ):
            with self.subTest(parent="proposal"):
                with self.assertRaisesRegex(ValueError, "Q20_PROPOSAL_MUST_REMAIN_NONEXECUTABLE"):
                    prove_proposal_evidence_conformance(proposal=p, evidence=evidence())
        for e in (
            evidence(execution_authorized=True),
            evidence(provider_effect_authorized=True),
            evidence(gate10_promoted=True),
        ):
            with self.subTest(parent="evidence"):
                with self.assertRaisesRegex(ValueError, "O64_EVIDENCE_ADMISSION_CANNOT_AUTHORIZE_EFFECTS"):
                    prove_proposal_evidence_conformance(proposal=proposal(), evidence=e)

    def test_evidence_representation_fingerprint_must_reproduce(self):
        with self.assertRaisesRegex(ValueError, "O64_REPRESENTATION_FINGERPRINT_NOT_REPRODUCIBLE"):
            prove_proposal_evidence_conformance(
                proposal=proposal(), evidence=evidence(representation_fingerprint="9" * 64)
            )

    def test_currentness_roots_are_bound_but_not_self_resolved(self):
        exact = prove_proposal_evidence_conformance(proposal=proposal(), evidence=evidence())
        changed = prove_proposal_evidence_conformance(
            proposal=proposal(),
            evidence=evidence(currentness_roots=("new-currentness-root",)),
        )
        self.assertNotEqual(exact.proposal_evidence_support_digest, changed.proposal_evidence_support_digest)
        self.assertFalse(changed.live_proposal_currentness_resolved)


if __name__ == "__main__":
    unittest.main()
