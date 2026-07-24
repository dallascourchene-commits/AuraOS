from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"expected one repair anchor for {label}, found {text.count(old)}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    harness = Path("scripts/aura_runtime_refactor_harness.py")
    replace_once(
        harness,
        '''def _strict_bool(value: Any, label: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise RuntimeHarnessError(f"{label} must be a boolean")
    return value
''',
        '''_MISSING = object()


def _strict_bool(value: Any, label: str, *, default: bool) -> bool:
    if value is _MISSING:
        return default
    if not isinstance(value, bool):
        raise RuntimeHarnessError(f"{label} must be a boolean")
    return value
''',
        "published strict boolean parser",
    )
    replace_once(
        harness,
        '''                environment.get("create_venv"),
''',
        '''                environment.get("create_venv", _MISSING),
''',
        "create_venv absent sentinel",
    )

    tests = Path("tests/test_aura_runtime_refactor_harness.py")
    replace_once(
        tests,
        '''@pytest.mark.parametrize("value", ["false", "true", 0, 1, [], {}])
''',
        '''@pytest.mark.parametrize("value", [None, "false", "true", 0, 1, [], {}])
''',
        "explicit null regression",
    )


if __name__ == "__main__":
    main()
