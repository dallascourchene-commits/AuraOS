from __future__ import annotations

import json
from pathlib import Path

import pytest

from aura_coding_waboose_review_lessons import ReviewLessonError, run_crucible_replay

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".aura" / "review_lessons" / "pr164_spatial_review_lessons.json"


def test_replay_at_registry_source_head_still_requires_merge_ancestry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import aura_review_lessons_replay as replay_module

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        replay_module,
        "_repository_evidence",
        lambda *_args, **_kwargs: {
            "repository_head": registry["repository_head"],
            "repository_tree": "c" * 40,
        },
    )
    monkeypatch.setattr(
        replay_module,
        "_registry_merge_is_ancestor",
        lambda *_args, **_kwargs: False,
    )

    with pytest.raises(ReviewLessonError, match="registry is stale"):
        run_crucible_replay(REGISTRY)
