from __future__ import annotations

import copy
import json
import threading
import time
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
import pytest

import aura_ephemeral_workspace_runtime_v2 as runtime
from aura_ephemeral_adapter_registry import AdapterMetadata, OperationalAdapterRegistry
from aura_ephemeral_manifest import create_manifest
from aura_ephemeral_registry_store import SCHEMA_VERSION, EphemeralRegistryStore
from aura_ephemeral_workspace_contracts import (
    CanonicalReference,
    EphemeralWorkspaceRecipe,
    ProjectContextProjection,
    RepositoryIdentity,
    WorkspaceBudget,
    compile_coding_spatial_workspace_recipe,
    stable_digest,
)

ROOT = Path(__file__).resolve().parents[1]
D = {str(i): f"{i:x}" * 64 for i in range(1, 10)}
MAIN = "9c04a1efa57461a6078acb9f3b569766cbd2ab24"


def _ref(name: str, digest: str) -> CanonicalReference:
    return CanonicalReference(
        name, "canonical.owner", f"owner://{name}", digest,
        truth_class="EXACT", freshness_class="CURRENT", metadata={},
    )


def _project() -> ProjectContextProjection:
    return ProjectContextProjection(
        "project:auraos-intent-spatial-pr2",
        "repository:dallascourchene-commits/AuraOS",
        "aura_unified_memory_continuity",
        D["1"], D["2"],
        RepositoryIdentity(
            "dallascourchene-commits/AuraOS", "refs/heads/main", MAIN, D["6"],
        ),
        (_ref("artifact:codemap", D["3"]),),
        decision_refs=(_ref("decision:pr2", D["4"]),),
        relationship_refs=(_ref("relationship:compass", D["5"]),),
        freshness_timestamp_ms=1_722_737_640_000,
        completeness_warnings=("External project stores remain unadmitted.",),
    )


