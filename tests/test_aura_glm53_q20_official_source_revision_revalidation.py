#!/usr/bin/env python3
from dataclasses import replace
import unittest

from tools.quantization.aura_glm53_q20_official_source_revision_revalidation import (
    CANDIDATE, CURRENT_K27_B3MOD27_XYZ, CURRENT_SOURCE_URL, OBSERVED_CHANGED_PATHS,
    PINNED_K27_B3MOD27_XYZ, PINNED_SOURCE_URL, assess_official_source_revision,
    current_q18_projection, decision_table, decision_tree, is_metadata_only_path,
    k27_b3mod27_xyz, observed_current_source_fixture, prove_64_state_lattice,
)


class Q20OfficialSourceRevisionRevalidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.q18 = current_q18_projection()
        self.obs = observed_current_source_fixture()

    def test_exact_current_observation_yields_nonpromoting_candidate(self) -> None:
        out = assess_official_source_revision(q18=self.q18, observation=self.obs)
        self.assertEqual(out["disposition"], CANDIDATE)
        self.assertTrue(out["repository_revision_changed"])
        self.assertTrue(out["tracked_model_payload_generation_unchanged_across_observed_diff"])
        self.assertFalse(out["tracked_model_payload_or_config_path_changed"])
        self.assertTrue(out["gate10_source_binding_candidate"])
        self.assertFalse(out["source_currentness_at_future_effect_proven"])
        self.assertFalse(out["tensor_payload_bound"])
        self.assertFalse(out["model_execution_observed"])
        self.assertFalse(out["gate10_promoted"])

    def test_current_and_pinned_k27_coordinates_are_deterministic_and_non_authoritative(self) -> None:
        self.assertEqual(k27_b3mod27_xyz(PINNED_SOURCE_URL), PINNED_K27_B3MOD27_XYZ)
        self.assertEqual(k27_b3mod27_xyz(CURRENT_SOURCE_URL), CURRENT_K27_B3MOD27_XYZ)
        out = assess_official_source_revision(q18=self.q18, observation=self.obs)
        self.assertFalse(out["k27_used_for_version_selection"])
        self.assertTrue(out["version_selected_before_k27_navigation"])
        self.assertFalse(out["semantic_k27_authority_minted"])

    def test_q18_generation_or_receipt_substitution_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Q18_EXACT_GREEN_PROJECTION_MISMATCH"):
            assess_official_source_revision(
                q18=replace(self.q18, receipt_digest="0" * 64), observation=self.obs
            )
        with self.assertRaisesRegex(ValueError, "Q18_EXACT_GREEN_PROJECTION_MISMATCH"):
            assess_official_source_revision(
                q18=replace(self.q18, disposition="FORGED_ELIGIBLE"), observation=self.obs
            )

    def test_provider_head_advance_requires_reopen(self) -> None:
        with self.assertRaisesRegex(ValueError, "OBSERVED_HEAD_REVISION_REOPEN_REQUIRED"):
            assess_official_source_revision(
                q18=self.q18,
                observation=replace(
                    self.obs,
                    observed_head_revision="a" * 40,
                    ancestry_chain=self.obs.ancestry_chain[:-1] + ("a" * 40,),
                ),
            )

    def test_ancestry_chain_substitution_fails_closed(self) -> None:
        broken = list(self.obs.ancestry_chain)
        broken[2], broken[3] = broken[3], broken[2]
        with self.assertRaisesRegex(ValueError, "EXACT_ANCESTRY_CHAIN_MISMATCH"):
            assess_official_source_revision(
                q18=self.q18, observation=replace(self.obs, ancestry_chain=tuple(broken))
            )

    def test_model_config_or_payload_path_change_cannot_be_laundered_as_metadata(self) -> None:
        self.assertFalse(is_metadata_only_path("config.json"))
        self.assertFalse(is_metadata_only_path("model-00001-of-00141.safetensors"))
        self.assertFalse(is_metadata_only_path("model.safetensors.index.json"))
        state = dict(
            q18_eligible=True, repository_exact=True, pinned_revision_exact=True,
            current_head_exact=True, ancestry_proven=True,
            model_relevant_paths_unchanged=False,
        )
        self.assertEqual(decision_tree(**state), "HOLD_MODEL_RELEVANT_SOURCE_CHANGE")
        self.assertEqual(decision_table(**state), "HOLD_MODEL_RELEVANT_SOURCE_CHANGE")

    def test_only_exact_observed_metadata_path_set_is_accepted(self) -> None:
        self.assertTrue(all(is_metadata_only_path(path) for path in OBSERVED_CHANGED_PATHS))
        with self.assertRaisesRegex(ValueError, "OBSERVED_CHANGED_PATH_SET_MISMATCH"):
            assess_official_source_revision(
                q18=self.q18,
                observation=replace(self.obs, changed_paths=OBSERVED_CHANGED_PATHS + ("config.json",)),
            )

    def test_repository_and_pinned_revision_identity_are_exact(self) -> None:
        with self.assertRaisesRegex(ValueError, "OFFICIAL_REPOSITORY_MISMATCH"):
            assess_official_source_revision(
                q18=self.q18, observation=replace(self.obs, repository="lookalike/GLM-5.3")
            )
        with self.assertRaisesRegex(ValueError, "PINNED_REVISION_MISMATCH"):
            assess_official_source_revision(
                q18=self.q18, observation=replace(self.obs, pinned_revision="b" * 40)
            )

    def test_receipt_is_deterministic(self) -> None:
        a = assess_official_source_revision(q18=self.q18, observation=self.obs)
        b = assess_official_source_revision(q18=self.q18, observation=self.obs)
        self.assertEqual(a["receipt_digest"], b["receipt_digest"])

    def test_complete_64_state_different_j_lattice(self) -> None:
        counts = prove_64_state_lattice()
        self.assertEqual(sum(counts.values()), 64)
        self.assertEqual(counts[CANDIDATE], 1)
        self.assertEqual(counts["HOLD_Q18_NOT_ELIGIBLE"], 32)


if __name__ == "__main__":
    unittest.main()
