from __future__ import annotations

import copy
import unittest

import low_storage_mechanism_assessment as lsm
import glm_reuse_low_storage_bridge as bridge


def preflight(*, logical=1000, physical=100, **overrides):
    reuse = max(0.0, min(1.0, 1.0 - physical / logical))
    row = {
        "schema": "GLM53HostCanaryPreflightReceiptV1",
        "host_digest": "host:1",
        "storage_plan_digest": "storage:1",
        "io_bound_digest": "io:1",
        "w4_binding_digest": "binding:1",
        "w4_attestation_id": "attest:1",
        "logical_expert_bytes_required": logical,
        "physical_expert_bytes_read": physical,
        "measured_reuse_ratio": reuse,
        "physical_io_amplification": physical > logical,
        "measured_backend_read_seconds": 1.0,
        "measured_physical_read_bytes_per_s": float(physical),
        "cold_nvme_floor_seconds_per_token": 10.0,
        "target_min_reuse_ratio": {},
        "c2_storage_ready": True,
        "c3_storage_ready": False,
        "host_measurement_complete": True,
        "w4_evidence_admissible": True,
        "planning_ready": True,
        "next_canary": "C2_EFFECT_ADMISSION_REQUIRED",
        "execution_authorized": False,
        "effect_authorized": False,
        "g2_admitted": False,
        "large_checkpoint_admitted": False,
        "runtime_execution_proven": False,
        "receipt_digest": "preflight:receipt:1",
    }
    row.update(overrides)
    return row


def scenario():
    return lsm.BenchmarkScenario(
        workload_id="glm53-trace-1",
        model_ref="glm53:pinned",
        runtime_ref="aura:pager",
        execution_environment_ref="thinkpad:wsl:host1",
        prompt_tokens=128,
        generated_tokens=32,
        batch_size=1,
        configured_context_tokens=4096,
    )


def observation(
    *,
    candidate_retained=800,
    baseline_retained=1000,
    candidate_peak=100,
    baseline_peak=100,
    candidate_startup=100.0,
    baseline_startup=100.0,
    candidate_reopen=100.0,
    baseline_reopen=100.0,
    evidence_class=lsm.EvidenceClass.REPOSITORY_BENCHMARK,
):
    return bridge.GLMStorageLifecycleObservationV1(
        observation_ref="obs:1",
        source_generation="gen:1",
        currentness_ref="current:1",
        candidate_retained_bytes=candidate_retained,
        baseline_retained_bytes=baseline_retained,
        candidate_peak_working_memory_bytes=candidate_peak,
        baseline_peak_working_memory_bytes=baseline_peak,
        candidate_startup_ms=candidate_startup,
        baseline_startup_ms=baseline_startup,
        candidate_reopen_ms=candidate_reopen,
        baseline_reopen_ms=baseline_reopen,
        candidate_downloaded_bytes=800,
        baseline_downloaded_bytes=1000,
        candidate_network_bytes=0,
        baseline_network_bytes=0,
        fidelity=lsm.FidelityClass.EXACT,
        fidelity_evidence_ref="fidelity:token-identical",
        evidence_class=evidence_class,
        benchmark_ref="benchmark:storage-lifecycle:1",
        trust_update_overhead="same signed source/update checks as baseline",
        counterexample="cache-hit traces can improve I/O while retained representation is unchanged",
        host_witness_ref="host:thinkpad:1",
    )


def assess(*, pf=None, obs=None):
    return bridge.assess_glm_low_storage_candidate(
        preflight=pf or preflight(),
        storage_observation=obs or observation(),
        scenario=scenario(),
        mechanism_id="aura.glm.expert-reuse",
        mechanism_version="1",
        mechanism_source_ref="repo:glm-pager",
        logical_payload_id="glm53:complete-topology",
        quality_target="token-identical selected-expert traversal",
    )


