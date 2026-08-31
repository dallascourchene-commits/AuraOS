from __future__ import annotations

import unittest

from tools.quantization.aura_glm53_packed_expert_quantization_plan import (
    PER_EXPERT_SLICEABLE,
    IndexedQuantizedRepresentation,
    PackedExpertQuantizationRequest,
    build_packed_expert_quantization_plan,
)
from tools.quantization.aura_glm53_quantized_representation_trial import (
    IndependentVerification,
    QuantizedTrialRequest,
    RepresentationIdentity,
    TrialSample,
)
from tools.quantization.aura_glm53_plan_conforming_quantized_trial import (
    Q2_EXACT_HEAD,
    Q2_EXACT_RUN,
    Q3_EXACT_HEAD,
    Q3_EXACT_RUN,
    bind_plan_conforming_quantized_trial,
    build_plan_bound_candidate_representation,
    plan_bound_candidate_identity,
)

H = "a" * 64
TASKS = "b" * 64
CRITERIA = "c" * 64
HOST = "d" * 64
BASE_REP = "e" * 64
OUT_BASE = "3" * 64
OUT_CAND = "4" * 64
IMPL_A = "1" * 64
IMPL_B = "2" * 64


def q2_representations():
    a = IndexedQuantizedRepresentation(
        representation_id="E8_A",
        vector_dim=8,
        index_bits_per_vector=18,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=PER_EXPERT_SLICEABLE,
        companion_bytes_per_expert=64,
    )
    b = IndexedQuantizedRepresentation(
        representation_id="E8_B",
        vector_dim=8,
        index_bits_per_vector=22,
        scale_group_weights=64,
        scale_bits_per_group=16,
        companion_layout=PER_EXPERT_SLICEABLE,
        companion_bytes_per_expert=64,
    )
    return {a.representation_id: a, b.representation_id: b}


def q2_request(*, assignments=("E8_A", "E8_A", "E8_B", "E8_A"), lifecycle="BACKGROUND"):
    return PackedExpertQuantizationRequest(
        num_experts=4,
        parameters_per_expert=1_000,
        expert_representation_ids=assignments,
        selected_expert_ids=(1, 2),
        cache_budget_bytes=10_000,
        bank_resident_companion_cap_bytes=0,
        lifecycle_mode=lifecycle,
    )


def prepared(*, assignments=("E8_A", "E8_A", "E8_B", "E8_A"), lifecycle="BACKGROUND"):
    reps = q2_representations()
    preq = q2_request(assignments=assignments, lifecycle=lifecycle)
    plan = build_packed_expert_quantization_plan(request=preq, representations=reps)
    manifest, candidate = plan_bound_candidate_identity(
        plan=plan,
        model_revision="glm53-r1",
        topology_digest=H,
        representation_revision="mixed-e8-r1",
        implementation_digests_by_representation_id={"E8_A": IMPL_A, "E8_B": IMPL_B},
        nominal_bits_per_weight=2.5,
        static_weight_bytes=5_000,
    )
    baseline = RepresentationIdentity("glm53-r1", H, "fp8-r1", BASE_REP, 8.0, 20_000, False)
    trial = QuantizedTrialRequest(TASKS, CRITERIA, HOST, "MEDIUM", "SINGLE", lifecycle, baseline, candidate)
    return reps, preq, plan, manifest, trial


def sample(trial, *, candidate: bool, passed=6, wall=100.0, ram=100, vram=100, rep_digest=None):
    identity = trial.candidate if candidate else trial.baseline
    return TrialSample(
        request_digest=trial.request_digest,
        representation_digest=identity.representation_digest if rep_digest is None else rep_digest,
        route_id="LOCAL_QUANT" if candidate else "LOCAL_FP8",
        task_count=6,
        tasks_passed=passed,
        tasks_failed=6 - passed,
        incorrect_edits=0,
        hallucinated_apis=0,
        source_currentness_violations=0,
        repair_loops=0,
        wall_seconds=wall,
        ttft_seconds=1.0,
        generation_tokens_per_second=10.0,
        bytes_read=1_000,
        peak_ram_bytes=ram,
        peak_vram_bytes=vram,
        output_set_digest=OUT_CAND if candidate else OUT_BASE,
    )


