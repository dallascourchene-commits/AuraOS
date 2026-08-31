from dataclasses import replace
import unittest

from tools.quantization.aura_glm53_official_source_admission import (
    OFFICIAL_COMMIT,
    current_public_state,
)
from tools.quantization.aura_glm53_official_source_trial_bridge import (
    VERSION,
    classify_official_source_trial,
)
from tools.quantization.aura_glm53_quantized_representation_trial import (
    FULL_MODEL_STATIC,
    QuantizedRepresentationComparison,
    QuantizedTrialRequest,
    RepresentationIdentity,
)

H = "a" * 64
B = "b" * 64
C = "c" * 64
D = "d" * 64


def request(model_revision: str = OFFICIAL_COMMIT) -> QuantizedTrialRequest:
    baseline = RepresentationIdentity(
        model_revision, H, "official-fp8-r1", B, 8.0, 1000,
        FULL_MODEL_STATIC, D, False,
    )
    candidate = RepresentationIdentity(
        model_revision, H, "candidate-lowbit-r1", C, 2.25, 300,
        FULL_MODEL_STATIC, D, True,
    )
    return QuantizedTrialRequest(
        task_corpus_digest="1" * 64,
        acceptance_criteria_digest="2" * 64,
        host_profile_digest="3" * 64,
        context_tier="MEDIUM",
        batch_tier="SINGLE",
        lifecycle_mode="INTERACTIVE",
        baseline=baseline,
        candidate=candidate,
    )


def comparison(req: QuantizedTrialRequest) -> QuantizedRepresentationComparison:
    return QuantizedRepresentationComparison(
        version="AURA_GLM53_QUANTIZED_REPRESENTATION_TRIAL_V2",
        parent_artifact_ids=("benchmark", "placement"),
        request_digest=req.request_digest,
        baseline_sample_digest="4" * 64,
        candidate_sample_digest="5" * 64,
        independent_verifier_identity="different-j-verifier",
        static_weight_byte_domain=req.baseline.static_weight_byte_domain,
        static_weight_byte_domain_digest=req.baseline.static_weight_byte_domain_digest,
        quality_pass_delta=0,
        candidate_quality_retained_on_frozen_corpus=True,
        independent_acceptance_reproduced=True,
        candidate_smaller_static_weights=True,
        candidate_faster_wall_time=True,
        candidate_lower_peak_memory=True,
        candidate_tradeoff_class="FROZEN_CORPUS_CANDIDATE_DOMINATES_MEASURED_AXES",
        exact_causal_timing_comparison_claimed=False,
        general_performance_winner_proven=False,
        coding_quality_generalized_beyond_frozen_corpus=False,
        owner_host_identity_authenticated=False,
        physical_io_attributed_exclusively=False,
        gate10_ready_for_owner_promotion=False,
        native_private_transformer_kv_accessed=False,
        semantic_k27_authority_minted=False,
        deployment_authorized=False,
    )


class OfficialSourceTrialBridgeTests(unittest.TestCase):
    def test_current_official_source_state_holds_even_for_exact_revision_and_trial_domain(self):
        req = request()
        out = classify_official_source_trial(
            source_state=current_public_state(), request=req, comparison=comparison(req)
        )
        self.assertEqual(out.schema, VERSION)
        self.assertTrue(out.model_revision_matches_official_source)
        self.assertTrue(out.trial_internal_byte_domain_bound)
        self.assertFalse(out.official_source_headers_trial_eligible)
        self.assertFalse(out.official_source_byte_domain_bound_to_trial)
        self.assertFalse(out.candidate_materialization_owner_bound)
        self.assertFalse(out.official_source_trial_admissible)
        self.assertEqual(out.disposition, "HOLD_OFFICIAL_INDEX_HEADER_EVIDENCE")

    def test_exact_model_revision_label_is_not_official_source_provenance(self):
        req = request()
        out = classify_official_source_trial(
            source_state=current_public_state(), request=req, comparison=comparison(req)
        )
        self.assertTrue(out.model_revision_matches_official_source)
        self.assertFalse(out.official_source_trial_admissible)

    def test_even_future_source_ready_state_cannot_self_mint_cross_domain_relation(self):
        ready = replace(
            current_public_state(),
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            header_trial_eligible=True,
            source_tensor_payload_bound=True,
            real_tensor_quantization_eligible=True,
            blocker="",
        )
        req = request()
        out = classify_official_source_trial(
            source_state=ready, request=req, comparison=comparison(req)
        )
        self.assertFalse(out.official_source_byte_domain_bound_to_trial)
        self.assertFalse(out.candidate_materialization_owner_bound)
        self.assertFalse(out.official_source_trial_admissible)
        self.assertEqual(out.disposition, "HOLD_OFFICIAL_SOURCE_TO_TRIAL_BYTE_DOMAIN_RELATION")

    def test_inconsistent_source_admission_boolean_cannot_bypass_prerequisites(self):
        forged = replace(current_public_state(), header_trial_eligible=True)
        req = request()
        with self.assertRaisesRegex(ValueError, "HEADER_ELIGIBILITY_PREREQUISITE_MISMATCH"):
            classify_official_source_trial(
                source_state=forged, request=req, comparison=comparison(req)
            )

    def test_foreign_model_revision_is_not_official_source_trial(self):
        req = request("foreign-revision")
        out = classify_official_source_trial(
            source_state=current_public_state(), request=req, comparison=comparison(req)
        )
        self.assertFalse(out.model_revision_matches_official_source)
        self.assertEqual(out.disposition, "HOLD_MODEL_REVISION_NOT_OFFICIAL_SOURCE")
        self.assertFalse(out.official_source_trial_admissible)

    def test_trial_domain_manifest_substitution_fails_closed(self):
        req = request()
        bad = replace(comparison(req), static_weight_byte_domain_digest="e" * 64)
        with self.assertRaisesRegex(ValueError, "TRIAL_BYTE_DOMAIN_MANIFEST_MISMATCH"):
            classify_official_source_trial(
                source_state=current_public_state(), request=req, comparison=bad
            )

    def test_bridge_never_promotes_unearned_authority_planes(self):
        req = request()
        out = classify_official_source_trial(
            source_state=current_public_state(), request=req, comparison=comparison(req)
        )
        for field in (
            "generalized_quality_proven", "runtime_performance_proven",
            "owner_host_authenticated", "physical_io_proven",
            "semantic_k27_authority", "native_private_transformer_kv_accessed",
            "gate10_promoted", "deployment_authorized",
        ):
            self.assertFalse(getattr(out, field), field)


if __name__ == "__main__":
    unittest.main()
