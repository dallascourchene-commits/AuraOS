from __future__ import annotations

from dataclasses import replace
import unittest

from tools import aura_bounded_proposal_capsule as o63
from tools import aura_closed_world_result_lifecycle_gate as o62
from tools import aura_owner_resolved_proposal_lifecycle_bridge as q20
from tools import aura_pre_attempt_admission as o65
from tools import aura_pre_attempt_lifecycle_conformance as o66
from tests.test_aura_pre_attempt_admission import (
    Resolver as O65Resolver,
    basis as o65_basis,
    policy_for as o65_policy_for,
)

A = "a" * 64
B = "b" * 64
C = "c" * 64


class Resolver(O65Resolver):
    def __init__(self, b: o63.ProposalBasis):
        super().__init__(b)
        self.relation_epoch = "o66-relation-epoch-1"
        self.relation_epoch_sequence = None
        self.relation_epoch_calls = 0
        self.raise_relation_epoch = False

    def resolve_pre_attempt_lifecycle_epoch(self, *, proposal_id: str, objective_id: str):
        if self.raise_relation_epoch:
            raise RuntimeError("relation epoch unavailable")
        self.relation_epoch_calls += 1
        if self.relation_epoch_sequence is not None:
            index = min(self.relation_epoch_calls - 1, len(self.relation_epoch_sequence) - 1)
            return self.relation_epoch_sequence[index]
        return self.relation_epoch


def fixture():
    b = o65_basis()
    resolver = Resolver(b)
    generation = o63.create_bounded_proposal_capsule(
        basis=b, producer_identity="worker-o66-parent", owner_resolver=resolver
    )
    capsule = generation.capsule
    resolver.policy = o65_policy_for(b)

    pre = o65.admit_pre_attempt(capsule=capsule, owner_resolver=resolver)
    assert pre.disposition == o65.ELIGIBLE and pre.pre_attempt_id is not None
    pre_ref = o66.pre_attempt_artifact_ref(pre.pre_attempt_id)
    proposal_ref = q20.proposal_artifact_ref(capsule)
    objective = "O66"
    result_code = "PRE_ATTEMPT_LIFECYCLE_EVALUATED"

    model = o62.ModelResultEnvelope(
        schema_version=o62.MODEL_SCHEMA,
        objective_id=objective,
        attempt_id="attempt-o66-1",
        worker_id="worker-o66",
        disposition="COMPLETED",
        result_code=result_code,
        claims=(
            o62.ClaimRef(
                "claim-o66",
                "PRE_ATTEMPT_LIFECYCLE_RELATION",
                "bounded",
                (proposal_ref, pre_ref),
            ),
        ),
        artifact_refs=(proposal_ref, pre_ref, "artifact:o66-result"),
        narrative=None,
        output_digest=A,
        source_generation_ref=capsule.basis.source_admission_generation,
        authority_scope=capsule.basis.authority_scope,
        consequence_key=q20.proposal_consequence_key(
            capsule, objective_id=objective, result_code=result_code
        ),
    )
    policy = o62.LifecyclePolicy(
        policy_generation_ref="o66-lifecycle-policy-v1",
        execution_required=False,
        physical_fanout_required=None,
        required_artifact_refs=(proposal_ref, pre_ref),
        required_claim_classes=("PRE_ATTEMPT_LIFECYCLE_RELATION",),
        current_source_generation_ref=capsule.basis.source_admission_generation,
        authority_scope=capsule.basis.authority_scope,
        validation_fingerprint=B,
        parent_validation_passed=True,
        contradiction_present=False,
        independent_review_required=False,
        hard_gates=(o62.HardGate("source-current", True),),
        expected_route_fingerprint=resolver.policy.expected_route_fingerprint,
        expected_observer_identity=resolver.policy.expected_observer_identity,
        host_receipt_authority_verified=False,
    )
    # Preliminary identity construction must not affect O66's relation-epoch barrier.
    resolver.relation_epoch_calls = 0
    return capsule, resolver, model, policy, pre


