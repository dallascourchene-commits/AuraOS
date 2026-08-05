from __future__ import annotations

import json
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


source_path = Path("aura_ephemeral_workspace_contracts.py")
source = source_path.read_text()

source = replace_once(
    source,
    'MAX_CANONICAL_ITEMS = MAX_ITEMS\n',
    'MAX_CANONICAL_ITEMS = MAX_ITEMS\n'
    'MAX_CANONICAL_SCALAR_BYTES = MAX_METADATA_BYTES\n'
    'MAX_CANONICAL_NUMBER_ABS = MAX_TIMESTAMP\n'
    'MAX_HANDOFF_OWNERS = 6\n',
    "canonical and owner ceilings",
)

source = replace_once(
    source,
    '''_LEGACY_RESOURCE_FIELDS = frozenset({
    "wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls",
    "cost_usd", "network_calls",
})
''',
    '''_LEGACY_RESOURCE_FIELDS = frozenset({
    "wall_time_ms", "memory_mb", "output_bytes", "tool_calls", "model_calls",
    "cost_usd", "network_calls",
})
_PR1_RESOURCE_CEILINGS = MappingProxyType({
    "wall_time_ms": 300_000,
    "memory_mb": 512,
    "output_bytes": 4_000_000,
    "tool_calls": 64,
    "model_calls": 0,
    "cost_microusd": 0,
    "network_calls": 0,
})
''',
    "safe PR1 resource profile",
)

source = replace_once(
    source,
    '''    if isinstance(value, (set, frozenset)):
        raise ValueError("sets are not JSON values")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite floats are prohibited")
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("canonical JSON strings must contain valid Unicode scalar values") from exc
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
''',
    '''    if isinstance(value, (set, frozenset)):
        raise ValueError("sets are not JSON values")
    if isinstance(value, str):
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("canonical JSON strings must contain valid Unicode scalar values") from exc
        if len(encoded) > MAX_CANONICAL_SCALAR_BYTES:
            raise ValueError("canonical JSON string exceeds its scalar byte ceiling")
        return value
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON integer exceeds its numeric ceiling")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
''',
    "bounded canonical scalars",
)

source = replace_once(
    source,
    '''def _metadata(value: Any, name: str) -> tuple[tuple[str, Any], ...]:
''',
    '''def _source_path(value: Any, name: str) -> str:
    """Require a safe repository-relative source path outside the V1 denylist."""
    path = _text(value, name, maximum=4096)
    if "\\\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:/", path):
        raise ValueError(f"{name} must be a repository-relative POSIX path")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"{name} contains an unsafe path segment")
    lowered = tuple(part.lower() for part in parts)
    if any(part.startswith(".env") for part in lowered):
        raise ValueError(f"{name} targets a forbidden environment path")
    if any(part.startswith("secrets") or part == ".key" for part in lowered):
        raise ValueError(f"{name} targets a forbidden secret path")
    if any(
        lowered[index] == ".git" and lowered[index + 1] == "credentials"
        for index in range(len(lowered) - 1)
    ):
        raise ValueError(f"{name} targets forbidden Git credentials")
    return path


def _metadata(value: Any, name: str) -> tuple[tuple[str, Any], ...]:
''',
    "safe source path helper",
)

source = replace_once(
    source,
    '''        if key == "manifest_version":
            validated[key] = _id(item, field_name)
        elif key in _METADATA_TEXT_FIELDS:
            validated[key] = _text(item, field_name, maximum=4096)
''',
    '''        if key == "manifest_version":
            validated[key] = _id(item, field_name)
        elif key == "source_path":
            validated[key] = _source_path(item, field_name)
        elif key in _METADATA_TEXT_FIELDS:
            validated[key] = _text(item, field_name, maximum=4096)
''',
    "source path metadata validation",
)

source = replace_once(
    source,
    '''    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    keys = tuple(payload)
''',
    '''    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    if len(payload) > len(expected):
        raise ValueError(
            f"{name} keys mismatch: expected at most {len(expected)} keys"
        )
    keys = tuple(payload)
''',
    "strict mapping breadth guard",
)

