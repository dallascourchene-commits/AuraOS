from __future__ import annotations

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


helpers = '''class _NormalizedCallbackError(ValueError):
    """Internal marker for an ordinary hostile callback normalized at a boundary."""


class _NormalizedPairCallbackError(_NormalizedCallbackError):
    """Internal marker for a normalized pair classification/length/index callback."""


def _guarded_isinstance(value: Any, classinfo: Any, name: str) -> bool:
    """Classify a hostile value without leaking ordinary __class__ callbacks."""
    try:
        return isinstance(value, classinfo)
    except ValueError:
        raise
    except RecursionError as exc:
        raise _NormalizedCallbackError(
            f"{name} type classification exceeds its depth ceiling"
        ) from exc
    except Exception as exc:
        raise _NormalizedCallbackError(
            f"{name} has an invalid type classification protocol"
        ) from exc


def _guarded_is_dataclass(value: Any) -> bool:
    """Classify a dataclass without leaking hostile metaclass callbacks."""
    try:
        return is_dataclass(value)
    except ValueError:
        raise
    except RecursionError as exc:
        raise _NormalizedCallbackError(
            "canonical JSON dataclass classification exceeds its depth ceiling"
        ) from exc
    except Exception as exc:
        raise _NormalizedCallbackError(
            "canonical JSON value has an invalid dataclass classification protocol"
        ) from exc


def _bounded_sequence_snapshot(value: Any, name: str, max_items: int) -> tuple[Any, ...]:
    """Detach a sequence once and normalize hostile classification/iteration failures."""
    if _guarded_isinstance(value, (str, bytes, bytearray), name):
        raise ValueError(f"{name} must be a sequence")
    if not _guarded_isinstance(value, Sequence, name):
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
        raise _NormalizedCallbackError(f"{name} has an invalid sequence protocol") from exc
    return tuple(result)


def _bounded_pair_snapshot(value: Any, name: str) -> tuple[Any, Any]:
    """Detach one pair-like sequence while marking only normalized callback failures."""
    try:
        if _guarded_isinstance(value, (str, bytes, bytearray), name):
            raise ValueError(f"{name} must be a key/value pair")
        if not _guarded_isinstance(value, Sequence, name):
            raise ValueError(f"{name} must be a key/value pair")
    except _NormalizedCallbackError as exc:
        raise _NormalizedPairCallbackError(f"{name} must be a key/value pair") from exc
    try:
        pair_length = len(value)
    except ValueError:
        raise
    except RecursionError as exc:
        raise _NormalizedPairCallbackError(
            f"{name} nesting exceeds its depth ceiling"
        ) from exc
    except Exception as exc:
        raise _NormalizedPairCallbackError(f"{name} must be a key/value pair") from exc
    if pair_length != 2:
        raise ValueError(f"{name} must be a key/value pair")
    try:
        return value[0], value[1]
    except ValueError:
        raise
    except RecursionError as exc:
        raise _NormalizedPairCallbackError(
            f"{name} nesting exceeds its depth ceiling"
        ) from exc
    except Exception as exc:
        raise _NormalizedPairCallbackError(f"{name} must be a key/value pair") from exc


def _bounded_mapping_snapshot(value: Any, name: str, max_items: int) -> tuple[tuple[Any, Any], ...]:
    """Detach a mapping once and normalize hostile classification/export callbacks."""
    if not _guarded_isinstance(value, Mapping, name):
        raise ValueError(f"{name} must be an object")
    try:
        if len(value) > max_items:
            raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise _NormalizedCallbackError(f"{name} has an invalid item count") from exc
    try:
        exported_items = value.items()
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise _NormalizedCallbackError(
            f"{name} has an invalid mapping export protocol"
        ) from exc
    result: list[tuple[Any, Any]] = []
    try:
        for item in exported_items:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except _NormalizedPairCallbackError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            result.append((key, item_value))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
    except ValueError:
        raise
    except RecursionError as exc:
        raise ValueError(f"{name} nesting exceeds its depth ceiling") from exc
    except Exception as exc:
        raise _NormalizedCallbackError(
            f"{name} has an invalid mapping export protocol"
        ) from exc
    return tuple(result)


'''
replace_regex(
    "aura_ephemeral_workspace_contracts.py",
    r"def _bounded_sequence_snapshot\(.*?(?=def _canonical\()",
    helpers,
)

