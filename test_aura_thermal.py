import sys
from types import SimpleNamespace

import pytest

import aura_thermal
from aura_thermal import DEFAULT_THERMAL_FALLBACK_C, read_cpu_temp_c


def test_missing_thermal_sensor_defaults_to_cool_idle(tmp_path):
    missing = tmp_path / "thermal_zone0" / "temp"

    assert read_cpu_temp_c(paths=(missing,)) == DEFAULT_THERMAL_FALLBACK_C


def test_thermal_reader_parses_millicelsius(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("39125\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == 39.125


def test_thermal_reader_auto_converts_kelvin(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("312.275\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == pytest.approx(39.125)


def test_thermal_reader_auto_converts_millikelvin(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("312275\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == pytest.approx(39.125)


def test_discovered_sysfs_sensor_uses_millicelsius_hint(monkeypatch, tmp_path):
    sensor = tmp_path / "hwmon0" / "temp1_input"
    sensor.parent.mkdir()
    sensor.write_text("3500\n", encoding="utf-8")
    monkeypatch.setattr(aura_thermal, "_discover_thermal_paths", lambda: (sensor,))

    assert read_cpu_temp_c() == pytest.approx(3.5)


def test_default_reader_uses_hottest_discovered_sensor(monkeypatch, tmp_path):
    cool = tmp_path / "hwmon0" / "temp1_input"
    hot = tmp_path / "hwmon1" / "temp1_input"
    cool.parent.mkdir()
    hot.parent.mkdir()
    cool.write_text("30000\n", encoding="utf-8")
    hot.write_text("95000\n", encoding="utf-8")
    monkeypatch.setattr(aura_thermal, "_discover_thermal_paths", lambda: (cool, hot))

    assert read_cpu_temp_c() == 95.0


def test_psutil_reader_preserves_zero_and_selects_hottest(monkeypatch):
    fake_psutil = SimpleNamespace(
        sensors_temperatures=lambda fahrenheit=False: {
            "cpu": [SimpleNamespace(current=0.0), SimpleNamespace(current=47.5)]
        }
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    assert aura_thermal._read_psutil_temp_c() == 47.5
    assert aura_thermal._parse_temp_c(0.0, unit_hint="celsius") == 0.0


@pytest.mark.parametrize("raw", ["150000", "-50000", "not-a-number", ""])
def test_invalid_sensor_values_use_fallback(tmp_path, raw):
    sensor = tmp_path / "temp"
    sensor.write_text(raw, encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,), fallback=36.5) == 36.5


def test_fallback_uses_psutil_when_no_paths(monkeypatch):
    monkeypatch.setattr(aura_thermal, "_discover_thermal_paths", lambda: ())
    monkeypatch.setattr(aura_thermal, "_read_psutil_temp_c", lambda: 42.5)
    monkeypatch.setattr(aura_thermal, "_read_windows_acpi_temp_c", lambda: None)

    assert read_cpu_temp_c() == 42.5


def test_fallback_uses_windows_acpi_when_no_paths_or_psutil(monkeypatch):
    monkeypatch.setattr(aura_thermal, "_discover_thermal_paths", lambda: ())
    monkeypatch.setattr(aura_thermal, "_read_psutil_temp_c", lambda: None)
    monkeypatch.setattr(aura_thermal, "_read_windows_acpi_temp_c", lambda: 44.25)

    assert read_cpu_temp_c() == 44.25


def test_windows_acpi_probe_skips_when_powershell_is_unavailable(monkeypatch):
    monkeypatch.setattr(aura_thermal.shutil, "which", lambda executable: None)
    monkeypatch.setattr(
        aura_thermal.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected probe")),
    )

    assert aura_thermal._run_windows_acpi_probe() is None


def test_windows_acpi_probe_uses_resolved_executable_and_fixed_arguments(monkeypatch):
    calls = []
    monkeypatch.setattr(
        aura_thermal.shutil,
        "which",
        lambda executable: r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )

    def fake_run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(returncode=0, stdout="3122\n")

    monkeypatch.setattr(aura_thermal.subprocess, "run", fake_run)

    assert aura_thermal._run_windows_acpi_probe() == pytest.approx(39.05)
    assert calls == [
        (
            [
                r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                (
                    "$ErrorActionPreference = 'Stop'; "
                    "Get-CimInstance -Namespace root/wmi "
                    "-ClassName MSAcpi_ThermalZoneTemperature | "
                    "ForEach-Object { $_.CurrentTemperature }"
                ),
            ],
            {
                "capture_output": True,
                "text": True,
                "timeout": 3.0,
                "check": False,
                "shell": False,
            },
        )
    ]


def test_windows_deci_kelvin_conversion_is_explicit():
    assert aura_thermal._parse_temp_c("3122", unit_hint="decikelvin") == pytest.approx(39.05)


def test_explicit_empty_paths_skip_device_auto_detection():
    assert read_cpu_temp_c(paths=(), fallback=36.5) == 36.5


def test_thermal_fallback_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("AURA_THERMAL_FALLBACK_C", "37.5")

    assert read_cpu_temp_c(paths=(tmp_path / "missing",)) == 37.5
