from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_proof_carrying_derived_cognition import (
    DERIVATION_SCHEMA,
    DERIVED_CANDIDATE_SCHEMA,
    DERIVED_POLICY_SCHEMA,
    EVIDENCE_IDENTITY_SCHEMA,
    DerivationDescriptor,
    DerivedCandidate,
    DerivedPolicy,
    EvidenceIdentity,
    ParentValidationRef,
    verified_semantic_equivalent,
    verify_derived_cognition,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64


def parent(**overrides):
    base = ParentValidationRef(
        parent_ref="artifact:parent:1",
        parent_content_digest=A,
        validation_fingerprint=B,
        validator_generation_ref="validator-gen-7",
        valid_current=True,
    )
    return replace(base, **overrides)


def evidence(**overrides):
    base = EvidenceIdentity(
        schema_version=EVIDENCE_IDENTITY_SCHEMA,
        evidence_id="evidence:1",
        producer_identity="worker-independent-a",
        generation_ref="evidence-gen-3",
        content_digest=C,
        source_refs=("source:raw:1",),
        independence_class="CLEAN_INDEPENDENT",
        search_used=False,
        memory_used=False,
        user_conditioned=False,
        condition_ref="condition:fresh-no-search-v1",
    )
    return replace(base, **overrides)


def derivation(**overrides):
    base = DerivationDescriptor(
        schema_version=DERIVATION_SCHEMA,
        transformation_code_digest=D,
        transformation_config_digest=E,
        inclusion_predicate_digest="NONE",
        exclusion_predicate_digest="NONE",
        ordering_grouping_digest="NONE",
        aggregation_digest=F,
        rounding_threshold_digest="NONE",
        label_reclassification_digest="NONE",
        source_set_selection_digest="NONE",
        randomness_seed_or_deterministic="DETERMINISTIC",
        environment_generation="python-test-env-v1",
        policy_generation_ref="derived-policy-gen-1",
    )
    return replace(base, **overrides)


def candidate(**overrides):
    base = DerivedCandidate(
        schema_version=DERIVED_CANDIDATE_SCHEMA,
        derived_artifact_id="derived:metric:1",
        objective_id="O-DF-1",
        producer_identity="worker-derive-a",
        output_digest=A,
        output_schema_generation="metric-schema-v1",
        claim_scope="BOUNDED_METRIC",
        currentness_cut="cut-20260831T1455Z",
        authority_scope="D0_NONPROMOTING",
    )
    return replace(base, **overrides)


def policy(**overrides):
    base = DerivedPolicy(
        schema_version=DERIVED_POLICY_SCHEMA,
        currentness_cut="cut-20260831T1455Z",
        authority_scope="D0_NONPROMOTING",
        claim_scope="BOUNDED_METRIC",
        require_clean_independent_evidence=False,
    )
    return replace(base, **overrides)


class ProofCarryingDerivedCognitionTests(unittest.TestCase):
    def test_verified_happy_path_is_deterministic(self):
        first = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(), policy=policy()
        )
        second = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(), policy=policy()
        )
        self.assertEqual(first.verification_state, "VERIFIED_BOUNDED")
        self.assertTrue(first.semantic_reuse_eligible)
        self.assertEqual(first.verified_derived_identity, second.verified_derived_identity)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_same_parents_and_output_but_exclusion_rule_change_changes_identity(self):
        no_exclusion = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(), policy=policy()
        )
        with_exclusion = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(exclusion_predicate_digest="1" * 64), policy=policy()
        )
        self.assertNotEqual(no_exclusion.derivation_fingerprint, with_exclusion.derivation_fingerprint)
        self.assertNotEqual(no_exclusion.verified_derived_identity, with_exclusion.verified_derived_identity)
        self.assertFalse(verified_semantic_equivalent(no_exclusion, with_exclusion))

    def test_same_output_but_rounding_threshold_change_changes_identity(self):
        a = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(rounding_threshold_digest="2" * 64), policy=policy()
        )
        b = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(rounding_threshold_digest="3" * 64), policy=policy()
        )
        self.assertNotEqual(a.verified_derived_identity, b.verified_derived_identity)

    def test_stale_parent_validation_holds_before_semantic_reuse(self):
        result = verify_derived_cognition(
            candidate=candidate(), parents=(parent(valid_current=False),), evidence=(evidence(),),
            derivation=derivation(), policy=policy()
        )
        self.assertEqual(result.verification_state, "HOLD")
        self.assertEqual(result.reason_code, "PARENT_VALIDATION_NOT_CURRENT_OR_LOSSLESS")
        self.assertIsNone(result.verified_derived_identity)
        self.assertFalse(result.semantic_reuse_eligible)

    def test_missing_derivation_descriptor_never_upgrades_matching_bytes(self):
        result = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=None, policy=policy()
        )
        self.assertEqual(result.verification_state, "HOLD")
        self.assertEqual(result.reason_code, "DERIVATION_DESCRIPTOR_REQUIRED")
        self.assertIsNone(result.verified_derived_identity)

    def test_ambiguous_omission_is_rejected_not_treated_as_none(self):
        bad = derivation(exclusion_predicate_digest=None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "EXCLUSION_PREDICATE_DIGEST_MUST_BE_SHA256_HEX"):
            verify_derived_cognition(
                candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
                derivation=bad, policy=policy()
            )

    def test_search_mediated_evidence_cannot_receive_clean_independence_credit(self):
        search_evidence = evidence(
            independence_class="SEARCH_MEDIATED", search_used=True,
            condition_ref="condition:search-enabled-v1"
        )
        result = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(search_evidence,),
            derivation=derivation(), policy=policy(require_clean_independent_evidence=True)
        )
        self.assertEqual(result.verification_state, "REVIEW")
        self.assertEqual(result.reason_code, "EVIDENCE_INDEPENDENCE_INCOMPATIBLE")
        self.assertFalse(result.independent_evidence_credit_eligible)
        self.assertIsNone(result.verified_derived_identity)

    def test_conditioned_evidence_can_still_be_verified_for_non_independence_claim(self):
        search_evidence = evidence(
            independence_class="SEARCH_MEDIATED", search_used=True,
            condition_ref="condition:search-enabled-v1"
        )
        result = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(search_evidence,),
            derivation=derivation(), policy=policy(require_clean_independent_evidence=False)
        )
        self.assertEqual(result.verification_state, "VERIFIED_BOUNDED")
        self.assertTrue(result.semantic_reuse_eligible)
        self.assertFalse(result.independent_evidence_credit_eligible)

    def test_same_semantic_derivation_from_two_producers_collapses_vdi_not_receipt(self):
        first = verify_derived_cognition(
            candidate=candidate(producer_identity="worker-a"), parents=(parent(),),
            evidence=(evidence(),), derivation=derivation(), policy=policy()
        )
        second = verify_derived_cognition(
            candidate=candidate(producer_identity="worker-b"), parents=(parent(),),
            evidence=(evidence(),), derivation=derivation(), policy=policy()
        )
        self.assertEqual(first.verified_derived_identity, second.verified_derived_identity)
        self.assertNotEqual(first.receipt_digest, second.receipt_digest)
        self.assertTrue(verified_semantic_equivalent(first, second))

    def test_evidence_production_history_changes_identity_even_when_content_matches(self):
        clean = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(), policy=policy()
        )
        conditioned = verify_derived_cognition(
            candidate=candidate(), parents=(parent(),),
            evidence=(evidence(
                evidence_id="evidence:2",
                producer_identity="worker-conditioned",
                independence_class="USER_CONDITIONED",
                user_conditioned=True,
                condition_ref="condition:user-followup-v1",
            ),),
            derivation=derivation(), policy=policy()
        )
        self.assertNotEqual(clean.verified_derived_identity, conditioned.verified_derived_identity)

    def test_currentness_authority_and_claim_scope_are_hard_gates(self):
        cases = (
            (candidate(currentness_cut="old-cut"), "DERIVED_CURRENTNESS_CUT_MISMATCH"),
            (candidate(authority_scope="D9_EFFECT"), "DERIVED_AUTHORITY_SCOPE_MISMATCH"),
            (candidate(claim_scope="UNBOUNDED_CLAIM"), "DERIVED_CLAIM_SCOPE_MISMATCH"),
        )
        for c, reason in cases:
            with self.subTest(reason=reason):
                result = verify_derived_cognition(
                    candidate=c, parents=(parent(),), evidence=(evidence(),),
                    derivation=derivation(), policy=policy()
                )
                self.assertEqual(result.verification_state, "HOLD")
                self.assertEqual(result.reason_code, reason)
                self.assertIsNone(result.verified_derived_identity)

    def test_duplicate_parent_and_evidence_identity_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PARENT_REF"):
            verify_derived_cognition(
                candidate=candidate(), parents=(parent(), parent()), evidence=(evidence(),),
                derivation=derivation(), policy=policy()
            )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EVIDENCE_ID"):
            verify_derived_cognition(
                candidate=candidate(), parents=(parent(),), evidence=(evidence(), evidence()),
                derivation=derivation(), policy=policy()
            )

    def test_conflicting_predeclared_derivations_are_preserved_not_voted_together(self):
        metric_a = verify_derived_cognition(
            candidate=candidate(output_digest="4" * 64), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(exclusion_predicate_digest="5" * 64), policy=policy()
        )
        metric_b = verify_derived_cognition(
            candidate=candidate(output_digest="6" * 64), parents=(parent(),), evidence=(evidence(),),
            derivation=derivation(exclusion_predicate_digest="7" * 64), policy=policy()
        )
        self.assertEqual(metric_a.verification_state, "VERIFIED_BOUNDED")
        self.assertEqual(metric_b.verification_state, "VERIFIED_BOUNDED")
        self.assertNotEqual(metric_a.verified_derived_identity, metric_b.verified_derived_identity)
        self.assertFalse(verified_semantic_equivalent(metric_a, metric_b))


if __name__ == "__main__":
    unittest.main()
