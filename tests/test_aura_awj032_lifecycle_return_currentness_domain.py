from __future__ import annotations

import copy
import inspect
import unittest
from dataclasses import replace

from scripts.aura_awj032_lifecycle_return_currentness_domain import (
    CROSS_DOMAIN_REJECTION,
    CURRENTNESS_DOMAIN,
    EVIDENCE_TYPE,
    HOST_OBSERVATION_CURRENTNESS_CONTEXT,
    LIFECYCLE_RETURN_CURRENTNESS_CONTEXT,
    RETRIEVAL_CONTEXT,
    W4_MEASUREMENT_CURRENTNESS_CONTEXT,
    _node_from_packet,
    project_owner_host_lifecycle_return_memory,
)
from scripts.aura_provenance_corroboration_memory_admission import (
    admit_evidence_nodes,
    seal_evidence_node,
)
from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
    join_owner_host_c2_attempt,
)
from tools.awj032.glm53_owner_host_lifecycle_return_packet import (
    build_owner_host_lifecycle_return_packet,
)


def request() -> OwnerHostC2CanaryRequest:
    return OwnerHostC2CanaryRequest(
        w3_proof_logical_id="1" * 64,
        preflight_receipt_digest="2" * 64,
        airllm_source_revision="airllm-exact-rev",
        airllm_security_evidence_digest="3" * 64,
        host_snapshot_digest="4" * 64,
        storage_plan_digest="5" * 64,
        workspace_root="/tmp/aura-awj032-o49",
        max_payload_bytes=1024,
        max_wall_seconds=60,
        effect_admission_ref="effect:owner-gate",
    )


def receipt(req: OwnerHostC2CanaryRequest, **changes) -> OwnerHostC2CanaryReceipt:
    value = OwnerHostC2CanaryReceipt(
        request_digest=req.request_digest,
        owner_host_observation_id="obs-o49",
        runner_identity="runner",
        runner_generation="runner-gen-1",
        started_at_utc="2026-08-31T00:00:00+00:00",
        ended_at_utc="2026-08-31T00:00:10+00:00",
        command_digest="6" * 64,
        environment_digest="7" * 64,
        source_snapshot_digest="8" * 64,
        airllm_source_revision=req.airllm_source_revision,
        model_repo=OFFICIAL_MODEL_REPO,
        model_revision=OFFICIAL_MODEL_REVISION,
        actual_payload_bytes=100,
        tensor_read_operations=2,
        physical_read_bytes=200,
        elapsed_seconds=10.0,
        process_exit_code=0,
        generated_token_count=1,
        generated_output_sha256="9" * 64,
        lifecycle_measurement_ref="lifecycle:pending-auth",
        host_measurement_ref="host:measurement",
    )
    return replace(value, **changes) if changes else value


def packet(req: OwnerHostC2CanaryRequest, rec: OwnerHostC2CanaryReceipt):
    join = join_owner_host_c2_attempt(request=req, receipt=rec)
    return build_owner_host_lifecycle_return_packet(request=req, receipt=rec, join=join)


