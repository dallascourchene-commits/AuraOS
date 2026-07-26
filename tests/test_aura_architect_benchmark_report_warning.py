from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def test_architect_benchmark_report_compiles_with_syntax_warnings_as_errors() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-W",
            "error::SyntaxWarning",
            "-m",
            "py_compile",
            str(repo_root / "aura_architect_benchmark_report.py"),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
