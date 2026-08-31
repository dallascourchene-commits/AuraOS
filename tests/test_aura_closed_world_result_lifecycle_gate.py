from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_closed_world_result_lifecycle_gate import (
    ClaimRef,
    HardGate,
    HostExecutionReceipt,
    IndependentReviewReceipt,
    LifecyclePolicy,
    ModelResultEnvelope,
    reduce_result_lifecycle,
    validate_reuse_state,
)


DIGEST = "1" * 64
HOST_DIGEST = "2" * 64
VF = "3" * 64
REVIEW_DIGEST = "4" * 64


def model(**overrides):
    base = ModelResultEnvelope(
        schema_version="AURA-MODEL-RESULT-v1",
        objective_id="O62",
        attempt_id="attempt-1",
        worker_id="worker-other-agent",
        disposition="COMPLETED",
        result_code="BOUNDED_TYPED_RESULT",
        claims=(
            ClaimRef(
                claim_id="claim-1",
                claim_class="SCIENTIFIC_EVIDENCE",
                value="bounded result",
                evidence_refs=("artifact:evidence:1",),
            ),
        ),
        artifact_refs=("artifact:evidence:1", "artifact:receipt:1"),
        narrative="I completed everything successfully.",
        output_digest=DIGEST,
        source_generation_ref="source-gen-7",
        authority_scope="D0_NONPROMOTING",
        consequence_key="SCK:closed-world-result:1",
    )
    return replace(base, **overrides)


def host(**overrides):
    base = HostExecutionReceipt(
        schema_version="AURA-HOST-EXEC-v1",
        attempt_id="attempt-1",
        output_digest=DIGEST,
        route_fingerprint="route:provider:worker:exact",
        provider_effect_started=True,
        provider_effect_completed=True,
        physical_fanout_observed=1,
        transport_state="RETURNED",
        observer_identity="HOST_OBSERVER",
        receipt_digest=HOST_DIGEST,
    )
    return replace(base, **overrides)


def reviewer(**overrides):
    base = IndependentReviewReceipt(
        schema_version="AURA-INDEPENDENT-REVIEW-v1",
        objective_id="O62",
        reviewer_id="reviewer-other-agent",
        source_generation_ref="source-gen-7",
        authority_scope="D0_NONPROMOTING",
        validation_fingerprint=VF,
        disposition="APPROVE",
        receipt_digest=REVIEW_DIGEST,
    )
    return replace(base, **overrides)


def policy(**overrides):
    base = LifecyclePolicy(
        policy_generation_ref="policy-gen-2",
        execution_required=True,
        physical_fanout_required=1,
        required_artifact_refs=("artifact:evidence:1",),
        required_claim_classes=("SCIENTIFIC_EVIDENCE",),
        current_source_generation_ref="source-gen-7",
        authority_scope="D0_NONPROMOTING",
        validation_fingerprint=VF,
        parent_validation_passed=True,
        contradiction_present=False,
        independent_review_required=False,
        hard_gates=(HardGate("source-current", True), HardGate("authority", True)),
        expected_route_fingerprint="route:provider:worker:exact",
        expected_observer_identity="HOST_OBSERVER",
        host_receipt_authority_verified=True,
    )
    return replace(base, **overrides)


