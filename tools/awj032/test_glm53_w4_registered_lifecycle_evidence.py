import copy
import inspect
import unittest

from tools.awj032.glm53_w4_cache_policy_decision import compare_cache_policy_to_baseline
from tools.awj032.glm53_w4_owner_host_measurement_admission import (
    OWNER_HOST_CLASS,
    W4HostPhaseCounters,
    W4OwnerHostAttestation,
    W4OwnerHostMeasurementObservation,
    W4OwnerHostMeasurementRequest,
    _evaluate_with_registry as admit_host_with_registry,
)
from tools.awj032.glm53_w4_registered_lifecycle_evidence import (
    W4LifecycleMeasurementReceipt,
    W4LifecycleMeasurementRegistryRecord,
    W4RegisteredLifecycleEvidenceError,
    _admit_with_registry,
    _observation_from_evidence,
    admit_registered_lifecycle_measurement,
    build_registered_cache_policy_observation,
    preflight_digest,
)


class RegisteredLifecycleEvidenceTests(unittest.TestCase):
    def request(self, policy="baseline"):
        return W4OwnerHostMeasurementRequest(
            scope_ref="owner-thinkpad-wsl:awj032", source_generation="glm53-source-gen",
            workload_ref="glm53-expert-trace-A", measurement_campaign_ref="owner-campaign-001",
            policy_id=policy, command_contract_digest=("a" if policy == "baseline" else "b") * 64,
            logical_expert_bytes_required=1000, exposed_io_budget_seconds=2.0,
        )

    def phase(self, name):
        return W4HostPhaseCounters(name, 800, 0, 0, 200, 0, 0, 1000.0, 0.0, 0.0, 10.0, 4096, 1.0)

    def host_admission(self, policy="baseline"):
        r = self.request(policy)
        o = W4OwnerHostMeasurementObservation(
            request_digest=r.request_digest, scope_ref=r.scope_ref, source_generation=r.source_generation,
            workload_ref=r.workload_ref, measurement_campaign_ref=r.measurement_campaign_ref,
            policy_id=r.policy_id, command_contract_digest=r.command_contract_digest,
            runner_class=OWNER_HOST_CLASS, runner_instance_ref=f"owner-host:{policy}",
            attestation_ref=f"drive:host:{policy}", phases=(self.phase("COLD"), self.phase("WARM"), self.phase("RESTART")),
            source_current=True, workload_current=True, command_observed_exact=True, run_completed=True,
        )
        att = W4OwnerHostAttestation(
            attestation_ref=o.attestation_ref, request_digest=r.request_digest,
            observation_digest=o.observation_digest, runner_class=OWNER_HOST_CLASS,
            runner_instance_ref=o.runner_instance_ref, measurement_campaign_ref=r.measurement_campaign_ref,
            command_contract_digest=r.command_contract_digest, current=True, independently_observed=True,
        )
        return admit_host_with_registry(r, o, {o.attestation_ref: att.normalized()})

    def pair(self, policy="baseline", *, phase_index=1, receipt_overrides=None, record_overrides=None):
        host = self.host_admission(policy)
        preflight = host.phase_preflights[phase_index]
        values = dict(
            receipt_ref=f"drive:lifecycle:{policy}", owner_host_request_digest=host.request_digest,
            owner_host_observation_digest=host.observation_digest, owner_host_attestation_ref=host.attestation_ref,
            scope_ref=preflight.scope_ref, source_generation=preflight.source_generation, workload_ref=preflight.workload_ref,
            measurement_campaign_ref=host.measurement_campaign_ref, policy_id=policy,
            preflight_receipt_digest=preflight_digest(preflight), observer_ref="arena:lifecycle-observer",
            observer_generation="observer-gen-1", producer_run_ref="owner-host-run-001", runner_class=OWNER_HOST_CLASS,
            runner_instance_ref=f"owner-host:{policy}", cache_hit_ratio=0.6 if policy == "baseline" else 0.7,
            energy_joules=12.0 if policy == "baseline" else 10.0,
            peak_resident_bytes=5000 if policy == "baseline" else 4800,
            warmup_seconds=2.0 if policy == "baseline" else 1.8,
            restart_seconds=3.0 if policy == "baseline" else 2.8,
            revalidation_seconds=0.3 if policy == "baseline" else 0.2,
            control_overhead_seconds=0.2 if policy == "baseline" else 0.1,
            physical_io_attested=True, correctness_reference_equivalent=True, source_current=True,
            measurement_current=True, independently_observed=True,
        )
        values.update(receipt_overrides or {})
        receipt = W4LifecycleMeasurementReceipt(**values)
        rvalues = dict(
            receipt_ref=receipt.receipt_ref, receipt_digest=receipt.receipt_digest,
            owner_host_request_digest=receipt.owner_host_request_digest,
            owner_host_observation_digest=receipt.owner_host_observation_digest,
            owner_host_attestation_ref=receipt.owner_host_attestation_ref,
            observer_ref=receipt.observer_ref, observer_generation=receipt.observer_generation,
            producer_run_ref=receipt.producer_run_ref, current=True, independently_verified=True,
        )
        rvalues.update(record_overrides or {})
        record = W4LifecycleMeasurementRegistryRecord(**rvalues)
        registry = {receipt.receipt_ref: {"receipt": receipt.normalized(), "registry_record": record.normalized()}}
        return host, preflight, receipt, registry

    def admit(self, policy="baseline"):
        host, preflight, receipt, registry = self.pair(policy)
        evidence = _admit_with_registry(
            lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id=policy,
            preflight=preflight, host_admission=host, registry=registry,
        )
        return host, preflight, receipt, registry, evidence

    def test_public_surface_has_no_caller_registry_or_metrics(self):
        self.assertEqual(
            ("lifecycle_receipt_ref", "expected_policy_id", "preflight", "host_admission"),
            tuple(inspect.signature(admit_registered_lifecycle_measurement).parameters),
        )
        params = tuple(inspect.signature(build_registered_cache_policy_observation).parameters)
        for forbidden in ("registry", "energy_joules", "lifecycle_metrics_attested", "measurement_current", "correctness_reference_equivalent"):
            self.assertNotIn(forbidden, params)

    def test_public_path_waits_for_real_lifecycle_producer_registry(self):
        host, preflight, receipt, _ = self.pair()
        with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
            admit_registered_lifecycle_measurement(
                lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline",
                preflight=preflight, host_admission=host,
            )
        self.assertEqual("LIFECYCLE_MEASUREMENT_PRODUCER_REQUIRED", ctx.exception.code)

    def test_registered_plumbing_builds_pr417_observation(self):
        _, preflight, receipt, _, ev = self.admit()
        obs = _observation_from_evidence(evidence=ev, policy_class="PAGE_DIRECTORY_LRU", preflight=preflight)
        self.assertEqual(receipt.receipt_ref, obs.lifecycle_measurement_attestation_ref)
        self.assertEqual(receipt.energy_joules, obs.energy_joules)
        self.assertTrue(obs.lifecycle_metrics_attested and obs.correctness_reference_equivalent)
        self.assertTrue(obs.source_current and obs.measurement_current)
        self.assertFalse(ev.runtime_execution_proven or ev.quality_proven or ev.g2_admitted or ev.authority)

    def test_metric_mutation_with_stale_registry_digest_fails(self):
        host, preflight, receipt, registry = self.pair()
        bad = copy.deepcopy(registry)
        bad[receipt.receipt_ref]["receipt"]["energy_joules"] = 1.0
        with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
            _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline", preflight=preflight, host_admission=host, registry=bad)
        self.assertEqual("LIFECYCLE_RECEIPT_DIGEST_MISMATCH", ctx.exception.code)

    def test_policy_preflight_and_host_admission_are_bound(self):
        host, preflight, receipt, registry = self.pair()
        with self.assertRaises(W4RegisteredLifecycleEvidenceError):
            _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="other", preflight=preflight, host_admission=host, registry=registry)
        with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
            _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline", preflight=host.phase_preflights[0], host_admission=host, registry=registry)
        self.assertEqual("LIFECYCLE_OWNER_HOST_BINDING_MISMATCH", ctx.exception.code)
        blocked = type(host)(**{**host.__dict__, "status": "WAITING_OWNER_HOST_ATTESTATION", "trusted_attestation_found": False, "owner_host_measurement_proven": False, "phase_preflights": ()})
        with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx2:
            _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline", preflight=preflight, host_admission=blocked, registry=registry)
        self.assertEqual("OWNER_HOST_MEASUREMENT_NOT_ADMITTED", ctx2.exception.code)

    def test_registry_observer_generation_run_and_digest_substitution_fail(self):
        host, preflight, receipt, registry = self.pair()
        for field, value, expected in (
            ("observer_ref", "other", "LIFECYCLE_REGISTRY_BINDING_MISMATCH"),
            ("observer_generation", "other", "LIFECYCLE_REGISTRY_BINDING_MISMATCH"),
            ("producer_run_ref", "other", "LIFECYCLE_REGISTRY_BINDING_MISMATCH"),
            ("receipt_digest", "f" * 64, "LIFECYCLE_RECEIPT_DIGEST_MISMATCH"),
        ):
            bad = copy.deepcopy(registry)
            bad[receipt.receipt_ref]["registry_record"][field] = value
            with self.subTest(field=field):
                with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
                    _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline", preflight=preflight, host_admission=host, registry=bad)
                self.assertEqual(expected, ctx.exception.code)

    def test_stale_revoked_nonindependent_or_authoritative_registry_fails(self):
        for field, value in (("current", False), ("revoked", True), ("independently_verified", False), ("authority", True)):
            with self.subTest(field=field):
                with self.assertRaises(W4RegisteredLifecycleEvidenceError):
                    self.pair(record_overrides={field: value})

    def test_receipt_exact_true_evidence_booleans_are_required(self):
        for field in ("physical_io_attested", "correctness_reference_equivalent", "source_current", "measurement_current", "independently_observed"):
            with self.subTest(field=field):
                with self.assertRaises(W4RegisteredLifecycleEvidenceError):
                    self.pair(receipt_overrides={field: 1})

    def test_receipt_effect_widening_fails(self):
        for field in ("revoked", "external_effect", "runtime_execution_proven", "quality_proven", "g2_admitted", "authority"):
            with self.subTest(field=field):
                with self.assertRaises(W4RegisteredLifecycleEvidenceError):
                    self.pair(receipt_overrides={field: True})

    def test_campaign_source_workload_scope_and_owner_host_identity_are_bound(self):
        for field, value in (
            ("measurement_campaign_ref", "other-campaign"), ("source_generation", "other-source"),
            ("workload_ref", "other-workload"), ("scope_ref", "other-scope"),
            ("owner_host_attestation_ref", "other-attestation"),
            ("owner_host_request_digest", "f" * 64), ("owner_host_observation_digest", "e" * 64),
        ):
            host, preflight, receipt, registry = self.pair(receipt_overrides={field: value})
            with self.subTest(field=field):
                with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
                    _admit_with_registry(lifecycle_receipt_ref=receipt.receipt_ref, expected_policy_id="baseline", preflight=preflight, host_admission=host, registry=registry)
                self.assertEqual("LIFECYCLE_OWNER_HOST_BINDING_MISMATCH", ctx.exception.code)

    def test_evidence_cannot_be_rebound_to_other_preflight(self):
        host, preflight, _, _, ev = self.admit()
        with self.assertRaises(W4RegisteredLifecycleEvidenceError) as ctx:
            _observation_from_evidence(evidence=ev, policy_class="PAGE_DIRECTORY_LRU", preflight=host.phase_preflights[0])
        self.assertEqual("REGISTERED_LIFECYCLE_PREFLIGHT_MISMATCH", ctx.exception.code)

    def test_two_registered_observations_feed_existing_pareto_comparator(self):
        observations = []
        for policy in ("baseline", "candidate"):
            _, preflight, _, _, ev = self.admit(policy)
            observations.append(_observation_from_evidence(evidence=ev, policy_class="PAGE_DIRECTORY_LRU", preflight=preflight))
        out = compare_cache_policy_to_baseline(baseline=observations[0], candidate=observations[1])
        self.assertEqual("CANDIDATE_PARETO_DOMINATES_BASELINE", out.relation)
        self.assertEqual("candidate", out.retained_policy_id)
        self.assertFalse(out.g2_admitted or out.authority)


if __name__ == "__main__":
    unittest.main()
