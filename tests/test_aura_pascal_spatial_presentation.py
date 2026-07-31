"""Collected Pascal presentation contracts split into bounded test modules for PR5."""
from __future__ import annotations

import sys
from pathlib import Path

_TEST_DIR = str(Path(__file__).resolve().parent)
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from pascal_spatial_presentation_test_contracts import *  # noqa: F401,F403,E402
from pascal_spatial_presentation_test_lifecycle import *  # noqa: F401,F403,E402
