from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text.rstrip() + "\n", encoding="utf-8")


path = "tests/test_aura_ephemeral_workspace_runtime_v2.py"
text = read(path)
marker = "def test_master_negative_unknown_adapter_and_identity_digest_mismatch() -> None:"
if marker in text:
    raise SystemExit("master exit-gate tests already present")

text += r'''


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
    output_path: dict[str, str] = {"value": ""}

    def symlink_adapter(**params: Any) -> dict[str, Any]:
        return {"ok": True, "artifact_path": output_path["value"], "echo": params}

    _, registry, _, graph, store, workspace_id = _admitted(
        tmp_path, overrides={first: symlink_adapter},
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
    output_path["value"] = str(link)

    result = runtime.execute_workspace_node_v2(
        workspace_id, graph["entry_node_ids"][0], params={},
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
'''
write(path, text)