class GLMReuseLowStorageBridgeTests(unittest.TestCase):
    def test_io_reuse_without_storage_measurement_stays_open_frontier(self):
        frontier = bridge.unresolved_storage_frontier(preflight(logical=1000, physical=100))
        self.assertEqual("STORAGE_LIFECYCLE_MEASUREMENT_REQUIRED", frontier["decision"])
        self.assertAlmostEqual(0.9, frontier["measured_io_reuse_ratio"])
        self.assertFalse(frontier["retained_storage_reduction_proven"])
        self.assertIsNone(frontier["candidate_retained_bytes"])

    def test_high_io_reuse_cannot_fake_low_storage_win(self):
        result = assess(
            pf=preflight(logical=1000, physical=100),
            obs=observation(candidate_retained=1000, baseline_retained=1000),
        )
        self.assertAlmostEqual(0.9, result["glm_io_reuse_ratio"])
        self.assertFalse(result["glm_io_reuse_is_retained_storage_proof"])
        self.assertEqual("DEMOTE", result["disposition"])
        self.assertIn("NO_RETAINED_BYTE_REDUCTION", result["reasons"])

    def test_real_storage_win_can_retain_when_lifecycle_is_bounded(self):
        result = assess(obs=observation(candidate_retained=700, baseline_retained=1000))
        self.assertEqual("RETAIN", result["disposition"])
        self.assertLess(result["ratios"]["retained_bytes"], 1.0)

    def test_storage_win_with_gt2x_reopen_cost_is_conditional(self):
        result = assess(
            obs=observation(
                candidate_retained=700,
                baseline_retained=1000,
                candidate_reopen=250.0,
                baseline_reopen=100.0,
            )
        )
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("STORAGE_WIN_WITH_GT2X_MEASURED_LIFECYCLE_COST", result["reasons"])

    def test_storage_win_with_gt2x_peak_memory_is_conditional(self):
        result = assess(
            obs=observation(
                candidate_retained=700,
                baseline_retained=1000,
                candidate_peak=250,
                baseline_peak=100,
            )
        )
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_synthetic_storage_win_cannot_prove_device_lifecycle_retain(self):
        result = assess(obs=observation(evidence_class=lsm.EvidenceClass.SYNTHETIC))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("SYNTHETIC_CANNOT_PROVE_DEVICE_LIFECYCLE_WIN", result["reasons"])

    def test_physical_io_amplification_is_not_reuse(self):
        pf = preflight(logical=1000, physical=1200)
        validated = bridge.validate_glm_preflight(pf)
        self.assertTrue(validated["physical_io_amplification"])
        self.assertEqual(0.0, validated["measured_reuse_ratio"])

    def test_forged_reuse_ratio_fails_closed(self):
        pf = preflight()
        pf["measured_reuse_ratio"] = 0.5
        with self.assertRaises(bridge.GLMStorageBridgeError) as ctx:
            bridge.validate_glm_preflight(pf)
        self.assertEqual("GLM_REUSE_RATIO_MISMATCH", ctx.exception.code)

    def test_preflight_authority_widening_fails_closed(self):
        for field in (
            "execution_authorized",
            "effect_authorized",
            "g2_admitted",
            "large_checkpoint_admitted",
            "runtime_execution_proven",
        ):
            pf = preflight(**{field: True})
            with self.assertRaises(bridge.GLMStorageBridgeError) as ctx:
                bridge.validate_glm_preflight(pf)
            self.assertEqual("GLM_PREFLIGHT_AUTHORITY_WIDENING", ctx.exception.code)

    def test_incomplete_host_or_w4_measurement_is_rejected(self):
        for field in ("host_measurement_complete", "w4_evidence_admissible"):
            pf = preflight(**{field: False})
            with self.assertRaises(bridge.GLMStorageBridgeError):
                bridge.validate_glm_preflight(pf)

    def test_assessment_identity_binds_preflight_and_storage_observation(self):
        a = assess()
        b = assess()
        self.assertEqual(a["bridge_digest"], b["bridge_digest"])
        changed = observation(candidate_retained=799)
        c = assess(obs=changed)
        self.assertNotEqual(a["bridge_digest"], c["bridge_digest"])

    def test_glm_read_bytes_never_replace_explicit_retained_bytes(self):
        evidence = bridge.compile_glm_low_storage_evidence(
            preflight=preflight(logical=10_000, physical=1),
            storage_observation=observation(candidate_retained=777, baseline_retained=999),
            scenario=scenario(),
            mechanism_id="aura.glm.expert-reuse",
            mechanism_version="1",
            mechanism_source_ref="repo:glm-pager",
            logical_payload_id="glm53:complete-topology",
            quality_target="token-identical selected-expert traversal",
        )
        self.assertEqual(777, evidence.candidate.encoded_or_retained_bytes)
        self.assertEqual(999, evidence.baseline.encoded_or_retained_bytes)
        self.assertNotEqual(1, evidence.candidate.encoded_or_retained_bytes)


if __name__ == "__main__":
    unittest.main()
