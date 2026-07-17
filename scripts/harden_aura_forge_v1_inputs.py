from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"missing source fragment in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_source() -> None:
    replace_once(
        "aura_forge.py",
        '''_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
''',
        '''_SECRET_SUFFIXES = ("_api_key", "_password", "_private_key", "_secret", "_credential")
_TOKEN_USAGE_KEYS = frozenset({
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "reasoning_tokens",
})
''',
    )
    replace_once(
        "aura_forge.py",
        '''    if isinstance(values, (str, bytes)):
        raise ValueError("expected an array of strings")
''',
        '''    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("expected an array of strings")
''',
    )
    replace_once(
        "aura_forge.py",
        '''            if lowered in _SECRET_KEYS or lowered.endswith(_SECRET_SUFFIXES):
                continue
''',
        '''            is_secret_token = (
                (lowered == "token" or lowered.endswith("_token"))
                and lowered not in _TOKEN_USAGE_KEYS
            )
            if (
                lowered in _SECRET_KEYS
                or lowered.endswith(_SECRET_SUFFIXES)
                or is_secret_token
            ):
                continue
''',
    )
    replace_once(
        "aura_forge.py",
        '''        return cls(
            objective=objective,
''',
        '''        metadata_value = raw.get("metadata")
        if metadata_value is None:
            metadata: dict[str, Any] = {}
        elif isinstance(metadata_value, Mapping):
            metadata = _sanitize(dict(metadata_value))
        else:
            raise ValueError("metadata must be an object")

        return cls(
            objective=objective,
''',
    )
    replace_once(
        "aura_forge.py",
        '''            required_gates=gates,
            metadata=_sanitize(dict(raw.get("metadata") or {})),
''',
        '''            required_gates=gates,
            metadata=metadata,
''',
    )


def patch_tests() -> None:
    replace_once(
        "tests/test_aura_forge.py",
        '''            "forge_contract_id": "spoofed-lineage",
        },
''',
        '''            "forge_contract_id": "spoofed-lineage",
            "github_token": "must-not-leak",
            "input_tokens": 321,
        },
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''        "forge_contract_id": "spoofed-lineage",
    }
''',
        '''        "forge_contract_id": "spoofed-lineage",
        "input_tokens": 321,
    }
''',
    )
    replace_once(
        "tests/test_aura_forge.py",
        '''def test_dot_prefixed_repository_paths_are_preserved() -> None:
''',
        '''def test_malformed_request_collections_fail_closed(tmp_path: Path) -> None:
    runtime, _bridge, _manager = build_runtime(tmp_path)

    criteria = runtime.prepare({"objective": "x", "acceptance_criteria": 7})
    metadata = runtime.prepare({"objective": "x", "metadata": ["not", "an", "object"]})

    assert criteria["ok"] is False
    assert criteria["stage"] == "REQUEST"
    assert criteria["error"] == "expected an array of strings"
    assert metadata["ok"] is False
    assert metadata["stage"] == "REQUEST"
    assert metadata["error"] == "metadata must be an object"


def test_dot_prefixed_repository_paths_are_preserved() -> None:
''',
    )


def main() -> None:
    patch_source()
    patch_tests()


if __name__ == "__main__":
    main()
