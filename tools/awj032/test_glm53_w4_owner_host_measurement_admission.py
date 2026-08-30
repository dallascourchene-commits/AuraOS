from dataclasses import replace
import inspect
import unittest

from tools.awj032.glm53_w4_owner_host_measurement_admission import (
    OWNER_HOST_CLASS,
    W4HostPhaseCounters,
    W4OwnerHostAttestation,
    W4OwnerHostMeasurementError,
    W4OwnerHostMeasurementObservation,
    W4OwnerHostMeasurementRequest,
    _evaluate_with_registry,
    evaluate_owner_host_measurement,
)


class OwnerHostMeasurementAdmissionTests(unittest.TestCase):
    def request(self, **overrides):
        value = dict(
            scope_ref="owner-thinkpad-wsl:awj032",
            source_generation="glm53-w4-source-generation",
            workload_ref="glm53-expert-trace-A",
            measurement_campaign_ref="campaign-owner-host-001",
            policy_id="baseline-page-directory-lru",
            command_contract_digest="a" * 64,
            logical_expert_bytes_required=1000,
            exposed_io_budget_seconds=2.0,
        )
        value.update(overrides)
        return W4OwnerHostMeasurementRequest(**value)

    def phase(self, name, *, demand=800, aura=200, os_cache=0, other=0, useful=0, waste=0):
        return W4HostPhaseCounters(
            phase=name,
            physical_demand_expert_bytes=demand,
            prefetch_useful_bytes=useful,
            prefetch_waste_bytes=waste,
            aura_cache_avoided_bytes=aura,
            os_cache_avoided_bytes=os_cache,
            other_proven_avoided_bytes=other,
            effective_bandwidth_bytes_per_s=1000.0,
            overlap_seconds=0.0,
            queue_seconds=0.05,
            energy_joules=10.0,
            peak_resident_bytes=4096,
            elapsed_seconds=1.0,
        )

    def observation(self, request=None, **overrides):
        r = request or self.request()
        value = dict(
            request_digest=r.request_digest,
            scope_ref=r.scope_ref,
            source_generation=r.source_generation,
            workload_ref=r.workload_ref,
            measurement_campaign_ref=r.measurement_campaign_ref,
            policy_id=r.policy_id,
            command_contract_digest=r.command_contract_digest,
            runner_class=OWNER_HOST_CLASS,
            runner_instance_ref="owner-host-instance-001",
            attestation_ref="drive:owner-host-attestation-001",
            phases=(self.phase("COLD"), self.phase("WARM"), self.phase("RESTART")),
            source_current=True,
            workload_current=True,
            command_observed_exact=True,
            run_completed=True,
        )
        value.update(overrides)
        return W4OwnerHostMeasurementObservation(**value)

    def registry(self, r, o, **overrides):
        value = dict(
            attestation_ref=o.attestation_ref,
            request_digest=r.request_digest,
            observation_digest=o.observation_digest,
            runner_class=OWNER_HOST_CLASS,
            runner_instance_ref=o.runner_instance_ref,
            measurement_campaign_ref=r.measurement_campaign_ref,
            command_contract_digest=r.command_contract_digest,
            current=True,
            independently_observed=True,
        )
        value.update(overrides)
        return {o.attestation_ref: value}

    def test_public_surface_has_no_caller_registry_or_attestation_override(self):
        params = tuple(inspect.signature(evaluate_owner_host_measurement).parameters)
        self.assertEqual(("request", "observation"), params)

    def test_structurally_valid_observation_waits_without_trusted_registry_pin(self):
        r = self.request()
        o = self.observation(r)
        out = evaluate_owner_host_measurement(r, o)
        self.assertEqual("WAITING_OWNER_HOST_ATTESTATION", out.status)
        self.assertFalse(out.trusted_attestation_found)
        self.assertFalse(out.owner_host_measurement_proven)
        self.assertEqual((), out.phase_preflights)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)

    def test_github_actions_cannot_impersonate_owner_host(self):
        r = self.request()
        o = self.observation(r, runner_class="GITHUB_ACTIONS")
        with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
            evaluate_owner_host_measurement(r, o)
        self.assertEqual("GITHUB_ACTIONS_RUNNER_FORBIDDEN", ctx.exception.code)

    def test_external_benchmark_k27_and_hit_ratio_cannot_be_measurement_authority(self):
        r = self.request()
        for field in (
            "external_benchmark_used_as_measurement",
            "k27_used_as_measurement_authority",
            "cache_hit_ratio_used_as_measurement_authority",
        ):
            with self.subTest(field=field):
                o = self.observation(r, **{field: True})
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    evaluate_owner_host_measurement(r, o)
                self.assertEqual("MEASUREMENT_AUTHORITY_SUBSTITUTION_FORBIDDEN", ctx.exception.code)

    def test_cold_warm_restart_are_all_required_in_order(self):
        r = self.request()
        for phases in (
            (self.phase("COLD"), self.phase("WARM")),
            (self.phase("WARM"), self.phase("COLD"), self.phase("RESTART")),
        ):
            with self.subTest(phases=tuple(p.phase for p in phases)):
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    evaluate_owner_host_measurement(r, self.observation(r, phases=phases))
                self.assertEqual("COLD_WARM_RESTART_PHASES_REQUIRED", ctx.exception.code)

    def test_request_observation_source_workload_campaign_and_command_are_bound(self):
        r = self.request()
        mutations = dict(
            source_generation="other-source",
            workload_ref="other-workload",
            measurement_campaign_ref="other-campaign",
            policy_id="other-policy",
            command_contract_digest="b" * 64,
        )
        for field, value in mutations.items():
            with self.subTest(field=field):
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    evaluate_owner_host_measurement(r, self.observation(r, **{field: value}))
                self.assertEqual("REQUEST_OBSERVATION_BINDING_MISMATCH", ctx.exception.code)

    def test_exact_booleans_reject_integer_truth(self):
        r = self.request()
        for field in ("source_current", "workload_current", "command_observed_exact", "run_completed"):
            with self.subTest(field=field):
                with self.assertRaises(W4OwnerHostMeasurementError):
                    evaluate_owner_host_measurement(r, self.observation(r, **{field: 1}))

    def test_effectful_request_is_rejected(self):
        for field in ("allow_provider_effect", "allow_checkpoint_download", "allow_g2", "authority"):
            with self.subTest(field=field):
                r = self.request(**{field: True})
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    _ = r.request_digest
                self.assertEqual("REQUEST_EFFECT_CEILING_WIDENED", ctx.exception.code)

    def test_trusted_registry_binding_admits_three_phase_preflights_only(self):
        r = self.request()
        o = self.observation(r)
        out = _evaluate_with_registry(r, o, self.registry(r, o))
        self.assertEqual("OWNER_HOST_MEASUREMENT_ADMITTED", out.status)
        self.assertTrue(out.owner_host_measurement_proven)
        self.assertEqual(3, len(out.phase_preflights))
        self.assertEqual(["glm53-expert-trace-A:COLD", "glm53-expert-trace-A:WARM", "glm53-expert-trace-A:RESTART"], [p.workload_ref for p in out.phase_preflights])
        self.assertTrue(all(p.physical_io_attested for p in out.phase_preflights))
        self.assertTrue(all(p.physical_io_attestation_ref.startswith(o.attestation_ref) for p in out.phase_preflights))
        self.assertFalse(out.runtime_mtp_support_proven)
        self.assertFalse(out.end_to_end_usability_proven)
        self.assertFalse(out.quality_proven)
        self.assertFalse(out.g2_admitted)
        self.assertFalse(out.authority)

    def test_attestation_must_bind_exact_observation_not_just_request(self):
        r = self.request()
        o = self.observation(r)
        reg = self.registry(r, o, observation_digest="f" * 64)
        with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
            _evaluate_with_registry(r, o, reg)
        self.assertEqual("TRUSTED_ATTESTATION_BINDING_MISMATCH", ctx.exception.code)

    def test_attestation_must_be_current_and_independent(self):
        r = self.request()
        o = self.observation(r)
        for field, value in (("current", False), ("independently_observed", False)):
            with self.subTest(field=field):
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    _evaluate_with_registry(r, o, self.registry(r, o, **{field: value}))
                self.assertEqual("TRUSTED_ATTESTATION_INVALID", ctx.exception.code)

    def test_physical_byte_accounting_still_flows_through_existing_w4_reducer(self):
        r = self.request()
        bad = self.phase("WARM", demand=700, aura=200)  # computed avoided=300, declared=200
        o = self.observation(r, phases=(self.phase("COLD"), bad, self.phase("RESTART")))
        with self.assertRaises(Exception) as ctx:
            _evaluate_with_registry(r, o, self.registry(r, o))
        self.assertIn("AVOIDED_BYTE_ACCOUNTING_MISMATCH", str(ctx.exception))

    def test_runner_instance_and_command_binding_are_attested(self):
        r = self.request()
        o = self.observation(r)
        for field, value in (("runner_instance_ref", "other-host"), ("command_contract_digest", "b" * 64)):
            with self.subTest(field=field):
                reg = self.registry(r, o, **{field: value})
                with self.assertRaises(W4OwnerHostMeasurementError) as ctx:
                    _evaluate_with_registry(r, o, reg)
                self.assertEqual("TRUSTED_ATTESTATION_BINDING_MISMATCH", ctx.exception.code)


if __name__ == "__main__":
    unittest.main()
