from __future__ import annotations

import os
from pathlib import Path
import subprocess

from scripts.aura_spatial_s4b_architect_harness import run

ROOT = Path(__file__).resolve().parents[1]


def _base_ref() -> str:
    configured = os.environ.get("AURA_S4B_TEST_BASE_REF")
    if configured:
        return configured
    for candidate in ("baseline-main-6f77ae4e", "origin/main", "6f77ae4e3f34054eb1ef0fd5aeeedc2ce7b2c3a3"):
        result = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", candidate],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    raise AssertionError("S4-B test base ref is unavailable")


def test_s4b_structural_harness_proves_mixed_gaussian_boundary() -> None:
    observed_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    receipt = run(
        ROOT,
        base_ref=_base_ref(),
        head_ref="HEAD",
        observed_head=observed_head,
        structural_only=True,
    )
    assert receipt["status"] == "PASSED", receipt["checks"]
    assert receipt["s4b_proof"]["point_cloud_fallback"] is True
    assert receipt["s4b_proof"]["accessible_fallback"] is True
    assert receipt["s4b_proof"]["headless_fallback"] is True
    assert receipt["s4b_proof"]["training_path"] is False
    assert receipt["s4b_proof"]["capture_path"] is False
    assert receipt["automatic_merge"] is False
