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
    retained, mem=100, startup=10, reopen=10, dl=0, net=0,
    kv=50, ttft=20, prefill=15, decode_token=2, recompute=5,
):
    return m.MetricSet(
        1000, retained, mem, startup, 1, reopen, 1, dl, net, None,
        kv, ttft, prefill, decode_token, recompute,
    )


def evidence(candidate, baseline, **kwargs):
    values = dict(
        mechanism_id="fixture",
        mechanism_version="v1",
        source_ref="repo://fixture",
        source_generation="gen1",
        currentness_ref="current://1",
        responsibility="reduce retained state",
        platform_scope=("BROWSER",),
        baseline_id="json",
        logical_payload_id="payload-A",
        quality_target="predeclared equivalent output quality",
        scenario=scenario(),
        required_metrics=("encoded_or_retained_bytes", "peak_working_memory_bytes"),
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
    )
    values.update(kwargs)
    return m.MechanismEvidence(**values)


class LowStorageMechanismAssessmentTests(unittest.TestCase):
    def test_exact_storage_win_retained(self):
        self.assertEqual("RETAIN", m.assess(evidence(metrics(50), metrics(100)))["disposition"])

    def test_no_storage_win_demoted(self):
        self.assertEqual("DEMOTE", m.assess(evidence(metrics(110), metrics(100)))["disposition"])

    def test_hidden_memory_cost_makes_conditional(self):
        result = m.assess(evidence(metrics(50, mem=250), metrics(100, mem=100)))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("STORAGE_WIN_WITH_GT2X_MEASURED_LIFECYCLE_COST", result["reasons"])

    def test_required_metric_unknown_fails_unknown(self):
        result = m.assess(evidence(
            metrics(50, kv=None), metrics(100, kv=100),
            required_metrics=("encoded_or_retained_bytes", "kv_cache_peak_bytes"),
        ))
        self.assertEqual("UNKNOWN", result["disposition"])
        self.assertIn("REQUIRED_METRIC_UNKNOWN:kv_cache_peak_bytes", result["reasons"])

    def test_unknown_not_zero(self):
        result = m.assess(
            evidence(metrics(None), metrics(100), evidence_class=m.EvidenceClass.UNKNOWN, benchmark_ref=None)
        )
        self.assertEqual("UNKNOWN", result["disposition"])
        self.assertIsNone(result["ratios"]["retained_bytes"])

    def test_synthetic_cannot_prove_retain(self):
        result = m.assess(
            evidence(metrics(50), metrics(100), evidence_class=m.EvidenceClass.SYNTHETIC, benchmark_ref=None)
        )
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_literature_report_cannot_prove_local_retain(self):
        result = m.assess(
            evidence(
                metrics(50), metrics(100),
                evidence_class=m.EvidenceClass.LITERATURE_REPORTED,
                benchmark_ref="arxiv://2402.02750",
            )
        )
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("LITERATURE_CANNOT_PROVE_LOCAL_DEVICE_LIFECYCLE_WIN", result["reasons"])

    def test_android_requires_host_witness_for_retain(self):
        result = m.assess(evidence(metrics(50), metrics(100), platform_scope=("ANDROID",)))
        self.assertEqual("CONDITIONAL", result["disposition"])
        self.assertIn("ANDROID_VIABILITY_NOT_PROVEN_WITHOUT_HOST_WITNESS", result["reasons"])

    def test_android_measured_requires_witness(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(
                metrics(50), metrics(100), platform_scope=("ANDROID",),
                evidence_class=m.EvidenceClass.ANDROID_MEASURED,
            )
        self.assertEqual("ANDROID_HOST_WITNESS_REQUIRED", ctx.exception.code)

    def test_bounded_accepted_can_retain_with_threshold_ref(self):
        result = m.assess(evidence(
            metrics(50), metrics(100),
            fidelity=m.FidelityClass.BOUNDED_ACCEPTED,
            fidelity_evidence_ref="quality://measured",
            quality_threshold_ref="policy://threshold-v1",
        ))
        self.assertEqual("RETAIN", result["disposition"])

    def test_bounded_accepted_requires_threshold_ref(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(
                metrics(50), metrics(100),
                fidelity=m.FidelityClass.BOUNDED_ACCEPTED,
                fidelity_evidence_ref="quality://measured",
                quality_threshold_ref=None,
            )
        self.assertEqual("QUALITY_THRESHOLD_REF_REQUIRED", ctx.exception.code)

    def test_lossy_never_plain_retain(self):
        result = m.assess(
            evidence(
                metrics(10), metrics(100), fidelity=m.FidelityClass.BOUNDED_LOSS,
                fidelity_evidence_ref="quality://1",
            )
        )
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_exact_requires_fidelity_evidence(self):
        with self.assertRaises(m.AssessmentError):
            evidence(metrics(50), metrics(100), fidelity_evidence_ref=None)

    def test_counterexample_required(self):
        with self.assertRaises(m.AssessmentError):
            evidence(metrics(50), metrics(100), counterexample="")

    def test_scenario_rejects_workload_over_context(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            scenario(prompt_tokens=900, generated_tokens=200, configured_context_tokens=1024)
        self.assertEqual("WORKLOAD_EXCEEDS_CONFIGURED_CONTEXT", ctx.exception.code)

    def test_required_metric_name_validated(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            evidence(metrics(50), metrics(100), required_metrics=("imaginary_metric",))
        self.assertEqual("REQUIRED_METRIC_INVALID", ctx.exception.code)

    def test_kv_hidden_decode_cost_makes_conditional(self):
        result = m.assess(evidence(
            metrics(50, decode_token=5), metrics(100, decode_token=2),
            required_metrics=(
                "encoded_or_retained_bytes", "kv_cache_peak_bytes",
                "ttft_ms", "decode_ms_per_token",
            ),
        ))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_inventory_unmapped_is_explicit(self):
        result = m.inventory_status("D2RM", current_code_refs=(), measurement_refs=())
        self.assertEqual("NO_CURRENT_EXECUTABLE_MAPPING_FOUND", result["status"])

    def test_identity_stable_and_scenario_bearing(self):
        a = m.assess(evidence(metrics(50), metrics(100)))
        b = m.assess(evidence(metrics(50), metrics(100)))
        c = m.assess(evidence(metrics(50), metrics(100), scenario=scenario(prompt_tokens=513)))
        self.assertEqual(a["logical_id"], b["logical_id"])
        self.assertNotEqual(a["logical_id"], c["logical_id"])


if __name__ == "__main__":
    unittest.main()
