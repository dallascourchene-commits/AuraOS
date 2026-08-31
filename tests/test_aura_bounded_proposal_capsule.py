from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_bounded_proposal_capsule import (
    BASIS_SCHEMA,
    ELIGIBILITY_DISPOSITION,
    EligibilityReceiptRef,
    ProposalBasis,
    create_bounded_proposal_capsule,
    revalidate_proposal_capsule,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64
G = "1" * 64
H = "2" * 64


def eligibility(**overrides):
    base = EligibilityReceiptRef(
        disposition=ELIGIBILITY_DISPOSITION,
        receipt_digest=A,
        receipt_generation="transition-gen-1",
        policy_generation_ref="eligibility-policy-gen-2",
        proposal_eligible=True,
        execution_authorized=False,
        provider_effect_authorized=False,
    )
    return replace(base, **overrides)


def basis(**overrides):
    base = ProposalBasis(
        schema_version=BASIS_SCHEMA,
        domain_id="generic.bounded.c2",
        action_kind="BOUNDED_C2_PROPOSAL",
        action_parameters_digest=B,
        scientific_scope_digest=C,
        scientific_evidence_generation="science-gen-8",
        scientific_evidence_receipt_digest=D,
        source_scope_digest=E,
        source_admission_generation="source-gen-4",
        source_admission_receipt_digest=F,
        request_id="request:c2:1",
        request_digest=G,
        resource_envelope_digest=H,
        eligibility=eligibility(),
        currentness_roots=("science-current:8", "source-current:4", "router-current:2"),
        invalidators=("science-generation-change", "source-generation-change", "request-envelope-change"),
        authority_scope="D0_NONPROMOTING",
    )
    return replace(base, **overrides)


class BoundedProposalCapsuleTests(unittest.TestCase):
    def test_same_exact_basis_collapses_to_same_proposal_id(self):
        first = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        second = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-b")
        self.assertEqual(first.capsule.proposal_id, second.capsule.proposal_id)
        self.assertEqual(first.capsule.proposal_basis_digest, second.capsule.proposal_basis_digest)
        self.assertNotEqual(first.generation_receipt_digest, second.generation_receipt_digest)

    def test_capsule_is_permanently_non_executable(self):
        generated = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        c = generated.capsule
        self.assertTrue(c.revalidation_required_before_execution)
        self.assertFalse(c.execution_authorized)
        self.assertFalse(c.provider_effect_authorized)
        self.assertFalse(c.owner_host_execution_observed)
        self.assertFalse(c.native_private_transformer_kv_accessed)
        self.assertFalse(c.semantic_k27_authority)
        self.assertFalse(c.gate10_promoted)
        self.assertFalse(c.merge_deploy_spend_public_human_effect)

    def test_hold_or_noneligible_receipt_cannot_create_capsule(self):
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_RECEIPT_NOT_PROPOSAL_ELIGIBLE"):
            create_bounded_proposal_capsule(
                basis=basis(eligibility=eligibility(disposition="HOLD")), producer_identity="worker-a"
            )

    def test_eligibility_receipt_cannot_smuggle_execution_authority(self):
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_EXECUTION"):
            create_bounded_proposal_capsule(
                basis=basis(eligibility=eligibility(execution_authorized=True)), producer_identity="worker-a"
            )
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_PROVIDER_EFFECT"):
            create_bounded_proposal_capsule(
                basis=basis(eligibility=eligibility(provider_effect_authorized=True)), producer_identity="worker-a"
            )

    def test_source_generation_change_mints_new_basis_not_renewal(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        changed = basis(source_admission_generation="source-gen-5")
        decision = revalidate_proposal_capsule(capsule=original.capsule, current_basis=changed)
        self.assertEqual(decision.state, "INVALIDATED")
        self.assertEqual(decision.reason_code, "PROPOSAL_OPERAND_OR_CURRENTNESS_DRIFT")
        new_capsule = create_bounded_proposal_capsule(basis=changed, producer_identity="worker-b")
        self.assertNotEqual(original.capsule.proposal_id, new_capsule.capsule.proposal_id)

    def test_evidence_scope_or_generation_change_mints_new_proposal(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        for changed in (
            basis(scientific_scope_digest="3" * 64),
            basis(scientific_evidence_generation="science-gen-9"),
            basis(scientific_evidence_receipt_digest="4" * 64),
        ):
            with self.subTest(changed=changed):
                newer = create_bounded_proposal_capsule(basis=changed, producer_identity="worker-b")
                self.assertNotEqual(original.capsule.proposal_id, newer.capsule.proposal_id)

    def test_request_or_resource_widening_changes_proposal_identity(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        for changed in (
            basis(request_digest="5" * 64),
            basis(resource_envelope_digest="6" * 64),
            basis(action_parameters_digest="7" * 64),
        ):
            newer = create_bounded_proposal_capsule(basis=changed, producer_identity="worker-b")
            self.assertNotEqual(original.capsule.proposal_id, newer.capsule.proposal_id)

    def test_policy_generation_change_invalidates_even_when_science_and_source_match(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        changed = basis(eligibility=eligibility(policy_generation_ref="eligibility-policy-gen-3"))
        decision = revalidate_proposal_capsule(capsule=original.capsule, current_basis=changed)
        self.assertEqual(decision.state, "INVALIDATED")

    def test_currentness_root_change_invalidates_without_wall_clock_renewal(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        changed = basis(currentness_roots=("science-current:8", "source-current:5", "router-current:2"))
        decision = revalidate_proposal_capsule(capsule=original.capsule, current_basis=changed)
        self.assertEqual(decision.state, "INVALIDATED")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.provider_effect_authorized)

    def test_order_of_set_like_currentness_and_invalidators_is_canonical(self):
        first = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        reordered = basis(
            currentness_roots=("router-current:2", "source-current:4", "science-current:8"),
            invalidators=("request-envelope-change", "source-generation-change", "science-generation-change"),
        )
        second = create_bounded_proposal_capsule(basis=reordered, producer_identity="worker-b")
        self.assertEqual(first.capsule.proposal_id, second.capsule.proposal_id)

    def test_exact_basis_revalidation_returns_current_but_never_authorizes(self):
        original = create_bounded_proposal_capsule(basis=basis(), producer_identity="worker-a")
        decision = revalidate_proposal_capsule(capsule=original.capsule, current_basis=basis())
        self.assertEqual(decision.state, "CURRENT_NONEXECUTABLE")
        self.assertEqual(decision.reason_code, "EXACT_PROPOSAL_BASIS_STILL_CURRENT")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.provider_effect_authorized)

    def test_duplicate_currentness_or_invalidators_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CURRENTNESS_ROOT"):
            create_bounded_proposal_capsule(
                basis=basis(currentness_roots=("same", "same")), producer_identity="worker-a"
            )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVALIDATOR"):
            create_bounded_proposal_capsule(
                basis=basis(invalidators=("same", "same")), producer_identity="worker-a"
            )


if __name__ == "__main__":
    unittest.main()
