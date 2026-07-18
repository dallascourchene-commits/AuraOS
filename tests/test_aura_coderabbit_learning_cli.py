from __future__ import annotations

import json
from pathlib import Path

import aura_coderabbit_learning_cli as cli


class FakeStore:
    def __init__(self, repo_root: str, *, learning_root: str) -> None:
        self.repo_root = repo_root
        self.learning_root = learning_root

    def ingest_review(self, payload: dict) -> dict:
        return {
            "ok": True,
            "status": "learned",
            "learned_count": len(payload.get("findings", [])),
            "patch_authority": "exact_source_spans_and_hashes_only",
            "production_mutation": False,
        }

    def summary(self) -> dict:
        return {
            "ok": True,
            "episode_count": 2,
            "pattern_count": 1,
            "production_mutation": False,
        }


def test_cli_ingests_review_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(cli, "CodeRabbitLearningStore", FakeStore)
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps({"findings": [{"title": "one"}]}),
        encoding="utf-8",
    )
    rc = cli.main(
        [
            "--repo-root",
            str(tmp_path),
            "--learning-root",
            str(tmp_path / "learning"),
            "ingest",
            "--review",
            str(review),
        ]
    )
    packet = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert packet["learned_count"] == 1
    assert packet["production_mutation"] is False


def test_cli_summary(monkeypatch, capsys) -> None:
    monkeypatch.setattr(cli, "CodeRabbitLearningStore", FakeStore)
    rc = cli.main(["summary"])
    packet = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert packet["episode_count"] == 2