def _recipe(
    *, ttl: int = 300, wall_time_ms: int | None = None, memory_mb: int | None = None,
) -> EphemeralWorkspaceRecipe:
    manifest = create_manifest(
        "Compile a verified interactive Ephemeral Workspace V2.",
        organ_id="EORG-intent-spatial-pr2",
        ttl_seconds=ttl,
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    project = _project()
    budgets = None
    if wall_time_ms is not None or memory_mb is not None:
        budgets = WorkspaceBudget(
            wall_time_ms=30_000 if wall_time_ms is None else wall_time_ms,
            memory_mb=256 if memory_mb is None else memory_mb,
            context_tokens=64_000,
            output_bytes=1_000_000,
            tool_calls=20,
            model_calls=0,
            cost_microusd=0,
            network_calls=0,
        )
    return compile_coding_spatial_workspace_recipe(
        base_manifest=manifest,
        expected_manifest_timestamps=(manifest.created_at, manifest.expires_at),
        project_projection=project,
        expected_project_projection=project,
        canonical_intent_digest=D["1"],
        adapter_refs=(_ref("adapter:runtime-v2", D["2"]),),
        evidence_refs=(_ref("evidence:source", D["3"]), _ref("evidence:tests", D["4"])),
        budgets=budgets,
        ttl_seconds=ttl,
    )


def _ok_adapter(**params: Any) -> dict[str, Any]:
    return {"ok": True, "echo": params}


def _hostile_adapter(**params: Any) -> dict[str, Any]:
    raise RuntimeError("hostile callback")


def _slow_file_adapter(
    *, started_file: str = "", completed_file: str = "", delay_seconds: float = 1.0,
    **params: Any,
) -> dict[str, Any]:
    Path(started_file).write_text("started", encoding="utf-8")
    time.sleep(delay_seconds)
    Path(completed_file).write_text("completed", encoding="utf-8")
    return {"ok": True, "echo": params}


def _interrupt_adapter(**params: Any) -> dict[str, Any]:
    raise KeyboardInterrupt()


def _memory_hog_adapter(*, allocation_mb: int = 512, **params: Any) -> dict[str, Any]:
    payload = bytearray(allocation_mb * 1024 * 1024)
    return {"ok": True, "allocated_bytes": len(payload), "echo": params}


def _recursive_result_adapter(**params: Any) -> dict[str, Any]:
    recursive: dict[str, Any] = {"ok": True}
    recursive["loop"] = recursive
    return recursive


def _escape_adapter(**params: Any) -> dict[str, Any]:
    return {"ok": True, "path": "/tmp/outside-aura-workspace"}


def _hidden_absolute_adapter(**params: Any) -> dict[str, Any]:
    return {"ok": True, "untrusted": "/tmp/outside-hidden-key"}


def _hidden_traversal_adapter(**params: Any) -> dict[str, Any]:
    return {"ok": True, "untrusted": "../outside-hidden-key"}


def _symlink_output_adapter(*, artifact_path: str = "", **params: Any) -> dict[str, Any]:
    return {"ok": True, "artifact_path": artifact_path, "echo": params}


def _spoof_failure_adapter(**params: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "adapter_deadline_exceeded",
        "failure_class": "policy",
        "_aura_bounded_event": "DEADLINE",
    }


def _registry(recipe: EphemeralWorkspaceRecipe, overrides: dict[str, Any] | None = None):
    registry = OperationalAdapterRegistry()
    bindings: dict[str, str] = {}
    overrides = overrides or {}
    for capability_id in recipe.capability_ids:
        adapter_id = f"adapter.{capability_id}"
        implementation = overrides.get(capability_id, _ok_adapter)
        handoff = capability_id == "prepare_forge_handoff"
        registry.declare(
            AdapterMetadata(
                adapter_id=adapter_id,
                side_effect_class="domain_handoff" if handoff else "read_only",
                human_approval_policy="required" if handoff else "not_required",
                implementation_ref=f"tests.{capability_id}",
                rollback_ref="tests._ok_adapter",
                tests=["tests/test_aura_ephemeral_workspace_runtime_v2.py"],
            ),
            implementation=implementation,
        )
        bindings[capability_id] = adapter_id
    return registry, bindings


def _admitted(
    tmp_path: Path,
    *,
    overrides: dict[str, Any] | None = None,
    recipe_override: EphemeralWorkspaceRecipe | None = None,
):
    recipe = _recipe() if recipe_override is None else recipe_override
    registry, bindings = _registry(recipe, overrides)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    store = EphemeralRegistryStore.for_tests(tmp_path)
    admitted = runtime.admit_workspace_v2(
        graph,
        expected_recipe=recipe,
        expected_adapter_bindings=bindings,
        adapter_registry=registry,
        store=store,
        activation_nonce=f"nonce-{tmp_path.name}",
    )
    assert admitted["ok"]
    return recipe, registry, bindings, graph, store, admitted["workspace_id"]


def _execute_all(workspace_id: str, graph: dict[str, Any], store: EphemeralRegistryStore,
                 registry: OperationalAdapterRegistry) -> None:
    for _ in range(len(graph["nodes"]) + 1):
        record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
        if len(record["node_receipts"]) == len(graph["nodes"]):
            return
        gates = {
            node["node_id"]: runtime.build_human_gate_receipt_v2(
                workspace_id=workspace_id, graph_digest=graph["graph_digest"],
                node_id=node["node_id"],
            )
            for node in graph["nodes"] if node["human_gate"]
        }
        result = runtime.execute_ready_wave_v2(
            workspace_id, params_by_node={}, store=store,
            adapter_registry=registry, human_gate_receipts=gates,
        )
        assert result["ok"], result
    raise AssertionError("graph did not complete")


def test_store_migrates_additive_v2_without_changing_v1(tmp_path: Path) -> None:
    store = EphemeralRegistryStore.for_tests(tmp_path)
    assert SCHEMA_VERSION == 2
    assert store.register({
        "organ_id": "legacy", "manifest_digest": D["1"], "state": "DRAFTED",
        "created_at": time.time(), "expires_at": time.time() + 60,
    })["ok"]
    assert store.get("legacy")["organ"]["state"] == "DRAFTED"
    tables = {row[0] for row in store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"ephemeral_organs", "ephemeral_workspaces_v2"} <= tables


def test_adapter_identity_is_deterministic_and_revocable() -> None:
    first, second = OperationalAdapterRegistry(), OperationalAdapterRegistry()
    meta1 = AdapterMetadata(adapter_id="adapter.test", implementation_ref="tests._ok_adapter")
    meta2 = AdapterMetadata(adapter_id="adapter.test", implementation_ref="tests._ok_adapter")
    first.declare(meta1, implementation=_ok_adapter)
    second.declare(meta2, implementation=_ok_adapter)
    assert meta1.adapter_digest == meta2.adapter_digest
    assert meta1.implementation_digest == meta2.implementation_digest
    before = meta1.adapter_digest
    assert first.revoke("adapter.test", reason="test revocation")["ok"]
    assert not first.is_operational("adapter.test")
    assert meta1.adapter_digest != before
    assert first.execute("adapter.test", params={})["status"] == "DENIED"


def test_adapter_registry_list_bindings_and_closed_identity_version() -> None:
    registry = OperationalAdapterRegistry()
    meta_a = AdapterMetadata(adapter_id="adapter.a", implementation_ref="tests._ok_adapter")
    meta_b = AdapterMetadata(adapter_id="adapter.b", implementation_ref="tests._ok_adapter")
    assert registry.declare(meta_b, implementation=_ok_adapter)["ok"]
    assert registry.declare(meta_a, implementation=_ok_adapter)["ok"]

    listed = registry.list_adapters()
    assert listed["ok"] and listed["count"] == 2
    assert [item["adapter_id"] for item in listed["adapters"]] == ["adapter.a", "adapter.b"]
    before_b = {item["adapter_id"]: item for item in listed["adapters"]}["adapter.b"]
    binding_before = registry.get_binding("adapter.b")
    assert binding_before["ok"]
    assert binding_before["binding"]["adapter_digest"] == before_b["adapter_digest"]
    assert binding_before["binding"]["implementation_digest"] == before_b["implementation_digest"]

    assert registry.revoke("adapter.b", reason="test revocation")["ok"]
    after_b = {
        item["adapter_id"]: item for item in registry.list_adapters()["adapters"]
    }["adapter.b"]
    assert after_b["revocation_state"] == "REVOKED"
    assert after_b["operational_status"] == "DENIED"
    assert after_b["revocation_reason"] == "test revocation"
    binding_after = registry.get_binding("adapter.b")["binding"]
    assert binding_after["revocation_state"] == "REVOKED"
    assert binding_after["adapter_digest"] == after_b["adapter_digest"]
    assert binding_after["implementation_digest"] == after_b["implementation_digest"]

    invalid = AdapterMetadata(
        adapter_id="adapter.invalid-version", implementation_ref="tests._ok_adapter",
        identity_version="unrecognized",
    )
    with pytest.raises(ValueError, match="invalid identity_version"):
        registry.declare(invalid, implementation=_ok_adapter)


def test_graph_compile_parse_bind_is_deterministic() -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    assert runtime.parse_workspace_execution_graph_v2(graph) == graph
    assert runtime.bind_workspace_execution_graph_v2(
        graph, expected_recipe=recipe, expected_adapter_bindings=bindings,
        adapter_registry=registry,
    ) == graph
    assert graph["max_parallelism"] == 1
    assert graph["arbitrary_native_execution"] is False
    assert len(graph["terminal_node_ids"]) == 3


def test_graph_requires_complete_adapter_identity_and_human_gate() -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    missing = dict(bindings)
    missing.pop(next(iter(missing)))
    with pytest.raises(ValueError, match="complete recipe capability"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=missing, adapter_registry=registry,
        )
    bad = OperationalAdapterRegistry()
    bad_bindings = {}
    for capability in recipe.capability_ids:
        adapter_id = f"bad.{capability}"
        bad.declare(AdapterMetadata(
            adapter_id=adapter_id,
            side_effect_class="domain_handoff" if capability == "prepare_forge_handoff" else "read_only",
            human_approval_policy="not_required",
        ), implementation=_ok_adapter)
        bad_bindings[capability] = adapter_id
    with pytest.raises(ValueError, match="lacks a human gate"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=bad_bindings, adapter_registry=bad,
        )


@pytest.mark.parametrize("mutation, message", [
    (lambda g: g["edges"].append({"source_node_id": g["terminal_node_ids"][0],
                                  "target_node_id": g["entry_node_ids"][0]}), "cycle"),
    (lambda g: g.__setitem__("terminal_node_ids", g["terminal_node_ids"][:-1]), "terminal"),
    (lambda g: g["nodes"][0].__setitem__("effect_class", "native"), "effect"),
    (lambda g: g["budgets"].__setitem__("network_calls", 1), "network"),
])
def test_graph_semantics_fail_closed(mutation, message: str) -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    altered = copy.deepcopy(graph)
    mutation(altered)
    # Re-sign only the outer graph so semantic validation is reached.
    altered["graph_digest"] = stable_digest(runtime._graph_identity_body(altered))
    altered["graph_id"] = f"workspace-graph:{altered['graph_digest'][:24]}"
    with pytest.raises(ValueError, match=message):
        runtime.validate_workspace_execution_graph_v2(altered)


def test_complete_graph_binding_rejects_self_consistent_stale_adapter() -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    registry.revoke(bindings[recipe.capability_ids[0]], reason="security incident")
    with pytest.raises(ValueError, match=r"revoked|operational"):
        runtime.bind_workspace_execution_graph_v2(
            graph, expected_recipe=recipe, expected_adapter_bindings=bindings,
            adapter_registry=registry,
        )


def test_duplicate_activation_and_dissolved_resume_are_denied(tmp_path: Path) -> None:
    _, registry, _, _graph, store, workspace_id = _admitted(tmp_path)
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    assert not runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    assert runtime.cancel_workspace_v2(workspace_id, store=store)["ok"]
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"
    assert not runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    assert not store.is_workspace_v2_lease_active(workspace_id)


def test_valid_lifecycle_executes_graph_and_cleans_up(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    activated = runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert activated["ok"] and activated["arbitrary_native_execution"] is False
    sandbox = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["sandbox_path"]
    assert Path(sandbox).is_dir()
    _execute_all(workspace_id, graph, store, registry)
    completed = runtime.complete_workspace_v2(workspace_id, store=store)
    assert completed["ok"] and completed["state"] == "DISSOLVED"
    assert not Path(sandbox).exists()
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert record["cleanup_receipt"]["cleanup_verified"] is True
    assert len(record["node_receipts"]) == len(graph["nodes"])


def test_node_requires_dependencies_and_exact_human_gate(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    handoff = next(node for node in graph["nodes"] if node["human_gate"])
    early = runtime.execute_workspace_node_v2(
        workspace_id, handoff["node_id"], params={}, store=store,
        adapter_registry=registry,
    )
    assert early["error"] == "upstream_receipts_missing"
    # Execute until handoff is ready.
    for _ in range(5):
        record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
        if handoff["node_id"] in runtime._ready_node_ids(record):
            break
        assert runtime.execute_ready_wave_v2(
            workspace_id, params_by_node={}, store=store, adapter_registry=registry,
        )["ok"]
    denied = runtime.execute_workspace_node_v2(
        workspace_id, handoff["node_id"], params={}, store=store,
        adapter_registry=registry,
    )
    assert denied["error"] == "human_gate_required"
    approval = runtime.build_human_gate_receipt_v2(
        workspace_id=workspace_id, graph_digest=graph["graph_digest"],
        node_id=handoff["node_id"],
    )
    assert runtime.execute_workspace_node_v2(
        workspace_id, handoff["node_id"], params={}, store=store,
        adapter_registry=registry, human_gate_receipt=approval,
    )["ok"]


def test_ordinary_hostile_callback_failure_normalizes_and_cleans(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path, overrides={first: _hostile_adapter},
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    result = runtime.execute_workspace_node_v2(
        workspace_id, first, params={}, store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "environment"
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_cancellation_during_adapter_execution_cannot_commit_receipt(
    tmp_path: Path,
) -> None:
    started_path = tmp_path / "cancel-started"
    completed_path = tmp_path / "cancel-completed"
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _slow_file_adapter}
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]

    result_box: dict[str, Any] = {}

    def execute() -> None:
        result_box["result"] = runtime.execute_workspace_node_v2(
            workspace_id,
            graph["entry_node_ids"][0],
            params={
                "started_file": str(started_path),
                "completed_file": str(completed_path),
                "delay_seconds": 1.0,
            },
            store=store,
            adapter_registry=registry,
        )

    worker = threading.Thread(target=execute)
    worker.start()
    deadline = time.time() + 5
    while not started_path.exists() and time.time() < deadline:
        time.sleep(0.01)
    assert started_path.exists()
    cancelled = runtime.cancel_workspace_v2(workspace_id, store=store)
    assert cancelled["ok"] and cancelled["state"] == "DISSOLVED"
    worker.join(timeout=5)
    assert not worker.is_alive()

    result = result_box["result"]
    assert not result["ok"]
    assert result["error"] == "workspace_execution_invalidated"
    assert result["receipt_committed"] is False
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert record["state"] == "DISSOLVED"
    assert graph["entry_node_ids"][0] not in record["node_receipts"]
    time.sleep(1.2)
    assert not completed_path.exists()


def test_bounded_adapter_deadline_kills_callback_process(tmp_path: Path) -> None:
    started_path = tmp_path / "deadline-started"
    completed_path = tmp_path / "deadline-completed"
    registry = OperationalAdapterRegistry()
    declared = registry.declare(
        AdapterMetadata(adapter_id="adapter.deadline-test", implementation_ref="tests._slow_file_adapter"),
        implementation=_slow_file_adapter,
    )
    assert declared["ok"]
    result = registry.execute(
        "adapter.deadline-test",
        params={
            "started_file": str(started_path),
            "completed_file": str(completed_path),
            "delay_seconds": 1.0,
        },
        deadline_monotonic=time.monotonic() + 0.25,
        authority_check=lambda: True,
        max_output_bytes=4096,
    )
    assert not result["ok"]
    assert result["error"] == "adapter_deadline_exceeded"
    assert result["_aura_bounded_event"] == "DEADLINE"
    assert started_path.exists()
    time.sleep(0.9)
    assert not completed_path.exists()


def test_activation_evidence_write_failure_destroys_unpersisted_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    sandbox_dir = tmp_path / "activation-unpersisted-sandbox"
    sandbox_dir.mkdir()

    def fake_prepare_sandbox(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "temp_dir": str(sandbox_dir),
            "receipt": {"sandbox_mode": "builtin_only"},
        }

    original_update = store.update_workspace_v2

    def reject_activation_evidence(target_workspace_id: str, **fields: Any) -> dict[str, Any]:
        if "sandbox_path" in fields:
            return {"ok": False, "workspace_id": target_workspace_id}
        return original_update(target_workspace_id, **fields)

    monkeypatch.setattr(runtime, "prepare_sandbox", fake_prepare_sandbox)
    monkeypatch.setattr(store, "update_workspace_v2", reject_activation_evidence)

    result = runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert not result["ok"]
    assert "activation evidence update failed" in result["error"]
    assert not sandbox_dir.exists()
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"


def test_zero_memory_budget_rejected_at_v2_executable_boundary(tmp_path: Path) -> None:
    recipe = _recipe(wall_time_ms=1000, memory_mb=0)
    registry, bindings = _registry(recipe)
    with pytest.raises(ValueError, match="memory_mb must be at least 1"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=bindings, adapter_registry=registry,
        )


def test_bounded_memory_budget_prevents_host_memory_exhaustion(tmp_path: Path) -> None:
    recipe = _recipe(ttl=5, wall_time_ms=3000, memory_mb=256)
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _memory_hog_adapter}, recipe_override=recipe,
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0],
        params={"allocation_mb": 512},
        store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "environment"
    assert "MemoryError" in result["error"] or "worker" in result["error"]
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"
    assert graph["entry_node_ids"][0] not in final["node_receipts"]


def test_runtime_wall_time_deadline_dissolves_and_kills_callback(tmp_path: Path) -> None:
    started_path = tmp_path / "budget-started"
    completed_path = tmp_path / "budget-completed"
    recipe = _recipe(ttl=5, wall_time_ms=250)
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _slow_file_adapter}, recipe_override=recipe,
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0],
        params={
            "started_file": str(started_path),
            "completed_file": str(completed_path),
            "delay_seconds": 1.0,
        },
        store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "budget"
    assert "deadline exceeded" in result["error"]
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"
    assert graph["entry_node_ids"][0] not in final["node_receipts"]
    assert started_path.exists()
    time.sleep(0.9)
    assert not completed_path.exists()