source = replace_once(
    source,
    '''def _owner_map(value: Any) -> tuple[tuple[str, str], ...]:
    """Validate and canonicalize the domain-owner handoff map."""
    if isinstance(value, Mapping):
        items = value.items()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = value
''',
    '''def _owner_map(value: Any) -> tuple[tuple[str, str], ...]:
    """Validate and canonicalize the domain-owner handoff map."""
    if isinstance(value, Mapping):
        if len(value) > MAX_HANDOFF_OWNERS:
            raise ValueError("handoff map exceeds its item ceiling")
        items = value.items()
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if len(value) > MAX_HANDOFF_OWNERS:
            raise ValueError("handoff map exceeds its item ceiling")
        items = value
''',
    "handoff map breadth guard",
)

source = replace_once(
    source,
    '''    limits["cost_microusd"] = int(math.floor(cost_usd * 1_000_000))
    return limits
''',
    '''    limits["cost_microusd"] = int(math.floor(cost_usd * 1_000_000))
    if limits["network_calls"] != 0:
        raise ValueError("base manifest network access must remain disabled")
    if limits["model_calls"] != 0:
        raise ValueError("base manifest model invocation must remain disabled")
    return {
        name: min(limits[name], ceiling)
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items()
    }
''',
    "safe manifest resource ceilings",
)

source = replace_once(
    source,
    '''def _manifest_snapshot(manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify and snapshot an exact safe V1 manifest into a wrapper identity."""
    raw = manifest.to_dict() if hasattr(manifest, "to_dict") else manifest
    body = _canonical(raw)
''',
    '''def _bounded_manifest_export(manifest: Any) -> Any:
    """Export a live V1 manifest while normalizing recursive failures."""
    if not hasattr(manifest, "to_dict"):
        return manifest
    try:
        return manifest.to_dict()
    except RecursionError as exc:
        raise ValueError("base manifest nesting exceeds its depth ceiling") from exc


def _manifest_snapshot(manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify and snapshot an exact safe V1 manifest into a wrapper identity."""
    body = _canonical(_bounded_manifest_export(manifest))
''',
    "bounded live manifest export",
)

source = replace_once(
    source,
    '''    raw_before = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(base_manifest)
    raw_after = base_manifest.to_dict() if hasattr(base_manifest, "to_dict") else base_manifest
    if before != canonical_json(raw_after):
''',
    '''    raw_before = _bounded_manifest_export(base_manifest)
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(base_manifest)
    raw_after = _bounded_manifest_export(base_manifest)
    if before != canonical_json(raw_after):
''',
    "bounded compiler snapshots",
)

source_path.write_text(source)

safe_source_path_pattern = (
    r"^(?!/)(?![A-Za-z]:/)(?!.*\\)(?!.*(?:^|/)\.{1,2}(?:/|$))"
    r"(?!.*(?:^|/)\.env[^/]*(?:/|$))(?!.*(?:^|/)secrets[^/]*(?:/|$))"
    r"(?!.*(?:^|/)\.key(?:/|$))(?!.*(?:^|/)\.git/credentials(?:/|$))"
    r"[^\u0000-\u001f]+$"
)

schema_paths = (
    Path("schemas/aura_project_context_projection.schema.json"),
    Path("schemas/aura_ephemeral_workspace_recipe.schema.json"),
    Path("schemas/aura_multimodal_spatial_observation.schema.json"),
)


def update_source_paths(node: object) -> int:
    count = 0
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "source_path" and isinstance(value, dict) and value.get("type") == "string":
                value["pattern"] = safe_source_path_pattern
                count += 1
            count += update_source_paths(value)
    elif isinstance(node, list):
        for value in node:
            count += update_source_paths(value)
    return count


for schema_path in schema_paths:
    schema = json.loads(schema_path.read_text())
    updated = update_source_paths(schema)
    if updated < 1:
        raise RuntimeError(f"{schema_path}: no source_path schema found")
    if schema_path.name == "aura_ephemeral_workspace_recipe.schema.json":
        budget = schema["$defs"]["budget"]["properties"]
        budget["model_calls"] = {"const": 0}
        budget["network_calls"] = {"const": 0}
    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text()
