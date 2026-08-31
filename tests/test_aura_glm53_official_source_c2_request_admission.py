from __future__ import annotations

from dataclasses import replace
import inspect
import unittest
from unittest.mock import patch

from tools.quantization.aura_glm53_official_source_admission import (
    AdmissionState,
    OFFICIAL_COMMIT,
    OFFICIAL_REPO,
    PR628_E8_PAGE_ARTIFACT_SHA,
    PR628_E8_PAGE_SCHEME,
    current_public_state,
)
from tools.quantization.aura_glm53_official_source_c2_request_admission import (
    C2_HANDOFF_HEAD,
    C2_HANDOFF_RUN,
    SOURCE_ADMISSION_HEAD,
    SOURCE_ADMISSION_RUN,
    _join_verified_source_state,
    admit_source_bound_c2_request,
    current_public_source_c2_disposition,
    deterministic_request_fixture,
)


class OfficialSourceC2RequestAdmissionTests(unittest.TestCase):
    def test_current_public_state_blocks_c2_request(self):
        out = current_public_source_c2_disposition(deterministic_request_fixture())
        self.assertTrue(out.c2_request_source_matches)
        self.assertFalse(out.source_header_trial_eligible)
        self.assertFalse(out.source_bound_c2_request_admissible)
        self.assertEqual(out.blocker, "OFFICIAL_INDEX_BYTES_AND_REPRESENTATIVE_HEADERS_NOT_MATERIALIZED")
        self.assertFalse(out.execution_authorized_by_this_contract)
        self.assertFalse(out.owner_host_execution_observed)

    def test_exact_parent_generations_are_pinned(self):
        out = current_public_source_c2_disposition(deterministic_request_fixture())
        self.assertEqual(out.exact_parent_heads, (SOURCE_ADMISSION_HEAD, C2_HANDOFF_HEAD))
        self.assertEqual(out.exact_parent_runs, (SOURCE_ADMISSION_RUN, C2_HANDOFF_RUN))
        self.assertEqual(SOURCE_ADMISSION_HEAD, "730426b82235b0ff4e75fef1cff00707877a84ad")
        self.assertEqual(C2_HANDOFF_HEAD, "24a5404ee3b987dee12192917e40b35d3a43e81c")

    def test_header_green_state_can_admit_request_but_not_execution(self):
        state = AdmissionState(
            schema="AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1",
            official_repository=OFFICIAL_REPO,
            official_revision=OFFICIAL_COMMIT,
            candidate_parent_sha=PR628_E8_PAGE_ARTIFACT_SHA,
            candidate_scheme=PR628_E8_PAGE_SCHEME,
            config_profile_bound=True,
            index_object_identity_bound=True,
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            candidate_representation_bound=True,
            header_trial_eligible=True,
            source_tensor_payload_bound=False,
            real_tensor_quantization_eligible=False,
            blocker="SOURCE_TENSOR_PAYLOAD_NOT_BOUND",
            semantic_k27_authority=False,
            native_transformer_kv_accessed=False,
            gate10_promoted=False,
        )
        out = _join_verified_source_state(source_state=state, request=deterministic_request_fixture())
        self.assertTrue(out.source_bound_c2_request_admissible)
        self.assertEqual(out.blocker, "NONE_HEADER_LEVEL_REQUEST_ADMISSIBLE")
        self.assertFalse(out.source_tensor_payload_bound)
        self.assertFalse(out.real_tensor_quantization_eligible)
        self.assertFalse(out.execution_authorized_by_this_contract)
        self.assertFalse(out.g2_admitted)

    def test_partial_header_state_stays_blocked(self):
        state = replace(current_public_state(), index_bytes_verified=True)
        out = _join_verified_source_state(source_state=state, request=deterministic_request_fixture())
        self.assertFalse(out.source_bound_c2_request_admissible)

    def test_candidate_parent_substitution_is_rejected(self):
        state = replace(current_public_state(), candidate_parent_sha="0" * 40)
        with self.assertRaisesRegex(ValueError, "CANDIDATE_PARENT_MISMATCH"):
            _join_verified_source_state(source_state=state, request=deterministic_request_fixture())

    def test_source_generation_substitution_is_rejected(self):
        state = replace(current_public_state(), official_revision="wrong")
        with self.assertRaisesRegex(ValueError, "OFFICIAL_SOURCE_GENERATION_MISMATCH"):
            _join_verified_source_state(source_state=state, request=deterministic_request_fixture())

    def test_public_raw_builder_has_no_admission_boolean_escape_hatch(self):
        params = set(inspect.signature(admit_source_bound_c2_request).parameters)
        forbidden = {
            "verified", "bound", "eligible", "header_trial_eligible",
            "source_tensor_payload_bound", "execution_authorized", "g2_admitted",
        }
        self.assertTrue(params.isdisjoint(forbidden))
        self.assertEqual(
            params,
            {"request", "config", "index_bytes", "expert_prefix", "shard_header_prefixes", "candidate_parent_sha"},
        )

    def test_public_raw_builder_consumes_pr639_recomputed_state(self):
        admitted = AdmissionState(
            schema="AURA_GLM53_OFFICIAL_QUANTIZATION_SOURCE_ADMISSION_V1",
            official_repository=OFFICIAL_REPO,
            official_revision=OFFICIAL_COMMIT,
            candidate_parent_sha=PR628_E8_PAGE_ARTIFACT_SHA,
            candidate_scheme=PR628_E8_PAGE_SCHEME,
            config_profile_bound=True,
            index_object_identity_bound=True,
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            candidate_representation_bound=True,
            header_trial_eligible=True,
            source_tensor_payload_bound=False,
            real_tensor_quantization_eligible=False,
            blocker="SOURCE_TENSOR_PAYLOAD_NOT_BOUND",
            semantic_k27_authority=False,
            native_transformer_kv_accessed=False,
            gate10_promoted=False,
        )
        with patch(
            "tools.quantization.aura_glm53_official_source_c2_request_admission.admit_official_header_state",
            return_value=admitted,
        ) as source_admit:
            out = admit_source_bound_c2_request(
                request=deterministic_request_fixture(),
                config={},
                index_bytes=b"raw",
                expert_prefix="model.layers.0.mlp.experts.0",
                shard_header_prefixes={"x.safetensors": b"header"},
                candidate_parent_sha=PR628_E8_PAGE_ARTIFACT_SHA,
            )
        source_admit.assert_called_once()
        self.assertTrue(out.source_bound_c2_request_admissible)
        self.assertFalse(out.execution_authorized_by_this_contract)

    def test_successful_header_level_join_remains_nonauthorizing(self):
        state = replace(
            current_public_state(),
            index_bytes_verified=True,
            representative_key_to_shard_bound=True,
            representative_headers_observed=True,
            fp8_companions_bound=True,
            header_trial_eligible=True,
            blocker="SOURCE_TENSOR_PAYLOAD_NOT_BOUND",
        )
        out = _join_verified_source_state(source_state=state, request=deterministic_request_fixture())
        self.assertTrue(out.source_bound_c2_request_admissible)
        self.assertFalse(out.execution_authorized_by_this_contract)
        self.assertFalse(out.owner_host_execution_observed)
        self.assertFalse(out.physical_io_attested)
        self.assertFalse(out.lifecycle_producer_authenticated)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.semantic_k27_authority_minted)
        self.assertFalse(out.native_private_transformer_kv_accessed)
        self.assertFalse(out.gate10_promoted)
        self.assertEqual(len(out.disposition_digest), 64)


if __name__ == "__main__":
    unittest.main()