def test_workspace_ttl_expiry_during_callback_kills_execution_and_cleans(tmp_path: Path) -> None:
    started_path = tmp_path / "ttl-started"
    completed_path = tmp_path / "ttl-completed"
    # The compiler floors remaining TTL; 10 requested seconds yields a 9-second effective TTL.
    # Match that budget so TTL remains the earliest authority deadline while leaving child startup margin.
    recipe = _recipe(ttl=10, wall_time_ms=9000)
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _slow_file_adapter}, recipe_override=recipe,
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    expires_at = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["expires_at"]
    remaining = expires_at - time.time()
    if remaining > 2.0:
        time.sleep(remaining - 2.0)
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0],
        params={
            "started_file": str(started_path),
            "completed_file": str(completed_path),
            "delay_seconds": 5.0,
        },
        store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["error"] == "workspace_execution_expired"
    assert result["failure"]["failure_class"] == "stale"
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"
    assert graph["entry_node_ids"][0] not in final["node_receipts"]
    assert started_path.exists()
    time.sleep(0.5)
    assert not completed_path.exists()


def test_workspace_cumulative_wall_time_budget_blocks_new_callback(tmp_path: Path) -> None:
    recipe = _recipe(ttl=5, wall_time_ms=250)
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, recipe_override=recipe,
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    time.sleep(0.3)
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={},
        store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "budget"
    assert result["error"] == "workspace wall-time budget exhausted"
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"
    assert not final["node_receipts"]


