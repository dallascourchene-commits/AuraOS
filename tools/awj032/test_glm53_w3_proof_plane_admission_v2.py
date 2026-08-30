import unittest
from unittest.mock import patch

from tools.awj032 import glm53_pr340_producer_snapshot_registry as registry
from tools.awj032 import glm53_w3_proof_plane_admission_v2 as g
from tools.awj032.glm53_official_mtp_role_source_appraiser import OfficialSourceMTPRoleEvidence
from tools.awj032.glm53_pr340_producer_snapshot import PR340ProducerSnapshot
from tools.awj032.test_glm53_w3_official_producer_admission import LowerPlan, metadata, security


def exact_snapshot(**overrides):
    value = dict(
        final_report_digest=registry.FINAL_REPORT_DIGEST,
        classification_stage_logical_id=registry.CLASSIFICATION_STAGE_LOGICAL_ID,
        source_bundle_id=registry.SOURCE_BUNDLE_ID,
        config_parsed_sha256="d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40",
        index_parsed_sha256="08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c",
        weight_map_digest="f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7",
        blocker_set=registry.BLOCKER_SET,
        producer_base_head=registry.PRODUCER_BASE_HEAD,
        producer_execution_head=registry.PRODUCER_EXECUTION_HEAD,
        airllm_security_generation="e26f5228b2a7ad97aa8325593cf5550febce61ed",
        model_revision=registry.MODEL_REVISION,
        index_sha256=registry.INDEX_SHA256,
    )
    value.update(overrides)
    return PR340ProducerSnapshot(**value)


def exact_report():
    return {
        "logical_id": registry.CLASSIFICATION_STAGE_LOGICAL_ID,
        "blockers": list(registry.BLOCKER_SET),
        "source_bundle_id": registry.SOURCE_BUNDLE_ID,
        "source_binding_proven": True,
    }


def source_evidence():
    return OfficialSourceMTPRoleEvidence(
        owner_repo="zai-org/GLM-5.3",
        immutable_model_revision=registry.MODEL_REVISION,
        config_raw_sha256="3ac72612095574542f7fff847ada8e59d9199dd8af44bdf625d7e02615572e69",
        config_parsed_sha256="d497aba98135da3586209ba863e8e42eccf77a014811d0d3df812db9909c5d40",
        index_sha256=registry.INDEX_SHA256,
        index_parsed_sha256="08f826679200e2dc91d5e9c5514bab239369122a8d0ef81df9c8accd55d4797c",
        weight_map_digest="f201f9a19849fab7d0cb4ce928294aa4536b03fed527ce3bf4b3be2962fbc6a7",
        source_bundle_id=registry.SOURCE_BUNDLE_ID,
        num_hidden_layers=78,
        num_nextn_predict_layers=1,
        observed_extra_checkpoint_layer_indices=(78,),
        mtp_marker_keys=("model.layers.78.eh_proj.weight",),
        role_index=78,
        role="MTP_NON_DECODER",
    )


class RegisteredProducerTests(unittest.TestCase):
    def test_registry_accepts_exact_hosted_snapshot_only(self):
        snap = exact_snapshot()
        with patch.object(registry, "final_source_bound_report_digest", return_value=registry.FINAL_REPORT_DIGEST):
            self.assertIs(snap, registry.verify_registered_pr340_snapshot(snap, exact_report()))

    def test_registry_rejects_execution_report_and_snapshot_substitution(self):
        cases = [
            exact_snapshot(producer_execution_head="0" * 40),
            exact_snapshot(final_report_digest="0" * 64),
            exact_snapshot(classification_stage_logical_id="0" * 64),
            exact_snapshot(source_bundle_id="0" * 64),
        ]
        for snap in cases:
            with self.subTest(snap=snap):
                with patch.object(registry, "final_source_bound_report_digest", return_value=registry.FINAL_REPORT_DIGEST):
                    with self.assertRaises(registry.PR340ProducerRegistryError):
                        registry.verify_registered_pr340_snapshot(snap, exact_report())

    def test_registry_rejects_producer_self_verification_and_effect_widening(self):
        for snap in (
            exact_snapshot(producer_snapshot_verified_by_external_registry=True),
            exact_snapshot(g2_admitted=True),
            exact_snapshot(runtime_execution_proven=True),
            exact_snapshot(authority=True),
        ):
            with self.subTest(snap=snap):
                with patch.object(registry, "final_source_bound_report_digest", return_value=registry.FINAL_REPORT_DIGEST):
                    with self.assertRaises(registry.PR340ProducerRegistryError):
                        registry.verify_registered_pr340_snapshot(snap, exact_report())

    def test_public_w3_path_cannot_use_caller_resolver_true(self):
        with patch.object(g, "_observe_registered_pr340") as observe:
            with self.assertRaises(g.W3ProofPlaneAdmissionError) as ctx:
                g.evaluate_w3_proof_plane_admission(
                    pager_plan=LowerPlan(),
                    airllm_security_evidence=security(),
                    glm53_metadata_evidence=metadata(resolver_provenance_proven=True),
                )
        self.assertEqual("CALLER_MTP_PROVENANCE_WIDENING_FORBIDDEN", ctx.exception.code)
        observe.assert_not_called()

    def test_unresolved_non_mtp_blocker_prevents_registry_use(self):
        with patch.object(g, "_observe_registered_pr340") as observe:
            with self.assertRaises(g.W3ProofPlaneAdmissionError) as ctx:
                g.evaluate_w3_proof_plane_admission(
                    pager_plan=LowerPlan(),
                    airllm_security_evidence=security(semantic_head="1" * 40),
                    glm53_metadata_evidence=metadata(),
                )
        self.assertEqual("W3_PRE_MTP_BLOCKERS_REMAIN", ctx.exception.code)
        observe.assert_not_called()

    def test_registered_composition_admits_only_native_synthetic_fixture(self):
        snap = exact_snapshot()
        evidence = source_evidence()
        admitted = {
            "status": "READY_FOR_HEADER_AND_TINY_FIXTURE",
            "blockers": [],
            "pr340_producer_logical_id_verified": True,
            "pr340_producer_logical_id": registry.CLASSIFICATION_STAGE_LOGICAL_ID,
            "pr340_producer_semantic_generation": registry.PRODUCER_BASE_HEAD,
            "extra_layer_resolver_provenance_proven": True,
            "extra_layer_resolver_provenance_method": "OFFICIAL_IMMUTABLE_SOURCE_DERIVATION",
            "g2_admitted": False,
            "runtime_execution_proven": False,
            "large_checkpoint_admitted": False,
        }
        with patch.object(g, "_observe_registered_pr340", return_value=(snap, exact_report(), evidence, admitted)):
            out = g.evaluate_w3_proof_plane_admission(
                pager_plan=LowerPlan(),
                airllm_security_evidence=security(),
                glm53_metadata_evidence=metadata(),
            )
        self.assertEqual("ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.pr340_producer_report_registered)
        self.assertTrue(out.pr409_producer_and_source_appraisal_proven)
        self.assertTrue(out.synthetic_tiny_fixture_admitted)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)


if __name__ == "__main__":
    unittest.main()
