import unittest

from tools.aura_adopt import low_storage_mechanism_assessment as m


def scenario(**kwargs):
    values = dict(
        workload_id="fixture-workload",
        model_ref="model://fixture",
        runtime_ref="runtime://fixture",
        execution_environment_ref="env://fixture",
        prompt_tokens=512,
        generated_tokens=128,
        batch_size=1,
        configured_context_tokens=1024,
    )
    values.update(kwargs)
    return m.BenchmarkScenario(**values)


def metrics(
    retained, mem=100, startup=10, encode=1, reopen=10, lookup=1, dl=10, net=0,
    kv=50, ttft=20, prefill=15, decode_token=2, recompute=5, payload=1000,
):
    return m.MetricSet(
        payload, retained, mem, startup, encode, reopen, lookup, dl, net, None,
        kv, ttft, prefill, decode_token, recompute,
    )


def floor(resp):
    return tuple(sorted(m.RESPONSIBILITY_METRIC_FLOORS[resp]))


def path(active=True, **kwargs):
    values = dict(
        mechanism_active=active,
        evidence_ref="trace://kv-path",
        evidence_digest="a" * 64,
        source_generation="gen1",
        currentness_ref="current://1",
    )
    values.update(kwargs)
    return m.MeasuredPathEvidenceV1(**values)


def host(**kwargs):
    values = dict(
        witness_ref="host://witness/1",
        witness_digest="b" * 64,
        source_generation="host-gen1",
        currentness_ref="current://1",
    )
    values.update(kwargs)
    return m.HostWitnessBindingV1(**values)


def evidence(candidate, baseline, **kwargs):
    resp = kwargs.pop("responsibility", m.ResponsibilityClass.ARTIFACT_COMPRESSION)
    values = dict(
        mechanism_id="fixture",
        mechanism_version="v1",
        source_ref="repo://fixture",
        source_generation="gen1",
        currentness_ref="current://1",
        responsibility=resp,
        platform_scope=("BROWSER",),
        baseline_id="json",
        logical_payload_id="payload-A",
        quality_target="predeclared equivalent output quality",
        scenario=scenario(),
        required_metrics=(
            floor(resp)
            if isinstance(resp, m.ResponsibilityClass)
            else floor(m.ResponsibilityClass.ARTIFACT_COMPRESSION)
        ),
        candidate=candidate,
        baseline=baseline,
        fidelity=m.FidelityClass.EXACT,
        fidelity_evidence_ref="test://roundtrip",
        quality_threshold_ref=None,
        evidence_class=m.EvidenceClass.REPOSITORY_BENCHMARK,
        benchmark_ref="ci://1",
        counterexample="incompressible payload",
        trust_update_overhead="same source-currentness check",
        invalidators=("source-change",),
        measured_path=path() if resp is m.ResponsibilityClass.TRANSFORMER_KV_CACHE else None,
    )
    values.update(kwargs)
    return m.MechanismEvidence(**values)


