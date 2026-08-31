from __future__ import annotations

from dataclasses import asdict, replace
import unittest

from tools.quantization.aura_glm53_representation_specific_source_trial_gate import (
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    PR628_EXACT_CANDIDATE,
    PR628_SCHEME,
    Q5_SOURCE_SCHEMA,
    classify_source_trial,
    validate_source_admission,
)
from tools.quantization.aura_glm53_quantization_evidence_transfer import q5_representation_identity


def current_hold() -> dict[str, object]:
    return {
        "schema": Q5_SOURCE_SCHEMA,
        "official_repository": OFFICIAL_REPOSITORY,
        "official_revision": OFFICIAL_REVISION,
        "candidate_parent_sha": PR628_EXACT_CANDIDATE,
        "candidate_scheme": PR628_SCHEME,
        "config_profile_bound": True,
        "index_object_identity_bound": True,
        "index_bytes_verified": False,
        "representative_key_to_shard_bound": False,
        "representative_headers_observed": False,
        "fp8_companions_bound": False,
        "candidate_representation_bound": True,
        "header_trial_eligible": False,
        "source_tensor_payload_bound": False,
        "real_tensor_quantization_eligible": False,
        "blocker": "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED",
        "semantic_k27_authority": False,
        "native_transformer_kv_accessed": False,
        "gate10_promoted": False,
    }


def hypothetical_header_green() -> dict[str, object]:
    out = current_hold()
    for key in (
        "index_bytes_verified",
        "representative_key_to_shard_bound",
        "representative_headers_observed",
        "fp8_companions_bound",
        "header_trial_eligible",
    ):
        out[key] = True
    out["blocker"] = "NONE_AT_HEADER_PLANE"
    return out


class RepresentationSpecificSourceTrialGateTests(unittest.TestCase):
    def test_current_q5_state_remains_hold(self) -> None:
        r = classify_source_trial(current_hold())
        self.assertEqual(r.disposition, "HOLD_SOURCE_HEADER_NOT_ELIGIBLE")
        self.assertFalse(r.header_bound_representation_trial_candidate)
        self.assertTrue(r.exact_target_representation_identity_bound)

    def test_header_green_exact_representation_only_grants_candidate(self) -> None:
        r = classify_source_trial(hypothetical_header_green())
        self.assertEqual(r.disposition, "HEADER_BOUND_REPRESENTATION_TRIAL_CANDIDATE")
        self.assertTrue(r.header_bound_representation_trial_candidate)
        self.assertFalse(r.source_tensor_payload_bound)
        self.assertFalse(r.real_tensor_quantization_eligible)
        self.assertFalse(r.evidence_transfer_authorized)
        self.assertFalse(r.glm53_quality_evidence)
        self.assertFalse(r.runtime_evidence)
        self.assertFalse(r.gate10_promoted)

    def test_geometry_or_near_identity_drift_holds(self) -> None:
        target = q5_representation_identity()
        drifted = replace(target, index_bits_per_vector=8, codec_bits_per_weight=1.25)
        r = classify_source_trial(hypothetical_header_green(), drifted)
        self.assertEqual(r.disposition, "HOLD_REPRESENTATION_IDENTITY_MISMATCH")
        self.assertFalse(r.exact_target_representation_identity_bound)
        self.assertFalse(r.header_bound_representation_trial_candidate)

    def test_scheme_alias_is_not_source_identity(self) -> None:
        source = current_hold()
        source["candidate_scheme"] = "E8_ROOT_240_U8_V1"
        with self.assertRaisesRegex(ValueError, "SOURCE_CANDIDATE_REPRESENTATION_MISMATCH"):
            classify_source_trial(source)

    def test_header_boolean_cannot_skip_missing_evidence(self) -> None:
        source = current_hold()
        source["header_trial_eligible"] = True
        with self.assertRaisesRegex(ValueError, "HEADER_ELIGIBLE_WITH_INCOMPLETE_Q5_EVIDENCE"):
            classify_source_trial(source)

    def test_payload_or_real_quantization_cannot_enter_header_gate(self) -> None:
        source = hypothetical_header_green()
        source["source_tensor_payload_bound"] = True
        with self.assertRaisesRegex(ValueError, "Q7_HEADER_GATE_CANNOT_CONSUME_PAYLOAD_OR_EXECUTION_PROMOTION"):
            classify_source_trial(source)

    def test_parent_authority_widening_rejected(self) -> None:
        for key in ("semantic_k27_authority", "native_transformer_kv_accessed", "gate10_promoted"):
            source = current_hold()
            source[key] = True
            with self.assertRaisesRegex(ValueError, "Q5_PARENT_CEILING_WIDENED"):
                validate_source_admission(source)

    def test_complete_source_schema_required(self) -> None:
        source = current_hold()
        del source["representative_headers_observed"]
        with self.assertRaisesRegex(ValueError, "SOURCE_SCHEMA_MISMATCH"):
            classify_source_trial(source)

    def test_receipt_is_deterministic_and_tamper_sensitive(self) -> None:
        a = classify_source_trial(current_hold())
        b = classify_source_trial(current_hold())
        self.assertEqual(a.receipt_digest, b.receipt_digest)
        modified = current_hold()
        modified["blocker"] = "SAME_HOLD_DIFFERENT_LABEL"
        c = classify_source_trial(modified)
        self.assertNotEqual(a.receipt_digest, c.receipt_digest)

    def test_claim_ceiling_is_complete_on_current_hold(self) -> None:
        r = asdict(classify_source_trial(current_hold()))
        for key in (
            "header_bound_representation_trial_candidate",
            "source_tensor_payload_bound",
            "real_tensor_quantization_eligible",
            "evidence_transfer_authorized",
            "glm53_quality_evidence",
            "runtime_evidence",
            "semantic_k27_authority",
            "native_private_transformer_kv_accessed",
            "gate10_promoted",
            "deployment_authorized",
        ):
            self.assertFalse(r[key], key)


if __name__ == "__main__":
    unittest.main()