def test_hostile_callback_cannot_spoof_deadline_or_failure_class(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _spoof_failure_adapter},
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={},
        store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "local"
    assert result["error"] == "adapter_deadline_exceeded"
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"


def test_child_process_interruption_is_parent_owned_worker_failure(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path, overrides={first: _interrupt_adapter},
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    result = runtime.execute_workspace_node_v2(
        workspace_id, first, params={}, store=store, adapter_registry=registry,
    )
    assert not result["ok"]
    assert result["failure"]["failure_class"] == "environment"
    assert "bounded_adapter_worker_interruption: KeyboardInterrupt" in result["error"]
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"


def test_authority_check_failure_uses_parent_owned_environment_event() -> None:
    registry = OperationalAdapterRegistry()
    declared = registry.declare(
        AdapterMetadata(
            adapter_id="adapter.authority-check-test",
            implementation_ref="tests._ok_adapter",
        ),
        implementation=_ok_adapter,
    )
    assert declared["ok"]

    def broken_authority_check() -> bool:
        raise RuntimeError("authority store unavailable")

    result = registry.execute(
        "adapter.authority-check-test",
        params={},
        deadline_monotonic=time.monotonic() + 1.0,
        authority_check=broken_authority_check,
        max_output_bytes=4096,
    )
    assert not result["ok"]
    assert result["_aura_bounded_event"] == "AUTHORITY_CHECK_FAILED"
    assert result["failure_class"] == "environment"
    assert "authority store unavailable" in result["error"]


def test_authority_check_false_emits_parent_owned_revocation_event() -> None:
    registry = OperationalAdapterRegistry()
    assert registry.declare(
        AdapterMetadata(
            adapter_id="adapter.authority-revoked-test",
            implementation_ref="tests._ok_adapter",
        ),
        implementation=_ok_adapter,
    )["ok"]
    result = registry.execute(
        "adapter.authority-revoked-test",
        params={},
        deadline_monotonic=time.monotonic() + 1.0,
        authority_check=lambda: False,
        max_output_bytes=4096,
    )
    assert not result["ok"]
    assert result["_aura_bounded_event"] == "AUTHORITY_REVOKED"
    assert result["failure_class"] == "cancellation"


def test_recursive_output_and_path_escape_fail_closed(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path / "recursive", overrides={first: _recursive_result_adapter},
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert not runtime.execute_workspace_node_v2(
        workspace_id, first, params={}, store=store, adapter_registry=registry,
    )["ok"]

    _, registry2, _, _, store2, workspace_id2 = _admitted(
        tmp_path / "escape", overrides={first: _escape_adapter},
    )
    runtime.activate_workspace_v2(
        workspace_id2, store=store2, adapter_registry=registry2, repo_root=str(ROOT),
    )
    result = runtime.execute_workspace_node_v2(
        workspace_id2, first, params={}, store=store2, adapter_registry=registry2,
    )
    assert not result["ok"] and "escapes" in result["error"]


def test_expiry_invalidates_and_dissolves(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    expires = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["expires_at"]
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime._expire_if_needed(workspace_id, store=store, now=expires + 1)
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert record["state"] == "DISSOLVED"
    assert record["failure_records"][-1]["failure_class"] == "stale"


def test_store_v2_lease_and_expiry_helpers_track_lifecycle(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "lease")
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert store.is_workspace_v2_lease_active(workspace_id, now=record["expires_at"] - 1)
    assert not store.is_workspace_v2_lease_active(workspace_id, now=record["expires_at"] + 1)
    assert store.revoke_workspace_v2_lease(workspace_id, reason="direct helper test")["ok"]
    assert not store.is_workspace_v2_lease_active(workspace_id)

    _, _, _, _, store2, workspace_id2 = _admitted(tmp_path / "expired-list")
    record2 = runtime.workspace_status_v2(workspace_id2, store=store2)["workspace"]
    listed = store2.list_expired_workspaces_v2(now=record2["expires_at"] + 1)
    assert workspace_id2 in listed["workspace_ids"]
    assert store2.transition_workspace_v2(workspace_id2, "ADMITTED", "DISSOLVING")["ok"]
    assert workspace_id2 not in store2.list_expired_workspaces_v2(
        now=record2["expires_at"] + 1
    )["workspace_ids"]
    assert store2.transition_workspace_v2(workspace_id2, "DISSOLVING", "DISSOLVED")["ok"]
    assert workspace_id2 not in store2.list_expired_workspaces_v2(
        now=record2["expires_at"] + 1
    )["workspace_ids"]


def test_terminal_reason_survives_reasonless_state_transition(tmp_path: Path) -> None:
    _, _, _, _, store, workspace_id = _admitted(tmp_path / "terminal-reason")
    assert store.update_workspace_v2(workspace_id, terminal_reason="preserve-me")["ok"]
    assert store.transition_workspace_v2(workspace_id, "ADMITTED", "ACTIVATING")["ok"]
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert record["terminal_reason"] == "preserve-me"


def test_expiry_state_race_converges_to_dissolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "expiry-race")
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    expires_at = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["expires_at"]
    original_transition = store.transition_workspace_v2

    def race_transition(
        target_workspace_id: str, expected_from: str | tuple[str, ...], to: str,
        *, terminal_reason: str = "",
    ) -> dict[str, Any]:
        if to == "EXPIRING":
            original_transition(
                target_workspace_id, expected_from, "CANCELLING",
                terminal_reason="concurrent_cancel",
            )
            return {"ok": False, "error": "stale_workspace_state"}
        return original_transition(
            target_workspace_id, expected_from, to, terminal_reason=terminal_reason,
        )

    monkeypatch.setattr(store, "transition_workspace_v2", race_transition)
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime._expire_if_needed(workspace_id, store=store, now=expires_at + 1)
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"


def test_tool_call_budget_overflow_fails_and_cleans(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    usage = dict(record["usage_json"])
    usage["tool_calls"] = graph["budgets"]["tool_calls"]
    store.update_workspace_v2(workspace_id, usage_json=usage)
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={}, store=store,
        adapter_registry=registry,
    )
    assert not result["ok"] and result["failure"]["failure_class"] == "budget"
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_adapter_revocation_after_activation_fails_closed(tmp_path: Path) -> None:
    recipe, registry, bindings, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    registry.revoke(bindings[recipe.capability_ids[0]], reason="incident")
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={}, store=store,
        adapter_registry=registry,
    )
    assert not result["ok"]
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_partial_reexecution_requires_unchanged_identity_closure(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    _execute_all(workspace_id, graph, store, registry)
    receipts = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["node_receipts"]
    changed = graph["entry_node_ids"][0]
    plan = runtime.partial_reexecution_plan_v2(
        graph, prior_receipts=receipts, changed_node_ids=[changed],
    )
    assert changed in plan["reexecute_node_ids"]
    assert set(plan["reexecute_node_ids"]) == {node["node_id"] for node in graph["nodes"]}
    tampered = copy.deepcopy(receipts)
    independent = graph["terminal_node_ids"][0]
    # With this frozen graph every entry change reaches all nodes, so use no declared change.
    tampered[independent]["assumptions_digest"] = D["9"]
    plan2 = runtime.partial_reexecution_plan_v2(
        graph, prior_receipts=tampered, changed_node_ids=[],
    )
    assert independent in plan2["reexecute_node_ids"]


def test_partial_reexecution_reuses_verified_receipts_when_identity_closure_is_unchanged(
    tmp_path: Path,
) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    _execute_all(workspace_id, graph, store, registry)
    receipts = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["node_receipts"]
    plan = runtime.partial_reexecution_plan_v2(
        graph, prior_receipts=receipts, changed_node_ids=[],
    )
    assert set(plan["reusable_node_ids"]) == set(receipts)
    assert plan["reexecute_node_ids"] == []


def test_action_certificate_lifecycle_is_monotonic_owner_bound_and_non_authoritative(tmp_path: Path) -> None:
    _, registry, _, _graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE", "FOCUSED_TESTS"], nonce="cert-nonce-1",
        expires_at=time.time() + 120,
    )
    assert prepared["ok"] and prepared["authorized"] is False
    with pytest.raises(ValueError, match="already has"):
        runtime.prepare_spatial_action_certificate_v2(
            workspace_id, store=store,
            principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
            subject_refs=["source:aura"], target_refs=["forge:candidate"],
            policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
            runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
            assumptions_digest=D["3"], cost_microusd=0, reversible=True,
            proof_obligations=["EXACT_SOURCE"], nonce="cert-nonce-1",
            expires_at=time.time() + 120,
        )
    status = "PREPARED"
    owners = ["spatial_runtime", "human:dallas", "aura_forge", "aura_runtime_refactor_harness"]
    for index, owner in enumerate(owners):
        advanced = runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status=status,
            evidence_digest=D[str(index + 4)], owner=owner,
            timestamp=time.time() + index,
        )
        assert advanced["ok"] and advanced["authorized"] is False
        status = advanced["certificate"]["status"]
    assert status == "CLOSED"
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["certificate_json"]
    assert runtime.validate_spatial_action_certificate_v2(
        final, expected_certificate=final,
        workspace_record=runtime.workspace_status_v2(workspace_id, store=store)["workspace"],
    )["status"] == "CLOSED"
    with pytest.raises(ValueError, match="illegal"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="CLOSED",
            evidence_digest=D["8"], owner="aura_runtime_refactor_harness",
        )


