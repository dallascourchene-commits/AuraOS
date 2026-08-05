from pathlib import Path

path = Path("aura_ephemeral_workspace_contracts.py")
text = path.read_text()

old_float = '''    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        if abs(value) > MAX_CANONICAL_NUMBER_ABS:
            raise ValueError("canonical JSON number exceeds its numeric ceiling")
        return value
'''
new_float = '''    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite floats are prohibited")
        return value
'''
if text.count(old_float) != 1:
    raise RuntimeError("expected one canonical float block")
text = text.replace(old_float, new_float, 1)

old_strict = '''    if len(payload) > len(expected):
        raise ValueError(
            f"{name} keys mismatch: expected at most {len(expected)} keys"
        )
    keys = tuple(payload)
'''
new_strict = '''    if len(payload) > len(expected):
        if isinstance(payload, dict):
            for index, key in enumerate(payload):
                if index > len(expected):
                    break
                if not isinstance(key, str):
                    raise ValueError(f"{name} keys must be strings")
        raise ValueError(
            f"{name} keys mismatch: expected at most {len(expected)} keys"
        )
    keys = tuple(payload)
'''
if text.count(old_strict) != 1:
    raise RuntimeError("expected one strict breadth block")
text = text.replace(old_strict, new_strict, 1)

path.write_text(text)
print("preserved field-specific validation precedence")
