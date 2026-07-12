"""Focused enforcement tests for Phase C2 aperture and localization boundaries."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

from aura_coding_workbench_capsule_adapter import CapsuleCodingWorkbenchWFSTSession
from aura_route_capsule_compiler import compile_route_capsule
from aura_route_capsule_materializer import materialize_route_capsule

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPSULE_REF = ".aura/route_capsules/coding_localize.v1.json"
LEASE = "tool:topology_inspector"
_COMPONENT_REFS = (
    ".aura/route_capsules/coding_localize.v1.json",
    ".aura/morphology_profiles/six_slot.v1.json",
    ".aura/vsa_profiles/complex_phasor.v1.json",
    ".aura/data_apertures/coding_localize.v1.json",
    ".aura/memory_apertures/coding_localize.v1.json",
    ".aura/tool_bundles/coding_localize.v1.json",
    ".aura/model_policies/local_first.v1.json",
    ".aura/execution_budgets/coding_localize.v1.json",
    ".aura/verifier_contracts/coding_localize.v1.json",
    ".aura/output_schemas/localization_packet.v1.json",
)


def _fixture_repo(tmp_path: Path) -> Path:
    for relative in _COMPONENT_REFS:
        source = REPO_ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return tmp_path


def _resolver(capabilities):
    return {
        "ok": True,
        "bindings": [
            {"capability_id": item, "kind": "test_binding", "grounded": True}
            for item in capabilities
        ],
        "denials": [],
    }


def _compile(repo_root: Path):
    result = compile_route_capsule(
        CAPSULE_REF,
        repo_root=repo_root,
        capability_resolver=_resolver,
    )
    assert result.ok, [item.to_dict() for item in result.diagnostics]
    return result.compiled


def test_materializer_rejects_missing_context_limit(tmp_path: Path):
    root = _fixture_repo(tmp_path)
    path = root / ".aura/data_apertures/coding_localize.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("maximum_files")
    path.write_text(json.dumps(payload), encoding="utf-8")
    denied = materialize_route_capsule(
        _compile(root),
        repo_root=root,
        policy={"route_capsules_enabled": True},
        context={"lease_capabilities": [LEASE]},
    )
    assert denied["ok"] is False
    assert denied["reason"] == "capsule_limits_missing"
    assert "maximum_files" in denied["missing"]


def test_zero_budget_is_a_real_zero_not_unlimited(tmp_path: Path):
    root = _fixture_repo(tmp_path)
    path = root / ".aura/execution_budgets/coding_localize.v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["model_calls"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    denied = materialize_route_capsule(
        _compile(root),
        repo_root=root,
        policy={"route_capsules_enabled": True},
        context={
            "lease_capabilities": [LEASE],
            "requested_model": "no_model",
            "capsule_budget_consumed": {"model_calls": 1},
        },
    )
    assert denied["ok"] is False
    assert denied["reason"] == "capsule_budget_exceeded"
    assert "model_calls" in denied["missing"]


def test_localization_clamps_ranges_and_adds_exact_source_hashes(monkeypatch):
    import aura_coding_workbench_actions

    monkeypatch.setattr(
        aura_coding_workbench_actions,
        "localize_code",
        lambda objective, repo_root: {
            "ok": True,
            "localized_files": [
                "aura_route_capsule_materializer.py",
                "aura_route_capsule_live_runtime.py",
            ],
            "localized_symbols": [
                "materialize_route_capsule",
                "CapsuleAwareArenaWFSTRuntime",
            ],
            "line_ranges": [[1, 10], [1, 10]],
            "affected_tests": [],
        },
    )

    class Runtime:
        last_route = {
            "selected": {
                "route_capsule": {
                    "capsule_id": "CODING.LOCALIZE.V1",
                    "capsule_digest": "capsule-digest",
                },
                "materialized_aperture": {
                    "aperture_digest": "aperture-digest",
                    "data_aperture": {
                        "maximum_files": 1,
                        "maximum_symbols": 1,
                        "maximum_lines": 10,
                        "require_source_hashes": True,
                    },
                    "tool_bundle": {
                        "capability_bindings": [
                            {"capability_id": LEASE, "grounded": True}
                        ]
                    },
                    "selected_model": "no_model",
                    "execution_budget": {
                        "input_tokens": 6000,
                        "output_tokens": 1500,
                        "tool_calls": 8,
                        "model_calls": 0,
                        "wall_seconds": 120,
                    },
                },
            }
        }

    session = CapsuleCodingWorkbenchWFSTSession.__new__(
        CapsuleCodingWorkbenchWFSTSession
    )
    session.repo_root = REPO_ROOT
    session.objective = "Inspect the C2 capsule materializer"
    session.evidence = {}
    session.route_capsules_enabled = True
    session.runtime = Runtime()
    session._capsule_context_items = []
    session._capsule_budget_consumed = {}

    result = session._do_localize_code({})
    assert result["ok"] is True
    produced = result["produced_evidence"]
    assert produced["localized_files"] == ["aura_route_capsule_materializer.py"]
    assert produced["localized_symbols"] == ["materialize_route_capsule"]
    assert produced["line_ranges"] == [[1, 10]]
    assert len(produced["source_hashes"]) == 1
    assert len(produced["source_hashes"][0]["source_hash"]) == 40
    assert produced["exact_source_spans"][0]["line_start"] == 1
    assert produced["exact_source_spans"][0]["line_end"] == 10
    assert result["capsule_usage"]["context_items"][0]["source_hash"]
    assert session.evidence["source_hashes"] == produced["source_hashes"]
