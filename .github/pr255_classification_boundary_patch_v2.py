from __future__ import annotations

import re
from pathlib import Path


def replace_regex(path: str, pattern: str, replacement: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
    if count != 1:
        raise RuntimeError(f"{path}: expected one correction replacement, found {count}")
    target.write_text(updated, encoding="utf-8")


def replace_count(path: str, old: str, new: str, expected: int) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{path}: expected {expected} correction anchors, found {count}")
    target.write_text(text.replace(old, new), encoding="utf-8")


path = "aura_ephemeral_workspace_contracts.py"
replace_count(
    path,
    '''class _NormalizedPairCallbackError(_NormalizedCallbackError):
    """Internal marker for a normalized pair classification/length/index callback."""


''',
    '''class _NormalizedPairCallbackError(_NormalizedCallbackError):
    """Internal marker for a normalized pair classification/length/index callback."""


class _PairShapeError(ValueError):
    """Internal marker for a pair value that is structurally not a two-item pair."""


''',
    1,
)

pair_function = '''def _bounded_pair_snapshot(value: Any, name: str) -> tuple[Any, Any]:
    """Detach one pair while separating caller ValueError from internal rejection markers."""
    try:
        if _guarded_isinstance(value, (str, bytes, bytearray), name):
            raise _PairShapeError(f"{name} must be a key/value pair")
        if not _guarded_isinstance(value, Sequence, name):
            raise _PairShapeError(f"{name} must be a key/value pair")
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
        raise _PairShapeError(f"{name} must be a key/value pair")
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


'''
replace_regex(
    path,
    r"def _bounded_pair_snapshot\(.*?(?=def _bounded_mapping_snapshot\()",
    pair_function,
)
replace_count(
    path,
    "except _NormalizedPairCallbackError as exc:",
    "except (_PairShapeError, _NormalizedPairCallbackError) as exc:",
    3,
)