class ClosedWorldLifecycleGateTests(unittest.TestCase):
    def test_happy_path_is_terminal_success_with_deterministic_semantic_commit(self):
        first = reduce_result_lifecycle(model=model(), policy=policy(), host=host())
        second = reduce_result_lifecycle(model=model(), policy=policy(), host=host())
        self.assertEqual(first.terminal_state, "TERMINAL_SUCCESS")
        self.assertTrue(first.semantic_commit_eligible)
        self.assertEqual(first.semantic_commit_key, second.semantic_commit_key)
        self.assertEqual(first.reducer_digest, second.reducer_digest)
        self.assertFalse(first.effect_authority_granted)
        self.assertFalse(first.semantic_k27_authority_minted)
        self.assertFalse(first.native_private_transformer_kv_accessed)

    def test_completed_narrative_cannot_replace_required_host_receipt(self):
        result = reduce_result_lifecycle(model=model(), policy=policy(), host=None)
        self.assertEqual(result.terminal_state, "HOLD")
        self.assertEqual(result.reason_code, "HOST_EXECUTION_RECEIPT_REQUIRED")
        self.assertFalse(result.narrative_can_mint_success)
        self.assertFalse(result.model_self_report_is_execution_truth)

    def test_host_authority_route_and_observer_are_independent_fail_closed_gates(self):
        cases = (
            (policy(host_receipt_authority_verified=False), host(), "HOST_RECEIPT_AUTHORITY_NOT_VERIFIED"),
            (policy(), host(route_fingerprint="route:caller:minted"), "HOST_ROUTE_FINGERPRINT_MISMATCH"),
            (policy(), host(observer_identity="CALLER_SELF_REPORT"), "HOST_OBSERVER_IDENTITY_MISMATCH"),
        )
        for p, h, reason in cases:
            with self.subTest(reason=reason):
                result = reduce_result_lifecycle(model=model(), policy=p, host=h)
                self.assertEqual(result.terminal_state, "HOLD")
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.semantic_commit_eligible)

    def test_optional_execution_physical_fanout_still_binds_entire_host_witness(self):
        p = policy(execution_required=False, physical_fanout_required=1)
        cases = (
            (host(attempt_id="unrelated-attempt"), "HOST_ATTEMPT_MISMATCH"),
            (host(output_digest="5" * 64), "HOST_OUTPUT_DIGEST_MISMATCH"),
            (host(route_fingerprint="route:wrong"), "HOST_ROUTE_FINGERPRINT_MISMATCH"),
            (host(observer_identity="WRONG_OBSERVER"), "HOST_OBSERVER_IDENTITY_MISMATCH"),
        )
        for h, reason in cases:
            with self.subTest(reason=reason):
                result = reduce_result_lifecycle(model=model(), policy=p, host=h)
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.semantic_commit_eligible)

        result = reduce_result_lifecycle(
            model=model(),
            policy=replace(p, host_receipt_authority_verified=False),
            host=host(),
        )
        self.assertEqual(result.reason_code, "HOST_RECEIPT_AUTHORITY_NOT_VERIFIED")

    def test_any_host_derived_success_requires_route_and_observer_bindings(self):
        p = policy(execution_required=False, physical_fanout_required=1)
        with self.assertRaisesRegex(ValueError, "EXPECTED_ROUTE_FINGERPRINT_REQUIRED"):
            replace(p, expected_route_fingerprint=None).validate()
        with self.assertRaisesRegex(ValueError, "EXPECTED_OBSERVER_IDENTITY_REQUIRED"):
            replace(p, expected_observer_identity=None).validate()

    def test_independent_review_requires_typed_receipt(self):
        p = policy(independent_review_required=True)
        result = reduce_result_lifecycle(model=model(), policy=p, host=host())
        self.assertEqual(result.terminal_state, "REVIEW")
        self.assertEqual(result.reason_code, "DISTINCT_REVIEW_REQUIRED")

    def test_independent_reviewer_must_be_distinct_and_bound_to_same_context(self):
        p = policy(independent_review_required=True)
        cases = (
            (reviewer(reviewer_id="worker-other-agent"), "REVIEWER_NOT_DISTINCT"),
            (reviewer(objective_id="OTHER"), "REVIEW_OBJECTIVE_MISMATCH"),
            (reviewer(source_generation_ref="source-gen-old"), "REVIEW_SOURCE_GENERATION_MISMATCH"),
            (reviewer(validation_fingerprint="6" * 64), "REVIEW_VALIDATION_FINGERPRINT_MISMATCH"),
            (reviewer(authority_scope="D9_EFFECT"), "REVIEW_AUTHORITY_SCOPE_MISMATCH"),
            (reviewer(disposition="REJECT"), "INDEPENDENT_REVIEW_NOT_APPROVED"),
        )
        for r, reason in cases:
            with self.subTest(reason=reason):
                result = reduce_result_lifecycle(model=model(), policy=p, host=host(), reviewer=r)
                self.assertEqual(result.terminal_state, "REVIEW")
                self.assertEqual(result.reason_code, reason)
                self.assertFalse(result.semantic_commit_eligible)

        good = reduce_result_lifecycle(model=model(), policy=p, host=host(), reviewer=reviewer())
        self.assertEqual(good.terminal_state, "TERMINAL_SUCCESS")
        self.assertTrue(good.semantic_commit_eligible)

    def test_noncompensatory_validation_source_and_authority_gates_remain_fail_closed(self):
        failed_gate = policy(hard_gates=(HardGate("source-current", False, "SOURCE_NOT_CURRENT"),))
        result = reduce_result_lifecycle(model=model(), policy=failed_gate, host=host())
        self.assertEqual(result.reason_code, "HARD_GATE_FAILED_NONCOMPENSATORY")
        self.assertEqual(result.failed_hard_gate_ids, ("source-current",))

        result = reduce_result_lifecycle(
            model=model(), policy=policy(parent_validation_passed=False), host=host()
        )
        self.assertEqual(result.reason_code, "PARENT_VALIDATION_NOT_CURRENT_OR_LOSSLESS")

        result = reduce_result_lifecycle(
            model=model(source_generation_ref="source-gen-old"), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "SOURCE_GENERATION_NOT_CURRENT")

        result = reduce_result_lifecycle(
            model=model(authority_scope="D9_EFFECT"), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "AUTHORITY_SCOPE_MISMATCH")

    def test_required_evidence_execution_and_disposition_gates_remain_bounded(self):
        result = reduce_result_lifecycle(
            model=model(artifact_refs=("artifact:receipt:1",)), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "REQUIRED_ARTIFACTS_MISSING")

        result = reduce_result_lifecycle(model=model(claims=()), policy=policy(), host=host())
        self.assertEqual(result.reason_code, "REQUIRED_TYPED_CLAIMS_MISSING")

        result = reduce_result_lifecycle(
            model=model(), policy=policy(), host=host(provider_effect_completed=None)
        )
        self.assertEqual(result.reason_code, "HOST_EFFECT_NOT_COMPLETED")

        result = reduce_result_lifecycle(
            model=model(), policy=policy(physical_fanout_required=2), host=host(physical_fanout_observed=1)
        )
        self.assertEqual(result.reason_code, "PHYSICAL_FANOUT_BELOW_POLICY")

        for disposition in ("PARTIAL", "UNKNOWN", "REVIEW_REQUIRED"):
            with self.subTest(disposition=disposition):
                result = reduce_result_lifecycle(
                    model=model(disposition=disposition), policy=policy(), host=host()
                )
                self.assertEqual(result.terminal_state, "REVIEW")
                self.assertFalse(result.semantic_commit_eligible)

    def test_cache_reuse_state_never_promotes_by_name_or_coordinate(self):
        self.assertEqual(validate_reuse_state("LOOKUP_ONLY"), "LOOKUP_ONLY")
        self.assertEqual(validate_reuse_state("NATIVE_CONSUMED"), "NATIVE_CONSUMED")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_REUSE_STATE"):
            validate_reuse_state("K27_COORDINATE_PRESENT_THEREFORE_NATIVE_CONSUMED")


if __name__ == "__main__":
    unittest.main()
