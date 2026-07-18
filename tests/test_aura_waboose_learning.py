from __future__ import annotations

import ast
from pathlib import Path
import subprocess
from typing import Any

import pytest

import aura_waboose_learning as learning_module
from aura_waboose_learning import CodeRabbitLearningStore


class FakeQDKT:
    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []
        self.crystals: list[dict[str, Any]] = []
        self.retrieval_rows: list[dict[str, Any]] = []

    def observe(self, event_type: str, payload: dict[str, Any], **kwargs: Any) -> str:
        self.observations.append(
            {"event_type": event_type, "payload": dict(payload), **kwargs}
        )
        return f"QDKT-{len(self.observations)}"

    def crystallize(self, concept: str, recommended_action: str, **kwargs: Any) -> None:
        self.crystals.append(
            {
                "concept": concept,
                "recommended_action": recommended_action,
                **kwargs,
            }
        )

    def observe_retrieval_usefulness(self, row: dict[str, Any]) -> str:
        self.retrieval_rows.append(dict(row))
        return f"DREAM-{len(self.retrieval_rows)}"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "learning@example.test")
    _git(repo, "config", "user.name", "Waboose Learning")
    (repo / "parser.py").write_text(
        "def parse(value):\n"
        "    return bool(value.get('include_source', True))\n",
        encoding="utf-8",
    )
    _git(repo, "add", "parser.py")
    _git(repo, "commit", "-m", "fixture")
    return repo


def _payload(repo: Path, *, run_id: str = "run-1") -> dict[str, Any]:
    return {
        "success": True,
        "status": "completed",
        "run_id": run_id,
        "pr_number": 156,
        "head_sha": _git(repo, "rev-parse", "HEAD"),
        "findings": [
            {
                "author": "coderabbitai",
                "file": "parser.py",
                "line_start": 2,
                "line_end": 2,
                "title": "Parse boolean options instead of applying truthiness",
                "message": "bool(\"false\") is True; accept actual booleans or reject invalid values.",
                "severity": "high",
                "category": "correctness",
                "suggested_fix": "Use a strict boolean parser.",
                "evidence_excerpt": "return bool(value.get('include_source', True))",
            }
        ],
    }


@pytest.fixture
def grounded_connectome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        learning_module,
        "resolve_capabilities",
        lambda *args, **kwargs: {
            "capability_path_digest": "path-digest",
            "capability_connectome_path": {
                "ok": True,
                "path": ["aura.coding_waboose", "aura.qdkt"],
                "path_details": [
                    {"id": "aura.coding_waboose"},
                    {"id": "aura.qdkt"},
                ],
            },
        },
    )
    monkeypatch.setattr(
        learning_module,
        "build_capability_connectome",
        lambda *args, **kwargs: {"ok": True, "nodes": [], "edges": []},
    )
    monkeypatch.setattr(
        learning_module,
        "enrich_connectome",
        lambda value: {**value, "graph_digest": "graph-digest"},
    )


def test_successful_grounded_review_is_stored_and_connectome_routed(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    qdkt = FakeQDKT()
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=qdkt,
    )

    result = store.ingest_review(_payload(repo))

    assert result["ok"] is True
    assert result["learned_count"] == 1
    learned = result["learned"][0]
    assert learned["semantic_rule_pack"] == "strict_input_types"
    assert learned["connectome_path"] == ["aura.coding_waboose", "aura.qdkt"]
    assert store.episodes_path.exists()
    assert store.patterns_path.exists()
    assert qdkt.observations[0]["event_type"] == "coderabbit_review_learning"
    assert qdkt.observations[0]["payload"]["patch_authority"] is False
    summary = store.summary()
    assert summary["episode_count"] == 1
    assert summary["pattern_count"] == 1


def test_unsuccessful_or_wrong_head_review_does_not_learn(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=FakeQDKT(),
    )
    failed = _payload(repo)
    failed["success"] = False
    failed["status"] = "failed"
    assert store.ingest_review(failed)["status"] == "coderabbit_review_not_successful"

    wrong = _payload(repo)
    wrong["head_sha"] = "0" * 40
    assert store.ingest_review(wrong)["status"] == "coderabbit_review_head_mismatch"
    assert not store.episodes_path.exists()


def test_dream_lite_and_qdkt_crystallize_after_repeated_confirmation(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    qdkt = FakeQDKT()
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=qdkt,
    )

    for index in range(3):
        result = store.ingest_review(_payload(repo, run_id=f"run-{index}"))
        assert result["ok"] is True

    patterns = store._load_patterns()
    assert len(patterns) == 1
    pattern = next(iter(patterns.values()))
    assert pattern["confirmation_count"] == 3
    assert pattern["qdkt_crystallized"] is True
    assert qdkt.crystals
    assert qdkt.retrieval_rows


def test_learning_context_uses_dream_ranked_advisory_memory(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=FakeQDKT(),
    )
    store.ingest_review(_payload(repo))

    context = store.learning_context(
        "Review boolean option parsing",
        changed_files=["parser.py"],
    )

    assert context["ok"] is True
    assert context["patterns"]
    assert context["dream_lite_ranked"] is True
    assert context["qdkt_backed"] is True
    assert context["patch_authority"] is False


def test_raw_coderabbit_threads_are_normalized(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=FakeQDKT(),
    )
    payload = {
        "success": True,
        "status": "commented",
        "run_id": "thread-run",
        "head_sha": _git(repo, "rev-parse", "HEAD"),
        "review_threads": [
            {
                "path": "parser.py",
                "line": 2,
                "comments": [
                    {
                        "author": {"login": "coderabbitai"},
                        "body": "**Parse boolean options instead of applying truthiness.** bool(\"false\") is True.",
                    }
                ],
            }
        ],
    }

    result = store.ingest_review(payload)
    assert result["ok"] is True
    assert result["learned_count"] == 1


def test_unknown_repeated_pattern_can_be_emulated_as_probable_only(
    tmp_path: Path,
    grounded_connectome: None,
) -> None:
    repo = _repo(tmp_path)
    qdkt = FakeQDKT()
    store = CodeRabbitLearningStore(
        repo,
        learning_root=tmp_path / "learning",
        qdkt=qdkt,
    )
    payload = _payload(repo)
    finding = payload["findings"][0]
    finding["title"] = "Preserve parser branch symmetry"
    finding["message"] = "This parser branch shape previously caused a hidden mismatch."
    finding["suggested_fix"] = "Inspect the branch symmetry and add a regression case."
    store.ingest_review(payload)

    source = (repo / "parser.py").read_text(encoding="utf-8")
    findings = store.scan_learned_patterns(
        file="parser.py",
        source=source,
        tree=ast.parse(source),
    )
    assert findings
    assert findings[0]["status"] == "probable"
    assert findings[0]["repair_authority"] is False
