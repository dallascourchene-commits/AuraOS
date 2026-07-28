#!/usr/bin/env python3
"""Evidence-only V2 adapter over Aura's canonical V1 Runtime Harness."""
from __future__ import annotations

import argparse
from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any

try:
    from scripts import aura_runtime_refactor_harness as _v1
except ModuleNotFoundError:
    import aura_runtime_refactor_harness as _v1  # type: ignore[no-redef]

VERSION = "AURA_RUNTIME_BILATERAL_PROOF_V1"
PROFILE_VERSION = "AURA_RUNTIME_PROFILE_V2"
CURRENT_HEAD = "CURRENT_HEAD"
CURRENT_TREE = "CURRENT_TREE"
MAX_ASSERTIONS = 256
MAX_SCENARIOS = 64
MAX_TRACES = 64
MAX_PATHS = 256
MAX_GUARDRAILS = 256
MAX_JSON_BYTES = 8 * 1024 * 1024
GROUPS = (
    "positive_assertions",
    "negative_assertions",
    "preservation_assertions",
    "fault_injections",
)
FALSE_AUTHORITIES = (
    "automatic_fix",
    "automatic_commit",
    "automatic_push",
    "automatic_pull_request",
    "automatic_merge",
    "production_mutation",
    "professional_authority",
    "physical_work_authority",
    "learning_promotion",
)
SPECIAL_TRACES = frozenset(
    {
        "runtime_harness_receipt.json",
        "readiness.receipt.json",
        "server-output.receipt.json",
        "server-termination.receipt.json",
    }
)
DIGEST = re.compile(r"[0-9a-f]{64}")
GIT_SHA = re.compile(r"[0-9a-f]{40}")
IDENTIFIER = re.compile(r"[a-z0-9][a-z0-9._:-]{0,127}")
JSON_PATH = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")
OPERATORS = frozenset({"equals", "not_equals", "truthy", "falsy", "contains", "nonempty"})
AUTHORITY_CONTRACT = {
    **_v1.AUTHORITY_CONTRACT,
    "production_mutation": False,
    "professional_authority": False,
    "physical_work_authority": False,
    "learning_promotion": False,
    "bilateral_runtime_evidence_authority": False,
}


class BilateralRuntimeProfileError(_v1.RuntimeHarnessError):
    """A V2 contract or proof crossed a deterministic boundary."""


def _json_digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.blake2b(body.encode(), digest_size=32).hexdigest()


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise BilateralRuntimeProfileError(f"{label} is invalid")
    return value


def _hex(value: Any, label: str, pattern: re.Pattern[str] = DIGEST) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise BilateralRuntimeProfileError(f"{label} has invalid identity")
    return value


