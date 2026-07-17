"""Exact Aura Council/Surgeon repair for RefactorSkeleton Python 3.11 syntax.

Temporary repair capsule for PR #149. It selects between a broad rewrite and an
exact identity-expression repair, verifies the canonical argument list, compiles
the module, runs direct regressions, and records proposal-only evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from aura_architect_control import normalize_control_profile
from aura_arena_architect_connector import AuraArenaArchitectConnector

ROOT = Path(".").resolve()
TARGET = ROOT / "aura_refactor_skeleton.py"
EVIDENCE = (
    ROOT
    / "docs"
    / "evidence"
    / "AURA_SCO_PHASE3_REFACTOR_SKELETON_SURGEON_REPAIR.json"
)
OBJECTIVE = "Repair RefactorSkeleton Python 3.11 identity syntax exactly."
REQUIRED = [
    "syntax_integrity",
    "canonical_identity_equivalence",
    "bounded_patch_scope",
    "direct_skeleton_tests",
    "construction_plan_regression",
    "rollback",
]
EXPECTED_BODY = [
    '        expected_id = f"RFS-{_digest(_skeleton_identity(',
    "            objective=self.objective,",
    "            domain=self.domain,",
    "            baseline_commit=self.baseline_commit,",
    "            source_plan_digest=self.source_plan_digest,",
    "            addendum_digest=self.addendum_digest,",
    '        ))[:20]}"',
]
REPLACEMENT_BODY = [
    "        identity_digest = _digest(",
    "            _skeleton_identity(",
    "                objective=self.objective,",
    "                domain=self.domain,",
    "                baseline_commit=self.baseline_commit,",
    "                source_plan_digest=self.source_plan_digest,",
    "                addendum_digest=self.addendum_digest,",
    "            )",
    "        )",
    '        expected_id = f"RFS-{identity_digest[:20]}"',
]


def _candidate(
    candidate_id: str,
    family: str,
    coverage: list[str],
    reuse: bool,
    size: str,
) -> dict:
    return {
        "candidate_id": candidate_id,
        "arm_family": family,
        "provenance": {"generation": "frozen_local_plan", "model_calls": 0},
        "token_usage": {
            "provider_reported": None,
            "measurement_class": "NOT_MEASURED",
        },
        "plan": {
            "architecture_decision": (
                "Preserve canonical identity and replace one incompatible expression."
                if reuse
                else "Rewrite validation broadly."
            ),
            "act_tasks": [
                {
                    "task_id": "SKELETON-ID-EXPRESSION",
                    "objective": OBJECTIVE,
                    "target_file": "aura_refactor_skeleton.py",
                    "target_symbol": "RefactorSkeleton.__post_init__",
                    "acceptance": "Compile and direct regressions pass.",
                    "expected_output": "UNIFIED_DIFF",
                    "allowed_scope": "one identity expression",
                    "size": size,
                }
            ],
            "acceptance_criteria": [
                "Python 3.11 compile passes.",
                "Direct skeleton tests pass.",
                "Construction plan tests pass.",
            ],
            "rollback_conditions": ["Any failure blocks commit."],
            "risk_map": ["Identity semantics must remain equivalent."],
            "constraints": ["No API or authority changes."],
            "coverage_tags": coverage,
            "architecture_reuse": reuse,
            "existing_modules": (
                [
                    "aura_architect_control.py",
                    "aura_arena_architect_connector.py",
                    "aura_refactor_skeleton.py",
                ]
                if reuse
                else []
            ),
        },
    }


def _select_plan() -> dict:
    exact = _candidate(
        "EXACT_IDENTITY_SYNTAX_SURGEON",
        "SELECTIVE_COUNCIL_V3_PLUS_SURGEON",
        REQUIRED,
        True,
        "S",
    )
    broad = _candidate(
        "BROAD_REWRITE",
        "BROAD_IMPLEMENTER",
        ["syntax_integrity"],
        False,
        "L",
    )
    comparison = AuraArenaArchitectConnector(ROOT, bridge=object()).compare_plans(
        objective=OBJECTIVE,
        candidates=[broad, exact],
        required_capabilities=REQUIRED,
        control=normalize_control_profile(
            {
                "surface": "native",
                "council_mode": "SELECTIVE_V3",
                "council_call_budget": 4,
                "critic_lanes": ["scope", "tests", "rollback", "cost"],
                "surgeon_mode": "STAGE_AND_VERIFY",
                "surgeon_max_turns": 4,
                "surgeon_max_local_repairs": 1,
                "record_outputs": False,
            }
        ),
        surface="native",
        record=False,
        benchmark=False,
    )
    print(
        json.dumps(
            {
                "selected_candidate_id": comparison["selected_candidate_id"],
                "actual_model_calls": comparison["actual_model_calls"],
            },
            sort_keys=True,
        )
    )
    if comparison["selected_candidate_id"] != exact["candidate_id"]:
        raise SystemExit(f"unexpected plan: {comparison['selected_candidate_id']}")
    return comparison


def _patch_exact_span() -> tuple[bytes, bytes, dict]:
    before = TARGET.read_bytes()
    text = before.decode("utf-8")
    lines = text.splitlines(keepends=True)
    normalized = [line.rstrip("\r\n") for line in lines]
    starts = [
        index for index, line in enumerate(normalized) if line == EXPECTED_BODY[0]
    ]
    if len(starts) != 1:
        raise SystemExit(f"canonical identity start count {len(starts)} != 1")
    start = starts[0]
    actual = normalized[start : start + len(EXPECTED_BODY)]
    if actual != EXPECTED_BODY:
        raise SystemExit(
            "canonical identity argument block mismatch:\n"
            + json.dumps({"expected": EXPECTED_BODY, "actual": actual}, indent=2)
        )
    newline = "\r\n" if lines[start].endswith("\r\n") else "\n"
    replacement = [line + newline for line in REPLACEMENT_BODY]
    lines[start : start + len(EXPECTED_BODY)] = replacement
    TARGET.write_text("".join(lines), encoding="utf-8", newline="")
    after = TARGET.read_bytes()
    evidence = {
        "path": "aura_refactor_skeleton.py",
        "before_sha256": hashlib.sha256(before).hexdigest(),
        "after_sha256": hashlib.sha256(after).hexdigest(),
        "start_line": start + 1,
        "removed_line_count": len(EXPECTED_BODY),
        "added_line_count": len(REPLACEMENT_BODY),
        "identity_arguments_changed": False,
    }
    print(json.dumps(evidence, sort_keys=True))
    return before, after, evidence


def _run_tests() -> list[dict]:
    subprocess.run(
        [sys.executable, "-m", "py_compile", str(TARGET)],
        cwd=ROOT,
        check=True,
    )
    results = []
    for test_path in (
        "tests/test_aura_refactor_skeleton.py",
        "tests/test_aura_construction_refactor_plan.py",
    ):
        started = time.perf_counter()
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", test_path],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=240,
            check=False,
        )
        row = {
            "test": test_path,
            "ok": completed.returncode == 0,
            "returncode": completed.returncode,
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
        }
        results.append(row)
        print(json.dumps(row, sort_keys=True))
        if not row["ok"]:
            raise SystemExit(json.dumps(row, indent=2))
    return results


def main() -> int:
    comparison = _select_plan()
    _, _, source = _patch_exact_span()
    tests = _run_tests()
    evidence = {
        "version": "AURA_SCO_PHASE3_REFACTOR_SKELETON_SURGEON_REPAIR_V2",
        "objective": OBJECTIVE,
        "selected_plan_id": comparison["selected_candidate_id"],
        "actual_model_calls": comparison["actual_model_calls"],
        "council_comparison": comparison,
        "source": source,
        "tests": tests,
        "claim_boundaries": {
            "provider_tokens": "NOT_MEASURED",
            "provider_cost": "NOT_MEASURED",
            "production_mutation": False,
            "human_review_required": True,
            "patch_authority": "exact_source_spans_and_hashes_only",
            "vsa_patch_authority": False,
        },
    }
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
