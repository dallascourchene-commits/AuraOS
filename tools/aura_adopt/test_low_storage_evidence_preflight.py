import unittest

from tools.aura_adopt import low_storage_mechanism_assessment as m
from tools.aura_adopt.low_storage_evidence_preflight import (
    ExternalEvidenceBindingV1,
    preflight_assess,
)


def scenario():
    return m.BenchmarkScenario(
        workload_id="fixture-workload",
        model_ref="model://fixture",
        runtime_ref="runtime://fixture",
        execution_environment_ref="env://fixture",
        prompt_tokens=512,
        generated_tokens=128,
        batch_size=1,
        configured_context_tokens=1024,
    )


def metrics(retained=50, **kwargs):
    values = dict(
        logical_payload_bytes=1000,
        encoded_or_retained_bytes=retained,
        peak_working_memory_bytes=100,
        startup_ms=10,
        encode_ms=1,
        decode_or_reopen_ms=10,
        lookup_ms=1,
        downloaded_bytes=0,
        network_bytes=0,
        energy_proxy=None,
        kv_cache_peak_bytes=50,
        ttft_ms=20,
        prefill_ms=15,
        decode_ms_per_token=2,
        recompute_or_cache_load_ms=5,
    )
    values.update(kwargs)
    return m.MetricSet(**values)


def path(resp=m.ResponsibilityClass.ARTIFACT_COMPRESSION):
    return m.MeasuredPathEvidence(
        evidence_ref="trace://1",
        source_generation="g1",
        currentness_ref="cur1",
        responsibility=resp,
        candidate_mechanism_observed=True,
        kv_cache_write_observed=resp is m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
        kv_cache_read_observed=resp is m.ResponsibilityClass.TRANSFORMER_KV_CACHE,
    )


def host():
    return m.HostEvidenceBinding(
        witness_ref="host://1",
        source_generation="hg1",
        currentness_ref="hcur1",
        currentness_status="CURRENT",
    )


def evidence(*, candidate=None, baseline=None, required_metrics=None, resp=m.ResponsibilityClass.ARTIFACT_COMPRESSION, platform=("BROWSER",), host_evidence=None):
    floor = tuple(sorted(m.RESPONSIBILITY_METRIC_FLOORS[resp]))
    return m.MechanismEvidence(
        mechanism_id="fixture",
        mechanism_version="v1",
        source_ref="repo://fixture",
        source_generation="g1",
        currentness_ref="cur1",
        responsibility=resp,
        responsibility_detail="bounded fixture",
        platform_scope=platform,
        baseline_id="baseline",
        logical_payload_id="payload-A",
        quality_target="equivalent output",
        scenario=scenario(),
        required_metrics=required_metrics or floor,
        candidate=candidate or metrics(50),
        baseline=baseline or metrics(100),
        path_evidence=path(resp),
        fidelity=m.FidelityClass.EXACT,
        fidelity_evidence_ref="quality://1",
        quality_threshold_ref=None,
        evidence_class=m.EvidenceClass.REPOSITORY_BENCHMARK,
        benchmark_ref="ci://1",
        counterexample="incompressible payload",
        trust_update_overhead="currentness check",
        invalidators=("source-change",),
        host_evidence=host_evidence,
    )


def binding(ref="trace://1", digest="a" * 64, gen="g1", cur="cur1"):
    return ExternalEvidenceBindingV1(ref, digest, gen, cur)


