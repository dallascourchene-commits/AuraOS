from __future__ import annotations

import unittest
from dataclasses import replace

from scripts.aura_awj032_owner_host_c2_memory_bridge import (
    CONTRACT_CONTEXT,
    HOST_OBSERVATION_CONTEXT,
    project_owner_host_c2_attempt_memory,
)
from scripts.aura_provenance_corroboration_memory_admission import admit_evidence_nodes
from tools.awj032.glm53_owner_host_c2_handoff import (
    OFFICIAL_MODEL_REPO,
    OFFICIAL_MODEL_REVISION,
    OwnerHostC2CanaryReceipt,
    OwnerHostC2CanaryRequest,
)


def request() -> OwnerHostC2CanaryRequest:
    return OwnerHostC2CanaryRequest(
        w3_proof_logical_id="1" * 64,
        preflight_receipt_digest="2" * 64,
        airllm_source_revision="airllm-exact-rev",
        airllm_security_evidence_digest="3" * 64,
        host_snapshot_digest="4" * 64,
        storage_plan_digest="5" * 64,
        workspace_root="/tmp/aura-awj032-c2",
        max_payload_bytes=1024,
        max_wall_seconds=60,
        effect_admission_ref="effect:owner-gate",
    )


def receipt(
    req: OwnerHostC2CanaryRequest,
    *,
    observation_id: str = "obs-1",
    exit_code: int = 0,
    generated_tokens: int = 1,
) -> OwnerHostC2CanaryReceipt:
    return OwnerHostC2CanaryReceipt(
        request_digest=req.request_digest,
        owner_host_observation_id=observation_id,
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
        process_exit_code=exit_code,
        generated_token_count=generated_tokens,
        generated_output_sha256=("9" * 64 if generated_tokens else None),
        lifecycle_measurement_ref="lifecycle:pending-auth",
        host_measurement_ref="host:measurement",
    )


class OwnerHostC2MemoryBridgeTests(unittest.TestCase):
    def test_valid_attempt_projects_contract_current_evidence_only(self) -> None:
        req = request()
        out = project_owner_host_c2_attempt_memory(request=req, receipt=receipt(req))
        node = out["evidence_node"]
        self.assertEqual("owner-host-c2-contract-join", node["evidence_type"])
        self.assertEqual("contract-generation", node["currentness_domain"])
        self.assertTrue(node["current"])
        self.assertTrue(out["host_observation_admission_rejected"])
        for key in (
            "host_observation_currentness_proven",
            "owner_host_producer_authenticated",
            "lifecycle_registry_satisfied",
            "real_w4_policy_winner_proven",
            "full_model_runtime_proven",
            "g2_admitted",
            "host_rank_transition_performed",
            "effect_authority_proven",
            "native_private_transformer_kv_accessed",
        ):
            self.assertFalse(out[key])

    def test_host_observation_context_excludes_contract_current_node(self) -> None:
        req = request()
        out = project_owner_host_c2_attempt_memory(request=req, receipt=receipt(req))
        node = out["evidence_node"]
        probe = admit_evidence_nodes([node], HOST_OBSERVATION_CONTEXT)
        self.assertEqual([], probe["eligible_artifact_refs"])
        self.assertEqual(
            ["CURRENTNESS_DOMAIN_NOT_ACCEPTED"],
            probe["excluded_by_artifact_ref"][node["artifact_ref"]],
        )

    def test_two_distinct_attempts_same_outcome_corroborate_without_rank(self) -> None:
        req = request()
        left = project_owner_host_c2_attempt_memory(
            request=req, receipt=receipt(req, observation_id="obs-a")
        )["evidence_node"]
        right = project_owner_host_c2_attempt_memory(
            request=req, receipt=receipt(req, observation_id="obs-b")
        )["evidence_node"]
        out = admit_evidence_nodes([left, right], CONTRACT_CONTEXT)
        edge = [row for row in out["relations"] if row["kind"] == "CORROBORATES"][0]
        self.assertTrue(edge["dependency_distinct"])
        self.assertFalse(edge["rank_transition_credit"])
        self.assertEqual(2, out["corroboration_groups"][0]["kappa"])
        self.assertFalse(out["corroboration_groups"][0]["corroboration_count_grants_host_rank"])

    def test_success_and_failure_attempts_are_contradictory_not_last_write_wins(self) -> None:
        req = request()
        success = project_owner_host_c2_attempt_memory(
            request=req,
            receipt=receipt(req, observation_id="obs-ok", exit_code=0, generated_tokens=1),
        )["evidence_node"]
        failure = project_owner_host_c2_attempt_memory(
            request=req,
            receipt=receipt(req, observation_id="obs-fail", exit_code=1, generated_tokens=0),
        )["evidence_node"]
        out = admit_evidence_nodes([success, failure], CONTRACT_CONTEXT)
        self.assertEqual(1, len([row for row in out["relations"] if row["kind"] == "CONTRADICTS"]))
        self.assertFalse(out["last_write_wins_performed"])

    def test_request_receipt_mismatch_fails_before_memory_projection(self) -> None:
        req = request()
        bad = replace(receipt(req), request_digest="f" * 64)
        with self.assertRaises(Exception):
            project_owner_host_c2_attempt_memory(request=req, receipt=bad)

    def test_projection_is_deterministic(self) -> None:
        req = request()
        attempt = receipt(req)
        self.assertEqual(
            project_owner_host_c2_attempt_memory(request=req, receipt=attempt),
            project_owner_host_c2_attempt_memory(request=req, receipt=attempt),
        )


if __name__ == "__main__":
    unittest.main()
