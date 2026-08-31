from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_nonexecutable_commit_candidate import (
    CANDIDATE_ELIGIBLE,
    LIFECYCLE_RELATION_SCHEMA,
    PRE_ATTEMPT_ELIGIBLE,
    PRE_ATTEMPT_SCHEMA,
    PreAttemptEnvelopeRef,
    ProposalLifecycleRelationRef,
    create_nonexecutable_commit_candidate,
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
L = "6" * 64
M = "7" * 64
N = "8" * 64


def pre_attempt(**overrides):
    base = PreAttemptEnvelopeRef(
        schema_version=PRE_ATTEMPT_SCHEMA,
        owner_ref="owner:o65-pre-attempt:v1",
        semantic_generation="o65-semantic-gen-1",
        disposition=PRE_ATTEMPT_ELIGIBLE,
        receipt_digest=A,
        proposal_id=B,
        proposal_basis_digest=C,
        proposal_source_generation="source-gen-9",
        pre_attempt_id=D,
        policy_generation="pre-attempt-policy-gen-4",
        policy_digest=E,
        authority_scope="D0_NONPROMOTING",
        expected_route_fingerprint="route:bounded:exact",
        expected_observer_identity="HOST_OBSERVER",
        action_parameters_digest=F,
        resource_envelope_digest=G,
        concurrency_scope_digest=H,
        effect_ceiling_digest=I,
        proposal_current=True,
        policy_current=True,
        concurrent_live_attempt_conflict=False,
        revalidation_required_at_effect_boundary=True,
        execution_authorized=False,
        execution_lease_minted=False,
        provider_effect_authorized=False,
        provider_effect_started=False,
        semantic_k27_authority=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_deploy_spend_public_financial_human_effect=False,
    )
    return replace(base, **overrides)


def lifecycle(**overrides):
    base = ProposalLifecycleRelationRef(
        schema_version=LIFECYCLE_RELATION_SCHEMA,
        owner_ref="owner:q20-proposal-lifecycle:v1",
        semantic_generation="q20-semantic-gen-1",
        receipt_digest=J,
        proposal_id=B,
        proposal_basis_digest=C,
        proposal_currentness_state="CURRENT_NONEXECUTABLE",
        model_objective_id="O66-fixture",
        model_attempt_id="attempt-q20-1",
        model_output_digest=K,
        lifecycle_source_generation="source-gen-9",
        lifecycle_authority_scope="D0_NONPROMOTING",
        proposal_ref_present=True,
        proposal_ref_required_by_policy=True,
        source_generation_bound_to_proposal=True,
        authority_scope_bound_to_proposal=True,
        consequence_key_bound_to_proposal=True,
        lifecycle_terminal_state="TERMINAL_SUCCESS",
        lifecycle_reason_code="ALL_CLOSED_WORLD_GATES_SATISFIED",
        semantic_commit_eligible=True,
        semantic_commit_key=L,
        execution_authority_granted=False,
        provider_effect_authority_granted=False,
        semantic_k27_authority_minted=False,
        native_private_transformer_kv_accessed=False,
        gate10_promoted=False,
        merge_deploy_spend_public_human_effect_authorized=False,
    )
    return replace(base, **overrides)


class NonExecutableCommitCandidateTests(unittest.TestCase):
    def test_exact_parent_relation_mints_only_nonexecutable_candidate(self):
        result = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        self.assertEqual(result.disposition, CANDIDATE_ELIGIBLE)
        self.assertIsNotNone(result.commit_candidate_id)
        self.assertEqual(result.proposal_id, B)
        self.assertEqual(result.proposal_basis_digest, C)
        self.assertEqual(result.source_generation, "source-gen-9")
        self.assertEqual(result.authority_scope, "D0_NONPROMOTING")
        self.assertFalse(result.execution_authorized)
        self.assertFalse(result.execution_lease_minted)
        self.assertFalse(result.commit_authorized)
        self.assertFalse(result.provider_effect_authorized)
        self.assertFalse(result.provider_effect_started)
        self.assertFalse(result.semantic_k27_authority)
        self.assertFalse(result.native_private_transformer_kv_accessed)
        self.assertFalse(result.gate10_promoted)
        self.assertFalse(result.merge_deploy_spend_public_financial_human_effect)
        self.assertTrue(result.revalidation_required_at_effect_boundary)

    def test_exact_candidate_identity_is_deterministic(self):
        first = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        second = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        self.assertEqual(first.commit_candidate_id, second.commit_candidate_id)
        self.assertEqual(first.receipt_digest, second.receipt_digest)

    def test_proposal_id_mismatch_holds_smallest_cone(self):
        result = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(), lifecycle=lifecycle(proposal_id=M)
        )
        self.assertEqual(result.disposition, "HOLD_PROPOSAL_ID_MISMATCH")
        self.assertEqual(result.minimum_invalidated_cone, ("proposal_identity",))
        self.assertIsNone(result.commit_candidate_id)

    def test_proposal_basis_mismatch_holds(self):
        result = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(), lifecycle=lifecycle(proposal_basis_digest=M)
        )
        self.assertEqual(result.reason_code, "PROPOSAL_BASIS_MISMATCH")
        self.assertEqual(result.minimum_invalidated_cone, ("proposal_basis",))

    def test_source_generation_mismatch_holds(self):
        result = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(), lifecycle=lifecycle(lifecycle_source_generation="source-gen-10")
        )
        self.assertEqual(result.reason_code, "SOURCE_GENERATION_MISMATCH")
        self.assertEqual(result.minimum_invalidated_cone, ("source_currentness",))

    def test_authority_scope_mismatch_holds(self):
        result = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(), lifecycle=lifecycle(lifecycle_authority_scope="D9_EFFECT")
        )
        self.assertEqual(result.reason_code, "AUTHORITY_SCOPE_MISMATCH")
        self.assertEqual(result.minimum_invalidated_cone, ("authority_scope",))

    def test_pre_attempt_parent_must_be_current_and_concurrency_clear(self):
        cases = (
            (pre_attempt(proposal_current=False), "PRE_ATTEMPT_PROPOSAL_NOT_CURRENT"),
            (pre_attempt(policy_current=False), "PRE_ATTEMPT_POLICY_NOT_CURRENT"),
            (pre_attempt(concurrent_live_attempt_conflict=True), "PRE_ATTEMPT_CONCURRENCY_NOT_CLEAR"),
            (pre_attempt(concurrent_live_attempt_conflict=None), "PRE_ATTEMPT_CONCURRENCY_NOT_CLEAR"),
        )
        for p, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    create_nonexecutable_commit_candidate(pre_attempt=p, lifecycle=lifecycle())

    def test_pre_attempt_parent_must_require_effect_boundary_revalidation(self):
        with self.assertRaisesRegex(ValueError, "PRE_ATTEMPT_EFFECT_BOUNDARY_REVALIDATION_REQUIRED"):
            create_nonexecutable_commit_candidate(
                pre_attempt=pre_attempt(revalidation_required_at_effect_boundary=False),
                lifecycle=lifecycle(),
            )

    def test_pre_attempt_parent_cannot_smuggle_authority(self):
        fields = (
            "execution_authorized",
            "execution_lease_minted",
            "provider_effect_authorized",
            "provider_effect_started",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "PRE_ATTEMPT_PARENT_EXCEEDS_NONPROMOTION_CEILING"):
                    create_nonexecutable_commit_candidate(
                        pre_attempt=replace(pre_attempt(), **{field: True}), lifecycle=lifecycle()
                    )

    def test_lifecycle_parent_must_be_current_terminal_and_semantically_eligible(self):
        cases = (
            (lifecycle(proposal_currentness_state="INVALIDATED"), "LIFECYCLE_PROPOSAL_NOT_CURRENT"),
            (lifecycle(lifecycle_terminal_state="REVIEW"), "LIFECYCLE_NOT_TERMINAL_SUCCESS"),
            (lifecycle(semantic_commit_eligible=False), "LIFECYCLE_RELATIONAL_GATE_NOT_SATISFIED"),
            (lifecycle(semantic_commit_key=None), "LIFECYCLE_SEMANTIC_COMMIT_KEY_REQUIRED"),
        )
        for relation, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(ValueError, reason):
                    create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=relation)

    def test_each_q20_relational_gate_is_noncompensatory(self):
        for field in (
            "proposal_ref_present",
            "proposal_ref_required_by_policy",
            "source_generation_bound_to_proposal",
            "authority_scope_bound_to_proposal",
            "consequence_key_bound_to_proposal",
        ):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "LIFECYCLE_RELATIONAL_GATE_NOT_SATISFIED"):
                    create_nonexecutable_commit_candidate(
                        pre_attempt=pre_attempt(), lifecycle=replace(lifecycle(), **{field: False})
                    )

    def test_lifecycle_parent_cannot_smuggle_effect_authority(self):
        fields = (
            "execution_authority_granted",
            "provider_effect_authority_granted",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_human_effect_authorized",
        )
        for field in fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "LIFECYCLE_PARENT_EXCEEDS_NONPROMOTION_CEILING"):
                    create_nonexecutable_commit_candidate(
                        pre_attempt=pre_attempt(), lifecycle=replace(lifecycle(), **{field: True})
                    )

    def test_route_observer_action_resource_concurrency_and_ceiling_are_identity_bearing(self):
        original = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        variants = (
            pre_attempt(expected_route_fingerprint="route:bounded:other"),
            pre_attempt(expected_observer_identity="OTHER_OBSERVER"),
            pre_attempt(action_parameters_digest=M),
            pre_attempt(resource_envelope_digest=M),
            pre_attempt(concurrency_scope_digest=M),
            pre_attempt(effect_ceiling_digest=M),
            pre_attempt(policy_generation="pre-attempt-policy-gen-5"),
            pre_attempt(policy_digest=M),
        )
        for variant in variants:
            with self.subTest(variant=variant):
                changed = create_nonexecutable_commit_candidate(pre_attempt=variant, lifecycle=lifecycle())
                self.assertEqual(changed.disposition, CANDIDATE_ELIGIBLE)
                self.assertNotEqual(original.commit_candidate_id, changed.commit_candidate_id)

    def test_lifecycle_semantic_consequence_is_identity_bearing(self):
        original = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        for relation in (
            lifecycle(semantic_commit_key=M),
            lifecycle(model_output_digest=N),
            lifecycle(model_objective_id="O66-other"),
            lifecycle(receipt_digest=M),
        ):
            with self.subTest(relation=relation):
                changed = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=relation)
                self.assertNotEqual(original.commit_candidate_id, changed.commit_candidate_id)

    def test_proof_generation_is_semantic_lineage_not_provider_retry_count(self):
        original = create_nonexecutable_commit_candidate(pre_attempt=pre_attempt(), lifecycle=lifecycle())
        changed_pre = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(semantic_generation="o65-semantic-gen-2"), lifecycle=lifecycle()
        )
        changed_relation = create_nonexecutable_commit_candidate(
            pre_attempt=pre_attempt(), lifecycle=lifecycle(semantic_generation="q20-semantic-gen-2")
        )
        self.assertNotEqual(original.commit_candidate_id, changed_pre.commit_candidate_id)
        self.assertNotEqual(original.commit_candidate_id, changed_relation.commit_candidate_id)

    def test_k27_or_cache_coordinates_are_not_inputs_to_candidate_api(self):
        fields = set(PreAttemptEnvelopeRef.__dataclass_fields__) | set(ProposalLifecycleRelationRef.__dataclass_fields__)
        self.assertNotIn("k27_coordinate", fields)
        self.assertNotIn("cache_key", fields)
        self.assertNotIn("native_kv_handle", fields)


if __name__ == "__main__":
    unittest.main()
