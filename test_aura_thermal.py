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


def test_thermal_reader_auto_converts_windows_deci_kelvin(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("3122\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == pytest.approx(39.05)


def test_thermal_reader_auto_converts_millikelvin(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("312275\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == pytest.approx(39.125)


def test_default_reader_uses_discovered_mobile_or_laptop_sensor(monkeypatch, tmp_path):
    sensor = tmp_path / "hwmon0" / "temp1_input"
    sensor.parent.mkdir()
    sensor.write_text("40125\n", encoding="utf-8")
    monkeypatch.setattr(aura_thermal, "_discover_thermal_paths", lambda: (sensor,))

    assert read_cpu_temp_c() == 40.125


def test_explicit_empty_paths_skip_device_auto_detection():
    assert read_cpu_temp_c(paths=(), fallback=36.5) == 36.5


def test_thermal_fallback_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("AURA_THERMAL_FALLBACK_C", "37.5")

    assert read_cpu_temp_c(paths=(tmp_path / "missing",)) == 37.5
