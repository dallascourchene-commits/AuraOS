from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def _run(root: Path, command: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(root / "aura_spatial_cli.py"), "--repo-root", str(root), command],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return json.loads(result.stdout)


def test_spatial_cli_validates_route() -> None:
    root = Path(__file__).resolve().parents[1]
    packet = _run(root, "validate-route")
    assert packet["ok"] is True
    assert packet["route"]["ok"] is True
    assert packet["production_mutation"] is False
    assert packet["automatic_merge"] is False


def test_spatial_cli_synthetic_demo_leaves_no_persistent_demo_state() -> None:
    root = Path(__file__).resolve().parents[1]
    before = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True).stdout
    packet = _run(root, "synthetic-construction-demo")
    after = subprocess.run(["git", "status", "--short"], cwd=root, check=True, capture_output=True, text=True).stdout
    assert packet["ok"] is True
    assert packet["synthetic"] is True
    assert packet["private_data_used"] is False
    assert packet["production_connectors_used"] is False
    assert packet["persistent_demo_state_written"] is False
    assert packet["lease_released"] is True
    assert packet["renderer_allocated"] is False
    assert packet["renderer_resources_released"] is False
    assert packet["renderer_resources_released_verified"] is False
    assert packet["renderer_resource_boundary_satisfied"] is True
    assert packet["physical_work_authorized"] is False
    assert packet["payment_released"] is False
    assert packet["access_controlled"] is False
    assert after == before
