import copy
import inspect
import unittest
from unittest.mock import patch

from tools.awj032 import glm53_pr340_registry_bound_mtp_appraiser as m
from tools.awj032 import glm53_official_mtp_role_source_appraiser as appraiser


class PR340RegistryBoundMTPAdmissionTests(unittest.TestCase):
    def report(self):
        report = {
            "schema": "GLM53CheckpointLayoutProbeV1",
            "status": "PARTIAL",
            "blockers": [appraiser.PROVENANCE_BLOCKER],
            "source_binding_proven": True,
            "model_revision": "model-revision",
            "index_sha256": "i" * 64,
            "num_hidden_layers": 78,
            "source_bundle_id": "s" * 64,
            "config_parsed_sha256": "c" * 64,
            "index_parsed_sha256": "p" * 64,
            "weight_map_digest": "w" * 64,
            "extra_checkpoint_layer_indices": [78],
            "classified_extra_checkpoint_layers": [
                {"index": 78, "role": "MTP_NON_DECODER", "decoder_pager_membership": False}
            ],
            "unclassified_extra_checkpoint_layer_indices": [],
            "extra_layer_resolver_provenance_proven": False,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
            "provider_calls": 0,
            "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
            "observation_time": "t1",
        }
        report["logical_id"] = appraiser._pr340_classification_stage_logical_id(report)
        return report

    def pin_for(self, report):
        return {
            "PINNED_CLASSIFICATION_STAGE_LOGICAL_ID": report["logical_id"],
            "PINNED_FINAL_REPORT_DIGEST": m.final_source_bound_report_digest(report),
            "PINNED_SOURCE_BUNDLE_ID": report["source_bundle_id"],
            "PINNED_MODEL_REVISION": report["model_revision"],
            "PINNED_INDEX_SHA256": report["index_sha256"],
            "PINNED_BLOCKER_SET": tuple(report["blockers"]),
        }

    def pin_context(self, report):
        patches = [patch.object(m, name, value) for name, value in self.pin_for(report).items()]
        class Context:
            def __enter__(self_nonlocal):
                for item in patches:
                    item.start()
                return self_nonlocal
            def __exit__(self_nonlocal, exc_type, exc, tb):
                for item in reversed(patches):
                    item.stop()
        return Context()

    def test_registry_pin_accepts_exact_final_report(self):
        report = self.report()
        with self.pin_context(report):
            receipt = m.verify_pr340_against_registry(report)
        self.assertTrue(receipt.producer_registry_verified)
        self.assertEqual(m.final_source_bound_report_digest(report), receipt.final_report_digest)
        self.assertFalse(receipt.runtime_execution_proven)
        self.assertFalse(receipt.g2_admitted)
        self.assertFalse(receipt.authority)

    def test_source_bound_field_mutation_is_caught_even_if_legacy_logical_id_is_unchanged(self):
        legitimate = self.report()
        forged = copy.deepcopy(legitimate)
        forged["weight_map_digest"] = "x" * 64
        self.assertEqual(
            appraiser._pr340_classification_stage_logical_id(forged),
            legitimate["logical_id"],
        )
        with self.pin_context(legitimate):
            with self.assertRaisesRegex(
                m.RegistryBoundMTPAdmissionError,
                "PR340_REGISTRY_FINAL_REPORT_DIGEST_MISMATCH",
            ):
                m.verify_pr340_against_registry(forged)

    def test_observation_time_is_not_part_of_final_report_identity(self):
        first = self.report()
        second = copy.deepcopy(first)
        second["observation_time"] = "later"
        self.assertEqual(
            m.final_source_bound_report_digest(first),
            m.final_source_bound_report_digest(second),
        )

    def test_recomputed_classification_id_still_cannot_replace_registry_final_digest(self):
        legitimate = self.report()
        forged = copy.deepcopy(legitimate)
        forged["blockers"] = [appraiser.PROVENANCE_BLOCKER, "OTHER_BLOCKER"]
        forged["logical_id"] = appraiser._pr340_classification_stage_logical_id(forged)
        with self.pin_context(legitimate):
            with self.assertRaises(m.RegistryBoundMTPAdmissionError):
                m.verify_pr340_against_registry(forged)

    def test_successor_public_api_has_no_caller_expected_identity_parameters(self):
        params = inspect.signature(
            m.verify_and_admit_registry_bound_official_mtp_role
        ).parameters
        self.assertNotIn("expected_pr340_logical_id", params)
        self.assertNotIn("expected_pr340_semantic_generation", params)
        self.assertFalse(m.public_interface_has_caller_expected_identity())

    def test_caller_cannot_supply_expected_identity_to_successor_api(self):
        with self.assertRaises(TypeError):
            m.verify_and_admit_registry_bound_official_mtp_role(
                self.report(),
                expected_pr340_logical_id="0" * 64,
            )

    def test_successor_passes_only_code_owned_lineage_to_pr409_compatibility_layer(self):
        report = self.report()
        evidence = object()
        admitted = {
            **report,
            "logical_id": "a" * 64,
            "extra_layer_resolver_provenance_proven": True,
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
        }
        captured = {}

        def fake_apply(in_report, in_evidence, **kwargs):
            captured.update(kwargs)
            self.assertIs(in_report, report)
            self.assertIs(in_evidence, evidence)
            return admitted

        with self.pin_context(report), \
             patch.object(appraiser, "observe_official_mtp_role", return_value=evidence), \
             patch.object(appraiser, "_apply_verified_source_role", side_effect=fake_apply):
            out = m.verify_and_admit_registry_bound_official_mtp_role(report)

        self.assertEqual(
            m.PINNED_CLASSIFICATION_STAGE_LOGICAL_ID,
            captured["expected_pr340_logical_id"],
        )
        self.assertEqual(
            m.PINNED_PRODUCER_BASE_HEAD,
            captured["expected_pr340_semantic_generation"],
        )
        self.assertTrue(out["pr340_producer_registry_verified"])
        self.assertEqual(m.REGISTRY_RECEIPT_REF, out["pr340_producer_registry_receipt_ref"])
        self.assertFalse(out["g2_admitted"])
        self.assertFalse(out["runtime_execution_proven"])

    def test_pinned_production_constants_match_independent_arena_registry_receipt(self):
        self.assertEqual(
            "d7ff1b34d091a92449d59c0cb561bc5a87724c67ab9bdb7504a5b38f5c3dfaa9",
            m.PINNED_FINAL_REPORT_DIGEST,
        )
        self.assertEqual(
            "e4f187dce49c3711d4c1a388107b190aed6ad5a99508d85c163238f4a8f1c851",
            m.PINNED_SNAPSHOT_DIGEST,
        )
        self.assertEqual(
            "d03c28d13e4c7c99f49d611c29c24bc9b509158c8a0b84883f584f0c09c43aaa",
            m.PINNED_CLASSIFICATION_STAGE_LOGICAL_ID,
        )
        self.assertEqual(
            "a120b0be445990a95476f2286bb75036039da7bb",
            m.PINNED_PRODUCER_EXECUTION_HEAD,
        )


if __name__ == "__main__":
    unittest.main()
