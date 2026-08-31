from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

from tools.k27_astge_thinkpad_owner_host_benchmark import (
    PHASES,
    PR459_REFERENCE_RUN,
    PR459_REFERENCE_SHA,
    PR477_SAFE_RUN,
    PR477_SAFE_SHA,
    ThinkPadASTGEBenchmarkPhaseSample,
    ThinkPadASTGEBenchmarkRequest,
    ThinkPadBenchmarkContractError,
    admit_thinkpad_owner_host_benchmark,
)

D = "ab" * 32
E = "cd" * 32
F = "12" * 32
G = "34" * 32


def request(**changes):
    value = ThinkPadASTGEBenchmarkRequest(
        graph_sha256=D,
        source_fixture_sha256=E,
        root_node_ids=(0, 17, 99),
        max_depth=3,
        iterations=10,
        implementation_generation=PR477_SAFE_SHA,
        runner_generation="thinkpad-wsl-runner:v1",
        host_snapshot_digest=F,
        storage_plan_digest=G,
    )
    return replace(value, **changes) if changes else value


def samples(req=None, *, with_device=False):
    req = req or request()

    def phase(
        name,
        process,
        elapsed,
        process_before,
        process_after,
        minor_before,
        minor_after,
        major_before,
        major_after,
        requests,
        hits,
        misses,
        device_before=None,
        device_after=None,
    ):
        return ThinkPadASTGEBenchmarkPhaseSample(
            phase=name,
            request_digest=req.request_digest,
            query_sequence_sha256=req.query_sequence_sha256,
            process_identity=process,
            elapsed_ns=elapsed,
            query_count=req.query_count_per_phase,
            process_read_bytes_before=process_before,
            process_read_bytes_after=process_after,
            minor_faults_before=minor_before,
            minor_faults_after=minor_after,
            major_faults_before=major_before,
            major_faults_after=major_after,
            astge_page_requests=requests,
            astge_cache_hits=hits,
            astge_cache_misses=misses,
            device_read_bytes_before=device_before,
            device_read_bytes_after=device_after,
        )

    device = ((1_000_000, 1_500_000), (1_500_000, 1_550_000), (2_000_000, 2_350_000))
    if not with_device:
        device = ((None, None), (None, None), (None, None))

    return (
        phase(
            PHASES[0], "pid:100", 30_000_000, 100, 5100, 10, 90, 0, 8,
            50, 5, 45, *device[0]
        ),
        phase(
            PHASES[1], "pid:100", 10_000_000, 5100, 5300, 90, 100, 8, 8,
            50, 48, 2, *device[1]
        ),
        phase(
            PHASES[2], "pid:101", 22_000_000, 0, 3000, 0, 50, 0, 4,
            50, 10, 40, *device[2]
        ),
    )


