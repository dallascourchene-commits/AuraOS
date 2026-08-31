from __future__ import annotations

from dataclasses import replace
import inspect
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
I = "3" * 64


def eligibility(**overrides):
    base = EligibilityReceiptRef(
        owner_ref="owner:generic-product-gate:v1",
        transition_id="transition:source:1",
        domain_id="generic.bounded.c2",
        gate_scope_digest=I,
        source_currentness_root="source-current:4",
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


class OwnerResolver:
    """Test double for a host-owned resolver registry; never used as semantic authority itself."""

    def __init__(
        self,
        current_basis: ProposalBasis,
        *,
        eligibility_state: EligibilityReceiptRef | None | object = ...,
        science_state: ScientificEvidenceState | None | object = ...,
        source_state: SourceAdmissionState | None | object = ...,
        request_state: RequestOwnerState | None | object = ...,
        current_roots: dict[str, bool | None] | None = None,
        invalidators: dict[str, bool | None] | None = None,
    ):
        b = current_basis
        self.eligibility_state = b.eligibility if eligibility_state is ... else eligibility_state
        self.science_state = (
            ScientificEvidenceState(
                scope_digest=b.scientific_scope_digest,
                generation=b.scientific_evidence_generation,
                receipt_digest=b.scientific_evidence_receipt_digest,
            )
            if science_state is ...
            else science_state
        )
        self.source_state = (
            SourceAdmissionState(
                scope_digest=b.source_scope_digest,
                generation=b.source_admission_generation,
                receipt_digest=b.source_admission_receipt_digest,
            )
            if source_state is ...
            else source_state
        )
        self.request_state = (
            RequestOwnerState(
                request_id=b.request_id,
                request_digest=b.request_digest,
                action_parameters_digest=b.action_parameters_digest,
                resource_envelope_digest=b.resource_envelope_digest,
            )
            if request_state is ...
            else request_state
        )
        self.current_roots = current_roots or {root: True for root in b.currentness_roots}
        self.invalidators = invalidators or {name: False for name in b.invalidators}

    def resolve_eligibility(self, *, owner_ref: str, transition_id: str):
        state = self.eligibility_state
        if state is None:
            return None
        if state.owner_ref != owner_ref or state.transition_id != transition_id:
            return None
        return state

    def resolve_scientific_evidence(self, *, scope_digest: str):
        state = self.science_state
        if state is None or state.scope_digest != scope_digest:
            return None
        return state

    def resolve_source_admission(self, *, scope_digest: str):
        state = self.source_state
        if state is None or state.scope_digest != scope_digest:
            return None
        return state

    def resolve_request(self, *, request_id: str):
        state = self.request_state
        if state is None or state.request_id != request_id:
            return None
        return state

    def currentness_root_is_current(self, *, root: str):
        return self.current_roots.get(root)

    def invalidator_is_triggered(self, *, invalidator: str):
        return self.invalidators.get(invalidator)


def create(b: ProposalBasis | None = None, *, producer="worker-a", resolver=None):
    b = b or basis()
    if resolver is None:
        resolver = OwnerResolver(b)
    return create_bounded_proposal_capsule(
        basis=b, producer_identity=producer, owner_resolver=resolver
    )


class BoundedProposalCapsuleTests(unittest.TestCase):
    def test_same_exact_owner_resolved_basis_collapses_to_same_proposal_id(self):
        b = basis()
        resolver = OwnerResolver(b)
        first = create(b, producer="worker-a", resolver=resolver)
        second = create(b, producer="worker-b", resolver=resolver)
        self.assertEqual(first.capsule.proposal_id, second.capsule.proposal_id)
        self.assertNotEqual(first.generation_receipt_digest, second.generation_receipt_digest)

    def test_capsule_is_permanently_non_executable(self):
        c = create().capsule
        self.assertTrue(c.revalidation_required_before_execution)
        self.assertFalse(c.execution_authorized)
        self.assertFalse(c.provider_effect_authorized)
        self.assertFalse(c.owner_host_execution_observed)
        self.assertFalse(c.native_private_transformer_kv_accessed)
        self.assertFalse(c.semantic_k27_authority)
        self.assertFalse(c.gate10_promoted)
        self.assertFalse(c.merge_deploy_spend_public_human_effect)

    def test_creation_requires_owner_resolver(self):
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_OWNER_RESOLVER_REQUIRED"):
            create_bounded_proposal_capsule(
                basis=basis(), producer_identity="worker-a", owner_resolver=None
            )

    def test_caller_minted_eligibility_cannot_create_capsule_against_owner_state(self):
        owner_basis = basis()
        forged = basis(
            eligibility=eligibility(
                receipt_digest="9" * 64,
                policy_generation_ref="forged-policy",
            )
        )
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_OWNER_RECEIPT_MISMATCH"):
            create(forged, resolver=OwnerResolver(owner_basis))

    def test_unknown_owner_eligibility_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_OWNER_RECEIPT_UNRESOLVED"):
            create(basis(), resolver=OwnerResolver(basis(), eligibility_state=None))

    def test_hold_or_noneligible_receipt_cannot_create_capsule(self):
        b = basis(eligibility=eligibility(disposition="HOLD"))
        with self.assertRaisesRegex(ValueError, "ELIGIBILITY_RECEIPT_NOT_PROPOSAL_ELIGIBLE"):
            create(b, resolver=OwnerResolver(b))

    def test_eligibility_receipt_binds_transition_scope_domain_policy_and_currentness(self):
        for changed in (
            eligibility(transition_id="transition:other"),
            eligibility(domain_id="other.domain"),
            eligibility(gate_scope_digest="4" * 64),
            eligibility(policy_generation_ref="policy-gen-new"),
            eligibility(source_currentness_root="source-current:other"),
        ):
            with self.subTest(changed=changed):
                forged = basis(eligibility=changed)
                with self.assertRaises(ValueError):
                    create(forged, resolver=OwnerResolver(basis()))

    def test_eligibility_receipt_cannot_smuggle_execution_authority(self):
        for changed, pattern in (
            (eligibility(execution_authorized=True), "ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_EXECUTION"),
            (eligibility(provider_effect_authorized=True), "ELIGIBILITY_RECEIPT_MUST_NOT_AUTHORIZE_PROVIDER_EFFECT"),
        ):
            b = basis(eligibility=changed)
            with self.assertRaisesRegex(ValueError, pattern):
                create(b, resolver=OwnerResolver(b))

    def test_revalidation_api_has_no_raw_current_basis_escape_hatch(self):
        params = inspect.signature(revalidate_proposal_capsule).parameters
        self.assertNotIn("current_basis", params)
        self.assertIn("owner_resolver", params)

    def test_revalidation_without_owner_resolver_invalidates(self):
        original = create()
        decision = revalidate_proposal_capsule(capsule=original.capsule, owner_resolver=None)
        self.assertEqual(decision.state, "INVALIDATED")
        self.assertEqual(decision.reason_code, "OWNER_RESOLVER_UNAVAILABLE")

    def test_exact_owner_resolved_revalidation_is_current_but_never_authorizes(self):
        b = basis()
        original = create(b)
        decision = revalidate_proposal_capsule(
            capsule=original.capsule, owner_resolver=OwnerResolver(b)
        )
        self.assertEqual(decision.state, "CURRENT_NONEXECUTABLE")
        self.assertEqual(decision.reason_code, "ALL_OWNER_RESOLVED_OPERANDS_STILL_CURRENT")
        self.assertFalse(decision.execution_authorized)
        self.assertFalse(decision.provider_effect_authorized)

    def test_science_source_request_or_resource_owner_drift_invalidates(self):
        original = create()
        variants = (
            basis(scientific_evidence_generation="science-gen-9"),
            basis(source_admission_generation="source-gen-5"),
            basis(request_digest="5" * 64),
            basis(resource_envelope_digest="6" * 64),
            basis(action_parameters_digest="7" * 64),
        )
        for current in variants:
            with self.subTest(current=current):
                decision = revalidate_proposal_capsule(
                    capsule=original.capsule, owner_resolver=OwnerResolver(current)
                )
                self.assertEqual(decision.state, "INVALIDATED")

    def test_policy_or_eligibility_owner_drift_invalidates(self):
        original = create()
        for current in (
            basis(eligibility=eligibility(policy_generation_ref="eligibility-policy-gen-3")),
            basis(eligibility=eligibility(owner_ref="owner:generic-product-gate:v2")),
        ):
            decision = revalidate_proposal_capsule(
                capsule=original.capsule, owner_resolver=OwnerResolver(current)
            )
            self.assertEqual(decision.state, "INVALIDATED")

    def test_stale_currentness_root_cannot_be_replayed_as_current(self):
        b = basis()
        original = create(b)
        roots = {root: True for root in b.currentness_roots}
        roots["source-current:4"] = False
        decision = revalidate_proposal_capsule(
            capsule=original.capsule,
            owner_resolver=OwnerResolver(b, current_roots=roots),
        )
        self.assertEqual(decision.state, "INVALIDATED")
        self.assertEqual(decision.reason_code, "CURRENTNESS_ROOT_NOT_ATTESTED_CURRENT")

    def test_unknown_currentness_or_invalidator_state_invalidates(self):
        b = basis()
        original = create(b)
        roots = {root: True for root in b.currentness_roots}
        roots["router-current:2"] = None
        decision = revalidate_proposal_capsule(
            capsule=original.capsule,
            owner_resolver=OwnerResolver(b, current_roots=roots),
        )
        self.assertEqual(decision.state, "INVALIDATED")
        invalidators = {name: False for name in b.invalidators}
        invalidators["request-envelope-change"] = None
        decision = revalidate_proposal_capsule(
            capsule=original.capsule,
            owner_resolver=OwnerResolver(b, invalidators=invalidators),
        )
        self.assertEqual(decision.state, "INVALIDATED")
        self.assertEqual(decision.reason_code, "INVALIDATOR_UNKNOWN_OR_TRIGGERED")

    def test_triggered_invalidator_invalidates(self):
        b = basis()
        original = create(b)
        invalidators = {name: False for name in b.invalidators}
        invalidators["source-generation-change"] = True
        decision = revalidate_proposal_capsule(
            capsule=original.capsule,
            owner_resolver=OwnerResolver(b, invalidators=invalidators),
        )
        self.assertEqual(decision.state, "INVALIDATED")

    def test_order_of_set_like_currentness_and_invalidators_is_canonical(self):
        first_basis = basis()
        reordered = basis(
            currentness_roots=("router-current:2", "source-current:4", "science-current:8"),
            invalidators=("request-envelope-change", "source-generation-change", "science-generation-change"),
        )
        first = create(first_basis)
        second = create(reordered)
        self.assertEqual(first.capsule.proposal_id, second.capsule.proposal_id)

    def test_tampered_embedded_basis_or_ids_are_rejected_before_resolution(self):
        original = create()
        tampered_basis = replace(
            original.capsule,
            basis=basis(source_admission_generation="source-gen-tampered"),
        )
        with self.assertRaisesRegex(ValueError, "PROPOSAL_CAPSULE_BASIS_INTEGRITY_MISMATCH"):
            revalidate_proposal_capsule(
                capsule=tampered_basis, owner_resolver=OwnerResolver(basis())
            )
        with self.assertRaisesRegex(ValueError, "PROPOSAL_CAPSULE_ID_INTEGRITY_MISMATCH"):
            revalidate_proposal_capsule(
                capsule=replace(original.capsule, proposal_id="9" * 64),
                owner_resolver=OwnerResolver(basis()),
            )

    def test_duplicate_currentness_or_invalidators_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CURRENTNESS_ROOT"):
            create(basis(currentness_roots=("same", "same")))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVALIDATOR"):
            create(basis(invalidators=("same", "same")))


if __name__ == "__main__":
    unittest.main()
