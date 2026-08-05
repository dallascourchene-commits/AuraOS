from pathlib import Path

path = Path("aura_ephemeral_workspace_contracts.py")
text = path.read_text(encoding="utf-8")
old = '''        for item in exported_items:
            result.append(_bounded_pair_snapshot(item, f"{name} entry"))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
'''
new = '''        for item in exported_items:
            try:
                key, item_value = _bounded_pair_snapshot(item, f"{name} entry")
            except ValueError as exc:
                raise ValueError(f"{name} entries must be key/value pairs") from exc
            result.append((key, item_value))
            if len(result) > max_items:
                raise ValueError(f"{name} exceeds its item ceiling")
'''
if text.count(old) != 1:
    raise RuntimeError(f"expected one mapping pair insertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
