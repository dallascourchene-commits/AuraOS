from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.thinkpad_sustained_operating_envelope import (
    CURRENTNESS_DOMAIN,
    OperatingEnvelopeError,
    observe_sustained_operating_envelope,
)


class ThinkPadSustainedOperatingEnvelopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.proc = root / "proc"
        self.sys = root / "sys"
        (self.proc / "pressure").mkdir(parents=True)
        (self.proc / "sys" / "kernel").mkdir(parents=True)
        (self.sys / "class" / "power_supply" / "AC").mkdir(parents=True)
        (self.sys / "class" / "power_supply" / "BAT0").mkdir(parents=True)
        (self.sys / "class" / "thermal" / "thermal_zone0").mkdir(parents=True)
        (self.sys / "devices" / "system" / "cpu" / "cpufreq" / "policy0").mkdir(parents=True)

        (self.proc / "meminfo").write_text(
            "MemTotal:       16000000 kB\n"
            "MemAvailable:    4000000 kB\n"
            "SwapTotal:       8000000 kB\n"
            "SwapFree:        6000000 kB\n",
            encoding="utf-8",
        )
        (self.proc / "pressure" / "memory").write_text(
            "some avg10=1.25 avg60=0.50 avg300=0.10 total=1234\n"
            "full avg10=0.05 avg60=0.02 avg300=0.01 total=12\n",
            encoding="utf-8",
        )
        (self.proc / "sys" / "kernel" / "osrelease").write_text("6.6.0-test\n", encoding="utf-8")
        (self.proc / "version").write_text("Linux version fixture\n", encoding="utf-8")

        ac = self.sys / "class" / "power_supply" / "AC"
        (ac / "type").write_text("Mains\n", encoding="utf-8")
        (ac / "online").write_text("1\n", encoding="utf-8")
        bat = self.sys / "class" / "power_supply" / "BAT0"
        (bat / "type").write_text("Battery\n", encoding="utf-8")
        (bat / "capacity").write_text("73\n", encoding="utf-8")
        (bat / "status").write_text("Charging\n", encoding="utf-8")
        (bat / "energy_now").write_text("42000000\n", encoding="utf-8")
        (bat / "power_now").write_text("18000000\n", encoding="utf-8")

        thermal = self.sys / "class" / "thermal" / "thermal_zone0"
        (thermal / "type").write_text("x86_pkg_temp\n", encoding="utf-8")
        (thermal / "temp").write_text("67000\n", encoding="utf-8")

        freq = self.sys / "devices" / "system" / "cpu" / "cpufreq" / "policy0"
        (freq / "scaling_cur_freq").write_text("1800000\n", encoding="utf-8")
        (freq / "scaling_min_freq").write_text("400000\n", encoding="utf-8")
        (freq / "scaling_max_freq").write_text("4600000\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def observe(self):
        return observe_sustained_operating_envelope(
            proc_root=str(self.proc),
            sys_root=str(self.sys),
            observed_at_utc="2026-08-31T06:30:00+00:00",
        )

    def test_observes_memory_pressure_power_thermal_and_frequency_together(self):
        receipt = self.observe()
        self.assertEqual(receipt.mem_total_bytes, 16000000 * 1024)
        self.assertEqual(receipt.mem_available_bytes, 4000000 * 1024)
        self.assertAlmostEqual(receipt.memory_available_ratio, 0.25)
        self.assertAlmostEqual(receipt.swap_free_ratio, 0.75)
        self.assertEqual(receipt.memory_psi["some"]["total"], 1234)
        self.assertEqual(len(receipt.power_supplies), 2)
        self.assertEqual(receipt.thermal_zones[0].temperature_millicelsius, 67000)
        self.assertEqual(receipt.cpu_frequency_policies[0].current_khz, 1800000)

    def test_power_supply_state_is_observed_not_interpreted_as_power_limit(self):
        receipt = self.observe()
        supplies = {s.name: s for s in receipt.power_supplies}
        self.assertEqual(supplies["AC"].online, 1)
        self.assertEqual(supplies["BAT0"].capacity_percent, 73)
        self.assertFalse(receipt.battery_power_limit_proven)

    def test_temperature_and_frequency_do_not_mint_throttling_or_performance_claim(self):
        receipt = self.observe()
        self.assertEqual(receipt.thermal_zones[0].temperature_millicelsius, 67000)
        self.assertEqual(receipt.cpu_frequency_policies[0].max_khz, 4600000)
        self.assertFalse(receipt.thermal_throttling_proven)
        self.assertFalse(receipt.performance_effect_proven)

    def test_currentness_is_scoped_to_observation_generation(self):
        receipt = self.observe()
        self.assertEqual(receipt.currentness_domain, CURRENTNESS_DOMAIN)
        self.assertTrue(receipt.current_at_observation_time_only)
        self.assertFalse(receipt.producer_authenticated)
        self.assertFalse(receipt.effect_authority_proven)
        self.assertFalse(receipt.g2_admitted)

    def test_missing_sensor_surfaces_remain_unknown_not_fabricated(self):
        other = Path(self.tmp.name) / "empty-sys"
        other.mkdir()
        receipt = observe_sustained_operating_envelope(
            proc_root=str(self.proc),
            sys_root=str(other),
            observed_at_utc="2026-08-31T06:30:00+00:00",
        )
        self.assertEqual(receipt.power_supplies, ())
        self.assertEqual(receipt.thermal_zones, ())
        self.assertEqual(receipt.cpu_frequency_policies, ())
        self.assertFalse(receipt.thinkpad_identity_proven)

    def test_symlinked_sensor_files_are_not_followed(self):
        thermal = self.sys / "class" / "thermal" / "thermal_zone0"
        (thermal / "temp").unlink()
        target = Path(self.tmp.name) / "foreign-temp"
        target.write_text("99000\n", encoding="utf-8")
        try:
            (thermal / "temp").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks unavailable")
        receipt = self.observe()
        self.assertIsNone(receipt.thermal_zones[0].temperature_millicelsius)

    def test_roots_must_be_absolute(self):
        with self.assertRaises(OperatingEnvelopeError) as ctx:
            observe_sustained_operating_envelope(proc_root="proc", sys_root=str(self.sys))
        self.assertEqual(ctx.exception.code, "OBSERVATION_ROOT_MUST_BE_ABSOLUTE")

    def test_fixed_observation_is_digest_deterministic_and_nonauthorizing(self):
        a = self.observe()
        b = self.observe()
        self.assertEqual(a.observation_digest, b.observation_digest)
        self.assertTrue(a.evidence_ref.startswith("thinkpad-operating-envelope-sha256:"))
        self.assertFalse(a.memory_pressure_safe_for_model)
        self.assertFalse(a.model_execution_observed)


if __name__ == "__main__":
    unittest.main()