def _path(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise BilateralRuntimeProfileError(f"{label} is invalid")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts:
        raise BilateralRuntimeProfileError(f"{label} escapes its boundary")
    return pure.as_posix()


def _read_json(path: Path, label: str, maximum: int) -> Any:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > maximum:
        raise BilateralRuntimeProfileError(f"{label} is missing, unsafe, or oversized")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BilateralRuntimeProfileError(f"{label} is not canonical UTF-8 JSON: {exc}") from exc


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise BilateralRuntimeProfileError(f"repository identity is unavailable: {exc}") from exc
    if result.returncode:
        raise BilateralRuntimeProfileError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _repo_identity(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists():
        raise BilateralRuntimeProfileError("V2 runtime proof requires a Git checkout")
    status = [item for item in _git(root, "status", "--porcelain=v1", "-z").split("\x00") if item]
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "source_tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "branch": _git(root, "branch", "--show-current"),
        "status": status[:10_000],
        "clean": not status,
    }


def _contract(value: Any) -> dict[str, str]:
    keys = {
        "intent_digest",
        "semantic_ledger_digest",
        "confirmation_digest",
        "guardrail_set_digest",
        "intent_revision_id",
        "expected_repository_head",
        "expected_source_tree",
        "allowed_path_set_digest",
    }
    if not isinstance(value, Mapping) or set(value) != keys:
        raise BilateralRuntimeProfileError("intent_contract must be complete and exact")
    head = value["expected_repository_head"]
    tree = value["expected_source_tree"]
    if head != CURRENT_HEAD:
        _hex(head, "expected_repository_head", GIT_SHA)
    if tree != CURRENT_TREE:
        _hex(tree, "expected_source_tree", GIT_SHA)
    return {
        "intent_digest": _hex(value["intent_digest"], "intent_digest"),
        "semantic_ledger_digest": _hex(value["semantic_ledger_digest"], "semantic_ledger_digest"),
        "confirmation_digest": _hex(value["confirmation_digest"], "confirmation_digest"),
        "guardrail_set_digest": _hex(value["guardrail_set_digest"], "guardrail_set_digest"),
        "intent_revision_id": _id(value["intent_revision_id"], "intent_revision_id"),
        "expected_repository_head": head,
        "expected_source_tree": tree,
        "allowed_path_set_digest": _hex(value["allowed_path_set_digest"], "allowed_path_set_digest"),
    }


def _assertions(raw: Any, group: str, traces: set[str], seen: set[str]) -> tuple[dict[str, Any], ...]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_ASSERTIONS:
        raise BilateralRuntimeProfileError(f"{group} must be a non-empty bounded array")
    rows = []
    allowed = {"assertion_id", "artifact", "json_path", "operator", "expected"}
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) - allowed:
            raise BilateralRuntimeProfileError(f"{group}[{index}] is invalid")
        assertion_id = _id(item.get("assertion_id"), f"{group}[{index}].assertion_id")
        if assertion_id in seen:
            raise BilateralRuntimeProfileError(f"duplicate assertion_id: {assertion_id}")
        seen.add(assertion_id)
        artifact = _path(item.get("artifact"), f"{group}[{index}].artifact")
        json_path = item.get("json_path")
        operator = item.get("operator", "equals")
        if artifact not in traces:
            raise BilateralRuntimeProfileError(f"{group}[{index}].artifact is not an admitted trace")
        if not isinstance(json_path, str) or not JSON_PATH.fullmatch(json_path):
            raise BilateralRuntimeProfileError(f"{group}[{index}].json_path is invalid")
        if operator not in OPERATORS:
            raise BilateralRuntimeProfileError(f"{group}[{index}].operator is invalid")
        if operator in {"equals", "not_equals", "contains"} and "expected" not in item:
            raise BilateralRuntimeProfileError(f"{group}[{index}] requires expected")
        rows.append(
            {
                "assertion_id": assertion_id,
                "artifact": artifact,
                "json_path": json_path,
                "operator": operator,
                "expected": item.get("expected"),
                "group": group,
            }
        )
    return tuple(rows)


