from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LEGACY_SCRIPT_TESTS = (
    "test_aura_functions.py",
    "test_synthesis_upgrades.py",
    "test_syntax_fixes.py",
)


def test_legacy_script_tests_do_not_exit_during_pytest_import() -> None:
    """Legacy script-style checks may exit as CLIs, never while pytest imports them."""
    for relative in LEGACY_SCRIPT_TESTS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert 'if __name__ == "__main__":' in text, relative
        assert "sys.exit(" not in text, relative


def test_legacy_script_failures_remain_assertive_under_pytest() -> None:
    for relative in LEGACY_SCRIPT_TESTS:
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "raise AssertionError(" in text, relative
