from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
SOURCE = ROOT / "aura_ephemeral_workspace_contracts.py"
TESTS = ROOT / "tests/test_aura_ephemeral_workspace_contracts.py"
DOCS = ROOT / "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md"
SCHEMAS = {
    "project": ROOT / "schemas/aura_project_context_projection.schema.json",
    "recipe": ROOT / "schemas/aura_ephemeral_workspace_recipe.schema.json",
    "observation": ROOT / "schemas/aura_multimodal_spatial_observation.schema.json",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
source = replace_once(
    source,
    '''def _bounded_sequence_snapshot(value: Any, name: str, max_items: int) -> tuple[Any, ...]:
    """Detach a sequence once and enforce the observed, not reported, item count."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result: list[Any] = []
    try:
        for item in value:
            result.append(item)
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    return tuple(result)


def _bounded_mapping_snapshot(value: Any, name: str, max_items: int) -> tuple[tuple[Any, Any], ...]:
    """Detach a mapping once and enforce reported and observed item ceilings."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    try:
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds its item ceiling")
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid item count") from exc
    result: list[tuple[Any, Any]] = []
    try:
        for item in value.items():
            if isinstance(item, (str, bytes, bytearray)) or not isinstance(item, Sequence):
                raise ValueError(f"{name} entries must be key/value pairs")
            try:
                pair_length = len(item)
            except (TypeError, OverflowError) as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            if pair_length != 2:
                raise ValueError(f"{name} entries must be key/value pairs")
            try:
                key, item_value = item[0], item[1]
            except (IndexError, KeyError, TypeError, OverflowError) as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            result.append((key, item_value))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    return tuple(result)
''',
    '''def _bounded_sequence_snapshot(value: Any, name: str, max_items: int) -> tuple[Any, ...]:
    """Detach a sequence once and normalize hostile iterator protocol failures."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result: list[Any] = []
    try:
        for item in value:
            result.append(item)
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid sequence protocol") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    return tuple(result)


def _bounded_pair_snapshot(value: Any, name: str) -> tuple[Any, Any]:
    """Detach one pair-like sequence while normalizing hostile callbacks."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a key/value pair")
    try:
        pair_length = len(value)
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    if pair_length != 2:
        raise ValueError(f"{name} must be a key/value pair")
    try:
        return value[0], value[1]
    except (IndexError, KeyError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc


def _bounded_mapping_snapshot(value: Any, name: str, max_items: int) -> tuple[tuple[Any, Any], ...]:
    """Detach a mapping once and normalize hostile export/iterator callbacks."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    try:
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds its item ceiling")
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid item count") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    try:
        exported_items = value.items()
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    result: list[tuple[Any, Any]] = []
    try:
        for item in exported_items:
            result.append(_bounded_pair_snapshot(item, f"{name} entry"))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except (TypeError, OverflowError) as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    return tuple(result)
''',
    "shared hostile-container boundary",
)
source = replace_once(
    source,
    '''        for item in pairs:
            if (
                isinstance(item, (str, bytes, bytearray))
                or not isinstance(item, Sequence)
                or len(item) != 2
            ):
                raise ValueError(f"{name} entries must be key/value pairs")
            key = item[0]
            if not isinstance(key, str):
                raise ValueError(f"{name} keys must be strings")
            normalized_pairs.append((key, item[1]))
''',
    '''        for item in pairs:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except ValueError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            if not isinstance(key, str):
                raise ValueError(f"{name} keys must be strings")
            normalized_pairs.append((key, item_value))
''',
    "metadata pair normalization",
)
source = replace_once(
    source,
    '''    pairs = []
    for item in items:
        if isinstance(item, (str, bytes, bytearray)) or not isinstance(item, Sequence) or len(item) != 2:
            raise ValueError("handoff map entries must be key/owner pairs")
        pairs.append((_id(item[0], "handoff key"), _id(item[1], "handoff owner")))
''',
    '''    pairs = []
    for item in items:
        try:
            key, owner = _bounded_pair_snapshot(item, "handoff map entry")
        except ValueError as exc:
            raise ValueError("handoff map entries must be key/owner pairs") from exc
        pairs.append((_id(key, "handoff key"), _id(owner, "handoff owner")))
''',
    "owner-map pair normalization",
)
source = replace_once(
    source,
    '''            for key, item in pairs:
                if not isinstance(key, str):
                    raise ValueError(f"{name} keys must be strings")
                if key in result:
                    raise ValueError(f"{name} keys must be unique")
                result[key] = _detached_json_snapshot(
                    item, f"{name}.{key}", _depth=next_depth, _active=active
                )
''',
    '''            for key, item in pairs:
                if not isinstance(key, str):
                    raise ValueError(f"{name} keys must be strings")
                try:
                    encoded_key = key.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        f"{name} keys must contain valid Unicode scalar values"
                    ) from exc
                if len(encoded_key) > MAX_CANONICAL_SCALAR_BYTES:
                    raise ValueError(f"{name} key exceeds its scalar byte ceiling")
                if key in result:
                    raise ValueError(f"{name} keys must be unique")
                result[key] = _detached_json_snapshot(
                    item, f"{name}.{key}", _depth=next_depth, _active=active
                )
''',
    "detached key scalar bound",
)
source = replace_once(
    source,
    '''    if (
        isinstance(expected_manifest_timestamps, (str, bytes, bytearray))
        or not isinstance(expected_manifest_timestamps, Sequence)
        or len(expected_manifest_timestamps) != 2
    ):
        raise ValueError("base manifest requires trusted timestamp bindings")
    expected_created_at = _finite_number(
        expected_manifest_timestamps[0],
        "expected base manifest created_at",
    )
    expected_expires_at = _finite_number(
        expected_manifest_timestamps[1],
        "expected base manifest expires_at",
    )
''',
    '''    try:
        timestamp_binding = _bounded_sequence_snapshot(
            expected_manifest_timestamps,
            "expected base manifest timestamps",
            2,
        )
    except ValueError as exc:
        raise ValueError("base manifest requires trusted timestamp bindings") from exc
    if len(timestamp_binding) != 2:
        raise ValueError("base manifest requires trusted timestamp bindings")
    expected_created_at = _finite_number(
        timestamp_binding[0],
        "expected base manifest created_at",
    )
    expected_expires_at = _finite_number(
        timestamp_binding[1],
        "expected base manifest expires_at",
    )
''',
    "trusted timestamp snapshot",
)
SOURCE.write_text(source, encoding="utf-8")

schema_updates: dict[str, tuple[dict[str, str], tuple[str, ...]]] = {
    "project": (
        {
            "current_and_bounded_freshness_admission": "mandatory semantic validator",
            "unicode_scalar_validation": "mandatory semantic validator",
        },
        (
            "project and nested reference current/bounded freshness delegated to mandatory semantic validation",
            "Unicode scalar validation delegated to mandatory semantic validation",
        ),
    ),
    "recipe": (
        {
            "reference_id_uniqueness_across_adapter_and_evidence_refs": "mandatory semantic validator",
            "manifest_reference_identity_digest_prefix_binding": "mandatory semantic validator",
            "unicode_scalar_validation": "mandatory semantic validator",
        },
        (
            "reference-ID uniqueness within and across adapter/evidence references delegated to mandatory semantic validation",
            "manifest reference ID and canonical-ref digest-prefix binding delegated to mandatory semantic validation",
            "Unicode scalar validation delegated to mandatory semantic validation",
        ),
    ),
    "observation": (
        {
            "transcript_digest_equality": "mandatory semantic validator",
            "target_binding_entity_evidence_id_uniqueness": "mandatory semantic validator",
            "unicode_scalar_validation": "mandatory semantic validator",
        },
        (
            "transcript digest equality delegated to mandatory semantic validation",
            "target binding, entity, and evidence-reference ID uniqueness delegated to mandatory semantic validation",
            "Unicode scalar validation delegated to mandatory semantic validation",
        ),
    ),
}
for kind, path in SCHEMAS.items():
    schema = json.loads(path.read_text(encoding="utf-8"))
    delegations = schema.setdefault("x-aura-semantic-delegations", {})
    invariants = schema.setdefault("x-aura-semantic-invariants", [])
    additions, statements = schema_updates[kind]
    for key, value in additions.items():
        delegations[key] = value
    for statement in statements:
        if statement not in invariants:
            invariants.append(statement)
    path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

docs = DOCS.read_text(encoding="utf-8")
docs = replace_once(
    docs,
    '''- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes malformed mapping-entry length/index protocols to `ValueError`;
''',
    '''- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile sequence iteration, mapping export/iteration, and pair length/index protocols to `ValueError`;
''',
    "docs hostile protocol boundary",
)
docs = replace_once(
    docs,
    '''Cross-record identity, graph, digest equality, timestamp arithmetic, transcript binding, canonical serialized array ordering, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. UTF-8 byte ceilings, source-span ordering (`line_start <= line_end`), and canonical serialized ordering are explicitly delegated to the named mandatory semantic validator because Draft 2020-12 counts code points, cannot compare sibling numeric fields, and cannot express deterministic ordering across independently identified records.
''',
    '''Cross-record identity, graph, digest equality, timestamp arithmetic, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.
''',
    "docs semantic honesty",
)
docs = replace_once(
    docs,
    '''The focused suite contains **33 tests** covering the original review waves plus the structural repair:
''',
    '''The focused suite contains **37 tests** covering the original review waves plus the structural repair:
''',
    "docs test count",
)
DOCS.write_text(docs, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
addition = r'''


def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries() -> None:
    """Accepted hostile containers must not leak protocol-specific exceptions."""
    class ItemsRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

        def items(self):
            raise TypeError("hostile items export")

    class ItemsIteratorRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 1

        def items(self):
            class BrokenIterator:
                def __iter__(self):
                    return self

                def __next__(self):
                    raise OverflowError("hostile items iterator")

            return BrokenIterator()

    class SequenceIteratorRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise OverflowError("hostile sequence iterator")

        def __len__(self) -> int:
            return 1

    class PairLengthRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            return ("architecture", "aura_coding_relationship_compass")[index]

        def __len__(self) -> int:
            raise TypeError("hostile pair length")

    for mapping in (ItemsRaisesMapping(), ItemsIteratorRaisesMapping()):
        with pytest.raises(ValueError, match="mapping export protocol"):
            workspace_contracts._bounded_mapping_snapshot(mapping, "hostile mapping", 2)
    with pytest.raises(ValueError, match="sequence protocol"):
        workspace_contracts._bounded_sequence_snapshot(
            SequenceIteratorRaises(), "hostile sequence", 2
        )
    with pytest.raises(ValueError, match="key/value pair"):
        workspace_contracts._bounded_pair_snapshot(PairLengthRaises(), "hostile pair")
    with pytest.raises(ValueError, match="metadata entries must be key/value pairs"):
        workspace_contracts._metadata((PairLengthRaises(),), "metadata")
    with pytest.raises(ValueError, match="handoff map entries must be key/owner pairs"):
        workspace_contracts._owner_map((PairLengthRaises(),))


def test_compiler_timestamp_binding_is_a_bounded_detached_sequence() -> None:
    """Trusted timestamp protocols must fail closed before indexed access."""
    class TimestampIndexRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise TypeError("hostile timestamp index")

        def __len__(self) -> int:
            return 2

    manifest = create_manifest(
        "Reject hostile trusted timestamp protocols",
        organ_id="EORG-hostile-timestamp-binding",
    )
    with pytest.raises(ValueError, match="trusted timestamp bindings"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=manifest,
            expected_manifest_timestamps=TimestampIndexRaises(),
            project_projection=project(),
            expected_project_projection=project(),
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


def test_detached_snapshot_bounds_object_keys_before_using_them_in_paths() -> None:
    """Unknown object keys receive the same scalar/Unicode guard as values."""
    oversized_key = "k" * (workspace_contracts.MAX_CANONICAL_SCALAR_BYTES + 1)
    with pytest.raises(ValueError, match="key exceeds its scalar byte ceiling"):
        workspace_contracts._detached_json_snapshot({oversized_key: 1}, "payload")
    with pytest.raises(ValueError, match="valid Unicode scalar values"):
        workspace_contracts._detached_json_snapshot({"\ud800": 1}, "payload")


def test_schema_delegations_name_all_remaining_public_boundary_semantics() -> None:
    """Schema-only consumers must be told which rejections require admission code."""
    expected = {
        "aura_project_context_projection.schema.json": {
            "current_and_bounded_freshness_admission",
            "unicode_scalar_validation",
        },
        "aura_ephemeral_workspace_recipe.schema.json": {
            "reference_id_uniqueness_across_adapter_and_evidence_refs",
            "manifest_reference_identity_digest_prefix_binding",
            "unicode_scalar_validation",
        },
        "aura_multimodal_spatial_observation.schema.json": {
            "transcript_digest_equality",
            "target_binding_entity_evidence_id_uniqueness",
            "unicode_scalar_validation",
        },
    }
    for filename, required_delegations in expected.items():
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        delegations = schema["x-aura-semantic-delegations"]
        assert required_delegations <= set(delegations)
        assert all(
            delegations[name] == "mandatory semantic validator"
            for name in required_delegations
        )
        invariants = "\n".join(schema["x-aura-semantic-invariants"])
        assert "Unicode scalar validation delegated" in invariants
'''
if "def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries" in tests:
    raise RuntimeError("public-boundary tests already present")
tests = tests.rstrip() + addition + "\n"
TESTS.write_text(tests, encoding="utf-8")
