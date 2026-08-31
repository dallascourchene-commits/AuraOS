from pathlib import Path
import hashlib
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import k27_spatial_display_sim_benchmark_contract as bench


PARENTS = (
    "1l8FLO6a0ebJX1D4L2VP5PThii4P_vcGGrGMxBHYy_Ew",
    "github:pr597@a68f3bc28c2398208d75bd72b18485615fe6e058",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request(**overrides):
    values = dict(
        imported_source_sha256="56d8593284d37ce03a2762dedc2390878ee6d271a0f1f100a5e245ad01080d6d",
        component="PHASE_STEERING", implementation_generation="optics-ref-v1",
        runtime_generation="python-3.12-env-1", environment_sha256=sha(b"env"),
        input_fixture_sha256=sha(b"fixture"), device_selector="CPU",
        width_px=512, height_px=512, precision="float64-reference",
        warmup_iterations=5, measured_iterations=100, candidate_latency_claim_ns=2_000_000,
    )
    values.update(overrides)
    return bench.SimulationBenchmarkRequest(**values)


def samples(req, **overrides):
    digest = req.digest()
    rows = [
        bench.SimulationPhaseSample(
            phase="PROCESS_COLD", request_sha256=digest, process_identity="proc-A",
            observed_runtime_device="generic-cpu", observed_runtime_generation=req.runtime_generation,
            iterations=req.measured_iterations, elapsed_total_ns=300_000_000,
            output_sha256=sha(b"cold-output"),
        ),
        bench.SimulationPhaseSample(
            phase="PROCESS_WARM", request_sha256=digest, process_identity="proc-A",
            observed_runtime_device="generic-cpu", observed_runtime_generation=req.runtime_generation,
            iterations=req.measured_iterations, elapsed_total_ns=150_000_000,
            output_sha256=sha(b"warm-output"),
        ),
        bench.SimulationPhaseSample(
            phase="RESTART", request_sha256=digest, process_identity="proc-B",
            observed_runtime_device="generic-cpu", observed_runtime_generation=req.runtime_generation,
            iterations=req.measured_iterations, elapsed_total_ns=250_000_000,
            output_sha256=sha(b"restart-output"),
        ),
    ]
    for index, changes in overrides.items():
        idx = int(index)
        rows[idx] = bench.SimulationPhaseSample(**{**rows[idx].__dict__, **changes})
    return tuple(rows)


class SpatialDisplaySimulationBenchmarkTests(unittest.TestCase):
    def test_exact_three_phase_fixture_admits_software_measurement_only(self):
        req = request()
        gate = bench.validate_simulation_samples(request=req, samples=samples(req))
        self.assertTrue(gate.admitted_software_measurement)
        self.assertTrue(gate.process_phase_semantics_exact)
        self.assertTrue(gate.candidate_threshold_met_in_warm_phase)
        self.assertFalse(gate.thinkpad_identity_proven)
        self.assertFalse(gate.physical_optics_proven)

    def test_phase_order_mismatch_rejects(self):
        req = request()
        rows = list(samples(req))
        rows[0], rows[1] = rows[1], rows[0]
        gate = bench.validate_simulation_samples(request=req, samples=rows)
        self.assertIn("PHASE_ORDER_MISMATCH", gate.refusals)

    def test_cold_and_warm_must_share_process(self):
        req = request()
        gate = bench.validate_simulation_samples(
            request=req, samples=samples(req, **{"1": {"process_identity": "proc-C"}})
        )
        self.assertIn("PROCESS_COLD_WARM_RESTART_IDENTITY_MISMATCH", gate.refusals)

    def test_restart_must_use_new_process(self):
        req = request()
        gate = bench.validate_simulation_samples(
            request=req, samples=samples(req, **{"2": {"process_identity": "proc-A"}})
        )
        self.assertIn("PROCESS_COLD_WARM_RESTART_IDENTITY_MISMATCH", gate.refusals)

    def test_request_identity_mismatch_rejects(self):
        req = request()
        gate = bench.validate_simulation_samples(
            request=req, samples=samples(req, **{"2": {"request_sha256": sha(b"foreign-request")}})
        )
        self.assertIn("REQUEST_IDENTITY_MISMATCH", gate.refusals)

    def test_iteration_count_mismatch_rejects(self):
        req = request()
        gate = bench.validate_simulation_samples(
            request=req, samples=samples(req, **{"0": {"iterations": 99}})
        )
        self.assertIn("MEASURED_ITERATION_COUNT_MISMATCH", gate.refusals)

    def test_runtime_generation_mismatch_rejects(self):
        req = request()
        gate = bench.validate_simulation_samples(
            request=req,
            samples=samples(req, **{"2": {"observed_runtime_generation": "python-other"}}),
        )
        self.assertIn("RUNTIME_GENERATION_MISMATCH", gate.refusals)

    def test_threshold_is_local_software_result_not_hardware_claim(self):
        req = request(candidate_latency_claim_ns=1_000_000)
        gate = bench.validate_simulation_samples(request=req, samples=samples(req))
        self.assertFalse(gate.candidate_threshold_met_in_warm_phase)
        self.assertTrue(gate.admitted_software_measurement)

    def test_receipt_is_two_parent_tamper_evident_and_closed(self):
        req = request()
        rows = samples(req)
        gate = bench.validate_simulation_samples(request=req, samples=rows)
        receipt = bench.build_simulation_benchmark_receipt(
            request=req, samples=rows, gate=gate, parent_artifact_ids=PARENTS
        )
        self.assertTrue(bench.verify_simulation_benchmark_receipt(receipt))
        self.assertTrue(all(v is False for v in receipt["claim_ceiling"].values()))
        tampered = dict(receipt)
        tampered["request_sha256"] = sha(b"tamper")
        self.assertFalse(bench.verify_simulation_benchmark_receipt(tampered))


if __name__ == "__main__":
    unittest.main()
