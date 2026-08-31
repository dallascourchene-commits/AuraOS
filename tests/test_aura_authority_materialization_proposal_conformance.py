from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_authority_materialization_proposal_conformance import (
    O64_JOB, O64_PROOF_HEAD, O64_RUN, O64_SEMANTIC_HEAD, O64_WORKFLOW,
    Q20_ACCOUNTING_DOMAIN, Q20_JOB, Q20_PROOF_HEAD, Q20_Q19_REPRESENTATION_IDENTITY,
    Q20_REPRESENTATION_FAMILY, Q20_RUN, Q20_WORKFLOW,
    AuthorityScopedEvidenceProjection, exact_q20_projection,
    prove_proposal_evidence_conformance, q20_accounting_contract_digest,
    q20_materialization_bound_basis_digest, q20_materialization_relation_digest,
    q20_representation_fingerprint, q20_scope_digest, representation_fingerprint,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


def evidence(**overrides):
    family = overrides.get("representation_family", Q20_REPRESENTATION_FAMILY)
    rep_digest = overrides.get("representation_digest", Q20_Q19_REPRESENTATION_IDENTITY)
    domain = overrides.get("accounting_domain", Q20_ACCOUNTING_DOMAIN)
    contract = overrides.get("accounting_contract_digest", q20_accounting_contract_digest())
    n = overrides.get("rate_numerator", 9)
    d = overrides.get("rate_denominator", 4)
    scope = overrides.get("bounded_scope_digest", q20_scope_digest())
    rf = overrides.pop("representation_fingerprint", representation_fingerprint(
        family=family, representation_digest=rep_digest, accounting_domain=domain,
        accounting_contract_digest=contract, rate_numerator=n, rate_denominator=d,
        bounded_scope_digest=scope,
    ))
    base = AuthorityScopedEvidenceProjection(
        proof_head=O64_PROOF_HEAD,
        semantic_head=O64_SEMANTIC_HEAD,
        run_id=O64_RUN,
        job_id=O64_JOB,
        workflow_name=O64_WORKFLOW,
        authority_fingerprint=A,
        admission_policy_fingerprint=B,
        evidence_admission_fingerprint=C,
        representation_fingerprint=rf,
        representation_family=family,
        representation_digest=rep_digest,
        accounting_domain=domain,
        accounting_contract_digest=contract,
        rate_numerator=n,
        rate_denominator=d,
        bounded_scope_digest=scope,
        evidence_scope_digest=overrides.get("evidence_scope_digest", scope),
        currentness_roots=("authority:exact", "source:exact", "policy:exact", "science:exact"),
        disposition="VERIFIED_BOUNDED",
        score_mass_eligible=True,
        proposal_mass_eligible=True,
    )
    clean = {k: v for k, v in overrides.items() if k not in {
        "representation_family", "representation_digest", "accounting_domain",
        "accounting_contract_digest", "rate_numerator", "rate_denominator",
        "bounded_scope_digest", "evidence_scope_digest"
    }}
    return replace(base, **clean)


class O65ConformanceTests(unittest.TestCase):
    def test_exact_conformance_is_deterministic_and_nonpromoting(self):
        first = prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=evidence())
        second = prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=evidence())
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

    def test_q20_parent_and_materialization_lineage_are_exact(self):
        p = exact_q20_projection()
        for changed, reason in (
            (replace(p, proof_head="1" * 40), "Q20_EXACT_HOSTED_PROOF_REQUIRED"),
            (replace(p, run_id=1), "Q20_EXACT_HOSTED_PROOF_REQUIRED"),
            (replace(p, job_id=2), "Q20_EXACT_HOSTED_PROOF_REQUIRED"),
            (replace(p, workflow_name="other"), "Q20_EXACT_HOSTED_PROOF_REQUIRED"),
            (replace(p, materialization_relation_digest="2" * 64), "Q20_MATERIALIZATION_RELATION_MISMATCH"),
            (replace(p, materialization_bound_proposal_basis_digest="3" * 64), "Q20_MATERIALIZATION_BOUND_BASIS_MISMATCH"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    prove_proposal_evidence_conformance(proposal=changed, evidence=evidence())

    def test_o64_parent_is_exact(self):
        for changed in (
            evidence(proof_head="4" * 40), evidence(semantic_head="5" * 40),
            evidence(run_id=1), evidence(job_id=2), evidence(workflow_name="other"),
        ):
            with self.subTest(changed=changed):
                with self.assertRaisesRegex(ValueError, "O64_EXACT_HOSTED_PROOF_REQUIRED"):
                    prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=changed)

    def test_representation_and_accounting_crosscasts_are_review(self):
        cases = (
            (evidence(representation_family="OTHER"), "REPRESENTATION_FAMILY_DIVERGENCE"),
            (evidence(representation_digest="6" * 64), "REPRESENTATION_DIGEST_DIVERGENCE"),
            (evidence(accounting_domain="SERIALIZED_CONTAINER_ONLY"), "ACCOUNTING_DOMAIN_DIVERGENCE"),
            (evidence(accounting_contract_digest="7" * 64), "ACCOUNTING_CONTRACT_DIVERGENCE"),
        )
        for e, reason in cases:
            with self.subTest(reason=reason):
                result = prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=e)
                self.assertEqual(result.disposition, "REVIEW")
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.bounded_evidence_supports_exact_proposal)

    def test_arbitrary_shared_accounting_contract_cannot_be_minted(self):
        forged = "8" * 64
        result = prove_proposal_evidence_conformance(
            proposal=exact_q20_projection(), evidence=evidence(accounting_contract_digest=forged)
        )
        self.assertEqual(result.reason_code, "ACCOUNTING_CONTRACT_DIVERGENCE")
        self.assertNotEqual(forged, q20_accounting_contract_digest())

    def test_equivalent_rational_alias_conforms_and_different_rate_does_not(self):
        equivalent = prove_proposal_evidence_conformance(
            proposal=exact_q20_projection(), evidence=evidence(rate_numerator=225, rate_denominator=100)
        )
        self.assertEqual(equivalent.disposition, "CONFORMANT_BOUNDED_SUPPORT")
        different = prove_proposal_evidence_conformance(
            proposal=exact_q20_projection(), evidence=evidence(rate_numerator=5, rate_denominator=2)
        )
        self.assertEqual(different.reason_code, "EXACT_RATE_DIVERGENCE")

    def test_scope_crosscast_is_review(self):
        scope = "9" * 64
        result = prove_proposal_evidence_conformance(
            proposal=exact_q20_projection(), evidence=evidence(bounded_scope_digest=scope, evidence_scope_digest=scope)
        )
        self.assertEqual(result.reason_code, "BOUNDED_SCOPE_DIVERGENCE")

    def test_representation_fingerprint_must_reproduce(self):
        with self.assertRaisesRegex(ValueError, "O64_REPRESENTATION_FINGERPRINT_NOT_REPRODUCIBLE"):
            prove_proposal_evidence_conformance(
                proposal=exact_q20_projection(), evidence=evidence(representation_fingerprint="0" * 64)
            )

    def test_unverified_noneligible_or_effect_bearing_evidence_fails_closed(self):
        bad = (
            evidence(disposition="HOLD"), evidence(score_mass_eligible=False),
            evidence(proposal_mass_eligible=False), evidence(execution_authorized=True),
            evidence(provider_effect_authorized=True), evidence(gate10_promoted=True),
        )
        for e in bad:
            with self.subTest(e=e):
                with self.assertRaises(ValueError):
                    prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=e)

    def test_q20_effect_authority_cannot_cross(self):
        p = exact_q20_projection()
        for changed in (replace(p, proposal_execution_authorized=True), replace(p, provider_effect_authorized=True)):
            with self.assertRaisesRegex(ValueError, "Q20_PROPOSAL_MUST_REMAIN_NONEXECUTABLE"):
                prove_proposal_evidence_conformance(proposal=changed, evidence=evidence())

    def test_currentness_roots_are_identity_bearing_not_self_resolved(self):
        exact = prove_proposal_evidence_conformance(proposal=exact_q20_projection(), evidence=evidence())
        changed = prove_proposal_evidence_conformance(
            proposal=exact_q20_projection(), evidence=evidence(currentness_roots=("new-root",))
        )
        self.assertNotEqual(exact.proposal_evidence_support_digest, changed.proposal_evidence_support_digest)
        self.assertFalse(changed.live_proposal_currentness_resolved)

    def test_q20_projection_helpers_are_stable(self):
        self.assertEqual(exact_q20_projection().materialization_relation_digest, q20_materialization_relation_digest())
        self.assertEqual(exact_q20_projection().materialization_bound_proposal_basis_digest, q20_materialization_bound_basis_digest())
        self.assertEqual(q20_representation_fingerprint(), evidence().representation_fingerprint)
        self.assertEqual(len(q20_accounting_contract_digest()), 64)
        self.assertEqual(len(q20_scope_digest()), 64)


if __name__ == "__main__":
    unittest.main()