class LowStorageEvidenceFirewallTests(unittest.TestCase):
    def test_artifact_storage_win_retained(self):
        self.assertEqual("RETAIN", m.assess(evidence(metrics(50), metrics(100)))["disposition"])

    def test_no_storage_win_demoted(self):
        self.assertEqual("DEMOTE", m.assess(evidence(metrics(110), metrics(100)))["disposition"])

    def test_payload_size_mismatch_rejected(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(metrics(50, payload=900), metrics(100, payload=1000))
        self.assertEqual("LOGICAL_PAYLOAD_SIZE_MISMATCH", ctx.exception.code)

    def test_responsibility_must_be_typed(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(metrics(50), metrics(100), responsibility="KV")
        self.assertEqual("RESPONSIBILITY_CLASS_REQUIRED", ctx.exception.code)

    def test_caller_cannot_remove_artifact_metric_floor(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(metrics(50), metrics(100), required_metrics=("encoded_or_retained_bytes",))
        self.assertEqual("RESPONSIBILITY_METRIC_FLOOR_MISSING", ctx.exception.code)

    def test_caller_may_add_metrics_above_floor(self):
        e = evidence(
            metrics(50), metrics(100),
            required_metrics=floor(m.ResponsibilityClass.ARTIFACT_COMPRESSION) + ("network_bytes",),
        )
        self.assertEqual("RETAIN", m.assess(e)["disposition"])

    def test_kv_requires_kv_specific_metric_floor(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(
                metrics(50), metrics(100),
                responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
                required_metrics=floor(m.ResponsibilityClass.ARTIFACT_COMPRESSION),
            )
        self.assertEqual("RESPONSIBILITY_METRIC_FLOOR_MISSING", ctx.exception.code)

    def test_kv_measured_path_active_can_retain(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        ))
        self.assertEqual("RETAIN", result["disposition"])
        self.assertTrue(result["transformer_kv_measured_path_proven"])

    def test_kv_cache_disabled_cannot_retain(self):
        result = m.assess(evidence(
            metrics(50), metrics(100),
            responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
            measured_path=path(active=False),
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("TRANSFORMER_KV_MEASURED_PATH_NOT_PROVEN", result["reasons"])

    def test_kv_path_stale_generation_cannot_retain(self):
        result = m.assess(evidence(
            metrics(50), metrics(100),
            responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
            measured_path=path(source_generation="other"),
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_coordinate_memory_does_not_require_kv_metrics(self):
        result = m.assess(evidence(
            metrics(50, kv=None, ttft=None, prefill=None, decode_token=None, recompute=None),
            metrics(100, kv=None, ttft=None, prefill=None, decode_token=None, recompute=None),
            responsibility=m.ResponsibilityClass.COORDINATE_MEMORY,
        ))
        self.assertEqual("RETAIN", result["disposition"])
        self.assertFalse(result["transformer_kv_measured_path_proven"])

    def test_coordinate_memory_missing_lookup_is_unknown(self):
        result = m.assess(evidence(
            metrics(50, lookup=None), metrics(100, lookup=1),
            responsibility=m.ResponsibilityClass.COORDINATE_MEMORY,
        ))
        self.assertEqual("UNKNOWN", result["disposition"])
        self.assertIn("REQUIRED_METRIC_UNKNOWN:lookup_ms", result["reasons"])

    def test_zero_baseline_positive_download_is_explicit_burden(self):
        result = m.assess(evidence(metrics(50, dl=10), metrics(100, dl=0)))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("downloaded_bytes", result["zero_baseline_added_burdens"])
        self.assertIn("ZERO_BASELINE_ADDED_BURDEN:downloaded_bytes", result["reasons"])

    def test_zero_to_zero_not_added_burden(self):
        result = m.assess(evidence(metrics(50, dl=0), metrics(100, dl=0)))
        self.assertNotIn("downloaded_bytes", result["zero_baseline_added_burdens"])

    def test_unknown_is_not_zero_baseline_burden(self):
        result = m.assess(evidence(
            metrics(50, net=None), metrics(100, net=0),
            required_metrics=floor(m.ResponsibilityClass.ARTIFACT_COMPRESSION),
        ))
        self.assertNotIn("network_bytes", result["zero_baseline_added_burdens"])

    def test_gt2x_hidden_memory_cost_conditional(self):
        result = m.assess(evidence(metrics(50, mem=250), metrics(100, mem=100)))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("STORAGE_WIN_WITH_GT2X_MEASURED_LIFECYCLE_COST", result["reasons"])

    def test_required_metric_unknown_fails_unknown(self):
        result = m.assess(evidence(metrics(50, reopen=None), metrics(100, reopen=10)))
        self.assertEqual("UNKNOWN", result["disposition"])
        self.assertIn("REQUIRED_METRIC_UNKNOWN:decode_or_reopen_ms", result["reasons"])

    def test_unknown_evidence_not_zero(self):
        result = m.assess(evidence(
            metrics(None), metrics(100), evidence_class=m.EvidenceClass.UNKNOWN, benchmark_ref=None
        ))
        self.assertEqual("UNKNOWN", result["disposition"])

    def test_synthetic_cannot_prove_retain(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), evidence_class=m.EvidenceClass.SYNTHETIC, benchmark_ref=None
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_literature_cannot_prove_local_retain(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), evidence_class=m.EvidenceClass.LITERATURE_REPORTED,
            benchmark_ref="arxiv://2607.05399",
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_android_measured_requires_typed_host_binding(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(
                metrics(50), metrics(100), platform_scope=("ANDROID",),
                evidence_class=m.EvidenceClass.ANDROID_MEASURED,
            )
        self.assertEqual("ANDROID_HOST_WITNESS_BINDING_REQUIRED", ctx.exception.code)

    def test_android_host_binding_never_proves_device_viability(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), platform_scope=("ANDROID",),
            evidence_class=m.EvidenceClass.ANDROID_MEASURED, host_witness=host(),
        ))
        self.assertFalse(result["device_viability_proven"])
        self.assertTrue(result["host_binding_current"])

    def test_stale_android_host_binding_makes_retain_conditional(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), platform_scope=("ANDROID",),
            evidence_class=m.EvidenceClass.ANDROID_MEASURED,
            host_witness=host(currentness_ref="old"),
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("ANDROID_CURRENT_HOST_BINDING_NOT_PROVEN", result["reasons"])

    def test_bounded_accepted_can_retain_with_threshold(self):
        result = m.assess(evidence(
            metrics(50), metrics(100), fidelity=m.FidelityClass.BOUNDED_ACCEPTED,
            fidelity_evidence_ref="quality://measured", quality_threshold_ref="policy://threshold-v1",
        ))
        self.assertEqual("RETAIN", result["disposition"])

    def test_bounded_loss_never_plain_retain(self):
        result = m.assess(evidence(
            metrics(10), metrics(100), fidelity=m.FidelityClass.BOUNDED_LOSS,
            fidelity_evidence_ref="quality://1",
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_inventory_unmapped_explicit(self):
        result = m.inventory_status("D2RM", current_code_refs=(), measurement_refs=())
        self.assertEqual("NO_CURRENT_EXECUTABLE_MAPPING_FOUND", result["status"])

    def test_identity_binds_responsibility(self):
        artifact = m.assess(evidence(metrics(50), metrics(100)))
        coordinate = m.assess(evidence(
            metrics(50), metrics(100), responsibility=m.ResponsibilityClass.COORDINATE_MEMORY
        ))
        self.assertNotEqual(artifact["logical_id"], coordinate["logical_id"])

    def test_identity_binds_path_evidence(self):
        a = m.assess(evidence(
            metrics(50), metrics(100), responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        ))
        b = m.assess(evidence(
            metrics(50), metrics(100), responsibility=m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
            measured_path=path(evidence_digest="c" * 64),
        ))
        self.assertNotEqual(a["logical_id"], b["logical_id"])


if __name__ == "__main__":
    unittest.main()
