from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "scripts/aura_spatial_continuation_architect_harness.py"


def _module():
    spec = importlib.util.spec_from_file_location("spatial_s3a_harness", HARNESS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_structural_harness_proves_grounded_non_authoritative_lifecycle():
    module = _module()
    receipt = module.run(
        ROOT,
        base_ref="HEAD~1",
        head_ref="HEAD",
        observed_head="a" * 40,
        structural_only=True,
    )
    assert receipt["status"] == "PASSED"
    assert receipt["repository_head"] == "a" * 40
    assert receipt["council_v3"]["selected_lanes"] == [
        "scope",
        "tests",
        "sequence",
        "continuity",
        "rollback",
        "cost",
    ]
    assert receipt["breadboard"]["circuit_status"].endswith("UNPOWERED")
    assert receipt["lifecycle_proof"]["active_sessions_after_dissolution"] == 0
    assert receipt["lifecycle_proof"]["raw_sensor_data_retained"] is False
    assert receipt["lifecycle_proof"]["renderer_disposed"] is False
    assert receipt["checks"]["renderer_disposal_not_overclaimed"] is True
    assert receipt["browser_and_import_proof"]["patch_authority"] == module.PATCH_AUTHORITY
    assert receipt["production_mutation"] is False
    assert receipt["automatic_merge"] is False