def load_runtime_profile_v2(root: Path, profile_path: str | Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    path = _v1._safe_repo_path(root, str(profile_path), "runtime profile")
    raw = _read_json(path, "runtime profile", _v1.MAX_PROFILE_BYTES)
    if not isinstance(raw, Mapping) or raw.get("version") != PROFILE_VERSION:
        raise BilateralRuntimeProfileError(f"runtime profile version must be {PROFILE_VERSION}")
    allowed_keys = {
        "version",
        "profile_id",
        "objective",
        "runtime_candidate_id",
        "base_profile",
        "intent_contract",
        "allowed_paths",
        "guardrail_ids",
        "scenarios",
        *GROUPS,
        "required_trace_artifacts",
        "repair_policy",
        "independent_verifier",
        "axiom_bindings",
    }
    if set(raw) - allowed_keys:
        raise BilateralRuntimeProfileError("runtime profile contains unknown top-level fields")

    profile_id = _id(raw.get("profile_id"), "profile_id")
    candidate_id = _id(raw.get("runtime_candidate_id"), "runtime_candidate_id")
    objective = raw.get("objective")
    if not isinstance(objective, str) or not objective.strip() or len(objective.encode()) > 2000:
        raise BilateralRuntimeProfileError("objective must be a non-empty bounded string")
    base_path = _path(raw.get("base_profile"), "base_profile")
    base = _v1.load_runtime_profile(root, base_path)
    contract = _contract(raw.get("intent_contract"))

    raw_allowed_paths = raw.get("allowed_paths", [])
    if not isinstance(raw_allowed_paths, list) or not raw_allowed_paths or len(raw_allowed_paths) > MAX_PATHS:
        raise BilateralRuntimeProfileError("allowed_paths must be a non-empty bounded array")
    allowed_paths = tuple(sorted(_path(item, "allowed_paths") for item in raw_allowed_paths))
    if len(set(allowed_paths)) != len(allowed_paths):
        raise BilateralRuntimeProfileError("allowed_paths must be unique and non-empty")
    raw_guardrail_ids = raw.get("guardrail_ids", [])
    if not isinstance(raw_guardrail_ids, list) or not raw_guardrail_ids or len(raw_guardrail_ids) > MAX_GUARDRAILS:
        raise BilateralRuntimeProfileError("guardrail_ids must be a non-empty bounded array")
    guardrails = tuple(sorted(_id(item, "guardrail_ids") for item in raw_guardrail_ids))
    if len(set(guardrails)) != len(guardrails):
        raise BilateralRuntimeProfileError("guardrail_ids must be unique and non-empty")
    for item in allowed_paths:
        _v1._safe_repo_path(root, item, "allowed path")
    if _json_digest(list(allowed_paths)) != contract["allowed_path_set_digest"]:
        raise BilateralRuntimeProfileError("allowed_path_set_digest does not match allowed_paths")
    if _json_digest(list(guardrails)) != contract["guardrail_set_digest"]:
        raise BilateralRuntimeProfileError("guardrail_set_digest does not match guardrail_ids")

    raw_traces = raw.get("required_trace_artifacts")
    if not isinstance(raw_traces, list) or not raw_traces or len(raw_traces) > MAX_TRACES:
        raise BilateralRuntimeProfileError("required_trace_artifacts must be a non-empty bounded array")
    traces = tuple(_path(item, "required_trace_artifacts") for item in raw_traces)
    admitted = set(base["probe"]["required_artifacts"]) | set(SPECIAL_TRACES)
    if len(set(traces)) != len(traces) or not set(traces).issubset(admitted):
        raise BilateralRuntimeProfileError("required traces are duplicated or not emitted by the V1 run")

    seen: set[str] = set()
    groups = {name: _assertions(raw.get(name), name, set(traces), seen) for name in GROUPS}
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, list) or not scenarios or len(scenarios) > MAX_SCENARIOS:
        raise BilateralRuntimeProfileError("scenarios must be a non-empty bounded array")
    scenario_rows, referenced, scenario_ids = [], set(), set()
    for index, item in enumerate(scenarios):
        if not isinstance(item, Mapping) or set(item) != {
            "scenario_id",
            "description",
            "required_assertion_ids",
        }:
            raise BilateralRuntimeProfileError(f"scenarios[{index}] is invalid")
        scenario_id = _id(item["scenario_id"], f"scenarios[{index}].scenario_id")
        raw_required = item["required_assertion_ids"]
        if not isinstance(raw_required, list) or len(raw_required) > MAX_ASSERTIONS:
            raise BilateralRuntimeProfileError(f"scenarios[{index}].required_assertion_ids must be a bounded array")
        required = tuple(_id(value, "required_assertion_ids") for value in raw_required)
        if scenario_id in scenario_ids or not required or not set(required).issubset(seen):
            raise BilateralRuntimeProfileError(f"scenarios[{index}] references invalid assertions")
        scenario_ids.add(scenario_id)
        referenced.update(required)
        scenario_rows.append(
            {
                "scenario_id": scenario_id,
                "description": str(item["description"])[:2000],
                "required_assertion_ids": required,
            }
        )
    if referenced != seen:
        raise BilateralRuntimeProfileError(f"scenarios leave assertions unreferenced: {sorted(seen - referenced)}")

    policy = raw.get("repair_policy")
    required_policy = {*FALSE_AUTHORITIES, "max_attempts", "retry_failed_assertions", "human_review_required"}
    if not isinstance(policy, Mapping) or set(policy) != required_policy:
        raise BilateralRuntimeProfileError("repair_policy must use the exact bounded schema")
    for field in FALSE_AUTHORITIES:
        if policy[field] is not False:
            raise BilateralRuntimeProfileError(f"repair_policy cannot grant {field}")
    if policy["max_attempts"] != 1 or policy["retry_failed_assertions"] is not False:
        raise BilateralRuntimeProfileError("persistent repair is deferred beyond B9")
    if policy["human_review_required"] is not True:
        raise BilateralRuntimeProfileError("repair_policy must require human review")

    verifier = raw.get("independent_verifier")
    if not isinstance(verifier, Mapping) or set(verifier) != {"verifier_id", "source_path", "source_sha256"}:
        raise BilateralRuntimeProfileError("independent_verifier must use the exact schema")
    verifier_id = _id(verifier["verifier_id"], "verifier_id")
    verifier_path = _path(verifier["source_path"], "verifier source")
    verifier_sha = _hex(verifier["source_sha256"], "verifier source_sha256")
    verifier_source = _v1._safe_repo_path(root, verifier_path, "independent verifier source")
    if verifier_id in {profile_id, candidate_id} or _v1._sha256(verifier_source) != verifier_sha:
        raise BilateralRuntimeProfileError("independent verifier identity or source digest mismatch")

    axioms = raw.get("axiom_bindings") or list(_v1.AXIOM_BINDINGS)
    if not isinstance(axioms, list) or not axioms or any(not isinstance(item, str) for item in axioms):
        raise BilateralRuntimeProfileError("axiom_bindings must be a non-empty string array")
    return {
        "version": PROFILE_VERSION,
        "profile_id": profile_id,
        "objective": objective.strip(),
        "runtime_candidate_id": candidate_id,
        "profile_path": path.relative_to(root).as_posix(),
        "profile_sha256": _v1._sha256(path),
        "base_profile": base_path,
        "base_profile_id": base["profile_id"],
        "base_profile_sha256": base["profile_sha256"],
        "intent_contract": contract,
        "allowed_paths": allowed_paths,
        "guardrail_ids": guardrails,
        "scenarios": tuple(scenario_rows),
        **groups,
        "required_trace_artifacts": traces,
        "repair_policy": dict(policy),
        "independent_verifier": {
            "verifier_id": verifier_id,
            "source_path": verifier_path,
            "source_sha256": verifier_sha,
        },
        "axiom_bindings": tuple(axioms),
    }


