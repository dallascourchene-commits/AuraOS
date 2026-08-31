from __future__ import annotations

from dataclasses import replace
import unittest

from tools.aura_closed_world_result_lifecycle_gate import (
    ClaimRef,
    HardGate,
    HostExecutionReceipt,
    LifecyclePolicy,
    ModelResultEnvelope,
    reduce_result_lifecycle,
    validate_reuse_state,
)


DIGEST = "1" * 64
HOST_DIGEST = "2" * 64
VF = "3" * 64


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
        distinct_reviewer_receipt_present=False,
        hard_gates=(HardGate("source-current", True), HardGate("authority", True)),
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

    def test_positive_result_cannot_compensate_failed_hard_gate(self):
        p = policy(hard_gates=(HardGate("source-current", False, "SOURCE_NOT_CURRENT"),))
        result = reduce_result_lifecycle(model=model(), policy=p, host=host())
        self.assertEqual(result.terminal_state, "HOLD")
        self.assertEqual(result.reason_code, "HARD_GATE_FAILED_NONCOMPENSATORY")
        self.assertEqual(result.failed_hard_gate_ids, ("source-current",))
        self.assertFalse(result.evidence_can_compensate_hard_gate)

    def test_parent_validation_failure_blocks_commit(self):
        result = reduce_result_lifecycle(
            model=model(), policy=policy(parent_validation_passed=False), host=host()
        )
        self.assertEqual(result.reason_code, "PARENT_VALIDATION_NOT_CURRENT_OR_LOSSLESS")
        self.assertFalse(result.semantic_commit_eligible)

    def test_old_source_generation_holds_even_with_completed_model(self):
        result = reduce_result_lifecycle(
            model=model(source_generation_ref="source-gen-old"), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "SOURCE_GENERATION_NOT_CURRENT")

    def test_authority_mismatch_holds(self):
        result = reduce_result_lifecycle(
            model=model(authority_scope="D9_EFFECT"), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "AUTHORITY_SCOPE_MISMATCH")

    def test_contradiction_requires_review(self):
        result = reduce_result_lifecycle(
            model=model(), policy=policy(contradiction_present=True), host=host()
        )
        self.assertEqual(result.terminal_state, "REVIEW")
        self.assertEqual(result.reason_code, "CONTRADICTION_PRESENT")

    def test_distinct_review_requirement_is_non_self_certifying(self):
        result = reduce_result_lifecycle(
            model=model(),
            policy=policy(independent_review_required=True, distinct_reviewer_receipt_present=False),
            host=host(),
        )
        self.assertEqual(result.terminal_state, "REVIEW")
        self.assertEqual(result.reason_code, "DISTINCT_REVIEW_REQUIRED")

    def test_missing_required_artifact_holds(self):
        result = reduce_result_lifecycle(
            model=model(artifact_refs=("artifact:receipt:1",)), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "REQUIRED_ARTIFACTS_MISSING")

    def test_missing_required_typed_claim_holds(self):
        result = reduce_result_lifecycle(
            model=model(claims=()), policy=policy(), host=host()
        )
        self.assertEqual(result.reason_code, "REQUIRED_TYPED_CLAIMS_MISSING")

    def test_host_output_digest_must_match_model_output(self):
        result = reduce_result_lifecycle(
            model=model(), policy=policy(), host=host(output_digest="4" * 64)
        )
        self.assertEqual(result.reason_code, "HOST_OUTPUT_DIGEST_MISMATCH")

    def test_host_effect_must_be_observed_completed(self):
        result = reduce_result_lifecycle(
            model=model(), policy=policy(), host=host(provider_effect_completed=None)
        )
        self.assertEqual(result.reason_code, "HOST_EFFECT_NOT_COMPLETED")

    def test_physical_fanout_claim_requires_host_observation(self):
        result = reduce_result_lifecycle(
            model=model(), policy=policy(physical_fanout_required=2), host=host(physical_fanout_observed=1)
        )
        self.assertEqual(result.reason_code, "PHYSICAL_FANOUT_BELOW_POLICY")

    def test_partial_unknown_review_required_dispositions_do_not_terminal_success(self):
        for disposition in ("PARTIAL", "UNKNOWN", "REVIEW_REQUIRED"):
            with self.subTest(disposition=disposition):
                result = reduce_result_lifecycle(
                    model=model(disposition=disposition), policy=policy(), host=host()
                )
                self.assertEqual(result.terminal_state, "REVIEW")
                self.assertFalse(result.semantic_commit_eligible)

    def test_blocked_refused_and_error_remain_terminal_but_not_success_commits(self):
        for disposition in ("BLOCKED", "REFUSED", "ERROR"):
            with self.subTest(disposition=disposition):
                result = reduce_result_lifecycle(
                    model=model(disposition=disposition), policy=policy(), host=host()
                )
                self.assertNotEqual(result.terminal_state, "TERMINAL_SUCCESS")
                self.assertFalse(result.semantic_commit_eligible)
                self.assertTrue(result.reusable_evidence_eligible)

    def test_cache_reuse_state_never_promotes_by_name_or_coordinate(self):
        self.assertEqual(validate_reuse_state("LOOKUP_ONLY"), "LOOKUP_ONLY")
        self.assertEqual(validate_reuse_state("NATIVE_CONSUMED"), "NATIVE_CONSUMED")
        with self.assertRaisesRegex(ValueError, "UNKNOWN_REUSE_STATE"):
            validate_reuse_state("K27_COORDINATE_PRESENT_THEREFORE_NATIVE_CONSUMED")


if __name__ == "__main__":
    unittest.main()
