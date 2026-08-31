from __future__ import annotations

import copy
import inspect
import unittest

from scripts.aura_k27_optics_import_currentness_domain import (
    CROSS_DOMAIN_REJECTION,
    DISPLAY_DEPLOYMENT_CURRENTNESS_CONTEXT,
    EVIDENCE_TYPE,
    CURRENTNESS_DOMAIN,
    IMPORT_CURRENTNESS_CONTEXT,
    IMPORTED_SOURCE_SHA256,
    MEASURED_OPTICAL_SYSTEM_CURRENTNESS_CONTEXT,
    project_k27_optics_import_currentness,
)
from scripts.aura_provenance_corroboration_memory_admission import (
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.k27_optics_candidate_falsifier import verify_import_receipt


class K27OpticsImportCurrentnessDomainTests(unittest.TestCase):
    def test_exact_source_bound_reference_is_current_only_in_owned_import_generation(self):
        out = project_k27_optics_import_currentness()
        node = out["evidence_node"]
        ref = node["artifact_ref"]
        self.assertEqual(IMPORTED_SOURCE_SHA256, out["imported_source_sha256"])
        self.assertTrue(verify_import_receipt(out["import_receipt"]))
        self.assertEqual(EVIDENCE_TYPE, node["evidence_type"])
        self.assertEqual(CURRENTNESS_DOMAIN, node["currentness_domain"])
        self.assertTrue(node["current"])
        self.assertEqual([ref], out["retrieval_admission"]["eligible_artifact_refs"])
        self.assertEqual([ref], out["optics_import_currentness_admission"]["eligible_artifact_refs"])
        self.assertTrue(out["optics_import_current_in_generation"])

    def test_measured_optics_and_deployment_currentness_fail_three_axis_closed(self):
        out = project_k27_optics_import_currentness()
        ref = out["evidence_node"]["artifact_ref"]
        for key in (
            "measured_optical_system_currentness_admission",
            "display_deployment_currentness_admission",
        ):
            admission = out[key]
            self.assertEqual([], admission["eligible_artifact_refs"])
            self.assertEqual(CROSS_DOMAIN_REJECTION, admission["excluded_by_artifact_ref"][ref])
        self.assertFalse(out["measured_optical_system_currentness_proven"])
        self.assertFalse(out["display_deployment_currentness_proven"])

    def test_stale_reference_fails_even_in_owned_import_domain(self):
        out = project_k27_optics_import_currentness()
        stale = copy.deepcopy(out["evidence_node"])
        stale.pop("receipt_identity")
        stale["current"] = False
        stale = seal_evidence_node(stale)
        probe = admit_evidence_nodes([stale], IMPORT_CURRENTNESS_CONTEXT)
        self.assertEqual([], probe["eligible_artifact_refs"])
        self.assertEqual(["NOT_CURRENT"], probe["excluded_by_artifact_ref"][stale["artifact_ref"]])

    def test_optics_reference_cannot_be_retyped_by_context_selection(self):
        out = project_k27_optics_import_currentness()
        node = out["evidence_node"]
        measured = admit_evidence_nodes([node], MEASURED_OPTICAL_SYSTEM_CURRENTNESS_CONTEXT)
        deployment = admit_evidence_nodes([node], DISPLAY_DEPLOYMENT_CURRENTNESS_CONTEXT)
        self.assertEqual([], measured["eligible_artifact_refs"])
        self.assertEqual([], deployment["eligible_artifact_refs"])

    def test_pr607_negative_ceiling_survives_memory_projection(self):
        out = project_k27_optics_import_currentness()
        self.assertTrue(out["import_receipt"]["claim_ceiling"])
        self.assertTrue(all(value is False for value in out["import_receipt"]["claim_ceiling"].values()))
        for key in (
            "measured_optical_system_currentness_proven",
            "display_deployment_currentness_proven",
            "calibrated_eye_pose_currentness_proven",
            "eye_pose_calibration_owned_by_this_module",
            "optical_energy_conservation_proven",
            "speckle_free_proven",
            "zero_light_leakage_proven",
            "metric_eye_pose_proven",
            "exact_scene_unbinding_proven",
            "varifocal_correctness_proven",
            "hardware_latency_proven",
            "display_safety_proven",
            "deployment_ready",
            "producer_authenticated",
            "semantic_truth_proven",
            "effect_authority_proven",
            "semantic_k27_authority_minted",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
        ):
            self.assertFalse(out[key], key)

    def test_memory_artifact_identity_is_exact_import_receipt_digest(self):
        out = project_k27_optics_import_currentness()
        digest = out["import_receipt"]["receipt_sha256"]
        self.assertEqual("k27-optics-import-sha256:" + digest, out["evidence_node"]["artifact_ref"])
        self.assertEqual(digest, out["evidence_node"]["artifact_ref_value"])
        self.assertEqual(
            "k27-optics-source-sha256:" + IMPORTED_SOURCE_SHA256,
            out["evidence_node"]["world_ref"],
        )

    def test_public_projection_accepts_no_caller_selected_source_type_domain_or_authority(self):
        self.assertEqual([], list(inspect.signature(project_k27_optics_import_currentness).parameters))

    def test_projection_is_deterministic(self):
        self.assertEqual(project_k27_optics_import_currentness(), project_k27_optics_import_currentness())


if __name__ == "__main__":
    unittest.main()
