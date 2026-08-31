from core.aura_resident_idle_policy import HostState, MaintenanceWork, WARM_MODEL, choose_background_route


def host(**kw):
    base = dict(available_ram_gib=8.0, free_disk_gib=40.0, on_ac_power=True,
                idle_minutes=10, cpu_percent=20.0, thermal_ok=True, foreground_heavy=False)
    base.update(kw)
    return HostState(**base)


def test_deterministic_first():
    assert choose_background_route(host(), MaintenanceWork("digest", deterministic_sufficient=True))["route"] == "NO_MODEL"


def test_primary_warm_model():
    out = choose_background_route(host(), MaintenanceWork("triage"))
    assert out == {"route": "LOCAL_WARM_MOE", "model": WARM_MODEL}


def test_battery_defers():
    assert choose_background_route(host(on_ac_power=False), MaintenanceWork("triage"))["route"] == "DEFER_MODEL_WORK"


def test_thermal_defers():
    assert choose_background_route(host(thermal_ok=False), MaintenanceWork("triage"))["route"] == "DEFER_MODEL_WORK"


def test_foreground_defers():
    assert choose_background_route(host(foreground_heavy=True), MaintenanceWork("triage"))["route"] == "DEFER_MODEL_WORK"


def test_d1_requires_human_gate():
    assert choose_background_route(host(), MaintenanceWork("write", consequence_class="D1"))["route"] == "HUMAN_GATE"


def test_background_cannot_promote_beyond_gate10():
    assert choose_background_route(host(), MaintenanceWork("promote", gate_target=11))["route"] == "BLOCK"


def test_gptoss_near_fit_not_normal():
    assert choose_background_route(host(), MaintenanceWork("deep", deep_reasoning=True))["route"] != "LOCAL_COLD_REASONER"


def test_gptoss_requires_exact_available_ram():
    out = choose_background_route(host(available_ram_gib=15.1, idle_minutes=35, cpu_percent=20), MaintenanceWork("deep", deep_reasoning=True))
    assert out["route"] == "LOCAL_COLD_REASONER"
    assert out["unload_warm_first"] is True


def test_airllm_is_separate_admission():
    out = choose_background_route(host(available_ram_gib=6.0, free_disk_gib=100.0, idle_minutes=65), MaintenanceWork("deep", deep_reasoning=True))
    assert out["route"] == "AIRLLM_COLD_EXPERIMENTAL"
    assert out["requires_separate_admission"] is True
