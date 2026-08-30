"""Early exact-head gate for the CS-HARNESS-001 H-I integration battery.

The repository-wide pytest job currently uses --maxfail=1 and has an unrelated
pre-existing failure later in root collection. This gate intentionally executes
the H-I unittest module first so its exact-head result is visible independently
of that downstream failure. It grants no promotion/effect authority.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest


def test_h_i_cross_lane_exact_head_battery() -> None:
    project030 = Path(__file__).resolve().parent / "tools" / "project030"
    path = str(project030)
    if path not in sys.path:
        sys.path.insert(0, path)

    suite = unittest.defaultTestLoader.loadTestsFromName(
        "test_creator_studio_harness_integration"
    )
    result = unittest.TestResult()
    suite.run(result)

    details = [
        *(f"FAIL {case}: {trace}" for case, trace in result.failures),
        *(f"ERROR {case}: {trace}" for case, trace in result.errors),
    ]
    assert result.testsRun == 10, f"expected 10 H-I tests, ran {result.testsRun}"
    assert result.wasSuccessful(), "\n".join(details)