class LifecycleReturnCurrentnessDomainTests(unittest.TestCase):
    def test_exact_packet_is_retrievable_and_current_only_in_return_generation(self) -> None:
        req = request()
        out = project_owner_host_lifecycle_return_memory(request=req, receipt=receipt(req))
        node = out["evidence_node"]
        self.assertEqual(EVIDENCE_TYPE, node["evidence_type"])
        self.assertEqual(CURRENTNESS_DOMAIN, node["currentness_domain"])
        self.assertTrue(node["current"])
        self.assertTrue(out["lifecycle_return_current_in_generation"])
        self.assertEqual([node["artifact_ref"]], out["retrieval_admission"]["eligible_artifact_refs"])
        self.assertEqual(
            [node["artifact_ref"]],
            out["lifecycle_return_currentness_admission"]["eligible_artifact_refs"],
        )
        for key in (
            "host_observation_currentness_proven",
            "lifecycle_measurement_currentness_proven",
            "lifecycle_measurement_receipt_present",
            "physical_io_attested",
            "producer_authenticated",
            "lifecycle_registry_admitted",
            "real_w4_policy_winner_proven",
            "full_model_runtime_proven",
            "quality_proven",
            "g2_admitted",
            "host_rank_transition_performed",
            "effect_authority_proven",
            "semantic_truth_proven",
            "native_private_transformer_kv_accessed",
            "semantic_k27_authority_minted",
        ):
            self.assertFalse(out[key], key)

    def test_host_observation_view_rejects_on_use_type_and_domain(self) -> None:
        req = request()
        node = project_owner_host_lifecycle_return_memory(request=req, receipt=receipt(req))["evidence_node"]
        probe = admit_evidence_nodes([node], HOST_OBSERVATION_CURRENTNESS_CONTEXT)
        self.assertEqual([], probe["eligible_artifact_refs"])
        self.assertEqual(CROSS_DOMAIN_REJECTION, probe["excluded_by_artifact_ref"][node["artifact_ref"]])

    def test_w4_measurement_view_rejects_on_use_type_and_domain(self) -> None:
        req = request()
        node = project_owner_host_lifecycle_return_memory(request=req, receipt=receipt(req))["evidence_node"]
        probe = admit_evidence_nodes([node], W4_MEASUREMENT_CURRENTNESS_CONTEXT)
        self.assertEqual([], probe["eligible_artifact_refs"])
        self.assertEqual(CROSS_DOMAIN_REJECTION, probe["excluded_by_artifact_ref"][node["artifact_ref"]])

    def test_stale_and_revoked_nodes_fail_even_in_owned_domain(self) -> None:
        req = request()
        node = project_owner_host_lifecycle_return_memory(request=req, receipt=receipt(req))["evidence_node"]
        stale = copy.deepcopy(node)
        stale.pop("receipt_identity")
        stale["current"] = False
        stale = seal_evidence_node(stale)
        revoked = copy.deepcopy(node)
        revoked.pop("receipt_identity")
        revoked["revoked"] = True
        revoked = seal_evidence_node(revoked)
        stale_probe = admit_evidence_nodes([stale], LIFECYCLE_RETURN_CURRENTNESS_CONTEXT)
        revoked_probe = admit_evidence_nodes([revoked], RETRIEVAL_CONTEXT)
        self.assertEqual(["NOT_CURRENT"], stale_probe["excluded_by_artifact_ref"][stale["artifact_ref"]])
        self.assertEqual(["REVOKED"], revoked_probe["excluded_by_artifact_ref"][revoked["artifact_ref"]])

    def test_attempt_telemetry_change_changes_packet_and_memory_identity(self) -> None:
        req = request()
        left = project_owner_host_lifecycle_return_memory(request=req, receipt=receipt(req))["evidence_node"]
        right = project_owner_host_lifecycle_return_memory(
            request=req,
            receipt=receipt(req, physical_read_bytes=201),
        )["evidence_node"]
        self.assertNotEqual(left["artifact_ref"], right["artifact_ref"])
        self.assertEqual(left["world_ref"], right["world_ref"])

    def test_parent_ceiling_widening_fails_before_memory_projection(self) -> None:
        req = request()
        rec = receipt(req)
        widened = replace(packet(req, rec), g2_admitted=True)
        with self.assertRaisesRegex(ValueError, "LIFECYCLE_RETURN_CEILING_WIDENED:g2_admitted"):
            _node_from_packet(widened)

    def test_exact_packet_digest_is_the_typed_memory_artifact_reference(self) -> None:
        req = request()
        rec = receipt(req)
        exact_packet = packet(req, rec)
        node = project_owner_host_lifecycle_return_memory(request=req, receipt=rec)["evidence_node"]
        self.assertEqual("awj032-lifecycle-return-sha256:" + exact_packet.packet_digest, node["artifact_ref"])
        self.assertEqual(exact_packet.packet_digest, node["artifact_ref_value"])

    def test_public_boundary_has_no_currentness_metric_trust_or_k27_override(self) -> None:
        params = set(inspect.signature(project_owner_host_lifecycle_return_memory).parameters)
        self.assertEqual({"request", "receipt"}, params)
        forbidden = {
            "current", "currentness_domain", "evidence_type", "use_class", "context",
            "cache_hit_ratio", "energy_joules", "peak_resident_bytes", "physical_io_attested",
            "producer_authenticated", "registry", "policy_winner", "g2_admitted",
            "effect_authority", "semantic_truth", "k27_coordinate", "kv_cache",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_projection_is_deterministic(self) -> None:
        req = request()
        rec = receipt(req)
        self.assertEqual(
            project_owner_host_lifecycle_return_memory(request=req, receipt=rec),
            project_owner_host_lifecycle_return_memory(request=req, receipt=rec),
        )


if __name__ == "__main__":
    unittest.main()