def test_action_certificate_cannot_self_authorize_execution(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-nonce-2",
        expires_at=time.time() + 120,
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime",
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="OPEN",
        evidence_digest=D["5"], owner="human:dallas",
    )
    with pytest.raises(ValueError, match="self-authorize"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="APPROVED",
            evidence_digest=D["6"], owner="spatial_runtime",
        )


def test_action_certificate_rejects_timestamp_regression_and_complete_record_drift(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-nonce-3",
        expires_at=time.time() + 120,
    )["certificate"]
    opened = runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime", timestamp=time.time() + 10,
    )["certificate"]
    with pytest.raises(ValueError, match="regressed"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="OPEN",
            evidence_digest=D["5"], owner="human:dallas", timestamp=time.time(),
        )
    drift = copy.deepcopy(opened)
    drift["policy_digest"] = D["8"]
    drift["certificate_digest"] = stable_digest(runtime._certificate_body(drift))
    with pytest.raises(ValueError, match="stale complete"):
        runtime.validate_spatial_action_certificate_v2(
            drift, expected_certificate=opened,
        )
    assert prepared["certificate_id"] == opened["certificate_id"]


def test_context_manager_cleans_on_exception(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    with pytest.raises(RuntimeError):
        with runtime.WorkspaceSessionV2(workspace_id, store=store):
            raise RuntimeError("session failed")
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_v2_schemas_are_meta_valid_and_delegate_semantics() -> None:
    for path in (
        ROOT / "schemas" / "aura_workspace_execution_graph_v2.schema.json",
        ROOT / "schemas" / "aura_spatial_action_certificate_v2.schema.json",
    ):
        schema = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        assert schema["x-aura-semantic-validator"]


def test_governance_records_bind_exact_scope_and_deny_automatic_merge() -> None:
    objective = json.loads((
        ROOT / ".aura" / "refactor_objectives" /
        "intent_native_ephemeral_workspace_pr2.v1.json"
    ).read_text(encoding="utf-8"))
    request = json.loads((
        ROOT / ".aura" / "waboose_requests" /
        "intent_native_ephemeral_workspace_pr2.v1.json"
    ).read_text(encoding="utf-8"))
    assert objective["source_main_sha"] == MAIN
    assert objective["status"] == "READY_FOR_HUMAN_REVIEW"
    assert objective["automatic_merge"] is False
    assert request["automatic_merge"] is False
    assert request["requested_reviewers"] == []
    assert set(objective["allowed_files"]) == set(request["files_to_review"])


def test_adapter_redeclaration_is_identity_based_and_status_is_explicit() -> None:
    registry = OperationalAdapterRegistry()
    first = AdapterMetadata(adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter")
    second = AdapterMetadata(adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter")
    assert registry.declare(first, implementation=_ok_adapter)["ok"]
    assert registry.declare(second, implementation=_ok_adapter)["ok"]
    assert first.adapter_digest == second.adapter_digest

    different = AdapterMetadata(
        adapter_id="adapter.redeclare", implementation_ref="tests._ok_adapter", version="2.0.0"
    )
    assert not registry.declare(different, implementation=_ok_adapter)["ok"]

    def missing_status(**params: Any) -> dict[str, Any]:
        return {"echo": params}

    meta = AdapterMetadata(adapter_id="adapter.missing-status", implementation_ref="tests.missing_status")
    assert registry.declare(meta, implementation=missing_status)["ok"]
    result = registry.execute("adapter.missing-status", params={})
    assert result["ok"] is False
    assert result["error"] == "adapter_result_missing_status"
    assert result["failure_class"] == "structural"

    malformed = registry.execute("adapter.redeclare", params={1: "bad"})  # type: ignore[dict-item]
    assert malformed["ok"] is False
    assert malformed["failure_class"] == "structural"
    assert malformed["error"].startswith("invalid_adapter_params:")


def test_compile_rejects_zero_wall_time_at_executable_boundary() -> None:
    recipe = _recipe()
    zero_budget = type(recipe.budgets)(**{**recipe.budgets.to_dict(), "wall_time_ms": 0})
    object.__setattr__(recipe, "budgets", zero_budget)
    registry, bindings = _registry(recipe)
    with pytest.raises(ValueError, match="wall_time_ms must be at least 1"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=bindings, adapter_registry=registry,
        )


def test_store_rejects_nonfinite_v2_timestamps(tmp_path: Path) -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    store = EphemeralRegistryStore.for_tests(tmp_path)
    base = {
        "workspace_id": "workspace:v2:timestamp-test",
        "recipe_json": recipe.to_dict(),
        "recipe_digest": recipe.recipe_digest,
        "graph_json": graph,
        "graph_digest": graph["graph_digest"],
        "state": "ADMITTED",
        "created_at": time.time(),
        "expires_at": time.time() + 60,
        "activation_nonce": "timestamp-test-nonce",
    }
    for index, invalid in enumerate(("bad", float("nan"), float("inf"))):
        record = dict(base)
        record["workspace_id"] = f"workspace:v2:timestamp-test-{index}"
        record["activation_nonce"] = f"timestamp-test-nonce-{index}"
        record["created_at"] = invalid
        with pytest.raises(ValueError, match="created_at must be a finite number"):
            store.register_workspace_v2(record)


def test_arbitrary_key_absolute_and_traversal_paths_fail_closed(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]

    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path / "hidden-absolute", overrides={first: _hidden_absolute_adapter}
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    result = runtime.execute_workspace_node_v2(
        workspace_id, first, params={}, store=store, adapter_registry=registry,
    )
    assert not result["ok"] and "escapes" in result["error"]

    _, registry2, _, _, store2, workspace_id2 = _admitted(
        tmp_path / "hidden-traversal", overrides={first: _hidden_traversal_adapter}
    )
    runtime.activate_workspace_v2(
        workspace_id2, store=store2, adapter_registry=registry2, repo_root=str(ROOT),
    )
    result2 = runtime.execute_workspace_node_v2(
        workspace_id2, first, params={}, store=store2, adapter_registry=registry2,
    )
    assert not result2["ok"] and "escapes" in result2["error"]



def test_action_certificate_runtime_owner_cannot_self_approve(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-self-approve",
        expires_at=time.time() + 120,
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime",
    )
    with pytest.raises(ValueError, match="self-authorize"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="OPEN",
            evidence_digest=D["5"], owner="spatial_runtime",
        )


def test_action_certificate_requires_active_state_and_uses_cas(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-cas-test",
        expires_at=time.time() + 120,
    )["certificate"]
    stale = dict(prepared)
    stale["status"] = "OPEN"
    cas = store.commit_workspace_v2_certificate(
        workspace_id,
        expected_certificate=stale,
        certificate=prepared,
    )
    assert cas["ok"] is False and cas["error"] == "stale_workspace_certificate"

    moved = store.transition_workspace_v2(workspace_id, "ACTIVE", "CANCELLING")
    assert moved["ok"]
    with pytest.raises(ValueError, match="active workspace"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
        )
    cleanup = runtime.dissolve_workspace_v2(workspace_id, store=store, reason="test_cleanup")
    assert cleanup["ok"] and cleanup["state"] == "DISSOLVED"


def test_cleanup_converges_when_cancellation_wins_first_transition(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    original = store.transition_workspace_v2
    injected = {"done": False}

    def racing_transition(workspace: str, expected: Any, target: str, *, terminal_reason: str = ""):
        if not injected["done"] and expected == "ACTIVE" and target == "DISSOLVING":
            injected["done"] = True
            assert original(
                workspace, "ACTIVE", "CANCELLING", terminal_reason="concurrent_cancel",
            )["ok"]
            return {"ok": False, "error": "stale_workspace_state"}
        return original(workspace, expected, target, terminal_reason=terminal_reason)

    monkeypatch.setattr(store, "transition_workspace_v2", racing_transition)
    result = runtime.dissolve_workspace_v2(workspace_id, store=store, reason="explicit_cleanup")
    assert injected["done"] is True
    assert result["ok"] and result["state"] == "DISSOLVED"
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_backdated_now_cannot_bypass_workspace_expiry(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert store._conn is not None
    store._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id),
    )
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.execute_workspace_node_v2(
            workspace_id, graph["entry_node_ids"][0], params={}, store=store,
            adapter_registry=registry, now=time.time() - 3600,
        )
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


def test_certificate_mutation_rejects_backdated_authority_after_expiry(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "prepare")
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    assert store._conn is not None
    store._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id),
    )
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.prepare_spatial_action_certificate_v2(
            workspace_id, store=store,
            principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
            subject_refs=["source:aura"], target_refs=["forge:candidate"],
            policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
            runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
            assumptions_digest=D["3"], cost_microusd=0, reversible=True,
            proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-prepare",
            expires_at=time.time() + 120, now=time.time() - 3600,
        )
    prepared_record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert prepared_record["state"] == "DISSOLVED"
    assert prepared_record["lease_status"] == "REVOKED"

    _, registry2, _, _, store2, workspace_id2 = _admitted(tmp_path / "advance")
    runtime.activate_workspace_v2(
        workspace_id2, store=store2, adapter_registry=registry2, repo_root=str(ROOT),
    )
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id2, store=store2,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-backdated-advance",
        expires_at=time.time() + 120,
    )["certificate"]
    assert store2._conn is not None
    store2._conn.execute(
        "UPDATE ephemeral_workspaces_v2 SET expires_at = ? WHERE workspace_id = ?",
        (time.time() - 1, workspace_id2),
    )
    with pytest.raises(ValueError, match="expired and dissolved"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id2, store=store2, expected_status="PREPARED",
            evidence_digest=D["4"], owner="spatial_runtime",
            timestamp=prepared["issued_at"],
        )
    advanced_record = runtime.workspace_status_v2(workspace_id2, store=store2)["workspace"]
    assert advanced_record["state"] == "DISSOLVED"
    assert advanced_record["lease_status"] == "REVOKED"



