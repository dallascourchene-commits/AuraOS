from __future__ import annotations

import pytest

from tools.benchmarks.select_swe_verified_smoke import build_manifest, select_instance_ids


def ids(n: int = 100) -> list[str]:
    return [f"repo__issue-{index:03d}" for index in range(n)]


def test_selection_is_deterministic_and_order_independent():
    forward = select_instance_ids(ids(), count=10)
    reverse = select_instance_ids(reversed(ids()), count=10)
    assert forward == reverse


def test_seed_changes_selection():
    assert select_instance_ids(ids(), count=10, seed="a") != select_instance_ids(ids(), count=10, seed="b")


def test_duplicate_instance_id_fails_closed():
    with pytest.raises(ValueError, match="DUPLICATE_INSTANCE_ID"):
        select_instance_ids(["a", "a"], count=1)


def test_invalid_count_fails_closed():
    with pytest.raises(ValueError, match="INVALID_SELECTION_COUNT"):
        select_instance_ids(ids(3), count=4)


def test_manifest_is_explicitly_non_official():
    manifest = build_manifest(ids(), source_generation="dataset-rev-1", count=10, seed="fixed")
    assert manifest["official"] is False
    assert manifest["leaderboard_score"] is False
    assert manifest["source_instance_count"] == 100
    assert len(manifest["selected_instance_ids"]) == 10
    assert manifest["selection_count"] == 10


def test_source_generation_is_bound_into_manifest():
    first = build_manifest(ids(), source_generation="rev-a", count=10, seed="fixed")
    second = build_manifest(ids(), source_generation="rev-b", count=10, seed="fixed")
    assert first["selected_instance_ids"] == second["selected_instance_ids"]
    assert first["source_generation"] != second["source_generation"]
