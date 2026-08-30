import unittest

from tools.aura_adopt import low_storage_mechanism_assessment as m


def metrics(retained, mem=100, startup=10, reopen=10, dl=0, net=0):
    return m.MetricSet(1000, retained, mem, startup, 1, reopen, 1, dl, net, None)


def evidence(candidate, baseline, **kwargs):
    values = dict(
        mechanism_id="fixture",
        mechanism_version="v1",
        source_ref="repo://fixture",
        source_generation="gen1",
        currentness_ref="current://1",
        responsibility="store recipe state",
        platform_scope=("BROWSER",),
        baseline_id="json",
        logical_payload_id="payload-A",
        quality_target="byte-exact reconstruction",
        candidate=candidate,
        baseline=baseline,
        fidelity=m.FidelityClass.EXACT,
        fidelity_evidence_ref="test://roundtrip",
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

    def test_inventory_unmapped_is_explicit(self):
        result = m.inventory_status("D2RM", current_code_refs=(), measurement_refs=())
        self.assertEqual("NO_CURRENT_EXECUTABLE_MAPPING_FOUND", result["status"])

    def test_identity_stable_and_measurement_bearing(self):
        a = m.assess(evidence(metrics(50), metrics(100)))
        b = m.assess(evidence(metrics(50), metrics(100)))
        c = m.assess(evidence(metrics(49), metrics(100)))
        self.assertEqual(a["logical_id"], b["logical_id"])
        self.assertNotEqual(a["logical_id"], c["logical_id"])


if __name__ == "__main__":
    unittest.main()