def _artifact(output: Path, name: str) -> Path:
    path = (output / Path(*PurePosixPath(name).parts)).resolve()
    try:
        path.relative_to(output)
    except ValueError as exc:
        raise BilateralRuntimeProfileError("runtime trace escaped the output directory") from exc
    return path


def _lookup(value: Any, path: str) -> tuple[bool, Any]:
    current = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _matches(actual: Any, operator: str, expected: Any) -> bool:
    if operator == "equals":
        return actual == expected
    if operator == "not_equals":
        return actual != expected
    if operator == "truthy":
        return bool(actual)
    if operator == "falsy":
        return not bool(actual)
    if operator == "nonempty":
        return hasattr(actual, "__len__") and len(actual) > 0
    try:
        return expected in actual
    except (TypeError, ValueError):
        return False


def _evaluate(output: Path, assertion: Mapping[str, Any]) -> dict[str, Any]:
    path = _artifact(output, str(assertion["artifact"]))
    value = _read_json(path, f"runtime trace {assertion['artifact']}", MAX_JSON_BYTES)
    found, actual = _lookup(value, str(assertion["json_path"]))
    return {
        **dict(assertion),
        "found": found,
        "actual": actual,
        "passed": found and _matches(actual, str(assertion["operator"]), assertion.get("expected")),
        "artifact_sha256": _v1._sha256(path),
    }


def _trace_inventory(output: Path, traces: Sequence[str]) -> list[dict[str, Any]]:
    maximum = int(getattr(_v1, "MAX_ARTIFACT_BYTES", 32 * 1024 * 1024))
    rows = []
    for name in traces:
        path = _artifact(output, name)
        present = path.is_file() and not path.is_symlink()
        size = path.stat().st_size if present else 0
        rows.append(
            {
                "path": name,
                "present": present,
                "size_bytes": size,
                "within_size_limit": present and size <= maximum,
                "sha256": _v1._sha256(path) if present and size <= maximum else None,
            }
        )
    return rows


