from dataclasses import replace
import unittest

from tools.project006.workercrystal_reference.workercrystal_acceptance_g6 import (
    AcceptanceFacts,
    AttemptTerminalFacts,
    ContractViolation,
    ContributionBinding,
    G5_CANONICAL_PROFILE,
    StoredAcceptance,
    build_acceptance_bundle,
    build_g6_binding,
    build_g6_operation_body,
    derive_g6_binding_identity_from_body,
    derive_g6_operation_digest_from_body,
    validate_g6_binding_record,
    verify_restart,
)


D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64
D6 = "6" * 64
D7 = "7" * 64
D8 = "8" * 64
D9 = "9" * 64
DA = "a" * 64
DB = "b" * 64
DC = "c" * 64
DD = "d" * 64
DE = "e" * 64
DF = "f" * 64


def contribution(attempt: str, dispatch: str, result_digest: str, receipt: str) -> ContributionBinding:
    return ContributionBinding(attempt, dispatch, result_digest, receipt)


C1 = contribution("attempt-a", "dispatch-a", D1, D2)
C2 = contribution("attempt-b", "dispatch-b", D3, D4)


def make_facts(
    contributions=(C1, C2),
    receipts=(D5, D6),
    result_digest=D7,
    capsule_id="capsule-1",
) -> AcceptanceFacts:
    return AcceptanceFacts(
        result_digest=result_digest,
        capsule_id=capsule_id,
        capsule_digest=D8,
        capsule_incarnation=2,
        accepted_lease_id="lease-1",
        lease_generation=3,
        fencing_token_digest=D9,
        source_currentness_digest=DA,
        authority_effect_ceiling_digest=DB,
        verifying_receipt_identities=receipts,
        required_contribution_profile_identity=DC,
        required_contribution_profile_generation=4,
        required_attempt_set_identity=DD,
        external_contribution_required=bool(contributions),
        contributing_attempt_bindings=contributions,
        accepted_state_generation=5,
    )


def make_terminals(contributions=(C1, C2)) -> tuple[AttemptTerminalFacts, ...]:
    return tuple(
        AttemptTerminalFacts(item, 10 + index)
        for index, item in enumerate(contributions)
    )


