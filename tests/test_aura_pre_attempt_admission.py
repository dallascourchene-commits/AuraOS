from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_bounded_proposal_capsule import (
    BASIS_SCHEMA,
    ELIGIBILITY_DISPOSITION,
    EligibilityReceiptRef,
    ProposalBasis,
    RequestOwnerState,
    ScientificEvidenceState,
    SourceAdmissionState,
    create_bounded_proposal_capsule,
)
from tools.aura_pre_attempt_admission import (
    ELIGIBLE,
    POLICY_SCHEMA,
    PreAttemptPolicyState,
    admit_pre_attempt,
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
K = "5" * 64


def eligibility(**overrides):
    base = EligibilityReceiptRef(
        owner_ref="owner:generic-product-gate:v1",
        transition_id="transition-1",
        domain_id="benchmark",
        gate_scope_digest=A,
        source_currentness_root="root-source",
        disposition=ELIGIBILITY_DISPOSITION,
        receipt_digest=B,
        receipt_generation="eligibility-gen-1",
        policy_generation_ref="eligibility-policy-gen-1",
        proposal_eligible=True,
        execution_authorized=False,
        provider_effect_authorized=False,
    )
    return replace(base, **overrides)


def basis(**overrides):
    base = ProposalBasis(
        schema_version=BASIS_SCHEMA,
        domain_id="benchmark",
        action_kind="run-bounded-benchmark",
        action_parameters_digest=C,
        scientific_scope_digest=D,
        scientific_evidence_generation="science-gen-1",
        scientific_evidence_receipt_digest=E,
        source_scope_digest=F,
        source_admission_generation="source-gen-1",
        source_admission_receipt_digest=G,
        request_id="request-1",
        request_digest=H,
        resource_envelope_digest=I,
        eligibility=eligibility(),
        currentness_roots=("root-source", "root-policy"),
        invalidators=("invalidator-source",),
        authority_scope="D0_PREATTEMPT_ONLY",
    )
    return replace(base, **overrides)


class Resolver:
    def __init__(self, b: ProposalBasis):
        self.eligibility_state = b.eligibility
        self.science_state = ScientificEvidenceState(
            scope_digest=b.scientific_scope_digest,
            generation=b.scientific_evidence_generation,
            receipt_digest=b.scientific_evidence_receipt_digest,
        )
        self.source_state = SourceAdmissionState(
            scope_digest=b.source_scope_digest,
            generation=b.source_admission_generation,
            receipt_digest=b.source_admission_receipt_digest,
        )
        self.request_state = RequestOwnerState(
            request_id=b.request_id,
            request_digest=b.request_digest,
            action_parameters_digest=b.action_parameters_digest,
            resource_envelope_digest=b.resource_envelope_digest,
        )
        self.roots = {root: True for root in b.currentness_roots}
        self.invalidators = {item: False for item in b.invalidators}
        self.policy = None
        self.conflict = False
        self.raise_policy = False
        self.raise_concurrency = False

    def resolve_eligibility(self, *, owner_ref: str, transition_id: str):
        return self.eligibility_state

    def resolve_scientific_evidence(self, *, scope_digest: str):
        return self.science_state

    def resolve_source_admission(self, *, scope_digest: str):
        return self.source_state

    def resolve_request(self, *, request_id: str):
        return self.request_state

    def currentness_root_is_current(self, *, root: str):
        return self.roots.get(root)

    def invalidator_is_triggered(self, *, invalidator: str):
        return self.invalidators.get(invalidator)

    def resolve_pre_attempt_policy(self, *, proposal_id: str, domain_id: str, action_kind: str):
        if self.raise_policy:
            raise RuntimeError("policy unavailable")
        return self.policy

    def concurrent_live_attempt_exists(self, *, proposal_id: str, concurrency_scope_digest: str):
        if self.raise_concurrency:
            raise RuntimeError("concurrency unavailable")
        return self.conflict


def policy_for(b: ProposalBasis, **overrides):
    base = PreAttemptPolicyState(
        schema_version=POLICY_SCHEMA,
        policy_generation="pre-policy-gen-1",
        proposal_id=b.proposal_id,
        domain_id=b.domain_id,
        action_kind=b.action_kind,
        authority_scope=b.authority_scope,
        expected_route_fingerprint="route:benchmark:exact",
        expected_observer_identity="HOST_PRE_ATTEMPT_OBSERVER",
        action_parameters_digest=b.action_parameters_digest,
        resource_envelope_digest=b.resource_envelope_digest,
        concurrency_scope_digest=J,
        effect_ceiling_digest=K,
        policy_current=True,
        execution_authorized=False,
        provider_effect_authorized=False,
    )
    return replace(base, **overrides)


def capsule_and_resolver(*, producer: str = "worker-a"):
    b = basis()
    r = Resolver(b)
    generation = create_bounded_proposal_capsule(
        basis=b, producer_identity=producer, owner_resolver=r
    )
    r.policy = policy_for(b)
    return generation.capsule, r


class PreAttemptAdmissionTests(unittest.TestCase):
    def test_exact_owner_resolved_basis_mints_only_pre_attempt_identity(self):
        capsule, resolver = capsule_and_resolver()
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.disposition, ELIGIBLE)
        self.assertEqual(len(result.pre_attempt_id or ""), 64)
        self.assertTrue(result.proposal_current)
        self.assertTrue(result.policy_current)
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.execution_lease_minted)
        self.assertFalse(result.provider_effect_authorized)
        self.assertFalse(result.provider_effect_started)
        self.assertFalse(result.semantic_k27_authority)
        self.assertFalse(result.native_private_transformer_kv_accessed)
        self.assertFalse(result.gate10_promoted)

    def test_same_semantic_proposal_from_two_producers_collapses_to_same_pre_attempt_identity(self):
        first, first_resolver = capsule_and_resolver(producer="worker-a")
        second, second_resolver = capsule_and_resolver(producer="worker-b")
        self.assertEqual(first.proposal_id, second.proposal_id)
        a = admit_pre_attempt(capsule=first, owner_resolver=first_resolver)
        b = admit_pre_attempt(capsule=second, owner_resolver=second_resolver)
        self.assertEqual(a.pre_attempt_id, b.pre_attempt_id)

    def test_missing_resolver_holds_without_minting_attempt_identity(self):
        capsule, _ = capsule_and_resolver()
        result = admit_pre_attempt(capsule=capsule, owner_resolver=None)
        self.assertEqual(result.reason_code, "OWNER_RESOLVER_UNAVAILABLE")
        self.assertIsNone(result.pre_attempt_id)

    def test_stale_proposal_currentness_holds_before_policy(self):
        capsule, resolver = capsule_and_resolver()
        resolver.roots["root-source"] = False
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "PROPOSAL_NOT_CURRENT")
        self.assertEqual(result.minimum_invalidated_cone, ("proposal_currentness",))

    def test_unknown_policy_state_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.policy = None
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "POLICY_UNAVAILABLE_OR_UNKNOWN")

    def test_policy_resolver_error_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.raise_policy = True
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "POLICY_RESOLVER_ERROR")

    def test_invalid_policy_cannot_smuggle_execution_authority(self):
        capsule, resolver = capsule_and_resolver()
        resolver.policy = replace(resolver.policy, execution_authorized=True)
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "POLICY_INVALID")
        self.assertFalse(result.execution_authorized)
        self.assertIsNone(result.pre_attempt_id)

    def test_stale_policy_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.policy = replace(resolver.policy, policy_current=False)
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "POLICY_NOT_CURRENT")

    def test_authority_action_and_resource_mismatches_are_noncompensatory(self):
        cases = (
            ("authority_scope", "D9_EFFECT", "AUTHORITY_SCOPE_MISMATCH"),
            ("action_parameters_digest", "6" * 64, "ACTION_PARAMETERS_MISMATCH"),
            ("resource_envelope_digest", "7" * 64, "RESOURCE_ENVELOPE_MISMATCH"),
        )
        for field, value, reason in cases:
            with self.subTest(field=field):
                capsule, resolver = capsule_and_resolver()
                resolver.policy = replace(resolver.policy, **{field: value})
                result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
                self.assertEqual(result.reason_code, reason)
                self.assertIsNone(result.pre_attempt_id)

    def test_live_concurrency_conflict_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.conflict = True
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "CONCURRENT_LIVE_ATTEMPT")
        self.assertTrue(result.concurrent_live_attempt_conflict)

    def test_unknown_concurrency_state_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.conflict = None
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "CONCURRENCY_UNKNOWN")

    def test_concurrency_resolver_error_holds(self):
        capsule, resolver = capsule_and_resolver()
        resolver.raise_concurrency = True
        result = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(result.reason_code, "CONCURRENCY_RESOLVER_ERROR")

    def test_current_policy_route_or_observer_generation_changes_pre_attempt_identity(self):
        capsule, resolver = capsule_and_resolver()
        first = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        for changes in (
            {"policy_generation": "pre-policy-gen-2"},
            {"expected_route_fingerprint": "route:benchmark:other"},
            {"expected_observer_identity": "OTHER_OBSERVER"},
        ):
            with self.subTest(changes=changes):
                capsule2, resolver2 = capsule_and_resolver()
                resolver2.policy = replace(resolver2.policy, **changes)
                changed = admit_pre_attempt(capsule=capsule2, owner_resolver=resolver2)
                self.assertEqual(changed.disposition, ELIGIBLE)
                self.assertNotEqual(first.pre_attempt_id, changed.pre_attempt_id)

    def test_receipt_digest_is_deterministic(self):
        capsule, resolver = capsule_and_resolver()
        first = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        second = admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(first.to_dict(), second.to_dict())


if __name__ == "__main__":
    unittest.main()