canonical = '''def _canonical(value: Any, *, _depth: int = 0, _active: set[int] | None = None) -> Any:
    """Return a lossless bounded canonical JSON value from one detached traversal."""
    if _depth > MAX_CANONICAL_DEPTH:
        raise ValueError("canonical JSON nesting exceeds its depth ceiling")
    active = set() if _active is None else _active
    next_depth = _depth + 1
    if _guarded_isinstance(value, Enum, "canonical JSON value"):
        try:
            enum_value = value.value
        except ValueError:
            raise
        except RecursionError as exc:
            raise ValueError("canonical JSON enum nesting exceeds its depth ceiling") from exc
        except Exception as exc:
            raise _NormalizedCallbackError(
                "canonical JSON enum has an invalid value protocol"
            ) from exc
        return _canonical(enum_value, _depth=next_depth, _active=active)
    if _guarded_is_dataclass(value):
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
    if _guarded_isinstance(value, Mapping, "canonical JSON value"):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive object")
        active.add(marker)
        try:
            pairs = _bounded_mapping_snapshot(value, "canonical JSON object", MAX_CANONICAL_ITEMS)
            keys = [key for key, _ in pairs]
            if any(type(key) is not str for key in keys):
                raise ValueError("JSON object keys must be strings")
            if len(set(keys)) != len(keys):
                raise ValueError("canonical JSON object keys must be unique")
            detached: dict[str, Any] = {}
            for key, item in pairs:
                try:
                    encoded_key = key.encode("utf-8")
                except UnicodeEncodeError as exc:
                    raise ValueError(
                        "canonical JSON object keys must contain valid Unicode scalar values"
                    ) from exc
                if len(encoded_key) > MAX_CANONICAL_SCALAR_BYTES:
                    raise ValueError("canonical JSON object key exceeds its scalar byte ceiling")
                detached[key] = item
            return {
                key: _canonical(detached[key], _depth=next_depth, _active=active)
                for key in sorted(detached)
            }
        finally:
            active.remove(marker)
    if _guarded_isinstance(value, (list, tuple), "canonical JSON value"):
        marker = id(value)
        if marker in active:
            raise ValueError("canonical JSON contains a recursive sequence")
        active.add(marker)
        try:
            items = _bounded_sequence_snapshot(value, "canonical JSON sequence", MAX_CANONICAL_ITEMS)
            return [_canonical(item, _depth=next_depth, _active=active) for item in items]
        finally:
            active.remove(marker)
    if _guarded_isinstance(value, (set, frozenset), "canonical JSON value"):
        raise ValueError("sets are not JSON values")
    if type(value) is str:
        try:
            encoded = value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("canonical JSON strings must contain valid Unicode scalar values") from exc
        if len(encoded) > MAX_CANONICAL_SCALAR_BYTES:
            raise ValueError("canonical JSON string exceeds its scalar byte ceiling")
        return value
    if value is None or type(value) is bool:
        return value
    if type(value) is int:
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON integer exceeds its numeric ceiling")
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
    raise ValueError(f"non-JSON value: {type(value).__name__}")

'''
replace_regex(
    "aura_ephemeral_workspace_contracts.py",
    r"def _canonical\(.*?(?=def canonical_json\()",
    canonical,
)

replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    if isinstance(value, tuple):
        pairs = _bounded_sequence_snapshot(value, name, len(_METADATA_FIELDS))
''',
    '''    if _guarded_isinstance(value, tuple, name):
        pairs = _bounded_sequence_snapshot(value, name, len(_METADATA_FIELDS))
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''            except ValueError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
''',
    '''            except _NormalizedPairCallbackError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    elif isinstance(value, Mapping):
        try:
