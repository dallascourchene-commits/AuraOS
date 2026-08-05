from __future__ import annotations

import copy
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
    '''_PR1_RESOURCE_CEILINGS = MappingProxyType({
    "wall_time_ms": 300_000,
    "memory_mb": 512,
    "output_bytes": 4_000_000,
    "tool_calls": 64,
    "model_calls": 0,
    "cost_microusd": 0,
    "network_calls": 0,
})
''',
    '''_PR1_RESOURCE_CEILINGS = MappingProxyType({
    "wall_time_ms": 300_000,
    "memory_mb": 512,
    "context_tokens": 64_000,
    "output_bytes": 4_000_000,
    "tool_calls": 64,
    "model_calls": 0,
    "cost_microusd": 0,
    "network_calls": 0,
    "device_events": 100_000,
})
''',
    "complete PR1 resource ceilings",
)

source = replace_once(
    source,
    '''    if isinstance(value, Mapping):
        if len(value) > MAX_CANONICAL_ITEMS:
            raise ValueError("canonical JSON object exceeds its item ceiling")
        if any(not isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return {
            key: _canonical(value[key], _depth=next_depth)
            for key in sorted(value)
        }
''',
    '''    if isinstance(value, Mapping):
        if len(value) > MAX_CANONICAL_ITEMS:
            raise ValueError("canonical JSON object exceeds its item ceiling")
        keys = tuple(value)
        if any(not isinstance(key, str) for key in keys):
            raise ValueError("JSON object keys must be strings")
        for key in keys:
            try:
                encoded_key = key.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise ValueError(
                    "canonical JSON object keys must contain valid Unicode scalar values"
                ) from exc
            if len(encoded_key) > MAX_CANONICAL_SCALAR_BYTES:
                raise ValueError(
                    "canonical JSON object key exceeds its scalar byte ceiling"
                )
        return {
            key: _canonical(value[key], _depth=next_depth)
            for key in sorted(keys)
        }
''',
    "bounded canonical object keys",
)

source = replace_once(
    source,
    '''    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        return value
''',
    '''    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
''',
    "bounded canonical floats",
)

source = replace_once(
    source,
    '''    if isinstance(value, tuple):
        pairs: list[tuple[str, Any]] = []
        for item in value:
''',
    '''    if isinstance(value, tuple):
        if len(value) > len(_METADATA_FIELDS):
            raise ValueError(f"{name} exceeds its field ceiling")
        pairs: list[tuple[str, Any]] = []
        for item in value:
''',
    "bounded tuple metadata",
)

source = replace_once(
    source,
    '''    elif isinstance(value, Mapping):
        candidate = dict(value)
    else:
        raise ValueError(f"{name} must be an object")
''',
    '''    elif isinstance(value, Mapping):
        if len(value) > len(_METADATA_FIELDS):
            raise ValueError(f"{name} exceeds its field ceiling")
        candidate = dict(value)
    else:
        raise ValueError(f"{name} must be an object")
''',
    "bounded mapping metadata",
)

source = replace_once(
    source,
    '''        elif key in _METADATA_BOOL_FIELDS:
            validated[key] = _bool(item, field_name, True)
        elif key in _METADATA_INT_FIELDS:
            validated[key] = _int(item, field_name, 0, MAX_INTEGER)
        elif key == "legacy_manifest_digest":
''',
    '''        elif key in _METADATA_BOOL_FIELDS:
            validated[key] = _bool(item, field_name, True)
        elif key in {"line_start", "line_end"}:
            validated[key] = _int(item, field_name, 1, MAX_INTEGER)
        elif key in _METADATA_INT_FIELDS:
            validated[key] = _int(item, field_name, 0, MAX_INTEGER)
        elif key == "legacy_manifest_digest":
''',
    "positive source line validation",
)

source = replace_once(
    source,
    '''        else:
            validated[key] = _digest(item, field_name)
    if len(canonical_json(validated).encode("utf-8")) > MAX_METADATA_BYTES:
''',
    '''        else:
            validated[key] = _digest(item, field_name)
    supplied_line_fields = {"line_start", "line_end"} & set(validated)
    if supplied_line_fields:
        if supplied_line_fields != {"line_start", "line_end"} or "source_path" not in validated:
            raise ValueError(
                f"{name} source line range requires source_path, line_start, and line_end"
            )
        if validated["line_start"] > validated["line_end"]:
            raise ValueError(f"{name} source line range is reversed")
    if len(canonical_json(validated).encode("utf-8")) > MAX_METADATA_BYTES:
''',
    "ordered complete source span validation",
)

