from aura_amd_demo_scenario import run_demo_scenario


def test_topology_workbench_end_to_end_fake_symbol_demo() -> None:
    """
    Integration test validating the complete workbench spine end-to-end:
    Planner targeting fake symbol -> clamped luminance -> blocked mutation state ->
    test gap filler refusal -> benchmark gate block -> hardware advisory scheduling ->
    scene export generation.
    """
    assert run_demo_scenario(verbose=True) is True
