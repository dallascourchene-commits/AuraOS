from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''                if kind == "base_exception":
                    error_type = envelope.get("error_type", "BaseException")
                    message = envelope.get("error", "")
                    if error_type == "KeyboardInterrupt":
                        raise KeyboardInterrupt(message)
                    if error_type == "SystemExit":
                        raise SystemExit(message)
                    if error_type == "GeneratorExit":
                        raise GeneratorExit(message)
                    raise BaseException(f"adapter process interruption: {error_type}: {message}")
''',
    '''                if kind == "base_exception":
                    # Child callback exception names/text are diagnostics only. They
                    # must never select a parent-process control-flow exception.
                    error_type = str(envelope.get("error_type", "BaseException"))[:128]
                    message = str(envelope.get("error", ""))[:2048]
                    return _bounded_event(
                        "WORKER_ERROR",
                        f"bounded_adapter_worker_interruption: {error_type}: {message}",
                        "environment",
                    )
''',
)

replace_once(
    "aura_ephemeral_workspace_runtime_v2.py",
    '''        store.update_workspace_v2(
            workspace_id, sandbox_path=sandbox["temp_dir"], usage_json=activation_usage,
        )
        moved = store.transition_workspace_v2(workspace_id, "ACTIVATING", "ACTIVE")
''',
    '''        evidence_update = store.update_workspace_v2(
            workspace_id, sandbox_path=sandbox["temp_dir"], usage_json=activation_usage,
        )
        if not evidence_update.get("ok"):
            removed = destroy_sandbox(sandbox["temp_dir"])
            if not removed.get("ok"):
                raise RuntimeError(
                    "activation evidence update failed and unpersisted sandbox cleanup failed: "
                    f"{removed.get('error', 'unknown cleanup failure')}"
                )
            raise ValueError("activation evidence update failed")
        moved = store.transition_workspace_v2(workspace_id, "ACTIVATING", "ACTIVE")
''',
)

replace_once(
    "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md",
    '''Executable V2 callbacks are bounded by one runtime-owned absolute deadline: the
minimum of the node timeout, the cumulative workspace wall-time budget measured
from activation, and the absolute workspace TTL. On POSIX hosts with Python's
''',
    '''Executable V2 callbacks are bounded by one runtime-owned absolute deadline. The
runtime first derives the node deadline as `callback_start + timeout_ms`, then
takes the minimum of that absolute node deadline, the absolute cumulative
workspace wall-time deadline measured from activation, and the absolute
workspace TTL. On POSIX hosts with Python's
''',
)

replace_once(
    "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md",
    '''absolute workspace TTL expiry is `stale`. `KeyboardInterrupt`, `SystemExit`, and
other process-level exceptions are never swallowed: bounded execution reports
the interruption to the parent runtime, cleanup runs, and the process-level
exception is re-raised.
''',
    '''absolute workspace TTL expiry is `stale`. A child callback cannot choose
parent-process control flow by raising `KeyboardInterrupt`, `SystemExit`,
`GeneratorExit`, or another `BaseException`: every child-reported process-level
interruption is normalized to one parent-owned `WORKER_ERROR` environment
failure, followed by normal fail-closed cleanup. Parent-local process
interruptions still run cleanup before they propagate.
''',
)

replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''def test_process_interruption_reraises_after_cleanup(tmp_path: Path) -> None:
    recipe = _recipe()
    first = recipe.capability_ids[0]
    _, registry, _, _, store, workspace_id = _admitted(
        tmp_path, overrides={first: _interrupt_adapter},
    )
    runtime.activate_workspace_v2(
        workspace_id, store=store, adapter_registry=registry, repo_root=str(ROOT),
    )
    with pytest.raises(KeyboardInterrupt):
        runtime.execute_workspace_node_v2(
            workspace_id, first, params={}, store=store, adapter_registry=registry,
        )
    assert runtime.workspace_status_v2(workspace_id, store=store)["workspace"]["state"] == "DISSOLVED"


''',
    '''def test_child_process_interruption_is_parent_owned_worker_failure(tmp_path: Path) -> None:
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


''',
)

anchor = '''def test_runtime_wall_time_deadline_dissolves_and_kills_callback(tmp_path: Path) -> None:
'''
activation_test = '''def test_activation_evidence_write_failure_destroys_unpersisted_sandbox(
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


'''
replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    anchor,
    activation_test + anchor,
)

print("round7 patch applied")