class LowStorageEvidencePreflightTests(unittest.TestCase):
    def test_delegates_to_canonical_assessment(self):
        result = preflight_assess(evidence(), path_binding=binding())
        self.assertTrue(result["canonical_assessment_logical_id"].startswith("lsm-"))
        self.assertFalse(result["effect_authorized"])
        self.assertFalse(result["evidence_authenticated"])

    def test_path_digest_must_be_exact_sha256(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            binding(digest="not-a-digest")
        self.assertEqual("EVIDENCE_DIGEST_INVALID", ctx.exception.code)

    def test_path_ref_mismatch_refused(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(evidence(), path_binding=binding(ref="trace://other"))
        self.assertEqual("PATH_EVIDENCE_REF_MISMATCH", ctx.exception.code)

    def test_path_generation_mismatch_refused(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(evidence(), path_binding=binding(gen="g2"))
        self.assertEqual("PATH_EVIDENCE_GENERATION_MISMATCH", ctx.exception.code)

    def test_path_currentness_mismatch_refused(self):
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(evidence(), path_binding=binding(cur="old"))
        self.assertEqual("PATH_EVIDENCE_CURRENTNESS_MISMATCH", ctx.exception.code)

    def test_hidden_network_zero_to_positive_must_be_admitted(self):
        e = evidence(candidate=metrics(50, network_bytes=5), baseline=metrics(100, network_bytes=0))
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(e, path_binding=binding())
        self.assertEqual("ZERO_BASELINE_BURDEN_NOT_ADMITTED", ctx.exception.code)
        self.assertIn("network_bytes", ctx.exception.detail)

    def test_hidden_download_zero_to_positive_must_be_admitted(self):
        e = evidence(candidate=metrics(50, downloaded_bytes=5), baseline=metrics(100, downloaded_bytes=0))
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(e, path_binding=binding())
        self.assertEqual("ZERO_BASELINE_BURDEN_NOT_ADMITTED", ctx.exception.code)
        self.assertIn("downloaded_bytes", ctx.exception.detail)

    def test_declared_zero_baseline_burden_passes_to_parent(self):
        floor = tuple(sorted(m.RESPONSIBILITY_METRIC_FLOORS[m.ResponsibilityClass.ARTIFACT_COMPRESSION]))
        e = evidence(
            candidate=metrics(50, network_bytes=5),
            baseline=metrics(100, network_bytes=0),
            required_metrics=floor + ("network_bytes",),
        )
        result = preflight_assess(e, path_binding=binding())
        self.assertIn("network_bytes", result["all_zero_baseline_added_burdens"])
        self.assertEqual("CONDITIONAL", result["canonical_assessment"]["disposition"])

    def test_host_evidence_requires_digest_binding(self):
        e = evidence(platform=("ANDROID",), host_evidence=host())
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(e, path_binding=binding())
        self.assertEqual("HOST_EVIDENCE_DIGEST_BINDING_REQUIRED", ctx.exception.code)

    def test_host_binding_exact_identity_preserves_no_device_claim(self):
        e = evidence(platform=("ANDROID",), host_evidence=host())
        result = preflight_assess(
            e,
            path_binding=binding(),
            host_binding=binding("host://1", "b" * 64, "hg1", "hcur1"),
        )
        self.assertEqual("b" * 64, result["host_binding"]["evidence_digest"])
        self.assertFalse(result["device_viability_proven"])
        self.assertFalse(result["canonical_assessment"]["device_viability_proven"])

    def test_host_currentness_mismatch_refused(self):
        e = evidence(platform=("ANDROID",), host_evidence=host())
        with self.assertRaises(m.AssessmentError) as ctx:
            preflight_assess(
                e,
                path_binding=binding(),
                host_binding=binding("host://1", "b" * 64, "hg1", "old"),
            )
        self.assertEqual("HOST_EVIDENCE_CURRENTNESS_MISMATCH", ctx.exception.code)

    def test_preflight_digest_binds_external_digest(self):
        e = evidence()
        a = preflight_assess(e, path_binding=binding(digest="a" * 64))
        b = preflight_assess(e, path_binding=binding(digest="b" * 64))
        self.assertNotEqual(a["preflight_digest"], b["preflight_digest"])
        self.assertEqual(a["canonical_assessment_logical_id"], b["canonical_assessment_logical_id"])


if __name__ == "__main__":
    unittest.main()