if "def test_review_wave10_bounded_policy_parity_fail_closed" in tests:
    raise RuntimeError("wave10 test already exists")
tests += r'''


def test_review_wave10_bounded_policy_parity_fail_closed() -> None:
    """Live snapshots, scalar/path inputs, resource limits, and schemas stay bounded."""
    live = create_manifest(
        "Reject recursive live manifest snapshots",
        organ_id="EORG-wave10-recursion",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    trusted_live_timestamps = _trusted_manifest_timestamps(live)
    nested: dict[str, Any] = {}
    cursor = nested
    for _ in range(2_000):
        child: dict[str, Any] = {}
        cursor["child"] = child
        cursor = child
    live.ui_manifest = {"schema": nested}
    with pytest.raises(ValueError, match="nesting exceeds"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=live,
            expected_manifest_timestamps=trusted_live_timestamps,
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )

    inflated = create_manifest(
        "Cap inherited resource ceilings",
        organ_id="EORG-wave10-resources",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    inflated.resource_budget["memory_mb"] = workspace_contracts.MAX_INTEGER
    inflated.phase_hash = inflated.compute_digest()
    oversized_budget = WorkspaceBudget(
        wall_time_ms=1_000,
        memory_mb=513,
        context_tokens=0,
        output_bytes=1,
        tool_calls=0,
        model_calls=0,
        cost_microusd=0,
        network_calls=0,
        device_events=0,
    )
    with pytest.raises(ValueError, match="memory_mb exceeds base manifest resource ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=inflated,
            expected_manifest_timestamps=_trusted_manifest_timestamps(inflated),
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            budgets=oversized_budget,
        )

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    recipe_payload, _ = recipe()
    unsafe_calls = recipe_payload.to_dict()
    unsafe_calls["budgets"]["model_calls"] = 1
    unsafe_calls["budgets"]["network_calls"] = 1
    error_paths = {
        tuple(error.absolute_path)
        for error in Draft202012Validator(recipe_schema).iter_errors(unsafe_calls)
    }
    assert ("budgets", "model_calls") in error_paths
    assert ("budgets", "network_calls") in error_paths

    with pytest.raises(ValueError, match="scalar byte ceiling"):
        canonical_json("x" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1))
    with pytest.raises(ValueError, match="numeric ceiling"):
        canonical_json(workspace_contracts.MAX_CANONICAL_NUMBER_ABS + 1)

    class OversizedMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            raise AssertionError("_strict must reject by length before iterating")

        def __len__(self) -> int:
            return 1_000_000

    with pytest.raises(ValueError, match="keys mismatch"):
        workspace_contracts._strict(OversizedMapping(), {"version"}, "oversized")

    with pytest.raises(ValueError, match="handoff map exceeds its item ceiling"):
        workspace_contracts._owner_map(
            {f"domain{index}": f"owner{index}" for index in range(7)}
        )

    safe = ref(
        "artifact:safe-source-path",
        D["1"],
        metadata={"source_path": "src/module.py"},
    )
    assert dict(safe.metadata)["source_path"] == "src/module.py"
    for unsafe_path in (
        ".env",
        ".env.local",
        ".git/credentials",
        "../secret",
        "/absolute/path",
        "C:/secret",
        "src/secrets-token",
        "src/.key",
        "src\\secret.py",
    ):
        with pytest.raises(ValueError):
            ref(
                f"artifact:unsafe-source-{stable_digest(unsafe_path)[:12]}",
                D["1"],
                metadata={"source_path": unsafe_path},
            )
'''
test_path.write_text(tests)


doc_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
doc = doc_path.read_text()
doc = replace_once(doc, "The focused suite now contains 25 tests covering:",
                   "The focused suite now contains 26 tests covering:", "doc test count")
doc = replace_once(doc, "- focused tests: **25 passed**;",
                   "- focused tests: **26 passed**;", "doc passed count")
doc_path.write_text(doc)

print("applied PR255 wave10 bounded-policy repairs")
