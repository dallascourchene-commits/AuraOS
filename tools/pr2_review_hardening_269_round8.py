from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one match, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


# Enforce the admitted memory budget in the existing bounded child process.
replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''def _bounded_callback_worker(
    implementation: Callable[..., dict[str, Any]],
    expected_implementation_digest: str,
    params: dict[str, Any],
    connection: Any,
    max_output_bytes: int,
) -> None:
    """Execute one exact registered callback in a new POSIX process group."""
    try:
        os.setsid()
        try:
            current_digest = _callable_digest(implementation)
''',
    '''def _bounded_callback_worker(
    implementation: Callable[..., dict[str, Any]],
    expected_implementation_digest: str,
    params: dict[str, Any],
    connection: Any,
    max_output_bytes: int,
    max_memory_mb: int,
) -> None:
    """Execute one exact registered callback in a new POSIX process group."""
    try:
        os.setsid()
        try:
            import resource
            if not hasattr(resource, "RLIMIT_AS"):
                raise RuntimeError("RLIMIT_AS is unavailable")
            limit_bytes = max_memory_mb * 1024 * 1024
            _soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
            if hard_limit != resource.RLIM_INFINITY:
                limit_bytes = min(limit_bytes, hard_limit)
            if limit_bytes < 1:
                raise RuntimeError("effective address-space limit is invalid")
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        except Exception as exc:
            connection.send_bytes(_canonical_json({
                "kind": "worker_error",
                "error": f"bounded_adapter_memory_limit_failed: {type(exc).__name__}: {str(exc)[:1024]}",
                "failure_class": "environment",
            }).encode("utf-8"))
            return
        try:
            current_digest = _callable_digest(implementation)
''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''    deadline_monotonic: float,
    authority_check: Callable[[], bool],
    max_output_bytes: int,
) -> tuple[dict[str, Any], bool]:
''',
    '''    deadline_monotonic: float,
    authority_check: Callable[[], bool],
    max_output_bytes: int,
    max_memory_mb: int,
) -> tuple[dict[str, Any], bool]:
''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''    if type(max_output_bytes) is not int or type(max_output_bytes) is bool or max_output_bytes < 1:
        raise ValueError("max_output_bytes must be a positive integer")
    if not callable(authority_check):
''',
    '''    if type(max_output_bytes) is not int or type(max_output_bytes) is bool or max_output_bytes < 1:
        raise ValueError("max_output_bytes must be a positive integer")
    if type(max_memory_mb) is not int or type(max_memory_mb) is bool or max_memory_mb < 1:
        raise ValueError("max_memory_mb must be a positive integer")
    if not callable(authority_check):
''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''            params,
            child,
            max_output_bytes,
        ),
''',
    '''            params,
            child,
            max_output_bytes,
            max_memory_mb,
        ),
''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''        authority_check: Callable[[], bool] | None = None,
        max_output_bytes: int = 4_000_000,
    ) -> dict[str, Any]:
''',
    '''        authority_check: Callable[[], bool] | None = None,
        max_output_bytes: int = 4_000_000,
        max_memory_mb: int = 512,
    ) -> dict[str, Any]:
''',
)

replace_once(
    "aura_ephemeral_adapter_registry.py",
    '''                deadline_monotonic=deadline_monotonic,
                authority_check=authority_check,
                max_output_bytes=max_output_bytes,
            )
''',
    '''                deadline_monotonic=deadline_monotonic,
                authority_check=authority_check,
                max_output_bytes=max_output_bytes,
                max_memory_mb=max_memory_mb,
            )
''',
)

# V2 executable workspaces require a non-zero memory budget and pass it to the
# bounded registry execution boundary. PR1's non-operational contract remains unchanged.
replace_once(
    "aura_ephemeral_workspace_runtime_v2.py",
    '''    if value.budgets.wall_time_ms < 1:
        raise ValueError("wall_time_ms must be at least 1 for executable workspaces")
    bindings = _exact_mapping(adapter_bindings, "adapter_bindings")
''',
    '''    if value.budgets.wall_time_ms < 1:
        raise ValueError("wall_time_ms must be at least 1 for executable workspaces")
    if value.budgets.memory_mb < 1:
        raise ValueError("memory_mb must be at least 1 for executable workspaces")
    bindings = _exact_mapping(adapter_bindings, "adapter_bindings")
