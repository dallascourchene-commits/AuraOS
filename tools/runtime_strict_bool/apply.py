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
        '''def _validate_loopback_url(value: Any, label: str) -> str:
''',
        '''def _strict_bool(value: Any, label: str, *, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise RuntimeHarnessError(f"{label} must be a boolean")
    return value


def _validate_loopback_url(value: Any, label: str) -> str:
''',
        "strict boolean parser",
    )
    replace_once(
        harness,
        '''            "create_venv": bool(environment.get("create_venv", True)),
''',
        '''            "create_venv": _strict_bool(
                environment.get("create_venv"),
                "environment.create_venv",
                default=True,
            ),
''',
        "create_venv strict parsing",
    )

    tests = Path("tests/test_aura_runtime_refactor_harness.py")
    marker = '''def test_runtime_profile_starts_probes_verifies_and_stops(
'''
    addition = '''@pytest.mark.parametrize("value", ["false", "true", 0, 1, [], {}])
def test_profile_rejects_non_boolean_create_venv(tmp_path: Path, value: object) -> None:
    _write_fixture(tmp_path)
    profile = _write_profile(tmp_path, _free_port())
    payload = json.loads(profile.read_text(encoding="utf-8"))
    payload["environment"]["create_venv"] = value
    profile.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        RuntimeHarnessError,
        match=r"environment\.create_venv must be a boolean",
    ):
        load_runtime_profile(tmp_path, profile.name)


def test_profile_defaults_create_venv_only_when_absent(tmp_path: Path) -> None:
    _write_fixture(tmp_path)
    profile = _write_profile(tmp_path, _free_port())
    payload = json.loads(profile.read_text(encoding="utf-8"))
    del payload["environment"]["create_venv"]
    profile.write_text(json.dumps(payload), encoding="utf-8")
    assert load_runtime_profile(tmp_path, profile.name)["environment"]["create_venv"] is True


'''
    replace_once(tests, marker, addition + marker, "strict boolean regressions")


if __name__ == "__main__":
    main()