def _resign_graph_after_node_mutation(graph: dict[str, Any], node_index: int = 0) -> None:
    node = graph["nodes"][node_index]
    node["node_digest"] = stable_digest(runtime._node_identity_body(node))
    graph["graph_digest"] = stable_digest(runtime._graph_identity_body(graph))
    graph["graph_id"] = f"workspace-graph:{graph['graph_digest'][:24]}"


def test_master_negative_unknown_adapter_and_identity_digest_mismatch() -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    first = recipe.capability_ids[0]
    unknown = dict(bindings)
    unknown[first] = "adapter.missing"
    with pytest.raises(ValueError, match="unknown_adapter"):
        runtime.compile_workspace_execution_graph_v2(
            recipe, adapter_bindings=unknown, adapter_registry=registry,
        )

    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )
    for field in (
        "adapter_digest", "implementation_digest", "input_schema_digest",
        "output_schema_digest", "source_identity_digest",
    ):
        altered = copy.deepcopy(graph)
        altered["nodes"][0][field] = D["9"]
        _resign_graph_after_node_mutation(altered)
        with pytest.raises(ValueError, match="stale complete execution graph identity"):
            runtime.bind_workspace_execution_graph_v2(
                altered,
                expected_recipe=recipe,
                expected_adapter_bindings=bindings,
                adapter_registry=registry,
            )


