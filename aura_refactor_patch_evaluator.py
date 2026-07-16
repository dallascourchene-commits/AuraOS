"""Evaluate generated refactor patches in an isolated workspace.

Only fixed tool entrypoints are used: git apply, Python compileall, pytest, ruff,
mypy, and bandit. Test inputs are validated repository-relative paths. The
source repository is never modified.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from typing import Any, Iterable, Sequence

from aura_refactor_output_record import (
    DEFAULT_REQUIRED_GATES,
    FAIL,
    NOT_APPLICABLE,
    NOT_MEASURED,
    PASS,
    UNAVAILABLE,
    RefactorOutputRecord,
    finalize_record,
    gate,
    write_record,
)


@dataclass(frozen=True)
class EvaluationSpec:
    benchmark_id: str
    run_id: str
    case_id: str
    arm_id: str
    method: str
    objective: str
    fixture_root: Path
    patch_file: Path
    allowed_files: tuple[str, ...]
    visible_test_paths: tuple[str, ...]
    hidden_test_paths: tuple[str, ...]
    regression_test_paths: tuple[str, ...]
    protected_api_files: tuple[str, ...] = ()
    required_gates: tuple[str, ...] = DEFAULT_REQUIRED_GATES
    run_ruff: bool = False
    run_mypy: bool = False
    run_bandit: bool = False
    model: str = ""
    provider: str = ""
    repository_commit_sha: str = ""
    prompt_digest: str = ""
    response_digest: str = ""
    token_usage: dict[str, Any] = field(default_factory=dict)
    workload: dict[str, Any] = field(default_factory=dict)
    supplemental_metrics: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 60


@dataclass(frozen=True)
class CommandResult:
    status: str
    command: list[str]
    exit_code: int | None
    duration_ms: float
    stdout_digest: str
    stderr_digest: str
    stdout_excerpt: str
    stderr_excerpt: str


_COMPLEXITY_TYPES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.BoolOp,
    ast.IfExp,
    ast.comprehension,
    ast.Match,
)


def _digest(text: str) -> str:
    return hashlib.blake2b(text.encode("utf-8", errors="replace"), digest_size=16).hexdigest()


def _excerpt(text: str, limit: int = 800) -> str:
    value = text.strip()
    return value if len(value) <= limit else value[:limit] + "\n...[truncated]"


def _run(command: Sequence[str], cwd: Path, timeout_seconds: int) -> CommandResult:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            list(command),
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        return CommandResult(
            status=PASS if proc.returncode == 0 else FAIL,
            command=list(command),
            exit_code=proc.returncode,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            stdout_digest=_digest(stdout),
            stderr_digest=_digest(stderr),
            stdout_excerpt=_excerpt(stdout),
            stderr_excerpt=_excerpt(stderr),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = str(exc.stdout or "")
        stderr = str(exc.stderr or "") + "\nTIMEOUT"
        return CommandResult(
            status=FAIL,
            command=list(command),
            exit_code=None,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            stdout_digest=_digest(stdout),
            stderr_digest=_digest(stderr),
            stdout_excerpt=_excerpt(stdout),
            stderr_excerpt=_excerpt(stderr),
        )
    except OSError as exc:
        message = f"{type(exc).__name__}: {exc}"
        return CommandResult(
            status=UNAVAILABLE,
            command=list(command),
            exit_code=None,
            duration_ms=round((time.perf_counter() - started) * 1000.0, 3),
            stdout_digest=_digest(""),
            stderr_digest=_digest(message),
            stdout_excerpt="",
            stderr_excerpt=message,
        )


def _safe_relpaths(values: Iterable[str], root: Path) -> tuple[str, ...]:
    rows: list[str] = []
    resolved_root = root.resolve()
    for raw in values:
        value = str(raw).replace("\\", "/").strip()
        candidate = Path(value)
        if not value or value.startswith("-") or candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"unsafe repository-relative path: {raw!r}")
        resolved = (resolved_root / candidate).resolve()
        resolved.relative_to(resolved_root)
        rows.append(candidate.as_posix())
    return tuple(rows)


def _pytest_group(paths: Sequence[str], workspace: Path, timeout_seconds: int) -> dict[str, Any]:
    if not paths:
        return gate(NOT_MEASURED, reason="no_test_paths_declared")
    result = _run(("python", "-m", "pytest", "-q", *paths), workspace, timeout_seconds)
    return gate(
        result.status,
        passed=1 if result.status == PASS else 0,
        total=1,
        evidence=asdict(result),
    )


def _fixed_tool(module: str, arguments: Sequence[str], workspace: Path, timeout_seconds: int) -> dict[str, Any]:
    result = _run(("python", "-m", module, *arguments), workspace, timeout_seconds)
    return gate(result.status, passed=1 if result.status == PASS else 0, total=1, evidence=asdict(result))


def _patch_stats(text: str) -> dict[str, Any]:
    files: list[str] = []
    additions = 0
    deletions = 0
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            files.append(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    touched = sorted(set(files))
    return {
        "files_touched": touched,
        "file_count": len(touched),
        "lines_added": additions,
        "lines_deleted": deletions,
        "total_changed_lines": additions + deletions,
        "test_files_touched": [item for item in touched if "test" in Path(item).name.lower()],
    }


def _signature(arguments: ast.arguments) -> str:
    parts = [item.arg for item in [*arguments.posonlyargs, *arguments.args]]
    if arguments.vararg:
        parts.append("*" + arguments.vararg.arg)
    parts.extend(item.arg for item in arguments.kwonlyargs)
    if arguments.kwarg:
        parts.append("**" + arguments.kwarg.arg)
    return "(" + ",".join(parts) + ")"


def _api_snapshot(root: Path, files: Iterable[str]) -> dict[str, Any]:
    symbols: dict[str, list[str]] = {}
    for rel in sorted(set(files)):
        path = root / rel
        if not path.is_file() or path.suffix != ".py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"), filename=rel)
        except SyntaxError:
            symbols[rel] = ["<SYNTAX_ERROR>"]
            continue
        rows: list[str] = []
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                rows.append(f"function:{node.name}{_signature(node.args)}")
            elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                rows.append(f"class:{node.name}")
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and not child.name.startswith("_"):
                        rows.append(f"method:{node.name}.{child.name}{_signature(child.args)}")
        symbols[rel] = sorted(rows)
    canonical = json.dumps(symbols, sort_keys=True, separators=(",", ":"))
    return {"symbols": symbols, "digest": _digest(canonical)}


def _complexity(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in {".git", "__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end = int(getattr(node, "end_lineno", node.lineno))
            rows.append(
                {
                    "complexity": 1 + sum(isinstance(child, _COMPLEXITY_TYPES) for child in ast.walk(node)),
                    "lines": max(1, end - int(node.lineno) + 1),
                }
            )
    return {
        "function_count": len(rows),
        "max_complexity": max((item["complexity"] for item in rows), default=0),
        "mean_complexity": round(sum(item["complexity"] for item in rows) / max(1, len(rows)), 4),
        "max_function_lines": max((item["lines"] for item in rows), default=0),
        "functions_over_complexity_10": sum(item["complexity"] > 10 for item in rows),
        "functions_over_60_lines": sum(item["lines"] > 60 for item in rows),
    }


def _maintainability(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "max_complexity",
        "mean_complexity",
        "max_function_lines",
        "functions_over_complexity_10",
        "functions_over_60_lines",
    )
    delta = {key: round(float(after.get(key, 0)) - float(before.get(key, 0)), 4) for key in keys}
    penalty = 0.0
    penalty += max(0.0, delta["max_complexity"]) * 0.04
    penalty += max(0.0, delta["mean_complexity"]) * 0.08
    penalty += max(0.0, delta["functions_over_complexity_10"]) * 0.10
    penalty += max(0.0, delta["functions_over_60_lines"]) * 0.08
    score = round(max(0.0, min(1.0, 1.0 - penalty)), 4)
    return {"before": before, "after": after, "delta": delta, "score": score}


def evaluate(spec: EvaluationSpec) -> RefactorOutputRecord:
    fixture = spec.fixture_root.resolve()
    if not fixture.is_dir():
        raise FileNotFoundError(fixture)
    patch_text = spec.patch_file.read_text(encoding="utf-8")
    stats = _patch_stats(patch_text)
    allowed = _safe_relpaths(spec.allowed_files, fixture)
    visible = _safe_relpaths(spec.visible_test_paths, fixture)
    hidden = _safe_relpaths(spec.hidden_test_paths, fixture)
    regression = _safe_relpaths(spec.regression_test_paths, fixture)
    protected = _safe_relpaths(spec.protected_api_files, fixture)

    record = RefactorOutputRecord(
        benchmark_id=spec.benchmark_id,
        run_id=spec.run_id,
        case_id=spec.case_id,
        arm_id=spec.arm_id,
        method=spec.method,
        repository_commit_sha=spec.repository_commit_sha,
        objective=spec.objective,
        model=spec.model,
        provider=spec.provider,
        prompt_digest=spec.prompt_digest,
        response_digest=spec.response_digest,
        patch_digest=_digest(patch_text),
        token_usage=dict(spec.token_usage),
        workload=dict(spec.workload),
        patch_stats=stats,
    )
    record.workload.setdefault("isolated_workspace", True)
    record.workload.setdefault("hidden_tests_prompt_exposed", False)

    with tempfile.TemporaryDirectory(prefix="aura-quality-") as temp:
        workspace = Path(temp) / "workspace"
        shutil.copytree(fixture, workspace)
        patch_path = Path(temp) / "candidate.patch"
        patch_path.write_text(patch_text, encoding="utf-8")
        before_api = _api_snapshot(workspace, protected)
        before_complexity = _complexity(workspace)

        check = _run(("git", "apply", "--check", str(patch_path)), workspace, spec.timeout_seconds)
        apply_result = _run(("git", "apply", str(patch_path)), workspace, spec.timeout_seconds) if check.status == PASS else check
        apply_ok = check.status == PASS and apply_result.status == PASS
        record.gates["patch_apply"] = gate(
            PASS if apply_ok else FAIL,
            evidence={"check": asdict(check), "apply": asdict(apply_result)},
        )

        out_of_scope = sorted(set(stats["files_touched"]) - set(allowed)) if allowed else sorted(stats["files_touched"])
        record.gates["scope"] = gate(
            PASS if allowed and not out_of_scope else NOT_MEASURED if not allowed else FAIL,
            evidence={"allowed_files": sorted(allowed), "out_of_scope_files": out_of_scope},
        )

        if apply_ok:
            compile_result = _run(("python", "-m", "compileall", "-q", "."), workspace, spec.timeout_seconds)
            record.gates["compile"] = gate(compile_result.status, evidence=asdict(compile_result))
            record.gates["visible_tests"] = _pytest_group(visible, workspace, spec.timeout_seconds)
            record.gates["hidden_tests"] = _pytest_group(hidden, workspace, spec.timeout_seconds)
            record.gates["regression_tests"] = _pytest_group(regression, workspace, spec.timeout_seconds)

            after_api = _api_snapshot(workspace, protected)
            record.gates["api_compatibility"] = (
                gate(PASS if before_api["digest"] == after_api["digest"] else FAIL, evidence={"before": before_api, "after": after_api})
                if protected
                else gate(NOT_APPLICABLE, reason="no_protected_api_files")
            )

            changed_python = [item for item in stats["files_touched"] if item.endswith(".py")]
            security_parts: list[dict[str, Any]] = []
            if spec.run_bandit and changed_python:
                security_parts.append(_fixed_tool("bandit", ("-q", *changed_python), workspace, spec.timeout_seconds))
            record.gates["security"] = (
                gate(
                    PASS if all(item["status"] == PASS for item in security_parts) else FAIL,
                    passed=sum(item["status"] == PASS for item in security_parts),
                    total=len(security_parts),
                    evidence=security_parts,
                )
                if security_parts
                else gate(NOT_MEASURED, reason="security_tool_not_enabled")
            )

            static_parts: list[dict[str, Any]] = []
            if spec.run_ruff and changed_python:
                static_parts.append(_fixed_tool("ruff", ("check", *changed_python), workspace, spec.timeout_seconds))
            if spec.run_mypy and changed_python:
                static_parts.append(_fixed_tool("mypy", tuple(changed_python), workspace, spec.timeout_seconds))
            record.gates["static_analysis"] = (
                gate(
                    PASS if all(item["status"] == PASS for item in static_parts) else FAIL,
                    passed=sum(item["status"] == PASS for item in static_parts),
                    total=len(static_parts),
                    evidence=static_parts,
                )
                if static_parts
                else gate(NOT_MEASURED, reason="static_analysis_tools_not_enabled")
            )

            maintainability = _maintainability(before_complexity, _complexity(workspace))
            record.engineering_metrics["maintainability"] = maintainability
            record.gates["maintainability"] = gate(
                PASS if maintainability["score"] >= 0.75 else FAIL,
                evidence=maintainability,
            )
            record.gates["performance"] = gate(
                PASS if spec.supplemental_metrics.get("performance_passed") is True else FAIL if spec.supplemental_metrics.get("performance_passed") is False else NOT_MEASURED,
                evidence=spec.supplemental_metrics.get("performance"),
            )
            record.gates["portability"] = gate(
                PASS if spec.supplemental_metrics.get("portability_passed") is True else FAIL if spec.supplemental_metrics.get("portability_passed") is False else NOT_MEASURED,
                evidence=spec.supplemental_metrics.get("portability"),
            )
        else:
            for name in (
                "compile",
                "visible_tests",
                "hidden_tests",
                "regression_tests",
                "api_compatibility",
                "security",
                "maintainability",
                "static_analysis",
                "performance",
                "portability",
            ):
                record.gates[name] = gate(NOT_MEASURED, reason="patch_did_not_apply")

    record.engineering_metrics["supplemental"] = dict(spec.supplemental_metrics)
    record.limitations.extend(
        [
            "Every measured component is retained even when a required gate fails.",
            "The benchmark score treats missing measurements as zero for cross-run comparability; the observed score normalizes only measured components.",
            "A working patch can be WORKED_BUT_NOT_ACCEPTABLE when scope, compatibility, security, or another required gate fails.",
            "This evaluator maps evidence to industry standards but does not claim certification or conformance.",
        ]
    )
    return finalize_record(record, required_gates=spec.required_gates)


def _tuple_paths(payload: dict[str, Any], name: str) -> tuple[str, ...]:
    return tuple(str(item) for item in payload.get(name, []) or [])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a generated refactor patch")
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.spec.read_text(encoding="utf-8"))
    spec = EvaluationSpec(
        benchmark_id=str(payload["benchmark_id"]),
        run_id=str(payload["run_id"]),
        case_id=str(payload["case_id"]),
        arm_id=str(payload["arm_id"]),
        method=str(payload["method"]),
        objective=str(payload["objective"]),
        fixture_root=Path(payload["fixture_root"]),
        patch_file=Path(payload["patch_file"]),
        allowed_files=_tuple_paths(payload, "allowed_files"),
        visible_test_paths=_tuple_paths(payload, "visible_test_paths"),
        hidden_test_paths=_tuple_paths(payload, "hidden_test_paths"),
        regression_test_paths=_tuple_paths(payload, "regression_test_paths"),
        protected_api_files=_tuple_paths(payload, "protected_api_files"),
        required_gates=_tuple_paths(payload, "required_gates") or DEFAULT_REQUIRED_GATES,
        run_ruff=bool(payload.get("run_ruff", False)),
        run_mypy=bool(payload.get("run_mypy", False)),
        run_bandit=bool(payload.get("run_bandit", False)),
        model=str(payload.get("model", "")),
        provider=str(payload.get("provider", "")),
        repository_commit_sha=str(payload.get("repository_commit_sha", "")),
        prompt_digest=str(payload.get("prompt_digest", "")),
        response_digest=str(payload.get("response_digest", "")),
        token_usage=dict(payload.get("token_usage") or {}),
        workload=dict(payload.get("workload") or {}),
        supplemental_metrics=dict(payload.get("supplemental_metrics") or {}),
        timeout_seconds=int(payload.get("timeout_seconds", 60)),
    )
    record = evaluate(spec)
    write_record(args.output, record)
    print(json.dumps({
        "disposition": record.disposition,
        "working_status": record.working_status,
        "observed_quality_score": record.observed_quality_score,
        "benchmark_quality_score": record.benchmark_quality_score,
        "measurement_completeness_pct": record.measurement_completeness_pct,
        "failed_required_gates": record.failed_required_gates,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