def verification(trial, cand, *, producer="agent-a", verifier="agent-b"):
    return IndependentVerification(
        request_digest=trial.request_digest,
        candidate_sample_digest=cand.sample_digest,
        producer_identity=producer,
        verifier_identity=verifier,
        reproduced_task_count=6,
        reproduced_tasks_passed=cand.tasks_passed,
        acceptance_criteria_reproduced=True,
    )


def bind_fixture(**overrides):
    reps, preq, plan, manifest, trial = prepared()
    base = sample(trial, candidate=False, wall=120, ram=200, vram=200)
    cand = sample(trial, candidate=True, wall=90, ram=100, vram=100)
    kwargs = dict(
        plan_request=preq,
        representations=reps,
        candidate_manifest=manifest,
        trial_request=trial,
        baseline_sample=base,
        candidate_sample=cand,
        independent_verification=verification(trial, cand),
    )
    kwargs.update(overrides)
    return bind_plan_conforming_quantized_trial(**kwargs)


class PlanConformingQuantizedTrialTests(unittest.TestCase):
    def test_happy_path_binds_q3_sample_to_exact_q2_plan_identity(self):
        out = bind_fixture()
        self.assertTrue(out.plan_bound_candidate_identity_admitted)
        self.assertTrue(out.exact_trial_sample_bound_to_plan_identity)
        self.assertTrue(out.candidate_quality_retained_on_frozen_corpus)
        self.assertTrue(out.independent_acceptance_reproduced)
        self.assertEqual(out.exact_parent_heads, (Q2_EXACT_HEAD, Q3_EXACT_HEAD))
        self.assertEqual(out.exact_parent_runs, (Q2_EXACT_RUN, Q3_EXACT_RUN))
        self.assertEqual(len(out.receipt_digest), 64)

    def test_plan_assignment_change_invalidates_old_candidate_manifest(self):
        reps, _, _, manifest, trial = prepared()
        changed = q2_request(assignments=("E8_A", "E8_B", "E8_B", "E8_A"))
        base = sample(trial, candidate=False)
        cand = sample(trial, candidate=True)
        with self.assertRaisesRegex(ValueError, "MANIFEST_PLAN_DIGEST_MISMATCH|MANIFEST_LAYOUT_PROJECTION_MISMATCH|MANIFEST_ASSIGNMENT_DIGEST_MISMATCH"):
            bind_plan_conforming_quantized_trial(
                plan_request=changed,
                representations=reps,
                candidate_manifest=manifest,
                trial_request=trial,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=verification(trial, cand),
            )

    def test_implementation_digest_change_changes_candidate_representation_digest(self):
        reps, preq, plan, manifest, _ = prepared()
        changed = build_plan_bound_candidate_representation(
            plan=plan,
            representation_revision="mixed-e8-r1",
            implementation_digests_by_representation_id={"E8_A": "5" * 64, "E8_B": IMPL_B},
        )
        self.assertNotEqual(manifest.representation_digest, changed.representation_digest)

    def test_missing_or_extra_representation_binding_fails_closed(self):
        _, _, plan, _, _ = prepared()
        with self.assertRaisesRegex(ValueError, "REPRESENTATION_BINDING_SET_MISMATCH"):
            build_plan_bound_candidate_representation(
                plan=plan,
                representation_revision="r",
                implementation_digests_by_representation_id={"E8_A": IMPL_A},
            )
        with self.assertRaisesRegex(ValueError, "REPRESENTATION_BINDING_SET_MISMATCH"):
            build_plan_bound_candidate_representation(
                plan=plan,
                representation_revision="r",
                implementation_digests_by_representation_id={"E8_A": IMPL_A, "E8_B": IMPL_B, "FOREIGN": "6" * 64},
            )

    def test_trial_candidate_digest_must_equal_plan_bound_manifest(self):
        reps, preq, _, manifest, trial = prepared()
        foreign_candidate = RepresentationIdentity(
            trial.candidate.model_revision,
            trial.candidate.topology_digest,
            trial.candidate.representation_revision,
            "6" * 64,
            trial.candidate.nominal_bits_per_weight,
            trial.candidate.static_weight_bytes,
            True,
        )
        bad_trial = QuantizedTrialRequest(TASKS, CRITERIA, HOST, "MEDIUM", "SINGLE", "BACKGROUND", trial.baseline, foreign_candidate)
        base = sample(bad_trial, candidate=False)
        cand = sample(bad_trial, candidate=True)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_DIGEST_NOT_PLAN_BOUND"):
            bind_plan_conforming_quantized_trial(
                plan_request=preq,
                representations=reps,
                candidate_manifest=manifest,
                trial_request=bad_trial,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=verification(bad_trial, cand),
            )

    def test_plan_and_trial_lifecycle_must_match(self):
        reps, preq, plan, manifest, trial = prepared(lifecycle="BACKGROUND")
        mismatch = QuantizedTrialRequest(TASKS, CRITERIA, HOST, "MEDIUM", "SINGLE", "INTERACTIVE", trial.baseline, trial.candidate)
        base = sample(mismatch, candidate=False)
        cand = sample(mismatch, candidate=True)
        with self.assertRaisesRegex(ValueError, "PLAN_TRIAL_LIFECYCLE_MISMATCH"):
            bind_plan_conforming_quantized_trial(
                plan_request=preq,
                representations=reps,
                candidate_manifest=manifest,
                trial_request=mismatch,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=verification(mismatch, cand),
            )

    def test_q3_sample_and_verifier_binding_remain_enforced(self):
        reps, preq, _, manifest, trial = prepared()
        base = sample(trial, candidate=False)
        cand = sample(trial, candidate=True)
        bad_verification = IndependentVerification(trial.request_digest, "7" * 64, "a", "b", 6, 6, True)
        with self.assertRaisesRegex(ValueError, "VERIFIER_SAMPLE_BINDING_MISMATCH"):
            bind_plan_conforming_quantized_trial(
                plan_request=preq,
                representations=reps,
                candidate_manifest=manifest,
                trial_request=trial,
                baseline_sample=base,
                candidate_sample=cand,
                independent_verification=bad_verification,
            )

    def test_q2_unbounded_companion_still_fails_before_trial_admission(self):
        from tools.quantization.aura_glm53_packed_expert_quantization_plan import BANK_ONLY_UNBOUNDED
        reps = q2_representations()
        bad = IndexedQuantizedRepresentation("BAD", 8, 18, 64, 16, BANK_ONLY_UNBOUNDED)
        reps["BAD"] = bad
        preq = q2_request(assignments=("BAD", "BAD", "BAD", "BAD"))
        with self.assertRaisesRegex(ValueError, "UNSLICEABLE_COMPANION_LAYOUT"):
            build_packed_expert_quantization_plan(request=preq, representations=reps)

    def test_successful_identity_join_does_not_promote_execution_or_authority(self):
        out = bind_fixture()
        for name in (
            "whole_model_static_bytes_derived_from_routed_expert_plan",
            "planned_layout_executed_proven",
            "selected_experts_actually_served_proven",
            "companion_layout_actually_loaded_proven",
            "implementation_bytes_authenticated",
            "physical_io_attributed_exclusively",
            "exact_causal_timing_comparison_claimed",
            "general_performance_winner_proven",
            "coding_quality_generalized_beyond_frozen_corpus",
            "owner_host_identity_authenticated",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
            "gate10_ready_for_owner_promotion",
            "deployment_authorized",
        ):
            self.assertFalse(getattr(out, name), name)


if __name__ == "__main__":
    unittest.main()