source = replace_once(
    source,
    '''        if not isinstance(self.budgets, WorkspaceBudget):
            object.__setattr__(self, "budgets", WorkspaceBudget.from_dict(self.budgets))
        if self.budgets.network_calls != 0:
''',
    '''        if not isinstance(self.budgets, WorkspaceBudget):
            object.__setattr__(self, "budgets", WorkspaceBudget.from_dict(self.budgets))
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items():
            if getattr(self.budgets, name) > ceiling:
                raise ValueError(f"budget.{name} exceeds the PR1 safe ceiling")
        if self.budgets.network_calls != 0:
''',
    "parsed recipe safe budget profile",
)

source = replace_once(
    source,
    '''    return {
        name: min(limits[name], ceiling)
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items()
    }
''',
    '''    return {
        name: min(limits.get(name, ceiling), ceiling)
        for name, ceiling in _PR1_RESOURCE_CEILINGS.items()
    }
''',
    "complete manifest-derived resource profile",
)

source = replace_once(
    source,
    '''def _manifest_snapshot(manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify and snapshot an exact safe V1 manifest into a wrapper identity."""
    body = _canonical(_bounded_manifest_export(manifest))
''',
    '''def _manifest_snapshot(raw_manifest: Any) -> tuple[dict[str, Any], str, str]:
    """Verify one already-exported safe V1 manifest snapshot into a wrapper identity."""
    body = _canonical(raw_manifest)
''',
    "single manifest snapshot helper",
)

source = replace_once(
    source,
    '''    raw_before = _bounded_manifest_export(base_manifest)
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(base_manifest)
    raw_after = _bounded_manifest_export(base_manifest)
''',
    '''    raw_before = _bounded_manifest_export(base_manifest)
    before = canonical_json(raw_before)
    body, legacy_digest, wrapper_digest = _manifest_snapshot(raw_before)
    raw_after = _bounded_manifest_export(base_manifest)
''',
    "single trusted pre-snapshot wrapping",
)

source_path.write_text(source)

safe_source_path_pattern = (
    r"^(?!/)(?![A-Za-z]:/)(?!.*\\)(?!.*(?:^|/)\.{1,2}(?:/|$))"
    r"(?!.*(?:^|/)\.[eE][nN][vV][^/]*(?:/|$))"
    r"(?!.*(?:^|/)[sS][eE][cC][rR][eE][tT][sS][^/]*(?:/|$))"
    r"(?!.*(?:^|/)\.[kK][eE][yY](?:/|$))"
    r"(?!.*(?:^|/)\.[gG][iI][tT]/[cC][rR][eE][dD][eE][nN][tT][iI][aA][lL][sS](?:/|$))"
    r"[^\u0000-\u001f]+$"
)

schema_paths = (
    Path("schemas/aura_project_context_projection.schema.json"),
    Path("schemas/aura_ephemeral_workspace_recipe.schema.json"),
    Path("schemas/aura_multimodal_spatial_observation.schema.json"),
)

for schema_path in schema_paths:
    schema = json.loads(schema_path.read_text())
    metadata = schema["$defs"]["metadata"]
    properties = metadata["properties"]
    properties["source_path"]["pattern"] = safe_source_path_pattern
    properties["line_start"]["minimum"] = 1
    properties["line_end"]["minimum"] = 1
    metadata["dependentRequired"] = {
        "line_start": ["line_end", "source_path"],
        "line_end": ["line_start", "source_path"],
    }
    invariants = schema.setdefault("x-aura-semantic-invariants", [])
    line_invariant = "source line ranges are positive, complete, and ordered"
    if line_invariant not in invariants:
        invariants.append(line_invariant)

    if schema_path.name == "aura_ephemeral_workspace_recipe.schema.json":
        budget_properties = schema["$defs"]["budget"]["properties"]
        safe_budget_ceilings = {
            "wall_time_ms": 300_000,
            "memory_mb": 512,
            "context_tokens": 64_000,
            "output_bytes": 4_000_000,
            "tool_calls": 64,
            "model_calls": 0,
            "cost_microusd": 0,
            "network_calls": 0,
            "device_events": 100_000,
        }
        for name, ceiling in safe_budget_ceilings.items():
            budget_properties[name] = (
                {"const": 0}
                if ceiling == 0
                else {"maximum": ceiling, "minimum": 0, "type": "integer"}
            )

    if schema_path.name == "aura_multimodal_spatial_observation.schema.json":
        inverse_transcript_rule = {
            "if": {
                "properties": {"speech_text": {"maxLength": 0}},
                "required": ["speech_text"],
            },
            "then": {
                "properties": {"transcript_digest": {"const": ""}},
            },
        }
        if inverse_transcript_rule not in schema["allOf"]:
            schema["allOf"].append(inverse_transcript_rule)

    schema_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


