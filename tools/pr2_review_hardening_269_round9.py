from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# 1. Registry hardening: close identity scheme, normalize a control-pipe race.
replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''        if self.revocation_state not in _REVOCATION_STATES:\n            raise ValueError("invalid revocation_state")\n        self.input_schema = _strict_mapping(self.input_schema, "input_schema")\n''',
    '''        if self.revocation_state not in _REVOCATION_STATES:\n            raise ValueError("invalid revocation_state")\n        if self.identity_version != ADAPTER_IDENTITY_VERSION:\n            raise ValueError("invalid identity_version")\n        self.input_schema = _strict_mapping(self.input_schema, "input_schema")\n''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''                    if time.monotonic() >= deadline_monotonic:\n                        return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")\n                    parent.send_bytes(b"execute")\n                    continue\n''',
    '''                    if time.monotonic() >= deadline_monotonic:\n                        return _bounded_event("DEADLINE", "adapter_deadline_exceeded", "budget")\n                    try:\n                        parent.send_bytes(b"execute")\n                    except OSError:\n                        return _bounded_event(\n                            "WORKER_ERROR", "bounded_adapter_protocol_failure", "environment"\n                        )\n                    continue\n''',
)

# 2. Store hardening: preserve an existing terminal reason on reason-less transitions.
replace_once(
    "aura_ephemeral_registry_store.py",
    '''        params: tuple[Any, ...] = (to, time.time(), terminal_reason, workspace_id, *expected)\n        cur = conn.execute(\n            f"UPDATE ephemeral_workspaces_v2 SET state = ?, updated_at = ?, terminal_reason = ? "\n            f"WHERE workspace_id = ? AND state IN ({placeholders})",\n            params,\n        )\n''',
    '''        params: tuple[Any, ...] = (\n            to, time.time(), 1 if terminal_reason else 0, terminal_reason, workspace_id, *expected,\n        )\n        cur = conn.execute(\n            f"UPDATE ephemeral_workspaces_v2 SET state = ?, updated_at = ?, "\n            f"terminal_reason = CASE WHEN ? THEN ? ELSE terminal_reason END "\n            f"WHERE workspace_id = ? AND state IN ({placeholders})",\n            params,\n        )\n''',
)

# 3. Runtime expiry convergence: if another terminal path wins the CAS, join it.
replace_once(
    "aura_ephemeral_workspace_runtime_v2.py",
    '''    if record["state"] != "EXPIRING":\n        moved = store.transition_workspace_v2(workspace_id, record["state"], "EXPIRING",\n                                              terminal_reason="ttl_expired")\n        if not moved.get("ok"):\n            raise ValueError("workspace expiry lost its state race")\n    _cleanup_workspace_v2(workspace_id, store=store, reason="ttl_expired")\n''',
    '''    if record["state"] != "EXPIRING":\n        moved = store.transition_workspace_v2(workspace_id, record["state"], "EXPIRING",\n                                              terminal_reason="ttl_expired")\n        if not moved.get("ok"):\n            record = _workspace(store, workspace_id)\n            if record["state"] not in _TERMINAL_PREP and record["state"] not in {\n                "DISSOLVING", "DISSOLVED",\n            }:\n                raise ValueError("workspace expiry lost its state race")\n    _cleanup_workspace_v2(workspace_id, store=store, reason="ttl_expired")\n''',
)

# 4. Tests: make cancellation kill proof conclusive, remove duplicate reuse case,
# and add direct coverage requested by the final Sourcery/CodeRabbit pass.
replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''                "delay_seconds": 5.0,\n            },\n''',
    '''                "delay_seconds": 1.0,\n            },\n''',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''    time.sleep(0.1)\n    assert not completed_path.exists()\n\n\ndef test_bounded_adapter_deadline_kills_callback_process''',
    '''    time.sleep(1.2)\n    assert not completed_path.exists()\n\n\ndef test_bounded_adapter_deadline_kills_callback_process''',
)

replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''\ndef test_partial_reexecution_reuses_complete_unchanged_receipt_set(tmp_path: Path) -> None:\n    _, registry, _, graph, store, workspace_id = _admitted(tmp_path)\n    runtime.activate_workspace_v2(\n        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),\n    )\n    _execute_all(workspace_id, graph, store, registry)\n    receipts = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["node_receipts"]\n    plan = runtime.partial_reexecution_plan_v2(\n        graph, prior_receipts=receipts, changed_node_ids=[],\n    )\n    assert plan["reexecute_node_ids"] == []\n    assert set(plan["reusable_node_ids"]) == {node["node_id"] for node in graph["nodes"]}\n\n''',
    '''\n''',
)

# Insert registry exposure / identity-version tests after the existing identity test.
anchor = '''    assert first.execute("adapter.test", params={})["status"] == "DENIED"\n\n\ndef test_graph_compile_parse_bind_is_deterministic() -> None:\n'''
insert = '''    assert first.execute("adapter.test", params={})["status"] == "DENIED"\n\n\ndef test_adapter_registry_list_bindings_and_closed_identity_version() -> None:\n    registry = OperationalAdapterRegistry()\n    meta_a = AdapterMetadata(adapter_id="adapter.a", implementation_ref="tests._ok_adapter")\n    meta_b = AdapterMetadata(adapter_id="adapter.b", implementation_ref="tests._ok_adapter")\n    assert registry.declare(meta_b, implementation=_ok_adapter)["ok"]\n    assert registry.declare(meta_a, implementation=_ok_adapter)["ok"]\n\n    listed = registry.list_adapters()\n    assert listed["ok"] and listed["count"] == 2\n    assert [item["adapter_id"] for item in listed["adapters"]] == ["adapter.a", "adapter.b"]\n    before_b = {item["adapter_id"]: item for item in listed["adapters"]}["adapter.b"]\n    binding_before = registry.get_binding("adapter.b")\n    assert binding_before["ok"]\n    assert binding_before["binding"]["adapter_digest"] == before_b["adapter_digest"]\n    assert binding_before["binding"]["implementation_digest"] == before_b["implementation_digest"]\n\n    assert registry.revoke("adapter.b", reason="test revocation")["ok"]\n    after_b = {\n        item["adapter_id"]: item for item in registry.list_adapters()["adapters"]\n    }["adapter.b"]\n    assert after_b["revocation_state"] == "REVOKED"\n    assert after_b["operational_status"] == "DENIED"\n    assert after_b["revocation_reason"] == "test revocation"\n    binding_after = registry.get_binding("adapter.b")["binding"]\n    assert binding_after["revocation_state"] == "REVOKED"\n    assert binding_after["adapter_digest"] == after_b["adapter_digest"]\n    assert binding_after["implementation_digest"] == after_b["implementation_digest"]\n\n    invalid = AdapterMetadata(\n        adapter_id="adapter.invalid-version", implementation_ref="tests._ok_adapter",\n        identity_version="unrecognized",\n    )\n    with pytest.raises(ValueError, match="invalid identity_version"):\n        registry.declare(invalid, implementation=_ok_adapter)\n\n\ndef test_graph_compile_parse_bind_is_deterministic() -> None:\n'''
replace_once("tests/test_aura_ephemeral_workspace_runtime_v2.py", anchor, insert)

# Insert AUTHORITY_REVOKED direct bounded test after authority-check failure coverage.
anchor = '''    assert "authority store unavailable" in result["error"]\n\n\ndef test_recursive_output_and_path_escape_fail_closed(tmp_path: Path) -> None:\n'''
insert = '''    assert "authority store unavailable" in result["error"]\n\n\ndef test_authority_check_false_emits_parent_owned_revocation_event() -> None:\n    registry = OperationalAdapterRegistry()\n    assert registry.declare(\n        AdapterMetadata(\n            adapter_id="adapter.authority-revoked-test",\n            implementation_ref="tests._ok_adapter",\n        ),\n        implementation=_ok_adapter,\n    )["ok"]\n    result = registry.execute(\n        "adapter.authority-revoked-test",\n        params={},\n        deadline_monotonic=time.monotonic() + 1.0,\n        authority_check=lambda: False,\n        max_output_bytes=4096,\n    )\n    assert not result["ok"]\n    assert result["_aura_bounded_event"] == "AUTHORITY_REVOKED"\n    assert result["failure_class"] == "cancellation"\n\n\ndef test_recursive_output_and_path_escape_fail_closed(tmp_path: Path) -> None:\n'''
replace_once("tests/test_aura_ephemeral_workspace_runtime_v2.py", anchor, insert)

# Insert direct V2 store helper coverage after expiry lifecycle test.
anchor = '''    assert record["failure_records"][-1]["failure_class"] == "stale"\n\n\ndef test_tool_call_budget_overflow_fails_and_cleans(tmp_path: Path) -> None:\n'''
insert = '''    assert record["failure_records"][-1]["failure_class"] == "stale"\n\n\ndef test_store_v2_lease_and_expiry_helpers_track_lifecycle(tmp_path: Path) -> None:\n    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "lease")\n    assert runtime.activate_workspace_v2(\n        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),\n    )["ok"]\n    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]\n    assert store.is_workspace_v2_lease_active(workspace_id, now=record["expires_at"] - 1)\n    assert not store.is_workspace_v2_lease_active(workspace_id, now=record["expires_at"] + 1)\n    assert store.revoke_workspace_v2_lease(workspace_id, reason="direct helper test")["ok"]\n    assert not store.is_workspace_v2_lease_active(workspace_id)\n\n    _, _, _, _, store2, workspace_id2 = _admitted(tmp_path / "expired-list")\n    record2 = runtime.workspace_status_v2(workspace_id2, store=store2)["workspace"]\n    listed = store2.list_expired_workspaces_v2(now=record2["expires_at"] + 1)\n    assert workspace_id2 in listed["workspace_ids"]\n    assert store2.transition_workspace_v2(workspace_id2, "ADMITTED", "DISSOLVING")["ok"]\n    assert workspace_id2 not in store2.list_expired_workspaces_v2(\n        now=record2["expires_at"] + 1\n    )["workspace_ids"]\n    assert store2.transition_workspace_v2(workspace_id2, "DISSOLVING", "DISSOLVED")["ok"]\n    assert workspace_id2 not in store2.list_expired_workspaces_v2(\n        now=record2["expires_at"] + 1\n    )["workspace_ids"]\n\n\ndef test_terminal_reason_survives_reasonless_state_transition(tmp_path: Path) -> None:\n    _, _, _, _, store, workspace_id = _admitted(tmp_path / "terminal-reason")\n    assert store.update_workspace_v2(workspace_id, terminal_reason="preserve-me")["ok"]\n    assert store.transition_workspace_v2(workspace_id, "ADMITTED", "ACTIVATING")["ok"]\n    record = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]\n    assert record["terminal_reason"] == "preserve-me"\n\n\ndef test_expiry_state_race_converges_to_dissolution(\n    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,\n) -> None:\n    _, registry, _, _, store, workspace_id = _admitted(tmp_path / "expiry-race")\n    assert runtime.activate_workspace_v2(\n        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),\n    )["ok"]\n    expires_at = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["expires_at"]\n    original_transition = store.transition_workspace_v2\n\n    def race_transition(\n        target_workspace_id: str, expected_from: str | tuple[str, ...], to: str,\n        *, terminal_reason: str = "",\n    ) -> dict[str, Any]:\n        if to == "EXPIRING":\n            original_transition(\n                target_workspace_id, expected_from, "CANCELLING",\n                terminal_reason="concurrent_cancel",\n            )\n            return {"ok": False, "error": "stale_workspace_state"}\n        return original_transition(\n            target_workspace_id, expected_from, to, terminal_reason=terminal_reason,\n        )\n\n    monkeypatch.setattr(store, "transition_workspace_v2", race_transition)\n    with pytest.raises(ValueError, match="expired and dissolved"):\n        runtime._expire_if_needed(workspace_id, store=store, now=expires_at + 1)\n    final = runtime.workspace_status_v2(workspace_id, store=store)["workspace"]\n    assert final["state"] == "DISSOLVED"\n    assert final["lease_status"] == "REVOKED"\n\n\ndef test_tool_call_budget_overflow_fails_and_cleans(tmp_path: Path) -> None:\n'''
replace_once("tests/test_aura_ephemeral_workspace_runtime_v2.py", anchor, insert)

print("round9 patch applied")
