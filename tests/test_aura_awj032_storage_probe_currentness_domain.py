from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from scripts.aura_awj032_lifecycle_return_currentness_domain import CROSS_DOMAIN_REJECTION
from scripts.aura_awj032_storage_probe_currentness_domain import (
    project_bounded_storage_probe_currentness,
)
from tools.awj032.glm53_owner_host_c2_handoff import OwnerHostC2CanaryRequest
from tools.awj032.thinkpad_bounded_storage_probe import ThinkPadStorageProbeReceipt


class AWJ032StorageProbeCurrentnessDomainTests(unittest.TestCase):
    def request(self) -> OwnerHostC2CanaryRequest:
        return OwnerHostC2CanaryRequest(
            w3_proof_logical_id="ab" * 32,
            preflight_receipt_digest="cd" * 32,
            airllm_source_revision="airllm-reviewed-source@deadbeef",
            airllm_security_evidence_digest="12" * 32,
            host_snapshot_digest="34" * 32,
            storage_plan_digest="56" * 32,
            workspace_root="/tmp/aura-o51-storage-probe-currentness",
            max_payload_bytes=2 * 1024 * 1024,
            max_wall_seconds=10,
            effect_admission_ref="owner-effect:awj032:c2:storage-probe-currentness-fixture",
        )

    def receipt(self, request=None, **changes) -> ThinkPadStorageProbeReceipt:
        req = request or self.request()
        value = ThinkPadStorageProbeReceipt(
            request_digest=req.request_digest,
            relative_path="model.safetensors",
            file_identity_digest="78" * 32,
            file_size_bytes=8192,
            byte_offset=0,
            requested_probe_bytes=4096,
            logical_bytes_read=4096,
            read_operations=1,
            chunk_bytes=4096,
            elapsed_seconds=0.01,
            observed_logical_read_bytes_per_second=409600.0,
            window_sha256="9a" * 32,
            eof_reached=False,
        )
        return replace(value, **changes) if changes else value

    def project(self, request=None, receipt=None):
        req = request or self.request()
        rec = receipt or self.receipt(req)
        return project_bounded_storage_probe_currentness(request=req, probe_receipt=rec)

    def test_storage_probe_is_current_only_in_owned_generation(self):
        out = self.project()
        ref = out["evidence_node"]["artifact_ref"]
        self.assertEqual(out["retrieval_admission"]["eligible_artifact_refs"], [ref])
        self.assertEqual(
            out["storage_probe_currentness_admission"]["eligible_artifact_refs"], [ref]
        )
        self.assertTrue(out["storage_probe_current_in_generation"])
        self.assertTrue(out["current_true_is_storage_probe_generation_scoped"])

    def test_four_stronger_currentness_views_fail_three_axis_closed(self):
        out = self.project()
        ref = out["evidence_node"]["artifact_ref"]
        for key in (
            "lifecycle_return_currentness_admission",
            "host_observation_currentness_admission",
            "w4_lifecycle_measurement_currentness_admission",
            "physical_nvme_currentness_admission",
        ):
            admission = out[key]
            self.assertEqual(admission["eligible_artifact_refs"], [])
            self.assertEqual(
                admission["excluded_by_artifact_ref"][ref], CROSS_DOMAIN_REJECTION
            )

    def test_request_world_mismatch_fails_before_memory_projection(self):
        req = self.request()
        rec = self.receipt(req)
        foreign = self.request()
        foreign = replace(foreign, host_snapshot_digest="ef" * 32)
        with self.assertRaisesRegex(ValueError, "STORAGE_PROBE_REQUEST_DIGEST_MISMATCH"):
            project_bounded_storage_probe_currentness(
                request=foreign,
                probe_receipt=rec,
            )

    def test_physical_nvme_ceiling_widening_is_rejected(self):
        req = self.request()
        rec = self.receipt(req, physical_nvme_io_attested=True)
        with self.assertRaisesRegex(
            ValueError, "STORAGE_PROBE_CEILING_WIDENED:physical_nvme_io_attested"
        ):
            self.project(req, rec)

    def test_storage_medium_ceiling_widening_is_rejected(self):
        req = self.request()
        rec = self.receipt(req, storage_medium_nvme_proven=True)
        with self.assertRaisesRegex(
            ValueError, "STORAGE_PROBE_CEILING_WIDENED:storage_medium_nvme_proven"
        ):
            self.project(req, rec)

    def test_telemetry_change_changes_artifact_not_request_world(self):
        req = self.request()
        first = self.receipt(req)
        second = self.receipt(
            req,
            elapsed_seconds=0.02,
            observed_logical_read_bytes_per_second=204800.0,
        )
        a = self.project(req, first)
        b = self.project(req, second)
        self.assertEqual(
            a["evidence_node"]["world_ref"], b["evidence_node"]["world_ref"]
        )
        self.assertNotEqual(
            a["evidence_node"]["artifact_ref"], b["evidence_node"]["artifact_ref"]
        )

    def test_bps_accounting_is_validated(self):
        req = self.request()
        rec = self.receipt(req, observed_logical_read_bytes_per_second=1.0)
        with self.assertRaisesRegex(ValueError, "STORAGE_PROBE_BPS_ACCOUNTING_MISMATCH"):
            self.project(req, rec)

    def test_public_boundary_has_no_currentness_or_authority_override(self):
        params = set(inspect.signature(project_bounded_storage_probe_currentness).parameters)
        self.assertEqual(params, {"request", "probe_receipt"})
        forbidden = {
            "evidence_type",
            "currentness_domain",
            "use_class",
            "current",
            "physical_nvme_currentness",
            "host_observation_currentness",
            "lifecycle_measurement_currentness",
            "producer_authenticated",
            "w4_admitted",
            "g2_admitted",
            "effect_authority",
            "semantic_k27_authority",
            "native_transformer_kv",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_valid_storage_observation_remains_nonauthorizing(self):
        out = self.project()
        for field in (
            "lifecycle_return_currentness_proven",
            "host_observation_currentness_proven",
            "w4_lifecycle_measurement_currentness_proven",
            "physical_nvme_currentness_proven",
            "physical_io_attested",
            "storage_medium_nvme_proven",
            "producer_authenticated",
            "model_execution_observed",
            "lifecycle_registry_admitted",
            "real_w4_policy_winner_proven",
            "g2_admitted",
            "host_rank_transition_performed",
            "effect_authority_proven",
            "semantic_truth_proven",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
        ):
            self.assertFalse(out[field], field)

    def test_projection_is_deterministic_for_frozen_receipt(self):
        req = self.request()
        rec = self.receipt(req)
        self.assertEqual(self.project(req, rec), self.project(req, rec))


if __name__ == "__main__":
    unittest.main()
