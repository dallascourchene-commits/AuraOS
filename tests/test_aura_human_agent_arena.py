"""Collection shim for the governed Human Agent Arena regression suite.

The full suite is preserved byte-for-byte in a non-collected support module so a
single stale generated-map contract can be replaced without dropping unrelated
coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

from aura_affordance_directory import SEED_AFFORDANCES
from test_support import aura_human_agent_arena_suite as _suite


for _name, _value in vars(_suite).items():
    if _name.startswith("test_") and _name != "test_affordance_map_declares_source_of_truth":
        globals()[_name] = _value


def test_affordance_map_declares_source_of_truth() -> None:
    """The generated map must preserve canonical seeds and advisory extensions."""
    repo_root = Path(__file__).resolve().parents[1]
    map_path = repo_root / ".aura" / "AFFORDANCE_MAP.json"
    assert map_path.is_file(), "AFFORDANCE_MAP.json must exist"

    data = json.loads(map_path.read_text(encoding="utf-8"))
    assert data.get("mode") == "generated_placeholder_with_review_learning_extension"
    assert data.get("source_of_truth") == (
        "aura_affordance_directory.SEED_AFFORDANCES plus bounded extension entries"
    )

    note = str(data.get("note") or "")
    assert "advisory-only" in note
    assert "not already present" in note

    extensions = list(data.get("affordances") or [])
    extension_ids = {str(item.get("id") or "") for item in extensions}
    seed_ids = {str(item.get("id") or "") for item in SEED_AFFORDANCES}
    assert extension_ids
    assert "" not in extension_ids
    assert extension_ids.isdisjoint(seed_ids)
    assert all(item.get("patch_authority") is False for item in extensions)
    assert all(item.get("vsa_patch_authority") is False for item in extensions)
