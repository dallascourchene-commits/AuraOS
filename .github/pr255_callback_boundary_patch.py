from __future__ import annotations

import json
import re
from pathlib import Path


def replace_regex(path: str, pattern: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex replacement, found {count}")
    target.write_text(updated, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one replacement anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


protocol_helpers = '''def _bounded_sequence_snapshot(value: Any, name: str, max_items: int) -> tuple[Any, ...]:
    """Detach a sequence once and normalize hostile iterator protocol failures."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a sequence")
    result: list[Any] = []
    try:
        for item in value:
            result.append(item)
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid sequence protocol") from exc
    return tuple(result)


def _bounded_pair_snapshot(value: Any, name: str) -> tuple[Any, Any]:
    """Detach one pair-like sequence while normalizing hostile callbacks."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(f"{name} must be a key/value pair")
    try:
        pair_length = len(value)
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc
    if pair_length != 2:
        raise ValueError(f"{name} must be a key/value pair")
    try:
        return value[0], value[1]
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} must be a key/value pair") from exc


def _bounded_mapping_snapshot(value: Any, name: str, max_items: int) -> tuple[tuple[Any, Any], ...]:
    """Detach a mapping once and normalize hostile export/iterator callbacks."""
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    try:
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid item count") from exc
    try:
        exported_items = value.items()
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    result: list[tuple[Any, Any]] = []
    try:
        for item in exported_items:
            key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            result.append((key, item_value))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError(f"{name} has an invalid mapping export protocol") from exc
    return tuple(result)


'''
replace_regex(
    "aura_ephemeral_workspace_contracts.py",
    r"def _bounded_sequence_snapshot\(.*?(?=def _canonical\()",
    protocol_helpers,
)

canonical_dataclass_branch = '''    if is_dataclass(value):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive dataclass")
        active.add(marker)
        try:
            try:
                exporter = getattr(value, "to_dict", None)
            except ValueError:
                raise
            except RecursionError as exc:
                raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
            except Exception as exc:
                raise ValueError("canonical JSON dataclass has an invalid export protocol") from exc
            if exporter is not None:
                if not callable(exporter):
                    raise ValueError("canonical JSON dataclass has an invalid export protocol")
                try:
                    exported = exporter()
                except ValueError:
                    raise
                except RecursionError as exc:
                    raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
                except Exception as exc:
                    raise ValueError("canonical JSON dataclass has an invalid export protocol") from exc
            else:
                try:
                    exported = {field.name: getattr(value, field.name) for field in fields(value)}
                except ValueError:
                    raise
                except RecursionError as exc:
                    raise ValueError("canonical JSON dataclass nesting exceeds its depth ceiling") from exc
                except Exception as exc:
                    raise ValueError("canonical JSON dataclass has an invalid field export protocol") from exc
            return _canonical(exported, _depth=next_depth, _active=active)
        finally:
            active.remove(marker)
'''
replace_regex(
    "aura_ephemeral_workspace_contracts.py",
    r"    if is_dataclass\(value\):\n.*?(?=    if isinstance\(value, Mapping\):)",
    canonical_dataclass_branch,
)

manifest_export = '''def _bounded_manifest_export(manifest: Any) -> Any:
    """Export a live V1 manifest while normalizing hostile export callbacks."""
    try:
        exporter = getattr(manifest, "to_dict", None)
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError("base manifest nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError("base manifest has an invalid export protocol") from exc
    if exporter is None:
        return manifest
    if not callable(exporter):
        raise ValueError("base manifest has an invalid export protocol")
    try:
        return exporter()
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError("base manifest nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise ValueError("base manifest has an invalid export protocol") from exc


'''
replace_regex(
    "aura_ephemeral_workspace_contracts.py",
    r"def _bounded_manifest_export\(.*?(?=def _manifest_snapshot\()",
    manifest_export,
)

container_test = '''def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries() -> None:
    """Every ordinary hostile container callback normalizes without catching BaseException."""
    class MappingLengthRaises(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            raise RuntimeError("hostile mapping length")

    class ItemsLookupRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

        @property
        def items(self):
            raise RuntimeError("hostile items lookup")

    class ItemsCallRaisesMapping(Mapping[str, Any]):
        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

        def items(self):
            raise RuntimeError("hostile items invocation")

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
                    raise RuntimeError("hostile items iterator")

            return BrokenIterator()

    class SequenceIteratorRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise IndexError(index)

        def __len__(self) -> int:
            return 1

        def __iter__(self):
            raise RuntimeError("hostile sequence iterator")

    class PairLengthRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            return ("architecture", "aura_coding_relationship_compass")[index]

        def __len__(self) -> int:
            raise RuntimeError("hostile pair length")

    class PairIndexRaises(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise RuntimeError("hostile pair index")

        def __len__(self) -> int:
            return 2

    class PreservedValueErrorSequence(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise IndexError(index)

        def __len__(self) -> int:
            return 1

        def __iter__(self):
            raise ValueError("preserved sequence callback")

    class ControlFlowSequence(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            raise IndexError(index)

        def __len__(self) -> int:
            return 1

        def __iter__(self):
            raise KeyboardInterrupt("control flow must propagate")

    with pytest.raises(ValueError, match="invalid item count"):
        workspace_contracts._bounded_mapping_snapshot(
            MappingLengthRaises(), "hostile mapping", 2
        )
    for mapping in (
        ItemsLookupRaisesMapping(),
        ItemsCallRaisesMapping(),
        ItemsIteratorRaisesMapping(),
    ):
        with pytest.raises(ValueError, match="mapping export protocol"):
            workspace_contracts._bounded_mapping_snapshot(mapping, "hostile mapping", 2)
    with pytest.raises(ValueError, match="sequence protocol"):
        stable_digest(SequenceIteratorRaises())
    for pair in (PairLengthRaises(), PairIndexRaises()):
        with pytest.raises(ValueError, match="key/value pair"):
            workspace_contracts._bounded_pair_snapshot(pair, "hostile pair")
    with pytest.raises(ValueError, match="metadata entries must be key/value pairs"):
        workspace_contracts._metadata((PairLengthRaises(),), "metadata")
    with pytest.raises(ValueError, match="handoff map entries must be key/owner pairs"):
        workspace_contracts._owner_map((PairIndexRaises(),))
    with pytest.raises(ValueError, match="preserved sequence callback"):
        workspace_contracts._bounded_sequence_snapshot(
            PreservedValueErrorSequence(), "hostile sequence", 2
        )
    with pytest.raises(KeyboardInterrupt, match="control flow must propagate"):
        workspace_contracts._bounded_sequence_snapshot(
            ControlFlowSequence(), "hostile sequence", 2
        )
    with pytest.raises(ValueError, match="mapping export protocol"):
        ProjectContextProjection.from_dict(ItemsCallRaisesMapping())


'''
replace_regex(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    r"def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries\(\) -> None:\n.*?(?=def test_compiler_timestamp_binding_is_a_bounded_detached_sequence)",
    container_test,
)

dataclass_test = '''def test_dataclass_export_callbacks_are_normalized_to_value_error() -> None:
    """Lookup, invocation, and field callbacks normalize RuntimeError but preserve ValueError."""
    @dataclass
    class NonCallableExport:
        value: int = 1
        to_dict: Any = 7

    @dataclass
    class LookupRaisesExport:
        value: int = 1

        @property
        def to_dict(self):
            raise RuntimeError("hostile dataclass lookup")

    @dataclass
    class InvocationRaisesExport:
        value: int = 1

        def to_dict(self) -> dict[str, Any]:
            raise RuntimeError("hostile dataclass invocation")

    @dataclass
    class FieldAccessRaisesExport:
        value: int = 1

        def __getattribute__(self, name: str) -> Any:
            if name == "value":
                raise RuntimeError("hostile dataclass field access")
            return object.__getattribute__(self, name)

    @dataclass
    class PreservedValueErrorExport:
        value: int = 1

        def to_dict(self) -> dict[str, Any]:
            raise ValueError("preserved dataclass callback")

    for value in (
        NonCallableExport(),
        LookupRaisesExport(),
        InvocationRaisesExport(),
    ):
        with pytest.raises(ValueError, match="dataclass has an invalid export protocol"):
            stable_digest(value)
    with pytest.raises(ValueError, match="dataclass has an invalid field export protocol"):
        stable_digest(FieldAccessRaisesExport())
    with pytest.raises(ValueError, match="preserved dataclass callback"):
        stable_digest(PreservedValueErrorExport())


'''
replace_regex(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    r"def test_dataclass_export_callbacks_are_normalized_to_value_error\(\) -> None:\n.*?(?=def test_live_manifest_export_callbacks_are_normalized_to_value_error)",
    dataclass_test,
)

manifest_test = '''def test_live_manifest_export_callbacks_are_normalized_to_value_error() -> None:
    """Live-manifest lookup and invocation normalize RuntimeError but preserve ValueError."""
    class NonCallableManifest:
        to_dict: Any = {}

    class LookupRaisesManifest:
        @property
        def to_dict(self):
            raise RuntimeError("hostile manifest lookup")

    class InvocationRaisesManifest:
        def to_dict(self) -> dict[str, Any]:
            raise RuntimeError("hostile manifest invocation")

    class PreservedValueErrorManifest:
        def to_dict(self) -> dict[str, Any]:
            raise ValueError("preserved manifest callback")

    for manifest in (
        NonCallableManifest(),
        LookupRaisesManifest(),
        InvocationRaisesManifest(),
    ):
        trusted_project = project()
        with pytest.raises(ValueError, match="base manifest has an invalid export protocol"):
            compile_coding_spatial_workspace_recipe(
                base_manifest=manifest,
                expected_manifest_timestamps=(0, 1),
                project_projection=trusted_project,
                expected_project_projection=trusted_project,
                canonical_intent_digest=D["1"],
                adapter_refs=(ref("adapter:compass", D["2"]),),
                evidence_refs=(ref("evidence:source", D["3"]),),
            )
    trusted_project = project()
    with pytest.raises(ValueError, match="preserved manifest callback"):
        compile_coding_spatial_workspace_recipe(
            base_manifest=PreservedValueErrorManifest(),
            expected_manifest_timestamps=(0, 1),
            project_projection=trusted_project,
            expected_project_projection=trusted_project,
            canonical_intent_digest=D["1"],
            adapter_refs=(ref("adapter:compass", D["2"]),),
            evidence_refs=(ref("evidence:source", D["3"]),),
        )


'''
replace_regex(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    r"def test_live_manifest_export_callbacks_are_normalized_to_value_error\(\) -> None:\n.*?(?=def test_nested_contract_subclasses_are_rejected_before_parent_signing)",
    manifest_test,
)

replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '            "exact_builtin_integer_representation",\n        },\n    }\n',
    '            "exact_builtin_integer_representation",\n'
    '            "exact_builtin_number_representation",\n'
    '        },\n'
    '    }\n',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '        if filename == "aura_ephemeral_workspace_recipe.schema.json":\n',
    '        if filename == "aura_multimodal_spatial_observation.schema.json":\n'
    '            assert "exact built-in number representation delegated" in invariants\n'
    '        if filename == "aura_ephemeral_workspace_recipe.schema.json":\n',
)

schema_path = Path("schemas/aura_multimodal_spatial_observation.schema.json")
schema = json.loads(schema_path.read_text(encoding="utf-8"))
delegations = schema["x-aura-semantic-delegations"]
delegations["exact_builtin_number_representation"] = "mandatory semantic validator"
schema["x-aura-semantic-delegations"] = dict(sorted(delegations.items()))
invariant = "exact built-in number representation delegated to mandatory semantic validation"
if invariant not in schema["x-aura-semantic-invariants"]:
    schema["x-aura-semantic-invariants"].append(invariant)
schema_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

replace_once(
    "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md",
    '- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile sequence iteration, mapping export/iteration, and pair length/index protocols to `ValueError`;',
    '- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile sequence iteration, mapping length/export/iteration, pair length/index, dataclass export/field access, and live-manifest export callbacks to `ValueError`; existing `ValueError` is preserved, other ordinary `Exception` failures are normalized, and control-flow `BaseException` values propagate;',
)
replace_once(
    "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md",
    'Cross-record identity, graph, digest equality, signed issue/TTL/expiration arithmetic, exact built-in integer representation, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, exact built-in integer representation, signed lifecycle arithmetic, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.',
    'Cross-record identity, graph, digest equality, signed issue/TTL/expiration arithmetic, exact built-in integer and number representation, transcript equality, freshness admission, reference-ID uniqueness, manifest digest-prefix identity, target identity uniqueness, canonical serialized array ordering, Unicode scalar validity, and complete admission require executable semantic validation. All three schemas declare `x-aura-semantic-requires-independent-binding: true`. Each non-structural rejection is named in `x-aura-semantic-delegations`; UTF-8 byte ceilings, Unicode scalar validity, exact built-in integer representation, exact built-in number representation for observation confidence/quality fields, signed lifecycle arithmetic, source-span ordering (`line_start <= line_end`), cross-record uniqueness/equality, freshness, digest-prefix identity, and canonical ordering are enforced by the named mandatory semantic validator rather than falsely claimed as Draft 2020-12 structure.',
)