''',
)

replace_once(
    "aura_ephemeral_workspace_runtime_v2.py",
    '''    for name, value in budgets.items():
        minimum = 1 if name == "wall_time_ms" else 0
        _integer(value, f"budget.{name}", minimum, 10_000_000_000)
''',
    '''    for name, value in budgets.items():
        minimum = 1 if name in {"wall_time_ms", "memory_mb"} else 0
        _integer(value, f"budget.{name}", minimum, 10_000_000_000)
''',
)

replace_once(
    "aura_ephemeral_workspace_runtime_v2.py",
    '''            authority_check=execution_authority_active,
            max_output_bytes=min(remaining_output, MAX_OUTPUT_BYTES),
        )
''',
    '''            authority_check=execution_authority_active,
            max_output_bytes=min(remaining_output, MAX_OUTPUT_BYTES),
            max_memory_mb=graph["budgets"]["memory_mb"],
        )
''',
)

# Schema must agree with the V2 executable semantic validator.
replace_once(
    "schemas/aura_workspace_execution_graph_v2.schema.json",
    '''        "memory_mb": {
          "maximum": 10000000000,
          "minimum": 0,
          "type": "integer"
        },
''',
    '''        "memory_mb": {
          "maximum": 10000000000,
          "minimum": 1,
          "type": "integer"
        },
''',
)

# Document the exact containment semantics without claiming a whole-host/cgroup sandbox.
replace_once(
    "docs/AURA_VERIFIED_EPHEMERAL_WORKSPACE_PR2.md",
    '''implementation identities; deadline expiry, revocation/cancellation, or binding
drift kills and reaps the whole child process group before output can be
accepted. The child re-verifies the admitted implementation source digest before
execution. Hosts without the required containment primitive fail V2 bounded
execution closed. This is internal containment of an admitted adapter, not a
''',
    '''implementation identities; deadline expiry, revocation/cancellation, or binding
drift kills and reaps the whole child process group before output can be
accepted. Before source re-verification or callback execution, the child applies
a POSIX `RLIMIT_AS` per-process address-space ceiling from the admitted
`memory_mb` budget; descendants inherit that ceiling. If the host cannot apply
the address-space limit, V2 execution fails closed. This is a per-process
address-space bound rather than a cgroup-wide aggregate-memory claim. The child
then re-verifies the admitted implementation source digest before execution.
Hosts without the required containment primitive fail V2 bounded execution
closed. This is internal containment of an admitted adapter, not a
''',
)

# Test helpers and regressions.
replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''def _recipe(*, ttl: int = 300, wall_time_ms: int | None = None) -> EphemeralWorkspaceRecipe:
''',
    '''def _recipe(
    *, ttl: int = 300, wall_time_ms: int | None = None, memory_mb: int | None = None,
) -> EphemeralWorkspaceRecipe:
''',
)

replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''    budgets = None
    if wall_time_ms is not None:
        budgets = WorkspaceBudget(
            wall_time_ms=wall_time_ms,
            memory_mb=256,
''',
    '''    budgets = None
    if wall_time_ms is not None or memory_mb is not None:
        budgets = WorkspaceBudget(
            wall_time_ms=30_000 if wall_time_ms is None else wall_time_ms,
            memory_mb=256 if memory_mb is None else memory_mb,
''',
)

replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    '''def _interrupt_adapter(**params: Any) -> dict[str, Any]:
    raise KeyboardInterrupt()


def _recursive_result_adapter(**params: Any) -> dict[str, Any]:
''',
    '''def _interrupt_adapter(**params: Any) -> dict[str, Any]:
    raise KeyboardInterrupt()


def _memory_hog_adapter(*, allocation_mb: int = 512, **params: Any) -> dict[str, Any]:
    payload = bytearray(allocation_mb * 1024 * 1024)
    return {"ok": True, "allocated_bytes": len(payload), "echo": params}


def _recursive_result_adapter(**params: Any) -> dict[str, Any]:
''',
)

anchor = '''def test_runtime_wall_time_deadline_dissolves_and_kills_callback(tmp_path: Path) -> None:
'''
new_tests = '''def test_zero_memory_budget_rejected_at_v2_executable_boundary(tmp_path: Path) -> None:
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


'''
replace_once(
    "tests/test_aura_ephemeral_workspace_runtime_v2.py",
    anchor,
    new_tests + anchor,
)

print("round8 patch applied")
