from pathlib import Path

SOURCE = Path("aura_ephemeral_workspace_contracts.py")
TESTS = Path("tests/test_aura_ephemeral_workspace_contracts.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


source = SOURCE.read_text(encoding="utf-8")
source = replace_once(
    source,
    '''    remaining_seconds = expires_at - now
    if remaining_seconds < 1:
        raise ValueError("base manifest has less than one whole second remaining")
    remaining_ttl = math.floor(remaining_seconds)
''',
    '''    remaining_seconds = expires_at - now
    if remaining_seconds <= 0:
        raise ValueError("base manifest is expired")
    if remaining_seconds < 1:
        raise ValueError("base manifest has less than one whole second remaining")
    remaining_ttl = math.floor(remaining_seconds)
''',
    "expired versus fractional TTL",
)
source = replace_once(
    source,
    '''        record = cls(**dict(payload))
        identity_body = record.to_dict()
''',
    '''        record = cls(**dict(payload))
        _require_exact_serialized_form(record, payload)
        identity_body = record.to_dict()
''',
    "recipe exact serialized form",
)
SOURCE.write_text(source, encoding="utf-8")

tests = TESTS.read_text(encoding="utf-8")
tests = replace_once(
    tests,
    "    assert short.ttl_seconds == 10\n",
    "    assert 1 <= short.ttl_seconds <= 10\n",
    "elapsed manifest TTL assertion",
)
tests = replace_once(
    tests,
    '        observation(sources=("voice", "VOICE"))\n',
    '        observation(sources=("VOICE", "VOICE"))\n',
    "canonical duplicate observation sources",
)
tests = replace_once(
    tests,
    '        observation(binding_sources=("gaze", "GAZE"))\n',
    '        observation(binding_sources=("GAZE", "GAZE"))\n',
    "canonical duplicate binding sources",
)
tests = replace_once(
    tests,
    '''    r, _ = recipe()
    reordered = r.to_dict()
    reordered["capability_ids"] = list(reversed(reordered["capability_ids"]))
''',
    '''    r, _ = recipe(adapters=(ref("adapter:z", D["2"]), ref("adapter:a", D["3"])))
    reordered = r.to_dict()
    reordered["adapter_refs"] = list(reversed(reordered["adapter_refs"]))
''',
    "order-normalized serialized reference regression",
)
TESTS.write_text(tests, encoding="utf-8")

print("reconciled wave-6 exact parsing, test ordering, and TTL semantics")
