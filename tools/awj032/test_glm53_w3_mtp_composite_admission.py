import copy
import unittest

from tools.awj032.glm53_official_w2_observation import OFFICIAL_W2_OBSERVATION
from tools.awj032.glm53_w3_mtp_composite_admission import (
    OFFICIAL_SOURCE_EVIDENCE_ID,
    PR409_VERIFIED_HEAD,
    PR410_PARENT_HEAD,
    W3CompositeAdmissionError,
    compose_w3_mtp_admission,
)
from tools.awj032.glm53_w3_official_producer_admission import (
    CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
    CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
)


class W3MTPCompositeAdmissionTests(unittest.TestCase):
    def w3_receipt(self):
        o = OFFICIAL_W2_OBSERVATION
        return {
            "schema": "AWJ032GLM53W3OfficialProducerAdmissionV1",
            "status": "BLOCKED",
            "blockers": ["GLM53_MTP_RESOLVER_PROVENANCE_REQUIRED"],
            "official_w2_bound_plan_digest": "a" * 64,
            "inner_source_plan_digest": "b" * 64,
            "official_w2_observation_digest": o.observation_digest,
            "official_w2_receipt_digest": o.receipt_digest,
            "official_w2_producer_semantic_head": o.producer_semantic_head,
            "official_w2_producer_run_ref": o.producer_run_ref,
            "official_w2_drive_observation_ref": o.drive_observation_ref,
            "representative_layer": o.layer,
            "representative_expert": o.expert,
            "airllm_security_semantic_head": CURRENT_AIRLLM_SECURITY_SEMANTIC_HEAD,
            "glm53_metadata_semantic_head": CURRENT_GLM53_METADATA_SEMANTIC_HEAD,
            "official_w2_producer_proof_consumed": True,
            "synthetic_tiny_fixture_admitted": False,
            "g2_admitted": False,
            "runtime_execution_admitted": False,
            "checkpoint_payload_admitted": False,
            "provider_effect_admitted": False,
            "authority": False,
        }

    def mtp_evidence(self):
        return {
            "owner_repo": "zai-org/GLM-5.3",
            "immutable_model_revision": "7cda81930d6e4cef42f48555de830aa32ecdde28",
            "config_raw_sha256": "3ac72612095574542f7fff847ada8e59d9199dd8af44bdf625d7e02615572e69",
            "config_parsed_sha256": "d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40",
            "index_sha256": "e0fe7f28c1f853d4824e4d796374e3dacf1fe470988773952c79b063768134bf",
            "index_parsed_sha256": "08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c",
            "weight_map_digest": "f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7",
            "source_bundle_id": "7821aa7406174e1ce1c88a8b7280c4ba797508a6eaeecebc4670af2a8de0fc8b",
            "num_hidden_layers": 78,
            "num_nextn_predict_layers": 1,
            "observed_extra_checkpoint_layer_indices": [78],
            "mtp_marker_keys": ["model.layers.78.eh_proj.weight"],
            "role_index": 78,
            "role": "MTP_NON_DECODER",
            "decoder_pager_membership": False,
            "source_verified": True,
            "payload_bytes_read": 0,
            "g2_admitted": False,
            "runtime_executed": False,
            "authority": False,
            "schema": "OfficialSourceMTPRoleEvidenceV1",
        }

    def mtp_report(self):
        e = self.mtp_evidence()
        return {
            "schema": "GLM53CheckpointLayoutProbeV1",
            "model_revision": e["immutable_model_revision"],
            "index_sha256": e["index_sha256"],
            "num_hidden_layers": e["num_hidden_layers"],
            "source_binding_proven": True,
            "source_bundle_id": e["source_bundle_id"],
            "config_parsed_sha256": e["config_parsed_sha256"],
            "index_parsed_sha256": e["index_parsed_sha256"],
            "weight_map_digest": e["weight_map_digest"],
            "extra_checkpoint_layer_indices": [78],
            "unexpected_extra_checkpoint_layer_indices": [78],
            "classified_extra_checkpoint_layers": [
                {"index": 78, "role": "MTP_NON_DECODER", "decoder_pager_membership": False}
            ],
            "unclassified_extra_checkpoint_layer_indices": [],
            "extra_layer_resolver_provenance_proven": True,
            "extra_layer_resolver_provenance_method": "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION",
            "official_mtp_role_source_evidence": e,
            "official_mtp_role_source_evidence_id": OFFICIAL_SOURCE_EVIDENCE_ID,
            "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
            "blockers": [],
            "g2_admitted": False,
            "large_checkpoint_admitted": False,
            "runtime_execution_proven": False,
            "observation_time": "hosted-observation",
            "claim_ceiling": "METADATA_ONLY_NO_MODEL_WEIGHT_EFFECT",
            "logical_id": "source-report-logical-id",
        }

    def assert_code(self, expected, fn):
        with self.assertRaises(W3CompositeAdmissionError) as ctx:
            fn()
        self.assertEqual(expected, ctx.exception.code)

    def test_exact_composition_opens_only_native_synthetic_w3(self):
        out = compose_w3_mtp_admission(
            w3_receipt=self.w3_receipt(),
            mtp_verified_report=self.mtp_report(),
        )
        self.assertEqual("ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.official_w2_producer_proof_consumed)
        self.assertTrue(out.official_mtp_source_provenance_consumed)
        self.assertTrue(out.native_synthetic_w3_eligible)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.provider_effect_admitted)
        self.assertFalse(out.authority)
        self.assertEqual(PR410_PARENT_HEAD, out.pr410_parent_head)
        self.assertEqual(PR409_VERIFIED_HEAD, out.pr409_verified_head)

    def test_w3_unrelated_blocker_cannot_be_laundered(self):
        w3 = self.w3_receipt()
        w3["blockers"].append("AIRLLM_SECURITY_GENERATION_STALE")
        self.assert_code(
            "W3_BLOCKER_SET_NOT_COMPOSABLE",
            lambda: compose_w3_mtp_admission(w3_receipt=w3, mtp_verified_report=self.mtp_report()),
        )

    def test_w3_caller_provenance_widening_cannot_be_laundered(self):
        w3 = self.w3_receipt()
        w3["blockers"].append("GLM53_MTP_CALLER_PROVENANCE_WIDENING_FORBIDDEN")
        self.assert_code(
            "W3_BLOCKER_SET_NOT_COMPOSABLE",
            lambda: compose_w3_mtp_admission(w3_receipt=w3, mtp_verified_report=self.mtp_report()),
        )

    def test_w3_official_producer_proof_required(self):
        w3 = self.w3_receipt()
        w3["official_w2_producer_proof_consumed"] = False
        self.assert_code(
            "W3_OFFICIAL_W2_PRODUCER_PROOF_REQUIRED",
            lambda: compose_w3_mtp_admission(w3_receipt=w3, mtp_verified_report=self.mtp_report()),
        )

    def test_w3_generation_substitution_fails(self):
        w3 = self.w3_receipt()
        w3["glm53_metadata_semantic_head"] = "0" * 40
        self.assert_code(
            "W3_RECEIPT_GENERATION_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=w3, mtp_verified_report=self.mtp_report()),
        )

    def test_w3_effect_widening_fails(self):
        w3 = self.w3_receipt()
        w3["g2_admitted"] = True
        self.assert_code(
            "W3_EFFECT_CEILING_WIDENED:g2_admitted",
            lambda: compose_w3_mtp_admission(w3_receipt=w3, mtp_verified_report=self.mtp_report()),
        )

    def test_mtp_source_binding_required(self):
        report = self.mtp_report()
        report["source_binding_proven"] = False
        self.assert_code(
            "MTP_SOURCE_BINDING_REQUIRED",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_mtp_provenance_method_must_be_official_source_derivation(self):
        report = self.mtp_report()
        report["extra_layer_resolver_provenance_method"] = "CALLER_ASSERTION"
        self.assert_code(
            "MTP_PROVENANCE_METHOD_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_mtp_unrelated_blocker_remains_blocking(self):
        report = self.mtp_report()
        report["blockers"] = ["OTHER_BLOCKER"]
        report["status"] = "PARTIAL"
        self.assert_code(
            "MTP_REPORT_STATUS_NOT_COMPOSABLE",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_wrong_official_revision_fails(self):
        report = self.mtp_report()
        report["model_revision"] = "0" * 40
        self.assert_code(
            "MTP_OFFICIAL_REVISION_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_wrong_official_index_fails(self):
        report = self.mtp_report()
        report["index_sha256"] = "0" * 64
        self.assert_code(
            "MTP_OFFICIAL_INDEX_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_wrong_source_bundle_fails(self):
        report = self.mtp_report()
        report["source_bundle_id"] = "0" * 64
        self.assert_code(
            "MTP_SOURCE_BUNDLE_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_report_evidence_binding_mismatch_fails(self):
        report = self.mtp_report()
        report["weight_map_digest"] = "0" * 64
        self.assert_code(
            "MTP_REPORT_EVIDENCE_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_source_evidence_digest_substitution_fails(self):
        report = self.mtp_report()
        report["official_mtp_role_source_evidence_id"] = "0" * 64
        self.assert_code(
            "MTP_SOURCE_EVIDENCE_DIGEST_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_nested_source_evidence_mutation_fails(self):
        report = self.mtp_report()
        report["official_mtp_role_source_evidence"]["config_raw_sha256"] = "0" * 64
        self.assert_code(
            "MTP_SOURCE_EVIDENCE_DIGEST_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_missing_mtp_marker_fails(self):
        report = self.mtp_report()
        report["official_mtp_role_source_evidence"]["mtp_marker_keys"] = []
        self.assert_code(
            "MTP_MARKER_REQUIRED",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_decoder_pager_cast_fails(self):
        report = self.mtp_report()
        report["classified_extra_checkpoint_layers"][0]["decoder_pager_membership"] = True
        self.assert_code(
            "MTP_ROLE_CLASSIFICATION_MISMATCH",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_mtp_effect_widening_fails(self):
        report = self.mtp_report()
        report["g2_admitted"] = True
        self.assert_code(
            "MTP_EFFECT_CEILING_WIDENED:g2_admitted",
            lambda: compose_w3_mtp_admission(w3_receipt=self.w3_receipt(), mtp_verified_report=report),
        )

    def test_composite_receipt_is_deterministic(self):
        a = compose_w3_mtp_admission(
            w3_receipt=copy.deepcopy(self.w3_receipt()),
            mtp_verified_report=copy.deepcopy(self.mtp_report()),
        )
        b = compose_w3_mtp_admission(
            w3_receipt=copy.deepcopy(self.w3_receipt()),
            mtp_verified_report=copy.deepcopy(self.mtp_report()),
        )
        self.assertEqual(a.logical_id, b.logical_id)
        self.assertEqual(a.w3_input_receipt_digest, b.w3_input_receipt_digest)
        self.assertEqual(a.mtp_input_report_digest, b.mtp_input_report_digest)


if __name__ == "__main__":
    unittest.main()
