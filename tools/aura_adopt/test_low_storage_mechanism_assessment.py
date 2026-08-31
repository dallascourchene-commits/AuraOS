import unittest

from tools.aura_adopt import low_storage_mechanism_assessment as m


def scenario(**kwargs):
    values = dict(workload_id="fixture-workload", model_ref="model://fixture", runtime_ref="runtime://fixture", execution_environment_ref="env://fixture", prompt_tokens=512, generated_tokens=128, batch_size=1, configured_context_tokens=1024)
    values.update(kwargs)
    return m.BenchmarkScenario(**values)


def metrics(retained, mem=100, startup=10, reopen=10, dl=0, net=0, kv=50, ttft=20, prefill=15, decode_token=2, recompute=5, payload=1000, encode=1, lookup=1):
    return m.MetricSet(payload, retained, mem, startup, encode, reopen, lookup, dl, net, None, kv, ttft, prefill, decode_token, recompute)


def path(responsibility=m.ResponsibilityClass.ARTIFACT_COMPRESSION, **kwargs):
    values = dict(evidence_ref="trace://fixture", source_generation="trace-gen1", currentness_ref="trace-current://1", responsibility=responsibility, candidate_mechanism_observed=True, kv_cache_write_observed=False, kv_cache_read_observed=False)
    values.update(kwargs)
    return m.MeasuredPathEvidence(**values)


def floor(responsibility):
    return tuple(sorted(m.RESPONSIBILITY_METRIC_FLOORS[responsibility]))


def evidence(candidate, baseline, **kwargs):
    responsibility = kwargs.pop("responsibility", m.ResponsibilityClass.ARTIFACT_COMPRESSION)
    supplied_path = kwargs.pop("path_evidence", None)
    default_path_responsibility = responsibility if isinstance(responsibility, m.ResponsibilityClass) else m.ResponsibilityClass.ARTIFACT_COMPRESSION
    values = dict(
        mechanism_id="fixture", mechanism_version="v1", source_ref="repo://fixture", source_generation="gen1", currentness_ref="current://1",
        responsibility=responsibility, responsibility_detail="reduce retained state", platform_scope=("BROWSER",), baseline_id="json", logical_payload_id="payload-A",
        quality_target="predeclared equivalent output quality", scenario=scenario(), required_metrics=floor(default_path_responsibility), candidate=candidate, baseline=baseline,
        path_evidence=supplied_path or path(default_path_responsibility, kv_cache_write_observed=responsibility is m.ResponsibilityClass.TRANSFORMER_KV_CACHE, kv_cache_read_observed=responsibility is m.ResponsibilityClass.TRANSFORMER_KV_CACHE),
        fidelity=m.FidelityClass.EXACT, fidelity_evidence_ref="test://roundtrip", quality_threshold_ref=None, evidence_class=m.EvidenceClass.REPOSITORY_BENCHMARK,
        benchmark_ref="ci://1", counterexample="incompressible payload", trust_update_overhead="same source-currentness check", invalidators=("source-change",),
    )
    values.update(kwargs)
    return m.MechanismEvidence(**values)


