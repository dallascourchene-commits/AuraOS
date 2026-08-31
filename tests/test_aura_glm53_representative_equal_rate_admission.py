from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch
import unittest

from tools.quantization import aura_glm53_representative_equal_rate_admission as q16


def synthetic_q5() -> dict:
    tiles = []
    for index, tile_id in enumerate(q16.EXPECTED_TILE_IDS):
        role, col = tile_id.split(":")
        tiles.append({
            "tensor_role": role,
            "col_start": int(col),
            "weights": 64,
            "canonical_float32_tile_sha256": f"{index + 1:064x}",
            "e8_payload_sha256": f"{index + 101:064x}",
            "control_payload_sha256": f"{index + 201:064x}",
            "e8_mse": 1.0 + index,
            "control_mse": 2.0 + index,
            "outcome": "E8_WIN",
        })
    body = {
        "schema": "AURA_GLM53_OFFICIAL_EQUAL_RATE_E8_CANARY_V1",
        "q13_source_tensor_set_digest": q16.SOURCE_SET_DIGEST,
        "codec_bpw_e8": q16.EXACT_BPW,
        "codec_bpw_control": q16.EXACT_BPW,
        "equal_rate": True,
        "total_official_weights_observed": 512,
        "tiles": tiles,
        "aggregate_e8_over_control": 0.5,
        "aggregate_outcome": "E8_WIN",
        "official_source_equal_rate_distortion_evidence": True,
        "representative_canary_scope_only": True,
        "geometry_privileged": False,
        "full_tensor_quantized": False,
        "whole_model_quantized": False,
        "glm_quality_proven": False,
        "runtime_performance_proven": False,
        "native_private_transformer_kv_accessed": False,
        "semantic_k27_authority": False,
        "gate10_promoted": False,
    }
    body["receipt_digest"] = q16._sha(body)
    return body


def admit_authorized_synthetic(payload: dict):
    digest = payload["receipt_digest"]
    ratio = payload["aggregate_e8_over_control"]
    with patch.object(q16, "Q5_RECEIPT_DIGEST", digest), patch.object(
        q16, "Q5_AGGREGATE_E8_OVER_CONTROL", ratio
    ):
        return q16.admit_exact_q5_representative_evidence(payload)


class RepresentativeEqualRateAdmissionTests(unittest.TestCase):
    def test_complete_eight_tile_scope_is_admitted_but_not_promoted(self):
        receipt = admit_authorized_synthetic(synthetic_q5())
        self.assertTrue(receipt["representative_scope_complete"])
        self.assertEqual(receipt["minimum_missing_evidence_cone"], [])
        self.assertEqual(receipt["outcome_counts"], {"CONTROL_WIN": 0, "E8_WIN": 8, "TIE": 0})
        self.assertEqual(receipt["next_work_mode"], "STOP_OR_REGISTER_HIGHER_SCOPE")
        self.assertTrue(receipt["representative_evidence_only"])
        for key in (
            "geometry_superiority_proven",
            "full_tensor_superiority_proven",
            "full_model_superiority_proven",
            "quality_superiority_proven",
            "runtime_superiority_proven",
            "model_execution_observed",
            "effect_authority",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority",
            "gate10_promoted",
            "merge_or_deployment_authorized",
        ):
            self.assertFalse(receipt[key], key)

    def test_body_mutation_cannot_reuse_old_receipt_digest(self):
        payload = synthetic_q5()
        old = payload["receipt_digest"]
        payload["tiles"][0]["e8_mse"] = 999.0
        with patch.object(q16, "Q5_RECEIPT_DIGEST", old), patch.object(q16, "Q5_AGGREGATE_E8_OVER_CONTROL", 0.5):
            with self.assertRaisesRegex(q16.RepresentativeEqualRateAdmissionError, "BODY_DIGEST"):
                q16.admit_exact_q5_representative_evidence(payload)

    def test_rate_drift_fails_after_authenticated_body(self):
        payload = synthetic_q5()
        payload["codec_bpw_e8"] = 2.0
        payload["receipt_digest"] = q16._sha(q16._receipt_body(payload))
        with patch.object(q16, "Q5_RECEIPT_DIGEST", payload["receipt_digest"]), patch.object(q16, "Q5_AGGREGATE_E8_OVER_CONTROL", 0.5):
            with self.assertRaisesRegex(q16.RepresentativeEqualRateAdmissionError, "RATE_MISMATCH"):
                q16.admit_exact_q5_representative_evidence(payload)

    def test_unregistered_tile_fails_after_authenticated_body(self):
        payload = synthetic_q5()
        payload["tiles"][0]["col_start"] = 512
        payload["receipt_digest"] = q16._sha(q16._receipt_body(payload))
        with patch.object(q16, "Q5_RECEIPT_DIGEST", payload["receipt_digest"]), patch.object(q16, "Q5_AGGREGATE_E8_OVER_CONTROL", 0.5):
            with self.assertRaisesRegex(q16.RepresentativeEqualRateAdmissionError, "TILE_REGISTRY_MISMATCH"):
                q16.admit_exact_q5_representative_evidence(payload)

    def test_declared_outcome_mse_contradiction_fails_in_scope_owner(self):
        payload = synthetic_q5()
        payload["tiles"][0]["e8_mse"] = 3.0
        payload["tiles"][0]["control_mse"] = 2.0
        payload["receipt_digest"] = q16._sha(q16._receipt_body(payload))
        with patch.object(q16, "Q5_RECEIPT_DIGEST", payload["receipt_digest"]), patch.object(q16, "Q5_AGGREGATE_E8_OVER_CONTROL", 0.5):
            with self.assertRaisesRegex(ValueError, "declared outcome disagrees"):
                q16.admit_exact_q5_representative_evidence(payload)

    def test_missing_tile_cannot_hide_behind_repeated_tile(self):
        payload = synthetic_q5()
        payload["tiles"][7] = deepcopy(payload["tiles"][0])
        payload["receipt_digest"] = q16._sha(q16._receipt_body(payload))
        with patch.object(q16, "Q5_RECEIPT_DIGEST", payload["receipt_digest"]), patch.object(q16, "Q5_AGGREGATE_E8_OVER_CONTROL", 0.5):
            with self.assertRaisesRegex(q16.RepresentativeEqualRateAdmissionError, "TILE_REGISTRY_MISMATCH"):
                q16.admit_exact_q5_representative_evidence(payload)

    def test_exact_parent_generations_are_frozen(self):
        self.assertEqual(q16.Q5_HEAD, "eb5887a1f2a26d763dd312b1c84af9ea7f961fe3")
        self.assertEqual(q16.Q5_RUN, 33401474768)
        self.assertEqual(q16.Q5_JOB, 99518559654)
        self.assertEqual(q16.Q6_HEAD, "6906337dd6e75f49a70a84652bfd9ab70d967eef")
        self.assertEqual(q16.Q6_RUN, 33401482324)
        self.assertEqual(q16.Q6_JOB, 99518584784)


if __name__ == "__main__":
    unittest.main()
