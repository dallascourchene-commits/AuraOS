from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aura_coding_waboose_review_lessons import (
    ReviewLessonEngine,
    ReviewLessonError,
    normalize_external_review,
    run_review_detector,
    validate_review_lesson_registry,
)

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".aura" / "review_lessons" / "pr164_spatial_review_lessons.json"


def _registry_digest(payload: dict[str, object]) -> str:
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
        default=str,
    ).encode("utf-8")
    return hashlib.blake2b(canonical, digest_size=20).hexdigest()


def _copy_registry(repo: Path) -> Path:
    target = repo / ".aura" / "review_lessons" / REGISTRY.name
    target.parent.mkdir(parents=True)
    target.write_text(REGISTRY.read_text(encoding="utf-8"), encoding="utf-8")
    return target


def test_runtime_registry_rejects_rehashed_authority_tampering() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    registry["authority"]["automatic_merge"] = True
    unsigned = dict(registry)
    unsigned.pop("registry_digest")
    registry["registry_digest"] = _registry_digest(unsigned)

    with pytest.raises(ReviewLessonError, match="authority envelope"):
        validate_review_lesson_registry(registry)


def test_authority_detector_accepts_the_canonical_envelope() -> None:
    canonical = {
        "production_mutation": False,
        "automatic_fix": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_pull_request": False,
        "automatic_merge": False,
        "human_review_required": True,
        "patch_authority": "exact_source_spans_and_hashes_only",
        "vsa_patch_authority": False,
    }
    result = run_review_detector("detect_protected_metadata_overrides", canonical)
    assert result["finding_count"] == 0


def test_normalizer_applies_one_global_cap_to_thread_expansion() -> None:
    comments = [
        {"id": index, "author": "Codex", "body": f"finding {index}"}
        for index in range(700)
    ]
    packet = normalize_external_review(
        {
            "head_sha": "a" * 40,
            "review_threads": [{"path": "module.py", "line": 1, "comments": comments}],
        },
        current_head="a" * 40,
    )
    assert packet["finding_count"] == 500
    assert packet["finding_limit_reached"] is True


def test_malformed_finding_does_not_abort_valid_neighbors() -> None:
    packet = normalize_external_review(
        {
            "head_sha": "a" * 40,
            "findings": [
                {"id": "good-1", "author": "Codex", "file": "a.py", "line": 1, "body": "good"},
                {"id": "bad", "author": "Codex", "file": "../bad.py", "line": "nope", "body": "bad"},
                {"id": "good-2", "author": "Codex", "file": "b.py", "line": 2, "body": "good"},
            ],
        },
        current_head="a" * 40,
    )
    assert packet["finding_count"] == 2
    assert packet["rejected_finding_count"] == 1


def test_persistent_review_store_stops_at_count_limit(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    registry = _copy_registry(repo)
    engine = ReviewLessonEngine(
        repo,
        registry_path=registry,
        learning_root=tmp_path / "learning",
    )
    payload = {
        "head_sha": "a" * 40,
        "findings": [
            {
                "id": f"f-{index}",
                "author": "Codex",
                "file": "module.py",
                "line": index + 1,
                "body": f"finding {index}",
            }
            for index in range(500)
        ],
    }
    first = engine.ingest_review(payload, current_head="a" * 40)
    assert first["stored_count"] == 500

    overflow = engine.ingest_review(
        {
            "head_sha": "a" * 40,
            "findings": [
                {"id": "overflow", "author": "Codex", "file": "module.py", "line": 999, "body": "overflow"}
            ],
        },
        current_head="a" * 40,
    )
    assert overflow["stored_count"] == 0
    assert overflow["rejected"][0]["reason"] == "storage_count_limit"


def _bind_replay_to_current_head(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ancestor: bool = True,
) -> None:
    import aura_review_lessons_replay as replay_module

    monkeypatch.setattr(
        replay_module,
        "_repository_evidence",
        lambda *_args, **_kwargs: {
            "repository_head": "b" * 40,
            "repository_tree": "c" * 40,
        },
    )
    monkeypatch.setattr(
        replay_module,
        "_registry_merge_is_ancestor",
        lambda *_args, **_kwargs: ancestor,
    )


def test_replay_rejects_registry_not_reachable_from_current_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_coding_waboose_review_lessons import run_crucible_replay

    _bind_replay_to_current_head(monkeypatch, ancestor=False)
    with pytest.raises(ReviewLessonError, match="registry is stale"):
        run_crucible_replay(REGISTRY)


def test_replay_canonicalizes_equivalent_detector_sets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_coding_waboose_review_lessons import run_crucible_replay

    _bind_replay_to_current_head(monkeypatch)
    detector_a = "detect_uri_alias_encoding"
    detector_b = "detect_authority_aliases"
    first = run_crucible_replay(
        REGISTRY,
        detector_ids=[detector_a, detector_b, detector_a],
    )
    second = run_crucible_replay(
        REGISTRY,
        detector_ids=[detector_b, detector_a],
    )

    assert first["selected_detector_ids"] == sorted({detector_a, detector_b})
    assert first["receipts"] == second["receipts"]
    assert first["packet_digest"] == second["packet_digest"]


def test_replay_rejects_vacuous_selected_scenario_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aura_coding_waboose_review_lessons import run_crucible_replay

    _bind_replay_to_current_head(monkeypatch)
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    detector_id = str(payload["lessons"][0]["detector_id"])
    payload["scenarios"] = [
        item
        for item in payload["scenarios"]
        if item["detector_id"] != detector_id
    ]
    unsigned = dict(payload)
    unsigned.pop("registry_digest")
    payload["registry_digest"] = _registry_digest(unsigned)

    with pytest.raises(ReviewLessonError, match="selected zero scenarios"):
        run_crucible_replay(payload, detector_ids=[detector_id])
