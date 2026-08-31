from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_authority_scoped_evidence_admission import (
    AUTHORITY_SCHEMA,
    CANDIDATE_SCHEMA,
    POLICY_SCHEMA,
    REPRESENTATION_SCHEMA,
    AuthorityBindingRef,
    EvidenceAdmissionCandidate,
    EvidenceAdmissionPolicy,
    RepresentationIdentity,
    admit_evidence,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64
E = "e" * 64
F = "f" * 64
G = "1" * 64
H = "2" * 64
I = "3" * 64
J = "4" * 64
ROUTE = "5" * 64


def representation(**overrides):
    base = RepresentationIdentity(
        schema_version=REPRESENTATION_SCHEMA,
        representation_family="E8_CODEC_V2",
        representation_digest=A,
        accounting_domain="CODEC_PAYLOAD_BPW",
        accounting_contract_digest=B,
        rate_numerator=9,
        rate_denominator=4,
        bounded_scope_digest=C,
    )
    return replace(base, **overrides)


def authority(**overrides):
    base = AuthorityBindingRef(
        schema_version=AUTHORITY_SCHEMA,
        owner_ref="owner:host-authority:v1",
        policy_generation_ref="authority-policy-gen-7",
        binding_receipt_digest=D,
        authority_state="VERIFIED_BOUNDED",
        authority_scope="D0_BOUNDED_EVIDENCE",
        execution_required=True,
        expected_route_fingerprint=ROUTE,
        expected_observer_identity="HOST_OBSERVER",
        expected_source_verifier_identity="SOURCE_VERIFIER",
    )
    return replace(base, **overrides)


def policy(**overrides):
    base = EvidenceAdmissionPolicy(
        schema_version=POLICY_SCHEMA,
        policy_owner_ref="owner:evidence-admission:v1",
        policy_generation_ref="admission-policy-gen-3",
        expected_authority_owner_ref="owner:host-authority:v1",
        expected_authority_policy_generation_ref="authority-policy-gen-7",
        expected_authority_scope="D0_BOUNDED_EVIDENCE",
        require_execution_authority=True,
        allowed_accounting_domains=("CODEC_PAYLOAD_BPW",),
        allowed_representation_families=("E8_CODEC_V2",),
    )
    return replace(base, **overrides)


def candidate(**overrides):
    base = EvidenceAdmissionCandidate(
        schema_version=CANDIDATE_SCHEMA,
        evidence_id="evidence:q19:codec-2p25",
        evidence_generation="evidence-gen-11",
        evidence_receipt_digest=E,
        evidence_scope_digest=C,
        source_generation="source-gen-5",
        source_receipt_digest=F,
        source_scope_digest=G,
        route_fingerprint=ROUTE,
        observer_identity="HOST_OBSERVER",
        source_verifier_identity="SOURCE_VERIFIER",
        outcome="SUPPORTS",
        representation=representation(),
        currentness_roots=("science:11", "source:5", "authority:7", "policy:3"),
    )
    return replace(base, **overrides)


class AuthorityScopedEvidenceAdmissionTests(unittest.TestCase):
    def test_verified_supporting_evidence_gets_bounded_mass_only(self):
        result = admit_evidence(candidate=candidate(), authority=authority(), policy=policy())
        self.assertEqual(result.disposition, "VERIFIED_BOUNDED")
        self.assertTrue(result.score_mass_eligible)
        self.assertTrue(result.proposal_mass_eligible)
        self.assertIsNotNone(result.evidence_admission_fingerprint)
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.provider_effect_authorized)
        self.assertFalse(result.gate10_promoted)

    def test_positive_and_negative_mass_share_identical_hard_gates(self):
        supports = admit_evidence(candidate=candidate(outcome="SUPPORTS"), authority=authority(), policy=policy())
        opposes = admit_evidence(candidate=candidate(outcome="OPPOSES"), authority=authority(), policy=policy())
        neutral = admit_evidence(candidate=candidate(outcome="NEUTRAL"), authority=authority(), policy=policy())
        for result in (supports, opposes, neutral):
            self.assertEqual(result.disposition, "VERIFIED_BOUNDED")
            self.assertTrue(result.score_mass_eligible)
        self.assertNotEqual(supports.evidence_admission_fingerprint, opposes.evidence_admission_fingerprint)

    def test_equivalent_rational_rates_have_one_semantic_identity(self):
        canonical = admit_evidence(candidate=candidate(), authority=authority(), policy=policy())
        unreduced = admit_evidence(
            candidate=candidate(representation=representation(rate_numerator=225, rate_denominator=100)),
            authority=authority(),
            policy=policy(),
        )
        self.assertEqual(canonical.representation_fingerprint, unreduced.representation_fingerprint)
        self.assertEqual(canonical.evidence_admission_fingerprint, unreduced.evidence_admission_fingerprint)

    def test_same_outcome_different_representation_is_distinct(self):
        first = admit_evidence(candidate=candidate(), authority=authority(), policy=policy())
        second = admit_evidence(
            candidate=candidate(representation=representation(representation_digest=H)),
            authority=authority(),
            policy=policy(),
        )
        self.assertNotEqual(first.representation_fingerprint, second.representation_fingerprint)
        self.assertNotEqual(first.evidence_admission_fingerprint, second.evidence_admission_fingerprint)

    def test_same_rate_different_accounting_domain_is_distinct_when_both_are_allowed(self):
        p = policy(allowed_accounting_domains=("CODEC_PAYLOAD_BPW", "SERIALIZED_CONTAINER_BPW"))
        codec = admit_evidence(candidate=candidate(), authority=authority(), policy=p)
        container = admit_evidence(
            candidate=candidate(representation=representation(accounting_domain="SERIALIZED_CONTAINER_BPW", accounting_contract_digest=I)),
            authority=authority(),
            policy=p,
        )
        self.assertEqual(codec.disposition, "VERIFIED_BOUNDED")
        self.assertEqual(container.disposition, "VERIFIED_BOUNDED")
        self.assertNotEqual(codec.representation_fingerprint, container.representation_fingerprint)
        self.assertNotEqual(codec.evidence_admission_fingerprint, container.evidence_admission_fingerprint)

    def test_admission_policy_generation_is_part_of_evidence_identity(self):
        first = admit_evidence(candidate=candidate(), authority=authority(), policy=policy())
        second = admit_evidence(
            candidate=candidate(), authority=authority(), policy=policy(policy_generation_ref="admission-policy-gen-4")
        )
        self.assertNotEqual(first.admission_policy_fingerprint, second.admission_policy_fingerprint)
        self.assertNotEqual(first.evidence_admission_fingerprint, second.evidence_admission_fingerprint)

    def test_set_like_policy_and_currentness_order_is_canonical(self):
        p1 = policy(
            allowed_accounting_domains=("CODEC_PAYLOAD_BPW", "SERIALIZED_CONTAINER_BPW"),
            allowed_representation_families=("E8_CODEC_V2", "SCALAR_CODEC_V2"),
        )
        p2 = policy(
            allowed_accounting_domains=("SERIALIZED_CONTAINER_BPW", "CODEC_PAYLOAD_BPW"),
            allowed_representation_families=("SCALAR_CODEC_V2", "E8_CODEC_V2"),
        )
        c1 = candidate()
        c2 = candidate(currentness_roots=("policy:3", "authority:7", "source:5", "science:11"))
        r1 = admit_evidence(candidate=c1, authority=authority(), policy=p1)
        r2 = admit_evidence(candidate=c2, authority=authority(), policy=p2)
        self.assertEqual(r1.admission_policy_fingerprint, r2.admission_policy_fingerprint)
        self.assertEqual(r1.evidence_admission_fingerprint, r2.evidence_admission_fingerprint)

    def test_representation_scope_cannot_crosscast_evidence_scope(self):
        result = admit_evidence(
            candidate=candidate(representation=representation(bounded_scope_digest=J)),
            authority=authority(),
            policy=policy(),
        )
        self.assertEqual(result.disposition, "REVIEW")
        self.assertEqual(result.reason_code, "REPRESENTATION_SCOPE_DOES_NOT_MATCH_EVIDENCE_SCOPE")
        self.assertFalse(result.score_mass_eligible)

    def test_unverified_authority_carries_no_positive_or_negative_mass(self):
        for state in ("HOLD", "REVIEW", "INVALID", "UNKNOWN"):
            with self.subTest(state=state):
                result = admit_evidence(candidate=candidate(outcome="OPPOSES"), authority=authority(authority_state=state), policy=policy())
                self.assertEqual(result.disposition, "HOLD")
                self.assertFalse(result.score_mass_eligible)
                self.assertFalse(result.proposal_mass_eligible)

    def test_authority_owner_policy_generation_and_scope_are_fail_closed(self):
        cases = (
            (authority(owner_ref="owner:other"), "AUTHORITY_OWNER_MISMATCH"),
            (authority(policy_generation_ref="authority-policy-gen-old"), "AUTHORITY_POLICY_GENERATION_MISMATCH"),
            (authority(authority_scope="D9_EFFECT"), "AUTHORITY_SCOPE_MISMATCH"),
        )
        for a, reason in cases:
            with self.subTest(reason=reason):
                result = admit_evidence(candidate=candidate(), authority=a, policy=policy())
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.score_mass_eligible)

    def test_source_verifier_route_and_observer_must_match_trusted_authority(self):
        cases = (
            (candidate(source_verifier_identity="SELF_VERIFIER"), "SOURCE_VERIFIER_IDENTITY_MISMATCH"),
            (candidate(route_fingerprint="6" * 64), "HOST_ROUTE_FINGERPRINT_MISMATCH"),
            (candidate(observer_identity="MODEL_SELF"), "HOST_OBSERVER_IDENTITY_MISMATCH"),
        )
        for c, reason in cases:
            with self.subTest(reason=reason):
                result = admit_evidence(candidate=c, authority=authority(), policy=policy())
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.score_mass_eligible)

    def test_execution_requirement_must_match_policy(self):
        result = admit_evidence(
            candidate=candidate(), authority=authority(), policy=policy(require_execution_authority=False)
        )
        self.assertEqual(result.reason_code, "EXECUTION_AUTHORITY_REQUIREMENT_MISMATCH")
        self.assertFalse(result.score_mass_eligible)

    def test_nonexecution_evidence_cannot_smuggle_host_route_or_observer(self):
        nonexec_authority = authority(
            execution_required=False,
            expected_route_fingerprint="NONE",
            expected_observer_identity="NONE",
        )
        nonexec_policy = policy(require_execution_authority=False)
        bad = admit_evidence(candidate=candidate(), authority=nonexec_authority, policy=nonexec_policy)
        self.assertEqual(bad.disposition, "REVIEW")
        self.assertEqual(bad.reason_code, "NONEXECUTION_EVIDENCE_CANNOT_CLAIM_HOST_ROUTE_OR_OBSERVER")
        good = admit_evidence(
            candidate=candidate(route_fingerprint="NONE", observer_identity="NONE"),
            authority=nonexec_authority,
            policy=nonexec_policy,
        )
        self.assertEqual(good.disposition, "VERIFIED_BOUNDED")

    def test_unadmitted_accounting_or_representation_is_review(self):
        accounting = admit_evidence(
            candidate=candidate(representation=representation(accounting_domain="SERIALIZED_CONTAINER_BPW")),
            authority=authority(),
            policy=policy(),
        )
        family = admit_evidence(
            candidate=candidate(representation=representation(representation_family="OTHER_CODEC")),
            authority=authority(),
            policy=policy(),
        )
        self.assertEqual(accounting.reason_code, "ACCOUNTING_DOMAIN_NOT_ADMITTED")
        self.assertEqual(family.reason_code, "REPRESENTATION_FAMILY_NOT_ADMITTED")

    def test_duplicate_policy_members_and_currentness_roots_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ALLOWED_ACCOUNTING_DOMAIN"):
            admit_evidence(
                candidate=candidate(), authority=authority(),
                policy=policy(allowed_accounting_domains=("CODEC_PAYLOAD_BPW", "CODEC_PAYLOAD_BPW")),
            )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ALLOWED_REPRESENTATION_FAMILY"):
            admit_evidence(
                candidate=candidate(), authority=authority(),
                policy=policy(allowed_representation_families=("E8_CODEC_V2", "E8_CODEC_V2")),
            )
        with self.assertRaisesRegex(ValueError, "DUPLICATE_EVIDENCE_CURRENTNESS_ROOT"):
            admit_evidence(
                candidate=candidate(currentness_roots=("same", "same")), authority=authority(), policy=policy()
            )

    def test_rate_must_be_positive_integer_rational(self):
        for rep in (
            representation(rate_numerator=0),
            representation(rate_denominator=0),
            representation(rate_numerator=2.25),
        ):
            with self.subTest(rep=rep):
                with self.assertRaises(ValueError):
                    rep.validate()


if __name__ == "__main__":
    unittest.main()
