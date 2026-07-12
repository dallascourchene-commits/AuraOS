"""Built-in-only isolated trial runner for Phase C3 route-capsule variants."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable

from aura_arena_experience import OutcomeVector
from aura_capsule_trial_types import (
    CapsuleTrialCase,
    CapsuleVariant,
    canonical_digest,
    repository_relative_path,
)
from aura_ephemeral_sandbox import (
    destroy_sandbox,
    enforce_resource_budget,
    prepare_sandbox,
    revoke_capabilities,
    verify_dissolution,
)

CAPSULE_TRIAL_RUNNER_VERSION = "AURA_CAPSULE_TRIAL_RUNNER_V1"
PATCH_AUTHORITY = "exact_source_spans_and_hashes_only"
VSA_PATCH_AUTHORITY = False
TRIAL_EXECUTION_LEASE = "trial:isolated_capsule"

Executor = Callable[[CapsuleTrialCase, CapsuleVariant, list[dict[str, Any]], Path], dict[str, Any]]
_BUILTIN_EXECUTORS: dict[str, Executor] = {}


def register_builtin_trial_executor(name: str, executor: Executor) -> None:
    if not str(name).strip() or not callable(executor):
        raise ValueError("built-in trial executor requires a name and callable")
    _BUILTIN_EXECUTORS[str(name)] = executor


def run_capsule_trial(
    *,
    run_id: str,
    variant: CapsuleVariant,
    case: CapsuleTrialCase,
    executor_id: str,
    repetition: int,
    repo_root: str | Path = ".",
    trials_enabled: bool = False,
    lease_capabilities: Iterable[str] = (),
) -> dict[str, Any]:
    """Run one deterministic built-in trial and always dissolve its temporary sandbox."""
    lease = {str(item) for item in lease_capabilities if str(item)}
    required = {TRIAL_EXECUTION_LEASE, *variant.requested_capabilities}
    if not trials_enabled:
        return _denial("c3_trials_feature_disabled", run_id=run_id)
    missing = sorted(required - lease)
    if missing:
        return _denial("c3_trial_lease_missing_capability", run_id=run_id, missing=missing)
    executor = _BUILTIN_EXECUTORS.get(str(executor_id))
    if executor is None:
        return _denial("trial_executor_not_allowlisted", run_id=run_id)

    trial_identity = {
        "run_id": run_id,
        "variant_id": variant.variant_id,
        "case_id": case.case_id,
        "dataset": case.dataset,
        "repetition": int(repetition),
    }
    trial_id = f"CTRY-{canonical_digest(trial_identity)[:24]}"
    try:
        context = _materialize_case_context(repo_root, case, variant)
    except Exception as exc:  # noqa: BLE001
        return _denial(
            f"trial_context_materialization_failed:{type(exc).__name__}",
            run_id=run_id,
            trial_id=trial_id,
        )

    budget = dict(variant.execution_budget)
    resource_budget = {
        "wall_time_ms": max(1, int(float(budget.get("wall_seconds") or 0) * 1000)),
        "output_bytes": max(1, int(float(budget.get("output_tokens") or 0) * 4)),
        "tool_calls": max(0, int(budget.get("tool_calls") or 0)),
    }
    prepared = prepare_sandbox(
        {
            "organ_id": trial_id,
            "resource_budget": resource_budget,
        },
        repo_root=str(Path(repo_root).resolve()),
    )
    if not prepared.get("ok"):
        return _denial("trial_sandbox_preparation_failed", run_id=run_id, trial_id=trial_id)

    temp_dir = Path(str(prepared.get("temp_dir") or ""))
    started = time.perf_counter()
    output: dict[str, Any]
    executor_error = ""
    try:
        output = dict(executor(case, variant, context, temp_dir) or {})
    except Exception as exc:  # noqa: BLE001
        output = {"ok": False, "reason": f"executor_failed:{type(exc).__name__}"}
        executor_error = type(exc).__name__
    elapsed = max(0.0, time.perf_counter() - started)

    stable_output = _stable_output(output)
    output_json = json.dumps(stable_output, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    usage = {
        "input_tokens": _token_estimate(case.objective) + _token_estimate(context),
        "output_tokens": _token_estimate(stable_output),
        "tool_calls": 1,
        "model_calls": 0,
        "wall_seconds": round(elapsed, 9),
        "output_bytes": len(output_json.encode("utf-8")),
    }
    resource_check = enforce_resource_budget(
        prepared.get("receipt") or {},
        elapsed_ms=elapsed * 1000.0,
        output_bytes=usage["output_bytes"],
        tool_calls=usage["tool_calls"],
    )
    exceeded = sorted(set(resource_check.get("exceeded") or []) | set(_budget_exceeded(budget, usage)))

    revoked = revoke_capabilities(trial_id)
    destroyed = destroy_sandbox(str(temp_dir))
    dissolution = verify_dissolution(str(temp_dir), bool(revoked.get("ok")))
    outcome = _outcome_vector(
        case=case,
        output=stable_output,
        usage=usage,
        budget=budget,
        budget_ok=not exceeded,
        dissolution_ok=bool(dissolution.get("ok")),
    )
    completed = bool(
        stable_output.get("ok")
        and not exceeded
        and dissolution.get("ok")
        and not executor_error
    )
    return {
        "ok": completed,
        "version": CAPSULE_TRIAL_RUNNER_VERSION,
        "trial_id": trial_id,
        "run_id": run_id,
        "variant_id": variant.variant_id,
        "case_id": case.case_id,
        "case_digest": case.digest(),
        "dataset": case.dataset,
        "repetition": int(repetition),
        "executor_id": executor_id,
        "executor_allowlisted": True,
        "arbitrary_code_executed": False,
        "native_fallback_used": False,
        "sandbox": {
            "mode": (prepared.get("receipt") or {}).get("sandbox_mode", ""),
            "wasmtime_available": bool(prepared.get("wasmtime_available")),
            "temporary_directory_created": bool(temp_dir),
            "temporary_directory_removed": bool(destroyed.get("temp_dir_removed")),
            "capabilities_revoked": bool(revoked.get("ok")),
            "dissolution_verified": bool(dissolution.get("ok")),
        },
        "output": stable_output,
        "output_digest": hashlib.blake2b(output_json.encode("utf-8"), digest_size=20).hexdigest(),
        "actual_context_digest": canonical_digest(context),
        "actual_context_items": context,
        "usage": usage,
        "budget_requested": budget,
        "budget_exceeded": exceeded,
        "outcome_vector": outcome.to_dict(),
        "outcome_projection": outcome.proposal_projection(),
        "terminal_class": "COMPLETED" if completed else "FAILED",
        "required_lease_capabilities": sorted(required),
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_capsule_activation": False,
        "automatic_code_installation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


def aggregate_trial_observations(observations: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = [dict(item) for item in observations]
    scores = [
        float((row.get("outcome_projection") or {}).get("score"))
        for row in rows
        if (row.get("outcome_projection") or {}).get("score") is not None
    ]
    groups: dict[str, set[str]] = {}
    for row in rows:
        groups.setdefault(str(row.get("case_id") or ""), set()).add(str(row.get("output_digest") or ""))
    reproducible = bool(groups) and all(len({item for item in digests if item}) == 1 for digests in groups.values())
    completed = sum(1 for row in rows if row.get("ok") is True)
    total_tokens = sum(float((row.get("usage") or {}).get("input_tokens") or 0.0) + float((row.get("usage") or {}).get("output_tokens") or 0.0) for row in rows)
    wall_seconds = sum(float((row.get("usage") or {}).get("wall_seconds") or 0.0) for row in rows)
    return {
        "observation_count": len(rows),
        "completed_count": completed,
        "all_completed": bool(rows) and completed == len(rows),
        "score_mean": round(sum(scores) / len(scores), 6) if scores else None,
        "score_min": round(min(scores), 6) if scores else None,
        "reproducible": reproducible,
        "case_output_digest_sets": {key: sorted(values) for key, values in sorted(groups.items())},
        "total_tokens": round(total_tokens, 6),
        "wall_seconds": round(wall_seconds, 9),
        "tool_calls": sum(int((row.get("usage") or {}).get("tool_calls") or 0) for row in rows),
        "model_calls": sum(int((row.get("usage") or {}).get("model_calls") or 0) for row in rows),
        "budget_failure_count": sum(1 for row in rows if row.get("budget_exceeded")),
        "dissolution_failure_count": sum(1 for row in rows if not (row.get("sandbox") or {}).get("dissolution_verified")),
        "proposal_only": True,
    }


def _materialize_case_context(
    repo_root: str | Path,
    case: CapsuleTrialCase,
    variant: CapsuleVariant,
) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    maximum_files = int(variant.data_aperture.get("maximum_files") or 0)
    maximum_symbols = int(variant.data_aperture.get("maximum_symbols") or 0)
    maximum_lines = int(variant.data_aperture.get("maximum_lines") or 0)
    if min(maximum_files, maximum_symbols, maximum_lines) <= 0:
        raise ValueError("variant data aperture must remain strictly bounded")

    objective_tokens = _tokens(case.objective)
    materialized: list[dict[str, Any]] = []
    for raw in case.context_items:
        relative = repository_relative_path(str(raw.get("path") or ""))
        path = root.joinpath(*Path(relative).parts)
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(relative)
        resolved = path.resolve()
        resolved.relative_to(root)
        content = path.read_bytes()
        symbols = [str(item) for item in raw.get("symbols") or () if str(item)]
        tests = [repository_relative_path(str(item)) for item in raw.get("tests") or () if str(item)]
        keywords = [str(item) for item in raw.get("keywords") or () if str(item)]
        haystack = " ".join((relative, *symbols, *tests, *keywords)).lower()
        overlap = len(objective_tokens & _tokens(haystack))
        line_count = max(1, content.count(b"\n") + 1)
        materialized.append({
            "path": relative,
            "symbols": symbols,
            "tests": tests,
            "keywords": keywords,
            "source_hash": hashlib.blake2b(content, digest_size=20).hexdigest(),
            "line_count": line_count,
            "semantic_overlap": overlap,
        })
    materialized.sort(key=lambda item: (-int(item["semantic_overlap"]), str(item["path"])))
    selected: list[dict[str, Any]] = []
    symbols_used = 0
    lines_used = 0
    for item in materialized:
        if len(selected) >= maximum_files or lines_used >= maximum_lines:
            break
        remaining_symbols = maximum_symbols - symbols_used
        if remaining_symbols <= 0:
            break
        bounded = dict(item)
        bounded["symbols"] = list(item["symbols"][:remaining_symbols])
        bounded["line_count"] = min(int(item["line_count"]), maximum_lines - lines_used)
        bounded["line_start"] = 1
        bounded["line_end"] = bounded["line_count"]
        selected.append(bounded)
        symbols_used += len(bounded["symbols"])
        lines_used += int(bounded["line_count"])
    if not selected:
        raise ValueError("bounded context materialized no source items")
    return selected


def _execute_coding_localization_fixture(
    case: CapsuleTrialCase,
    variant: CapsuleVariant,
    context: list[dict[str, Any]],
    temp_dir: Path,
) -> dict[str, Any]:
    files = [str(item["path"]) for item in context]
    symbols = [str(symbol) for item in context for symbol in item.get("symbols") or ()]
    tests = list(dict.fromkeys(str(test) for item in context for test in item.get("tests") or ()))
    source_hashes = [
        {"path": str(item["path"]), "source_hash": str(item["source_hash"])}
        for item in context
    ]
    spans = [
        {
            "path": str(item["path"]),
            "line_start": int(item.get("line_start") or 1),
            "line_end": int(item.get("line_end") or item.get("line_count") or 1),
            "source_hash": str(item["source_hash"]),
        }
        for item in context
    ]
    output = {
        "ok": True,
        "localized_files": files,
        "localized_symbols": symbols,
        "affected_tests": tests,
        "source_hashes": source_hashes,
        "exact_source_spans": spans,
        "variant_id": variant.variant_id,
        "case_id": case.case_id,
    }
    (temp_dir / "trial_result.json").write_text(
        json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=True),
        encoding="utf-8",
    )
    return output


def _outcome_vector(
    *,
    case: CapsuleTrialCase,
    output: dict[str, Any],
    usage: dict[str, Any],
    budget: dict[str, Any],
    budget_ok: bool,
    dissolution_ok: bool,
) -> OutcomeVector:
    files = {str(item) for item in output.get("localized_files") or ()}
    symbols = {str(item) for item in output.get("localized_symbols") or ()}
    tests = {str(item) for item in output.get("affected_tests") or ()}
    expected_files = set(case.expected_files)
    expected_symbols = set(case.expected_symbols)
    expected_tests = set(case.expected_tests)
    file_score = _f1(files, expected_files)
    symbol_score = _f1(symbols, expected_symbols) if expected_symbols else file_score
    test_score = _f1(tests, expected_tests) if expected_tests else 1.0
    hashes = {
        str(item.get("path") or "")
        for item in output.get("source_hashes") or ()
        if isinstance(item, dict) and item.get("source_hash")
    }
    evidence = len(files & hashes) / len(files) if files else 0.0
    requested_tokens = max(1.0, float(budget.get("input_tokens") or 0) + float(budget.get("output_tokens") or 0))
    consumed_tokens = float(usage.get("input_tokens") or 0) + float(usage.get("output_tokens") or 0)
    cost_efficiency = max(0.0, min(1.0, 1.0 - consumed_tokens / requested_tokens))
    wall_limit = max(0.001, float(budget.get("wall_seconds") or 0.001))
    latency_efficiency = max(0.0, min(1.0, 1.0 - float(usage.get("wall_seconds") or 0.0) / wall_limit))
    completed = bool(output.get("ok") and budget_ok and dissolution_ok)
    return OutcomeVector(
        terminal_class="COMPLETED" if completed else "FAILED",
        task_progress=file_score,
        evidence_quality=evidence,
        verification_quality=test_score,
        safety_quality=1.0 if budget_ok and dissolution_ok else 0.0,
        human_alignment=round((file_score + symbol_score) / 2.0, 6),
        cost_efficiency=cost_efficiency,
        latency_efficiency=latency_efficiency,
        abstention_quality=1.0 if completed else 0.0,
        recovery_quality=1.0 if dissolution_ok else 0.0,
        measurement_classes={
            "task_progress": "EXPECTED_FILE_F1",
            "evidence_quality": "EXACT_SOURCE_HASH_COVERAGE",
            "verification_quality": "AFFECTED_TEST_F1",
            "safety_quality": "BUDGET_AND_DISSOLUTION",
        },
        labels=(case.dataset, "C3_CAPSULE_TRIAL"),
    )


def _stable_output(output: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "ok",
        "reason",
        "localized_files",
        "localized_symbols",
        "affected_tests",
        "source_hashes",
        "exact_source_spans",
        "variant_id",
        "case_id",
    }
    return {key: output[key] for key in sorted(output) if key in allowed}


def _budget_exceeded(budget: dict[str, Any], usage: dict[str, Any]) -> list[str]:
    exceeded: list[str] = []
    for key in ("input_tokens", "output_tokens", "tool_calls", "model_calls", "wall_seconds"):
        if key in budget and float(usage.get(key) or 0.0) > float(budget.get(key) or 0.0):
            exceeded.append(key)
    return exceeded


def _f1(actual: set[str], expected: set[str]) -> float:
    if not expected:
        return 1.0 if not actual else 0.5
    if not actual:
        return 0.0
    intersection = len(actual & expected)
    precision = intersection / len(actual)
    recall = intersection / len(expected)
    return round(2 * precision * recall / (precision + recall), 6) if precision + recall else 0.0


def _tokens(value: Any) -> set[str]:
    return {item for item in re.findall(r"[a-z0-9_]+", str(value).lower()) if len(item) > 1}


def _token_estimate(value: Any) -> float:
    if not isinstance(value, str):
        value = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return round(max(0.0, len(value) / 4.0), 6)


def _denial(
    reason: str,
    *,
    run_id: str = "",
    trial_id: str = "",
    missing: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "status": "DENIED",
        "reason": reason,
        "run_id": run_id,
        "trial_id": trial_id,
        "missing": list(missing or []),
        "fail_closed": True,
        "arbitrary_code_executed": False,
        "native_fallback_used": False,
        "patch_authority": PATCH_AUTHORITY,
        "vsa_patch_authority": VSA_PATCH_AUTHORITY,
        "automatic_capsule_activation": False,
        "automatic_code_installation": False,
        "automatic_commit": False,
        "automatic_push": False,
        "automatic_merge": False,
    }


register_builtin_trial_executor(
    "coding_localization_fixture_v1",
    _execute_coding_localization_fixture,
)