def test_master_negative_retry_and_parallelism_overflow() -> None:
    recipe = _recipe()
    registry, bindings = _registry(recipe)
    graph = runtime.compile_workspace_execution_graph_v2(
        recipe, adapter_bindings=bindings, adapter_registry=registry,
    )

    retry = copy.deepcopy(graph)
    retry["nodes"][0]["retry_limit"] = 9
    _resign_graph_after_node_mutation(retry)
    with pytest.raises(ValueError, match="retry_limit"):
        runtime.validate_workspace_execution_graph_v2(retry)

    parallel = copy.deepcopy(graph)
    parallel["max_parallelism"] = 17
    parallel["graph_digest"] = stable_digest(runtime._graph_identity_body(parallel))
    parallel["graph_id"] = f"workspace-graph:{parallel['graph_digest'][:24]}"
    with pytest.raises(ValueError, match="max_parallelism"):
        runtime.validate_workspace_execution_graph_v2(parallel)


def test_master_negative_symlink_escape_fails_and_cleans(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: _symlink_output_adapter},
    )
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    sandbox = Path(record["sandbox_path"])
    outside = tmp_path / "outside-artifact.txt"
    outside.write_text("outside", encoding="utf-8")
    link = sandbox / "escape-link"
    link.symlink_to(outside)

    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0],
        params={"artifact_path": str(link)},
        store=store, adapter_registry=registry,
    )
    assert not result["ok"] and "symlink" in result["error"]
    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]
    assert final["state"] == "DISSOLVED"
    assert final["lease_status"] == "REVOKED"
    assert not sandbox.exists()
    assert outside.exists()