class ThinkPadASTGEBenchmarkContractTests(unittest.TestCase):
    def assert_code(self, code, fn):
        with self.assertRaises(ThinkPadBenchmarkContractError) as ctx:
            fn()
        self.assertEqual(code, ctx.exception.code)

    def admit(self, req=None, phase_samples=None):
        req = req or request()
        return admit_thinkpad_owner_host_benchmark(
            request=req,
            samples=phase_samples or samples(req),
            host_observation_id="thinkpad-wsl:astge-bench:001",
            runner_identity="aura-owner-host-benchmark-runner",
        )

    def test_exact_three_phase_same_graph_contract(self):
        receipt = self.admit()
        self.assertTrue(receipt.same_graph_workload_proven)
        self.assertTrue(receipt.process_cold_scope_proven)
        self.assertTrue(receipt.process_warm_same_process_proven)
        self.assertTrue(receipt.restart_new_process_proven)
        self.assertEqual(3, len(receipt.phase_summaries))
        self.assertEqual(50, receipt.phase_summaries[0]["astge_page_requests"])
        self.assertEqual(5000, receipt.phase_summaries[0]["process_read_bytes_delta"])

    def test_process_cold_is_not_os_or_device_cold(self):
        receipt = self.admit()
        self.assertFalse(receipt.os_page_cache_cold_proven)
        self.assertFalse(receipt.device_cache_cold_proven)
        self.assertFalse(receipt.physical_io_attested)

    def test_device_counter_delta_still_does_not_authenticate_physical_io(self):
        req = request()
        receipt = self.admit(req, samples(req, with_device=True))
        self.assertGreater(receipt.phase_summaries[0]["device_read_bytes_delta"], 0)
        self.assertFalse(receipt.device_counter_is_exclusive_to_benchmark)
        self.assertFalse(receipt.physical_io_attested)
        self.assertFalse(receipt.producer_authenticated)

    def test_warm_speedup_does_not_mint_winner(self):
        receipt = self.admit()
        cold = receipt.phase_summaries[0]["elapsed_ns"]
        warm = receipt.phase_summaries[1]["elapsed_ns"]
        self.assertLess(warm, cold)
        self.assertFalse(receipt.real_performance_winner_proven)
        self.assertFalse(receipt.w4_admitted)

    def test_query_sequence_mismatch_fails_before_comparison(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[1] = replace(phase_samples[1], query_sequence_sha256=D)
        self.assert_code(
            "QUERY_SEQUENCE_MISMATCH",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_request_digest_mismatch_fails(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[2] = replace(phase_samples[2], request_digest=D)
        self.assert_code(
            "PHASE_REQUEST_DIGEST_MISMATCH",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_cold_and_warm_require_same_process(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[1] = replace(phase_samples[1], process_identity="pid:999")
        self.assert_code(
            "PROCESS_WARM_MUST_REUSE_COLD_PROCESS",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_restart_requires_new_process(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[2] = replace(phase_samples[2], process_identity="pid:100")
        self.assert_code(
            "RESTART_MUST_USE_NEW_PROCESS",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_process_counter_rollback_fails(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[0] = replace(
            phase_samples[0],
            process_read_bytes_before=5000,
            process_read_bytes_after=4999,
        )
        self.assert_code(
            "PROCESS_READ_COUNTER_ROLLBACK",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_cache_accounting_must_close(self):
        req = request()
        phase_samples = list(samples(req))
        phase_samples[0] = replace(phase_samples[0], astge_cache_hits=4)
        self.assert_code(
            "ASTGE_CACHE_ACCOUNTING_MISMATCH",
            lambda: self.admit(req, tuple(phase_samples)),
        )

    def test_device_counter_pair_is_optional_but_cannot_be_partial(self):
        req = request()
        base = samples(req)[0]
        self.assert_code(
            "PARTIAL_DEVICE_COUNTER_PAIR",
            lambda: replace(base, device_read_bytes_before=1, device_read_bytes_after=None),
        )

    def test_request_refuses_unproved_coldness_and_authority(self):
        self.assert_code(
            "UNPROVEN_COLDNESS_REQUIREMENT_FORBIDDEN",
            lambda: request(os_page_cache_cold_required=True),
        )
        self.assert_code(
            "REQUEST_AUTHORITY_WIDENING_FORBIDDEN",
            lambda: request(physical_io_claim_requested=True),
        )
        self.assert_code(
            "REQUEST_AUTHORITY_WIDENING_FORBIDDEN",
            lambda: request(performance_winner_claim_requested=True),
        )

    def test_public_admission_has_no_physical_or_policy_override(self):
        params = set(inspect.signature(admit_thinkpad_owner_host_benchmark).parameters)
        self.assertEqual(
            {"request", "samples", "host_observation_id", "runner_identity"}, params
        )
        forbidden = {
            "os_page_cache_cold",
            "device_cache_cold",
            "physical_io_attested",
            "producer_authenticated",
            "w4_admitted",
            "performance_winner",
            "effect_authority",
            "k27_authority",
            "native_kv_cache",
        }
        self.assertTrue(params.isdisjoint(forbidden))

    def test_parent_evidence_generations_are_pinned(self):
        self.assertEqual(
            "a71d1c55af84973a29b28fdfa3db157056780e92", PR459_REFERENCE_SHA
        )
        self.assertEqual(33343082922, PR459_REFERENCE_RUN)
        self.assertEqual(
            "3d8f1e83fff13e622042543ca23c486008e19944", PR477_SAFE_SHA
        )
        self.assertEqual(33344540826, PR477_SAFE_RUN)

    def test_receipt_identity_is_deterministic(self):
        first = self.admit()
        second = self.admit()
        self.assertEqual(first.to_dict(), second.to_dict())
        self.assertEqual(first.receipt_digest, second.receipt_digest)
        self.assertEqual(64, len(first.receipt_digest))


if __name__ == "__main__":
    unittest.main()
