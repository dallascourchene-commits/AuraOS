from aura_thermal import DEFAULT_THERMAL_FALLBACK_C, read_cpu_temp_c


def test_missing_thermal_sensor_defaults_to_cool_idle(tmp_path):
    missing = tmp_path / "thermal_zone0" / "temp"

    assert read_cpu_temp_c(paths=(missing,)) == DEFAULT_THERMAL_FALLBACK_C


def test_thermal_reader_parses_millicelsius(tmp_path):
    sensor = tmp_path / "temp"
    sensor.write_text("39125\n", encoding="utf-8")

    assert read_cpu_temp_c(paths=(sensor,)) == 39.125


def test_thermal_fallback_can_be_overridden(monkeypatch, tmp_path):
    monkeypatch.setenv("AURA_THERMAL_FALLBACK_C", "37.5")

    assert read_cpu_temp_c(paths=(tmp_path / "missing",)) == 37.5