class O66PreAttemptLifecycleConformanceTests(unittest.TestCase):
    def test_exact_epoch_serializable_pre_attempt_binds_to_lifecycle_without_authority(self):
        c, r, m, p, pre = fixture()
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(out.disposition, o66.BOUND)
        self.assertEqual(out.pre_attempt_id, pre.pre_attempt_id)
        self.assertEqual(out.relation_owner_epoch, "o66-relation-epoch-1")
        self.assertEqual(r.relation_epoch_calls, 2)
        self.assertEqual(out.lifecycle_terminal_state, "TERMINAL_SUCCESS")
        self.assertTrue(out.semantic_commit_eligible)
        self.assertTrue(out.lifecycle_relational_gates_bound)
        self.assertFalse(out.execution_authority_granted)
        self.assertFalse(out.execution_lease_minted)
        self.assertFalse(out.provider_effect_authority_granted)
        self.assertFalse(out.semantic_k27_authority_minted)

    def test_lifecycle_failure_can_still_have_exact_lineage_binding(self):
        c, r, m, p, _ = fixture()
        p = replace(p, hard_gates=(o62.HardGate("source-current", False, "stale"),))
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(out.disposition, o66.BOUND)
        self.assertNotEqual(out.lifecycle_terminal_state, "TERMINAL_SUCCESS")
        self.assertFalse(out.semantic_commit_eligible)
        self.assertIsNotNone(out.relation_id)

    def test_missing_pre_attempt_artifact_in_model_fails_closed(self):
        c, r, m, p, _ = fixture()
        m = replace(m, artifact_refs=tuple(x for x in m.artifact_refs if not x.startswith("pre_attempt:")))
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_ARTIFACT_REF_MISSING_FROM_MODEL")
        self.assertIsNone(out.relation_id)

    def test_lifecycle_policy_must_require_exact_pre_attempt_artifact(self):
        c, r, m, p, _ = fixture()
        p = replace(p, required_artifact_refs=tuple(x for x in p.required_artifact_refs if not x.startswith("pre_attempt:")))
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_NOT_REQUIRED_BY_LIFECYCLE_POLICY")
        self.assertIsNone(out.relation_id)

    def test_k27_coordinate_cannot_substitute_pre_attempt_artifact(self):
        c, r, m, p, _ = fixture()
        refs = tuple("k27:(12,18,26)" if x.startswith("pre_attempt:") else x for x in m.artifact_refs)
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=replace(m, artifact_refs=refs), policy=p
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_ARTIFACT_REF_MISSING_FROM_MODEL")

    def test_pre_attempt_route_must_equal_lifecycle_route(self):
        c, r, m, p, _ = fixture()
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c,
            owner_resolver=r,
            model=m,
            policy=replace(p, expected_route_fingerprint="route:other"),
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_LIFECYCLE_ROUTE_MISMATCH")

    def test_pre_attempt_observer_must_equal_lifecycle_observer(self):
        c, r, m, p, _ = fixture()
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c,
            owner_resolver=r,
            model=m,
            policy=replace(p, expected_observer_identity="OTHER_OBSERVER"),
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_LIFECYCLE_OBSERVER_MISMATCH")

    def test_relation_epoch_drift_rejects_torn_cross_parent_read(self):
        c, r, m, p, _ = fixture()
        r.relation_epoch_sequence = ("relation-epoch-a", "relation-epoch-b")
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(out.reason_code, "RELATION_OWNER_EPOCH_CHANGED_DURING_EVALUATION")
        self.assertIsNone(out.relation_id)

    def test_missing_unknown_or_exceptional_relation_epoch_fails_closed(self):
        cases = (
            (None, False, "RELATION_OWNER_EPOCH_UNAVAILABLE_OR_UNKNOWN"),
            ("", False, "RELATION_OWNER_EPOCH_INVALID"),
            (None, True, "RELATION_OWNER_EPOCH_RESOLVER_ERROR"),
        )
        for epoch, raises, reason in cases:
            with self.subTest(reason=reason):
                c, r, m, p, _ = fixture()
                r.relation_epoch = epoch
                r.raise_relation_epoch = raises
                out = o66.evaluate_pre_attempt_lifecycle_conformance(
                    capsule=c, owner_resolver=r, model=m, policy=p
                )
                self.assertEqual(out.reason_code, reason)
                self.assertIsNone(out.relation_id)

    def test_pre_attempt_hold_cannot_be_laundered_by_green_lifecycle(self):
        c, r, m, p, _ = fixture()
        r.conflict = True
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertTrue(out.reason_code.startswith("PRE_ATTEMPT_NOT_ELIGIBLE:"))
        self.assertIsNone(out.relation_id)

    def test_proposal_lifecycle_source_mismatch_remains_owned_and_blocks_relation(self):
        c, r, m, p, _ = fixture()
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c,
            owner_resolver=r,
            model=replace(m, source_generation_ref="other-source-generation"),
            policy=p,
        )
        self.assertTrue(out.reason_code.startswith("PROPOSAL_LIFECYCLE_RELATION_NOT_BOUND:"))
        self.assertFalse(out.lifecycle_relational_gates_bound)

    def test_pre_attempt_identity_cannot_be_reused_as_execution_attempt_identity(self):
        c, r, m, p, pre = fixture()
        out = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c,
            owner_resolver=r,
            model=replace(m, attempt_id=pre.pre_attempt_id),
            policy=p,
        )
        self.assertEqual(out.reason_code, "PRE_ATTEMPT_ID_MUST_NOT_BECOME_EXECUTION_ATTEMPT_ID")
        self.assertIsNone(out.relation_id)

    def test_relation_receipt_is_deterministic_and_permanently_nonpromoting(self):
        c, r, m, p, _ = fixture()
        first = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        second = o66.evaluate_pre_attempt_lifecycle_conformance(
            capsule=c, owner_resolver=r, model=m, policy=p
        )
        self.assertEqual(first.disposition, o66.BOUND)
        self.assertEqual(first.relation_id, second.relation_id)
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        for key in (
            "execution_authority_granted",
            "execution_lease_minted",
            "provider_effect_authority_granted",
            "provider_effect_started",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "merge_deploy_spend_public_financial_human_effect_authorized",
        ):
            self.assertFalse(getattr(first, key), key)


if __name__ == "__main__":
    unittest.main()
