import unittest
from unittest.mock import patch

from tools.awj032 import glm53_w3_official_producer_admission as p
from tools.awj032 import glm53_w3_proof_plane_admission_v2 as g
from tools.awj032.glm53_official_mtp_role_source_appraiser import OfficialSourceMTPRoleEvidence
from tools.awj032.test_glm53_w3_official_producer_admission import LowerPlan, metadata, security


def source_evidence(**overrides):
    value = dict(
        owner_repo=g.OFFICIAL_REPO,
        immutable_model_revision=g.OFFICIAL_REVISION,
        config_raw_sha256="1" * 64,
        config_parsed_sha256="2" * 64,
        index_sha256=g.OFFICIAL_INDEX_SHA256,
        index_parsed_sha256="3" * 64,
        weight_map_digest="4" * 64,
        source_bundle_id="5" * 64,
        num_hidden_layers=g.OFFICIAL_NUM_HIDDEN_LAYERS,
        num_nextn_predict_layers=g.OFFICIAL_NUM_NEXTN_PREDICT_LAYERS,
        observed_extra_checkpoint_layer_indices=(g.OFFICIAL_MTP_LAYER,),
        mtp_marker_keys=(f"model.layers.{g.OFFICIAL_MTP_LAYER}.eh_proj.weight",),
        role_index=g.OFFICIAL_MTP_LAYER,
        role=g.OFFICIAL_ROLE,
    )
    value.update(overrides)
    return OfficialSourceMTPRoleEvidence(**value)


def base_receipt(**kwargs):
    return p.evaluate_w3_official_producer_admission(
        pager_plan=kwargs.get("plan", LowerPlan()),
        airllm_security_evidence=kwargs.get("sec", security()),
        glm53_metadata_evidence=kwargs.get("meta", metadata()),
    )


class W3ProofPlaneAdmissionV2Tests(unittest.TestCase):
    def test_exact_source_reduces_only_mtp_blocker_and_admits_synthetic_fixture(self):
        out = g._reduce_with_observed_source(base_receipt(), source_evidence())
        self.assertEqual("ELIGIBLE_FOR_NATIVE_SYNTHETIC_W3_FIXTURE", out.status)
        self.assertEqual((), out.blockers)
        self.assertTrue(out.official_w2_producer_proof_consumed)
        self.assertTrue(out.official_mtp_source_role_proven)
        self.assertTrue(out.synthetic_tiny_fixture_admitted)
        self.assertFalse(out.official_tensor_payload_admitted)
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.runtime_execution_admitted)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)

    def test_public_path_observes_source_internally_not_from_caller(self):
        observed = source_evidence()
        with patch.object(g, "observe_official_mtp_role", return_value=observed) as call:
            out = g.evaluate_w3_proof_plane_admission(
                pager_plan=LowerPlan(),
                airllm_security_evidence=security(),
                glm53_metadata_evidence=metadata(),
            )
        call.assert_called_once_with()
        self.assertEqual(observed.evidence_id, out.official_mtp_source_evidence_id)

    def test_caller_provenance_boolean_is_rejected_before_source_observation(self):
        with patch.object(g, "observe_official_mtp_role") as call:
            with self.assertRaises(g.W3ProofPlaneAdmissionError) as ctx:
                g.evaluate_w3_proof_plane_admission(
                    pager_plan=LowerPlan(),
                    airllm_security_evidence=security(),
                    glm53_metadata_evidence=metadata(resolver_provenance_proven=True),
                )
        self.assertEqual("CALLER_MTP_PROVENANCE_WIDENING_FORBIDDEN", ctx.exception.code)
        call.assert_not_called()

    def test_unresolved_non_mtp_blocker_prevents_source_credit(self):
        base = base_receipt(sec=security(semantic_head="1" * 40))
        with self.assertRaises(g.W3ProofPlaneAdmissionError) as ctx:
            g._reduce_with_observed_source(base, source_evidence())
        self.assertEqual("W3_PRE_MTP_BLOCKERS_REMAIN", ctx.exception.code)

    def test_repo_revision_index_and_role_substitutions_fail(self):
        cases = [
            source_evidence(owner_repo="other/repo"),
            source_evidence(immutable_model_revision="0" * 40),
            source_evidence(index_sha256="0" * 64),
            source_evidence(role="DECODER"),
            source_evidence(role_index=79),
        ]
        for evidence in cases:
            with self.subTest(evidence=evidence):
                with self.assertRaises(g.W3ProofPlaneAdmissionError):
                    g._reduce_with_observed_source(base_receipt(), evidence)

    def test_mtp_geometry_and_marker_substitutions_fail(self):
        cases = [
            source_evidence(num_hidden_layers=77),
            source_evidence(num_nextn_predict_layers=0),
            source_evidence(observed_extra_checkpoint_layer_indices=(78, 79)),
            source_evidence(mtp_marker_keys=()),
            source_evidence(mtp_marker_keys=("model.layers.77.eh_proj.weight",)),
            source_evidence(decoder_pager_membership=True),
        ]
        for evidence in cases:
            with self.subTest(evidence=evidence):
                with self.assertRaises(g.W3ProofPlaneAdmissionError):
                    g._reduce_with_observed_source(base_receipt(), evidence)

    def test_source_effect_widening_fails(self):
        cases = [
            source_evidence(source_verified=False),
            source_evidence(payload_bytes_read=1),
            source_evidence(g2_admitted=True),
            source_evidence(runtime_executed=True),
            source_evidence(authority=True),
        ]
        for evidence in cases:
            with self.subTest(evidence=evidence):
                with self.assertRaises(g.W3ProofPlaneAdmissionError):
                    g._reduce_with_observed_source(base_receipt(), evidence)

    def test_lower_plan_producer_failure_prevents_source_observation(self):
        with patch.object(g, "observe_official_mtp_role") as call:
            with self.assertRaises(g.W3ProofPlaneAdmissionError) as ctx:
                g.evaluate_w3_proof_plane_admission(
                    pager_plan=LowerPlan(header_observation_repo_id="synthetic/local"),
                    airllm_security_evidence=security(),
                    glm53_metadata_evidence=metadata(),
                )
        self.assertEqual("W2_PRODUCER_CONSUMER_ADMISSION_FAILED", ctx.exception.code)
        call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
