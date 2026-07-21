from __future__ import annotations

from pathlib import Path
import hashlib

import pytest

from scripts import aura_architecture_harness as harness


def test_digest_is_order_stable() -> None:
    assert harness._digest({"b": 2, "a": 1}) == harness._digest({"a": 1, "b": 2})


def test_default_venv_is_outside_repository() -> None:
    root = Path("/tmp/AuraOS")
    result = harness._default_venv(root)
    assert result.parent == root.parent
    assert result != root / ".venv"


def test_parser_defaults_to_bounded_minimal_atlas() -> None:
    args = harness._parser().parse_args(["--repo-root", ".", "run"])
    assert args.atlas_profile == "MINIMAL"
    assert args.allow_expansive_atlas is False
    assert args.pair_limit == 5_000_000
    assert args.resume is False
    assert args.reference_file == []


def test_reference_manifest_binds_external_specification(tmp_path: Path) -> None:
    reference = tmp_path / "architecture.txt"
    reference.write_text("bounded architecture specification\n", encoding="utf-8")

    manifest = harness._reference_manifest([reference])

    assert manifest == [
        {
            "name": "architecture.txt",
            "path": str(reference.resolve()),
            "size_bytes": reference.stat().st_size,
            "sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
        }
    ]


def test_reference_manifest_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="reference file is missing"):
        harness._reference_manifest([tmp_path / "missing.txt"])


def test_required_surfaces_cover_requested_architecture() -> None:
    required = set(harness.REQUIRED_REPOSITORY_FILES)
    assert "aura_capability_connectome.py" in required
    assert "aura_relational_synthesis.py" in required
    assert "aura_relationship_atlas.py" in required
    assert "aura_emergent_potential_repl.py" in required
    assert "aura_architect_loop.py" in required


def test_harness_is_proposal_only() -> None:
    assert harness.PATCH_AUTHORITY == "exact_source_spans_and_hashes_only"


def test_run_architecture_accepts_serialized_output_dir(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = tmp_path / "run"

    class _ConnectomeModule:
        @staticmethod
        def build_capability_connectome(_root):
            return {"nodes": [], "edges": []}

    class _ConnectomeV2Module:
        @staticmethod
        def enrich_connectome(graph):
            return {**graph, "node_count": 0, "edge_count": 0, "graph_digest": "g"}

    class _IndexModule:
        @staticmethod
        def build_relational_index(*_args, **_kwargs):
            return {"participant_count": 0, "index": {"participants": [], "relationships": []}}

    class _Snapshot:
        snapshot_digest = "a"
        assessments = []
        missing_configurations = []
        prohibitions = []

        def to_dict(self):
            return {"snapshot_digest": "a", "assessments": [], "missing_configurations": [], "prohibitions": []}

    atlas_calls: list[dict] = []

    class _AtlasModule:
        @staticmethod
        def build_relationship_atlas(**kwargs):
            atlas_calls.append(kwargs)
            return _Snapshot()

    class _Report:
        verifier_summary = "ok"
        def to_dict(self):
            return {"summary": {}, "verifier_summary": "ok", "connections": []}

    class _EmergentModule:
        @staticmethod
        def audit_emergent_potential(*_args, **_kwargs):
            return _Report()

    class _Prepared:
        def to_dict(self):
            return {"plan": {}, "shadow_report": {}, "arena": {}}

    class _FusionLoop:
        def __init__(self, repo_root):
            self.repo_root = repo_root
        def prepare(self, *_args, **_kwargs):
            return _Prepared()

    class _ArchitectModule:
        ArchitectFusionLoop = _FusionLoop

    modules = {
        "aura_capability_connectome": _ConnectomeModule,
        "aura_capability_connectome_v2": _ConnectomeV2Module,
        "aura_relational_index": _IndexModule,
        "aura_relationship_atlas": _AtlasModule,
        "aura_emergent_potential_repl": _EmergentModule,
        "aura_architect_loop": _ArchitectModule,
    }
    for name, module in modules.items():
        monkeypatch.setitem(__import__("sys").modules, name, module)
    monkeypatch.setattr(harness, "_git_info", lambda _root: {"available": True, "clean": True})

    result = harness.run_architecture(
        root,
        objective="test",
        combine_with=[],
        profile="MINIMAL",
        top=1,
        pair_limit=1,
        allow_expansive=False,
        output_dir=str(output),
        resume=False,
        enforce_clean=True,
        reference_files=[],
    )

    assert result["ok"] is True
    assert (output / "harness_summary.json").is_file()
    assert atlas_calls[0]["persist"] is False
    assert atlas_calls[0]["relational_index_data"] == {
        "participants": [],
        "relationships": [],
    }