class LowStorageMechanismAssessmentTests(unittest.TestCase):
    def test_exact_storage_win_retained(self): self.assertEqual("RETAIN", m.assess(evidence(metrics(50), metrics(100)))["disposition"])
    def test_no_storage_win_demoted(self): self.assertEqual("DEMOTE", m.assess(evidence(metrics(110), metrics(100)))["disposition"])

    def test_payload_size_mismatch_rejected(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50, payload=900), metrics(100, payload=1000))
        self.assertEqual("LOGICAL_PAYLOAD_SIZE_MISMATCH", ctx.exception.code)

    def test_responsibility_is_typed(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), responsibility="TRANSFORMER_KV_CACHE", path_evidence=path())
        self.assertEqual("RESPONSIBILITY_CLASS_REQUIRED", ctx.exception.code)

    def test_path_responsibility_must_match(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), path_evidence=path(m.ResponsibilityClass.COORDINATE_MEMORY))
        self.assertEqual("PATH_RESPONSIBILITY_MISMATCH", ctx.exception.code)

    def test_candidate_mechanism_must_be_observed_on_path(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), path_evidence=path(candidate_mechanism_observed=False))
        self.assertEqual("CANDIDATE_MECHANISM_NOT_OBSERVED_ON_PATH", ctx.exception.code)

    def test_kv_cache_requires_read_and_write_observation(self):
        r = m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), responsibility=r, path_evidence=path(r, kv_cache_write_observed=True, kv_cache_read_observed=False))
        self.assertEqual("KV_CACHE_IN_PATH_EVIDENCE_REQUIRED", ctx.exception.code)

    def test_caller_cannot_remove_responsibility_metric_floor(self):
        r = m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        incomplete = tuple(x for x in floor(r) if x != "decode_ms_per_token")
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), responsibility=r, required_metrics=incomplete)
        self.assertEqual("RESPONSIBILITY_METRIC_FLOOR_MISSING", ctx.exception.code)

    def test_required_metric_unknown_fails_unknown(self):
        r = m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        result = m.assess(evidence(metrics(50, kv=None), metrics(100, kv=100), responsibility=r))
        self.assertEqual("UNKNOWN", result["disposition"]); self.assertIn("REQUIRED_METRIC_UNKNOWN:kv_cache_peak_bytes", result["reasons"])

    def test_zero_baseline_positive_burden_is_conditional(self):
        result = m.assess(evidence(metrics(50, reopen=5), metrics(100, reopen=0)))
        self.assertEqual("CONDITIONAL", result["disposition"]); self.assertIn("ADDED_BURDEN_FROM_ZERO_BASELINE:decode_or_reopen_ms", result["reasons"])

    def test_zero_to_zero_not_added_burden(self): self.assertEqual("RETAIN", m.assess(evidence(metrics(50, reopen=0), metrics(100, reopen=0)))["disposition"])
    def test_hidden_memory_cost_makes_conditional(self): self.assertEqual("CONDITIONAL", m.assess(evidence(metrics(50, mem=250), metrics(100, mem=100)))["disposition"])
    def test_unknown_not_zero(self): self.assertEqual("UNKNOWN", m.assess(evidence(metrics(None), metrics(100), evidence_class=m.EvidenceClass.UNKNOWN, benchmark_ref=None))["disposition"])
    def test_synthetic_cannot_prove_retain(self): self.assertEqual("CONDITIONAL", m.assess(evidence(metrics(50), metrics(100), evidence_class=m.EvidenceClass.SYNTHETIC, benchmark_ref=None))["disposition"])

    def test_literature_report_cannot_prove_local_retain(self):
        result = m.assess(evidence(metrics(50), metrics(100), evidence_class=m.EvidenceClass.LITERATURE_REPORTED, benchmark_ref="arxiv://2402.02750"))
        self.assertEqual("CONDITIONAL", result["disposition"])

    def test_android_measured_requires_typed_host_evidence(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), platform_scope=("ANDROID",), evidence_class=m.EvidenceClass.ANDROID_MEASURED)
        self.assertEqual("ANDROID_HOST_EVIDENCE_REQUIRED", ctx.exception.code)

    def test_android_current_host_binding_does_not_prove_viability(self):
        host = m.HostEvidenceBinding("host://1", "host-gen1", "host-current://1", "CURRENT")
        result = m.assess(evidence(metrics(50), metrics(100), platform_scope=("ANDROID",), evidence_class=m.EvidenceClass.ANDROID_MEASURED, host_evidence=host))
        self.assertEqual("CURRENT_BOUND", result["host_binding_state"]); self.assertFalse(result["device_viability_proven"])

    def test_stale_host_evidence_rejected(self):
        with self.assertRaises(m.AssessmentError) as ctx: m.HostEvidenceBinding("host://1", "host-gen1", "host-current://1", "STALE")
        self.assertEqual("HOST_EVIDENCE_NOT_CURRENT", ctx.exception.code)

    def test_bounded_accepted_can_retain_with_threshold_ref(self):
        result = m.assess(evidence(metrics(50), metrics(100), fidelity=m.FidelityClass.BOUNDED_ACCEPTED, fidelity_evidence_ref="quality://measured", quality_threshold_ref="policy://threshold-v1"))
        self.assertEqual("RETAIN", result["disposition"])

    def test_bounded_accepted_requires_threshold_ref(self):
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), fidelity=m.FidelityClass.BOUNDED_ACCEPTED, fidelity_evidence_ref="quality://measured", quality_threshold_ref=None)
        self.assertEqual("QUALITY_THRESHOLD_REF_REQUIRED", ctx.exception.code)

    def test_lossy_never_plain_retain(self): self.assertEqual("CONDITIONAL", m.assess(evidence(metrics(10), metrics(100), fidelity=m.FidelityClass.BOUNDED_LOSS, fidelity_evidence_ref="quality://1"))["disposition"])

    def test_exact_requires_fidelity_evidence(self):
        with self.assertRaises(m.AssessmentError): evidence(metrics(50), metrics(100), fidelity_evidence_ref=None)

    def test_counterexample_required(self):
        with self.assertRaises(m.AssessmentError): evidence(metrics(50), metrics(100), counterexample="")

    def test_scenario_rejects_workload_over_context(self):
        with self.assertRaises(m.AssessmentError) as ctx: scenario(prompt_tokens=900, generated_tokens=200, configured_context_tokens=1024)
        self.assertEqual("WORKLOAD_EXCEEDS_CONFIGURED_CONTEXT", ctx.exception.code)

    def test_required_metric_name_validated(self):
        required = floor(m.ResponsibilityClass.ARTIFACT_COMPRESSION) + ("imaginary_metric",)
        with self.assertRaises(m.AssessmentError) as ctx: evidence(metrics(50), metrics(100), required_metrics=required)
        self.assertEqual("REQUIRED_METRIC_INVALID", ctx.exception.code)

    def test_kv_hidden_decode_cost_makes_conditional(self):
        r = m.ResponsibilityClass.TRANSFORMER_KV_CACHE
        self.assertEqual("CONDITIONAL", m.assess(evidence(metrics(50, decode_token=5), metrics(100, decode_token=2), responsibility=r))["disposition"])

    def test_coordinate_memory_floor_does_not_require_kv_metrics(self):
        r = m.ResponsibilityClass.COORDINATE_MEMORY
        result = m.assess(evidence(metrics(50, kv=None, ttft=None, prefill=None, decode_token=None, recompute=None), metrics(100, kv=None, ttft=None, prefill=None, decode_token=None, recompute=None), responsibility=r))
        self.assertEqual("RETAIN", result["disposition"])

    def test_inventory_unmapped_is_explicit(self): self.assertEqual("NO_CURRENT_EXECUTABLE_MAPPING_FOUND", m.inventory_status("D2RM", current_code_refs=(), measurement_refs=())["status"])

    def test_identity_stable_and_scenario_bearing(self):
        a = m.assess(evidence(metrics(50), metrics(100))); b = m.assess(evidence(metrics(50), metrics(100))); c = m.assess(evidence(metrics(50), metrics(100), scenario=scenario(prompt_tokens=513)))
        self.assertEqual(a["logical_id"], b["logical_id"]); self.assertNotEqual(a["logical_id"], c["logical_id"])


if __name__ == "__main__": unittest.main()