def run_runtime_profile_v2(
    root: Path,
    *,
    profile_path: str | Path,
    output_dir: str | Path,
    venv_path: str | Path | None = None,
    install_requirements: bool = False,
    allow_dirty: bool = False,
    baseline_receipt: str | Path | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    profile = load_runtime_profile_v2(root, profile_path)
    output = _v1._external_output_path(root, output_dir)
    output.mkdir(parents=True, exist_ok=True)
    before = _repo_identity(root)
    if before["status"] and not allow_dirty:
        raise BilateralRuntimeProfileError("repository is dirty; V2 proof requires a clean tree")
    contract = profile["intent_contract"]
    expected_head = before["head"] if contract["expected_repository_head"] == CURRENT_HEAD else contract["expected_repository_head"]
    expected_tree = before["source_tree"] if contract["expected_source_tree"] == CURRENT_TREE else contract["expected_source_tree"]
    if before["head"] != expected_head:
        raise BilateralRuntimeProfileError("expected repository head mismatch")
    if before["source_tree"] != expected_tree:
        raise BilateralRuntimeProfileError("expected source-tree mismatch")

    base = _v1.run_runtime_profile(
        root,
        profile_path=profile["base_profile"],
        output_dir=output,
        venv_path=venv_path,
        install_requirements=install_requirements,
        allow_dirty=allow_dirty,
        baseline_receipt=baseline_receipt,
    )
    after = _repo_identity(root)
    results, by_id = {}, {}
    for group in GROUPS:
        results[group] = [_evaluate(output, row) for row in profile[group]]
        by_id.update({row["assertion_id"]: row for row in results[group]})
    scenarios = []
    for row in profile["scenarios"]:
        required = [by_id[item] for item in row["required_assertion_ids"]]
        scenarios.append(
            {
                **row,
                "passed": all(item["passed"] for item in required),
                "failed_assertion_ids": [item["assertion_id"] for item in required if not item["passed"]],
            }
        )
    traces = _trace_inventory(output, profile["required_trace_artifacts"])
    identity_ok = before == after
    ok = (
        bool(base.get("ok"))
        and identity_ok
        and all(item["passed"] for rows in results.values() for item in rows)
        and all(item["passed"] for item in scenarios)
        and all(item["present"] and item["within_size_limit"] for item in traces)
    )
    unproved = [item["assertion_id"] for rows in results.values() for item in rows if not item["passed"]]
    proof = {
        "version": VERSION,
        "profile_version": PROFILE_VERSION,
        "profile_id": profile["profile_id"],
        "profile_path": profile["profile_path"],
        "profile_sha256": profile["profile_sha256"],
        "base_profile_id": profile["base_profile_id"],
        "base_profile_sha256": profile["base_profile_sha256"],
        "runtime_candidate_id": profile["runtime_candidate_id"],
        "objective": profile["objective"],
        "ok": ok,
        "repository_identity_before": before,
        "repository_identity_after": after,
        "repository_identity_unchanged": identity_ok,
        "resolved_expected_repository_head": expected_head,
        "resolved_expected_source_tree": expected_tree,
        "intent_contract": profile["intent_contract"],
        "allowed_paths": list(profile["allowed_paths"]),
        "guardrail_ids": list(profile["guardrail_ids"]),
        "scenarios": scenarios,
        **results,
        "positive_requirements_proved": [item["assertion_id"] for item in results[GROUPS[0]] if item["passed"]],
        "negative_requirements_proved": [item["assertion_id"] for item in results[GROUPS[1]] if item["passed"]],
        "preservation_requirements_proved": [item["assertion_id"] for item in results[GROUPS[2]] if item["passed"]],
        "fault_behaviors_proved": [item["assertion_id"] for item in results[GROUPS[3]] if item["passed"]],
        "requirements_unproved": unproved,
        "guardrail_violations": [
            item["assertion_id"]
            for group in GROUPS[1:]
            for item in results[group]
            if not item["passed"]
        ],
        "required_trace_artifacts": traces,
        "independent_verifier": profile["independent_verifier"],
        "repair_policy": profile["repair_policy"],
        "base_runtime_receipt": {
            "version": base.get("version"),
            "profile_id": base.get("profile_id"),
            "run_digest": base.get("run_digest"),
            "ok": base.get("ok"),
            "cycle_state": base.get("cycle_state"),
        },
        "residual_risks": [] if ok else ["one or more runtime proof obligations remain unproved"],
        "human_review_required": True,
        "axiom_bindings": list(profile["axiom_bindings"]),
        **AUTHORITY_CONTRACT,
    }
    proof["proof_digest"] = _json_digest(proof)
    proof_path = output / "bilateral_runtime_proof.json"
    _v1._write_json(proof_path, proof)
    return {**proof, "proof_path": str(proof_path), "output_dir": str(output)}


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--venv")
    parser.add_argument("--install-requirements", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--baseline-receipt")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        result = run_runtime_profile_v2(
            Path(args.repo_root),
            profile_path=args.profile,
            output_dir=args.output_dir,
            venv_path=args.venv,
            install_requirements=args.install_requirements,
            allow_dirty=args.allow_dirty,
            baseline_receipt=args.baseline_receipt,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "version": VERSION,
                    "profile_version": PROFILE_VERSION,
                    "error": f"{type(exc).__name__}: {exc}",
                    **AUTHORITY_CONTRACT,
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
