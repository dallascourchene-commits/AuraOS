from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one correction anchor, found {count}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once(
    "aura_ephemeral_workspace_contracts.py",
    '''        for item in exported_items:
            key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            result.append((key, item_value))
''',
    '''        for item in exported_items:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except ValueError as exc:
                if exc.__cause__ is None:
                    raise
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            result.append((key, item_value))
''',
)
replace_once(
    "tests/test_aura_ephemeral_workspace_contracts.py",
    '''    with pytest.raises(ValueError, match="sequence protocol"):
        stable_digest(SequenceIteratorRaises())
''',
    '''    with pytest.raises(ValueError, match="sequence protocol"):
        workspace_contracts._bounded_sequence_snapshot(
            SequenceIteratorRaises(), "hostile sequence", 2
        )
''',
)