''',
    '''    elif _guarded_isinstance(value, Mapping, name):
        try:
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    if not isinstance(payload, Mapping):
        raise ValueError(f"{name} must be an object")
    if isinstance(payload, dict) and any(type(key) is not str for key in payload):
''',
    '''    if not _guarded_isinstance(payload, Mapping, name):
        raise ValueError(f"{name} must be an object")
    if _guarded_isinstance(payload, dict, name) and any(type(key) is not str for key in payload):
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    if isinstance(value, Mapping):
        marker = id(value)
''',
    '''    if _guarded_isinstance(value, Mapping, name):
        marker = id(value)
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        marker = id(value)
''',
    '''    if (
        _guarded_isinstance(value, Sequence, name)
        and not _guarded_isinstance(value, (str, bytes, bytearray), name)
    ):
        marker = id(value)
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''    if isinstance(value, Mapping):
        items = _bounded_mapping_snapshot(value, "handoff map", MAX_HANDOFF_OWNERS)
''',
    '''    if _guarded_isinstance(value, Mapping, "handoff map"):
        items = _bounded_mapping_snapshot(value, "handoff map", MAX_HANDOFF_OWNERS)
''',
)
replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''        except ValueError as exc:
            raise ValueError("handoff map entries must be key/owner pairs") from exc
''',
    '''        except _NormalizedPairCallbackError as exc:
            raise ValueError("handoff map entries must be key/owner pairs") from exc
''',
)

enum_test = '''def test_enum_unicode_failures_are_normalized_to_value_error() -> None:
    """Enum value lookup and recursive validation share the fail-closed boundary."""
    class RuntimeValueEnum(Enum):
        BAD = "runtime"

        @property
        def value(self):
            raise RuntimeError("hostile enum value lookup")

    class PreservedValueEnum(Enum):
        BAD = "value-error"

        @property
        def value(self):
            raise ValueError("preserved enum value callback")

    with pytest.raises(ValueError, match="valid Unicode scalar values"):
        stable_digest(_SurrogateEnum.BAD)
    with pytest.raises(ValueError, match="enum has an invalid value protocol"):
        stable_digest(RuntimeValueEnum.BAD)
    with pytest.raises(ValueError, match="preserved enum value callback"):
        stable_digest(PreservedValueEnum.BAD)


'''
replace_regex(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    r"def test_enum_unicode_failures_are_normalized_to_value_error\(\) -> None:\n.*?(?=def test_hostile_container_protocol_callbacks_fail_closed_at_shared_boundaries)",
    enum_test,
)

replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    class PreservedValueErrorSequence(Sequence[Any]):
''',
    '''    class ClassificationRaisesMapping(Mapping[str, Any]):
        @property
        def __class__(self):
            raise RuntimeError("hostile mapping classification")

        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 0

    class ClassificationRaisesSequence(Sequence[Any]):
        @property
        def __class__(self):
            raise RuntimeError("hostile sequence classification")

        def __getitem__(self, index: int) -> Any:
            raise IndexError(index)

        def __len__(self) -> int:
            return 0

    class CausedValueErrorPairLength(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            return ("architecture", "aura_coding_relationship_compass")[index]

        def __len__(self) -> int:
            try:
                raise RuntimeError("pair length cause")
            except RuntimeError as cause:
                raise ValueError("preserved caused pair length") from cause

    class CausedValueErrorPairIndex(Sequence[Any]):
        def __getitem__(self, index: int) -> Any:
            try:
                raise RuntimeError("pair index cause")
            except RuntimeError as cause:
                raise ValueError("preserved caused pair index") from cause

        def __len__(self) -> int:
            return 2

    class PreservedValueErrorSequence(Sequence[Any]):
''',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    with pytest.raises(ValueError, match="preserved sequence callback"):
''',
    '''    with pytest.raises(ValueError, match="invalid type classification protocol"):
        workspace_contracts._bounded_mapping_snapshot(
            ClassificationRaisesMapping(), "hostile mapping", 2
        )
    with pytest.raises(ValueError, match="invalid type classification protocol"):
        workspace_contracts._bounded_sequence_snapshot(
            ClassificationRaisesSequence(), "hostile sequence", 2
        )
    for pair, message in (
        (CausedValueErrorPairLength(), "preserved caused pair length"),
        (CausedValueErrorPairIndex(), "preserved caused pair index"),
    ):
        with pytest.raises(ValueError, match=message):
            workspace_contracts._bounded_mapping_snapshot(
                {"entry": 1}.items() if False else _SinglePairMapping(pair),
                "hostile mapping",
                2,
            )
    with pytest.raises(ValueError, match="preserved sequence callback"):
''',
)
# Define a tiny mapping fixture locally before the caused-pair assertions.
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    class ControlFlowSequence(Sequence[Any]):
''',
    '''    class _SinglePairMapping(Mapping[str, Any]):
        def __init__(self, pair: Sequence[Any]) -> None:
            self.pair = pair

        def __getitem__(self, key: str) -> Any:
            raise KeyError(key)

        def __iter__(self):
            return iter(())

        def __len__(self) -> int:
            return 1

        def items(self):
            return iter((self.pair,))

    class ControlFlowSequence(Sequence[Any]):
''',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    with pytest.raises(ValueError, match="mapping export protocol"):
        ProjectContextProjection.from_dict(ItemsCallRaisesMapping())
''',
    '''    with pytest.raises(ValueError, match="mapping export protocol"):
        ProjectContextProjection.from_dict(ItemsCallRaisesMapping())
    with pytest.raises(ValueError, match="invalid type classification protocol"):
        ProjectContextProjection.from_dict(ClassificationRaisesMapping())
''',
)

replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    @dataclass
    class PreservedValueErrorExport:
''',
    '''    class RuntimeClassificationMeta(type):
        def __getattribute__(cls, name: str) -> Any:
            if name == "__dataclass_fields__":
                raise RuntimeError("hostile dataclass classification")
            return super().__getattribute__(name)

    class RuntimeClassification(metaclass=RuntimeClassificationMeta):
        pass

    class PreservedClassificationMeta(type):
        def __getattribute__(cls, name: str) -> Any:
            if name == "__dataclass_fields__":
                raise ValueError("preserved dataclass classification")
            return super().__getattribute__(name)

    class PreservedClassification(metaclass=PreservedClassificationMeta):
        pass

    @dataclass
    class PreservedValueErrorExport:
''',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    with pytest.raises(ValueError, match="preserved dataclass callback"):
        stable_digest(PreservedValueErrorExport())
''',
    '''    with pytest.raises(ValueError, match="invalid dataclass classification protocol"):
        stable_digest(RuntimeClassification())
    with pytest.raises(ValueError, match="preserved dataclass classification"):
        stable_digest(PreservedClassification())
    with pytest.raises(ValueError, match="preserved dataclass callback"):
        stable_digest(PreservedValueErrorExport())
''',
)

replace_once(
    "docs/AURA_INTENT_NATIVE_SPATIAL_WORKSPACE_PR1.md",
    '- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile sequence iteration, mapping length/export/iteration, pair length/index, dataclass export/field access, and live-manifest export callbacks to `ValueError`; existing `ValueError` is preserved, other ordinary `Exception` failures are normalized, and control-flow `BaseException` values propagate;',
    '- rechecks observed breadth after iteration rather than trusting a custom `len()`, and normalizes hostile container/type classification, sequence iteration, mapping length/export/iteration, pair length/index, enum-value lookup, dataclass classification/export/field access, and live-manifest export callbacks to `ValueError`; an internal callback marker—not exception chaining—is used to distinguish normalized pair failures, so existing `ValueError` (including explicitly caused values) is preserved, other ordinary `Exception` failures are normalized, and control-flow `BaseException` values propagate;',
)