class G6ReferenceTests(unittest.TestCase):
    def test_accepted_result_identity_is_permutation_invariant_for_canonical_sets(self) -> None:
        a = make_facts((C1, C2), (D5, D6))
        b = make_facts((C2, C1), (D6, D5))
        self.assertEqual(a.accepted_result_identity(), b.accepted_result_identity())

    def test_duplicate_verifier_identity_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            make_facts(receipts=(D5, D5)).accepted_result_identity()

    def test_duplicate_contribution_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            make_facts(contributions=(C1, C1)).accepted_result_identity()

    def test_binding_schema_normatively_excludes_operation_digest(self) -> None:
        facts = make_facts()
        record = build_g6_binding(facts, make_terminals()[0], facts.accepted_result_identity())
        body = {key: value for key, value in record.items() if key != "binding_identity"}
        body["acceptance_operation_digest"] = DF
        with self.assertRaises(ContractViolation):
            derive_g6_binding_identity_from_body(body)

    def test_g5_profile_alias_is_rejected(self) -> None:
        facts = make_facts()
        terminal = make_terminals()[0]
        record = build_g6_binding(facts, terminal, facts.accepted_result_identity())
        tampered = dict(record)
        tampered["canonical_profile_id"] = G5_CANONICAL_PROFILE
        with self.assertRaises(ContractViolation):
            validate_g6_binding_record(tampered, facts, terminal)

    def test_semantic_binding_validator_requires_protected_facts(self) -> None:
        facts = make_facts()
        terminal = make_terminals()[0]
        record = build_g6_binding(facts, terminal, facts.accepted_result_identity())
        with self.assertRaises(ContractViolation):
            validate_g6_binding_record(record)

    def test_semantic_binding_validator_accepts_exact_record(self) -> None:
        facts = make_facts()
        terminal = make_terminals()[0]
        record = build_g6_binding(facts, terminal, facts.accepted_result_identity())
        self.assertEqual(
            validate_g6_binding_record(record, facts, terminal),
            record["binding_identity"],
        )

    def test_semantic_binding_validator_rejects_rehashed_protected_fact_transplants(self) -> None:
        facts = make_facts()
        terminal = make_terminals()[0]
        record = build_g6_binding(facts, terminal, facts.accepted_result_identity())
        mutations = {
            "accepted_result_identity": DF,
            "accepted_result_digest": DE,
            "terminal_reconciliation_generation": terminal.terminal_reconciliation_generation + 1,
            "capsule_id": "capsule-transplanted",
            "capsule_digest": DE,
            "capsule_incarnation": facts.capsule_incarnation + 1,
            "lease_id": "lease-transplanted",
            "lease_generation": facts.lease_generation + 1,
            "fencing_token_digest": DE,
        }
        for field, value in mutations.items():
            with self.subTest(field=field):
                tampered = dict(record)
                tampered[field] = value
                body = {
                    key: item
                    for key, item in tampered.items()
                    if key != "binding_identity"
                }
                tampered["binding_identity"] = derive_g6_binding_identity_from_body(body)
                with self.assertRaises(ContractViolation):
                    validate_g6_binding_record(tampered, facts, terminal)

    def test_binding_builder_rejects_transplanted_accepted_result_identity(self) -> None:
        facts = make_facts()
        with self.assertRaises(ContractViolation):
            build_g6_binding(facts, make_terminals()[0], DF)

    def test_operation_builder_rejects_transplanted_accepted_result_identity(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        with self.assertRaises(ContractViolation):
            build_g6_operation_body(facts, DF, bundle.binding_identities)

    def test_operation_binding_set_is_permutation_invariant_at_builder_boundary(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        reversed_body = build_g6_operation_body(
            facts, bundle.accepted_result_identity, reversed(bundle.binding_identities)
        )
        self.assertEqual(bundle.operation_body, reversed_body)
        self.assertEqual(
            bundle.acceptance_operation_digest,
            derive_g6_operation_digest_from_body(reversed_body),
        )

    def test_noncanonical_stored_binding_set_is_rejected_on_restart(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        reversed_ids = tuple(reversed(bundle.binding_identities))
        self.assertNotEqual(reversed_ids, bundle.binding_identities)
        stored = StoredAcceptance(
            accepted_result_identity=bundle.accepted_result_identity,
            attempt_accepted_result_binding_identities=reversed_ids,
            bindings=bundle.bindings,
            operation_body=bundle.operation_body,
            acceptance_operation_digest=bundle.acceptance_operation_digest,
        )
        with self.assertRaises(ContractViolation):
            verify_restart(facts, make_terminals(), stored)

    def test_transplanted_operation_digest_fails_closed(self) -> None:
        facts_a = make_facts()
        facts_b = make_facts(result_digest=DE, capsule_id="capsule-2")
        bundle_a = build_acceptance_bundle(facts_a, make_terminals())
        bundle_b = build_acceptance_bundle(facts_b, make_terminals())
        stored = StoredAcceptance(
            accepted_result_identity=bundle_a.accepted_result_identity,
            attempt_accepted_result_binding_identities=bundle_a.binding_identities,
            bindings=bundle_a.bindings,
            operation_body=bundle_a.operation_body,
            acceptance_operation_digest=bundle_b.acceptance_operation_digest,
        )
        with self.assertRaises(ContractViolation):
            verify_restart(facts_a, make_terminals(), stored)

    def test_binding_identity_tamper_fails_closed(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        bindings = [dict(item) for item in bundle.bindings]
        bindings[0]["binding_identity"] = DF
        stored = StoredAcceptance(
            accepted_result_identity=bundle.accepted_result_identity,
            attempt_accepted_result_binding_identities=bundle.binding_identities,
            bindings=bindings,
            operation_body=bundle.operation_body,
            acceptance_operation_digest=bundle.acceptance_operation_digest,
        )
        with self.assertRaises(ContractViolation):
            verify_restart(facts, make_terminals(), stored)

    def test_missing_required_attempt_fails_closed(self) -> None:
        with self.assertRaises(ContractViolation):
            build_acceptance_bundle(make_facts(), make_terminals()[:1])

    def test_extra_attempt_fails_closed(self) -> None:
        facts = make_facts((C1,))
        extra = contribution("attempt-x", "dispatch-x", DE, DF)
        terminals = (AttemptTerminalFacts(C1, 10), AttemptTerminalFacts(extra, 11))
        with self.assertRaises(ContractViolation):
            build_acceptance_bundle(facts, terminals)

    def test_empty_required_attempt_set_invalid_when_external_required(self) -> None:
        facts = replace(make_facts(contributions=()), external_contribution_required=True)
        with self.assertRaises(ContractViolation):
            build_acceptance_bundle(facts, ())

    def test_multiple_accepted_result_relations_do_not_overwrite_attempt_state(self) -> None:
        terminal = AttemptTerminalFacts(C1, 10)
        facts_a = make_facts((C1,), result_digest=D7, capsule_id="capsule-a")
        facts_b = make_facts((C1,), result_digest=DE, capsule_id="capsule-b")
        bundle_a = build_acceptance_bundle(facts_a, (terminal,))
        bundle_b = build_acceptance_bundle(facts_b, (terminal,))
        self.assertNotEqual(
            bundle_a.bindings[0]["binding_identity"],
            bundle_b.bindings[0]["binding_identity"],
        )
        self.assertEqual(terminal.terminal_reconciliation_generation, 10)

    def test_operation_body_rejects_extra_field(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        body = dict(bundle.operation_body)
        body["unexpected"] = "x"
        with self.assertRaises(ContractViolation):
            derive_g6_operation_digest_from_body(body)

    def test_operation_body_rejects_malformed_protected_digest(self) -> None:
        facts = make_facts()
        bundle = build_acceptance_bundle(facts, make_terminals())
        body = dict(bundle.operation_body)
        body["source_currentness_digest"] = "not-a-digest"
        with self.assertRaises(ContractViolation):
            derive_g6_operation_digest_from_body(body)

    def test_restart_fails_for_non_complete_lifecycle(self) -> None:
        facts = make_facts()
        terminals = make_terminals()
        bundle = build_acceptance_bundle(facts, terminals)
        stored = StoredAcceptance(
            accepted_result_identity=bundle.accepted_result_identity,
            attempt_accepted_result_binding_identities=bundle.binding_identities,
            bindings=bundle.bindings,
            operation_body=bundle.operation_body,
            acceptance_operation_digest=bundle.acceptance_operation_digest,
            lifecycle="PENDING",
        )
        with self.assertRaises(ContractViolation):
            verify_restart(facts, terminals, stored)

    def test_restart_rebuild_succeeds_for_exact_bundle(self) -> None:
        facts = make_facts()
        terminals = make_terminals()
        bundle = build_acceptance_bundle(facts, terminals)
        stored = StoredAcceptance(
            accepted_result_identity=bundle.accepted_result_identity,
            attempt_accepted_result_binding_identities=bundle.binding_identities,
            bindings=bundle.bindings,
            operation_body=bundle.operation_body,
            acceptance_operation_digest=bundle.acceptance_operation_digest,
        )
        self.assertEqual(verify_restart(facts, terminals, stored), bundle)


if __name__ == "__main__":
    unittest.main()