def test_master_negative_revoked_lease_denies_execution(tmp_path: Path) -> None:
    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    assert store.revoke_workspace_v2_lease(
        workspace_id, reason="master-exit-gate-test",
    )["ok"]
    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={},
        store=store, adapter_registry=registry,
    )
    assert result == {"ok": False, "error": "workspace_lease_revoked"}
    cleanup = runtime.dissolve_workspace_v2(
        workspace_id, store=store, reason="master-exit-gate-test",
    )
    assert cleanup["ok"] and cleanup["state"] == "DISSOLVED"


def test_certificate_advancement_clamps_backdated_receipt_timestamp_to_trusted_now(
    tmp_path: Path,
) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    prepared = runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-trusted-receipt-time",
        expires_at=time.time() + 120,
    )["certificate"]
    real_before = time.time()
    advanced = runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime",
        timestamp=prepared["issued_at"] - 3600,
    )["certificate"]
    receipt_time = advanced["receipts"][-1]["timestamp"]
    assert receipt_time >= real_before
    assert receipt_time > prepared["issued_at"] - 3600


def test_master_negative_runtime_cannot_close_certificate_with_self_proof(tmp_path: Path) -> None:
    _, registry, _, _, store, workspace_id = _admitted(tmp_path)
    assert runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )["ok"]
    runtime.prepare_spatial_action_certificate_v2(
        workspace_id, store=store,
        principal_id="human:dallas", requested_operation="PREPARE_FORGE_HANDOFF",
        subject_refs=["source:aura"], target_refs=["forge:candidate"],
        policy_digest=D["1"], approval_class="HUMAN_EXPLICIT",
        runtime_environment_digest=D["2"], effect_boundary="PROPOSAL_ONLY",
        assumptions_digest=D["3"], cost_microusd=0, reversible=True,
        proof_obligations=["EXACT_SOURCE"], nonce="cert-master-close-proof",
        expires_at=time.time() + 120,
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="PREPARED",
        evidence_digest=D["4"], owner="spatial_runtime",
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="OPEN",
        evidence_digest=D["5"], owner="human:dallas",
    )
    runtime.advance_spatial_action_certificate_v2(
        workspace_id, store=store, expected_status="APPROVED",
        evidence_digest=D["6"], owner="canonical_runtime",
    )
    with pytest.raises(ValueError, match="cannot self-prove outcome"):
        runtime.advance_spatial_action_certificate_v2(
            workspace_id, store=store, expected_status="EXECUTED",
            evidence_digest=D["7"], owner="spatial_runtime",
        )
