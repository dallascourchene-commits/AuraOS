"""JUnit-counted adapter for the standard isolated refactor patch evaluator.

V1 established fixed-command execution and quality records. V2 replaces its
command-level pytest result with exact test-case counts while retaining the same
EvaluationSpec and RefactorOutputRecord contracts.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path
from typing import Any, Sequence
import xml.etree.ElementTree as ET

import aura_refactor_patch_evaluator as base
from aura_refactor_output_record import FAIL, NOT_MEASURED, PASS, gate

EvaluationSpec = base.EvaluationSpec


def _report_name(paths: Sequence[str]) -> str:
    body = "|".join(paths)
    return hashlib.blake2b(body.encode("utf-8"), digest_size=8).hexdigest() + ".xml"


def _pytest_group(
    paths: Sequence[str],
    workspace: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    if not paths:
        return gate(NOT_MEASURED, reason="no_test_paths_declared")
    report_dir = workspace / ".aura_test_reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / _report_name(paths)
    relative_report = report_path.relative_to(workspace).as_posix()
    result = base._run(  # noqa: SLF001 - deliberate fixed-command adapter
        (
            "python",
            "-m",
            "pytest",
            "-q",
            *paths,
            f"--junitxml={relative_report}",
        ),
        workspace,
        timeout_seconds,
    )
    counts = {
        "tests": 0,
        "passed": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    failing_tests: list[str] = []
    report_digest = ""
    parse_error = ""
    if report_path.is_file():
        raw = report_path.read_bytes()
        report_digest = hashlib.blake2b(raw, digest_size=16).hexdigest()
        try:
            root = ET.fromstring(raw)
            suites = [root] if root.tag == "testsuite" else list(root.findall(".//testsuite"))
            if root.tag == "testsuites" and root.attrib.get("tests") is not None:
                counts["tests"] = int(float(root.attrib.get("tests", 0)))
                counts["failures"] = int(float(root.attrib.get("failures", 0)))
                counts["errors"] = int(float(root.attrib.get("errors", 0)))
                counts["skipped"] = int(float(root.attrib.get("skipped", 0)))
            else:
                counts["tests"] = sum(int(float(item.attrib.get("tests", 0))) for item in suites)
                counts["failures"] = sum(int(float(item.attrib.get("failures", 0))) for item in suites)
                counts["errors"] = sum(int(float(item.attrib.get("errors", 0))) for item in suites)
                counts["skipped"] = sum(int(float(item.attrib.get("skipped", 0))) for item in suites)
            counts["passed"] = max(
                0,
                counts["tests"]
                - counts["failures"]
                - counts["errors"]
                - counts["skipped"],
            )
            for case in root.findall(".//testcase"):
                if case.find("failure") is None and case.find("error") is None:
                    continue
                classname = str(case.attrib.get("classname") or "")
                name = str(case.attrib.get("name") or "")
                failing_tests.append(f"{classname}::{name}".strip(":"))
        except (ET.ParseError, TypeError, ValueError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"
    else:
        parse_error = "junit_report_missing"

    status = (
        PASS
        if result.status == PASS
        and counts["tests"] > 0
        and counts["failures"] == 0
        and counts["errors"] == 0
        else FAIL
    )
    return gate(
        status,
        passed=counts["passed"],
        total=counts["tests"],
        evidence={
            "command": asdict(result),
            "junit": counts,
            "junit_report_digest": report_digest,
            "failing_tests": failing_tests,
            "parse_error": parse_error,
        },
    )


base._pytest_group = _pytest_group  # noqa: SLF001 - install V2 measurement adapter


def evaluate(spec: EvaluationSpec):
    return base.evaluate(spec)


def main(argv: list[str] | None = None) -> int:
    base._pytest_group = _pytest_group  # noqa: SLF001
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
