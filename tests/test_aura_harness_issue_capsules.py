from __future__ import annotations

import json
from pathlib import Path

import pytest

import aura_affordance_directory
import aura_agent_workbench_interface
import aura_capability_lane_registry
import aura_cockpit_plugin_registration
import aura_module_manifest
from aura_capability_resolver import resolve_capabilities
from aura_module_manifest import load_module_manifest
from aura_waboose_semantic_rules import _is_source_owner


def _write_minimal_codemap(repo_root: Path) -> None:
    aura_dir = repo_root / ".aura"
    aura_dir.mkdir(parents=True, exist_ok=True)
    (repo_root / "target.py").write_text("def target_symbol():\n    return True\n", encoding="utf-8")
    payload = {
        "coverage": {"included_file_count": 1},
        "summary": {
            "file_count": 1,
            "topology_nodes": 1,
            "topology_edges": 0,
            "topology_source": "focused_test_fixture",
        },
        "symbol_index": {
            "target_symbol": [
                {
                    "file": "target.py",
                    "kind": "function",
                    "line": 1,
                    "end_line": 2,
                    "digest8": "fixture",
                    "semantic_id": "target.py#function:target_symbol:fixture",
                    "signature_hash": "fixture",
                }
            ]
        },
        "command_index": {},
        "files": [{"path": "target.py"}],
        "topology": {"source": "focused_test_fixture", "file_index": {"target.py": {}}},
    }
    (aura_dir / "CODEMAP.json").write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _raise_secret(*_args, **_kwargs):
    raise RuntimeError("SECRET_PAYLOAD_MUST_NOT_ESCAPE")


def test_resolver_reports_bounded_optional_dependency_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_minimal_codemap(tmp_path)
    monkeypatch.setattr(aura_affordance_directory, "find_affordances", _raise_secret)
    monkeypatch.setattr(aura_capability_lane_registry, "load_capability_lanes", _raise_secret)
    monkeypatch.setattr(
        aura_cockpit_plugin_registration,
        "list_registered_plugins",
        _raise_secret,
    )
    monkeypatch.setattr(aura_agent_workbench_interface, "list_agent_actions", _raise_secret)
    monkeypatch.setattr(aura_module_manifest, "load_module_manifest", _raise_secret)

    packet = resolve_capabilities(
        "Use target_symbol from target.py",
        target_files=["target.py"],
        target_symbols=["target_symbol"],
        repo_root=tmp_path,
    )

    assert packet["exact_matches"][0]["file"] == "target.py"
    assert packet["evidence_complete"] is False
    assert packet["evidence_status"] == "PARTIAL_DEPENDENCY_FAILURE"
    assert packet["dependency_failures"] == [
        {"owner": "affordance_directory", "error_type": "RuntimeError", "status": "UNAVAILABLE"},
        {"owner": "capability_lane_registry", "error_type": "RuntimeError", "status": "UNAVAILABLE"},
        {"owner": "cockpit_plugin_registry", "error_type": "RuntimeError", "status": "UNAVAILABLE"},
        {"owner": "agent_workbench_interface", "error_type": "RuntimeError", "status": "UNAVAILABLE"},
        {"owner": "module_manifest", "error_type": "RuntimeError", "status": "UNAVAILABLE"},
    ]
    assert "SECRET_PAYLOAD_MUST_NOT_ESCAPE" not in json.dumps(packet, sort_keys=True)


def test_resolver_default_does_not_persist_missing_module_manifest(tmp_path: Path) -> None:
    _write_minimal_codemap(tmp_path)

    packet = resolve_capabilities(
        "Use target_symbol from target.py",
        target_files=["target.py"],
        target_symbols=["target_symbol"],
        repo_root=tmp_path,
    )

    assert packet["module_manifest_hash"]
    assert not (tmp_path / ".aura" / "MODULE_MANIFEST.json").exists()


def test_invalid_existing_manifest_is_reported_as_bounded_dependency_failure(
    tmp_path: Path,
) -> None:
    _write_minimal_codemap(tmp_path)
    manifest_path = tmp_path / ".aura" / "MODULE_MANIFEST.json"
    manifest_path.write_text('{"secret": "MUST_NOT_ESCAPE",', encoding="utf-8")

    packet = resolve_capabilities(
        "Use target_symbol from target.py",
        target_files=["target.py"],
        target_symbols=["target_symbol"],
        repo_root=tmp_path,
    )

    assert packet["exact_matches"][0]["file"] == "target.py"
    assert packet["module_manifest_hash"] == ""
    assert packet["evidence_complete"] is False
    assert packet["evidence_status"] == "PARTIAL_DEPENDENCY_FAILURE"
    assert {"owner": "module_manifest", "error_type": "JSONDecodeError", "status": "UNAVAILABLE"} in packet[
        "dependency_failures"
    ]
    assert "MUST_NOT_ESCAPE" not in json.dumps(packet, sort_keys=True)
    assert load_module_manifest(tmp_path, persist_if_missing=True) is None


def test_module_manifest_persistence_remains_explicit(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text("def sample():\n    return 1\n", encoding="utf-8")

    in_memory = load_module_manifest(tmp_path, persist_if_missing=False)
    assert in_memory and in_memory["modules"]
    assert not (tmp_path / ".aura" / "MODULE_MANIFEST.json").exists()

    persisted = load_module_manifest(tmp_path, persist_if_missing=True)
    assert persisted == in_memory
    assert (tmp_path / ".aura" / "MODULE_MANIFEST.json").is_file()


def test_waboose_source_owner_detection_excludes_diagnostic_inventories() -> None:
    assert _is_source_owner("_watchdog_artifact_inventory") is False
    assert _is_source_owner("_runtime_process_inventory") is False
    assert _is_source_owner("_repo_python_sources") is True
    assert _is_source_owner("_repository_sources") is True
    assert _is_source_owner("_source_inventory") is True


def test_real_refactor_trial_uses_live_parent_when_push_before_is_zero() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workflow = (repo_root / ".github" / "workflows" / "architect-real-refactor-trial.yml").read_text(
        encoding="utf-8"
    )

    assert "NEED_PARENT_BASE=1" in workflow
    assert "fetch --no-tags --depth=2 origin" in workflow
    assert 'ACCEPTANCE_SCOPE_BASE_SHA="$(git rev-parse "$TARGET_SHA^")"' in workflow
    assert 'ACCEPTANCE_SCOPE_BASE_SHA="$BENCHMARK_BASE_SHA"' not in workflow