test_path = Path("tests/test_aura_ephemeral_workspace_contracts.py")
tests = test_path.read_text()
old_cost_assertion = 'with pytest.raises(ValueError, match="micro-USD ceiling"):'
if old_cost_assertion not in tests:
    raise RuntimeError("cost overflow assertion anchor missing")
tests = tests.replace(
    old_cost_assertion,
    'with pytest.raises(ValueError, match="numeric ceiling|micro-USD ceiling"):',
    1,
)
if "def test_review_wave11_complete_bounds_and_schema_parity_fail_closed" in tests:
    raise RuntimeError("wave11 test already exists")
tests += r'''


def test_review_wave11_complete_bounds_and_schema_parity_fail_closed() -> None:
    """Every budget, key, metadata span, schema path, and live snapshot stays bounded."""
    with pytest.raises(ValueError, match="numeric ceiling"):
        canonical_json(1e308)
    with pytest.raises(ValueError, match="object key exceeds its scalar byte ceiling"):
        canonical_json({"x" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1): 1})
    with pytest.raises(ValueError, match="object keys must contain valid Unicode"):
        canonical_json({"\ud800": 1})

    class OversizedMetadata(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            raise AssertionError("metadata must reject by length before copying")

        def __len__(self) -> int:
            return len(workspace_contracts._METADATA_FIELDS) + 1

    with pytest.raises(ValueError, match="field ceiling"):
        workspace_contracts._metadata(OversizedMetadata(), "reference.metadata")

    for metadata, message in (
        ({"source_path": "src/module.py", "line_start": 0, "line_end": 1}, "integer in 1"),
        ({"source_path": "src/module.py", "line_start": 1}, "requires source_path"),
        ({"source_path": "src/module.py", "line_start": 2, "line_end": 1}, "reversed"),
    ):
        with pytest.raises(ValueError, match=message):
            ref(
                f"artifact:bad-span-{stable_digest(metadata)[:12]}",
                D["1"],
                metadata=metadata,
            )
    valid_span = ref(
        "artifact:valid-span",
        D["1"],
        metadata={"source_path": "src/module.py", "line_start": 1, "line_end": 2},
    )
    assert dict(valid_span.metadata)["line_end"] == 2

    manifest = create_manifest(
        "Reject unbounded context authority",
        organ_id="EORG-wave11-context",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    )
    oversized_context = WorkspaceBudget(
        wall_time_ms=1_000,
        memory_mb=1,
        context_tokens=64_001,
        output_bytes=1,
        tool_calls=0,
        model_calls=0,
        cost_microusd=0,
        network_calls=0,
        device_events=0,
    )
    with pytest.raises(ValueError, match="context_tokens exceeds the PR1 safe ceiling"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=_trusted_manifest_timestamps(manifest),
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
            budgets=oversized_context,
        )

    parsed_recipe, _ = recipe()
    oversized_device = parsed_recipe.to_dict()
    oversized_device["budgets"]["device_events"] = 100_001
    with pytest.raises(ValueError, match="device_events exceeds the PR1 safe ceiling"):
        EphemeralWorkspaceRecipe.from_dict(oversized_device)

    schema_cases = (
        (
            "schemas/aura_project_context_projection.schema.json",
            project().to_dict(),
            ("artifact_evidence_refs", 0, "metadata"),
        ),
        (
            "schemas/aura_ephemeral_workspace_recipe.schema.json",
            parsed_recipe.to_dict(),
            ("adapter_refs", 0, "metadata"),
        ),
        (
            "schemas/aura_multimodal_spatial_observation.schema.json",
            observation().to_dict(),
            ("target_candidates", 0, "evidence_ref", "metadata"),
        ),
    )

    def metadata_at(payload: dict[str, Any], path: tuple[Any, ...]) -> dict[str, Any]:
        current: Any = payload
        for part in path:
            current = current[part]
        return current

    for schema_name, base_payload, metadata_path in schema_cases:
        schema = json.loads((ROOT / schema_name).read_text())
        validator = Draft202012Validator(schema)
        for unsafe_path in ("src/.ENV.local", "SRC/Secrets-token", ".GIT/credentials"):
            payload = copy.deepcopy(base_payload)
            metadata_at(payload, metadata_path).clear()
            metadata_at(payload, metadata_path)["source_path"] = unsafe_path
            assert list(validator.iter_errors(payload)), (schema_name, unsafe_path)
        bad_line = copy.deepcopy(base_payload)
        metadata_at(bad_line, metadata_path).clear()
        metadata_at(bad_line, metadata_path).update(
            {"source_path": "src/module.py", "line_start": 0, "line_end": 1}
        )
        assert list(validator.iter_errors(bad_line)), schema_name

    recipe_schema = json.loads(
        (ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json").read_text()
    )
    unsafe_budget = parsed_recipe.to_dict()
    unsafe_budget["budgets"]["context_tokens"] = 64_001
    unsafe_budget["budgets"]["device_events"] = 100_001
    budget_error_paths = {
        tuple(error.absolute_path)
        for error in Draft202012Validator(recipe_schema).iter_errors(unsafe_budget)
    }
    assert ("budgets", "context_tokens") in budget_error_paths
    assert ("budgets", "device_events") in budget_error_paths

    observation_schema = json.loads(
        (ROOT / "schemas/aura_multimodal_spatial_observation.schema.json").read_text()
    )
    orphan_transcript = observation().to_dict()
    orphan_transcript["speech_text"] = ""
    orphan_transcript["transcript_digest"] = D["1"]
    assert list(Draft202012Validator(observation_schema).iter_errors(orphan_transcript))

    primary = create_manifest(
        "Single snapshot A",
        organ_id="EORG-wave11-single-snapshot",
        requested_capabilities=["resolve_capabilities", "read_slice", "dissolve"],
    ).to_dict()
    alternate = copy.deepcopy(primary)
    alternate["objective"] = "Single snapshot B"
    alternate["objective_hash"] = workspace_contracts.hashlib.blake2b(
        alternate["objective"].encode("utf-8"), digest_size=12
    ).hexdigest()
    alternate["phase_hash"] = workspace_contracts._legacy_manifest_digest(alternate)

    class TogglingManifest:
        def __init__(self) -> None:
            self.calls = 0

        def to_dict(self) -> dict[str, Any]:
            snapshots = (primary, alternate, primary)
            result = copy.deepcopy(snapshots[self.calls % len(snapshots)])
            self.calls += 1
            return result

    toggling = TogglingManifest()
    with pytest.raises(ValueError, match="changed while wrapping"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=toggling,
            expected_manifest_timestamps=(primary["created_at"], primary["expires_at"]),
            project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )
    assert toggling.calls == 2
'''
test_path.write_text(tests)


doc_path = Path("docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md")
doc = doc_path.read_text()
doc = replace_once(
    doc,
    "The focused suite now contains 26 tests covering:",
    "The focused suite now contains 27 tests covering:",
    "documentation test count",
)
doc = replace_once(
    doc,
    "13. docstring coverage and proof of no operational or persistence calls.",
    "13. docstring coverage and proof of no operational or persistence calls;\n"
    "14. complete budget, canonical-key, source-path/span, transcript, and single-snapshot bounds.",
    "documentation coverage list",
)
doc = replace_once(
    doc,
    "- focused tests: **26 passed**;",
    "- focused tests: **27 passed**;",
    "documentation verification count",
)
doc_path.write_text(doc)

print("applied PR255 wave11 complete-bound and schema-parity repairs")
