from __future__ import annotations

from dataclasses import replace
import unittest

from tools.thinkpad_longitudinal_envelope_series import (
    LongitudinalEnvelopeError,
    build_longitudinal_envelope_series,
)
from tools.thinkpad_sustained_operating_envelope import (
    CpuFrequencyObservation,
    PowerSupplyObservation,
    SustainedOperatingEnvelope,
    ThermalObservation,
)

D = "ab" * 32
E = "cd" * 32


class ThinkPadLongitudinalEnvelopeSeriesTests(unittest.TestCase):
    def envelope(
        self,
        *,
        observed_at: str,
        mem_ratio: float | None,
        swap_ratio: float | None,
        temp_mc: int | None,
        freq_khz: int | None,
        ac_online: int | None,
        battery_capacity: int | None,
    ) -> SustainedOperatingEnvelope:
        power = []
        if ac_online is not None:
            power.append(PowerSupplyObservation("AC", "Mains", ac_online, None, None, None, None))
        if battery_capacity is not None:
            power.append(
                PowerSupplyObservation(
                    "BAT0", "Battery", None, battery_capacity, "Discharging", 40_000_000, 12_000_000
                )
            )
        thermal = () if temp_mc is None else (ThermalObservation("thermal_zone0", "x86_pkg_temp", temp_mc),)
        freq = () if freq_khz is None else (CpuFrequencyObservation("policy0", freq_khz, 400_000, 4_600_000),)
        return SustainedOperatingEnvelope(
            observed_at_utc=observed_at,
            proc_root="/proc",
            sys_root="/sys",
            os_release="6.6.0-test",
            kernel_version="Linux fixture",
            mem_total_bytes=16_000_000_000,
            mem_available_bytes=None if mem_ratio is None else int(16_000_000_000 * mem_ratio),
            swap_total_bytes=8_000_000_000,
            swap_free_bytes=None if swap_ratio is None else int(8_000_000_000 * swap_ratio),
            memory_available_ratio=mem_ratio,
            swap_free_ratio=swap_ratio,
            memory_psi={},
            power_supplies=tuple(power),
            thermal_zones=thermal,
            cpu_frequency_policies=freq,
        )

    def three(self):
        return (
            self.envelope(
                observed_at="2026-08-31T06:00:00+00:00",
                mem_ratio=0.50,
                swap_ratio=0.90,
                temp_mc=55_000,
                freq_khz=3_000_000,
                ac_online=1,
                battery_capacity=80,
            ),
            self.envelope(
                observed_at="2026-08-31T06:10:00+00:00",
                mem_ratio=0.40,
                swap_ratio=0.80,
                temp_mc=67_000,
                freq_khz=2_600_000,
                ac_online=1,
                battery_capacity=78,
            ),
            self.envelope(
                observed_at="2026-08-31T06:20:00+00:00",
                mem_ratio=0.30,
                swap_ratio=0.70,
                temp_mc=72_000,
                freq_khz=2_200_000,
                ac_online=0,
                battery_capacity=72,
            ),
        )

    def build(self, **changes):
        cold, warm, restart = self.three()
        values = dict(
            benchmark_request_digest=D,
            query_sequence_sha256=E,
            process_cold=cold,
            process_warm=warm,
            restart=restart,
        )
        values.update(changes)
        return build_longitudinal_envelope_series(**values)

    def test_ordered_three_phase_series_computes_descriptive_deltas(self):
        series = self.build()
        self.assertEqual(tuple(item["phase"] for item in series.phase_summaries), ("PROCESS_COLD", "PROCESS_WARM", "RESTART"))
        self.assertAlmostEqual(series.first_to_last_memory_available_ratio_delta, -0.20)
        self.assertAlmostEqual(series.first_to_last_swap_free_ratio_delta, -0.20)
        self.assertEqual(series.first_to_last_max_temperature_millicelsius_delta, 17_000)
        self.assertEqual(series.first_to_last_min_current_cpu_khz_delta, -800_000)
        self.assertEqual(series.first_to_last_battery_capacity_percent_delta, -8)
        self.assertTrue(series.ac_online_changed)

    def test_nonmonotonic_phase_times_fail_closed(self):
        cold, warm, restart = self.three()
        bad = replace(warm, observed_at_utc="2026-08-31T05:59:00+00:00")
        with self.assertRaisesRegex(LongitudinalEnvelopeError, "PHASE_TIMESTAMPS_NOT_STRICTLY_INCREASING"):
            self.build(process_cold=cold, process_warm=bad, restart=restart)

    def test_duplicate_observation_identity_is_rejected(self):
        cold, _, restart = self.three()
        duplicate = replace(cold, observed_at_utc=cold.observed_at_utc)
        with self.assertRaisesRegex(LongitudinalEnvelopeError, "DISTINCT_PHASE_OBSERVATIONS_REQUIRED"):
            self.build(process_cold=cold, process_warm=duplicate, restart=restart)

    def test_benchmark_and_query_bindings_require_exact_sha256(self):
        with self.assertRaisesRegex(LongitudinalEnvelopeError, "INVALID_SHA256"):
            self.build(benchmark_request_digest="not-a-digest")
        with self.assertRaisesRegex(LongitudinalEnvelopeError, "INVALID_SHA256"):
            self.build(query_sequence_sha256="f" * 63)

    def test_missing_sensor_layers_remain_unknown(self):
        cold = self.envelope(
            observed_at="2026-08-31T06:00:00+00:00",
            mem_ratio=None, swap_ratio=None, temp_mc=None, freq_khz=None, ac_online=None, battery_capacity=None
        )
        warm = replace(cold, observed_at_utc="2026-08-31T06:10:00+00:00")
        restart = replace(cold, observed_at_utc="2026-08-31T06:20:00+00:00")
        series = self.build(process_cold=cold, process_warm=warm, restart=restart)
        self.assertIsNone(series.first_to_last_memory_available_ratio_delta)
        self.assertIsNone(series.first_to_last_max_temperature_millicelsius_delta)
        self.assertIsNone(series.first_to_last_min_current_cpu_khz_delta)
        self.assertIsNone(series.ac_online_changed)

    def test_series_cannot_promote_correlation_to_causality_or_current_authority(self):
        series = self.build()
        self.assertTrue(series.historical_series_only)
        self.assertFalse(series.same_host_proven)
        self.assertFalse(series.benchmark_execution_proven)
        self.assertFalse(series.thermal_throttling_proven)
        self.assertFalse(series.temperature_caused_performance_change)
        self.assertFalse(series.memory_pressure_caused_performance_change)
        self.assertFalse(series.battery_state_caused_performance_change)
        self.assertFalse(series.performance_winner_proven)
        self.assertFalse(series.current_now_proven)
        self.assertFalse(series.producer_authenticated)
        self.assertFalse(series.g2_admitted)
        self.assertFalse(series.effect_authority_proven)

    def test_parent_envelope_ceiling_widening_fails_before_series_reasoning(self):
        cold, warm, restart = self.three()
        widened = replace(warm, thermal_throttling_proven=True)
        with self.assertRaisesRegex(LongitudinalEnvelopeError, "PARENT_ENVELOPE_CEILING_WIDENED"):
            self.build(process_cold=cold, process_warm=widened, restart=restart)

    def test_series_identity_is_deterministic(self):
        a = self.build()
        b = self.build()
        self.assertEqual(a.series_digest, b.series_digest)
        self.assertTrue(a.evidence_ref.startswith("thinkpad-longitudinal-envelope-series-sha256:"))


if __name__ == "__main__":
    unittest.main()
